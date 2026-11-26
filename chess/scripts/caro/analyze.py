#!/usr/bin/env python3
"""caro/analyze — where each Caro variety goes wrong for Justin (exploratory, 2026-11-26).

Not pre-registered; descriptive. For each variety (caro/classify.py):
  - games, score
  - P1 error rate (win-prob drop >= 15 points on one own move; README convention)
    per 100 own moves, in own moves 4-12 (opening) and 13-30 (early middlegame),
    for him and for the thread-9 panel players' own Caro games as Black
    (same classifier, same eval depth: SF16 depth 12) as a same-rating benchmark
  - mean own-POV win chance after own moves 10 / 15 / 20 / 25
Writes /tmp/caro_errors.csv: every P1 error of his in own moves 4-30 of a Caro
game, with position features, for caro/themes.py and the deck builder.
"""
import os, sys, glob, gzip, io, math, csv, random
from collections import defaultdict
import chess, chess.pgn
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import studylib
from hanging import parse_eval, winprob
from classify import caro_games, sans, variety, struct

FAM = {"advance": "Advance", "exchange": "Exchange", "nf3_exch": "Exchange (no d4)", "panov": "Panov",
       "classical_nf6": "4.Nxe4 Nf6", "classical_bf5": "4.Nxe4 Bf5", "classical_nd7": "4.Nxe4 Nd7",
       "classical_other": "4.Nxe4 other", "bc4": "2.Bc4", "two_knights": "Two Knights", "fantasy": "Fantasy",
       "d3": "2.d3", "other": "other"}


def panel_games():
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, "..", "..", "data", "panel", "ann", "*_analyzed.pgn.gz"))):
        pid = os.path.basename(f).split("_")[0]
        txt = io.StringIO(gzip.open(f, "rt", encoding="utf-8").read())
        while True:
            game = chess.pgn.read_game(txt)
            if game is None:
                break
            h = game.headers
            if h.get("Black") != pid or h.get("TimeControl") not in ("180+2", "300+0"):
                continue
            moves, evals = [], []
            node = game
            while node.variations:
                node = node.variations[0]
                wm = node.parent.board().turn == chess.WHITE
                moves.append(node.move.uci()); evals.append(parse_eval(node.comment, wm))
            if len(moves) < 10 or moves[:2] != ["e2e4", "c7c6"]:
                continue
            sc = {"1-0": 0.0, "0-1": 1.0, "1/2-1/2": 0.5}.get(h.get("Result"))
            if sc is None:
                continue
            g = {"gid": h.get("GameId"), "me": chess.BLACK, "moves": moves, "evals": evals, "score": sc,
                 "clocks": [None] * len(moves), "player": pid}
            s = sans(g)
            out.append(dict(g, var=variety(s), struct=struct(g), sans16=s))
    return out


def own_rows(g):
    """yield (own_move_no, ply, wp_before, wp_after) for Black's moves, own POV."""
    ev = g["evals"]
    for ply in range(1, len(g["moves"]), 2):
        if ply - 1 < 0 or ev[ply - 1] is None or ev[ply] is None:
            continue
        wb = 1 - winprob(ev[ply - 1]); wa = 1 - winprob(ev[ply])
        yield (ply + 1) // 2, ply, wb, wa


def rates(gs, lo, hi):
    n = e = 0
    for g in gs:
        for mn, ply, wb, wa in own_rows(g):
            if lo <= mn <= hi:
                n += 1
                e += (wb - wa) >= 0.15
    return n, e


def boot(gs, lo, hi, B=2000, seed=7):
    rnd = random.Random(seed)
    per = [rates([g], lo, hi) for g in gs]
    vals = []
    for _ in range(B):
        s = [per[rnd.randrange(len(per))] for _ in per]
        n = sum(x[0] for x in s); e = sum(x[1] for x in s)
        vals.append(100.0 * e / n if n else 0)
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B)]


def features(g, ply):
    b = chess.Board()
    for u in g["moves"][:ply]:
        b.push(chess.Move.from_uci(u))
    m = chess.Move.from_uci(g["moves"][ply])
    pt = b.piece_type_at(m.from_square)
    f = {"san": b.san(m), "piece": chess.piece_symbol(pt).upper(), "capture": int(b.is_capture(m)),
         "check": int(b.gives_check(m)), "castled": int(not b.has_castling_rights(chess.BLACK) and
                                                        b.king(chess.BLACK) in (chess.G8, chess.C8, chess.B8, chess.H8)),
         "kingsq": chess.square_name(b.king(chess.BLACK)), "fen": b.fen()}
    return f


def main():
    mine = caro_games()
    panel = panel_games()
    print("his Caro games %d, panel Caro-as-Black games %d (players %d)" % (
        len(mine), len(panel), len(set(g["player"] for g in panel))))
    groups = ["advance", "exchange", "nf3_exch", "panov", "classical_nf6", "classical_bf5", "classical_nd7",
              "bc4", "two_knights", "fantasy", "d3", "other"]
    print("%-18s %5s %5s | %-26s | %-26s | %s" % ("variety", "n", "score", "P1/100 moves 4-12 me (pan)", "P1/100 moves 13-30 me (pan)", "wp@10/15/20/25"))
    for v in groups:
        gs = [g for g in mine if g["var"] == v]
        ps = [g for g in panel if g["var"] == v]
        if not gs and not ps:
            continue
        row = [FAM[v], len(gs), "%3.0f%%" % (100 * sum(g["score"] for g in gs) / max(1, len(gs)))]
        cells = []
        for lo, hi in ((4, 12), (13, 30)):
            n, e = rates(gs, lo, hi); pn, pe = rates(ps, lo, hi)
            ci = boot(gs, lo, hi) if len(gs) >= 30 else (float("nan"),) * 2
            cells.append("%4.1f [%4.1f,%4.1f] (%4.1f, n=%d)" % (100.0 * e / max(1, n), ci[0], ci[1], 100.0 * pe / max(1, pn), len(ps)))
        wps = []
        for k in (10, 15, 20, 25):
            xs = [wa for g in gs for mn, ply, wb, wa in own_rows(g) if mn == k]
            wps.append("%2.0f" % (100 * sum(xs) / len(xs)) if xs else " -")
        print("%-18s %5d %5s | %s | %s | %s" % (row[0], row[1], row[2], cells[0], cells[1], "/".join(wps)))

    # error rows
    rows = []
    for g in mine:
        for mn, ply, wb, wa in own_rows(g):
            if 4 <= mn <= 30 and wb - wa >= 0.15:
                f = features(g, ply)
                clk = g["clocks"][ply] if g["clocks"][ply] is not None else ""
                rows.append(dict(gid=g["gid"], var=g["var"], struct=g["struct"], move=mn, ply=ply,
                                 wb=round(wb, 3), wa=round(wa, 3), clock=clk, score=g["score"], block=g["block"], **f))
    with open("/tmp/caro_errors.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("errors written:", len(rows))


if __name__ == "__main__":
    main()
