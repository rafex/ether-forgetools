"""forgetools.lint.checkstyle — Parse Checkstyle XML result files."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "lint.checkstyle"


def run(*, path: str = "checkstyle-result.xml", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            full_path = Path(cwd or ".") / path
            if not full_path.exists():
                return ForgeResult.failure(
                    TOOL,
                    [f"Checkstyle result file not found: {full_path}"],
                    t.elapsed_ms,
                    suggestion="Run checkstyle first to generate the result file",
                )
            tree = ET.parse(full_path)
            data = _parse(tree.getroot())
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except ET.ParseError as e:
            return ForgeResult.failure(TOOL, [f"XML parse error: {e}"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


def _parse(root: ET.Element) -> dict:
    total = errors = warnings = infos = 0
    files: list[dict] = []

    for file_elem in root.findall("file"):
        fname = file_elem.get("name", "")
        violations: list[dict] = []
        for err in file_elem.findall("error"):
            severity = err.get("severity", "error")
            violations.append({
                "line": int(err.get("line", 0)),
                "col": int(err.get("column", 0)),
                "severity": severity,
                "message": err.get("message", ""),
                "rule": err.get("source", "").split(".")[-1],
            })
            total += 1
            if severity == "error":
                errors += 1
            elif severity == "warning":
                warnings += 1
            elif severity == "info":
                infos += 1
        if violations:
            files.append({"file": fname, "violations": violations})

    return {
        "total": total,
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "files": files,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="checkstyle-result.xml",
                   help="Path to checkstyle XML result file")


if __name__ == "__main__":
    make_cli(TOOL, "Parse Checkstyle XML result file", run, _add_args)
