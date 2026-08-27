#!/usr/bin/env python3
"""
oppmove.py — does the opponent's previous move predict my blunder?

Usage:
    python3 oppmove.py /home/claude/features/moves.csv.gz [--seed 29] \
        [--nperm 2000] [--nboot 2000]

Reads `features.py`'s `moves.csv.gz`. No engine, no PGN walk, no new data.

The raw crosstab (README, open thread 1) says forcing moves are followed by
FEWER blunders than quiet ones — checks 7.95%, captures 8.46%, quiet 10.16%.
That is the reverse of the intuition, and all three rows turn out to be
confounded in a different way. This script reports the controlled version.

Method is the think-time treatment: direct standardization across
    move band x n_legal quartile x n_caps_avail x eval bucket x tc
then a within-stratum permutation test, plus a game-clustered bootstrap CI
because rows inside one game are not independent.

`in_check` is deliberately NOT a stratum axis here, unlike the think-time run.
It is perfectly collinear with the exposure for the check arm (see contrast B),
so including it would leave zero usable strata rather than controlling anything.

Three contrasts:

  A  capture / quiet / pawn_break, and the capture arm split on
     `opp_prev_was_recapture` — the split is the finding.
  B  check vs non-check. Reports overlap diagnostics first; the honest answer
     is that it is not identifiable under these controls.
  C  created-a-threat. The raw row is definitional (`opp_created_threat == 1`
     implies `see_standing >= 150`), so the contrast is re-posed WITHIN the
     material-hanging set: newly created vs already standing.

Scope throughout: own moves, fullmove > 12, non-mate. Blunder = drop_cp >= 200,
which sits at the +2 line and is inside the depth-12 reliable band.
"""
import argparse
import sys

import numpy as np
import pandas as pd

KEYS = ['mb', 'lq', 'caps', 'eb', 'tc']


def load(path):
    df = pd.read_csv(path, low_memory=False)
    d = df[(df.fullmove > 12) & (df.mate_flag == 0)].copy()
    d['blunder'] = (d.drop_cp >= 200).astype(int)
    d['mb'] = pd.cut(d.fullmove, [12, 18, 25, 35, 10**6],
                     labels=['13-18', '19-25', '26-35', '36+']).astype(str)
    d['eb'] = pd.cut(d.cp_before, [-10**9, -300, -100, 100, 300, 10**9],
                     labels=['e1', 'e2', 'e3', 'e4', 'e5']).astype(str)
    d['caps'] = d.n_caps_avail.clip(upper=3)
    return d


def add_legal_q(sub):
    """Quartiles are cut within the contrast set, not globally — a quartile
    boundary set on a pool the comparison never uses is not a control."""
    sub = sub.copy()
    sub['lq'] = pd.qcut(sub.n_legal, 4, labels=['q1', 'q2', 'q3', 'q4'],
                        duplicates='drop').astype(str)
    return sub


def _usable(sub, expo, groups):
    sub = sub.copy()
    sub['stratum'] = sub[KEYS].astype(str).agg('|'.join, axis=1)
    cnt = sub.groupby(['stratum', expo]).size().unstack(fill_value=0)
    ok = set(cnt.index[(cnt[list(groups)] > 0).all(axis=1)])
    u = sub[sub.stratum.isin(ok)]
    w = u.groupby('stratum').size().astype(float)
    return u, w / w.sum()


def standardize(sub, expo, groups):
    """Direct standardization to the pooled distribution of usable strata.
    A stratum counts only if every compared group appears in it."""
    u, w = _usable(sub, expo, groups)
    out = {}
    for g in groups:
        r = u[u[expo] == g].groupby('stratum').blunder.mean().reindex(w.index)
        out[g] = float((w * r).sum())
    return out, u, w


