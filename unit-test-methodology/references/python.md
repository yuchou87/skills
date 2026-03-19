# Python Unit Testing Conventions

## Frameworks

- Primary: `pytest`
- Mocking: `unittest.mock` (standard library) / `pytest-mock` (recommended)
- Assertions: pytest native assertions (auto-expands diffs)

---

## Parametrize Standard Structure

```python
import pytest
from unittest.mock import MagicMock, patch, call
from myapp.services import UserService
from myapp.errors import (
    NameRequiredError, EmailInvalidError, AgeInvalidError, SaveFailedError
)


class TestCreateUser:
    """
    Function under test: UserService.create_user(name, email, age)
    Techniques: Equivalence Partitioning + Boundary Value Analysis + Dependency Failures
    """

    # ─── Happy Path ───────────────────────────────────────────
    def test_valid_input_creates_user(self, mock_repo):
        """[EP·valid] valid input - creates user successfully"""
        svc = UserService(repo=mock_repo)
        mock_repo.save.return_value = None

        result = svc.create_user(
            name="Markus Moen",
            email="markus.moen@kozey.biz",
            age=34,
        )

        assert result.name == "Markus Moen"
        assert result.email == "markus.moen@kozey.biz"
        mock_repo.save.assert_called_once()  # side-effect verification

    # ─── Invalid Equivalence Classes ──────────────────────────
    @pytest.mark.parametrize("name, email, age, expected_error, technique", [
        # each invalid class is its own case, never merge
        ("",        "m@kozey.biz", 34, NameRequiredError, "EP·invalid·1: name empty"),
        ("   ",     "m@kozey.biz", 34, NameRequiredError, "EP·invalid·2: name whitespace"),
        ("Markus",  "not-email",   34, EmailInvalidError, "EP·invalid·3: email format"),
        ("Markus",  "",            34, EmailInvalidError, "EP·invalid·4: email empty"),
    ])
    def test_invalid_input_raises_error(
        self, name, email, age, expected_error, technique, mock_repo
    ):
        svc = UserService(repo=mock_repo)
        with pytest.raises(expected_error):
            svc.create_user(name=name, email=email, age=age)
        mock_repo.save.assert_not_called()  # verify no side effects

    # ─── Boundary Values ──────────────────────────────────────
    @pytest.mark.parametrize("age, should_succeed, technique", [
        (0,   False, "BV·min-1: age below minimum"),
        (1,   True,  "BV·min: age at minimum"),
        (2,   True,  "BV·min+1"),
        (149, True,  "BV·max-1"),
        (150, True,  "BV·max: age at maximum"),
        (151, False, "BV·max+1: age above maximum"),
    ])
    def test_age_boundary(self, age, should_succeed, technique, mock_repo):
        svc = UserService(repo=mock_repo)
        if should_succeed:
            result = svc.create_user(name="Test", email="t@t.com", age=age)
            assert result is not None
        else:
            with pytest.raises(AgeInvalidError):
                svc.create_user(name="Test", email="t@t.com", age=age)

    # ─── Dependency Failures ──────────────────────────────────
    def test_repo_failure_raises_save_error(self, mock_repo):
        """[EP·invalid: dependency] database exception propagates up"""
        mock_repo.save.side_effect = Exception("db connection refused")
        svc = UserService(repo=mock_repo)

        with pytest.raises(SaveFailedError):
            svc.create_user(name="Test", email="t@t.com", age=25)


# ─── Fixtures ─────────────────────────────────────────────────
@pytest.fixture
def mock_repo():
    """shared mock repo fixture, isolated between tests"""
    repo = MagicMock()
    repo.save.return_value = None
    repo.find_by_email.return_value = None
    return repo


@pytest.fixture
def valid_user_data():
    """realistic valid user data"""
    return {
        "name": "Markus Moen",
        "email": "markus.moen@kozey.biz",
        "age": 34,
    }
```

---

## State Transition Test Example

