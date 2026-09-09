#!/usr/bin/env python3
"""Build helper: copy the compiled web viewer into the Python package so the
wheel is self-contained (release users never need Node).

Fails loudly if the frontend was not built.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = ROOT / "web" / "dist"
STATIC_DEST = ROOT / "src" / "agentcrash" / "server" / "static"


def main() -> int:
    if not (WEB_DIST / "index.html").is_file():
        print("error: web/dist/index.html missing. Run `cd web && npm run build` first.",
              file=sys.stderr)
        return 1
    if STATIC_DEST.exists():
        shutil.rmtree(STATIC_DEST)
    shutil.copytree(WEB_DIST, STATIC_DEST)
    count = len(list(STATIC_DEST.rglob("*")))
    print(f"copied {count} files from web/dist/ to src/agentcrash/server/static/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())