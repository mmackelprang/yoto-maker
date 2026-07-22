"""Item B's frontend contract, as static assertions.

The live-behaviour half — a real batch, a real network kill, a real cancel
during a real transcode — is in the plan's Test Plan §F-§J and cannot be
asserted here. What can be asserted here is the set of decisions that regress
silently under a well-meaning refactor.
"""
from __future__ import annotations

import pytest

from yoto_maker.server.app import STATIC_DIR


@pytest.fixture(scope="module")
def index_html() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (STATIC_DIR / "app.js").read_text(encoding="utf-8")


def test_only_the_audio_input_is_multiple(index_html):
    """#picUploadInput stays single-select. Named in the brief and restated in
    the spec so nobody 'finishes the job'."""
    audio = index_html[index_html.index('id="fileInput"'):]
    audio = audio[:audio.index(">") + 1]
    assert " multiple" in audio

    pic = index_html[index_html.index('id="picUploadInput"'):]
    pic = pic[:pic.index(">") + 1]
    assert "multiple" not in pic


def test_the_button_says_files_plural(index_html):
    """The plural is what ADVERTISES the feature — overview.md §12.2's lesson.
    'Choose an audio file' states the opposite of the new capability."""
    assert "📁 Choose audio files" in index_html
    assert "📁 Choose an audio file" not in index_html


def test_the_ordering_promise_is_on_screen_before_she_picks(index_html):
    """Natural sort is only SAFE because tracks can be reordered afterwards, and
    that safety is only real if she knows it. Rejected: a title attribute
    (invisible to scanning and touch) and showing it after the batch (a promise
    has to precede the action it governs)."""
    assert "You can pick more than one. They go in order by file name, and you can move them around afterwards." in index_html


def test_api_rethrows_abort_error_before_the_network_message(app_js):
    """Without this, the user's own cancel is reported as a network failure AND
    offered a Try again button, because the classifier reads a missing .status
    as transient. spec §B.3.4.2 — the one change without which cancel actively
    misinforms."""
    fn = app_js[app_js.index("async function api(") : app_js.index("function show(")]
    assert 'if (e && e.name === "AbortError") throw e;' in fn
    # (reconciliation) Anchor both ends to the actual CODE lines, not the prose:
    # the plan's Task 11 comment legitimately quotes the network message, so the
    # bare .index("Couldn't reach...") the plan used finds that comment (which
    # precedes the AbortError text) and mis-reads the order. The behavioral
    # guarantee — the AbortError re-throw runs before the network-error throw —
    # is asserted directly. See final report.
    assert (fn.index('if (e && e.name === "AbortError") throw e;')
            < fn.index("throw new Error("))


def test_the_sort_uses_the_platform_collator(app_js):
    """Do NOT hand-roll digit-run splitting. It is the obvious implementation,
    it is what gets written, and it gets 07-vs-7, unicode digits and case wrong
    in ways that only show up on a user's machine."""
    assert 'new Intl.Collator(undefined, { numeric: true, sensitivity: "base" })' in app_js


def test_the_precheck_reads_the_accept_attribute(app_js):
    """One list, and it cannot drift."""
    fn = app_js[app_js.index("function isProbablyAudio") : app_js.index("let BATCH")]
    assert 'getAttribute("accept")' in fn
    assert ".mp3" not in fn, "the extension list was restated in JS"


def test_uploads_are_sequential_and_lock_both_pickers(app_js):
    """A correctness decision, not a performance one: the server appends, so
    parallel uploads would land in nondeterministic order and destroy the
    ordering this feature promised."""
    fn = app_js[app_js.index("async function runBatch") : app_js.index("function newTrackIds")]
    assert "Promise.all" not in fn
    assert '$("#filePick").disabled = true;' in fn
    assert '$("#ytAdd").disabled = true;' in fn


def test_a_cancelled_batch_never_reorders(app_js):
    """The reorder sends a FULL order array. After a cancel, files that never
    arrived have no ids, so it would permute real tracks against positions that
    do not exist."""
    fn = app_js[app_js.index("async function repairOrderIfNeeded") : app_js.index("$(\"#addCancel\").addEventListener")]
    assert "if (b.cancelled) return;" in fn
    assert "if (!b.repaired) return;" in fn


def test_the_reorder_sorts_groups_not_tracks(app_js):
    """One file becomes one OR MORE tracks — split_audio cuts at 50 minutes. The
    parts must stay together and in part order."""
    fn = app_js[app_js.index("async function repairOrderIfNeeded") : app_js.index("$(\"#addCancel\").addEventListener")]
    assert "b.groups.get(file)" in fn
    assert "sortByFilename(b.ok)" in fn


