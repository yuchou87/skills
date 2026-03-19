# Rust Unit Testing Conventions

## Frameworks

- Built-in: `#[test]` + `#[cfg(test)]` module (standard library)
- Parameterized tests: [`rstest`](https://github.com/la10736/rstest) (`#[rstest]` + `#[case]`)
- Mocking: [`mockall`](https://github.com/asomers/mockall) (`#[automock]` + `MockXxx`)
- Assertions: standard macros (`assert_eq!`, `assert!`, `assert_matches!`) + [`pretty_assertions`](https://github.com/rust-pretty-assertions/rust-pretty-assertions) for readable diffs

---

## Table-Driven Test Standard Structure (rstest)

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use rstest::rstest;

    // ─── Happy Path ───────────────────────────────────────────
    #[test]
    fn create_user_valid_input_returns_user() {
        // [EP·valid]
        let mut repo = MockUserRepository::new();
        repo.expect_save()
            .once()
            .returning(|_| Ok(()));

        let result = create_user("Markus Moen", "markus.moen@kozey.biz", 34, &repo);

        assert!(result.is_ok());
        let user = result.unwrap();
        assert_eq!(user.name, "Markus Moen");
        assert_eq!(user.email, "markus.moen@kozey.biz");
    }

    // ─── Invalid Equivalence Classes ──────────────────────────
    // each invalid class is its own test — never merge
    #[rstest]
    #[case("",        "m@kozey.biz",  34, UserError::NameRequired,  "EP·invalid·1: name empty")]
    #[case("   ",     "m@kozey.biz",  34, UserError::NameRequired,  "EP·invalid·2: name whitespace")]
    #[case("Markus",  "not-email",    34, UserError::EmailInvalid,  "EP·invalid·3: email format")]
    #[case("Markus",  "",             34, UserError::EmailInvalid,  "EP·invalid·4: email empty")]
    fn create_user_invalid_input_returns_error(
        #[case] name: &str,
        #[case] email: &str,
        #[case] age: u32,
        #[case] expected_err: UserError,
        #[case] _technique: &str,
    ) {
        let repo = MockUserRepository::new(); // no calls expected
        let result = create_user(name, email, age, &repo);

        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), expected_err);
    }

    // ─── Boundary Values ──────────────────────────────────────
    #[rstest]
    #[case(0,   false, "BV·min-1: below minimum")]
    #[case(1,   true,  "BV·min: at minimum")]
    #[case(2,   true,  "BV·min+1")]
    #[case(149, true,  "BV·max-1")]
    #[case(150, true,  "BV·max: at maximum")]
    #[case(151, false, "BV·max+1: above maximum")]
    fn create_user_age_boundary(
        #[case] age: u32,
        #[case] should_succeed: bool,
        #[case] _technique: &str,
    ) {
        let mut repo = MockUserRepository::new();
        if should_succeed {
            repo.expect_save().once().returning(|_| Ok(()));
        }

        let result = create_user("Test User", "test@example.com", age, &repo);
        assert_eq!(result.is_ok(), should_succeed);
        if !should_succeed {
            assert_eq!(result.unwrap_err(), UserError::AgeInvalid);
        }
    }

    // ─── Dependency Failures ──────────────────────────────────
    #[test]
    fn create_user_repo_save_fails_returns_save_error() {
        // [EP·invalid: dependency]
        let mut repo = MockUserRepository::new();
        repo.expect_save()
            .once()
            .returning(|_| Err(RepoError::ConnectionRefused));

        let result = create_user("Test User", "test@example.com", 25, &repo);

        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), UserError::SaveFailed);
    }
}
```

---

## mockall Setup

```rust
use mockall::automock;

// annotate the trait — mockall generates MockUserRepository
#[automock]
pub trait UserRepository {
    fn save(&self, user: &User) -> Result<(), RepoError>;
    fn find_by_email(&self, email: &str) -> Option<User>;
}
```

```rust
// in tests: configure expectations
let mut repo = MockUserRepository::new();

// called exactly once with any argument
repo.expect_save()
    .once()
    .returning(|_| Ok(()));

// called with a specific argument
repo.expect_find_by_email()
    .with(mockall::predicate::eq("markus@kozey.biz"))
    .once()
    .returning(|_| None);

// simulate failure
repo.expect_save()
    .once()
    .returning(|_| Err(RepoError::ConnectionRefused));

// never called (no expect_ call needed; drop verify on mock)
// or explicitly:
repo.expect_save().never();
```

---

## State Transition Test Example

```rust
#[cfg(test)]
mod state_tests {
    use super::*;
    use rstest::rstest;

    // valid transitions
    #[rstest]
    #[case(OrderStatus::Pending,   "pay",    OrderStatus::Paid,      "ST·valid: pending→paid")]
    #[case(OrderStatus::Paid,      "ship",   OrderStatus::Shipped,   "ST·valid: paid→shipped")]
    #[case(OrderStatus::Shipped,   "deliver",OrderStatus::Delivered, "ST·valid: shipped→delivered")]
    fn order_valid_transition_changes_status(
        #[case] initial: OrderStatus,
        #[case] action: &str,
        #[case] expected: OrderStatus,
        #[case] _technique: &str,
    ) {
        let mut order = Order::new(initial);
        let result = order.apply(action);
        assert!(result.is_ok());
        assert_eq!(order.status, expected);
    }

