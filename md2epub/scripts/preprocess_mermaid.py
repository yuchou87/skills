#!/usr/bin/env python3
"""
md2epub skill — Mermaid 预处理器
将 Markdown 中的 ```mermaid 代码块渲染为 PNG 图片，并替换为图片引用。
用法: python preprocess_mermaid.py <input.md> <output.md> <img_dir>
"""
import re
import subprocess
import sys
import hashlib
from pathlib import Path


def render_mermaid_blocks(md_content: str, img_dir: Path, file_stem: str) -> tuple[str, int, int]:
    """
    渲染所有 mermaid 代码块为 PNG，返回 (处理后内容, 成功数, 失败数)。
    """
    pattern = re.compile(r'```mermaid\n(.*?)```', re.DOTALL)
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

        mmd_path.write_text(diagram_code, encoding="utf-8")

        if not png_path.exists():
            result = subprocess.run(
                ["npx", "--yes", "@mermaid-js/mermaid-cli",
                 "-i", str(mmd_path),
                 "-o", str(png_path),
                 "--backgroundColor", "white",
                 "--width", "1200"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                print(f"  ⚠ 渲染失败 [{img_name}]: {result.stderr.strip()[:80]}", file=sys.stderr)
                mmd_path.unlink(missing_ok=True)
                failed[0] += 1
                return match.group(0)  # 保留原始代码块

        mmd_path.unlink(missing_ok=True)
        success[0] += 1
        return f"![图表 {counter[0]}]({png_path.name})"

    new_content = pattern.sub(replace_block, md_content)
    return new_content, success[0], failed[0]


def main():
    if len(sys.argv) != 4:
        print(f"用法: {sys.argv[0]} <input.md> <output.md> <img_dir>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    img_dir = Path(sys.argv[3])
    img_dir.mkdir(parents=True, exist_ok=True)

    content = input_path.read_text(encoding="utf-8")
    new_content, ok, fail = render_mermaid_blocks(content, img_dir, input_path.stem)
    output_path.write_text(new_content, encoding="utf-8")

    print(f"✓ {input_path.name} → {output_path.name}  [图表: {ok}成功 {fail}失败]")


if __name__ == "__main__":
    main()
