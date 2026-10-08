from __future__ import annotations

import subprocess
from functools import cache
from pathlib import Path


@cache
def pipeline_commit() -> str:
    """Commit hash of the pipeline code, with "-dirty" if there are uncommitted changes."""
    repo = Path(__file__).resolve().parents[2]
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return f"{sha}-dirty" if dirty else sha
