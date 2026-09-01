"""
microengine_v3.py - reacting single-cylinder model with ring blowby.

Cantera chemistry + compressible-orifice ring leakage in one reactor network.
Closed cycle, -180 to +180 deg. Motored (rpm imposed).

NOTE ON LEAKAGE: leak_area_mm2 is a CALIBRATED effective area (Cd*A) valid only
at the pressure it was derived for. For an ABC annulus use
physics/annulus.py:equiv_area(), which takes P and T explicitly. See FINDINGS 3.2:
annulus mdot ~ P^2 while orifice mdot ~ P, so a fixed CdA is systematically
biased across any pressure sweep.

Mechanism paths are resolved from MECH_DIR (env var MICROENGINE_MECH_DIR,
default current directory). See mechanisms/PROVENANCE.md for regeneration.
"""
from __future__ import annotations
import math
import os
import cantera as ct

R_UNIV = 8314.462
MECH_DIR = os.environ.get("MICROENGINE_MECH_DIR", ".")


def _m(name):
    return os.path.join(MECH_DIR, name)


FUELS = {
    "methane":    dict(mech="gri30.yaml",           fuel="CH4:1",        ox="O2:1,N2:3.76"),
    "methanol":   dict(mech="gri30.yaml",           fuel="CH3OH:1",      ox="O2:1,N2:3.76"),
    "efuel_6040": dict(mech="gri30.yaml",           fuel="CH3OH:0.6,CH4:0.4", ox="O2:1,N2:3.76"),
    "h2":         dict(mech="gri30.yaml",           fuel="H2:1",         ox="O2:1,N2:3.76"),
    "ndodecane":  dict(mech="nDodecane_Reitz.yaml", fuel="c12h26:1",     ox="o2:1,n2:3.76"),
    "dme":        dict(mech=_m("dme_sk39.yaml"),      fuel="CH3OCH3:1",  ox="O2:1,N2:3.76"),
    "dme_parent": dict(mech=_m("dme_zhao_full.yaml"), fuel="CH3OCH3:1",  ox="O2:1,N2:3.76"),
}


def blend(dme_mole_frac, partner="CH4", mech=None):
    """DME/partner blend. Partner must exist in the mechanism -- the Zhao
    skeleton has CH4 and H2 but NOT CH3OH."""
    x = dme_mole_frac
    return dict(mech=mech or _m("dme_sk39.yaml"),
                fuel=f"CH3OCH3:{x:.6f},{partner}:{1-x:.6f}", ox="O2:1,N2:3.76")


class Geom:
    def __init__(self, bore_mm=8.5, stroke_mm=7.0, cr=7.0, rod_ratio=1.6):
        self.b = bore_mm / 1e3
        self.s = stroke_mm / 1e3
        self.a = self.s / 2
        self.rod = rod_ratio * self.s
        self.A = math.pi * self.b**2 / 4
        self.Vd = self.A * self.s
        self.Vc = self.Vd / (cr - 1)
        self.hc = self.Vc / self.A

    def pos(self, th):
        return self.a * (1 - math.cos(th)) + self.rod - math.sqrt(
            max(1e-30, self.rod**2 - (self.a * math.sin(th))**2))

    def dpos(self, th):
        r2 = math.sqrt(max(1e-30, self.rod**2 - (self.a * math.sin(th))**2))
        return self.a * math.sin(th) + self.a**2 * math.sin(th) * math.cos(th) / r2

    def vol(self, th):
        return self.Vc + self.A * self.pos(th)

    def surf(self, th):
        return 2 * self.A + math.pi * self.b * (self.hc + self.pos(th))


def orifice(p_up, T_up, p_dn, A_eff, gamma, R_gas):
    """Compressible orifice, one direction. A_eff already includes Cd."""
    if A_eff <= 0 or p_up <= p_dn:
        return 0.0
    r = p_dn / p_up
    crit = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    pre = A_eff * p_up / math.sqrt(R_gas * T_up)
    if r <= crit:
        return pre * math.sqrt(gamma) * (2 / (gamma + 1)) ** ((gamma + 1) / (2 * (gamma - 1)))
    fac = 2 * gamma / (gamma - 1) * (r ** (2 / gamma) - r ** ((gamma + 1) / gamma))
    return pre * math.sqrt(max(0.0, fac))


def _wall_gas(T):
    s = ct.Solution("air.yaml")
    s.TP = T, ct.one_atm
    return s


