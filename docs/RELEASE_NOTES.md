# Yoto Maker v0.1.11

Turn audio into a Yoto card and print a matching label, from one simple screen.
Built to be usable by someone with little computer knowledge.

### 🆕 New in v0.1.11
- **You can add several audio files at once.** Press **📁 Choose audio files**
  and pick as many as you like. They're added one after another, in order by
  file name, and you can move them around afterwards. If one of them doesn't
  work, the rest still get added and Yoto Maker tells you which one it was and
  why.
- **You can stop a long add.** A **Cancel** button now sits beside the progress
  bar. Anything already added stays in your list, and Yoto Maker tells you
  exactly what got in and what didn't.
- **A new "If you need to ask for help" section at the bottom of Settings.**
  It shows the handful of details anyone helping you will ask for. Nothing
  there can be changed by looking at it.

### Fixed in v0.1.11
- **Typing the wrong thing in the Client ID box can't sign you out any more.**
  If you paste something that isn't a Client ID — an email address, say, or a
  web address — Yoto Maker now says so and changes nothing. Before, it would
  save it and sign you out, and the only thing you'd see was an error page on
  Yoto's website.
- **If a bad Client ID is already saved, Yoto Maker now says so plainly** — on
  the Settings screen and next to the Connect button — shows you the whole
  value rather than a shortened version, and gives you a one-press way back to
  the built-in one.

### Fixed in v0.1.10
- **The way to use a different Yoto account is back where you can see it.** The
  link at the bottom of step 3 now says **⚙️ Connect a different Yoto account**
  once you're signed in, and it no longer disappears when everything is working.
  Previously it only showed up while you were *dis*connected — which is the one
  time you don't need it.
- **The Yoto button in the corner is easier to read.** Its label was too faint
  against the purple header. It's now a filled shape with a small `›` to show it
  takes you somewhere.
- **The app now finishes updating itself properly.** After an update, some parts
  of the app could still be the old version — so new buttons were there but did
  nothing, and the Settings page wouldn't open. Everything now arrives together.
  If the app has been behaving strangely since it last updated, this release
  fixes it on its own; you don't need to do anything.

## v0.1.9

### 🆕 New in v0.1.9
- **A Settings page.** Click the **Yoto** button in the top-right corner (or
  **Settings** at the bottom) to see whether your Yoto connection is actually
  working, and fix it with one button if it isn't. The four numbered steps are
  unchanged — step 3 is now a little shorter.
- **See the Client ID you're actually using.** If you or someone else set up your
  own Client ID, Settings now shows it — the short form (`abCD…xy9`) at a glance,
  and **Show the whole thing** when you need to read every character. It's shown
  in a typewriter font so `O` and `0` can't be confused when you're checking it
  against the Yoto website.
- **"Yoto connected" now means it.** The app used to say you were connected
  whenever a saved sign-in existed on the computer, even if Yoto had stopped
  accepting it — so the one time you needed the truth, it told you everything
  was fine. Settings now checks with Yoto for real, and says **We couldn't check
  right now** if the computer is offline, rather than blaming your account.
- **Keyboard users can see where they are.** Every button now shows a purple
  outline when you move to it with the Tab key.

### Fixed in v0.1.9
- **Changing the Client ID no longer breaks sending, silently.** A sign-in
  belongs to one Client ID, so changing it now signs you out and tells you to
  sign in again — instead of leaving the app claiming to be connected while
  every upload failed.
- **You can go back to the built-in Client ID** after pasting your own. There was
  previously no way to undo it.
- **An abandoned sign-in stops waiting.** Closing the Yoto tab without signing in
  used to leave the app checking every two seconds forever. It now stops after
  three minutes, and you can press **Cancel**.

### 🆕 New in v0.1.8
- **Emoticons.** The picture tab is now **😊 Emoticons** — pick from a big set of
  colorful emoji (animals, faces, nature, treats, and more) for the label and the
  Yoto screen. Combine with **✏️ Adjust** to zoom/position it just right.

### New in v0.1.7
- **Adjust the picture.** After a picture is set, click **✏️ Adjust** to **drag
  it around and zoom** to frame exactly the part you want — great for getting the
  best crop out of a wide thumbnail or photo. What you frame is used on both the
  printed label and the Yoto screen.

### Fixed in v0.1.6
- **Long files (audiobooks) now work.** Yoto can't process a single track longer
  than ~60 minutes — a long file would get stuck "Preparing the audio…". The app
  now **automatically splits long audio into parts** (each a track on the card),
  so a whole audiobook uploads cleanly and is easy to navigate on the player.
- **Preparing large tracks waits properly.** The transcode step used to give up
  after 60 seconds; it now waits up to 10 minutes and shows a live "Yoto is
  processing…" progress message so it never looks stuck.

### Fixed in v0.1.5
- **"Something went wrong while uploading the audio"** is fixed. The upload used
  a 60-second limit that a larger file on a home connection could exceed — now
  the upload isn't time-capped, so big files upload fine. (Verified end-to-end
  against a real Yoto account.)
- **The little on-screen (pixel) icons now attach to each track.** They were
  being sent to Yoto in the wrong format and silently dropped; fixed.

### 🆕 Also new in v0.1.5
- **Automatic updates.** When the app is opened and a newer version exists, it
  now updates itself automatically (downloads + restarts) — as long as you
  haven't started a card yet. If you're mid-card, it waits and shows the
  "Update now" banner instead so nothing is lost.