def test_counts_are_files_never_tracks(app_js):
    """She picked FILES, and the part-splitting is pre-existing behaviour she has
    already met on the single-file path."""
    assert "files were added." in app_js
    assert "tracks were added" not in app_js
    assert "of your ${n} files" in app_js


def test_the_single_file_summary_is_untouched(app_js):
    """'1 of your 1 files were added.' is what a naive template produces and it
    is the failure mode this branch exists to prevent."""
    fn = app_js[app_js.index("function renderAddError") : app_js.index("async function retryTransient")]
    assert "} else if (n === 1) {" in fn


def test_unknown_failures_default_to_transient(app_js):
    """Guessing deterministic when it was transient TELLS HER TO CHANGE A FILE
    THAT IS FINE. That is wrong advice, not a slower path to the same place."""
    fn = app_js[app_js.index("function classifyUploadError") : app_js.index("function uploadReasonText")]
    assert fn.rstrip().rstrip("}").rstrip().endswith('return "transient";')


def test_a_cancelled_file_is_in_neither_failure_group(app_js):
    """She stopped on purpose. Classifying her decision as a failure and
    offering to retry it would blur Try again into meaning two things."""
    fn = app_js[app_js.index("async function runBatch") : app_js.index("function newTrackIds")]
    abort = fn[fn.index('e.name === "AbortError"'):]
    abort = abort[:abort.index("BATCH.failed.push")]
    assert "BATCH.cancelled = true;" in abort
    assert "continue;" in abort


def test_the_not_started_group_has_no_reason_and_no_button(app_js):
    """There is no reason beyond her own decision, and inventing one would read
    as blame."""
    assert "You stopped before this one:" in app_js
    assert "You stopped before these ${b.notStarted.length}:" in app_js
    assert "lines(b.notStarted, (f) => f.name);" in app_js


def test_the_in_flight_hedge_says_may(app_js):
    """Verified by observation: the transcode runs to completion after the
    abort, so the track lands. The sentence must keep saying 'may' — do not
    tighten it into a promise that it won't."""
    assert "The one that was still going may still finish — it’ll turn up in your list if it does." in app_js


def test_there_is_one_retry_button_and_it_is_disabled_not_removed(app_js):
    """Removing it destroys it while focused and focus falls to <body> — the
    single most common way a keyboard user gets lost in a flow like this."""
    assert 'btn.id = "addRetry"' in app_js
    assert "if (btn) btn.disabled = true;" in app_js
    assert app_js.count('btn.textContent = "Try again"') == 1


def test_the_add_regions_have_their_roles(index_html):
    assert 'id="addMsg" role="status"' in index_html
    assert 'id="addError" class="msg-box err hidden" role="alert" tabindex="-1"' in index_html


# --- the three job-system ADR seams (that arc is out of scope; these are not) ---

def test_seam_s1_there_is_one_upload_call_site(app_js):
    """uploadOneFile is the ONLY place POST /api/tracks/file is sent. The batch
    loop, the retry round and the n=1 path all route through it, so the eventual
    endpoint swap rewrites one function body and hunts no call sites."""
    assert "async function uploadOneFile(file, { signal, onProgress } = {})" in app_js
    # Exactly one POST to the file endpoint in the whole script, and it is inside
    # uploadOneFile. (The GET at /api/draft and the reorder POST are different
    # paths.)
    assert app_js.count('"/api/tracks/file"') == 1
    fn = app_js[app_js.index("async function uploadOneFile") : app_js.index("async function runBatch")]
    assert '"/api/tracks/file"' in fn
    # onProgress is the seam for PR C's XHR swap; it must survive being unused.
    assert "onProgress" in fn


def test_seam_s2_the_server_tag_beats_the_status_code(app_js):
    """The classifier consults e.data.reason / e.data.retryable BEFORE any status
    code. Without this, a future job-based failure — a bare error with no
    .status — misclassifies as transient and offers a retry that reliably fails,
    breaking success criterion 12 from the server side.

    Asserted structurally AND executably: the reason branch must appear before
    the first status read, and the precedence must actually hold.
    """
    fn = app_js[app_js.index("function classifyUploadError") : app_js.index("function uploadReasonText")]
    assert "if (d.reason)" in fn
    assert "if (d.retryable === true) return \"transient\";" in fn
    assert "if (d.retryable === false) return \"deterministic\";" in fn
    # The reason branch precedes the first status-code read.
    assert fn.index("if (d.reason)") < fn.index("const s = e && e.status;")


