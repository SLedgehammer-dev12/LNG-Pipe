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


def test_terminal_3d_has_rack_manifold_gradient_and_inspector(sample_simulation_results):
    html = generate_terminal_3d_html(
        sample_simulation_results,
        main_diameter_mm=219.1,
        main_wall_mm=8.18,
        return_diameter_mm=114.3,
        return_wall_mm=6.02,
    )
    lowered = html.lower()
    assert "pipe rack" in lowered
    assert "manifold" in lowered
    assert "buildtempgradient" in lowered
    assert "raycaster" in lowered
    assert "pick-panel" in lowered
    assert "dinamik" in lowered
    # Supply and return are separated and mirrored.
    assert "main_z" in lowered
    assert "ret_z" in lowered
    assert "min_centerline_clearance" in lowered
    assert "offsetpolyline" in lowered
    assert "paralleloffset" in lowered
    assert "returnendz" in lowered


def test_terminal_3d_uses_return_line_simulation(sample_simulation_results):
    from core.fluids import FluidManager
    from core.heat_transfer import InsulationLayer, PipeThermalModel
    from core.solver import PipelineSolver, PipelineSimulationConfig

    cfg = PipelineSimulationConfig(length_m=500.0, inner_diameter_m=0.10, num_cells=20)
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    tm = PipeThermalModel(inner_diameter_m=0.10, wall_thickness_m=0.006, insulation_layers=layers)
    return_results = PipelineSolver(fm, tm, cfg).solve()

    html = generate_terminal_3d_html(sample_simulation_results, return_results=return_results)
    assert "return_stations" in html
    assert "retStations" in html


def test_dynamic_omega_count_syncs_2d_and_3d(sample_simulation_results):
    html2 = generate_schematic_2d_html(sample_simulation_results, length_m=1000.0, anchor_dist_m=180.0)
    html3 = generate_terminal_3d_html(sample_simulation_results, length_m=1000.0, anchor_dist_m=180.0)
    assert "OMEGA-6 DOLFENİ" in html2
    assert "OMEGA-7 DOLFENİ" not in html2
    assert '"omega_count": 6' in html3
    assert "Ω: 6" in html2


def test_short_and_long_line_omega_counts(sample_simulation_results):
    short = generate_schematic_2d_html(sample_simulation_results, length_m=100.0, anchor_dist_m=180.0)
    assert "OMEGA-1 DOLFENİ" in short
    assert "OMEGA-2 DOLFENİ" not in short

    long = generate_schematic_2d_html(sample_simulation_results, length_m=3000.0, anchor_dist_m=180.0)
    assert "OMEGA-8 DOLFENİ" in long
    assert "OMEGA-9 DOLFENİ" not in long
