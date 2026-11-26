#!/usr/bin/env python3
"""caro/select_moments — positions for the caro_moves deck ("Good idea or mistake?").

Pool: his Caro games (caro/classify.py), own moves 8-30, Black to move, the move
he actually played is a *theme move*: a kingside pawn move (f/g/h-pawn, not a
capture) in any variety, ...d4 in the Advance, ...e5 in the Exchange. Contested
positions only (depth-12 own win chance 30-80% before the move), clock > 20s,
games not on the drill pages, one position per game.

Kinds, judged at Stockfish 17.1 depth 18 (winning chance, Lichess logistic):
  bad   played move >= 12 points (of 100) below the engine's best
  fine  played move within 3 points of best
Accepted answers: engine top-5 moves within 5 points of best (the played move
too when 'fine').

Writes chess/study/caro_moments.json (positions, engine lines, labels) so the
deck builds with no engine. Cache: chess/study/engine_cache_caro.json.
Exploratory, 2026-11-26.
"""
import os, sys, json, math, random
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import enginecheck, studylib
enginecheck.CACHE = os.path.join(HERE, "..", "..", "study", "engine_cache_caro.json")
from hanging import winprob
from classify import caro_games

DEPTH = 18
FAM = {"advance": "advance", "exchange": "exchange", "nf3_exch": "exchange", "classical_nf6": "classical"}
SIZES = {("advance", "bad"): 8, ("advance", "fine"): 6, ("exchange", "bad"): 8, ("exchange", "fine"): 6,
         ("classical", "bad"): 5, ("classical", "fine"): 3}
OUT = os.path.join(HERE, "..", "..", "study", "caro_moments.json")


def wp(cp):
    if cp >= 10000: return 1.0
    if cp <= -10000: return 0.0
    cp = max(-1000, min(1000, cp))
    return 1 / (1 + math.exp(-0.00368208 * cp))


def theme(fam, b, m):
    p = b.piece_type_at(m.from_square)
    if p == chess.PAWN and not b.is_capture(m):
        f = chess.square_file(m.from_square)
        if f >= 5:
            return "kside"
        if fam == "advance" and m.to_square == chess.D4:
            return "d4"
        if fam == "exchange" and m.to_square == chess.E5:
            return "e5"
    return None


def candidates():
    drilled = studylib.drilled_gids()
    out = []
    for g in caro_games():
        fam = FAM.get(g["var"])
        if not fam or g["gid"] in drilled:
            continue
        b = chess.Board(); ev = g["evals"]
        for ply, u in enumerate(g["moves"][:61]):
            m = chess.Move.from_uci(u)
            if ply % 2 == 1 and ply >= 15 and ev[ply - 1] is not None and ev[ply] is not None:
                t = theme(fam, b, m)
                clk = g["clocks"][ply - 1] if ply >= 1 else None
                wb = 1 - winprob(ev[ply - 1]); wa = 1 - winprob(ev[ply])
                if t and 0.30 <= wb <= 0.80 and (clk is None or clk > 20):
                    k = "bad" if wb - wa >= 0.15 else ("fine" if wb - wa <= 0.03 else None)
                    if k:
                        out.append(dict(gid=g["gid"], ply=ply, fam=fam, var=g["var"], theme=t, kind=k, fen=b.fen(),
                                        uci=u, san=b.san(m), score=g["score"], block=g["block"],
                                        moves=g["moves"][:ply]))
            b.push(m)
    return out


def main():
    eng = enginecheck.Engine(depth=DEPTH)
    pool = candidates()
    random.Random(1126).shuffle(pool)
    # prefer a balance of themes: kside first-come, but cap d4/e5 at half of 'bad'
    picked, used, count = [], set(), {k: 0 for k in SIZES}
    tcount = {}
    try:
        for c in pool:
            key = (c["fam"], c["kind"])
            if count[key] >= SIZES[key] or c["gid"] in used:
                continue
            tk = (c["fam"], c["kind"], c["theme"])
            if c["theme"] != "kside" and tcount.get(tk, 0) >= SIZES[key] // 2:
                continue
            fen = c["fen"]
            top = eng.best(fen, 5, depth=DEPTH)
            best_w = 1 - wp(top[0][1])            # Black's chance
            pcp, ppv = eng.move_eval(fen, c["uci"], depth=DEPTH)
            pw = 1 - wp(pcp)
            gap = best_w - pw
            if best_w > 0.85 or best_w < 0.25:
                continue
            if c["kind"] == "bad" and gap < 0.12:
                continue
            if c["kind"] == "fine" and gap > 0.03:
                continue
            good = [[u, round(1 - wp(cp), 3), pv] for u, cp, pv in top if best_w - (1 - wp(cp)) <= 0.05]
            if c["kind"] == "fine" and c["uci"] not in [x[0] for x in good]:
                good.append([c["uci"], round(pw, 3), [c["uci"]] + [x for x in ppv if x != c["uci"]][:7] if ppv and ppv[0] != c["uci"] else ppv])
            if c["kind"] == "bad" and c["uci"] in [x[0] for x in good]:
                continue
            c.update(best_w=round(best_w, 3), played_w=round(pw, 3), played_pv=ppv if (ppv and ppv[0] == c["uci"]) else [c["uci"]] + ppv,
                     good=good)
            picked.append(c); used.add(c["gid"]); count[key] += 1; tcount[tk] = tcount.get(tk, 0) + 1
            eng.save()
            print(key, c["theme"], c["san"], "gap %.2f" % gap, flush=True)
            if all(count[k] >= SIZES[k] for k in SIZES):
                break
    finally:
        eng.close()
    json.dump(picked, open(OUT, "w"), indent=0, sort_keys=True)
    print("picked", count)


if __name__ == "__main__":
    main()
