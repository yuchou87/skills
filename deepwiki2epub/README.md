# deepwiki2epub

A Claude Code skill that converts [DeepWiki](https://deepwiki.com) repository documentation into EPUB3 ebooks for offline mobile reading.

> **中文说明**: [README.zh-CN.md](README.zh-CN.md)

## Features

- Fetches AI-generated documentation from DeepWiki via its official MCP server
- Assembles topics into ordered chapters automatically
- Delegates EPUB generation to the [md2epub](../md2epub/) skill (Mermaid rendering, TOC, etc.)
- Supports `en`, `zh-CN`, and `bilingual` language modes
- Accepts GitHub URLs, DeepWiki URLs, or `owner/repo` shorthand

## Requirements

| Dependency | Install | Required |
|------------|---------|----------|
| DeepWiki MCP | `claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp` | Yes |
| [md2epub skill](../md2epub/) | `cp -r md2epub ~/.claude/skills/md2epub` | Yes |
| [pandoc](https://pandoc.org) | `brew install pandoc` | Yes |
| python3 | pre-installed on macOS | Yes |
| Node.js / npx | [nodejs.org](https://nodejs.org) | Only for Mermaid rendering |

## Installation

```bash
# 1. Install this skill
cp -r deepwiki2epub ~/.claude/skills/deepwiki2epub

# 2. Install md2epub skill (required dependency)
cp -r md2epub ~/.claude/skills/md2epub

# 3. Configure DeepWiki MCP server
claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp
```

## Usage

Invoke the skill with natural language. Claude automatically triggers it when it detects relevant intent.

**English triggers:**
- "deepwiki to epub facebook/react"
- "convert deepwiki to ebook"
- "download deepwiki as epub"

**Chinese triggers (中文唤醒):**
- "deepwiki 转 epub"
- "从 deepwiki 生成电子书"
- "把 deepwiki 转成电子书"

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `repo` | GitHub repo (`owner/repo` or full URL) | *(required)* |
| `output` | Output EPUB file path | `./{owner}-{repo}.epub` |
| `title` | Book title | `{repo} (from DeepWiki)` |
| `author` | Author name | `{owner}` |
| `lang` | Language mode: `en` / `zh-CN` / `bilingual` | `en` |
| `render_mermaid` | Render Mermaid diagrams to images | `true` |

### Examples

**Basic:**
> "deepwiki epub facebook/react"

**From URL:**
> "deepwiki2epub https://deepwiki.com/golang/go"

**Chinese with custom title:**
> "把 langchain-ai/langchain 的 deepwiki 转成电子书，书名《LangChain 深度解析》"

## How it works

```
DeepWiki MCP
      │
      ▼
[Step 1] read_wiki_structure → get topic list
      │
      ▼
[Step 2] read_wiki_contents × N → fetch each topic as markdown
      │
      ▼
[Step 3] Post-process: add headings, download images
      │
      ▼
[Step 4] Delegate to md2epub skill
         → Mermaid rendering → pandoc → EPUB3
      │
      ▼
Output: {owner}-{repo}.epub
```

## File structure

```
deepwiki2epub/
├── SKILL.md          # Skill definition (read by Claude Code)
├── README.md         # This file
└── README.zh-CN.md   # Chinese documentation
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "DeepWiki MCP not configured" | Run `claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp` |
| "Repo not indexed" | Visit `https://deepwiki.com/{owner}/{repo}` to trigger indexing |
| Some chapters missing | DeepWiki may rate-limit; try again later |
| md2epub errors | Check pandoc installation: `brew install pandoc` |

## Version

Current version: **1.0.0**

Changes:
- `1.0.0` — Initial release: DeepWiki MCP fetch + md2epub delegation
