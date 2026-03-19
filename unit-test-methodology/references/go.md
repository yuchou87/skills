# Go Unit Testing Conventions

## Frameworks

- Standard library: `testing`
- Assertions: `github.com/stretchr/testify/assert` + `require`
- Mocking: `github.com/stretchr/testify/mock` or hand-written mock structs

---

## Table-Driven Test Standard Structure

```go
package xxx_test  // external test package, avoids accessing private implementation

import (
    "testing"
    "errors"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestFunctionName(t *testing.T) {
    t.Parallel()

    tests := []struct {
        name      string                  // scenario description (must be meaningful)
        input     InputType               // corresponds to function parameters
        setupMock func() *MockDep         // when dependency exists (optional)
        want      *ResultType             // expected return value (nil means skip check)
        wantErr   error                   // expected error (nil means expect success)
        // side-effect verification (when there are side effects)
        assertMock func(t *testing.T, m *MockDep)
        // technique traceability (comment only, not used at runtime)
        technique string
    }{
        // ─── Happy Path ───────────────────────────────────────
        {
            name:      "valid input - creates user successfully",
            technique: "EP·valid",
            input: InputType{
                Name:  "Markus Moen",
                Email: "markus.moen@kozey.biz",
                Age:   34,
            },
            setupMock: func() *MockDep {
                m := &MockDep{}
                m.On("Save", mock.Anything).Return(nil)
                return m
            },
            want: &ResultType{ID: "generated-uuid", Name: "Markus Moen"},
            assertMock: func(t *testing.T, m *MockDep) {
                m.AssertCalled(t, "Save", mock.Anything)
                m.AssertNumberOfCalls(t, "Save", 1)
            },
        },

        // ─── Invalid Equivalence Classes ──────────────────────
        {
            name:      "empty name - invalid EP 1",
            technique: "EP·invalid·1: name empty",
            input:     InputType{Name: "", Email: "markus@kozey.biz", Age: 34},
            wantErr:   ErrNameRequired,
        },
        {
            name:      "invalid email format - invalid EP 2",
            technique: "EP·invalid·2: email format",
            input:     InputType{Name: "Markus", Email: "not-an-email", Age: 34},
            wantErr:   ErrEmailInvalid,
        },

        // ─── Boundary Values ──────────────────────────────────
        {
            name:      "age=0 - below min boundary",
            technique: "BV·min-1",
            input:     InputType{Name: "Test", Email: "t@t.com", Age: 0},
            wantErr:   ErrAgeInvalid,
        },
        {
            name:      "age=1 - at min boundary (valid)",
            technique: "BV·min",
            input:     InputType{Name: "Test", Email: "t@t.com", Age: 1},
            want:      &ResultType{Name: "Test"},
        },
        {
            name:      "age=150 - at max boundary (valid)",
            technique: "BV·max",
            input:     InputType{Name: "Test", Email: "t@t.com", Age: 150},
            want:      &ResultType{Name: "Test"},
        },
        {
            name:      "age=151 - above max boundary",
            technique: "BV·max+1",
            input:     InputType{Name: "Test", Email: "t@t.com", Age: 151},
            wantErr:   ErrAgeInvalid,
        },

        // ─── Dependency Failures ──────────────────────────────
        {
            name:      "database save fails",
            technique: "EP·invalid: dependency error",
            input:     InputType{Name: "Test", Email: "t@t.com", Age: 25},
            setupMock: func() *MockDep {
                m := &MockDep{}
                m.On("Save", mock.Anything).Return(errors.New("db connection refused"))
                return m
            },
            wantErr: ErrSaveFailed,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()

            // initialize mock
            var dep *MockDep
            if tt.setupMock != nil {
                dep = tt.setupMock()
            } else {
                dep = &MockDep{}
            }

            // call the function under test
            got, err := FunctionName(tt.input, dep)

            // assert error
            if tt.wantErr != nil {
                require.Error(t, err)
                assert.ErrorIs(t, err, tt.wantErr)
                return
            }
            require.NoError(t, err)

            // assert return value
            if tt.want != nil {
                assert.Equal(t, tt.want.Name, got.Name)
                // assert specific fields as needed
            }

            // assert mock calls (side-effect verification)
            if tt.assertMock != nil {
                tt.assertMock(t, dep)
            }
        })
    }
}
```

---

## Hand-Written Mock Structure (no mockery needed)

