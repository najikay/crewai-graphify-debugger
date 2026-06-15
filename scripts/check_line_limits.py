#!/usr/bin/env python3
"""CI gate: fail if any .py file under src/ or tests/ exceeds MAX_LINES lines.

Per the submission guidelines (§3.2, §6.6) the 150-line limit applies to test
files as well, so both directories are scanned by default.

Usage::

    python scripts/check_line_limits.py              # scans src/ and tests/
    python scripts/check_line_limits.py --max-lines 150 src/
    python scripts/check_line_limits.py --max-lines 150 src/ tests/ --verbose

Exit codes:
    0  — all files within limit
    1  — one or more files exceed the limit (names printed to stderr)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enforce a maximum source-line count per Python file."
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["src", "tests"],
        metavar="DIR",
        help="Root directories to scan (default: src/ and tests/).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=150,
        metavar="N",
        dest="max_lines",
        help="Maximum allowed lines per file (default: 150).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print a line for every file checked, not just violators.",
    )
    return parser.parse_args()


def _count_lines(path: Path) -> int:
    """Return the number of lines in *path*, excluding trailing blank lines."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return len(text.rstrip("\n").splitlines())


def main() -> int:
    args = _parse_args()
    violations: list[tuple[Path, int]] = []

    for root in args.directories:
        root_path = Path(root)
        if not root_path.exists():
            print(f"[WARN] directory not found, skipping: {root_path}", file=sys.stderr)
            continue

        for py_file in sorted(root_path.rglob("*.py")):
            line_count = _count_lines(py_file)
            over_limit = line_count > args.max_lines

            if over_limit:
                violations.append((py_file, line_count))
                print(
                    f"[FAIL] {py_file}  ({line_count} lines > {args.max_lines} limit)",
                    file=sys.stderr,
                )
            elif args.verbose:
                print(f"[ OK ] {py_file}  ({line_count} lines)")

    if violations:
        print(
            f"\n{len(violations)} file(s) exceed the {args.max_lines}-line limit.",
            file=sys.stderr,
        )
        return 1

    total = sum(1 for d in args.directories for _ in Path(d).rglob("*.py") if Path(d).exists())
    print(f"All {total} file(s) are within the {args.max_lines}-line limit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
