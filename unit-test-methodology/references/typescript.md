# TypeScript / JavaScript Unit Testing Conventions

## Frameworks

- Primary: `Vitest` (recommended — fast, compatible with Vite ecosystem) or `Jest`
- Mocking: built-in (`vi.fn()` / `jest.fn()`)
- Assertions: built-in `expect`

> **Vitest and Jest APIs are largely compatible.** This file uses Vitest; differences are noted where they exist.

---

## test.each Standard Structure

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
// Jest: import { describe, it, expect, jest, beforeEach } from '@jest/globals'

import { UserService } from './UserService'
import { UserRepository } from './UserRepository'
import {
  NameRequiredError,
  EmailInvalidError,
  AgeInvalidError,
  SaveFailedError,
} from './errors'

// ─── Mock dependencies ────────────────────────────────────────
const mockRepo = {
  save: vi.fn(),        // Jest: jest.fn()
  findByEmail: vi.fn(),
} satisfies Partial<UserRepository>

describe('UserService.createUser()', () => {
  let svc: UserService

  beforeEach(() => {
    vi.clearAllMocks()  // Jest: jest.clearAllMocks()
    svc = new UserService(mockRepo as UserRepository)
  })

  // ─── Happy Path ───────────────────────────────────────────
  it('[EP·valid] valid input - creates user successfully', async () => {
    // Arrange
    mockRepo.save.mockResolvedValue({ id: 'uuid-123', name: 'Markus Moen' })

    // Act
    const result = await svc.createUser({
      name: 'Markus Moen',
      email: 'markus.moen@kozey.biz',
      age: 34,
    })

    // Assert
    expect(result.name).toBe('Markus Moen')
    expect(result.email).toBe('markus.moen@kozey.biz')

    // side-effect verification
    expect(mockRepo.save).toHaveBeenCalledTimes(1)
    expect(mockRepo.save).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'markus.moen@kozey.biz' })
    )
  })

  // ─── Invalid Equivalence Classes ──────────────────────────
  it.each([
    // [name, email, age, ErrorClass, technique]
    ['',       'm@kozey.biz',  34, NameRequiredError, 'EP·invalid·1: name empty'],
    ['   ',    'm@kozey.biz',  34, NameRequiredError, 'EP·invalid·2: name whitespace'],
    ['Markus', 'not-email',    34, EmailInvalidError, 'EP·invalid·3: email format'],
    ['Markus', '',             34, EmailInvalidError, 'EP·invalid·4: email empty'],
  ])(
    '[%4$s] invalid input - should throw',
    async (name, email, age, ErrorClass, _technique) => {
      await expect(svc.createUser({ name, email, age }))
        .rejects.toThrow(ErrorClass)

      // verify no side effects
      expect(mockRepo.save).not.toHaveBeenCalled()
    }
  )

  // ─── Boundary Values ──────────────────────────────────────
  it.each([
    [0,   false, 'BV·min-1: below minimum'],
    [1,   true,  'BV·min: at minimum'],
    [2,   true,  'BV·min+1'],
    [149, true,  'BV·max-1'],
    [150, true,  'BV·max: at maximum'],
    [151, false, 'BV·max+1: above maximum'],
  ])('age=%i → success=%s [%s]', async (age, shouldSucceed, _technique) => {
    if (shouldSucceed) {
      mockRepo.save.mockResolvedValue({ id: 'id', name: 'Test' })
      const result = await svc.createUser({ name: 'Test', email: 't@t.com', age })
      expect(result).toBeDefined()
    } else {
      await expect(svc.createUser({ name: 'Test', email: 't@t.com', age }))
        .rejects.toThrow(AgeInvalidError)
    }
  })

  // ─── Dependency Failures ──────────────────────────────────
  it('[EP·invalid: dependency] database fails - should wrap exception', async () => {
    mockRepo.save.mockRejectedValue(new Error('db connection refused'))

    await expect(svc.createUser({ name: 'Test', email: 't@t.com', age: 25 }))
      .rejects.toThrow(SaveFailedError)
  })
})
```

---

## State Transition Tests

```typescript
describe('Order state machine', () => {
  // valid transitions
  it.each([
    ['pending',   'pay',    'paid',      'ST·valid: pending→paid'],
    ['paid',      'ship',   'shipped',   'ST·valid: paid→shipped'],
    ['shipped',   'deliver','delivered', 'ST·valid: shipped→delivered'],
  ])(
    '%s → %s after %s() [%s]',
    (initial, action, expectedStatus, _technique) => {
      const order = new Order({ status: initial as OrderStatus })
      ;(order as any)[action]()
      expect(order.status).toBe(expectedStatus)
    }
  )

  // invalid transitions
  it.each([
    ['delivered', 'reset',  'ST·invalid: cannot rollback delivered'],
    ['cancelled', 'pay',    'ST·invalid: cannot pay cancelled'],
    ['pending',   'deliver','ST·invalid: cannot skip shipped'],
  ])(
    '%s → %s() should throw [%s]',
    (initial, action, _technique) => {
      const order = new Order({ status: initial as OrderStatus })
      expect(() => (order as any)[action]()).toThrow(InvalidTransitionError)
      expect(order.status).toBe(initial)  // state unchanged
    }
  )
})
```

---

## Decision Table Tests

```typescript
describe('checkPermission()', () => {
  it.each([
    // isAdmin  isOwner  isPublic  expected  technique
    [true,  false, false, true,  'DT·admin always allowed'],
    [false, true,  false, true,  'DT·owner allowed'],
    [false, false, true,  true,  'DT·public readable'],
    [false, false, false, false, 'DT·no permission'],
  ])(
    'admin=%s owner=%s public=%s → %s [%s]',
    (isAdmin, isOwner, isPublic, expected, _technique) => {
      expect(checkPermission({ isAdmin, isOwner, isPublic })).toBe(expected)
    }
  )
})
```

---

## Mock Usage Conventions

```typescript
// function mock
const mockFn = vi.fn()
mockFn.mockReturnValue('result')
mockFn.mockReturnValueOnce('first').mockReturnValueOnce('second')
mockFn.mockResolvedValue(data)          // async success
mockFn.mockRejectedValue(new Error())   // async failure
mockFn.mockImplementation((arg) => arg.toUpperCase())

