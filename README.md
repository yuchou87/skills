# Claude Code Skills

> A collection of Skills for [Claude Code](https://claude.ai/code) that make Claude work like a domain expert in specific scenarios.

**[中文](README.zh.md)**

---

## Skills

| Skill | Description | Docs |
|-------|-------------|------|
| [unit-test-methodology](unit-test-methodology/) | Systematic unit test generation enforcing equivalence partitioning, boundary value analysis, decision tables, and more. Supports Go / Python / Java / TypeScript / Rust / Zig | [README](unit-test-methodology/README.md) |

---

## Installation

### Single skill

```bash
# Clone the repository
git clone https://github.com/yuchou87/skills.git

# Symlink the skill into Claude Code's Skills directory
ln -s /path/to/skills/unit-test-methodology ~/.claude/skills/unit-test-methodology
```

### All skills

```bash
# Clone the entire repository directly into the Skills directory
git clone https://github.com/yuchou87/skills.git ~/.claude/skills
```

### Updating

```bash
cd ~/.claude/skills
git pull
```

---

## Usage

Once installed, simply describe your task in Claude Code — the relevant Skill will trigger automatically. See each Skill's README for its specific trigger phrases.

---

## Contributing

Contributions are welcome. Each Skill should include:

- `SKILL.md`: the Skill definition
- `README.md` + `README.zh.md`: English and Chinese documentation
- `evals/evals.json`: test case set
