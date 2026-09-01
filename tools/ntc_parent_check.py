"""Mechanism acceptance gate, test 1 of 2: NTC-versus-parent.

A skeletal mechanism is only usable for this project if it retained its parent's
low-temperature chemistry. Pfahl et al. report significant NTC for stoichiometric
DME/air at 13 and 40 bar over 650-1250 K; a reduction that flattened the NTC has
thrown away the chemistry the whole engine depends on.

Reference result (FINDINGS 2.2):
    skeletal 39 : NTC ratio 1.52x over 850-1000 K
    Zhao full 55: NTC ratio 1.51x over 850-1000 K

Negative control (FINDINGS 2.4): Peters-21 n-heptane fails the equivalent test.

Usage:
    python ntc_parent_check.py                          # both DME mechanisms
    python ntc_parent_check.py <mech.yaml> <fuel-spec>  # any mechanism
"""
import cantera as ct


def tau(mech, fuel, T, P_bar, phi, tmax=2.0):
    """Constant-volume adiabatic ignition delay, max dT/dt criterion."""
    g = ct.Solution(mech)
    g.set_equivalence_ratio(phi, fuel, "O2:1,N2:3.76")
    g.TP = T, P_bar * 1e5
    r = ct.IdealGasReactor(g)
    n = ct.ReactorNet([r])
    n.rtol, n.atol = 1e-9, 1e-15
    T0 = r.T
    t = 0.0
    best = (0.0, None)
    Tp = T0
    while t < tmax:
        t = n.step()
        d = r.T - Tp
        if d > best[0]:
            best = (d, t)
        Tp = r.T
        if r.T > T0 + 400:
            return best[1]
    return None


def ntc_ratio(mech, fuel, P_bar=40.0, phi=1.0, Ts=range(650, 1101, 50)):
    """Peak/trough ratio of the ignition-delay turnover. 1.0 means no NTC."""
    Ts = list(Ts)
    taus = [tau(mech, fuel, T, P_bar, phi) for T in Ts]
    v = [(T, t) for T, t in zip(Ts, taus) if t]
    strength, loc = 1.0, None
    for i in range(1, len(v) - 1):
        if v[i][1] > v[i - 1][1]:
            j = i
            while j + 1 < len(v) and v[j + 1][1] > v[j][1]:
                j += 1
            s = v[j][1] / v[i - 1][1]
            if s > strength:
                strength, loc = s, (v[i - 1][0], v[j][0])
    return strength, loc, list(zip(Ts, taus))


if __name__ == "__main__":
    import sys
    pairs = [("skeletal 39", "dme_sk39.yaml", "CH3OCH3:1"),
             ("Zhao full 55", "dme_zhao_full.yaml", "CH3OCH3:1")]
    if len(sys.argv) > 2:
        pairs = [("cli", sys.argv[1], sys.argv[2])]
    for name, mech, fuel in pairs:
        s, loc, series = ntc_ratio(mech, fuel)
        print(f"{name:14s} NTC ratio {s:5.2f}x"
              + (f"  over {loc[0]}-{loc[1]} K" if loc else "  -- NO NTC DETECTED"))
        for T, t in series:
            print(f"    {T:5d} K  {t*1000:8.3f} ms" if t else f"    {T:5d} K  >2000 ms")