def test_seam_s2_precedence_holds_when_evaluated(tmp_path):
    """Extract classifyUploadError and run it under Node if available; otherwise
    assert the source guarantees the precedence. The behavior under test:
    {data:{reason:'x', retryable:false}, status:500} must be 'deterministic'
    (reason wins over a 5xx that status alone would call transient), and
    {data:{reason:'x', retryable:true}, status:400} must be 'transient'
    (reason wins over a 4xx that status alone would call deterministic).
    """
    import shutil
    import subprocess

    from yoto_maker.server.app import STATIC_DIR

    node = shutil.which("node")
    src = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    start = src.index("const UPLOAD_ERROR_CLASS")
    end = src.index("function uploadReasonText")
    snippet = src[start:end]

    if not node:
        # No Node in this environment — the structural test above is the guard,
        # and we still assert the two decisive lines exist in the right order.
        assert snippet.index("if (d.retryable === false)") < snippet.index("const s = e && e.status;")
        pytest.skip("node not available; precedence checked structurally")

    harness = tmp_path / "check.js"
    harness.write_text(
        snippet
        + """
const a = classifyUploadError({ data: { reason: "x", retryable: false }, status: 500 });
const b = classifyUploadError({ data: { reason: "x", retryable: true }, status: 400 });
const c = classifyUploadError({ status: 400 });          // no tag -> status wins
const d = classifyUploadError({});                        // unknown -> transient
if (a !== "deterministic") throw new Error("reason:false did not beat 500: " + a);
if (b !== "transient") throw new Error("reason:true did not beat 400: " + b);
if (c !== "deterministic") throw new Error("day-one 400 regressed: " + c);
if (d !== "transient") throw new Error("unknown default regressed: " + d);
console.log("ok");
""",
        encoding="utf-8",
    )
    out = subprocess.run([node, str(harness)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "ok" in out.stdout


def test_seam_s3_one_progress_setter(app_js):
    """Every #addBar / #addMsg write goes through setAddProgress. No inlined
    width strings at call sites in the batch code."""
    assert "function setAddProgress(pct, msg)" in app_js
    # The loop and the cancel handler call the setter, never write the bar
    # directly. (renderStatus/send flows have their own #sendBar and are
    # unrelated.) No literal "40%" survives as an inlined batch width.
    batch = app_js[app_js.index("async function runBatch") : app_js.index("async function retryTransient")]
    assert '$("#addBar").style.width' not in batch
    assert 'setAddProgress(' in batch


# --- pre-merge review fixes (Stack B): two regressions caught before merge -----

def test_the_batch_skip_guard_resets_per_invocation_not_the_sticky_flag(app_js):
    """Pre-merge HIGH. The loop's "skip remaining files" guard must read the
    per-invocation abort signal — a fresh AbortController is created at the top of
    every runBatch, including a retry re-entry, so it resets each call. Reading the
    sticky BATCH.cancelled (set on cancel, never cleared) would make a retry after
    ANY cancel re-enter with it still true and route every retried file to
    notStarted WITHOUT uploading it — a silent no-op of the retry (Test Plan §I.9).
    BATCH.cancelled stays sticky, but only for summary/reorder rendering."""
    fn = app_js[app_js.index("async function runBatch") : app_js.index("function newTrackIds")]
    assert "if (addAbort.signal.aborted) { BATCH.notStarted.push(file); continue; }" in fn
    # The old sticky-flag guard must be gone from the loop.
    assert "if (BATCH.cancelled) { BATCH.notStarted.push(file); continue; }" not in fn


def test_cancel_is_scoped_to_the_file_batch_not_youtube(index_html, app_js):
    """Pre-merge MEDIUM. #addCancel shares #addProgress with addYouTube(), which
    wires no AbortController — so a Cancel shown on the YouTube path is a dead
    button. It is hidden by default and revealed ONLY by runBatch(); addYouTube()
    never reveals it."""
    btn = index_html[index_html.index('id="addCancel"'):]
    btn = btn[:btn.index(">") + 1]
    assert "hidden" in btn, "#addCancel must be hidden by default"

    rb = app_js[app_js.index("async function runBatch") : app_js.index("function newTrackIds")]
    assert 'show($("#addCancel"), true)' in rb
    assert 'show($("#addCancel"), false)' in rb

    yt = app_js[app_js.index("async function addYouTube") : app_js.index("// ---- add audio: the batch")]
    assert '$("#addCancel")' not in yt, "addYouTube must not touch #addCancel"
