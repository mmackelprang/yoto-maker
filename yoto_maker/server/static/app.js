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
    // Prefer our own {error} envelope. Fall back to FastAPI's {detail} — the shape
    // a bare HTTPException(status, "message") serialises to — so those messages
    // reach the user instead of being swallowed to the generic line below.
    //
    // typeof === "string" is load-bearing: FastAPI ALSO uses `detail` for 422
    // request-validation errors, where it is a LIST of error objects, not a
    // sentence. new Error([{…}]) renders "[object Object]", which is worse than the
    // generic fallback — so a non-string detail is ignored and the generic line
    // stands. Guarded by tests/test_httpexception_reaches_user.py.
    const msg =
      (data && data.error) ||
      (data && typeof data.detail === "string" && data.detail) ||
      "Something went wrong. Please try again.";
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

// Render a .msg-box's contents. A string sets one text node — byte for byte
// what showError() has always done. An array becomes one <p> per entry.
//
// The array shape is not new: CLIENT_ID_CONFIRM.body is already an array and
// openClientIdConfirm() already renders it exactly this way into
// #clientIdConfirmBody. This lifts that loop out of one call site so the two
// places that now need it — the Client ID refusal messages (copy.md §4c) and
// the grouped upload summary (spec §B.3.3) — share one implementation instead
// of growing two. Landed as its own commit ahead of both items for that reason.
//
// replaceChildren() and not innerHTML: every string here is user-facing copy or
// a filename the user chose, and a filename is attacker-controllable in the
// only sense that matters locally — it is not ours to trust into markup.
function setMsgBoxContent(box, content) {
  if (!Array.isArray(content)) { box.textContent = content; return; }
  box.replaceChildren(...content.map((text) => {
    const p = document.createElement("p");
    p.textContent = text;
    return p;
  }));
}

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
  applyRoute();    // honour a #settings hash on load / reload
  checkUpdate();   // non-blocking
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
  pill.classList.toggle("connected", connected);
  text.textContent = connected ? "Yoto connected" : "Yoto not connected";
  // NOTE: STATUS.yoto.configured is permanently true (resolve_client_id() falls
  // back to a non-empty baked-in constant), so it drives nothing. The old
  // `show($("#setupRow"), !configured)` here meant the Client ID row could never
  // appear on its own; that row now lives in the settings view.
  show($("#connectRow"), !connected);
  // #advRow is NOT in #connectRow any more, so the call above no longer reaches
  // it — that is the fix, not an oversight. It is never hidden in either state.
  // "a different" is false before there is a current one: she hasn't connected
  // any account yet, and in that state the big 🔗 Connect my Yoto account button
  // directly above already owns the connect intent. Same rule copy.md §4 applies
  // to the Client ID label (Paste a Client ID / Paste a different Client ID).
  $("#advToggle").textContent = connected
    ? "⚙️ Connect a different Yoto account"
    : "⚙️ Yoto connection settings";
  $("#sendBtn").disabled = !connected;
}

async function refreshStatus() {
  STATUS = await api("/api/status");
  renderStatus();
}

// ---- settings view routing ------------------------------------------------
// The hashchange handler is the single place that swaps views. Every entry point
// just sets location.hash, so a click and a browser Back press cannot diverge.
let returnFocusTo = null;

function inSettings() { return location.hash === "#settings"; }

function applyRoute() {
  if (!STATUS) return;            // init() calls applyRoute() once STATUS exists
  const on = inSettings();
  show($("#cardView"), !on);
  show($("#settingsView"), on);
  document.title = on ? "Settings · Yoto Maker" : "Yoto Maker";
  if (on) {
    // The card view may be scrolled far down a long track list; landing
    // mid-page on a fresh view is disorienting.
    window.scrollTo(0, 0);
    $("#settingsTitle").focus();
    openSettings();
  } else {
    closeSettings();
    const back = returnFocusTo && document.contains(returnFocusTo) ? returnFocusTo : null;
    returnFocusTo = null;
    if (back) back.focus();
    // The user may have just connected or disconnected; step 3 and #sendBtn
    // must reflect reality on return.
    refreshStatus().catch(() => {});
  }
}

function gotoSettings(opener) {
  returnFocusTo = opener || null;
  if (inSettings()) applyRoute();      // already there (e.g. reload) — just render
  else location.hash = "settings";     // hashchange does the swap
}

function leaveSettings() {
  // Always setting the hash costs one extra history entry but can never escape
  // the app, which history.back() could if the user arrived at #settings direct.
  if (location.hash) location.hash = "";
  else applyRoute();
}

// No focus trap and no Escape-to-exit: .hidden is `display: none !important`,
// which takes the hidden view out of the tab order, the accessibility tree and
// find-in-page for free. This is a page, not a dialog — and the user may be
// mid-way through pasting a Client ID, which a stray Escape must not discard.

