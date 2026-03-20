# Zig Unit Testing Conventions

## Frameworks

- Built-in: `test "description" { ... }` blocks (standard library, no external deps)
- Assertions: `std.testing` (`expectEqual`, `expectError`, `expect`, `expectEqualStrings`, etc.)
- Mocking: idiomatic Zig uses **comptime interfaces** (struct with function pointer fields) — no external library needed
- Runner: `zig test src/main.zig` or `zig build test`

---

## Table-Driven Test Standard Structure

```zig
const std = @import("std");
const testing = std.testing;

test "createUser - equivalence classes and boundary values" {
    const Case = struct {
        name: []const u8,
        input_name: []const u8,
        input_email: []const u8,
        input_age: u32,
        expected_err: ?UserError, // null = expect success
        technique: []const u8,
    };

    const cases = [_]Case{
        // ─── Happy Path ───────────────────────────────────────
        .{
            .name         = "valid input - creates user successfully",
            .input_name   = "Markus Moen",
            .input_email  = "markus.moen@kozey.biz",
            .input_age    = 34,
            .expected_err = null,
            .technique    = "EP·valid",
        },
        // ─── Invalid Equivalence Classes ──────────────────────
        .{
            .name         = "empty name - invalid EP 1",
            .input_name   = "",
            .input_email  = "markus@kozey.biz",
            .input_age    = 34,
            .expected_err = UserError.NameRequired,
            .technique    = "EP·invalid·1: name empty",
        },
        .{
            .name         = "invalid email format - invalid EP 2",
            .input_name   = "Markus",
            .input_email  = "not-an-email",
            .input_age    = 34,
            .expected_err = UserError.EmailInvalid,
            .technique    = "EP·invalid·2: email format",
        },
        // ─── Boundary Values ──────────────────────────────────
        .{
            .name         = "age=0 - below min boundary",
            .input_name   = "Test",
            .input_email  = "t@t.com",
            .input_age    = 0,
            .expected_err = UserError.AgeInvalid,
            .technique    = "BV·min-1",
        },
        .{
            .name         = "age=1 - at min boundary (valid)",
            .input_name   = "Test",
            .input_email  = "t@t.com",
            .input_age    = 1,
            .expected_err = null,
            .technique    = "BV·min",
        },
        .{
            .name         = "age=150 - at max boundary (valid)",
            .input_name   = "Test",
            .input_email  = "t@t.com",
            .input_age    = 150,
            .expected_err = null,
            .technique    = "BV·max",
        },
        .{
            .name         = "age=151 - above max boundary",
            .input_name   = "Test",
            .input_email  = "t@t.com",
            .input_age    = 151,
            .expected_err = UserError.AgeInvalid,
            .technique    = "BV·max+1",
        },
    };

    for (cases) |c| {
        var repo = MockUserRepo.init();
        const result = createUser(c.input_name, c.input_email, c.input_age, repo.interface());

        if (c.expected_err) |expected| {
            try testing.expectError(expected, result);
        } else {
            const user = try result;
            try testing.expectEqualStrings(c.input_name, user.name);
        }
    }
}

// ─── Dependency Failure ───────────────────────────────────────
test "createUser - repo save fails returns SaveFailed" {
    // [EP·invalid: dependency]
    var repo = MockUserRepo.initWithSaveError(error.ConnectionRefused);
    const result = createUser("Test", "t@t.com", 25, repo.interface());
    try testing.expectError(UserError.SaveFailed, result);
}
```

---

## Comptime Interface (Dependency Injection / Mocking)

Zig's idiomatic mock pattern uses a struct with function pointer fields — no macro magic needed.

```zig
// production interface definition
pub const UserRepository = struct {
    ptr: *anyopaque,
    saveFn: *const fn (ptr: *anyopaque, user: User) anyerror!void,
    findByEmailFn: *const fn (ptr: *anyopaque, email: []const u8) ?User,

    pub fn save(self: UserRepository, user: User) anyerror!void {
        return self.saveFn(self.ptr, user);
    }
    pub fn findByEmail(self: UserRepository, email: []const u8) ?User {
        return self.findByEmailFn(self.ptr, email);
    }
};
```

```zig
// test mock implementation
const MockUserRepo = struct {
    save_error: ?anyerror = null,
    save_calls: u32 = 0,
    saved_user: ?User = null,

    pub fn init() MockUserRepo {
        return .{};
    }

    pub fn initWithSaveError(err: anyerror) MockUserRepo {
        return .{ .save_error = err };
    }

    fn saveFn(ptr: *anyopaque, user: User) anyerror!void {
        const self: *MockUserRepo = @ptrCast(@alignCast(ptr));
        self.save_calls += 1;
        self.saved_user = user;
        if (self.save_error) |err| return err;
    }

    fn findByEmailFn(ptr: *anyopaque, email: []const u8) ?User {
        _ = ptr;
        _ = email;
        return null;
    }

    pub fn interface(self: *MockUserRepo) UserRepository {
        return .{
            .ptr = self,
            .saveFn = saveFn,
            .findByEmailFn = findByEmailFn,
        };
    }
};

// assertion usage
try testing.expectEqual(@as(u32, 1), repo.save_calls);
try testing.expectEqualStrings("markus@kozey.biz", repo.saved_user.?.email);
```

---

## State Transition Test Example

