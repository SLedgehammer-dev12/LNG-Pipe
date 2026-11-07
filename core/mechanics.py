"""Cryogenic Mechanical Integrity & Piping Module.

Complies with: ASME B31.3 (2022) Chapter III & IX, SIGTTO ESD Surge Guidelines, TEMA 10th Ed.
"""

import math
from dataclasses import dataclass


# Cryogenic piping material allowable properties (ASME B31.3 Table A-1 / A-1M, cryogenic).
# S_c: basic allowable stress (Pa) at -162 C; alpha: mean CTE (1/K); E: Young's modulus (Pa);
# rho: density (kg/m^3). Conservative values; engineer shall verify against material spec.
MATERIAL_PROPERTIES = {
    "Paslanmaz Çelik 304L/316L": dict(
        S_c=138e6, alpha=15.8e-6, E=200e9, rho=8000.0
    ),
    "%9 Nikel Çeliği (Cryogenic 9% Ni)": dict(
        S_c=155e6, alpha=12.0e-6, E=190e9, rho=7900.0
    ),
    "Invar 36 (Düşük Genleşmeli)": dict(
        S_c=125e6, alpha=1.2e-6, E=145e9, rho=8100.0
    ),
    "Alüminyum 5083-O": dict(
        S_c=95e6, alpha=23.6e-6, E=70e9, rho=2660.0
    ),
}

MATERIAL_ALIASES = {
    "Paslanmaz Çelik 304L/316L": "304L/316L",
    "%9 Nikel Çeliği (Cryogenic 9% Ni)": "9%Ni",
    "Invar 36 (Düşük Genleşmeli)": "Invar36",
    "Alüminyum 5083-O": "Al5083",
}


@dataclass(frozen=True)
class PipelineSpecification:
    outer_diameter_m: float
    design_pressure_pa: float
    operating_pressure_pa: float
    pipeline_length_m: float
    material_name: str = "Paslanmaz Çelik 304L/316L"
    material_allowable_stress_pa: float = 138e6  # 304L/316L S at cryogenic temp (Pa)
    weld_joint_efficiency: float = 1.00          # Seamless or 100% RT E
    y_coefficient: float = 0.40                  # Austenitic steel thin-wall Y
    corrosion_allowance_m: float = 0.000         # Cryogenic clean liquid CA (m)
    mill_tolerance: float = 0.125                # ASTM A312 12.5% mill undertolerance
    thermal_expansion_coeff: float = 15.8e-6     # 304L mean alpha (1/K)
    delta_t_k: float = 182.0                     # +20 C ambient to -162 C operating (182 K)
    fluid_density_kg_m3: float = 430.0           # LNG density at -162 C
    fluid_bulk_modulus_pa: float = 1.15e9        # LNG liquid bulk modulus K (Pa)
    pipe_youngs_modulus_pa: float = 200e9        # Steel E (Pa)
    material_allowable_stress_hot_pa: float = 0.0  # S_h at hot condition (Pa); 0 => cold-only displacement
    stress_range_factor: float = 1.0             # f per B31.3 319.4.4 (1.0 <= ~7000 cycles)
    sustained_stress_pa: float = 0.0             # S_L: pressure + weight sustained stress (Pa)


def spec_from_material(material_name: str, **overrides) -> PipelineSpecification:
    """Build a PipelineSpecification keyed by user-facing material name."""
    props = MATERIAL_PROPERTIES.get(material_name, MATERIAL_PROPERTIES["Paslanmaz Çelik 304L/316L"])
    data = {
        "material_allowable_stress_pa": props["S_c"],
        "thermal_expansion_coeff": props["alpha"],
        "pipe_youngs_modulus_pa": props["E"],
        "fluid_density_kg_m3": props["rho"],
        "material_name": material_name,
    }
    data.update(overrides)
    return PipelineSpecification(**data)


def calculate_asme_b31_3_thickness(spec: PipelineSpecification) -> dict:
    """ASME B31.3 Para 304.1.2 Minimum Pressure Design Thickness & Hydrotest."""
    p = spec.design_pressure_pa
    d = spec.outer_diameter_m
    s = spec.material_allowable_stress_pa
    e = spec.weld_joint_efficiency
    y = spec.y_coefficient
    c = spec.corrosion_allowance_m

    # Pressure design thickness (Eq. 3a)
    t_pressure = (p * d) / (2.0 * (s * e + p * y))
    t_req = t_pressure + c
    t_nom = t_req / (1.0 - spec.mill_tolerance)
    p_hydro = 1.5 * spec.design_pressure_pa

    return {
        "t_pressure_design_mm": round(t_pressure * 1e3, 3),
        "t_required_min_mm": round(t_req * 1e3, 3),
        "t_nominal_recommended_mm": round(t_nom * 1e3, 3),
        "hydrostatic_test_pressure_bar": round(p_hydro * 1e-5, 2)
    }


