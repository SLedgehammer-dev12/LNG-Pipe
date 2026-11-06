import pytest
from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig
from core.solver_3d import PipelineSolver3D, Solver3DConfig
from reports.pdf_report import generate_pdf_report

def test_generate_pdf_report_from_1d_and_3d():
    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="Cryogenic Aerogel", thickness_m=0.03, thermal_conductivity=0.015)]
    thermal_model = PipeThermalModel(inner_diameter_m=0.15, wall_thickness_m=0.006, insulation_layers=layers)
    config = PipelineSimulationConfig(length_m=150.0, inner_diameter_m=0.15, num_cells=30)
    
    # 1D
    res_1d = PipelineSolver(fm, thermal_model, config).solve()
    meta = {"project_name": "LNG 1D Test", "tag_id": "LNG-01", "engineer_name": "Proses Eng", "date_str": "2026-11-06"}
    pdf_1d = generate_pdf_report(res_1d, meta)
    assert len(pdf_1d) > 2000
    assert pdf_1d.startswith(b"%PDF")
    
    # 3D
    cfg_3d = Solver3DConfig(pipeline_config=config, n_radial=8, n_azimuthal=8, n_axial=30)
    res_3d = PipelineSolver3D(fm, thermal_model, cfg_3d).solve()
    meta_3d = {"project_name": "LNG 3D Test", "tag_id": "LNG-3D-01", "engineer_name": "Proses Eng", "date_str": "2026-11-06"}
    pdf_3d = generate_pdf_report(res_3d, meta_3d)
    assert len(pdf_3d) > 2000
    assert pdf_3d.startswith(b"%PDF")
