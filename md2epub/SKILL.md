---
name: md2epub
description: >
  Convert Markdown files to EPUB3 ebooks. Supports single-file or multi-file merge,
  automatically renders Mermaid code blocks as embedded images.
  Trigger keywords: "generate ebook", "convert to epub", "md to epub",
  "生成电子书", "转成 epub", "打包成电子书", "md 转 epub"
version: 1.2.0
---

# Markdown → EPUB Conversion Skill

## Scripts

Scripts are located in the `scripts/` directory alongside this SKILL.md.

**Important**: Resolve `SKILL_DIR` before Step 3:

```bash
SKILL_DIR="${HOME}/.claude/skills/md2epub"
```

| Script | Purpose |
|--------|---------|
| `scripts/preprocess_mermaid.py` | Renders mermaid code blocks in Markdown to PNG images and replaces them with image references |

## Prerequisite Check

Confirm the following tools are available before proceeding; prompt the user to install any that are missing:

```bash
# Required
which pandoc   || echo "❌ Missing pandoc: brew install pandoc"
which python3  || echo "❌ Missing python3"

# Mermaid rendering (auto-installed via npx on first run — no manual setup needed)
which npx      || echo "⚠ No npx — Mermaid diagrams will be kept as code blocks (install Node.js)"
```

## Workflow

### Step 1: Collect Input Parameters

Ask or infer from context:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `input_files` | MD files to convert: single file, list of files, or directory (auto-sorted by name) | `*.md` in current directory |
| `output_epub` | Output file path | `{first file's directory}/book.epub` |
| `title` | Book title | First H1 heading, or filename |
| `author` | Author name | (optional) omit if blank |
| `lang` | Language mode | `en` |
| `cover` | Cover image path | (optional) omit for no cover |
| `render_mermaid` | Whether to render Mermaid diagrams | `true` (if npx available) |

**Language modes** — `lang` controls both the EPUB metadata language and the default image alt-text prefix:

| `lang` value | EPUB `lang` field | Default `alt_label` | Use case |
|---|---|---|---|
| `en` (default) | `en` | `Diagram` | English content |
| `zh-CN` | `zh-CN` | `图表` | Chinese content |
| `bilingual` | `zh-CN` | `Diagram / 图表` | Mixed Chinese–English content |

The user can override `alt_label` explicitly regardless of `lang`.

**File sort order**: When input is a directory, files are sorted ascending by name; files with numeric prefixes (e.g. `01_`, `02_`) are naturally ordered.

### Step 2: Set Up Build Directory

```bash
BUILD_DIR="$(dirname {output_epub})/_epub_build"
IMG_DIR="${BUILD_DIR}/images"
mkdir -p "${BUILD_DIR}" "${IMG_DIR}"
```

### Step 3: Preprocess Mermaid Diagrams

If `render_mermaid=true` and `npx` is available, run for each input file:

```bash
python3 "${SKILL_DIR}/scripts/preprocess_mermaid.py" \
  "{input_file}" \
  "${BUILD_DIR}/{input_file_basename}" \
  "${IMG_DIR}" \
  "{alt_label}"
```

- The script writes `![{alt_label} N](xxx.png)` into the processed MD file
- PNG images are saved under `${IMG_DIR}/`
- If a mermaid block fails to render (including timeout), the original code block is preserved — build continues
- First run of npx will download mermaid-cli, which may take 1–2 minutes

If `render_mermaid=false` or `npx` is unavailable, copy the original MD files directly to `${BUILD_DIR}/`.

Copy rendered PNGs to `${BUILD_DIR}/` so pandoc can resolve relative image paths:

```bash
cp "${IMG_DIR}"/*.png "${BUILD_DIR}/" 2>/dev/null || true
```

### Step 4: Generate EPUB Metadata File

Write `${BUILD_DIR}/metadata.yaml` (TOC options belong here only — do not repeat in the pandoc command):

**For `lang=en`:**
```yaml
---
title: '{title}'
author: '{author}'     # omit this line if author is blank
lang: en
toc: true
toc-depth: 2
---
```

**For `lang=zh-CN`:**
```yaml
---
title: '{title}'
author: '{author}'
lang: zh-CN
toc: true
toc-depth: 2
---
```

**For `lang=bilingual`:**
```yaml
---
title: '{title}'
author: '{author}'
lang: zh-CN
toc: true
toc-depth: 2
---
```

### Step 5: Run pandoc to Generate EPUB

Use a subshell to avoid changing the agent's current working directory (Issue #4 fix):

```bash
(
  cd "${BUILD_DIR}" && pandoc \
    --from markdown+raw_html \
    --to epub3 \
    --output "{output_epub}" \
    --metadata-file metadata.yaml \
    --split-level=1 \
    --resource-path="${BUILD_DIR}" \
    --wrap=none \
    {--epub-cover-image="{cover}" if cover is set} \
    {processed MD files in order}
)
```

**About `--split-level`**:
- `1` (default): each H1 heading becomes a separate chapter file — best for multi-file merges
- `2`: split at H2 — better for a single file with very many H1 sections

### Step 6: Clean Up and Report

Delete the temporary build directory after a successful build:

```bash
rm -rf "${BUILD_DIR}"
```

Then output a report:

```
✅ Ebook generated successfully

File:     {output_epub}
Size:     {file size}
Chapters: {chapter count} (from {file count} MD file(s))
Diagrams: {success count} rendered as images / {fail count} kept as code blocks
```

## Troubleshooting

| Problem | Resolution |
|---------|-----------|
| First npx run is slow | Normal — first download of mermaid-cli takes 1–2 min; script timeout is 120 s |
| Mermaid render fails | Code block is preserved; build continues; fail count shown in report |
| pandoc can't find images | Confirm Step 5 uses the subshell form `(cd ... && pandoc ...)` |
| "Abstract" warning with Chinese content | Harmless — pandoc language-pack warning; does not affect content |
| EPUB file is corrupted | Validate with `epubcheck {output_epub}` (if installed) |
| MD file has relative image paths | Copy those images to `${BUILD_DIR}/` before converting |

## Examples

**Example 1: Convert all MD files in a directory**
> User: "generate an ebook from docs/explain/"

1. `input_files` = files in `docs/explain/` sorted by name
2. `title` = first H1 in the first file
3. Run full workflow

**Example 2: Single file conversion**
> User: "convert this README.md to epub"

1. `input_files` = `README.md`
2. `output_epub` = `README.epub`
3. `render_mermaid` = `true` only if the file contains mermaid blocks
4. Consider `--split-level=2` for single-file with many sections

**Example 3: Chinese ebook with metadata**
> User: "生成电子书，书名《AI 架构指南》，作者张三"

1. `lang` = `zh-CN`
2. `title` = `AI 架构指南`
3. `author` = `张三`
4. `alt_label` = `图表` (auto-derived from `lang`)

**Example 4: Bilingual ebook**
> User: "make a bilingual epub, English and Chinese"

1. `lang` = `bilingual`
2. `alt_label` = `Diagram / 图表` (auto-derived)
3. EPUB `lang` field = `zh-CN`
4. All other parameters inferred as usual
