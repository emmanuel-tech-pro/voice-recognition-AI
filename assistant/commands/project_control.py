"""Opening named project folders in the editor."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from assistant.commands.base import CommandResult
from assistant.config import load_projects, resolve_project

EDITOR_CANDIDATES = ("code", "code-insiders")


def open_project(spoken_name: str, *, dry_run: bool = False) -> CommandResult:
    """Open the project folder registered under `spoken_name` in VS Code."""
    known = load_projects()
    if not known:
        return CommandResult(False, "No projects configured. Add them to data/projects.json.")

    folder = resolve_project(spoken_name, known)
    if folder is None:
        return CommandResult(
            False, f"I do not know the project {spoken_name!r}. Known: {', '.join(sorted(known))}."
        )
    if not Path(folder).is_dir():
        return CommandResult(False, f"Project folder does not exist: {folder}")

    editor = next((shutil.which(name) for name in EDITOR_CANDIDATES if shutil.which(name)), None)
    if editor is None:
        return CommandResult(False, "VS Code ('code') is not on PATH.")

    if dry_run:
        return CommandResult(True, f"Would run: {editor} {folder}")

    subprocess.Popen(  # noqa: S603 - launching the user's editor
        [editor, folder],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return CommandResult(True, f"Opening project {spoken_name} ({folder}).")
