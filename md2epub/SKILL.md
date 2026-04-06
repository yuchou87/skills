---
name: md2epub
description: >
  将 Markdown 文件转换为 EPUB3 电子书。支持单文件或多文件合并，
  自动将 Mermaid 代码块渲染为图片嵌入电子书。
  当用户说"生成电子书"、"转成 epub"、"打包成电子书"、"md 转 epub" 时使用本技能。
version: 1.1.0
---

# Markdown → EPUB 转换技能

## 脚本目录

脚本位于本 SKILL.md 同级的 `scripts/` 目录。

**重要**：在步骤 3 前，必须先解析 `{baseDir}` 的实际路径：

```bash
# 获取本 SKILL.md 所在目录的绝对路径（Issue #5 修复）
SKILL_DIR="$(cd "$(dirname "$(python3 -c "import subprocess; print(subprocess.check_output(['find', '$HOME/.claude/skills/md2epub', '-name', 'SKILL.md']).decode().strip())")")" && pwd)"
# 或者更简单：直接用已知安装路径
SKILL_DIR="${HOME}/.claude/skills/md2epub"
```

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
| `alt_label` | 图片 alt 文字前缀 | `图表`（中文）或 `Diagram`（英文） |

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
python3 "${SKILL_DIR}/scripts/preprocess_mermaid.py" \
  "{input_file}" \
  "${BUILD_DIR}/{input_file_basename}" \
  "${IMG_DIR}" \
  "{alt_label}"
```

- 脚本会把 `![{alt_label} N](xxx.png)` 写入处理后的 MD 文件
- PNG 图片保存在 `${IMG_DIR}/` 下
- 若某个 mermaid 块渲染失败（含超时），保留原始代码块（降级，不中断）
- 首次运行 npx 会下载 mermaid-cli，可能需要 1-2 分钟，属正常现象

若 `render_mermaid=false` 或无 `npx`，直接将原始 MD 文件复制到 `${BUILD_DIR}/`。

将渲染好的 PNG 复制到 `${BUILD_DIR}/`（pandoc 需要从同一目录解析图片相对路径）：

```bash
cp "${IMG_DIR}"/*.png "${BUILD_DIR}/" 2>/dev/null || true
```

### 步骤 4：生成 EPUB 元数据文件

在 `${BUILD_DIR}/metadata.yaml` 写入（toc 选项只在此处指定，不在 pandoc 命令重复）：

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

用子 shell 执行以避免影响当前 shell 的工作目录（Issue #4 修复）：

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
    {--epub-cover-image="{cover}" 若有封面} \
    {处理后的 MD 文件列表，按顺序}
)
```

**关于 `--split-level`**：
- `1`（默认）：每个 H1 标题生成独立章节文件，适合多文件合并场景
- `2`：按 H2 分割，适合单文件且 H1 极多的情况

### 步骤 6：清理并输出结果报告

构建完成后删除临时构建目录（保持用户项目整洁）：

```bash
rm -rf "${BUILD_DIR}"
```

然后输出报告：

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
| 首次运行 npx 很慢 | 正常，首次下载 mermaid-cli 需 1-2 分钟，脚本超时已设为 120 秒 |
| Mermaid 渲染失败 | 保留代码块，继续生成，在报告中标注失败数 |
| pandoc 找不到图片 | 确认步骤 5 使用了子 shell `(cd ... && pandoc ...)` 形式 |
| 中文显示"Abstract"警告 | 可忽略，是 pandoc 的语言包缺失警告，不影响内容 |
| EPUB 文件损坏 | 用 `epubcheck {output_epub}` 验证（若已安装） |
| 某 MD 文件含相对路径图片 | 将图片复制到 `${BUILD_DIR}/` 后再转换 |

## 使用示例

**示例 1：将目录下的全部 MD 文件生成电子书**
> 用户说："把 docs/explain/ 下的文件生成一本电子书"

1. `input_files` = `docs/explain/01_*.md docs/explain/02_*.md ...`（按名称排序）
2. `title` = 从第一个文件的第一个 H1 提取
3. 执行完整工作流

**示例 2：单文件转换**
> 用户说："把这个 README.md 转成 epub"

1. `input_files` = `README.md`
2. `output_epub` = `README.epub`
3. `render_mermaid` = 根据是否有 mermaid 代码块决定
4. `--split-level=2` 可能更适合单文件场景

**示例 3：指定元数据**
> 用户说："生成电子书，书名《AI 架构指南》，作者张三"

1. `title` = `AI 架构指南`
2. `author` = `张三`
3. 其余参数正常推断