def _arrays(u, expo, g1, g2):
    sc, slev = pd.factorize(u.stratum)
    gc, glev = pd.factorize(u.gid)
    S, G = len(slev), len(glev)
    b = u.blunder.values.astype(float)
    f1 = (u[expo].values == g1).astype(float)
    f2 = (u[expo].values == g2).astype(float)
    w0 = np.bincount(sc, minlength=S).astype(float)
    w0 /= w0.sum()

    def contrast(idx, lab1=None, lab2=None):
        s = sc[idx]
        a1 = f1[idx] if lab1 is None else lab1
        a2 = f2[idx] if lab2 is None else lab2
        n1 = np.bincount(s, weights=a1, minlength=S)
        n2 = np.bincount(s, weights=a2, minlength=S)
        k1 = np.bincount(s, weights=a1 * b[idx], minlength=S)
        k2 = np.bincount(s, weights=a2 * b[idx], minlength=S)
        m = (n1 > 0) & (n2 > 0)
        if not m.any():
            return float('nan')
        w = w0[m] / w0[m].sum()
        return float((w * (k1[m] / n1[m] - k2[m] / n2[m])).sum())

    return sc, gc, S, G, f1, f2, contrast


def perm_p(u, expo, g1, g2, nperm, seed):
    """Shuffle exposure labels WITHIN stratum. Two-sided."""
    u = u[u[expo].isin([g1, g2])]
    sc, gc, S, G, f1, f2, contrast = _arrays(u, expo, g1, g2)
    idx = np.arange(len(u))
    obs = contrast(idx)
    order = np.argsort(sc, kind='stable')
    bounds = np.flatnonzero(np.diff(sc[order])) + 1
    blocks = np.split(order, bounds)
    r = np.random.default_rng(seed)
    hits = 0
    for _ in range(nperm):
        l1 = f1.copy()
        for blk in blocks:
            l1[blk] = r.permutation(f1[blk])
        if abs(contrast(idx, l1, 1.0 - l1)) >= abs(obs) - 1e-12:
            hits += 1
    return obs, hits / nperm


def boot_ci(u, expo, g1, g2, nboot, seed):
    """Resample whole GAMES, not rows. Rows inside a game share an opponent,
    a clock trajectory and a position, so a row-level CI is too tight."""
    u = u[u[expo].isin([g1, g2])]
    sc, gc, S, G, f1, f2, contrast = _arrays(u, expo, g1, g2)
    obs = contrast(np.arange(len(u)))
    order = np.argsort(gc, kind='stable')
    st = np.searchsorted(gc[order], np.arange(G))
    en = np.searchsorted(gc[order], np.arange(G), side='right')
    rows = [order[st[i]:en[i]] for i in range(G)]
    r = np.random.default_rng(seed)
    out = np.empty(nboot)
    for i in range(nboot):
        out[i] = contrast(np.concatenate([rows[g] for g in r.integers(0, G, G)]))
    lo, hi = np.nanpercentile(out, [2.5, 97.5])
    return obs, lo, hi, G


