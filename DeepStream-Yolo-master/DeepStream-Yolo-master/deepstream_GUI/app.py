#!/usr/bin/env python3
import os, sys, time, json, signal, threading, subprocess
from collections import deque
from typing import Optional, Tuple
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from urllib.parse import urlparse

# -------------------------------------------------
# Paths
# -------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT, "static")
INDEX_HTML = os.path.join(ROOT, "index2.html")
os.makedirs(STATIC_DIR, exist_ok=True)

# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# -------------------------------------------------
# Buffers
# -------------------------------------------------
LOG_MAX = 2000
EVT_MAX = 200
_logs = deque(maxlen=LOG_MAX)
_events = deque(maxlen=EVT_MAX)
SQUELCH_UNTIL = 0.0

def log(line: str):
    ts = time.strftime("%H:%M:%S")
    msg = f"[{ts}] {line}"
    _logs.append(msg)
    print(msg, flush=True)

def add_event(it: dict):
    if time.time() >= SQUELCH_UNTIL:
        _events.append(it)

# -------------------------------------------------
# DeepStream command
# -------------------------------------------------
# DeepStream command (use your absolute config path)
DS_CONFIG = "/home/lain/DeepStream-Yolo-master/Deepstream_example_usb.txt"
DS_CMD = f"deepstream-app -c {DS_CONFIG}"


# Process state
_proc: Optional[subprocess.Popen] = None
_running = False

def _reader(stream, prefix):
    for raw in iter(stream.readline, b""):
        try:
            txt = raw.decode("utf-8", errors="ignore").rstrip()
        except Exception:
            txt = str(raw)
        _logs.append(f"[{prefix}] {txt}")
    try:
        stream.close()
    except Exception:
        pass

def _start_process() -> bool:
    """Start DeepStream with a controllable process group and stdin."""
    global _proc, _running
    if _running:
        log("[START] already running")
        return True
    try:
        log(f"[START] launching: {DS_CMD}")
        # Start new process group so we can signal the entire tree
        _proc = subprocess.Popen(
            DS_CMD,
            shell=True,                          # keep shell for your path/env usage
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,               # allow sending 'q\n'
            bufsize=1,
            preexec_fn=os.setsid                 # new process group (Linux/Unix)
        )
        _running = True
        threading.Thread(target=_reader, args=(_proc.stdout, "DSO"), daemon=True).start()
        threading.Thread(target=_reader, args=(_proc.stderr, "DSE"), daemon=True).start()
        return True
    except Exception as e:
        log(f"[START] error: {e}")
        _proc = None
        _running = False
        return False

def _stop_process() -> bool:
    """Stop DeepStream and close its window (q -> SIGINT -> TERM -> KILL)."""
    global _proc, _running
    if not _running or _proc is None:
        log("[STOP] not running")
        return True

    # try to get process group id
    pgid = None
    try:
        pgid = os.getpgid(_proc.pid)
    except Exception:
        pass

    try:
        # 1) Ask nicely via stdin 'q\n' (DeepStream quits)
        try:
            if _proc.stdin:
                _proc.stdin.write(b"q\n")
                _proc.stdin.flush()
                log("[STOP] sent 'q' to deepstream stdin")
        except Exception as e:
            log(f"[STOP] could not write 'q': {e}")

        # give it a moment
        try:
            _proc.wait(timeout=3.5)
        except Exception:
            pass

        # 2) SIGINT process group if still alive
        if _proc.poll() is None:
            if pgid is not None:
                log("[STOP] sending SIGINT to process group…")
                os.killpg(pgid, signal.SIGINT)
            else:
                log("[STOP] sending SIGINT to process…")
                _proc.send_signal(signal.SIGINT)
            try:
                _proc.wait(timeout=4.0)
            except Exception:
                pass

        # 3) SIGTERM if still alive
        if _proc.poll() is None:
            if pgid is not None:
                log("[STOP] sending SIGTERM to process group…")
                os.killpg(pgid, signal.SIGTERM)
            else:
                log("[STOP] sending SIGTERM to process…")
                _proc.terminate()
            try:
                _proc.wait(timeout=3.0)
            except Exception:
                pass

        # 4) SIGKILL last resort
        if _proc.poll() is None:
            if pgid is not None:
                log("[STOP] sending SIGKILL to process group…")
                os.killpg(pgid, signal.SIGKILL)
            else:
                log("[STOP] sending SIGKILL to process…")
                _proc.kill()
            try:
                _proc.wait(timeout=2.0)
            except Exception:
                pass

        # 5) Belt-and-suspenders cleanup (optional)
        try:
            subprocess.run(["pkill", "-f", "deepstream-app"], timeout=1)
        except Exception:
            pass

        log("[STOP] stopped")
        _proc = None
        _running = False
        return True

    except Exception as e:
        log(f"[STOP] error: {e}")
        return False

