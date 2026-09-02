"""Pressure-aware leakage conversions.

This module exists because of FINDINGS 3.2. The two leakage models have
DIFFERENT PRESSURE EXPONENTS:

    annulus (viscous, Poiseuille):  mdot ~ rho * dP        ~ P^2 / T
    choked orifice:                 mdot ~ A * P / sqrt(T)

so the equivalent orifice area of a given clearance scales as A_eq ~ P_up.
There is NO single CdA that represents an annulus across a pressure sweep, and
the error direction depends on which way the sweep runs -- it under-leaks at
high pressure, flattering exactly the end where conclusions get drawn.

A lookup table of clearance -> area is therefore a bug. Call the function.

Reference values (50 bar, 1100 K, 8.5 mm bore, 8 mm skirt, concentric):
    2 um -> 0.00037 mm^2
    3 um -> 0.00124 mm^2
    5 um -> 0.00572 mm^2
"""
import math

R_AIR = 287.0
GAMMA = 1.35


def annulus_mdot(D_mm, h_um, L_mm, P_up_bar, P_dn_bar=1.0,
                 T=1100.0, mu=4.0e-5, eccentricity=0.0,
                 gas_constant=R_AIR):
    """Laminar compressible flow through a thin annulus (ABC piston/liner,
    or a valve seat). Eccentricity multiplier 1 + 1.5*e^2 per Beta 2.3.

    D_mm : annulus diameter
    h_um : radial clearance
    L_mm : flow length (piston skirt length, or valve seat width)
    gas_constant : specific gas constant [J/(kg K)]; defaults to air
    """
    D, h, L = D_mm / 1e3, h_um / 1e6, L_mm / 1e3
    Pu, Pd = P_up_bar * 1e5, P_dn_bar * 1e5
    if Pu <= Pd:
        return 0.0
    if gas_constant <= 0:
        raise ValueError("gas_constant must be positive")
    base = math.pi * D * h**3 * (Pu**2 - Pd**2) / (24 * mu * L * gas_constant * T)
    return base * (1.0 + 1.5 * eccentricity**2)


def equiv_area(mdot, P_up_bar, T=1100.0, gamma=GAMMA, gas_constant=R_AIR):
    """Effective choked-orifice area (mm^2) giving the same mass flow AT THIS
    PRESSURE. Not transferable to another pressure -- recompute."""
    Pu = P_up_bar * 1e5
    if gas_constant <= 0:
        raise ValueError("gas_constant must be positive")
    k = Pu / math.sqrt(gas_constant * T) * math.sqrt(gamma) * \
        (2 / (gamma + 1)) ** ((gamma + 1) / (2 * (gamma - 1)))
    return mdot / k * 1e6


def clearance_to_area(h_um, P_up_bar, D_mm=8.5, L_mm=8.0, T=1100.0,
                      mu=4.0e-5, eccentricity=0.0, gas_constant=R_AIR):
    """Convenience: ABC radial clearance -> equivalent CdA in mm^2, at a stated
    pressure and temperature. The pressure argument is REQUIRED by design.

    ``mu`` is exposed because room-temperature leak-down comparisons and hot
    in-cylinder comparisons must not silently share the same viscosity.
    """
    return equiv_area(
        annulus_mdot(
            D_mm,
            h_um,
            L_mm,
            P_up_bar,
            T=T,
            mu=mu,
            eccentricity=eccentricity,
            gas_constant=gas_constant,
        ),
        P_up_bar,
        T,
        gas_constant=gas_constant,
    )


if __name__ == "__main__":
    print("ABC piston annulus, 8.5 mm bore, 8 mm skirt, 1100 K")
    print("equivalent CdA [mm^2] -- note the linear growth with P_up\n")
    print(f"{'P_up bar':>9s} " + "".join(f"{f'{c} um':>10s}" for c in [2, 3, 5, 8]))
    for P in [10, 20, 30, 50, 80]:
        print(f"{P:9.0f} " + "".join(
            f"{clearance_to_area(c, P):10.5f}" for c in [2, 3, 5, 8]))

    print("\nValve seat, 3.5 mm dia, 0.3 mm seat width, 2 valves, 45 bar")
    print("(FINDINGS 3.5: spec is <0.5 um. The earlier orifice-based alarm was ~100x high.)\n")
    piston3 = annulus_mdot(8.5, 3.0, 8.0, 45.0)
    print(f"{'seat gap':>9s} {'equiv mm2':>11s} {'% of 3um piston':>17s}")
    for gap in [0.1, 0.25, 0.5, 1.0, 2.0]:
        m = 2 * annulus_mdot(3.5, gap, 0.3, 45.0)
        print(f"{gap:7.2f}um {equiv_area(m, 45.0):11.5f} {100*m/piston3:16.1f}%")
