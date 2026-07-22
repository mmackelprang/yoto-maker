# ADR — Move `/api/tracks/file` onto the background job system

**Date:** 2026-07-21
**Status:** proposed — needs Mark's approval before Planner picks it up
**Escalated by:** Designer, during
[`2026-07-21-client-id-validation-and-multi-file-upload-design.md`](../../superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md)
§B.3.4.6 — *"This is an architecture decision, not mine to make."*

**Decision in one line:** Do it, in **three PRs, after Item B ships** — and ask
Planner to build three named seams into Item B *now* so the rework is ~15–20% of
its client code touched and **nothing thrown away**.

---

## 1. Context

### 1.1 What `/api/tracks/file` does today

`add_file` (`yoto_maker/server/app.py:278-296`) is fully synchronous inside one
held-open HTTP request:

```python
dest.write_bytes(await file.read())        # whole upload into RAM, then to disk
result = adapter.fetch(str(dest), work_dir) # copies AGAIN, probes, reads tags
added = _add_result_as_tracks(result, "file")  # split_audio() + probe per part
return {"count": len(added), "track": ...}
```

Two facts about this that are load-bearing for everything below, and one
correction to the framing this ADR was handed.

**Correction: the file path does not transcode.** `AudioFileAdapter.fetch`
(`sources/audiofile.py:26-61`) does `shutil.copy2` + `ffprobe` + a mutagen tag
read. No encoding happens. The only ffmpeg *encode* on this path is
`split_audio`'s **fallback** branch (`audio/normalize.py:244`), reached only when
the file is over 50 minutes **and** stream-copy segmentation produced nothing.
The common long-file case takes the `-c copy` branch at line 241, which is
I/O-bound, not CPU-bound.

This matters because it relocates the multi-minute cost. It is **not** compute we
can meaningfully report a percentage against. It is bytes moving.

**The bytes, counted.** A three-hour audiobook at 192 kbps CBR is ~260 MB. Today
that file is written to disk **twice** before splitting — once by `write_bytes` to
`work_dir/uploads/`, then again by `adapter.fetch`'s `copy2` to `work_dir/`,
because `uploads/x.mp3` and `x.mp3` do not resolve equal so the in-place shortcut
at `audiofile.py:41` never fires.

| | Bytes written | Bytes read | Peak RAM |
| --- | --- | --- | --- |
| **Today** | ~780 MB | ~520 MB | **~260 MB** (`await file.read()` returns one `bytes`) |
| Chunked write, redundant copy removed | ~520 MB | ~260 MB | ~1 MB |

~40% of the total I/O on the slowest path in the app is a copy that exists only
because two functions each chose their own destination directory. On a machine
with real-time antivirus scanning every write, that copy is a meaningful share of
the wait Mark observed.

### 1.2 The reference pattern — what the job system actually is

`server/jobs.py` is 87 lines. `JobManager.start(target)` runs `target(update)` on
a `daemon=True` thread, returns a hex id; `update(stage, percent, message)`
mutates the `Job`; the client polls `GET /api/jobs/{id}` via `pollJob()`
(`app.js:36-44`) every 500 ms until `status` is `done` or `error`.

Three endpoints use it: `/api/tracks/youtube`, `/api/send`, `/api/update/apply`.

**What it does not have, and every one of these is in scope below:**

| Missing | Consequence for this arc |
| --- | --- |
| **Any cancellation** | No token, no `cancelled` status, no cancel route. Exact cancel is entirely new mechanism. |
| **Any error classification** | `job.error` is a bare string. No status code, no reason. Item B's classifier is blind to it — see §4.3. |
| **Any eviction** | `self._jobs` is an unbounded dict. A 12-file batch plus two retry rounds is ~16 permanent entries per session. |
| **A lock on `get()`** | Harmless in CPython today; worth noting, not worth a PR. |
| **Any persistence** | Correct, and it must stay that way — see §5.4. |

### 1.3 Why cancel cannot be exact today

