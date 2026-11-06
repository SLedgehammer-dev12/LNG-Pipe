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
