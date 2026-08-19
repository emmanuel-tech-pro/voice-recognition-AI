from assistant.commands.parser import Risk
from assistant.config import SafetyMode
from assistant.security.authorization import Session, authorize


def test_authorize_above_threshold():
    session = authorize(0.96, threshold=0.85)
    assert session is not None
    assert session.authorized


def test_authorize_below_threshold():
    assert authorize(0.42, threshold=0.85) is None


def test_session_expires_and_refreshes():
    now = [0.0]
    session = Session(owner="Salem", timeout_seconds=60, clock=lambda: now[0])
    now[0] = 61
    assert session.expired
    session.refresh()
    assert not session.expired


def test_confirmation_policy_per_mode():
    normal = Session(owner="Salem", safety_mode=SafetyMode.NORMAL)
    assert not normal.requires_confirmation(Risk.SAFE)
    assert normal.requires_confirmation(Risk.DANGEROUS)

    strict = Session(owner="Salem", safety_mode=SafetyMode.STRICT)
    assert strict.requires_confirmation(Risk.SAFE)

    full = Session(owner="Salem", safety_mode=SafetyMode.FULL_AUTOMATION)
    assert not full.requires_confirmation(Risk.DANGEROUS)
