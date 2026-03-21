"""ForgeResult — unified output contract for all forgetools scripts."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ForgeResult:
    ok: bool
    tool: str
    data: Any = None
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0
    suggestion: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["suggestion"] is None:
            d.pop("suggestion")
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    def print(self) -> None:
        print(self.to_json())

    @classmethod
    def success(cls, tool: str, data: Any, duration_ms: int = 0) -> "ForgeResult":
        return cls(ok=True, tool=tool, data=data, duration_ms=duration_ms)

    @classmethod
    def failure(
        cls,
        tool: str,
        errors: list[str],
        duration_ms: int = 0,
        suggestion: str | None = None,
    ) -> "ForgeResult":
        return cls(
            ok=False,
            tool=tool,
            data=None,
            errors=errors,
            duration_ms=duration_ms,
            suggestion=suggestion,
        )


class Timer:
    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed_ms: int = 0

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = int((time.monotonic() - self._start) * 1000)
