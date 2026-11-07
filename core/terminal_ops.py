"""Terminal Operations Engineering: BOG Generation & Cooldown Recirculation Module.

Complies with: EN 1473, GIIGNL Custody Transfer Handbook, API 521.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TerminalOperatingMetrics:
    total_heat_ingress_w: float
    bog_rate_kg_h: float
    bog_rate_nm3_h: float
    boil_off_rate_pct_day: float
    recirc_min_flow_kg_s: float
    recirc_min_flow_m3_h: float
    recirc_velocity_m_s: float
    recirc_pump_head_m: float
    recirc_pump_power_kw: float
    stratification_risk: bool
    unloading_flow_m3_h: float = 0.0
    unloading_pump_head_m: float = 0.0
    unloading_pump_power_kw: float = 0.0
    unloading_pump_recommendation: str = ""
    recirc_pump_recommendation: str = ""


def evaluate_terminal_operations(
    total_heat_w: float,
    length_m: float,
    inner_diam_m: float,
    fluid_density: float,
    specific_heat: float,
    latent_heat: float,
    delta_t_allowable: float = 1.5,
    pressure_drop_pa: float = 1.5e5,
    main_mass_flow_kg_s: float = 0.0,
    tank_backpressure_pa: float = 0.3e5,
    fitting_loss_factor: float = 0.20
) -> TerminalOperatingMetrics:
    """Calculates BOG rates, standby boil-off, and pumping requirements for both unloading and cooldown recirculation."""
    # 1. BOG Rates during standby/heat ingress
    bog_kg_s = total_heat_w / max(latent_heat, 200000.0)
    bog_kg_h = bog_kg_s * 3600.0
    rho_norm = 0.736  # kg/Nm3 for LNG BOG at 0 °C, 1.01325 bar
    bog_nm3_h = bog_kg_h / rho_norm

    rho_liq = max(fluid_density, 1.0)
    cp_val = max(specific_heat, 500.0)
    dt_allow = max(delta_t_allowable, 0.1)

    # Line liquid inventory
    line_vol = (math.pi / 4.0) * (inner_diam_m ** 2) * length_m
    inventory_kg = line_vol * rho_liq
    bor_pct_day = (bog_kg_h * 24.0 / inventory_kg) * 100.0 if inventory_kg > 0 else 0.0

    # 2. Recirculation (Cooldown Mode to maintain line at <= -161 C)
    m_recirc_kg_s = total_heat_w / (cp_val * dt_allow)
    q_recirc_m3_h = (m_recirc_kg_s / rho_liq) * 3600.0
    pipe_area = (math.pi / 4.0) * (inner_diam_m ** 2)
    v_recirc = m_recirc_kg_s / (rho_liq * pipe_area) if pipe_area > 0 else 0.0
    stratification_risk = v_recirc < 0.20  # Richardson stratification / bowing risk

    # 3. Recirculation Pump P-201 Head & Shaft Power (70% pump, 90% motor efficiency)
    # Recirculation requires overcoming closed-loop circuit friction (minimum 1.0 bar head)
    g = 9.80665
    dp_circuit = max(pressure_drop_pa, 1.0e5)
    head_m = dp_circuit / (rho_liq * g)
    p_shaft_kw = (m_recirc_kg_s * (dp_circuit / rho_liq) / (0.70 * 0.90)) / 1000.0
    recirc_rec = f"P-201 Karadan Gemiye Kriyo Sirkülasyon: {q_recirc_m3_h:.1f} m³/h @ {head_m:.1f} mLC (Motor: ~{p_shaft_kw:.1f} kW)"

    # 4. Main Unloading Pumping Requirements (Gemiden Karaya Ana Boşaltım Pompalaması)
    q_unload_m3_h = (main_mass_flow_kg_s / rho_liq) * 3600.0 if main_mass_flow_kg_s > 0 else 0.0
    dp_unload_total = max(pressure_drop_pa, 0.0) * (1.0 + fitting_loss_factor) + tank_backpressure_pa
    head_unload_m = dp_unload_total / (rho_liq * g) if rho_liq > 0 else 0.0
    # Combined cryogenic pump & drive efficiency (~69%: 75% hydraulic, 92% electric motor)
    p_unload_kw = (main_mass_flow_kg_s * (dp_unload_total / rho_liq) / (0.75 * 0.92)) / 1000.0 if main_mass_flow_kg_s > 0 else 0.0

    if q_unload_m3_h > 2500.0:
        n_pumps = 4
        flow_per_p = q_unload_m3_h / n_pumps
        kw_per_p = p_unload_kw / n_pumps
        unload_rec = f"Tavsiye: 4x Daldırma Kargo Pompası (her biri ~{flow_per_p:.0f} m³/h @ {head_unload_m:.0f} mLC, motor: ~{kw_per_p:.0f} kW)"
    elif q_unload_m3_h > 1000.0:
        n_pumps = 2
        flow_per_p = q_unload_m3_h / n_pumps
        kw_per_p = p_unload_kw / n_pumps
        unload_rec = f"Tavsiye: 2x Daldırma Kargo Pompası (her biri ~{flow_per_p:.0f} m³/h @ {head_unload_m:.0f} mLC, motor: ~{kw_per_p:.0f} kW)"
    elif q_unload_m3_h > 0:
        unload_rec = f"Tavsiye: 1x Kriyo Transfer Pompası (~{q_unload_m3_h:.0f} m³/h @ {head_unload_m:.0f} mLC, motor: ~{p_unload_kw:.0f} kW)"
    else:
        unload_rec = "Ana boşaltım akışı tanımlı değil (Standby modu)."

    return TerminalOperatingMetrics(
        total_heat_ingress_w=total_heat_w,
        bog_rate_kg_h=bog_kg_h,
        bog_rate_nm3_h=bog_nm3_h,
        boil_off_rate_pct_day=bor_pct_day,
        recirc_min_flow_kg_s=m_recirc_kg_s,
        recirc_min_flow_m3_h=q_recirc_m3_h,
        recirc_velocity_m_s=v_recirc,
        recirc_pump_head_m=head_m,
        recirc_pump_power_kw=p_shaft_kw,
        stratification_risk=stratification_risk,
        unloading_flow_m3_h=q_unload_m3_h,
        unloading_pump_head_m=head_unload_m,
        unloading_pump_power_kw=p_unload_kw,
        unloading_pump_recommendation=unload_rec,
        recirc_pump_recommendation=recirc_rec
    )
