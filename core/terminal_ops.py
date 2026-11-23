"""Terminal Operations Engineering: BOG Generation & Cooldown Recirculation Module.

Complies with: EN 1473, GIIGNL Custody Transfer Handbook, API 521, API 625.
"""

import math
from dataclasses import dataclass
from typing import Optional


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
    recirc_min_pump_power_kw: float = 0.0
    user_recirc_flow_kg_s: float = 0.0
    user_recirc_flow_m3_h: float = 0.0
    user_recirc_pump_power_kw: float = 0.0
    user_recirc_delta_t_k: float = 0.0
    recirc_flow_deficit_warning: bool = False
    recirc_flow_warning_msg: str = ""
    tank_heat_ingress_w: float = 0.0
    tank_bog_rate_kg_h: float = 0.0
    pump_heat_to_lng_w: float = 0.0
    total_terminal_bog_kg_h: float = 0.0
    total_terminal_bog_nm3_h: float = 0.0


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
    fitting_loss_factor: float = 0.20,
    return_heat_w: float = 0.0,
    return_pressure_drop_pa: float = 0.0,
    user_recirc_flow_kg_s: Optional[float] = None,
    recirc_suction_pressure_pa: float = 1.15e5,
    recirc_target_pressure_pa: float = 0.0,
    recirc_pump_eff: float = 0.70,
    recirc_motor_eff: float = 0.90,
    unload_pump_eff: float = 0.75,
    unload_motor_eff: float = 0.92,
    tank_volume_m3: float = 0.0,
    tank_bor_pct_day: float = 0.05,
    molar_mass_g_mol: float = 16.5,
) -> TerminalOperatingMetrics:
    """Calculates BOG rates, standby boil-off, and pumping requirements for both unloading and cooldown recirculation."""
    h_fg = max(latent_heat, 200000.0)
    rho_norm = max(molar_mass_g_mol / 22.414, 0.05)  # kg/Nm3 from composition molar mass
    rho_liq = max(fluid_density, 1.0)
    cp_val = max(specific_heat, 500.0)
    dt_allow = max(delta_t_allowable, 0.1)

    eta_p_rec = max(0.05, min(recirc_pump_eff, 1.0))
    eta_m_rec = max(0.05, min(recirc_motor_eff, 1.0))
    eta_p_unl = max(0.05, min(unload_pump_eff, 1.0))
    eta_m_unl = max(0.05, min(unload_motor_eff, 1.0))

    # Total pipeline loop heat ingress (main + return line)
    q_loop_w = max(0.0, total_heat_w) + max(0.0, return_heat_w)

    # 1. BOG Rates during standby/heat ingress in pipeline
    bog_kg_s = q_loop_w / h_fg
    bog_kg_h = bog_kg_s * 3600.0
    bog_nm3_h = bog_kg_h / rho_norm

    # Line liquid inventory
    line_vol = (math.pi / 4.0) * (inner_diam_m ** 2) * length_m
    inventory_kg = line_vol * rho_liq
    bor_pct_day = (bog_kg_h * 24.0 / inventory_kg) * 100.0 if inventory_kg > 0 else 0.0

    # 2. Recirculation Circuit Head & Pump Shaft Heat Input
    g = 9.80665
    dp_target_boost = max(0.0, recirc_target_pressure_pa - recirc_suction_pressure_pa) if recirc_target_pressure_pa > 0.0 else 0.0
    # Do not double-count main unloading friction with target boost: scale main friction for low cooldown flow or use return friction
    if recirc_target_pressure_pa > 0.0:
        dp_loop_at_recirc = max(return_pressure_drop_pa, 0.0)
        dp_circuit = max(dp_target_boost, dp_loop_at_recirc, 1.0e5)
    else:
        dp_circuit = max(max(pressure_drop_pa, 0.0) + max(return_pressure_drop_pa, 0.0), 1.0e5)
    head_m = dp_circuit / (rho_liq * g)

    # Pump shaft energy dissipation into LNG stream (dH_pump = dP / (rho * eta_p))
    dh_pump_j_kg = dp_circuit / (rho_liq * eta_p_rec)
    effective_cp_dt = max(cp_val * dt_allow - dh_pump_j_kg, 0.10 * cp_val * dt_allow)

    # 3. Minimum Recirculation (Cooldown Mode to maintain line within delta_t_allowable including pump heat)
    m_recirc_kg_s = q_loop_w / effective_cp_dt
    q_recirc_m3_h = (m_recirc_kg_s / rho_liq) * 3600.0
    pipe_area = (math.pi / 4.0) * (inner_diam_m ** 2)
    p_min_shaft_kw = (m_recirc_kg_s * (dp_circuit / rho_liq) / (eta_p_rec * eta_m_rec)) / 1000.0

    # User-entered recirculation flow evaluation & checkpoint
    u_flow_kg_s = m_recirc_kg_s if user_recirc_flow_kg_s is None else max(0.0, float(user_recirc_flow_kg_s))
    u_flow_m3_h = (u_flow_kg_s / rho_liq) * 3600.0
    u_pump_power_kw = (u_flow_kg_s * (dp_circuit / rho_liq) / (eta_p_rec * eta_m_rec)) / 1000.0
    u_delta_t_k = ((q_loop_w / (u_flow_kg_s * cp_val)) + (dh_pump_j_kg / cp_val)) if u_flow_kg_s > 0.0 else float("inf")
    v_recirc = u_flow_kg_s / (rho_liq * pipe_area) if pipe_area > 0 else 0.0
    stratification_risk = v_recirc < 0.20  # Richardson stratification / bowing risk at active cooldown flow

    if user_recirc_flow_kg_s is not None and u_flow_kg_s < (m_recirc_kg_s - 1e-6):
        deficit_warn = True
        dt_disp = f"+{u_delta_t_k:.2f} K" if math.isfinite(u_delta_t_k) else "∞ (Akış Yok)"
        warn_msg = (
            f"⚠️ KRİTİK SİRKÜLASYON DEBİSİ UYARISI: Girilen dönüş debisi ({u_flow_kg_s:.2f} kg/s | {u_flow_m3_h:.1f} m³/h), "
            f"hattı ΔT ≤ {dt_allow:.1f} K sınırında soğuk tutmak için gereken minimum debiden "
            f"({m_recirc_kg_s:.2f} kg/s | {q_recirc_m3_h:.1f} m³/h) DÜŞÜKTÜR! "
            f"Mevcut debide hat boyunca ΔT = {dt_disp} ısınma, flaş/kaynama ve termal eğilme (bowing) oluşacaktır."
        )
    else:
        deficit_warn = False
        warn_msg = (
            f"✓ Sirkülasyon debisi ({u_flow_kg_s:.2f} kg/s | {u_flow_m3_h:.1f} m³/h), "
            f"minimum gerekli soğuk tutma debisini ({m_recirc_kg_s:.2f} kg/s | {q_recirc_m3_h:.1f} m³/h) karşılamaktadır "
            f"(Gerçekleşen ΔT = +{u_delta_t_k:.2f} K ≤ {dt_allow:.1f} K)."
        )

    recirc_rec = (
        f"P-201 Min. Gerekli Güç: {p_min_shaft_kw:.1f} kW ({q_recirc_m3_h:.1f} m³/h @ {head_m:.1f} mLC) | "
        f"Seçilen Debide Güç: {u_pump_power_kw:.1f} kW ({u_flow_m3_h:.1f} m³/h)"
    )

    # 4. Onshore Storage Tank Heat Ingress & Total Terminal BOG Budget
    tank_mass_kg = max(0.0, tank_volume_m3) * rho_liq
    tank_bog_kg_h = (tank_mass_kg * (max(0.0, tank_bor_pct_day) / 100.0)) / 24.0 if tank_mass_kg > 0 else 0.0
    tank_heat_w = (tank_bog_kg_h / 3600.0) * h_fg
    active_p_kw = u_pump_power_kw if user_recirc_flow_kg_s is not None else p_min_shaft_kw
    pump_heat_w = active_p_kw * eta_m_rec * 1000.0
    tot_term_bog_kg_h = tank_bog_kg_h + ((q_loop_w + pump_heat_w) / h_fg) * 3600.0
    tot_term_bog_nm3_h = tot_term_bog_kg_h / rho_norm

    # 5. Main Unloading Pumping Requirements (Gemiden Karaya Ana Boşaltım Pompalaması)
    q_unload_m3_h = (main_mass_flow_kg_s / rho_liq) * 3600.0 if main_mass_flow_kg_s > 0 else 0.0
    dp_unload_total = max(pressure_drop_pa, 0.0) * (1.0 + fitting_loss_factor) + tank_backpressure_pa
    head_unload_m = dp_unload_total / (rho_liq * g) if rho_liq > 0 else 0.0
    p_unload_kw = (main_mass_flow_kg_s * (dp_unload_total / rho_liq) / (eta_p_unl * eta_m_unl)) / 1000.0 if main_mass_flow_kg_s > 0 else 0.0

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
        total_heat_ingress_w=q_loop_w,
        bog_rate_kg_h=bog_kg_h,
        bog_rate_nm3_h=bog_nm3_h,
        boil_off_rate_pct_day=bor_pct_day,
        recirc_min_flow_kg_s=m_recirc_kg_s,
        recirc_min_flow_m3_h=q_recirc_m3_h,
        recirc_velocity_m_s=v_recirc,
        recirc_pump_head_m=head_m,
        recirc_pump_power_kw=p_min_shaft_kw,
        stratification_risk=stratification_risk,
        unloading_flow_m3_h=q_unload_m3_h,
        unloading_pump_head_m=head_unload_m,
        unloading_pump_power_kw=p_unload_kw,
        unloading_pump_recommendation=unload_rec,
        recirc_pump_recommendation=recirc_rec,
        recirc_min_pump_power_kw=p_min_shaft_kw,
        user_recirc_flow_kg_s=u_flow_kg_s,
        user_recirc_flow_m3_h=u_flow_m3_h,
        user_recirc_pump_power_kw=u_pump_power_kw,
        user_recirc_delta_t_k=u_delta_t_k,
        recirc_flow_deficit_warning=deficit_warn,
        recirc_flow_warning_msg=warn_msg,
        tank_heat_ingress_w=tank_heat_w,
        tank_bog_rate_kg_h=tank_bog_kg_h,
        pump_heat_to_lng_w=pump_heat_w,
        total_terminal_bog_kg_h=tot_term_bog_kg_h,
        total_terminal_bog_nm3_h=tot_term_bog_nm3_h,
    )
