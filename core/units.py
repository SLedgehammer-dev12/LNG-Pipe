"""Centralized unit management for the LNG simulator.

Internal calculation units are SI: K, Pa (absolute), kg/s, m, mm, m/s.
Input widgets convert their displayed value to SI with ``to_si``; displays
convert back with ``from_si``. Temperature (°C/°F) and gauge pressure (bar (g),
kPa (g), MPa (g), psi (g), Pa (g)) are affine (have a zero-point offset), so
*differences* (ΔT, ΔP, flashing margin P - Psat, surge ΔP) use the separate
``delta_*`` helpers.
"""

from dataclasses import dataclass

P_ATM_PA = 101325.0  # Standard atmospheric pressure (1.01325 bar)


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
        "bar": Unit(1.0e5, 0.0),
        "bar (g)": Unit(1.0e5, P_ATM_PA),
        "kPa": Unit(1.0e3, 0.0),
        "kPa (g)": Unit(1.0e3, P_ATM_PA),
        "MPa": Unit(1.0e6, 0.0),
        "MPa (g)": Unit(1.0e6, P_ATM_PA),
        "Pa": Unit(1.0, 0.0),
        "Pa (g)": Unit(1.0, P_ATM_PA),
        "psi": Unit(6894.757, 0.0),
        "psi (g)": Unit(6894.757, P_ATM_PA),
        "atm": Unit(P_ATM_PA, 0.0),
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

# Explicit (abs) aliases mapped to the same absolute Unit objects
PRESSURE_ABS_ALIASES = {
    "bar (abs)": UNITS["pressure"]["bar"],
    "bar (a)": UNITS["pressure"]["bar"],
    "barg": UNITS["pressure"]["bar (g)"],
    "bara": UNITS["pressure"]["bar"],
    "kPa (abs)": UNITS["pressure"]["kPa"],
    "kPa (a)": UNITS["pressure"]["kPa"],
    "MPa (abs)": UNITS["pressure"]["MPa"],
    "MPa (a)": UNITS["pressure"]["MPa"],
    "Pa (abs)": UNITS["pressure"]["Pa"],
    "Pa (a)": UNITS["pressure"]["Pa"],
    "psi (abs)": UNITS["pressure"]["psi"],
    "psi (a)": UNITS["pressure"]["psi"],
    "psia": UNITS["pressure"]["psi"],
    "psig": UNITS["pressure"]["psi (g)"],
    "atm (abs)": UNITS["pressure"]["atm"],
}

PRESSURE_DISPLAY_LABELS = {
    "bar": "bar (abs)",
    "bar (abs)": "bar (abs)",
    "bar (g)": "bar (g)",
    "kPa": "kPa (abs)",
    "kPa (abs)": "kPa (abs)",
    "kPa (g)": "kPa (g)",
    "MPa": "MPa (abs)",
    "MPa (abs)": "MPa (abs)",
    "MPa (g)": "MPa (g)",
    "Pa": "Pa (abs)",
    "Pa (abs)": "Pa (abs)",
    "Pa (g)": "Pa (g)",
    "psi": "psi (abs)",
    "psi (abs)": "psi (abs)",
    "psi (g)": "psi (g)",
    "atm": "atm (abs)",
    "atm (abs)": "atm (abs)",
}

DEFAULT_UNITS = {
    "temperature": "°C",
    "pressure": "bar",
    "mass_flow": "kg/s",
    "length": "m",
    "diameter": "mm",
    "velocity": "m/s",
}


def _resolve_unit(category: str, unit: str) -> Unit:
    if category == "pressure" and unit in PRESSURE_ABS_ALIASES:
        return PRESSURE_ABS_ALIASES[unit]
    return UNITS[category][unit]


def units_for(category: str) -> list[str]:
    """Return the selectable unit labels for a category."""
    return list(UNITS[category].keys())


def unit_display_label(category: str, unit: str) -> str:
    """Return human-readable unit label explicitly distinguishing (abs) vs (g) for pressure."""
    if category == "pressure":
        return PRESSURE_DISPLAY_LABELS.get(unit, unit)
    return unit


def delta_unit_display_label(category: str, unit: str) -> str:
    """Return unit label for differential quantities (e.g. ΔP, margin) without abs/g suffix."""
    if category == "pressure":
        lbl = PRESSURE_DISPLAY_LABELS.get(unit, unit)
        return lbl.replace(" (abs)", "").replace(" (g)", "")
    return unit


def to_si(category: str, value: float, unit: str) -> float:
    return _resolve_unit(category, unit).to_si(value)


def from_si(category: str, value: float, unit: str) -> float:
    return _resolve_unit(category, unit).from_si(value)


def delta_to_si(category: str, delta: float, unit: str) -> float:
    return _resolve_unit(category, unit).delta_to_si(delta)


def delta_from_si(category: str, delta: float, unit: str) -> float:
    return _resolve_unit(category, unit).delta_from_si(delta)