// call verification
expect(mockFn).toHaveBeenCalled()
expect(mockFn).toHaveBeenCalledTimes(1)
expect(mockFn).toHaveBeenCalledWith('expected-arg')
expect(mockFn).toHaveBeenCalledWith(expect.objectContaining({ key: 'val' }))
expect(mockFn).not.toHaveBeenCalled()

// extract call arguments
const [firstCall] = mockFn.mock.calls
const [arg1, arg2] = firstCall
expect(arg1).toBe('expected')

// module mock (Vitest)
vi.mock('./emailService', () => ({
  sendEmail: vi.fn().mockResolvedValue(undefined),
}))

// spy (observe real implementation)
const spy = vi.spyOn(obj, 'method').mockReturnValue('mocked')
expect(spy).toHaveBeenCalledOnce()

// cleanup
beforeEach(() => vi.clearAllMocks())
afterAll(() => vi.restoreAllMocks())
```

---

## Common expect Assertions

```typescript
// basic
expect(result).toBe(exact)              // strict equality (===)
expect(result).toEqual(deep)            // deep equality
expect(result).toStrictEqual(deep)      // deep equality (includes undefined fields)
expect(result).toBeTruthy()
expect(result).toBeFalsy()
expect(result).toBeNull()
expect(result).toBeUndefined()
expect(result).toBeDefined()

// numbers
expect(num).toBeGreaterThan(0)
expect(num).toBeGreaterThanOrEqual(1)
expect(num).toBeLessThan(100)
expect(price).toBeCloseTo(9.99, 2)      // decimal precision

// strings
expect(str).toContain('substring')
expect(str).toMatch(/regex/)
expect(str).toHaveLength(10)

// arrays / objects
expect(arr).toHaveLength(3)
expect(arr).toContain(item)
expect(arr).toEqual(expect.arrayContaining([a, b]))
expect(obj).toMatchObject({ key: 'val' })  // partial match
expect(obj).toHaveProperty('nested.key', 'val')

// exceptions
expect(() => fn()).toThrow()
expect(() => fn()).toThrow(CustomError)
expect(() => fn()).toThrow('error message')
await expect(asyncFn()).rejects.toThrow(CustomError)
await expect(asyncFn()).resolves.toEqual(expected)

// snapshots (use sparingly — can produce misleading tests)
expect(complexObject).toMatchSnapshot()
```

---

## Test Structure Organization

```typescript
// nest with describe per method under test
describe('UserService', () => {
  describe('createUser()', () => {
    // related tests
  })

  describe('updateUser()', () => {
    // related tests
  })
})

// test naming: describe behavior, not implementation
// ✓ 'should throw NameRequiredError when name is empty'
// ✓ '[EP·invalid·1] name is empty → throws NameRequiredError'
// ✗ 'test1'
// ✗ 'empty name'
```

---

## Async Test Pitfalls

```typescript
// ✓ correct: await or return promise
it('async test', async () => {
  const result = await asyncFn()
  expect(result).toBeDefined()
})

// ✓ correct: return promise (less preferred, easy to forget)
it('async test', () => {
  return expect(asyncFn()).resolves.toBeDefined()
})

// ✗ wrong: no await — assertion never executes
it('broken async test', () => {
  asyncFn().then(result => {
    expect(result).toBeDefined()  // this line never runs!
  })
})
```
