# Claude Code Skills

A collection of reusable [Claude Code](https://claude.ai/code) skills for everyday development workflows.

> **中文说明**: [README.zh-CN.md](README.zh-CN.md)

## What are Skills?

Claude Code Skills are Markdown-based workflow definitions that teach Claude how to perform specific tasks. Once installed, they are automatically triggered when you describe what you want in natural language — no commands to memorize.

Each skill lives in its own directory and consists of:
- `SKILL.md` — the workflow definition (read by Claude Code)
- `README.md` — human-readable documentation
- `scripts/` — optional helper scripts

## Installation

```bash
# Clone this repo into your Claude Code skills directory
git clone https://github.com/yuchou87/skills ~/.claude/skills

# Or install a single skill
git clone https://github.com/yuchou87/skills /tmp/skills
cp -r /tmp/skills/<skill-name> ~/.claude/skills/<skill-name>
```

Claude Code automatically discovers skills placed in `~/.claude/skills/`.

## Skills

| Skill | Description | Triggers |
|-------|-------------|---------|
| [md2epub](md2epub/) | Convert Markdown files to EPUB3 ebooks with Mermaid diagram rendering | "generate ebook", "convert to epub", "生成电子书" |
| [deepwiki2epub](deepwiki2epub/) | Convert DeepWiki repo docs to EPUB3 ebooks for offline reading | "deepwiki to epub", "deepwiki 电子书" |

## Contributing

1. Fork this repo
2. Create a directory for your skill: `mkdir my-skill`
3. Add `SKILL.md` following the [Claude Code skill format](https://docs.anthropic.com/en/docs/claude-code/skills)
4. Add `README.md` and `README.zh-CN.md`
5. Open a pull request

## License

MIT — see [LICENSE](LICENSE)
