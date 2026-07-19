"use strict";

// ---- tiny helpers ---------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    // fetch() throws "Failed to fetch" when the local app server can't be
    // reached — turn that into something a non-technical user can act on.
    throw new Error(
      "Couldn't reach the Yoto Maker app. Make sure it's still running " +
      "(look for the 🎵 icon near the clock), then try again."
    );
  }
  let data = null;
  try { data = await res.json(); } catch (_) { /* some routes return files */ }
  if (!res.ok) {
    const msg = (data && data.error) || "Something went wrong. Please try again.";
    const err = new Error(msg);
    err.data = data;
    err.status = res.status;
    throw err;
  }
  return data;
}

function show(el, on = true) { el.classList.toggle("hidden", !on); }
function showError(el, msg) { el.textContent = msg; show(el, true); }
function clearError(el) { el.textContent = ""; show(el, false); }

// Poll a background job until it finishes. Calls onProgress(percent, message).
async function pollJob(jobId, onProgress) {
  while (true) {
    const job = await api(`/api/jobs/${jobId}`);
    if (onProgress) onProgress(job.percent, job.message);
    if (job.status === "done") return job.result;
    if (job.status === "error") throw new Error(job.error || "Something went wrong.");
    await new Promise((r) => setTimeout(r, 500));
  }
}

// ---- state ----------------------------------------------------------------
let STATUS = null;
let UPD = null;

// ---- startup --------------------------------------------------------------
async function init() {
  try {
    STATUS = await api("/api/status");
  } catch (e) {
    $("#toolsWarning").textContent = "The app couldn't start properly. Please restart Yoto Maker.";
    show($("#toolsWarning"), true);
    return;
  }
  $("#ver").textContent = "v" + STATUS.version;
  $("#aboutVer").textContent = STATUS.version;
  renderStatus();
  $("#skipSponsors").checked = STATUS.remove_sponsors !== false;
  if (STATUS.ai_available) show($("#aiTab"), true);
  if (!STATUS.tools.ok) {
    showError($("#toolsWarning"),
      "Some tools this app needs are missing. Please reinstall Yoto Maker or ask for help.");
  }
  await loadIcons();
  await loadEmojis();
  await refreshDraft();
  checkUpdate();  // non-blocking
}

// ---- update banner --------------------------------------------------------
async function checkUpdate() {
  try {
    UPD = await api("/api/update");
  } catch (_) {
    return;  // offline / no update info — stay quiet
  }
  if (!UPD || !UPD.update_available) return;
  $("#updateText").textContent = `🎉 A new version (v${UPD.latest}) is available.`;
  $("#updateWhatsNew").href = UPD.release_url;
  $("#updateNow").textContent = UPD.can_self_update ? "⬇️ Update now" : "⬇️ Get the update";
  show($("#updateBanner"), true);

  // Auto-update: if we can self-update, do it automatically on startup — but
  // ONLY when the card is empty (so we never interrupt work in progress), and
  // never twice for the same version (guards against a bad-release loop).
  if (UPD.can_self_update && localStorage.getItem("autoUpdatedTo") !== UPD.latest) {
    let draft = null;
    try { draft = await api("/api/draft"); } catch (_) { /* ignore */ }
    const idle = draft && (!draft.tracks || draft.tracks.length === 0);
    if (idle) {
      localStorage.setItem("autoUpdatedTo", UPD.latest);
      $("#updateText").textContent = `⬇️ Updating to v${UPD.latest} automatically…`;
      doUpdate();
    }
  }
}

async function doUpdate() {
  // Running from source (or non-Windows): just open the download page.
  if (!UPD || !UPD.can_self_update) {
    window.open(UPD ? UPD.release_url : "https://github.com/mmackelprang/yoto-maker/releases/latest", "_blank");
    return;
  }
  show($("#updateActions"), false);
  show($("#updateProgress"), true);
  $("#updateBar").style.width = "2%";
  $("#updateMsg").textContent = "Starting…";
  try {
    const { job_id } = await api("/api/update/apply", { method: "POST" });
    await pollJob(job_id, (p, m) => {
      $("#updateBar").style.width = Math.max(2, p) + "%";
      $("#updateMsg").textContent = m;
    });
    $("#updateBar").style.width = "100%";
    $("#updateMsg").textContent =
      "Updating… the app will close and reopen in a new window in a moment. You can close this tab.";
  } catch (e) {
    // The app exits mid-restart, so the last poll may fail — that's expected.
    $("#updateMsg").textContent =
      "Updating… the app will reopen in a new window shortly. You can close this tab.";
  }
}

