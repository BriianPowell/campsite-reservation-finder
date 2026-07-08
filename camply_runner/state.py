from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


class NotificationStateStore:
    def __init__(self, state_file: Path, notification_ttl: timedelta) -> None:
        self.state_file = state_file
        self.notification_ttl = notification_ttl

    def load(self, now: datetime) -> dict[str, datetime]:
        if not self.state_file.exists():
            return {}
        try:
            data = json.loads(self.state_file.read_text())
        except json.JSONDecodeError:
            print(f"Ignoring unreadable state file: {self.state_file}", file=sys.stderr)
            return {}
        if not isinstance(data, dict):
            return {}

        notifications = data.get("notified")
        if isinstance(notifications, list):
            # Migrate the original timestamp-less state format without spamming.
            return {str(item): now for item in notifications}
        if not isinstance(notifications, dict):
            return {}

        notified_at_by_key: dict[str, datetime] = {}
        for key, notified_at in notifications.items():
            if not isinstance(notified_at, str):
                continue
            parsed_notified_at = parse_datetime(notified_at)
            if parsed_notified_at is None:
                continue
            if now - parsed_notified_at < self.notification_ttl:
                notified_at_by_key[str(key)] = parsed_notified_at
        return notified_at_by_key

    def save(self, notified_at_by_key: dict[str, datetime]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(
                {
                    "notification_ttl_days": self.notification_ttl.days,
                    "notified": {
                        key: notified_at.isoformat()
                        for key, notified_at in sorted(notified_at_by_key.items())
                    },
                },
                indent=2,
            )
            + "\n"
        )


def parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
