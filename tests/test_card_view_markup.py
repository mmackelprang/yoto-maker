"""The way into Settings must exist, be worded for the user, and be legible.

Regression cover for the v0.1.9 field report: a connected user who knew the
Settings feature existed could not find it. #advToggle lived inside #connectRow,
which is hidden whenever connected, and its label had been changed from words
naming the *account* to words naming the *destination*. See
docs/design-handoffs/configuration-surface/overview.md §12.

These are markup and stylesheet assertions, deliberately. The defect was
structural — a control nested inside a container that gets hidden — and that is
exactly the class of defect a cheap static assertion catches and a browser test
only catches if someone remembers to check the healthy state.
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


@pytest.fixture(scope="module")
def styles_css() -> str:
    return (STATIC_DIR / "styles.css").read_text(encoding="utf-8")


def test_adv_row_is_not_inside_connect_row(index_html):
    """The v0.1.9 defect itself.

    #connectRow's contents run from its own id to the #sendBtn that follows the
    div, so anything inside it lies in that span. #advToggle must not.
    """
    start = index_html.index('id="connectRow"')
    end = index_html.index('id="sendBtn"')
    assert start < end, "markup order changed; this test needs rewriting"
    assert 'id="advToggle"' not in index_html[start:end]


def test_adv_row_is_the_last_child_of_step_3(index_html):
    """Not before #sendBtn: that pushes the primary action down and takes a tab
    stop ahead of it. Last child also fixes the link's position as the transient
    boxes come and go, and lands it directly beneath #sendError on a failure.
    """
    order = [
        index_html.index(f'id="{el}"')
        for el in ("connectRow", "sendBtn", "sendProgress", "sendError", "sendDone", "advRow")
    ]
    assert order == sorted(order)


def test_adv_row_is_never_hidden(index_html):
    """No .hidden class in the markup and no show() call in the script.

    Asserted on the exact opening tag rather than a slice around it: the
    explanatory comment above the div contains the word "hidden", so a window
    around the id would match the prose and prove nothing.
    """
    assert '<div id="advRow" class="tiny"' in index_html
    assert 'id="advRow" class="tiny hidden"' not in index_html
    assert 'id="advRow" class="hidden' not in index_html


def test_adv_row_is_not_hidden_by_script(app_js):
    assert 'show($("#advRow")' not in app_js


def test_tiny_is_on_the_wrapper_not_the_anchor(index_html):
    """On the anchor, .tiny's color (0-1-0) beat `a { color: --accent-dark }`
    (0-0-1) and the app's most important contextual link rendered grey, reading
    as a caption rather than a link. Same construction as the footer's
    #settingsLink. interactions.md §1.4.
    """
    assert '<div id="advRow" class="tiny"' in index_html
    assert 'id="advToggle" class="tiny"' not in index_html
    assert 'class="tiny" id="advToggle"' not in index_html


def test_both_link_strings_are_rendered(app_js):
    """Verbatim from copy.md §1a. The connected variant is the whole fix: it
    contains the words the user was scanning with — account, different — which
    no string on the connected screen previously did.
    """
    assert '"⚙️ Connect a different Yoto account"' in app_js
    assert '"⚙️ Yoto connection settings"' in app_js


def test_the_gear_stays_on_the_step_3_link(index_html, app_js):
    """The glyph is the constant and the words are the variable, so a user who
    found this control in one state can recognise it in the other. This is the
    opposite of the pill's answer and that is deliberate — copy.md §1a.
    """
    assert "⚙️" in index_html
    assert app_js.count("⚙️") == 2


def test_pill_has_no_aria_label(index_html):
    """WCAG 2.1 AA 2.5.3 Label in Name. It overrode the visible text as the
    accessible name, so a speech-input user saying "click Yoto connected" did
    not activate it. title alone gives the right name/description split.
    """
    pill = index_html[index_html.index('id="yotoPill"') : index_html.index("yotoPillText")]
    assert "aria-label" not in pill
    assert 'title="Yoto connection settings"' in pill


def test_pill_chevron_is_present_and_silent(index_html):
    """Unlike .dot (an empty span), the chevron is text content and would be
    read out. It is an affordance mark, not a label.
    """
    assert '<span class="pill-chev" aria-hidden="true">›</span>' in index_html


def test_pill_is_not_given_a_gear(index_html):
    """Decided, not defaulted. A gear says "settings" — the category vocabulary
    that already failed to match — and reads as "machinery, don't touch" to the
    INSTALL-FOR-MOM user. overview.md §12.6.
    """
    pill = index_html[index_html.index('id="yotoPill"') : index_html.index("</button>", index_html.index('id="yotoPill"'))]
    assert "⚙" not in pill
    assert "→" not in pill


def test_pill_fill_is_ink_not_white(styles_css):
    """White at 18% over an already-light gradient lightened the background
    behind white text: 2.56:1 against a 4.5:1 bar. tokens.md §2b.

    The absence of the old value is asserted on the `background:` declaration
    rather than on the file, for the same reason test_adv_row_is_never_hidden
    asserts on the exact opening tag: the comment above the rule cites
    rgba(255,255,255,0.18) by name as the thing that was wrong, so a bare
    substring check would match that prose and fail on the documentation.
    """
    assert "rgba(36,29,56,0.28)" in styles_css
    assert "background: rgba(255,255,255,0.18)" not in styles_css


def test_stale_hover_derivation_is_gone(styles_css):
    """The two-layer grey composite existed only because the rest state was
    white. Leaving the derivation comment would send the next reader hunting for
    a composite that isn't there.
    """
    assert "rgba(144,144,144" not in styles_css
    assert "145,145,145" not in styles_css
    assert "rgba(36,29,56,0.38)" in styles_css


def test_no_stylesheet_comment_still_claims_the_retired_hazard(styles_css):
    """tokens.md §2a's outline-offset hazard is superseded by the fill inversion
    (2.57:1 -> 4.97:1) and was amended in place. The duplicate of that claim in
    styles.css must not survive to mislead a reviewer. The offset itself stays.
    """
    assert "2.57:1" not in styles_css
    assert "outline-offset: 2px" in styles_css


@pytest.mark.parametrize("derived", ["4.97:1", "5.81:1"])
def test_derived_contrast_figures_are_labelled_as_derived(styles_css, derived):
    """The same standard the test above applies to 2.57:1, applied to our own
    numbers.

    4.97 and 5.81 are Designer's *derived* sweep values (tokens.md §2b). The
    live pixels measure 5.03 and 5.87. Both figures may appear — the derivation
    is why alpha 0.28 was chosen and is worth keeping — but a bare derived
    figure reads as a measurement, and this stylesheet was rewritten twice
    precisely because it asserted figures a later change falsified. So each
    occurrence must sit next to the word "derived".

    Not a style nit: the sentence this replaced said the pair "measures 4.97:1",
    claiming measurement for a derived number, in the very PR that took the
    actual measurement.
    """
    for line in styles_css.splitlines():
        if derived in line:
            assert "derived" in line.lower(), (
                f"{derived} appears unqualified in styles.css. It is Designer's "
                f"derived figure, not a measurement — mark it, and cite the "
                f"measured value alongside.\n  {line.strip()}"
            )


def test_measured_contrast_figures_are_present(styles_css):
    """The derived figures are only safe to keep if the measured ones sit beside
    them. If someone strips these, the file is back to asserting predictions as
    fact and the test above starts passing vacuously.
    """
    assert "5.03:1" in styles_css
    assert "5.87:1" in styles_css


# --------------------------------------------------------------------------- #
# Save-to-a-folder mode. docs/design-handoffs/export-only-mode/.
# --------------------------------------------------------------------------- #
import re

# "path" is in copy.md's preamble ban list alongside the rest, and it holds
# against the shipped markup — nothing user-visible in index.html says it.
_BANNED_IN_COPY = ("export", "directory", "path", "file format", "codec",
                   "transcode", "metadata")


def _visible_text(index_html: str) -> str:
    """Text nodes only. Comments are stripped FIRST — the new markup's own
    comments say "export" repeatedly, and they are not user-visible."""
    without_comments = re.sub(r"<!--.*?-->", " ", index_html, flags=re.S)
    return " ".join(re.findall(r">([^<>]+)<", without_comments))


def test_the_export_block_sits_after_connect_warn_and_before_adv_row(index_html):
    order = [
        index_html.index(f'id="{el}"')
        for el in ("connectWarn", "exportRow", "exportProgress", "exportError",
                   "exportDone", "exportNote", "exportActions", "exportOpenError",
                   "advRow")
    ]
    assert order == sorted(order)


def test_adv_row_is_still_the_last_child_of_step_3(index_html):
    """configuration-surface interactions.md §1.4, unchanged by this feature."""
    assert index_html.index('id="advRow"') > index_html.index('id="exportOpenError"')


def test_the_export_row_is_never_hidden(index_html):
    row = index_html[index_html.index('id="exportRow"'):]
    row = row[:row.index(">") + 1]
    assert "hidden" not in row


def test_the_export_button_is_never_disabled_by_connection_state(app_js):
    """overview.md §10.1. Disabling it would delete the feature's reason to exist."""
    assert "#exportBtn\").disabled = !STATUS" not in app_js
    assert "#exportBtn\").disabled = !connected" not in app_js
    assert 'show($("#exportRow")' not in app_js


