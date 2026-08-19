from assistant.commands.parser import parse
from assistant.config import SafetyMode
from assistant.executor import execute
from assistant.security.authorization import Session


def make_session(mode: SafetyMode = SafetyMode.NORMAL) -> Session:
    return Session(owner="Salem", safety_mode=mode)


def test_dry_run_open_site():
    result = execute(parse("open facebook"), make_session(), dry_run=True)
    assert result.ok
    assert "facebook.com" in result.message


def test_dry_run_search_encodes_query():
    result = execute(parse("google python dataclasses"), make_session(), dry_run=True)
    assert "python+dataclasses" in result.message


def test_unknown_command_reports_failure():
    result = execute(parse("make me a sandwich"), make_session(), dry_run=True)
    assert not result.ok


def test_dangerous_command_blocked_without_confirmation():
    result = execute(parse("delete everything"), make_session(), dry_run=True)
    assert not result.ok
    assert "confirmation" in result.message


def test_strict_mode_asks_for_safe_command():
    asked: list[str] = []

    def confirm(command: str) -> bool:
        asked.append(command)
        return True

    result = execute(
        parse("open facebook"),
        make_session(SafetyMode.STRICT),
        dry_run=True,
        confirm=confirm,
    )
    assert result.ok
    assert asked == ["open facebook"]


def test_unauthorized_session_executes_nothing():
    session = Session(owner="Salem", similarity=0.1, threshold=0.85)
    assert not execute(parse("open facebook"), session, dry_run=True).ok
