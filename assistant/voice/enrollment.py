"""Recording the owner's voice samples into a profile."""

from __future__ import annotations

from collections.abc import Callable

from assistant.voice.profile import RECOMMENDED_SAMPLES, VoiceProfile

SAMPLE_SECONDS = 4.0

ENROLLMENT_PHRASES = (
    "Hey assistant, this is my voice.",
    "Open Chrome and start my work session.",
    "The quick brown fox jumps over the lazy dog.",
    "Authorize me and run my commands.",
    "Today I am building my own AI assistant.",
)


def enroll(
    profile: VoiceProfile,
    record: Callable[[float], bytes],
    *,
    samples: int = RECOMMENDED_SAMPLES,
    seconds: float = SAMPLE_SECONDS,
    announce: Callable[[str], None] = print,
) -> list[str]:
    """Record `samples` clips into the profile and return their paths.

    `record(seconds) -> wav_bytes` is injected so enrollment can be driven by a
    microphone in production and by a fake in tests.
    """
    announce(f"Enrolling {profile.owner}: {samples} clips of {seconds:.0f}s each.")
    saved: list[str] = []
    for index in range(samples):
        phrase = ENROLLMENT_PHRASES[index % len(ENROLLMENT_PHRASES)]
        announce(f"[{index + 1}/{samples}] Say: {phrase}")
        wav_bytes = record(seconds)
        path = profile.add_sample(wav_bytes)
        announce(f"    saved {path}")
        saved.append(str(path))
    announce(f"Enrollment complete: {len(profile.samples())} samples in {profile.directory}.")
    return saved
