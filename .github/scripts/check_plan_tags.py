#!/usr/bin/env python3
"""Fail if a docs feature page has no plan tag in its frontmatter.

Every page under the checked directories must list at least one of
`oss`, `team`, `enterprise` in its `tags` frontmatter. `mirrord mcp`
reads these tags to answer which plan a feature needs, so the set has
to stay complete.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs"
CHECKED_DIRS = ["using-mirrord", "sharing-the-cluster", "use-cases"]
PLAN_TAGS = {"oss", "team", "enterprise"}


def frontmatter(text: str) -> str | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return match.group(1) if match else None


def tags(block: str) -> set[str]:
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("tags:"):
            continue
        inline = line[len("tags:"):].strip()
        if inline:
            # tags: ["team", "enterprise"]
            return {t.strip().strip("\"'") for t in inline.strip("[]").split(",")}
        found = set()
        for item in lines[i + 1:]:
            stripped = item.strip()
            if not stripped.startswith("- "):
                break
            found.add(stripped[2:].strip().strip("\"'"))
        return found
    return set()


def main() -> int:
    failures = []
    for directory in CHECKED_DIRS:
        base = DOCS_ROOT / directory
        if not base.is_dir():
            print(f"{base}: checked directory not found, update CHECKED_DIRS")
            return 1
        for page in sorted(base.rglob("*.md")):
            block = frontmatter(page.read_text(encoding="utf-8"))
            if block is None or not tags(block) & PLAN_TAGS:
                failures.append(page.relative_to(DOCS_ROOT.parent))
    for page in failures:
        print(f"{page}: missing plan tag (one of {', '.join(sorted(PLAN_TAGS))})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
