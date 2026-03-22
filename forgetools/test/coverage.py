"""forgetools.test.coverage — Parse Cobertura coverage.xml reports."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "test.coverage"


def run(*, path: str = "coverage.xml", cwd: str | None = None) -> ForgeResult:
    with Timer() as t:
        try:
            full_path = Path(cwd or ".") / path
            if not full_path.exists():
                return ForgeResult.failure(
                    TOOL,
                    [f"Coverage file not found: {full_path}"],
                    t.elapsed_ms,
                    suggestion="Run tests with coverage reporting enabled",
                )
            tree = ET.parse(full_path)
            data = _parse(tree.getroot())
            return ForgeResult.success(TOOL, data, t.elapsed_ms)
        except ET.ParseError as e:
            return ForgeResult.failure(TOOL, [f"XML parse error: {e}"], t.elapsed_ms)
        except Exception as e:
            return ForgeResult.failure(TOOL, [str(e)], t.elapsed_ms)


def _parse(root: ET.Element) -> dict:
    line_rate = float(root.get("line-rate", 0.0))
    branch_rate = float(root.get("branch-rate", 0.0))
    total_pct = round(line_rate * 100, 2)

    modules: list[dict] = []
    for pkg in root.iter("package"):
        for cls in pkg.iter("class"):
            name = cls.get("name") or cls.get("filename", "unknown")
            cls_line_rate = float(cls.get("line-rate", 0.0))
            lines = cls.find("lines")
            lines_valid = 0
            lines_covered = 0
            uncovered: list[int] = []
            if lines is not None:
                for line in lines.findall("line"):
                    hits = int(line.get("hits", 0))
                    num = int(line.get("number", 0))
                    lines_valid += 1
                    if hits > 0:
                        lines_covered += 1
                    else:
                        uncovered.append(num)
            modules.append({
                "name": name,
                "line_rate": round(cls_line_rate, 4),
                "lines_valid": lines_valid,
                "lines_covered": lines_covered,
                "uncovered_lines": uncovered,
            })

    return {
        "total_pct": total_pct,
        "line_rate": round(line_rate, 4),
        "branch_rate": round(branch_rate, 4),
        "modules": modules,
    }


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", default="coverage.xml", help="Path to coverage.xml")


if __name__ == "__main__":
    make_cli(TOOL, "Parse Cobertura coverage.xml report", run, _add_args)
