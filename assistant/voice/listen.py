"""Stage 2: microphone input converted to text.

Uses SpeechRecognition + Google's free web API by default so no model download
is needed to get the first spoken command working.
"""

from __future__ import annotations


class SpeechUnavailableError(RuntimeError):
    """Raised when microphone or speech dependencies are missing."""


class MicrophoneListener:
    """Blocking microphone listener that returns recognized text."""

    def __init__(self, *, phrase_time_limit: float = 6.0, energy_threshold: int | None = None) -> None:
        try:
            import speech_recognition as sr
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise SpeechUnavailableError(
                "Install the voice extras: pip install -r requirements-voice.txt"
            ) from exc

        self._sr = sr
        self._recognizer = sr.Recognizer()
        if energy_threshold is not None:
            self._recognizer.energy_threshold = energy_threshold
            self._recognizer.dynamic_energy_threshold = False
        self._phrase_time_limit = phrase_time_limit

    def calibrate(self, duration: float = 1.0) -> None:
        """Measure ambient noise so short commands are detected reliably."""
        with self._sr.Microphone() as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=duration)

    def listen(self) -> str:
        """Record one phrase and return its transcription ('' if unintelligible)."""
        with self._sr.Microphone() as source:
            audio = self._recognizer.listen(source, phrase_time_limit=self._phrase_time_limit)
        try:
            return self._recognizer.recognize_google(audio)
        except self._sr.UnknownValueError:
            return ""
        except self._sr.RequestError as exc:
            raise SpeechUnavailableError(f"Speech service unavailable: {exc}") from exc