def test_the_word_export_never_reaches_the_user(index_html):
    """Acceptance criterion 6."""
    text = _visible_text(index_html).lower()
    for word in _BANNED_IN_COPY:
        assert word not in text, f"{word!r} is visible in index.html"


# --------------------------------------------------------------------------- #
# The same ban, everywhere the feature's copy actually lives.
#
# index.html carries one changed sentence. app.js renders ~25 of these strings
# and yoto_maker/export/sheet.py renders the whole instruction page — the largest
# body of user-visible copy in the app — and neither was guarded.
#
# WHAT THIS COVERS: string literals that get rendered.
# WHAT IT DELIBERATELY DOES NOT: comments, identifiers, DOM ids (`#exportError`
# is correct and intentional), route paths and URLs, and the `${…}` expressions
# inside template literals. All of those are code; none of them is copy.
# --------------------------------------------------------------------------- #
import ast
from pathlib import Path

_ID_SELECTOR = re.compile(r"^#[A-Za-z][\w-]*$")
_ROUTE_OR_URL = re.compile(r"^(/|https?://)")


def _js_rendered_strings(js: str) -> list[str]:
    without_comments = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    without_comments = re.sub(r"(?m)^[ \t]*//.*$", " ", without_comments)
    without_comments = re.sub(r"(?m)(?<=[;,)}\]\s])//[^\n]*$", " ", without_comments)

    found = re.findall(r'"((?:[^"\\\n]|\\.)*)"', without_comments)
    found += re.findall(r"'((?:[^'\\\n]|\\.)*)'", without_comments)
    # A template literal's ${…} holds an expression, not copy: `${exportWhere(r)}`
    # would trip the guard on a function name the user never sees.
    found += [
        re.sub(r"\$\{[^{}]*\}", " ", t)
        for t in re.findall(r"`((?:[^`\\]|\\.)*)`", without_comments, flags=re.S)
    ]
    return [s for s in found
            if not _ID_SELECTOR.match(s) and not _ROUTE_OR_URL.match(s)]


