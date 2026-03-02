
#!/usr/bin/env python3
# ds7_ptz_follow.py — DeepStream 7.1 + YOLOv8 PTZ follow (Dahua CGI)
# FIXES:
#  - tracker-height set to 384 (multiple of 32)
#  - robust batch_meta getter for DS 7.1 vs older Python bindings
#  - guards for missing meta

import os, time, math
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import pyds

# === Import our PTZ controller (CGI backend) ===
import ptz_control as PTZ

# ---- Tunables (adjust to your stream/output) ----
FRAME_W = 1280   # must match nvstreammux out size
FRAME_H = 1280
TRACK_CLASS_IDS = {0,1,2,3}   # your 4 YOLOv8 classes

DEAD_ZONE = 0.03             # fraction of frame; no PTZ if error below
BURST_SEC = 0.12             # PTZ "start" duration per pulse
REFRACTORY_SEC = 0.10        # min gap between pulses
ZOOM_IN_THRESH = 0.12        # zoom in when bbox height < 12% of frame
ZOOM_BURST_SEC = 0.10

_last_ptz  = 0.0
_last_zoom = 0.0

def choose_direction(ex, ey):
    # ex>0 => target right of center => pan Right
    # ey>0 => target above center (screen y down) => "Up"
    if abs(ex) <= DEAD_ZONE and abs(ey) <= DEAD_ZONE:
        return None
    horiz = "Right" if ex > 0 else "Left"
    vert  = "Up" if ey > 0 else "Down"
    if abs(ex) > DEAD_ZONE and abs(ey) > DEAD_ZONE:
        return vert + horiz  # e.g., "RightUp"
    elif abs(ex) > abs(ey):
        return horiz
    else:
        return vert

def zoom_if_needed(bbox_h_frac):
    global _last_zoom
    now = time.time()
    if bbox_h_frac < ZOOM_IN_THRESH and (now - _last_zoom) > REFRACTORY_SEC:
        PTZ.start_move("ZoomTele")
        time.sleep(ZOOM_BURST_SEC)
        PTZ.stop_move("ZoomTele")
        _last_zoom = now

def get_batch_meta(gst_buffer):
    """
    Works across DeepStream Python bindings variants:
    - pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
    - pyds.nvds_get_batch_meta(hash(buf))   (fallback for newer)
    """
    h = hash(gst_buffer)
    if hasattr(pyds, "gst_buffer_get_nvds_batch_meta"):
        return pyds.gst_buffer_get_nvds_batch_meta(h)
    elif hasattr(pyds, "nvds_get_batch_meta"):
        return pyds.nvds_get_batch_meta(h)
    else:
        return None

def osd_sink_pad_buffer_probe(pad, info, u_data):
    global _last_ptz
    buffer = info.get_buffer()
    if not buffer:
        return Gst.PadProbeReturn.OK

    batch_meta = get_batch_meta(buffer)
    if not batch_meta:
        return Gst.PadProbeReturn.OK

    l_frame = batch_meta.frame_meta_list
    while l_frame:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except Exception:
            break

        best = None
        best_area = 0.0

        l_obj = frame_meta.obj_meta_list
        while l_obj:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except Exception:
                break
            if obj_meta.class_id in TRACK_CLASS_IDS:
                r = obj_meta.rect_params
                area = float(r.width * r.height)
                if area > best_area:
                    best_area = area
                    best = r
            l_obj = l_obj.next

        if best:
            cx = (best.left + best.width * 0.5) / FRAME_W
            cy = (best.top  + best.height* 0.5) / FRAME_H
            ex = 0.5 - cx
            ey = 0.5 - cy

            direction = choose_direction(ex, ey)
            now = time.time()
            if direction and (now - _last_ptz) > REFRACTORY_SEC:
                PTZ.start_move(direction)
                time.sleep(BURST_SEC)
                PTZ.stop_move(direction)
                _last_ptz = now

            bbox_h_frac = best.height / FRAME_H
            zoom_if_needed(bbox_h_frac)

        l_frame = l_frame.next if hasattr(l_frame, "next") else None

    return Gst.PadProbeReturn.OK

def build_pipeline(rtsp_url, infer_config_path):
    Gst.init(None)
    pipeline = Gst.Pipeline()

    # Source
    src = Gst.ElementFactory.make("rtspsrc", "src")
    src.set_property("location", rtsp_url)
    src.set_property("latency", 200)

    depay = Gst.ElementFactory.make("rtph264depay", "depay")
    h264p = Gst.ElementFactory.make("h264parse", "h264p")
    dec   = Gst.ElementFactory.make("nvv4l2decoder", "dec")

    mux = Gst.ElementFactory.make("nvstreammux", "mux")
    mux.set_property("batch-size", 1)
    mux.set_property("live-source", 1)
    mux.set_property("width", FRAME_W)
    mux.set_property("height", FRAME_H)
    mux.set_property("batched-push-timeout", 40000)

    pgie = Gst.ElementFactory.make("nvinfer", "primary-infer")
    pgie.set_property("config-file-path", infer_config_path)

    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    tracker.set_property("tracker-width", 640)
    tracker.set_property("tracker-height", 384)  # multiple of 32
    tracker.set_property("ll-lib-file", "/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so")
    tracker.set_property("ll-config-file", "/opt/nvidia/deepstream/deepstream/samples/configs/deepstream-app/config_tracker_NvDCF_perf.yml")

    nvosd = Gst.ElementFactory.make("nvdsosd", "osd")

    sink = Gst.ElementFactory.make("nveglglessink", "sink")
    sink.set_property("sync", 0)

    # rtspsrc has dynamic pads; connect to depay on "pad-added"
    def on_pad_added(src, pad):
        pad_caps = pad.query_caps(None)
        name = pad_caps.to_string()
        if "application/x-rtp" in name:
            pad.link(depay.get_static_pad("sink"))

    src.connect("pad-added", on_pad_added)

    for el in (src, depay, h264p, dec, mux, pgie, tracker, nvosd, sink):
        pipeline.add(el)

    depay.link(h264p); h264p.link(dec)
    sinkpad = mux.get_request_pad("sink_0")
    srcpad  = dec.get_static_pad("src")
    srcpad.link(sinkpad)

    mux.link(pgie); pgie.link(tracker); tracker.link(nvosd); nvosd.link(sink)

    # Attach our probe on OSD sink pad (post-tracker bboxes)
    osd_sink_pad = nvosd.get_static_pad("sink")
    osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, None)

    return pipeline

def main():
    # Edit these two to your actual values:
    rtsp_url = "rtsp://admin:krishna_01@192.168.188.108:554/cam/realmonitor?channel=1&subtype=0"
    infer_config_path = "./config_infer_primary_yoloV8.txt"

    PTZ.stop_all()

    pipeline = build_pipeline(rtsp_url, infer_config_path)
    loop = GLib.MainLoop()
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)
        PTZ.stop_all()

if __name__ == "__main__":
    main()
