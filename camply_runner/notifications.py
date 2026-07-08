from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Any

from camply_runner.campsites import campsite_sort_key, date_field, field, word


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
    def format(
        self,
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
            "<html>",
            "<body>",
            f"<h2>{escape(search_name)}</h2>",
            "<p>"
            f"<strong>{len(matches)}</strong> new matching "
            f"{word(len(matches), 'campsite', 'campsites')} found.<br>"
            f"<strong>{total_matches}</strong> total matching "
            f"{word(total_matches, 'campsite', 'campsites')} currently available."
            "</p>",
        ]

        for (facility_name, booking_date, booking_end_date), campsites in sorted(
            grouped.items()
        ):
            lines.extend(
                [
                    f"<h3>{escape(facility_name)}</h3>",
                    (
                        "<p><strong>"
                        f"{display_date(booking_date)} to "
                        f"{display_date(booking_end_date)}"
                        "</strong></p>"
                    ),
                    "<ul>",
                ]
            )
            for campsite in sorted(campsites, key=campsite_sort_key):
                lines.append(self._format_campsite_item(campsite))
            lines.append("</ul>")

        lines.extend(
            [
                "<p><em>camply, the campsite finder</em></p>",
                "</body>",
                "</html>",
            ]
        )
        return "\n".join(lines)

    def _format_campsite_item(self, campsite: Any) -> str:
        site_name = field(campsite, "campsite_site_name", "Unknown site")
        loop_name = field(campsite, "campsite_loop_name", "Unknown loop")
        campsite_type = field(campsite, "campsite_type", "Unknown type")
        booking_url = field(campsite, "booking_url")

        line = (
            f"<li><strong>Site {escape(site_name)}</strong>"
            f" - {escape(loop_name)}, {escape(campsite_type)}"
        )
        if booking_url:
            escaped_url = escape(booking_url, quote=True)
            line += f'<br><a href="{escaped_url}">{escaped_url}</a>'
        return line + "</li>"


class NotificationError(ValueError):
    pass


def display_date(value: str) -> str:
    return escape(value.split("T", 1)[0])