```go
// mock interface implementation, tracks calls precisely
type MockUserRepo struct {
    // function fields, behavior customizable per test
    FindByIDFunc func(id string) (*User, error)
    SaveFunc     func(u *User) error

    // call records (for side-effect assertions)
    calls struct {
        FindByID []string
        Save     []*User
    }
}

func (m *MockUserRepo) FindByID(id string) (*User, error) {
    m.calls.FindByID = append(m.calls.FindByID, id)
    if m.FindByIDFunc != nil {
        return m.FindByIDFunc(id)
    }
    return nil, nil
}

func (m *MockUserRepo) Save(u *User) error {
    m.calls.Save = append(m.calls.Save, u)
    if m.SaveFunc != nil {
        return m.SaveFunc(u)
    }
    return nil
}

// assertion usage
assert.Len(t, mock.calls.Save, 1)
assert.Equal(t, "markus.moen@kozey.biz", mock.calls.Save[0].Email)
```

---

## State Transition Test Example

```go
func TestOrderStateTransition(t *testing.T) {
    t.Parallel()

    tests := []struct {
        name      string
        initial   OrderStatus
        action    func(o *Order) error
        wantState OrderStatus
        wantErr   error
        technique string
    }{
        {
            name:      "pending to paid - valid transition",
            technique: "ST·valid: pending to paid",
            initial:   StatusPending,
            action:    func(o *Order) error { return o.Pay() },
            wantState: StatusPaid,
        },
        {
            name:      "delivered to pending - invalid rollback",
            technique: "ST·invalid: cannot rollback delivered",
            initial:   StatusDelivered,
            action:    func(o *Order) error { return o.Reset() },
            wantErr:   ErrInvalidTransition,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()
            order := &Order{Status: tt.initial}
            err := tt.action(order)
            if tt.wantErr != nil {
                assert.ErrorIs(t, err, tt.wantErr)
                assert.Equal(t, tt.initial, order.Status) // state unchanged
                return
            }
            require.NoError(t, err)
            assert.Equal(t, tt.wantState, order.Status)
        })
    }
}
```

---

## Idempotency Test Example

```go
func TestCreateUserIdempotent(t *testing.T) {
    t.Parallel()

    repo := NewInMemoryRepo()
    svc := NewUserService(repo)
    input := CreateUserInput{Name: "Markus", Email: "markus@kozey.biz"}

    // first call
    user1, err := svc.CreateUser(input)
    require.NoError(t, err)
    require.NotNil(t, user1)

    // second identical call
    user2, err := svc.CreateUser(input)

    // assert based on business semantics:
    // Scenario A: should return error (unique email constraint)
    assert.ErrorIs(t, err, ErrEmailAlreadyExists)

    // Scenario B: should return existing user (idempotent creation)
    // assert.NoError(t, err)
    // assert.Equal(t, user1.ID, user2.ID)

    // verify database was written only once
    count, _ := repo.CountByEmail("markus@kozey.biz")
    assert.Equal(t, 1, count)
}
```

---

## Common Assertion Reference

```go
assert.Equal(t, expected, actual)           // deep equality
assert.NotEqual(t, unexpected, actual)
assert.Nil(t, value)
assert.NotNil(t, value)
assert.NoError(t, err)
assert.Error(t, err)
assert.ErrorIs(t, err, targetErr)           // error chain match
assert.ErrorAs(t, err, &target)            // error type assertion
assert.Contains(t, slice, element)
assert.ElementsMatch(t, expected, actual)   // unordered slice equality
assert.Len(t, collection, n)
assert.Empty(t, value)
assert.True(t, condition, "msg: %v", val)
assert.InDelta(t, expected, actual, delta)  // float approximation

// require: stops immediately on failure (use for preconditions)
require.NoError(t, err)
require.NotNil(t, result)
```

---

## Test Helper Function Conventions

```go
// helper naming: must* means fatal on failure
func mustCreateUser(t *testing.T, svc *UserService, input CreateUserInput) *User {
    t.Helper()  // error points to caller, not inside the helper
    user, err := svc.CreateUser(input)
    require.NoError(t, err)
    return user
}

// fixture data: use realistic data
func validUserInput() CreateUserInput {
    return CreateUserInput{
        Name:  "Markus Moen",
        Email: "markus.moen@kozey.biz",
        Age:   34,
    }
}
```
