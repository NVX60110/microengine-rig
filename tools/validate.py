"""Mechanism acceptance gate, test 2 of 2: shock-tube regression.

Runs any Cantera mechanism against ChemKED-format experimental ignition-delay
data and reports the bias distribution. Uses the EXPERIMENTS' OWN ignition
criterion (max dP/dt), not max dT/dt -- those are different quantities.

Data:
    git clone --depth 1 https://github.com/pr-omethe-us/ChemKED-database.git ckdb

Contains n-heptane, n-pentane, butanols, toluene, methyl esters. NO DME --
direct DME data needs ReSpecTh registration (https://respecth.elte.hu).

Reference results (FINDINGS 2.3/2.4), n-heptane, 99 pts, Ciezki 1993 +
Fieweger 1997, <=60 bar:

    Nordin 41sp : median 1.53x, 85% within 2x, 99% within 3x, low-T median 1.35
    Peters 21sp : median 2.15x,  9% within 2x, low-T median 154x, 22 non-ignitions

The Peters result is why species count alone is not an acceptance criterion.

NOTE: ChemKED 'equivalence-ratio' is a SCALAR while 'temperature', 'pressure'
and 'ignition-delay' are LISTS. Parsing it as a list throws -- and a bare
'except: continue' will silently discard the entire dataset and report a clean
zero (FINDINGS 7.5).
"""
import glob
import math
import os
import statistics as st

import cantera as ct
import yaml


def load_points(pattern, pmax_bar=60.0, quiet=False):
    pts = []
    for path in sorted(glob.glob(pattern)):
        with open(path) as fh:
            d = yaml.safe_load(fh)
        for dp in d.get("datapoints", []):
            try:
                T = float(dp["temperature"][0].split()[0])
                P = float(dp["pressure"][0].split()[0])
                ts = dp["ignition-delay"][0].split()
                tau = float(ts[0]) * (1e-6 if ts[1].startswith("us") else 1e-3)
                _phi = dp.get("equivalence-ratio", 1.0)
                phi = float(_phi[0] if isinstance(_phi, list) else _phi)
                comp = {s["species-name"]: float(s["amount"][0])
                        for s in dp["composition"]["species"]}
            except Exception as e:
                if not quiet:
                    print(f"  parse skip in {os.path.basename(path)}: "
                          f"{type(e).__name__} {str(e)[:60]}")
                continue
            if P <= pmax_bar:
                pts.append(dict(T=T, P=P, tau=tau, phi=phi, comp=comp,
                                src=os.path.basename(os.path.dirname(path))))
    return pts


def sim_tau(mech, fuel, comp, T, P_bar, tmax=0.5):
    """Constant-volume adiabatic, ignition = max dP/dt (matches the experiment)."""
    g = ct.Solution(mech)
    alias = {"nC7H16": fuel, "NC7H16": fuel, "C7H16": fuel,
             "O2": "O2" if "O2" in g.species_names else "o2",
             "N2": "N2" if "N2" in g.species_names else "n2"}
    X = {}
    for k, v in comp.items():
        kk = alias.get(k, k)
        if kk in g.species_names:
            X[kk] = v
    if fuel not in X:
        return None
    g.TPX = T, P_bar * 1e5, X
    r = ct.IdealGasReactor(g)
    net = ct.ReactorNet([r])
    net.rtol, net.atol = 1e-8, 1e-14
    t, tp = 0.0, 0.0
    Pp = P0 = r.thermo.P
    best = (0.0, None)
    while t < tmax:
        t = net.step()
        if t <= tp:
            break
        dP = (r.thermo.P - Pp) / (t - tp)
        if dP > best[0]:
            best = (dP, t)
        Pp, tp = r.thermo.P, t
        if r.thermo.P > 2.5 * P0 and best[1]:
            return best[1]
    return best[1]


def regress(mech, fuel, pts, label=""):
    ratios, per_T, fails = [], [], 0
    for p in pts:
        try:
            s = sim_tau(mech, fuel, p["comp"], p["T"], p["P"])
        except Exception:
            s = None
        if not s or s <= 0:
            fails += 1
            continue
        ratios.append(s / p["tau"])
        per_T.append((p["T"], s / p["tau"]))
    if not ratios:
        print(f"{label}: no usable results ({fails} failures)")
        return None
    lr = [math.log10(r) for r in ratios]
    out = dict(
        n=len(ratios), failed=fails,
        median=10 ** st.median(lr),
        geomean=10 ** (sum(lr) / len(lr)),
        within2=sum(1 for r in ratios if 0.5 <= r <= 2.0) / len(ratios) * 100,
        within3=sum(1 for r in ratios if 1 / 3 <= r <= 3.0) / len(ratios) * 100,
        lo=min(ratios), hi=max(ratios),
    )
    low = [r for T, r in per_T if T < 900]
    high = [r for T, r in per_T if T >= 1100]
    if low:
        out["lowT_median"] = 10 ** st.median([math.log10(r) for r in low])
        out["lowT_n"] = len(low)
    if high:
        out["highT_median"] = 10 ** st.median([math.log10(r) for r in high])
    print(f"=== {label} ===  n={out['n']}  failed={out['failed']}")
    print(f"  median sim/exp : {out['median']:.3f}")
    print(f"  within 2x / 3x : {out['within2']:.0f}% / {out['within3']:.0f}%")
    print(f"  range          : {out['lo']:.2f}x to {out['hi']:.2f}x")
    if "lowT_median" in out:
        print(f"  low-T (<900 K, the LTC region) median : "
              f"{out['lowT_median']:.3f}  n={out['lowT_n']}")
    if "highT_median" in out:
        print(f"  high-T (>=1100 K) median              : {out['highT_median']:.3f}")
    print()
    return out


if __name__ == "__main__":
    pts = load_points("ckdb/n-heptane/Ciezki 1993/*.yaml")
    pts += load_points("ckdb/n-heptane/Fieweger 1997/*.yaml")
    print(f"loaded {len(pts)} experimental points (<=60 bar)\n")
    if not pts:
        raise SystemExit("no points loaded -- check the ckdb clone path")
    regress("mechs/n-Heptane_C7H16/Peters2002/Peters30/chem_peters.yaml",
            "nc7h16", pts, "Peters 21sp (negative control)")
    regress("mechs/n-Heptane_C7H16/Nordin_42s_168r_1998/mech_41s168r.yaml",
            "C7H16", pts, "Nordin 41sp")