Designer's reading (§B.3.4.6) is correct and I confirm it: between
`await file.read()` and `return` there is **no `await`**. `adapter.fetch` and
`_add_result_as_tracks` are synchronous calls in an `async def`, so they run on
the event loop thread and asyncio cancellation has nowhere to land. A client
abort during that window abandons the response and changes nothing else. The work
completes, `draft.add_track()` runs, and the track appears in her list some
seconds later.

Two corollaries, both already in the spec and both correct:

- `add_track` is the **last** statement, so no half-made track is ever registered
  and no cleanup path is needed today.
- Abort during `await file.read()` *does* prevent the file, because `write_bytes`
  never runs.

The visible cost is one sentence Designer had to write:

> *The one that was still going may still finish — it'll turn up in your list if
> it does.*

Deleting that sentence is the clearest single success criterion for this arc.

### 1.4 The fake bar, and what would actually replace it

`addFile()` sets `#addBar` to a fixed `40%` (`app.js:911`). Item B upgrades it to
`(completed / total) × 100` for a batch, which is honest but coarse, and leaves
`n = 1` at 40%.

**The uncomfortable finding, stated plainly because a differently-fake bar is not
an improvement:**

For a file **under 50 minutes** — the overwhelmingly common case — `split_audio`
probes, sees `duration_s <= max_seconds + 1`, and returns `[input_path]`
immediately (`normalize.py:208-209`). There is no long work for a job to report.
Essentially the entire elapsed time is the **upload leg**: the browser pushing
bytes into `await file.read()`.

So moving to the job system, *by itself*, gives the common case a progress bar
that sits at zero for the whole wait and then jumps to 100 in under a second. It
is accurate and it is useless. The fake 40% would be retired and replaced by
something no better.

**Real progress on the file path is two separate mechanisms, and only one of them
is the job system:**

| Leg | Who can report it | Mechanism |
| --- | --- | --- |
| **Upload** (dominant for < 50 min files) | **The browser only** | `fetch()` has no upload-progress event. Requires `XMLHttpRequest` + `upload.onprogress`. The server cannot help — the job does not exist yet. |
| **Split / re-encode** (dominant for audiobooks) | **The job** | ffmpeg `-progress pipe:1 -nostats` emits `out_time_us=`; we already know total duration from the probe, so the percentage is genuinely well-founded. |
| Copy, probe, tag read | The job | Chunked `copyfileobj` with a callback; part *k* of *n*. |

That split is why this is three PRs rather than one, and why the PR that actually
satisfies "retire the fake bar" for most users is the *last* one and touches no
server code at all.

### 1.5 Version skew — the frozen .exe question

Checked, and the answer is reassuring. `index()` (`app.py:680-706`) serves
`index.html` with `Cache-Control: no-store` and stamps `?v=__version__` onto
`app.js` and `styles.css`; the static middleware (`app.py:72-93`) adds
`no-cache` so every reuse revalidates. Both guards exist *because* a v0.1.8
`app.js` survived the update to v0.1.9 and made Settings unreachable.

The decisive structural fact: **there is no independently-versioned client.** The
browser is served by the same process that serves the API. A user cannot be
running client v0.1.11 against server v0.1.12. The only skew window is **one
browser tab held open across an in-place update**, which the `?v=` stamp closes on
its next document load.

And the degradation in that window is mild rather than destructive: an old
`app.js` doing `await api(POST)` then `refreshDraft()` would receive `{job_id}`,
refresh too early, and show nothing — then the track would appear on her next
interaction. No data loss, no error, no orphan.

**Conclusion: no compatibility shim. Do not keep a synchronous form of the
endpoint.** Preserving it would double this surface permanently to protect a
window measured in one page reload, and it is exactly the "second async idiom"
this ADR was told to avoid inventing.

---

## 2. Options considered

**Option 1 — Do nothing.** Ship Item B on the synchronous contract and leave it.
Costs: the hedging sentence stays; cancel remains inexact forever; the 40% bar
stays fake for `n = 1`; the double-write stays; a 260 MB RAM spike per audiobook
stays. Rejected — but note it is *survivable*, which is why the arc is not urgent
and can wait for Item B.

