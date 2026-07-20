"""End-to-end API tests via FastAPI TestClient (no real Yoto network)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from yoto_maker.server.app import app
from yoto_maker.server.draft import get_draft


@pytest.fixture
def client(temp_config):
    get_draft().reset()
    return TestClient(app)


def test_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "Yoto Maker"
    assert "tools" in body and "yoto" in body
    assert body["ai_available"] is False


def test_icons_listed_and_served(client):
    r = client.get("/api/icons")
    assert r.status_code == 200
    icons = r.json()["icons"]
    assert len(icons) == 10
    one = client.get(f"/api/icons/{icons[0]['id']}.png")
    assert one.status_code == 200
    assert one.headers["content-type"] == "image/png"


def test_add_file_then_label(client, sample_mp3):
    with open(sample_mp3, "rb") as fh:
        r = client.post("/api/tracks/file", files={"file": ("sample.mp3", fh, "audio/mpeg")})
    assert r.status_code == 200
    track = r.json()["track"]
    assert track["title"] == "Sample Song"

    # name + picture
    assert client.post("/api/card/name", json={"name": "My Card"}).status_code == 200
    assert client.post("/api/picture/library", json={"icon_id": "star"}).status_code == 200

    draft = client.get("/api/draft").json()
    assert draft["card_name"] == "My Card"
    assert draft["has_picture"] is True
    assert len(draft["tracks"]) == 1

    # label builds and serves a real PDF
    assert client.post("/api/label").status_code == 200
    pdf = client.get("/api/label.pdf")
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"


def test_rename_reorder_delete(client, sample_mp3):
    def add():
        with open(sample_mp3, "rb") as fh:
            return client.post("/api/tracks/file", files={"file": ("s.mp3", fh, "audio/mpeg")}).json()["track"]["id"]

    a, b = add(), add()
    # rename
    assert client.patch(f"/api/tracks/{a}", json={"title": "Renamed"}).json()["track"]["title"] == "Renamed"
    # reorder
    assert client.post("/api/tracks/reorder", json={"order": [b, a]}).status_code == 200
    order = [t["id"] for t in client.get("/api/draft").json()["tracks"]]
    assert order == [b, a]
    # per-track icon
    assert client.post(f"/api/tracks/{a}/icon", json={"icon_id": "rocket"}).status_code == 200
    # delete
    assert client.delete(f"/api/tracks/{b}").status_code == 200
    assert len(client.get("/api/draft").json()["tracks"]) == 1


def test_send_requires_connection(client, sample_mp3):
    with open(sample_mp3, "rb") as fh:
        client.post("/api/tracks/file", files={"file": ("s.mp3", fh, "audio/mpeg")})
    client.post("/api/card/name", json={"name": "X"})
    r = client.post("/api/send")
    assert r.status_code == 409
    assert r.json()["need_connect"] is True


def test_send_requires_name_and_tracks(client, sample_mp3):
    # no tracks
    assert client.post("/api/send").status_code in (400, 409)
    # tracks but no name
    with open(sample_mp3, "rb") as fh:
        client.post("/api/tracks/file", files={"file": ("s.mp3", fh, "audio/mpeg")})
    r = client.post("/api/send")
    assert r.status_code in (400, 409)


def test_bad_youtube_link(client):
    r = client.post("/api/tracks/youtube", json={"url": "https://example.com/not-youtube"})
    assert r.status_code == 400
    assert "youtube" in r.json()["error"].lower()


def test_remove_sponsors_setting(client):
    # default on
    assert client.get("/api/status").json()["remove_sponsors"] is True
    # can turn off and it persists in status
    assert client.post("/api/settings/remove-sponsors", json={"enabled": False}).json()["remove_sponsors"] is False
    assert client.get("/api/status").json()["remove_sponsors"] is False
    # and back on
    client.post("/api/settings/remove-sponsors", json={"enabled": True})
    assert client.get("/api/status").json()["remove_sponsors"] is True


def test_picture_auto_without_source_errors(client, sample_mp3):
    # a file upload has no thumbnail, so auto should fail cleanly
    with open(sample_mp3, "rb") as fh:
        client.post("/api/tracks/file", files={"file": ("s.mp3", fh, "audio/mpeg")})
    r = client.post("/api/picture/auto")
    assert r.status_code == 400


def test_auto_apply_picture_from_suggested(temp_config):
    from PIL import Image

    from yoto_maker.server.app import _auto_apply_picture_if_absent

    draft = get_draft()
    draft.reset()
    img = temp_config.work_dir / "thumb.png"
    Image.new("RGB", (400, 300), (30, 140, 90)).save(img)
    draft.add_track("Song", temp_config.work_dir / "a.mp3", suggested_image_path=img)

    assert draft.picture_path is None            # nothing yet
    _auto_apply_picture_if_absent()
    assert draft.picture_path is not None and draft.picture_path.exists()
    assert draft.picture_source == "auto"


def test_auto_apply_picture_skips_when_no_art_and_when_already_set(temp_config):
    from PIL import Image

    from yoto_maker.server.app import _auto_apply_picture_if_absent

    draft = get_draft()
    draft.reset()
    # track with no suggested image -> stays without a picture
    draft.add_track("Song", temp_config.work_dir / "a.mp3", suggested_image_path=None)
    _auto_apply_picture_if_absent()
    assert draft.picture_path is None

    # if a picture is already chosen, auto-apply must NOT overwrite it
    chosen = temp_config.work_dir / "chosen.png"
    Image.new("RGB", (10, 10), (0, 0, 0)).save(chosen)
    draft.picture_path = chosen
    draft.picture_source = "upload"
    later = temp_config.work_dir / "thumb.png"
    Image.new("RGB", (50, 50), (1, 2, 3)).save(later)
    draft.tracks[0].suggested_image_path = later
    _auto_apply_picture_if_absent()
    assert draft.picture_path == chosen           # unchanged
    assert draft.picture_source == "upload"


def test_emoji_list_and_set(client):
    r = client.get("/api/emoji")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True          # Segoe UI Emoji present on Windows CI
    assert len(body["emojis"]) > 20 and "🐶" in body["emojis"]

    # picking an emoji sets the label picture (and an editable source)
    r = client.post("/api/picture/emoji", json={"emoji": "🐶"})
    assert r.status_code == 200
    draft = client.get("/api/draft").json()
    assert draft["has_picture"] is True and draft["has_source"] is True
    assert draft["picture_source"] == "emoji"
    assert client.get("/api/picture.png").status_code == 200


def test_picture_crop_and_source(client):
    # picking a library icon stores an editable source
    assert client.post("/api/picture/library", json={"icon_id": "star"}).status_code == 200
    draft = client.get("/api/draft").json()
    assert draft["has_picture"] is True and draft["has_source"] is True
    assert client.get("/api/picture/source.png").status_code == 200

    # crop it (coords in source pixels) → picture updates, no error
    r = client.post("/api/picture/crop", json={"x": 20, "y": 20, "w": 200, "h": 200})
    assert r.status_code == 200
    assert client.get("/api/picture.png").status_code == 200
    # out-of-bounds box is clamped, not an error
    assert client.post("/api/picture/crop", json={"x": -50, "y": 0, "w": 99999, "h": 99999}).status_code == 200


def test_picture_crop_without_source_errors(client):
    client.post("/api/draft/reset")
    assert client.post("/api/picture/crop", json={"x": 0, "y": 0, "w": 10, "h": 10}).status_code == 400
    assert client.get("/api/picture/source.png").status_code == 404


def test_reset(client, sample_mp3):
    with open(sample_mp3, "rb") as fh:
        client.post("/api/tracks/file", files={"file": ("s.mp3", fh, "audio/mpeg")})
    client.post("/api/draft/reset")
    assert client.get("/api/draft").json()["tracks"] == []


def test_upload_filename_cannot_escape(client, sample_mp3, temp_config):
    # A path-traversal filename must be reduced to its basename.
    with open(sample_mp3, "rb") as fh:
        r = client.post("/api/tracks/file", files={"file": (r"..\..\evil.mp3", fh, "audio/mpeg")})
    assert r.status_code == 200
    uploads = temp_config.work_dir / "uploads"
    assert (uploads / "evil.mp3").exists()          # landed safely inside uploads
    # nothing wrote outside the uploads dir
    assert not (temp_config.work_dir.parent / "evil.mp3").exists()


def test_origin_guard_blocks_cross_site(client):
    # Cross-site POST is rejected...
    r = client.post("/api/draft/reset", headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    # ...loopback origin is allowed...
    ok = client.post("/api/draft/reset", headers={"origin": "http://127.0.0.1:8777"})
    assert ok.status_code == 200
    # ...and GETs are never blocked by origin.
    assert client.get("/api/draft", headers={"origin": "https://evil.example"}).status_code == 200


def test_status_reports_client_id_source_and_mask(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "builtin"
    assert "…" in body["yoto"]["client_id_masked"]


def test_status_omits_the_full_client_id_when_builtin(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "builtin"
    assert body["yoto"]["client_id_full"] is None


def test_status_reports_the_full_client_id_when_saved(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    client.post("/api/yoto/client-id", json={"client_id": "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1"})
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "saved"
    assert body["yoto"]["client_id_full"] == "a8OGO6EfbWit5tDUUrOz0g49s49NQoU1"
    assert body["yoto"]["client_id_masked"] == "a8OG…oU1"


def test_status_reports_the_full_client_id_when_set_by_env(client, monkeypatch):
    monkeypatch.setenv("YOTO_CLIENT_ID", "envSetByS0meoneElse00000000000x1")
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_source"] == "env"
    # env is the one state where the value is not discoverable anywhere else, so
    # it is the state the disclosure matters most in (overview.md §11.4).
    assert body["yoto"]["client_id_full"] == "envSetByS0meoneElse00000000000x1"


def test_status_full_equals_masked_for_a_short_saved_value(client, monkeypatch):
    """The frontend omits the toggle by comparing these two, never by re-implementing
    mask_client_id()'s length rule. This test pins the case that comparison exists for."""
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    client.post("/api/yoto/client-id", json={"client_id": "mine"})
    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_masked"] == body["yoto"]["client_id_full"] == "mine"


