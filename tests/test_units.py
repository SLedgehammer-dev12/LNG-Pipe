"""Unit management round-trip and offset checks."""

import pytest

from core.units import DEFAULT_UNITS, UNITS, delta_from_si, delta_to_si, from_si, to_si, units_for


@pytest.mark.parametrize("category", list(UNITS))
def test_round_trip_all_units(category):
    for unit in units_for(category):
        value = 12.345
        assert from_si(category, to_si(category, value, unit), unit) == pytest.approx(value, rel=1e-12)


def test_temperature_offsets():
    assert to_si("temperature", -161.5, "°C") == pytest.approx(111.65)
    assert to_si("temperature", -258.7, "°F") == pytest.approx(111.65, rel=1e-6)
    assert from_si("temperature", 111.65, "K") == pytest.approx(111.65)


def test_temperature_delta_has_no_offset():
    assert delta_from_si("temperature", 0.14, "°C") == pytest.approx(0.14)
    assert delta_from_si("temperature", 0.14, "°F") == pytest.approx(0.252)
    assert delta_to_si("temperature", 0.252, "°F") == pytest.approx(0.14, rel=1e-6)


def test_pressure_defaults_to_bar():
    assert DEFAULT_UNITS["pressure"] == "bar"
    assert to_si("pressure", 5.0, "bar") == pytest.approx(5.0e5)
    assert from_si("pressure", 5.0e5, "psi") == pytest.approx(72.5189, rel=1e-4)


def test_flow_conversions():
    assert to_si("mass_flow", 40.0, "kg/s") == pytest.approx(40.0)
    assert to_si("mass_flow", 144.0, "t/h") == pytest.approx(40.0)
    assert from_si("mass_flow", 40.0, "kg/h") == pytest.approx(144000.0)