### New in v0.1.4
- **Automatic updates.** When a newer version is out, the app shows a banner at
  the top. Click **Update now** and it downloads the new version, closes itself,
  swaps in the update, and reopens — no more "file is in use" errors from trying
  to replace it by hand. (There's also a *What's new* link.)

### Fixed in v0.1.3
- **Some YouTube videos failed to download** (introduced in v0.1.1 with sponsor
  skipping). The sponsor-skipping step needs `ffprobe`, which wasn't bundled —
  now it is. This was intermittent (it depended on the audio format YouTube
  served), which is why the same video sometimes worked and sometimes didn't.
- **Sponsor-skipping is now best-effort:** if it ever can't run, the app still
  gets your audio (just without the trim) instead of failing the whole import.
- **Clearer message** if the app window loses contact with the background app
  ("Couldn't reach the Yoto Maker app… make sure it's still running") instead of
  a cryptic *"Failed to fetch"*.
- **The picture is now filled in automatically** from the audio (YouTube
  thumbnail or a file's album art) the moment you add a track — no need to click
  "Use that picture". You can still change it to Upload / Icons / AI.

### New in v0.1.2
- **Pre-configured Yoto connection** — the app now ships with its Yoto app ID
  built in, so there's **no setup step**: just click *Connect my Yoto account*
  and sign in. (Advanced users can still point it at their own Yoto app via the
  "Use a different Yoto account" link.)
- **About popup** — a little *About* link in the footer.

### New in v0.1.1
- **Skips sponsor / ad segments in YouTube audio** automatically (using the
  community SponsorBlock database) — paid promos and "like &amp; subscribe" bits
  are cut out. There's a checkbox under the YouTube box to turn it off. It stays
  conservative (only advertising-type segments) so it never trims real story or
  song content. *Note: ads the creator baked into the recording still can't be
  detected; YouTube's own interruptive ads were never included anyway.*

---


## 📥 Install (Windows)

1. Download **`YotoMaker.exe`** below.
2. Double-click it. If Windows shows *“Windows protected your PC”*, click
   **More info → Run anyway** (the app is new and unsigned).
3. It opens in your web browser automatically.

👉 Full picture-by-picture guide:
**[INSTALL-FOR-MOM.md](https://github.com/mmackelprang/yoto-maker/blob/main/docs/INSTALL-FOR-MOM.md)**

## ✨ What it does

- **Add audio** from a **YouTube link** or an **audio file** (MP3/M4A/WAV…).
- **Name the card** and give it a **picture** — from the audio, your own upload,
  or a built-in icon library.
- **Send it to your Yoto** account over Yoto's official API (one-time sign-in).
- **Print a label** with the picture and track names.
- Each track gets a little **pixel icon** on the Yoto screen.

## ⚙️ One-time setup for the Yoto connection

Sending to Yoto needs a free **Client ID** from
[dashboard.yoto.dev](https://dashboard.yoto.dev). It takes ~5 minutes and only
the person setting up needs to do it — see
**[SETUP-YOTO-CONNECTION.md](https://github.com/mmackelprang/yoto-maker/blob/main/docs/SETUP-YOTO-CONNECTION.md)**.
Adding audio, pictures, and printing labels all work without it.

## 📝 Notes

- Windows 10/11 only for now.
- Downloading YouTube audio is at your discretion (personal/family use).
- Audible/DRM audiobooks are not supported (they can't be legally converted).
- ffmpeg + yt-dlp are bundled — nothing else to install.

## 🔒 What's verified

- Real YouTube download + thumbnail, audio-file import (with tags/art), icon
  library, per-track icons, and label PDF are all verified end-to-end.
- The Yoto upload flow is implemented against Yoto's documented API and covered
  by tests with mocked responses; live upload needs your Client ID (above).

## ❓ Not verified in v0.1.10

- **How the Yoto button in the corner sounds in a screen reader.** This release
  changed what that button is called for assistive software — it now reads out
  its visible label, **Yoto connected**, instead of a different hidden one, and
  the small `›` is deliberately silent. Inspected programmatically it looks
  right, but nobody has actually listened to it. NVDA isn't installed here and
  Narrator's speech can't be captured as text, so this is genuinely unheard —
  not "probably fine". Same gap as the v0.1.9 item below. If you use a screen
  reader and it announces something confusing, that's worth reporting.

## ❓ Not verified in v0.1.9

- **How the new "Show the whole thing" button sounds in a screen reader.** The
  button is built as a standard disclosure and reports the right state to
  assistive software when inspected programmatically, but no one has actually
  listened to it with NVDA or Narrator. If you use a screen reader and it
  announces something confusing, that's worth reporting — it hasn't been ruled
  out.

---

## 🛠️ Maintainer tooling (not part of the app UI, no version bump)

- **`python -m yoto_maker.repair` — repair an existing card's declared audio
  format.** Cards this app made before v0.1.11 advertise `format: "mp3"` while
  Yoto actually serves Ogg Opus; on the physical player that mismatch is the
  leading suspect for an offline download that never completes. This CLI reads a
  card in place, confirms each track's served artifact really is Opus, and
  rewrites **only** the `format` field — preserving the NFC link, icons, keys and
  order. It is **dry-run by default** (writing needs `--apply`), backs up every
  card before writing, is all-or-nothing per card, verifies the round-trip, and
  is idempotent. Run from source; it ships in the package but is not surfaced in
  the app. (Queue item 18.)
