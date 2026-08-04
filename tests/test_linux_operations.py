from __future__ import annotations

from pathlib import Path

from forgetools.linux.logs import run as logs_run
from forgetools.linux.network import run as network_run
from forgetools.linux.privilege import run as privilege_run
from forgetools.linux.storage import run as storage_run
from forgetools.linux.system import run as system_run


def test_linux_system_reports_host_snapshot() -> None:
    result = system_run(action="info")

    assert result.ok
    assert result.data["hostname"]
    assert result.data["cpu"]["logical_cpus"] >= 1
    assert "memory" in result.data
    assert "uptime" in result.data


def test_linux_storage_reports_usage_and_largest_paths(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_bytes(b"x" * 128)

    usage = storage_run(action="usage", path=str(tmp_path))
    largest = storage_run(action="largest", path=str(tmp_path), max_entries=5, max_depth=1)

    assert usage.ok and usage.data["total_bytes"] >= usage.data["used_bytes"]
    assert largest.ok
    assert any(row["path"].endswith("large.txt") for row in largest.data["entries"])


def test_linux_file_logs_are_bounded_and_filterable(tmp_path: Path) -> None:
    log = tmp_path / "app.log"
    log.write_text("INFO ready\nERROR failed\nINFO recovered\n", encoding="utf-8")

    result = logs_run(action="file", path=str(log), lines=2, pattern="error")

    assert result.ok
    assert result.data["lines"] == ["ERROR failed"]


def test_linux_network_dns_returns_structured_data() -> None:
    result = network_run(action="dns")

    assert result.ok
    assert "nameservers" in result.data
    assert isinstance(result.data["nameservers"], list)


def test_linux_privilege_checks_without_executing_command() -> None:
    result = privilege_run(command="true")

    assert result.ok
    assert result.data["binary_available"] is True
    assert result.data["command"] == "true"
    assert result.data["recommendation"]


def test_linux_privilege_rejects_shell_compound_commands() -> None:
    result = privilege_run(command="true && echo unsafe")

    assert not result.ok
    assert "shell operators" in result.errors[0]
