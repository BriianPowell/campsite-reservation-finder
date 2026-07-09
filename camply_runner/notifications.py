from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from jinja2 import (  # type: ignore[reportMissingImports]
    Environment,
    FileSystemLoader,
)

from camply_runner.campsites import campsite_sort_key, date_field, field, word

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


class AppriseNotifier:
    def __init__(self, apprise_url: str) -> None:
        import apprise  # type: ignore[reportMissingImports]

        self._apprise = apprise
        self._notifier = apprise.Apprise()
        if not self._notifier.add(apprise_url):
            raise NotificationError("APPRISE_URL could not be parsed by Apprise.")

    def notify_matches(
        self,
        search_name: str,
        matches: list[Any],
        total_matches: int,
    ) -> bool:
        title = (
            f"Camply: {search_name} - "
            f"{len(matches)} new {word(len(matches), 'match', 'matches')}"
        )
        body = HtmlMatchFormatter().format(
            search_name=search_name,
            matches=matches,
            total_matches=total_matches,
        )
        return bool(
            self._notifier.notify(
                body=body,
                title=title,
                body_format=self._apprise.NotifyFormat.HTML,
            )
        )


class HtmlMatchFormatter:
    def __init__(self) -> None:
        self._template = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=True,
        ).get_template("matches_email.html.j2")

    def format(
        self,
        search_name: str,
        matches: list[Any],
        total_matches: int,
    ) -> str:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for campsite in matches:
            grouped[field(campsite, "facility_name", "Unknown campground")].append(
                campsite
            )

        campgrounds = [
            {
                "name": facility_name,
                "campsites": [
                    self._format_campsite_row(campsite)
                    for campsite in sorted(campsites, key=campsite_sort_key)
                ],
            }
            for facility_name, campsites in sorted(grouped.items())
        ]

        return self._template.render(
            search_name=search_name,
            new_match_count=len(matches),
            total_matches=total_matches,
            campgrounds=campgrounds,
        )

    def _format_campsite_row(self, campsite: Any) -> dict[str, str]:
        booking_date = date_field(campsite, "booking_date")
        booking_end_date = date_field(campsite, "booking_end_date")

        return {
            "dates": f"{display_date(booking_date)} to {display_date(booking_end_date)}",
            "site": format_site_name(
                field(campsite, "campsite_site_name", "Unknown site")
            ),
            "loop": field(campsite, "campsite_loop_name", "Unknown loop"),
            "type": field(campsite, "campsite_type", "Unknown type"),
            "use": field(campsite, "campsite_use_type"),
            "occupancy": format_occupancy(getattr(campsite, "campsite_occupancy", "")),
            "equipment": format_permitted_equipment(
                getattr(campsite, "permitted_equipment", "")
            ),
            "booking_url": field(campsite, "booking_url"),
        }


class NotificationError(ValueError):
    pass


def display_date(value: str) -> str:
    return value.split("T", 1)[0]


def format_site_name(value: str) -> str:
    return value.removeprefix("Site:").strip()


def format_occupancy(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (tuple, list)) and len(value) == 2:
        minimum, maximum = value
        return f"{minimum}-{maximum} people"
    return str(value)


def format_permitted_equipment(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(format_equipment_item(item) for item in value)
    return format_equipment_item(value)


def format_equipment_item(value: Any) -> str:
    equipment_name = getattr(value, "equipment_name", None)
    if equipment_name:
        max_length = getattr(value, "max_length", None)
        if max_length:
            try:
                formatted_length = f"{float(max_length):g}"
            except (TypeError, ValueError):
                formatted_length = str(max_length)
            return f"{equipment_name} up to {formatted_length} ft"
        return str(equipment_name)
    return str(value)
