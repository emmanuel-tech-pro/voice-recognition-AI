"""Storage for the owner's enrolled voice samples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PROFILE_DIR = Path("data/voice_profile")
SAMPLE_SUFFIX = ".wav"
METADATA_FILE = "profile.json"
RECOMMENDED_SAMPLES = 5


@dataclass(frozen=True)
class VoiceProfile:
    """The enrolled samples for one owner, stored as WAV files on disk."""

    directory: Path = DEFAULT_PROFILE_DIR
    owner: str = "Salem"

    @property
    def metadata_path(self) -> Path:
        return self.directory / METADATA_FILE

    def samples(self) -> list[Path]:
        if not self.directory.is_dir():
            return []
        return sorted(p for p in self.directory.glob(f"*{SAMPLE_SUFFIX}") if p.is_file())

    @property
    def enrolled(self) -> bool:
        return bool(self.samples())

    def add_sample(self, wav_bytes: bytes) -> Path:
        """Persist one recorded sample and return its path."""
        self.directory.mkdir(parents=True, exist_ok=True)
        index = len(self.samples()) + 1
        path = self.directory / f"sample_{index:02d}{SAMPLE_SUFFIX}"
        path.write_bytes(wav_bytes)
        self._write_metadata()
        return path

    def clear(self) -> int:
        """Delete all enrolled samples; returns how many were removed."""
        removed = 0
        for path in self.samples():
            path.unlink()
            removed += 1
        if self.metadata_path.exists():
            self.metadata_path.unlink()
        return removed

    def _write_metadata(self) -> None:
        self.metadata_path.write_text(
            json.dumps({"owner": self.owner, "samples": len(self.samples())}, indent=2)
        )