def test_check_reports_not_connected_with_no_saved_sign_in(client):
    r = client.post("/api/yoto/check")
    assert r.status_code == 200
    assert r.json() == {"state": "not_connected"}


def test_check_reports_connected(client, monkeypatch):
    import time

    from yoto_maker.yoto import auth

    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})
    assert client.post("/api/yoto/check").json() == {"state": "connected"}


def test_check_reports_broken(client, monkeypatch):
    import time

    from yoto_maker.yoto import auth

    class Rejecting:
        status_code = 401

        def raise_for_status(self):
            import httpx
            raise httpx.HTTPStatusError("nope", request=None, response=None)

        def json(self):
            return {}

    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    monkeypatch.setattr(auth.httpx, "post", lambda *a, **k: Rejecting())
    assert client.post("/api/yoto/check").json() == {"state": "broken"}


def test_check_reports_unknown_when_offline(client, monkeypatch):
    import time

    from yoto_maker.yoto import auth

    def boom(*a, **k):
        raise OSError("no route to host")

    auth._save_tokens({"access_token": "old", "refresh_token": "RT", "expires_at": time.time() - 10})
    monkeypatch.setattr(auth.httpx, "post", boom)
    assert client.post("/api/yoto/check").json() == {"state": "unknown", "reason": "offline"}


