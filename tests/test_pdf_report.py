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


def test_pdf_report_xml_escaping_11col_table_custom_units_and_mechanics():
    from core.mechanics import (
        spec_from_material,
        calculate_asme_b31_3_thickness,
        calculate_thermal_contraction_and_omega_loop,
        calculate_joukowsky_surge,
    )

    fm = FluidManager(fluid_type="pure_methane")
    layers = [InsulationLayer(name="PIR", thickness_m=0.05, thermal_conductivity=0.024)]
    tm = PipeThermalModel(inner_diameter_m=0.20, wall_thickness_m=0.008, insulation_layers=layers)
    cfg = PipelineSimulationConfig(length_m=400.0, inner_diameter_m=0.20, num_cells=10)
    res = PipelineSolver(fm, tm, cfg).solve()

    spec = spec_from_material("Invar 36 (Düşük Genleşmeli)", outer_diameter_m=0.2191, design_pressure_pa=25e5, operating_pressure_pa=5e5, pipeline_length_m=400.0)
    asme = calculate_asme_b31_3_thickness(spec)
    omega = calculate_thermal_contraction_and_omega_loop(spec, anchor_distance_m=150.0, outer_diameter_m=0.2191)
    surge = calculate_joukowsky_surge(spec, nominal_velocity_m_s=2.5, valve_closure_time_s=4.0, wall_thickness_m=0.008)

    meta = {
        "project_name": "R&D LNG <Terminal> & Co.",
        "tag_id": "PL-01 & <Main>",
        "engineer_name": "Ömer Şahin & İrem Ağaoğlu",
        "date_str": "2026-11-23",
    }
    headers = [f"Col{i} (unit)" for i in range(11)]
    cell_data = [headers] + [[f"{r}.{c} & <ok>" for c in range(11)] for r in range(5)]

    pdf = generate_pdf_report(
        res,
        meta,
        temp_unit="°F",
        press_unit="psi (g)",
        cell_data=cell_data,
        asme_mech=asme,
        omega_mech=omega,
        surge_mech=surge,
        valve_closure_time_s=4.0,
    )
    assert len(pdf) > 3000
    assert pdf.startswith(b"%PDF")

