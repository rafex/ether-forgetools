# ether-forgetools

> Python toolkit of structured scripts for code agents — smarter wrappers around git, gh, kubectl, maven, grep, and more.

Every script returns a `ForgeResult` JSON object with `ok`, `data`, `errors`, and `suggestion` — no raw shell output to parse.

## Install

```bash
pip install -e .
```

## Usage

**As unified CLI:**
```bash
forge git status
forge search grep --pattern "TODO" --path ./src
forge k8s pods --namespace production
forge java maven --goal "clean test" --module api
forge diag health
```

**As Python module:**
```bash
python -m forgetools.git.status
python -m forgetools.search.grep --pattern "TODO" --path ./src --context 3
```

**As Python import:**
```python
from forgetools.git import status
result = status.run(cwd="/path/to/repo")
if result.ok:
    print(result.data["branch"])
```

## Output format

```json
{
  "ok": true,
  "tool": "git.status",
  "data": { "branch": "main", "is_clean": false, "staged": [...] },
  "errors": [],
  "duration_ms": 12
}
```

## Categories

| Category | Scripts |
|---|---|
| `git` | status, log, diff, branch, blame, stash, conflicts |
| `gh` | pr-list, pr-create, pr-review, issue-list, actions |
| `k8s` | pods, logs, rollout, contexts |
| `search` | grep, find-files, replace, todo |
| `edit` | insert, replace-lines, bulk-rename |
| `java` | maven, gradle, stacktrace, test-report |
| `fs` | tree, read |
| `diag` | health, env, port |
| `net` | http, health |
| `docs` | changelog |

See [AGENTS.md](AGENTS.md) for full agent usage guide.