def _py_rendered_strings(path: Path) -> list[str]:
    """Every string constant in a module except its docstrings.

    ast rather than a regex, for one specific reason: a docstring IS a string
    literal, and sheet.py's own module docstring names the route it is served
    from. Comments never reach the tree at all, which is the other half of it.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = node.body
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            docstrings.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


def _sheet_py() -> Path:
    from yoto_maker.export import sheet as sheet_mod

    return Path(sheet_mod.__file__)


def test_the_banned_words_never_reach_the_user_from_app_js(app_js):
    for text in _js_rendered_strings(app_js):
        low = text.lower()
        for word in _BANNED_IN_COPY:
            assert word not in low, f"{word!r} is in a rendered app.js string: {text!r}"


def test_the_banned_words_never_reach_the_user_from_the_instruction_sheet():
    for text in _py_rendered_strings(_sheet_py()):
        low = text.lower()
        for word in _BANNED_IN_COPY:
            assert word not in low, f"{word!r} is in a rendered sheet.py string: {text!r}"


def test_the_ban_guard_actually_reaches_the_copy_it_guards(app_js):
    """A guard whose extractor returns nothing passes trivially and proves
    nothing. Pin that both extractors reach real, known user-visible strings."""
    js = _js_rendered_strings(app_js)
    assert any("Yoto Maker couldn’t save the files." in s for s in js)
    assert any("in a folder called" in s for s in js)
    assert any("bigger than Yoto allows for a single track" in s for s in js)

    sheet = _py_rendered_strings(_sheet_py())
    assert any("Open Yoto’s website" in s for s in sheet)
    assert any("Put it on a card" in s for s in sheet)


# --------------------------------------------------------------------------- #
# The panel's own bookkeeping. Three defects that only show up on the second
# press of something, which is why they are pinned as assertions on the script.
# --------------------------------------------------------------------------- #
def test_the_sheet_link_appends_its_cache_buster_with_the_right_separator(app_js):
    """sheet_url now carries this save's id, so a bare "?t=" makes a second "?"."""
    assert 'r.sheet_url + "?t=" + Date.now()' not in app_js
    assert 'r.sheet_url.indexOf("?") === -1 ? "?" : "&"' in app_js