```zig
test "Order state transitions" {
    const Case = struct {
        name: []const u8,
        initial: OrderStatus,
        action: fn (*Order) UserError!void,
        expected_status: OrderStatus,
        expect_err: ?UserError,
        technique: []const u8,
    };

    const cases = [_]Case{
        // valid transitions
        .{ .name = "pending to paid",           .initial = .pending,   .action = Order.pay,    .expected_status = .paid,      .expect_err = null,                    .technique = "ST·valid: pending→paid" },
        .{ .name = "paid to shipped",           .initial = .paid,      .action = Order.ship,   .expected_status = .shipped,   .expect_err = null,                    .technique = "ST·valid: paid→shipped" },
        // invalid transitions
        .{ .name = "delivered cannot rollback", .initial = .delivered, .action = Order.reset,  .expected_status = .delivered, .expect_err = UserError.InvalidTransition, .technique = "ST·invalid: cannot rollback delivered" },
        .{ .name = "cancelled cannot pay",      .initial = .cancelled, .action = Order.pay,    .expected_status = .cancelled, .expect_err = UserError.InvalidTransition, .technique = "ST·invalid: cannot pay cancelled" },
    };

    for (cases) |c| {
        var order = Order{ .status = c.initial };
        const result = c.action(&order);
        if (c.expect_err) |expected| {
            try testing.expectError(expected, result);
            try testing.expectEqual(c.initial, order.status); // status unchanged
        } else {
            try result;
            try testing.expectEqual(c.expected_status, order.status);
        }
    }
}
```

---

## Decision Table Test Example

```zig
test "checkPermission - decision table" {
    const Case = struct {
        is_admin: bool,
        is_owner: bool,
        is_public: bool,
        expected: bool,
        technique: []const u8,
    };

    const cases = [_]Case{
        .{ .is_admin = true,  .is_owner = false, .is_public = false, .expected = true,  .technique = "DT·admin always allowed" },
        .{ .is_admin = false, .is_owner = true,  .is_public = false, .expected = true,  .technique = "DT·owner allowed" },
        .{ .is_admin = false, .is_owner = false, .is_public = true,  .expected = true,  .technique = "DT·public readable" },
        .{ .is_admin = false, .is_owner = false, .is_public = false, .expected = false, .technique = "DT·no permission" },
    };

    for (cases) |c| {
        const result = checkPermission(c.is_admin, c.is_owner, c.is_public);
        try testing.expectEqual(c.expected, result);
    }
}
```

---

## Error Type Conventions

```zig
// define error sets for precise error assertions
pub const UserError = error{
    NameRequired,
    EmailInvalid,
    AgeInvalid,
    SaveFailed,
};

// assert on specific error
try testing.expectError(UserError.NameRequired, result);

// assert success and unwrap
const user = try result;

// assert success without using value
_ = try result;

// check error type at runtime
if (result) |_| {
    // success case
} else |err| {
    try testing.expectEqual(UserError.NameRequired, err);
}
```

---

## Allocator Usage in Tests

```zig
test "createUserList - allocates correct count" {
    // use the testing allocator — detects leaks automatically
    const allocator = testing.allocator;

    const users = try createUserList(allocator, 3);
    defer allocator.free(users);

    try testing.expectEqual(@as(usize, 3), users.len);
}
```

`testing.allocator` automatically fails the test on any memory leak — no manual leak-checking required.

---

## Common Assertion Reference

```zig
const testing = std.testing;

// equality (note: expected first, actual second)
try testing.expectEqual(expected, actual);
try testing.expectEqualStrings(expected_str, actual_str);
try testing.expectEqualSlices(T, expected_slice, actual_slice);

// boolean
try testing.expect(condition);

// errors
try testing.expectError(expected_error, result_or_error_union);

// null / optional
try testing.expect(optional != null);
try testing.expectEqual(@as(?T, null), optional);

// approximate (floats)
try testing.expectApproxEqAbs(expected, actual, tolerance);
try testing.expectApproxEqRel(expected, actual, tolerance);

// panics (comptime — use sparingly)
// Zig has no built-in expect-panic; use if/catch pattern instead:
const result = dangerousFn();
if (result) |_| {
    return error.ExpectedError; // fail: should have errored
} else |err| {
    try testing.expectEqual(ExpectedError.SomeVariant, err);
}
```

---

## Test Naming Convention

```
test "<function> - <scenario>"

Examples:
  test "createUser - valid input returns user"
  test "createUser - empty name returns NameRequired"
  test "createUser - age=0 below min boundary returns AgeInvalid"
  test "createUser - repo save fails returns SaveFailed"
  test "transferMoney - insufficient balance returns error"
  test "checkPermission - decision table"
```

Zig test names are free-form strings. Use `<function> - <scenario>` consistently. `zig test` prints each test name on failure, so names must be self-explanatory.

---

## Test File Organization

```zig
// option 1: inline test blocks in the same file (standard)
pub fn createUser(...) !User { ... }

test "createUser - valid input returns user" { ... }
test "createUser - empty name returns NameRequired" { ... }

// option 2: separate test file importing the module
// src/user_test.zig
const user = @import("user.zig");

test "createUser - valid input returns user" {
    const result = try user.createUser(...);
    ...
}

// build.zig: add test step
const unit_tests = b.addTest(.{
    .root_source_file = b.path("src/main.zig"),
    .target = target,
    .optimize = optimize,
});
const run_unit_tests = b.addRunArtifact(unit_tests);
const test_step = b.step("test", "Run unit tests");
test_step.dependOn(&run_unit_tests.step);
```
