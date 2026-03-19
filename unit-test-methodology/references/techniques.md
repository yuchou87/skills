# Testing Techniques Reference

## Equivalence Partitioning (EP)

Divide the input domain of each parameter into valid and invalid equivalence classes, then select one representative value per class.

**Typical partitions by type**:

```
string:
  valid class:    normal string (non-empty, format valid)
  invalid class 1: empty string ""
  invalid class 2: whitespace only "   "
  invalid class 3: exceeds maxLength
  invalid class 4: invalid format (email → "not-email", URL → "not-url")
  invalid class 5: contains illegal characters (e.g. path traversal "../")

int / number:
  valid class:    normal value within business range
  invalid class 1: negative (if business requires > 0)
  invalid class 2: zero (if business requires ≥ 1)
  invalid class 3: exceeds upper limit
  invalid class 4: non-integer (if business requires integer)

pointer / reference / nullable:
  valid class:    non-null/nil and valid value
  invalid class 1: null / nil

enum / constant:
  valid class:    one class per legal enum value
  invalid class 1: value outside the enum

slice / array / list:
  valid class 1:  contains 1 element
  valid class 2:  contains multiple elements
  invalid class 1: empty list/array
  invalid class 2: exceeds maxItems
```

> **Key rule**: Invalid classes must each be their own independent test case — never merge them. Merging masks the real cause of failure.

---

## Boundary Value Analysis (BVA)

For parameters with range constraints, take boundary points and their neighbors — 6 test points total:

```
range [min, max]:

  min-1  ← outer (expect error/exception)
  min    ← inner minimum (expect success)
  min+1  ← inner (expect success)
  ...
  max-1  ← inner (expect success)
  max    ← inner maximum (expect success)
  max+1  ← outer (expect error/exception)
```

**Applies to**:
- Numeric `minimum` / `maximum`
- String `minLength` / `maxLength`
- Array `minItems` / `maxItems`
- Date ranges

**Relationship with EP**: Partition equivalence classes first, then add boundary values on top of ranged classes.

---

## Decision Table

Use when multiple conditions jointly determine the output — enumerate meaningful condition combinations.

**Example: permission check function**

```
Conditions: is_admin / is_owner / is_public

is_admin  is_owner  is_public  → result      annotation
T         any       any        → allow       DT·admin
F         T         any        → allow       DT·owner
F         F         T          → read-only   DT·public
F         F         F          → deny        DT·no-permission
```

**Generation rules**:
- List all conditions that affect the result
- Enumerate meaningful combinations (no need to exhaust all 2^n — focus on mutually exclusive and dependent boundary cases)
- Generate one test case per combination

---

## Pairwise Combinatorial Testing

Use when there are 4+ independent parameters to compress full combinations.

**Core principle**: Research shows the vast majority of bugs are caused by interactions between 1-2 parameters. Pairwise guarantees every combination of any two parameters' values appears at least once.

**Compression effect**:

```
4 parameters × 3 values each = 81 full combinations
Pairwise → ~12 test cases (85% reduction)
Coverage: 100% of pairwise interactions
```

**Using caseforge pairwise**:

```bash
caseforge pairwise \
  --var "role:admin,user,guest" \
  --var "plan:free,pro,enterprise" \
  --var "is_active:true,false" \
  --var "region:cn,us,eu"
```

**Manual derivation (for ≤ 4 parameters)**:

```
Parameters: role(3 values) × plan(2 values) × active(2 values)
Full combinations = 3×2×2 = 12

Pairwise (ensure every pair of parameters' values appears once):
  [admin, free, true]
  [admin, pro, false]
  [user, free, false]
  [user, pro, true]
  [guest, free, true]
  [guest, pro, false]
→ 6 cases cover all pairwise combinations
```

---

## State Transition Testing

For objects with state fields, cover both valid and invalid state transition paths.

**State machine diagram example (Order)**:

```
pending ──pay()──→ paid ──ship()──→ shipped ──deliver()──→ delivered
                                                              ↓
                                                          cancelled (cancellable from any state)
```

**Generation rules**:
- Each **valid transition**: 1 success case, verify state changes
- Each **invalid transition**: 1 failure case, verify state unchanged + exception thrown
- Key path: full pending→paid→shipped→delivered chain

**Example cases**:

```
valid:   pending.pay()     → paid          ✓
valid:   paid.ship()       → shipped       ✓
invalid: pending.deliver() → InvalidTransition, status still pending   ✗
invalid: delivered.reset() → InvalidTransition, status still delivered ✗
```

---

## Idempotency Testing

Verify that "the same operation executed multiple times produces the same result as executing it once."

**Applicable scenarios**:
- PUT/PATCH endpoints (update operations)
- POST endpoints with idempotency keys (prevent duplicate submissions)
- Functions called multiple times with the same parameters

**Test pattern**:

```
// call twice, results are consistent
result1 = fn(input)
result2 = fn(input)
assert result1 == result2

// side effects happen only once (e.g. DB write)
assert repo.save.call_count == 1  // even though called twice
```

---

## Test Case Count Reference

| Function complexity | Param count | Expected cases | Notes |
|--------------------|-------------|----------------|-------|
| Simple | 1-2 | 5-10 | EP + BVA |
| Moderate | 2-3 | 12-25 | EP + BVA + dependency failures |
| Complex | 4+ | 15-35 | Pairwise + Decision Table |
| Stateful | any | +N | 2 per state transition (valid + invalid) |

**Fewer than 5 cases usually means insufficient analysis.** Revisit whether you missed:
- An invalid equivalence class for some parameter
- nil/null/empty scenarios
- Dependency service failure scenarios
- Boundary values (if range constraints exist)
