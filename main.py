"""Voice-controlled automation assistant.

Stage 1: typed commands drive the execution engine.
Stage 2: --input voice replaces the keyboard with the microphone.
Stage 3: the wake word triggers speaker verification, which opens a session
         that then executes commands without asking again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from assistant.commands.parser import IntentName, parse
from assistant.config import SafetyMode
from assistant.executor import HELP_TEXT, execute
from assistant.security.authorization import Session, authorize
from assistant.voice.enrollment import SAMPLE_SECONDS, enroll
from assistant.voice.listen import MicrophoneListener, SpeechUnavailableError
from assistant.voice.profile import RECOMMENDED_SAMPLES, VoiceProfile
from assistant.voice.speaker_verification import (
    DEFAULT_THRESHOLD,
    VerifierUnavailableError,
    build_verifier,
)
from assistant.voice.wake_word import contains_wake_word, strip_wake_word


def confirm_in_terminal(command: str) -> bool:
    answer = input(f"Confirm {command!r}? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def run_text_loop(session: Session, *, dry_run: bool) -> int:
    """Stage 1 loop: the keyboard is trusted, so no verification runs."""
    print(HELP_TEXT)
    while True:
        if session.expired:
            print("Session expired. Restart the assistant.")
            return 0
        try:
            text = input("Command: ")
        except EOFError:
            return 0
        intent = parse(text)
        if intent.name is IntentName.EXIT:
            print("Goodbye.")
            return 0
        if not text.strip():
            continue
        print(execute(intent, session, dry_run=dry_run, confirm=confirm_in_terminal))


def run_voice_loop(args: argparse.Namespace, profile: VoiceProfile) -> int:
    """Stages 2-3: wake word -> speaker verification -> authorized session."""
    listener = MicrophoneListener()
    verifier = build_verifier(profile, insecure=args.insecure_voice)

    print("Calibrating microphone...")
    listener.calibrate()
    print(f"Listening for the wake word (say 'hey assistant'). Owner: {args.owner}")

    session: Session | None = None
    while True:
        utterance = listener.listen_phrase()
        if not utterance.text:
            continue
        print(f"Heard: {utterance.text}")

        if session is not None and session.expired:
            print("Session expired. Say the wake word again.")
            session = None

        if session is None:
            if not contains_wake_word(utterance.text):
                continue
            similarity = verifier.similarity(utterance.wav_bytes)
            session = authorize(
                similarity,
                owner=args.owner,
                threshold=args.threshold,
                safety_mode=SafetyMode(args.mode),
            )
            if session is None:
                print(f"Voice similarity {similarity:.2f} < {args.threshold:.2f} -> IGNORED")
                continue
            print(
                f"Voice similarity {similarity:.2f} >= {args.threshold:.2f}"
                f" -> SESSION AUTHORIZED ({session.owner}, {session.safety_mode.value})"
            )
            command = strip_wake_word(utterance.text)
            if not command:
                continue
        else:
            command = utterance.text

        intent = parse(command)
        if intent.name is IntentName.EXIT:
            print("Goodbye.")
            return 0
        print(execute(intent, session, dry_run=args.dry_run, confirm=confirm_in_terminal))


def run_enrollment(args: argparse.Namespace, profile: VoiceProfile) -> int:
    listener = MicrophoneListener()
    print("Calibrating microphone...")
    listener.calibrate()
    enroll(profile, listener.record, samples=args.samples, seconds=SAMPLE_SECONDS)
    return 0


def run_verify(args: argparse.Namespace, profile: VoiceProfile) -> int:
    """Score one spoken phrase against the profile, for tuning --threshold."""
    listener = MicrophoneListener()
    verifier = build_verifier(profile, insecure=args.insecure_voice)
    print("Calibrating microphone...")
    listener.calibrate()
    print("Speak now...")
    utterance = listener.listen_phrase()
    similarity = verifier.similarity(utterance.wav_bytes)
    verdict = "MATCH" if similarity >= args.threshold else "NO MATCH"
    print(f"Heard: {utterance.text or '(not transcribed)'}")
    print(f"Similarity {similarity:.3f} vs threshold {args.threshold:.2f} -> {verdict}")
    return 0


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
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="voice similarity required to authorize a session",
    )
    parser.add_argument("--dry-run", action="store_true", help="print actions instead of performing them")
    parser.add_argument("--once", help="run a single command and exit")
    parser.add_argument("--profile-dir", default="data/voice_profile", help="where voice samples live")
    parser.add_argument("--enroll", action="store_true", help="record voice samples and exit")
    parser.add_argument(
        "--samples", type=int, default=RECOMMENDED_SAMPLES, help="clips to record when enrolling"
    )
    parser.add_argument("--reset-profile", action="store_true", help="delete enrolled samples and exit")
    parser.add_argument("--verify", action="store_true", help="score one phrase against the profile")
    parser.add_argument(
        "--insecure-voice",
        action="store_true",
        help="skip speaker verification (development only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    profile = VoiceProfile(directory=Path(args.profile_dir), owner=args.owner)

    try:
        if args.reset_profile:
            print(f"Removed {profile.clear()} sample(s) from {profile.directory}.")
            return 0
        if args.enroll:
            return run_enrollment(args, profile)
        if args.verify:
            return run_verify(args, profile)

        if args.once:
            session = Session(owner=args.owner, safety_mode=SafetyMode(args.mode))
            result = execute(parse(args.once), session, dry_run=args.dry_run, confirm=confirm_in_terminal)
            print(result)
            return 0 if result.ok else 1

        if args.input == "voice":
            return run_voice_loop(args, profile)

        session = Session(owner=args.owner, safety_mode=SafetyMode(args.mode))
        print(f"Typed input trusted for {session.owner}. Safety mode: {session.safety_mode.value}")
        return run_text_loop(session, dry_run=args.dry_run)
    except (SpeechUnavailableError, VerifierUnavailableError) as exc:
        print(exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
