"""Convenience entry point so `python -m yoto_maker.repair` runs the repair CLI.

The implementation lives in yoto_maker/yoto/repair.py (next to the Yoto client).
This thin shim exists so the command the maintainer runs is exactly:

    python -m yoto_maker.repair --card-id 1WCvI,gzP2B,7FcVe --apply
"""
import sys

from .yoto.repair import main

if __name__ == "__main__":
    sys.exit(main())
