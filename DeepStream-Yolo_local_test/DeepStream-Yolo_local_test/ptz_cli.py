# ptz_cli.py  — Dahua PTZ CLI (Digest)
# Controls: pan/tilt move (step or continuous), zoom (step/continuous), stop, presets.
# Usage examples are at the bottom of this file.

import sys, time, requests
from requests.auth import HTTPDigestAuth

# === EDIT THESE ===
CAM_HOST  = "192.168.188.108"
USER      = "admin"
PASSWORD  = "krishna_01"
CHANNEL   = 1            # usually 1
DEFAULT_SPEED = 2        # 0..8 typical
DEFAULT_BURST_MS = 300   # for step moves
# ===================

BASE_URL = f"http://{CAM_HOST}/cgi-bin/ptz.cgi"
AUTH     = HTTPDigestAuth(USER, PASSWORD)
TIMEOUT  = 2.0

# --- core helpers ---
def ptz(action, code, speed=DEFAULT_SPEED, arg1=0, arg3=0):
    # Dahua PTZ: action=start|stop, code=Up/Down/Left/Right/LeftUp/RightUp/LeftDown/RightDown/ZoomTele/ZoomWide/FocusNear/FocusFar/GotoPreset/SetPreset/RemovePreset, etc.
    # arg1, arg3 typically 0; speed in arg2.
    params = dict(action=action, channel=CHANNEL, code=code, arg1=arg1, arg2=speed, arg3=arg3)
    r = requests.get(BASE_URL, params=params, auth=AUTH, timeout=TIMEOUT)
    print(f"{action} {code} (speed={speed}) -> {r.status_code}")
    return r.ok

def burst(code, ms=DEFAULT_BURST_MS, speed=DEFAULT_SPEED):
    if ptz("start", code, speed=speed):
        time.sleep(ms/1000.0)
    # be safe: stop both axes/zoom directions that share the code family
    family = {
        "ZoomTele":  ["ZoomTele","ZoomWide"],
        "ZoomWide":  ["ZoomTele","ZoomWide"],
        "Up":        ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "Down":      ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "Left":      ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "Right":     ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "LeftUp":    ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "RightUp":   ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "LeftDown":  ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "RightDown": ["Up","Down","LeftUp","RightUp","LeftDown","RightDown","Left","Right"],
        "FocusNear": ["FocusNear","FocusFar"],
        "FocusFar":  ["FocusNear","FocusFar"],
    }.get(code, [code])
    for c in family:
        ptz("stop", c, speed=0)

def stop_all():
    # stop movement and zoom
    for c in ("Up","Down","Left","Right","LeftUp","RightUp","LeftDown","RightDown","ZoomTele","ZoomWide","FocusNear","FocusFar"):
        ptz("stop", c, speed=0)

# --- command handlers ---
def cmd_zoom_step(ms=None, speed=None, tele=True):
    burst("ZoomTele" if tele else "ZoomWide",
          ms=DEFAULT_BURST_MS if ms is None else int(ms),
          speed=DEFAULT_SPEED if speed is None else int(speed))

def cmd_zoom_start(speed=None, tele=True):
    ptz("start", "ZoomTele" if tele else "ZoomWide",
        speed=DEFAULT_SPEED if speed is None else int(speed))

def cmd_move_step(direction, ms=None, speed=None):
    valid = {"up":"Up","down":"Down","left":"Left","right":"Right",
             "upleft":"LeftUp","upright":"RightUp",
             "downleft":"LeftDown","downright":"RightDown"}
    code = valid.get(direction.lower())
    if not code:
        print("invalid direction. use: up, down, left, right, upleft, upright, downleft, downright")
        sys.exit(2)
    burst(code, ms=DEFAULT_BURST_MS if ms is None else int(ms),
          speed=DEFAULT_SPEED if speed is None else int(speed))

def cmd_move_start(direction, speed=None):
    valid = {"up":"Up","down":"Down","left":"Left","right":"Right",
             "upleft":"LeftUp","upright":"RightUp",
             "downleft":"LeftDown","downright":"RightDown"}
    code = valid.get(direction.lower())
    if not code:
        print("invalid direction. use: up, down, left, right, upleft, upright, downleft, downright")
        sys.exit(2)
    ptz("start", code, speed=DEFAULT_SPEED if speed is None else int(speed))

def cmd_focus_step(ms=None, speed=None, near=True):
    burst("FocusNear" if near else "FocusFar",
          ms=DEFAULT_BURST_MS if ms is None else int(ms),
          speed=DEFAULT_SPEED if speed is None else int(speed))

def cmd_focus_start(speed=None, near=True):
    ptz("start", "FocusNear" if near else "FocusFar",
        speed=DEFAULT_SPEED if speed is None else int(speed))

