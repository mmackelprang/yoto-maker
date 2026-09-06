# Mockups — the folder

What the user sees in Windows Explorer, and what she sees in the browser's
file-open dialog on Yoto's website. Those are two different views of the same
folder and the design has to work in both.

Rules and rationale: [`../overview.md`](../overview.md) §5.

---

## 1. The everyday case — five YouTube tracks

```
  Documents ▸ Yoto Maker ▸ Bedtime Stories

  ┌──────────────────────────────────────────────────────────────┐
  │  📁  Track pictures                                          │  ← folders first
  │  🎵  01 - Chapter One.mp3                        3.2 MB      │    in Explorer
  │  🎵  02 - Chapter Two.mp3                        3.8 MB      │
  │  🎵  03 - Chapter Three.mp3                      3.1 MB      │
  │  🎵  04 - Chapter Four.mp3                       4.0 MB      │
  │  🎵  05 - Chapter Five.mp3                       3.5 MB      │
  │  🖼  Card picture.png                             412 KB      │
  │  🌐  What to do next.html                          18 KB      │
  └──────────────────────────────────────────────────────────────┘
```

Four properties, each deliberate.

**(a) The numbers are the card's track order, and they are the ordering
mechanism.** A web upload orders by file name, by selection order, or by
dragging; a zero-padded prefix survives all three. Two digits, matching the
`key` the API path already writes (`models.py:31`), widening to three past 99
tracks so the sort never breaks.

**(b) The audio is a contiguous block.** Digits sort before letters, so
`Card picture.png` and `What to do next.html` land beneath every `NN - ` entry
and never interleave with the files she is selecting.

**(c) Nothing is named cryptically.** She is going to meet these files in a
file-open dialog with no help text beside them. `Card picture.png` and
`What to do next.html` are what a person would have called them.

**(d) There is nothing else in here.** No `.txt`, no `.json`, no log, no
leftovers. Everything in the folder is something she might legitimately open or
upload; the app's plumbing stays in `work/`, where it already lives.

---

## 2. The same folder in a browser's file-open dialog

This is the view that actually matters, and it is the one the design is tuned
for.

```
  ┌──────────────────────────────────────────────────────────────┐
  │  Open                                                        │
  │  ▸ Documents ▸ Yoto Maker ▸ Bedtime Stories                  │
  │  ┌────────────────────────────────────────────────────────┐  │
  │  │ 📁 Track pictures                                      │  │
  │  │ ▣  01 - Chapter One.mp3          ◀┐                    │  │
  │  │ ▣  02 - Chapter Two.mp3           │                    │  │
  │  │ ▣  03 - Chapter Three.mp3         ├ shift-click, or    │  │
  │  │ ▣  04 - Chapter Four.mp3          │  Ctrl+A            │  │
  │  │ ▣  05 - Chapter Five.mp3         ◀┘                    │  │
  │  │ ▢  Card picture.png                                    │  │
  │  │ ▢  What to do next.html                                │  │
  │  └────────────────────────────────────────────────────────┘  │
  │                                        [ Open ]  [ Cancel ]  │
  └──────────────────────────────────────────────────────────────┘
```

**This is why the track pictures are in a subfolder.** Five loose 16×16 PNGs
interleaved among the audio — `01 - Chapter One.png` sorting immediately after
`01 - Chapter One.mp3` — would put a decoy beside every single file she is trying
to select, in the one dialog where a mis-click costs her the whole upload.

In a subfolder they are invisible here and one click away if the website asks for
them. That is what makes `../overview.md` §16.2 item 2 — *does the site support
per-track pictures at all?* — a question this design does not need answered.

**And this is why the instruction sheet says "pick them all at once"**
(`../copy.md` §6.4). It is correct under every possible ordering behaviour on the
website, so the sheet does not have to know which one it is.

---

## 3. A long audiobook, with a split track

