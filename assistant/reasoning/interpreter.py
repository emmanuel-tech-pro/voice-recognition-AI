"""Stage 4: turn open-ended requests into a plan of known intents.

The deterministic parser stays the fast path; the LLM is only consulted when a
phrase does not match any rule ("I want to continue working on my hospital
website"). Whatever the model returns is validated back into `Intent` objects,
so the model can never invent an action the executor does not already support.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Protocol

from assistant.commands.parser import Intent, IntentName, classify_risk, parse
from assistant.config import APP_ALIASES, APP_REGISTRY, WEBSITES, load_projects

DEFAULT_MODEL = "gpt-4o-mini"
MAX_PLAN_STEPS = 6

# Intents the model may emit, with their required argument.
PLANNABLE_INTENTS: dict[str, str] = {
    IntentName.OPEN_APP.value: "app",
    IntentName.OPEN_PROJECT.value: "project",
    IntentName.OPEN_SITE.value: "site",
    IntentName.OPEN_URL.value: "url",
    IntentName.SEARCH.value: "query",
    IntentName.TYPE.value: "text",
}

SYSTEM_PROMPT = """You translate a computer user's spoken request into a short plan.

Reply with JSON only: {{"steps": [{{"action": "<action>", "<argument>": "<value>"}}]}}

Allowed actions and their argument:
  open_app     -> app      one of: {apps}
  open_project -> project  one of: {projects}
  open_site    -> site     one of: {sites}
  open_url     -> url      any https URL
  search       -> query    any search text
  type         -> text     text to type into the focused window

Rules:
- At most {max_steps} steps, ordered as they should run.
- Only use the listed apps, projects and sites. If the request needs something
  else, return {{"steps": []}}.
- Never invent file paths, credentials, or destructive actions.
"""


class ChatClient(Protocol):
    """Minimal chat interface, so any backend or a fake can be plugged in."""

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


class OpenAIChatClient:
    """OpenAI-compatible client; point `base_url` at Ollama or LM Studio to run locally."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI, OpenAIError
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ReasoningUnavailableError(
                "Install the reasoning extras: pip install -r requirements-llm.txt"
            ) from exc

        key = api_key or os.environ.get("OPENAI_API_KEY")
        url = base_url or os.environ.get("OPENAI_BASE_URL")
        if key is None and url is None:
            raise ReasoningUnavailableError(
                "Set OPENAI_API_KEY, or point --llm-base-url at a local model server."
            )
        self._model = model
        self._client = OpenAI(api_key=key or "local", base_url=url)
        self._backend_error = OpenAIError

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except self._backend_error as exc:
            raise ReasoningUnavailableError(f"Reasoning backend unreachable: {exc}") from exc
        return response.choices[0].message.content or ""


class ReasoningUnavailableError(RuntimeError):
    """Raised when no reasoning backend is configured."""


def build_prompt() -> str:
    projects = sorted(load_projects()) or ["(none configured)"]
    return SYSTEM_PROMPT.format(
        apps=", ".join(sorted(set(APP_REGISTRY) | set(APP_ALIASES))),
        projects=", ".join(projects),
        sites=", ".join(sorted(WEBSITES)),
        max_steps=MAX_PLAN_STEPS,
    )


def parse_plan(payload: str, raw_request: str) -> list[Intent]:
    """Validate a model reply into intents, dropping anything unsupported."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    steps = data.get("steps") if isinstance(data, dict) else None
    if not isinstance(steps, list):
        return []

    risk = classify_risk(raw_request)
    intents: list[Intent] = []
    for step in steps[:MAX_PLAN_STEPS]:
        if not isinstance(step, dict):
            continue
        action = step.get("action")
        argument = PLANNABLE_INTENTS.get(action) if isinstance(action, str) else None
        if argument is None:
            continue
        value = step.get(argument)
        if not isinstance(value, str) or not value.strip():
            continue
        intents.append(
            Intent(IntentName(action), {argument: value.strip()}, risk, f"{action}: {value.strip()}")
        )
    return intents


class Interpreter:
    """Deterministic parsing first, LLM planning only for unmatched phrases."""

    def __init__(self, client: ChatClient | None = None) -> None:
        self._client = client

    def plan(self, text: str) -> Sequence[Intent]:
        intent = parse(text)
        if intent.name is not IntentName.UNKNOWN or self._client is None:
            return [intent]
        reply = self._client.complete(build_prompt(), text)
        return parse_plan(reply, text) or [intent]
