import pytest

from assistant.commands.parser import parse
from assistant.config import SafetyMode
from assistant.executor import execute
from assistant.security.authorization import authorize
from assistant.voice.enrollment import enroll
from assistant.voice.profile import VoiceProfile
from assistant.voice.similarity import cosine_similarity, mean_vector
from assistant.voice.speaker_verification import (
    AlwaysTrustVerifier,
    VerifierUnavailableError,
    build_verifier,
)
from assistant.voice.wake_word import contains_wake_word, strip_wake_word


def test_cosine_similarity():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([0, 0], [1, 1]) == 0.0


def test_cosine_similarity_length_mismatch():
    with pytest.raises(ValueError):
        cosine_similarity([1, 2], [1])


def test_mean_vector():
    assert mean_vector([[1.0, 3.0], [3.0, 1.0]]) == [2.0, 2.0]


def test_wake_word_detection():
    assert contains_wake_word("Hey Assistant, open chrome")
    assert contains_wake_word("hey salem")
    assert not contains_wake_word("open chrome")


def test_strip_wake_word():
    assert strip_wake_word("Hey assistant, open chrome") == "open chrome"
    assert strip_wake_word("hey assistant") == ""


def test_profile_roundtrip(tmp_path):
    profile = VoiceProfile(directory=tmp_path / "voice", owner="Salem")
    assert not profile.enrolled

    profile.add_sample(b"RIFF-one")
    profile.add_sample(b"RIFF-two")
    assert profile.enrolled
    assert [p.name for p in profile.samples()] == ["sample_01.wav", "sample_02.wav"]
    assert profile.metadata_path.exists()

    assert profile.clear() == 2
    assert not profile.enrolled


def test_enroll_records_requested_number_of_samples(tmp_path):
    profile = VoiceProfile(directory=tmp_path / "voice")
    recorded: list[float] = []

    def fake_record(seconds: float) -> bytes:
        recorded.append(seconds)
        return b"RIFF" + str(len(recorded)).encode()

    saved = enroll(profile, fake_record, samples=3, seconds=2.0, announce=lambda _: None)
    assert len(saved) == 3
    assert recorded == [2.0, 2.0, 2.0]
    assert len(profile.samples()) == 3


def test_build_verifier_requires_enrollment(tmp_path):
    profile = VoiceProfile(directory=tmp_path / "empty")
    with pytest.raises(VerifierUnavailableError):
        build_verifier(profile)
    assert isinstance(build_verifier(profile, insecure=True), AlwaysTrustVerifier)


def test_matching_voice_opens_session_and_other_voice_is_ignored():
    class FakeVerifier:
        def __init__(self, score: float) -> None:
            self.score = score

        def similarity(self, wav_bytes: bytes) -> float:
            return self.score

    owner_score = FakeVerifier(0.91).similarity(b"audio")
    session = authorize(owner_score, threshold=0.45, safety_mode=SafetyMode.NORMAL)
    assert session is not None
    assert execute(parse("open facebook"), session, dry_run=True).ok

    stranger_score = FakeVerifier(0.21).similarity(b"audio")
    assert authorize(stranger_score, threshold=0.45) is None
