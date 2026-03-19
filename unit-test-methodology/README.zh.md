# unit-test-methodology

> 系统化单元测试生成 Skill，为 [Claude Code](https://claude.ai/code) 提供测试方法论驱动的测试用例生成能力。

**[English](README.md)**

---

## 简介

与随意生成测试不同，本 Skill 强制应用测试设计方法论：先分析函数特征，再系统推导测试用例，最后生成代码。覆盖等价类划分、边界值分析、决策表、Pairwise 组合等经典方法。

**支持语言**：Go / Python / Java / TypeScript

---

## 触发方式

在 Claude Code 中，以下任意说法都会触发本 Skill：

```
帮我写单元测试      给这个函数加测试      单测
写 test            补充测试            测试覆盖率不够
write tests for    add tests           test coverage
unit test          这个方法怎么测
```

---

## 工作流程

```
用户提供函数代码
      ↓
Step 1  识别语言，加载对应规范（Go / Python / Java / TypeScript）
      ↓
Step 2  分析函数：参数维度 · 行为维度 · 依赖维度
      ↓
Step 3  选择方法论：等价类 / 边界值 / 决策表 / Pairwise / 状态转换 / 幂等性
      ↓
Step 4  系统推导测试用例，每个用例标注来源方法论
      ↓
Step 5  生成有业务含义的真实感测试数据
      ↓
Step 6  输出完整可运行的测试代码
```

---

## 示例

**输入（Go）**：

```go
func CreateUser(name, email string, age int, repo UserRepository) (*User, error)
```

**输出（节选）**：

```go
func TestCreateUser(t *testing.T) {
    t.Parallel()
    tests := []struct { ... }{
        {name: "有效输入·正常创建用户",    technique: "EP·valid",   ...},  // happy path
        {name: "name为空·无效等价类",      technique: "EP·invalid·1", wantErr: ErrNameRequired},
        {name: "age=0·边界值min-1",        technique: "BV·min-1",   wantErr: ErrAgeInvalid},
        {name: "age=1·边界值min（有效）",  technique: "BV·min",     ...},
        {name: "age=151·边界值max+1",      technique: "BV·max+1",   wantErr: ErrAgeInvalid},
        {name: "数据库保存失败",           technique: "EP·invalid: dependency", ...},
    }
    // ...
}
```

---

## 方法论速查

| 方法论 | 适用场景 | 标注前缀 |
|--------|----------|----------|
| 等价类划分 | 任意参数 | `EP·valid` / `EP·invalid·N` |
| 边界值分析 | 数值/字符串有范围约束 | `BV·min` / `BV·max+1` |
| 决策表 | 多个条件共同影响输出 | `DT·...` |
| Pairwise 组合 | 独立参数 ≥ 4 个 | `PW·...` |
| 状态转换 | 对象有状态字段 | `ST·valid` / `ST·invalid` |
| 幂等性 | 写操作可重复调用 | `IDEM·...` |

---

## 文件结构

```
unit-test-methodology/
├── SKILL.md                  # Skill 主文件（Claude 读取）
├── README.md                 # English documentation
├── README.zh.md              # 本文件（中文使用说明）
├── evals/
│   └── evals.json            # 测试用例集（4 语言 × 场景）
└── references/
    ├── go.md                 # Go 测试规范与示例
    ├── python.md             # Python / pytest 规范与示例
    ├── java.md               # Java / JUnit 5 规范与示例
    ├── typescript.md         # TypeScript / Vitest 规范与示例
    ├── techniques.md         # 方法论详细说明
    └── patterns.md           # 通用测试模式
```

---

## 安装

将本目录放入 Claude Code 的 Skills 路径即可：

```bash
# 克隆到 skills 目录
git clone <repo> ~/.claude/skills/unit-test-methodology

# 或软链接
ln -s /path/to/unit-test-methodology ~/.claude/skills/unit-test-methodology
```

---

## 可选工具

以下工具非必须，但在 Skill 中有提及：

- **[caseforge](https://github.com/yuchou87/caseforge)**：命令行工具，自动计算 Pairwise 最小组合集，生成真实感 Fake 数据

```bash
# Pairwise 组合计算
caseforge pairwise --var "role:admin,user,guest" --var "status:active,inactive"

# 生成测试数据
caseforge fake --field "name:person_name" --field "email:email" --count 5
```
