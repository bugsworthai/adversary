---
applyTo: "**/*.go"
description: AdversaryPR — Go backend review rules
---

# Go backend review rules

## P1 — Bugs

- A returned `error` assigned to `_` or otherwise ignored.
- A goroutine launched with no way to stop it — no `context.Context`, no done channel.
- A mutex locked with no `defer` unlock on every return path.
- A loop variable captured by a goroutine closure without being passed as a parameter (pre-Go 1.22
  semantics), producing the same value in every iteration.

## P2 — Correctness and resilience

- `context.Background()` used where a request-scoped context should be propagated.
- An outbound HTTP call with no timeout on the client or context.
- A `defer` inside a loop, so cleanup is deferred to function exit rather than iteration exit.
- An unbuffered channel written to with no reader guaranteed — deadlock risk.

## P3 — Architecture

- Business logic in an HTTP handler. It belongs in a service layer.
- Direct database access from a handler. It must go through a repository.
- Secrets or API keys hardcoded in source.

## P4 — Observability

- A new error branch that returns without wrapping context — use `fmt.Errorf("...: %w", err)`.
- A new cross-service call with no span or structured log entry.
