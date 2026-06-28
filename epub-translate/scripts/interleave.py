#!/usr/bin/env python3
"""Merge a source chapter and its translation into one bilingual chapter.

Alignment model
---------------
Markdown is split into blocks. Fenced code blocks are kept ATOMIC (a fence may
contain blank lines, so naive blank-line splitting would tear the fence apart
and corrupt every following block, which silently swallows images). Each block
is reduced to a TYPE signature:

    H = heading, C = code, I = image (carrying its path), p = prose

The two block streams are aligned with ``difflib`` on those signatures.
Structural blocks (H/C/I) are identical tokens on both sides, so difflib pins
them as anchors; the only divergences are prose paragraphs the translator
merged or split, which land in small replace/insert/delete regions.

    - equal region -> pair blocks 1:1
          code    -> emit the translated block once (keeps translated comments)
          image   -> emit once (language-neutral)
          heading -> emit the translated heading only (clean, single TOC)
          prose   -> emit source block, then translated block
    - diff region  -> emit the source blocks of the range, then the translated
          blocks of the range (kept local to that short run)

Image paths are also de-duplicated chapter-globally, so a figure is never
emitted twice even if an alignment quirk places it in a diff region.

This replaces an older blank-line-split + whole-chapter-fallback approach; the
alignment handles paragraph merge/split locally, so no whole-chapter fallback
is needed.

Usage:
    interleave.py <source.md> <translated.md> <output.md>
"""
import difflib
import re
import sys
from pathlib import Path

FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_BARE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
IMG_LINE = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$")
IMG_URL = re.compile(r"\]\(([^)]+)\)")
ORDERED_ITEM = re.compile(r"^\d+\.\s+(.*)$")  # top-level numbered list item


def split_blocks(text: str) -> list[str]:
    """Split into blocks on blank lines, keeping fenced code blocks atomic."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        if lines[i].strip() == "":
            i += 1
            continue
        m = FENCE_OPEN.match(lines[i])
        if m:
            fence_char = m.group(1)[0]
            buf = [lines[i]]
            i += 1
            while i < n:
                buf.append(lines[i])
                cm = FENCE_BARE.match(lines[i])
                i += 1
                if cm and cm.group(1)[0] == fence_char:
                    break
            blocks.append("\n".join(buf).strip("\n"))
            continue
        buf = []
        while i < n and lines[i].strip() != "":
            buf.append(lines[i])
            i += 1
        blocks.append("\n".join(buf).strip("\n"))
    return [b for b in _refine(blocks) if b.strip()]


def _refine(blocks: list[str]) -> list[str]:
    """Split standalone image lines into their own blocks.

    Pandoc's ``blank_before_header`` means an image glued to a ``###### Figure``
    caption (no blank line between) is one paragraph; splitting them lets the
    image anchor cleanly and the caption render as a heading.
    """
    out: list[str] = []
    for b in blocks:
        if FENCE_OPEN.match(b.split("\n", 1)[0]):
            out.append(b)
            continue
        cur: list[str] = []
        cur_img: bool | None = None
        for ln in b.split("\n"):
            img = bool(IMG_LINE.match(ln))
            if cur and img != cur_img:
                out.append("\n".join(cur))
                cur = []
            cur.append(ln)
            cur_img = img
        if cur:
            out.append("\n".join(cur))
    return out


def is_heading(block: str) -> bool:
    return bool(re.match(r"^#{1,6}\s", block.lstrip()))


def is_code(block: str) -> bool:
    return bool(FENCE_OPEN.match(block.split("\n", 1)[0]))


def is_image_only(block: str) -> bool:
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    return bool(lines) and all(re.fullmatch(r"!\[[^\]]*\]\([^)]+\)", ln) for ln in lines)


def sig(block: str):
    """Alignment token. Images carry their paths so difflib pins them as hard
    anchors (same paths, same order on both sides)."""
    if is_code(block):
        return "C"
    if is_image_only(block):
        return ("I", tuple(IMG_URL.findall(block)))
    if is_heading(block):
        return "H"
    return "p"


def _emit_pair(s: str, z: str, out: list[str]) -> None:
    if is_code(s) or is_code(z):
        out.append(z if is_code(z) else s)
    elif is_image_only(s) or is_image_only(z):
        out.append(s if is_image_only(s) else z)
    elif is_heading(s):
        out.append(z if is_heading(z) else s)
    else:
        out.append(s)
        out.append(z)


def interleave(src: list[str], zh: list[str]) -> tuple[list[str], int]:
    """Return (interleaved blocks, number of diff regions)."""
    sm = difflib.SequenceMatcher(a=[sig(b) for b in src], b=[sig(b) for b in zh], autojunk=False)
    out: list[str] = []
    seen_imgs: set[str] = set()
    diff_regions = 0

    def push(b: str) -> None:
        if is_image_only(b):
            paths = set(IMG_URL.findall(b))
            if paths <= seen_imgs:  # already emitted -> skip duplicate figure
                return
            seen_imgs.update(paths)
        out.append(b)

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                tmp: list[str] = []
                _emit_pair(src[i1 + k], zh[j1 + k], tmp)
                for b in tmp:
                    push(b)
        else:
            diff_regions += 1
            for b in src[i1:i2]:
                push(b)
            for b in zh[j1:j2]:
                push(b)
    return out, diff_regions


# --- Table-of-contents / ordered-list pages -------------------------------
# A TOC is a long top-level ordered list. The default per-block interleave
# emits the source item then the translated item, so Pandoc renumbers the list
# sequentially and the numbering DOUBLES (1,2,3,4 for two entries). For a page
# that is essentially one big numbered list we instead merge each entry with
# its translation into a SINGLE list item, so the list numbers once per entry.


def _parse_entries(text: str):
    """Split a TOC-like page into (preamble_lines, entries).

    An entry begins at a top-level ``N.`` line; following blank/indented lines
    (sub-titles, one-line descriptions) belong to it until the next ``N.``.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    preamble: list[str] = []
    while i < len(lines) and not ORDERED_ITEM.match(lines[i]):
        preamble.append(lines[i])
        i += 1
    entries: list[dict] = []
    cur: dict | None = None
    for ln in lines[i:]:
        m = ORDERED_ITEM.match(ln)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {"title": m.group(1).strip(), "rest": []}
        elif cur is not None and ln.strip():
            cur["rest"].append(ln.strip())
    if cur is not None:
        entries.append(cur)
    return preamble, entries


