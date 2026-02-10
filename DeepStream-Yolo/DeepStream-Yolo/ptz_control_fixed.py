# ptz_control.py — Shared Dahua PTZ helpers (HTTP Digest via ptz.cgi)
import time
import threading
import requests
from requests.auth import HTTPDigestAuth

# === Centralized config (edit once here) ===
CAM_HOST  = "192.168.188.108"
USER      = "admin"
PASSWORD  = "krishna_01"
CHANNEL   = 1
SPEED_PTZ = 3   # 0..8
SPEED_ZM  = 3   # 0..8
TIMEOUT   = 2.0

BASE_URL  = f"http://{CAM_HOST}/cgi-bin/ptz.cgi"
AUTH      = HTTPDigestAuth(USER, PASSWORD)

def ptz(action: str, code: str, speed: int) -> bool:
    """Low-level Dahua PTZ call.
    action: 'start' | 'stop'
    code:   'Up','Down','Left','Right','LeftUp','RightUp','LeftDown','RightDown','ZoomTele','ZoomWide'
    speed:  0..8 (pan/tilt uses arg2; Dahua ignores others for zoom)
    """
    try:
        r = requests.get(
            BASE_URL,
            params=dict(action=action, channel=CHANNEL, code=code, arg1=0, arg2=speed, arg3=0),
            auth=AUTH, timeout=TIMEOUT
        )
        return r.ok
    except Exception:
        return False

def stop_all():
    for c in ("Up","Down","Left","Right","LeftUp","RightUp","LeftDown","RightDown","ZoomTele","ZoomWide"):
        ptz("stop", c, 0)

def pulse_move(code: str, speed: int = None, ms: int = 120):
    """Short pan/tilt pulse: start -> sleep -> stop (runs in a thread)."""
    if speed is None: speed = SPEED_PTZ
    def worker():
        ptz("start", code, speed)
        time.sleep(ms/1000.0)
        ptz("stop", code, 0)
    threading.Thread(target=worker, daemon=True).start()

def step_zoom(code: str, speed: int = None, ms: int = 160):
    """Small zoom 'tick' in/out: start briefly then stop (threaded)."""
    if speed is None: speed = SPEED_ZM
    def worker():
        ptz("start", code, speed)
        time.sleep(ms/1000.0)
        ptz("stop", code, 0)
    threading.Thread(target=worker, daemon=True).start()