```python
class TestOrderStateTransition:
    """[ST] Order state machine tests"""

    @pytest.mark.parametrize("initial, action, expected_state, technique", [
        ("pending",   "pay",    "paid",      "ST·valid: pending→paid"),
        ("paid",      "ship",   "shipped",   "ST·valid: paid→shipped"),
        ("shipped",   "deliver","delivered", "ST·valid: shipped→delivered"),
    ])
    def test_valid_transitions(self, initial, action, expected_state, technique):
        order = Order(status=initial)
        getattr(order, action)()
        assert order.status == expected_state

    @pytest.mark.parametrize("initial, action, technique", [
        ("delivered", "reset",  "ST·invalid: cannot rollback delivered"),
        ("pending",   "deliver","ST·invalid: cannot skip shipped"),
        ("cancelled", "pay",    "ST·invalid: cannot pay cancelled order"),
    ])
    def test_invalid_transitions_raise_error(self, initial, action, technique):
        order = Order(status=initial)
        with pytest.raises(InvalidTransitionError):
            getattr(order, action)()
        assert order.status == initial  # state unchanged
```

---

## Decision Table Test Example

```python
class TestCheckPermission:
    """[DT] Permission check decision table"""

    @pytest.mark.parametrize(
        "is_admin, is_owner, is_public, expected, technique",
        [
            # is_admin  is_owner  is_public  → result
            (True,  False, False, True,  "DT·admin always allowed"),
            (False, True,  False, True,  "DT·owner allowed"),
            (False, False, True,  True,  "DT·public readable"),
            (False, False, False, False, "DT·no permission"),
        ],
    )
    def test_permission_matrix(
        self, is_admin, is_owner, is_public, expected, technique
    ):
        result = check_permission(
            is_admin=is_admin,
            is_owner=is_owner,
            is_public=is_public,
        )
        assert result == expected
```

---

## Mock Usage Conventions

```python
from unittest.mock import MagicMock, patch, call, ANY

# basic mock
repo = MagicMock()
repo.find_by_id.return_value = User(id="123", name="Markus")
repo.save.side_effect = Exception("db error")  # simulate exception

# call verification
repo.save.assert_called_once()
repo.save.assert_called_once_with(ANY)         # don't care about specific args
repo.save.assert_called_with(expected_user)    # precise argument verification
repo.find_by_id.assert_not_called()
assert repo.save.call_count == 1

# extract call arguments for assertion
actual_user = repo.save.call_args[0][0]
assert actual_user.email == "markus@kozey.biz"

# patch decorator (replace global dependencies)
@patch("myapp.services.uuid.uuid4", return_value="fixed-uuid")
def test_creates_with_uuid(self, mock_uuid, mock_repo):
    ...

# pytest-mock (cleaner syntax)
def test_with_mocker(self, mocker, mock_repo):
    mock_send = mocker.patch("myapp.email.send_email")
    svc = UserService(repo=mock_repo)
    svc.create_user(name="Test", email="t@t.com", age=25)
    mock_send.assert_called_once_with(to="t@t.com", subject="Welcome")
```

---

## conftest.py Organization

```python
# tests/conftest.py (global fixtures)
import pytest
from myapp.db import get_test_db

@pytest.fixture(scope="session")
def db():
    """session-scoped database connection (expensive resource)"""
    conn = get_test_db()
    yield conn
    conn.close()

@pytest.fixture(autouse=True)
def reset_db(db):
    """automatically rollback after each test (isolation)"""
    yield
    db.rollback()

# tests/unit/conftest.py (unit-test-specific fixtures)
@pytest.fixture
def mock_email_sender():
    return MagicMock()
```

---

## Common Assertions Reference

```python
assert result == expected
assert result is not None
assert result is None
assert isinstance(result, ExpectedType)
assert "keyword" in result.message
assert len(result.items) == 3
assert result.count > 0

# floats
assert abs(result.price - 9.99) < 0.001
pytest.approx(9.99, abs=0.001)

# exception assertions
with pytest.raises(ValueError, match="invalid email"):
    ...

# warnings
with pytest.warns(DeprecationWarning):
    ...
```

---

## Test Naming Convention

```
test_<action>_when_<condition>_<expected_outcome>

Examples:
  test_create_user_when_name_empty_raises_name_required_error
  test_create_user_when_age_below_minimum_raises_age_invalid_error
  test_create_user_when_repo_fails_raises_save_failed_error
  test_pay_order_when_status_delivered_raises_invalid_transition_error
```