NESTED_ITEM = re.compile(r"^\s+\d+\.\s")  # an indented (sub-list) ordered item


def _is_nested_toc(text: str) -> bool:
    """A TOC with indented numbered sub-items (its own sub-numbering)."""
    return any(NESTED_ITEM.match(ln) for ln in text.replace("\r\n", "\n").split("\n"))


def _split_lists(src_text: str, zh_text: str):
    """Bilingual layout for a NESTED table of contents.

    A nested list can't be merged entry-by-entry without flattening its
    sub-numbering, so emit the whole source list, a divider, then the whole
    translated list. A non-list block between them makes Pandoc treat them as
    two separate lists, so each numbers independently (no doubling) and the
    nesting is preserved on both sides.
    """
    def split_head(text):
        lines = text.replace("\r\n", "\n").split("\n")
        i = 0
        while i < len(lines) and not ORDERED_ITEM.match(lines[i]):
            i += 1
        return "\n".join(lines[:i]).strip(), "\n".join(lines[i:]).strip()

    _, src_body = split_head(src_text)
    zh_head, zh_body = split_head(zh_text)
    parts = []
    if zh_head:
        parts.append(zh_head)
    if src_body:
        parts.append(src_body)
    parts.append("------")  # thematic break: separates the two lists
    if zh_body:
        parts.append(zh_body)
    return parts


def _looks_like_toc(text: str) -> bool:
    """True when the page is essentially one big top-level ordered list.

    Requires at least 8 numbered items and that ~all non-blank body lines are
    either numbered items or their indented continuations — so prose chapters
    that merely contain a short list never qualify.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    body, seen_heading = [], False
    for ln in lines:
        if not seen_heading and is_heading(ln):
            seen_heading = True
            continue
        if ln.strip():
            body.append(ln)
    if not body:
        return False
    numbered = sum(1 for ln in body if ORDERED_ITEM.match(ln))
    in_list = sum(1 for ln in body if ORDERED_ITEM.match(ln) or ln[:1].isspace())
    return numbered >= 8 and in_list / len(body) >= 0.9


def _merge_toc(src_text: str, zh_text: str):
    """Merge a TOC source and translation into one bilingual numbered list.

    Returns the parts list, or None if the entry counts differ (caller then
    falls back to the normal interleave).
    """
    _, s_entries = _parse_entries(src_text)
    zh_preamble, z_entries = _parse_entries(zh_text)
    if len(s_entries) != len(z_entries) or not s_entries:
        return None
    parts: list[str] = []
    head = "\n".join(zh_preamble).strip()  # translated heading, if any
    if head:
        parts.append(head)
    for n, (se, ze) in enumerate(zip(s_entries, z_entries), start=1):
        # Continuation lines must be indented to the list item's content column,
        # which is the marker width. A fixed 4-space indent breaks for two-digit
        # numbers (e.g. "10. " is 4 wide -> a 4-space continuation is fine, but
        # "10.  " content sits at column 5), so derive the indent from the marker.
        marker = f"{n}. "
        indent = " " * len(marker)
        body = [f"{marker}{se['title']}", "", f"{indent}{ze['title']}"]
        sd, zd = se["rest"], ze["rest"]
        for k in range(max(len(sd), len(zd))):  # pair descriptions EN then ZH
            if k < len(sd):
                body += ["", f"{indent}{sd[k]}"]
            if k < len(zd):
                body += ["", f"{indent}{zd[k]}"]
        parts.append("\n".join(body))
    return parts


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit("usage: interleave.py <source.md> <translated.md> <output.md>")
    src_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    zh_text = Path(sys.argv[2]).read_text(encoding="utf-8")
    out_path = Path(sys.argv[3])

    # TOC pages: avoid Pandoc renumbering the doubled EN/ZH list.
    if _looks_like_toc(src_text):
        if _is_nested_toc(src_text):
            # nested list -> source tree, divider, translated tree
            parts = _split_lists(src_text, zh_text)
        else:
            # flat list -> merge each entry (source title then translation)
            parts = _merge_toc(src_text, zh_text)
        if parts is not None:
            out_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
            return

    src = split_blocks(src_text)
    zh = split_blocks(zh_text)
    parts, diff_regions = interleave(src, zh)
    if diff_regions:
        print(
            f"NOTE: {out_path.name} aligned with {diff_regions} grouped "
            f"paragraph region(s) (translator merged/split text there)",
            file=sys.stderr,
        )
    out_path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
