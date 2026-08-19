"""Configuration for the assistant: safety modes and the application registry."""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SafetyMode(str, Enum):
    """How much confirmation the assistant asks for before acting."""

    NORMAL = "normal"
    STRICT = "strict"
    FULL_AUTOMATION = "full_automation"


@dataclass(frozen=True)
class AppLaunchSpec:
    """How to launch one application on each supported platform."""

    windows: list[str] = field(default_factory=list)
    linux: list[str] = field(default_factory=list)
    darwin: list[str] = field(default_factory=list)

    def candidates_for(self, system: str) -> list[str]:
        return {
            "Windows": self.windows,
            "Linux": self.linux,
            "Darwin": self.darwin,
        }.get(system, [])


# Spoken name -> launch candidates. The first candidate found on PATH wins.
APP_REGISTRY: dict[str, AppLaunchSpec] = {
    "chrome": AppLaunchSpec(
        windows=["chrome", "chrome.exe"],
        linux=["google-chrome", "google-chrome-stable", "chromium"],
        darwin=["Google Chrome"],
    ),
    "firefox": AppLaunchSpec(
        windows=["firefox"], linux=["firefox"], darwin=["Firefox"]
    ),
    "vscode": AppLaunchSpec(windows=["code"], linux=["code"], darwin=["Visual Studio Code"]),
    "whatsapp": AppLaunchSpec(windows=["whatsapp"], linux=["whatsapp-for-linux"], darwin=["WhatsApp"]),
    "spotify": AppLaunchSpec(windows=["spotify"], linux=["spotify"], darwin=["Spotify"]),
    "terminal": AppLaunchSpec(
        windows=["wt", "powershell"],
        linux=["gnome-terminal", "x-terminal-emulator", "xterm"],
        darwin=["Terminal"],
    ),
    "explorer": AppLaunchSpec(windows=["explorer"], linux=["nautilus", "xdg-open"], darwin=["Finder"]),
    "calculator": AppLaunchSpec(windows=["calc"], linux=["gnome-calculator"], darwin=["Calculator"]),
    "notepad": AppLaunchSpec(windows=["notepad"], linux=["gedit"], darwin=["TextEdit"]),
}

# Spoken aliases mapped onto registry keys.
APP_ALIASES: dict[str, str] = {
    "google chrome": "chrome",
    "browser": "chrome",
    "vs code": "vscode",
    "visual studio code": "vscode",
    "code": "vscode",
    "file explorer": "explorer",
    "files": "explorer",
    "command prompt": "terminal",
    "cmd": "terminal",
    "powershell": "terminal",
    "music": "spotify",
}

# Websites that can be opened by name, e.g. "open facebook".
WEBSITES: dict[str, str] = {
    "facebook": "https://www.facebook.com",
    "youtube": "https://www.youtube.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "whatsapp web": "https://web.whatsapp.com",
}

SEARCH_URL = "https://www.google.com/search?q={query}"

# Named project folders, e.g. {"sightfirst": "C:/code/sightfirst"}. Edit this
# file rather than the code to teach the assistant about your own projects.
PROJECTS_FILE = Path("data/projects.json")


def load_projects(path: Path = PROJECTS_FILE) -> dict[str, str]:
    """Spoken project name -> folder to open. A missing file means no projects."""
    if not path.is_file():
        return {}
    data = json.loads(path.read_text())
    return {" ".join(name.lower().split()): str(folder) for name, folder in data.items()}


def resolve_project(spoken: str, projects: dict[str, str] | None = None) -> str | None:
    """Match a spoken project name, allowing partial names like 'hospital'."""
    known = load_projects() if projects is None else projects
    name = " ".join(spoken.lower().split())
    if name in known:
        return known[name]
    matches = [folder for project, folder in known.items() if name in project or project in name]
    return matches[0] if len(matches) == 1 else None


def current_system() -> str:
    return platform.system()


def resolve_app_name(spoken: str) -> str | None:
    """Map a spoken application name onto a registry key."""
    name = " ".join(spoken.lower().split())
    if name in APP_REGISTRY:
        return name
    return APP_ALIASES.get(name)