// ---- settings section registry --------------------------------------------
// The only coordination the .setting primitive needs, and the one place the
// "no coordination with other sections" promise (overview.md §4.4) used to
// leak: openSettings(), closeSettings() and the Escape handler each hardcoded
// every section by name, so adding setting #3 meant editing three shared
// functions — and forgetting the Escape chain would silently ship a
// confirmation that could not be dismissed with the keyboard.
//
// Now each section registers itself once, next to its own code:
//
//   registerSetting({
//     onOpen,        // settings view shown — render current state here
//     onClose,       // settings view left — tear down timers, clear messages
//     confirm,       // this section's .setting-confirm element, if it has one
//     closeConfirm,  // (restoreFocus) => void — dismisses `confirm`
//   });
//
// Nothing below is keyed to a specific setting's id.
const SETTINGS_SECTIONS = [];

function registerSetting(section) { SETTINGS_SECTIONS.push(section); }

// Dismisses whichever confirmation is open. Returns true if one was, so the
// caller can tell "Escape closed something" from "Escape did nothing".
function closeOpenConfirms(restoreFocus = true) {
  let closed = false;
  for (const s of SETTINGS_SECTIONS) {
    if (s.confirm && !s.confirm.classList.contains("hidden")) {
      s.closeConfirm(restoreFocus);
      closed = true;
    }
  }
  return closed;
}

// Catches the failure mode this registry exists to prevent: a confirmation
// added to the markup but never registered. It would look and behave correctly
// until a keyboard user pressed Escape, which is exactly the kind of gap that
// ships unnoticed.
function auditSettingConfirms() {
  const registered = new Set(SETTINGS_SECTIONS.map((s) => s.confirm).filter(Boolean));
  document.querySelectorAll("#settingsView .setting-confirm").forEach((el) => {
    if (!registered.has(el)) {
      console.warn(
        `[settings] #${el.id || "(unnamed)"} is a .setting-confirm but was never ` +
        `passed to registerSetting(); Escape will not dismiss it.`
      );
    }
  });
}

function openSettings() {
  for (const s of SETTINGS_SECTIONS) if (s.onOpen) s.onOpen();
}

function closeSettings() {
  for (const s of SETTINGS_SECTIONS) if (s.onClose) s.onClose();
  // restoreFocus: false — focusing a confirmation's opener would be wrong and
  // would also lose a race: applyRoute() restores focus to `returnFocusTo` (the
  // control that opened Settings) immediately after this returns.
  closeOpenConfirms(false);
}

// ---- setting 1: your Yoto account -----------------------------------------
// Copy is verbatim from the design handoff (copy.md §3). Do not reword.
const ACCOUNT_STATUS = {
  checking: {
    cls: "is-unknown", head: "Checking your Yoto connection…", sub: "",
  },
  connected: {
    cls: "is-ok", head: "Connected and working",
    sub: "We just checked with Yoto and everything’s fine.",
  },
  not_connected: {
    cls: "is-unknown", head: "Not connected yet",
    sub: "Connect your Yoto account to send cards to it.",
  },
  broken: {
    cls: "is-err", head: "There’s a problem with this connection",
    sub: "Yoto Maker can’t send cards right now. Signing in again usually fixes it.",
  },
  unknown: {
    cls: "is-unknown", head: "We couldn’t check right now",
    sub: "This computer doesn’t seem to be online. Check your internet, then come back.",
  },
  signing_in: {
    cls: "is-warn", head: "Waiting for you to sign in…",
    sub: "We opened Yoto’s website in another tab. Sign in there, then come back here.",
  },
};

// The backend tags sign-in failures with a reason so the UI can use its own
// wording rather than echoing a message written for a different context.
const SIGNIN_ERRORS = {
  rejected: "Yoto couldn’t complete the sign-in. Please try again.",
  offline: "We couldn’t reach Yoto. Check your internet connection, then try again.",
};

const CHECK_TIMEOUT_MS = 8000;
const SIGNIN_POLL_MS = 2000;
const SIGNIN_MAX_MS = 3 * 60 * 1000;

const ACCOUNT = { state: "checking", prev: "not_connected", timer: null };

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms)),
  ]);
}

function accountMsg(kind, html) {
  const box = $("#accountMsg");
  box.className = "msg-box " + kind;
  box.innerHTML = html;
  show(box, true);
}

function setAccountState(state) {
  // Remember the last settled state so Cancel and a 3-minute timeout can put
  // the section back where it was rather than guessing.
  if (state !== "signing_in" && state !== "checking") ACCOUNT.prev = state;
  ACCOUNT.state = state;
  renderAccount();
}