def test_the_open_button_sends_an_id_and_never_a_path(app_js):
    """overview.md §7.3. The id is opaque and server-minted; a path is refused."""
    assert "JSON.stringify({ id: exportSaveId })" in app_js
    assert "JSON.stringify({ path" not in app_js
    assert "folder_path }" not in app_js


def test_a_successful_open_clears_its_own_region_and_nothing_else(app_js):
    """interactions.md §4.4.2. The reveal button's failures live in
    #exportOpenError, which holds nothing else — so a successful open clears it
    UNCONDITIONALLY, and there is no flag to guard anything with.

    #exportError is the SAVE button's region: after a partial save it holds the
    list of tracks that could not be saved and the pointer to the instruction
    sheet (copy.md §5.6). The reveal button must not touch it in EITHER
    direction — not written, not cleared, not re-focused.
    """
    body = app_js.split("async function openSavedFolder")[1]
    body = body[:body.index("// ---- wire up")]
    assert 'clearError($("#exportOpenError"))' in body
    assert "exportErrorIsRevealFailure" not in body
    # The QUOTED id, so this tests the selectors the code actually uses and not
    # the comments, which name #exportError precisely to say it is off limits.
    # "#exportOpenError" does not contain "#exportError" as a substring.
    assert '"#exportError"' not in body, "the reveal button still touches #exportError"


def test_the_reveal_failure_flag_is_gone_from_the_whole_script(app_js):
    """interactions.md §4.4.2: "it must go rather than be left as dead state that
    implies a rule that no longer holds"."""
    assert "exportErrorIsRevealFailure" not in app_js


def test_start_over_disowns_a_save_that_is_still_running(app_js):
    """#startOver is not disabled during a save — only #exportBtn is — so an
    in-flight poll could resolve and re-show a panel for the discarded card."""
    assert "exportSaveGeneration += 1;" in app_js
    assert app_js.count("if (generation !== exportSaveGeneration) return;") == 2


def test_the_connect_box_no_longer_claims_connecting_is_required(index_html):
    assert "To send cards straight to your Yoto, connect your account first." in index_html
    assert "You'll need to connect your Yoto account first." not in index_html


def test_the_feature_adds_no_css(styles_css, index_html):
    """Acceptance criterion 10. If this fails, something in the spec §2 was
    reinterpreted and it goes back to Designer — do not add a rule to make it
    pass.

    The .msg-box.warn check is asserted on the RULE, not on the substring:
    styles.css:14 already carries a comment saying "Deliberately no
    .msg-box.warn variant", so a bare `"msg-box.warn" not in styles_css` fails
    on the shipped file and tests the documentation rather than the stylesheet.
    What must stay true is that tokens.md §1's refusal of that variant is still
    a refusal — i.e. no selector declares it.
    """
    for token in ("export", "#exportRow", "#exportBtn"):
        assert token not in styles_css
    assert not re.search(r"^\s*\.msg-box\.warn\b", styles_css, flags=re.M)

    block = index_html[index_html.index('id="exportRow"'):index_html.index('id="advRow"')]
    # Compared as CLASS TOKENS, not as whole attribute strings: #exportProgress
    # is class="progress hidden", which no attribute-level allow list would
    # contain, and the intent is "every class here is a shipped primitive".
    used = set()
    for attr in re.findall(r'class="([^"]+)"', block):
        used.update(attr.split())
    allowed = {"btn", "primary", "tiny", "progress", "bar", "msg", "msg-box",
               "err", "ok", "info", "done-actions", "hidden"}
    assert used <= allowed, used - allowed


