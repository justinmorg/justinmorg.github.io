#!/usr/bin/env python3
"""caro/kingzone — where the damage lands after a Caro error (exploratory, 2026-11-26).

For every P1 error (win-prob drop >= 15 on one own move) in own moves 10-30 of
a Caro game, his and the thread-9 panel's (Black after 1.e4 c6), ask Stockfish
17.1 at depth 12 for White's best reply and label it 'king' if it is a check, or
lands on / captures on a square within two files and three ranks of Black's
king (the king's shelter), else 'other'. Also: score and later errors split by
whether he gave up the light-squared bishop for a knight (...Bxf3 / ...Bxe2 by
move 12). Writes caro_kingzone.json next to this file's data dir for the deck.
"""
import os, sys, json, pickle
from collections import defaultdict, Counter
import chess, chess.engine
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from hanging import winprob
from classify import caro_games
from analyze import panel_games
SF = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/sf17/stockfish/stockfish-ubuntu-x86-64-avx2")
FAMS = {"advance": "advance", "exchange": "exchange", "nf3_exch": "exchange", "classical_nf6": "classical",
        "classical_bf5": "classical", "classical_nd7": "classical", "classical_other": "classical"}


def errors(g):
    b = chess.Board(); ev = g["evals"]
    for ply, u in enumerate(g["moves"][:61]):
        m = chess.Move.from_uci(u)
        if ply % 2 == 1 and 19 <= ply and ev[ply - 1] is not None and ev[ply] is not None:
            if (1 - winprob(ev[ply - 1])) - (1 - winprob(ev[ply])) >= 0.15:
                a = b.copy(stack=False); a.push(m)
                yield ply, a
        b.push(m)


def near(ksq, sq):
    return abs(chess.square_file(ksq) - chess.square_file(sq)) <= 2 and abs(chess.square_rank(ksq) - chess.square_rank(sq)) <= 3


def label(eng, board):
    if board.is_game_over():
        return "king"
    r = eng.play(board, chess.engine.Limit(depth=12)).move
    k = board.king(chess.BLACK)
    if board.gives_check(r) or near(k, r.to_square):
        return "king"
    return "other"


def main():
    eng = chess.engine.SimpleEngine.popen_uci(SF); eng.configure({"Threads": 2, "Hash": 128})
    out = {}
    for who, gs in (("him", caro_games()), ("panel", panel_games())):
        c = defaultdict(Counter)
        for g in gs:
            f = FAMS.get(g["var"])
            if not f:
                continue
            for ply, a in errors(g):
                c[f][label(eng, a)] += 1
        out[who] = {f: dict(v) for f, v in c.items()}
        print(who, {f: "%d/%d king (%.0f%%)" % (v["king"], sum(v.values()), 100. * v["king"] / sum(v.values())) for f, v in c.items()})
    eng.quit()
    # bishop trade split, his games
    mv = pickle.load(open("/tmp/caro_moves.pkl", "rb"))
    by = defaultdict(list)
    for r in mv:
        by[r["gid"]].append(r)
    split = {}
    for g in caro_games():
        f = FAMS.get(g["var"])
        if f not in ("advance", "exchange"):
            continue
        b = chess.Board(); traded = False
        for ply, u in enumerate(g["moves"][:24]):
            m = chess.Move.from_uci(u)
            if ply % 2 == 1 and b.piece_type_at(m.from_square) == chess.BISHOP and b.is_capture(m) \
                    and b.piece_type_at(m.to_square) == chess.KNIGHT and chess.square_file(m.from_square) in (6, 7, 4, 5) \
                    and (chess.square_rank(m.to_square) <= 2):
                traded = True
            b.push(m)
        k = "%s_%s" % (f, "Bx" if traded else "kept")
        s = split.setdefault(k, [0, 0.0, 0, 0, []])
        s[0] += 1; s[1] += g["score"]
        for r in by[g["gid"]]:
            if 13 <= r["move"] <= 30:
                s[2] += 1; s[3] += r["loss"] >= 0.15
            if r["move"] == 12:
                s[4].append(r["wa"])
    for k, s in sorted(split.items()):
        print("%-16s n=%4d score %3.0f%%  wp12 %2.0f  P1/100 moves 13-30 %.1f" % (k, s[0], 100 * s[1] / s[0], 100 * sum(s[4]) / max(1, len(s[4])), 100. * s[3] / s[2]))
    out["bishop_split"] = {k: s[:4] for k, s in split.items()}
    json.dump(out, open("/tmp/caro_kingzone.json", "w"), indent=1)


if __name__ == "__main__":
    main()
