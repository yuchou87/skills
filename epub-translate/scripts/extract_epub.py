#!/usr/bin/env python3
"""Extract an EPUB into ordered Markdown chapters + images.

Chapter order is taken from the OPF <spine> (NOT filename order) — EPUB
internal filenames are frequently arbitrary; reading order lives only in
the spine. Each XHTML spine item is converted to Markdown via pandoc.

Usage:
    extract_epub.py <input.epub> <out_dir>

Outputs under <out_dir>:
    src/NNN.md        ordered chapter Markdown (3-digit prefix)
    images/           all image resources from the EPUB
    meta.json         {title, author, lang, chapters:[{file,title}], image_count}

Requires: pandoc on PATH. Stdlib only otherwise.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET


def strip_ns(tag: str) -> str:
    """Return the local name of a possibly-namespaced XML tag."""
    return tag.rsplit("}", 1)[-1]


def find_rootfile(zf: zipfile.ZipFile) -> str:
    """Read META-INF/container.xml to locate the OPF package document."""
    with zf.open("META-INF/container.xml") as f:
        tree = ET.parse(f)
    for el in tree.iter():
        if strip_ns(el.tag) == "rootfile":
            return el.attrib["full-path"]
    raise SystemExit("ERROR: no rootfile found in META-INF/container.xml")


def parse_opf(zf: zipfile.ZipFile, opf_path: str):
    """Return (metadata dict, ordered list of (href, media_type), images list)."""
    with zf.open(opf_path) as f:
        tree = ET.parse(f)
    root = tree.getroot()

    title = author = lang = None
    manifest = {}  # id -> (href, media_type)
    spine_ids = []

    for el in root.iter():
        name = strip_ns(el.tag)
        if name == "title" and title is None:
            title = (el.text or "").strip() or None
        elif name == "creator" and author is None:
            author = (el.text or "").strip() or None
        elif name == "language" and lang is None:
            lang = (el.text or "").strip() or None
        elif name == "item":
            manifest[el.attrib.get("id")] = (
                el.attrib.get("href"),
                el.attrib.get("media-type", ""),
            )
        elif name == "itemref":
            spine_ids.append(el.attrib.get("idref"))

    opf_dir = os.path.dirname(opf_path)

    def resolve(href: str) -> str:
        href = unquote(href)
        return os.path.normpath(os.path.join(opf_dir, href)) if opf_dir else href

    chapters = []
    for sid in spine_ids:
        if sid not in manifest:
            continue
        href, mtype = manifest[sid]
        if href and "html" in mtype:
            chapters.append((resolve(href), mtype))

    images = [
        resolve(href)
        for href, mtype in manifest.values()
        if href and mtype.startswith("image/")
    ]

    meta = {"title": title, "author": author, "lang": lang}
    return meta, chapters, images


def extract_title(xhtml_bytes: bytes) -> str | None:
    """Best-effort chapter title from <title> or first heading."""
    text = xhtml_bytes.decode("utf-8", "ignore")
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if m and m.group(1).strip():
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"<h[1-6][^>]*>(.*?)</h[1-6]>", text, re.I | re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() or None
    return None


def ensure_h1(md: str, title: str) -> str:
    """Guarantee the chapter starts with an H1 so md2epub can split on it."""
    if re.match(r"^\s*#\s", md):
        return md
    return f"# {title}\n\n{md.lstrip()}"


_IMG_REF = re.compile(r"(!\[[^\]]*\]\(\s*)(<?)([^)\s>]+)(>?)(\s+\"[^\"]*\")?(\s*\))")


def flatten_image_paths(md: str) -> str:
    """Rewrite local image references to bare basenames.

    Images are stored flat in images/ by basename, but the EPUB's XHTML keeps
    directory-prefixed paths (e.g. assets/foo.png, ../images/foo.png). Without
    this, packaging copies images/* into the build dir root yet the Markdown
    still points at assets/foo.png, so every figure breaks. Leaves real URLs
    (http/https/data:) untouched.
    """
    def repl(m: "re.Match[str]") -> str:
        url = m.group(3)
        if re.match(r"[a-z][a-z0-9+.-]*:", url, re.I):  # scheme -> external URL
            return m.group(0)
        base = url.rsplit("/", 1)[-1]
        return f"{m.group(1)}{m.group(2)}{base}{m.group(4)}{m.group(5) or ''}{m.group(6)}"

    return _IMG_REF.sub(repl, md)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: extract_epub.py <input.epub> <out_dir>")
    epub_path = Path(sys.argv[1]).expanduser()
    out_dir = Path(sys.argv[2]).expanduser()
    if not epub_path.is_file():
        sys.exit(f"ERROR: not a file: {epub_path}")

    src_dir = out_dir / "src"
    img_dir = out_dir / "images"
    src_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(epub_path) as zf:
        names = set(zf.namelist())
        opf_path = find_rootfile(zf)
        meta, chapters, images = parse_opf(zf, opf_path)

        # Unzip the whole EPUB to a temp dir so pandoc can resolve relative
        # asset references inside each XHTML file.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            zf.extractall(tmp_root)

            chapter_meta = []
            seq = 0
            for href, _mtype in chapters:
                if href not in names:
                    continue
                src_file = tmp_root / href
                if not src_file.is_file():
                    continue
                seq += 1
                title = extract_title(src_file.read_bytes()) or f"Chapter {seq}"
                out_md = src_dir / f"{seq:03d}.md"
                # Drop styling wrappers (fenced/native divs & spans, raw HTML,
                # heading attributes) so chapters are clean prose Markdown. This
                # keeps headings/lists/emphasis but strips `::: {.class}` and
                # `{#id .class}` noise that would otherwise break the TOC and
                # the bilingual interleave (which pairs blank-line blocks).
                pandoc_to = (
                    "markdown"
                    "-raw_html-fenced_divs-native_divs-native_spans"
                    "-header_attributes-bracketed_spans"
                    "-inline_code_attributes-link_attributes"
                )
                proc = subprocess.run(
                    [
                        "pandoc",
                        str(src_file),
                        "--from", "html",
                        "--to", pandoc_to,
                        "--wrap", "none",
                    ],
                    capture_output=True,
                    text=True,
                )
                if proc.returncode != 0:
                    print(
                        f"WARN: pandoc failed on {href}: {proc.stderr.strip()}",
                        file=sys.stderr,
                    )
                    seq -= 1
                    continue
                md = ensure_h1(proc.stdout.strip(), title)
                md = flatten_image_paths(md)
                if not md.strip():
                    seq -= 1
                    continue
                out_md.write_text(md + "\n", encoding="utf-8")
                chapter_meta.append({"file": out_md.name, "title": title})

            img_count = 0
            for img in images:
                if img not in names:
                    continue
                src_img = tmp_root / img
                if src_img.is_file():
                    dest = img_dir / Path(img).name
                    dest.write_bytes(src_img.read_bytes())
                    img_count += 1

    meta_out = {
        "title": meta.get("title") or epub_path.stem,
        "author": meta.get("author"),
        "lang": meta.get("lang"),
        "chapters": chapter_meta,
        "image_count": img_count,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Extracted {len(chapter_meta)} chapter(s), {img_count} image(s)")
    print(f"  src:    {src_dir}")
    print(f"  images: {img_dir}")
    print(f"  meta:   {out_dir / 'meta.json'}")
    if not chapter_meta:
        sys.exit("ERROR: no chapters extracted — is this a valid EPUB?")


if __name__ == "__main__":
    main()
