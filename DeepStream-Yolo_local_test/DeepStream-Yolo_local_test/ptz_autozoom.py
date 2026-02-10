#!/usr/bin/env python3
# Motion-triggered PTZ centerer for Dahua PTZ (no IVS/MQTT).
# Pan/Tilt to center motion; optional zoom (can be disabled with --no-zoom).

import time, threading, argparse, requests, cv2, signal
from requests.auth import HTTPDigestAuth, HTTPBasicAuth

# ---------------- CLI ----------------
p = argparse.ArgumentParser("Motion-triggered PTZ for Dahua")
p.add_argument("--uri", "--main-uri", dest="main_uri", required=True,
               help="RTSP MAIN stream (subtype=0). If --sub-uri is omitted, this is also used for motion.")
p.add_argument("--sub-uri", default=None,
               help="(Optional) RTSP SUB stream (subtype=1) for cheaper motion detection.")
p.add_argument("--force-tcp", action="store_true",
               help="Open RTSP via GStreamer rtspsrc protocols=tcp (reduces RTP warnings).")
p.add_argument("--rtsp-latency", type=int, default=200, help="rtspsrc latency (ms) when --force-tcp")
p.add_argument("--dahua-ip", required=True)
p.add_argument("--user", default="admin")
p.add_argument("--password", required=True)
p.add_argument("--channel", type=int, default=1)

# Motion ROI
p.add_argument("--roi", default="0.25,0.75,0.25,0.75",
               help="ROI (fractions) xmin,xmax,ymin,ymax")
p.add_argument("--motion-fps", type=float, default=5.0, help="Process at ~this FPS")
p.add_argument("--motion-thresh", type=int, default=22, help="MOG2 varThreshold (lower = more sensitive)")
p.add_argument("--min-area-frac", type=float, default=0.0015, help="Min contour area fraction to trigger")
p.add_argument("--min-persist", type=int, default=4, help="Frames-in-ROI required to arm PTZ")
p.add_argument("--downscale", type=float, default=1.0, help="Downscale factor for motion frames (e.g., 0.5)")

# PT behavior (no zoom by default if --no-zoom is set)
p.add_argument("--no-zoom", action="store_true", help="Disable zoom; only pan/tilt to center motion")
p.add_argument("--target-size", type=float, default=0.15, help="Desired blob height fraction (used only if zoom enabled)")
p.add_argument("--zoom-band", type=float, default=0.03, help="Deadband around target height (± fraction)")
p.add_argument("--deadband", type=float, default=0.05, help="Center deadband for pan/tilt")
p.add_argument("--ptz-rate-hz", type=float, default=2.0, help="How often to send PTZ pulses")
p.add_argument("--max-pulse-ms", type=int, default=250)
p.add_argument("--zoom-base-ms", type=int, default=100, help="Base ms for zoom pulses")
p.add_argument("--zoom-gain-ms-per-err", type=int, default=300,
               help="Added ms = gain * normalized size error")
p.add_argument("--pan-tilt-gain-ms", type=int, default=300,
               help="Pulse ms = 100 + gain*abs(error) for pan/tilt")
p.add_argument("--show", action="store_true", help="Show debug window (ROI/motion)")
args = p.parse_args()

# Parse ROI
ROI = tuple(max(0.0, min(1.0, float(x))) for x in args.roi.split(","))
if len(ROI) != 4:
    raise SystemExit("ROI must be four comma-separated fractions: xmin,xmax,ymin,ymax")

# ------------- Dahua PTZ helpers (HTTP) -------------
session = requests.Session()
session.auth = HTTPDigestAuth(args.user, args.password)
session.timeout = 1.5

def _ptz_call(params):
    url = f"http://{args.dahua_ip}/cgi-bin/ptz.cgi"
    r = session.get(url, params=params, timeout=1.5, allow_redirects=False)
    if r.status_code == 401:
        session.auth = HTTPBasicAuth(args.user, args.password)
        r = session.get(url, params=params, timeout=1.5, allow_redirects=False)
    return r

def ptz_pulse(code: str, ms: int = 200):
    _ptz_call({"action":"start","channel":str(args.channel),
               "code":code,"arg1":"0","arg2":"0","arg3":"0"})
    time.sleep(max(0.05, ms/1000.0))
    _ptz_call({"action":"stop","channel":str(args.channel),
               "code":code,"arg1":"0","arg2":"0","arg3":"0"})

def pan_tilt_to_center(cx_frac, cy_frac):
    ex = cx_frac - 0.5
    ey = cy_frac - 0.5
    if abs(ex) > args.deadband:
        ms = int(min(args.max_pulse_ms, 100 + args.pan_tilt_gain_ms*abs(ex)))
        ptz_pulse("Right" if ex > 0 else "Left", ms)
    if abs(ey) > args.deadband:
        ms = int(min(args.max_pulse_ms, 100 + args.pan_tilt_gain_ms*abs(ey)))
        ptz_pulse("Down" if ey > 0 else "Up", ms)

def zoom_towards(target_h_frac, h_frac):
    if args.no_zoom:
        return  # zoom disabled
    low = target_h_frac - args.zoom_band
    if h_frac < low:
        err = (target_h_frac - h_frac) / max(1e-6, target_h_frac)  # 0..1
        ms = int(min(args.max_pulse_ms, args.zoom_base_ms + args.zoom_gain_ms_per_err*err))
        ptz_pulse("ZoomTele", ms)

