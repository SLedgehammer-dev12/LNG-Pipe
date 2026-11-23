"""3D Cylindrical (r, theta, z) Finite-Volume Marching Thermal-Hydraulic Solver."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import math
import numpy as np
import CoolProp.CoolProp as CP

from core.fluids import FluidManager, FluidProperties
from core.heat_transfer import PipeThermalModel
from core.solver import PipelineSimulationConfig, calculate_churchill_friction_factor
from core.two_phase import calculate_two_phase_flashing


@dataclass
class Solver3DConfig:
    """Numerical grid configuration for 3D cylindrical marching solver."""
    pipeline_config: PipelineSimulationConfig
    n_radial: int = 12       # Number of radial shells in fluid
    n_azimuthal: int = 12    # Number of azimuthal sectors (theta)
    n_axial: int = 50        # Number of axial marching planes (z)

    def __getattr__(self, name: str):
        """Forward PipelineSimulationConfig attributes for unified 1D/3D interface compatibility."""
        if name == "pipeline_config":
            raise AttributeError(name)
        return getattr(self.pipeline_config, name)


@dataclass
class Simulation3DResults:
    """Full 3D volumetric fields and axial profile summaries."""
    config: Solver3DConfig
    distance_m: List[float] = field(default_factory=list)
    pressure_pa: List[float] = field(default_factory=list)
    bulk_temperature_k: List[float] = field(default_factory=list)
    center_temperature_k: List[float] = field(default_factory=list)
    wall_temperature_k: List[float] = field(default_factory=list)
    bulk_vapor_pressure_pa: List[float] = field(default_factory=list)
    wall_vapor_pressure_pa: List[float] = field(default_factory=list)
    bulk_flashing_margin_pa: List[float] = field(default_factory=list)
    wall_flashing_margin_pa: List[float] = field(default_factory=list)
    total_heat_ingress_w: float = 0.0
    total_pressure_drop_pa: float = 0.0

    # 3D temperature tensor: shape (n_axial + 1, n_radial, n_azimuthal)
    temp_field_k: np.ndarray = field(default_factory=lambda: np.zeros((0, 0, 0)))
    radial_coords_m: np.ndarray = field(default_factory=lambda: np.zeros(0))
    azimuthal_coords_rad: np.ndarray = field(default_factory=lambda: np.zeros(0))

    has_bulk_flashed: bool = False
    bulk_flashing_point_m: Optional[float] = None
    has_wall_flashed: bool = False
    wall_flashing_point_m: Optional[float] = None
    min_flashing_margin_pa: float = 0.0
    void_fraction: List[float] = field(default_factory=list)
    two_phase_multiplier: List[float] = field(default_factory=list)
    density_kg_m3: List[float] = field(default_factory=list)

    @property
    def flashing_margin_pa(self) -> List[float]:
        """Backward-compatible alias returning wall flashing margin (most conservative)."""
        return self.wall_flashing_margin_pa

    @property
    def temperature_k(self) -> List[float]:
        """Unified 1D/3D alias returning bulk axial temperature profile [K]."""
        return self.bulk_temperature_k

    @property
    def vapor_pressure_pa(self) -> List[float]:
        """Unified 1D/3D alias returning wall saturation vapor pressure profile [Pa]."""
        return self.wall_vapor_pressure_pa

    @property
    def outlet_temperature_k(self) -> float:
        """Unified 1D/3D outlet bulk temperature [K]."""
        return self.bulk_temperature_k[-1] if self.bulk_temperature_k else 0.0

    @property
    def outlet_pressure_pa(self) -> float:
        """Unified 1D/3D outlet pressure [Pa]."""
        return self.pressure_pa[-1] if self.pressure_pa else 0.0

    @property
    def outlet_vapor_pressure_pa(self) -> float:
        """Unified 1D/3D outlet wall vapor pressure [Pa]."""
        return self.wall_vapor_pressure_pa[-1] if self.wall_vapor_pressure_pa else 0.0

    @property
    def inlet_vapor_pressure_pa(self) -> float:
        """Unified 1D/3D inlet wall vapor pressure [Pa]."""
        return self.wall_vapor_pressure_pa[0] if self.wall_vapor_pressure_pa else 0.0

    @property
    def has_flashed(self) -> bool:
        """Unified 1D/3D flashing flag (True if wall or bulk flashed)."""
        return bool(self.has_wall_flashed or self.has_bulk_flashed)

    @property
    def flashing_point_m(self) -> Optional[float]:
        """Unified 1D/3D first flashing location [m]."""
        return self.wall_flashing_point_m if self.wall_flashing_point_m is not None else self.bulk_flashing_point_m

    @property
    def velocity_m_s(self) -> List[float]:
        """Unified 1D/3D axial velocity profile [m/s] computed from density and cross-section."""
        cfg = self.config.pipeline_config
        area = math.pi * ((cfg.inner_diameter_m / 2.0) ** 2)
        if area <= 0.0 or not self.density_kg_m3:
            return [0.0] * len(self.distance_m)
        return [cfg.mass_flow_rate_kg_s / (max(rho, 1e-6) * area) for rho in self.density_kg_m3]


def is_3d_results(results: object) -> bool:
    """Reload-safe check for Simulation3DResults across Streamlit module hot-reloads."""
    return (
        isinstance(results, Simulation3DResults)
        or hasattr(results, "bulk_temperature_k")
        or getattr(getattr(results, "__class__", None), "__name__", "") == "Simulation3DResults"
    )


def solve_tdma(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> np.ndarray:
    """
    Solves tridiagonal matrix system a[i]*x[i-1] + b[i]*x[i] + c[i]*x[i+1] = d[i]
    using Thomas Algorithm (TDMA). Unconditionally stable for diagonally dominant systems.
    """
    n = len(d)
    c_prime = np.zeros(n)
    d_prime = np.zeros(n)
    x = np.zeros(n)

    c_prime[0] = c[0] / b[0]
    d_prime[0] = d[0] / b[0]

    for i in range(1, n):
        denom = b[i] - a[i] * c_prime[i - 1]
        c_prime[i] = c[i] / denom if i < n - 1 else 0.0
        d_prime[i] = (d[i] - a[i] * d_prime[i - 1]) / denom

    x[-1] = d_prime[-1]
    for i in range(n - 2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i + 1]

    return x


class PipelineSolver3D:
    """
    3D Cylindrical Finite-Volume Marching Solver.
    Integrates the coupled Navier-Stokes / Energy conservation equations
    in (r, theta, z) coordinates along the pipe length using an unconditionally stable
    implicit radial conduction formulation.
    """

    def __init__(
        self,
        fluid_manager: FluidManager,
        thermal_model: PipeThermalModel,
        config: Solver3DConfig
    ):
        self.fm = fluid_manager
        self.thermal_model = thermal_model
        self.config = config

    def solve(self) -> Simulation3DResults:
        pipe_cfg = self.config.pipeline_config
        nr = self.config.n_radial
        nt = self.config.n_azimuthal
        nz = self.config.n_axial

        # Guard against invalid grid / geometry / flow inputs
        if pipe_cfg.mass_flow_rate_kg_s <= 0.0:
            raise ValueError(
                f"mass_flow_rate_kg_s must be > 0 (got {pipe_cfg.mass_flow_rate_kg_s}); "
                "use 1D solver or set a small positive flow for standby."
            )
        if pipe_cfg.length_m <= 0.0 or pipe_cfg.inner_diameter_m <= 0.0:
            raise ValueError("length_m and inner_diameter_m must be > 0")
        if nz < 1 or nr < 2 or nt < 1:
            raise ValueError("Grid dimensions must satisfy n_axial >= 1, n_radial >= 2, n_azimuthal >= 1")

        # Methane triple point pressure (11.696 kPa) — pressure floor for both solvers
        P_TRIPLE_PA = 11696.0

        r_max = pipe_cfg.inner_diameter_m / 2.0
        dz = pipe_cfg.length_m / nz
        d_theta = 2.0 * math.pi / nt
        g = 9.80665
        sin_incline = math.sin(math.radians(pipe_cfg.inclination_deg))

        # 1. Radial discretization
        # Wall-clustered grid: finest spacing near r = r_max to resolve thermal boundary layer
        eta = np.linspace(0.0, 1.0, nr + 1)
        r_faces = r_max * (1.0 - (1.0 - eta) ** 1.5)
        r_centers = 0.5 * (r_faces[:-1] + r_faces[1:])
        dr = r_faces[1:] - r_faces[:-1]
        theta_centers = np.linspace(0.5 * d_theta, 2.0 * math.pi - 0.5 * d_theta, nt)

        # Cross-sectional annular areas A[i]
        ring_areas = np.zeros(nr)
        for i in range(nr):
            ring_areas[i] = math.pi * (r_faces[i + 1] ** 2 - r_faces[i] ** 2)

        pipe_area = math.pi * (r_max ** 2)

        # 2. Velocity profile u_z(r)
        inlet_props = self.fm.get_properties(pipe_cfg.inlet_temperature_k, pipe_cfg.inlet_pressure_pa)
        v_mean = pipe_cfg.mass_flow_rate_kg_s / (inlet_props.density * pipe_area)
        re_inlet = (inlet_props.density * v_mean * pipe_cfg.inner_diameter_m) / inlet_props.viscosity

        u_profile = np.zeros(nr)
        if re_inlet > 2300:
            u_max = (60.0 / 49.0) * v_mean
            for i in range(nr):
                dist_wall = max(0.0, 1.0 - (r_centers[i] / r_max))
                u_profile[i] = u_max * (dist_wall ** (1.0 / 7.0))
        else:
            for i in range(nr):
                u_profile[i] = 2.0 * v_mean * (1.0 - (r_centers[i] / r_max) ** 2)

        # Normalize velocity field to conserve mass flow rate exactly
        ring_mass_flows = inlet_props.density * u_profile * ring_areas
        total_m_calc = np.sum(ring_mass_flows)
        if total_m_calc > 0:
            scale_fac = pipe_cfg.mass_flow_rate_kg_s / total_m_calc
            u_profile *= scale_fac
            ring_mass_flows = inlet_props.density * u_profile * ring_areas

        # 3. Turbulent thermal conductivity k_eff(r): zero eddy diffusivity in laminar flow, Van Driest damped Prandtl mixing in turbulent flow
        rel_roughness = pipe_cfg.roughness_m / pipe_cfg.inner_diameter_m
        f_darcy = calculate_churchill_friction_factor(re_inlet, rel_roughness)
        tau_w = 0.125 * f_darcy * inlet_props.density * (v_mean ** 2)
        u_tau = math.sqrt(max(1e-6, tau_w / inlet_props.density))
        nu_inlet = max(inlet_props.viscosity / inlet_props.density, 1e-8)

        k_eff_profile = np.zeros(nr)
        if re_inlet <= 2300.0:
            k_eff_profile[:] = inlet_props.thermal_conductivity
        else:
            pr_t = 0.85
            kappa = 0.41
            for i in range(nr):
                y = max(1e-5, r_max - r_centers[i])
                y_plus = (y * u_tau) / nu_inlet
                d_vd = 1.0 - math.exp(-y_plus / 26.0)
                l_mix = min(kappa * y * d_vd, 0.09 * r_max)
                du_dy = u_tau / max(kappa * y, 1e-6)
                eps_m = (l_mix ** 2) * du_dy
                eps_h = eps_m / pr_t
                k_turb = inlet_props.density * inlet_props.specific_heat * eps_h
                k_eff_profile[i] = inlet_props.thermal_conductivity + k_turb

        # Conductances between radial rings (W/K)
        # G_in[i] is between i and i-1 at face r_faces[i]
        g_in = np.zeros(nr)
        for i in range(1, nr):
            k_face = 0.5 * (k_eff_profile[i] + k_eff_profile[i - 1])
            area_face = 2.0 * math.pi * r_faces[i] * dz
            delta_r = r_centers[i] - r_centers[i - 1]
            g_in[i] = k_face * area_face / delta_r

        g_out = np.zeros(nr)
        for i in range(nr - 1):
            g_out[i] = g_in[i + 1]

        # 4. Initialize 3D Temperature field (nz + 1, nr, nt)
        temp_field = np.zeros((nz + 1, nr, nt))
        temp_field[0, :, :] = pipe_cfg.inlet_temperature_k

        curr_p = pipe_cfg.inlet_pressure_pa
        curr_h = inlet_props.enthalpy
        total_heat_ingress = 0.0
        molar_mass_kg = self.fm.mixture_molar_mass_g_mol() * 1e-3

        results = Simulation3DResults(
            config=self.config,
            radial_coords_m=r_centers,
            azimuthal_coords_rad=theta_centers
        )

        for k_idx in range(nz + 1):
            curr_x = k_idx * dz
            results.distance_m.append(round(curr_x, 2))
            results.pressure_pa.append(curr_p)

            slice_t = temp_field[k_idx, :, :]
            radial_t_mean = np.mean(slice_t, axis=1)
            # Cup-mixing bulk temperature
            t_bulk = float(np.sum(ring_mass_flows * radial_t_mean) / np.sum(ring_mass_flows))
            t_center = float(radial_t_mean[0])
            t_wall = float(radial_t_mean[-1])

            props_station = self.fm.get_properties(t_bulk, curr_p)
            p_sat_bulk = props_station.vapor_pressure
            p_sat_wall = self.fm.get_vapor_pressure(t_wall)

            margin_bulk = curr_p - p_sat_bulk
            margin_wall = curr_p - p_sat_wall

            results.bulk_temperature_k.append(t_bulk)
            results.center_temperature_k.append(t_center)
            results.wall_temperature_k.append(t_wall)
            results.bulk_vapor_pressure_pa.append(p_sat_bulk)
            results.wall_vapor_pressure_pa.append(p_sat_wall)
            results.bulk_flashing_margin_pa.append(margin_bulk)
            results.wall_flashing_margin_pa.append(margin_wall)

            if margin_bulk <= 0.0 and not results.has_bulk_flashed:
                results.has_bulk_flashed = True
                results.bulk_flashing_point_m = round(curr_x, 2)

            if margin_wall <= 0.0 and not results.has_wall_flashed:
                results.has_wall_flashed = True
                results.wall_flashing_point_m = round(curr_x, 2)

            vapor_quality = 0.0
            liq_density = props_station.density
            liq_viscosity = props_station.viscosity
            flow_density = liq_density
            if margin_wall <= 0.0:
                h_fg = max(self.fm.get_latent_heat(curr_p), 1e4)
                t_sat, _ = self.fm.get_bubble_dew_temperature(curr_p)
                h_liq = self.fm.get_saturated_liquid_enthalpy(curr_p)
                if liq_density < 100.0:
                    liq_props = self.fm.get_properties(max(90.7, t_sat - 0.1), curr_p)
                    liq_density = liq_props.density
                    liq_viscosity = liq_props.viscosity
                # First Law quality: bulk enthalpy excess above h_f(P) + local wall-superheat fraction when only boundary layer flashes
                x_bulk = max(0.0, (curr_h - h_liq) / h_fg)
                wall_excess_h = float(np.sum(ring_mass_flows * np.maximum(0.0, radial_t_mean - t_sat))) * props_station.specific_heat / max(float(np.sum(ring_mass_flows)), 1e-6)
                vapor_quality = min(0.99, max(x_bulk, wall_excess_h / h_fg))
                rho_v = max(0.05, molar_mass_kg * curr_p / (8.314 * max(t_sat, 90.7)))
                alpha, phi_l_sq, two_phase_rho = calculate_two_phase_flashing(
                    vapor_quality=vapor_quality,
                    liquid_density=liq_density,
                    vapor_density=rho_v,
                    liquid_viscosity=liq_viscosity,
                    vapor_viscosity=8.0e-6
                )
                flow_density = two_phase_rho
            else:
                alpha = 0.0
                phi_l_sq = 1.0

            results.density_kg_m3.append(flow_density)
            results.void_fraction.append(alpha)
            results.two_phase_multiplier.append(phi_l_sq)

            if k_idx < nz:
                props = props_station
                q_prime_total, _ = self.thermal_model.calculate_heat_ingress(props, pipe_cfg.mass_flow_rate_kg_s)
                total_heat_ingress += q_prime_total * dz
                curr_h += (q_prime_total * dz) / pipe_cfg.mass_flow_rate_kg_s - g * sin_incline * dz

                # Solve implicit axisymmetric radial conduction once per axial slice and broadcast across theta
                c_cap = (ring_mass_flows / nt) * props.specific_heat
                g_in_sec = g_in / nt
                g_out_sec = g_out / nt

                a_mat = np.zeros(nr)
                a_mat[1:] = -g_in_sec[1:]
                b_mat = c_cap + g_in_sec + g_out_sec
                c_mat = np.zeros(nr)
                c_mat[:-1] = -g_out_sec[:-1]

                rhs = c_cap * radial_t_mean
                rhs[-1] += (q_prime_total * dz) / nt
                next_radial_t = solve_tdma(a_mat, b_mat, c_mat, rhs)

                # Pin flashing cells to T_sat(P) so sensible temperature does not run away past boiling
                if margin_wall <= 0.0:
                    next_radial_t = np.minimum(next_radial_t, max(90.7, t_sat))
                temp_field[k_idx + 1, :, :] = next_radial_t[:, None]

                # Hydraulic pressure drop: liquid-only friction * Phi_L^2 + hydrostatic + momentum acceleration
                g_total = pipe_cfg.mass_flow_rate_kg_s / pipe_area
                g_liq = g_total * (1.0 - vapor_quality)
                if alpha > 1e-5:
                    re_liq = max((g_liq * pipe_cfg.inner_diameter_m) / liq_viscosity, 1.0)
                    f_liq = calculate_churchill_friction_factor(re_liq, rel_roughness)
                    dp_fric = f_liq * (dz / pipe_cfg.inner_diameter_m) * ((g_liq ** 2) / (2.0 * liq_density)) * phi_l_sq
                else:
                    v_mean_local = pipe_cfg.mass_flow_rate_kg_s / (flow_density * pipe_area)
                    re_local = (flow_density * v_mean_local * pipe_cfg.inner_diameter_m) / props.viscosity
                    f_local = calculate_churchill_friction_factor(re_local, rel_roughness)
                    dp_fric = f_local * (dz / pipe_cfg.inner_diameter_m) * (0.5 * flow_density * (v_mean_local ** 2))
                dp_hydro = flow_density * g * sin_incline * dz
                dp_accel = 0.0
                if alpha > 1e-5 and len(results.density_kg_m3) >= 2:
                    dp_accel = g_total ** 2 * (1.0 / max(results.density_kg_m3[-1], 1e-3) - 1.0 / max(results.density_kg_m3[-2], 1e-3))
                curr_p = max(P_TRIPLE_PA, curr_p - dp_fric - dp_hydro - dp_accel)

        results.temp_field_k = temp_field
        results.total_heat_ingress_w = total_heat_ingress
        results.total_pressure_drop_pa = pipe_cfg.inlet_pressure_pa - results.pressure_pa[-1]
        results.min_flashing_margin_pa = min(results.wall_flashing_margin_pa)

        return results
