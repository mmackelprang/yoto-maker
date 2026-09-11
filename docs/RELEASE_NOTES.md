# Yoto Maker v0.1.14

Turn audio into a Yoto card and print a matching label, from one simple screen.
Built to be usable by someone with little computer knowledge.

### 🆕 New in v0.1.14

- **New cards now carry the chapter numbers Yoto's own player software expects.**
  Every card Yoto Maker has ever made was missing a small numbering label that
  Yoto's published description of a card lists as **required** on every track.
  Yoto Maker now includes it, numbered **1, 2, 3…** down your list of tracks.
  **Please read the note below about what this does and does not fix.**
- **Cards you already made can be brought up to date without being re-made.**
  The repair tool that whoever set this up for you can run now adds the missing
  numbering to a card that is already in your Yoto account, in place — the card
  keeps working with the same physical card you already tapped, and nothing else
  about it is touched. It writes a backup of the card first, checks afterwards
  that only what it meant to change actually changed, and does nothing at all if
  the card is already correct.

### ✅ Confirmed on a real Yoto player — 2026-09-11

**Twisting the button on the player brings up the chapter list, and pressing it
picks a chapter.** This was tried on a physical Yoto player on **2026-09-11**, on
a card with several chapters that this version had numbered. That is exactly the
problem this release was aimed at, and it is fixed.

When this release was published, the explanation behind it was only an informed
guess — Yoto publishes nothing that says this numbering label is what makes the
chapter list appear, and its own description of the field mentions the phone
*app* rather than the player. **The guess turned out to be right, and it has now
been watched happening on the hardware rather than reasoned about.** What was
observed: the chapter list appeared when the right-hand button was twisted, and a
chapter was selected by pressing it.

One thing this does **not** settle, and it is worth being plain about: **it says
nothing about the card that sits on the player and never finishes downloading for
offline listening.** That is a separate problem, it is still open, and nothing
seen on 2026-09-11 is evidence about it in either direction.

### 🆕 New in v0.1.13

- **There’s a second way to finish a card, and it doesn’t need you to be signed
  in.** Under **🚀 Send to Yoto** in step 3 there is now
  **📁 Save the files to a folder**. Press it and Yoto Maker puts everything for
  your card — the audio, the pictures, and a page of instructions — into a folder
  in your **Documents**, under **Yoto Maker**. You then put them on Yoto’s
  website yourself. Nothing about sending straight to your Yoto has changed.
- **The folder comes with instructions written for your card.** A page called
  **What to do next** opens in your browser and names your card, lists your
  actual files in order, links to Yoto’s website, and ends where it should — at
  tapping a blank card in the Yoto app. It stays in the folder, so you can open
  it a week later, or on a different computer.
- **Files Yoto’s website is fussy about are saved as MP3 copies.** They’re the
  same audio, and Yoto Maker tells you which ones it did that to. Your original
  files are untouched.
- **Nothing is ever overwritten.** Save the same card twice and you get a second
  folder ending in **(2)**, exactly like copying a file in Windows.

### Fixed in v0.1.13

- **When a track is too big, the message now talks about *that track*.** If Yoto
  refused one of your tracks for being too large, Yoto Maker used to answer with
  the limit for a whole card — *“max 5 hours per card”* — at the very moment the
  problem was one single track, on a card that might be nowhere near five hours.
  It now names the track Yoto wouldn’t take, says plainly that **no card was made
  in your Yoto account**, and points you at **📁 Save the files to a folder** as
  another way to finish that same card.
- **A message that used to be a dead end now tells you what to do.** If something
  else turns out to be too big to send, the app no longer just says so and leaves
  you there — it tells you to let whoever set Yoto Maker up for you know.
- **Sending a long track no longer eats the computer’s memory.** The app used to
  load an entire track into memory before sending it: a 200 MB file meant about
  **200 MB** held in memory at once, and a long recording more again. It now
  sends the file as it reads it — the same upload, sent the same way, holding
  **well under a megabyte** at a time. Nothing looks different; it simply no
  longer strains an older computer.

### 🆕 New in v0.1.12

- **Nothing you do changes in this release.** Making a card works exactly as it
  did in v0.1.11 — same screen, same steps, same buttons. Everything below is
  groundwork for one specific problem: a card that sits on the player and never
  finishes downloading.
