"""Session authorization: verify once, then trust commands for the session."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from assistant.commands.parser import Risk
from assistant.config import SafetyMode

DEFAULT_SESSION_TIMEOUT_SECONDS = 30 * 60


@dataclass
class Session:
    """An authorized session for one speaker.

    The speaker is verified once (stage 3 plugs a real speaker model in here);
    afterwards commands run without re-asking until the session expires.
    """

    owner: str
    similarity: float = 1.0
    threshold: float = 0.85
    safety_mode: SafetyMode = SafetyMode.NORMAL
    timeout_seconds: float = DEFAULT_SESSION_TIMEOUT_SECONDS
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    started_at: float = field(init=False)

    def __post_init__(self) -> None:
        self.started_at = self.clock()

    @property
    def authorized(self) -> bool:
        return self.similarity >= self.threshold and not self.expired

    @property
    def expired(self) -> bool:
        return self._now() - self.started_at > self.timeout_seconds

    def refresh(self) -> None:
        """Extend the session after successful activity."""
        self.started_at = self._now()

    def requires_confirmation(self, risk: Risk) -> bool:
        if self.safety_mode is SafetyMode.FULL_AUTOMATION:
            return False
        if self.safety_mode is SafetyMode.STRICT:
            return True
        return risk is Risk.DANGEROUS

    def _now(self) -> float:
        return self.clock()


def authorize(
    similarity: float,
    *,
    owner: str = "Salem",
    threshold: float = 0.85,
    safety_mode: SafetyMode = SafetyMode.NORMAL,
) -> Session | None:
    """Start a session when the voice similarity clears the threshold."""
    session = Session(
        owner=owner,
        similarity=similarity,
        threshold=threshold,
        safety_mode=safety_mode,
    )
    return session if session.authorized else None