# -------------------------------------------------
# MQTT listener (optional; parses detections)
# -------------------------------------------------
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "ds/events")

def _trigger_devices():
    # hook for GPIO/relays if needed later
    pass

def _mqtt_loop():
    try:
        import paho.mqtt.client as mqtt
    except Exception as e:
        log(f"[MQTT] paho not available: {e}")
        return

    has_v2 = hasattr(mqtt, "CallbackAPIVersion")
    if has_v2:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        def on_connect(cl, ud, flags, rc, properties=None):
            if rc == 0:
                log(f"[MQTT] Connected to {MQTT_HOST}:{MQTT_PORT}")
                cl.subscribe(MQTT_TOPIC, qos=0)
                log(f"[MQTT] Subscribed '{MQTT_TOPIC}'")
            else:
                log(f"[MQTT] connect failed rc={rc}")
        client.on_connect = on_connect
    else:
        client = mqtt.Client()
        def on_connect(cl, ud, flags, rc):
            if rc == 0:
                log(f"[MQTT] Connected to {MQTT_HOST}:{MQTT_PORT}")
                cl.subscribe(MQTT_TOPIC, qos=0)
                log(f"[MQTT] Subscribed '{MQTT_TOPIC}'")
            else:
                log(f"[MQTT] connect failed rc={rc}")
        client.on_connect = on_connect

    def on_message(cl, ud, msg):
        try:
            txt = msg.payload.decode("utf-8", errors="ignore")
            obj = json.loads(txt)
        except Exception:
            log("[MQTT] <unparsed>")
            return

        det_label, conf, bbox = None, None, None
        o = obj.get("object") or {}
        for k in ("person", "vehicle", "car"):
            if isinstance(o.get(k), dict) and "confidence" in o[k]:
                det_label = k
                conf = float(o[k]["confidence"])
                break
        bb = o.get("bbox") or {}
        if bb:
            bbox = (bb.get("topleftx"), bb.get("toplefty"),
                    bb.get("bottomrightx"), bb.get("bottomrighty"))

        if det_label is not None and conf is not None:
            add_event({
                "ts": obj.get("@timestamp"),
                "label": det_label,
                "confidence": conf,
                "bbox": bbox,
                "source": "mqtt",
            })
            log(f"[MQTT] {det_label} conf={conf} bbox={bbox}")
            _trigger_devices()
        else:
            log("[MQTT] json (no object)")

    client.on_message = on_message

    try:
        log(f"[MQTT] Connecting to {MQTT_HOST}:{MQTT_PORT}…")
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
        client.loop_forever()
    except Exception as e:
        log(f"[MQTT] error: {e}")

# start mqtt thread
threading.Thread(target=_mqtt_loop, name="mqtt", daemon=True).start()

# -------------------------------------------------
# PTZ (Dahua) endpoints
# -------------------------------------------------
class PTZConfig(BaseModel):
    host: str
    user: str
    password: str
    channel: int = 1
    protocol: str = "http"
    port: int = 80
    auth: str = "digest"     # digest|basic
    timeout: float = 4.0

PTZ_HOST = ""
PTZ_USER = ""
PTZ_PASS = ""
PTZ_CHANNEL = 1
PTZ_PROTOCOL = "http"
PTZ_PORT = 80
PTZ_AUTH = "digest"
PTZ_TIMEOUT = 4.0

def _normalize_ptz_host(host_in: str, protocol: str, port: int) -> Tuple[str,str,int]:
    host_in = (host_in or "").strip()
    if host_in.startswith("http://") or host_in.startswith("https://"):
        u = urlparse(host_in)
        return (u.hostname or ""), (u.scheme or protocol or "http"), (u.port or port or 80)
    return host_in.strip("/ "), (protocol or "http").lower(), (port or 80)

