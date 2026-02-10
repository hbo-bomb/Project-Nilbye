// --- client error logger: puts JS errors into the Logs panel ---
window.addEventListener("error", (e) => {
  const msg = `[JS] ${e.message} @ ${e.filename}:${e.lineno}`;
  const box = document.getElementById("logs");
  if (box) {
    box.textContent += (box.textContent ? "\n" : "") + msg;
    box.scrollTop = box.scrollHeight;
  } else {
    console.error(msg);
  }
});

// ========= helpers =========
async function postJSON(url, body = {}) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(body)
  });
  let data = {};
  try { data = await r.json(); } catch {}
  return data;
}

function appendLog(line) {
  const box = document.getElementById("logs");
  if (!box) return;
  const atBottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 8;
  box.textContent += (box.textContent ? "\n" : "") + line;
  if (atBottom) box.scrollTop = box.scrollHeight;
}

async function refreshStatus() {
  try {
    const r = await fetch("/status");
    const s = await r.json();
    const pill = document.getElementById("runState");
    if (pill) {
      pill.textContent = s.running ? "running" : "stopped";
      pill.className = s.running ? "pill pill--ok" : "pill pill--muted";
    }
  } catch {}
}

function setBusy(el, on) {
  if (!el) return;
  el.disabled = !!on;
  el.classList.toggle("is-busy", !!on);
}

// ========= global UI state =========
let isPaused = false;     // when true, no poll/animations
let pollTimer = null;

function setPaused(p) {
  isPaused = !!p;
}

function flashAlertOnce() {
  if (isPaused) return;
  const light = document.getElementById("strobe");
  const beep = document.getElementById("beep");
  light?.classList.add("flash");
  beep?.classList.add("ping");
  setTimeout(()=>light?.classList.remove("flash"), 260);
  setTimeout(()=>beep?.classList.remove("ping"), 260);
}

// ========= DeepStream buttons =========
document.getElementById("btnStart")?.addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  setBusy(btn, true);
  appendLog("[UI] start…");
  try {
    const r = await postJSON("/start");
    appendLog(r.ok ? "[UI] start ok" : "[UI] start failed");
    setPaused(false);                   // allow events again
  } catch (err) {
    appendLog(`[UI] start error: ${err}`);
  } finally {
    setBusy(btn, false);
    setTimeout(refreshStatus, 300);
  }
});

document.getElementById("btnStop")?.addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  setBusy(btn, true);
  appendLog("[UI] stop…");
  try {
    const r = await postJSON("/stop");  // ensures backend stop
    appendLog(r.ok ? "[UI] stop ok" : "[UI] stop failed");
  } catch (err) {
    appendLog(`[UI] stop error: ${err}`);
  } finally {
    // immediately pause UI so no more animations while DS is stopping
    setPaused(true);
    const pill = document.getElementById("runState");
    if (pill) { pill.textContent = "stopped"; pill.className = "pill pill--muted"; }
    setBusy(btn, false);
    setTimeout(refreshStatus, 300);
  }
});

document.getElementById("btnRefresh")?.addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  setBusy(btn, true);
  appendLog("[UI] refresh…");

  // 1) try to stop pipeline
  try { await postJSON("/stop"); } catch {}

  // 2) try to clear backend buffers (optional)
  try { await fetch("/clear", {method:"POST"}); } catch {}

  // 3) clear UI + pause briefly so nothing fires
  document.getElementById("logs").textContent = "";
  document.getElementById("detections").innerHTML = "";
  setPaused(true);

  // 4) tidy up visuals
  const light = document.getElementById("strobe");
  const beep = document.getElementById("beep");
  light?.classList.remove("flash");
  beep?.classList.remove("ping");

  // 5) show state
  const pill = document.getElementById("runState");
  if (pill) { pill.textContent = "stopped"; pill.className = "pill pill--muted"; }

  setBusy(btn, false);
  appendLog("[UI] cleared");
  // after a short grace period allow polling again
  setTimeout(()=>{ setPaused(false); refreshStatus(); }, 800);
});

// Simulate alert
document.getElementById("btnSim")?.addEventListener("click", async () => {
  try { await postJSON("/simulate"); } catch {}
  flashAlertOnce();
  appendLog("[UI] simulate alert");
});

// ========= Poll logs + events =========
async function poll() {
  if (isPaused) { pollTimer = setTimeout(poll, 800); return; }

  try {
    const lj = await (await fetch("/logs")).json();
    const box = document.getElementById("logs");
    if (box && lj.lines) box.textContent = lj.lines.join("\n");
  } catch {}

  try {
    const ej = await (await fetch("/events?limit=30")).json();
    const list = document.getElementById("detections");
    if (list && ej.items) {
      // flash strobe/beep if there are new detections (UI-only)
      if (ej.items.length) flashAlertOnce();
      list.innerHTML = ej.items.map(it => {
        const c = it.confidence != null ? (Math.round(it.confidence*100)/100) : "";
        const src = it.source || "";
        const tid = it.track || "";
        return `<div class="det">
          <b>${it.label ?? "object"}</b>
          <span>${c}</span>
          <code>${src} ${tid ? ("track:"+tid) : ""}</code>
        </div>`;
      }).join("");
    }
  } catch {}

  pollTimer = setTimeout(poll, 800);
}
refreshStatus();
poll();

// ========= PTZ =========
function currentSpeed(){
  const s = document.getElementById("ptzSpeed");
  return Number(s?.value || 3);
}
function bindPtzButton(el){
  let code = el.dataset.code;
  if (!code) return;
  let down = false;

  const start = async () => {
    if (code === "Stop") return;
    down = true;
    await postJSON("/ptz/start", {code, speed: currentSpeed()});
  };
  const stop = async () => {
    if (!down && code !== "Stop") return;
    down = false;
    await postJSON("/ptz/stop", {code});
  };

  el.addEventListener("mousedown", start);
  el.addEventListener("touchstart", (e)=>{e.preventDefault(); start();});
  el.addEventListener("mouseup", stop);
  el.addEventListener("mouseleave", stop);
  el.addEventListener("touchend", stop);

  if (code === "Stop"){
    el.addEventListener("click", async ()=>{ await postJSON("/ptz/stop", {code}); });
  }
}
document.querySelectorAll(".ptz.btn-ico").forEach(bindPtzButton);

document.querySelectorAll(".ptz-zoom").forEach(el=>{
  el.addEventListener("click", async ()=>{
    const dir = el.dataset.zoom === "in" ? "ZoomTele" : "ZoomWide";
    const speed = currentSpeed();
    await postJSON("/ptz/start", {code: dir, speed});
    setTimeout(()=>postJSON("/ptz/stop", {code: dir}), 350);
  });
});

document.getElementById("btnSavePTZ")?.addEventListener("click", async ()=>{
  const host = document.getElementById("ptzHost").value.trim();
  const port = Number(document.getElementById("ptzPort").value || 80);
  const protocol = document.getElementById("ptzProto").value || "http";
  const auth = document.getElementById("ptzAuth").value || "digest";
  const user = document.getElementById("ptzUser").value || "";
  const password = document.getElementById("ptzPass").value || "";
  const channel = Number(document.getElementById("ptzChan").value || 1);
  const timeout = Number(document.getElementById("ptzTmo").value || 4.0);

  const body = {host, port, protocol, auth, user, password, channel, timeout};
  const r = await postJSON("/ptz/config", body);
  appendLog(r.ok ? `[PTZ] config saved for ${host}` : "[PTZ] config failed");
});

