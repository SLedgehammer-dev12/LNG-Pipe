import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from components.pipeline_schematic_2d import generate_schematic_2d_html
from components.terminal_3d_viewer import generate_terminal_3d_html

@pytest.fixture
def sample_simulation_results():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=layers)
    config = PipelineSimulationConfig(length_m=500.0, inner_diameter_m=0.20, num_cells=20)
    return PipelineSolver(fm, thermal_model, config).solve()

def test_schematic_2d_html_generation(sample_simulation_results):
    html = generate_schematic_2d_html(sample_simulation_results)
    assert isinstance(html, str)
    assert len(html) > 1000
    assert "lup" in html.lower()
    assert "apd" in html.lower()
    assert "omega" in html.lower()
    assert "tank" in html.lower()
    assert "sirkülasyon" in html.lower() or "recirculation" in html.lower()
    assert "gemi" in html.lower() or "carrier" in html.lower()

def test_terminal_3d_html_generation(sample_simulation_results):
    html = generate_terminal_3d_html(sample_simulation_results)
    assert isinstance(html, str)
    assert len(html) > 1000
    assert "three" in html.lower()
    assert "lup" in html.lower()
    assert "omega" in html.lower()
    assert "tank" in html.lower()
