"""Multi-layer radial heat transfer model for insulated cryogenic pipelines."""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import math
from core.fluids import FluidProperties


@dataclass
class InsulationLayer:
    """Represents a concentric cylindrical insulation layer."""
    name: str
    thickness_m: float
    thermal_conductivity: float  # W/(m*K)


class PipeThermalModel:
    """Calculates radial thermal resistance network and heat ingress per meter."""

    def __init__(
        self,
        inner_diameter_m: float,
        wall_thickness_m: float,
        pipe_conductivity: float = 15.0,  # W/m-K (Stainless Steel 304L/316L)
        insulation_layers: List[InsulationLayer] = None,
        ambient_temperature_k: float = 298.15,  # 25 °C
        wind_speed_m_s: float = 2.0,
        surface_emissivity: float = 0.85,
    ):
        self.inner_diameter_m = inner_diameter_m
        self.wall_thickness_m = wall_thickness_m
        self.pipe_conductivity = pipe_conductivity
        self.insulation_layers = insulation_layers or []
        self.ambient_temperature_k = ambient_temperature_k
        self.wind_speed_m_s = wind_speed_m_s
        self.surface_emissivity = surface_emissivity

        self.outer_pipe_diameter_m = self.inner_diameter_m + 2.0 * self.wall_thickness_m

    def _calculate_internal_convection_coeff(self, props: FluidProperties, mass_flow_rate: float) -> float:
        """Internal forced convection coefficient h_i (W/m^2*K) using Gnielinski/Dittus-Boelter.

        Smooth laminar-turbulent transition in Re ∈ [2000, 4000] to avoid the
        ~300% Nusselt jump at Re = 2300 with the hard switch.
        """
        flow_area = (math.pi / 4.0) * (self.inner_diameter_m ** 2)
        velocity = mass_flow_rate / (props.density * flow_area)
        re = (props.density * velocity * self.inner_diameter_m) / props.viscosity
        pr = (props.specific_heat * props.viscosity) / props.thermal_conductivity

        if re <= 2000.0:
            nu = 4.36  # Constant heat flux laminar flow
        elif re >= 4000.0:
            nu = 0.023 * (re ** 0.8) * (pr ** 0.4)  # Gnielinski / Dittus-Boelter
        else:
            # Linear blend in transition range 2000–4000
            blend = (re - 2000.0) / 2000.0
            nu_lam = 4.36
            nu_turb = 0.023 * (re ** 0.8) * (pr ** 0.4)
            nu = (1.0 - blend) * nu_lam + blend * nu_turb

        return (nu * props.thermal_conductivity) / self.inner_diameter_m

    def _calculate_external_heat_transfer_coeff(self, outer_diameter_m: float) -> float:
        """External convection (wind / natural) and Stefan-Boltzmann radiation coefficient."""
        # Wind forced convection correlation (Jurges / McAdams)
        v = max(0.5, self.wind_speed_m_s)
        h_conv = 1.163 * (4.0 + 12.0 * math.sqrt(v))

        # Linearized radiation coefficient at ambient temperature
        sigma = 5.670374e-8
        t_amb = self.ambient_temperature_k
        h_rad = 4.0 * self.surface_emissivity * sigma * (t_amb ** 3)

        return h_conv + h_rad

    def calculate_heat_ingress(
        self, props: FluidProperties, mass_flow_rate: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates heat ingress per meter (W/m) and radial temperature distribution.
        Returns: (heat_ingress_w_m, temperatures_dict)
        """
        r_current = self.inner_diameter_m / 2.0
        r_pipe_out = self.outer_pipe_diameter_m / 2.0

        # 1. Internal convection resistance
        h_i = self._calculate_internal_convection_coeff(props, mass_flow_rate)
        r_prime_int = 1.0 / (math.pi * self.inner_diameter_m * h_i)

        # 2. Pipe metal wall conduction resistance
        r_prime_pipe = math.log(r_pipe_out / r_current) / (2.0 * math.pi * self.pipe_conductivity)

        # 3. Insulation layers conduction resistance
        r_prime_ins = 0.0
        layer_radii = [r_pipe_out]
        layer_resistances = []
        r_walk = r_pipe_out
        for layer in self.insulation_layers:
            r_next = r_walk + layer.thickness_m
            r_res = math.log(r_next / r_walk) / (2.0 * math.pi * layer.thermal_conductivity)
            layer_resistances.append(r_res)
            r_prime_ins += r_res
            r_walk = r_next
            layer_radii.append(r_walk)

        outer_insulation_diameter_m = 2.0 * r_walk

        # 4. External ambient convection & radiation resistance
        h_o = self._calculate_external_heat_transfer_coeff(outer_insulation_diameter_m)
        r_prime_ext = 1.0 / (math.pi * outer_insulation_diameter_m * h_o)

        # Total radial thermal resistance per meter (K*m/W)
        r_prime_total = r_prime_int + r_prime_pipe + r_prime_ins + r_prime_ext

        delta_t_overall = self.ambient_temperature_k - props.temperature
        heat_ingress_w_m = delta_t_overall / r_prime_total

        # Compute radial temperature interfaces
        t_pipe_in = props.temperature + heat_ingress_w_m * r_prime_int
        t_pipe_out = t_pipe_in + heat_ingress_w_m * r_prime_pipe

        # Interface temperatures across insulation layers
        ins_temps = []
        t_cursor = t_pipe_out
        for r_res in layer_resistances:
            t_cursor += heat_ingress_w_m * r_res
            ins_temps.append(t_cursor)

        t_ins_out = ins_temps[-1] if ins_temps else t_pipe_out

        temperatures = {
            "fluid": props.temperature,
            "pipe_inner": t_pipe_in,
            "pipe_outer": t_pipe_out,
            "insulation_interfaces": ins_temps,
            "insulation_outer": t_ins_out,
            "ambient": self.ambient_temperature_k,
        }

        return heat_ingress_w_m, temperatures


def check_radial_consistency(
    t_wall_1d: float,
    t_wall_3d: float,
    label: str = "station",
) -> dict:
    """
    Compares the 1D radial-network inner-wall temperature with a 3D wall
    temperature at the same axial station. Returns absolute/relative delta
    and a consistency flag. Useful as a runtime diagnostic (B9).
    """
    delta_k = abs(t_wall_1d - t_wall_3d)
    rel_delta = delta_k / max(abs(t_wall_1d), 1.0)
    consistent = rel_delta <= 0.05  # 5 % tolerance
    return {
        "label": label,
        "t_wall_1d_k": t_wall_1d,
        "t_wall_3d_k": t_wall_3d,
        "delta_k": round(delta_k, 3),
        "relative_delta": round(rel_delta, 4),
        "consistent": consistent,
    }
