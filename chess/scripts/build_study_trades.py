#!/usr/bin/env python3
"""build_study_trades — "trade or keep?" decks for /chess-study (2026-11-25).

    python3 build_study_trades.py TRADES.csv.gz

TRADES.csv.gz is written by chess/scripts/trades/extract.py (see
notes/2026-11-25-trades-from-level.md). Decks:

  tr_lessons  lesson cards: what the trade check found.
  tr_keep     "Who's better? Trade or keep?": his own positions after move 12,
              material level, at least one even piece trade available. The card
              never says who is better (Justin, 2026-11-25: with level material,
              judging that is the skill). Step 1 asks who is better (key:
              Stockfish 17.1 depth 18 winning chance >= 62% you, 42-58% even,
              <= 38% them; positions in the gaps are skipped). Step 2 asks trade
              or keep. Step 3 asks for a good move (within 5 points of best, of
              the right kind). Four kinds:
                better_keep  (14) he traded; best is not an even trade; the best
                             trade is >= 8 points (of 100) below best.
                better_trade (8)  you better; a trade within 3 points of best,
                             best non-trade >= 8 below.
                even (8) / worse (6)  a trade within 3 points of best, best
                             non-trade >= 5 below.
              So "keep" is the answer on 14 of 36 and "you are better" on 22.

Own cache chess/study/engine_cache_trades.json; a rebuild with it present needs
no engine. Engine: STOCKFISH_PATH (enginecheck default, Stockfish 17.1).
"""
import os, sys, math, random
import pandas as pd
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "trades"))
import enginecheck
enginecheck.CACHE = os.path.join(HERE, "..", "study", "engine_cache_trades.json")
from studycards import write_deck, after, gsub, game_link, mv
from studyauthor import number_line
from extract import even_trades

SIZES = {"better_keep": 14, "better_trade": 8, "even": 8, "worse": 6}
DEPTH = 18
YEAR = {"2024h2": "2024", "2025q1": "2025", "2025q2": "2025", "2025q3": "2025", "2025q4": "2025",
        "2026": "2026", "pending": "2026", "2026_fblock": "2026"}
FAMN = {"Caro": "Caro-Kann", "London": "London", "Englund": "Englund", "Englund-as-White": "1.d4 e5", "other": ""}


def wp(cp):
    if cp >= 10000:
        return 1.0
    if cp <= -10000:
        return 0.0
    cp = max(-1000, min(1000, cp))
    return 1 / (1 + math.exp(-0.00368208 * cp))


def pvline(b, ucis, n=6):
    x, sans = b.copy(stack=False), []
    for u in ucis[:n]:
        m = chess.Move.from_uci(u)
        if m not in x.legal_moves:
            break
        sans.append(x.san(m)); x.push(m)
    return number_line(b, sans)


def ended(score):
    return {1.0: "You went on to win", 0.5: "The game was drawn", 0.0: "You went on to lose"}[score]


def judge(eng, fen):
    """-> (b, me, moves) where moves = list of (uci, mover_wp, pv, is_trade), best first,
    covering the engine's top 5 plus every even trade."""
    b = chess.Board(fen); me = b.turn
    trades = {m.uci() for m, _ in even_trades(b)}
    seen = {}
    for u, cp, pv in eng.best(fen, 5, depth=DEPTH):
        seen[u] = (wp(cp if me else -cp), pv)
    for u in trades:
        if u not in seen:
            cp, pv = eng.move_eval(fen, u, depth=DEPTH)
            seen[u] = (wp(cp if me else -cp), pv if pv and pv[0] == u else [u] + pv)
    moves = sorted(((u, w, pv, u in trades) for u, (w, pv) in seen.items()), key=lambda x: -x[1])
    return b, me, moves


WHO = ["You are", "About even", "They are"]


def who(w):
    """Engine winning chance for the mover -> index into WHO, or None in the gaps."""
    if w >= 0.62:
        return 0
    if 0.42 <= w <= 0.58:
        return 1
    if w <= 0.38:
        return 2
    return None


