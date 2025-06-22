"""Convenience launcher so that `python subtitle_inserter/run_app.py` works out-of-the-box.

It appends `subtitle_inserter/src` to `sys.path` then imports the real main entry.
"""
from __future__ import annotations

import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from subtitle_inserter.main import main  # noqa: E402  # pylint: disable=wrong-import-position

if __name__ == "__main__":
    main() 