"""Thermodynamic real-fluid engine for Cryogenic LNG using CoolProp Helmholtz EOS."""

from dataclasses import dataclass
from typing import Dict, Optional
import math
import CoolProp.CoolProp as CP


@dataclass(frozen=True)
class FluidProperties:
    """Thermophysical properties of cryogenic fluid at given (T, P)."""
    temperature: float          # K
    pressure: float             # Pa
    density: float              # kg/m^3
    specific_heat: float        # J/(kg*K)
    viscosity: float            # Pa*s
    thermal_conductivity: float # W/(m*K)
    vapor_pressure: float       # Pa (saturation pressure at temperature T)
    enthalpy: float             # J/kg


class FluidManager:
    """Manages thermophysical property evaluations for pure methane and LNG mixtures."""

    def __init__(self, fluid_type: str = "pure_methane", composition: Optional[Dict[str, float]] = None):
        """
        Initialize fluid manager.
        :param fluid_type: 'pure_methane' or 'mixture'
        :param composition: Mole fractions e.g. {'Methane': 0.94, 'Ethane': 0.04, 'Propane': 0.01, 'Nitrogen': 0.01}
        """
        self.fluid_type = fluid_type
        self.composition = composition or {"Methane": 1.0}
        self._backend_string = self._build_backend_string()
        self._cache: Dict[tuple, FluidProperties] = {}

    def _build_backend_string(self) -> str:
        if self.fluid_type == "pure_methane" or len(self.composition) == 1:
            return "Methane"
        
        # Build CoolProp mixture string e.g. HEOS::Methane[0.94]&Ethane[0.04]...
        components = []
        fractions = []
        total = sum(self.composition.values())
        for comp, frac in self.composition.items():
            norm_frac = frac / total
            components.append(comp)
            fractions.append(norm_frac)

        comp_str = "&".join(f"{comp}[{frac:.4f}]" for comp, frac in zip(components, fractions))
        return f"HEOS::{comp_str}"

    def get_vapor_pressure(self, T: float) -> float:
        """Calculate saturation vapor pressure Psat(T) in Pa."""
        # Clamp temperature to valid range
        T_clamped = max(91.0, min(T, 190.0))
        try:
            if "HEOS::" in self._backend_string:
                # Bubble point pressure for mixture
                return float(CP.PropsSI("P", "T", T_clamped, "Q", 0, self._backend_string))
            else:
                return float(CP.PropsSI("P", "T", T_clamped, "Q", 0, "Methane"))
        except Exception:
            # Robust Antoine / Wagner fallback for methane
            # ln(Psat/Pc) = (Tc/T) * (a1*tau + a2*tau^1.5 + a3*tau^3 + a4*tau^6)
            Tc = 190.564  # K
            Pc = 4599200.0  # Pa
            tau = 1.0 - (T_clamped / Tc)
            if tau <= 0:
                return Pc
            # Simplified Wagner coefficients for Methane
            a1, a2, a3, a4 = -6.02242, 1.26652, -0.5707, -1.366
            ln_p_pc = (Tc / T_clamped) * (a1 * tau + a2 * (tau**1.5) + a3 * (tau**3) + a4 * (tau**6))
            p_sat = Pc * math.exp(ln_p_pc)
            
            # Mixture vapor pressure correction if nitrogen / heavier fractions exist
            if self.composition:
                n2_frac = self.composition.get("Nitrogen", 0.0)
                # Nitrogen raises vapor pressure significantly
                p_sat *= (1.0 + 1.8 * n2_frac)
            return p_sat

    def get_properties(self, T: float, P: float) -> FluidProperties:
        """
        Evaluate real fluid properties at temperature T (K) and pressure P (Pa).
        Uses quantized caching for fast finite-volume integration.
        """
        # Cache key rounded to 0.05 K and 100 Pa
        cache_key = (round(T, 2), round(P, -2))
        if cache_key in self._cache:
            return self._cache[cache_key]

        T_val = max(91.0, min(T, 350.0))
        P_val = max(50000.0, P)

        backend = self._backend_string
        try:
            rho = float(CP.PropsSI("D", "T", T_val, "P", P_val, backend))
            cp = float(CP.PropsSI("C", "T", T_val, "P", P_val, backend))
            mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, backend))
            k = float(CP.PropsSI("L", "T", T_val, "P", P_val, backend))
            h = float(CP.PropsSI("H", "T", T_val, "P", P_val, backend))
        except Exception:
            # Fallback to pure methane if mixture flash struggles
            try:
                rho = float(CP.PropsSI("D", "T", T_val, "P", P_val, "Methane"))
                cp = float(CP.PropsSI("C", "T", T_val, "P", P_val, "Methane"))
                mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, "Methane"))
                k = float(CP.PropsSI("L", "T", T_val, "P", P_val, "Methane"))
                h = float(CP.PropsSI("H", "T", T_val, "P", P_val, "Methane"))
                # Adjust density for heavier hydrocarbons
                if self.composition:
                    molar_mass_mix = (
                        self.composition.get("Methane", 0.94) * 16.04
                        + self.composition.get("Ethane", 0.04) * 30.07
                        + self.composition.get("Propane", 0.01) * 44.10
                        + self.composition.get("Nitrogen", 0.01) * 28.01
                    )
                    rho *= (molar_mass_mix / 16.04)
            except Exception:
                # Liquid methane physical correlations (near 112 K)
                rho = 422.6 - 1.45 * (T_val - 111.66)
                cp = 3480.0
                mu = 1.15e-4
                k = 0.185
                h = 0.0

        p_sat = self.get_vapor_pressure(T_val)

        props = FluidProperties(
            temperature=T,
            pressure=P,
            density=max(rho, 300.0),
            specific_heat=max(cp, 2000.0),
            viscosity=max(mu, 1e-5),
            thermal_conductivity=max(k, 0.05),
            vapor_pressure=max(p_sat, 1000.0),
            enthalpy=h
        )
        self._cache[cache_key] = props
        return props
