# deepwiki2epub

一个 Claude Code Skill，将 [DeepWiki](https://deepwiki.com) 仓库文档转换为 EPUB3 电子书，支持手机离线阅读。

> **English documentation**: [README.md](README.md)

## 功能特性

- 通过 DeepWiki 官方 MCP 服务获取 AI 生成的仓库文档
- 自动将 topics 组装为有序章节
- 委托 [md2epub](../md2epub/) skill 生成 EPUB（含 Mermaid 渲染、目录等）
- 支持 `en`（英文）、`zh-CN`（中文）、`bilingual`（双语）三种语言模式
- 支持 GitHub URL、DeepWiki URL 或 `owner/repo` 简写

## 环境要求

| 依赖 | 安装方式 | 是否必须 |
|------|---------|---------|
| DeepWiki MCP | `claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp` | 必须 |
| [md2epub skill](../md2epub/) | `cp -r md2epub ~/.claude/skills/md2epub` | 必须 |
| [pandoc](https://pandoc.org) | `brew install pandoc` | 必须 |
| python3 | macOS 预装 | 必须 |
| Node.js / npx | [nodejs.org](https://nodejs.org) | 仅 Mermaid 渲染需要 |

## 安装方法

```bash
# 1. 安装本 Skill
cp -r deepwiki2epub ~/.claude/skills/deepwiki2epub

# 2. 安装 md2epub skill（必需依赖）
cp -r md2epub ~/.claude/skills/md2epub

# 3. 配置 DeepWiki MCP
claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp
```

## 使用方法

用自然语言描述需求，Claude 会自动识别并触发本 Skill。

**中文唤醒词：**
- "deepwiki 转 epub"
- "从 deepwiki 生成电子书"
- "把 deepwiki 转成电子书"
- "deepwiki 电子书"

**英文触发词：**
- "deepwiki to epub"
- "convert deepwiki to ebook"
- "download deepwiki as epub"

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `repo` | GitHub 仓库（`owner/repo` 或完整 URL） | *(必填)* |
| `output` | 输出 EPUB 路径 | `./{owner}-{repo}.epub` |
| `title` | 书名 | `{repo} (from DeepWiki)` |
| `author` | 作者 | `{owner}` |
| `lang` | 语言模式：`en` / `zh-CN` / `bilingual` | `en` |
| `render_mermaid` | 是否渲染 Mermaid 图表 | `true` |

### 使用示例

**基本用法：**
> "deepwiki epub facebook/react"

**从 URL：**
> "deepwiki2epub https://deepwiki.com/golang/go"

**中文 + 自定义书名：**
> "把 langchain-ai/langchain 的 deepwiki 转成电子书，书名《LangChain 深度解析》"

**指定输出路径：**
> "deepwiki 电子书 anthropics/claude-code，保存到 ~/Books/"

## 工作原理

```
DeepWiki MCP
      │
      ▼
[第 1 步] read_wiki_structure → 获取主题列表
      │
      ▼
[第 2 步] read_wiki_contents × N → 逐个获取主题 markdown
      │
      ▼
[第 3 步] 后处理：添加标题、下载图片
      │
      ▼
[第 4 步] 委托 md2epub skill
          → Mermaid 渲染 → pandoc → EPUB3
      │
      ▼
输出：{owner}-{repo}.epub
```

## 目录结构

```
deepwiki2epub/
├── SKILL.md          # Skill 定义文件（Claude Code 读取）
├── README.md         # 英文说明文档
└── README.zh-CN.md   # 本文件（中文说明）
```

## 常见问题

| 问题 | 解决方法 |
|------|---------|
| "DeepWiki MCP 未配置" | 运行 `claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp` |
| "仓库未被索引" | 访问 `https://deepwiki.com/{owner}/{repo}` 触发索引 |
| 部分章节缺失 | DeepWiki 可能有频率限制，稍后重试 |
| md2epub 报错 | 检查 pandoc 安装：`brew install pandoc` |

## 版本历史

当前版本：**1.0.0**

| 版本 | 变更内容 |
|------|---------|
| 1.0.0 | 初始版本：DeepWiki MCP 抓取 + md2epub 委托生成 |
