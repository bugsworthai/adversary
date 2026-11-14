---
applyTo: "**/*.yaml,**/*.yml,**/*.json,**/*.properties,**/*.xml"
description: AdversaryPR — configuration file review rules
---

# Configuration file review rules

- **P1** — Secrets, passwords, tokens, or private keys in plaintext.
- **P2** — Environment-specific values placed in a shared or base config file rather than an
  environment override.
- **P2** — A breaking schema change (a field removed or renamed) with no migration path noted in the
  PR description.
- **P3** — A new required key added with no default and no corresponding update to every
  environment's config.

Ignore generated or lock files — `package-lock.json`, `yarn.lock`, `Podfile.lock`, and similar.
