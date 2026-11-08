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


def test_expanded_coolprop_components_heavy_hc_co2_n2():
    from core.fluids import AVAILABLE_LNG_COMPONENTS, LNG_COMPONENTS_CATALOG

    assert len(AVAILABLE_LNG_COMPONENTS) >= 25
    for expected in (
        "Methane", "Ethane", "Propane", "IsoButane", "n-Butane",
        "Isopentane", "n-Pentane", "Neopentane", "n-Hexane", "n-Heptane",
        "n-Octane", "n-Nonane", "n-Decane", "Nitrogen", "CarbonDioxide",
        "HydrogenSulfide", "Helium", "Hydrogen", "Argon", "Oxygen",
    ):
        assert expected in LNG_COMPONENTS_CATALOG

    heavy_mix = {
        "Methane": 86.0,
        "Ethane": 7.5,
        "Propane": 3.0,
        "IsoButane": 0.8,
        "n-Butane": 0.7,
        "Isopentane": 0.3,
        "n-Pentane": 0.2,
        "n-Hexane": 0.2,
        "n-Octane": 0.05,
        "Nitrogen": 1.0,
        "CarbonDioxide": 0.2,
        "Helium": 0.05,
    }
    fm_heavy = FluidManager(fluid_type="mixture", composition=heavy_mix)
    fm_pure = FluidManager(fluid_type="pure_methane")
    assert fm_heavy.mixture_molar_mass_g_mol() > fm_pure.mixture_molar_mass_g_mol()

    props = fm_heavy.get_properties(112.0, 5.0e5)
    assert 425.0 < props.density < 550.0
    assert 2000.0 < props.specific_heat < 4500.0
    assert props.vapor_pressure > 50000.0


def test_preset_compositions_3d_performance_guard():
    """Guard against CoolProp AbstractState re-instantiation / saturation flash timeouts on multi-component presets."""
    import time
    from core.heat_transfer import InsulationLayer, PipeThermalModel
    from core.solver import PipelineSimulationConfig
    from core.solver_3d import PipelineSolver3D, Solver3DConfig

    gorgon_heavy = {
        "Methane": 88.5, "Ethane": 7.8, "Propane": 2.2, "IsoButane": 0.5,
        "n-Butane": 0.4, "Isopentane": 0.15, "n-Pentane": 0.10, "n-Hexane": 0.05, "Nitrogen": 0.3,
    }
    t0 = time.perf_counter()
    fm = FluidManager(fluid_type="mixture", composition=gorgon_heavy)
    tm = PipeThermalModel(0.2, 0.006, 15.0, [InsulationLayer("PIR", 0.06, 0.024)], 298.15, 3.0)
    cfg = PipelineSimulationConfig(300.0, 0.2, 4.5e-5, 0.0, 111.65, 5e5, 40.0, 50)
    res = PipelineSolver3D(fm, tm, Solver3DConfig(cfg, 12, 12, 50)).solve()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert res.bulk_temperature_k[-1] > 111.65
    # Previously ~4,600 ms; with persistent AbstractState must complete well under 300 ms
    assert elapsed_ms < 300.0, f"Heavy LNG 3D simulation regression: took {elapsed_ms:.1f} ms (> 300 ms)"

