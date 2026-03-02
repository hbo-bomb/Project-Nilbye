#!/usr/bin/env python3
# Auto-zoom PTZ using DeepStream (YOLOv8 PGIE) + Dahua CGI (relative zoom pulses).
# Adds SEEK mode: proactively zooms in until a detection appears, then tracks.

import sys, os, time, threading, argparse, requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth

# ---------------------------
# CLI
# ---------------------------
p = argparse.ArgumentParser(description="DeepStream auto-zoom (Dahua PTZ relative zoom) with SEEK-before-detect")
p.add_argument("--uri", required=True, help="RTSP URL of Dahua MAIN stream (subtype=0)")
p.add_argument("--dahua_ip", required=True, help="Dahua camera IP/host (e.g., 192.168.188.108)")
p.add_argument("--user", default="admin", help="Dahua username")
p.add_argument("--password", required=True, help="Dahua password")
p.add_argument("--channel", type=int, default=1, help="Dahua channel (usually 1)")
p.add_argument("--infer", default="config_infer_primary_yoloV8.txt", help="Path to your YOLOv8 nvinfer config")
p.add_argument("--allowed-ids", default="0", help="Comma-separated class IDs that should trigger auto-zoom (e.g., '0,2')")

# TRACK controller params
p.add_argument("--target-frac", type=float, default=0.20, help="Target bbox height as fraction of frame height")
p.add_argument("--low-band", type=float, default=0.18, help="Lower band for hysteresis (zoom in below)")
p.add_argument("--high-band", type=float, default=0.22, help="Upper band for hysteresis (zoom out above)")
p.add_argument("--rate-hz", type=float, default=3.0, help="PTZ command/check rate")

# SEEK mode (proactive zoom-in) params
p.add_argument("--enable-seek", action="store_true", help="Enable seek mode (proactive zoom-in until detect)")
p.add_argument("--no-det-timeout", type=float, default=1.0, help="If no detection for this many seconds, enter SEEK")
p.add_argument("--seek-pulse-ms", type=int, default=250, help="ZoomTele pulse length in SEEK")
p.add_argument("--seek-pulses", type=int, default=12, help="Number of consecutive Tele pulses per SEEK cycle")
p.add_argument("--seek-relax-ms", type=int, default=150, help="Small ZoomWide pulse between cycles to avoid hard-stop")
p.add_argument("--seek-sleep", type=float, default=0.25, help="Pause between SEEK pulses (seconds)")

p.add_argument("--display", action="store_true", help="Show EGL window (omit for headless)")
args = p.parse_args()

ALLOWED_CLASS_IDS = {int(x) for x in args.allowed_ids.split(",") if x.strip() != ""}

# ---------------------------
# Dahua PTZ helpers (relative pulses)
# ---------------------------
session = requests.Session()
session.auth = HTTPDigestAuth(args.user, args.password)
session.timeout = 1.5

def _ptz_call(params):
    """Call Dahua PTZ CGI, fallback to Basic auth if Digest 401."""
    url = f"http://{args.dahua_ip}/cgi-bin/ptz.cgi"
    r = session.get(url, params=params, timeout=1.5, allow_redirects=False)
    if r.status_code == 401:
        session.auth = HTTPBasicAuth(args.user, args.password)
        r = session.get(url, params=params, timeout=1.5, allow_redirects=False)
    return r

def dahua_zoom_pulse(direction: int, ms: int = 250):
    """
    direction: +1 = zoom in (tele), -1 = zoom out (wide)
    ms: pulse duration in milliseconds
    """
    code = "ZoomTele" if direction > 0 else "ZoomWide"
    r1 = _ptz_call({"action":"start","channel":str(args.channel),
                    "code":code,"arg1":"0","arg2":"0","arg3":"0"})
    print(f"[PTZ] start {code} → {r1.status_code}")
    time.sleep(max(0.05, ms/1000.0))
    r2 = _ptz_call({"action":"stop","channel":str(args.channel),
                    "code":code,"arg1":"0","arg2":"0","arg3":"0"})
    print(f"[PTZ] stop  {code} → {r2.status_code}")

