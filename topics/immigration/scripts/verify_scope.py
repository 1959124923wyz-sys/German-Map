#!/usr/bin/env python3
"""Fail if an immigration branch commit modifies files outside its ownership.

Call with the merge-base against origin/main, and the *actual immigration head*
rather than a pull-request synthetic merge commit. No third-party dependencies.
"""
from __future__ import annotations

import argparse
from pathlib import PurePosixPath
import re
import subprocess
import sys

TOPIC_PREFIX = "topics/immigration/"
WORKFLOW_PATTERN = re.compile(r"^\.github/workflows/immigration-[a-z0-9][a-z0-9._-]*\.ya?ml$")


def path_allowed(path: str) -> bool:
    if not path or "\x00" in path or "\n" in path or "\\" in path:
        return False
    parts = PurePosixPath(path).parts
    if any(part in (".", "..") for part in parts):
        return False
    return (path.startswith(TOPIC_PREFIX) and len(path) > len(TOPIC_PREFIX)) or bool(
        WORKFLOW_PATTERN.fullmatch(path)
    )


def find_violations(paths: list[str]) -> list[str]:
    return sorted({path for path in paths if not path_allowed(path)})


def changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "-z", "--no-ext-diff", "--no-renames",
         f"{base}..{head}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return [p.decode("utf-8", errors="surrogateescape") for p in result.stdout.split(b"\x00") if p]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="merge-base with origin/main")
    parser.add_argument("--head", default="HEAD", help="immigration branch commit")
    args = parser.parse_args()
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", args.base, args.head],
            check=True, capture_output=True,
        )
        paths = changed_paths(args.base, args.head)
    except subprocess.CalledProcessError as exc:
        print(f"SCOPE CHECK ERROR: git operation failed: {exc}", file=sys.stderr)
        return 2
    violations = find_violations(paths)
    print(f"Immigration scope: checked {len(paths)} changed path(s) from {args.base} to {args.head}")
    if violations:
        print("FAILED: out-of-scope changes:", file=sys.stderr)
        for path in violations:
            print(f"  - {path}", file=sys.stderr)
        return 1
    print("PASS: all changed files belong to immigration topic or immigration-only CI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
