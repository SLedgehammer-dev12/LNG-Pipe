"""Tests for offline packaging assets, desktop launcher helpers, and PDF generation."""

from components._three_assets import get_three_script_tags
from components.pipe_3d_viewer import generate_3d_pipe_html
from components.terminal_3d_viewer import generate_terminal_3d_html
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSimulationConfig, PipelineSolver
import launcher_desktop
from reports.pdf_report import generate_pdf_report


def test_offline_three_assets_embedded():
    tags = get_three_script_tags()
    assert "<script>" in tags
    assert "<script src=" not in tags
    assert "cdnjs.cloudflare.com" not in tags
    assert "cdn.jsdelivr.net" not in tags
    assert "OrbitControls" in tags

    fm = FluidManager(fluid_type="pure_methane")
    tm = PipeThermalModel(
        inner_diameter_m=0.20,
        wall_thickness_m=0.008,
        insulation_layers=[InsulationLayer("PIR", 0.05, 0.024)],
    )
    res = PipelineSolver(
        fm, tm, PipelineSimulationConfig(length_m=300.0, inner_diameter_m=0.20, num_cells=15)
    ).solve()

    for html in (generate_terminal_3d_html(res), generate_3d_pipe_html(res)):
        assert "cdnjs.cloudflare.com" not in html
        assert "cdn.jsdelivr.net" not in html


def test_launcher_finds_valid_free_port():
    port = launcher_desktop._find_free_port()
    assert isinstance(port, int)
    assert 1024 < port < 65536


def test_pdf_report_generates_valid_pdf_bytes():
    fm = FluidManager(fluid_type="pure_methane")
    tm = PipeThermalModel(
        inner_diameter_m=0.20,
        wall_thickness_m=0.008,
        insulation_layers=[InsulationLayer("PIR", 0.05, 0.024)],
    )
    res = PipelineSolver(
        fm, tm, PipelineSimulationConfig(length_m=300.0, inner_diameter_m=0.20, num_cells=15)
    ).solve()
    pdf_bytes = generate_pdf_report(
        res,
        project_info={
            "project_name": "İskenderun LNG Terminali Şartlandırma",
            "engineer": "Test Mühendisi",
            "fluid_desc": "Saf Metan (CH4)",
        },
    )
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1500
