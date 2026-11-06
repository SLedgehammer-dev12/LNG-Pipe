import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from components.pipe_3d_viewer import generate_3d_pipe_html

def test_generate_3d_pipe_html_contains_threejs_and_simulation_data():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=layers)
    config = PipelineSimulationConfig(length_m=100.0, inner_diameter_m=0.20, num_cells=20)
    results = PipelineSolver(fm, thermal_model, config).solve()
    
    html_content = generate_3d_pipe_html(results)
    
    assert isinstance(html_content, str)
    assert len(html_content) > 500
    assert "three" in html_content.lower()
    assert "inlet_t_c" in html_content.lower() or "giriş sıcaklığı" in html_content.lower()
    assert "canvas" in html_content.lower() or "webgl" in html_content.lower()
