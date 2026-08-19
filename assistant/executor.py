"""Maps parsed intents onto command handlers."""

from __future__ import annotations

from collections.abc import Callable

from assistant.commands import app_control, browser_control, typing_control
from assistant.commands.base import CommandResult
from assistant.commands.parser import Intent, IntentName
from assistant.config import APP_ALIASES, APP_REGISTRY, WEBSITES
from assistant.security.authorization import Session

HELP_TEXT = """Commands I understand right now:
  open <app>        apps: {apps}
  open <website>    sites: {sites}
  open <url>
  search <query>
  type <text>
  help / exit""".format(
    apps=", ".join(sorted(set(APP_REGISTRY) | set(APP_ALIASES))),
    sites=", ".join(sorted(WEBSITES)),
)

ConfirmFn = Callable[[str], bool]


def execute(
    intent: Intent,
    session: Session,
    *,
    dry_run: bool = False,
    confirm: ConfirmFn | None = None,
) -> CommandResult:
    """Run an intent on behalf of an authorized session."""
    if not session.authorized:
        return CommandResult(False, "Session is not authorized.")

    if session.requires_confirmation(intent.risk):
        if confirm is None or not confirm(intent.raw):
            return CommandResult(False, f"Cancelled: {intent.raw!r} needed confirmation.")

    session.refresh()

    if intent.name is IntentName.OPEN_APP:
        return app_control.open_app(intent.args["app"], dry_run=dry_run)
    if intent.name is IntentName.OPEN_SITE:
        return browser_control.open_site(intent.args["site"], dry_run=dry_run)
    if intent.name is IntentName.OPEN_URL:
        return browser_control.open_url(intent.args["url"], dry_run=dry_run)
    if intent.name is IntentName.SEARCH:
        return browser_control.search_web(intent.args["query"], dry_run=dry_run)
    if intent.name is IntentName.TYPE:
        return typing_control.type_text(intent.args["text"], dry_run=dry_run)
    if intent.name is IntentName.HELP:
        return CommandResult(True, HELP_TEXT)
    if intent.name is IntentName.EXIT:
        return CommandResult(True, "Goodbye.")

    target = intent.args.get("target")
    detail = f" I do not know {target!r}." if target else ""
    return CommandResult(False, f"I did not understand {intent.raw!r}.{detail} Say 'help' for the list.")
