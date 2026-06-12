"""Shared helpers to build domain-scoped MCP servers."""
from __future__ import annotations

import functools
import importlib
import inspect
import json
from typing import Iterable

from fastmcp import FastMCP

from forgetools._forge_cli import REGISTRY


DESCRIPTION_OVERRIDES = {
    "context repo-size": "Measure repository size, language distribution, and git metadata for context planning",
    "ether catalog": "List Ether ecosystem repositories and their local/remote availability",
    "fs find-by-type": "Find files by semantic type such as code, docs, config, images, or archives",
    "fs head": "Read the first lines of a file or matching files with structured metadata",
    "fs read": "Read a text file with metadata; accepts file, filePath, or path as the file location",
    "fs tail": "Read the last lines of a file or matching files with structured metadata",
    "gh actions-logs": "Fetch and summarize logs for GitHub Actions workflow runs or jobs",
    "gh actions-trigger": "Trigger a GitHub Actions workflow dispatch with structured inputs",
    "gh actions-validate": "Validate GitHub Actions workflow files and CI configuration",
    "gh api-releases": "Query GitHub release metadata through the GitHub API",
    "gh api-repo": "Query GitHub repository metadata through the GitHub API",
    "gh api-search": "Search GitHub repositories, issues, pull requests, or code through the GitHub API",
    "gh branch": "Inspect, create, delete, or protect GitHub branches with structured output",
    "gh issue-create": "Create a GitHub issue with title, body, labels, and assignees",
    "gh issue-view": "View a GitHub issue with comments, labels, assignees, and state",
    "gh pr-diff": "Fetch and summarize the diff for a GitHub pull request",
    "gh pr-merge": "Merge a GitHub pull request using the selected merge strategy",
    "git commit": "Create structured git commits with validation and optional dry-run planning",
    "git multi-repo": "Inspect and coordinate git status across multiple repositories",
    "git worktree-workflow": "Manage parallel git worktree workflows from plan through integration",
    "helm diff": "Compare Helm release changes before install or upgrade",
    "java format": "Format Java source files with google-java-format when available",
    "java jdt": "Inspect Java projects using JDT-style source and symbol analysis helpers",
    "java maven-central": "Query Maven Central for artifact versions, metadata, and checksums",
    "java maven-modules": "Inspect Maven multi-module project structure and module metadata",
    "json query": "Query JSON documents using dotted paths and array indexes",
    "net http": "Execute HTTP requests with structured status, headers, body, and timing data",
    "process inspect": "Inspect a process by PID with command, resource usage, and open-file details",
    "process ports": "List listening or connected network ports with owning process information",
    "process top": "Show top local processes by CPU or memory usage",
    "security eslint": "Run ESLint-oriented security checks and return structured findings",
    "security owasp": "Run OWASP dependency checks and parse security findings",
    "security spotbugs": "Run SpotBugs security analysis and parse structured findings",
    "specnative context": "Read, write, or list SpecNative context documents for the current repository",
    "specnative initiative": "Create or update SpecNative initiatives from repository context",
    "specnative project": "Health-check, suggest, snapshot, and safely refine SpecNative project documents",
    "specnative session": "Resume, checkpoint, or clear SpecNative multi-agent session state",
    "specnative status": "Report SpecNative specs, initiatives, states, and task progress",
    "specnative templates": "List or apply SpecNative archetypes, spec templates, and decision snippets",
    "template scaffold": "Generate files from a named template and variable map",
    "test coverage-report": "Parse coverage reports and return summary metrics and uncovered files",
}


def _wrap(fn):
    """Return dict instead of ForgeResult, preserve signature for schema gen."""
    @functools.wraps(fn)
    def wrapped(**kwargs):
        result = fn(**kwargs)
        return result.to_dict()
    wrapped.__signature__ = inspect.signature(fn)
    return wrapped


def _tool_description(key: str, module_path: str) -> str:
    """Build a stable MCP description for a forgetools tool."""
    if key in DESCRIPTION_OVERRIDES:
        return DESCRIPTION_OVERRIDES[key]

    try:
        mod = importlib.import_module(module_path)
    except Exception:
        mod = None

    if mod is not None:
        run_doc = inspect.getdoc(getattr(mod, "run", None)) or ""
        if run_doc:
            return run_doc.splitlines()[0].strip()

        module_doc = inspect.getdoc(mod) or ""
        if module_doc:
            first_line = module_doc.splitlines()[0].strip()
            if "-" in first_line:
                _, _, first_line = first_line.partition("-")
                first_line = first_line.strip()
            if first_line:
                return first_line.rstrip(".")

    words = key.replace("-", " ").split()
    if not words:
        return "Run a forgetools command"

    category = words[0]
    action = " ".join(words[1:]) or "command"
    return f"Run the {category} {action} forgetools command"


def _domain_registry(categories: Iterable[str]) -> dict[str, str]:
    allowed = set(categories)
    return {k: v for k, v in REGISTRY.items() if k.split(" ", 1)[0] in allowed}


def build_domain_server(name: str, categories: Iterable[str]) -> FastMCP:
    """Create a FastMCP server that only exposes tools for given categories."""
    server = FastMCP(name)
    category_list = tuple(categories)
    domain_registry = _domain_registry(category_list)

    for key, module_path in domain_registry.items():
        mod = importlib.import_module(module_path)
        run = getattr(mod, "run")
        tool_name = key.replace(" ", "_").replace("-", "_")
        description = _tool_description(key, module_path)
        wrapped = _wrap(run)
        wrapped.__doc__ = description
        server.tool(name=tool_name, description=description)(wrapped)

    @server.resource("forge://catalog")
    def resource_catalog() -> str:
        """List tools available in this domain server."""
        lines = [
            f"# {name} Catalog",
            f"Total tools: {len(domain_registry)}",
        ]
        current_cat = None
        for key, module_path in domain_registry.items():
            category = key.split(" ", 1)[0]
            if category != current_cat:
                lines.append(f"\n## {category.upper()}")
                current_cat = category
            tool_name = key.replace(" ", "_").replace("-", "_")
            lines.append(f"\n### `{tool_name}`")
            lines.append(f"- forge key: `forge {key}`")
            lines.append(f"- description: {_tool_description(key, module_path)}")
        return "\n".join(lines)

    @server.resource("forge://capabilities")
    def resource_capabilities() -> str:
        """Machine-readable capabilities manifest for this domain server."""
        tools = [
            {
                "name": key.replace(" ", "_").replace("-", "_"),
                "forge_key": f"forge {key}",
                "category": key.split(" ", 1)[0],
                "description": _tool_description(key, module_path),
            }
            for key, module_path in domain_registry.items()
        ]
        return json.dumps(
            {
                "name": name,
                "version": "0.1.0",
                "categories": list(category_list),
                "tools": tools,
                "resources": ["forge://catalog", "forge://capabilities"],
            },
            indent=2,
        )

    return server
