---
applyTo: "**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: AdversaryPR — TypeScript / JavaScript review rules
---

# TypeScript / JavaScript review rules

## P1 — Bugs

- A Promise returned but not awaited inside an `async` function.
- An unhandled Promise rejection — no `.catch()` and no surrounding `try/catch`.
- `==` used instead of `===` for equality.

## P2 — Type safety

- `any` used where a proper type already exists or can be inferred.
- A non-null assertion (`!`) on a value that can legitimately be `null` or `undefined`.

## P3 — Architecture

- An API call made directly from a UI component. It must go through a service or hook layer.
- Hardcoded API base URLs or secrets in source.

## P4 — Test coverage

- A new exported function or hook with no test.
- Error and rejection paths with no test.
