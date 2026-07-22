"""The Client ID verdict: a deny-list hard gate and a 32-character advisory.

The two rules are DELIBERATELY NOT THE SAME RULE, and that is the single most
important fact in this module. The gate that hard-blocks fires only on shapes
that are wrong regardless of format. The 32-character alphanumeric rule is
knowledge about a third party's current format, the app has no way to learn
that it has changed, and its failure mode as a hard gate is a total lockout
with no override — so it only ever advises.

Do not "simplify" the gate into the 32-character check. See
docs/design-handoffs/configuration-surface/overview.md §13.2.
"""
from __future__ import annotations

import pytest

from yoto_maker.config import DEFAULT_YOTO_CLIENT_ID, validate_client_id


# --- the two values that must never be hard-blocked ---------------------------

def test_the_shipped_default_scores_ok():
    """The one failure this whole design cannot recover from.

    A validator that rejects the shipped default bricks the app on first run for
    every user, and "Go back to the built-in one" would go back to a value the
    app refuses. overview.md §13.2 marks this test required, not optional.
    """
    assert validate_client_id(DEFAULT_YOTO_CLIENT_ID) == ("ok", None)


def test_the_test_suites_own_client_id_is_not_blocked():
    """tests/conftest.py:26 injects YOTO_CLIENT_ID="test_client_id".

    14 characters with an underscore. It contains no @, no whitespace, no / and
    no :, so it passes the gate — which is why uniform blocking across all three
    tiers (overview.md §13.5) does not block every test run in this repo.

    Had the gate been the strict 32-char allow-list, this assertion would fail
    and so would the entire suite. That is the point of the assertion.
    """
    verdict, _ = validate_client_id("test_client_id")
    assert verdict != "invalid"
    assert verdict == "unusual"


# --- the deny-list: invalid regardless of what format Yoto adopts -------------

@pytest.mark.parametrize(
    "value,reason",
    [
        ("mandydeogie@gmail.com", "email"),          # the observed real failure
        ("someone@example.co.uk", "email"),
        ("http://127.0.0.1:8777/yoto/callback", "email" if False else "url"),
        ("127.0.0.1:8777", "url"),
        ("some/path", "url"),
        ("a8OGO6EfbWit5tDU UrOz0g49s49NQoU1", "spaces"),
        ("a8OGO6EfbWit\n5tDUUrOz0g49s49", "spaces"),
        # NOTE (reconciliation): the plan parametrized this as "charset", but a
        # </script> contains a "/", and validate_client_id checks the url deny
        # (/ :) before the charset deny (< >), so it reports "url". The
        # implementation is preserved verbatim from the plan; charset detection
        # is guarded independently below by the "<b>" case. See final report.
        ("<script>alert(1)</script>", "url"),
        ("a" * 129, "too_long"),
        ("", "length"),
        ("   ", "length"),
        (None, "length"),
    ],
)
def test_deny_list_values_are_invalid(value, reason):
    assert validate_client_id(value) == ("invalid", reason)


def test_an_email_inside_a_url_reports_email():
    """@ is checked before / and :.

    An email address is the more actionable diagnosis and it is the incident's
    actual case; a value with both gets the message that names the mistake she
    made.
    """
    assert validate_client_id("http://x/mandy@gmail.com") == ("invalid", "email")


# --- the exclusions: these demonstrate the principle, not merely apply it ------

@pytest.mark.parametrize(
    "value",
    [
        "yotoplay.com",                               # a dot is NOT denied
        "123-abc.apps.googleusercontent.com",         # dotted identifiers exist
        "a8OGO6Ef-bWit-5tDU-UrOz-0g49s49NQoU1",       # hyphens are NOT denied
        "a8OGO6Ef_bWit_5tDUUrOz0g49s49NQoU",          # underscores are NOT denied
        "a8OGO6EfbWit5tDUU",                          # a truncated paste
        "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1EXTRA40CHAR",  # a 40-char future format
    ],
)
def test_narrow_deny_list_leaves_these_usable(value):
    """Each of these is warned about and MUST remain usable.

    - and _ are the two commonest characters in machine identifiers; denying
    them would be the fastest possible way to build the lockout this rule exists
    to prevent. A 40-character ID is what happens if Yoto changes its format
    tomorrow — under a strict allow-list every legitimate new ID would be
    hard-blocked and the app would tell the user, confidently and in red, that
    her correct value is wrong. Recovery would need a code change and a release.
    """
    verdict, _ = validate_client_id(value)
    assert verdict == "unusual"


def test_the_32_char_rule_is_advice_and_never_hard_blocks():
    """Stated as its own assertion so a future 'simplification' trips a test
    whose name says what it broke."""
    for value in ("short", "a" * 31, "a" * 33, "MiXeD1234567890abcdefGHIJKLMNOP"):
        verdict, _ = validate_client_id(value)
        assert verdict != "invalid", value


