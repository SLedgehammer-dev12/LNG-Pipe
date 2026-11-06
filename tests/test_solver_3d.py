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
