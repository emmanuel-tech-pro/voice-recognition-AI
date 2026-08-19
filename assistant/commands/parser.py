"""Deterministic command parsing: spoken/typed text -> an intent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from assistant.commands.browser_control import resolve_site
from assistant.config import resolve_app_name, resolve_project


class Risk(str, Enum):
    """How careful the assistant should be before running a command."""

    SAFE = "safe"
    DANGEROUS = "dangerous"


class IntentName(str, Enum):
    OPEN_APP = "open_app"
    OPEN_PROJECT = "open_project"
    OPEN_SITE = "open_site"
    OPEN_URL = "open_url"
    SEARCH = "search"
    TYPE = "type"
    HELP = "help"
    EXIT = "exit"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Intent:
    name: IntentName
    args: dict[str, str] = field(default_factory=dict)
    risk: Risk = Risk.SAFE
    raw: str = ""


DANGEROUS_PATTERNS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\bformat\b",
    r"\bshut ?down\b",
    r"\brestart\b",
    r"\buninstall\b",
    r"\binstall\b",
    r"\bsend money\b",
    r"\btransfer\b",
    r"\bchange (my )?password\b",
]

_EXIT_WORDS = {"exit", "quit", "stop", "goodbye", "shut up"}
_HELP_WORDS = {"help", "what can you do", "commands"}


def normalize(text: str) -> str:
    """Lowercase, strip punctuation noise and collapse whitespace."""
    cleaned = re.sub(r"[^\w\s:./?=&-]", " ", text.lower())
    return " ".join(cleaned.split())


def classify_risk(text: str) -> Risk:
    return Risk.DANGEROUS if any(re.search(p, text) for p in DANGEROUS_PATTERNS) else Risk.SAFE


def parse(text: str) -> Intent:
    """Turn raw user text into an intent the executor understands."""
    raw = text.strip()
    command = normalize(raw)
    if not command:
        return Intent(IntentName.UNKNOWN, raw=raw)

    risk = classify_risk(command)

    if command in _EXIT_WORDS:
        return Intent(IntentName.EXIT, raw=raw)
    if command in _HELP_WORDS:
        return Intent(IntentName.HELP, raw=raw)

    type_match = re.match(r"^(?:type|write)\s+(.+)$", raw.strip(), flags=re.IGNORECASE)
    if type_match:
        return Intent(IntentName.TYPE, {"text": type_match.group(1)}, risk, raw)

    search_match = re.match(r"^(?:search|google|look up)\s+(?:for\s+)?(.+)$", command)
    if search_match:
        return Intent(IntentName.SEARCH, {"query": search_match.group(1)}, risk, raw)

    project_match = re.match(
        r"^(?:open|launch|start)\s+(?:my\s+)?(?:project\s+(.+)|(.+?)\s+project)$", command
    )
    if project_match:
        project = project_match.group(1) or project_match.group(2)
        return Intent(IntentName.OPEN_PROJECT, {"project": project}, risk, raw)

    open_match = re.match(r"^(?:open|launch|start|go to)\s+(.+)$", command)
    if open_match:
        target = open_match.group(1)
        if target.startswith(("http://", "https://")):
            return Intent(IntentName.OPEN_URL, {"url": target}, risk, raw)
        if resolve_app_name(target):
            return Intent(IntentName.OPEN_APP, {"app": target}, risk, raw)
        if resolve_site(target):
            return Intent(IntentName.OPEN_SITE, {"site": target}, risk, raw)
        if resolve_project(target):
            return Intent(IntentName.OPEN_PROJECT, {"project": target}, risk, raw)
        return Intent(IntentName.UNKNOWN, {"target": target}, risk, raw)

    return Intent(IntentName.UNKNOWN, risk=risk, raw=raw)
