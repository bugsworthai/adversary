# CLAUDE.md (excerpt, repo conventions)

## Architecture
- Every feature follows View → ViewModel → UseCase → Repository protocol → concrete Repository.
- UseCases may be thin pass-throughs to a repository today. Do not collapse layers, even when a
  UseCase only delegates; the layer is where business rules land later and it is the mocking seam
  for ViewModel tests.
- ViewModels receive dependencies through their initializer.

## Composition
- `AppEnvironment.shared` is the sanctioned app-wide container. Only composition roots
  (`*Composition.swift`) may read it; feature code must never touch it.

## Testing
- Each test sets up its own objects inline (Arrange / Act / Assert). Do not introduce shared
  mutable fixtures or `setUp` state across tests.
- Formatters used by ViewModels are protocols so tests can inject a stub.