**Option 2 — Job-ify everything in one PR** (contract + cancel + both progress
mechanisms). Rejected. It lands an endpoint contract change, a `subprocess`
lifecycle rewrite in a module three call paths share (`normalize.py::_run` is used
by `probe_audio`, `normalize_to_mp3` *and* `split_audio`), a new cancel protocol,
and an XHR rewrite, all in one reviewable unit. The first bug found would be in an
unbisectable diff.

**Option 3 — Keep both a sync and an async endpoint** for a release. Rejected in
§1.5. There is no independent client to be compatible with.

**Option 4 — Delay Item B and do this first.** Rejected. Item B is designed and in
planning now; it delivers user-facing value; its own spec states it *"ships
correctly without it."* Blocking a shipped feature on an internal refactor to save
a rework cost measured in §4 as ~15–20% of one file is a bad trade.

**Option 5 (recommended) — Three sequenced PRs after Item B, with three seams
built into Item B now.** §3.

---

## 3. Decision

### Do it. Three PRs, in this order, starting after Item B has shipped and had one UAT round.

And **before that** — while Item B is still being planned — build three seams into
it. They are good code on their own terms and they are what turns this from a
rewrite into an edit.

### 3.0 The three seams (belong to Item B, not to this arc)

| Seam | What Planner does in Item B | Why |
| --- | --- | --- |
| **S1. One upload call site** | Put the single-file POST behind `uploadOneFile(file, { signal, onProgress })`. The batch loop, the retry round and the `n = 1` path all call it. | PR A then rewrites **one function body** instead of hunting call sites. Good structure regardless. |
| **S2. Classifier reads the server's tag first** | §B.3.1.1 already specifies *"the server's own tag wins when present"* (`err.data.reason`). Build that branch on day one even though nothing emits it yet. | It is the entire compatibility hook for §4.3. Without it, PR A silently regresses success criterion 12. |
| **S3. One progress setter** | Route every `#addBar` / `#addMsg` write through `setAddProgress(pct, msg)`. Do not inline `"40%"`. | PR A and PR C both change what feeds the bar and neither should touch the batch loop to do it. |

These cost Item B perhaps thirty minutes and they are the difference between the
answer in §4 and a much worse one.

### 3.1 PR A — move the endpoint onto a job

**Contract change.** `POST /api/tracks/file` returns `{"job_id": "..."}`, matching
`/api/tracks/youtube` exactly. The `{count, track}` payload moves to `job.result`
unchanged, so `pollJob()` returns the same object the POST used to.

**What stays synchronous in the request handler, and why this is not negotiable:**

1. **The upload read.** Starlette's `UploadFile` wraps a `SpooledTemporaryFile`
   that is closed when the request completes. It cannot be handed to a background
   thread that outlives the response. The endpoint **must** drain the body before
   returning.
2. **The filename sanitization** (`Path(file.filename).name`) and the
   **`can_handle` extension check.** Both are microseconds, and keeping the format
   rejection synchronous means an unsupported file still returns a **400 with the
   server's plain-language sentence** — which is what keeps Item B's deterministic
   classification working with zero client change.

So the honest version of Designer's phrase: the request is freed **after the
upload leg**, not "instantly." For a 260 MB file over loopback that is seconds,
not minutes. The multi-minute part is what moves.

**Shape:**

```python
@app.post("/api/tracks/file")
async def add_file(file: UploadFile) -> dict:
    safe_name = Path(file.filename or "audio").name or "audio"
    adapter = AudioFileAdapter()
    if not adapter.can_handle(safe_name):          # 400, verbatim, synchronous
        raise SourceError("That file type isn't supported. Try an MP3, M4A or WAV file.")

    dest = get_config().work_dir / safe_name        # NOT work_dir/uploads — see below
    await run_in_threadpool(_stream_to_disk, file, dest)   # chunked, ~1 MB RAM

    def work(update):
        update("read", 10, "Checking the audio…")
        result = adapter.fetch(str(dest), cfg.work_dir)     # now a no-op copy
        update("split", 30, "Getting it ready…")
        added = _add_result_as_tracks(result, "file", on_progress=update)
        return {"count": len(added), "track": added[0].view() if added else None}

    return {"job_id": get_jobs().start(work)}
```

**Two included fixes that are the reason PR A pays for itself even before cancel
and progress land:**

