# zoom_keys_debug.py
import sys, termios, tty, time, requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# ==== EDIT THESE ====
CAM_HOST   = "192.168.188.108"# your camera IP
HTTP_PORT  = 80               # often 80 or 88 (change if your web UI uses :88)
HTTPS_PORT = 443              # 443 if HTTPS is enabled
USER       = "admin"
PASSWORD   = "krishna_01"
CHANNEL    = 1
SPEED      = 2                # 0..8 (higher = faster)
VERIFY_TLS = False            # set True if using a valid cert
# =====================

def getch():
    fd = sys.stdin.fileno(); old = termios.tcgetattr(fd)
    try: termios.tcsetattr(fd, termios.TCSADRAIN, old); tty.setraw(fd); ch = sys.stdin.read(1)
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def try_request(params):
    combos = [
        ("http",  HTTP_PORT,  HTTPBasicAuth),
        ("http",  HTTP_PORT,  HTTPDigestAuth),
        ("https", HTTPS_PORT, HTTPBasicAuth),
        ("https", HTTPS_PORT, HTTPDigestAuth),
    ]
    for scheme, port, Auth in combos:
        base = f"{scheme}://{CAM_HOST}:{port}/cgi-bin/ptz.cgi"
        try:
            r = requests.get(base, params=params, auth=Auth(USER, PASSWORD),
                             timeout=2.0, verify=VERIFY_TLS)
            print(f"[{scheme.upper()}:{port} {Auth.__name__}] {r.status_code}")
            if r.status_code == 200:
                return True
        except Exception as e:
            print(f"[{scheme.upper()}:{port} {Auth.__name__}] {e}")
    return False

def ptz(action, code, speed=SPEED):
    params = dict(action=action, channel=CHANNEL, code=code, arg1=0, arg2=speed, arg3=0)
    if not try_request(params):
        print("No success—check IP/port/auth or try other port (e.g., 88).")

def burst(code, ms=180):
    ptz("start", code)
    time.sleep(ms/1000.0)
    for c in ("ZoomTele","ZoomWide"):
        ptz("stop", c, speed=0)

print("Controls: [+]=Zoom In, [-]=Zoom Out, [s]=Stop, [q]=Quit")
while True:
    k = getch()
    if k == '+': burst("ZoomTele", 180)
    elif k == '-': burst("ZoomWide", 180)
    elif k in ('s','S'):
        for c in ("ZoomTele","ZoomWide"): ptz("stop", c, speed=0)
    elif k in ('q','Q'):
        for c in ("ZoomTele","ZoomWide"): ptz("stop", c, speed=0)
        break
    time.sleep(0.05)


