# zoom_keys.py
import sys, termios, tty, requests, time

CAM_IP    = "192.168.188.108"
USER      = "admin"
PASSWORD  = "krishna_01"
CHANNEL   = 1
SPEED     = 2   # 0..8

BASE = f"http://{CAM_IP}/cgi-bin/ptz.cgi"
AUTH = (USER, PASSWORD)

def dahua(cmd, action="start", code=None):
    params = dict(action=action, channel=CHANNEL, code=code, arg1=0, arg2=SPEED, arg3=0)
    try: requests.get(BASE, params=params, auth=AUTH, timeout=1.0)
    except: pass

def getch():
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd)
    try: tty.setraw(fd); ch=sys.stdin.read(1)
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

print("Controls: [+]=Zoom In, [-]=Zoom Out, [s]=Stop, [q]=Quit")
while True:
    k = getch()
    if k == '+':
        dahua("in", action="start", code="ZoomTele")
    elif k == '-':
        dahua("out", action="start", code="ZoomWide")
    elif k in ('s', 'S'):
        # stop both directions just in case
        for c in ("ZoomTele","ZoomWide"):
            dahua("stop", action="stop", code=c)
    elif k in ('q','Q'):
        for c in ("ZoomTele","ZoomWide"):
            dahua("stop", action="stop", code=c)
        break
    time.sleep(0.05)

