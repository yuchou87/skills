#!/usr/bin/env python3
"""
md2epub skill — Mermaid 预处理器
将 Markdown 中的 ```mermaid 代码块渲染为 PNG 图片，并替换为图片引用。
用法: python preprocess_mermaid.py <input.md> <output.md> <img_dir> [alt_label]
  alt_label: 图片 alt 文字前缀，默认 "Diagram"（可传 "图表" 用于中文输出）
"""
import re
import subprocess
import sys
import hashlib
from pathlib import Path


def render_mermaid_blocks(
    md_content: str,
    img_dir: Path,
    file_stem: str,
    alt_label: str = "Diagram",
) -> tuple[str, int, int]:
    """
    渲染所有 mermaid 代码块为 PNG，返回 (处理后内容, 成功数, 失败数)。
    支持 LF 和 CRLF 行尾，以及开头 fence 行尾有空格的情况。
    """
    # 兼容 CRLF 和 fence 后有空格的情况（S1）
    pattern = re.compile(r'```mermaid[ \t]*\r?\n(.*?)```', re.DOTALL)
    counter = [0]
    success = [0]
    failed = [0]

    def replace_block(match: re.Match) -> str:
        diagram_code = match.group(1).strip()
        counter[0] += 1

        content_hash = hashlib.md5(diagram_code.encode()).hexdigest()[:8]
        img_name = f"{file_stem}_d{counter[0]:02d}_{content_hash}"
        mmd_path = img_dir / f"{img_name}.mmd"
        png_path = img_dir / f"{img_name}.png"

        # 删除旧的可能损坏的输出，确保结果可信（Issue #1）
        png_path.unlink(missing_ok=True)
        mmd_path.write_text(diagram_code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["npx", "--yes", "@mermaid-js/mermaid-cli",
                 "-i", str(mmd_path),
                 "-o", str(png_path),
                 "--backgroundColor", "white",
                 "--width", "1200"],
                capture_output=True, text=True, timeout=120,  # 首次 npx 下载需要更长时间
            )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as exc:
            # Issue #2：超时或子进程错误，降级为保留原始代码块
            print(f"  ⚠ 渲染超时/错误 [图表 {counter[0]}]: {exc}", file=sys.stderr)
            mmd_path.unlink(missing_ok=True)
            png_path.unlink(missing_ok=True)
            failed[0] += 1
            return match.group(0)

        mmd_path.unlink(missing_ok=True)

        # Issue #1：验证输出文件存在且非空
        if result.returncode != 0 or not png_path.exists() or png_path.stat().st_size == 0:
            print(
                f"  ⚠ 渲染失败 [图表 {counter[0]}]: {result.stderr.strip()[:100]}",
                file=sys.stderr,
            )
            png_path.unlink(missing_ok=True)
            failed[0] += 1
            return match.group(0)

        success[0] += 1
        return f"![{alt_label} {counter[0]}]({png_path.name})"

    new_content = pattern.sub(replace_block, md_content)
    return new_content, success[0], failed[0]


def main():
    if len(sys.argv) < 4:
        print(
            f"用法: {sys.argv[0]} <input.md> <output.md> <img_dir> [alt_label]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    img_dir = Path(sys.argv[3])
    alt_label = sys.argv[4] if len(sys.argv) > 4 else "Diagram"

    # Issue #3：友好处理文件不存在的情况
    try:
        content = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"❌ 输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"❌ 读取文件失败: {exc}", file=sys.stderr)
        sys.exit(1)

    img_dir.mkdir(parents=True, exist_ok=True)
    new_content, ok, fail = render_mermaid_blocks(content, img_dir, input_path.stem, alt_label)
    output_path.write_text(new_content, encoding="utf-8")

    print(f"✓ {input_path.name} → {output_path.name}  [图表: {ok} 成功, {fail} 失败]")


if __name__ == "__main__":
    main()
