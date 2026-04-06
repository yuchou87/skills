---
name: md2epub
description: >
  将 Markdown 文件转换为 EPUB3 电子书。支持单文件或多文件合并，
  自动将 Mermaid 代码块渲染为图片嵌入电子书。
  当用户说"生成电子书"、"转成 epub"、"打包成电子书"、"md 转 epub" 时使用本技能。
version: 1.0.0
---

# Markdown → EPUB 转换技能

## 脚本目录

脚本位于本 SKILL.md 同级的 `scripts/` 目录，`{baseDir}` = 本文件所在目录的绝对路径。

| 脚本 | 用途 |
|------|------|
| `scripts/preprocess_mermaid.py` | 将 Markdown 中的 mermaid 代码块渲染为 PNG，并替换为图片引用 |

## 前置依赖检查

执行前先确认以下工具可用，若缺失则提示用户安装：

```bash
# 必须
which pandoc   || echo "❌ 缺少 pandoc：brew install pandoc"
which python3  || echo "❌ 缺少 python3"

# Mermaid 渲染（有 npx 则自动安装，无需手动）
which npx      || echo "⚠ 无 npx，Mermaid 图将保留为代码块（需安装 Node.js）"
```

## 工作流程

### 步骤 1：收集输入信息

询问或从上下文推断以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_files` | 要转换的 MD 文件，可以是单个文件、文件列表、或目录（自动按名称排序） | 当前目录的 `*.md` |
| `output_epub` | 输出文件路径 | `{第一个文件的目录}/book.epub` |
| `title` | 书名 | 第一个 H1 标题，或文件名 |
| `author` | 作者 | （可选）留空则不写入 |
| `lang` | 语言代码 | `zh-CN` |
| `cover` | 封面图片路径 | （可选）留空则无封面 |
| `render_mermaid` | 是否渲染 Mermaid 图表 | `true`（若有 npx） |

**文件排序规则**：若输入为目录，按文件名升序排列，数字前缀的文件（如 `01_`, `02_`）会自然有序。

### 步骤 2：建立构建目录

```bash
BUILD_DIR="$(dirname {output_epub})/_epub_build"
IMG_DIR="${BUILD_DIR}/images"
mkdir -p "${BUILD_DIR}" "${IMG_DIR}"
```

### 步骤 3：预处理 Mermaid 图表

若 `render_mermaid=true` 且 `npx` 可用，对每个输入文件执行：

```bash
python3 {baseDir}/scripts/preprocess_mermaid.py \
  "{input_file}" \
  "${BUILD_DIR}/{input_file_basename}" \
  "${IMG_DIR}"
```

- 脚本会把 `![图表 N](xxx.png)` 写入处理后的 MD 文件
- PNG 图片保存在 `${IMG_DIR}/` 下
- 若某个 mermaid 块渲染失败，保留原始代码块（降级处理，不中断）

若 `render_mermaid=false` 或无 `npx`，直接将原始 MD 文件复制到 `${BUILD_DIR}/`。

将 `${IMG_DIR}/*.png` 复制到 `${BUILD_DIR}/`（pandoc 需要从同一目录解析图片相对路径）：

```bash
cp "${IMG_DIR}"/*.png "${BUILD_DIR}/" 2>/dev/null || true
```

### 步骤 4：生成 EPUB 元数据文件

在 `${BUILD_DIR}/metadata.yaml` 写入：

```yaml
---
title: '{title}'
author: '{author}'     # 若为空则省略此行
lang: {lang}
toc: true
toc-depth: 2
---
```

### 步骤 5：调用 pandoc 生成 EPUB

切换到 `${BUILD_DIR}` 再执行（确保图片相对路径正确）：

```bash
cd "${BUILD_DIR}"

pandoc \
  --from markdown+raw_html \
  --to epub3 \
  --output "{output_epub}" \
  --metadata-file metadata.yaml \
  --toc \
  --toc-depth=2 \
  --split-level=1 \
  --resource-path="${BUILD_DIR}" \
  --wrap=none \
  {--epub-cover-image="{cover}" 若有封面} \
  {处理后的 MD 文件列表，按顺序}
```

### 步骤 6：输出结果报告

```
✅ 电子书生成成功

文件：{output_epub}
大小：{文件大小}
章节：{章节数}（来自 {文件数} 个 MD 文件）
图表：{成功渲染数} 张图片 / {失败数} 张降级为代码块

后续操作：
  用 Calibre 打开：open '{output_epub}'
  转为 PDF：ebook-convert '{output_epub}' '{output_epub%.epub}.pdf'
  转为 MOBI：ebook-convert '{output_epub}' '{output_epub%.epub}.mobi'
```

## 常见问题处理

| 问题 | 处理方式 |
|------|---------|
| Mermaid 渲染失败（npx 超时） | 保留代码块，继续生成，在报告中标注 |
| pandoc 找不到图片 | 确认已 `cd ${BUILD_DIR}` 再执行 pandoc |
| 中文显示"Abstract"警告 | 可忽略，是 pandoc 的语言包缺失警告，不影响内容 |
| EPUB 文件损坏 | 用 `epubcheck {output_epub}` 验证（若已安装） |
| 某 MD 文件含相对路径图片 | 将图片复制到 `${BUILD_DIR}/` 后再转换 |

## 使用示例

**示例 1：将当前目录的全部 MD 文件生成电子书**
> 用户说："把 docs/explain/ 下的文件生成一本电子书"

1. `input_files` = `docs/explain/01_*.md docs/explain/02_*.md ...`（按名称排序）
2. `title` = 从第一个文件的第一个 H1 提取
3. 执行完整工作流

**示例 2：单文件转换**
> 用户说："把这个 README.md 转成 epub"

1. `input_files` = `README.md`
2. `output_epub` = `README.epub`
3. `render_mermaid` = 根据是否有 mermaid 代码块决定

**示例 3：指定元数据**
> 用户说："生成电子书，书名《AI 架构指南》，作者张三"

1. `title` = `AI 架构指南`
2. `author` = `张三`
3. 其余参数正常推断
