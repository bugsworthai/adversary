---
applyTo: "**/*.kt,**/*.kts"
description: AdversaryPR — Android / Kotlin review rules
---

# Android / Kotlin review rules

**Scope check first.** Apply these rules only when the file is Android code — it sits under
`src/main/`, `androidMain/`, or an `app/` module, or it imports from `android.*`, `androidx.*`, or
`kotlinx.coroutines` in a UI context. If the Kotlin file is a JVM backend service (Spring, Ktor
server, Kafka consumer), use the JVM backend rules instead.

## P1 — Bugs and logic

- Context leaks: an `Activity` or `Fragment` context stored in a ViewModel or a singleton.
- `viewModelScope` replaced with `GlobalScope` or a bare `CoroutineScope(Dispatchers.IO)` — this
  survives configuration changes and leaks.
- `collectAsState()` called outside a Composable, or without lifecycle awareness.
- `LiveData` or `StateFlow` observed without a `lifecycleOwner` — the observer fires after the view
  is destroyed.
- Null pointer risk: a platform API that can return null called with no null check.

## P2 — Coroutine / Compose correctness

- `LaunchedEffect` keyed on `Unit` when the data it reads should re-trigger the effect.
- `remember` with no key on a lambda that captures a changing value.
- A `State` object created with `mutableStateOf` inside a non-Composable — it will never trigger
  recomposition.
- `Dispatchers.Main` where `Dispatchers.Main.immediate` is needed, causing jank on the first frame.

## P3 — Architecture

- A ViewModel calling a data-layer class directly. It must go through a Repository or UseCase.
- Hardcoded strings in a Composable. These belong in `strings.xml` or a constants object.
- Hardcoded dimension literals. These belong in `dimens.xml` or a named constant.
- `Log.d` / `Log.e` in production code. Use the project's logging wrapper.
- Missing `@VisibleForTesting` on an internal method that is exposed only for tests.

## P4 — Test coverage

- ViewModel `StateFlow` state transitions with no test.
- Repository error paths with no test.

## P5 — Debug artifacts

- `BuildConfig.DEBUG` used as a runtime gate for a feature. Use a remote flag.
- Hardcoded URLs or API keys in a source file.
