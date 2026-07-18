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
