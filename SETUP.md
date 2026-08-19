# Setting up the assistant on your own machine

This is the practical guide: install, enroll your voice, tune the threshold,
run it, and troubleshoot. Written for Windows first (macOS/Linux notes at the
end).

---

## 1. Prerequisites

| Requirement | Notes |
| --- | --- |
| Python 3.10+ | `python --version`. Install from python.org and tick **Add python.exe to PATH**. |
| A working microphone | Windows Settings → System → Sound → Input; speak and check the level bar moves. |
| Internet | Needed for speech-to-text (Google Web Speech) and the one-time model download. |
| ~2 GB disk | PyTorch + the ECAPA speaker model. |

## 2. Install

```powershell
git clone https://github.com/emmanuel-tech-pro/voice-recognition-AI.git
cd voice-recognition-AI

python -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements-voice.txt     # everything: typing, mic, speaker model
```

Stage-by-stage installs, if you'd rather not pull PyTorch yet:

| File | Gives you |
| --- | --- |
| `requirements.txt` | typed commands + `type <text>` (pyautogui) |
| `requirements-voice.txt` | the above + microphone, speech-to-text, speaker verification |
| `requirements-dev.txt` | pytest + ruff for development |

If `pip install PyAudio` fails on Windows, install a prebuilt wheel:

```powershell
python -m pip install pipwin
pipwin install pyaudio
```

## 3. Prove the execution engine works (no microphone yet)

```powershell
python main.py --dry-run --once "open chrome"      # prints the command it would run
python main.py --once "open chrome"                # actually opens Chrome
python main.py                                     # typed command loop; type "help"
```

If `open chrome` says it can't find Chrome, the executable isn't on your PATH —
see *Adding your own apps* below.

## 4. Enroll your voice

```powershell
python main.py --enroll
```

It records 5 clips of 4 seconds and writes them to `data/voice_profile/`.
Guidelines that make verification far more reliable:

- Record in the room where you normally work, with the same mic you'll use.
- Speak at your normal volume and pace — don't over-enunciate.
- Vary the phrasing a little (the prompts already do this).
- Re-enroll if you change microphones or headsets.

Manage the profile:

```powershell
python main.py --reset-profile     # delete all samples
python main.py --enroll --samples 8
```

`data/voice_profile/` is gitignored — **your voice samples never leave your
machine and must not be committed.**

## 5. Check your similarity scores and pick a threshold

```powershell
python main.py --verify
```

Speak a sentence; you get something like:

```
Similarity 0.712 vs threshold 0.45 -> MATCH
```

Run it a few times, then have someone else run it while you watch:

| Speaker | Typical cosine score |
| --- | --- |
| You (same mic, same room) | 0.55 – 0.85 |
| Someone else | 0.05 – 0.35 |

Pick a threshold between the two clusters — the default is `0.45`:

```powershell
python main.py --input voice --threshold 0.55
```

Higher threshold = more secure, more re-tries. Lower = more convenient, more
risk that a similar voice gets in.

The first `--verify` run downloads the ECAPA model (~80 MB) into
`data/models/`; later runs are fast.

## 6. Run it for real

```powershell
python main.py --input voice
```

The flow:

```
say "Hey assistant"                -> speaker verification runs
similarity 0.71 >= threshold 0.45  -> SESSION AUTHORIZED
"open chrome"                      -> Chrome opens        (no re-verification)
"open facebook"                    -> Facebook opens
"type hello John"                  -> types into the focused window
30 minutes idle                    -> session expires, wake word needed again
```

Wake phrases accepted: `hey assistant`, `hey salem`, `ok assistant`,
`hey system`. You can chain the first command onto the wake word:
"Hey assistant, open chrome".

Useful flags:

| Flag | Effect |
| --- | --- |
| `--mode strict` | confirm every command |
| `--mode full_automation` | never confirm, even dangerous commands |
| `--dry-run` | print actions instead of performing them |
| `--insecure-voice` | skip speaker verification (debugging only) |
| `--owner "Salem"` | name used in prompts and the profile metadata |
| `--profile-dir PATH` | use a different voice profile |

## 7. Start it when Windows starts

Task Scheduler is more reliable than the Startup folder because it can run
hidden and restart on failure:

1. Create `run_assistant.bat` in the repo root:

   ```bat
   @echo off
   cd /d "%~dp0"
   call .venv\Scripts\activate
   python main.py --input voice
   ```

2. Task Scheduler → **Create Task**
   - General: *Run only when user is logged on* (it needs your desktop session
     to open apps and type)
   - Triggers: *At log on*
   - Actions: Start a program → your `run_assistant.bat`
   - Conditions: untick *Start the task only if the computer is on AC power*

Do **not** run it as SYSTEM or as admin — it would then be able to type into
elevated windows, and any misfire becomes much more damaging.

## 8. Adding your own apps and sites

Everything is data in `assistant/config.py` — no parser changes needed:

```python
APP_REGISTRY["obs"] = AppLaunchSpec(
    windows=[r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"],
    linux=["obs"],
)
APP_ALIASES["streaming"] = "obs"
WEBSITES["notion"] = "https://www.notion.so"
```

Launching looks for each candidate on your PATH, so either add the app's folder
to PATH or put the full `.exe` path in the list. Then `"open obs"` and
`"open streaming"` both work.

## 9. How the security model actually works

```
wake word heard
   -> ECAPA embedding of that utterance
   -> cosine similarity vs the mean of your enrolled embeddings
   -> similarity >= threshold ? open Session : ignore
Session: owner, similarity, threshold, safety mode, 30 min idle timeout
   -> every executed command calls session.refresh()
```

- Verification happens **once per session**, not per command.
- `normal` mode still confirms dangerous commands (delete, remove, format,
  shutdown, restart, install/uninstall, transfer, change password) — the intent
  is classified in `assistant/commands/parser.py:DANGEROUS_PATTERNS`.
- Speaker verification is a convenience gate, not a cryptographic one: a good
  recording of your voice can pass it. Keep dangerous actions in `normal` or
  `strict` mode, and don't wire it up to anything financial.
- Audio is sent to Google's free Web Speech endpoint for transcription; the
  speaker verification itself runs fully offline. To keep everything local,
  swap `recognize_google` in `assistant/voice/listen.py` for
  `recognize_whisper` (needs `pip install openai-whisper`).

## 10. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Install the voice extras` | `pip install -r requirements-voice.txt` (activate the venv first) |
| `No voice samples in data/voice_profile` | run `python main.py --enroll` |
| Nothing is heard / it never reacts | check the Windows default input device; try `--input text` to confirm the engine works |
| It reacts to silence or noise | pass a fixed threshold: `MicrophoneListener(energy_threshold=300)` in `run_voice_loop` |
| Wake word never matches | check the `Heard:` line — the transcriber may render it differently; add that spelling to `DEFAULT_WAKE_WORDS` in `assistant/voice/wake_word.py` |
| Your own voice scores low | re-enroll with the mic you actually use; lower `--threshold` slightly |
| Someone else gets in | raise `--threshold` (0.55–0.65) and re-enroll with more samples |
| `PyAudio` build error | use `pipwin install pyaudio` (Windows) or `sudo apt install portaudio19-dev` (Linux) |
| `type hello` does nothing | pyautogui types into the *focused* window — click the target window first |
| Model download is slow/blocked | it comes from Hugging Face; a proxy or firewall may block it |

## 11. macOS / Linux differences

- Install PortAudio first: `brew install portaudio` or
  `sudo apt install portaudio19-dev python3-pyaudio`.
- macOS asks for **Microphone** and **Accessibility** permissions the first
  time (System Settings → Privacy & Security); typing won't work until
  Accessibility is granted to your terminal.
- Apps launch via `open -a "Google Chrome"` on macOS and via PATH lookup on
  Linux; adjust `APP_REGISTRY` for your distro's binary names.

## 12. Development

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
```

The command engine, session policy, profile handling and wake-word matching are
all covered by tests that need no microphone; audio capture and the ECAPA model
are injected behind interfaces so they can be faked.

## 13. What comes next (stages 4-5)

- **Stage 4 — LLM reasoning:** an interpreter that turns "I want to continue
  working on my hospital website" into a list of known intents, falling back to
  the deterministic parser. Keep the parser as the fast path.
- **Stage 5 — computer agent:** multi-step plans (open editor → open project →
  run backend → run frontend → report errors) with per-step confirmation in
  `strict` mode.
