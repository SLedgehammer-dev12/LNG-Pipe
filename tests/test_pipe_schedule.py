"""ASME B36.10 / B36.19 pipe schedule table checks."""

from core.pipe_schedule import PIPE_TABLE_GROUPS, inner_diameter_mm


def test_both_standard_groups_present_and_populated():
    assert set(PIPE_TABLE_GROUPS) == {
        "Karbon Çelik (ASME B36.10)",
        "Paslanmaz Çelik (ASME B36.19)",
    }
    for table in PIPE_TABLE_GROUPS.values():
        assert len(table) >= 15
        for label, row in table.items():
            assert row["od_mm"] > 0, label
            assert row["schedules"], label


def test_wall_thicknesses_leave_positive_inner_diameter():
    for group, table in PIPE_TABLE_GROUPS.items():
        for label, row in table.items():
            for schedule, wall in row["schedules"].items():
                assert 0 < wall < row["od_mm"] / 2.0, (group, label, schedule)
                assert inner_diameter_mm(row["od_mm"], wall) > 0


def test_stainless_table_uses_s_schedules():
    for row in PIPE_TABLE_GROUPS["Paslanmaz Çelik (ASME B36.19)"].values():
        assert all(key.endswith("S") for key in row["schedules"])


def test_carbon_table_includes_std_and_xs():
    for row in PIPE_TABLE_GROUPS["Karbon Çelik (ASME B36.10)"].values():
        assert "STD" in row["schedules"]
        assert "XS" in row["schedules"]


def test_dn200_carbon_lists_full_schedule_set():
    expected = {
        "Sch 5", "Sch 10", "Sch 20", "Sch 30", "Sch 40", "STD",
        "Sch 60", "Sch 80", "XS", "Sch 100", "Sch 120", "Sch 140",
        "Sch 160", "XXS",
    }
    actual = set(PIPE_TABLE_GROUPS["Karbon Çelik (ASME B36.10)"]['DN200 (NPS 8")']["schedules"])
    assert actual == expected


def test_inner_diameter_formula():
    assert inner_diameter_mm(219.1, 8.18) == 219.1 - 2.0 * 8.18
