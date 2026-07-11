from __future__ import annotations

from types import SimpleNamespace

from camply_runner.notifications import HtmlMatchFormatter


def test_email_template_groups_campsites_by_campground_table() -> None:
    body = HtmlMatchFormatter().format(
        search_name="recreation-big-sur-inyo",
        total_matches=2,
        matches=[
            SimpleNamespace(
                facility_name="Lone <Pine>",
                booking_date="2026-08-06T00:00:00",
                booking_end_date="2026-08-09T00:00:00",
                campsite_site_name="Site: 042",
                campsite_loop_name="PINE",
                campsite_type="WALK TO",
                campsite_use_type="Overnight",
                campsite_occupancy=(0, 6),
                permitted_equipment=[
                    SimpleNamespace(equipment_name="Tent", max_length=None),
                    SimpleNamespace(equipment_name="RV", max_length=30.0),
                    SimpleNamespace(equipment_name="Trailer", max_length=30.0),
                    SimpleNamespace(
                        equipment_name="Large Tent Over 9X12", max_length=None
                    ),
                    SimpleNamespace(equipment_name="Pickup Camper", max_length=30.0),
                    SimpleNamespace(equipment_name="Pop up", max_length=30.0),
                    SimpleNamespace(
                        equipment_name="Caravan/Camper Van", max_length=None
                    ),
                    SimpleNamespace(equipment_name="Fifth Wheel", max_length=30.0),
                    SimpleNamespace(equipment_name="Small Tent", max_length=None),
                ],
                booking_url="https://www.recreation.gov/camping/campsites/67118",
            ),
            SimpleNamespace(
                facility_name="Lone <Pine>",
                booking_date="2026-08-13T00:00:00",
                booking_end_date="2026-08-16T00:00:00",
                campsite_site_name="043",
                campsite_loop_name="PINE",
                campsite_type="STANDARD NONELECTRIC",
                campsite_use_type="Overnight",
                campsite_occupancy=(0, 8),
                permitted_equipment=[],
                booking_url="",
            ),
        ],
    )

    assert body.count("<h3>Lone &lt;Pine&gt;</h3>") == 1
    assert '<table border="1" cellpadding="6" cellspacing="0">' in body
    assert body.count("<tr>") == 3
    assert "<th>Dates</th>" in body
    assert "<th>Loop</th>" not in body
    assert "<td>2026-08-06 to 2026-08-09</td>" in body
    assert "<td>042</td>" in body
    assert "Site: 042" not in body
    assert "<td>WALK TO</td>" in body
    assert "<td>Overnight</td>" in body
    assert "<td>6 people</td>" in body
    assert (
        "<td>Small Tent<br>Tent<br>Large Tent Over 9X12<br>RV<br>Trailer<br>"
        "Pickup Camper<br>Pop up<br>Caravan/Camper Van<br>Fifth Wheel</td>"
    ) in body
    assert (
        '<a href="https://www.recreation.gov/camping/campsites/67118">Book</a>' in body
    )
    assert "T00:00:00" not in body
