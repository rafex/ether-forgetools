"""forge — unified CLI entry point for forgetools."""
from __future__ import annotations

import argparse
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
    "git operations":      "forgetools.git.operations",
    # gh — no token required (public repos via GitHub REST API)
    "gh api-repo":         "forgetools.gh.api_repo",
    "gh api-releases":     "forgetools.gh.api_releases",
    "gh api-search":       "forgetools.gh.api_search",
    # gh — requires gh CLI + auth
    "gh pr-list":          "forgetools.gh.pr_list",
    "gh pr-create":        "forgetools.gh.pr_create",
    "gh pr-review":        "forgetools.gh.pr_review",
    "gh pr-merge":         "forgetools.gh.pr_merge",
    "gh pr-diff":          "forgetools.gh.pr_diff",
    "gh issue-list":       "forgetools.gh.issue_list",
    "gh issue-create":     "forgetools.gh.issue_create",
    "gh issue-view":       "forgetools.gh.issue_view",
    "gh actions":          "forgetools.gh.actions",
    "gh actions-validate": "forgetools.gh.actions_validate",
    "gh actions-trigger":  "forgetools.gh.actions_trigger",
    "gh actions-logs":     "forgetools.gh.actions_logs",
    "gh branch":           "forgetools.gh.branch",
    "gh repo-status":      "forgetools.gh.repo_status",
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
    "java maven-modules":  "forgetools.java.maven_modules",
    "java maven-central":  "forgetools.java.maven_central",
    "java gradle":         "forgetools.java.gradle",
    "java stacktrace":     "forgetools.java.parse_stacktrace",
    "java test-report":    "forgetools.java.test_report",
    "java format":         "forgetools.java.format",
    "java jdt":            "forgetools.java.jdt",
    # fs
    "fs tree":             "forgetools.fs.tree",
    "fs read":             "forgetools.fs.read",
    "fs find-by-type":     "forgetools.fs.find_by_type",
    "fs head":             "forgetools.fs.head",
    "fs tail":             "forgetools.fs.tail",
    "fs disk-usage":       "forgetools.fs.disk_usage",
    "fs operations":       "forgetools.fs.operations",
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
    # linux host operations
    "linux system":        "forgetools.linux.system",
    "linux storage":       "forgetools.linux.storage",
    "linux logs":          "forgetools.linux.logs",
    "linux services":      "forgetools.linux.services",
    "linux network":       "forgetools.linux.network",
    "linux privilege":     "forgetools.linux.privilege",
    # test
    "test junit-report":   "forgetools.test.junit_report",
    "test coverage":         "forgetools.test.coverage",
    "test coverage-report":  "forgetools.test.coverage_report",
    # security
    "security owasp":         "forgetools.security.owasp",
    "security spotbugs":      "forgetools.security.spotbugs",
    "security eslint":        "forgetools.security.eslint_security",
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
    "process inspect":     "forgetools.process.inspect",
    "process ports":       "forgetools.process.ports",
    "process top":         "forgetools.process.top",
    # template
    "template scaffold":   "forgetools.template.scaffold",
    # openapi parsing
    "openapi parse":       "forgetools.openapi.parse",
    # context
    "context summarize":   "forgetools.context.summarize",
    # git additions
    "git multi-repo":        "forgetools.git.multi_repo",
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
    "config gitignore":      "forgetools.config.gitignore",
    # git worktree
    "git worktree":           "forgetools.git.worktree",
    "git worktree-workflow":  "forgetools.git.worktree_workflow",
    "git worktree-merge-plan": "forgetools.git.worktree_merge_plan",
    "git commit":             "forgetools.git.commit",
    "git commit-plan":        "forgetools.git.commit_plan",
    "git stack-plan":         "forgetools.git.stack_plan",
    "git backport-plan":      "forgetools.git.backport_plan",
    "git preflight":          "forgetools.git.preflight",
    # text
    "text audit-chars":      "forgetools.text.audit_chars",
    # ether ecosystem
    "ether catalog":         "forgetools.ether.catalog",
    # specnative — spec-first development workflow
    "specnative status":     "forgetools.specnative.status",
    "specnative context":    "forgetools.specnative.context",
    "specnative initiative": "forgetools.specnative.initiative",
    "specnative session":    "forgetools.specnative.session",
    "specnative project":    "forgetools.specnative.project",
    "specnative templates":  "forgetools.specnative.templates",
    "specnative board":      "forgetools.specnative.board",
    "specnative backlog":    "forgetools.specnative.backlog",
    "specnative artifacts":  "forgetools.specnative.artifacts",
    # diff — semantic comparisons
    "diff dirs":             "forgetools.diff.dirs",
    "diff json":             "forgetools.diff.json",
    "diff yaml":             "forgetools.diff.yaml",
    # web — webpage content extraction
    "web fetch":             "forgetools.web.fetch",
    # websearch — search engine + browsing workflows
    "websearch ddg-search":  "forgetools.websearch.ddg_search",
    "websearch visit":       "forgetools.websearch.visit",
    # python — uv based Python workflows
    "python uv":             "forgetools.python.uv",
    "python pytest":         "forgetools.python.pytest",
    "python ruff":           "forgetools.python.ruff",
    "python mypy":           "forgetools.python.mypy",
    # frontend — web app diagnostics
    "frontend detect":       "forgetools.frontend.detect",
    "frontend assets":       "forgetools.frontend.assets",
    # office — document conversion/extraction
    "office markdown-html":  "forgetools.office.markdown_html",
    "office pdf-create":     "forgetools.office.pdf_create",
    "office docx-create":    "forgetools.office.docx_create",
    "office table-report":   "forgetools.office.table_report",
    "office pdf-append-tables": "forgetools.office.pdf_append_tables",
    "office pdf-merge":      "forgetools.office.pdf_merge",
    "office pdf-text":       "forgetools.office.pdf_text",
    "office pdf-metadata":   "forgetools.office.pdf_metadata",
    "office pdf-images":     "forgetools.office.pdf_images",
    "office pdf-stamp":      "forgetools.office.pdf_stamp",
    # observability — logs and runtime diagnosis
    "observability log-tail":  "forgetools.observability.log_tail",
    "observability log-parse": "forgetools.observability.log_parse",
    # podman — bastion-safe rootless container workflows
    "podman ps":             "forgetools.podman.ps",
    "podman logs":           "forgetools.podman.logs",
    "podman ports":          "forgetools.podman.ports",
    "podman select-port":    "forgetools.podman.select_port",
    "podman validate-ports": "forgetools.podman.validate_ports",
    # cloud — provider identity/context
    "cloud whoami":          "forgetools.cloud.whoami",
    # ai — local/remote AI tooling
    "ai ollama":             "forgetools.ai.ollama",
    # release — release orchestration
    "release precheck":      "forgetools.release.precheck",
    # deps — dependency metadata research
    "deps pypi":             "forgetools.deps.pypi",
    "deps npm":              "forgetools.deps.npm",
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
