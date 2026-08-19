# voice-recognition-AI

A voice-controlled automation assistant, built one layer at a time.

Current state: **Stage 1 (typed command engine) and Stage 2 (speech-to-text) are working.**
Stage 3 (speaker verification) has its interface in place but always trusts the
microphone for now.

## Quick start

```bash
python -m pip install -r requirements-dev.txt
python main.py --dry-run --once "open chrome"     # prints what it would do
python main.py                                    # typed command loop
```

Real execution (no `--dry-run`):

```bash
python main.py --once "open chrome"
python main.py --once "open facebook"
python main.py --once "type hello, I am building my own AI assistant"
```

Voice input (Stage 2):

```bash
python -m pip install -r requirements-voice.txt
python main.py --input voice
```

On Windows, `pip install PyAudio` normally works; on Linux install
`portaudio19-dev` first.

## Commands

| Say / type | Effect |
| --- | --- |
| `open chrome`, `open vs code`, `open whatsapp`, `open terminal` | launches the app |
| `open facebook`, `open youtube`, `open github` | opens the site |
| `open https://…` | opens the URL |
| `search <query>` / `google <query>` | Google search |
| `type <text>` | types into the focused window |
| `help`, `exit` | list commands, quit |

Applications and websites are declared in `assistant/config.py` — add your own
there rather than editing the parser.

## Authorization model

Verification happens **once per session**, then commands run without asking again:

```
similarity 0.96 >= threshold 0.85  ->  SESSION AUTHORIZED  ->  execute
```

Safety modes (`--mode`):

- `normal` — safe commands run immediately, dangerous ones (delete, install,
  shutdown, transfer money, change password) ask for confirmation
- `strict` — every command asks for confirmation
- `full_automation` — nothing asks

Sessions expire after 30 minutes of inactivity and must be re-authorized.

## Layout

```
main.py                            CLI entry point / command loop
assistant/config.py                app registry, websites, safety modes
assistant/commands/parser.py       text -> intent (deterministic, no LLM)
assistant/commands/app_control.py  launch applications
assistant/commands/browser_control.py  open sites and search
assistant/commands/typing_control.py   type into the focused window
assistant/executor.py              intent -> handler, applies safety policy
assistant/security/authorization.py    session + confirmation policy
assistant/voice/listen.py          microphone -> text
assistant/voice/speaker_verification.py  stage 3 interface (stub)
data/voice_profile/                enrolled voice samples (stage 3)
```

## Roadmap

1. ~~Typed command engine~~
2. ~~Speech-to-text~~
3. Speaker verification (SpeechBrain ECAPA embeddings vs. enrolled profile) + wake word
4. LLM reasoning for open-ended requests
5. Multi-step computer agent

## Development

```bash
python -m pytest
python -m ruff check .
```