def _ptz_url(code: str, action: str, speed: int) -> str:
    return (f"{PTZ_PROTOCOL}://{PTZ_HOST}:{PTZ_PORT}/cgi-bin/ptz.cgi"
            f"?action={action}&channel={PTZ_CHANNEL}&code={code}&arg1=0&arg2={speed}&arg3=0")

def _ptz_request(url: str):
    import requests
    auth = None
    if PTZ_AUTH == "digest":
        from requests.auth import HTTPDigestAuth
        auth = HTTPDigestAuth(PTZ_USER, PTZ_PASS)
    elif PTZ_AUTH == "basic":
        from requests.auth import HTTPBasicAuth
        auth = HTTPBasicAuth(PTZ_USER, PTZ_PASS)
    return requests.get(url, auth=auth, timeout=PTZ_TIMEOUT)

@app.post("/ptz/config")
def ptz_set_config(cfg: PTZConfig):
    global PTZ_HOST, PTZ_USER, PTZ_PASS, PTZ_CHANNEL, PTZ_PROTOCOL, PTZ_PORT, PTZ_AUTH, PTZ_TIMEOUT
    host, proto, port = _normalize_ptz_host(cfg.host, cfg.protocol, cfg.port)
    if not host:
        return JSONResponse({"ok": False, "error": "empty host"}, status_code=400)
    PTZ_HOST, PTZ_PROTOCOL, PTZ_PORT = host, proto, port
    PTZ_USER, PTZ_PASS = cfg.user or "", cfg.password or ""
    PTZ_CHANNEL, PTZ_AUTH, PTZ_TIMEOUT = int(cfg.channel or 1), (cfg.auth or "digest").lower(), float(cfg.timeout or 4.0)
    log(f"[PTZ] config set: {PTZ_PROTOCOL}://{PTZ_HOST}:{PTZ_PORT} auth={PTZ_AUTH} ch={PTZ_CHANNEL}")
    return {"ok": True}

@app.post("/ptz/start")
def ptz_start(body: dict):
    if not PTZ_HOST:
        log("[PTZ] error: PTZ host not configured")
        return {"ok": False, "error": "PTZ host not configured"}
    code = str(body.get("code") or "")
    speed = int(body.get("speed") or 3)
    try:
        url = _ptz_url(code, "start", speed)
        r = _ptz_request(url)
        log(f"[PTZ] start {code} speed {speed} -> {r.status_code}")
        return {"ok": True}
    except Exception as e:
        log(f"[PTZ] error: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/ptz/stop")
def ptz_stop(body: dict):
    if not PTZ_HOST:
        log("[PTZ] error: PTZ host not configured")
        return {"ok": False, "error": "PTZ host not configured"}
    code = str(body.get("code") or "Stop")
    try:
        url = _ptz_url(code, "stop", 0)
        r = _ptz_request(url)
        log(f"[PTZ] stop {code} -> {r.status_code}")
        return {"ok": True}
    except Exception as e:
        log(f"[PTZ] error: {e}")
        return {"ok": False, "error": str(e)}

# -------------------------------------------------
# DeepStream lifecycle endpoints
# -------------------------------------------------
@app.post("/start")
def start_app():
    ok = _start_process()
    return {"ok": ok, "running": ok}

@app.post("/stop")
def stop_app():
    global SQUELCH_UNTIL
    SQUELCH_UNTIL = time.time() + 1.5  # silence MQTT/events briefly
    ok = _stop_process()
    return {"ok": ok, "running": False}

@app.get("/status")
def status():
    return {"running": _running}

@app.post("/clear")
def clear():
    global SQUELCH_UNTIL
    _logs.clear()
    _events.clear()
    SQUELCH_UNTIL = time.time() + 1.0
    return {"ok": True}

# -------------------------------------------------
# Simulate detection
# -------------------------------------------------
@app.post("/simulate")
def simulate():
    add_event({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "label": "person",
        "confidence": 0.83,
        "bbox": (100, 120, 200, 240),
        "source": "sim"
    })
    log("[DEV] (sim) strobe flash + beep")
    _trigger_devices()
    return {"ok": True}

# -------------------------------------------------
# Feeds + GUI
# -------------------------------------------------
@app.get("/logs")
def get_logs():
    return {"lines": list(_logs)}

@app.get("/events")
def get_events(limit: int = 30):
    return {"items": list(_events)[-limit:]}

@app.get("/")
def root():
    return FileResponse(INDEX_HTML)

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

