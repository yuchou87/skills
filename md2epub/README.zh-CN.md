# md2epub

一个 Claude Code Skill，将 Markdown 文件转换为 EPUB3 电子书，并自动将 Mermaid 图表渲染为嵌入式 PNG 图片。

> **English documentation**: [README.md](README.md)

## 功能特性

- 支持单文件或多文件合并为一本电子书
- 自动将 ` ```mermaid ` 代码块渲染为 PNG 图片（通过 `npx @mermaid-js/mermaid-cli`）
- 支持 `en`（英文）、`zh-CN`（中文）、`bilingual`（双语）三种语言模式
- 自动生成目录
- 优雅降级：渲染失败的图表保留原始代码块，不中断构建

## 环境要求

| 工具 | 安装方式 | 是否必须 |
|------|---------|---------|
| [pandoc](https://pandoc.org) | `brew install pandoc` | 必须 |
| python3 | macOS 预装 | 必须 |
| Node.js / npx | [nodejs.org](https://nodejs.org) | 仅 Mermaid 渲染需要 |

## 安装方法

将 Skill 复制到 Claude Code 的 skills 目录：

```bash
# 克隆或下载本仓库后：
cp -r md2epub ~/.claude/skills/md2epub
```

或从完整 skills 仓库安装：

```bash
git clone https://github.com/yuchou87/skills ~/.claude/skills-repo
cp -r ~/.claude/skills-repo/md2epub ~/.claude/skills/md2epub
```

安装后在 Claude Code 会话中，Skill 列表会出现 `md2epub` 条目即表示成功。

## 使用方法

用自然语言描述需求，Claude 会自动识别并触发本 Skill。

**中文唤醒词：**
- "生成电子书"
- "转成 epub"
- "打包成电子书"
- "md 转 epub"

**英文触发词：**
- "generate an ebook from these markdown files"
- "convert to epub"
- "make an epub from docs/"
- "md to epub"

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_files` | 要转换的 MD 文件：单个文件、文件列表或目录 | 当前目录的 `*.md` |
| `output_epub` | 输出路径 | `{第一个文件所在目录}/book.epub` |
| `title` | 书名 | 第一个 H1 标题，或文件名 |
| `author` | 作者名 | *(留空则不写入)* |
| `lang` | 语言模式：`en` / `zh-CN` / `bilingual` | `en` |
| `cover` | 封面图片路径 | *(无封面)* |
| `render_mermaid` | 是否渲染 Mermaid 图表 | `true`（若 npx 可用） |

### 语言模式说明

| `lang` 值 | EPUB lang 字段 | 图表 alt 文字 |
|----------|---------------|--------------|
| `en` | `en` | `Diagram` |
| `zh-CN` | `zh-CN` | `图表` |
| `bilingual` | `zh-CN` | `Diagram / 图表` |

### 使用示例

**将目录下的 MD 文件生成电子书：**
> "把 docs/explain/ 下的文件生成一本电子书，书名《OpenHarness 深度解析》，作者张三"

**单文件转换（中文）：**
> "把 README.md 转成 epub，语言中文"

**双语电子书：**
> "生成双语电子书，书名《AI 架构指南》"

## 工作原理

```
输入 MD 文件
      │
      ▼
[第 1 步] 预处理 Mermaid 图表
          scripts/preprocess_mermaid.py
          → 将每个 ```mermaid 块通过 npx mmdc 渲染为 PNG
          → 替换为 ![图表 N](xxx.png) 引用
      │
      ▼
[第 2 步] 生成 metadata.yaml
          书名、作者、语言、目录设置
      │
      ▼
[第 3 步] 调用 pandoc
          --from markdown+raw_html --to epub3
          --split-level=1（每个 H1 独立章节）
      │
      ▼
输出：book.epub
```

## 目录结构

```
md2epub/
├── SKILL.md                      # Skill 定义文件（Claude Code 读取）
├── README.md                     # 英文说明文档
├── README.zh-CN.md               # 本文件（中文说明）
└── scripts/
    └── preprocess_mermaid.py     # Mermaid → PNG 渲染脚本
```

## 常见问题

| 问题 | 解决方法 |
|------|---------|
| 首次运行很慢 | 正常现象——npx 首次使用会下载 mermaid-cli，约需 1~2 分钟 |
| Mermaid 渲染失败 | 图表以代码块保留，构建继续，报告中会标注失败数量 |
| 找不到 pandoc | 执行 `brew install pandoc` |
| EPUB 显示异常 | 用 `epubcheck book.epub` 验证文件完整性 |
| 中文出现 "Abstract" 警告 | 可忽略，是 pandoc 语言包缺失的警告，不影响内容 |

## 版本历史

当前版本：**1.2.0**

| 版本 | 变更内容 |
|------|---------|
| 1.2.0 | 全面英文化；新增 `lang` 参数支持 `en` / `zh-CN` / `bilingual` 三种模式 |
| 1.1.0 | 超时优雅处理、空 PNG 检测、友好错误提示 |
| 1.0.0 | 初始版本 |
