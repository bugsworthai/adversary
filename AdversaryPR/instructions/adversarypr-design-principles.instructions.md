---
applyTo: "**/*.swift,**/*.kt,**/*.kts,**/*.java,**/*.py,**/*.go,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: AdversaryPR — SOLID, DRY, and YAGNI review rules
---

# Design principle review rules

Post a design finding only if all four hold:
1. The diff added it or made it clearly worse. Old debt in untouched code is out of scope.
2. You can name the cost: a change that gets harder, a bug it invites, or a test that can't be written. "Violates X" alone is not a cost.
3. The fix is small and local, or you suggest a follow-up ticket.
4. The repo's conventions (CLAUDE.md, AGENTS.md, CONTRIBUTING.md) don't call for it. Mandated layers and documented singletons are fine.

Default to P3. Use P1 only for a defect you can point to: copies of one rule that already disagree, a subtype that throws or no-ops where callers rely on the base, a getter whose side effect changes results. One finding per principle per file. At most five P3 design findings per PR. Start tradeoffs with "Judgment call:". Lead with the consequence, not the acronym.

## SRP
Flag a class or function that gains a second reason to change: fetch + decode + cache + format in one body, or a new collaborator from an unrelated area.
Example: `OrderService` now also builds and sends the receipt email. Move sending to a `ReceiptMailer`.
Skip long functions that do one thing, and composition roots.

## OCP
Flag a new case added to a switch on a type when the same switch exists elsewhere, or a `default` that will swallow the next case.
Suggest an exhaustive switch with no `default` first. Suggest a lookup table or polymorphism only if the switch repeats.

## LSP
Flag overrides that throw "unsupported", do nothing, or return placeholders, and callers adding `is` / `instanceof` checks for one subtype.
Example: `GiftCard.refund()` throws, but `cancel()` refunds every payment. Make the contract say what can happen, such as a refund-or-store-credit result.

## ISP
Flag interfaces that conformers half-fill with empty bodies, `fatalError()`, or `TODO()`, and consumers that take a wide interface to call one method.
Example: a read-only store forced to implement `write`, `sync`, `migrate`. Split into `ReadableStore` and `WritableStore`.

## DIP
Flag business logic that builds its own database, HTTP, or SDK client, uses a service locator, or reads the clock or random directly.
Example: `LateFeeCalculator` opens a DB connection and calls `now()`. Inject an invoice source and a clock.
Skip composition roots, value types, and repo-sanctioned shared instances.

## DRY
DRY is about knowledge, not text. Flag one business rule, validation, regex, or mapping written in two places. Use the rule of three for other repetition. Copies that already differ are P1.
Example: sign-up requires 12-character passwords, the new change-password copy checks 8. Use one `PasswordPolicy`.
Skip repetition in tests, look-alike code for different rules, and merges that would need a flag parameter.

## YAGNI
Flag an interface plus factory plus registry for one implementation, unused options or generic parameters, "for later" enum cases, stubs that throw "not implemented", and caching or concurrency with no measured need.
Example: a `NotificationChannelFactory` with EMAIL, SMS, PUSH, FAX where only EMAIL works. Ship `EmailNotifier`.
Skip test seams, module boundaries, and extension points the ticket requires.
