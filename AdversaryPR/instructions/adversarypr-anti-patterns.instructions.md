---
applyTo: "**/*.swift,**/*.kt,**/*.kts,**/*.java,**/*.py,**/*.go,**/*.ts,**/*.tsx,**/*.js,**/*.jsx"
description: AdversaryPR — anti-pattern review rules
---

# Anti-pattern review rules

Use the same gates and severity as the design principle rules: only what the diff adds, only with a named cost, default P3. If a language rule already covers it (swallowed errors, hardcoded values, logic in controllers), report it there instead.

| Anti-pattern | Flag when the diff... | Suggest |
|---|---|---|
| God object | adds another unrelated job to a type most changes already touch | put the new part in a new type |
| Arrow code | nests if/loops 4+ levels deep | guard clauses, early returns |
| Flag arguments | adds a boolean that switches behavior: `send(order, true, false)` | two functions or a named options object |
| Data clumps | passes the same values together everywhere: `(lat, lng, radius)` | a small value type |
| Primitive obsession | uses raw strings or ints for IDs and states: `status == "shiped"` | enums and ID wrapper types |
| Magic numbers | leaves unexplained literals in logic: `if attempts > 3` | named constants |
| Money in floats (P1) | stores or sums money as Double, Float, or number | integer cents or a decimal type |
| Feature envy | computes a fact about another object from its fields | move the method to that object |
| Train wreck | chains through internals: `order.customer.account.settings.locale` | ask the nearest object |
| Shotgun surgery | adds one variant by editing many parallel switches | one enum, sealed type, or table |
| Hidden dependencies | reaches for a service locator, static shared instance, or mutable global inside logic | pass it in |
| Leaky abstraction | returns DTOs, ORM entities, or SDK types to UI, or an internal mutable list | map at the boundary, return a copy |
| Circular dependency | makes module A import B while B imports A | move the shared contract down a layer |
| Inheritance for reuse | subclasses only to reuse a helper, or disables inherited methods | composition |
| Temporal coupling | needs `configure()` before `run()`, or adds fields set "later" | constructor parameters |
| Side-effect query | makes a getter, `isX`, or `toString` write state, do I/O, or track analytics | split the query and the command |
| Sentinel returns | returns -1, null, or "" for failure where Optional or Result exists | Optional or Result; P1 if a caller already uses the sentinel as a value |
| Exceptions as flow | uses try/catch for ordinary branching | an explicit check |
| Middle man | adds a class whose every method only forwards | call the target directly |
| Dead code (P5) | adds unused functions, parameters, branches, or commented-out code | delete it |

Never flag: framework-required subclassing, fluent or collection pipelines, mappers reading another type's fields, composition roots, repetition in tests, or thin layers the repo's architecture requires.
