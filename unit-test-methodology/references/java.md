# Java Unit Testing Conventions

## Frameworks

- Primary: `JUnit 5` (`@ParameterizedTest` + `@MethodSource` / `@CsvSource`)
- Mocking: `Mockito` (`@Mock` + `@InjectMocks` + `@ExtendWith(MockitoExtension.class)`)
- Assertions: `AssertJ` (fluent assertions, clearer than JUnit native)

---

## Parameterized Test Standard Structure

```java
package com.example.service;

import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("UserService.createUser()")
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    // ─── Happy Path ───────────────────────────────────────────
    @Test
    @DisplayName("[EP·valid] valid input - creates user successfully")
    void createUser_validInput_returnsCreatedUser() {
        // Arrange
        var input = new CreateUserInput("Markus Moen", "markus.moen@kozey.biz", 34);
        when(userRepository.save(any())).thenReturn(new User("uuid-123", "Markus Moen"));

        // Act
        var result = userService.createUser(input);

        // Assert
        assertThat(result).isNotNull();
        assertThat(result.getName()).isEqualTo("Markus Moen");

        // side-effect verification
        verify(userRepository, times(1)).save(any(User.class));
        verifyNoMoreInteractions(userRepository);
    }

    // ─── Invalid Equivalence Classes (MethodSource for object params) ─
    @ParameterizedTest(name = "[{index}] {2}")
    @MethodSource("invalidInputProvider")
    @DisplayName("invalid input - should throw corresponding exception")
    void createUser_invalidInput_throwsException(
            CreateUserInput input,
            Class<? extends Exception> expectedException,
            String technique
    ) {
        assertThatThrownBy(() -> userService.createUser(input))
                .isInstanceOf(expectedException);

        // verify no side effects
        verifyNoInteractions(userRepository);
    }

    static Stream<Arguments> invalidInputProvider() {
        return Stream.of(
            Arguments.of(
                new CreateUserInput("", "m@kozey.biz", 34),
                NameRequiredException.class,
                "EP·invalid·1: name empty"
            ),
            Arguments.of(
                new CreateUserInput("   ", "m@kozey.biz", 34),
                NameRequiredException.class,
                "EP·invalid·2: name whitespace only"
            ),
            Arguments.of(
                new CreateUserInput("Markus", "not-email", 34),
                EmailInvalidException.class,
                "EP·invalid·3: email format invalid"
            ),
            Arguments.of(
                new CreateUserInput("Markus", "", 34),
                EmailInvalidException.class,
                "EP·invalid·4: email empty"
            )
        );
    }

    // ─── Boundary Values (CsvSource for simple params) ────────
    @ParameterizedTest(name = "[{index}] age={0} → success={1} [{2}]")
    @CsvSource({
        "0,   false, BV·min-1: below minimum",
        "1,   true,  BV·min: at minimum",
        "2,   true,  BV·min+1",
        "149, true,  BV·max-1",
        "150, true,  BV·max: at maximum",
        "151, false, BV·max+1: above maximum"
    })
    @DisplayName("age boundary value tests")
    void createUser_ageBoundary(int age, boolean shouldSucceed, String technique) {
        var input = new CreateUserInput("Test", "test@example.com", age);

        if (shouldSucceed) {
            when(userRepository.save(any())).thenReturn(new User("id", "Test"));
            var result = userService.createUser(input);
            assertThat(result).isNotNull();
        } else {
            assertThatThrownBy(() -> userService.createUser(input))
                    .isInstanceOf(AgeInvalidException.class);
        }
    }

    // ─── Dependency Failures ──────────────────────────────────
    @Test
    @DisplayName("[EP·invalid: dependency] repository throws - should wrap exception")
    void createUser_repositoryThrows_throwsSaveFailedException() {
        // Arrange
        var input = new CreateUserInput("Test", "test@example.com", 25);
        when(userRepository.save(any())).thenThrow(new RuntimeException("db error"));

        // Act + Assert
        assertThatThrownBy(() -> userService.createUser(input))
                .isInstanceOf(SaveFailedException.class)
                .hasMessageContaining("db error");  // verify error message propagation
    }
}
```

---

## State Transition Tests

