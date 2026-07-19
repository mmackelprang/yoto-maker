"""Self-update logic: version comparison, release check, swapper script."""
from __future__ import annotations

import httpx
import pytest

from yoto_maker import updater


@pytest.mark.parametrize("latest,current,expected", [
    ("0.1.4", "0.1.3", True),
    ("v0.1.4", "0.1.3", True),
    ("0.2.0", "0.1.9", True),
    ("1.0.0", "0.9.9", True),
    ("0.1.3", "0.1.3", False),
    ("0.1.2", "0.1.3", False),
    ("v0.1.3", "0.1.3", False),
])
def test_is_newer(latest, current, expected):
    assert updater.is_newer(latest, current) is expected


def test_parse_version():
    assert updater.parse_version("v0.1.4") == (0, 1, 4)
    assert updater.parse_version("2.10.3-beta") == (2, 10, 3)
    assert updater.parse_version("") == (0,)


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def test_check_for_update_available(monkeypatch):
    updater._cache.update(ts=0.0, data=None)  # clear cache
    monkeypatch.setattr(updater, "__version__", "0.1.3")
    payload = {
        "tag_name": "v0.1.4",
        "html_url": "https://github.com/mmackelprang/yoto-maker/releases/tag/v0.1.4",
        "assets": [{"name": "YotoMaker.exe", "browser_download_url": "https://example/YotoMaker.exe"}],
    }
    monkeypatch.setattr(updater.httpx, "get", lambda *a, **k: _Resp(payload))
    info = updater.check_for_update(force=True)
    assert info["latest"] == "0.1.4"
    assert info["update_available"] is True
    assert info["download_url"] == "https://example/YotoMaker.exe"


def test_check_for_update_up_to_date(monkeypatch):
    updater._cache.update(ts=0.0, data=None)
    monkeypatch.setattr(updater, "__version__", "0.1.4")
    payload = {"tag_name": "v0.1.4", "assets": []}
    monkeypatch.setattr(updater.httpx, "get", lambda *a, **k: _Resp(payload))
    info = updater.check_for_update(force=True)
    assert info["update_available"] is False


def test_check_for_update_offline_is_quiet(monkeypatch):
    updater._cache.update(ts=0.0, data=None)

    def boom(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(updater.httpx, "get", boom)
    info = updater.check_for_update(force=True)
    assert info["update_available"] is False   # never raises
    assert info["current"] == updater.__version__


def test_swapper_script_contents(temp_config, tmp_path):
    new_exe = tmp_path / "YotoMaker.update.exe"
    cur_exe = tmp_path / "YotoMaker.exe"
    bat = updater._write_swapper(new_exe, cur_exe)
    text = bat.read_text()
    assert bat.exists() and bat.suffix == ".bat"
    # atomic same-dir rename of new over current, then relaunch
    assert f'move /y "{new_exe}" "{cur_exe}"' in text
    assert f"Start-Process -FilePath '{cur_exe}'" in text  # robust relaunch
    assert "goto retry" in text  # waits for the lock to release


def test_clean_child_env_strips_pyinstaller_vars(monkeypatch):
    # A relaunched onefile exe must NOT inherit the parent's PyInstaller runtime
    # vars, or its bootloader points at the parent's deleted temp dir and hangs.
    monkeypatch.setenv("_MEIPASS", r"C:\Temp\_MEI123")
    monkeypatch.setenv("_PYI_APPLICATION_HOME_DIR", r"C:\Temp\_MEI123")
    monkeypatch.setenv("_PYI_ARCHIVE_FILE", r"C:\app.exe")
    monkeypatch.setenv("_PYI_PARENT_PROCESS_LEVEL", "1")
    monkeypatch.setenv("PATH_KEEP_ME", "yes")
    env = updater._clean_child_env()
    assert not any(k.startswith("_PYI") or k.startswith("_MEIPASS") for k in env)
    assert env.get("PATH_KEEP_ME") == "yes"  # ordinary vars are preserved


def test_apply_update_requires_frozen(temp_config, monkeypatch):
    # running from source (not frozen) must refuse to self-update
    monkeypatch.setattr(updater.sys, "frozen", False, raising=False)
    with pytest.raises(updater.UpdateError):
        updater.apply_update("https://example/YotoMaker.exe")
