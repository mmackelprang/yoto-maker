"""``What to do next.html`` — the page that goes in the folder.

One file, one rendering, both routes: the same bytes are written into the folder
and served by GET /api/export/sheet.html, so the two can never drift
(overview.md §6.3).

Pure. It takes already-read bytes and returns a string; the runner does the I/O.
"""
from __future__ import annotations

import base64
import html
from dataclasses import dataclass, field

from .names import duration_words
from .rules import Advisories, SavedFile, SplitGroup

_STYLE = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:#f6f4fb;color:#241d38;
  font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;
  font-size:17px;line-height:1.5}
.wrap{max-width:720px;margin:0 auto;padding:28px 18px 64px}
h1{font-size:28px;margin:0 0 6px}
h2{font-size:22px;margin:0 0 4px}
h3{font-size:18px;margin:0 0 10px}
.rule{height:1px;background:#e3ddf3;margin:14px 0 22px}
.muted{color:#6b6480}
.meta{color:#6b6480;font-size:15px;margin:0}
.lede{margin:0 0 22px}
.head{display:flex;gap:16px;align-items:center}
.cover{width:180px;height:180px;object-fit:cover;border-radius:16px;flex:0 0 auto}
.card{background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(90,60,160,.10);
  padding:20px 22px;margin:0 0 18px}
.card p:last-child{margin-bottom:0}
a{color:#5f43b0}
.files{font-family:Consolas,"Cascadia Mono","Courier New",monospace;font-size:14px;
  background:#f6f4fb;border-radius:12px;padding:14px 16px;margin:14px 0;
  white-space:pre-wrap;word-break:break-all}
.name{font-size:22px;font-weight:600;margin:6px 0 12px}
.notice{background:#fdeaea;color:#c62828;border-radius:12px;padding:14px 16px;margin:0 0 18px}
ul{margin:0;padding-left:20px}
li{margin-bottom:10px}
li:last-child{margin-bottom:0}
.foot{color:#6b6480;font-size:14px;margin-top:22px}
@media print{
  body{background:#fff}
  .wrap{padding:0}
  .card{box-shadow:none;border:1px solid #e3ddf3;break-inside:avoid}
  .notice{border:1px solid #c62828}
}
"""


@dataclass
class SheetData:
    card_name: str
    files: list[SavedFile]
    failures: list[str]                      # titles that did not make it
    advisories: Advisories
    split: list[SplitGroup] = field(default_factory=list)
    picture_png: bytes | None = None
    has_card_picture_file: bool = False
    # Whether the "Track pictures" subfolder is actually there with pictures in
    # it. The runner declines to create it whenever no track resolved an icon, and
    # its mkdir can fail — so this is reported from what landed on disk rather
    # than assumed (overview.md §9.2: the sheet mentions them CONDITIONALLY).
    has_track_pictures: bool = False
    version: str = ""
    date_label: str = ""

    @property
    def converted(self) -> list[SavedFile]:
        return [f for f in self.files if f.converted]


def render_sheet(d: SheetData) -> str:
    e = html.escape
    out: list[str] = []
    out.append("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">")
    out.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    out.append(f"<title>What to do next — {e(d.card_name)}</title>")
    out.append(f"<style>{_STYLE}</style></head><body><div class=\"wrap\">")

    out.append("<h1>What to do next</h1><div class=\"rule\"></div>")

    # --- the missing-track notice, above everything (copy.md §6.8) ---------- #
    if d.failures:
        out.append(_missing_notice(d.failures))

    # --- head: picture, card name, the REAL counts (copy.md §6.1) ---------- #
    out.append('<div class="head">')
    if d.picture_png:
        uri = base64.b64encode(d.picture_png).decode("ascii")
        out.append(f'<img class="cover" alt="" src="data:image/png;base64,{uri}">')
    total_s = sum(f.duration_s for f in d.files)
    noun = "track" if len(d.files) == 1 else "tracks"
    out.append("<div>")
    out.append(f"<h2>{e(d.card_name)}</h2>")
    out.append(f'<p class="meta">{len(d.files)} {noun} · {e(duration_words(total_s))}</p>')
    out.append("</div></div>")

    out.append(
        '<p class="lede">Everything for your card is in this folder. Here’s how to '
        "put it on your Yoto — it takes about five minutes, and there’s nothing "
        "here you can break.</p>"
    )

    # --- 1 ------------------------------------------------------------------ #
    out.append(
        '<div class="card"><h3>1. Open Yoto’s website</h3>'
        '<p>Go to <a href="https://my.yotoplay.com">my.yotoplay.com</a> and sign in '
        "with your normal Yoto email and password — the same one you use in the "
        "Yoto app on your phone.</p>"
        "<p>Click <strong>Make Your Own</strong>, then start a new card.</p></div>"
    )

    # --- 2 ------------------------------------------------------------------ #
    out.append(
        '<div class="card"><h3>2. Give it this name</h3>'
        f'<p class="name">{e(d.card_name)}</p>'
        "<p>It doesn’t have to match — but it’s easier if your card, your label "
        "and this folder all say the same thing.</p></div>"
    )

    # --- 3 ------------------------------------------------------------------ #
    out.append('<div class="card"><h3>3. Add the audio files</h3>')
    out.append(
        "<p>Add these files from this folder. <strong>Pick them all at once</strong> "
        "— they’re numbered so they stay in the right order.</p>"
    )
    if d.split:
        # copy.md §6.4, singular and plural. The sheet's line names no titles and
        # no counts in EITHER variant, unlike the panel's §5.3: it sits six inches
        # above the file list, where every part is already printed with its own
        # number, and repeating them in prose would be the same information twice.
        out.append(
            "<p>One of your tracks was too long for a Yoto card, so it’s in more "
            "than one piece. That’s normal — add all the pieces and they’ll play "
            "one after the other.</p>"
            if len(d.split) == 1 else
            "<p>Some of your tracks were too long for a Yoto card, so they’re each "
            "in more than one piece. That’s normal — add all the pieces and they’ll "
            "play one after the other.</p>"
        )
    if d.converted:
        out.append(
            "<p>Some of these are MP3 copies that Yoto Maker made, because Yoto’s "
            "website is fussier about this than the app is. They’re the same "
            "audio.</p>"
        )
    if d.advisories.anything_over:
        out.append(
            "<p>One of these is bigger than Yoto usually allows on a card. If the "
            "website refuses it, that’s why — the numbers are at the bottom of "
            "this page.</p>"
        )
    listing = "\n".join(e(f.name) for f in d.files)
    out.append(f'<div class="files">{listing}</div>')
    out.append(
        "<p>If you add them one at a time, add them in number order — 01 first, "
        "then 02, and so on.</p></div>"
    )

    # --- 4: omitted entirely when there is no picture (mockup §5) ----------- #
    if d.has_card_picture_file:
        out.append(
            '<div class="card"><h3>4. Add the picture <span class="muted">(if you '
            'want one)</span></h3>'
            "<p><strong>Card picture.png</strong>, in this folder, is the picture "
            "from your card. Add it wherever the website asks for a picture.</p>"
            "</div>"
        )

    # --- the little pictures: whenever that subfolder actually landed, and ---- #
    # --- true under both answers to the open question (overview.md §9.2) ----- #
    # Conditional, not unconditional: the runner skips the subfolder when no track
    # resolved an icon and when its mkdir fails, and a page that says "there's a
    # folder here called Track pictures" beside no such folder sends her looking
    # for something that does not exist.
    if d.has_track_pictures:
        out.append(
            '<div class="card"><h3>The little pictures on the Yoto screen</h3>'
            "<p>There’s a folder here called <strong>Track pictures</strong>, with a "
            "small picture for each track — the ones that show on the Yoto player’s "
            "screen. They’re named to match the audio files.</p>"
            "<p>If Yoto’s website asks you for a picture for each track, they’re in "
            "there. If it doesn’t ask, you don’t need them.</p></div>"
        )

    # --- 5 and 6. STEP 6 IS NEVER CONDITIONAL AND MUST NEVER BE DROPPED. ---- #
    out.append('<div class="card"><h3>5. Save it on the website</h3></div>')
    out.append(
        '<div class="card"><h3>6. Put it on a card</h3>'
        "<p>Open the Yoto app on your phone, tap a blank <strong>Make Your Own</strong> "
        "card to link it, and press play. 🎶</p>"
        "<p>This last bit is a Yoto step — no app can do it for you, and it’s the "
        "same whether you upload by hand or send straight from Yoto Maker.</p>"
        "</div>"
    )

    # --- footer: the ONE place Yoto's limits are written down --------------- #
    out.append('<div class="rule"></div><h3>If something doesn’t work</h3><ul>')
    out.append(
        "<li><strong>The website won’t take one of the files.</strong> Tell whoever "
        "set Yoto Maker up for you which file it was — that’s the useful thing to "
        "say.</li>"
    )
    out.append(
        "<li><strong>The website says something is too big, or won’t take them "
        "all.</strong> Yoto allows <strong>100 MB and an hour</strong> for any one "
        "track, and <strong>500 MB, five hours and 100 tracks</strong> for a whole "
        "card. If you’ve gone over, make two shorter cards instead of one.</li>"
    )
    out.append(
        "<li><strong>The tracks came out in the wrong order.</strong> Remove them "
        "and add them again, picking them all at once, or drag them into number "
        "order on the website.</li>"
    )
    out.append(
        "<li><strong>You can’t find the folder.</strong> It’s in your "
        "<strong>Documents</strong>, in a folder called <strong>Yoto Maker</strong>.</li>"
    )
    out.append("</ul>")
    out.append(
        f'<p class="foot">Made by Yoto Maker {e(d.version)} on {e(d.date_label)}. '
        "Not affiliated with Yoto.</p>"
    )

    out.append("</div></body></html>")
    return "".join(out)


def _missing_notice(titles: list[str]) -> str:
    e = html.escape
    # The closing clause belongs to its branch. Shared, it made the plural read
    # "…couldn’t save “A”, “B”, so they aren’t in this folder… If you want IT on
    # the card…". copy.md §6.8 gives the singular verbatim and leaves the plural
    # body unspecified, so this is a grammar fix inside an unspecified string —
    # the singular below is byte-identical to §6.8 and must stay that way.
    if len(titles) == 1:
        head = "One of your tracks isn’t here."
        body = (
            f"Yoto Maker couldn’t save <strong>“{e(titles[0])}”</strong>, so it isn’t "
            "in this folder and isn’t in the list below."
        )
        tail = "If you want it on the card, go back to Yoto Maker and try again."
    else:
        head = f"{len(titles)} of your tracks aren’t here."
        listed = ", ".join(f"“{e(t)}”" for t in titles)
        body = (
            f"Yoto Maker couldn’t save <strong>{listed}</strong>, so they aren’t in "
            "this folder and aren’t in the list below."
        )
        tail = "If you want them on the card, go back to Yoto Maker and try again."
    return (
        f'<div class="notice"><p><strong>⚠️ {head}</strong></p><p>{body} {tail}</p></div>'
    )
