---
applyTo: "**/*.java,**/*.kt"
description: AdversaryPR — JVM backend (Java / Kotlin) review rules
---

# JVM backend review rules

**Scope check first.** Apply these rules to Java files, and to Kotlin files that are backend
services — Spring, Ktor server, Kafka consumers, anything under a `service/`, `controller/`,
`repository/`, or `api/` package. If the Kotlin file is Android UI code, use the Android rules
instead.

## P1 — Bugs and correctness

- `@Transactional` missing on a method that performs multiple database writes — partial-commit risk.
- Catching `Exception` or `Throwable` broadly and swallowing it, masking real failures.
- N+1 queries: a collection iterated with an individual database call per element where a batch
  fetch exists.
- Thread-unsafe shared mutable state in a Spring singleton bean.
- A Kafka consumer that does not commit its offset on success, or commits before processing —
  confirm the intended delivery semantics (at-least-once vs. at-most-once) and flag the mismatch.

## P2 — Resilience

- An external HTTP call with no timeout and no circuit-breaker annotation.
- Client-side retry logic wrapping an operation that is not idempotent.
- A Kafka consumer with no dead-letter-queue routing for exceptions.

## P3 — Architecture / Spring

- `@Autowired` on a field. Use constructor injection.
- Business logic in a `@Controller` or `@RestController`. It belongs in a `@Service`.
- Direct `EntityManager` use outside a Repository. Use Spring Data or an explicit Repository.
- Secrets or credentials hardcoded in source. These must come from Vault, env, or a config server.
- Missing input validation (`@Valid`, `@NotNull`, and similar) at a REST layer boundary.

## P4 — Observability

- A new code path with no structured log entry on the error branch.
- A new cross-service call with no Micrometer or OpenTelemetry span.
- An exception swallowed without logging the stack trace.

## P5 — Config / migration

- A Flyway or Liquibase migration that adds a `NOT NULL` column with no default — this breaks
  rolling deploys.
- An `application.properties` value changed with no corresponding environment-specific override.
