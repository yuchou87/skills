#!/usr/bin/env python3
"""Merge a source chapter and its translation into a bilingual chapter.

Block model: Markdown is split into blocks separated by blank lines. When the
source and translation have the SAME block count, blocks are paired:

    - heading blocks  -> emit the translated heading only (keeps a single,
      clean TOC; avoids duplicate H1s that md2epub would split into 2 chapters)
    - body blocks     -> emit original block, then translated block

When block counts DIFFER (translator merged/split paragraphs), we cannot align
safely, so we fall back: emit the full translated chapter (intact headings ->
clean TOC), then append the original body under a single non-heading section,
with original headings demoted to bold so they don't pollute the TOC. A warning
is printed to stderr naming the file.

Usage:
    interleave.py <source.md> <translated.md> <output.md>
"""
import re
import sys
from pathlib import Path


def split_blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]


def is_heading(block: str) -> bool:
    return bool(re.match(r"^#{1,6}\s", block.lstrip()))


def demote_heading(block: str) -> str:
    """Turn an ATX heading into bold text so it stays out of the TOC."""
    m = re.match(r"^(#{1,6})\s+(.*)$", block.lstrip(), re.S)
    if m:
        return f"**{m.group(2).strip()}**"
    return block


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("usage: interleave.py <source.md> <translated.md> <output.md>")
    src = split_blocks(Path(sys.argv[1]).read_text(encoding="utf-8"))
    zh = split_blocks(Path(sys.argv[2]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[3])

    parts: list[str] = []

    if len(src) == len(zh):
        for s, z in zip(src, zh):
            if is_heading(s):
                parts.append(z if is_heading(z) else s)
            else:
                parts.append(s)
                parts.append(z)
    else:
        print(
            f"WARN: block count mismatch in {out_path.name} "
            f"(src={len(src)}, zh={len(zh)}); falling back to whole-chapter layout",
            file=sys.stderr,
        )
        parts.extend(zh)
        parts.append("---")
        parts.append("**原文 / Original:**")
        parts.extend(demote_heading(b) if is_heading(b) else b for b in src)

    out_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
