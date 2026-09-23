"""Shared local settings for CLI and Celery; environment overrides the project .env."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / ".env", ".env"), extra="ignore")

    pipeline_fake: bool = False
    stt_backend: Literal["local"] = "local"
    stt_model: str = "large-v3-turbo"
    stt_model_dir: Path = ROOT / "pipeline" / ".models"
    stt_language: Literal["auto", "ru", "kk"] = "auto"
    stt_device: Literal["cpu", "cuda"] = "cpu"
    stt_compute_type: str = "int8"
    stt_cpu_threads: int = Field(default=4, ge=1)
    diarization_model_dir: Path = ROOT / "pipeline" / ".models" / "diarization"
    diarization_num_speakers: int | None = Field(default=None, ge=1, le=50)
    diarization_threshold: float = Field(default=0.5, gt=0.0, lt=2.0)
    diarization_cpu_threads: int = Field(default=4, ge=1, le=32)
