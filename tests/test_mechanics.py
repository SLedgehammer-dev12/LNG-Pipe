import pytest
from core.mechanics import (
    PipelineSpecification,
    calculate_asme_b31_3_thickness,
    calculate_thermal_contraction_and_omega_loop,
    calculate_joukowsky_surge
)


def test_asme_b31_3_minimum_thickness():
    # 16" (DN400) pipe, 20 bar design pressure, 304L
    spec = PipelineSpecification(
        outer_diameter_m=0.4064,
        design_pressure_pa=2.0e6,
        operating_pressure_pa=1.0e6,
        pipeline_length_m=1000.0,
        material_allowable_stress_pa=138e6
    )
    res = calculate_asme_b31_3_thickness(spec)
    assert "t_required_min_mm" in res
    assert "hydrostatic_test_pressure_bar" in res
    # t_req should be around 2.9 - 3.5 mm for 20 bar on 16"
    assert 2.0 < res["t_required_min_mm"] < 5.0
    # P_hydro = 1.5 * 20 bar = 30 bar
    assert res["hydrostatic_test_pressure_bar"] == 30.0


def test_thermal_contraction_and_omega_loop():
    spec = PipelineSpecification(
        outer_diameter_m=0.4064,
        design_pressure_pa=2.0e6,
        operating_pressure_pa=1.0e6,
        pipeline_length_m=1000.0,
        thermal_expansion_coeff=15.8e-6,
        delta_t_k=182.0
    )
    res = calculate_thermal_contraction_and_omega_loop(spec, anchor_distance_m=200.0, outer_diameter_m=0.4064)
    # Contraction per meter ~ 2.88 mm/m
    assert 2.7 < res["contraction_rate_mm_per_m"] < 3.0
    # 1 km contraction ~ 2.88 m
    assert 2.7 < res["total_line_contraction_m"] < 3.0
    # 200m section loop contraction ~ 575 mm
    assert 500.0 < res["loop_absorbed_delta_l_mm"] < 650.0
    # Minimum leg height > 2.0 m
    assert res["min_omega_loop_leg_height_m"] > 2.0


def test_joukowsky_surge_and_valve_closure():
    spec = PipelineSpecification(
        outer_diameter_m=0.4064,
        design_pressure_pa=2.0e6,
        operating_pressure_pa=8.0e5,
        pipeline_length_m=1000.0,
        fluid_density_kg_m3=430.0
    )
    # 2.5 m/s velocity, 1.0 s rapid closure (t < t_crit)
    res_fast = calculate_joukowsky_surge(spec, nominal_velocity_m_s=2.5, valve_closure_time_s=1.0, wall_thickness_m=0.00952)
    assert res_fast["speed_of_sound_m_s"] > 1000.0
    # Joukowsky surge should be around 14 - 16 bar
    assert 12.0 < res_fast["actual_surge_bar"] < 18.0
    assert "Instantaneous" in res_fast["closure_regime"]

    # 20.0 s gradual closure
    res_slow = calculate_joukowsky_surge(spec, nominal_velocity_m_s=2.5, valve_closure_time_s=20.0, wall_thickness_m=0.00952)
    assert res_slow["actual_surge_bar"] < 2.0
    assert "Gradual" in res_slow["closure_regime"]
    assert res_slow["recommended_min_valve_closure_s"] >= 15.0


def test_joukowsky_surge_zero_wall_thickness_guarded():
    spec = PipelineSpecification(
        outer_diameter_m=0.4064,
        design_pressure_pa=2.0e6,
        operating_pressure_pa=8.0e5,
        pipeline_length_m=1000.0,
        fluid_density_kg_m3=430.0
    )
    # wall_thickness_m = 0.0 should not raise ZeroDivisionError
    res = calculate_joukowsky_surge(spec, nominal_velocity_m_s=2.5, valve_closure_time_s=15.0, wall_thickness_m=0.0)
    assert res["speed_of_sound_m_s"] > 0.0
    assert res["actual_surge_bar"] >= 0.0