function renderStatus() {
  const pill = $("#yotoPill");
  const text = $("#yotoPillText");
  const connected = STATUS.yoto.connected;
  const configured = STATUS.yoto.configured;
  pill.classList.toggle("connected", connected);
  text.textContent = connected ? "Yoto connected" : "Yoto not connected";
  // Setup box only when there's no Client ID yet; connect only when configured.
  show($("#setupRow"), !configured);
  show($("#connectRow"), configured && !connected);
  $("#sendBtn").disabled = !connected;
}

async function saveClientId() {
  const cid = $("#clientIdInput").value.trim();
  if (!cid) return;
  clearError($("#setupError"));
  try {
    await api("/api/yoto/client-id", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: cid }),
    });
    await refreshStatus();
  } catch (e) {
    showError($("#setupError"), e.message);
  }
}

async function refreshStatus() {
  STATUS = await api("/api/status");
  renderStatus();
}

// ---- draft + tracks -------------------------------------------------------
async function refreshDraft() {
  const draft = await api("/api/draft");
  $("#cardName").value = draft.card_name || "";
  renderTracks(draft.tracks);
  renderPicture(draft.has_picture ? draft.picture_url + "?t=" + Date.now() : null);
  show($("#adjustPic"), !!(draft.has_picture && draft.has_source));
}

