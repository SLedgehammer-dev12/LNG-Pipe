"""Syntax and behavioral checks for embedded JavaScript in 2D/3D HTML viewers."""

import re
import shutil
import subprocess
import pytest

from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from core.solver_3d import PipelineSolver3D, Solver3DConfig
from components.terminal_3d_viewer import generate_terminal_3d_html
from components.pipe_3d_viewer import generate_3d_pipe_html
from components.pipeline_schematic_2d import generate_schematic_2d_html


def _extract_inline_scripts(html: str) -> list[str]:
    scripts = []
    for match in re.finditer(r"<script([^>]*)>(.*?)</script>", html, re.DOTALL | re.IGNORECASE):
        attrs, body = match.group(1), match.group(2)
        if "src=" not in attrs.lower() and body.strip():
            scripts.append(body)
    return scripts


@pytest.mark.parametrize("is_3d,theme,flashing", [
    (False, "Gündüz", False),
    (True, "Gece", False),
    (True, "Gündüz", True),
])
def test_embedded_js_passes_node_syntax_check(is_3d, theme, flashing):
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js not installed")

    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.02 if flashing else 0.06, thermal_conductivity=0.035 if flashing else 0.024)]
    tm = PipeThermalModel(inner_diameter_m=0.15, wall_thickness_m=0.006, insulation_layers=layers)
    cfg = PipelineSimulationConfig(
        length_m=300.0,
        inner_diameter_m=0.15,
        inlet_temperature_k=112.0,
        inlet_pressure_pa=130000.0 if flashing else 500000.0,
        mass_flow_rate_kg_s=6.0 if flashing else 30.0,
        num_cells=25,
    )
    if is_3d:
        res = PipelineSolver3D(fm, tm, Solver3DConfig(pipeline_config=cfg, n_radial=8, n_azimuthal=8, n_axial=25)).solve()
    else:
        res = PipelineSolver(fm, tm, cfg).solve()

    html_samples = [
        generate_terminal_3d_html(res, length_m=800.0, anchor_dist_m=100.0, theme=theme),
        generate_3d_pipe_html(res, temp_unit="°F", press_unit="psi"),
        generate_schematic_2d_html(res, length_m=500.0, temp_unit="°F", press_unit="psi (g)"),
    ]
    for html in html_samples:
        scripts = _extract_inline_scripts(html)
        assert scripts, "Expected inline <script> block in HTML component"
        for js in scripts:
            proc = subprocess.run(
                [node_bin, "--check", "-"],
                input=js,
                text=True,
                capture_output=True,
                check=False,
            )
            assert proc.returncode == 0, f"JS syntax error: {proc.stderr}"


def test_3d_and_2d_viewer_regression_fixes():
    fm = FluidManager(fluid_type="pure_methane")
    tm = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=[InsulationLayer("PIR", 0.05, 0.024)])
    cfg = PipelineSimulationConfig(length_m=300.0, inner_diameter_m=0.20, num_cells=20)
    res = PipelineSolver(fm, tm, cfg).solve()

    html_term = generate_terminal_3d_html(res, theme='Gündüz')
    assert "curb.rotation.y = angle;" in html_term
    assert "const effFrac = isReturn ? (1.0 - frac) : frac;" in html_term
    assert "Math.min(clock.getDelta(), 0.1)" in html_term
    assert "pts[pts.length - 1].x < ROUTE_END - 20.0" in html_term

    html_pipe = generate_3d_pipe_html(res)
    assert "fluidMesh.rotation.z = -Math.PI / 2;" in html_pipe
    assert 'class="ctrl-btn active" id="btn-particles"' in html_pipe
    assert "particles.visible = showParticles;" in html_pipe
    assert "obj.geometry.dispose()" in html_pipe

    html_2d = generate_schematic_2d_html(res, temp_unit="°F", press_unit="psi")
    assert "°F" in html_2d
    assert "psi (abs)" in html_2d
    # Ensure converted °F values are not labeled with °C in interactive node showInfo calls
    assert "°C', '" not in html_2d
    assert "bar', '" not in html_2d