def calculate_thermal_contraction_and_omega_loop(
    spec: PipelineSpecification,
    anchor_distance_m: float,
    outer_diameter_m: float
) -> dict:
    """Thermal contraction and Omega expansion loop flexibility (ASME B31.3 Para 319)."""
    # Unit contraction
    contraction_per_meter = spec.thermal_expansion_coeff * spec.delta_t_k
    total_contraction_1km = contraction_per_meter * 1000.0
    delta_l_loop = contraction_per_meter * anchor_distance_m

    # Displacement stress limit S_A (ASME B31.3 319.4.1):
    #   Eq. 1a: S_A = f (1.25 S_c + 0.25 S_h)
    #   Eq. 1b: S_A = f [1.25 (S_c + S_h) - S_L]  when S_h > S_L
    # S_c = cold allowable, S_h = hot allowable (0 => cold-only), f = stress-range factor,
    # S_L = sustained stress (pressure + weight).
    s_c = spec.material_allowable_stress_pa
    s_h = spec.material_allowable_stress_hot_pa
    f = spec.stress_range_factor
    s_l = spec.sustained_stress_pa
    if s_h > s_l:
        s_a = f * (1.25 * (s_c + s_h) - s_l)   # Eq. 1b
    else:
        s_a = f * (1.25 * s_c + 0.25 * s_h)     # Eq. 1a
    s_a = max(s_a, 1e5)

    # Minimum leg length H_min = sqrt(6 * E * D * DeltaL / S_A)
    e = spec.pipe_youngs_modulus_pa
    d = outer_diameter_m
    h_min = math.sqrt((6.0 * e * d * delta_l_loop) / s_a)

    return {
        "contraction_rate_mm_per_m": round(contraction_per_meter * 1e3, 3),
        "total_line_contraction_m": round(total_contraction_1km, 3),
        "loop_absorbed_delta_l_mm": round(delta_l_loop * 1e3, 2),
        "allowable_displacement_stress_mpa": round(s_a * 1e-6, 1),
        "min_omega_loop_leg_height_m": round(h_min, 2)
    }


def calculate_joukowsky_surge(
    spec: PipelineSpecification,
    nominal_velocity_m_s: float,
    valve_closure_time_s: float,
    wall_thickness_m: float
) -> dict:
    """Joukowsky water hammer and ESDV valve closure dynamics (SIGTTO guidelines)."""
    t_w = max(wall_thickness_m, 1e-4)
    d_i = max(spec.outer_diameter_m - 2.0 * t_w, 0.01)
    k = spec.fluid_bulk_modulus_pa
    rho = max(spec.fluid_density_kg_m3, 1.0)
    e = spec.pipe_youngs_modulus_pa

    # Korteweg acoustic wave speed in elastic pipe
    c_sound = math.sqrt((k / rho) / (1.0 + (k / e) * (d_i / t_w)))

    # Critical reflection time
    t_crit = (2.0 * spec.pipeline_length_m) / c_sound

    # Maximum Joukowsky surge (instantaneous closure)
    delta_p_instant = rho * c_sound * nominal_velocity_m_s

    # Actual surge considering valve closure time
    if valve_closure_time_s <= t_crit:
        delta_p_actual = delta_p_instant
        regime = "Instantaneous (Joukowsky Max Surge)"
    else:
        delta_p_actual = (2.0 * rho * spec.pipeline_length_m * nominal_velocity_m_s) / max(valve_closure_time_s, 0.01)
        regime = "Gradual (Attenuated Wave)"

    peak_pressure_bar = (spec.operating_pressure_pa + delta_p_actual) * 1e-5

    # Safe closure time for 133% MAWP surge limit
    p_mawp = spec.design_pressure_pa
    delta_p_allowable = max(0.33 * p_mawp, 1e5)
    min_safe_time_s = (2.0 * rho * spec.pipeline_length_m * nominal_velocity_m_s) / delta_p_allowable

    return {
        "speed_of_sound_m_s": round(c_sound, 1),
        "critical_time_s": round(t_crit, 2),
        "instantaneous_surge_bar": round(delta_p_instant * 1e-5, 2),
        "actual_surge_bar": round(delta_p_actual * 1e-5, 2),
        "peak_line_pressure_bar": round(peak_pressure_bar, 2),
        "closure_regime": regime,
        "recommended_min_valve_closure_s": round(max(min_safe_time_s * 1.5, 15.0), 1)
    }
