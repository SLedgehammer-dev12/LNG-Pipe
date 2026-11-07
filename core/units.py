"""Centralized unit management for the LNG simulator.

Internal calculation units are SI: K, Pa, kg/s, m, mm, m/s.
Input widgets convert their displayed value to SI with ``to_si``; displays
convert back with ``from_si``. Temperature is affine (°C/°F offsets), so
temperature *differences* use the separate ``delta_*`` helpers.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Unit:
    factor: float
    offset: float = 0.0

    def to_si(self, value: float) -> float:
        return value * self.factor + self.offset

    def from_si(self, value: float) -> float:
        return (value - self.offset) / self.factor

    def delta_to_si(self, delta: float) -> float:
        return delta * self.factor

    def delta_from_si(self, delta: float) -> float:
        return delta / self.factor


UNITS = {
    "temperature": {
        "°C": Unit(1.0, 273.15),
        "K": Unit(1.0),
        "°F": Unit(5.0 / 9.0, 255.37222222222223),
    },
    "pressure": {
        "bar": Unit(1.0e5),
        "kPa": Unit(1.0e3),
        "MPa": Unit(1.0e6),
        "Pa": Unit(1.0),
        "psi": Unit(6894.757),
    },
    "mass_flow": {
        "kg/s": Unit(1.0),
        "kg/h": Unit(1.0 / 3600.0),
        "t/h": Unit(1.0 / 3.6),
        "lb/s": Unit(0.45359237),
    },
    "length": {
        "m": Unit(1.0),
        "km": Unit(1000.0),
        "ft": Unit(0.3048),
        "in": Unit(0.0254),
    },
    "diameter": {
        "mm": Unit(1.0),
        "in": Unit(25.4),
        "m": Unit(1000.0),
    },
    "velocity": {
        "m/s": Unit(1.0),
        "ft/s": Unit(0.3048),
    },
}

DEFAULT_UNITS = {
    "temperature": "°C",
    "pressure": "bar",
    "mass_flow": "kg/s",
    "length": "m",
    "diameter": "mm",
    "velocity": "m/s",
}


def units_for(category: str) -> list[str]:
    """Return the selectable unit labels for a category."""
    return list(UNITS[category].keys())


def to_si(category: str, value: float, unit: str) -> float:
    return UNITS[category][unit].to_si(value)


def from_si(category: str, value: float, unit: str) -> float:
    return UNITS[category][unit].from_si(value)


def delta_to_si(category: str, delta: float, unit: str) -> float:
    return UNITS[category][unit].delta_to_si(delta)


def delta_from_si(category: str, delta: float, unit: str) -> float:
    return UNITS[category][unit].delta_from_si(delta)
