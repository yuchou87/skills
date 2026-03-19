# Common Testing Patterns

## Mock Design Principles

**Only mock direct dependencies — never mock methods on the class under test.**

```
✓ correct: mock external dependencies (DB / external API / message queue)
✗ wrong:   mock internal private methods of the class under test
           (signals a design problem — refactor instead)
```

**Mock granularity**:
- Unit tests: mock all I/O and external dependencies
- Integration tests: use real dependencies (in-memory DB / local message queue)

---

## Fixture Design

```go
// Go: helper functions to create valid test data
func validCreateUserInput() CreateUserInput {
    return CreateUserInput{
        Name:  "Markus Moen",      // use realistic fake data
        Email: "markus.moen@kozey.biz",
        Age:   34,
    }
}

// variant: partially modify valid data
func TestNameEmpty(t *testing.T) {
    input := validCreateUserInput()
    input.Name = ""               // only change the field under test
    // ...
}
```

```python
# Python: pytest fixture
@pytest.fixture
def valid_input():
    return CreateUserInput(
        name="Markus Moen",
        email="markus.moen@kozey.biz",
        age=34,
    )

def test_name_empty(valid_input):
    valid_input.name = ""
    with pytest.raises(NameRequiredError):
        svc.create_user(valid_input)
```

---

## Test Isolation

Every test must be independent — no reliance on execution order or shared state:

```
✓ reset all mocks and state in beforeEach
✓ test data created inside the test, not from global variables
✗ data created by test A used by test B
✗ test results depend on execution order
```

```go
// Go: t.Cleanup registers cleanup functions
func TestXxx(t *testing.T) {
    db := setupTestDB(t)
    t.Cleanup(func() { db.Rollback() })
    // ...
}
```

```typescript
// TypeScript: reset in beforeEach
beforeEach(() => {
    vi.clearAllMocks()
    // reset any global state
})
```

---

## Dependency-Injection-Friendly Design

Hard-to-test code is often a signal of design problems. Good design:

```go
// ✓ inject dependencies via interface — easy to mock
type UserService struct {
    repo   UserRepository  // interface, not concrete implementation
    mailer Mailer
}

func NewUserService(repo UserRepository, mailer Mailer) *UserService {
    return &UserService{repo: repo, mailer: mailer}
}

// ✗ global dependency — cannot be mocked
func CreateUser(name string) {
    db.Save(...)  // global db
}
```

---

## Side-Effect Verification Priority

For functions with side effects, verify in this order:

```
1. Core side effects (write DB / send message)  — must verify
2. Call count (prevent duplicate writes)
3. Call arguments (verify correct data was written)
4. Call order (if there is a dependency relationship)
```

```go
// Go: verify side effects
verify(repo).Save(captor.capture())
actualUser := captor.getValue()
assert.Equal(t, "markus@kozey.biz", actualUser.Email)
assert.NotEmpty(t, actualUser.ID)               // verify ID was generated
assert.False(t, actualUser.CreatedAt.IsZero())  // verify timestamp was set
```

---

## Test Naming Convention

| Language | Recommended format | Example |
|----------|--------------------|---------|
| Go | `Test<Method>_<scenario>_<outcome>` | `TestCreateUser_nameEmpty_returnsError` |
| Python | `test_<action>_when_<condition>_<outcome>` | `test_create_user_when_name_empty_raises_error` |
| Java | `@DisplayName` descriptive string | `"[EP·invalid] name is empty - should throw exception"` |
| TypeScript | descriptive string | `'[EP·invalid·1] name is empty → throws NameRequiredError'` |

---

## Patterns to Avoid

### Snapshot Testing
```
use for:  UI component render output, serialization format
avoid for: business logic — snapshots are often updated blindly
           without understanding what actually changed
```

### Testing Private Methods
```
✗ test private methods directly (crosses encapsulation boundary)
✓ trigger private logic indirectly through public methods
✓ if private method logic is complex, extract into a separate component
```

### Over-Mocking
```
✗ mock everything the function under test depends on
  (including simple utility functions)
✓ only mock dependencies with I/O
✓ pure functions don't need mocking — call them directly
```

### Testing Implementation Details
```
✗ assert on internal variable values
✗ assert that private methods were called
✓ assert on public outputs and observable side effects
```
