"""Safe filesystem operations with preview-by-default semantics."""
from __future__ import annotations

import argparse
import os
import shutil
import stat as stat_module
import tarfile
import zipfile
from pathlib import Path

from forgetools._cli import make_cli
from forgetools._result import ForgeResult, Timer

TOOL = "fs.operations"
READ_ACTIONS = {"info"}
MUTATING_ACTIONS = {"mkdir", "touch", "copy", "move", "delete", "archive", "extract"}
ACTIONS = tuple(sorted(READ_ACTIONS | MUTATING_ACTIONS))
ARCHIVE_FORMATS = {"tar.gz", "tgz", "tar", "zip"}


def run(
    *,
    action: str = "info",
    cwd: str | None = None,
    path: str = "",
    source: str = "",
    destination: str = "",
    sources: str = "",
    archive_format: str = "auto",
    execute: bool = False,
    confirm: bool = False,
    recursive: bool = False,
    overwrite: bool = False,
    allow_dangerous: bool = False,
) -> ForgeResult:
    with Timer() as t:
        if action not in ACTIONS:
            return ForgeResult.failure(
                TOOL,
                [f"Unknown action: {action}"],
                t.elapsed_ms,
                suggestion=f"Use one of: {', '.join(ACTIONS)}",
            )
        base = Path(cwd or ".").resolve()
        try:
            if action == "info":
                target = _resolve(base, path)
                return ForgeResult.success(TOOL, _info(target), t.elapsed_ms)
            plan = _plan(
                action=action,
                base=base,
                path=path,
                source=source,
                destination=destination,
                sources=sources,
                archive_format=archive_format,
                recursive=recursive,
                overwrite=overwrite,
                allow_dangerous=allow_dangerous,
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)

        if not execute:
            return ForgeResult.success(
                TOOL,
                {**plan, "preview": True, "executed": False, "requires_confirmation": True},
                t.elapsed_ms,
            )
        if not confirm:
            return ForgeResult.failure(
                TOOL,
                ["Explicit confirmation is required for this filesystem mutation"],
                t.elapsed_ms,
                suggestion="Call again with execute=true and confirm=true after reviewing the preview",
            )
        try:
            result = _execute(plan, overwrite=overwrite)
        except (FileNotFoundError, OSError, ValueError) as exc:
            return ForgeResult.failure(TOOL, [str(exc)], t.elapsed_ms)
        return ForgeResult.success(
            TOOL,
            {**result, "preview": False, "executed": True},
            t.elapsed_ms,
        )


def _resolve(base: Path, value: str) -> Path:
    if not value:
        raise ValueError("path is required")
    candidate = Path(value)
    # Normalize lexical path segments without following the final symlink.
    # This keeps delete/info safe for links and still produces absolute paths.
    return Path(os.path.abspath(str(candidate if candidate.is_absolute() else base / candidate)))


def _info(target: Path) -> dict:
    result = {"path": str(target), "exists": target.exists(), "lexists": os.path.lexists(target)}
    if not os.path.lexists(target):
        return result
    metadata = target.lstat()
    if target.is_symlink():
        kind = "symlink"
    elif target.is_dir():
        kind = "directory"
    elif target.is_file():
        kind = "file"
    else:
        kind = "other"
    result.update({
        "type": kind,
        "size_bytes": metadata.st_size,
        "mode": stat_module.filemode(metadata.st_mode),
        "mode_octal": oct(stat_module.S_IMODE(metadata.st_mode)),
        "modified_epoch": metadata.st_mtime,
        "is_symlink": target.is_symlink(),
    })
    if target.is_symlink():
        result["link_target"] = os.readlink(target)
    return result


def _plan(
    *,
    action: str,
    base: Path,
    path: str,
    source: str,
    destination: str,
    sources: str,
    archive_format: str,
    recursive: bool,
    overwrite: bool,
    allow_dangerous: bool,
) -> dict:
    if action in {"mkdir", "touch", "delete"}:
        target = _resolve(base, path)
        if action == "delete" and not allow_dangerous:
            _guard_delete(target, base)
        return {"action": action, "path": str(target), "recursive": recursive}
    if action in {"copy", "move"}:
        src = _resolve(base, source)
        dest = _resolve(base, destination)
        if not src.exists():
            raise FileNotFoundError(f"Source not found: {src}")
        if dest.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {dest}; set overwrite=true to replace it")
        return {"action": action, "source": str(src), "destination": str(dest), "overwrite": overwrite}
    if action == "archive":
        items = [_resolve(base, item.strip()) for item in sources.split(",") if item.strip()]
        if not items:
            raise ValueError("sources is required for archive")
        archive = _resolve(base, destination or path)
        _validate_sources(items)
        if archive.exists() and not overwrite:
            raise FileExistsError(f"Archive exists: {archive}; set overwrite=true to replace it")
        fmt = _archive_format(archive_format, archive)
        return {"action": action, "sources": [str(item) for item in items], "destination": str(archive), "format": fmt, "overwrite": overwrite}
    if action == "extract":
        archive = _resolve(base, source or path)
        dest = _resolve(base, destination)
        if not archive.is_file():
            raise FileNotFoundError(f"Archive not found: {archive}")
        fmt = _archive_format(archive_format, archive)
        return {"action": action, "source": str(archive), "destination": str(dest), "format": fmt, "overwrite": overwrite}
    raise ValueError(f"Unsupported action: {action}")