- **Write the upload where the adapter wants it** (`work_dir/`, not
  `work_dir/uploads/`), so `audiofile.py:41`'s in-place shortcut fires and the
  second 260 MB copy disappears. Keep the `Path(...).name` sanitization exactly as
  it is — the traversal defense must not move.
- **Chunked `copyfileobj` instead of `await file.read()`** — peak RAM 260 MB → ~1 MB.

Per §1.1's table: **~40% of the I/O on this path, and ~99.6% of its peak memory,
removed by PR A alone.**

**`Job` gains two fields, and they are the compatibility contract with Item B:**

```python
reason: str | None = None        # "unsupported_format", "disk_full", "ffmpeg_failed", …
retryable: bool | None = None    # None = unknown → client's transient default (§B.3.1.2)
```

`pollJob()` attaches both to the `Error` it throws, so Item B's classifier — via
seam S2 — reads `err.data.reason` exactly as it already does for sign-in errors at
`app.js:1033`. **No second error-mapping mechanism.**

**Client change, total:** the body of `uploadOneFile` (seam S1). Everything around
it is untouched.

**Delivers independently:** no multi-minute held connection; the event loop stays
free (today a long split blocks *every* other request, including `/api/status`);
40% less disk I/O; the RAM spike gone; true stage messages. Ships without cancel
and without new progress.

### 3.2 PR B — exact cancel, and real progress for long files

These are one PR because they are **the same surgery on the same function**.

`normalize.py::_run` uses `subprocess.run(capture_output=True)`, which blocks
until exit and buffers output. Both cancel and `-progress` parsing require the
same change: `Popen`, read stdout line-by-line, and be able to kill the child.

```python
def _run(cmd, *, cancel: threading.Event | None = None,
         on_progress: Callable[[float], None] | None = None) -> CompletedProcess
```

- **Cancel**: poll `cancel` while the child runs; on set, `terminate()`, then
  `kill()` after a short grace; raise `Cancelled`.
- **Progress**: when `on_progress` is given, append `-progress pipe:1 -nostats`
  and parse `out_time_us=` against the duration we already probed. Real, not
  estimated.

`probe_audio` and `normalize_to_mp3` pass neither and behave exactly as today.

**Job system gains:**

| Addition | Note |
| --- | --- |
| `Job.cancel_event: threading.Event` | Passed into `work(update, cancel)`. |
| `status = "cancelled"` | **A third terminal state, not an error.** §B.3.4.3 says a cancel is not a failure; if it arrives as `status: "error"` the client will classify it transient and offer `Try again` for her own decision — the exact bug §B.3.4.2 fixes on the client side, reintroduced from the server. |
| `POST /api/jobs/{id}/cancel` | Idempotent. 404 unknown, 200 otherwise. Non-GET, so the origin guard covers it. |
| Eviction | Drop terminal jobs older than ~10 min, or cap at 50. Cheap; do it here. |
| Cleanup on cancel | **New requirement.** A killed ffmpeg leaves partial `*_partNNN.mp3` files in `work_dir/parts/`. Today this cannot happen. Unlink on the cancelled path. |

**Client change:** the cancel handler gains a second branch — abort the
`AbortController` if still in the upload leg, `POST .../cancel` and await the job
reaching `cancelled` if past it. The `Stopping…` state (§B.5) becomes real rather
than cosmetic.

**Delivers independently:** success criterion 14 becomes true in the strong sense.
**The hedging sentence in §B.3.4.6 is deleted**, and the cancelled-summary's
uncertainty case goes with it. Long files get a genuine percentage.

### 3.3 PR C — real progress for the common case

Client-only. Replace `fetch` with `XMLHttpRequest` inside `uploadOneFile` (seam
S1 again) to get `upload.onprogress`, and feed it through `setAddProgress` (seam
S3) as the first 0–60% of a file's share of the bar, with the job's percentage as
the remaining 40%.

This is the PR that actually retires the fake bar for a user adding a normal
20-minute file, because §1.4 established that her entire wait is the upload leg.

