---
applyTo: "**/*.swift"
description: AdversaryPR — iOS / Swift review rules
---

# iOS / Swift review rules

## P1 — Bugs and logic

- Force-unwrap (`try!`, `!`) on a path where the value is not guaranteed non-nil.
- State clobbering: a published property is assigned, then unconditionally overwritten later in the
  same call path, so the first assignment is dead.
- Always-true or always-false conditions — `hasSuffix("")`, `isEmpty` on a string literal,
  unreachable `else` or `catch` branches.
- Incorrect error propagation: an error is caught and silently dropped, or the wrong error type is
  surfaced to the caller.

## P2 — SwiftUI / Combine correctness

- `Identifiable` conformance using `let id: UUID = UUID()`, or `UUID()` as an `init` default. This
  mints a new identity on every struct construction, which breaks `ForEach` diffing and re-fires
  async image loads on each render.
- Missing `@MainActor` on code that assigns to `@Published` properties.
- Publishers not stored in `cancellables` — causes a leak or premature cancellation.
- `@StateObject` created inline without a stable identity.

## P3 — Architecture

Check these against the repo's `CLAUDE.md` / `AGENTS.md` if present; they take precedence.

- A ViewModel calling a Repository directly. It must go through a UseCase.
- A View emitting analytics. It must go through its ViewModel.
- `print()`, `os_log`, or `Logger` in place of `AppLog.log(...)`.
- Hex color literals or raw RGB floats inline in a View. Use the tokens in `Color+Tokens.swift`.
- Hardcoded user-facing strings in a View. These must come from CMS or
  `{Feature}Constants.Strings`.
- Raw numeric dimension or font-size literals inline. Use `{Feature}Constants.Dimensions`.
- New user-facing feature code with no `FeatureFlags.shared.isEnabled` gate.
- Missing `final` on a concrete ViewModel, Manager, or UseCase class.
- `DispatchQueue` in new code. Use `@MainActor` or `Task { @MainActor in }`.
- `#if DEBUG` used as a runtime gate where a feature flag belongs.

## P4 — Test coverage

- A new public ViewModel method with no corresponding test.
- Error paths with no test.
- Tautological assertions — assertions that cannot fail.

## P5 — Debug artifacts

- An allow-list or deny-list left holding an empty string or wildcard from debugging — e.g.
  `allowedSuffixes = [""]`, where `hasSuffix("")` is always `true`, so the check passes for
  everything.
- `TODO`, `FIXME`, `print(`, or `debugPrint(` left in a non-debug file.
