"""Two-Phase Cryogenic Flow Hydraulics & Flashing Multipliers.

Complies with: Lockhart-Martinelli, Chisholm (1967), Rouhani-Axelsson.
"""

import math
from typing import Tuple


def calculate_two_phase_flashing(
    vapor_quality: float,
    liquid_density: float,
    vapor_density: float,
    liquid_viscosity: float,
    vapor_viscosity: float
) -> Tuple[float, float, float]:
    """Calculates void fraction alpha, two-phase multiplier phi_l_squared, and two-phase density.

    Returns:
        (void_fraction_alpha, phi_l_squared, two_phase_density)
    """
    x = max(0.0, min(1.0, vapor_quality))
    if x <= 1e-5:
        return 0.0, 1.0, liquid_density

    if x >= 0.9999:
        return 1.0, 200.0, vapor_density

    # Lockhart-Martinelli parameter X_tt (Turbulent Liquid - Turbulent Vapor)
    rho_ratio = max(vapor_density, 0.1) / max(liquid_density, 10.0)
    mu_ratio = max(liquid_viscosity, 1e-6) / max(vapor_viscosity, 1e-6)
    
    x_tt = ((1.0 - x) / x) ** 0.9 * (rho_ratio ** 0.5) * (mu_ratio ** 0.1)
    x_tt = max(x_tt, 1e-4)

    # Chisholm / Butterworth void fraction alpha
    alpha = 1.0 / (1.0 + 0.28 * (x_tt ** 0.71))
    alpha = max(0.0, min(0.999, alpha))

    # Chisholm two-phase frictional multiplier Phi_L^2 (C=20)
    phi_l_sq = 1.0 + (20.0 / x_tt) + (1.0 / (x_tt ** 2))
    phi_l_sq = max(1.0, min(phi_l_sq, 200.0))

    # Homogeneous / separated mixture density
    two_phase_rho = alpha * vapor_density + (1.0 - alpha) * liquid_density

    return round(alpha, 4), round(phi_l_sq, 3), round(two_phase_rho, 2)
