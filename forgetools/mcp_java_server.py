"""Domain MCP server for Java build, quality, and best-practice guidance."""
from __future__ import annotations

from pathlib import Path

from forgetools.mcp_domain_server import build_domain_server
from forgetools.mcp_domain_extras import register_domain_prompts, register_domain_resources

server = build_domain_server("forgetools-java", ("java",))
register_domain_resources(server, "java")
register_domain_prompts(server, "java")


def _read_doc(relative_path: str) -> str:
    path = Path(__file__).resolve().parent.parent / relative_path
    return path.read_text(encoding="utf-8")


@server.resource("forge://java/standards/project-structure")
def java_project_structure() -> str:
    """Java project layout and module structure standards."""
    return _read_doc("docs/java/standards/project-structure.md")


@server.resource("forge://java/standards/testing-strategy")
def java_testing_strategy() -> str:
    """Java testing strategy, levels, and quality gates."""
    return _read_doc("docs/java/standards/testing-strategy.md")


@server.resource("forge://java/standards/dependency-policy")
def java_dependency_policy() -> str:
    """Java dependency and version upgrade policy."""
    return _read_doc("docs/java/standards/dependency-policy.md")


@server.prompt()
def java_new_service_scaffold(service_name: str, package_base: str) -> str:
    """Scaffold a new Java service following local standards."""
    return f"""\
# Java Service Scaffold

Create a new Java service named `{service_name}` under package base `{package_base}`.

Use these standards first:
- forge://java/standards/project-structure
- forge://java/standards/testing-strategy
- forge://java/standards/dependency-policy

Then execute this workflow:
1. Propose module/package layout.
2. Add minimal production code and unit tests.
3. Run java_maven(goal="test") or java_gradle(task="test").
4. Run lint_checkstyle and security_spotbugs.
5. Summarize quality gate results and next fixes.
"""


@server.prompt()
def java_code_review_strict(scope: str) -> str:
    """Run a strict Java code review workflow for a target scope."""
    return f"""\
# Strict Java Review

Review scope: `{scope}`

Checklist:
1. API/behavior regressions.
2. Null-safety and error handling.
3. Test quality and coverage gaps.
4. Dependency risks.
5. Style and static-analysis violations.

Suggested tool sequence:
- java_maven(goal="test")
- test_junit_report(path="<report-path>")
- lint_checkstyle(path="<checkstyle-report>")
- security_spotbugs(path="<spotbugs-report>")
"""


def main() -> None:
    server.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
