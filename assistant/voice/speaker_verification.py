"""Stage 3: speaker verification.

`SpeechBrainVerifier` compares live audio against the enrolled samples in
`data/voice_profile/` using ECAPA-TDNN embeddings and cosine similarity. The
`SpeakerVerifier` protocol keeps the rest of the assistant independent of the
model: swap in another embedding backend without touching the session logic.
"""

from __future__ import annotations

import io
from typing import Protocol

from assistant.voice.profile import VoiceProfile
from assistant.voice.similarity import cosine_similarity, mean_vector

ECAPA_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
MODEL_CACHE_DIR = "data/models/spkrec-ecapa-voxceleb"
TARGET_SAMPLE_RATE = 16000

# Cosine similarity between ECAPA embeddings. 0.45 accepts the owner reliably
# while rejecting other speakers; tune it with `python main.py --verify`.
DEFAULT_THRESHOLD = 0.45


class SpeakerVerifier(Protocol):
    """Returns a 0..1 similarity between live audio and the enrolled owner."""

    def similarity(self, wav_bytes: bytes) -> float: ...


class AlwaysTrustVerifier:
    """Development stand-in that trusts whoever is at the microphone."""

    def similarity(self, wav_bytes: bytes) -> float:
        return 1.0


class VerifierUnavailableError(RuntimeError):
    """Raised when the speaker model or the enrolled profile is missing."""


class SpeechBrainVerifier:
    """Cosine similarity between live audio and the averaged enrolled voice."""

    def __init__(
        self,
        profile: VoiceProfile,
        *,
        source: str = ECAPA_SOURCE,
        cache_dir: str = MODEL_CACHE_DIR,
    ) -> None:
        if not profile.enrolled:
            raise VerifierUnavailableError(
                f"No voice samples in {profile.directory}. Run: python main.py --enroll"
            )
        self._profile = profile
        self._source = source
        self._cache_dir = cache_dir
        self._encoder = None
        self._reference: list[float] | None = None

    def similarity(self, wav_bytes: bytes) -> float:
        """Similarity of `wav_bytes` to the enrolled owner, clamped to 0..1."""
        reference = self._reference_embedding()
        candidate = self._embed(wav_bytes)
        return max(0.0, cosine_similarity(reference, candidate))

    def _reference_embedding(self) -> list[float]:
        if self._reference is None:
            embeddings = [self._embed(p.read_bytes()) for p in self._profile.samples()]
            self._reference = mean_vector(embeddings)
        return self._reference

    def _load_encoder(self):
        if self._encoder is None:
            try:
                from speechbrain.inference.speaker import EncoderClassifier
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise VerifierUnavailableError(
                    "Install the verification extras: pip install -r requirements-voice.txt"
                ) from exc
            self._encoder = EncoderClassifier.from_hparams(
                source=self._source, savedir=self._cache_dir
            )
        return self._encoder

    def _embed(self, wav_bytes: bytes) -> list[float]:
        try:
            import torchaudio
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise VerifierUnavailableError(
                "Install the verification extras: pip install -r requirements-voice.txt"
            ) from exc

        waveform, sample_rate = torchaudio.load(io.BytesIO(wav_bytes))
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sample_rate != TARGET_SAMPLE_RATE:
            waveform = torchaudio.functional.resample(waveform, sample_rate, TARGET_SAMPLE_RATE)
        embedding = self._load_encoder().encode_batch(waveform)
        return embedding.squeeze().tolist()


def build_verifier(profile: VoiceProfile, *, insecure: bool = False) -> SpeakerVerifier:
    """Pick the real verifier, or the always-trust stub when explicitly asked."""
    if insecure:
        return AlwaysTrustVerifier()
    return SpeechBrainVerifier(profile)
