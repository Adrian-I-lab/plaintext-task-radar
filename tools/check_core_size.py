"""Fail when the core modules grow past the line budget.

Counts non-blank lines that are not comments in the six core modules.
Usage: python tools/check_core_size.py [--limit N]
"""

import argparse
import sys
from pathlib import Path

CORE = ("model", "parse", "lint", "radar", "cli", "html")
SRC = Path(__file__).resolve().parent.parent / "src" / "taskradar"


def count(path: Path) -> int:
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return sum(1 for line in lines if line and not line.startswith("#"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=500)
    limit = parser.parse_args(argv).limit
    total = 0
    for name in CORE:
        lines = count(SRC / f"{name}.py")
        total += lines
        print(f"{name + '.py':10} {lines:4}")
    print(f"{'total':10} {total:4} (limit {limit})")
    if total > limit:
        print("core is over the line budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
