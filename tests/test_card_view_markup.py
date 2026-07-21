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
