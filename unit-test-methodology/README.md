# unit-test-methodology

> A methodology-driven unit test generation Skill for [Claude Code](https://claude.ai/code).

**[中文](README.zh.md)**

---

## Overview

Unlike ad-hoc test generation, this Skill enforces a structured testing methodology: analyze the function first, systematically derive test cases, then generate code. It applies classical techniques including Equivalence Partitioning, Boundary Value Analysis, Decision Tables, and Pairwise combinatorial testing.

**Supported languages**: Go / Python / Java / TypeScript / Rust

---

## Trigger phrases

Any of the following will activate this Skill in Claude Code:

```
write unit tests       add tests for this     test coverage
unit test              write tests for        how do I test this
帮我写单元测试          单测                   补充测试
```

---

## Workflow

```
User provides function code
      ↓
Step 1  Detect language, load language-specific conventions (Go / Python / Java / TypeScript)
      ↓
Step 2  Analyze function: parameters · behavior · dependencies
      ↓
Step 3  Select techniques: EP / BVA / Decision Table / Pairwise / State Transition / Idempotency
      ↓
Step 4  Derive test cases systematically, annotating each with its source technique
      ↓
Step 5  Generate realistic, business-meaningful test data
      ↓
Step 6  Output complete, runnable test code
```

---

## Example

**Input (Go)**:

```go
func CreateUser(name, email string, age int, repo UserRepository) (*User, error)
```

**Output (excerpt)**:

```go
func TestCreateUser(t *testing.T) {
    t.Parallel()
    tests := []struct { ... }{
        {name: "valid input - creates user",       technique: "EP·valid",              ...},
        {name: "empty name - invalid EP",          technique: "EP·invalid·1",          wantErr: ErrNameRequired},
        {name: "age=0 - below min boundary",       technique: "BV·min-1",              wantErr: ErrAgeInvalid},
        {name: "age=1 - at min boundary (valid)",  technique: "BV·min",                ...},
        {name: "age=151 - above max boundary",     technique: "BV·max+1",              wantErr: ErrAgeInvalid},
        {name: "repo save fails",                  technique: "EP·invalid: dependency",...},
    }
    // ...
}
```

---

## Technique reference

| Technique | When to use | Annotation prefix |
|-----------|-------------|-------------------|
| Equivalence Partitioning | Any parameter | `EP·valid` / `EP·invalid·N` |
| Boundary Value Analysis | Numeric / string with range constraints | `BV·min` / `BV·max+1` |
| Decision Table | Multiple conditions affecting output | `DT·...` |
| Pairwise Combinatorial | 4+ independent parameters | `PW·...` |
| State Transition | Object with a state field | `ST·valid` / `ST·invalid` |
| Idempotency | Write operations called multiple times | `IDEM·...` |

---

## File structure

```
unit-test-methodology/
├── SKILL.md                  # Skill definition (read by Claude)
├── README.md                 # This file (English documentation)
├── README.zh.md              # 中文文档
├── evals/
│   └── evals.json            # Test cases (4 languages × scenarios)
└── references/
    ├── go.md                 # Go testing conventions and examples
    ├── python.md             # Python / pytest conventions and examples
    ├── java.md               # Java / JUnit 5 conventions and examples
    ├── typescript.md         # TypeScript / Vitest conventions and examples
    ├── rust.md               # Rust / rstest / mockall conventions and examples
    ├── techniques.md         # Detailed methodology explanations
    └── patterns.md           # General testing patterns
```

---

## Installation

Place this directory in Claude Code's Skills path:

```bash
# Clone into skills directory
git clone <repo> ~/.claude/skills/unit-test-methodology

# Or symlink
ln -s /path/to/unit-test-methodology ~/.claude/skills/unit-test-methodology
```

---

## Optional tooling

The following tools are optional but referenced in the Skill:

- **[caseforge](https://github.com/yuchou87/caseforge)**: CLI tool for computing minimum Pairwise test sets and generating realistic fake data.

```bash
# Compute Pairwise combinations
caseforge pairwise --var "role:admin,user,guest" --var "status:active,inactive"

# Generate test data
caseforge fake --field "name:person_name" --field "email:email" --count 5
```
