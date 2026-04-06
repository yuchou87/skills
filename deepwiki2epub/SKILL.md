---
name: deepwiki2epub
description: >
  Convert DeepWiki repository documentation to EPUB3 ebooks for offline reading.
  Fetches content via DeepWiki MCP server, assembles chapters, then delegates to
  md2epub skill for EPUB generation.
  Trigger keywords: "deepwiki to epub", "deepwiki epub", "deepwiki ebook",
  "deepwiki 电子书", "deepwiki 转 epub", "从 deepwiki 生成电子书",
  "convert deepwiki to ebook", "download deepwiki as epub"
version: 1.1.0
---

# DeepWiki → EPUB Conversion Skill

## Scripts

No scripts in this skill. All processing is done inline.

**Important**: Resolve `SKILL_DIR` before proceeding:

```bash
SKILL_DIR="${HOME}/.claude/skills/deepwiki2epub"
```

## Prerequisites

This skill depends on external tools and another skill. Confirm all are available before proceeding.

### 1. DeepWiki MCP Server

The DeepWiki MCP must be configured in Claude Code. Check by attempting to call `read_wiki_structure`. If unavailable, prompt the user:

```
DeepWiki MCP is not configured. Run this command to add it:

  claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp

Then restart your Claude Code session.
```

### 2. md2epub Skill

This skill delegates EPUB generation to `md2epub`. Verify the skill exists:

```bash
MD2EPUB_SKILL="${HOME}/.claude/skills/md2epub/SKILL.md"
test -f "${MD2EPUB_SKILL}" && echo "OK" || echo "MISSING: install md2epub skill — cp -r md2epub ~/.claude/skills/md2epub"
```

### 3. Other Dependencies

```bash
which pandoc   || echo "MISSING pandoc: brew install pandoc"
which python3  || echo "MISSING python3"
which npx      || echo "OPTIONAL: npx not found — Mermaid diagrams will be kept as code blocks"
```

## Workflow

### Step 1: Collect Input Parameters

Ask or infer from context:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `repo` | GitHub repo identifier (required) | — |
| `output` | Output EPUB file path | `./{owner}-{repo}.epub` |
| `title` | Book title | `{repo} (from DeepWiki)` |
| `author` | Author name | `{owner}` |
| `lang` | Language mode: `en` / `zh-CN` / `bilingual` | `en` |
| `cover` | Cover image path | (optional) omit for no cover |
| `render_mermaid` | Whether to render Mermaid diagrams | `true` (if npx available) |

**Repo format normalization**: Accept any of these formats and extract `{owner}/{repo}`:
- `facebook/react`
- `https://github.com/facebook/react`
- `github.com/facebook/react`
- `https://deepwiki.com/facebook/react`

**Language inference**: If `lang` is not specified explicitly, infer from the user's prompt language (Chinese prompt → `zh-CN`, English prompt → `en`).

### Step 2: Fetch Wiki Structure

Call the DeepWiki MCP tool:

```
read_wiki_structure({ "repoName": "{owner}/{repo}" })
```

This returns the documentation hierarchy — a list of topics with titles.

Record:
- Total topic count
- Topic titles and order (for chapter sequencing and headings)

If the repo is not indexed by DeepWiki, inform the user:

```
This repository hasn't been indexed by DeepWiki yet.
Visit https://deepwiki.com/{owner}/{repo} to trigger indexing, then try again.
```

### Step 3: Fetch Wiki Contents

Call the DeepWiki MCP tool to fetch all documentation content at once:

```
read_wiki_contents({ "repoName": "{owner}/{repo}" })
```

This returns the full documentation content for the repository as markdown.

Set up a working directory anchored to the output path:

```bash
WORK_DIR="$(dirname "{output}")/_deepwiki_export/{owner}-{repo}"
mkdir -p "${WORK_DIR}"
```

Split the returned content into separate chapter files based on the topic structure from Step 2. Use H1 headings (`# ...`) as chapter boundaries. Save each chapter as a numbered file:

```
{WORK_DIR}/001_introduction.md
{WORK_DIR}/002_architecture.md
{WORK_DIR}/003_core-concepts.md
...
```

