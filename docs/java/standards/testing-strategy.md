# Java Testing Strategy

## Objectives

- Fast feedback for developers.
- High confidence for refactors.
- Deterministic CI results.

## Test Pyramid

1. Unit tests: primary layer, run on each change.
2. Integration tests: external boundaries (DB, HTTP, messaging).
3. End-to-end tests: critical user flows only.

## Minimum Gates

1. Unit tests must pass.
2. Integration tests for changed boundaries must pass.
3. No flaky tests accepted in main branch.
4. Coverage report required for each PR (trend monitoring).

## Practices

- Use clear arrange-act-assert structure.
- Prefer behavior-focused test names.
- Keep fixtures local and minimal.
- Avoid shared mutable global state.
