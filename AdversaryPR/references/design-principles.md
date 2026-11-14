# Design principles: SOLID, DRY, YAGNI

Reference for AdversaryPR's design rule set. The design principle rules (`adversarypr-design-principles.instructions.md`) hold the four gates, the severity rules, and
the volume limits. This file holds what each principle looks like in a diff, what a violation
costs, a before/after example, and when to leave it alone.

Every name in the examples (articles, orders, invoices, exports, notifications) is invented. The
examples show the shape of a problem, not any real codebase. They rotate through the supported
languages, but the signals apply to all of them.

## Contents

- [SRP: Single Responsibility](#srp-single-responsibility)
- [OCP: Open/Closed](#ocp-openclosed)
- [LSP: Liskov Substitution](#lsp-liskov-substitution)
- [ISP: Interface Segregation](#isp-interface-segregation)
- [DIP: Dependency Inversion](#dip-dependency-inversion)
- [DRY: Don't Repeat Yourself](#dry-dont-repeat-yourself)
- [YAGNI: You Aren't Gonna Need It](#yagni-you-arent-gonna-need-it)
- [When principles pull against each other](#when-principles-pull-against-each-other)
- [Writing the comment](#writing-the-comment)

---

## SRP: Single Responsibility

**The idea:** a unit should have one reason to change, meaning one concern (or one group of
people) that would ask for changes to it. It is not about size. A 200-line parser can have one
responsibility, and a 30-line class can have three.

SRP is the S in SOLID. It gets the most detail here because it is the design issue reviewers
run into most, at both the class level and the function level.

**Look for, in added or changed lines:**
- A class gaining a collaborator from an unrelated area, such as a screen model that now takes an
  HTTP client, a decoder, a file cache, and a mailer.
- A description that needs "and": it fetches *and* formats *and* caches.
- A function that mixes levels: it validates input, applies business rules, writes storage, and
  sends a message in one body.
- `Manager`, `Helper`, `Util`, `Service`, or `Handler` types absorbing methods that don't use each
  other's state.
- A constructor with six or more dependencies. That's a smell worth checking, not a finding by
  itself.

**Cost:** unrelated changes collide in one file, a formatting tweak can break caching, and tests
have to build the whole world to check one rule.

**Example: class level (Swift)**

```swift
// Before: the screen model fetches, decodes, caches, and formats
final class ArticleListViewModel: ObservableObject {
    @Published private(set) var rows: [String] = []
    private let session: URLSession
    private let cacheFile: URL

    func load() async throws {
        let (data, _) = try await session.data(from: ArticleAPI.listURL)
        let articles = try JSONDecoder().decode([ArticleDTO].self, from: data)
        try data.write(to: cacheFile)
        rows = articles.map { "\($0.title) · \(Self.shortDate.string(from: $0.publishedAt))" }
    }
}
```

```swift
// After: the view model turns domain data into screen state; everything else has its own home
final class ArticleListViewModel: ObservableObject {
    @Published private(set) var rows: [ArticleRow] = []
    private let fetchArticles: FetchArticlesUseCase   // network, decoding, and caching live behind this
    private let formatter: ArticleRowFormatter

    func load() async throws {
        rows = try await fetchArticles.execute().map(formatter.row(for:))
    }
}
```

**Example: function level (Python)**

```python
# Before: validation, pricing, persistence, and email in one body
def place_order(request):
    if not request.items:
        raise EmptyCartError()
    total_cents = sum(item.price_cents * item.quantity for item in request.items)
    order_id = db.insert("orders", user_id=request.user_id, total_cents=total_cents)
    smtp.send(to=request.email, body=render_receipt(order_id, total_cents))
    return order_id
```

```python
# After: the function reads as the steps of the use case, and each step has one owner
def place_order(request, pricing, orders, notifier):
    cart = Cart.from_request(request)          # raises EmptyCartError
    order = orders.create(request.user_id, pricing.total_for(cart))
    notifier.order_placed(order)
    return order.id
```

**Don't flag:**
- A long function that does one thing in clear steps.
- A composition root, DI module, or factory. Knowing about everything is its one job.
- A small type with many methods that all serve the same concern.

---

## OCP: Open/Closed

**The idea:** adding a new variant should mean adding code, not editing working code in several
places.

**Look for:**
- The diff adds a case to a `switch` / `when` / `if-else` chain on a type or kind, and the same
  chain exists elsewhere (the diff touches two or more of them, or you can see others).
- A `default` / `else` branch that will silently swallow the next new case.
- A function that grows one more mode or flag parameter for each new caller.

**Cost:** every new variant turns into a hunt through the codebase, and the one switch that gets
missed fails quietly through its `default`.

**Example (TypeScript)**

```ts
// Before: adding "xlsx" means editing three switches, and a missed one falls into `default`
function mimeType(format: ExportFormat): string {
  switch (format) {
    case "csv": return "text/csv";
    case "pdf": return "application/pdf";
    default: return "application/octet-stream";
  }
}
function fileExtension(format: ExportFormat): string { /* the same switch again */ }
function render(format: ExportFormat, report: Report): Uint8Array { /* and again */ }
```

```ts
// After: one object per format; the Record type makes a missing format a compile error
interface Exporter {
  readonly mimeType: string;
  readonly fileExtension: string;
  render(report: Report): Uint8Array;
}

const exporters: Record<ExportFormat, Exporter> = {
  csv: csvExporter,
  pdf: pdfExporter,
};
```

**Suggest the cheapest fix first.** Often the right comment is just "make this switch exhaustive
and drop the `default`" (a Swift `enum`, a Kotlin `sealed` type with `when` as an expression, a
Java `switch` expression, or a TypeScript `never` check), so the compiler lists every place that
needs updating:

```ts
default: {
  const unhandled: never = format;   // compile error here when a new format is added
  throw new Error(`Unhandled export format: ${unhandled}`);
}
```

**Don't flag:** a single switch over a small, stable set (HTTP methods, days of the week). Don't
push a plugin system onto two variants; that's a YAGNI problem of its own.

---

## LSP: Liskov Substitution

**The idea:** a subtype has to work anywhere its base type is expected, without the caller
checking which one it got.

**Look for:**
- An override that throws `UnsupportedOperationException`, `NotImplementedError`, `fatalError()`,
  or `TODO()`, or that returns a placeholder value.
- An override that silently does nothing where the base type promises an effect (a `save()` that
  saves nothing).
- An override that rejects inputs the base accepts, or returns `null` or empty where the base never
  does.
- Callers adding `is` / `instanceof` / `as?` checks to special-case one subtype.

**Cost:** code written against the base type crashes or misbehaves when handed the new subtype,
and the failure shows up far from the cause, often on a path no test covers.

**Example (Kotlin)**

```kotlin
// Before: GiftCard is a PaymentMethod that can't keep the PaymentMethod contract
abstract class PaymentMethod {
    abstract fun charge(amount: Money): Receipt
    abstract fun refund(receipt: Receipt): Refund
}

class GiftCard(private val balance: Balance) : PaymentMethod() {
    override fun charge(amount: Money) = balance.debit(amount)
    override fun refund(receipt: Receipt): Refund =
        throw UnsupportedOperationException("Gift cards can't be refunded")
}

// Elsewhere, unchanged, and now crashes on the first cancelled gift card order
fun cancel(order: Order) = order.payments.forEach { it.method.refund(it.receipt) }
```

```kotlin
// After: the contract says what can actually happen, so every caller handles it
sealed interface RefundOutcome {
    data class ToOriginalMethod(val refund: Refund) : RefundOutcome
    data class AsStoreCredit(val credit: StoreCredit) : RefundOutcome
}

abstract class PaymentMethod {
    abstract fun charge(amount: Money): Receipt
    abstract fun refund(receipt: Receipt): RefundOutcome
}

class GiftCard(private val balance: Balance) : PaymentMethod() {
    override fun charge(amount: Money) = balance.debit(amount)
    override fun refund(receipt: Receipt) = RefundOutcome.AsStoreCredit(balance.credit(receipt.amount))
}
```

Splitting the capability into its own interface (see ISP) is the other good fix, when callers can
be typed to only the capability they need.

**Severity:** P1 when an existing caller will reach the throwing or no-op override, like `cancel`
above. P3 when nothing reaches it yet.

**Don't flag:** test doubles and fakes, or an operation the base type documents as optional (the
contract itself says it may throw).

---

## ISP: Interface Segregation

**The idea:** a client shouldn't have to depend on methods it doesn't use. Several small,
role-shaped interfaces beat one wide one.

**Look for:**
- The diff adds a requirement to a protocol or interface that most conformers will have to stub.
- A new conformer that fills half the interface with empty bodies, `fatalError()`, or `TODO()`
  (usually an LSP problem too).
- A consumer that takes a wide dependency but calls one method on it, which also makes it harder
  to fake in tests.

**Cost:** every conformer pays for every member, the stubs become landmines, and one change to the
wide interface ripples into everything that touches it.

**Example (Swift)**

```swift
// Before: a read-only store has to pretend it can write, sync, and migrate
protocol DataStore {
    func read(_ key: String) -> Data?
    func write(_ data: Data, for key: String) throws
    func delete(_ key: String) throws
    func sync() async throws
    func migrate(from version: Int) throws
}

struct BundledDefaultsStore: DataStore {
    let defaults: [String: Data]
    func read(_ key: String) -> Data? { defaults[key] }
    func write(_ data: Data, for key: String) throws { fatalError("read-only") }
    func delete(_ key: String) throws { fatalError("read-only") }
    func sync() async throws {}
    func migrate(from version: Int) throws {}
}
```

```swift
// After: small role protocols; each type conforms to what it can do,
// and each consumer asks only for what it uses
protocol ReadableStore { func read(_ key: String) -> Data? }
protocol WritableStore: ReadableStore {
    func write(_ data: Data, for key: String) throws
    func delete(_ key: String) throws
}
protocol SyncingStore { func sync() async throws }

struct BundledDefaultsStore: ReadableStore {
    let defaults: [String: Data]
    func read(_ key: String) -> Data? { defaults[key] }
}

final class SettingsViewModel {
    private let store: ReadableStore
    init(store: ReadableStore) { self.store = store }
}
```

**Go note:** idiomatic Go already works this way. Small interfaces are defined where they are
consumed, and constructors return concrete types. Flag a Go diff that exports a large interface
from the producing package only so that something can mock it.

**Don't flag:** a cohesive interface whose members are always used together (`open` / `read` /
`close`).

---

## DIP: Dependency Inversion

**The idea:** business rules shouldn't depend on details like a particular database, HTTP client,
SDK, or the system clock. The rule depends on an abstraction it owns, and the detail gets passed
in.

**Look for:**
- Business logic building its own infrastructure, such as `PostgresClient(...)`, `URLSession.shared`,
  `HttpClient.newHttpClient()`, `requests.get(...)`, or a vendor SDK singleton, inside a service or
  use case.
- Service locator lookups inside logic: `Container.resolve(...)`, `ServiceLocator.get(...)`.
- Hidden non-determinism inside rules that tests need to control: `Date()`, `datetime.now()`,
  `System.currentTimeMillis()`, `UUID()`, `random()`.
- A domain or core module importing a framework, ORM, or vendor SDK type.

**Cost:** the rule can't be tested without the real database or network, a vendor swap becomes a
rewrite, and a change to a vendor type ripples into business code.

**Example (Python)**

```python
# Before: the late fee rule opens its own database connection and reads the clock itself
class LateFeeCalculator:
    def fee_for(self, invoice_id: str) -> int:
        invoice = PostgresInvoiceTable(os.environ["DB_URL"]).get(invoice_id)
        days_late = (datetime.now(timezone.utc).date() - invoice.due_date).days
        return max(0, days_late) * DAILY_LATE_FEE_CENTS
```

```python
# After: the rule states what it needs, and the caller decides where it comes from
class InvoiceSource(Protocol):
    def get(self, invoice_id: str) -> Invoice: ...

class LateFeeCalculator:
    def __init__(self, invoices: InvoiceSource, today: Callable[[], date]):
        self._invoices = invoices
        self._today = today

    def fee_for(self, invoice_id: str) -> int:
        invoice = self._invoices.get(invoice_id)
        days_late = (self._today() - invoice.due_date).days
        return max(0, days_late) * DAILY_LATE_FEE_CENTS
```

Tests pass an in-memory `InvoiceSource` and a fixed date. The composition root passes the real
table and a real clock.

**Don't flag:** value types, pure functions, and standard library helpers. Don't flag the
composition root, app startup, or DI module, since constructing concrete things is their job.
Don't flag shared instances the repo's conventions sanction (check CLAUDE.md / AGENTS.md).

---

## DRY: Don't Repeat Yourself

**The idea:** every piece of *knowledge* (a business rule, a calculation, a validation, a
mapping) has one authoritative home. DRY is about knowledge, not text. Two blocks that look alike
but encode different rules are not duplication. One rule written two different ways is.

**Look for:**
- A block copied from elsewhere in the diff or the codebase with small edits.
- The same rule (eligibility, pricing, rounding, a regex, a status-to-label mapping) implemented in
  two places or two layers.
- The same literal (a limit, a URL path, a storage key) defined in several files.
- Parallel `switch` statements mapping the same enum to related things (see OCP).

**Rule of three:** a second copy is a warning and a third is a finding. Flag the second copy
right away when it's a business or security rule, or when the copies already differ. Copies that
differ are P1, because the system now gives two answers to one question.

**Example (Java)**

```java
// Existing, in SignUpService
if (password.length() < 12 || !password.matches(".*\\d.*")) {
    throw new WeakPasswordException();
}

// Added in this PR, in ChangePasswordService: a copy that has already drifted
if (password.length() < 8 || !password.matches(".*\\d.*")) {
    throw new WeakPasswordException();
}
```

This one is P1, not P3: a user can now change to a password that sign-up would have rejected.

```java
// After: one policy, used by both services
public final class PasswordPolicy {
    private static final int MIN_LENGTH = 12;
    private static final Pattern HAS_DIGIT = Pattern.compile(".*\\d.*");

    private PasswordPolicy() {}

    public static void requireStrong(String password) {
        if (password.length() < MIN_LENGTH || !HAS_DIGIT.matcher(password).matches()) {
            throw new WeakPasswordException();
        }
    }
}
```

**Don't flag:**
- Incidental similarity, such as two DTOs with the same fields that belong to different APIs, or
  two screens whose layout code is going to diverge.
- Repetition in tests. Tests should read top to bottom ("DAMP over DRY"). Flag only when repeated
  setup hides what the test checks, or a copied fixture has drifted.
- Small duplication across modules or services that must release independently, where sharing
  would couple them. Mention it as a judgment call at most.
- Cases where the shared version would need a flag parameter to handle the differences. That's
  worse than the duplication.

---

## YAGNI: You Aren't Gonna Need It

**The idea:** build what the current requirement needs. Speculative flexibility costs something now
(code to read, test, and keep working) for a benefit that usually doesn't arrive, and when it does,
it rarely has the shape that was guessed.

**Look for:**
- An interface plus factory plus registry for exactly one implementation, with no test seam or
  module boundary to justify it.
- Generic parameters, options, hooks, or config keys that no caller uses.
- Parameters that every call site passes the same value for.
- "For later" enum cases, stubs that throw "not implemented", and unused fields on new types.
- Caching, pooling, batching, or concurrency added with no measured problem, especially when it
  adds a staleness or race risk.
- Code paths for requirements that aren't in the ticket.

**Cost:** every speculative branch is untested surface area, it misleads readers about what's
supported, and it makes the real next change harder because that change has to fit the guessed
shape.

**Example (Kotlin)**

```kotlin
// Before: a pluggable pipeline for one channel; three of the four types fail at runtime
interface NotificationChannel { fun send(message: Message) }

class NotificationChannelFactory(
    private val registry: Map<ChannelType, () -> NotificationChannel>,
) {
    fun create(type: ChannelType, options: ChannelOptions = ChannelOptions()): NotificationChannel =
        registry[type]?.invoke() ?: throw NotImplementedError("$type not supported yet")
}

enum class ChannelType { EMAIL, SMS, PUSH, FAX }   // only EMAIL has an implementation
data class ChannelOptions(val retries: Int = 0, val priority: Int = 0, val batch: Boolean = false)   // no caller sets these
```

```kotlin
// After: what the ticket asked for
class EmailNotifier(private val mailer: Mailer) {
    fun send(message: Message) = mailer.send(message.toEmail())
}
```

Keep an interface when it's the test seam or crosses a module boundary. Add SMS when SMS is a
requirement. It will be quick then, and it will fit the real need.

**Don't flag:** extension points the ticket or its epic requires, public versioned APIs and SDKs
where later breaking changes are expensive, or an interface that exists as a test seam.

---

## When principles pull against each other

| Tension | How to resolve it in review |
|---|---|
| DRY vs YAGNI | Don't push a shared abstraction at the second copy unless it's the same business rule or the copies already differ. Otherwise wait for the third. |
| OCP vs YAGNI | Suggest an extension point only when the diff itself adds a variant or the same switch is already repeated. Offer the cheapest fix first: an exhaustive switch the compiler checks. |
| SRP vs cohesion | Splitting a small, cohesive type into many tiny ones makes a change touch more files, not fewer. SRP is about reasons to change, not size. |
| DIP vs simplicity | Invert dependencies that cross a boundary: network, disk, database, clock, randomness, third-party SDKs. Don't wrap pure logic, value types, or standard library helpers. |
| DRY vs decoupling | Two services or modules that deploy on their own may deliberately duplicate a small mapping. That's a judgment call, not a defect. |

---

## Writing the comment

Design comments get ignored when they read like a textbook. Compare these.

**Weak:**

> This class violates the Single Responsibility Principle. Consider refactoring.

It names a rule, gives no cost, and offers no fix. The author can't act on it and has no reason to
want to.

**Strong:**

> **SRP: `ReportService` now also sends email**
>
> `ReportService.generate()` now builds the report and also formats and sends the email. Should the
> sending live in its own class?
>
> The next change to the email words or delivery means editing and re-testing report code. And you
> can't test the new send call without a mail server.
>
> Please take a look at the suggested fix below, unless this was intentional.
>
> ```java
> Report report = build(request);
> reportMailer.send(report);   // new ReportMailer takes the finished Report
> return report;
> ```
>
> `ReportService` stays simple, and its current tests keep working.

**Strong, labeled as a judgment call:**

> **YAGNI: `ExporterFactory` for a single exporter**
>
> Judgment call: `ExporterFactory` and its registry add three types for the one CSV exporter this
> ticket needs. Is a second format coming soon?
>
> Today, every reader has to trace through the factory. The good part is a ready slot if a second
> format lands.
>
> Please take a look at the suggested fix below, unless this was intentional.
>
> ```java
> new CsvExporter().export(orders, out);
> ```
>
> If PDF export is already planned in this epic, keep the factory and resolve this thread.
