# Anti-pattern catalog

Reference for AdversaryPR's design rule set. Each entry covers the signal to look for in a diff, what
it costs, a short before/after example, and when to leave it alone. The default severity is P3.
Entries note when to raise it.

Every name in the examples is invented. The examples show the shape of a problem, not any real
codebase.

Several entries overlap with the language rule files (swallowed errors, hardcoded values,
business logic in controllers). Report an issue once, under whichever rule gives the clearer fix.
The gates in `adversarypr-design-principles.instructions.md` apply to every entry here: the diff has to cause it, you have to be able to
name the cost, and the repo's own conventions win.

## Contents

**Size and shape:** [God Object](#god-object) ·
[Long Method / Arrow Code](#long-method--arrow-code) ·
[Long Parameter List and Flag Arguments](#long-parameter-list-and-flag-arguments) ·
[Data Clumps](#data-clumps)

**Types and values:** [Primitive Obsession](#primitive-obsession--stringly-typed-code) ·
[Magic Numbers and Strings](#magic-numbers-and-strings) ·
[Money in Floating Point](#money-in-floating-point-p1)

**Coupling:** [Feature Envy](#feature-envy) · [Train Wreck](#train-wreck-law-of-demeter) ·
[Shotgun Surgery](#shotgun-surgery) ·
[Hidden Dependencies and Global Mutable State](#hidden-dependencies-and-global-mutable-state) ·
[Leaky Abstraction](#leaky-abstraction) · [Circular Dependency](#circular-dependency) ·
[Inheritance for Reuse / Refused Bequest](#inheritance-for-reuse--refused-bequest)

**Behavior and flow:** [Temporal Coupling](#temporal-coupling) ·
[Side Effects in Queries](#side-effects-in-queries) ·
[Sentinel Returns and Exceptions as Control Flow](#sentinel-returns-and-exceptions-as-control-flow) ·
[Middle Man](#middle-man--needless-indirection) · [Dead Code](#dead-code-p5)

**Covered in design-principles.md:** Copy-Paste Programming (see DRY) and Speculative Generality
(see YAGNI).

---

## Size and shape

### God Object

**Signal:** the diff adds another unrelated responsibility to a type that already holds state and
logic for several features and that most changes in the codebase touch. Names like `AppManager`,
`CoreService`, and `Utils` are common.

**Cost:** constant merge conflicts, fragile tests, and every change risks breaking an unrelated
feature.

**Example:** see SRP in design-principles.md.

**Fix:** put the new responsibility in a new type now. Don't ask this PR to break up the whole
object; suggest a follow-up ticket for that.

**Don't flag:** growth the repo's architecture expects, such as a coordinator documented as the
single owner of navigation.

### Long Method / Arrow Code

**Signal:** a new or changed function that nests conditionals or loops four or more levels deep,
or that mixes several steps and needs scrolling to follow.

**Cost:** it's hard to see which branch runs when, a bug slips easily into one arm, and each path
is hard to test.

**Example (Swift)**

```swift
// Before
func apply(_ coupon: Coupon?, to cart: Cart) -> Cart {
    if let coupon {
        if !coupon.isExpired {
            if cart.subtotal >= coupon.minimumSpend {
                return cart.discounted(by: coupon.amount)
            }
        }
    }
    return cart
}

// After: guard clauses keep the happy path flat
func apply(_ coupon: Coupon?, to cart: Cart) -> Cart {
    guard let coupon, !coupon.isExpired, cart.subtotal >= coupon.minimumSpend else { return cart }
    return cart.discounted(by: coupon.amount)
}
```

**Don't flag:** length alone, when the function is a flat, readable sequence (a mapper that lists
thirty fields, for example).

### Long Parameter List and Flag Arguments

**Signal:** a function gains a fifth or later parameter, or a boolean that switches its behavior,
so call sites read like `sendReceipt(order, true, false)`.

**Cost:** call sites can't be read without jumping to the definition, arguments of the same type
get swapped silently, and each flag doubles the paths to test.

**Example (TypeScript)**

```ts
// Before
sendReceipt(order, true, false);   // what do true and false mean here?

// After: a named options object...
sendReceipt(order, { channel: "email", attachInvoicePdf: false });

// ...or, when the boolean picks between two behaviors, two functions
emailReceipt(order);
printReceipt(order);
```

**Don't flag:** calls where argument labels or named arguments make each value readable (Swift
labels, Kotlin or Python named arguments), unless the flag still splits the function into two
different behaviors.

### Data Clumps

**Signal:** the same group of values travels together through several signatures, such as
`(lat, lng, radiusMeters)`, `(amount, currency)`, or `(start, end, timeZone)`.

**Cost:** validation of the group gets duplicated or skipped, and values get passed in the wrong
order.

**Example (Kotlin)**

```kotlin
// Before
fun storesNear(lat: Double, lng: Double, radiusMeters: Int): List<Store>
fun deliveryFee(lat: Double, lng: Double, radiusMeters: Int, basketCents: Long): Long

// After: the group becomes a type that validates itself once
data class SearchArea(val center: Coordinate, val radiusMeters: Int) {
    init { require(radiusMeters > 0) { "radius must be positive" } }
}
fun storesNear(area: SearchArea): List<Store>
fun deliveryFee(area: SearchArea, basketCents: Long): Long
```

**Don't flag:** two values that happen to travel together once.

---

## Types and values

### Primitive Obsession / Stringly-Typed Code

**Signal:** IDs, states, units, or currencies passed around as raw `String`, `Int`, or `Double`;
functions that take several IDs of the same raw type; states compared as strings
(`status == "SHIPPED"`).

**Cost:** swapped arguments compile fine, a typo becomes a silent runtime bug, and invalid values
have no place where they get rejected.

**Example (Swift)**

```swift
// Before: both IDs are Strings, so swapping them compiles; the typo is silently false
func transfer(from accountId: String, to recipientId: String, amountCents: Int)
if order.status == "shiped" { notifyCustomer() }

// After: the compiler catches both mistakes
struct AccountID: Hashable { let rawValue: String }
struct RecipientID: Hashable { let rawValue: String }
enum OrderStatus: String { case pending, shipped, delivered }

func transfer(from account: AccountID, to recipient: RecipientID, amountCents: Int)
if order.status == .shipped { notifyCustomer() }
```

**Raise to P1** when the diff already mixes up two same-typed values or compares against a
misspelled string.

**Don't flag:** a raw string at a boundary (a JSON field, a database row) that gets converted to the
typed value right away.

### Magic Numbers and Strings

**Signal:** an unexplained literal inside logic, such as `if attempts > 3`, `status == 7`,
`86400`, or `"usr_pref_v2"`.

**Cost:** the reader can't tell what the value means or whether two `3`s are the same rule, and
changing it means finding every copy.

**Example (Go)**

```go
// Before
if attempts > 3 {
    return lockUntil(now.Add(900 * time.Second))
}

// After
const (
    maxLoginAttempts = 3
    lockoutDuration  = 15 * time.Minute
)

if attempts > maxLoginAttempts {
    return lockUntil(now.Add(lockoutDuration))
}
```

**Overlap:** hardcoded user-facing strings, colors, and dimensions are already covered by the
language rules. Report those there.

**Don't flag:** `0`, `1`, the empty string, or a literal whose meaning is obvious from a named
argument or the line itself (`timeout: .seconds(30)`).

### Money in Floating Point (P1)

**Signal:** prices, balances, tax, or totals stored or computed as `Double`, `Float`, `float`, or a
JavaScript `number` holding fractional currency.

**Cost:** binary floating point can't represent most decimal fractions exactly, so
`0.1 + 0.2 != 0.3`. Totals drift by a cent, equality checks fail, and reconciliation breaks.

**Example (Java)**

```java
// Before
double total = 0.10 + 0.20;           // 0.30000000000000004
if (total == 0.30) applyDiscount();   // never runs

// After: integer minor units, or a decimal type with an explicit rounding mode
long totalCents = 10 + 20;
BigDecimal total = new BigDecimal("0.10").add(new BigDecimal("0.20"));   // exactly 0.30
```

Equivalents: Swift `Decimal`, Kotlin or Java `BigDecimal` or `Long` cents, Python
`decimal.Decimal`, Go `int64` cents, TypeScript integer cents or a decimal library.

**Don't flag:** display-only formatting of a value that's stored correctly elsewhere, or
scientific and statistical values that aren't money.

---

## Coupling

### Feature Envy

**Signal:** a new method that mostly reads another object's fields to work out something about that
object.

**Cost:** the rule lives away from the data it depends on, so it gets duplicated somewhere else
and breaks when the other type changes.

**Example (Python)**

```python
# Before: in ShippingService, but it's all about the Order's internals
def is_free_shipping(self, order):
    return (order.subtotal_cents >= 5000
            and order.address.country == "US"
            and not order.has_oversized_items)

# After: the rule moves next to the data it reads
class Order:
    def qualifies_for_free_shipping(self) -> bool:
        return (self.subtotal_cents >= FREE_SHIPPING_MIN_CENTS
                and self.address.country == "US"
                and not self.has_oversized_items)
```

**Don't flag:** mappers, serializers, and presenters, whose job is to read another type's fields.

### Train Wreck (Law of Demeter)

**Signal:** long chains through other objects' internals, like
`order.customer.account.settings.locale.language`.

**Cost:** the caller now depends on the shape of five types, any change in the middle breaks it,
and a missing value anywhere in the chain crashes or needs a guard at every step.

**Example (Kotlin)**

```kotlin
// Before
val language = order.customer.account.settings.locale.language

// After: ask the nearest object for what you need
val language = order.customerLanguage()
```

**Don't flag:** fluent and builder APIs, collection pipelines (`items.filter { }.map { }.sum()`),
and plain data navigation inside mappers.

### Shotgun Surgery

**Signal:** one conceptual change forces small edits across many files. For example, the diff adds
one new status and touches five switch statements, three mappers, and two lookup tables.

**Cost:** the next person to add a status will miss one of those places, and nothing tells them
which.

**Example:** see OCP in design-principles.md.

**Fix:** gather the per-variant knowledge in one place (an enum with properties, a sealed type, a
single table), or at least make every switch exhaustive with no `default` so the compiler finds
them all.

**Don't flag:** a change that legitimately crosses the layers once. A new field flowing from DTO
to mapper to model to UI is normal layering.

### Hidden Dependencies and Global Mutable State

**Signal:** logic that reaches out for collaborators instead of receiving them: a service locator,
a static `shared` or `getInstance()`, an environment variable, or a global mutable variable read or
written deep inside a function.

**Cost:** the function's signature lies about what it needs, tests leak state into each other, and
concurrent callers race on the global.

**Example (TypeScript)**

```ts
// Before
export let currentUser: User | null = null;   // global, mutable, set from anywhere

export function canEdit(doc: Doc): boolean {
  return ServiceLocator.get(Permissions).check(currentUser, doc);
}

// After: dependencies are parameters (or constructor arguments)
export function canEdit(user: User, doc: Doc, permissions: Permissions): boolean {
  return permissions.check(user, doc);
}
```

**Raise to P2** when the global is mutated from more than one thread or request. That's a
concurrency finding as well.

**Don't flag:** app-wide instances the repo documents as sanctioned (check CLAUDE.md / AGENTS.md),
or the logger.

### Leaky Abstraction

**Signal:** a layer's internals escape through its interface: a repository returning ORM entities,
HTTP responses, or raw JSON to UI code; vendor SDK types in domain signatures; a getter that hands
out an internal mutable collection.

**Cost:** callers couple to the details the abstraction was supposed to hide, so changing the
database, API, or vendor ripples outward, and exposed mutable state gets changed behind the owner's
back.

**Example (Java)**

```java
// Before: callers can modify the cart's internal list and skip its rules
public List<LineItem> getItems() { return items; }

// After: hand out a read-only copy, and make changes go through the owner
public List<LineItem> getItems() { return List.copyOf(items); }

public void add(LineItem item) {
    validate(item);
    items.add(item);
}
```

A second common form: a data-layer method such as `fetchProfile()` returning its
`ProfileResponseDTO` all the way to a screen. Map it to a domain type at the boundary.

**Don't flag:** internal types used inside the same module or layer.

### Circular Dependency

**Signal:** module or package A imports B while B imports A, directly or through C; or a "shared"
module that imports the features that use it.

**Cost:** neither side can be changed, built, or tested alone, and initialization order bugs
appear. In some languages the build simply fails, and in others a value is quietly `undefined` at
load time.

**Example (Kotlin, two Gradle modules)**

```kotlin
// Before: :orders depends on :billing to create invoices, and :billing depends on :orders for Order

// After: :billing owns the small contract it needs, and :orders implements it
// in :billing
interface Billable {
    val customerId: CustomerId
    val totalCents: Long
}
fun createInvoice(item: Billable): Invoice

// in :orders (depends on :billing; :billing no longer depends on :orders)
data class Order(override val customerId: CustomerId, override val totalCents: Long) : Billable
```

**Related:** a reference cycle between objects (for example a stored closure that captures `self`
strongly) is a memory leak. Report it under the language rules as P2.

**Don't flag:** a pair of types designed as one unit, like a tree node with a weak `parent`
reference.

### Inheritance for Reuse / Refused Bequest

**Signal:** a new subclass that extends a base only to reuse a helper, that overrides inherited
methods to disable them (the "refused bequest"; see LSP), or that adds a third or deeper level to a
hierarchy.

**Cost:** the subclass inherits every future change to the base, wanted or not, and the hierarchy
becomes hard to change without breaking a sibling.

**Example (Swift)**

```swift
// Before: inherits a whole screen base class to reuse one date helper
final class ReceiptFormatter: BaseScreenController {
    func text(for receipt: Receipt) -> String {
        "\(receipt.totalText) on \(formatShortDate(receipt.date))"
    }
}

// After: compose the one thing actually needed
struct ReceiptFormatter {
    let dates: ShortDateFormatter
    func text(for receipt: Receipt) -> String {
        "\(receipt.totalText) on \(dates.string(from: receipt.date))"
    }
}
```

**Don't flag:** subclassing the framework requires (a platform view controller, activity,
fragment, or view model base class) or test base classes the repo already uses.

---

## Behavior and flow

### Temporal Coupling

**Signal:** a type that only works when methods are called in a certain order (`configure()`
before `start()`, `setUser()` before `load()`), or new `lateinit`, implicitly unwrapped (`!`), or
nullable fields that get filled in "later".

**Cost:** calling out of order crashes or silently misbehaves, and nothing in the API tells the
caller the rule.

**Example (Kotlin)**

```kotlin
// Before
class ReportExporter {
    lateinit var destination: Destination
    fun export(report: Report) = destination.write(report.render())   // crashes if destination was never set
}

// After: required inputs go in the constructor, so an unusable object can't exist
class ReportExporter(private val destination: Destination) {
    fun export(report: Report) = destination.write(report.render())
}
```

**Raise to P1** when a call path in the diff can reach the method before setup runs.

**Don't flag:** lifecycles the platform defines, or fields a DI framework guarantees to fill before
use.

### Side Effects in Queries

**Signal:** a getter, computed property, `is…` / `has…` / `get…` function, or `toString()` that
writes state, performs I/O, sends analytics, or advances an iterator. (This is the
command-query separation rule: a function should either answer a question or do something, not
both.)

**Cost:** reading a value changes the system, calling it twice gives different results, and a
debugger or log line that evaluates the getter triggers the side effect.

**Example (Swift)**

```swift
// Before: checking validity also saves a draft and sends an analytics event
var isValid: Bool {
    let ok = !email.isEmpty && password.count >= Self.minimumPasswordLength
    if ok { try? draftStore.save(draft) }
    analytics.track("form_validated")
    return ok
}

// After: the query answers; the command acts
var isValid: Bool { !email.isEmpty && password.count >= Self.minimumPasswordLength }

func submit() throws {
    guard isValid else { throw FormError.invalid }
    try draftStore.save(draft)
    analytics.track(.formSubmitted)
}
```

**Raise to P1** when the side effect changes results, such as a double charge, a double count, or
a skipped item.

**Don't flag:** lazy initialization or memoization that callers can't observe, or debug-only
logging.

### Sentinel Returns and Exceptions as Control Flow

**Signal:** a function that reports failure with `-1`, `null`, `""`, or `false` where the language
offers an optional, a `Result`, or typed errors; or the opposite, `try` / `catch` used for ordinary
branching (catching a parse error to ask "is this a number?", catching "not found" to mean
"create it").

**Cost:** a sentinel gets used as a real value (`-1` as an index or a percentage, `""` saved as a
name), and exceptions used for normal paths are slow and hide real errors in the same `catch`.

**Example (Kotlin)**

```kotlin
// Before: callers must remember that -1 means "no discount"
fun discountPercent(code: String): Int = discounts[code] ?: -1
val price = base * (100 - discountPercent(code)) / 100   // an unknown code raises the price by 1%

// After: the type says "might be missing", and the compiler makes callers handle it
fun discountPercent(code: String): Int? = discounts[code]
val price = discountPercent(code)?.let { base * (100 - it) / 100 } ?: base
```

**Overlap:** catching an error and silently dropping it is already P1 in the language rules. Report
it there.

**Raise to P1** when a caller in the diff already treats the sentinel as a real value, like the
example above.

**Don't flag:** platform APIs whose convention is a sentinel (`indexOf` returning `-1`) when the
caller checks for it properly.

### Middle Man / Needless Indirection

**Signal:** a new class whose every method forwards to another object with the same arguments,
adding no validation, mapping, error translation, caching, or policy.

**Cost:** one more file to read, test, and update on every change, with nothing gained.

**Example (Python)**

```python
# Before: a wrapper that adds nothing
class UserHelper:
    def __init__(self, repo):
        self._repo = repo

    def get(self, user_id):
        return self._repo.get(user_id)

    def save(self, user):
        return self._repo.save(user)

# After: call the repository directly, or give the wrapper a real job
# (mapping, caching, authorization checks)
```

**Don't flag (important):** layers the repo's architecture requires, even when they're thin today.
If the conventions say every screen goes through a view model, then a use case, then a repository,
a use case that only delegates is following the rules, not a Middle Man. The same goes for wrappers
that exist to isolate a third-party SDK.

### Dead Code (P5)

**Signal:** added functions, parameters, branches, toggles, or imports that nothing uses; code after
an unconditional `return`; commented-out code.

**Cost:** readers maintain and reason about code that never runs, and it rots and misleads.

**Example (TypeScript)**

```ts
// No caller passes legacyMode, so the first branch never runs
export function formatPrice(cents: number, legacyMode = false): string {
  if (legacyMode) return (cents / 100).toString();
  return currencyFormatter.format(cents / 100);
}
```

**Fix:** delete it. Version control remembers.

**Don't flag:** the public API of a published library, code behind a live feature flag, or test
helpers used by test files outside the diff (check before flagging).