- **If the app can't confirm what Yoto really made, it now writes that down.**
  When you send a card, Yoto converts your audio and tells the app what it
  produced. The app puts that answer on the card so the player knows what it's
  fetching. If Yoto doesn't answer, the app falls back to describing the file on
  your computer instead — and that guess can be wrong, which is the leading
  suspect when a card downloads forever and never completes. Until now that
  fallback happened in silence. It now records which track it happened on and
  what it wrote instead, so whoever is helping you can look it up rather than
  guess. **Nothing about how cards are made has changed** — the app makes the
  same card it made before; it just no longer keeps quiet about this one thing.

### 🛠️ Maintainer tooling in v0.1.12

Not part of the app. `python -m yoto_maker.repair` is a command-line tool run
from source by the maintainer to fix cards that were already made; there is
nothing to press for it in Yoto Maker itself.

- **The repair tool now writes track links and icons in the form Yoto's API
  requires.** Reading a card back gives those fields as full web addresses, and
  Yoto refuses to accept them in that form — a repair attempt came back rejected
  outright, so nothing was written and no card was harmed, but the repair
  couldn't finish either. The tool now converts them to the short reference form
  Yoto expects (`yoto:#…`) before saving — both the audio link and the 16×16
  icons — and if any value is one it can't recognise it declines to write that
  card at all rather than write half of it.

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
- **The player's chapter list — confirmed on real hardware 2026-09-11.** On a card
  numbered by v0.1.14, twisting the player's right-hand button brings up the
  chapter list, and pressing it selects a chapter. See
  *✅ Confirmed on a real Yoto player* under v0.1.14 above.

## ❓ Not verified in v0.1.14

> **The headline question has moved out of this section.** *"Whether the missing
> chapter numbering is what stops the player's button from bringing up a chapter
> list"* used to be the first item here, marked UNVERIFIED. It was **confirmed on
> a physical Yoto player on 2026-09-11** and now sits under *🔒 What's verified*
> above. Everything still listed below is genuinely unsettled.

- **⚠️ A card that plays in the Yoto phone app still proves nothing about the
  *download*.** For the same reason as in v0.1.13 below, streaming works even on a
  card a player cannot download — so the phone app cannot answer it. The chapter
  list is settled; **whether the download for offline listening finishes is not**,
  and that is still the question that needs a player with its wi-fi turned off.
- **Whether `1` or `01` is what Yoto wants to show.** The numbering is sent
  unpadded — `1`, `2`, … `18` — on the strength of Yoto's own example code, which
  puts `1` beside the padded `01` it uses for its internal name of the same track.
  A chapter list built from the unpadded form has now been seen working on a real
  player and nothing about it was reported as looking wrong — but nobody compared
  the two forms, so the padded alternative is untested rather than ruled out. If it
  ever looks wrong, it is a one-line change.
- **Whether Yoto keeps or discards a field left out of an update.** This matters
  only to undoing a repair: a backup taken before this release does not contain
  the new numbering, so restoring one asks Yoto to put the card back without it.
  The repair tool reports that case as *restored, and the numbering is still
  there* rather than as a failure, so an undo cannot cry wolf either way.

## ❓ Not verified in v0.1.13

- **Whether saving to a folder fixes the card that never finishes downloading.**
  This feature exists to route around a card that sits on the player and never
  completes its download for offline listening. The saving itself has been
  tested end to end on this computer: the folder is written correctly, the files
  are numbered in playing order, the ones Yoto's website is fussy about are
  saved as MP3 copies, the instructions page opens on its own, and nothing is
  ever overwritten. **None of that is the same as knowing the original problem
  is solved.** Answering that needs a physical Yoto player, and there isn't one
  here — so this ships as a way around the problem, not as a proven fix for it.
- **⚠️ A card that plays in the Yoto phone app proves nothing about this.**
  Streaming in the app will very likely work even on a card a player cannot
  download — which is exactly why this problem went unnoticed for three
  releases. The questions that matter are whether the **download for offline
  finishes** on the player itself, and whether the card then plays with the
  wi-fi turned **off**.
- **Whether Yoto's website accepts the files.** The folder is built to what Yoto
  publishes about what its website takes — accepted kinds of audio file, and its
  size and length limits. Those figures are Yoto's documentation, not something
  measured here, and nobody has yet uploaded one of these folders by hand. If a
  real upload ever disagrees with what the instructions page says, the upload is
  right.
- **Whether Yoto turns down an over-large track the way the new message
  expects.** The wording described above has been seen on screen, but with a
  stand-in playing Yoto’s part — nobody here has had Yoto itself refuse a real
  over-large track. If Yoto ever refuses one in some other way, you may still
  get a vaguer message instead. The new wording deliberately quotes no size
  limit at all, so there is at least no figure in it that can turn out to be
  wrong.

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
