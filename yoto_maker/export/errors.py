"""Failure vocabulary for saving a card to a folder.

These live in their own module because both the runner and the reveal route
raise them, and because a total failure reaches the browser as a bare string:
jobs.py captures only ``str(exc)`` (jobs.py:70-73) and this PR deliberately does
not extend it. So the CAUSE-SPECIFIC sentence is composed here, server-side,
where the cause is known; app.js supplies the fixed first and third paragraphs of
copy.md §5.7 around it.
"""
from __future__ import annotations


class ExportError(RuntimeError):
    """A user-friendly save failure. The message is shown verbatim."""


class NameTooLongError(ValueError):
    """A file or folder name cannot be made to fit Windows' path limit."""


# --- copy.md §5.7, the {reason} table -------------------------------------- #
REASON_NO_SPACE = "This computer looks like it’s out of space."
REASON_PERMISSION = "Windows wouldn’t let Yoto Maker write to your Documents folder."
REASON_TOO_LONG = (
    "The card name is very long, and that made the file names too long for "
    "Windows. Try a shorter name in step 2."
)
REASON_GENERIC = "Something went wrong while writing the files."

# --- copy.md §5.6, the per-track {reason} ---------------------------------- #
# Both are EXISTING in-tree strings, reused rather than reinvented:
#   sources/audiofile.py:46  and  audio/normalize.py:183-185 (its first sentence
#   pair only — the "Technical detail: …" tail is a developer string and must
#   never reach this panel).
REASON_UNREADABLE = "We couldn’t read that file — it may be open in another program."
REASON_CONVERT_FAILED = "We couldn’t convert that audio. It may be an unusual or damaged file."

# --- copy.md §5.5a, the reveal button's own runtime failures ---------------- #
# (a) No folder recorded, or the recorded folder is gone. ONE string for both,
# because the recovery is identical: press save again. "yet" was rejected —
# #exportActions is hidden until a run succeeds, so she DID save; telling her she
# hasn't invites her to doubt her own memory (copy.md §5.5a).
REASON_FOLDER_GONE = (
    "Yoto Maker can’t open that folder any more — it may have been moved or "
    "deleted, or Yoto Maker may have been restarted since you saved it. Press "
    "“📁 Save the files to a folder” again to make a fresh one."
)
# (b) The folder is there and the OS refused. The PATH is rendered beneath this
# sentence in .mono-value, so the message is not a dead end.
REASON_CANNOT_OPEN = "Yoto Maker couldn’t open the folder for you. It’s here:"