def report(sub, expo, groups, pairs, args, label):
    print(f'\n{label}')
    print('-' * len(label))
    std, u, w = standardize(sub, expo, groups)
    raw = sub.groupby(expo).blunder.agg(['mean', 'size'])
    print(f'contrast set n={len(sub)}  usable strata={len(w)}  '
          f'rows retained={len(u)} ({len(u) / len(sub) * 100:.1f}%)')
    print(f'  {"group":16s} {"n":>7s} {"raw":>8s} {"std":>8s}')
    for g in groups:
        print(f'  {str(g):16s} {int(raw.loc[g, "size"]):7d} '
              f'{raw.loc[g, "mean"] * 100:7.2f}% {std[g] * 100:7.2f}%')
    for g1, g2 in pairs:
        _, p = perm_p(u, expo, g1, g2, args.nperm, args.seed)
        o, lo, hi, G = boot_ci(u, expo, g1, g2, args.nboot, args.seed)
        print(f'  {str(g1)} - {str(g2)}: {o * 100:+.2f} pp  '
              f'[{lo * 100:+.2f}, {hi * 100:+.2f}]  p = {p:.4f}  ({G} games)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('moves', nargs='?',
                    default='/home/claude/features/moves.csv.gz')
    ap.add_argument('--seed', type=int, default=29)
    ap.add_argument('--nperm', type=int, default=2000)
    ap.add_argument('--nboot', type=int, default=2000)
    args = ap.parse_args()

    d = load(args.moves)
    print(f'scoped rows: {len(d)} (own moves, fullmove > 12, non-mate)')

    # Validation gate, same discipline as features.py: the raw crosstab must
    # reproduce the published table before any controlled figure is believed.
    print('\nraw crosstab (must match README open thread 1):')
    for k in ['check', 'capture', 'pawn_break', 'quiet']:
        s = d[d.opp_prev_kind == k]
        print(f'  {k:11s} freq {len(s) / len(d) * 100:5.1f}%  '
              f'blunder {s.blunder.mean() * 100:5.2f}%')
    for v, nm in [(1.0, 'created'), (0.0, 'did not')]:
        s = d[d.opp_created_threat == v]
        print(f'  {nm:11s} freq {len(s) / len(d) * 100:5.1f}%  '
              f'blunder {s.blunder.mean() * 100:5.2f}%')
    exp = {'check': 7.95, 'capture': 8.46, 'pawn_break': 10.44, 'quiet': 10.16}
    for k, v in exp.items():
        got = d[d.opp_prev_kind == k].blunder.mean() * 100
        if abs(got - v) > 0.05:
            sys.exit(f'FAIL: {k} reads {got:.2f}%, published {v:.2f}%. '
                     f'Fix the pipeline before reading anything below.')
    print('  OK — reproduces the published raw table')

    # ---- A. captures, and the recapture split ----
    A = add_legal_q(d[d.opp_prev_kind.isin(['capture', 'quiet', 'pawn_break'])])
    report(A, 'opp_prev_kind', ['quiet', 'capture', 'pawn_break'],
           [('quiet', 'capture'), ('pawn_break', 'quiet')], args,
           'A. capture / quiet / pawn_break')

    A2 = A.copy()
    A2['kind2'] = np.where(A2.opp_prev_kind != 'capture', A2.opp_prev_kind,
                           np.where(A2.opp_prev_was_recapture == 1,
                                    'recapture', 'capture_new'))
    A2 = add_legal_q(A2[A2.kind2 != 'pawn_break'])
    report(A2, 'kind2', ['quiet', 'capture_new', 'recapture'],
           [('quiet', 'recapture'), ('quiet', 'capture_new'),
            ('capture_new', 'recapture')], args,
           'A2. the capture arm split on recapture')

    # ---- B. checks: diagnose before comparing ----
    print('\nB. check vs non-check — overlap diagnostics')
    print('-' * 42)
    d['ischeck'] = (d.opp_prev_kind == 'check').astype(int)
    print(f'  in_check == (opp_prev_kind == "check") disagreements: '
          f'{int(((d.ischeck == 1) != (d.in_check == 1)).sum())}')
    print('  n_legal quartiles:')
    print('   ', d.groupby('ischeck').n_legal.describe()[
        ['min', '25%', '50%', '75%', 'max']].to_string().replace('\n', '\n    '))
    for t in (3, 5, 8, 10):
        print(f'    n_legal <= {t:2d}: check {int(((d.ischeck == 1) & (d.n_legal <= t)).sum()):6d}'
              f'   non-check {int(((d.ischeck == 0) & (d.n_legal <= t)).sum()):6d}')
    print('  -> in_check is collinear with the exposure and n_legal barely')
    print('     overlaps. Below is the narrowest defensible comparison, not')
    print('     an answer to the question.')
    ov = d[d.n_legal <= 8].copy()
    ov['lq'] = ov.n_legal.astype(str)          # exact match, not quartile
    report(ov, 'ischeck', [1, 0], [(1, 0)], args,
           'B. check vs non-check, n_legal <= 8, exact-matched')

    # ---- C. created threat, de-confounded ----
    print('\n  note: opp_created_threat == 1 implies see_standing >= 150 in '
          f'{int(((d.opp_created_threat == 1) & (d.see_standing < 150)).sum())} '
          'exceptions — the raw row is definitional.')
    H = add_legal_q(d[d.see_standing >= 150])
    report(H, 'opp_created_threat', [1.0, 0.0], [(1.0, 0.0)], args,
           'C. within material-hanging positions: newly created vs standing')


if __name__ == '__main__':
    main()
