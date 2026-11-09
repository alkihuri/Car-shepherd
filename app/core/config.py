from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class CameraConfig(BaseModel):
    id: str
    name: str
    stream_url: str = ""
    enabled: bool = True
    scan_interval: int | None = None


class GoogleConfig(BaseModel):
    apps_script_url: str = ""
    api_token: str = ""


class TrackingConfig(BaseModel):
    scan_interval: int = Field(default=30, gt=0)
    departure_timeout: int = Field(default=300, gt=0)


class RecognitionConfig(BaseModel):
    confidence_threshold: float = Field(default=0.8, ge=0, le=1)


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    cameras: list[CameraConfig] = Field(default_factory=list)
    google: GoogleConfig = Field(default_factory=GoogleConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    recognition: RecognitionConfig = Field(default_factory=RecognitionConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class RuntimeSettings(BaseModel):
    telegram_enabled: bool = False
    notify_on_arrival: bool = True
    notify_on_departure: bool = True
    telegram_chat_id: str = ""
    scan_interval: int = Field(default=30, gt=0)
    departure_timeout: int = Field(default=300, gt=0)
    recognition_confidence_threshold: float = Field(default=0.8, ge=0, le=1)


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip().strip("\"'")
        os.environ.setdefault(key.strip(), value)


def _expand_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in os.environ:
                raise ValueError(f"Required environment variable {name} is not set")
            return os.environ[name]

        return _ENV_PATTERN.sub(replace, value)
    return value


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    config_path = Path(path)
    _load_dotenv(config_path.parent / ".env")
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(_expand_env(data))
