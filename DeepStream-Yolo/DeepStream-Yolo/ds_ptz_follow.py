#!/usr/bin/env python3
import time, requests, sys
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GObject', '2.0')
from gi.repository import Gst, GObject
import pyds

# ---------- YOUR CAM & MODEL ----------
RTSP = "rtsp://admin:krishna_01@192.168.188.108:554/cam/realmonitor?channel=1&subtype=0"
INFER_CFG = "/home/lain/DeepStream-Yolo/config_infer_primary_yoloV8.txt"
STREAMMUX_W, STREAMMUX_H = 1280, 1280
# --------------------------------------

# ---------- PTZ (Dahua CGI) ----------
CAMERA_IP = "192.168.188.108"
USERNAME  = "admin"
PASSWORD  = "krishna_01"
def dahua(action, direction, speed=3, tout=1.5):
    try:
        requests.get(
            f"http://{CAMERA_IP}/cgi-bin/ptz.cgi",
            params={"action": action, "code": direction, "speed": speed, "user": USERNAME, "password": PASSWORD},
            timeout=tout
        )
    except Exception as e:
        print("PTZ error:", e)

def nudge(vx, vy, dur=0.12):
    if abs(vx) < 1e-3 and abs(vy) < 1e-3: return
    if abs(vx) < 1e-3:
        move = "Up" if vy > 0 else "Down"; sp = max(1, min(8, int(round(3 + 5*abs(vy)))))
    elif abs(vy) < 1e-3:
        move = "Right" if vx > 0 else "Left"; sp = max(1, min(8, int(round(3 + 5*abs(vx)))))
    else:
        move = ("Right" if vx>0 else "Left")+("Up" if vy>0 else "Down")
        sp = max(1, min(8, int(round(3 + 5*max(abs(vx),abs(vy))))))

    dahua("start", move, sp); time.sleep(dur); dahua("stop", move, 0)

def zoom_step(direction="in", dur=0.18):
    code = "ZoomTele" if direction=="in" else "ZoomWide"
    dahua("start", code, 3); time.sleep(dur); dahua("stop", code, 0)
# --------------------------------------

# ---------- TARGETING TUNABLES ----------
CONF_MIN    = 0.50
CLASS_IDS   = (0,1,2,3)
PX_GOAL     = 100
DEAD_ZONE   = 0.03
GAIN        = 0.8
PAN_BURST   = 0.12
ZOOM_IN     = 0.18
ZOOM_OUT    = 0.15
# ---------------------------------------

Gst.init(None)

def make_element(factory, name=None):
    e = Gst.ElementFactory.make(factory, name if name else factory)
    if not e:
        print(f"Could not create element {factory}"); sys.exit(1)
    return e

def build_pipeline():
    pipeline = Gst.Pipeline.new("ds-ptz")

    # Source branch
    src = make_element("rtspsrc", "src")
    src.set_property("location", RTSP)
    src.set_property("latency", 200)
    depay = make_element("rtph264depay", "depay")
    parse = make_element("h264parse", "parse")
    dec   = make_element("nvv4l2decoder", "dec")

    # Streammux + infer + display
    mux = make_element("nvstreammux", "mux")
    mux.set_property("batch-size", 1)
    mux.set_property("width", STREAMMUX_W)
    mux.set_property("height", STREAMMUX_H)
    mux.set_property("live-source", 1)
    mux.set_property("enable-padding", 1)

    pgie = make_element("nvinfer", "pgie")
    pgie.set_property("config-file-path", INFER_CFG)

    nvosd = make_element("nvdsosd", "osd")
    sink  = make_element("nveglglessink", "sink")
    sink.set_property("sync", 0)

    # Add elements
    for e in [pipeline,]:
        pass
    for e in (depay, parse, dec, mux, pgie, nvosd, sink):
        pipeline.add(e)
    pipeline.add(src)

    # Dynamic pad from rtspsrc → depay
    def on_pad_added(src_elem, new_pad):
        caps = new_pad.get_current_caps()
        if caps and caps.to_string().startswith("application/x-rtp"):
            sinkpad = depay.get_static_pad("sink")
            if sinkpad and not sinkpad.is_linked():
                new_pad.link(sinkpad)
    src.connect("pad-added", on_pad_added)

    # Link depay → parse → dec
    if not depay.link(parse): print("link depay→parse failed"); sys.exit(1)
    if not parse.link(dec):   print("link parse→dec failed"); sys.exit(1)

    # Link dec → mux (request pad)
    sinkpad = mux.get_request_pad("sink_0")
    if not sinkpad: print("mux sink_0 request failed"); sys.exit(1)
    srcpad = dec.get_static_pad("src")
    if not srcpad: print("dec src pad missing"); sys.exit(1)
    if srcpad.link(sinkpad) != Gst.PadLinkReturn.OK:
        print("link dec→mux failed"); sys.exit(1)

    # Link mux → pgie → nvosd → sink
    if not mux.link(pgie):   print("link mux→pgie failed"); sys.exit(1)
    if not pgie.link(nvosd): print("link pgie→nvosd failed"); sys.exit(1)
    if not nvosd.link(sink): print("link nvosd→sink failed"); sys.exit(1)

    # Attach probe after PGIE (on nvosd sink)
    osd_sink_pad = nvosd.get_static_pad("sink")
    if not osd_sink_pad: print("Unable to get sink pad of nvosd"); sys.exit(1)
    osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, probe_after_pgie, None)

    return pipeline

def select_target(frame_meta):
    best = None
    l_obj = frame_meta.obj_meta_list
    while l_obj:
        obj = pyds.NvDsObjectMeta.cast(l_obj.data)
        if obj.confidence >= CONF_MIN and obj.class_id in CLASS_IDS:
            s = min(obj.rect_params.width, obj.rect_params.height)
            cx = obj.rect_params.left + obj.rect_params.width/2.0
            cy = obj.rect_params.top  + obj.rect_params.height/2.0
            cand = {"cx":cx,"cy":cy,"s":s}
            if best is None or cand["s"] < best["s"]:
                best = cand
        try:
            l_obj = l_obj.next
        except StopIteration:
            break
    return best

def probe_after_pgie(pad, info, udata):
    buf = info.get_buffer()
    if not buf: return Gst.PadProbeReturn.OK
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
    if not batch_meta: return Gst.PadProbeReturn.OK
    l_frame = batch_meta.frame_meta_list
    while l_frame:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        det = select_target(frame_meta)
        if det:
            cx, cy, s = det["cx"], det["cy"], det["s"]
            ex = (cx/STREAMMUX_W) - 0.5
            ey = (cy/STREAMMUX_H) - 0.5
            vx = 0 if abs(ex)<DEAD_ZONE else max(-1.0, min(1.0, GAIN*ex))
            vy = 0 if abs(ey)<DEAD_ZONE else max(-1.0, min(1.0, -GAIN*ey))
            if vx or vy: nudge(vx, vy, PAN_BURST)
            if   s < PX_GOAL*0.9:  zoom_step("in",  ZOOM_IN)
            elif s > PX_GOAL*1.2:  zoom_step("out", ZOOM_OUT)
        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK

def main():
    pipeline = build_pipeline()
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    def on_msg(bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, dbg = message.parse_error(); print("ERROR:", err, dbg); loop.quit()
        elif t == Gst.MessageType.EOS:
            loop.quit()
    bus.connect("message", on_msg)

    print("Starting pipeline… (disable Dahua Smart Tracking to avoid conflict)")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()