Naming: `{three-digit sequence}_{topic_title_slugified}.md`

Three-digit prefixes support repos with 100+ topics.

**Splitting rules:**
- Match each H1 heading in the content to a topic from the structure
- If the content has no clear H1 boundaries, treat the entire content as a single chapter
- Preserve all content between H1 boundaries (sub-headings, code blocks, etc.)

### Step 4: Post-process Markdown Files

For each chapter markdown file:

1. **Ensure chapter heading**: If the file doesn't start with `# {topic_title}`, prepend it
2. **Clean DeepWiki artifacts**: Remove any navigation links, breadcrumbs, or DeepWiki-specific UI elements if present in the markdown
3. **Preserve Mermaid blocks**: Keep ` ```mermaid ` code blocks as-is (md2epub handles rendering)
4. **Handle external images**: If markdown references external image URLs, download them to `${WORK_DIR}/images/` and update references to local paths

```bash
mkdir -p "${WORK_DIR}/images"
# For each external image URL found in markdown:
# curl -sL "{image_url}" -o "${WORK_DIR}/images/{filename}"
# Update markdown reference to ./images/{filename}
```

### Step 5: Delegate to md2epub Skill

Follow the **md2epub SKILL.md workflow starting from Step 2** (Set Up Build Directory), passing these parameters:

| md2epub parameter | Value |
|-------------------|-------|
| `input_files` | `${WORK_DIR}/*.md` (sorted by filename) |
| `output_epub` | `{output}` |
| `title` | `{title}` |
| `author` | `{author}` |
| `lang` | `{lang}` |
| `cover` | `{cover}` (omit if not set) |
| `render_mermaid` | `{render_mermaid}` |

Do **not** invoke md2epub as a separate skill call. Instead, read `${HOME}/.claude/skills/md2epub/SKILL.md` and execute its Steps 2–6 inline with the parameters above. This ensures a single continuous workflow.

### Step 6: Clean Up and Report

Remove the working directory:

```bash
rm -rf "${WORK_DIR}"
# Also remove parent if empty
rmdir "$(dirname "{output}")/_deepwiki_export" 2>/dev/null || true
```

Output a report:

```
✅ DeepWiki → EPUB conversion complete

Repository: {owner}/{repo}
File:       {output}
Size:       {file_size}
Chapters:   {chapter_count}
Diagrams:   {success_count} rendered as images / {fail_count} kept as code blocks

Source: https://deepwiki.com/{owner}/{repo}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| DeepWiki MCP not configured | Print setup command and stop |
| md2epub skill not installed | Print installation instructions and stop |
| Repo not indexed by DeepWiki | Suggest visiting deepwiki.com to trigger indexing |
| Content fetch returns empty | Abort and suggest the repo may not be indexed |
| Content cannot be split into chapters | Use entire content as a single chapter |
| md2epub conversion fails | Surface the error from md2epub (likely pandoc issue) |
| External image download fails | Keep original URL reference, note in report |

## Examples

**Example 1: Basic usage**
> User: "deepwiki epub facebook/react"

```
repo   = facebook/react
output = ./facebook-react.epub
title  = react (from DeepWiki)
author = facebook
lang   = en
```

**Example 2: Chinese language**
> User: "把 langchain-ai/langchain 的 deepwiki 转成电子书"

```
repo   = langchain-ai/langchain
output = ./langchain-ai-langchain.epub
title  = langchain (from DeepWiki)
author = langchain-ai
lang   = zh-CN
```

**Example 3: Custom title and output**
> User: "convert deepwiki of anthropic/claude-code to epub, title 'Claude Code Internals', save to ~/Books/"

```
repo   = anthropic/claude-code
output = ~/Books/anthropic-claude-code.epub
title  = Claude Code Internals
author = anthropic
lang   = en
```

**Example 4: From DeepWiki URL**
> User: "deepwiki2epub https://deepwiki.com/golang/go"

```
repo   = golang/go
output = ./golang-go.epub
title  = go (from DeepWiki)
author = golang
lang   = en
```
