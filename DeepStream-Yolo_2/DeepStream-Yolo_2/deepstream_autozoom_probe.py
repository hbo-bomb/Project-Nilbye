# deepstream_autozoom_probe.py — attach this probe to nvdsosd sink
import pyds
from ptz_autozoom import AutoZoomController

AUTO = AutoZoomController(
    min_area=0.02,
    max_area=0.10,
    center_deadband=0.12,
    zoom_cooldown=0.7,
    pan_cooldown=0.12
)

TARGET_CLASS_IDS = set()  # empty = all classes; or e.g. {0, 2}

def osd_sink_pad_buffer_probe(pad, info, u_data):
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        return
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    if batch_meta is None:
        return

    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        W = frame_meta.source_frame_width
        H = frame_meta.source_frame_height

        best = None
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            if (not TARGET_CLASS_IDS) or (obj_meta.class_id in TARGET_CLASS_IDS):
                rect = obj_meta.rect_params
                w = max(0.0, rect.width)
                h = max(0.0, rect.height)
                if w > 1 and h > 1:
                    area = w*h
                    if (best is None) or (area > best[0]):
                        best = (area, rect.left, rect.top, w, h)
            l_obj = l_obj.next

        if best is not None:
            _, x, y, w, h = best
            AUTO.update((x, y, w, h), (W, H))

        l_frame = l_frame.next
    return
