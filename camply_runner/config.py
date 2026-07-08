from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_DIR = PROJECT_ROOT / "searches"
DEFAULT_STATE_FILE = PROJECT_ROOT / ".cache" / "camply-notifications.json"
DEFAULT_NOTIFICATION_TTL = timedelta(days=3)


@dataclass(frozen=True)
class RunnerConfig:
    apprise_url: str
    search_dir: Path = DEFAULT_SEARCH_DIR
    state_file: Path = DEFAULT_STATE_FILE
    notification_ttl: timedelta = DEFAULT_NOTIFICATION_TTL

    @classmethod
    def from_env(cls) -> "RunnerConfig":
        apprise_url = os.getenv("APPRISE_URL")
        if not apprise_url:
            raise ConfigError("APPRISE_URL is required to send grouped notifications.")

        return cls(
            apprise_url=apprise_url,
            search_dir=Path(os.getenv("SEARCH_DIR", DEFAULT_SEARCH_DIR)),
            state_file=Path(os.getenv("STATE_FILE", DEFAULT_STATE_FILE)),
        )


class ConfigError(ValueError):
    pass
