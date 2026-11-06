import pytest
from core.fluids import FluidManager
from core.terminal_ops import evaluate_terminal_operations, TerminalOperatingMetrics


def test_latent_heat_and_bubble_dew_temperature():
    fm_pure = FluidManager(fluid_type="pure_methane")
    h_fg_pure = fm_pure.get_latent_heat(101325.0)
    assert 450000.0 < h_fg_pure < 550000.0

    t_bubble, t_dew = fm_pure.get_bubble_dew_temperature(101325.0)
    assert abs(t_bubble - t_dew) < 0.1
    assert 111.0 < t_bubble < 112.5

    fm_mix = FluidManager(fluid_type="mixture", composition={"Methane": 0.94, "Ethane": 0.045, "Propane": 0.01, "Nitrogen": 0.005})
    h_fg_mix = fm_mix.get_latent_heat(101325.0)
    assert 450000.0 < h_fg_mix < 650000.0

    t_b_mix, t_d_mix = fm_mix.get_bubble_dew_temperature(101325.0)
    assert t_d_mix >= t_b_mix


def test_evaluate_terminal_operations_metrics():
    # 500m DN200 line, 15 kW heat ingress
    metrics = evaluate_terminal_operations(
        total_heat_w=15000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        delta_t_allowable=1.5,
        pressure_drop_pa=1.2e5
    )
    assert isinstance(metrics, TerminalOperatingMetrics)
    assert metrics.bog_rate_kg_h > 0.0
    # 15 kW / 510 kJ/kg = 0.0294 kg/s = ~105.8 kg/h
    assert 90.0 < metrics.bog_rate_kg_h < 120.0
    assert metrics.bog_rate_nm3_h > 100.0
    assert metrics.boil_off_rate_pct_day > 0.0
    assert metrics.recirc_min_flow_kg_s > 0.0
    # m_recirc = 15000 / (3480 * 1.5) = 2.87 kg/s = ~24.3 m3/h
    assert 2.0 < metrics.recirc_min_flow_kg_s < 4.0
    assert 15.0 < metrics.recirc_min_flow_m3_h < 35.0
    assert metrics.recirc_pump_head_m > 0.0
    assert metrics.recirc_pump_power_kw > 0.0


def test_two_phase_flashing_multipliers():
    from core.two_phase import calculate_two_phase_flashing
    
    # Subcooled liquid (x=0)
    alpha, phi_l_sq, rho_mix = calculate_two_phase_flashing(
        vapor_quality=0.0,
        liquid_density=425.0,
        vapor_density=5.0,
        liquid_viscosity=1.15e-4,
        vapor_viscosity=8.0e-6
    )
    assert alpha == 0.0
    assert phi_l_sq == 1.0
    assert rho_mix == 425.0

    # 2% vapor quality (flashing onset)
    alpha_2, phi_l_sq_2, rho_mix_2 = calculate_two_phase_flashing(
        vapor_quality=0.02,
        liquid_density=425.0,
        vapor_density=5.0,
        liquid_viscosity=1.15e-4,
        vapor_viscosity=8.0e-6
    )
    # Even 2% vapor quality by mass yields ~40-60% void fraction due to 85x density ratio!
    assert 0.30 < alpha_2 < 0.70
    assert phi_l_sq_2 > 2.0
    assert rho_mix_2 < 300.0


def test_evaluate_terminal_operations_downhill_positive_head():
    # Negative pressure_drop_pa (e.g. downhill line) should enforce circuit floor
    metrics = evaluate_terminal_operations(
        total_heat_w=10000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        delta_t_allowable=1.5,
        pressure_drop_pa=-50000.0  # Downhill gravitational gain
    )
    assert metrics.recirc_pump_head_m > 0.0
    assert metrics.recirc_pump_power_kw > 0.0
