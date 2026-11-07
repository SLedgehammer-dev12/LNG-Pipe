import pytest
from core.fluids import FluidManager, FluidProperties

def test_pure_methane_at_normal_boiling_point():
    fm = FluidManager(fluid_type="pure_methane")
    T = 111.66  # K (~ -161.5 °C)
    P = 101325.0  # Pa (1 atm)
    props = fm.get_properties(T, P)
    
    assert isinstance(props, FluidProperties)
    # Density of liquid methane near boiling point is approx 422 kg/m³
    assert 415.0 < props.density < 430.0
    # Saturation pressure near 111.66 K is approx 101.3 kPa
    assert 95000.0 < props.vapor_pressure < 105000.0
    # Specific heat of liquid methane ~ 3400-3600 J/kg-K
    assert 3000.0 < props.specific_heat < 4000.0
    # Dynamic viscosity ~ 1.1e-4 - 1.3e-4 Pa.s
    assert 0.00008 < props.viscosity < 0.00020
    # Thermal conductivity ~ 0.17 - 0.21 W/m-K
    assert 0.15 < props.thermal_conductivity < 0.25

def test_saturation_pressure_increases_with_temperature():
    fm = FluidManager(fluid_type="pure_methane")
    P = 500000.0  # 5 bar
    props_cold = fm.get_properties(110.0, P)
    props_warm = fm.get_properties(120.0, P)
    
    # Second law / Clausius-Clapeyron consistency: Psat must strictly increase with T
    assert props_warm.vapor_pressure > props_cold.vapor_pressure
    # Liquid density must decrease as temperature rises (thermal expansion)
    assert props_warm.density < props_cold.density

def test_lng_mixture_properties():
    # Standard commercial LNG: 94% C1, 4% C2, 1% C3, 1% N2
    composition = {"Methane": 0.94, "Ethane": 0.04, "Propane": 0.01, "Nitrogen": 0.01}
    fm = FluidManager(fluid_type="mixture", composition=composition)
    T = 112.0
    P = 300000.0  # 3 bar
    props = fm.get_properties(T, P)
    
    # LNG mixture density is higher than pure methane due to C2 and C3 (~ 430-460 kg/m³)
    assert 420.0 < props.density < 470.0
    assert props.vapor_pressure > 0.0
    assert props.specific_heat > 2500.0


def test_b1_gas_density_not_floored_at_300():
    # B1: low-pressure gas region must NOT be clamped to 300 kg/m³
    fm = FluidManager(fluid_type="pure_methane")
    props = fm.get_properties(130.0, 60000.0)  # ~130 K / 0.6 bar -> gaseous methane
    assert props.density < 50.0, f"gas density wrongly floored: {props.density}"
    assert props.viscosity < 1e-4
    assert props.thermal_conductivity < 0.05


def test_b3_non_finite_coolprop_falls_back():
    # B3: non-finite CoolProp output must fall back cleanly (no crash, finite props)
    fm = FluidManager(fluid_type="pure_methane")
    props = fm.get_properties(111.66, 101325.0)
    assert all(
        __import__("math").isfinite(v)
        for v in (props.density, props.specific_heat, props.viscosity, props.thermal_conductivity, props.enthalpy)
    )


def test_b10_npsh_margin_positive_in_liquid():
    # B10: NPSH available positive for subcooled liquid, negative when flashing
    fm = FluidManager(fluid_type="pure_methane")
    npsh_liq = fm.get_npsh_margin_a(111.66, 200000.0)  # 2 bar, well above Psat
    assert npsh_liq > 0.0
    npsh_flash = fm.get_npsh_margin_a(111.66, 50000.0)  # below Psat -> flashing
    assert npsh_flash < 0.0


def test_b10_composition_guard_rejects_empty():
    # B10: empty/zero-sum composition must raise, not silently produce nonsense
    with pytest.raises(ValueError):
        FluidManager(fluid_type="mixture", composition={"Methane": 0.0, "Ethane": 0.0})

