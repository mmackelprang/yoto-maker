"""Show the user the folder, in her own file manager.

The browser cannot do this. A ``file:///`` link from an ``http://`` page is
refused **silently** — it must not be shipped and must not be "tried first" — and
a ZIP download lands in Downloads and asks her to unzip it, which is precisely
the file management DESIGN.md §2 promises she never faces.

So the server does it, and that is sound here for configuration-surface §7.8's
reason, unchanged: the app binds to 127.0.0.1 (config.py:198) with no
authentication, so *the browser, the server, the OS account and the person are
all the same.* There is nothing for a gate to gate.

**The caller never supplies a path.** app.py remembers the folder it last wrote
and passes that. Handing an arbitrary caller-supplied string to the shell is a
foot-gun with no upside, and the UI never needs it — there is exactly one folder
this button can mean (overview.md §7.3).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .errors import REASON_CANNOT_OPEN, ExportError

log = logging.getLogger("yoto_maker.export")


def reveal_supported() -> bool:
    """Whether this machine can be asked to show a folder.

    ``os.startfile`` is stdlib and Windows-only, so a PyInstaller-frozen build
    needs no hook — but confirm it in the .exe rather than take that on trust
    (overview.md §16.2 item 5).

    When this is False the UI **omits** the button rather than disabling it, and
    shows the full path instead (copy.md §5.5). Omitted, never disabled —
    configuration-surface §3.5.2 and §13.5.
    """
    return hasattr(os, "startfile")


def reveal_folder(folder: Path) -> None:
    if not reveal_supported():
        raise ExportError(REASON_CANNOT_OPEN)
    try:
        os.startfile(str(folder))  # noqa: S606 - a path this process itself wrote
    except OSError as exc:
        log.warning("save: could not open %s: %s", folder, exc)
        raise ExportError(REASON_CANNOT_OPEN) from exc