```java
@DisplayName("Order state machine")
class OrderStateTransitionTest {

    @ParameterizedTest(name = "[{index}] {0}→{2} [{3}]")
    @MethodSource("validTransitionsProvider")
    void validTransition_changesStatus(
            OrderStatus initial, String action,
            OrderStatus expectedStatus, String technique
    ) throws Exception {
        var order = new Order(initial);
        order.getClass().getMethod(action).invoke(order);
        assertThat(order.getStatus()).isEqualTo(expectedStatus);
    }

    static Stream<Arguments> validTransitionsProvider() {
        return Stream.of(
            Arguments.of(PENDING,   "pay",    PAID,      "ST·valid: pending→paid"),
            Arguments.of(PAID,      "ship",   SHIPPED,   "ST·valid: paid→shipped"),
            Arguments.of(SHIPPED,   "deliver",DELIVERED, "ST·valid: shipped→delivered")
        );
    }

    @ParameterizedTest(name = "[{index}] {0}→{1}() should throw [{2}]")
    @MethodSource("invalidTransitionsProvider")
    void invalidTransition_throwsException(
            OrderStatus initial, String action, String technique
    ) throws Exception {
        var order = new Order(initial);
        var initialStatus = order.getStatus();

        assertThatThrownBy(() ->
            order.getClass().getMethod(action).invoke(order)
        ).hasCauseInstanceOf(InvalidTransitionException.class);

        assertThat(order.getStatus()).isEqualTo(initialStatus); // state unchanged
    }

    static Stream<Arguments> invalidTransitionsProvider() {
        return Stream.of(
            Arguments.of(DELIVERED, "reset",  "ST·invalid: cannot rollback delivered"),
            Arguments.of(CANCELLED, "pay",    "ST·invalid: cannot pay cancelled order")
        );
    }
}
```

---

## Decision Table Tests

```java
@DisplayName("Permission check decision table")
class PermissionCheckTest {

    @ParameterizedTest(name = "[{index}] admin={0} owner={1} public={2} → {3} [{4}]")
    @CsvSource({
        "true,  false, false, true,  DT·admin always has access",
        "false, true,  false, true,  DT·owner has access",
        "false, false, true,  true,  DT·public resource readable",
        "false, false, false, false, DT·no permission"
    })
    void checkPermission_decisionTable(
            boolean isAdmin, boolean isOwner,
            boolean isPublic, boolean expected, String technique
    ) {
        var result = permissionChecker.check(isAdmin, isOwner, isPublic);
        assertThat(result).isEqualTo(expected);
    }
}
```

---

## Mockito Usage Conventions

```java
// basic mock setup
when(repo.findById("123")).thenReturn(Optional.of(user));
when(repo.findById("999")).thenReturn(Optional.empty());
when(repo.save(any())).thenThrow(new DataAccessException("db error"));

// doReturn (chained return values)
doReturn(user1, user2, user3).when(repo).findNext();

// call verification
verify(repo).save(user);                              // exact match
verify(repo, times(2)).save(any());                  // call count
verify(repo, never()).delete(any());                 // never called
verify(repo).save(argThat(u -> u.getEmail().contains("@"))); // custom matcher

// argument capture (extract call arguments for assertion)
var captor = ArgumentCaptor.forClass(User.class);
verify(repo).save(captor.capture());
assertThat(captor.getValue().getEmail()).isEqualTo("markus@kozey.biz");

// verify no further interactions
verifyNoMoreInteractions(repo);
verifyNoInteractions(emailSender);
```

---

## AssertJ Common Assertions

```java
// basic
assertThat(result).isEqualTo(expected);
assertThat(result).isNotNull();
assertThat(result).isNull();
assertThat(result).isTrue();
assertThat(flag).isFalse();

// strings
assertThat(message).contains("error");
assertThat(email).matches("[^@]+@[^@]+\\.[^@]+");
assertThat(name).isNotBlank();

// collections
assertThat(list).hasSize(3);
assertThat(list).contains(element);
assertThat(list).containsExactlyInAnyOrder(a, b, c);
assertThat(list).isEmpty();
assertThat(list).extracting("name").containsExactly("Alice", "Bob");

// exceptions
assertThatThrownBy(() -> svc.create(input))
    .isInstanceOf(ValidationException.class)
    .hasMessage("name is required")
    .hasFieldOrPropertyWithValue("field", "name");

// numbers
assertThat(price).isBetween(0.0, 9999.99);
assertThat(count).isGreaterThan(0);
assertThat(actual).isCloseTo(9.99, within(0.001));

// soft assertions (collect all failures without stopping)
SoftAssertions.assertSoftly(softly -> {
    softly.assertThat(result.getName()).isEqualTo("Markus");
    softly.assertThat(result.getEmail()).isEqualTo("markus@kozey.biz");
    softly.assertThat(result.getAge()).isEqualTo(34);
});
```

---

## Test Structure Organization

```java
@DisplayName("UserService")
class UserServiceTest {

    @Nested
    @DisplayName("createUser()")
    class CreateUser {
        @Test @DisplayName("...") void ...() {}
    }

    @Nested
    @DisplayName("updateUser()")
    class UpdateUser {
        @Test @DisplayName("...") void ...() {}
    }
}
```

One `@Nested` class per method, use `@DisplayName` to describe business intent clearly.