def test_the_export_panel_renders_only_from_the_job_result(app_js):
    """It must never rebuild the folder name or path from anything local.

    Sliced across the whole render half, from the folder sentence's own helper
    down to the start of the request: r.folder_name is read in exportWhere(),
    which sits above renderExportResult(), so a slice starting at the renderer
    would miss it.
    """
    block = app_js[app_js.index("function exportWhere"):app_js.index("async function saveToFolder")]
    assert "Documents" not in block.replace("in your Documents, under Yoto Maker", "")
    assert "r.folder_path" in block and "r.folder_name" in block


def test_the_open_button_is_omitted_not_disabled(app_js):
    assert 'show($("#exportOpen"), !!r.can_open)' in app_js
    assert '#exportOpen").disabled' not in app_js


def test_there_is_no_cancel(app_js, index_html):
    """jobs.py has no cancellation and this PR does not add one (spec §2.8)."""
    assert "exportCancel" not in app_js
    assert "exportCancel" not in index_html


def test_start_over_clears_the_saved_panel(app_js):
    handler = app_js[app_js.index('$("#startOver")'):]
    assert 'show($("#exportActions"), false)' in handler
    assert '$("#exportReadme").removeAttribute("href")' in handler


def test_start_over_clears_all_six_regions(app_js):
    """interactions.md §9.3, amended for the sixth. A reveal failure left behind
    describes a folder belonging to the card she has just discarded, and it would
    survive onto a blank draft."""
    handler = app_js[app_js.index('$("#startOver")'):]
    for region in ("exportProgress", "exportError", "exportDone", "exportNote",
                   "exportActions", "exportOpenError"):
        assert f'show($("#{region}"), false)' in handler, region


def test_the_recovery_sentence_appears_once_however_many_ceilings_fired(app_js):
    assert app_js.count("make two shorter cards instead of one") == 1


def test_the_split_note_is_one_paragraph_however_many_tracks_were_split(app_js):
    """copy.md §5.3, which replaces the plan's paragraph-per-group stopgap.

    It is one fact about the card, not N facts, and N paragraphs would blow
    overview.md §10.3's five-paragraph budget for the note box.
    """
    block = app_js[app_js.index("function exportNotes"):app_js.index("function exportFailureParagraphs")]
    assert "for (const g of r.split_groups)" not in block
    assert "r.split_groups.length === 1" in block
    assert "r.split_groups.length > 1" in block


def test_the_oversize_note_ends_on_the_list_in_both_variants(app_js):
    """copy.md §5.9 moved the list to the end so both variants finish on the
    actionable thing, and rejected the earlier draft's closing advice."""
    block = app_js[app_js.index("function exportNotes"):app_js.index("function exportFailureParagraphs")]
    assert "needs making smaller" not in block
    assert "those tracks need" not in block
    assert block.count("which one it is: ${list}") == 1
    assert block.count("which ones they are: ") == 1


def test_a_failed_open_moves_focus_and_renders_the_path(app_js):
    """interactions.md §4.4.2. The failure renders into #exportOpenError and
    focus moves there — no longer to compensate for a message rendered behind
    her scroll position (the region is directly beneath the button now), but
    because it is what announces the message. copy.md §5.5a(b)'s path must be
    rendered, in .mono-value, or the message is a dead end."""
    block = app_js[app_js.index("async function openSavedFolder"):]
    block = block[:block.index("// ---- wire up")]
    assert 'const box = $("#exportOpenError")' in block
    assert "box.focus()" in block
    assert "e.data && e.data.path" in block
    assert 'p.className = "mono-value"' in block
    # showError() sets textContent, which would delete the appended child.
    assert "showError(" not in block


# --------------------------------------------------------------------------- #
# The two 2026-09-05 rulings. interactions.md §4.4 (a second region) and §4a /
# copy.md §5.10 (stop asserting an outcome the app does not have).
# --------------------------------------------------------------------------- #
def test_the_reveal_button_has_its_own_region_below_the_button(index_html):
    """interactions.md §1 note 5 and §4.4.2's Region row. Feedback sits beneath
    the control that raised it — overview.md §4.3 point 1's own rule, which
    refused a placement precisely because it made one button's feedback appear
    next to a different button."""
    assert index_html.index('id="exportOpenError"') > index_html.index('id="exportActions"')
    div = index_html[index_html.index('id="exportOpenError"'):]
    div = div[:div.index(">") + 1]
    assert 'class="msg-box err hidden"' in div
    assert 'role="alert"' in div
    assert 'tabindex="-1"' in div