function renderAccount() {
  const s = ACCOUNT_STATUS[ACCOUNT.state] || ACCOUNT_STATUS.unknown;
  $("#accountStatus").className = "setting-status " + s.cls;
  $("#accountStatusHead").textContent = s.head;
  $("#accountStatusSub").textContent = s.sub;

  const btn = $("#accountPrimary");
  if (ACCOUNT.state === "signing_in") {
    btn.textContent = "Waiting for Yoto…";
    btn.disabled = true;
  } else if (ACCOUNT.state === "not_connected") {
    // Word-for-word identical to step 3's #connectBtn, deliberately: the two
    // places that do this must never look like different features.
    btn.textContent = "🔗 Connect my Yoto account";
    btn.disabled = false;
  } else {
    btn.textContent = "🔗 Sign in to Yoto again";
    // Only "checking" disables it. An offline user may still legitimately want
    // to start a sign-in — she might be about to fix her Wi-Fi — so `unknown`
    // must never dead-end her.
    btn.disabled = ACCOUNT.state === "checking";
  }
  show($("#accountCancel"), ACCOUNT.state === "signing_in");
}

async function checkAccount() {
  setAccountState("checking");
  let res;
  try {
    res = await withTimeout(api("/api/yoto/check", { method: "POST" }), CHECK_TIMEOUT_MS);
  } catch (_) {
    // Never render a network problem as "your connection is broken", or she
    // will disconnect a healthy account chasing a Wi-Fi fault.
    setAccountState("unknown");
    return;
  }
  setAccountState(res && res.state ? res.state : "unknown");
}

function openAccountConfirm() {
  // Primitive rule: the confirmation replaces the actions slot, so there is
  // never more than one live set of choices in a section.
  show($("#accountActions"), false);
  show($("#accountConfirm"), true);
  // Focus starts on the way out, not the way through: a reflexive Space or
  // Enter must not disconnect her account.
  $("#accountConfirmNo").focus();
}

// restoreFocus defaults to true: Escape and "Never mind" both return focus to
// the button that opened the confirmation. The "Yes" path passes false, because
// startSignIn() is about to take over.
function closeAccountConfirm(restoreFocus = true) {
  const box = $("#accountConfirm");
  if (box.classList.contains("hidden")) return;
  show(box, false);
  show($("#accountActions"), true);
  if (restoreFocus) $("#accountPrimary").focus();
}

function stopSignInPoll() {
  if (ACCOUNT.timer) { clearInterval(ACCOUNT.timer); ACCOUNT.timer = null; }
}

async function startSignIn() {
  const wasConnected = !!(STATUS && STATUS.yoto && STATUS.yoto.connected);
  clearError($("#accountMsg"));
  let url;
  try {
    // Folding the sign-out into the sign-in is what lets one button serve both
    // "fix this" and "switch accounts" — the user never has to know they are
    // two operations.
    if (wasConnected) await api("/api/yoto/logout", { method: "POST" });
    ({ url } = await api("/api/yoto/login"));
  } catch (e) {
    await refreshStatus().catch(() => {});
    setAccountState(wasConnected ? "broken" : "not_connected");
    accountMsg("err", SIGNIN_ERRORS[e.data && e.data.reason] || e.message);
    return;
  }

  const win = window.open(url, "_blank");
  if (!win) {
    // Popup blocked. A real link is the only reliable recovery — "allow popups"
    // is not an actionable instruction for this audience.
    accountMsg("info",
      "Your browser stopped the Yoto window from opening.<br>" +
      '<a id="accountOpenLink" target="_blank" rel="noopener">Open Yoto’s sign-in page&nbsp;↗</a>');
    $("#accountOpenLink").href = url;   // set as a property, never interpolated
    await refreshStatus().catch(() => {});
    await checkAccount();
    return;
  }

  setAccountState("signing_in");
  const deadline = Date.now() + SIGNIN_MAX_MS;
  stopSignInPoll();
  ACCOUNT.timer = setInterval(async () => {
    if (Date.now() > deadline) {
      stopSignInPoll();
      setAccountState(ACCOUNT.prev);
      accountMsg("info",
        "We stopped waiting for the sign-in. If you finished signing in on Yoto’s website, " +
        "press “Sign in to Yoto again” — otherwise you can try again now.");
      return;
    }
    try { await refreshStatus(); } catch (_) { return; }
    if (STATUS.yoto.connected) {
      stopSignInPoll();
      // A token file appearing is not proof it works; confirm with a real check
      // before claiming success. The status line updates first so the polite
      // role="status" announcement isn't queued behind the assertive alert.
      await checkAccount();
      accountMsg("ok", "🎉 You’re signed in. Yoto Maker can send cards again.");
    }
  }, SIGNIN_POLL_MS);
}

function cancelSignIn() {
  stopSignInPoll();
  setAccountState(ACCOUNT.prev);
  accountMsg("info", "Stopped waiting. You can close the Yoto tab if it’s still open.");
}

