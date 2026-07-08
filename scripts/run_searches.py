#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_DIR = PROJECT_ROOT / "searches"
DEFAULT_STATE_FILE = PROJECT_ROOT / ".cache" / "camply-notifications.json"
NOTIFICATION_TTL = timedelta(days=3)
SKIPPED_NAMES = {"example.yaml", "example.yml"}


def main() -> int:
    apprise_url = os.getenv("APPRISE_URL")
    if not apprise_url:
        print("APPRISE_URL is required to send grouped notifications.", file=sys.stderr)
        return 1

    import apprise  # type: ignore[reportMissingImports]

    notifier = apprise.Apprise()
    if not notifier.add(apprise_url):
        print("APPRISE_URL could not be parsed by Apprise.", file=sys.stderr)
        return 1

    ran_search = False
    search_dir = Path(os.getenv("SEARCH_DIR", DEFAULT_SEARCH_DIR))
    state_file = Path(os.getenv("STATE_FILE", DEFAULT_STATE_FILE))
    now = datetime.now(timezone.utc)
    notified_at_by_key = load_notification_state(
        state_file=state_file,
        now=now,
    )

    for config in iter_search_configs(search_dir):
        ran_search = True
        search_name = config.stem
        print(f"Running Camply search config: {config.name}")
        matches = run_search(config)
        new_matches = [
            campsite
            for campsite in matches
            if notification_key(search_name=search_name, campsite=campsite)
            not in notified_at_by_key
        ]

        if not matches:
            print(f"No matching campsites found for {config.name}")
            continue

        if not new_matches:
            print(
                f"No new matching campsites found for {config.name} "
                f"({len(matches)} already notified in the last 3 days)."
            )
            continue

        title = (
            f"Camply: {search_name} - "
            f"{len(new_matches)} new {word(len(new_matches), 'match', 'matches')}"
        )
        body = format_matches(
            search_name=search_name,
            matches=new_matches,
            total_matches=len(matches),
        )
        print(
            f"Sending grouped notification for {config.name}: "
            f"{len(new_matches)} new {word(len(new_matches), 'match', 'matches')}"
        )
        if not notifier.notify(body=body, title=title):
            print(
                f"Failed to send Apprise notification for {config.name}",
                file=sys.stderr,
            )
            return 1
        for campsite in new_matches:
            notified_at_by_key[
                notification_key(search_name=search_name, campsite=campsite)
            ] = now
        save_notification_state(
            state_file=state_file,
            notified_at_by_key=notified_at_by_key,
        )

    if not ran_search:
        print(f"No enabled search configs found in {search_dir}.")
        print(
            "Copy searches/example.yaml to a new filename and fill in real search criteria."
        )

    return 0


def load_notification_state(
    state_file: Path,
    now: datetime,
) -> dict[str, datetime]:
    if not state_file.exists():
        return {}
    try:
        data = json.loads(state_file.read_text())
    except json.JSONDecodeError:
        print(f"Ignoring unreadable state file: {state_file}", file=sys.stderr)
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
        if now - parsed_notified_at < NOTIFICATION_TTL:
            notified_at_by_key[str(key)] = parsed_notified_at
    return notified_at_by_key


def save_notification_state(
    state_file: Path,
    notified_at_by_key: dict[str, datetime],
) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "notification_ttl_days": NOTIFICATION_TTL.days,
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


def iter_search_configs(search_dir: Path) -> Iterable[Path]:
    for config in sorted([*search_dir.glob("*.yaml"), *search_dir.glob("*.yml")]):
        if config.name in SKIPPED_NAMES or ".disabled." in config.name:
            print(f"Skipping template or disabled search config: {config.name}")
            continue
        yield config


def run_search(config: Path) -> list[Any]:
    from camply.search import CAMPSITE_SEARCH_PROVIDER
    from camply.utils import yaml_utils

    provider, provider_kwargs, search_kwargs = yaml_utils.yaml_file_to_arguments(
        file_path=str(config)
    )
    provider_class = CAMPSITE_SEARCH_PROVIDER[provider]
    camping_finder = provider_class(**provider_kwargs)

    # We own notification formatting here, so Camply should only search.
    search_kwargs.update(
        {
            "continuous": False,
            "notification_provider": "silent",
            "search_forever": False,
            "search_once": False,
        }
    )
    return sorted(
        camping_finder.get_matching_campsites(**search_kwargs),
        key=campsite_sort_key,
    )


def format_matches(
    search_name: str,
    matches: list[Any],
    total_matches: int,
) -> str:
    grouped: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    for campsite in matches:
        grouped[
            (
                field(campsite, "facility_name"),
                date_field(campsite, "booking_date"),
                date_field(campsite, "booking_end_date"),
            )
        ].append(campsite)

    lines = [
        f"{search_name}",
        f"{len(matches)} new matching {word(len(matches), 'campsite', 'campsites')} found.",
        f"{total_matches} total matching {word(total_matches, 'campsite', 'campsites')} currently available.",
        "",
    ]

    for (facility_name, booking_date, booking_end_date), campsites in sorted(
        grouped.items()
    ):
        lines.extend(
            [
                facility_name,
                f"{booking_date} to {booking_end_date}",
            ]
        )
        for campsite in sorted(campsites, key=campsite_sort_key):
            lines.append(format_campsite_line(campsite))
        lines.append("")

    lines.append("camply, the campsite finder")
    return "\n".join(lines)


def format_campsite_line(campsite: Any) -> str:
    site_name = field(campsite, "campsite_site_name", "Unknown site")
    loop_name = field(campsite, "campsite_loop_name", "Unknown loop")
    campsite_type = field(campsite, "campsite_type", "Unknown type")
    booking_url = field(campsite, "booking_url")

    line = f"- Site {site_name}, {loop_name}, {campsite_type}"
    if booking_url:
        line += f"\n  {booking_url}"
    return line


def campsite_sort_key(campsite: Any) -> tuple[str, str, str, str]:
    return (
        date_field(campsite, "booking_date"),
        field(campsite, "facility_name"),
        field(campsite, "campsite_loop_name"),
        field(campsite, "campsite_site_name"),
    )


def notification_key(search_name: str, campsite: Any) -> str:
    return "|".join(
        [
            search_name,
            field(campsite, "campsite_id"),
            field(campsite, "facility_id"),
            date_field(campsite, "booking_date"),
            date_field(campsite, "booking_end_date"),
        ]
    )


def field(campsite: Any, name: str, default: str = "") -> str:
    value = getattr(campsite, name, default)
    if value is None:
        return default
    return str(value)


def date_field(campsite: Any, name: str) -> str:
    value = getattr(campsite, name, "")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def word(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


if __name__ == "__main__":
    raise SystemExit(main())
