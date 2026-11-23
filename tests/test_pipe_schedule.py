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


def test_b36_19_includes_unscheduled_mm_thicknesses():
    from core.pipe_schedule import get_wall_thickness_options

    ss_group = "Paslanmaz Çelik (ASME B36.19)"
    ss_table = PIPE_TABLE_GROUPS[ss_group]
    for dn_label, row in ss_table.items():
        assert len(row.get("unscheduled_mm", [])) >= 5, dn_label
        opts = get_wall_thickness_options(ss_group, dn_label)
        # Contains both S-schedules and unscheduled mm options
        assert any("S (" in k for k in opts), dn_label
        assert any("Schedule'sız" in k for k in opts), dn_label
        for opt_lbl, wall_mm in opts.items():
            assert 0.0 < wall_mm < row["od_mm"] / 2.0, (dn_label, opt_lbl)


def test_b36_19_and_b36_10_standards_accuracy():
    ss_table = PIPE_TABLE_GROUPS["Paslanmaz Çelik (ASME B36.19)"]
    cs_table = PIPE_TABLE_GROUPS["Karbon Çelik (ASME B36.10)"]

    # ASME B36.19M 40S = 9.53 mm (STD) for DN300-DN600; 80S = 12.70 mm (XS) for DN250-DN600
    assert ss_table['DN250 (NPS 10")']["schedules"]["80S"] == 12.70
    for dn in ('DN300 (NPS 12")', 'DN350 (NPS 14")', 'DN400 (NPS 16")', 'DN450 (NPS 18")', 'DN500 (NPS 20")', 'DN600 (NPS 24")'):
        assert ss_table[dn]["schedules"]["40S"] == 9.53
        assert ss_table[dn]["schedules"]["80S"] == 12.70

    # ASME B36.19M 10S for DN350-DN500
    assert ss_table['DN350 (NPS 14")']["schedules"]["10S"] == 4.78
    assert ss_table['DN400 (NPS 16")']["schedules"]["10S"] == 4.78
    assert ss_table['DN450 (NPS 18")']["schedules"]["10S"] == 4.78
    assert ss_table['DN500 (NPS 20")']["schedules"]["10S"] == 5.54

    # ASME B36.10M DN100/125/150 non-existent schedule cleanup & true Sch 160 values
    assert "Sch 140" not in cs_table['DN100 (NPS 4")']["schedules"]
    assert cs_table['DN100 (NPS 4")']["schedules"]["Sch 160"] == 13.49
    assert "Sch 140" not in cs_table['DN125 (NPS 5")']["schedules"]
    assert cs_table['DN125 (NPS 5")']["schedules"]["Sch 160"] == 15.88
    assert "Sch 100" not in cs_table['DN150 (NPS 6")']["schedules"]

