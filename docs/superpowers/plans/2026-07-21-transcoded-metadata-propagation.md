# Plan — Propagate Yoto's transcoded `format` into the card payload

**Date:** 2026-07-21
**Author:** Planner (narrowed 2026-07-21 after a live capture superseded the original premise)
**Ships in:** rides the next release cut (no version bump of its own — backend-only, no static assets; coordinates with item 13's version to avoid a bump collision)
**Queue item:** 17
**Branch:** `feat/transcoded-metadata-propagation`
**Type:** backend correctness fix. No user-facing surface, no new copy, no design handoff.

---

## The defect (as measured, not as documented)

Yoto re-transcodes every uploaded MP3 server-side and serves the transcoded
artifact to physical players. The app builds the `/content` card from the
**local pre-upload** file's probe, so it hardcodes `format = "mp3"`. But Yoto
serves **Ogg Opus**, so the card advertises the wrong `format` for every track.

This plan was originally scoped far wider — to also propagate `fileSize`,
`duration`, and `channels`, and to *fail loud* if Yoto's `transcodedInfo` was
missing. **A live read-only diagnostic against the three real affected cards, plus
one live upload→transcode-poll capture, overturned that scope.** See §Live
evidence. The corrected scope is: **advertise Yoto's true `format`, best-effort.
Nothing else changes.**

## Live evidence (ground truth — supersedes the yoto.dev docs)

A real upload was pushed through the transcode poll and the response captured. The
ready-poll body shape is:

```json
{"transcode": {"transcodedSha256": "…",
  "transcodedInfo": {"duration": 0, "codec": "opus", "format": "opus",
    "sampleRate": 48000, "channels": "stereo", "bitrate": 0,
    "inputFormat": "…", "fileSize": 0}}}
```

- `transcodedInfo` is a **direct child of `transcode`**. `_dig(body, "transcodedInfo")`
  resolves it (one nesting level deep). Do **not** `_dig(body, "format")` directly —
  `format` lives two levels deep and the key is ambiguous.
- `transcodedInfo.format` is the literal string **`"opus"`** (a valid value in Yoto's
  `/content` schema enum). **This is the only field the app gets wrong.**
- `transcodedInfo.channels` is the string **`"stereo"`** — already exactly what the
  app sends today (`"stereo"`/`"mono"`). No change needed; making it an int would be a
  regression.
- A read-only GET/HEAD diagnostic on the three real cards found declared `fileSize`
  and `duration` **already equal the served-artifact values** (delta 0 on all 24
  tracks). Yoto self-corrects those server-side; propagating them from
  `transcodedInfo` changes nothing observable. Left to the local probe.

The docs that the original (wider, fail-loud) plan trusted were wrong about the codec
(they claimed AAC/MP4 128 kbps; the artifact is Ogg Opus ~92 kbps). Because the docs
were unreliable, **fail-loud on a "missing/misshapen" `transcodedInfo` is unsafe** — a
shape we didn't anticipate would block all card creation. The fix therefore
**degrades, never raises.**

## The change (the entire behavioural delta is `format`)

**`yoto_maker/yoto/client.py`**

1. New pure helper `_transcoded_format(info) -> str | None`: returns `info["format"]`
   when `info` is a dict carrying a non-empty string `format`, else `None`. Best-effort
   by construction — a missing / empty / wrong-type / `None` `transcodedInfo` yields
   `None`.
2. `_poll_transcode` returns `(sha, transcodedInfo)` instead of just `sha`. On the ready
   poll it returns `(sha, _dig(body, "transcodedInfo"))` — the dict as-is, or `None` if
   Yoto didn't include one. The sha alone is still enough to build the card.
3. `create_card` computes `fmt = _transcoded_format(transcoded_info) or info.format` —
   prefer Yoto's transcoded `"opus"`; otherwise fall back to today's local-probe format.
   That flows through the **existing** `TrackMeta.fmt` → `build_content_payload`'s
   `"format": t.fmt`.

**`yoto_maker/yoto/models.py`** — unchanged. `TrackMeta.fmt`/`channels` keep their
existing defaults and string types.

### Explicitly NOT changed (guard-rails)

- No fail-loud. Missing/empty/wrong-type `transcodedInfo` degrades to the local format;
  the card is always built.
- `channels` stays the existing `"stereo"`/`"mono"` **string** (never an int).
- `fileSize`/`duration` stay from the local probe (Yoto self-corrects them).
- `TrackMeta` fields keep their defaults — nothing made required.
- No format allow-list / mapping — `format` passes through verbatim.
- `_safe_probe` and its `AudioInfo, probe_audio` import are **kept** (still the fallback).
- No version bump. Split logic / `MAX_TRACK_SECONDS` / bitrate untouched.

## Test plan (device-independent)

- `_transcoded_format` returns `"opus"` for the live shape; returns `None` for
  absent / empty / wrong-type / `None` input.
- `_poll_transcode` returns `(sha, info)` — the dict when `transcodedInfo` is present,
  `None` when absent. `FakeClient`'s ready-poll fixture uses the confirmed nested shape
  (`transcode.transcodedInfo`, `format: "opus"`, `channels: "stereo"`).
- End-to-end: the built `/content` track carries `format == "opus"` (not `"mp3"`), and
  `channels` stays the `"stereo"`/`"mono"` string.
- **Degrade-not-break:** a ready transcode with NO `transcodedInfo` still builds the
  card (no exception) and the track's `format` falls back to the local probe's value.

**On-device confirmation** — that advertising `format: "opus"` actually resolves the
physical player's stuck offline download — is the post-merge maintainer step. It is not
a merge blocker: this change is strictly more correct than the status quo (which
advertised a definitely-wrong `"mp3"`), and it cannot break card creation.
