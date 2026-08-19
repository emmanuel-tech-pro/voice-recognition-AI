"""Wake word detection over transcribed speech.

Speech-to-text already runs on every phrase, so the wake word is matched on the
transcript rather than with a dedicated keyword model. Transcribers often
mis-hear the wake phrase, so a few common variants are accepted.
"""

from __future__ import annotations

from assistant.commands.parser import normalize

DEFAULT_WAKE_WORDS = (
    "hey assistant",
    "hey salem",
    "ok assistant",
    "hey system",
)


def contains_wake_word(text: str, wake_words: tuple[str, ...] = DEFAULT_WAKE_WORDS) -> bool:
    command = normalize(text)
    return any(word in command for word in wake_words)


def strip_wake_word(text: str, wake_words: tuple[str, ...] = DEFAULT_WAKE_WORDS) -> str:
    """Return whatever followed the wake word, e.g. 'hey assistant open chrome'."""
    command = normalize(text)
    for word in wake_words:
        index = command.find(word)
        if index != -1:
            return command[index + len(word) :].strip(" ,.")
    return command