// ---- setting 2: Yoto Client ID --------------------------------------------
// Copy is verbatim from the design handoff (copy.md §4). Do not reword.
// copy.md §4b. Replaces the three-row table this object used to hold.
//
// Keyed source-then-verdict, and the table is TOTAL: every combination of
// source and verdict has a row, including builtin+invalid, which is unreachable
// in a correct build and guarded by test_the_shipped_default_scores_ok. It
// exists so nobody has to reason about whether a gap is a decision. Same
// completeness discipline tokens.md §4 adopted after an unmeasured pair shipped
// a 2.56:1 label.
const ENV_SUB =
  "Someone set this up on this computer using YOTO_CLIENT_ID, and that takes " +
  "priority. To change it, they’ll need to change it there.";

const CANT_SIGN_IN_FIX_BELOW =
  "Yoto Maker can’t sign in to Yoto until this is fixed. " +
  "Press \"Go back to the built-in one\" below.";

const CLIENT_ID_STATUS = {
  builtin: {
    ok: {
      cls: "is-ok", head: "Using the built-in Client ID",
      sub: "This is what most people use. Nothing to do here.",
    },
    invalid: {
      cls: "is-err", head: "Something’s wrong with the built-in Client ID",
      sub: "Yoto Maker can’t sign in to Yoto. This shouldn’t be possible — the " +
           "details at the bottom of this page are what someone will need to help you.",
    },
  },
  saved: {
    ok: {
      cls: "is-ok", head: "Using your own Client ID",
      sub: "Saved on this computer only.",
    },
    unusual: {
      cls: "is-warn", head: "Using your own Client ID",
      sub: "Saved on this computer only. It isn’t the usual 32 letters and numbers, " +
           "so signing in to Yoto may not work.",
    },
    invalid: { cls: "is-err", head: "This isn’t a Client ID", sub: CANT_SIGN_IN_FIX_BELOW },
    // The email case gets its OWN headline. The thesis of this whole change is
    // that NAMING the mistake is what visibility failed to do — the mask
    // rendered mandydeogie@gmail.com as "mand…com", deleting the one substring
    // that would have made it self-evident. Being explicit in the save refusal
    // while being coy here would be inconsistent, and this is the exact user in
    // the incident.
    invalid_email: {
      cls: "is-err", head: "That’s an email address, not a Client ID",
      sub: CANT_SIGN_IN_FIX_BELOW,
    },
  },
  env: {
    // env + unusual DELIBERATELY has no row of its own. On a value a developer
    // set on purpose, "that isn't the usual shape" is precisely the
    // false-positive noise the deny-list's conservatism exists to suppress. On
    // env we speak up only when the value is definitely wrong.
    ok: { cls: "is-warn", head: "Set outside the app", sub: ENV_SUB },
    unusual: { cls: "is-warn", head: "Set outside the app", sub: ENV_SUB },
    invalid: {
      cls: "is-err", head: "Set outside the app, and it isn’t a Client ID",
      sub: "Yoto Maker can’t sign in to Yoto until this is fixed. YOTO_CLIENT_ID on " +
           "this computer holds something that isn’t a Client ID, and only whoever " +
           "set it can change it.",
    },
  },
};

function clientIdStatusRow(source, verdict, reason) {
  const tier = CLIENT_ID_STATUS[source] || CLIENT_ID_STATUS.builtin;
  if (verdict === "invalid" && reason === "email" && tier.invalid_email) {
    return tier.invalid_email;
  }
  // Falls back to the tier's `ok` row for any combination the table does not
  // enumerate (builtin+unusual, which the shipped default makes unreachable).
  return tier[verdict] || tier.ok;
}

const CLIENT_ID_CONFIRM = {
  save: {
    title: "Use this Client ID?",
    body: [
      "Yoto Maker will start using the Client ID you pasted. Because this changes how " +
      "the app signs in, you’ll need to sign in to Yoto again afterwards.",
      "Nothing in your Yoto account changes.",
    ],
    yes: "Yes, use it",
  },
  reset: {
    title: "Go back to the built-in Client ID?",
    body: [
      "Yoto Maker will forget the Client ID you pasted and use the one it came with. " +
      "You’ll need to sign in to Yoto again afterwards.",
      "Nothing in your Yoto account changes.",
    ],
    yes: "Yes, use the built-in one",
  },
};

// The client-side mirror of config.py's validate_client_id(). It exists ONLY
// for the honesty of the confirmation flow — never confirm an action that will
// be refused (interactions.md §3.6.3, extending §3.2's "never confirm a no-op"
// from no-op to no-op or refusal). Showing the save confirmation for a value
// that will be refused would ask the user to accept a frightening consequence
// ("you'll need to sign in to Yoto again") that is never going to happen, and
// then error at her.
//
// THE SERVER CHECK IS THE SAFETY PROPERTY (app.py set_client_id). This one is
// allowed to be a second implementation for that reason and for no other; it
// must stay in lockstep with config.py. Same deny-list, same order, same
// reasons. It is NOT the 32-character rule — see config.validate_client_id.
function clientIdVerdict(value) {
  const t = (value || "").trim();
  if (!t) return { verdict: "invalid", reason: "length" };
  if (t.includes("@")) return { verdict: "invalid", reason: "email" };
  if (t.includes("/") || t.includes(":")) return { verdict: "invalid", reason: "url" };
  if (t.includes("<") || t.includes(">")) return { verdict: "invalid", reason: "charset" };
  if (/\s/.test(t)) return { verdict: "invalid", reason: "spaces" };
  if (t.length > 128) return { verdict: "invalid", reason: "too_long" };
  if (!/^[A-Za-z0-9]{32}$/.test(t)) return { verdict: "unusual", reason: "charset" };
  return { verdict: "ok", reason: null };
}

