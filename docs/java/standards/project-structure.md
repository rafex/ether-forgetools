# Java Project Structure Standard

## Goals

- Keep module boundaries explicit.
- Keep code navigable for humans and agents.
- Make tests, linting, and security checks easy to run in CI.

## Baseline Layout

```text
<repo>/
  modules/
    <service-name>/
      src/main/java/<package-base>/...
      src/test/java/<package-base>/...
      src/main/resources/
      src/test/resources/
      pom.xml or build.gradle
  docs/
  scripts/
```

## Rules

1. One service or bounded context per module.
2. Production code only under `src/main`.
3. Tests only under `src/test`.
4. No mixed test and production packages.
5. Keep package names aligned with domain boundaries, not technical layers only.
6. Keep module-level README with run/test/lint commands.