def test_saving_a_client_id_signs_the_user_out(client, monkeypatch, temp_config):
    import time

    from yoto_maker.yoto import auth

    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})
    assert temp_config.token_path.exists()

    r = client.post("/api/yoto/client-id", json={"client_id": "  mine  "})
    assert r.status_code == 200
    # Tokens are minted per Client ID. Keeping the old sign-in would leave the
    # app reporting "connected" while every upload failed.
    assert not temp_config.token_path.exists()
    assert r.json()["yoto"]["connected"] is False
    assert r.json()["yoto"]["client_id_source"] == "saved"

    body = client.get("/api/status").json()
    assert body["yoto"]["client_id_masked"] == "mine"  # short: masking would reveal it anyway


def test_saving_an_empty_client_id_is_rejected(client):
    r = client.post("/api/yoto/client-id", json={"client_id": "   "})
    assert r.status_code == 400


def test_deleting_the_client_id_reverts_and_signs_out(client, monkeypatch, temp_config):
    import time

    from yoto_maker import config as cfg
    from yoto_maker.yoto import auth

    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    client.post("/api/yoto/client-id", json={"client_id": "mine"})
    auth._save_tokens({"access_token": "AT", "expires_at": time.time() + 999})

    r = client.request("DELETE", "/api/yoto/client-id")
    assert r.status_code == 200
    assert not temp_config.token_path.exists()
    assert r.json()["yoto"]["client_id_source"] == "builtin"
    assert cfg.resolve_client_id() == cfg.DEFAULT_YOTO_CLIENT_ID


def test_deleting_when_nothing_is_saved_is_harmless(client, monkeypatch):
    monkeypatch.delenv("YOTO_CLIENT_ID", raising=False)
    r = client.request("DELETE", "/api/yoto/client-id")
    assert r.status_code == 200
    assert r.json()["yoto"]["client_id_source"] == "builtin"


def test_callback_renders_the_cancel_page_on_error(client, temp_config):
    """A denied/cancelled sign-in renders the cancel page and never touches tokens.

    This is the automated stand-in for a manual "press Cancel on Yoto's site"
    step, which is unrunnable: Yoto's hosted sign-in is Auth0 universal login,
    which exposes no Cancel/Deny control for a first-party client. The only
    route to a consent screen is completing an authentication, so no agent or
    human can reach the cancel path through the browser. The handler branches
    purely on the ``error`` query param, so driving it directly is faithful.
    """
    r = client.get("/yoto/callback", params={"error": "access_denied"})
    assert r.status_code == 200
    assert "Sign-in was cancelled. You can close this tab and try again." in r.text
    # The error branch returns before finish_login(), so no sign-in is written.
    assert not temp_config.token_path.exists()


def test_callback_error_branch_ignores_any_code(client, temp_config):
    """``error`` wins over ``code`` — the handler must not try to redeem it."""
    r = client.get("/yoto/callback", params={"error": "access_denied", "code": "ignored"})
    assert r.status_code == 200
    assert "Sign-in was cancelled." in r.text
    assert not temp_config.token_path.exists()
