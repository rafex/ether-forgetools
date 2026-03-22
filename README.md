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

---

## MCP — opencode integration

Exposes all forgetools as MCP tools for use with [opencode](https://opencode.ai) or any MCP-compatible agent.

### Install with MCP support

```bash
pip install -e ".[mcp]"
```

### Configure opencode

Add to `~/.config/opencode/config.json`:

```json
{
  "mcp": {
    "forgetools": {
      "type": "local",
      "command": ["forge-mcp"]
    }
  }
}
```

### Available MCP tools (35)

| Category | Tools |
|---|---|
| `git` | `git_status`, `git_log`, `git_diff`, `git_branch`, `git_blame`, `git_stash`, `git_conflicts` |
| `gh` | `gh_pr_list`, `gh_pr_create`, `gh_pr_review`, `gh_issue_list`, `gh_actions` |
| `k8s` | `k8s_pods`, `k8s_logs`, `k8s_rollout`, `k8s_contexts` |
| `search` | `search_grep`, `search_find_files`, `search_replace`, `search_todo` |
| `edit` | `edit_insert`, `edit_replace_lines`, `edit_bulk_rename` |
| `java` | `java_maven`, `java_gradle`, `java_stacktrace`, `java_test_report` |
| `fs` | `fs_tree`, `fs_read` |
| `diag` | `diag_health`, `diag_env`, `diag_port` |
| `net` | `net_http`, `net_health` |
| `docs` | `docs_changelog` |

Every tool returns `{ "ok": bool, "tool": str, "data": ..., "errors": [], "duration_ms": int }`.