    // invalid transitions
    #[rstest]
    #[case(OrderStatus::Delivered, "reset",   "ST·invalid: cannot rollback delivered")]
    #[case(OrderStatus::Cancelled, "pay",     "ST·invalid: cannot pay cancelled")]
    #[case(OrderStatus::Pending,   "deliver", "ST·invalid: cannot skip shipped")]
    fn order_invalid_transition_returns_error_and_keeps_status(
        #[case] initial: OrderStatus,
        #[case] action: &str,
        #[case] _technique: &str,
    ) {
        let mut order = Order::new(initial.clone());
        let result = order.apply(action);
        assert!(result.is_err());
        assert_eq!(order.status, initial); // status unchanged
    }
}
```

---

## Decision Table Test Example

```rust
#[cfg(test)]
mod permission_tests {
    use super::*;
    use rstest::rstest;

    #[rstest]
    // is_admin  is_owner  is_public  expected  technique
    #[case(true,  false, false, true,  "DT·admin always allowed")]
    #[case(false, true,  false, true,  "DT·owner allowed")]
    #[case(false, false, true,  true,  "DT·public readable")]
    #[case(false, false, false, false, "DT·no permission")]
    fn check_permission_decision_table(
        #[case] is_admin: bool,
        #[case] is_owner: bool,
        #[case] is_public: bool,
        #[case] expected: bool,
        #[case] _technique: &str,
    ) {
        let result = check_permission(is_admin, is_owner, is_public);
        assert_eq!(result, expected);
    }
}
```

---

## Error Type Conventions

```rust
// define error types with PartialEq for assertion comparison
#[derive(Debug, PartialEq)]
pub enum UserError {
    NameRequired,
    EmailInvalid,
    AgeInvalid,
    SaveFailed,
}

// assert on error variants
assert_eq!(result.unwrap_err(), UserError::NameRequired);

// assert on error with data payload
assert!(matches!(result.unwrap_err(), UserError::InvalidAge { age } if age == 0));

// assert on wrapped errors
assert!(matches!(result, Err(UserError::SaveFailed)));
```

---

## Async Test Example

```rust
// add tokio as dev-dependency for async tests
// [dev-dependencies]
// tokio = { version = "1", features = ["full"] }

#[cfg(test)]
mod async_tests {
    use super::*;

    #[tokio::test]
    async fn transfer_money_valid_returns_transaction() {
        // [EP·valid]
        let mut repo = MockAccountRepository::new();
        repo.expect_find_by_id()
            .returning(|id| {
                Ok(Some(Account { id: id.to_string(), balance: 1000 }))
            });
        repo.expect_save()
            .times(2)  // both from and to accounts saved
            .returning(|_| Ok(()));

        let result = transfer_money("acc-1", "acc-2", 100, &repo).await;

        assert!(result.is_ok());
        let tx = result.unwrap();
        assert_eq!(tx.amount, 100);
    }

    #[tokio::test]
    async fn transfer_money_insufficient_balance_returns_error() {
        // [EP·invalid: insufficient balance]
        let mut repo = MockAccountRepository::new();
        repo.expect_find_by_id()
            .returning(|id| {
                Ok(Some(Account { id: id.to_string(), balance: 50 }))
            });

        let result = transfer_money("acc-1", "acc-2", 100, &repo).await;

        assert_eq!(result.unwrap_err(), TransferError::InsufficientBalance);
    }
}
```

---

## Cargo.toml Dependencies

```toml
[dev-dependencies]
rstest = "0.23"
mockall = "0.13"
pretty_assertions = "1"
tokio = { version = "1", features = ["full"] }  # async tests only
```

---

## Common Assertion Reference

```rust
// equality
assert_eq!(actual, expected);
assert_ne!(actual, unexpected);

// boolean
assert!(condition);
assert!(!condition);

// Result / Option
assert!(result.is_ok());
assert!(result.is_err());
assert_eq!(result.unwrap(), expected_value);
assert_eq!(result.unwrap_err(), expected_error);
assert!(option.is_some());
assert!(option.is_none());
assert_eq!(option.unwrap(), expected_value);

// pattern matching (error with payload)
assert!(matches!(result, Err(MyError::Variant { field } if field == expected)));

// collections
assert_eq!(vec.len(), 3);
assert!(vec.contains(&item));
assert!(vec.is_empty());

// floats
assert!((actual - expected).abs() < 0.001);

// should_panic (use sparingly — prefer Result-based errors)
#[test]
#[should_panic(expected = "index out of bounds")]
fn panics_on_invalid_index() {
    let v: Vec<i32> = vec![];
    let _ = v[0];
}
```

---

## Test Naming Convention

```
<function>_<scenario>_<expected_outcome>

Examples:
  create_user_valid_input_returns_user
  create_user_name_empty_returns_name_required_error
  create_user_age_below_minimum_returns_age_invalid_error
  create_user_repo_save_fails_returns_save_error
  transfer_money_insufficient_balance_returns_error
```

Use descriptive snake_case. Rust test output shows full path (`tests::create_user_name_empty_returns_name_required_error`), so names must be self-explanatory.

---

## Test Module Organization

```rust
// inline test module (standard for unit tests)
#[cfg(test)]
mod tests {
    use super::*;

    mod create_user {
        use super::*;
        #[test] fn valid_input_returns_user() { ... }
        #[test] fn name_empty_returns_error() { ... }
    }

    mod transfer_money {
        use super::*;
        #[test] fn valid_transfer_returns_transaction() { ... }
        #[test] fn insufficient_balance_returns_error() { ... }
    }
}
```