// copy.md §4c, verbatim. Three paragraphs each: what you entered / what it
// should be / reassurance. The reassurance line is appended at render time
// because it is state-dependent.
const CLIENT_ID_REFUSAL = {
  email: [
    "That looks like an email address, not a Client ID.",
    "A Client ID is a code from Yoto’s developer website — letters and numbers, with " +
    "no @ sign. It isn’t the email address you sign in to Yoto with.",
  ],
  url: [
    "That looks like a web address, not a Client ID.",
    "The setup page shows a web address and a Client ID next to each other, and it’s " +
    "easy to copy the wrong one. The Client ID is the shorter one — just letters and " +
    "numbers.",
  ],
  _default: [
    "That doesn’t look like a Client ID.",
    "A Client ID is one unbroken run of letters and numbers, with no spaces. It may " +
    "help to copy it again from Yoto’s developer website.",
  ],
};

// The reassurance line is TRUE ONLY BECAUSE the server's verdict check runs
// above get_settings().set(...) and above logout() (app.py set_client_id). It is
// the readable form of that invariant. If the ordering ever changes, this string
// must change with it.
//
// And it is state-dependent because "you're still signed in" is false when she
// isn't, and a reassurance that is audibly wrong about her situation costs more
// trust than it buys. copy.md §4c; same rule §1a and §4 already apply twice.
function clientIdReassurance() {
  const connected = !!(STATUS && STATUS.yoto && STATUS.yoto.connected);
  return connected
    ? "Nothing was changed, and you’re still signed in to Yoto."
    : "Nothing was changed.";
}

function clientIdMsg(kind, content) {
  const box = $("#clientIdMsg");
  box.className = "msg-box " + kind;
  // A string is one text node, exactly as before; an array is one <p> each.
  // The refusal messages (copy.md §4c) are three paragraphs — what you entered
  // / what it should be / reassurance — and the reassurance line keeps its own
  // visual separation because it is the sentence doing the most work.
  setMsgBoxContent(box, content);
  show(box, true);
}

// Whether the full value is currently on screen. Module-level, and deliberately
// NOT reset inside renderClientId(): that function also runs from
// closeClientIdConfirm() (below), which fires when a user CANCELS a confirmation
// — an event she did not aim at this control. Without the flag, cancelling a
// confirmation would silently collapse a reveal she had opened, for no reason
// she caused. That is the single defect this flag exists to prevent.
//
// Reset on exactly three events, each set at its own site:
//   1. entering the settings view      → the onOpen wrapper in init()
//   2. a successful save or reset      → submitClientId(), success path only
//   3. source becoming "builtin"       → subsumed by 2; the block is removed
//
// There is NO timer. An auto-hide would defend against a bystander reading a
// value that is printed in the user's own sign-in URL and on a public dashboard,
// while breaking the one task the feature serves — she is mid-comparison against
// another screen, or reading it aloud over the phone. It would also flip
// aria-expanded with no user action, an unannounced state change a screen-reader
// user has no way to anticipate: a real defect traded for theatre.
let clientIdRevealed = false;

// The label names the ACTION, aria-expanded names the STATE. Together they read
// "Show the short version, button, expanded" — coherent, not contradictory. A
// constant label while the whole thing is already displayed would be plainly
// confusing to the sighted majority. aria-pressed is wrong here: it would
// announce "pressed", which describes a control switched on and says nothing
// about whether the text beside it is long or short.
function setClientIdRevealLabel(revealed) {
  const btn = $("#clientIdReveal");
  btn.textContent = revealed ? "Show the short version" : "Show the whole thing";
  btn.setAttribute("aria-expanded", revealed ? "true" : "false");
}