def run(fuel="methane", bore_mm=8.5, stroke_mm=7.0, cr=7.0, rpm=1200.0,
        phi=1.1, P_in_bar=1.5, T_in=500.0, T_wall=800.0, h_wall=300.0,
        leak_area_mm2=0.0141, P_crank_bar=1.0, T_crank=350.0,
        step_deg=0.25, cache_gas_props=True, verbose=False):
    """Run one closed cycle. Returns a summary dict.

    cache_gas_props: refresh gamma and R once per crank step instead of on every
    CVODE substep. ~20% faster, shifts IMEP ~1.9% (FINDINGS 7.3) -- confirm
    convergence before trusting near a branch boundary.
    """
    spec = FUELS[fuel]
    g = Geom(bore_mm, stroke_mm, cr, )
    omega = rpm * 2 * math.pi / 60
    dth = math.radians(step_deg)
    dt = dth / omega

    _raw = ct.Solution(spec["mech"])
    if _raw.thermo_model.lower().replace("-", "") != "idealgas":
        # e.g. nDodecane_Reitz is Redlich-Kwong; IdealGasReactor rejects it
        gas = ct.Solution(thermo="ideal-gas", kinetics="gas",
                          species=_raw.species(), reactions=_raw.reactions())
    else:
        gas = _raw
    gas.set_equivalence_ratio(phi, spec["fuel"], spec["ox"])
    gas.TP = T_in, P_in_bar * 1e5
    fuel_names = [s.split(":")[0] for s in spec["fuel"].split(",")]

    cyl = ct.IdealGasReactor(gas, energy="on")
    cyl.volume = g.vol(-math.pi)
    m0 = cyl.mass
    fuel0 = m0 * sum(gas[n].Y[0] for n in fuel_names)
    fuel_leaked = 0.0

    amb = ct.Reservoir(ct.Solution("air.yaml"))
    crank_gas = ct.Solution("air.yaml")
    crank_gas.TP = T_crank, P_crank_bar * 1e5
    crank = ct.Reservoir(crank_gas)

    piston = ct.Wall(cyl, amb, A=g.A, U=0.0)          # drives volume
    heatw = ct.Wall(cyl, ct.Reservoir(_wall_gas(T_wall)), A=g.surf(-math.pi),
                    U=h_wall, velocity=0.0)           # continuous h*A*(Tg-Tw)

    A_eff = leak_area_mm2 * 1e-6
    _gp = {"gam": 1.35, "R": 287.0}

    def mdot_out(t):
        if cache_gas_props:
            return orifice(cyl.phase.P, cyl.T, P_crank_bar * 1e5, A_eff,
                           _gp["gam"], _gp["R"])
        return orifice(cyl.phase.P, cyl.T, P_crank_bar * 1e5, A_eff,
                       cyl.phase.cp_mass / cyl.phase.cv_mass,
                       R_UNIV / cyl.phase.mean_molecular_weight)

    def mdot_in(t):
        return orifice(P_crank_bar * 1e5, T_crank, cyl.phase.P, A_eff, 1.4, 287.0)

    ct.MassFlowController(cyl, crank, mdot=mdot_out)
    ct.MassFlowController(crank, cyl, mdot=mdot_in)

    net = ct.ReactorNet([cyl])
    net.max_time_step = dt / 4
    net.max_err_test_fails = 20

    th, t = -math.pi, 0.0
    hist, work = [], 0.0
    Pprev, Vprev = cyl.phase.P, g.vol(th)
    Pmax, Tmax = cyl.phase.P, cyl.T
    tdc = None
    for _ in range(int(round(2 * math.pi / dth))):
        th2 = th + dth
        _gp["gam"] = cyl.phase.cp_mass / cyl.phase.cv_mass
        _gp["R"] = R_UNIV / cyl.phase.mean_molecular_weight
        piston.velocity = g.dpos(th) * omega
        heatw.area = 0.5 * (g.surf(th) + g.surf(th2))
        try:
            net.advance(t + dt)
        except Exception as e:
            return dict(fuel=fuel, status="solver_fail", error=str(e)[:160])
        t += dt
        th = th2
        P, T, m = cyl.phase.P, cyl.T, cyl.mass
        Vnow = g.vol(th)
        work += 0.5 * (P + Pprev) * (Vnow - Vprev)
        Pprev, Vprev = P, Vnow
        Yf = sum(cyl.phase[n].Y[0] for n in fuel_names)
        fuel_leaked += mdot_out(t) * Yf * dt     # leaked fuel is NOT burned fuel
        burn = max(0.0, (fuel0 - m * Yf - fuel_leaked) / fuel0)
        Pmax, Tmax = max(Pmax, P), max(Tmax, T)
        if tdc is None and th >= 0:
            tdc = dict(P=P / 1e5, T=T, m_frac=m / m0, burn=burn)
        hist.append((math.degrees(th), P / 1e5, T, m / m0, burn))

    burns = [r[4] for r in hist]
    dpmax = max((hist[i][1] - hist[i - 1][1]) / step_deg
                for i in range(1, len(hist)))
    bmax = max(burns) if burns else 0.0

    def ca_at(frac):
        if bmax <= 0:
            return None
        tgt = frac * bmax
        for d, P, T, mf, b in hist:
            if b >= tgt:
                return d
        return None

    return dict(
        fuel=fuel, status="ok", cr=cr, rpm=rpm, T_in=T_in, T_wall=T_wall,
        leak_mm2=leak_area_mm2, phi=phi, P_in_bar=P_in_bar, step_deg=step_deg,
        Vd_cc=g.Vd * 1e6, m0_mg=m0 * 1e6,
        tdc_P_bar=tdc["P"], tdc_T_K=tdc["T"], tdc_retained=tdc["m_frac"],
        Pmax_bar=Pmax / 1e5, Tmax_K=Tmax,
        burn_max=bmax, burn_end=burns[-1], ignited=bmax > 0.01,
        imep_bar=work / g.Vd / 1e5, work_mJ=work * 1000.0,
        dPdCA_max=dpmax, CA10=ca_at(0.10), CA50=ca_at(0.50), CA90=ca_at(0.90),
        hist=hist if verbose else None,
    )
