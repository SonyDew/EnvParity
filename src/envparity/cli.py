"""Command-line interface for comparing .env files without printing values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import EnvError, compare, read_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="envparity",
        description="Compare two .env files without printing their values.",
    )
    parser.add_argument("left", type=Path, help="first .env file")
    parser.add_argument("right", type=Path, help="second .env file")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    parser.add_argument("--keys-only", action="store_true", help="compare key presence only")
    parser.add_argument("--ignore", action="append", default=[], metavar="KEY", help="ignore a key (repeatable)")
    args = parser.parse_args(argv)

    try:
        left = read_env(args.left)
        right = read_env(args.right)
        result = compare(left, right, ignored=set(args.ignore), keys_only=args.keys_only)
    except EnvError as error:
        print(f"envparity: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print("Files match." if result.equal else "Files differ.")
        for label, keys in (
            ("Only in first file", result.only_left),
            ("Only in second file", result.only_right),
            ("Different values", result.changed),
        ):
            if keys:
                print(f"{label}: {', '.join(keys)}")
        print(f"Keys: {result.left_count} / {result.right_count}; unchanged: {result.unchanged}")
    return 0 if result.equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