// Synchronous. Both strings are already in STATUS, so this makes no network
// request and has no failure mode — no spinner, no error string, no decision
// about what the toggle shows when a request times out (overview.md §7.8).
function toggleClientIdReveal() {
  clientIdRevealed = !clientIdRevealed;
  const y = (STATUS && STATUS.yoto) || {};
  $("#clientIdValue").textContent =
    clientIdRevealed ? (y.client_id_full || "") : (y.client_id_masked || "");
  setClientIdRevealLabel(clientIdRevealed);
  // Focus deliberately stays on the button: the content it controls is adjacent
  // and the button is also the way back. No focus management, nothing to get
  // wrong — a direct benefit of choosing a disclosure over a modal-ish reveal.
  //
  // And no live region on #clientIdValue: #clientIdStatus in this section
  // already carries role="status", and a second live region in one section is
  // exactly the double-announcement hazard interactions.md §4.3 prohibits. A
  // user who wants the value reads it with the virtual cursor, where she can
  // also arrow through it character by character — which is what transcription
  // needs, and what one utterance of 32 random characters would not give her.
}

function renderClientId() {
  const y = (STATUS && STATUS.yoto) || {};
  const source = y.client_id_source || "builtin";
  const masked = y.client_id_masked || "";
  const full = y.client_id_full || "";
  const verdict = y.client_id_verdict || "ok";
  const reason = y.client_id_reason || null;
  const s = clientIdStatusRow(source, verdict, reason);

  $("#clientIdStatus").className = "setting-status " + s.cls;
  $("#clientIdStatusHead").textContent = s.head;
  $("#clientIdStatusSub").textContent = s.sub;

  // ---- the value in effect (interactions.md §3.5.2) ----
  // Row order is load-bearing. `builtin` is tested FIRST because client_id_full
  // is deliberately null in exactly that state — testing for the null first
  // would misread a designed absence as version skew.
  //
  // builtin renders no value at all: the built-in ID is the app author's
  // registration, so there is no dashboard entry to compare it against and the
  // comparison task simply does not exist here. Rendering 32 characters under
  // "This is what most people use. Nothing to do here." would contradict that
  // sentence for every user who ever opens this screen, to serve no task.
  const showValue = source !== "builtin" && !!masked;
  show($("#clientIdCurrent"), showValue);
  if (showValue) {
    // interactions.md §3.6.4 adds two rows ABOVE the existing ones, reached by
    // the same principle the table already establishes: the toggle is OMITTED,
    // never disabled, whenever it could do nothing. Here it could do nothing
    // because the whole value is already displayed.
    //
    // THE RULE: the mask is the summary form of a value that has the expected
    // SHAPE. Applied to a value that does not, it is not a summary — it is
    // camouflage. mask_client_id("mandydeogie@gmail.com") is "mand…com", which
    // deleted @gmail.com — the exact substring that would have made the mistake
    // self-evident — and what survived reads MORE code-like than the original.
    //
    // `unusual` matters here as much as `invalid`: a truncated 17-character
    // paste masks to "a8OG…tDU", hiding the truncation completely and looking
    // entirely plausible.
    const shapeFailed = verdict === "invalid" || verdict === "unusual";
    const canReveal = !shapeFailed && !!full && full !== masked;
    // clientIdRevealed is irrelevant when there is no toggle and must not be
    // consulted (§3.6.4). Its three reset events are unchanged.
    const revealed = canReveal && clientIdRevealed;
    $("#clientIdValue").textContent =
      shapeFailed ? (full || masked) : (revealed ? full : masked);
    setClientIdRevealLabel(revealed);
    show($("#clientIdReveal"), canReveal);
  }

  // With the current value displayed directly above it, the `saved` state stacks
  // two Client-ID-shaped things and "Paste a Client ID" no longer distinguishes
  // the one you have from the one you would replace it with (copy.md, input
  // label). builtin and env are unchanged — in neither is there a saved value of
  // hers to differ from.
  $("#clientIdInputLabel").textContent =
    source === "saved" ? "Paste a different Client ID" : "Paste a Client ID";

  const isEnv = source === "env";
  // Disabled and explained, not hidden. Hiding the input would make the section
  // look broken to the person who came here specifically to change this.
  //
  // The value block above is deliberately EXEMPT from this disabling
  // (interactions.md §3.4 as amended). It is read-only — there is nothing to
  // disable — and env is the one state where the value is not discoverable
  // anywhere else, so it is the state the display matters most in.
  const input = $("#clientIdInput");
  input.disabled = isEnv;
  $("#clientIdSave").disabled = isEnv;
  show($("#clientIdEnvNote"), isEnv);
  // Tie the note to the field it explains, so a screen-reader user hears *why*
  // the field is disabled instead of just finding it dead. Set only while the
  // note is visible — a description pointing at a display:none element is
  // dropped from the accessibility tree anyway.
  if (isEnv) input.setAttribute("aria-describedby", "clientIdEnvNote");
  else input.removeAttribute("aria-describedby");

  const actions = $("#clientIdActions");
  if (actions) {
    // Absent, not merely hidden, when an env var is in effect: deleting the
    // saved value would fall through to the env var rather than the built-in
    // one, so "Go back to the built-in one" would be a lie.
    if (isEnv) actions.remove();
    else show(actions, source === "saved");
  }

  // Promoted to .btn primary in the invalid state ONLY, and this does not
  // breach overview.md §4.3.4's one-primary-per-setting rule: the Client ID
  // section has NO primary today — Save and the reset are both plain .btn — so
  // promoting one is within budget. It is the only state in which this section
  // has a primary action.
  //
  // Null when source is "env": the actions block is removed entirely there,
  // because deleting the saved value would fall through to the env var and
  // "Go back to the built-in one" would be a lie (overview.md §7.4).
  const reset = $("#clientIdReset");
  if (reset) reset.classList.toggle("primary", verdict === "invalid");
}

