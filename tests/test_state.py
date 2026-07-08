from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from camply_runner.state import NotificationStateStore, parse_datetime


def test_state_store_saves_and_loads_recent_notifications(tmp_path) -> None:
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    state_file = tmp_path / "state.json"
    store = NotificationStateStore(
        state_file=state_file,
        notification_ttl=timedelta(days=3),
    )

    assert store.load(now=now) == {}

    store.save({"fresh": now})

    assert store.load(now=now) == {"fresh": now}
    assert json.loads(state_file.read_text()) == {
        "notification_ttl_days": 3,
        "notified": {"fresh": "2026-07-08T00:00:00+00:00"},
    }


def test_state_store_prunes_expired_notifications(tmp_path) -> None:
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    fresh = now - timedelta(days=2, hours=23)
    expired = now - timedelta(days=3, seconds=1)
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "notified": {
                    "fresh": fresh.isoformat(),
                    "expired": expired.isoformat(),
                    "invalid": "not-a-date",
                }
            }
        )
    )
    store = NotificationStateStore(
        state_file=state_file,
        notification_ttl=timedelta(days=3),
    )

    assert store.load(now=now) == {"fresh": fresh}


def test_state_store_migrates_legacy_list_format_without_spamming(tmp_path) -> None:
    now = datetime(2026, 7, 8, tzinfo=timezone.utc)
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"notified": ["legacy-key"]}))
    store = NotificationStateStore(
        state_file=state_file,
        notification_ttl=timedelta(days=3),
    )

    assert store.load(now=now) == {"legacy-key": now}


def test_parse_datetime_assumes_utc_for_naive_values() -> None:
    assert parse_datetime("2026-07-08T12:00:00") == datetime(
        2026,
        7,
        8,
        12,
        tzinfo=timezone.utc,
    )
