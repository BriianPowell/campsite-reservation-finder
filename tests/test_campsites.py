from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from camply_runner.campsites import (
    campsite_sort_key,
    date_field,
    field,
    notification_key,
    word,
)


def test_notification_key_uses_search_site_facility_and_dates() -> None:
    campsite = SimpleNamespace(
        campsite_id=123,
        facility_id=456,
        booking_date=date(2026, 8, 6),
        booking_end_date=date(2026, 8, 9),
    )

    assert notification_key("recreation-big-sur-inyo", campsite) == (
        "recreation-big-sur-inyo|123|456|2026-08-06|2026-08-09"
    )


def test_campsite_sort_key_orders_by_date_facility_loop_and_site() -> None:
    campsite = SimpleNamespace(
        booking_date="2026-08-06",
        facility_name="Lone Pine",
        campsite_loop_name="PINE",
        campsite_site_name="042",
    )

    assert campsite_sort_key(campsite) == (
        "2026-08-06",
        "Lone Pine",
        "PINE",
        "042",
    )


def test_field_and_date_helpers_handle_missing_none_and_date_values() -> None:
    campsite = SimpleNamespace(name=None, booking_date=date(2026, 8, 6))

    assert field(campsite, "missing", "fallback") == "fallback"
    assert field(campsite, "name", "fallback") == "fallback"
    assert date_field(campsite, "booking_date") == "2026-08-06"
    assert date_field(campsite, "missing") == ""


def test_word_pluralizes_by_count() -> None:
    assert word(1, "match", "matches") == "match"
    assert word(2, "match", "matches") == "matches"
