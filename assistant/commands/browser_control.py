"""Opening websites and running web searches."""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from assistant.commands.base import CommandResult
from assistant.config import SEARCH_URL, WEBSITES


def resolve_site(spoken_name: str) -> str | None:
    return WEBSITES.get(" ".join(spoken_name.lower().split()))


def open_url(url: str, *, dry_run: bool = False) -> CommandResult:
    if dry_run:
        return CommandResult(True, f"Would open {url}")
    if webbrowser.open(url):
        return CommandResult(True, f"Opening {url}")
    return CommandResult(False, f"No browser available to open {url}")


def open_site(spoken_name: str, *, dry_run: bool = False) -> CommandResult:
    url = resolve_site(spoken_name)
    if url is None:
        return CommandResult(False, f"I do not know the website {spoken_name!r}.")
    return open_url(url, dry_run=dry_run)


def search_web(query: str, *, dry_run: bool = False) -> CommandResult:
    if not query.strip():
        return CommandResult(False, "Nothing to search for.")
    return open_url(SEARCH_URL.format(query=quote_plus(query)), dry_run=dry_run)
