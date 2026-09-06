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
                   "exportDone", "exportNote", "exportActions", "advRow")
    ]
    assert order == sorted(order)


def test_adv_row_is_still_the_last_child_of_step_3(index_html):
    """configuration-surface interactions.md §1.4, unchanged by this feature."""
    assert index_html.index('id="advRow"') > index_html.index('id="exportActions"')


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


def test_a_successful_open_clears_only_a_reveal_failure(app_js):
    """After a partial save #exportError holds the list of tracks that could not
    be saved (copy.md §5.6). An unconditional clear would destroy it."""
    body = app_js.split("async function openSavedFolder")[1]
    assert "if (exportErrorIsRevealFailure) {" in body
    assert body.count('clearError($("#exportError"))') == 1


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
    """interactions.md §4.4: #exportError sits ABOVE #exportActions, so a message
    raised by the reveal button appears behind the user's position. Moving focus
    is what takes her to it. And copy.md §5.5a(b)'s path must be rendered, in
    .mono-value, or the message is a dead end."""
    block = app_js[app_js.index("async function openSavedFolder"):]
    block = block[:block.index("// ---- wire up")]
    assert "box.focus()" in block
    assert "e.data && e.data.path" in block
    assert 'p.className = "mono-value"' in block
    # showError() sets textContent, which would delete the appended child.
    assert "showError(" not in block