# ---------------------------
# DeepStream / GStreamer
# ---------------------------
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GObject", "2.0")
from gi.repository import Gst, GObject, GLib
import pyds

Gst.init(None)

# Shared state b/w probe and controller
latest = {"h_frac": None, "ts": 0.0, "last_det_ts": 0.0}
state  = {"ema": None}

TARGET_FRAC = args.target_frac
LOW_BAND    = args.low_band
HIGH_BAND   = args.high_band
RATE_HZ     = args.rate_hz
EMA_ALPHA   = 0.30  # smoothing for bbox height

# ---------------------------
# SEEK + TRACK state machine
# ---------------------------
def controller_thread():
    """
    If --enable-seek and no detection for > no-det-timeout:
       -> SEEK: send ZoomTele pulses to increase pixel-on-target.
    Else:
       -> TRACK: use banded control to keep box height near TARGET_FRAC.
    """
    tick = max(0.05, 1.0 / max(0.5, RATE_HZ))
    seek_cycle_pulses = 0
    print(f"[CTRL] rate={1.0/tick:.2f} Hz, bands=({LOW_BAND:.2f},{HIGH_BAND:.2f}), target={TARGET_FRAC:.2f}, seek={args.enable_seek}")

    while True:
        now = time.time()
        h = latest["h_frac"]
        last_det_age = now - (latest["last_det_ts"] or 0.0)

        if args.enable_seek and (last_det_age > args.no_det_timeout):
            # SEEK mode: zoom in until we get any allowed-class detection
            print(f"[SEEK] no detection for {last_det_age:.2f}s → zoom in")
            if seek_cycle_pulses < max(1, args.seek_pulses):
                dahua_zoom_pulse(+1, args.seek_pulse_ms)
                seek_cycle_pulses += 1
                time.sleep(max(tick, args.seek_sleep))
            else:
                # small relax pulse to avoid slamming at hard tele limit
                dahua_zoom_pulse(-1, args.seek_relax_ms)
                seek_cycle_pulses = 0
                time.sleep(max(tick, args.seek_sleep))
            continue  # skip TRACK logic this tick

        # TRACK mode (we have a recent detection)
        seek_cycle_pulses = 0  # reset cycle state
        if h is not None:
            ema = state["ema"] = (h if state["ema"] is None else EMA_ALPHA*h + (1-EMA_ALPHA)*state["ema"])
            if ema < LOW_BAND:
                err = (TARGET_FRAC - ema) / max(1e-6, TARGET_FRAC)
                pulse_ms = int(min(400, max(100, 600*err)))  # 100–400 ms
                dahua_zoom_pulse(+1, pulse_ms)
            elif ema > HIGH_BAND:
                err = (ema - TARGET_FRAC) / max(1e-6, TARGET_FRAC)
                pulse_ms = int(min(400, max(100, 600*err)))
                dahua_zoom_pulse(-1, pulse_ms)

        time.sleep(tick)

def pgie_src_pad_buffer_probe(pad, info, u_data):
    """
    Reads DeepStream metadata from PGIE, picks best detection in ALLOWED_CLASS_IDS,
    and updates latest["h_frac"] with bbox height fraction.
    """
    buffer = info.get_buffer()
    if not buffer:
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buffer))
    if not batch_meta:
        return Gst.PadProbeReturn.OK

    best_h_frac, best_conf = None, -1.0
    l_frame = batch_meta.frame_meta_list
    while l_frame:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        frame_h = int(frame_meta.source_frame_height)

        l_obj = frame_meta.obj_meta_list
        while l_obj:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            cid = int(obj_meta.class_id)
            if cid in ALLOWED_CLASS_IDS:
                conf = float(obj_meta.confidence)
                rect = obj_meta.rect_params
                h_pix = float(rect.height)
                h_frac = h_pix / float(frame_h) if frame_h else 0.0
                if conf > best_conf:
                    best_conf = conf
                    best_h_frac = h_frac
            try:
                l_obj = l_obj.next
            except StopIteration:
                break
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    if best_h_frac is not None:
        latest["h_frac"] = best_h_frac
        latest["ts"] = time.time()
        latest["last_det_ts"] = latest["ts"]
        print(f"[DETECT] h_frac={best_h_frac:.3f} (conf={best_conf:.2f})")

    return Gst.PadProbeReturn.OK

