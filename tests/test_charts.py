import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from components.charts_2d import (
    create_pressure_comparison_chart,
    create_temperature_profile_chart,
    create_flashing_margin_chart,
    create_radial_temperature_chart
)

def test_charts_creation_returns_valid_plotly_figures():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=layers)
    config = PipelineSimulationConfig(length_m=200.0, inner_diameter_m=0.20, num_cells=20)
    results = PipelineSolver(fm, thermal_model, config).solve()
    
    fig_p = create_pressure_comparison_chart(results)
    assert fig_p is not None
    assert len(fig_p.data) >= 2  # At least Total P and Psat
    
    fig_t = create_temperature_profile_chart(results)
    assert fig_t is not None
    assert len(fig_t.data) >= 1
    
    fig_margin = create_flashing_margin_chart(results)
    assert fig_margin is not None
    
    fig_radial = create_radial_temperature_chart(results, slice_index=0)
    assert fig_radial is not None
