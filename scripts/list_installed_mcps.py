"""List domain MCP binaries installed in the local virtualenv."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = ROOT / ".venv" / "bin"


def _domains() -> list[str]:
    return sorted(path.parent.name for path in (ROOT / "mcps").glob("*/pyproject.toml"))


def _rows() -> list[dict[str, str | bool]]:
    rows = []
    for domain in _domains():
        binary = f"forge-mcp-{domain}"
        path = VENV_BIN / binary
        installed = path.exists() and path.is_file()
        rows.append(
            {
                "domain": domain,
                "binary": binary,
                "installed": installed,
                "path": str(path.resolve()),
                "install_command": f"make install-mcp-{domain}",
            }
        )
    return rows


def _print_table(rows: list[dict[str, str | bool]]) -> None:
    print("Domain          Installed  Binary                    Path")
    print("--------------  ---------  ------------------------  ----")
    for row in rows:
        installed = "yes" if row["installed"] else "no"
        print(f"{row['domain']:<14}  {installed:<9}  {row['binary']:<24}  {row['path']}")
    print()
    print("Install all:")
    print("  make install-mcp-all")
    print()
    print("Use path example:")
    installed_rows = [row for row in rows if row["installed"]]
    example = installed_rows[0] if installed_rows else rows[0]
    print(f"  {example['path']}")
    print()
    print("Install individual example:")
    print(f"  {example['install_command']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List domain MCP binaries installed in .venv/bin")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    rows = _rows()
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        _print_table(rows)


if __name__ == "__main__":
    main()
