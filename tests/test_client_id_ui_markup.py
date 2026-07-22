"""Item A's frontend contract, as static assertions.

Markup and script assertions deliberately. The defects here are structural — a
gate on the wrong side of a write, a mask applied to a value it was never meant
to summarise, a control offered in a state where it cannot act — and that is the
class a cheap static assertion catches reliably. The live-behaviour half is in
the plan's Test Plan §A–§E.
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


def test_connect_warn_is_not_send_error(index_html):
    """Both connectYoto() and sendToYoto() call clearError($("#sendError")) on
    entry, so a config warning parked there would be wiped by an unrelated
    action."""
    assert 'id="connectWarn"' in index_html
    assert 'id="connectWarn" class="msg-box err hidden" role="alert"' in index_html


def test_connect_warn_sits_between_send_done_and_adv_row(index_html):
    """Second-to-last child: directly above the link it refers to, with #advRow
    still last (interactions.md §1.4)."""
    order = [index_html.index(f'id="{el}"')
             for el in ("sendDone", "connectWarn", "advRow")]
    assert order == sorted(order)


def test_the_connect_button_is_never_disabled_by_the_block(app_js):
    """Disabling it with no visible reason is the dead-end antipattern §2.2
    forbids. Pressing it is the fastest path to the explanation."""
    assert '$("#connectBtn").disabled' not in app_js


def test_the_reset_button_is_omitted_not_disabled_on_env_and_builtin(app_js):
    """A disabled button would invite her to keep pressing it. env and builtin
    get a recovery SENTENCE instead; only `saved` gets a button."""
    assert 'button: "Put back the built-in Client ID"' in app_js
    assert app_js.count("button: null") == 2


def test_the_env_variable_name_is_spoken_twice(app_js):
    """copy.md §4d: deliberate, and the name IS the recovery instruction. A user
    who cannot act on it will read it out to someone who can."""
    start = app_js.index("const CONNECT_WARN")
    end = app_js.index("let connectWarnKey")
    assert app_js[start:end].count("YOTO_CLIENT_ID") == 2


def test_there_is_no_tier_condition_in_the_blocking_decision(app_js):
    """One gate. The source decides the RECOVERY and nothing else."""
    assert 'y.client_id_verdict === "invalid"' in app_js
    # The blocked test must never be conjoined with a source test.
    assert 'client_id_verdict === "invalid" && ' not in app_js
    assert 'client_id_source === "saved" && ' not in app_js


def test_the_email_case_has_its_own_headline(app_js):
    """Naming the mistake is what visibility failed to do. Being explicit in the
    refusal while being coy in the status line would be inconsistent."""
    assert "That’s an email address, not a Client ID" in app_js
    assert "invalid_email" in app_js


def test_all_three_refusal_bodies_are_present(app_js):
    assert "That looks like an email address, not a Client ID." in app_js
    assert "That looks like a web address, not a Client ID." in app_js
    assert "That doesn’t look like a Client ID." in app_js


def test_the_reassurance_line_is_state_dependent(app_js):
    """"You're still signed in" is false when she isn't, and a reassurance that
    is audibly wrong about her situation costs more trust than it buys.

    The longer line is also the readable form of the server-side ordering
    invariant (app.py set_client_id). If it ever disappears, check that the
    ordering did not change with it.
    """
    assert "Nothing was changed, and you’re still signed in to Yoto." in app_js
    assert '"Nothing was changed."' in app_js


def test_the_client_gate_is_the_deny_list_not_the_32_char_rule(app_js):
    """The client mirror must stay in lockstep with config.validate_client_id.
    A "simplification" to the 32-char test here would refuse legitimate values
    at the confirmation while the server accepted them — the exact
    save-gate/sign-in-gate disagreement one shared rule exists to prevent."""
    fn = app_js[app_js.index("function clientIdVerdict") : app_js.index("const CLIENT_ID_REFUSAL")]
    assert 'reason: "email"' in fn
    assert 'reason: "url"' in fn
    assert 'reason: "spaces"' in fn
    # The 32-char rule appears, and it produces "unusual" — never "invalid".
    assert '{32}$/.test(t)' in fn
    assert fn.index("{32}$/.test(t)") > fn.index('verdict: "invalid", reason: "too_long"')
    assert 'verdict: "unusual"' in fn


def test_the_mask_is_suppressed_when_the_shape_check_fails(app_js):
    """The mask is the summary form of a value that has the expected SHAPE.
    Applied to one that does not it is camouflage — mand…com reads MORE
    code-like than mandydeogie@gmail.com. `unusual` matters as much as
    `invalid`: a 17-character truncation masks to a8OG…tDU, which hides the
    truncation entirely."""
    assert 'const shapeFailed = verdict === "invalid" || verdict === "unusual";' in app_js
    assert "const canReveal = !shapeFailed" in app_js


def test_setting_three_uses_the_literal_template(index_html):
    """Slot 6 is present though empty and permanently hidden. §4.2 says treat
    this as the literal template; carving an exception for one section would be
    the widening §11.5 worked to avoid."""
    start = index_html.index('id="setting-help"')
    end = index_html.index("</section>", start)
    section = index_html[start:end]
    assert "<h3>If you need to ask for help</h3>" in section
    assert 'class="setting-desc"' in section
    assert 'id="helpMsg"' in section
    assert 'class="setting-confirm' not in section
    assert 'class="setting-actions' not in section
    assert 'class="setting-status' not in section


def test_setting_three_has_all_five_rows_and_the_guides_label(index_html):
    for label in ("Version", "Client ID in use", "Where that came from",
                  "Redirect URL", "Where Yoto Maker keeps its files"):
        assert f">{label}</p>" in index_html
    # "Sign-in address" was drafted first and deliberately rejected: the person
    # holding a word at that moment is the helper, reading SETUP-YOTO-CONNECTION.md.
    # (reconciliation) Scoped to the LABEL: the plan's markup comment records the
    # rejection rationale verbatim and legitimately names the phrase, so the bare
    # "not in index_html" from the plan would false-positive on that comment. The
    # guard's actual intent — the phrase is never a visible row label — is checked
    # with the same >label</p> idiom used just above. See final report.
    assert ">Sign-in address</p>" not in index_html


def test_setting_three_is_last(index_html):
    order = [index_html.index(f'id="{el}"')
             for el in ("setting-account", "setting-client-id", "setting-help")]
    assert order == sorted(order)


def test_no_config_value_is_constructed_in_js(app_js):
    """config.py:108 — the port is chosen at runtime if 8777 is busy, so a
    hardcoded frontend redirect URL would be wrong exactly when the row matters
    most."""
    assert "127.0.0.1:8777" not in app_js
    assert "/yoto/callback" not in app_js


def test_the_msg_box_paragraph_rules_exist(styles_css):
    """.setting-confirm p's margin reset is scoped and does not reach .msg-box,
    so without these a <p> takes the UA default 1em margin inside a box with
    12px of padding."""
    assert ".msg-box p { margin: 0 0 10px; }" in styles_css
    assert ".msg-box p:last-child { margin-bottom: 0; }" in styles_css