def cmd_preset_goto(idx, speed=None):
    # Dahua uses GotoPreset with arg2 = preset index (we pass via speed arg2 by convention in CGI; some firmwares use arg2 for speed; if not, use arg2 as preset via arg2 and speed fixed)
    # Safer method: use code=GotoPreset and pass preset in arg2; keep speed arg2 as same numeric.
    # We'll send preset index in arg2 and ignore speed.
    r = requests.get(BASE_URL, params=dict(
        action="start", channel=CHANNEL, code="GotoPreset",
        arg1=0, arg2=int(idx), arg3=0), auth=AUTH, timeout=TIMEOUT)
    print(f"goto preset {idx} -> {r.status_code}")
    return r.ok

def cmd_preset_set(idx):
    r = requests.get(BASE_URL, params=dict(
        action="start", channel=CHANNEL, code="SetPreset",
        arg1=0, arg2=int(idx), arg3=0), auth=AUTH, timeout=TIMEOUT)
    print(f"set preset {idx} -> {r.status_code}")
    return r.ok

def cmd_preset_del(idx):
    r = requests.get(BASE_URL, params=dict(
        action="start", channel=CHANNEL, code="RemovePreset",
        arg1=0, arg2=int(idx), arg3=0), auth=AUTH, timeout=TIMEOUT)
    print(f"remove preset {idx} -> {r.status_code}")
    return r.ok

# --- arg parsing ---
def usage():
    print("""usage:
  # ZOOM (step / continuous)
  ptz_cli.py zoom-in [ms] [speed]          # e.g. 500 3
  ptz_cli.py zoom-out [ms] [speed]
  ptz_cli.py zoom-in-start [speed]
  ptz_cli.py zoom-out-start [speed]

  # MOVE (pan/tilt) directions: up, down, left, right, upleft, upright, downleft, downright
  ptz_cli.py move <direction> [ms] [speed]         # step move
  ptz_cli.py move-start <direction> [speed]        # continuous until stop

  # FOCUS (optional)
  ptz_cli.py focus-near [ms] [speed]
  ptz_cli.py focus-far  [ms] [speed]
  ptz_cli.py focus-near-start [speed]
  ptz_cli.py focus-far-start  [speed]

  # PRESETS
  ptz_cli.py preset-goto <index>
  ptz_cli.py preset-set  <index>
  ptz_cli.py preset-del  <index>

  # STOP everything (movement, zoom, focus)
  ptz_cli.py stop
""")

def main():
    if len(sys.argv) < 2:
        usage(); sys.exit(1)
    cmd = sys.argv[1].lower()

    if cmd == "zoom-in":
        cmd_zoom_step(ms=sys.argv[2] if len(sys.argv)>2 else None,
                      speed=sys.argv[3] if len(sys.argv)>3 else None, tele=True)
    elif cmd == "zoom-out":
        cmd_zoom_step(ms=sys.argv[2] if len(sys.argv)>2 else None,
                      speed=sys.argv[3] if len(sys.argv)>3 else None, tele=False)
    elif cmd == "zoom-in-start":
        cmd_zoom_start(speed=sys.argv[2] if len(sys.argv)>2 else None, tele=True)
    elif cmd == "zoom-out-start":
        cmd_zoom_start(speed=sys.argv[2] if len(sys.argv)>2 else None, tele=False)

    elif cmd == "move":
        if len(sys.argv) < 3: usage(); sys.exit(1)
        direction = sys.argv[2]
        ms    = sys.argv[3] if len(sys.argv)>3 else None
        speed = sys.argv[4] if len(sys.argv)>4 else None
        cmd_move_step(direction, ms=ms, speed=speed)
    elif cmd == "move-start":
        if len(sys.argv) < 3: usage(); sys.exit(1)
        direction = sys.argv[2]
        speed = sys.argv[3] if len(sys.argv)>3 else None
        cmd_move_start(direction, speed=speed)

    elif cmd == "focus-near":
        cmd_focus_step(ms=sys.argv[2] if len(sys.argv)>2 else None,
                       speed=sys.argv[3] if len(sys.argv)>3 else None, near=True)
    elif cmd == "focus-far":
        cmd_focus_step(ms=sys.argv[2] if len(sys.argv)>2 else None,
                       speed=sys.argv[3] if len(sys.argv)>3 else None, near=False)
    elif cmd == "focus-near-start":
        cmd_focus_start(speed=sys.argv[2] if len(sys.argv)>2 else None, near=True)
    elif cmd == "focus-far-start":
        cmd_focus_start(speed=sys.argv[2] if len(sys.argv)>2 else None, near=False)

    elif cmd == "preset-goto":
        if len(sys.argv) < 3: usage(); sys.exit(1)
        cmd_preset_goto(sys.argv[2])
    elif cmd == "preset-set":
        if len(sys.argv) < 3: usage(); sys.exit(1)
        cmd_preset_set(sys.argv[2])
    elif cmd == "preset-del":
        if len(sys.argv) < 3: usage(); sys.exit(1)
        cmd_preset_del(sys.argv[2])

    elif cmd == "stop":
        stop_all()
    else:
        usage(); sys.exit(2)

if __name__ == "__main__":
    main()

