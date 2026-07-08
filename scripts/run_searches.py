#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import apprise  # type: ignore[reportMissingImports]
from camply.search import CAMPSITE_SEARCH_PROVIDER
from camply.utils import yaml_utils

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_DIR = PROJECT_ROOT / "searches"
SKIPPED_NAMES = {"example.yaml", "example.yml"}


def main() -> int:
    apprise_url = os.getenv("APPRISE_URL")
    if not apprise_url:
        print("APPRISE_URL is required to send grouped notifications.", file=sys.stderr)
        return 1

    notifier = apprise.Apprise()
    if not notifier.add(apprise_url):
        print("APPRISE_URL could not be parsed by Apprise.", file=sys.stderr)
        return 1

    ran_search = False
    search_dir = Path(os.getenv("SEARCH_DIR", DEFAULT_SEARCH_DIR))

    for config in iter_search_configs(search_dir):
        ran_search = True
        search_name = config.stem
        print(f"Running Camply search config: {config.name}")
        matches = run_search(config)

        if not matches:
            print(f"No matching campsites found for {config.name}")
            continue

        title = f"Camply: {search_name} - {len(matches)} {word(len(matches), 'match', 'matches')}"
        body = format_matches(search_name=search_name, matches=matches)
        print(
            f"Sending grouped notification for {config.name}: "
            f"{len(matches)} {word(len(matches), 'match', 'matches')}"
        )
        if not notifier.notify(body=body, title=title):
            print(
                f"Failed to send Apprise notification for {config.name}",
                file=sys.stderr,
            )
            return 1

    if not ran_search:
        print(f"No enabled search configs found in {search_dir}.")
        print(
            "Copy searches/example.yaml to a new filename and fill in real search criteria."
        )

    return 0


def iter_search_configs(search_dir: Path) -> Iterable[Path]:
    for config in sorted([*search_dir.glob("*.yaml"), *search_dir.glob("*.yml")]):
        if config.name in SKIPPED_NAMES or ".disabled." in config.name:
            print(f"Skipping template or disabled search config: {config.name}")
            continue
        yield config


def run_search(config: Path) -> list[Any]:
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


def format_matches(search_name: str, matches: list[Any]) -> str:
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
        f"{len(matches)} matching {word(len(matches), 'campsite', 'campsites')} found.",
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