def test_surrounding_whitespace_is_trimmed_not_rejected():
    """A paste that grabbed a trailing newline is the normal case, not an error.
    Interior whitespace is what means 'a phrase'; the trim is what makes that
    distinction possible."""
    assert validate_client_id(f"  {DEFAULT_YOTO_CLIENT_ID}\n") == ("ok", None)


def test_verdict_and_reason_are_only_meaningful_as_a_pair():
    """'charset' appears under BOTH verdicts and means different things.

    invalid+charset = contains < or >. unusual+charset = passes the deny-list
    but is not 32 alphanumerics. The verdict disambiguates; nothing may branch
    on the reason alone.
    """
    assert validate_client_id("<b>") == ("invalid", "charset")
    assert validate_client_id("not-32-chars") == ("unusual", "charset")


# --- what the frontend actually reads -----------------------------------------

def test_status_carries_the_verdict_and_the_config_summary(client):
    """Both fields are derived from the ONE function in config.py.

    A second implementation is how the save gate and the sign-in gate come to
    disagree, and a user allowed to save a value she is then not allowed to use
    is in a worse state than the one this change is fixing.
    """
    body = client.get("/api/status").json()

    assert body["yoto"]["client_id_verdict"] in ("ok", "unusual", "invalid")
    assert "client_id_reason" in body["yoto"]

    cfg = body["config"]
    assert cfg["version"]
    # Rendered from auth._redirect_uri(), the same function start_login() uses,
    # so the string the user reads out to a helper and the string sent to Yoto
    # cannot disagree. That is the entire reason the row exists.
    assert cfg["redirect_uri"].startswith("http://127.0.0.1:")
    assert cfg["redirect_uri"].endswith("/yoto/callback")
    assert cfg["data_dir"]


def test_redirect_uri_is_not_a_frontend_constant(client):
    """config.py:108 notes the port is chosen at runtime if 8777 is busy, so a
    hardcoded frontend string would be wrong exactly when it matters most."""
    from yoto_maker.yoto import auth

    assert client.get("/api/status").json()["config"]["redirect_uri"] == auth.redirect_uri()


# --- the save gate ------------------------------------------------------------

def test_saving_an_email_is_refused(client):
    r = client.post("/api/yoto/client-id", json={"client_id": "mandydeogie@gmail.com"})
    assert r.status_code == 400
    assert r.json()["reason"] == "email"


def test_the_refusal_runs_BEFORE_the_write_and_BEFORE_logout(client, monkeypatch):
    """The invariant the whole of Item A rests on, asserted as ordering.

    The refusal copy ends with "Nothing was changed, and you're still signed in
    to Yoto." That sentence is TRUE ONLY BECAUSE OF THIS ORDERING. If a refactor
    moves the verdict check below get_settings().set(...) or below logout(), the
    copy silently becomes a lie about the one thing this change exists to
    guarantee — a user with a working sign-in must never lose it to a typo.

    Asserting "the value wasn't saved" alone would not catch a check placed
    between the write and logout(). This asserts NEITHER side effect fired.

    IF THIS TEST FAILS, DO NOT RELAX IT. Either the ordering regressed, or the
    ordering changed on purpose and copy.md §4c's reassurance line must change
    with it.
    """
    from yoto_maker.server import app as app_mod

    calls = []
    monkeypatch.setattr(app_mod, "logout", lambda: calls.append("logout"))

    from yoto_maker.settings import get_settings
    before = get_settings().get("yoto_client_id")

    r = client.post("/api/yoto/client-id", json={"client_id": "mandydeogie@gmail.com"})

    assert r.status_code == 400
    assert calls == [], "logout() ran on a refused save — a working sign-in was destroyed"
    assert get_settings().get("yoto_client_id") == before, "the refused value was written"


@pytest.mark.parametrize(
    "value,reason",
    [("someone@example.com", "email"),
     ("http://127.0.0.1:8777/yoto/callback", "url"),
     ("two words here", "spaces"),
     ("a" * 200, "too_long")],
)
def test_every_invalid_reason_reaches_the_client(client, value, reason):
    r = client.post("/api/yoto/client-id", json={"client_id": value})
    assert r.status_code == 400
    assert r.json()["reason"] == reason
    assert r.json()["error"]


def test_an_unusual_value_still_saves(client):
    """Soft, not hard. A truncated paste is warned about and then allowed —
    the false-positive cost of hard-blocking it is a total lockout."""
    r = client.post("/api/yoto/client-id", json={"client_id": "a8OGO6EfbWit5tDUU"})
    assert r.status_code == 200