def build_pipeline():
    """
    uridecodebin → nvvideoconvert → caps(NVMM) → nvstreammux(1280x1280, pad) → nvinfer → nvdsosd → sink
    """
    pipeline = Gst.Pipeline.new("ds-autozoom")

    # Source (decodebin handles depay/parse/decode)
    src = Gst.ElementFactory.make("uridecodebin", "src")
    if not src:
        raise RuntimeError("Could not create uridecodebin")
    src.set_property("uri", args.uri)

    # Convert to NVMM (DeepStream expects NV12 in NVMM)
    vidconv = Gst.ElementFactory.make("nvvideoconvert", "vidconv")
    capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
    caps = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=NV12")
    capsfilter.set_property("caps", caps)

    mux = Gst.ElementFactory.make("nvstreammux", "streammux")
    mux.set_property("batch-size", 1)
    mux.set_property("width", 1280)
    mux.set_property("height", 1280)
    mux.set_property("enable-padding", 1)
    mux.set_property("live-source", 1)

    pgie = Gst.ElementFactory.make("nvinfer", "primary-infer")
    pgie.set_property("config-file-path", args.infer)

    osd = Gst.ElementFactory.make("nvdsosd", "osd")
    sink = Gst.ElementFactory.make("nveglglessink" if args.display else "fakesink", "sink")
    sink.set_property("sync", 0)

    for e in [vidconv, capsfilter, mux, pgie, osd, sink]:
        if not e:
            raise RuntimeError("Failed to create a pipeline element (check DeepStream install)")
        pipeline.add(e)

    # uridecodebin → vidconv (video pad only)
    def on_pad_added(src_, pad):
        caps = pad.get_current_caps()
        if caps:
            s = caps.to_string()
            if not s.startswith("video/"):
                return
        sink_pad = vidconv.get_static_pad("sink")
        if not sink_pad.is_linked():
            pad.link(sink_pad)

    src.connect("pad-added", on_pad_added)
    pipeline.add(src)

    # static links
    if not vidconv.link(capsfilter):
        raise RuntimeError("link vidconv→capsfilter failed")

    sinkpad = mux.get_request_pad("sink_0")
    if not sinkpad:
        raise RuntimeError("Unable to get request pad sink_0 from streammux")
    srcpad = capsfilter.get_static_pad("src")
    if srcpad.link(sinkpad) != Gst.PadLinkReturn.OK:
        raise RuntimeError("link capsfilter→streammux sink_0 failed")

    if not mux.link(pgie):
        raise RuntimeError("link streammux→pgie failed")
    if not pgie.link(osd):
        raise RuntimeError("link pgie→osd failed")
    if not osd.link(sink):
        raise RuntimeError("link osd→sink failed")

    # Attach PGIE src pad probe
    pgie_src_pad = pgie.get_static_pad("src")
    if not pgie_src_pad:
        raise RuntimeError("Unable to get PGIE src pad")
    pgie_src_pad.add_probe(Gst.PadProbeType.BUFFER, pgie_src_pad_buffer_probe, None)

    return pipeline

def main():
    pipeline = build_pipeline()
    threading.Thread(target=controller_thread, daemon=True).start()
    loop = GLib.MainLoop()
    pipeline.set_state(Gst.State.PLAYING)
    try:
        print("[RUN] Pipeline playing. Ctrl+C to stop.")
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()

