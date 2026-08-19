"""Launching desktop applications."""

from __future__ import annotations

import shutil
import subprocess

from assistant.commands.base import CommandResult
from assistant.config import APP_REGISTRY, current_system, resolve_app_name


def _spawn(argv: list[str]) -> None:
    subprocess.Popen(  # noqa: S603 - launching a user-requested application
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def open_app(spoken_name: str, *, dry_run: bool = False) -> CommandResult:
    """Open the application the user asked for by its spoken name."""
    key = resolve_app_name(spoken_name)
    if key is None:
        return CommandResult(False, f"I do not know the application {spoken_name!r}.")

    system = current_system()
    candidates = APP_REGISTRY[key].candidates_for(system)
    if not candidates:
        return CommandResult(False, f"{key} is not configured for {system}.")

    if system == "Darwin":
        argv = ["open", "-a", candidates[0]]
        if dry_run:
            return CommandResult(True, f"Would run: {' '.join(argv)}")
        _spawn(argv)
        return CommandResult(True, f"Opening {key}.")

    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable is None:
            continue
        if dry_run:
            return CommandResult(True, f"Would run: {executable}")
        _spawn([executable])
        return CommandResult(True, f"Opening {key}.")

    return CommandResult(False, f"Could not find {key} on this machine (tried {', '.join(candidates)}).")
