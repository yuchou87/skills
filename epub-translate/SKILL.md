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
version: 1.0.0
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
| `scripts/interleave.py` | Merge a source chapter and its translation into one bilingual chapter (with TOC-safe fallback on paragraph-count mismatch) |

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

Decide the file set md2epub will consume, based on `layout`:

**`layout=mono`** — use the translated chapters directly:

```bash
PACK_DIR="${WORK_DIR}/${target_lang}"
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

If `interleave.py` prints a block-count-mismatch warning for any chapter, surface it in the final report (that chapter fell back to whole-chapter layout — original demoted, translation kept clean).

Copy images so relative references resolve during packaging:

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
rm -rf "${WORK_DIR}/bilingual"
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
Bilingual fallbacks: {n} chapter(s) (paragraph mismatch — listed below)
```

List any bilingual fallback chapters by filename so the user can spot-check them.

## Error Handling

| Scenario | Action |
|----------|--------|
| baoyu-translate not installed | Stop; tell user to install the baoyu skills plugin |
| md2epub not installed | Stop; print install command |
| pandoc missing | Stop; print `brew install pandoc` |
| `extract_epub.py` finds no chapters | Abort — likely not a valid EPUB or DRM-protected |
| A chapter fails to translate | Leave its `${target_lang}/NNN.md` absent so a re-run retries it; note in report |
| Bilingual block-count mismatch | `interleave.py` falls back to whole-chapter layout; surface in report |
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