**Genuinely deferrable.** If it never ships, PR A + PR B still leave the bar
honest-but-coarse (`completed / total`, exactly Item B's design) rather than fake.
XHR is a step backwards in ergonomics from `fetch` and it is worth being sure the
progress is wanted before taking it — this is the one PR in the arc that could be
cut and leave the system coherent.

---

## 4. The central question: what happens to Item B's client code?

The instruction was to be concrete and not soften this. Here it is.

### 4.1 Verdict per piece

| Item B piece | Verdict | Cost |
| --- | --- | --- |
| Natural sort (`Intl.Collator`, §B.1.1) | **Unchanged** | 0 |
| Sequential-upload loop and its rationale (§B.1.2) | **Unchanged** | 0 — the *reason* (`_add_result_as_tracks` appends) is untouched |
| Disabling `#filePick` / `#ytAdd`, re-enable in `finally` | **Unchanged** | 0 |
| Client-side non-audio pre-check (§B.3.2) | **Unchanged** | 0 |
| Grouped error box: summary line, two groups, headings, arity rules, all copy (§B.3.3) | **Unchanged** | 0 — except **one sentence deleted** |
| One `Try again` per group, re-entering the batch flow (§B.3.1.3–4) | **Unchanged** | 0 — held `File` objects still work |
| Reorder repair after a successful retry (§B.3.1.5) | **Unchanged** | ~2 lines — `count` moves from the POST response to `job.result`, same field |
| `AbortError` branch in `api()` (§B.3.4.2) | **Unchanged, and still required** | 0 — still the only thing preventing criterion 16 |
| Keep completed tracks on cancel (§B.3.4.4); never reorder after cancel (§B.3.4.5) | **Unchanged** | 0 |
| All a11y: `role="status"`, `role="alert"`, `tabindex="-1"`, focus rules (§B.6) | **Unchanged** | 0 |
| **The upload call itself** | **Rewritten** | ~10 lines, confined to `uploadOneFile` by seam S1 |
| **Progress bar feed** | **Extended** | ~3 lines with seam S3; the `(completed/total)` formula survives as the outer term |
| **Failure classification (§B.3.1.1)** | **Structure survives, plumbing rewritten** | see §4.3 |
| **Cancel (§B.3.4)** | **Survives + gains a second branch** | see §4.4 |

### 4.2 The number

**~15–20% of Item B's client code is touched. Approximately none of it is thrown
away.** The largest single change is *additive*: the job-cancel branch, ~30–50
lines that sit alongside the AbortController path rather than replacing it.

The bulk of Item B's complexity — batching, grouping, classification policy, retry
semantics, ordering repair, copy, accessibility — is endpoint-agnostic. It
describes *what the user is told and what the controls mean*, and none of that
depends on whether the server answered in one response or two.

**One string is deleted:** *"The one that was still going may still finish — it'll
turn up in your list if it does."* That is the intended outcome of the arc, not a
casualty of it.

### 4.3 The one place there is genuine, non-obvious rework

`pollJob()` throws `new Error(job.error || "Something went wrong.")`
(`app.js:41`) — **a bare string with no `.status` and no `.data`.**

Item B's classification table (§B.3.1.1) is driven by `err.status`. After PR A,
every failure *after* the upload leg arrives through `pollJob`, so `.status` is
`undefined`, which the table reads as *fetch rejected* → **transient** → offers
`Try again`.

**Concretely: a file the server rejects for a real, permanent reason would get a
retry button that reliably fails — the exact thing §B.3.1's principle forbids, and
a direct regression of success criterion 12.**

This is the finding the maintainer would rather have now than later. Two things
defuse it, and both are already in the design:

1. **Seam S2.** §B.3.1.1 already declares *"the server's own tag wins when
   present"* and nominates `err.data.reason`. Build that branch during Item B and
   PR A simply starts populating it.
2. **Keeping the format check synchronous** (§3.1). The most common deterministic
   failure by far — she selected `cover.jpg` — never enters a job at all. It stays
   a 400 with the server's verbatim sentence, on the path Item B already handles.

With those, the classifier's *table* survives intact and only its *inputs* change.
Without seam S2, PR A carries a silent correctness regression that no test in the
repo would catch, because **there are currently no tests for `jobs.py` at all.**

### 4.4 Cancel: the honest accounting

Cancel is the piece that changes most, and it is worth being precise about how.

- The AbortController **still governs the upload leg** and is still the right
  mechanism there. It is not replaced.
- A cancel *after* the upload completes becomes a different call —
  `POST /api/jobs/{id}/cancel` — and waits for `status: "cancelled"`.
- So the handler goes from one mechanism to two, keyed on which phase is live.

Roughly **60% survives, 40% is new code added alongside. Nothing is deleted.**

### 4.5 Does the client get simpler? No.

Stated plainly because the opposite would be an easy thing to assume: **the client
gets slightly more complex, and more correct.** One `await` becomes POST-then-poll.
One cancel mechanism becomes two. Anyone claiming the job system simplifies this
client is wrong.

What *does* get simpler is the **copy and the user's model**: the hedge is gone,
the cancelled summary states a definite outcome, and there is no longer a class of
file whose fate is unknown to the app that is processing it.

### 4.6 Does it need a second polling-shaped variant alongside? No.

One flow. §1.5 establishes there is no independent client to stay compatible with,
so a parallel synchronous path would exist only to serve a browser tab that has not
reloaded. It would double the surface permanently and would be the second async
idiom this ADR was explicitly told not to invent.

---

## 5. Consequences

### 5.1 Good

- No held connection. Today a 3-hour split blocks the **event loop**, so
  `/api/status`, `/api/draft` and every other route are unserved for the duration —
  the app appears frozen, not merely slow. PR A fixes that for every endpoint at
  once.
- ~40% of the I/O and ~99.6% of the peak RAM on the slowest path removed (§1.1).
- Cancel becomes exact; the hedging sentence is deleted.
- One idiom for slow work. Four endpoints, one shape, one `pollJob`.
- `jobs.py` gains cancellation, terminal-state richness and eviction — reusable by
  `/api/send` and `/api/tracks/youtube` afterwards.

### 5.2 Bad — failure modes that are impossible today and become possible

This is the section that matters most.

1. **Partial files on disk after a cancel.** Today ffmpeg always runs to
   completion, so `parts/` never holds a fragment. Killing it mid-segment leaves
   `*_partNNN.mp3` stubs. **PR B must unlink them** — and note `split_audio`
   already has a "drop segments under 1 s" filter (`normalize.py:229-237`) that a
   partial file could slip past, since a killed 40-minute segment is not short.
2. **A job that outlives the page that started it.** The `job_id` lives only in a
   JS variable. Reload the tab and the job keeps running and keeps calling
   `add_track` into a draft the UI is no longer watching. Today the equivalent is
   an abandoned request that *also* completes — so this is not new in substance,
   but the job system makes it **look** durable when it is not.
3. **A job that does not survive an app restart, while appearing to.** Threads are
   `daemon=True`; quitting from the tray kills them mid-write. The client then
   polls a `job_id` that 404s. Today the browser sees the connection drop, which is
   at least legible. **PR A must map a 404 from `/api/jobs/{id}` to a clear
   "Yoto Maker restarted" message, not to the generic transient branch.**
4. **Unbounded job accumulation.** 12 files + retries ≈ 16 entries per batch, each
   holding a `result` dict, never evicted. Small in absolute terms; still a leak in
   a process designed to run for weeks in the tray. Eviction is in PR B.
5. **Two error surfaces instead of one** — §4.3.
6. **A killed ffmpeg's exit code is indistinguishable from a crash** unless the
   cancel path is checked *first*. Get that backwards and a user's own cancel is
   reported to her as *"We couldn't split that long audio file into parts."*

### 5.3 Neutral, worth stating

The **200-file draft problem is unchanged**. Everything still lands in one global
in-memory `DraftCard` (`server/draft.py:118`). This arc does not touch that and
should not.

### 5.4 Explicitly rejected: persisting jobs

Do not add job persistence, and do not let a future PR add it casually.

`_draft` is a module-level global that dies with the process. A job that survived a
restart would complete and `add_track` into a **fresh, empty draft** — the user's
other tracks gone, one mystery track present. That is strictly worse than losing
the job. **Job lifetime must not exceed draft lifetime**, and the draft is
in-memory by design (`draft.py:1-5`).

If drafts ever become persistent, revisit this — as a new ADR, not an amendment.

---

## 6. Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Silent classification regression (§4.3) | **High** — no test would catch it; `jobs.py` has zero test coverage | Seam S2 in Item B; keep the format check synchronous; **add `tests/test_jobs.py` in PR A** covering `reason` / `retryable` / cancelled propagation |
| `_run` Popen rewrite regresses `probe_audio` or `normalize_to_mp3` | **Medium** — three call paths share it, and `probe_audio` runs on nearly every request | Default both new kwargs to `None` and assert byte-identical behavior when unset; `tests/test_audio_images_labels.py` already exercises real ffmpeg |
| Cancel reported to the user as a crash | Medium | `cancelled` as a distinct terminal state, checked before the returncode branch |
| Partial segments treated as valid tracks | Medium | Unlink on the cancelled path; do not rely on the 1-second filter |
| Tab reload orphans a job | Low–Medium | Accept for now; log it. A `GET /api/jobs?active=1` reattachment endpoint is a possible future PR, deliberately out of scope here |
| PR C's XHR rewrite regresses the abort path | Medium | XHR has its own `abort()`; PR C must be sequenced **after** PR B so cancel is settled first |
| Scope creep into `/api/send` and `/api/tracks/youtube` | Medium | They *gain* cancellability from PR B's mechanism but **wiring them is not in this arc**. `yt_dlp` is a library call, not a subprocess we own, and killing it mid-download is a different problem. |

---

## 7. UX implications — flagged, not specified

Designer owns all of these. Naming them so they are not discovered during
implementation:

1. **The deleted sentence** (§B.3.4.6) and the cancelled summary that replaces it.
2. **`Stopping…` becomes a real state with a real duration** — up to a few seconds
   while ffmpeg is killed. §B.5 already specifies it; it now needs to hold longer.
3. **A new failure state: "the app restarted while your file was being added"** —
   consequence 5.2.3, which has no copy today.
4. **What the bar shows after PR A but before PR C** — for a short file it will sit
   near zero and then complete. Item B's `(completed / total)` batch formula covers
   the batch case; the `n = 1` case may look worse than the fake 40% until PR C.
   **This is the one place PR A could feel like a regression**, and it deserves a
   Designer decision rather than an implementer's guess.
5. **Whether progress is wanted enough to justify PR C's XHR rewrite** at all.

---

## 8. Related

- **Spec:** [`docs/superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md`](../../superpowers/specs/2026-07-21-client-id-validation-and-multi-file-upload-design.md)
  — Item B §B.2, §B.3.1.1, §B.3.4, §B.5, §B.6. §B.3.4.6 is the escalation this ADR answers.
- **System overview:** [`docs/DESIGN.md`](../../DESIGN.md) §3. Its data-flow line
  needs no change; §6's "honest progress" claim becomes true of the file path once
  PR C lands.
- **Cache/versioning precedent:** `app.py:72-93` and `app.py:680-706` —
  the reasoning §1.5 relies on, and `tests/test_static_cache.py`.
- **Prior art in-tree:** `/api/tracks/youtube` (`app.py:248-275`), `/api/send`
  (`app.py:589-619`), `pollJob` (`app.js:36-44`).

---

## 9. Open questions

1. **Does PR C ship at all?** (§3.3, §7.5.) It is the only PR whose value is not
   self-evident, and it is the only one that touches `fetch` → `XHR`. **Mark
   decides**; the arc is coherent with A + B alone.
2. **Is the short-file bar acceptable between PR A and PR C?** (§7.4.) A bar that
   sits at zero then jumps may read worse than today's fake 40%. **Designer
   decides** — possible answers include keeping an indeterminate style during the
   upload leg, which needs no new mechanism.
3. **Should the two other job endpoints be wired to cancel in this arc?**
   Recommendation: **no** — PR B builds the mechanism, a later PR spends it, and
   `yt_dlp`'s cancellability needs its own look. **Mark decides.**
4. **Job reattachment after a tab reload** (§5.2.2). Out of scope; worth a queue
   row of its own if it is ever observed in practice.
</content>
</invoke>
