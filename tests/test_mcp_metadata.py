from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_capabilities_exist_for_each_domain() -> None:
    domains = sorted(path.parent.name for path in (ROOT / "mcps").glob("*/pyproject.toml"))
    assert domains, "No MCP domain pyprojects found"

    for domain in domains:
        capabilities_path = ROOT / "mcps" / domain / "capabilities.json"
        snapshot_path = ROOT / "snapshots" / "mcp" / f"{domain}.json"
        assert capabilities_path.exists(), f"Missing {capabilities_path}"
        assert snapshot_path.exists(), f"Missing {snapshot_path}"

        capabilities = _load_json(capabilities_path)
        snapshot = _load_json(snapshot_path)
        assert capabilities["domain"] == domain
        assert snapshot["domain"] == domain
        assert capabilities["tools"] == snapshot["tools"]
        assert capabilities["resources"] == snapshot["resources"]
        assert capabilities["prompts"] == snapshot["prompts"]


def test_mcp_snapshots_match_generated_metadata() -> None:
    generated_files = [
        *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "mcps").glob("*/capabilities.json")),
        *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "snapshots" / "mcp").glob("*.json")),
        "docs/generated/mcp-capabilities.md",
    ]
    before = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in generated_files
        if (ROOT / path).exists()
    }

    proc = subprocess.run(
        [sys.executable, "scripts/gen_mcp_metadata.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    after = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in generated_files
        if (ROOT / path).exists()
    }
    assert after == before


def test_mcp_tools_have_descriptions() -> None:
    for path in sorted((ROOT / "mcps").glob("*/capabilities.json")):
        capabilities = _load_json(path)
        missing = [tool["name"] for tool in capabilities["tools"] if not tool.get("description")]
        assert not missing, f"{path}: tools without descriptions: {missing}"


def test_mcp_tool_descriptions_are_not_generic() -> None:
    weak_literals = {"in templates", "notation paths"}
    for path in sorted((ROOT / "mcps").glob("*/capabilities.json")):
        capabilities = _load_json(path)
        weak = [
            (tool["name"], tool["description"])
            for tool in capabilities["tools"]
            if tool["description"].startswith("Run the ") or tool["description"] in weak_literals
        ]
        assert not weak, f"{path}: weak tool descriptions: {weak}"