# ------------- Global state -------------
running = True
motion = {"active": False, "cx": 0.5, "cy": 0.5, "h": 0.0, "last_ts": 0.0}

# ------------- Stream helpers -------------
def open_capture(uri: str):
    if args.force_tcp:
        gst = (
            f"rtspsrc location=\"{uri}\" protocols=tcp latency={args.rtsp_latency} ! "
            f"rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! "
            f"video/x-raw,format=BGR ! appsink drop=true max-buffers=1 sync=false"
        )
        cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
    else:
        cap = cv2.VideoCapture(uri, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap = cv2.VideoCapture(uri)
    return cap

# ------------- Motion worker -------------
def motion_worker():
    global running
    uri = args.sub_uri or args.main_uri
    print(f"[MOTION] reading: {uri} ({'sub' if args.sub_uri else 'main'}; {'TCP' if args.force_tcp else 'FFmpeg/UDP'})")
    cap = open_capture(uri)
    if not cap.isOpened():
        print("[MOTION] Cannot open stream"); running = False; return

    cap.set(cv2.CAP_PROP_FPS, args.motion_fps)
    bs = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=args.motion_thresh, detectShadows=False)

    persist = 0
    interval = 1.0 / max(1.0, args.motion_fps)

    if args.show:
        cv2.namedWindow("PTZ Motion", cv2.WINDOW_NORMAL)

    while running:
        t0 = time.time()
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.2); continue

        view = frame.copy()
        if args.downscale != 1.0:
            frame = cv2.resize(frame, (0,0), fx=args.downscale, fy=args.downscale)
            view  = cv2.resize(view,  (0,0), fx=args.downscale, fy=args.downscale)

        H, W = frame.shape[:2]
        xmin,xmax,ymin,ymax = ROI
        rx1, rx2 = int(xmin*W), int(xmax*W)
        ry1, ry2 = int(ymin*H), int(ymax*H)

        roi = frame[ry1:ry2, rx1:rx2]
        fg = bs.apply(roi)
        fg = cv2.medianBlur(fg, 5)
        _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)), iterations=1)
        cnts = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]

        biggest, best_area = None, 0.0
        for c in cnts:
            area = cv2.contourArea(c)
            if area > best_area:
                best_area = area; biggest = c

        area_frac = best_area / float((rx2-rx1)*(ry2-ry1) + 1e-6)

        active_now = False
        cx_frac = cy_frac = h_frac = 0.0
        if biggest is not None and area_frac > args.min_area_frac:
            x,y,w,h = cv2.boundingRect(biggest)
            cx = rx1 + x + w/2.0
            cy = ry1 + y + h/2.0
            cx_frac = cx / float(W)
            cy_frac = cy / float(H)
            h_frac  = h / float(H)

            persist = min(args.min_persist, persist + 1)
            if persist >= args.min_persist:
                active_now = True
                motion.update({
                    "active": True, "cx": cx_frac, "cy": cy_frac,
                    "h": h_frac, "last_ts": time.time()
                })
        else:
            persist = max(0, persist - 1)
            if time.time() - motion["last_ts"] > 1.0:
                motion.update({"active": False})

        if args.show:
            cv2.rectangle(view, (rx1, ry1), (rx2, ry2), (0,255,255), 2)
            cpx, cpy = int(W*0.5), int(H*0.5)
            db = int(min(W,H) * args.deadband)
            cv2.rectangle(view, (cpx-db, cpy-db), (cpx+db, cpy+db), (128,128,128), 1)
            if biggest is not None:
                x,y,w,h = cv2.boundingRect(biggest)
                cv2.rectangle(view, (rx1+x, ry1+y), (rx1+x+w, ry1+y+h), (0,255,0), 2)
                cv2.circle(view, (int(cx_frac*W), int(cy_frac*H)), 4, (0,0,255), -1)
            status = "ACTIVE" if active_now else ("ARMED" if persist>0 else "IDLE")
            cv2.putText(view, f"Status:{status} h={h_frac:.3f} target={args.target_size:.3f} (zoom {'OFF' if args.no_zoom else 'ON'})",
                        (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.imshow("PTZ Motion", view)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                running = False
                break

        dt = time.time() - t0
        if dt < interval:
            time.sleep(interval - dt)

    cap.release()
    if args.show:
        cv2.destroyAllWindows()

# ------------- Controller loop -------------
def controller_loop():
    tick = 1.0 / max(1.0, args.ptz_rate_hz)
    print(f"[CTRL] PTZ at {1.0/tick:.2f} Hz. ROI={ROI}, zoom={'OFF' if args.no_zoom else 'ON'}")
    while running:
        m = motion.copy
        m = motion.copy()
        if m["active"]:
            pan_tilt_to_center(m["cx"], m["cy"])
            zoom_towards(args.target_size, m["h"])  # will no-op if --no-zoom
        time.sleep(tick)

# ---------------- RUN ----------------
def main():
    def _sigint(_a,_b):
        global running; running = False
    signal.signal(signal.SIGINT, _sigint)

    t = threading.Thread(target=motion_worker, daemon=True)
    t.start()
    try:
        controller_loop()
    finally:
        global running; running = False
        t.join(timeout=0.5)
        if args.show:
            try: cv2.destroyAllWindows()
            except: pass

if __name__ == "__main__":
    main()

