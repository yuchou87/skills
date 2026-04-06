#!/usr/bin/env python3
"""
md2epub skill — Mermaid preprocessor
Renders ```mermaid code blocks in Markdown to PNG images and replaces them with image references.
Usage: python preprocess_mermaid.py <input.md> <output.md> <img_dir> [alt_label]
  alt_label: prefix for image alt text, default "Diagram"
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
    Render all mermaid code blocks to PNG, return (processed content, success count, fail count).
    Supports LF and CRLF line endings, and trailing spaces after the opening fence.
    """
    # Compatible with CRLF and trailing whitespace after fence tag (S1)
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

        # Remove any stale output to ensure result is trustworthy (Issue #1)
        png_path.unlink(missing_ok=True)
        mmd_path.write_text(diagram_code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["npx", "--yes", "@mermaid-js/mermaid-cli",
                 "-i", str(mmd_path),
                 "-o", str(png_path),
                 "--backgroundColor", "white",
                 "--width", "1200"],
                capture_output=True, text=True, timeout=120,  # first npx run may need to download mermaid-cli
            )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as exc:
            # Issue #2: on timeout or subprocess error, fall back to keeping the original code block
            print(f"  ⚠ Render timeout/error [diagram {counter[0]}]: {exc}", file=sys.stderr)
            mmd_path.unlink(missing_ok=True)
            png_path.unlink(missing_ok=True)
            failed[0] += 1
            return match.group(0)

        mmd_path.unlink(missing_ok=True)

        # Issue #1: verify output file exists and is non-empty
        if result.returncode != 0 or not png_path.exists() or png_path.stat().st_size == 0:
            print(
                f"  ⚠ Render failed [diagram {counter[0]}]: {result.stderr.strip()[:100]}",
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
            f"Usage: {sys.argv[0]} <input.md> <output.md> <img_dir> [alt_label]",
            file=sys.stderr,
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    img_dir = Path(sys.argv[3])
    alt_label = sys.argv[4] if len(sys.argv) > 4 else "Diagram"

    # Issue #3: friendly error for missing input file
    try:
        content = input_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"❌ Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except OSError as exc:
        print(f"❌ Failed to read file: {exc}", file=sys.stderr)
        sys.exit(1)

    img_dir.mkdir(parents=True, exist_ok=True)
    new_content, ok, fail = render_mermaid_blocks(content, img_dir, input_path.stem, alt_label)
    output_path.write_text(new_content, encoding="utf-8")

    print(f"✓ {input_path.name} → {output_path.name}  [diagrams: {ok} succeeded, {fail} failed]")


if __name__ == "__main__":
    main()
