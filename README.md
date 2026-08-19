# voice-recognition-AI

A voice-controlled automation assistant, built one layer at a time.

Current state: **Stages 1-4 are working** — typed commands, speech-to-text,
speaker verification that only authorizes the enrolled owner, and optional LLM
reasoning for phrases the deterministic parser does not know.

Full install / enrollment / tuning / troubleshooting guide: [SETUP.md](SETUP.md).

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

Voice (Stages 2-3):

```bash
python -m pip install -r requirements-voice.txt
python main.py --enroll        # record 5 samples of your voice
python main.py --verify        # score one phrase, to tune --threshold
python main.py --input voice   # wake word -> verification -> commands
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
| `open my hospital project`, `open sightfirst` | opens a registered project folder in VS Code |
| `help`, `exit` | list commands, quit |

Applications and websites are declared in `assistant/config.py` — add your own
there rather than editing the parser. Projects live in `data/projects.json`
(copy `data/projects.example.json`), so paths stay on your machine.

## Stage 4: reasoning for open-ended requests

The deterministic parser is always tried first and never calls a model. Only
when nothing matches — "I want to continue working on my hospital website" —
is the request sent to an LLM, which must reply with a short JSON plan:

```bash
python -m pip install -r requirements-llm.txt

# hosted
set OPENAI_API_KEY=sk-...
python main.py --llm --input voice

# or fully local (Ollama)
ollama serve && ollama pull llama3.1
python main.py --llm --llm-model llama3.1 --llm-base-url http://localhost:11434/v1
```

```
"I want to continue working on my hospital website"
Plan (2 steps):
  1. open_app: vscode
  2. open_project: sightfirst hospital
```

The model cannot invent actions. Its reply is validated against an allowlist —
`open_app`, `open_project`, `open_site`, `open_url`, `search`, `type` — capped
at 6 steps, and anything else is dropped; a plan with nothing valid falls back
to "I did not understand". There is no shell execution path, and every step
still goes through the same session and confirmation policy as typed commands.

## Authorization model

The wake word (`hey assistant`) triggers speaker verification on that same
utterance; ECAPA-TDNN embeddings of the live audio are compared by cosine
similarity against the mean of your enrolled samples. Verification happens
**once per session** — commands then run without asking again:

```
"hey assistant"  ->  similarity 0.71 >= threshold 0.45  ->  SESSION AUTHORIZED
"open chrome"    ->  executes, no re-verification
```

Other voices score far below the threshold and are ignored. Tune the threshold
with `python main.py --verify` (see SETUP.md); `--insecure-voice` bypasses
verification for development only.

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
assistant/commands/project_control.py  open a registered project in VS Code
assistant/reasoning/interpreter.py     LLM plan -> validated intents (Stage 4)
assistant/executor.py              intent -> handler, applies safety policy
assistant/security/authorization.py    session + confirmation policy
assistant/voice/listen.py          microphone -> audio + text
assistant/voice/wake_word.py       wake phrase matching
assistant/voice/enrollment.py      record the owner's samples
assistant/voice/profile.py         voice profile storage
assistant/voice/speaker_verification.py  ECAPA embeddings + cosine similarity
data/voice_profile/                your enrolled samples (gitignored)
```

## Roadmap

1. ~~Typed command engine~~
2. ~~Speech-to-text~~
3. ~~Speaker verification (SpeechBrain ECAPA embeddings vs. enrolled profile) + wake word~~
4. ~~LLM reasoning for open-ended requests (allowlisted multi-step plans)~~
5. Multi-step computer agent

## Development

```bash
python -m pytest
python -m ruff check .
```
