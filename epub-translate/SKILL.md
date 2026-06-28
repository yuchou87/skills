---
name: epub-translate
description: >
  Translate an EPUB ebook into another language and repackage it as a new EPUB.
  Unzips the book in spine (reading) order, delegates per-chapter translation to
  the baoyu-translate skill (shared glossary for consistent terminology), then
  delegates EPUB packaging to the md2epub skill. Supports mono (target-only) and
  bilingual (original + translation) layouts, with chapter-level resume.
  Trigger keywords: "translate epub", "translate ebook", "epub translation",
  "翻译 epub", "翻译电子书", "epub 翻译", "把这本 epub 翻译成中文",
  "translate this book to chinese", "bilingual epub"
version: 1.3.4
---

# EPUB Translation Skill

## Scripts

Scripts live in the `scripts/` directory alongside this SKILL.md.

**Important**: Resolve `SKILL_DIR` before proceeding:

```bash
SKILL_DIR="${HOME}/.claude/skills/epub-translate"
```

| Script | Purpose |
|--------|---------|
| `scripts/extract_epub.py` | Unzip an EPUB into ordered chapter Markdown (spine order) + images + `meta.json` |
| `scripts/interleave.py` | Merge a source chapter and its translation into one bilingual chapter (difflib-aligned: code blocks kept atomic, structural blocks anchored, figures de-duplicated; table-of-contents pages handled so numbering isn't doubled — flat lists merged per entry, nested lists split into source + translated trees) |
| `scripts/clean_md.py` | Clean assembled Markdown before packaging — flatten every dead link (any relative/anchor/`.html` target, empty-text `[](…)` anchors, malformed-host URLs) to plain text, drop "images" whose src isn't a real image (mangled `![](toc.xhtml#x)`), and strip Pandoc `{#id .class}` attribute blocks so the EPUB validates (no RSC-007/012/005/020 errors). Real http(s)/mailto links, real images, and code are kept |

## Prerequisites

This skill orchestrates two other skills and a few CLI tools. Confirm all are available before proceeding.

### 1. baoyu-translate skill

Per-chapter translation is delegated to `baoyu-translate`. Verify it is installed by checking that it appears in the available skills list. If missing, tell the user to install the baoyu skills plugin before continuing.

### 2. md2epub skill

EPUB packaging is delegated to `md2epub` (a sibling skill in this repo). Verify it exists:

```bash
MD2EPUB_SKILL="${HOME}/.claude/skills/md2epub/SKILL.md"
test -f "${MD2EPUB_SKILL}" && echo "OK" || echo "MISSING: install md2epub skill — cp -r md2epub ~/.claude/skills/md2epub"
```

### 3. Other dependencies

```bash
which pandoc   || echo "MISSING pandoc: brew install pandoc"
which python3  || echo "MISSING python3"
which npx      || echo "OPTIONAL: npx not found — Mermaid diagrams (if any) kept as code blocks"
```

## Workflow

### Step 1: Collect Input Parameters

Ask or infer from context:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `input_epub` | Path to the source `.epub` (required) | — |
| `output_epub` | Output file path | `{input dir}/{input stem}.{target_lang}.epub` |
| `target_lang` | Target language | `zh-CN` |
| `layout` | `mono` (target only) or `bilingual` (original + translation) | `mono` |
| `mode` | Translation mode passed to baoyu-translate: `quick` / `normal` / `refined` | `refined` |
| `title` | Book title for the output | from `meta.json`, suffixed with target lang |
| `author` | Author | from `meta.json` |

**Language / layout inference**: If the user says "对照" / "bilingual" / "中英对照", set `layout=bilingual`. If they say "纯译文" / "只要中文", set `layout=mono`. Infer `target_lang` from the request ("翻译成中文" → `zh-CN`).

**Cost warning**: A full book is many chapters and `refined` mode is slow and token-heavy. Before processing a large book, tell the user the chapter count (from Step 2's `meta.json`) and confirm they want to proceed, or suggest a test run on the first 1–2 chapters.

### Step 2: Extract the EPUB

Set up a working directory anchored to the output path:

```bash
WORK_DIR="$(dirname "{output_epub}")/_epub_translate/$(basename "{input_epub}" .epub)"
mkdir -p "${WORK_DIR}"
python3 "${SKILL_DIR}/scripts/extract_epub.py" "{input_epub}" "${WORK_DIR}"
```

This produces:

```
${WORK_DIR}/src/NNN.md     ordered chapter Markdown (spine order, NOT filename order)
${WORK_DIR}/images/        image resources from the EPUB
${WORK_DIR}/meta.json      {title, author, lang, chapters, image_count}
```

Read `meta.json` to get the chapter list, original title/author, and chapter count. Create the translation output and glossary directories:

```bash
mkdir -p "${WORK_DIR}/${target_lang}"
GLOSSARY="${WORK_DIR}/EXTEND.md"   # shared term table for whole-book consistency
```

If `EXTEND.md` does not exist, create it with a short header explaining it holds agreed term translations (e.g. `| Source | Target |` table). It is shared across all chapters so names and jargon stay consistent.

### Step 3: Translate Each Chapter (delegate to baoyu-translate, with resume)

**Pre-flight — keep the loop non-interactive.** baoyu-translate runs a *blocking*
first-time setup (an `AskUserQuestion` prompt) when it finds no config `EXTEND.md`
of its own. That would interrupt this per-chapter loop. Before translating, ensure
its config exists so it runs unattended:

```bash
BAOYU_CFG="${HOME}/.baoyu-skills/baoyu-translate/EXTEND.md"
if [ ! -f "${BAOYU_CFG}" ]; then
  mkdir -p "$(dirname "${BAOYU_CFG}")"
  printf -- '---\ntarget_language: %s\ndefault_mode: %s\naudience: technical\nstyle: technical\n---\n' \
    "${target_lang}" "${mode}" > "${BAOYU_CFG}"
fi
```

If the user already has a baoyu-translate config, leave it untouched and just pass
per-call flags. Either way, also pass the book glossary via `--glossary "${WORK_DIR}/EXTEND.md"`.

For each `src/NNN.md` in ascending numeric order:

1. **Resume check** — if `${WORK_DIR}/${target_lang}/NNN.md` already exists and is non-empty, skip it (already translated). This makes the workflow resumable after interruption.
2. Otherwise, **invoke the `baoyu-translate` skill** on `src/NNN.md`:
   - target language = `target_lang`
   - mode = `mode` (default `refined`)
   - glossary = `${WORK_DIR}/EXTEND.md` — pass it as the EXTEND glossary so terminology stays consistent across chapters, and let baoyu-translate append newly-fixed terms to it
   - write the translation to `${WORK_DIR}/${target_lang}/NNN.md`
3. Keep the Markdown structure intact (headings, lists, code blocks, image references) so packaging and optional interleaving work.

Process chapters sequentially so the glossary accumulates in order. Report progress (`{done}/{total}`) as you go.

### Step 4: Assemble Chapters for Packaging

Build a `PACK_DIR` of the exact files md2epub will consume. Always assemble into
a **fresh** directory (never package straight from `${target_lang}/`, which is
the resume cache — Step 4b rewrites these files in place).

**`layout=mono`** — copy the translated chapters into a packaging dir:

```bash
PACK_DIR="${WORK_DIR}/mono"
mkdir -p "${PACK_DIR}"
cp "${WORK_DIR}/${target_lang}"/*.md "${PACK_DIR}/"
```

**`layout=bilingual`** — interleave each chapter's source and translation:

```bash
PACK_DIR="${WORK_DIR}/bilingual"
mkdir -p "${PACK_DIR}"
for f in "${WORK_DIR}/src"/*.md; do
  base="$(basename "$f")"
  python3 "${SKILL_DIR}/scripts/interleave.py" \
    "$f" "${WORK_DIR}/${target_lang}/${base}" "${PACK_DIR}/${base}"
done
```

`interleave.py` aligns the two chapters with difflib, so every chapter is interleaved paragraph-by-paragraph (no whole-chapter fallback). Where the translator merged or split paragraphs, those few blocks are emitted as a grouped source-run-then-translation-run and the script prints a `NOTE: NNN.md aligned with N grouped paragraph region(s)` to stderr — collect these for the report so the user can spot-check those spots.

A page that is essentially one big top-level **ordered list** (a table of contents) is detected and handled specially, otherwise Pandoc renumbers the doubled EN/ZH items sequentially and the chapter numbering runs together (1,2,3,4 for two entries). A **flat** list merges each entry with its translation into a single numbered item (source title, then translated title, then any descriptions). A **nested** list (with its own indented sub-numbering) can't be merged without flattening, so it emits the whole source tree, a divider, then the whole translated tree — a non-list block between them makes Pandoc number each tree independently.

### Step 4b: Clean the assembled Markdown (both layouts)

Run `clean_md.py` over the `PACK_DIR` so the repackaged EPUB validates. It
flattens every dead link to plain text — any relative target, `#anchor`, or
`.html` reference (none survive repackaging → RSC-007/RSC-012), plus URLs with a
malformed host that EPUB extraction sometimes produces, e.g.
`https://wiki.solidbook.iohref=…` (→ RSC-020) — and strips Pandoc
`{#id .class}` attribute blocks (which duplicate across the two languages in a
bilingual interleave → RSC-005 duplicate-ID errors). Real http(s)/mailto links,
images, code blocks, and fence info strings are left untouched; link text may
contain escaped brackets; the pass is idempotent.

```bash
python3 "${SKILL_DIR}/scripts/clean_md.py" "${PACK_DIR}"/*.md
```

Then copy images so relative references resolve during packaging (image refs are
bare basenames, matching the flat `images/` store):

```bash
cp "${WORK_DIR}/images"/* "${PACK_DIR}/" 2>/dev/null || true
```

### Step 5: Package the EPUB (delegate to md2epub)

Follow the **md2epub SKILL.md workflow starting from Step 2** (Set Up Build Directory), passing these parameters. Do **not** invoke md2epub as a separate skill call — read `${HOME}/.claude/skills/md2epub/SKILL.md` and execute its Steps 2–6 inline so this stays one continuous workflow.

| md2epub parameter | Value |
|-------------------|-------|
| `input_files` | `${PACK_DIR}/*.md` (sorted by filename — `NNN` prefixes preserve order) |
| `output_epub` | `{output_epub}` |
| `title` | `{title}` (default: original title + ` ({target_lang})`) |
| `author` | `{author}` |
| `lang` | `target_lang` for `mono`; `bilingual` for `layout=bilingual` |
| `render_mermaid` | `true` only if any chapter contains mermaid blocks |

### Step 6: Clean Up and Report

Keep `${WORK_DIR}/${target_lang}/` is NOT required after success, but the resume cache is cheap to keep. Remove only the bilingual scratch and build dirs:

```bash
rm -rf "${WORK_DIR}/bilingual" "${WORK_DIR}/mono"
# Keep src/ and ${target_lang}/ for re-runs, or remove the whole WORK_DIR if the user wants a clean state:
# rm -rf "${WORK_DIR}"
```

Output a report:

```
✅ EPUB translation complete

Source:   {input_epub}
Output:   {output_epub}
Size:     {file_size}
Language: {original lang} → {target_lang}
Layout:   {mono | bilingual}
Mode:     {mode}
Chapters: {translated_count}/{total} ({skipped} resumed from cache)
Grouped-paragraph regions: {n} chapter(s) (translator merged/split text — listed below)
```

List any chapters that printed a grouped-paragraph `NOTE` by filename so the user can spot-check those spots.

## Error Handling

| Scenario | Action |
|----------|--------|
| baoyu-translate not installed | Stop; tell user to install the baoyu skills plugin |
| md2epub not installed | Stop; print install command |
| pandoc missing | Stop; print `brew install pandoc` |
| `extract_epub.py` finds no chapters | Abort — likely not a valid EPUB or DRM-protected |
| A chapter fails to translate | Leave its `${target_lang}/NNN.md` absent so a re-run retries it; note in report |
| Translator merged/split paragraphs | `interleave.py` aligns with difflib and groups those blocks locally; it prints a `NOTE` to stderr — surface in report |
| epubcheck reports RSC-007 / RSC-012 / RSC-005 errors | The Step 4b `clean_md.py` pass was skipped — run it over `PACK_DIR` and repackage |
| md2epub packaging fails | Surface the pandoc error from md2epub |

## Examples

**Example 1: Translate to Chinese, target-only**
> User: "把 ~/Books/clean-code.epub 翻译成中文"

```
input_epub  = ~/Books/clean-code.epub
target_lang = zh-CN
layout      = mono
mode        = refined
output_epub = ~/Books/clean-code.zh-CN.epub
```

**Example 2: Bilingual study edition**
> User: "translate this epub to a bilingual English-Chinese book: ./pragmatic.epub"

```
input_epub  = ./pragmatic.epub
target_lang = zh-CN
layout      = bilingual
output_epub = ./pragmatic.zh-CN.epub
```

**Example 3: Quick test run**
> User: "先翻前两章试试 book.epub 转中文"

Extract, then translate only `001.md` and `002.md`, package those, and ask whether to continue with the rest (resume will skip the two already done).
