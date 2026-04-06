---
name: deepwiki2epub
description: >
  Convert DeepWiki repository documentation to EPUB3 ebooks for offline reading.
  Fetches content via DeepWiki MCP server, assembles chapters, then delegates to
  md2epub skill for EPUB generation.
  Trigger keywords: "deepwiki to epub", "deepwiki epub", "deepwiki ebook",
  "deepwiki 电子书", "deepwiki 转 epub", "从 deepwiki 生成电子书",
  "convert deepwiki to ebook", "download deepwiki as epub"
version: 1.0.0
---

# DeepWiki → EPUB Conversion Skill

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
test -f "${HOME}/.claude/skills/md2epub/SKILL.md" && echo "OK" || echo "MISSING: install md2epub skill first"
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
| `render_mermaid` | Whether to render Mermaid diagrams | `true` (if npx available) |

**Repo format normalization**: Accept any of these formats and extract `{owner}/{repo}`:
- `facebook/react`
- `https://github.com/facebook/react`
- `github.com/facebook/react`
- `https://deepwiki.com/facebook/react`

### Step 2: Fetch Wiki Structure

Call the DeepWiki MCP tool:

```
read_wiki_structure({ "repoName": "{owner}/{repo}" })
```

This returns the documentation hierarchy — a list of topics with IDs and titles.

Record:
- Total topic count
- Topic order (for chapter sequencing)

If the repo is not indexed by DeepWiki, inform the user:

```
This repository hasn't been indexed by DeepWiki yet.
Visit https://deepwiki.com/{owner}/{repo} to trigger indexing, then try again.
```

### Step 3: Fetch All Topic Contents

Set up a working directory:

```bash
WORK_DIR="./_deepwiki_export/{owner}-{repo}"
mkdir -p "${WORK_DIR}"
```

For each topic in the structure (in order), call:

```
read_wiki_contents({ "repoName": "{owner}/{repo}", "topicId": "{topic_id}" })
```

Save each topic's markdown content to a numbered file:

```
{WORK_DIR}/01_introduction.md
{WORK_DIR}/02_architecture.md
{WORK_DIR}/03_core-concepts.md
...
```

Naming: `{two-digit sequence}_{topic_id_slugified}.md`

**Error handling per topic:**
- If a single topic fetch fails, log a warning and skip it
- Continue with remaining topics
- Track skipped topics for the final report

### Step 4: Post-process Markdown Files

For each downloaded markdown file:

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

Invoke the `md2epub` skill with the following parameters:

| md2epub parameter | Value |
|-------------------|-------|
| `input_files` | `${WORK_DIR}/*.md` (sorted by filename) |
| `output_epub` | `{output}` |
| `title` | `{title}` |
| `author` | `{author}` |
| `lang` | `{lang}` |
| `render_mermaid` | `{render_mermaid}` |

The md2epub skill handles: Mermaid preprocessing, metadata generation, pandoc conversion, and build directory cleanup.

### Step 6: Clean Up and Report

Remove the working directory:

```bash
rm -rf "${WORK_DIR}"
# Also remove parent if empty
rmdir "./_deepwiki_export" 2>/dev/null || true
```

Output a report:

```
DeepWiki → EPUB conversion complete

Repository: {owner}/{repo}
File:       {output}
Size:       {file_size}
Chapters:   {success_count} of {total_topics} topics
Skipped:    {skip_count} topics (if any)
Diagrams:   (reported by md2epub)

Source: https://deepwiki.com/{owner}/{repo}
```

## Error Handling

| Scenario | Action |
|----------|--------|
| DeepWiki MCP not configured | Print setup command and stop |
| md2epub skill not installed | Print installation instructions and stop |
| Repo not indexed by DeepWiki | Suggest visiting deepwiki.com to trigger indexing |
| Single topic fetch fails | Skip topic, continue with others, report at end |
| All topic fetches fail | Abort and report error |
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
> User: "convert deepwiki of anthropics/claude-code to epub, title 'Claude Code Internals', save to ~/Books/"

```
repo   = anthropics/claude-code
output = ~/Books/anthropics-claude-code.epub
title  = Claude Code Internals
author = anthropics
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
