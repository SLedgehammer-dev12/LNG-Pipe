import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from core.solver_3d import PipelineSolver3D, Solver3DConfig
from components.charts_2d import (
    create_pressure_comparison_chart,
    create_temperature_profile_chart,
    create_flashing_margin_chart,
    create_radial_cross_section_heatmap
)

def test_charts_creation_returns_valid_plotly_figures():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=layers)
    config = PipelineSimulationConfig(length_m=200.0, inner_diameter_m=0.20, num_cells=20)
    
    # 1D Charts
    results_1d = PipelineSolver(fm, thermal_model, config).solve()
    fig_p1 = create_pressure_comparison_chart(results_1d)
    assert fig_p1 is not None
    assert len(fig_p1.data) >= 2
    
    # 3D Charts & Radial Contour Heatmap
    cfg_3d = Solver3DConfig(pipeline_config=config, n_radial=8, n_azimuthal=8, n_axial=20)
    results_3d = PipelineSolver3D(fm, thermal_model, cfg_3d).solve()
    
    fig_p3 = create_pressure_comparison_chart(results_3d)
    assert fig_p3 is not None
    assert len(fig_p3.data) >= 3  # Total P, Wall Psat, Bulk Psat
    
    fig_t3 = create_temperature_profile_chart(results_3d)
    assert fig_t3 is not None
    assert len(fig_t3.data) >= 3  # Wall, Bulk, Center
    
    fig_heatmap = create_radial_cross_section_heatmap(results_3d, slice_index=10)
    assert fig_heatmap is not None
