"""Shared types for command handlers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    """Outcome of executing one command."""

    ok: bool
    message: str

    def __str__(self) -> str:
        prefix = "OK" if self.ok else "FAILED"
        return f"[{prefix}] {self.message}"
