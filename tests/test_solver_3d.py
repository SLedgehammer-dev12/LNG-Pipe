import pytest
import numpy as np
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSimulationConfig
from core.solver_3d import PipelineSolver3D, Solver3DConfig, Simulation3DResults

def test_solver_3d_grid_and_radial_boundary_layer():
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
    
    pipe_cfg = PipelineSimulationConfig(
        length_m=300.0,
        inner_diameter_m=0.20,
        roughness_m=4.5e-5,
        inclination_deg=0.0,
        inlet_temperature_k=111.5,
        inlet_pressure_pa=500000.0,
        mass_flow_rate_kg_s=25.0,
        num_cells=50
    )
    
    cfg_3d = Solver3DConfig(
        pipeline_config=pipe_cfg,
        n_radial=10,
        n_azimuthal=12,
        n_axial=50
    )
    
    solver_3d = PipelineSolver3D(fluid_manager=fm, thermal_model=thermal_model, config=cfg_3d)
    results = solver_3d.solve()
    
    assert isinstance(results, Simulation3DResults)
    # Check 3D tensor shapes (n_axial + 1, n_radial, n_azimuthal)
    assert results.temp_field_k.shape == (51, 10, 12)
    assert len(results.distance_m) == 51
    assert len(results.pressure_pa) == 51
    
    # Check radial thermal boundary layer:
    # Wall temperature (outermost radial shell r[-1]) must be hotter than centerline (r[0])
    outlet_idx = -1
    t_center = results.temp_field_k[outlet_idx, 0, :].mean()
    t_wall = results.temp_field_k[outlet_idx, -1, :].mean()
    assert t_wall > t_center
    
    # Total pressure must decrease along pipe
    assert results.pressure_pa[-1] < results.pressure_pa[0]
    
    # Bulk temperature must be between center and wall
    assert t_center < results.bulk_temperature_k[-1] <= t_wall

def test_solver_3d_detects_wall_flashing_before_bulk():
    fm = FluidManager(fluid_type="pure_methane")
    # Moderate insulation with low pressure line to trigger wall boiling
    layers = [InsulationLayer(name="Standard Foam", thickness_m=0.02, thermal_conductivity=0.035)]
    thermal_model = PipeThermalModel(
        inner_diameter_m=0.10,
        wall_thickness_m=0.005,
        pipe_conductivity=15.0,
        insulation_layers=layers,
        ambient_temperature_k=305.0
    )
    
    pipe_cfg = PipelineSimulationConfig(
        length_m=200.0,
        inner_diameter_m=0.10,
        roughness_m=4.5e-5,
        inlet_temperature_k=112.0,
        inlet_pressure_pa=130000.0,  # 1.3 bar
        mass_flow_rate_kg_s=6.0,
        num_cells=40
    )
    
    cfg_3d = Solver3DConfig(
        pipeline_config=pipe_cfg,
        n_radial=10,
        n_azimuthal=8,
        n_axial=40
    )
    
    solver_3d = PipelineSolver3D(fluid_manager=fm, thermal_model=thermal_model, config=cfg_3d)
    results = solver_3d.solve()
    
    # Near-wall flashing must occur at or before bulk flashing
    assert results.has_wall_flashed is True
    if results.has_bulk_flashed:
        assert results.wall_flashing_point_m <= results.bulk_flashing_point_m


def test_simulation_3d_results_unified_interface_and_hot_reload_resilience():
    import importlib
    import core.solver_3d as s3d_mod
    from components.pipeline_schematic_2d import generate_schematic_2d_html
    from components.terminal_3d_viewer import generate_terminal_3d_html
    from components.pipe_3d_viewer import generate_3d_pipe_html
    from components.charts_2d import (
        create_pressure_comparison_chart,
        create_temperature_profile_chart,
        create_flashing_margin_chart,
    )

    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=layers)
    pipe_cfg = PipelineSimulationConfig(length_m=300.0, inner_diameter_m=0.20, num_cells=20)
    cfg_3d = Solver3DConfig(pipeline_config=pipe_cfg, n_radial=8, n_azimuthal=8, n_axial=20)
    res_3d = PipelineSolver3D(fluid_manager=fm, thermal_model=thermal_model, config=cfg_3d).solve()

    # 1. Unified 1D/3D interface properties on Simulation3DResults & Solver3DConfig
    assert res_3d.outlet_temperature_k == pytest.approx(res_3d.bulk_temperature_k[-1])
    assert res_3d.outlet_pressure_pa == pytest.approx(res_3d.pressure_pa[-1])
    assert res_3d.outlet_vapor_pressure_pa == pytest.approx(res_3d.wall_vapor_pressure_pa[-1])
    assert res_3d.inlet_vapor_pressure_pa == pytest.approx(res_3d.wall_vapor_pressure_pa[0])
    assert res_3d.has_flashed == (res_3d.has_wall_flashed or res_3d.has_bulk_flashed)
    assert res_3d.temperature_k == res_3d.bulk_temperature_k
    assert res_3d.vapor_pressure_pa == res_3d.wall_vapor_pressure_pa
    assert len(res_3d.velocity_m_s) == len(res_3d.distance_m)
    assert res_3d.config.inlet_temperature_k == pytest.approx(pipe_cfg.inlet_temperature_k)
    assert res_3d.config.length_m == pytest.approx(pipe_cfg.length_m)

    # 2. Simulate Streamlit module hot-reload where cached object comes from pre-reload class
    importlib.reload(s3d_mod)
    assert s3d_mod.is_3d_results(res_3d) is True
    assert len(generate_schematic_2d_html(res_3d)) > 1000
    assert len(generate_terminal_3d_html(res_3d)) > 1000
    assert len(generate_3d_pipe_html(res_3d)) > 1000
    assert create_pressure_comparison_chart(res_3d) is not None
    assert create_temperature_profile_chart(res_3d) is not None
    assert create_flashing_margin_chart(res_3d) is not None

