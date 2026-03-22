"""forgetools.fs.checksum — Compute file checksums using stdlib hashlib."""
from __future__ import annotations

import argparse
import hashlib
import os

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "fs.checksum"

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".tox", ".mypy_cache"}


def run(
    *,
    path: str,
    algorithm: str = "sha256",
    recursive: bool = False,
    cwd: str | None = None,
) -> ForgeResult:
    with Timer() as t:
        if algorithm not in hashlib.algorithms_available:
            return ForgeResult.failure(
                TOOL,
                [f"Unsupported algorithm: {algorithm}. Available: {', '.join(sorted(hashlib.algorithms_guaranteed))}"],
                duration_ms=t.elapsed_ms,
            )

        resolved = path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path)

        if not os.path.exists(resolved):
            return ForgeResult.failure(
                TOOL, [f"Path not found: {resolved}"], duration_ms=t.elapsed_ms
            )

        try:
            if os.path.isfile(resolved):
                entry = _checksum_file(resolved, algorithm)
                return ForgeResult.success(
                    TOOL, {"algorithm": algorithm, "files": [entry], "count": 1}, t.elapsed_ms
                )
            elif os.path.isdir(resolved):
                if not recursive:
                    return ForgeResult.failure(
                        TOOL,
                        [f"{resolved} is a directory; use --recursive to checksum all files"],
                        duration_ms=t.elapsed_ms,
                    )
                files = _checksum_dir(resolved, algorithm)
                return ForgeResult.success(
                    TOOL, {"algorithm": algorithm, "files": files, "count": len(files)}, t.elapsed_ms
                )
            else:
                return ForgeResult.failure(TOOL, [f"Not a file or directory: {resolved}"], duration_ms=t.elapsed_ms)
        except OSError as e:
            return ForgeResult.failure(TOOL, [str(e)], duration_ms=t.elapsed_ms)


def _checksum_file(filepath: str, algorithm: str) -> dict:
    h = hashlib.new(algorithm)
    size = 0
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
            size += len(chunk)
    return {"path": filepath, "checksum": h.hexdigest(), "size_bytes": size}


def _checksum_dir(dirpath: str, algorithm: str) -> list[dict]:
    results = []
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            try:
                results.append(_checksum_file(fpath, algorithm))
            except OSError:
                continue
    return results


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--path", required=True, help="File or directory path")
    p.add_argument("--algorithm", default="sha256", help="Hash algorithm (default: sha256)")
    p.add_argument("--recursive", action="store_true", default=False,
                   help="Recursively checksum all files in a directory")


if __name__ == "__main__":
    make_cli(TOOL, "Compute file checksums", run, _add_args)
