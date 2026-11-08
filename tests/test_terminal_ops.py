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
    # 500m DN200 line, 15 kW heat ingress, 150 kg/s unloading flow
    metrics = evaluate_terminal_operations(
        total_heat_w=15000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        delta_t_allowable=1.5,
        pressure_drop_pa=1.2e5,
        main_mass_flow_kg_s=150.0
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
    assert metrics.unloading_flow_m3_h > 1000.0
    assert metrics.unloading_pump_head_m > 0.0
    assert metrics.unloading_pump_power_kw > 0.0
    assert "Daldırma" in metrics.unloading_pump_recommendation


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


def test_recirculation_flow_deficit_checkpoint_and_min_vs_user_power():
    # Total loop heat = 15 kW (main) + 6 kW (return) = 21 kW
    # m_min = 21000 / (3480 * 1.5) = 4.023 kg/s
    m_low = evaluate_terminal_operations(
        total_heat_w=15000.0,
        return_heat_w=6000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        delta_t_allowable=1.5,
        pressure_drop_pa=0.8e5,
        return_pressure_drop_pa=0.7e5,
        user_recirc_flow_kg_s=2.0,  # Below 4.023 kg/s minimum!
        recirc_suction_pressure_pa=1.15e5,
        recirc_target_pressure_pa=5.0e5,
    )
    assert m_low.recirc_flow_deficit_warning is True
    assert "KRİTİK SİRKÜLASYON DEBİSİ UYARISI" in m_low.recirc_flow_warning_msg
    assert m_low.user_recirc_delta_t_k > 1.5
    assert m_low.recirc_min_pump_power_kw > m_low.user_recirc_pump_power_kw > 0.0

    # Now provide sufficient flow (6.0 kg/s > 4.023 kg/s)
    m_ok = evaluate_terminal_operations(
        total_heat_w=15000.0,
        return_heat_w=6000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        delta_t_allowable=1.5,
        pressure_drop_pa=0.8e5,
        return_pressure_drop_pa=0.7e5,
        user_recirc_flow_kg_s=6.0,
        recirc_suction_pressure_pa=1.15e5,
        recirc_target_pressure_pa=5.0e5,
    )
    assert m_ok.recirc_flow_deficit_warning is False
    assert "minimum gerekli soğuk tutma debisini" in m_ok.recirc_flow_warning_msg
    assert m_ok.user_recirc_delta_t_k <= 1.5
    assert m_ok.user_recirc_pump_power_kw > m_ok.recirc_min_pump_power_kw


def test_custom_pump_and_motor_efficiencies_and_onshore_tank_bog():
    base = evaluate_terminal_operations(
        total_heat_w=15000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        pressure_drop_pa=1.5e5,
        main_mass_flow_kg_s=100.0,
        recirc_pump_eff=0.70,
        recirc_motor_eff=0.90,
        unload_pump_eff=0.80,
        unload_motor_eff=0.95,
        tank_volume_m3=160000.0,
        tank_bor_pct_day=0.05,
    )
    lower_eff = evaluate_terminal_operations(
        total_heat_w=15000.0,
        length_m=500.0,
        inner_diam_m=0.20,
        fluid_density=425.0,
        specific_heat=3480.0,
        latent_heat=510000.0,
        pressure_drop_pa=1.5e5,
        main_mass_flow_kg_s=100.0,
        recirc_pump_eff=0.50,
        recirc_motor_eff=0.80,
        unload_pump_eff=0.60,
        unload_motor_eff=0.85,
        tank_volume_m3=160000.0,
        tank_bor_pct_day=0.05,
    )
    # Lower pump & motor efficiencies must require higher electrical motor power
    assert lower_eff.recirc_min_pump_power_kw > base.recirc_min_pump_power_kw
    assert lower_eff.unloading_pump_power_kw > base.unloading_pump_power_kw

    # Onshore tank BOG check: 160,000 m³ * 425 kg/m³ = 68,000,000 kg
    # 0.05%/day = 34,000 kg/day = 1416.67 kg/h
    assert abs(base.tank_bog_rate_kg_h - 1416.67) < 1.0
    assert base.tank_heat_ingress_w > 190000.0  # ~200.7 kW
    assert base.total_terminal_bog_kg_h > base.tank_bog_rate_kg_h + base.bog_rate_kg_h
