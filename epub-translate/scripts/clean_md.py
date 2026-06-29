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
# A heading with no text (e.g. "# " or "###"). EPUB extraction sometimes emits
# these; Pandoc turns them into empty nav entries, so drop the line entirely.
EMPTY_HEADING = re.compile(r"^#{1,6}\s*$")
# Any ATX heading, capturing its level and the rest of the line.
HEADING = re.compile(r"^(#{1,6})(\s.*)$")
# A heading whose entire content is an image (e.g. "## ![](image33.png)"). Pandoc
# puts it in the nav TOC but the nav can't reference the image -> broken resource,
# so demote it to a plain image paragraph (drop the heading marker).
IMG_HEADING = re.compile(r"^#{1,6}\s+(!\[[^\]]*\]\([^)]+\))\s*$")
# A markdown link NOT preceded by '!' (images stay intact). The text may
# contain escaped brackets (e.g. "[As a \[role\], I want ...]"), so allow
# backslash escapes inside it; it may also be empty (e.g. a bare "[](toc.xhtml)"
# anchor that some TOC exports emit), so allow zero characters too.
LINK = re.compile(r"(?<!\!)\[((?:\\.|[^\]\\])*)\]\(([^)]+)\)")
# Pandoc attribute block that begins with an id (#) or class (.).
ATTR = re.compile(r"[ \t]*\{[#.][^{}]*\}")
# An image. Its src is a real image only if it is a data: URI or ends in an
# image extension (local OR remote). A src with no image extension — a mangled
# link like "![](toc.xhtml#x)", or a remote page URL like
# "![](https://shop/product/123)" — is flattened to its alt text. A real local
# image carrying a directory prefix is rewritten to its bare basename, since
# images are always stored flat (matches older work dirs that predate that fix).
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMG_EXT = re.compile(r"\.(png|jpe?g|gif|svg|webp|bmp|tiff?|avif|ico)$", re.I)


def _img_is_real(src: str) -> bool:
    s = src.strip()
    return s.startswith("data:") or bool(IMG_EXT.search(s))


def _fix_image(m: "re.Match[str]") -> str:
    alt, src = m.group(1), m.group(2)
    s = src.strip()
    if not _img_is_real(s):
        return alt  # not a real image -> flatten to alt text
    if not s.startswith(("http://", "https://", "data:")) and "/" in s:
        return f"![{alt}]({s.rsplit('/', 1)[-1]})"  # local path -> basename
    return m.group(0)


def _drop_dead_images(line: str) -> str:
    return IMG.sub(_fix_image, line)


# A linked image: [![alt](imgsrc)](linkurl) — common for cover thumbnails that
# link to a store page. The generic link/image regexes would mis-parse the
# nesting and mangle it into a broken "![](linkurl)" remote image, so unwrap it
# to just the image first (the external link wrapper adds little in a book).
LINKED_IMG = re.compile(r"\[(!\[[^\]]*\]\([^)]+\))\]\([^)]+\)")


def _unwrap_linked_images(line: str) -> str:
    return LINKED_IMG.sub(lambda m: m.group(1), line)


def _is_dead(url: str) -> bool:
    u = url.strip()
    if u.startswith(("http://", "https://")):
        # Flatten URLs with a malformed host that epubcheck (RSC-020) rejects.
        # EPUB extraction sometimes mangles internal links into forms like
        # "https://wiki.solidbook.iohref=..." (domain fused with an href).
        host = re.sub(r"^https?://", "", u).split("/")[0].split("?")[0].split("#")[0]
        if any(ch in host for ch in "=& \t") or any(len(lbl) > 63 for lbl in host.split(".")):
            return True
        return False
    if u.startswith("mailto:"):
        return False
    # Anything else is a relative/in-page reference. After repackaging into a
    # single new EPUB, no source-relative target survives (chapter files were
    # renamed, custom #anchors and notion-style slug links don't resolve), and
    # images use the `![]()` syntax which this LINK regex already excludes. So
    # treat every remaining relative link as dead and flatten it to plain text.
    return True


def _flatten_links(line: str) -> str:
    return LINK.sub(lambda m: m.group(1) if _is_dead(m.group(2)) else m.group(0), line)


def _count_h1(lines: list[str]) -> int:
    n, in_fence, fch = 0, False, ""
    for line in lines:
        m = FENCE.match(line)
        if m:
            c = m.group(1)[0]
            if not in_fence:
                in_fence, fch = True, c
            elif c == fch and FENCE_BARE.match(line):
                in_fence = False
            continue
        if not in_fence and re.match(r"^#\s", line):
            n += 1
    return n


def clean(text: str) -> str:
    lines_all = text.replace("\r\n", "\n").split("\n")
    # Only collapse multi-H1 files: a file with one H1 already has the right
    # shape, so its existing H2/H3 must be left alone.
    demote_extra = _count_h1(lines_all) > 1
    out: list[str] = []
    in_fence = False
    fence_char = ""
    seen_first_h1 = False
    for line in lines_all:
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
            continue
        if EMPTY_HEADING.match(line):
            continue  # drop empty heading lines (would become empty nav entries)
        mh = IMG_HEADING.match(line)
        if mh:
            line = mh.group(1)  # demote image-only heading to a plain image
        else:
            # One spine chapter == one source file == one H1. Sources that use
            # "#" for every section (e.g. Head First books) otherwise make
            # --split-level=1 explode into hundreds of tiny, fragmented pages.
            # Keep the file's first H1 (the chapter title) and demote every
            # later heading by one level, preserving the relative hierarchy.
            hm = HEADING.match(line) if demote_extra else None
            if hm:
                level, rest = hm.group(1), hm.group(2)
                if len(level) == 1 and not seen_first_h1:
                    seen_first_h1 = True
                else:
                    line = "#" * min(len(level) + 1, 6) + rest
        out.append(ATTR.sub("", _flatten_links(_drop_dead_images(_unwrap_linked_images(line)))))
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
