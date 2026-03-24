"""forge — unified CLI entry point for forgetools."""
from __future__ import annotations

import argparse
import importlib
import json
import sys


REGISTRY: dict[str, str] = {
    # git
    "git status":          "forgetools.git.status",
    "git log":             "forgetools.git.log",
    "git diff":            "forgetools.git.diff",
    "git branch":          "forgetools.git.branch",
    "git blame":           "forgetools.git.blame",
    "git stash":           "forgetools.git.stash",
    "git conflicts":       "forgetools.git.conflicts",
    # gh
    "gh pr-list":          "forgetools.gh.pr_list",
    "gh pr-create":        "forgetools.gh.pr_create",
    "gh pr-review":        "forgetools.gh.pr_review",
    "gh issue-list":       "forgetools.gh.issue_list",
    "gh actions":          "forgetools.gh.actions",
    # k8s
    "k8s pods":            "forgetools.k8s.pods",
    "k8s logs":            "forgetools.k8s.logs",
    "k8s rollout":         "forgetools.k8s.rollout",
    "k8s contexts":        "forgetools.k8s.contexts",
    # search
    "search grep":         "forgetools.search.grep",
    "search find-files":   "forgetools.search.find_files",
    "search replace":      "forgetools.search.search_replace",
    "search todo":         "forgetools.search.todo",
    # edit
    "edit insert":         "forgetools.edit.insert",
    "edit replace-lines":  "forgetools.edit.replace_lines",
    "edit bulk-rename":    "forgetools.edit.bulk_rename",
    # java
    "java maven":          "forgetools.java.maven",
    "java gradle":         "forgetools.java.gradle",
    "java stacktrace":     "forgetools.java.parse_stacktrace",
    "java test-report":    "forgetools.java.test_report",
    # fs
    "fs tree":             "forgetools.fs.tree",
    "fs read":             "forgetools.fs.read",
    # diag
    "diag health":         "forgetools.diag.health",
    "diag env":            "forgetools.diag.env_validate",
    "diag port":           "forgetools.diag.port_check",
    # net
    "net http":            "forgetools.net.http_request",
    "net health":          "forgetools.net.health_check",
    # docs
    "docs changelog":      "forgetools.docs.changelog",
    # shell
    "shell run":           "forgetools.shell.run",
    # test
    "test junit-report":   "forgetools.test.junit_report",
    "test coverage":       "forgetools.test.coverage",
    # lint
    "lint checkstyle":     "forgetools.lint.checkstyle",
    "lint eslint":         "forgetools.lint.eslint",
    "lint pylint":         "forgetools.lint.pylint",
    "lint golangci":       "forgetools.lint.golangci",
    # docker
    "docker ps":           "forgetools.docker.ps",
    "docker build":        "forgetools.docker.build",
    "docker logs":         "forgetools.docker.logs",
    "docker inspect":      "forgetools.docker.inspect",
    "docker exec":         "forgetools.docker.exec",
    # npm
    "npm run":             "forgetools.npm.run",
    "npm install":         "forgetools.npm.install",
    "npm audit":           "forgetools.npm.audit",
    # go
    "go build":            "forgetools.go.build",
    "go test":             "forgetools.go.test",
    "go mod":              "forgetools.go.mod",
    # cargo
    "cargo build":         "forgetools.cargo.build",
    "cargo test":          "forgetools.cargo.test",
    "cargo check":         "forgetools.cargo.check",
    # git additions
    "git pr-workflow":     "forgetools.git.pr_workflow",
    # fs additions
    "fs diff":             "forgetools.fs.diff",
    # secrets
    "secrets scan":        "forgetools.secrets.scan",
    # process
    "process ps":          "forgetools.process.ps",
    "process kill":        "forgetools.process.kill",
    "process port":        "forgetools.process.port",
    # template
    "template scaffold":   "forgetools.template.scaffold",
    # openapi parsing
    "openapi parse":       "forgetools.openapi.parse",
    # context
    "context summarize":   "forgetools.context.summarize",
    # git additions
    "git submodule-status":  "forgetools.git.submodule_status",
    "git submodule-sync":    "forgetools.git.submodule_sync",
    "git tag":               "forgetools.git.tag",
    "git cherry-pick":       "forgetools.git.cherry_pick",
    # db
    "db query":              "forgetools.db.query",
    "db schema":             "forgetools.db.schema",
    "db migrations":         "forgetools.db.migrations",
    # docker additions
    "docker compose":        "forgetools.docker.compose",
    # gh additions
    "gh release":            "forgetools.gh.release",
    # helm
    "helm status":           "forgetools.helm.status",
    "helm install":          "forgetools.helm.install",
    "helm upgrade":          "forgetools.helm.upgrade",
    "helm diff":             "forgetools.helm.diff",
    # make
    "make run":              "forgetools.make.run",
    # json
    "json query":            "forgetools.json.query",
    # fs additions
    "fs checksum":           "forgetools.fs.checksum",
    # context additions
    "context diff-summary":  "forgetools.context.diff_summary",
    "context repo-size":     "forgetools.context.repo_size",
    # config
    "config validate":       "forgetools.config.validate",
    # git worktree
    "git worktree":          "forgetools.git.worktree",
    # text
    "text audit-chars":      "forgetools.text.audit_chars",
}


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help", "help"):
        _print_help()
        return

    category = sys.argv[1]
    command = sys.argv[2]
    key = f"{category} {command}"

    if key not in REGISTRY:
        print(json.dumps({"ok": False, "tool": key, "errors": [f"Unknown command: forge {key}"], "suggestion": "Run 'forge help' to list available commands"}), flush=True)
        sys.exit(1)

    module_path = REGISTRY[key]
    # Rewrite argv so the submodule's argparse sees only its own args
    sys.argv = [f"forge {key}"] + sys.argv[3:]

    try:
        mod = importlib.import_module(module_path)
        mod.run  # ensure it has run()
        # Run the module as __main__ equivalent
        import runpy
        runpy.run_module(module_path, run_name="__main__", alter_sys=True)
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"ok": False, "tool": key, "errors": [str(e)]}))
        sys.exit(1)


def _print_help() -> None:
    lines = ["forge — forgetools unified CLI\n", "Usage: forge <category> <command> [options]\n", "Available commands:"]
    current_cat = None
    for key in REGISTRY:
        cat, cmd = key.split(" ", 1)
        if cat != current_cat:
            lines.append(f"\n  {cat}")
            current_cat = cat
        lines.append(f"    forge {key}")
    lines.append("\nRun 'forge <category> <command> --help' for command-specific options.")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
