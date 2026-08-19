"""Voice-controlled automation assistant.

Stage 1: typed commands drive the execution engine.
Stage 2: --input voice replaces the keyboard with the microphone.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from assistant.commands.parser import IntentName, parse
from assistant.config import SafetyMode
from assistant.executor import HELP_TEXT, execute
from assistant.security.authorization import authorize
from assistant.voice.listen import MicrophoneListener, SpeechUnavailableError
from assistant.voice.speaker_verification import AlwaysTrustVerifier


def confirm_in_terminal(command: str) -> bool:
    answer = input(f"Confirm {command!r}? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def read_typed_command() -> str | None:
    try:
        return input("Command: ")
    except EOFError:
        return None


def build_voice_reader(owner: str) -> Callable[[], str | None]:
    listener = MicrophoneListener()
    print("Calibrating microphone...")
    listener.calibrate()
    print(f"Listening, {owner}. Speak a command.")

    def read() -> str | None:
        text = listener.listen()
        if text:
            print(f"Heard: {text}")
        return text

    return read


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Voice-controlled automation assistant")
    parser.add_argument(
        "--input", choices=["text", "voice"], default="text", help="how commands are received"
    )
    parser.add_argument("--owner", default="Salem", help="name of the authorized owner")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in SafetyMode],
        default=SafetyMode.NORMAL.value,
        help="confirmation policy for commands",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.85, help="voice similarity required to authorize"
    )
    parser.add_argument("--dry-run", action="store_true", help="print actions instead of performing them")
    parser.add_argument("--once", help="run a single command and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    similarity = AlwaysTrustVerifier().similarity()
    session = authorize(
        similarity,
        owner=args.owner,
        threshold=args.threshold,
        safety_mode=SafetyMode(args.mode),
    )
    if session is None:
        print(f"Voice similarity {similarity:.2f} below threshold {args.threshold:.2f}. Not authorized.")
        return 1

    print(
        f"Voice similarity: {similarity:.2f} / threshold {args.threshold:.2f}"
        f" -> SESSION AUTHORIZED ({session.owner})"
    )
    print(f"Safety mode: {session.safety_mode.value}")

    if args.once:
        result = execute(parse(args.once), session, dry_run=args.dry_run, confirm=confirm_in_terminal)
        print(result)
        return 0 if result.ok else 1

    if args.input == "voice":
        try:
            read_command = build_voice_reader(session.owner)
        except SpeechUnavailableError as exc:
            print(exc, file=sys.stderr)
            return 1
    else:
        print(HELP_TEXT)
        read_command = read_typed_command

    while True:
        if session.expired:
            print("Session expired. Re-authorize with the wake word.")
            return 0
        text = read_command()
        if text is None:
            return 0
        intent = parse(text)
        if intent.name is IntentName.EXIT:
            print("Goodbye.")
            return 0
        if intent.name is IntentName.UNKNOWN and not text.strip():
            continue
        print(execute(intent, session, dry_run=args.dry_run, confirm=confirm_in_terminal))


if __name__ == "__main__":
    raise SystemExit(main())