def test_the_new_region_adds_no_tab_stop(index_html):
    """interactions.md §6.1. A tabindex="-1" div is reachable by the focus move
    and by the virtual cursor, never by Tab — which is what lets §1 append it
    after #exportActions without touching the order §6.1's table fixes."""
    div = index_html[index_html.index('id="exportOpenError"'):]
    div = div[:div.index(">") + 1]
    assert 'tabindex="0"' not in div
    assert div.startswith('id="exportOpenError"')
    assert "<button" not in div and "<a " not in div


def test_the_ledger_says_six_regions_not_five(index_html):
    """overview.md §13's everyday-path ledger. A number in a ledger that quietly
    stops matching is exactly the drift that section exists to catch."""
    regions = re.findall(r'id="(export(?:Progress|Error|Done|Note|Actions|OpenError))"',
                         index_html)
    assert len(set(regions)) == 6, sorted(set(regions))


def test_the_retry_is_opt_in_and_only_the_save_path_opts_in(app_js):
    """interactions.md §4a.1, as ruled by the maintainer: the retry is requested
    per call site, and in this PR only saveToFolder() asks for it.

    doUpdate() must never opt in — it EXPECTS its last poll to fail, because the
    server exits mid-restart, and it already reports success from that. Retrying
    there would freeze a bar for the whole window before showing a message that
    was already right.

    The send path is written (copy.md §9) but deliberately unshipped: verifying a
    send-path retry needs a live authenticated send against a real Yoto account,
    which is the exact thing this feature exists to avoid needing. §9.1's stated
    fallback, taken.
    """
    assert "retryWindowMs: POLL_RETRY_WINDOW_MS" in app_js
    assert app_js.count("retryWindowMs: POLL_RETRY_WINDOW_MS") == 1

    save = app_js[app_js.index("async function saveToFolder"):
                  app_js.index("async function openSavedFolder")]
    assert "retryWindowMs" in save

    for fn, end in (("async function doUpdate", "const CONNECT_WARN"),
                    ("async function sendToYoto", "async function makeLabel")):
        block = app_js[app_js.index(fn):app_js.index(end)]
        assert "retryWindowMs" not in block, f"{fn} must not opt in"


def test_the_retry_window_stays_inside_the_designed_bounds(app_js):
    """interactions.md §4a rule 1. The number is Builder's measurement, but the
    two bounds are the design's: long enough to ride out a busy machine, and
    under ~30s, "past which the cure is the disease"."""
    window = int(re.search(r"const POLL_RETRY_WINDOW_MS = (\d+);", app_js).group(1))
    assert 5000 <= window < 30000, window


def test_the_retry_is_silent(app_js):
    """interactions.md §4a rule 1: during the retry window the bar and the last
    #exportMsg line stay EXACTLY as they were. A blip that resolves must leave
    nothing to read, and onProgress is only ever called with a real job status."""
    block = app_js[app_js.index("async function pollJob"):app_js.index("// ---- state")]
    for word in ("Reconnecting", "reconnecting", "Retrying", "retrying",
                 "Still working", "Trying again"):
        assert word not in block
    # onProgress is called once, and only after a poll actually came back.
    assert block.count("onProgress(job.percent, job.message)") == 1


def test_lost_contact_replaces_the_outcome_claim_and_only_then(app_js):
    """copy.md §5.10's boundary table, which is normative. Getting this wrong
    means showing an uncertainty message for a failure the app definitely knows
    about — or, worse, keeping "Nothing was saved" for one it does not."""
    save = app_js[app_js.index("async function saveToFolder"):
                  app_js.index("async function openSavedFolder")]
    assert "e.lostContact\n      ? EXPORT_LOST_CONTACT" in save
    # The refusal and the job-reported error keep §5.7 / §3 untouched.
    assert "e.status === 400" in save
    assert "EXPORT_FAIL_HEAD" in save and "EXPORT_FAIL_TAIL" in save

    # lostContact is set in exactly one place: pollJob, after the window is
    # spent. A job that reported its own error throws a bare Error, so it can
    # never carry the flag.
    assert app_js.count("e.lostContact = true;") == 1
    poll = app_js[app_js.index("async function pollJob"):app_js.index("// ---- state")]
    assert "e.lostContact = true;" in poll
    assert 'if (job.status === "error") throw new Error(' in poll


