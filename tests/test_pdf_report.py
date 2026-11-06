import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from reports.pdf_report import generate_pdf_report

def test_generate_pdf_report_creates_valid_pdf_buffer():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="Cryogenic Aerogel", thickness_m=0.03, thermal_conductivity=0.015)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.15, wall_thickness_m=0.006, insulation_layers=layers)
    config = PipelineSimulationConfig(length_m=150.0, inner_diameter_m=0.15, num_cells=30)
    results = PipelineSolver(fm, thermal_model, config).solve()
    
    project_info = {
        "project_name": "LNG Terminal Jetty Transfer Line",
        "tag_id": "LNG-PL-001",
        "engineer_name": "Kıdemli Proses Mühendisi",
        "date_str": "2026-11-06"
    }
    
    pdf_bytes = generate_pdf_report(results, project_info)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")
