"use strict";

// ---- tiny helpers ---------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
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
  renderStatus();
  if (STATUS.ai_available) show($("#aiTab"), true);
  if (!STATUS.tools.ok) {
    showError($("#toolsWarning"),
      "Some tools this app needs are missing. Please reinstall Yoto Maker or ask for help.");
  }
  await loadIcons();
  await refreshDraft();
}

function renderStatus() {
  const pill = $("#yotoPill");
  const text = $("#yotoPillText");
  const connected = STATUS.yoto.connected;
  pill.classList.toggle("connected", connected);
  text.textContent = connected ? "Yoto connected" : "Yoto not connected";
  show($("#connectRow"), !connected);
  $("#sendBtn").disabled = !connected;
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

async function loadIcons() {
  const { icons } = await api("/api/icons");
  const grid = $("#iconGrid");
  grid.innerHTML = "";
  icons.forEach((ic) => {
    const img = document.createElement("img");
    img.src = ic.url;
    img.title = ic.label;
    img.dataset.id = ic.id;
    img.addEventListener("click", () => {
      $$("#iconGrid img").forEach((x) => x.classList.remove("sel"));
      img.classList.add("sel");
      setPicture(() => api("/api/picture/library", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ icon_id: ic.id }),
      }));
    });
    grid.appendChild(img);
  });
  window.__icons = icons;
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

  $("#connectBtn").addEventListener("click", connectYoto);
  $("#yotoPill").addEventListener("click", () => { if (!STATUS.yoto.connected) connectYoto(); });
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
