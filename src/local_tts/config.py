from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    model: str
    device: str
    host: str
    port: int
    voices_dir: Path
    preload: bool
    temperature: float
    top_p: float
    min_p: float
    repetition_penalty: float
    cfg_weight: float
    exaggeration: float
    output_rms_db: float
    output_peak_db: float

    @classmethod
    def from_env(cls) -> "Settings":
        root_dir = Path(__file__).resolve().parents[2]
        voices_default = root_dir / "voices"
        voices_dir = Path(os.getenv("LOCAL_TTS_VOICES_DIR", str(voices_default))).expanduser()
        if not voices_dir.is_absolute():
            voices_dir = (root_dir / voices_dir).resolve()

        return cls(
            model=os.getenv("LOCAL_TTS_MODEL", "chatterbox"),
            device=os.getenv("LOCAL_TTS_DEVICE", "auto"),
            host=os.getenv("LOCAL_TTS_HOST", "127.0.0.1"),
            port=int(os.getenv("LOCAL_TTS_PORT", "8000")),
            voices_dir=voices_dir,
            preload=_bool_env("LOCAL_TTS_PRELOAD", default=False),
            temperature=float(os.getenv("LOCAL_TTS_TEMPERATURE", "0.65")),
            top_p=float(os.getenv("LOCAL_TTS_TOP_P", "0.9")),
            min_p=float(os.getenv("LOCAL_TTS_MIN_P", "0.05")),
            repetition_penalty=float(os.getenv("LOCAL_TTS_REPETITION_PENALTY", "1.15")),
            cfg_weight=float(os.getenv("LOCAL_TTS_CFG_WEIGHT", "0.6")),
            exaggeration=float(os.getenv("LOCAL_TTS_EXAGGERATION", "0.5")),
            output_rms_db=float(os.getenv("LOCAL_TTS_OUTPUT_RMS_DB", "-16.0")),
            output_peak_db=float(os.getenv("LOCAL_TTS_OUTPUT_PEAK_DB", "-1.0")),
        )

    def generation_defaults(self) -> dict[str, float]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "repetition_penalty": self.repetition_penalty,
            "cfg_weight": self.cfg_weight,
            "exaggeration": self.exaggeration,
        }
