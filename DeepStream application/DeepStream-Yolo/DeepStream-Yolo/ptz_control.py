
# ptz_control.py — callable Dahua PTZ control (CGI)
# Directions: "Up","Down","Left","Right","LeftUp","RightUp","LeftDown","RightDown","ZoomTele","ZoomWide"
# Edit CAM_HOST / USER / PASSWORD if needed.

import requests
from requests.auth import HTTPDigestAuth

CAM_HOST  = "192.168.188.108"   # <<< EDIT if needed
USER      = "admin"             # <<< EDIT
PASSWORD  = "krishna_01"        # <<< EDIT
CHANNEL   = 1
SPEED_PTZ = 3   # 0..8
SPEED_ZM  = 3   # 0..8
TIMEOUT   = 2.0

BASE_URL = f"http://{CAM_HOST}/cgi-bin/ptz.cgi"
AUTH     = HTTPDigestAuth(USER, PASSWORD)

def _ptz(action, code, speed):
    try:
        r = requests.get(
            BASE_URL,
            params=dict(action=action, channel=CHANNEL, code=code, arg1=0, arg2=speed, arg3=0),
            auth=AUTH, timeout=TIMEOUT
        )
        return r.ok
    except Exception:
        return False

def start_move(direction):
    speed = SPEED_PTZ if not direction.startswith("Zoom") else SPEED_ZM
    return _ptz("start", direction, speed)

def stop_move(direction):
    return _ptz("stop", direction, 0)

def stop_all():
    for c in ("Up","Down","Left","Right","LeftUp","RightUp","LeftDown","RightDown","ZoomTele","ZoomWide"):
        _ptz("stop", c, 0)
