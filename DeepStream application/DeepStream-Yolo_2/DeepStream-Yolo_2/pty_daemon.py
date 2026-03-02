# auto_zoom_daemon.py
import json, time, math, paho.mqtt.client as mqtt, requests
from requests.auth import HTTPDigestAuth

# ==== EDIT THESE ====
BROKER="127.0.0.1"; TOPIC="deepstream/events"

CAM_IP="192.168.188.108"
USER="admin"
PASSWORD="krishna_01"
CHANNEL=1

TARGET_CLASS = "person"     # e.g., "person" or your exact label (e.g., "nilgai")
LOW, HIGH = 0.20, 0.40      # bbox-height fraction hysteresis band
ZOOM_SPEED = 3              # 0..8
COOLDOWN_MS = 400           # min time between commands
EMA_ALPHA = 0.3             # smoothing for bbox height (0..1)
ALLOW_PAN_TILT = True       # set False if you only want zoom
CENTER_DEADBAND = 0.15      # allow ±15% off center before panning
PAN_SPEED = 2               # gentle pan/tilt speed
# =====================

BASE = f"http://{CAM_IP}/cgi-bin/ptz.cgi"
AUTH = HTTPDigestAuth(USER, PASSWORD)
TIMEOUT = 1.5

last_cmd_ms = 0
ema_h = None

def now_ms(): return int(time.time()*1000)

def dahua(action, code, speed, arg1=0, arg3=0):
    try:
        r = requests.get(BASE, params=dict(
            action=action, channel=CHANNEL, code=code, arg1=arg1, arg2=speed, arg3=arg3
        ), auth=AUTH, timeout=TIMEOUT)
        return r.ok
    except Exception:
        return False

def zoom_in_burst(ms=150):
    if dahua("start", "ZoomTele", ZOOM_SPEED):
        time.sleep(ms/1000.0)
    dahua("stop", "ZoomTele", 0)

def zoom_out_burst(ms=150):
    if dahua("start", "ZoomWide", ZOOM_SPEED):
        time.sleep(ms/1000.0)
    dahua("stop", "ZoomWide", 0)

def pan_once(dx_norm, dy_norm):
    """
    dx_norm, dy_norm: target center minus frame center, normalized (-1..1).
    Positive dx -> target to the RIGHT (camera should pan RIGHT).
    Positive dy -> target BELOW (camera should tilt DOWN).
    """
    if abs(dx_norm) > CENTER_DEADBAND:
        dahua("start", "Right" if dx_norm>0 else "Left", PAN_SPEED)
        time.sleep(0.10)
        dahua("stop",  "Right" if dx_norm>0 else "Left", 0)
    if abs(dy_norm) > CENTER_DEADBAND:
        dahua("start", "Down" if dy_norm>0 else "Up", PAN_SPEED)
        time.sleep(0.10)
        dahua("stop",  "Down" if dy_norm>0 else "Up", 0)

def on_message(c, u, msg):
    global last_cmd_ms, ema_h
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        return

    # expect DeepStream standard schema: payload["objects"], payload["videoResolution"]
    W = payload.get("videoResolution", {}).get("width")
    H = payload.get("videoResolution", {}).get("height")
    objs = payload.get("objects", [])
    if not W or not H or not objs: return

    # pick largest TARGET_CLASS by bbox height
    cand = None; cand_h = 0
    for o in objs:
        if o.get("objType") != TARGET_CLASS:  # change key if your schema uses "class" or "label"
            continue
        bbox = o.get("bbox", {})
        h = bbox.get("height", 0)
        if h > cand_h:
            cand = o; cand_h = h

    if not cand: return

    # smoothing on bbox height fraction
    frac_h = cand_h / float(H)
    ema_h = frac_h if ema_h is None else (EMA_ALPHA*frac_h + (1-EMA_ALPHA)*ema_h)

    # optional centering
    if ALLOW_PAN_TILT:
        bbox = cand.get("bbox", {})
        cx = (bbox.get("left",0) + bbox.get("width",0)/2.0) / float(W)
        cy = (bbox.get("top",0)  + bbox.get("height",0)/2.0) / float(H)
        dx = cx - 0.5
        dy = cy - 0.5
        pan_once(dx, dy)

    # hysteresis: only act outside [LOW, HIGH]
    t = now_ms()
    if t - last_cmd_ms < COOLDOWN_MS:
        return
    if ema_h < LOW:
        zoom_in_burst(150)    # short tap
        last_cmd_ms = t
    elif ema_h > HIGH:
        zoom_out_burst(150)
        last_cmd_ms = t
    # else inside deadband: do nothing (stable)

def main():
    print(f"Auto-zoom: target={TARGET_CLASS} thresholds=({LOW},{HIGH}) speeds: zoom={ZOOM_SPEED}, pan={PAN_SPEED}")
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(BROKER, 1883, 60)
    client.subscribe(TOPIC)
    client.loop_forever()

if __name__ == "__main__":
    main()

