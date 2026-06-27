#!/usr/bin/env python3
"""Clean assembled Markdown so the repackaged EPUB validates cleanly.

Two idempotent passes, applied only OUTSIDE fenced code blocks (so code text
and fence info strings like ```` ```{data-type=...} ```` are never touched):

1. Flatten dead cross-reference links. The source EPUB's internal hrefs
   (`chNN.html`, `prefaceNN.html#frag`, custom in-page `#anchor`s) don't exist
   in the repackaged book, so `[text](dead)` becomes plain `text`. Real links
   (http/https/mailto) and images (`![alt](src)`) are left intact. Without this,
   epubcheck reports a flood of RSC-007 (missing resource) / RSC-012 (bad
   fragment) errors.

2. Strip Pandoc attribute blocks (`{#id ...}`, `{.class ...}`) on headings,
   table captions, spans, etc. Once the links above are flattened these ids
   target nothing, and in a bilingual interleave the same `{#id}` appears on
   both the source and translated element — epubcheck then reports RSC-005
   duplicate-ID errors. Stripping them fixes that.

Run this on the files that will be packaged (the bilingual/ or mono/ PACK_DIR
copies), NOT on the cached translations, since it rewrites in place.

Usage:
    clean_md.py <file.md> [<file.md> ...]
"""
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_BARE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
# A markdown link NOT preceded by '!' (images stay intact).
LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
# Pandoc attribute block that begins with an id (#) or class (.).
ATTR = re.compile(r"[ \t]*\{[#.][^{}]*\}")


def _is_dead(url: str) -> bool:
    u = url.strip()
    if u.startswith(("http://", "https://", "mailto:")):
        return False
    if u.startswith("#"):
        return True
    if re.search(r"\.x?html(\#|$)", u):
        return True
    return False


def _flatten_links(line: str) -> str:
    return LINK.sub(lambda m: m.group(1) if _is_dead(m.group(2)) else m.group(0), line)


def clean(text: str) -> str:
    out: list[str] = []
    in_fence = False
    fence_char = ""
    for line in text.replace("\r\n", "\n").split("\n"):
        m = FENCE.match(line)
        if m:
            c = m.group(1)[0]
            if not in_fence:
                in_fence, fence_char = True, c
            elif c == fence_char and FENCE_BARE.match(line):
                in_fence = False
            out.append(line)
            continue
        if in_fence:
            out.append(line)
        else:
            out.append(ATTR.sub("", _flatten_links(line)))
    return "\n".join(out)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: clean_md.py <file.md> [<file.md> ...]")
    changed = 0
    for p in sys.argv[1:]:
        path = Path(p)
        old = path.read_text(encoding="utf-8")
        new = clean(old)
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"clean_md: rewrote {changed}/{len(sys.argv) - 1} file(s)")


if __name__ == "__main__":
    main()
