# Claude Code Skills

一个可复用的 [Claude Code](https://claude.ai/code) Skill 合集，覆盖常见开发工作流。

> **English documentation**: [README.md](README.md)

## 什么是 Skill？

Claude Code Skill 是基于 Markdown 的工作流定义文件，用于教会 Claude 如何执行特定任务。安装后，只需用自然语言描述需求，Claude 即可自动触发对应 Skill，无需记忆任何命令。

每个 Skill 存放在独立目录中，包含：
- `SKILL.md` — 工作流定义（Claude Code 读取）
- `README.md` — 英文说明文档
- `README.zh-CN.md` — 中文说明文档
- `scripts/` — 可选的辅助脚本

## 安装方法

```bash
# 克隆整个仓库到 Claude Code skills 目录
git clone https://github.com/yuchou87/skills ~/.claude/skills

# 或仅安装单个 Skill
git clone https://github.com/yuchou87/skills /tmp/skills
cp -r /tmp/skills/<skill-name> ~/.claude/skills/<skill-name>
```

放置在 `~/.claude/skills/` 下的 Skill 会被 Claude Code 自动发现。

## Skill 列表

| Skill | 说明 | 触发词 |
|-------|------|--------|
| [md2epub](md2epub/) | 将 Markdown 文件转换为 EPUB3 电子书，支持 Mermaid 图表渲染 | "生成电子书"、"转成 epub"、"generate ebook" |
| [deepwiki2epub](deepwiki2epub/) | 将 DeepWiki 仓库文档转换为 EPUB3 电子书，支持离线阅读 | "deepwiki 电子书"、"deepwiki 转 epub" |

## 贡献指南

1. Fork 本仓库
2. 为你的 Skill 创建目录：`mkdir my-skill`
3. 按照 [Claude Code Skill 格式](https://docs.anthropic.com/en/docs/claude-code/skills) 编写 `SKILL.md`
4. 添加 `README.md` 和 `README.zh-CN.md`
5. 提交 Pull Request

## 许可证

MIT — 详见 [LICENSE](LICENSE)
