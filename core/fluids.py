"""Thermodynamic real-fluid engine for Cryogenic LNG using CoolProp Helmholtz EOS."""

from dataclasses import dataclass
from typing import Dict, Optional
import math
import CoolProp.CoolProp as CP


# Comprehensive CoolProp-supported LNG & Natural Gas Component Catalog
# Molar masses in g/mol; volatility_factor adjusts fallback mixture vapor pressure relative to Methane at ~112 K.
LNG_COMPONENTS_CATALOG: Dict[str, Dict[str, object]] = {
    # Paraffinic Hydrocarbons (Alkanes C1 - C10)
    "Methane":         {"label": "Metan (CH4)",              "molar_mass": 16.043,  "volatility_factor": 0.0,   "category": "Hafif Hidrokarbon"},
    "Ethane":          {"label": "Etan (C2H6)",              "molar_mass": 30.070,  "volatility_factor": -0.92, "category": "Hafif Hidrokarbon"},
    "Propane":         {"label": "Propan (C3H8)",            "molar_mass": 44.096,  "volatility_factor": -0.98, "category": "Ağır Hidrokarbon (LPG)"},
    "IsoButane":       {"label": "İzo-Bütan (i-C4H10)",      "molar_mass": 58.122,  "volatility_factor": -0.99, "category": "Ağır Hidrokarbon (LPG)"},
    "n-Butane":        {"label": "Normal Bütan (n-C4H10)",   "molar_mass": 58.122,  "volatility_factor": -0.99, "category": "Ağır Hidrokarbon (LPG)"},
    "Isopentane":      {"label": "İzo-Pentan (i-C5H12)",     "molar_mass": 72.149,  "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C5+)"},
    "n-Pentane":       {"label": "Normal Pentan (n-C5H12)",  "molar_mass": 72.149,  "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C5+)"},
    "Neopentane":      {"label": "Neo-Pentan (neo-C5H12)",   "molar_mass": 72.149,  "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C5+)"},
    "n-Hexane":        {"label": "Normal Hekzan (n-C6H14)",  "molar_mass": 86.175,  "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C6+)"},
    "Isohexane":       {"label": "İzo-Hekzan (i-C6H14)",     "molar_mass": 86.175,  "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C6+)"},
    "n-Heptane":       {"label": "Normal Heptan (n-C7H16)",  "molar_mass": 100.202, "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C6+)"},
    "n-Octane":        {"label": "Normal Oktan (n-C8H18)",   "molar_mass": 114.229, "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C6+)"},
    "n-Nonane":        {"label": "Normal Nonan (n-C9H20)",   "molar_mass": 128.255, "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C6+)"},
    "n-Decane":        {"label": "Normal Dekan (n-C10H22)",  "molar_mass": 142.282, "volatility_factor": -1.00, "category": "Ağır Hidrokarbon (C6+)"},
    # Cyclic, Aromatic & Unsaturated Hydrocarbons
    "Cyclopentane":    {"label": "Siklopentan (C5H10)",      "molar_mass": 70.133,  "volatility_factor": -1.00, "category": "Halkalı / Aromatik HC"},
    "Cyclohexane":     {"label": "Siklohekzan (C6H12)",      "molar_mass": 84.160,  "volatility_factor": -1.00, "category": "Halkalı / Aromatik HC"},
    "Benzene":         {"label": "Benzen (C6H6)",            "molar_mass": 78.112,  "volatility_factor": -1.00, "category": "Halkalı / Aromatik HC"},
    "Toluene":         {"label": "Toluen (C7H8)",            "molar_mass": 92.138,  "volatility_factor": -1.00, "category": "Halkalı / Aromatik HC"},
    "Ethylene":        {"label": "Etilen (C2H4)",            "molar_mass": 28.053,  "volatility_factor": -0.75, "category": "Doymamış Hidrokarbon"},
    "Propylene":       {"label": "Propilen (C3H6)",          "molar_mass": 42.080,  "volatility_factor": -0.96, "category": "Doymamış Hidrokarbon"},
    # Inert, Acid & Permanent Gases
    "Nitrogen":        {"label": "Azot (N2)",                "molar_mass": 28.013,  "volatility_factor": 1.80,  "category": "İnert / Asit Gazlar"},
    "CarbonDioxide":   {"label": "Karbondioksit (CO2)",      "molar_mass": 44.010,  "volatility_factor": -0.95, "category": "İnert / Asit Gazlar"},
    "HydrogenSulfide": {"label": "Hidrojen Sülfür (H2S)",    "molar_mass": 34.081,  "volatility_factor": -0.95, "category": "İnert / Asit Gazlar"},
    "Helium":          {"label": "Helyum (He)",              "molar_mass": 4.003,   "volatility_factor": 3.50,  "category": "İnert / Asit Gazlar"},
    "Hydrogen":        {"label": "Hidrojen (H2)",            "molar_mass": 2.016,   "volatility_factor": 2.80,  "category": "İnert / Asit Gazlar"},
    "Argon":           {"label": "Argon (Ar)",               "molar_mass": 39.948,  "volatility_factor": 0.90,  "category": "İnert / Asit Gazlar"},
    "Oxygen":          {"label": "Oksijen (O2)",             "molar_mass": 31.999,  "volatility_factor": 0.70,  "category": "İnert / Asit Gazlar"},
    "CarbonMonoxide":  {"label": "Karbonmonoksit (CO)",      "molar_mass": 28.010,  "volatility_factor": 1.40,  "category": "İnert / Asit Gazlar"},
}

