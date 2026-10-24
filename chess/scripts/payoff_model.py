#!/usr/bin/env python3
"""payoff_model.py — where would an improver-like year pay off most?
Exploratory, not pre-specified (2026-10-24).

    python3 payoff_model.py STAKES.csv [area|pooled] [BETA]

Per area: stakes (P1 errors/game x realized cost, from payoff_stakes.py),
his standing vs same-rated peers (R = logit his P1 - logit opponents' P1,
vsopp table), panel improvability (improver-minus-control excess, log-odds,
thread 9 per-area table) plus the panel's tilt toward weak areas:

    gain_a = excess_a + BETA * R_a          (log-odds cut in P1, one year)
    points/100 games = 100 * err_pg * (1 - r'/r) * cost

Monte Carlo (20,000 draws, seed 23) over excess_a, BETA and the vsopp
difference, normal from their 95% intervals, drawn independently.
`pooled` replaces every excess_a with the gate value (+0.100 [0.052, 0.147]):
the six per-area excesses are no more spread out than their own noise
(Cochran Q = 5.9 on 5 df, p ~ 0.3), so area-specific values are not
established. BETA 0.212 is the cross-fitted panel estimate; it is attenuated
by noisy per-player profiles, so 0.45 is run as an upper sensitivity.
"""
import sys
import numpy as np
import pandas as pd
from scipy.special import expit, logit

AREAS = ["Opening", "MG level", "MG winning", "EG ahead", "EG level", "M2 mate danger"]
# vsopp (README): his P1, opponents' P1, 95% CI of the difference (pp)
VS = {"Opening": (3.85, 4.30, -0.63, -0.26), "MG winning": (11.74, 12.35, -1.55, 0.30),
      "MG level": (13.00, 12.56, -0.40, 1.31), "EG ahead": (7.34, 6.21, 0.54, 1.75),
      "EG level": (10.38, 8.74, 0.77, 2.57), "M2 mate danger": (11.67, 11.18, -0.65, 1.65)}
# thread 9 per-area excess, log-odds, 95% (result_look1_40pairs.txt)
EX = {"Opening": (0.183, 0.094, 0.271), "MG level": (0.133, 0.034, 0.229),
      "MG winning": (0.049, -0.045, 0.146), "EG ahead": (0.072, -0.006, 0.149),
      "EG level": (0.055, -0.088, 0.196), "M2 mate danger": (0.128, 0.008, 0.245)}
# panel_variation.py true SD of relative strength
SD = {"Opening": 0.31, "MG level": 0.27, "MG winning": 0.20, "EG ahead": 0.20,
      "EG level": 0.19, "M2 mate danger": 0.20}
BETA_SE = (0.422 - 0.007) / 3.92


def main():
    st = pd.read_csv(sys.argv[1]).set_index("bucket")
    mode = sys.argv[2] if len(sys.argv) > 2 else "area"
    beta = float(sys.argv[3]) if len(sys.argv) > 3 else 0.212
    ex = {a: (0.100, 0.052, 0.147) for a in EX} if mode == "pooled" else EX
    rng = np.random.default_rng(23); N = 20000
    out, draws = [], {}
    for a in AREAS:
        me, op, lo, hi = VS[a]
        R = logit(me / 100) - logit(op / 100)
        diff = (me - op) + rng.normal(0, (hi - lo) / 3.92, N)
        R_d = logit(me / 100) - logit((me - diff) / 100)
        e, elo, ehi = ex[a]
        gain = rng.normal(e, (ehi - elo) / 3.92, N) + rng.normal(beta, BETA_SE, N) * R_d
        r = st.loc[a, "P1"] / 100
        pts = 100 * st.loc[a, "err_pg"] * (1 - expit(logit(r) - gain) / r) * st.loc[a, "real_cost"]
        draws[a] = pts
        out.append(dict(area=a, stakes=st.loc[a, "pts_per100_real"], cost=st.loc[a, "real_cost"],
                        vs_peer_pp=me - op, z=R / SD[a], gain_logodds=e + beta * R,
                        pts_med=np.median(pts), p10=np.percentile(pts, 10),
                        p90=np.percentile(pts, 90)))
    t = pd.DataFrame(out).set_index("area")
    D = pd.DataFrame(draws)
    t["P_top"] = D.idxmax(axis=1).value_counts(normalize=True).reindex(t.index).fillna(0)
    t["P_top2"] = (D.rank(axis=1, ascending=False) <= 2).mean()
    pd.set_option("display.width", 200)
    print(f"mode {mode}, beta {beta}")
    print(t.sort_values("pts_med", ascending=False).round(3).to_string())
    tot = D.sum(axis=1)
    print(f"all six: {np.median(tot):.2f} pts/100 games [80%: {np.percentile(tot, 10):.2f}, "
          f"{np.percentile(tot, 90):.2f}], ~{np.median(tot) * 6.95:.0f} Elo")


if __name__ == "__main__":
    main()
