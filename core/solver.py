"""1D Finite-Volume Thermal-Hydraulic Pipeline Solver for Cryogenic LNG."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import math
import numpy as np

from core.fluids import FluidManager, FluidProperties
from core.heat_transfer import PipeThermalModel
from core.two_phase import calculate_two_phase_flashing


@dataclass
class PipelineSimulationConfig:
    """Configuration parameters for pipeline simulation."""
    length_m: float
    inner_diameter_m: float
    roughness_m: float = 4.5e-5
    inclination_deg: float = 0.0
    inlet_temperature_k: float = 111.5
    inlet_pressure_pa: float = 500000.0  # 5 bar
    mass_flow_rate_kg_s: float = 20.0
    num_cells: int = 100


@dataclass
class PipelineSimulationResults:
    """Full numerical simulation results along pipeline length."""
    config: PipelineSimulationConfig
    distance_m: List[float] = field(default_factory=list)
    temperature_k: List[float] = field(default_factory=list)
    pressure_pa: List[float] = field(default_factory=list)
    vapor_pressure_pa: List[float] = field(default_factory=list)
    flashing_margin_pa: List[float] = field(default_factory=list)
    heat_ingress_w_m: List[float] = field(default_factory=list)
    velocity_m_s: List[float] = field(default_factory=list)
    density_kg_m3: List[float] = field(default_factory=list)
    reynolds: List[float] = field(default_factory=list)
    radial_temperatures: List[Dict[str, float]] = field(default_factory=list)
    void_fraction: List[float] = field(default_factory=list)
    two_phase_multiplier: List[float] = field(default_factory=list)

    outlet_temperature_k: float = 0.0
    outlet_pressure_pa: float = 0.0
    outlet_vapor_pressure_pa: float = 0.0
    inlet_vapor_pressure_pa: float = 0.0
    total_heat_ingress_w: float = 0.0
    total_pressure_drop_pa: float = 0.0
    has_flashed: bool = False
    flashing_point_m: Optional[float] = None
    min_flashing_margin_pa: float = 0.0


def calculate_churchill_friction_factor(re: float, relative_roughness: float) -> float:
    """
    Churchill (1977) friction factor equation.
    Smoothly spans laminar (Re < 2300), transition, and rough turbulent flows.
    """
    re_safe = max(re, 1.0)
    theta1 = (8.0 / re_safe) ** 12
    term_a = (2.457 * math.log(1.0 / ((7.0 / re_safe) ** 0.9 + 0.27 * relative_roughness))) ** 16
    term_b = (37530.0 / re_safe) ** 16
    theta2 = (term_a + term_b) ** (-1.5)
    return 8.0 * ((theta1 + theta2) ** (1.0 / 12.0))


class PipelineSolver:
    """1D Finite-Volume marching solver coupling energy and momentum equations."""

    def __init__(
        self,
        fluid_manager: FluidManager,
        thermal_model: PipeThermalModel,
        config: PipelineSimulationConfig
    ):
        self.fm = fluid_manager
        self.thermal_model = thermal_model
        self.config = config

    def solve(self) -> PipelineSimulationResults:
        """Executes marching integration from inlet (x=0) to outlet (x=L)."""
        cfg = self.config
        dx = cfg.length_m / cfg.num_cells
        flow_area = (math.pi / 4.0) * (cfg.inner_diameter_m ** 2)
        rel_roughness = cfg.roughness_m / cfg.inner_diameter_m
        sin_theta = math.sin(math.radians(cfg.inclination_deg))
        g = 9.80665

        # Triple-point pressure floor for methane (~11.7 kPa); below this the EOS is invalid.
        P_TRIPLE_PA = 11696.0

        # Initial state at inlet
        curr_t = cfg.inlet_temperature_k
        curr_p = cfg.inlet_pressure_pa

        results = PipelineSimulationResults(config=cfg)
        total_heat_ingress = 0.0

        for i in range(cfg.num_cells + 1):
            curr_x = i * dx
            props = self.fm.get_properties(curr_t, curr_p)
            q_prime, radial_temps = self.thermal_model.calculate_heat_ingress(props, cfg.mass_flow_rate_kg_s)

            # Enthalpy state: h (J/kg). Initialized from CoolProp; updated by heat ingress.
            if i == 0:
                curr_h = props.enthalpy

            p_sat = props.vapor_pressure
            margin = curr_p - p_sat

            results.distance_m.append(round(curr_x, 2))
            results.temperature_k.append(curr_t)
            results.pressure_pa.append(curr_p)
            results.vapor_pressure_pa.append(p_sat)
            results.flashing_margin_pa.append(margin)
            results.heat_ingress_w_m.append(q_prime)
            results.radial_temperatures.append(radial_temps)

            alpha = 0.0
            phi_l_sq = 1.0
            flow_density = props.density
            if margin <= 0.0:
                # Two-phase flashing regime: pin T to Tsat(P), compute quality from enthalpy.
                h_fg = self.fm.get_latent_heat(curr_p)
                t_sat, _ = self.fm.get_bubble_dew_temperature(curr_p)
                curr_t = t_sat  # mixture temperature pinned to saturation at local pressure
                h_liq = self.fm.get_properties(t_sat, curr_p).enthalpy
                h_vap = self.fm.get_properties(t_sat, curr_p + 100.0).enthalpy  # approximate sat-vapor via property call
                h_fg = max(h_vap - h_liq, 1e4)
                # Quality from cumulative enthalpy relative to saturated liquid at local P
                vapor_quality = min(0.99, max(0.0, (curr_h - h_liq) / h_fg))
                # Saturated vapor density via ideal-gas estimate for Lockhart-Martinelli
                rho_v = max(0.05, 0.01604 * curr_p / (8.314 * max(curr_t, 90.7)))
                alpha, phi_l_sq, two_phase_rho = calculate_two_phase_flashing(
                    vapor_quality=vapor_quality,
                    liquid_density=props.density,
                    vapor_density=rho_v,
                    liquid_viscosity=props.viscosity,
                    vapor_viscosity=8.0e-6
                )
                # Use homogeneous two-phase density for velocity / hydrostatics when flashing
                flow_density = two_phase_rho
            else:
                alpha = 0.0
                phi_l_sq = 1.0

            results.density_kg_m3.append(flow_density)
            # Velocity / Reynolds based on the effective (possibly two-phase) density
            velocity = cfg.mass_flow_rate_kg_s / (flow_density * flow_area)
            reynolds = (flow_density * velocity * cfg.inner_diameter_m) / props.viscosity
            results.velocity_m_s.append(velocity)
            results.reynolds.append(reynolds)
            results.void_fraction.append(alpha)
            results.two_phase_multiplier.append(phi_l_sq)

            if margin <= 0.0 and not results.has_flashed:
                results.has_flashed = True
                results.flashing_point_m = round(curr_x, 2)

            # Marching step for i < num_cells
            if i < cfg.num_cells:
                # 1. Hydraulic drop (friction * two-phase multiplier + hydrostatic elevation)
                f = calculate_churchill_friction_factor(reynolds, rel_roughness)
                dp_friction = f * (dx / cfg.inner_diameter_m) * (0.5 * flow_density * (velocity ** 2)) * phi_l_sq
                dp_hydrostatic = flow_density * g * sin_theta * dx
                # Two-phase acceleration / momentum pressure-drop term (dG/dx)
                dp_accel = 0.0
                if alpha > 1e-5 and len(results.density_kg_m3) >= 2:
                    mass_flux = cfg.mass_flow_rate_kg_s / flow_area
                    dp_accel = mass_flux ** 2 * (1.0 / max(results.density_kg_m3[-1], 1e-3) - 1.0 / max(results.density_kg_m3[-2], 1e-3))
                dp_total = dp_friction + dp_hydrostatic + dp_accel

                # 2. Thermal energy rise as enthalpy (dH = q' * dx / m); absorbs latent heat on flashing
                dh = (q_prime * dx) / cfg.mass_flow_rate_kg_s
                curr_h += dh
                total_heat_ingress += q_prime * dx

                # Convert enthalpy back to temperature: pinned at Tsat(P) while flashing
                if margin <= 0.0:
                    curr_t = max(90.7, self.fm.get_bubble_dew_temperature(curr_p)[0])
                else:
                    curr_t = curr_t + dh / max(props.specific_heat, 100.0)

                # Update next cell pressure; stop at methane triple point instead of 1 kPa floor
                curr_p = max(P_TRIPLE_PA, curr_p - dp_total)

        # Final summaries
        results.outlet_temperature_k = results.temperature_k[-1]
        results.outlet_pressure_pa = results.pressure_pa[-1]
        results.outlet_vapor_pressure_pa = results.vapor_pressure_pa[-1]
        results.inlet_vapor_pressure_pa = results.vapor_pressure_pa[0]
        results.total_heat_ingress_w = total_heat_ingress
        results.total_pressure_drop_pa = cfg.inlet_pressure_pa - results.outlet_pressure_pa
        results.min_flashing_margin_pa = min(results.flashing_margin_pa)

        return results
