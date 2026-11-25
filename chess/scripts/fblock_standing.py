#!/usr/bin/env python3
"""Group F secondary 2: standing-threat blunder rate, treatment block vs the six
settled Lichess blocks, standardized as in oppmove.py, game-level permutation.
Reads features.py moves.csv.gz built with the seven blocks (TREAT label).
Tripwire: the six-block standing arm must read 17.74% (published)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/claude/justinmorg.github.io/chess/scripts')
from oppmove import load, add_legal_q, standardize, _arrays
d = load('/home/claude/features7/moves.csv.gz')
# raw created-vs-standing over the six baseline blocks, for reference against the published 17.74
H = add_legal_q(d[(d.see_standing >= 150)])
base = H[H.block != 'TREAT']
r, u, w = standardize(base, 'opp_created_threat', [1.0, 0.0])
print('baseline six Lichess blocks, standardized: created %.2f%%  standing %.2f%%  (n standing %d)' % (r[1.0]*100, r[0.0]*100, (base.opp_created_threat==0).sum()))
S = H[H.opp_created_threat == 0].copy()
S = add_legal_q(S)
S['arm'] = np.where(S.block == 'TREAT', 'T', 'B')
r2, u2, w2 = standardize(S, 'arm', ['T', 'B'])
print('standing arm: TREAT n=%d raw %.2f%%  | baseline n=%d raw %.2f%%' % ((S.arm=='T').sum(), S[S.arm=='T'].blunder.mean()*100, (S.arm=='B').sum(), S[S.arm=='B'].blunder.mean()*100))
print('standardized: TREAT %.2f%%  baseline %.2f%%  diff %+.2f pp  (usable strata %d)' % (r2['T']*100, r2['B']*100, (r2['T']-r2['B'])*100, len(w2)))
# game-level label permutation (block is a game attribute): shuffle arm across games
sc, gc, Sn, G, f1, f2, contrast = _arrays(u2, 'arm', 'T', 'B')
obs = contrast(np.arange(len(u2)))
game_arm = pd.Series(f1, index=gc).groupby(level=0).first().reindex(range(G)).values
rng = np.random.default_rng(23); cnt = 0; N = 5000
for _ in range(N):
    ga = rng.permutation(game_arm); a1 = ga[gc]; a2 = 1 - a1
    if contrast(np.arange(len(u2)), a1, a2) <= obs: cnt += 1
print('one-sided (TREAT lower) game-level permutation p = %.4f  (%d perms, seed 23)' % ((cnt+1)/(N+1), N))
