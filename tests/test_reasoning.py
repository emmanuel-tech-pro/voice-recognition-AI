import json

import pytest

from assistant.commands.parser import IntentName, Risk
from assistant.config import load_projects, resolve_project
from assistant.reasoning.interpreter import Interpreter, parse_plan


class FakeClient:
    """Replays a canned model reply and records the prompt it was given."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.requests: list[str] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.requests.append(user_prompt)
        return self.reply


def plan_json(*steps: dict) -> str:
    return json.dumps({"steps": list(steps)})


def test_known_command_never_reaches_the_model():
    client = FakeClient(plan_json({"action": "open_site", "site": "youtube"}))
    intents = Interpreter(client).plan("open chrome")
    assert [i.name for i in intents] == [IntentName.OPEN_APP]
    assert client.requests == []


def test_open_ended_request_becomes_a_multi_step_plan():
    client = FakeClient(
        plan_json(
            {"action": "open_app", "app": "vscode"},
            {"action": "open_project", "project": "sightfirst"},
        )
    )
    intents = Interpreter(client).plan("I want to continue working on my hospital website")
    assert [i.name for i in intents] == [IntentName.OPEN_APP, IntentName.OPEN_PROJECT]
    assert intents[1].args["project"] == "sightfirst"
    assert client.requests == ["I want to continue working on my hospital website"]


def test_unknown_stays_unknown_without_a_model():
    intents = Interpreter().plan("make me a sandwich")
    assert [i.name for i in intents] == [IntentName.UNKNOWN]


def test_empty_plan_falls_back_to_unknown():
    intents = Interpreter(FakeClient(plan_json())).plan("do something vague")
    assert [i.name for i in intents] == [IntentName.UNKNOWN]


@pytest.mark.parametrize(
    "reply",
    [
        "not json at all",
        json.dumps({"steps": "nope"}),
        plan_json({"action": "rm_rf", "path": "/"}),
        plan_json({"action": "open_app"}),
        plan_json({"action": "open_app", "app": "   "}),
    ],
)
def test_invalid_model_replies_produce_no_intents(reply):
    assert parse_plan(reply, "whatever") == []


def test_plan_is_capped_and_inherits_request_risk():
    steps = [{"action": "search", "query": f"q{i}"} for i in range(10)]
    intents = parse_plan(plan_json(*steps), "delete my old branches and search around")
    assert len(intents) == 6
    assert all(i.risk is Risk.DANGEROUS for i in intents)


def test_projects_are_loaded_and_matched_partially(tmp_path):
    path = tmp_path / "projects.json"
    path.write_text(json.dumps({"SightFirst Hospital": "/code/sightfirst", "blog": "/code/blog"}))
    projects = load_projects(path)
    assert projects == {"sightfirst hospital": "/code/sightfirst", "blog": "/code/blog"}
    assert resolve_project("sightfirst", projects) == "/code/sightfirst"
    assert resolve_project("hospital", projects) == "/code/sightfirst"
    assert resolve_project("unknown thing", projects) is None
