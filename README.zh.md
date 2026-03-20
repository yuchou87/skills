# Claude Code Skills

> 一组用于 [Claude Code](https://claude.ai/code) 的 Skill，让 Claude 在特定场景下像领域专家一样工作。

**[English](README.md)**

---

## Skills 列表

| Skill | 描述 | 文档 |
|-------|------|------|
| [unit-test-methodology](unit-test-methodology/) | 系统化单元测试生成，强制应用等价类、边界值、决策表等测试方法论，支持 Go / Python / Java / TypeScript / Rust / Zig | [README](unit-test-methodology/README.zh.md) |

---

## 安装

### 单个 Skill

```bash
# 克隆整个仓库
git clone https://github.com/yuchou87/skills.git

# 将需要的 Skill 软链接到 Claude Code Skills 目录
ln -s /path/to/skills/unit-test-methodology ~/.claude/skills/unit-test-methodology
```

### 全部 Skill

```bash
# 直接将整个仓库克隆到 Skills 目录
git clone https://github.com/yuchou87/skills.git ~/.claude/skills
```

### 更新

```bash
cd ~/.claude/skills
git pull
```

---

## 使用

安装后，在 Claude Code 对话中直接描述需求即可触发对应 Skill。每个 Skill 的触发短语详见各自的文档。

---

## 贡献

欢迎提交新的 Skill 或改进现有 Skill。每个 Skill 需包含：

- `SKILL.md`：Skill 主文件
- `README.md` + `README.zh.md`：英文和中文使用说明
- `evals/evals.json`：测试用例集
