"""Step A: clock-aware cost + observable segments, one row per own move (3+2)."""
import sys, re, numpy as np, pandas as pd, statsmodels.api as sm, chess
sys.path.insert(0, '/home/claude/repo/chess/scripts')
from hanging import see
FEAT = '/home/claude/feat'
m = pd.read_csv(FEAT+'/moves.csv.gz', dtype={'block': str, 'gid': str}, low_memory=False)
g = pd.read_csv(FEAT+'/games.csv', dtype={'block': str, 'gid': str}).set_index('gid')
fen = pd.read_csv(FEAT+'/fens.csv.gz', dtype={'block': str, 'gid': str})
m = m.merge(fen[['gid','ply','fen']], on=['gid','ply'], how='left')
m = m[(m.tc == '180+2') & m.clk.notna() & m.opp_clk.notna() & m.spend.notna()].copy()
m = m[(m.spend >= 0) & (m.spend <= 120)]
m['score'] = m.gid.map(g.score)
m['my'] = (m.clk + m.spend - 2).clip(lower=0)    # my clock before the move
m['op'] = m.opp_clk.clip(lower=0)
lg = lambda w: np.log(np.clip(w,.02,.98)/(1-np.clip(w,.02,.98)))
def X(L, my, op):
    a = np.log(np.asarray(my,float)+5); b = np.log(np.asarray(op,float)+5); L = np.asarray(L,float)
    return sm.add_constant(pd.DataFrame({'L':L,'a':a,'b':b,'La':L*a,'Lb':L*b}), has_constant='add').values
fit_rows = m[m.fullmove >= 8]
w = 1/fit_rows.groupby('gid').gid.transform('size')
tr, te = fit_rows[fit_rows.block!='TREAT'], fit_rows[fit_rows.block=='TREAT']
wt = w[tr.index]; we = w[te.index]
f = sm.GLM(tr.score.values, X(lg(tr.wp_before),tr.my,tr.op), family=sm.families.Binomial(),
           freq_weights=(wt*tr.gid.nunique()/wt.sum()).values).fit()
p = f.predict(X(lg(te.wp_before),te.my,te.op)); print('held-out Brier (move 8+, TREAT) %.4f' % np.average((te.score-p)**2, weights=we))
f0 = sm.GLM(tr.score.values, sm.add_constant(np.asarray(lg(tr.wp_before))), family=sm.families.Binomial(),
           freq_weights=(wt*tr.gid.nunique()/wt.sum()).values).fit()
p0 = f0.predict(sm.add_constant(np.asarray(lg(te.wp_before)))); print('eval-only %.4f' % np.average((te.score-p0)**2, weights=we))
print(np.round(f.params,4))
E = lambda wp, my, op: np.asarray(f.predict(X(lg(wp), my, op)))
# board part of the move's cost, clocks held at their post-move values
m['E_before'] = E(m.wp_before, m.clk, m.op)
m['E_after']  = E(m.wp_after,  m.clk, m.op)
m['cost'] = m.E_before - m.E_after                 # + = I lost expected score on the board
m['clock_cost'] = E(m.wp_before, m.my, m.op) - m.E_before
# perceived (settled) material: add the best recapture on the square the opponent just took on
SQ = re.compile(r'([a-h][1-8])(?!.*[a-h][1-8])')
def perceived(r):
    if not isinstance(r.fen, str): return np.nan
    bal = r.mat_bal
    s = r.opp_prev_san if isinstance(r.opp_prev_san, str) else ''
    if 'x' in s:
        mm = SQ.search(s.split('=')[0])
        if mm:
            b = chess.Board(r.fen); sq = chess.parse_square(mm.group(1))
            best = 0
            for mv in b.legal_moves:
                if mv.to_square == sq and b.is_capture(mv):
                    best = max(best, see(b, mv))
            bal += round(best/100)
    return bal
m['pmat'] = [perceived(r) for r in m.itertuples()]
m.drop(columns=['fen']).to_parquet('/home/claude/vis/moves.parquet')
print(len(m), 'rows', m.gid.nunique(), 'games')
for t in (.05,.10,.15,.20):
    s = m[(m.fullmove>=6)&(m.cost>=t)]; print(f'cost>={t}: {len(s)} moves')
