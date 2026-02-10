# auto_zoom_probe.py
import os, sys, time, requests, gi
from requests.auth import HTTPDigestAuth
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GObject, GLib
import pyds

# ====== Choose your source ======
USE_USB = True                       # set False for RTSP
USB_DEV = "/dev/video0"              # your USB device
RTSP_URL = "rtsp://admin:krishna_01@192.168.188.108:554/Streaming/Channels/101"

# If you don't have a display or EGL issues, set this True
FAKESINK = False

# ====== PGIE config (your YOLOv8) ======
PGIE_CFG = "/home/lain/DeepStream-Yolo/config_infer_primary_yoloV8.txt"

# ====== Dahua PTZ ======
CAM_IP="192.168.188.108"; USER="admin"; PASSWORD="krishna_01"; CH=1
AUTH=HTTPDigestAuth(USER,PASSWORD)
BASE=f"http://{CAM_IP}/cgi-bin/ptz.cgi"
def ptz_tap(code, ms=120, speed=3):
    try:
        requests.get(BASE, params=dict(action="start",channel=CH,code=code,arg1=0,arg2=speed,arg3=0),
                     auth=AUTH, timeout=1.2)
        time.sleep(ms/1000.0)
    finally:
        try:
            requests.get(BASE, params=dict(action="stop",channel=CH,code=code,arg1=0,arg2=0,arg3=0),
                         auth=AUTH, timeout=1.2)
        except Exception:
            pass

# keep largest object between 20% and 40% of frame height
LOW_H, HIGH_H = 0.20, 0.40

def on_infer_out(pad, info, udata):
    buf = info.get_buffer()
    if not buf:
        return Gst.PadProbeReturn.OK
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
    l_frame = batch_meta.frame_meta_list
    while l_frame:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        H = float(frame_meta.source_frame_height) or 1.0
        max_frac_h = 0.0
        l_obj = frame_meta.obj_meta_list
        while l_obj:
            obj = pyds.NvDsObjectMeta.cast(l_obj.data)
            rect = obj.rect_params
            frac_h = rect.height / H
            if frac_h > max_frac_h:
                max_frac_h = frac_h
            l_obj = l_obj.next
        if max_frac_h and max_frac_h < LOW_H:
            ptz_tap("ZoomTele", ms=120, speed=3)
        elif max_frac_h and max_frac_h > HIGH_H:
            ptz_tap("ZoomWide", ms=120, speed=3)
        l_frame = l_frame.next
    return Gst.PadProbeReturn.OK

def make_pipeline():
    sink = "fakesink sync=0" if FAKESINK else "nveglglessink sync=0"
    if USE_USB:
        return Gst.parse_launch(
            f'v4l2src device={USB_DEV} ! image/jpeg,framerate=30/1 ! jpegdec ! '
            'videoconvert ! nvvideoconvert ! video/x-raw(memory:NVMM),format=NV12 ! '
            'm.sink_0 nvstreammux name=m batch-size=1 width=1280 height=720 live-source=1 ! '
            f'nvinfer config-file-path={PGIE_CFG} name=pgie ! '
            'nvdsosd name=osd ! ' + sink
        )
    else:
        return Gst.parse_launch(
            f'uridecodebin uri="{RTSP_URL}" name=srcbin '
            'srcbin. ! queue ! nvvideoconvert ! video/x-raw(memory:NVMM),format=NV12 ! '
            'm.sink_0 nvstreammux name=m batch-size=1 width=1280 height=720 live-source=1 ! '
            f'nvinfer config-file-path={PGIE_CFG} name=pgie ! '
            'nvdsosd name=osd ! ' + sink
        )


def on_bus_msg(bus, msg, loop):
    t = msg.type
    if t == Gst.MessageType.ERROR:
        err, dbg = msg.parse_error()
        print("\n*** GStreamer ERROR:", err.message)
        if dbg: print("    Debug:", dbg)
        loop.quit()
    elif t == Gst.MessageType.EOS:
        print("EOS")
        loop.quit()
    return True

def main():
    Gst.init(None)
    pipeline = make_pipeline()
    pgie = pipeline.get_by_name("pgie")
    if not pgie:
        raise RuntimeError("nvinfer not found in pipeline")
    pgie.get_static_pad("src").add_probe(Gst.PadProbeType.BUFFER, on_infer_out, None)

    bus = pipeline.get_bus()
    loop = GLib.MainLoop()
    bus.add_signal_watch()
    bus.connect("message", on_bus_msg, loop)

    pipeline.set_state(Gst.State.PLAYING)
    print("Auto-zoom running. Ctrl+C to stop.")
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()

