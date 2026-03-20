"""Pre-commit hook: run ruff check + black --check on backend/app/ before any git commit."""

import json
import re
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent.parent / "backend"


def main() -> None:
    data = json.load(sys.stdin)
    cmd = data.get("tool_input", {}).get("command", "")

    # Only intercept git commit commands
    if not re.search(r"git\b.*\bcommit\b", cmd):
        return

    failed = False

    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "app/"],
        cwd=BACKEND_DIR,
    )
    if result.returncode != 0:
        failed = True

    result = subprocess.run(
        [sys.executable, "-m", "black", "--check", "app/"],
        cwd=BACKEND_DIR,
    )
    if result.returncode != 0:
        failed = True

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