def _guard_delete(target: Path, base: Path) -> None:
    if target == base or target == Path(target.anchor):
        raise ValueError("Refusing to delete the working directory or filesystem root without allow_dangerous=true")
    if target.name == ".git":
        raise ValueError("Refusing to delete .git without allow_dangerous=true")


def _validate_sources(items: list[Path]) -> None:
    for item in items:
        if not item.exists():
            raise FileNotFoundError(f"Source not found: {item}")


def _archive_format(requested: str, archive: Path) -> str:
    if requested != "auto":
        if requested not in ARCHIVE_FORMATS:
            raise ValueError(f"Unsupported archive format: {requested}")
        return requested
    name = archive.name.lower()
    if name.endswith((".tar.gz", ".tgz")):
        return "tar.gz"
    if name.endswith(".tar"):
        return "tar"
    if name.endswith(".zip"):
        return "zip"
    return "tar.gz"


def _execute(plan: dict, *, overwrite: bool) -> dict:
    action = plan["action"]
    if action == "mkdir":
        Path(plan["path"]).mkdir(parents=True, exist_ok=True)
        return {"action": action, "path": plan["path"]}
    if action == "touch":
        target = Path(plan["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        return {"action": action, "path": plan["path"]}
    if action == "delete":
        target = Path(plan["path"])
        if target.is_dir() and not target.is_symlink():
            if not plan["recursive"]:
                raise ValueError("recursive=true is required to delete a directory")
            shutil.rmtree(target)
        else:
            target.unlink()
        return {"action": action, "path": plan["path"]}
    if action in {"copy", "move"}:
        src, dest = Path(plan["source"]), Path(plan["destination"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        if action == "copy":
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=overwrite)
            else:
                shutil.copy2(src, dest)
        else:
            if dest.exists() and overwrite:
                if dest.is_dir() and not dest.is_symlink():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(src), str(dest))
        return {"action": action, "source": str(src), "destination": str(dest)}
    if action == "archive":
        archive = Path(plan["destination"])
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists() and overwrite:
            archive.unlink()
        items = [Path(item) for item in plan["sources"]]
        if plan["format"] in {"tar.gz", "tgz"}:
            with tarfile.open(archive, "w:gz") as handle:
                for item in items:
                    handle.add(item, arcname=item.name)
        elif plan["format"] == "tar":
            with tarfile.open(archive, "w") as handle:
                for item in items:
                    handle.add(item, arcname=item.name)
        else:
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
                for item in items:
                    if item.is_dir():
                        for child in item.rglob("*"):
                            if child.is_file():
                                handle.write(child, child.relative_to(item.parent))
                    else:
                        handle.write(item, item.name)
        return {"action": action, "destination": str(archive), "format": plan["format"]}
    if action == "extract":
        archive, dest = Path(plan["source"]), Path(plan["destination"])
        dest.mkdir(parents=True, exist_ok=True)
        if plan["format"] in {"tar.gz", "tgz", "tar"}:
            with tarfile.open(archive, "r:*") as handle:
                members = _safe_tar_members(handle, dest)
                handle.extractall(dest, members=members)
        else:
            with zipfile.ZipFile(archive) as handle:
                names = _safe_zip_members(handle, dest)
                handle.extractall(dest, members=names)
        return {"action": action, "source": str(archive), "destination": str(dest), "format": plan["format"]}
    raise ValueError(f"Unsupported action: {action}")


def _safe_tar_members(handle: tarfile.TarFile, destination: Path) -> list[tarfile.TarInfo]:
    safe: list[tarfile.TarInfo] = []
    root = destination.resolve()
    for member in handle.getmembers():
        target = (destination / member.name).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Unsafe archive member: {member.name}")
        if member.issym() or member.islnk():
            raise ValueError(f"Link members are not allowed during extraction: {member.name}")
        safe.append(member)
    return safe


def _safe_zip_members(handle: zipfile.ZipFile, destination: Path) -> list[zipfile.ZipInfo]:
    safe: list[zipfile.ZipInfo] = []
    root = destination.resolve()
    for member in handle.infolist():
        target = (destination / member.filename).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Unsafe archive member: {member.filename}")
        safe.append(member)
    return safe


def _add_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("action", choices=ACTIONS)
    p.add_argument("--path", default="")
    p.add_argument("--source", default="")
    p.add_argument("--destination", default="")
    p.add_argument("--sources", default="", help="Comma-separated source paths for archive")
    p.add_argument("--archive-format", default="auto", choices=["auto", *sorted(ARCHIVE_FORMATS)])
    p.add_argument("--execute", action="store_true")
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--recursive", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--allow-dangerous", action="store_true")


if __name__ == "__main__":
    make_cli(TOOL, "Inspect, create, copy, move, delete, archive, or extract filesystem paths safely", run, _add_args)