```
  Documents ▸ Yoto Maker ▸ The BFG

  ┌──────────────────────────────────────────────────────────────┐
  │  📁  Track pictures                                          │
  │  🎵  01 - Chapter One.mp3                                    │
  │  🎵  02 - Chapter Two.mp3                                    │
  │       …                                                      │
  │  🎵  17 - Chapter Seventeen.mp3                              │
  │  🎵  18 - Chapter Eighteen (part 1).mp3        ◀┐            │
  │  🎵  19 - Chapter Eighteen (part 2).mp3        ◀┘ ONE track  │
  │  🖼  Card picture.png                             she added   │
  │  🌐  What to do next.html                                     │
  └──────────────────────────────────────────────────────────────┘
```

**Split parts are numbered flat, alongside everything else**, because on the card
they genuinely are separate tracks — which is exactly what the API path does too.
Filename sort still equals play order, which is the only property that matters.

**The split has already happened before export sees the draft.** `split_audio`
runs at *add* time (`app.py:235`) and each part is already its own track with a
`(part N)` title (`app.py:243`), so export never splits anything. This corrects
the brief — `../overview.md` §12.1.

**She is told about it** (`../copy.md` §5.3), because here she will *see* two
files where she added one. On the send path the split is invisible and she never
needs to know; here an unexplained extra file reads as a bug, and the wrong
recovery — deleting one of them — is one click away.

---

## 4. The subfolder

```
  Documents ▸ Yoto Maker ▸ Bedtime Stories ▸ Track pictures

  ┌──────────────────────────────────────────────────────────────┐
  │  🖼  01 - Chapter One.png                          1 KB      │
  │  🖼  02 - Chapter Two.png                          1 KB      │
  │  🖼  03 - Chapter Three.png                        1 KB      │
  │  🖼  04 - Chapter Four.png                         1 KB      │
  │  🖼  05 - Chapter Five.png                         1 KB      │
  └──────────────────────────────────────────────────────────────┘
```

Named to match their audio file exactly, so the mapping needs no explanation and
no legend.

**One per track, even when every file is byte-identical.** `_resolve_icon`
(`app.py:618-628`) derives most cards' icons from the *card* picture, so on a
typical card all five of these are the same image. De-duplicating would break the
1:1 name match that makes the folder usable without thought, and would force the
sheet to explain a mapping. Five copies of a 16×16 PNG is about four kilobytes.

---

## 5. Saved twice

```
  Documents ▸ Yoto Maker

  ┌──────────────────────────────────────────────────────────────┐
  │  📁  Bedtime Stories                                         │
  │  📁  Bedtime Stories (2)          ← the second save          │
  │  📁  The BFG                                                 │
  │  📁  Wild Robot                                              │
  └──────────────────────────────────────────────────────────────┘
```

**Nothing is ever overwritten.** She may be halfway through uploading the first
copy. ` (2)` is the convention Windows itself uses when you copy a file, so it
needs no explanation — and the success panel names the folder she actually got
(`../copy.md` §5.8), so a `(2)` is stated rather than discovered.

Timestamped names (`Bedtime Stories 2026-09-05 14-03`) were rejected: they answer
a question nobody asked and are much harder to say out loud on the phone, which
is the use case that decided the location in the first place.

---

## 6. Where this is *not*

```
  %LOCALAPPDATA%\YotoMaker\work\        ← NOT here
  ├─ Chapter One.mp3
  ├─ card_picture.png
  ├─ picture_source.png
  ├─ icon_a3f1.png
  ├─ label.pdf
  ├─ parts\
  └─ uploads\
```

`work/` is the app's scratch space. It is flat, it holds thirteen kinds of
intermediate file under fixed overwritten names, and it has **no cleanup of any
kind** — no purge, no TTL, no size cap anywhere in `yoto_maker/`, and
`DraftCard.reset()` deletes nothing from disk.

Putting the user's deliverables in there would mean a deliverable can be silently
clobbered by the next card's scratch, and would put *her* files inside the app's
private area where an uninstall takes them with it.

`Documents` wins on the one use case that decides it: *"where did it put them?"*
asked down a phone line, about a computer that is not in front of you.
