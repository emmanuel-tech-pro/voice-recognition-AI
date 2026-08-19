"""Typing text into whichever window currently has focus."""

from __future__ import annotations

from assistant.commands.base import CommandResult

TYPING_INTERVAL_SECONDS = 0.02


def type_text(text: str, *, dry_run: bool = False) -> CommandResult:
    if not text.strip():
        return CommandResult(False, "Nothing to type.")
    if dry_run:
        return CommandResult(True, f"Would type: {text}")

    try:
        import pyautogui
    except Exception as exc:  # pragma: no cover - depends on desktop environment
        return CommandResult(False, f"Typing needs pyautogui: {exc}")

    pyautogui.typewrite(text, interval=TYPING_INTERVAL_SECONDS)
    return CommandResult(True, f"Typed: {text}")