def keep_cards(d, eng):
    base = d[(d.mine == 1) & (d.bal == 0) & (d.phase != "opening")].sort_values(["gid", "fullmove"])
    pools = {"better_keep": base[(base.took == 1) & base.cp_before.between(120, 500)],
             "better_trade": base[base.cp_before.between(120, 500)],
             "even": base[base.cp_before.between(-40, 40)],
             "worse": base[base.cp_before.between(-500, -120)]}
    out = {k: [] for k in SIZES}
    used = set()
    for kind, seed in (("better_keep", 601), ("better_trade", 602), ("even", 604), ("worse", 605)):
        s = pools[kind]
        s = s[~s.gid.isin(used)].groupby("gid").head(1)
        rows = list(s.itertuples())
        random.Random(seed).shuffle(rows)
        rows.sort(key=lambda r: 0 if r.era == "treat" else 1)
        for r in rows:
            if len(out[kind]) >= SIZES[kind]:
                break
            if r.gid in used:
                continue
            b, me, moves = judge(eng, r.fen)
            eng.save()
            best = moves[0]
            w_idx = who(best[1])
            want = {"better_keep": 0, "better_trade": 0, "even": 1, "worse": 2}[kind]
            if w_idx != want or best[1] > 0.92 or best[1] < 0.08:
                continue
            tr = [x for x in moves if x[3]]
            nt = [x for x in moves if not x[3]]
            if not tr or not nt:
                continue
            played = next((x for x in moves if x[0] == b.parse_san(r.san).uci()), None)
            if kind == "better_keep":
                if best[3] or played is None or not played[3] or best[1] - tr[0][1] < 0.08:
                    continue
                good = [x for x in nt if best[1] - x[1] <= 0.05]
                keep = True
            else:
                gap = 0.08 if kind == "better_trade" else 0.05
                if best[1] - tr[0][1] > 0.03 or tr[0][1] - nt[0][1] < gap:
                    continue
                good = [x for x in tr if tr[0][1] - x[1] <= 0.05]
                keep = False
            trade_list = ", ".join(mv(b.san(chess.Move.from_uci(x[0]))) for x in tr)
            bsan = b.san(chess.Move.from_uci(good[0][0]))
            psan = r.san
            pct = round(100 * best[1])
            who_text = {0: "You are better", 1: "It is about even", 2: "They are better"}[want]
            explain1 = ("<b>%s.</b> The engine gives you about %d%% winning chance with best play. Material is level, so the "
                        "difference is in the position: king safety, how active the pieces are, weaknesses, space." % (who_text, pct))
            if keep:
                cost = round(100 * (best[1] - played[1]))
                explain2 = ("<b>Keep.</b> You are better, and the edge is in your pieces. %s keeps it. Trading with %s, as you did "
                            "in the game, gives up about %d points of winning chance out of 100. Likely line after %s: "
                            "<span class=\"mv\">%s</span>. %s." % (
                                mv(bsan), mv(psan), cost, mv(bsan), pvline(b, good[0][2]), ended(r.score)))
            else:
                cost = round(100 * (tr[0][1] - nt[0][1]))
                pl = ("In the game you played %s too." % mv(psan)) if (played and played[3]) else (
                    "In the game you played %s." % mv(psan))
                why = {"better_trade": "Even though you are better, this trade gets something concrete.",
                       "even": "With the game even, the trade is the safe choice.",
                       "worse": "When you are worse, trades take pressure off you."}[kind]
                explain2 = ("<b>Trade.</b> %s The engine's choice is %s. The best move that keeps pieces on, %s, costs about "
                            "%d points of winning chance out of 100. Likely line: <span class=\"mv\">%s</span>. %s" % (
                                why, mv(bsan), mv(b.san(chess.Move.from_uci(nt[0][0]))), cost, pvline(b, good[0][2]), pl))
            accept = {x[0]: {"san": b.san(chess.Move.from_uci(x[0])), "fen": after(b, chess.Move.from_uci(x[0])).fen()}
                      for x in good}
            bad = {}
            if keep:
                for x in tr:
                    bad[x[0]] = "%s trades. It costs about %d points of winning chance here." % (
                        mv(b.san(chess.Move.from_uci(x[0]))), round(100 * (best[1] - x[1])))
            side = "White" if me else "Black"
            steps = [
                {"type": "choice", "fen": r.fen,
                 "ask": "%s to move, and material is level. Before anything else: who is better here?" % side,
                 "options": WHO, "answer": want, "explain": explain1},
                {"type": "choice", "fen": r.fen,
                 "ask": "You can trade: %s. Trade, or keep the pieces on?" % trade_list,
                 "options": ["Trade", "Keep the pieces on"], "answer": 1 if keep else 0, "explain": explain2},
                {"type": "move", "fen": r.fen,
                 "ask": "Now play a good move." + (" Any move that keeps the edge without trading counts." if keep else ""),
                 "accept": accept, "main": good[0][0], "bad": bad,
                 "wrong": "Not one of the engine's good options here. Try another, or ask to be shown.",
                 "text": "<p class=\"dim\">Judged by Stockfish 17.1 at depth %d.</p>" % DEPTH},
            ]
            extra = " &middot; ".join(x for x in (FAMN.get(r.fam, ""), YEAR.get(r.block, "")) if x)
            out[kind].append({"k": "TR-%s-%d" % (r.gid, r.fullmove), "t": "Who's better? Trade or keep?",
                              "sub": gsub(None, me, b.fullmove_number, extra), "flip": not me,
                              "links": [game_link(r.gid, 2 * (r.fullmove - 1) + (0 if me else 1), me)],
                              "steps": steps})
            used.add(r.gid)
    cards = [c for k in SIZES for c in out[k]]
    random.Random(603).shuffle(cards)
    return cards, {k: len(v) for k, v in out.items()}


def P(*paras):
    return "".join("<p>%s</p>" % x for x in paras)


def lessons():
    """Figures from notes/2026-11-25-trades-from-level.md."""
    from trades_lesson_text import CARDS
    return [{"k": k, "t": t, "steps": [{"type": "show", "text": P(*paras)}]} for k, t, paras in CARDS]


def main(path):
    d = pd.read_csv(path, dtype={"gid": str})
    eng = enginecheck.Engine(depth=DEPTH)
    try:
        print("tr_lessons", write_deck({"id": "tr_lessons", "title": "When to trade", "cards": lessons()})["bytes"])
        cards, n = keep_cards(d, eng)
        print("tr_keep", n, write_deck({"id": "tr_keep", "title": "Who's better? Trade or keep?", "cards": cards})["bytes"])
    finally:
        eng.close()


if __name__ == "__main__":
    main(sys.argv[1])