// ---- picture crop editor (pan + zoom) -------------------------------------
function openCropEditor() {
  const V = 300; // square viewport size in CSS px
  const overlay = document.createElement("div");
  overlay.className = "overlay";
  overlay.innerHTML = `
    <div class="modal" style="max-width:360px">
      <h3 style="margin:0 0 4px">Adjust the picture</h3>
      <p class="tiny" style="margin-top:0">Drag to move it around, and use the slider to zoom.</p>
      <div id="cropView" style="width:${V}px;height:${V}px;max-width:100%;margin:0 auto;overflow:hidden;
        position:relative;border-radius:12px;background:#eee;cursor:grab;touch-action:none">
        <img id="cropImg" alt="" style="position:absolute;left:0;top:0;-webkit-user-drag:none;user-select:none" />
      </div>
      <div class="row" style="align-items:center;gap:10px;margin-top:12px">
        <span class="tiny">🔍</span>
        <input id="cropZoom" type="range" min="1" max="4" step="0.02" value="1" style="flex:1;accent-color:var(--accent)" />
      </div>
      <div id="cropError" class="msg-box err hidden"></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:14px">
        <button class="btn ghost" id="cropCancel">Cancel</button>
        <button class="btn primary" id="cropApply">Apply</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);

  const view = overlay.querySelector("#cropView");
  const img = overlay.querySelector("#cropImg");
  const zoom = overlay.querySelector("#cropZoom");
  let W = 0, H = 0, base = 1, scale = 1, tx = 0, ty = 0;

  const clamp = () => {
    tx = Math.min(0, Math.max(V - W * scale, tx));
    ty = Math.min(0, Math.max(V - H * scale, ty));
  };
  const render = () => {
    img.style.width = W * scale + "px";
    img.style.height = H * scale + "px";
    img.style.left = tx + "px";
    img.style.top = ty + "px";
  };
  img.onload = () => {
    W = img.naturalWidth; H = img.naturalHeight;
    base = V / Math.min(W, H);          // zoom=1 → image covers the square
    scale = base;
    tx = (V - W * scale) / 2; ty = (V - H * scale) / 2;
    clamp(); render();
  };
  img.src = "/api/picture/source.png?t=" + Date.now();

  zoom.addEventListener("input", () => {
    const cx = (V / 2 - tx) / scale, cy = (V / 2 - ty) / scale;  // keep center fixed
    scale = base * parseFloat(zoom.value);
    tx = V / 2 - cx * scale; ty = V / 2 - cy * scale;
    clamp(); render();
  });

  const pt = (e) => {
    const t = e.touches ? e.touches[0] : e;
    const r = view.getBoundingClientRect();
    return { x: t.clientX - r.left, y: t.clientY - r.top };
  };
  let dragging = false, ox = 0, oy = 0;
  const start = (e) => { dragging = true; const p = pt(e); ox = p.x - tx; oy = p.y - ty; view.style.cursor = "grabbing"; };
  const move = (e) => { if (!dragging) return; const p = pt(e); tx = p.x - ox; ty = p.y - oy; clamp(); render(); e.preventDefault(); };
  const end = () => { dragging = false; view.style.cursor = "grab"; };
  view.addEventListener("mousedown", start);
  window.addEventListener("mousemove", move);
  window.addEventListener("mouseup", end);
  view.addEventListener("touchstart", start);
  view.addEventListener("touchmove", move, { passive: false });
  view.addEventListener("touchend", end);

  const close = () => {
    window.removeEventListener("mousemove", move);
    window.removeEventListener("mouseup", end);
    document.body.removeChild(overlay);
  };
  overlay.querySelector("#cropCancel").addEventListener("click", close);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  overlay.querySelector("#cropApply").addEventListener("click", async () => {
    const x = -tx / scale, y = -ty / scale, w = V / scale, h = V / scale;
    try {
      await api("/api/picture/crop", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ x, y, w, h }),
      });
      close();
      await refreshDraft();
    } catch (e) {
      showError(overlay.querySelector("#cropError"), e.message);
    }
  });
}

function renderTracks(tracks) {
  const ul = $("#tracks");
  ul.innerHTML = "";
  show($("#noTracks"), tracks.length === 0);
  tracks.forEach((t, i) => ul.appendChild(trackRow(t, i, tracks.length)));
}

function trackRow(t, index, total) {
  const li = document.createElement("li");
  li.className = "track";
  const iconSrc = t.icon_id ? `/api/icons/${t.icon_id}.png` : "/api/icons/music.png";
  const iconStyle = t.icon_id ? "" : "opacity:.35";
  li.innerHTML = `
    <span class="num2">${index + 1}</span>
    <img class="ticon" style="${iconStyle}" src="${iconSrc}" title="Choose the icon shown on the Yoto screen" />
    <div class="tmain">
      <input type="text" value="" />
      <div class="tmeta"></div>
    </div>
    <div class="tbtns">
      <button class="iconbtn up" title="Move up" ${index === 0 ? "disabled" : ""}>▲</button>
      <button class="iconbtn down" title="Move down" ${index === total - 1 ? "disabled" : ""}>▼</button>
      <button class="iconbtn del" title="Remove">🗑️</button>
    </div>`;
  const input = li.querySelector(".tmain input");
  input.value = t.title;
  li.querySelector(".tmeta").textContent =
    (t.source_kind === "youtube" ? "YouTube" : "File") + (t.duration_label ? " · " + t.duration_label : "");

  // rename (save on blur / Enter)
  const save = async () => {
    if (input.value.trim() && input.value !== t.title) {
      await api(`/api/tracks/${t.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: input.value.trim() }),
      });
      t.title = input.value.trim();
    }
  };
  input.addEventListener("blur", save);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });

  li.querySelector(".del").addEventListener("click", async () => {
    await api(`/api/tracks/${t.id}`, { method: "DELETE" });
    await refreshDraft();
  });
  li.querySelector(".up").addEventListener("click", () => move(t.id, index, -1));
  li.querySelector(".down").addEventListener("click", () => move(t.id, index, +1));
  li.querySelector(".ticon").addEventListener("click", () => openIconModal(t.id));
  return li;
}

async function move(id, index, delta) {
  const draft = await api("/api/draft");
  const ids = draft.tracks.map((t) => t.id);
  const j = index + delta;
  if (j < 0 || j >= ids.length) return;
  [ids[index], ids[j]] = [ids[j], ids[index]];
  await api("/api/tracks/reorder", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order: ids }),
  });
  await refreshDraft();
}

