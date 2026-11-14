---
applyTo: "**/*.py"
description: AdversaryPR — Python backend review rules
---

# Python backend review rules

## P1 — Bugs

- Mutable default argument — `def f(x=[])` — the default is shared across every call.
- `except Exception:` or a bare `except:` that swallows the error silently.
- A database query inside a loop (N+1) where a batch query exists.
- A missing `await` on an async call — the coroutine is created and discarded.

## P2 — Correctness

- Thread-unsafe global state in a WSGI or ASGI app. Use `contextvars` or request-scoped objects.
- `datetime.now()` with no timezone info, stored alongside timezone-aware data.

## P3 — Architecture

- Business logic in a route handler or view. It belongs in a service or use-case layer.
- Direct database access from a route handler. It must go through a repository.
- Secrets in source. Use environment variables or a secrets manager.

## P4 — Test coverage

- A new public service function with no test.
- Error and exception paths with no test.
