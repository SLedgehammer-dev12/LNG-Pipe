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

        # Initial state at inlet
        curr_t = cfg.inlet_temperature_k
        curr_p = cfg.inlet_pressure_pa

        results = PipelineSimulationResults(config=cfg)
        total_heat_ingress = 0.0

        for i in range(cfg.num_cells + 1):
            curr_x = i * dx
            props = self.fm.get_properties(curr_t, curr_p)
            q_prime, radial_temps = self.thermal_model.calculate_heat_ingress(props, cfg.mass_flow_rate_kg_s)

            velocity = cfg.mass_flow_rate_kg_s / (props.density * flow_area)
            reynolds = (props.density * velocity * cfg.inner_diameter_m) / props.viscosity
            p_sat = props.vapor_pressure
            margin = curr_p - p_sat

            results.distance_m.append(round(curr_x, 2))
            results.temperature_k.append(curr_t)
            results.pressure_pa.append(curr_p)
            results.vapor_pressure_pa.append(p_sat)
            results.flashing_margin_pa.append(margin)
            results.heat_ingress_w_m.append(q_prime)
            results.velocity_m_s.append(velocity)
            results.density_kg_m3.append(props.density)
            results.reynolds.append(reynolds)
            results.radial_temperatures.append(radial_temps)

            if margin <= 0.0:
                h_fg = self.fm.get_latent_heat(curr_p)
                t_sat, _ = self.fm.get_bubble_dew_temperature(curr_p)
                delta_t_superheat = max(0.0, curr_t - t_sat)
                vapor_quality = min(0.99, (props.specific_heat * delta_t_superheat) / max(h_fg, 1e4))
                # Saturated vapor properties for Lockhart-Martinelli (M_methane = 0.01604 kg/mol)
                rho_v = max(0.1, 0.01604 * curr_p / (8.314 * max(curr_t, 100.0)))
                alpha, phi_l_sq, _ = calculate_two_phase_flashing(
                    vapor_quality=vapor_quality,
                    liquid_density=props.density,
                    vapor_density=rho_v,
                    liquid_viscosity=props.viscosity,
                    vapor_viscosity=8.0e-6
                )
            else:
                alpha = 0.0
                phi_l_sq = 1.0

            results.void_fraction.append(alpha)
            results.two_phase_multiplier.append(phi_l_sq)

            if margin <= 0.0 and not results.has_flashed:
                results.has_flashed = True
                results.flashing_point_m = round(curr_x, 2)

            # Marching step for i < num_cells
            if i < cfg.num_cells:
                # 1. Hydraulic drop (friction + two-phase multiplier + hydrostatic elevation)
                f = calculate_churchill_friction_factor(reynolds, rel_roughness)
                dp_friction = f * (dx / cfg.inner_diameter_m) * (0.5 * props.density * (velocity ** 2)) * phi_l_sq
                dp_hydrostatic = props.density * g * sin_theta * dx
                dp_total = dp_friction + dp_hydrostatic

                # 2. Thermal energy rise (dT = q' * dx / (m * cp))
                dt = (q_prime * dx) / (cfg.mass_flow_rate_kg_s * props.specific_heat)
                total_heat_ingress += q_prime * dx

                # Update next cell states
                curr_p = max(1000.0, curr_p - dp_total)
                curr_t = curr_t + dt

        # Final summaries
        results.outlet_temperature_k = results.temperature_k[-1]
        results.outlet_pressure_pa = results.pressure_pa[-1]
        results.outlet_vapor_pressure_pa = results.vapor_pressure_pa[-1]
        results.inlet_vapor_pressure_pa = results.vapor_pressure_pa[0]
        results.total_heat_ingress_w = total_heat_ingress
        results.total_pressure_drop_pa = cfg.inlet_pressure_pa - results.outlet_pressure_pa
        results.min_flashing_margin_pa = min(results.flashing_margin_pa)

        return results