// ---- add audio ------------------------------------------------------------
async function addYouTube() {
  const url = $("#ytUrl").value.trim();
  if (!url) return;
  clearError($("#addError"));
  show($("#addProgress"), true);
  $("#addBar").style.width = "5%";
  $("#addMsg").textContent = "Getting the audio…";
  $("#ytAdd").disabled = true;
  try {
    const { job_id } = await api("/api/tracks/youtube", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    await pollJob(job_id, (p, m) => { $("#addBar").style.width = Math.max(5, p) + "%"; $("#addMsg").textContent = m; });
    $("#ytUrl").value = "";
    await refreshDraft();
  } catch (e) {
    showError($("#addError"), e.message);
  } finally {
    show($("#addProgress"), false);
    $("#ytAdd").disabled = false;
  }
}

async function addFile(file) {
  clearError($("#addError"));
  show($("#addProgress"), true);
  $("#addBar").style.width = "40%";
  $("#addMsg").textContent = "Adding your file…";
  try {
    const fd = new FormData();
    fd.append("file", file);
    await api("/api/tracks/file", { method: "POST", body: fd });
    await refreshDraft();
  } catch (e) {
    showError($("#addError"), e.message);
  } finally {
    show($("#addProgress"), false);
  }
}

// ---- picture --------------------------------------------------------------
function renderPicture(url) {
  const box = $("#picPreview");
  if (url) box.innerHTML = `<img src="${url}" alt="card picture" />`;
  else box.innerHTML = "<span>No picture yet</span>";
}

function picBusy(on) { show($("#picBusy"), on); }

async function setPicture(fn) {
  clearError($("#picError"));
  picBusy(true);
  try {
    await fn();
    await refreshDraft();
  } catch (e) {
    showError($("#picError"), e.message);
  } finally {
    picBusy(false);
  }
}

// Pixel icons are still used by the per-track device-icon picker (window.__icons).
async function loadIcons() {
  try {
    const { icons } = await api("/api/icons");
    window.__icons = icons;
  } catch (_) { /* ignore */ }
}

// Emoticons for the label picture.
async function loadEmojis() {
  const grid = $("#emojiGrid");
  let data;
  try { data = await api("/api/emoji"); } catch (_) { return; }
  if (!data.available) {
    grid.innerHTML = '<p class="tiny">Emoticons aren’t available on this computer.</p>';
    return;
  }
  grid.innerHTML = "";
  data.emojis.forEach((em) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "emojibtn";
    b.textContent = em;
    b.title = "Use this emoticon";
    b.addEventListener("click", () => setPicture(() => api("/api/picture/emoji", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ emoji: em }),
    })));
    grid.appendChild(b);
  });
}

// ---- per-track icon modal -------------------------------------------------
function openIconModal(trackId) {
  const icons = window.__icons || [];
  const overlay = document.createElement("div");
  overlay.style.cssText =
    "position:fixed;inset:0;background:rgba(30,20,50,.45);display:flex;align-items:center;" +
    "justify-content:center;z-index:50;padding:20px";
  const box = document.createElement("div");
  box.style.cssText = "background:#fff;border-radius:16px;padding:22px;max-width:380px;width:100%";
  box.innerHTML = `<h3 style="margin:0 0 6px">Pick a Yoto-screen icon</h3>
    <p class="tiny" style="margin-top:0">Shown on the player screen for this track.</p>
    <div class="icongrid" id="modalGrid"></div>
    <div style="text-align:right;margin-top:14px"><button class="btn ghost" id="modalCancel">Cancel</button></div>`;
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  const grid = box.querySelector("#modalGrid");
  icons.forEach((ic) => {
    const img = document.createElement("img");
    img.src = ic.url; img.title = ic.label;
    img.addEventListener("click", async () => {
      await api(`/api/tracks/${trackId}/icon`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ icon_id: ic.id }),
      });
      document.body.removeChild(overlay);
      await refreshDraft();
    });
    grid.appendChild(img);
  });
  const close = () => document.body.removeChild(overlay);
  box.querySelector("#modalCancel").addEventListener("click", close);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
}

// ---- connect + send -------------------------------------------------------
async function connectYoto() {
  try {
    const { url } = await api("/api/yoto/login");
    window.open(url, "_blank");
    // Poll status until the callback lands.
    const timer = setInterval(async () => {
      await refreshStatus();
      if (STATUS.yoto.connected) clearInterval(timer);
    }, 2000);
  } catch (e) {
    showError($("#sendError"), e.message);
  }
}

