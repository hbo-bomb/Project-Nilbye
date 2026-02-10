# ptz_keys.py — Manual keyboard control using shared ptz_control
# Arrows to pan/tilt (hold), +/- to zoom (hold). 's' stop all, 'q' quit.
import curses, time
from ptz_control import ptz, stop_all

POLL_SLEEP = 0.02

KEYMAP_MOVE = {
    curses.KEY_UP:    "Up",
    curses.KEY_DOWN:  "Down",
    curses.KEY_LEFT:  "Left",
    curses.KEY_RIGHT: "Right",
}

KEYMAP_ZOOM = {
    ord('+'):   "ZoomTele",
    ord('='):   "ZoomTele",
    ord('-'):   "ZoomWide",
    ord('_'):   "ZoomWide",
    ord('*'):   "ZoomWide",
}

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.clear()
    stdscr.addstr(0,0,"Dahua PTZ manual control — arrows pan/tilt, +/- zoom, 's' stop, 'q' quit")
    stdscr.refresh()

    held_moves = set()
    held_zoom  = set()

    try:
        while True:
            ch = stdscr.getch()
            if ch != -1:
                if ch in (ord('q'), ord('Q')):
                    break
                elif ch in (ord('s'), ord('S')):
                    stop_all()
                    held_moves.clear()
                    held_zoom.clear()
                elif ch in KEYMAP_MOVE:
                    code = KEYMAP_MOVE[ch]
                    if code not in held_moves:
                        held_moves.add(code)
                        ptz("start", code, 3)
                elif ch in KEYMAP_ZOOM:
                    code = KEYMAP_ZOOM[ch]
                    if code not in held_zoom:
                        held_zoom.add(code)
                        ptz("start", code, 3)

            # On key release, curses won't tell us directly.
            # We simply stop everything briefly if nothing is pressed.
            # (Optional: implement a more advanced key-up detection if needed)
            time.sleep(POLL_SLEEP)

            # Lightweight approach: if no keys currently pressed, stop any ongoing motions
            # (You can improve this by tracking last-pressed timestamps per key)
            if stdscr.getch() == -1:
                if held_moves or held_zoom:
                    for code in list(held_moves):
                        ptz("stop", code, 0)
                    for code in list(held_zoom):
                        ptz("stop", code, 0)
                    held_moves.clear()
                    held_zoom.clear()

    finally:
        stop_all()

if __name__ == "__main__":
    curses.wrapper(main)
