"""50-stock portfolio app entrypoint for the Data Factory Floor walkthrough."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = next(
    (parent for parent in Path(__file__).resolve().parents if (parent / "fintools").is_dir()),
    Path(__file__).resolve().parents[4],
)
BASE_DIR = Path(__file__).resolve().parent.parent

for p in [REPO_ROOT, BASE_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.app_views import main  # noqa: E402

if __name__ == "__main__":
    main()