async function sendToYoto() {
  clearError($("#sendError"));
  show($("#sendDone"), false);
  show($("#sendProgress"), true);
  $("#sendBar").style.width = "2%";
  $("#sendMsg").textContent = "Starting…";
  $("#sendBtn").disabled = true;
  try {
    const { job_id } = await api("/api/send", { method: "POST" });
    const result = await pollJob(job_id, (p, m) => {
      $("#sendBar").style.width = Math.max(2, p) + "%"; $("#sendMsg").textContent = m;
    });
    $("#sendDone").innerHTML =
      "🎉 Your card is ready in your Yoto account!<br><span class='tiny'>" +
      "Open the Yoto app and tap a blank Make-Your-Own card to link it, then press play.</span>";
    show($("#sendDone"), true);
  } catch (e) {
    if (e.data && e.data.need_connect) { await refreshStatus(); }
    showError($("#sendError"), e.message);
  } finally {
    show($("#sendProgress"), false);
    $("#sendBtn").disabled = !STATUS.yoto.connected;
  }
}

// ---- label ----------------------------------------------------------------
async function makeLabel() {
  clearError($("#labelError"));
  show($("#labelDone"), false);
  $("#labelBtn").disabled = true;
  try {
    const { label_url } = await api("/api/label", { method: "POST" });
    $("#labelOpen").href = label_url + "?t=" + Date.now();
    show($("#labelDone"), true);
  } catch (e) {
    showError($("#labelError"), e.message);
  } finally {
    $("#labelBtn").disabled = false;
  }
}

// ---- wire up --------------------------------------------------------------
function wire() {
  $("#ytAdd").addEventListener("click", addYouTube);
  $("#ytUrl").addEventListener("keydown", (e) => { if (e.key === "Enter") addYouTube(); });
  $("#filePick").addEventListener("click", () => $("#fileInput").click());
  $("#fileInput").addEventListener("change", (e) => { if (e.target.files[0]) addFile(e.target.files[0]); e.target.value = ""; });
  $("#skipSponsors").addEventListener("change", (e) => {
    api("/api/settings/remove-sponsors", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: e.target.checked }),
    }).catch(() => {});
  });

  // card name (save on change)
  let nameTimer;
  $("#cardName").addEventListener("input", () => {
    clearTimeout(nameTimer);
    nameTimer = setTimeout(() => {
      api("/api/card/name", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: $("#cardName").value }),
      });
    }, 400);
  });

  // picture tabs
  $$(".tab").forEach((tab) => tab.addEventListener("click", () => {
    $$(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    $$(".tabpanel").forEach((p) => show(p, p.dataset.panel === tab.dataset.tab));
  }));
  $("#adjustPic").addEventListener("click", openCropEditor);
  $("#picAuto").addEventListener("click", () => setPicture(() => api("/api/picture/auto", { method: "POST" })));
  $("#picUploadBtn").addEventListener("click", () => $("#picUploadInput").click());
  $("#picUploadInput").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (f) setPicture(() => { const fd = new FormData(); fd.append("file", f); return api("/api/picture/upload", { method: "POST", body: fd }); });
    e.target.value = "";
  });
  $("#aiGen").addEventListener("click", () => {
    const prompt = $("#aiPrompt").value.trim();
    if (prompt) setPicture(() => api("/api/picture/ai", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    }));
  });

  $("#updateNow").addEventListener("click", doUpdate);
  $("#clientIdSave").addEventListener("click", saveClientId);
  $("#advToggle").addEventListener("click", (e) => {
    e.preventDefault();
    show($("#setupRow"), true);
    $("#clientIdInput").focus();
  });
  // About popup
  const about = $("#aboutOverlay");
  $("#aboutLink").addEventListener("click", (e) => { e.preventDefault(); show(about, true); });
  $("#aboutClose").addEventListener("click", () => show(about, false));
  about.addEventListener("click", (e) => { if (e.target === about) show(about, false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") show(about, false); });
  $("#connectBtn").addEventListener("click", connectYoto);
  $("#yotoPill").addEventListener("click", () => {
    if (STATUS.yoto.configured && !STATUS.yoto.connected) connectYoto();
  });
  $("#sendBtn").addEventListener("click", sendToYoto);
  $("#labelBtn").addEventListener("click", makeLabel);

  $("#startOver").addEventListener("click", async (e) => {
    e.preventDefault();
    if (confirm("Start a brand-new card? This clears what you've added.")) {
      await api("/api/draft/reset", { method: "POST" });
      await refreshDraft();
      $("#cardName").value = "";
      show($("#sendDone"), false);
      show($("#labelDone"), false);
    }
  });
}

wire();
init();
