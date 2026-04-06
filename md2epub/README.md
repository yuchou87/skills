# md2epub

A Claude Code skill that converts Markdown files to EPUB3 ebooks, with automatic rendering of Mermaid diagrams as embedded PNG images.

> **中文说明**: [README.zh-CN.md](README.zh-CN.md)

## Features

- Single-file or multi-file merge into one ebook
- Renders ` ```mermaid ` code blocks to PNG images via `npx @mermaid-js/mermaid-cli`
- Supports `en`, `zh-CN`, and `bilingual` language modes
- Auto-generates table of contents
- Graceful fallback: failed diagram renders keep the original code block

## Requirements

| Tool | Install | Required |
|------|---------|----------|
| [pandoc](https://pandoc.org) | `brew install pandoc` | Yes |
| python3 | pre-installed on macOS | Yes |
| Node.js / npx | [nodejs.org](https://nodejs.org) | Only for Mermaid rendering |

## Installation

Copy the skill into your Claude Code skills directory:

```bash
# Clone or download this repo, then:
cp -r md2epub ~/.claude/skills/md2epub
```

Or if you have the full skills repo:

```bash
git clone https://github.com/yuchou87/skills ~/.claude/skills-repo
cp -r ~/.claude/skills-repo/md2epub ~/.claude/skills/md2epub
```

Verify the skill is recognized:

```bash
# In a Claude Code session, the skill will appear in the skill list as "md2epub"
```

## Usage

Invoke the skill by describing what you want in natural language. Claude will automatically trigger the skill when it detects relevant intent.

**English triggers:**
- "generate an ebook from these markdown files"
- "convert to epub"
- "make an epub from docs/"
- "md to epub"

**Chinese triggers (中文唤醒):**
- "生成电子书"
- "转成 epub"
- "打包成电子书"
- "md 转 epub"

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `input_files` | MD files to convert: single file, list, or directory | `*.md` in current directory |
| `output_epub` | Output path | `{first file's dir}/book.epub` |
| `title` | Book title | First H1 heading, or filename |
| `author` | Author name | *(omitted if blank)* |
| `lang` | Language mode: `en` / `zh-CN` / `bilingual` | `en` |
| `cover` | Cover image path | *(none)* |
| `render_mermaid` | Render Mermaid diagrams | `true` (if npx available) |

### Language modes

| `lang` | EPUB lang field | Diagram alt-text |
|--------|-----------------|------------------|
| `en` | `en` | `Diagram` |
| `zh-CN` | `zh-CN` | `图表` |
| `bilingual` | `zh-CN` | `Diagram / 图表` |

### Examples

**Convert a directory to an ebook:**
> "generate an ebook from docs/explain/, title 'OpenHarness Guide', author 'Alice'"

**Single file, Chinese:**
> "把 README.md 转成 epub，语言中文"

**Bilingual ebook:**
> "make a bilingual epub from these docs, title 'AI Architecture Guide'"

## How it works

```
Input MD files
      │
      ▼
[Step 1] Preprocess Mermaid blocks
         scripts/preprocess_mermaid.py
         → renders each ```mermaid block to PNG via npx mmdc
         → replaces block with ![Diagram N](xxx.png)
      │
      ▼
[Step 2] Generate metadata.yaml
         title, author, lang, toc settings
      │
      ▼
[Step 3] Run pandoc
         --from markdown+raw_html --to epub3
         --split-level=1 (one chapter per H1)
      │
      ▼
Output: book.epub
```

## File structure

```
md2epub/
├── SKILL.md                      # Skill definition (read by Claude Code)
├── README.md                     # This file
├── README.zh-CN.md               # Chinese documentation
└── scripts/
    └── preprocess_mermaid.py     # Mermaid → PNG renderer
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| First run is slow | Normal — npx downloads mermaid-cli on first use (~1–2 min) |
| Mermaid render fails | Diagram kept as code block; build continues |
| pandoc not found | `brew install pandoc` |
| EPUB looks broken | Validate with `epubcheck book.epub` |

## Version

Current version: **1.2.0**

Changes:
- `1.2.0` — Full English translation; added `lang` parameter with `en` / `zh-CN` / `bilingual` modes
- `1.1.0` — Graceful timeout handling, stale PNG detection, friendly error messages
- `1.0.0` — Initial release
