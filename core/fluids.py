"""Thermodynamic real-fluid engine for Cryogenic LNG using CoolProp Helmholtz EOS."""

from dataclasses import dataclass
from typing import Dict, Optional
import math
import threading
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
    "Nitrogen":        {"label": "Azot (N2)",                "molar_mass": 28.013,  "volatility_factor": 14.5,  "category": "İnert / Asit Gazlar"},
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
        self._h_fg_cache: Dict[float, float] = {}    # Latent heat by P
        self._h_liq_sat_cache: Dict[float, float] = {}  # Saturated liquid enthalpy by P
        self._t_bubble_dew_cache: Dict[float, tuple[float, float]] = {}  # Bubble/dew T by P
        self._lock = threading.RLock()
        self.fallback_used: bool = False
        self.eos_mode: str = "HEOS"

        # Persistent CoolProp AbstractState objects (eliminates C++ JSON/BIP re-parsing per axial cell)
        self._methane_state: Optional[CP.AbstractState] = None
        self._mix_liq_state: Optional[CP.AbstractState] = None
        self._mix_sat_state: Optional[CP.AbstractState] = None
        self._mix_eos_name: Optional[str] = None
        self._mix_has_viscosity: bool = False
        self._mix_has_conductivity: bool = False
        self._sat_flash_supported: bool = True
        self._pq_flash_supported: bool = True
        self._molar_mass_g_mol: float = 16.043
        self._init_persistent_states()

    @staticmethod
    def _bounded_set(cache: dict, key, value, max_size: int = 4096) -> None:
        """Insert into cache while keeping long-lived server memory bounded."""
        if len(cache) >= max_size:
            cache.clear()
        cache[key] = value

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

    def _init_persistent_states(self) -> None:
        """Initialize reusable CoolProp AbstractState backends once per FluidManager."""
        try:
            self._methane_state = CP.AbstractState("HEOS", "Methane")
        except Exception:
            self._methane_state = None

        # Precompute mixture molar mass once
        if self.fluid_type == "pure_methane" or not self.normalized_composition:
            self._molar_mass_g_mol = 16.043
        else:
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
            self._molar_mass_g_mol = max(mm, 2.0)

        comps = [c for c, f in self.normalized_composition.items() if f > 0.0]
        fracs = [self.normalized_composition[c] for c in comps]
        if self.fluid_type == "pure_methane" or (len(comps) == 1 and comps[0] == "Methane"):
            self.eos_mode = "HEOS (Methane)"
            return

        if len(comps) == 1:
            comp_single = comps[0]
            try:
                st = CP.AbstractState("HEOS", comp_single)
                self._mix_liq_state = st
                self._mix_eos_name = "HEOS"
                self._mix_has_viscosity = True
                self._mix_has_conductivity = True
                self._mix_sat_state = CP.AbstractState("HEOS", comp_single)
                self.eos_mode = f"HEOS ({comp_single})"
                return
            except Exception:
                self.fallback_used = True
                self.eos_mode = "Empirical Fallback (Methane-Scaled)"
                return

        fluid_join = "&".join(comps)
        # Probe HEOS -> SRK -> PR once at typical cryogenic liquid state (112 K, 5 bar)
        for eos_name in ("HEOS", "SRK", "PR"):
            try:
                st = CP.AbstractState(eos_name, fluid_join)
                st.set_mole_fractions(fracs)
                st.specify_phase(CP.iphase_liquid)
                st.update(CP.PT_INPUTS, 500000.0, 112.0)
                rho = float(st.rhomass())
                cp = float(st.cpmass())
                h = float(st.hmass())
                if math.isfinite(rho) and math.isfinite(cp) and math.isfinite(h) and rho > 350.0 and cp > 500.0:
                    self._mix_liq_state = st
                    self._mix_eos_name = eos_name
                    self.eos_mode = f"{eos_name} Mixture"
                    try:
                        mu = float(st.viscosity())
                        self._mix_has_viscosity = math.isfinite(mu) and mu > 0.0
                    except Exception:
                        self._mix_has_viscosity = False
                    try:
                        k = float(st.conductivity())
                        self._mix_has_conductivity = math.isfinite(k) and k > 0.0
                    except Exception:
                        self._mix_has_conductivity = False
                    break
            except Exception:
                continue

        if self._mix_liq_state is None:
            self.fallback_used = True
            self.eos_mode = "Empirical Fallback (Methane-Scaled)"

        # Multi-component QT/PQ saturation flashes in HEOS only converge reliably for simple <=4-comp C1-C3/N2 mixtures
        _fast_sat_comps = {"Methane", "Ethane", "Propane", "Nitrogen"}
        if self._mix_eos_name == "HEOS" and len(comps) <= 4 and all(c in _fast_sat_comps for c in comps):
            try:
                sat_st = CP.AbstractState("HEOS", fluid_join)
                sat_st.set_mole_fractions(fracs)
                self._mix_sat_state = sat_st
            except Exception:
                self._sat_flash_supported = False
                self._pq_flash_supported = False
                self.fallback_used = True
        else:
            self._sat_flash_supported = False
            self._pq_flash_supported = False
            self.fallback_used = True

    def composition_sum(self) -> float:
        """Returns the sum of composition mole fractions (should be ~100 for % inputs, ~1.0 for fractions)."""
        return sum(self.composition.values())

    def mixture_molar_mass_g_mol(self) -> float:
        """Return precomputed mixture molar mass (g/mol) from normalized mole fractions."""
        return self._molar_mass_g_mol

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
        with self._lock:
            if cache_key in self._psat_cache:
                return self._psat_cache[cache_key]
            try:
                if "HEOS::" in self._backend_string:
                    if not self._sat_flash_supported or self._mix_sat_state is None:
                        raise ValueError("Use analytical mixture bubble-point model")
                    self._mix_sat_state.update(CP.QT_INPUTS, 0.0, T_clamped)
                    p_b = float(self._mix_sat_state.p())
                    if math.isfinite(p_b) and 1000.0 < p_b < 1.5e7:
                        self._bounded_set(self._psat_cache, cache_key, p_b)
                        return p_b
                    raise ValueError("Invalid mixture Psat from CoolProp")
                else:
                    if self._methane_state is not None:
                        self._methane_state.specify_phase(CP.iphase_not_imposed)
                        self._methane_state.update(CP.QT_INPUTS, 0.0, T_clamped)
                        p_m = float(self._methane_state.p())
                    else:
                        p_m = float(CP.PropsSI("P", "T", T_clamped, "Q", 0, "Methane"))
                    if math.isfinite(p_m) and p_m > 0.0:
                        self._bounded_set(self._psat_cache, cache_key, p_m)
                        return p_m
                    raise ValueError("Invalid Methane Psat")
            except Exception:
                if "HEOS::" in self._backend_string:
                    self._sat_flash_supported = False
                    self.fallback_used = True
                # Robust Antoine / Wagner fallback for methane + Raoult/volatility mixture correction
                Tc = 190.564  # K
                Pc = 4599200.0  # Pa
                tau = 1.0 - (T_clamped / Tc)
                if tau <= 0:
                    self._bounded_set(self._psat_cache, cache_key, Pc)
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
                self._bounded_set(self._psat_cache, cache_key, p_sat)
                return p_sat

    def _evaluate_methane_transport(self, T_val: float, P_val: float) -> tuple[float, float]:
        """Fast pure-methane viscosity and thermal conductivity via persistent AbstractState."""
        if self._methane_state is not None:
            try:
                if T_val < 175.0 and P_val >= 80000.0:
                    self._methane_state.specify_phase(CP.iphase_liquid)
                else:
                    self._methane_state.specify_phase(CP.iphase_not_imposed)
                self._methane_state.update(CP.PT_INPUTS, P_val, T_val)
                return float(self._methane_state.viscosity()), float(self._methane_state.conductivity())
            except Exception:
                pass
        return 1.15e-4, 0.185

    def _evaluate_liquid_mixture_abstract_state(self, T_val: float, P_val: float) -> Optional[tuple[float, float, float, float, float]]:
        """Evaluate liquid mixture via persistent CoolProp AbstractState (1 flash instead of re-instantiating)."""
        st = self._mix_liq_state
        if st is None:
            return None
        try:
            if T_val < 175.0 and P_val >= 80000.0:
                st.specify_phase(CP.iphase_liquid)
            else:
                st.specify_phase(CP.iphase_not_imposed)
            st.update(CP.PT_INPUTS, P_val, T_val)
            rho = float(st.rhomass())
            cp = float(st.cpmass())
            h = float(st.hmass())
            if not (math.isfinite(rho) and math.isfinite(cp) and math.isfinite(h) and rho > 50.0 and cp > 500.0):
                return None
            mu_m, k_m = (0.0, 0.0)
            if not (self._mix_has_viscosity and self._mix_has_conductivity):
                mu_m, k_m = self._evaluate_methane_transport(T_val, P_val)
            if self._mix_has_viscosity:
                mu = float(st.viscosity())
            else:
                mu = mu_m * math.sqrt(self._molar_mass_g_mol / 16.043)
            if self._mix_has_conductivity:
                k = float(st.conductivity())
            else:
                k = k_m
            return rho, cp, mu, k, h
        except Exception:
            return None

    def get_properties(self, T: float, P: float) -> FluidProperties:
        """
        Evaluate real fluid properties at temperature T (K) and pressure P (Pa).
        Uses persistent AbstractState, thread-safe locking, and bounded caching.
        """
        # Cache key rounded to 0.05 K and 2,000 Pa (0.02 bar) for high hit rate without enthalpy drift.
        cache_key = (round(T * 20.0) / 20.0, round(P, -3))
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

            # Clamp to physically valid methane range for EOS evaluation
            # Methane triple point ~90.7 K / 11.7 kPa; critical point ~190.6 K / 4.6 MPa
            T_val = max(90.7, min(T, 190.6))
            P_val = max(5000.0, P)  # above triple-point pressure; small epsilon for division safety

            backend = self._backend_string
            mm_mix = self._molar_mass_g_mol
            p_sat = self.get_vapor_pressure(T_val)
            want_liquid = (T_val < 185.0) and (P_val >= p_sat * 0.995)
            try:
                if "HEOS::" in backend:
                    phased = self._evaluate_liquid_mixture_abstract_state(T_val, P_val)
                    if phased is None:
                        raise ValueError("Mixture AbstractState evaluation failed")
                    rho, cp, mu, k, h = phased
                elif self._methane_state is not None:
                    self._methane_state.specify_phase(CP.iphase_liquid if want_liquid else CP.iphase_not_imposed)
                    try:
                        self._methane_state.update(CP.PT_INPUTS, P_val, T_val)
                    except Exception:
                        self._methane_state.specify_phase(CP.iphase_not_imposed)
                        self._methane_state.update(CP.PT_INPUTS, P_val, T_val)
                    rho = float(self._methane_state.rhomass())
                    cp = float(self._methane_state.cpmass())
                    mu = float(self._methane_state.viscosity())
                    k = float(self._methane_state.conductivity())
                    h = float(self._methane_state.hmass())
                    if not all(math.isfinite(v) for v in (rho, cp, mu, k, h)):
                        raise ValueError("CoolProp returned non-finite value")
                else:
                    rho = float(CP.PropsSI("D", "T", T_val, "P", P_val, backend))
                    cp = float(CP.PropsSI("C", "T", T_val, "P", P_val, backend))
                    mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, backend))
                    k = float(CP.PropsSI("L", "T", T_val, "P", P_val, backend))
                    h = float(CP.PropsSI("H", "T", T_val, "P", P_val, backend))
                    if not all(math.isfinite(v) for v in (rho, cp, mu, k, h)):
                        raise ValueError("CoolProp returned non-finite value")
            except Exception:
                self.fallback_used = True
                # Fallback to pure methane scaled by full 28-component molar mass
                try:
                    if self._methane_state is not None:
                        if T_val < 175.0 and P_val >= 80000.0:
                            self._methane_state.specify_phase(CP.iphase_liquid)
                        else:
                            self._methane_state.specify_phase(CP.iphase_not_imposed)
                        self._methane_state.update(CP.PT_INPUTS, P_val, T_val)
                        rho = float(self._methane_state.rhomass())
                        cp = float(self._methane_state.cpmass())
                        mu = float(self._methane_state.viscosity())
                        k = float(self._methane_state.conductivity())
                        h = float(self._methane_state.hmass())
                    else:
                        rho = float(CP.PropsSI("D", "T", T_val, "P", P_val, "Methane"))
                        cp = float(CP.PropsSI("C", "T", T_val, "P", P_val, "Methane"))
                        mu = float(CP.PropsSI("V", "T", T_val, "P", P_val, "Methane"))
                        k = float(CP.PropsSI("L", "T", T_val, "P", P_val, "Methane"))
                        h = float(CP.PropsSI("H", "T", T_val, "P", P_val, "Methane"))
                    if not all(math.isfinite(v) for v in (rho, cp, mu, k, h)):
                        raise ValueError("Fallback CoolProp returned non-finite value")
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
                    h = cp * (T_val - 111.66)

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
            self._bounded_set(self._cache, cache_key, props)
            return props

    def get_saturated_liquid_enthalpy(self, P: float) -> float:
        """Return saturated liquid enthalpy h_f(P) via PQ=0 flash (never crosses onto vapor curve)."""
        P_clamped = max(12000.0, min(P, 4.2e6))
        cache_key = round(P_clamped, -1)
        with self._lock:
            if cache_key in self._h_liq_sat_cache:
                return self._h_liq_sat_cache[cache_key]
            try:
                if "HEOS::" in self._backend_string and self._pq_flash_supported and self._mix_sat_state is not None:
                    self._mix_sat_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    h_liq = float(self._mix_sat_state.hmass())
                    if math.isfinite(h_liq):
                        self._bounded_set(self._h_liq_sat_cache, cache_key, h_liq)
                        return h_liq
                elif "HEOS::" not in self._backend_string and self._methane_state is not None:
                    self._methane_state.specify_phase(CP.iphase_not_imposed)
                    self._methane_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    h_liq = float(self._methane_state.hmass())
                    if math.isfinite(h_liq):
                        self._bounded_set(self._h_liq_sat_cache, cache_key, h_liq)
                        return h_liq
            except Exception:
                pass
            t_sat, _ = self.get_bubble_dew_temperature(P_clamped)
            h_sub = self.get_properties(max(90.7, t_sat - 0.1), P_clamped).enthalpy
            self._bounded_set(self._h_liq_sat_cache, cache_key, h_sub)
            return h_sub

    def get_latent_heat(self, P: float) -> float:
        """Calculate latent heat of vaporization h_fg (J/kg) at saturation pressure P (Pa)."""
        P_clamped = max(50000.0, min(P, 4.2e6))
        cache_key = round(P_clamped, -1)
        with self._lock:
            if cache_key in self._h_fg_cache:
                return self._h_fg_cache[cache_key]
            try:
                if "HEOS::" in self._backend_string:
                    if not self._pq_flash_supported or self._mix_sat_state is None:
                        raise ValueError("Use Watson latent heat correlation")
                    self._mix_sat_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    h_liq = float(self._mix_sat_state.hmass())
                    self._mix_sat_state.update(CP.PQ_INPUTS, P_clamped, 1.0)
                    h_vap = float(self._mix_sat_state.hmass())
                elif self._methane_state is not None:
                    self._methane_state.specify_phase(CP.iphase_not_imposed)
                    self._methane_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    h_liq = float(self._methane_state.hmass())
                    self._methane_state.update(CP.PQ_INPUTS, P_clamped, 1.0)
                    h_vap = float(self._methane_state.hmass())
                else:
                    h_liq = float(CP.PropsSI("H", "P", P_clamped, "Q", 0, self._backend_string))
                    h_vap = float(CP.PropsSI("H", "P", P_clamped, "Q", 1, self._backend_string))
                diff = h_vap - h_liq
                if diff > 100000.0:
                    self._bounded_set(self._h_fg_cache, cache_key, float(diff))
                    return float(diff)
            except Exception:
                if "HEOS::" in self._backend_string:
                    self._pq_flash_supported = False
                    self.fallback_used = True

            # Robust Watson correlation fallback for methane/LNG
            Tc = 190.56
            T_sat = 111.66 * ((P_clamped / 101325.0) ** 0.11)
            tau = max(1e-4, 1.0 - (T_sat / Tc))
            result = float(510500.0 * ((tau / (1.0 - 111.66 / Tc)) ** 0.38))
            self._bounded_set(self._h_fg_cache, cache_key, result)
            return result

    def get_bubble_dew_temperature(self, P: float) -> tuple[float, float]:
        """Returns (T_bubble, T_dew) in K for pressure P (Pa)."""
        P_clamped = max(50000.0, min(P, 4.2e6))
        cache_key = round(P_clamped, -1)
        with self._lock:
            if cache_key in self._t_bubble_dew_cache:
                return self._t_bubble_dew_cache[cache_key]
            try:
                if "HEOS::" in self._backend_string:
                    if not self._pq_flash_supported or self._mix_sat_state is None:
                        raise ValueError("Use analytical saturation temperature")
                    self._mix_sat_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    t_bubble = float(self._mix_sat_state.T())
                    self._mix_sat_state.update(CP.PQ_INPUTS, P_clamped, 1.0)
                    t_dew = float(self._mix_sat_state.T())
                elif self._methane_state is not None:
                    self._methane_state.specify_phase(CP.iphase_not_imposed)
                    self._methane_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    t_bubble = float(self._methane_state.T())
                    t_dew = t_bubble
                else:
                    t_bubble = float(CP.PropsSI("T", "P", P_clamped, "Q", 0, self._backend_string))
                    t_dew = float(CP.PropsSI("T", "P", P_clamped, "Q", 1, self._backend_string))
                if math.isnan(t_bubble) or math.isnan(t_dew):
                    raise ValueError("CoolProp returned NaN")
                self._bounded_set(self._t_bubble_dew_cache, cache_key, (float(t_bubble), float(t_dew)))
                return float(t_bubble), float(t_dew)
            except Exception:
                if "HEOS::" in self._backend_string:
                    self._pq_flash_supported = False
                    self.fallback_used = True

            try:
                if self._methane_state is not None:
                    self._methane_state.specify_phase(CP.iphase_not_imposed)
                    self._methane_state.update(CP.PQ_INPUTS, P_clamped, 0.0)
                    t_sat = float(self._methane_state.T())
                else:
                    t_sat = float(CP.PropsSI("T", "P", P_clamped, "Q", 0, "Methane"))
            except Exception:
                t_sat = 111.66 * ((P_clamped / 101325.0) ** 0.11)

            glide = 1.8 if self.fluid_type != "pure_methane" else 0.0
            result = float(t_sat), float(t_sat + glide)
            self._bounded_set(self._t_bubble_dew_cache, cache_key, result)
            return result

