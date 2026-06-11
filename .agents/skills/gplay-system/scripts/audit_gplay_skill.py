from __future__ import annotations

import re
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "SKILL.md",
    "references/project-standards.md",
    "references/subskill-standard.md",
    "references/usage-guide.md",
]
MOJIBAKE_MARKERS = ["�", "锟", "閳", "娑", "閸", "閹", "濡", "闂", "鐠", "缁"]


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        path = SKILL_ROOT / rel
        if not path.exists():
            errors.append(f"missing required file: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = [marker for marker in MOJIBAKE_MARKERS if marker in text]
        if hits:
            warnings.append(f"{rel}: possible mojibake markers {hits[:4]}")
        if "TODO" in text or "[TODO" in text:
            warnings.append(f"{rel}: TODO marker remains")

    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    meta = parse_frontmatter(skill_text)
    if meta.get("name") != "gplay-system":
        errors.append("SKILL.md: frontmatter name must be gplay-system")
    description = meta.get("description", "")
    if not description.startswith("Use when"):
        errors.append("SKILL.md: description must start with 'Use when'")

    print("GPlay skill audit")
    print(f"root: {SKILL_ROOT}")
    if warnings:
        print("\nwarnings:")
        for warning in warnings:
            print(f"- {warning}")
    if errors:
        print("\nerrors:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("\nresult: audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