function openClientIdConfirm(kind, unusual = false) {
  const c = CLIENT_ID_CONFIRM[kind];
  $("#clientIdConfirm").dataset.kind = kind;
  $("#clientIdConfirmText").textContent = c.title;
  const body = $("#clientIdConfirmBody");
  body.innerHTML = "";
  // An `unusual` value IS saved — the concern is named, not enforced. One extra
  // paragraph, inserted FIRST, above "Yoto Maker will start using the Client ID
  // you pasted." No new UI: the slot already carries multi-paragraph bodies.
  // copy.md §4c. Buttons unchanged: Never mind / Yes, use it.
  const paras = unusual
    ? ["Just so you know: a Client ID is usually 32 letters and numbers, and this one " +
       "isn’t. If you’re sure it’s right, go ahead."].concat(c.body)
    : c.body;
  paras.forEach((para) => {
    const p = document.createElement("p");
    p.textContent = para;
    body.appendChild(p);
  });
  $("#clientIdConfirmYes").textContent = c.yes;

  const actions = $("#clientIdActions");
  if (actions) show(actions, false);
  // The Save button lives in the body slot rather than the actions slot, so
  // disable it too — one live set of choices per section, always.
  $("#clientIdInput").disabled = true;
  $("#clientIdSave").disabled = true;
  show($("#clientIdConfirm"), true);
  $("#clientIdConfirmNo").focus();
}

function closeClientIdConfirm(restoreFocus = true) {
  const box = $("#clientIdConfirm");
  if (box.classList.contains("hidden")) return;
  const kind = box.dataset.kind;
  show(box, false);
  $("#clientIdConfirmNo").disabled = false;
  $("#clientIdConfirmYes").disabled = false;
  renderClientId();                       // restores the input, Save and the reset action
  if (restoreFocus) {
    const opener = kind === "reset" ? $("#clientIdReset") : $("#clientIdSave");
    if (opener) opener.focus();
  }
}

async function submitClientId(kind) {
  $("#clientIdConfirmNo").disabled = true;
  $("#clientIdConfirmYes").disabled = true;
  clearError($("#clientIdMsg"));
  try {
    if (kind === "reset") {
      await api("/api/yoto/client-id", { method: "DELETE" });
    } else {
      await api("/api/yoto/client-id", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: $("#clientIdInput").value.trim() }),
      });
    }
  } catch (e) {
    // Leave the value intact so nothing the user pasted is lost.
    closeClientIdConfirm(false);
    clientIdMsg("err", "We couldn’t save that. Please try again.");
    $("#clientIdInput").focus();
    return;
  }

  $("#clientIdInput").value = "";
  // Resets #2 and #3. The value just changed, so continuing to display the
  // previous revealed string would be actively wrong; and if the source became
  // "builtin" the block is removed entirely. Set BEFORE refreshStatus(), because
  // closeClientIdConfirm() below re-renders.
  //
  // Deliberately NOT inside closeClientIdConfirm(): the failure path above calls
  // it too, and a save that failed changed nothing to collapse the reveal for.
  clientIdRevealed = false;
  await refreshStatus();
  closeClientIdConfirm(false);
  // Both actions signed the user out on the server, so re-render the account
  // section above — it has already flipped to "Not connected yet".
  await checkAccount();
  clientIdMsg("ok", kind === "reset"
    ? "Done — back to the built-in Client ID. Now sign in to Yoto again using the button above."
    : "Saved. Now sign in to Yoto again using the button above.");
  $("#clientIdMsg").focus();
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
let connectTimer = null;

