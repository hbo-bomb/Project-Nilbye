# ptz_keys.py â€” Dahua PTZ keyboard control (hold-to-move & hold-to-zoom)
# Arrows: hold to pan/tilt; release = stop
# + / = : hold to zoom in;   release = stop
# - / _ / * : hold to zoom out; release = stop
# s : stop all    | q : quit

import curses, time, requests
from requests.auth import HTTPDigestAuth

# ==== EDIT THESE ====
CAM_HOST  = "192.168.188.108"
USER      = "admin"
PASSWORD  = "krishna_01"
CHANNEL   = 1
SPEED_PTZ = 3   # pan/tilt speed (0..8)
SPEED_ZM  = 3   # zoom speed (0..8)
IDLE_TICKS_TO_STOP = 2  # how fast to stop after release; 1â‰ˆ~30ms, 2â‰ˆ~60ms, 3â‰ˆ~90ms
POLL_SLEEP = 0.03       # seconds between polls
# ====================

BASE_URL = f"http://{CAM_HOST}/cgi-bin/ptz.cgi"
AUTH     = HTTPDigestAuth(USER, PASSWORD)
TIMEOUT  = 2.0

def ptz(action, code, speed):
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

def main(stdscr):
    curses.cbreak()
    stdscr.nodelay(True)      # non-blocking getch
    stdscr.keypad(True)       # decode arrow keys
    curses.noecho()
    stdscr.clear()
    stdscr.addstr(0,0,"Hold keys: â† â†’ â†‘ â†“ pan/tilt | + = zoom in | - _ * zoom out | s stop | q quit")
    stdscr.refresh()

    current_move = None   # "Up/Down/Left/Right"
    current_zoom = None   # "ZoomTele"/"ZoomWide"
    idle_ticks   = 0

    try:
        while True:
            ch = stdscr.getch()
            if ch != -1:
                idle_ticks = 0
                if ch in (ord('q'), ord('Q')):
                    break
                elif ch in (ord('s'), ord('S')):
                    stop_all()
                    current_move = None
                    current_zoom = None

                elif ch in (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT):
                    wanted = {curses.KEY_UP:"Up", curses.KEY_DOWN:"Down",
                              curses.KEY_LEFT:"Left", curses.KEY_RIGHT:"Right"}[ch]
                    if current_move != wanted:
                        if current_move is not None:
                            ptz("stop", current_move, 0)
                        ptz("start", wanted, SPEED_PTZ)
                        current_move = wanted

                elif ch in (ord('+'), ord('=')):  # treat '=' like '+'
                    # start/refresh zoom-in while key is held
                    if current_zoom != "ZoomTele":
                        if current_zoom is not None:
                            ptz("stop", current_zoom, 0)
                        ptz("start", "ZoomTele", SPEED_ZM)
                        current_zoom = "ZoomTele"

                elif ch in (ord('-'), ord('_'), ord('*')):  # '-', '_' or '*' = zoom out
                    if current_zoom != "ZoomWide":
                        if current_zoom is not None:
                            ptz("stop", current_zoom, 0)
                        ptz("start", "ZoomWide", SPEED_ZM)
                        current_zoom = "ZoomWide"

                # Any other key: ignore

            else:
                # No key this poll: count toward "released" and stop accordingly
                idle_ticks += 1
                if idle_ticks >= IDLE_TICKS_TO_STOP:
                    if current_move is not None:
                        ptz("stop", current_move, 0)
                        current_move = None
                    if current_zoom is not None:
                        ptz("stop", current_zoom, 0)
                        current_zoom = None
                    idle_ticks = 0

            time.sleep(POLL_SLEEP)
    finally:
        stop_all()

if __name__ == "__main__":
    curses.wrapper(main)