COMPONENT_ALIASES: Dict[str, str] = {
    "Butane": "n-Butane",
    "IsoPentane": "Isopentane",
    "Pentane": "n-Pentane",
    "NeoPentane": "Neopentane",
    "Hexane": "n-Hexane",
    "Heptane": "n-Heptane",
    "Octane": "n-Octane",
    "Nonane": "n-Nonane",
    "Decane": "n-Decane",
}

AVAILABLE_LNG_COMPONENTS = list(LNG_COMPONENTS_CATALOG.keys())

COMPONENT_LABELS: Dict[str, str] = {
    k: str(v["label"]) for k, v in LNG_COMPONENTS_CATALOG.items()
}
for _alias, _target in COMPONENT_ALIASES.items():
    COMPONENT_LABELS[_alias] = str(LNG_COMPONENTS_CATALOG[_target]["label"])


def canonical_component_name(name: str) -> str:
    """Resolve user/legacy component name to canonical CoolProp fluid identifier."""
    return COMPONENT_ALIASES.get(name, name)


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
        raw_comp = composition or {"Methane": 1.0}
        self.composition = dict(raw_comp)
        self.normalized_composition: Dict[str, float] = {}
        self._backend_string = self._build_backend_string()
        self._cache: Dict[tuple, FluidProperties] = {}
        self._psat_cache: Dict[float, float] = {}

    def _build_backend_string(self) -> str:
        total = sum(self.composition.values())
        if total <= 0.0:
            raise ValueError("Kompozisyon toplamı sıfır veya negatif; en az bir componente mol oranı gereklidir.")

        norm_map: Dict[str, float] = {}
        for comp, frac in self.composition.items():
            if frac < 0.0:
                raise ValueError(f"Kompozisyon negatif olamaz: {comp}={frac}")
            canon = canonical_component_name(comp)
            norm_map[canon] = norm_map.get(canon, 0.0) + (frac / total)

        self.normalized_composition = norm_map

        if self.fluid_type == "pure_methane" or (len(norm_map) == 1 and "Methane" in norm_map):
            return "Methane"

        comp_str = "&".join(f"{comp}[{frac:.6f}]" for comp, frac in norm_map.items() if frac > 0.0)
        return f"HEOS::{comp_str}"

    def composition_sum(self) -> float:
        """Returns the sum of composition mole fractions (should be ~100 for % inputs, ~1.0 for fractions)."""
        return sum(self.composition.values())

    def mixture_molar_mass_g_mol(self) -> float:
        """Calculate mixture molar mass (g/mol) from normalized mole fractions."""
        if self.fluid_type == "pure_methane" or not self.normalized_composition:
            return 16.043
        mm = 0.0
        for comp, frac in self.normalized_composition.items():
            entry = LNG_COMPONENTS_CATALOG.get(comp)
            if entry is not None:
                mm += frac * float(entry["molar_mass"])
            else:
                try:
                    mm += frac * float(CP.PropsSI("M", comp)) * 1000.0
                except Exception:
                    mm += frac * 16.043
        return max(mm, 2.0)

    def get_npsh_margin_a(self, T: float, P: float) -> float:
        """
        Net Positive Suction Head available (m of liquid) at (T, P).
        NPSH_a = (P_abs - P_sat(T)) / (rho * g). Mirrors the flashing margin
        expressed in head units; negative values indicate cavitation/flashing risk.
        """
        props = self.get_properties(T, P)
        p_sat = props.vapor_pressure
        rho = max(props.density, 1e-3)
        return (P - p_sat) / (rho * 9.80665)

    def get_vapor_pressure(self, T: float) -> float:
        """Calculate saturation vapor pressure Psat(T) in Pa."""
        # Clamp temperature to valid range
        T_clamped = max(91.0, min(T, 190.0))
        cache_key = round(T_clamped, 2)
        if cache_key in self._psat_cache:
            return self._psat_cache[cache_key]
        try:
            if "HEOS::" in self._backend_string:
                # Bubble point pressure for mixture
                p_b = float(CP.PropsSI("P", "T", T_clamped, "Q", 0, self._backend_string))
                if math.isfinite(p_b) and 1000.0 < p_b < 1.5e7:
                    self._psat_cache[cache_key] = p_b
                    return p_b
                raise ValueError("Invalid mixture Psat from CoolProp")
            else:
                p_m = float(CP.PropsSI("P", "T", T_clamped, "Q", 0, "Methane"))
                if math.isfinite(p_m) and p_m > 0.0:
                    self._psat_cache[cache_key] = p_m
                    return p_m
                raise ValueError("Invalid Methane Psat")
        except Exception:
            # Robust Antoine / Wagner fallback for methane + Raoult/volatility mixture correction
            Tc = 190.564  # K
            Pc = 4599200.0  # Pa
            tau = 1.0 - (T_clamped / Tc)
            if tau <= 0:
                self._psat_cache[cache_key] = Pc
                return Pc
            a1, a2, a3, a4 = -6.02242, 1.26652, -0.5707, -1.366
            ln_p_pc = (Tc / T_clamped) * (a1 * tau + a2 * (tau**1.5) + a3 * (tau**3) + a4 * (tau**6))
            p_sat = Pc * math.exp(ln_p_pc)

            if self.fluid_type != "pure_methane" and self.normalized_composition:
                vol_shift = 0.0
                for comp, frac in self.normalized_composition.items():
                    entry = LNG_COMPONENTS_CATALOG.get(comp)
                    if entry is not None:
                        vol_shift += frac * float(entry["volatility_factor"])
                p_sat *= max(0.15, 1.0 + vol_shift)
            self._psat_cache[cache_key] = p_sat
            return p_sat

    def _evaluate_liquid_mixture_abstract_state(self, T_val: float, P_val: float) -> Optional[tuple[float, float, float, float, float]]:
        """Evaluate liquid mixture via CoolProp AbstractState (HEOS -> SRK -> PR) with iphase_liquid."""
        comps = [c for c, f in self.normalized_composition.items() if f > 0.0]
        fracs = [self.normalized_composition[c] for c in comps]
        if len(comps) <= 1:
            return None
        fluid_join = "&".join(comps)
        for eos_name in ("HEOS", "SRK", "PR"):
            try:
                st = CP.AbstractState(eos_name, fluid_join)
                st.set_mole_fractions(fracs)
                if T_val < 175.0 and P_val >= 80000.0:
                    st.specify_phase(CP.iphase_liquid)
                st.update(CP.PT_INPUTS, P_val, T_val)
                rho = float(st.rhomass())
                cp = float(st.cpmass())
                h = float(st.hmass())
                if not (math.isfinite(rho) and math.isfinite(cp) and math.isfinite(h) and rho > 50.0 and cp > 500.0):
                    continue
                try:
                    mu = float(st.viscosity())
                    if not math.isfinite(mu) or mu <= 0.0:
                        raise ValueError()
                except Exception:
                    mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, "Methane")) * math.sqrt(self.mixture_molar_mass_g_mol() / 16.043)
                try:
                    k = float(st.conductivity())
                    if not math.isfinite(k) or k <= 0.0:
                        raise ValueError()
                except Exception:
                    k = float(CP.PropsSI("L", "T", T_val, "P", P_val, "Methane"))
                return rho, cp, mu, k, h
            except Exception:
                continue
        return None

    def get_properties(self, T: float, P: float) -> FluidProperties:
        """
        Evaluate real fluid properties at temperature T (K) and pressure P (Pa).
        Uses quantized caching for fast finite-volume integration.
        """
        # Cache key rounded to 0.05 K and 100 Pa
        cache_key = (round(T, 2), round(P, -2))
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Clamp to physically valid methane range for EOS evaluation
        # Methane triple point ~90.7 K / 11.7 kPa; critical point ~190.6 K / 4.6 MPa
        T_val = max(90.7, min(T, 190.6))
        P_val = max(5000.0, P)  # above triple-point pressure; small epsilon for division safety

        backend = self._backend_string
        mm_mix = self.mixture_molar_mass_g_mol()
        try:
            rho = float(CP.PropsSI("D", "T", T_val, "P", P_val, backend))
            cp = float(CP.PropsSI("C", "T", T_val, "P", P_val, backend))
            mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, backend))
            k = float(CP.PropsSI("L", "T", T_val, "P", P_val, backend))
            h = float(CP.PropsSI("H", "T", T_val, "P", P_val, backend))
            # Validate CoolProp output is finite and physically consistent for liquid mixtures
            if not all(math.isfinite(v) for v in (rho, cp, mu, k, h)):
                raise ValueError("CoolProp returned non-finite value")
            if "HEOS::" in backend and T_val < 135.0 and P_val > 1.5e5 and rho < 380.0 and mm_mix >= 16.0:
                # CoolProp un-phased HEOS flash hit spinodal root for heavy component; refine with phased AbstractState
                raise ValueError("Un-phased mixture root below cryogenic liquid density threshold")
        except Exception:
            phased = self._evaluate_liquid_mixture_abstract_state(T_val, P_val) if "HEOS::" in backend else None
            if phased is not None:
                rho, cp, mu, k, h = phased
            else:
                # Fallback to pure methane scaled by full 28-component molar mass
                try:
                    rho = float(CP.PropsSI("D", "T", T_val, "P", P_val, "Methane"))
                    cp = float(CP.PropsSI("C", "T", T_val, "P", P_val, "Methane"))
                    mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, "Methane"))
                    k = float(CP.PropsSI("L", "T", T_val, "P", P_val, "Methane"))
                    h = float(CP.PropsSI("H", "T", T_val, "P", P_val, "Methane"))
                    if self.fluid_type != "pure_methane":
                        ratio = mm_mix / 16.043
                        rho *= (1.0 + 0.55 * (ratio - 1.0))
                        cp /= (1.0 + 0.25 * (ratio - 1.0))
                        mu *= math.sqrt(max(ratio, 0.2))
                except Exception:
                    # Liquid methane physical correlations (near 112 K)
                    ratio = mm_mix / 16.043 if self.fluid_type != "pure_methane" else 1.0
                    rho = (422.6 - 1.45 * (T_val - 111.66)) * (1.0 + 0.55 * (ratio - 1.0))
                    cp = 3480.0 / (1.0 + 0.25 * (ratio - 1.0))
                    mu = 1.15e-4 * math.sqrt(max(ratio, 0.2))
                    k = 0.185
                    h = 0.0

        p_sat = self.get_vapor_pressure(T_val)

        props = FluidProperties(
            temperature=T,
            pressure=P,
            density=max(rho, 1e-3),
            specific_heat=max(cp, 100.0),
            viscosity=max(mu, 1e-7),
            thermal_conductivity=max(k, 1e-4),
            vapor_pressure=max(p_sat, 100.0),
            enthalpy=h
        )
        self._cache[cache_key] = props
        return props

    def get_latent_heat(self, P: float) -> float:
        """Calculate latent heat of vaporization h_fg (J/kg) at saturation pressure P (Pa)."""
        P_clamped = max(50000.0, min(P, 4.2e6))
        try:
            h_liq = float(CP.PropsSI("H", "P", P_clamped, "Q", 0, self._backend_string))
            h_vap = float(CP.PropsSI("H", "P", P_clamped, "Q", 1, self._backend_string))
            diff = h_vap - h_liq
            if diff > 100000.0:
                return float(diff)
        except Exception:
            pass

        # Robust Watson correlation fallback for methane/LNG
        Tc = 190.56
        T_sat = 111.66 * ((P_clamped / 101325.0) ** 0.11)
        tau = max(1e-4, 1.0 - (T_sat / Tc))
        return float(510500.0 * ((tau / (1.0 - 111.66 / Tc)) ** 0.38))

    def get_bubble_dew_temperature(self, P: float) -> tuple[float, float]:
        """Returns (T_bubble, T_dew) in K for fluid at pressure P (Pa)."""
        P_clamped = max(50000.0, min(P, 4.2e6))
        try:
            t_bubble = float(CP.PropsSI("T", "P", P_clamped, "Q", 0, self._backend_string))
            t_dew = float(CP.PropsSI("T", "P", P_clamped, "Q", 1, self._backend_string))
            if math.isnan(t_bubble) or math.isnan(t_dew):
                raise ValueError("CoolProp returned NaN")
            return float(t_bubble), float(t_dew)
        except Exception:
            pass

        try:
            t_sat = float(CP.PropsSI("T", "P", P_clamped, "Q", 0, "Methane"))
        except Exception:
            t_sat = 111.66 * ((P_clamped / 101325.0) ** 0.11)

        glide = 1.8 if self.fluid_type != "pure_methane" else 0.0
        return float(t_sat), float(t_sat + glide)