async function connectYoto() {
  clearError($("#sendError"));
  try {
    const { url } = await api("/api/yoto/login");
    window.open(url, "_blank");
    // Bounded poll. The previous version cleared the interval only on success,
    // so a sign-in the user closed or cancelled polled /api/status forever until
    // the page was reloaded.
    if (connectTimer) { clearInterval(connectTimer); connectTimer = null; }
    const deadline = Date.now() + SIGNIN_MAX_MS;
    connectTimer = setInterval(async () => {
      if (Date.now() > deadline) { clearInterval(connectTimer); connectTimer = null; return; }
      try { await refreshStatus(); } catch (_) { return; }
      if (STATUS.yoto.connected) { clearInterval(connectTimer); connectTimer = null; }
    }, SIGNIN_POLL_MS);
  } catch (e) {
    if (connectTimer) { clearInterval(connectTimer); connectTimer = null; }
    showError($("#sendError"), SIGNIN_ERRORS[e.data && e.data.reason] || e.message);
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
  // Settings entry points. All three route through gotoSettings() so the
  // element to return focus to on exit is recorded in one place.
  $("#advToggle").addEventListener("click", (e) => { e.preventDefault(); gotoSettings(e.currentTarget); });
  $("#settingsLink").addEventListener("click", (e) => { e.preventDefault(); gotoSettings(e.currentTarget); });
  $("#settingsBack").addEventListener("click", leaveSettings);
  window.addEventListener("hashchange", applyRoute);

  // Account setting. not_connected skips the confirmation entirely — there is
  // nothing to forget, so the button goes straight to Yoto.
  $("#accountPrimary").addEventListener("click", () => {
    if (ACCOUNT.state === "not_connected") startSignIn();
    else openAccountConfirm();
  });
  $("#accountConfirmNo").addEventListener("click", () => closeAccountConfirm());
  $("#accountConfirmYes").addEventListener("click", () => {
    closeAccountConfirm(false);
    startSignIn();
  });
  $("#accountCancel").addEventListener("click", cancelSignIn);
  registerSetting({
    onOpen: checkAccount,
    onClose: () => {
      stopSignInPoll();
      // Clear stale feedback: without this, leaving after a save and coming
      // back leaves an old success message sitting under a fresh "Checking…".
      clearError($("#accountMsg"));
    },
    confirm: $("#accountConfirm"),
    closeConfirm: closeAccountConfirm,
  });

  // Client ID setting.
  const trySave = () => {
    const cid = $("#clientIdInput").value.trim();
    if (!cid) {
      // Never confirm a no-op.
      clientIdMsg("err", "Please paste a Client ID first.");
      $("#clientIdInput").focus();
      return;
    }
    const { verdict, reason } = clientIdVerdict(cid);
    if (verdict === "invalid") {
      // Never confirm a refusal, either — the same rule, extended.
      // Focus and input handling mirror interactions.md §3.2 exactly: show the
      // message, focus the input, LEAVE THE VALUE INTACT so nothing she pasted
      // is lost, open no confirmation, touch neither the value display nor the
      // actions. Select-all on focus was considered and rejected — her first
      // job here is to READ what she typed and recognise it.
      const body = CLIENT_ID_REFUSAL[reason] || CLIENT_ID_REFUSAL._default;
      clientIdMsg("err", body.concat(clientIdReassurance()));
      $("#clientIdInput").focus();
      return;
    }
    openClientIdConfirm("save", verdict === "unusual");
  };
  $("#clientIdSave").addEventListener("click", trySave);
  $("#clientIdInput").addEventListener("keydown", (e) => { if (e.key === "Enter") trySave(); });
  $("#clientIdReset").addEventListener("click", () => openClientIdConfirm("reset"));
  $("#clientIdReveal").addEventListener("click", toggleClientIdReveal);
  $("#clientIdConfirmNo").addEventListener("click", () => closeClientIdConfirm());
  $("#clientIdConfirmYes").addEventListener("click", () =>
    submitClientId($("#clientIdConfirm").dataset.kind));
  registerSetting({
    // Reset #1: a fresh view starts in its default state, consistent with the
    // existing scrollTo(0,0) and account re-check. It lives HERE and not inside
    // renderClientId(), which also runs on confirmation-cancel — see the comment
    // on clientIdRevealed.
    onOpen: () => { clientIdRevealed = false; renderClientId(); },
    onClose: () => clearError($("#clientIdMsg")),
    confirm: $("#clientIdConfirm"),
    closeConfirm: closeClientIdConfirm,
  });

  // Fails loudly in the console if a future .setting-confirm forgets to
  // register. Runs after every section above has registered.
  auditSettingConfirms();
  // About popup
  const about = $("#aboutOverlay");
  $("#aboutLink").addEventListener("click", (e) => { e.preventDefault(); show(about, true); });
  $("#aboutClose").addEventListener("click", () => show(about, false));
  about.addEventListener("click", (e) => { if (e.target === about) show(about, false); });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    show(about, false);
    if (!inSettings()) return;
    // Inside settings, Escape does exactly one thing: dismiss an open
    // confirmation. Anywhere else on this surface it does nothing. Driven off
    // the section registry, so a new setting's confirmation is covered the
    // moment it registers — no edit here.
    closeOpenConfirms();
  });
  $("#connectBtn").addEventListener("click", connectYoto);
  // The pill now always goes to Settings. It used to be a dead click whenever
  // the user was connected — and a user whose upload just failed looks for the
  // one thing on screen that talks about her Yoto connection, so following the
  // symptom lands her exactly where the fix is.
  $("#yotoPill").addEventListener("click", (e) => gotoSettings(e.currentTarget));
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
