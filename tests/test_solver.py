import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig

def test_pipeline_solver_energy_conservation_and_temperature_rise():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.06, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(
        inner_diameter_m=0.20,
        wall_thickness_m=0.008,
        pipe_conductivity=15.0,
        insulation_layers=layers,
        ambient_temperature_k=300.0,
        wind_speed_m_s=3.0
    )
    
    config = PipelineSimulationConfig(
        length_m=500.0,
        inner_diameter_m=0.20,
        roughness_m=4.5e-5,  # Commercial steel pipe
        inclination_deg=0.0,
        inlet_temperature_k=111.5,
        inlet_pressure_pa=600000.0,  # 6 bar
        mass_flow_rate_kg_s=30.0,
        num_cells=100
    )
    
    solver = PipelineSolver(fluid_manager=fm, thermal_model=thermal_model, config=config)
    results = solver.solve()
    
    # 1. Output temperature must increase (heat ingress from ambient 300 K to 111.5 K LNG)
    assert results.outlet_temperature_k > config.inlet_temperature_k
    assert results.outlet_temperature_k < 116.0  # Well insulated, temperature rises mildly over 500m
    
    # 2. Total pressure must decrease due to friction
    assert results.outlet_pressure_pa < config.inlet_pressure_pa
    
    # 3. Saturation pressure at outlet must increase because T increased
    assert results.outlet_vapor_pressure_pa > results.inlet_vapor_pressure_pa
    
    # 4. In a 6 bar line, pressure stays well above Psat (~ 1.1 bar), so no flashing
    assert results.has_flashed is False
    assert results.min_flashing_margin_pa > 400000.0
    
    # 5. First law conservation: Total Q ≈ m * cp * (Tout - Tin)
    # Average cp ~ 3480 J/kg-K
    expected_q_approx = config.mass_flow_rate_kg_s * 3480.0 * (results.outlet_temperature_k - config.inlet_temperature_k)
    assert pytest.approx(results.total_heat_ingress_w, rel=0.05) == expected_q_approx

def test_pipeline_solver_detects_flashing_when_margin_vanishes():
    fm = FluidManager(fluid_type="pure_methane")
    # Thin insulation / uninsulated pipe causing severe heat leak
    layers = [InsulationLayer(name="Damaged Thin Foam", thickness_m=0.005, thermal_conductivity=0.05)]
    thermal_model = PipeThermalModel(
        inner_diameter_m=0.10,
        wall_thickness_m=0.005,
        pipe_conductivity=15.0,
        insulation_layers=layers,
        ambient_temperature_k=305.0,
        wind_speed_m_s=5.0
    )
    
    # Low inlet pressure (1.2 bar) with high heat leak
    config = PipelineSimulationConfig(
        length_m=300.0,
        inner_diameter_m=0.10,
        roughness_m=4.5e-5,
        inclination_deg=0.0,
        inlet_temperature_k=112.5,
        inlet_pressure_pa=125000.0,  # 1.25 bar
        mass_flow_rate_kg_s=8.0,
        num_cells=100
    )
    
    solver = PipelineSolver(fluid_manager=fm, thermal_model=thermal_model, config=config)
    results = solver.solve()
    
    # Flashing must be detected along the line!
    assert results.has_flashed is True
    assert results.flashing_point_m is not None
    assert 0.0 < results.flashing_point_m < config.length_m
    assert results.min_flashing_margin_pa <= 0.0

def test_hydrostatic_elevation_head():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(
        inner_diameter_m=0.20,
        wall_thickness_m=0.008,
        insulation_layers=layers,
        ambient_temperature_k=295.0
    )
    
    # Compare horizontal vs uphill (inclination 30 degrees, delta z = 100 * sin(30) = 50 m)
    base_kwargs = dict(
        length_m=100.0,
        inner_diameter_m=0.20,
        roughness_m=4.5e-5,
        inlet_temperature_k=111.5,
        inlet_pressure_pa=500000.0,
        mass_flow_rate_kg_s=25.0,
        num_cells=50
    )
    
    config_flat = PipelineSimulationConfig(inclination_deg=0.0, **base_kwargs)
    config_uphill = PipelineSimulationConfig(inclination_deg=30.0, **base_kwargs)
    
    res_flat = PipelineSolver(fm, thermal_model, config_flat).solve()
    res_uphill = PipelineSolver(fm, thermal_model, config_uphill).solve()
    
    # Uphill pipe must have much greater pressure drop due to gravity head: rho * g * delta_z
    # delta_z = 100 * 0.5 = 50 m. rho ~ 422 kg/m³. rho * g * dz ~ 422 * 9.81 * 50 ≈ 207 kPa
    delta_p_flat = config_flat.inlet_pressure_pa - res_flat.outlet_pressure_pa
    delta_p_uphill = config_uphill.inlet_pressure_pa - res_uphill.outlet_pressure_pa
    
    assert delta_p_uphill > delta_p_flat + 180000.0


def test_b2_two_phase_marching_stays_bounded_at_triple_point():
    # B2: when flashing occurs, pressure must not collapse below methane triple point,
    # void fraction must stay in [0,1], and temperature pinned at Tsat(P) (not rising on liquid cp).
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="Bare Thin Foam", thickness_m=0.003, thermal_conductivity=0.08)]
    thermal_model = PipeThermalModel(
        inner_diameter_m=0.08,
        wall_thickness_m=0.004,
        pipe_conductivity=15.0,
        insulation_layers=layers,
        ambient_temperature_k=300.0,
        wind_speed_m_s=10.0,
    )
    config = PipelineSimulationConfig(
        length_m=200.0,
        inner_diameter_m=0.08,
        roughness_m=4.5e-5,
        inclination_deg=0.0,
        inlet_temperature_k=111.5,
        inlet_pressure_pa=60000.0,  # 0.6 bar, near flashing
        mass_flow_rate_kg_s=3.0,
        num_cells=80,
    )
    solver = PipelineSolver(fluid_manager=fm, thermal_model=thermal_model, config=config)
    results = solver.solve()

    # Pressure must never drop below methane triple point (~11.7 kPa)
    assert min(results.pressure_pa) >= 11696.0 - 100.0
    # Void fraction bounded
    assert all(0.0 <= a <= 1.0 for a in results.void_fraction)
    # If flashing occurred, outlet temperature should be pinned at/near saturation, not superheated on liquid cp
    if results.has_flashed:
        assert results.outlet_temperature_k < 115.0
        assert max(results.void_fraction) > 0.0

