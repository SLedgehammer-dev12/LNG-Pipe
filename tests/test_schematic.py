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


def test_terminal_3d_scales_footprint_and_has_access_routes(sample_simulation_results):
    short = generate_terminal_3d_html(sample_simulation_results, length_m=300.0)
    long = generate_terminal_3d_html(sample_simulation_results, length_m=800.0)
    lowered = short.lower()
    assert "buildcatwalk" in lowered
    assert "buildaccessroad" in lowered
    assert "length_scale" in short
    assert '"length_scale": 1.0' in short
    assert '"length_scale": 2.5' in long


def test_terminal_3d_irregular_coast_earth_terrain_and_jetty_side_mooring_qrh(sample_simulation_results):
    html = generate_terminal_3d_html(sample_simulation_results, length_m=500.0)
    # 1. Irregular coastline profile (JS + GLSL water shader sync)
    assert "getShorelineWorldX" in html
    assert "shoreProfileX" in html
    assert "buildNaturalCoastAndTerrain" in html
    # 2. Earth-toned onshore terrain colors (wet sand, beach sand, earth/soil brown, terracotta)
    assert "0x8b6843" in html
    assert "0x9c6b43" in html
    assert "0xc4a77d" in html
    # 3. Jetty-side (iskele tarafı) Breasting Dolphins (BD-1..4 at x=-139) and Mooring Dolphins (MD-1..6 at x=-108..-118)
    assert "breastingDolphinPositions" in html
    assert "mooringDolphinPositions" in html
    assert "x: -139, z: -64" in html
    assert "x: -108, z: -182" in html
    # Old wrong seaward position (-172) for mooring dolphins must not exist
    assert "{ x: -172, z: -180, name: 'MD-1' }" not in html
    # 4. Properly scaled Quick Release Hooks (QRH) and catenary mooring lines
    assert "createQuickReleaseHookUnit" in html
    assert "createMooringHawser" in html
    assert "createCatwalkBridge" in html
    assert "mooringLinePairs" in html


def test_terminal_3d_four_tanks_spherical_dome_roof_piping_lng_pit_and_control_bldg(sample_simulation_results):
    html = generate_terminal_3d_html(sample_simulation_results, length_m=500.0)
    # 1. 4 LNG Storage Tanks (1x4 coastal-parallel row: T-101..T-104) with T-101 cutaway
    for code in ("T-101", "T-102", "T-103", "T-104"):
        assert f'code: "{code}"' in html
    assert 'code: "T-101", z: -195.0, cutaway: true' in html
    assert "createTankBandTexture" in html

    # 2. Corrected spherical dome roof (SphereGeometry cap, no inverted cone CylinderGeometry(62, 50, 10, 64))
    assert "domeSphereR" in html
    assert "domeThetaMax" in html
    assert "CylinderGeometry(62, 50, 10, 64)" not in html

    # 3. Roof-top piping & valve platform + Inter-tank supply, return & BOG headers
    assert "roofFillHeader" in html
    assert "roofRetHeader" in html
    assert "buildInterTankPiping" in html
    assert "supplyHeaderCurve" in html
    assert "returnHeaderCurve" in html
    assert "bogHeaderCurve" in html
    assert "supRiser" in html
    assert "retRiser" in html

    # 4. Secondary impounding basins (dikes), concrete spill trenches, common deep LNG Pit & foam generators
    assert "buildImpoundingAndLNGPit" in html
    assert "pitCryoPool" in html
    assert "mainTrenchFloor" in html
    assert "foamGenMat" in html

    # 5. Automation & Control Building behind tanks + Full Perimeter Access Road network
    assert "buildAutomationAndControlBuilding" in html
    assert "ctrlGlassMat" in html
    assert "addRoadSegment" in html
    assert "westRoadX" in html
    assert "eastRoadX" in html


