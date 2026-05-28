# Java Dependency Policy

## Principles

- Minimize dependency count.
- Pin versions explicitly.
- Upgrade with changelog review and tests.

## Rules

1. No new dependency without concrete use case.
2. Prefer standard library and existing project utilities first.
3. Block known vulnerable versions.
4. Avoid overlapping libraries that solve the same problem.
5. Track dependency ownership per module.

## Upgrade Workflow

1. Inspect current dependency graph.
2. Select minimal upgrade set.
3. Run unit, integration, lint, and security checks.
4. Document behavioral impact and rollback strategy.
