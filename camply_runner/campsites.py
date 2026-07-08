from __future__ import annotations

from typing import Any


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