def _joined(block: str) -> str:
    """Adjacent string literals, concatenated as the user will read them.

    Copy assertions must not be sensitive to where the source happens to wrap a
    `"…" + "…"` pair — that is source layout, not copy, and a reflow would
    otherwise break a test that has nothing to say about it.
    """
    return re.sub(r'"\s*\+\s*"', "", block)


def test_the_lost_contact_message_claims_no_outcome_and_names_no_folder(app_js):
    """copy.md §5.10. The head and half the tail of §5.7 are assertions the app
    is in no position to make; "Nothing on this card has changed" is the half
    that is true however the save ended, and it is kept."""
    block = _joined(app_js[app_js.index("const EXPORT_LOST_CONTACT"):
                           app_js.index("// The opaque id of the save")])
    # Paragraph 1 — the correction. The claim is dropped, the true half kept.
    assert ("Yoto Maker stopped answering while it was saving, so it can’t tell "
            "you whether it finished. Nothing on this card has changed.") in block
    assert "Nothing was saved" not in block
    assert "couldn’t save the files" not in block
    # Paragraph 2 — a test she can perform, and her ONLY route to the sheet in
    # this state: no result arrived, so "📄 What to do next" was never drawn, and
    # the page is named in words instead.
    assert ("Look in your Documents, under Yoto Maker, for a folder named after "
            "this card. If there’s a page in it called “What to do next”, the "
            "save finished — that page lists what’s actually there.") in block
    # The folder is NOT named: the panel has no result, so it does not know the
    # name — the card name is not it (sanitized, possibly " (2)"). The JS-side
    # reconstruction overview.md §11.3 forbids.
    assert "folder_name" not in block and "r.folder" not in block
    # Paragraph 3 — check the app is alive, then the permission to press again,
    # which is §5.2's invariant in her words.
    assert "make sure Yoto Maker is still running — look for the 🎵 icon" in block
    assert "Nothing you already have will be written over." in block


def test_the_lost_contact_paragraphs_are_copy_md_verbatim(app_js):
    """SESSION_STATE §5 constraint 1: copy.md is the AUTHORITY for every
    user-visible string, and where anything disagrees with it, copy.md wins.

    This is the only test in the suite that asserts a shipped string against the
    handoff itself rather than against a copy of it. It earns that coupling: the
    three paragraphs of §5.10 are the longest string in the package, they exist
    specifically to stop the app claiming an outcome it does not have, and a
    well-meaning reword — "Nothing was saved yet", say — would put the claim
    straight back while every other test still passed.
    """
    repo_root = Path(__file__).resolve().parent.parent
    doc = (repo_root / "docs" / "design-handoffs" / "export-only-mode"
           / "copy.md").read_text(encoding="utf-8")
    section = doc[doc.index("### 5.10"):doc.index("**The defect this replaces.**")]
    spec = re.findall(r"^> `(.+)`$", section, flags=re.M)
    assert len(spec) == 3, "copy.md §5.10 no longer has three quoted paragraphs"

    block = _joined(app_js[app_js.index("const EXPORT_LOST_CONTACT"):
                           app_js.index("// The opaque id of the save")])
    shipped = re.findall(r'^  "(.*)",$', block, flags=re.M)
    assert shipped == spec


def test_lost_contact_leaves_no_bar_and_a_live_button(app_js):
    """interactions.md §4a rule 2. A bar on screen says the app is still
    watching; it is not. And §5.10's third paragraph tells her to press the
    button, so it must be live. Both come from the existing finally block —
    pinned because a refactor that moved either would break the copy."""
    save = app_js[app_js.index("async function saveToFolder"):
                  app_js.index("async function openSavedFolder")]
    finally_block = save[save.index("} finally {"):]
    assert 'show($("#exportProgress"), false)' in finally_block
    assert '$("#exportBtn").disabled = false' in finally_block
    # No success box and no actions: neither is shown anywhere but on a result.
    assert save.count('show($("#exportActions"), true)') == 0
