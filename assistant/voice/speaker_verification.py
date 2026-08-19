"""Stage 3 placeholder: speaker verification.

The real implementation (SpeechBrain ECAPA embeddings compared against an
enrolled profile in data/voice_profile/) plugs in behind this interface, so the
rest of the assistant does not change when it lands.
"""

from __future__ import annotations

from typing import Protocol


class SpeakerVerifier(Protocol):
    """Returns a 0..1 similarity between live audio and the enrolled owner."""

    def similarity(self) -> float: ...


class AlwaysTrustVerifier:
    """Development stand-in that trusts whoever is at the microphone."""

    def similarity(self) -> float:
        return 1.0
