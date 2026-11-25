#!/usr/bin/env python3
"""Step 3: classify every floored hang hit by what was actually lost.

Inputs: hits.json (extract.py) and eng18.jsonl (engine.py). Writes a per-hit
CSV and prints the tables used in the write-up.

Material is the 1/3/3/5/9 count, from jamorgan's POV, "resolved": plus the
best SEE capture available to the side to move, so a half-finished trade
reads as finished. Mate at the end of a line counts as +-40.

  m0          perceived material before his move: raw count plus the best
              recapture on the square the opponent just captured on
  best_end    resolved material at the end of the depth-18 best line from P0
  played_end  ... at the end of the opponent's best line after the move played
  gain_best   best_end - m0        what best play would have netted him
  loss_play   m0 - played_end      what he loses by force after his move
  err18       winprob(s0) - winprob(s1), the error re-measured at depth 18
  cap_ok      s2 - s1 <= 100: the flagged capture is (within a pawn) a correct
              reply for the opponent

Classes (err18 >= 0.05 counts as a real error):
  noise       err18 < 0.05 - not an error at depth 18
  hang        loss_play >= 2 and cap_ok - the flagged capture is real
  other_loss  loss_play >= 2, flagged capture is not the right reply
  missed_win  loss_play < 2 and gain_best >= 2 - the cost is the material he
              didn't take, not material he gave
  no_mat      neither - the drop is positional / king safety / tempo
`hang` and `other_loss` also carry `also_missed_win` when gain_best >= 2.

    python3 analyze.py hits.json eng18.jsonl out.csv [depth18_verify.json]
"""
import csv, json, math, os, sys
from collections import Counter, defaultdict
import chess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from hanging import see, winprob  # noqa: E402

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
INC = {"180+2": 2, "300+0": 0}
# Plies of each engine line counted, starting with his move: 6 = his move and
# the next five (three moves each), the same "within three moves" horizon as
# the visibility study. Longer lines start crediting ordinary conversion of a
# winning position as "material won". Override with HANG_HORIZON.
HORIZON = int(os.environ.get("HANG_HORIZON", "6"))


def raw_mat(b, me):
    t = 0
    for pt, v in VAL.items():
        t += v * (len(b.pieces(pt, me)) - len(b.pieces(pt, not me)))
    return t


def resolved(b, me):
    if b.is_checkmate():
        return -40 if b.turn == me else 40
    best = 0
    for m in b.legal_moves:
        if b.is_capture(m):
            best = max(best, see(b, m))
    adj = best / 100.0
    return raw_mat(b, me) + (adj if b.turn == me else -adj)


def perceived(b, me, last_uci):
    """Material before his move as he would count it: raw count, plus the best
    recapture on the square the opponent just captured on (a half-finished
    trade reads as level). Unlike resolved(), free material elsewhere is NOT
    credited, so taking a hung piece shows up as gain_best."""
    t = raw_mat(b, me)
    if last_uci:
        sq = chess.Move.from_uci(last_uci).to_square
        best = 0
        for m in b.legal_moves:
            if m.to_square == sq and b.is_capture(m):
                best = max(best, see(b, m))
        t += best / 100.0
    return t


def end_of(fen, moves, me):
    b = chess.Board(fen)
    for u in moves:
        b.push_uci(u)
    return resolved(b, me)


def best_cap150(fen, pv):
    if not pv:
        return False
    b = chess.Board(fen)
    m = chess.Move.from_uci(pv[0])
    return b.is_capture(m) and see(b, m) >= 150


def score_for(result, side):
    if result == "1/2-1/2":
        return 0.5
    w = result == "1-0"
    return 1.0 if (w == (side == "white")) else 0.0


def classify(h, e):
    b0 = chess.Board(h["fen"])
    me = b0.turn
    m0 = perceived(b0, me, h["moves"][h["ply"] - 2] if h["ply"] >= 2 else None)
    played = b0.parse_san(h["move_played"]).uci()
    best_end = end_of(h["fen"], e["pv0"][:HORIZON], me)
    played_end = end_of(h["fen"], ([played] + e["pv1"])[:HORIZON], me)
    gain_best = best_end - m0
    loss_play = m0 - played_end
    err18 = winprob(e["s0"]) - winprob(e["s1"])
    cap_ok = (e["s2"] - e["s1"]) <= 100
    if err18 < 0.05:
        cls = "noise"
    elif loss_play >= 2:
        cls = "hang" if cap_ok else "other_loss"
    elif gain_best >= 2:
        cls = "missed_win"
    else:
        cls = "no_mat"

    # mechanical shape (only meaningful for real hangs)
    bb = chess.Board(h["fen"])
    pm = bb.parse_san(h["move_played"])
    was_cap = bb.is_capture(pm)
    shape = h["label"]
    if was_cap and chess.Move.from_uci(e["cap_uci"]).to_square == pm.to_square:
        shape = "losing trade"
    elif h["label"] == "hung it myself":
        shape = ("moved piece en prise"
                 if chess.Move.from_uci(e["cap_uci"]).to_square == pm.to_square
                 else "hung other (defender moved / line opened)")

    # what happened in the game
    moves, ply = h["moves"], h["ply"]          # ply = 1-based index of his move
    g = chess.Board()
    for u in moves[:ply - 1]:
        g.push_uci(u)
    assert g.fen() == h["fen"], (h["gid"], h["ply"])
    traj = {}
    for n in (2, 6, 12, 20):
        gb = g.copy(stack=False)
        upto = min(len(moves), ply - 1 + n)
        for u in moves[ply - 1:upto]:
            gb.push_uci(u)
        traj[n] = resolved(gb, me) - m0
        traj[f"end{n}"] = upto < ply - 1 + n
    nxt = moves[ply] if len(moves) > ply else None
    took_at_once = nxt == e["cap_uci"]
    # any opponent capture worth >= 1.5 pawns on the next ply
    took_any = False
    if nxt:
        a = g.copy(stack=False)
        a.push_uci(moves[ply - 1])
        mv = chess.Move.from_uci(nxt)
        took_any = a.is_capture(mv) and see(a, mv) >= 150
    sustained = traj[6] <= -2 and traj[20] <= -2

    # clock spend and the opponent's previous move
    clocks, inc = h["clocks"], INC.get(h["tc"], 0)
    spend = None
    if ply >= 3 and clocks[ply - 1] is not None and clocks[ply - 3] is not None:
        spend = clocks[ply - 3] - clocks[ply - 1] + inc
    ev = h["evals_w"]
    sgn = 1 if me == chess.WHITE else -1
    gift = None
    if ply >= 3:
        gift = winprob(sgn * ev[ply - 2]) - winprob(sgn * ev[ply - 3])

    return {
        "block": h["block"], "gid": h["gid"], "ply": ply, "fullmove": h["fullmove"],
        "label": h["label"], "shape": shape, "move": h["move_played"],
        "their_capture": h["their_capture"], "see_after": h["see_after"],
        "cp_before12": h["cp_before"], "cp_after12": h["cp_after"],
        "wp_error12": round(h["wp_error"], 4),
        "s0": e["s0"], "s1": e["s1"], "s2": e["s2"], "best18": e["pv0"][0] if e["pv0"] else "",
        "best_is_cap150": best_cap150(h["fen"], e["pv0"]),
        "played_is_best": bool(e["pv0"]) and e["pv0"][0] == played,
        "opp_best_is_flag": bool(e["pv1"]) and e["pv1"][0] == e["cap_uci"],
        "err18": round(err18, 4), "cap_ok": cap_ok,
        "m0": round(m0, 2), "gain_best": round(gain_best, 2), "loss_play": round(loss_play, 2),
        "cls": cls, "also_missed_win": cls in ("hang", "other_loss") and gain_best >= 2,
        "d2": round(traj[2], 2), "d6": round(traj[6], 2), "d12": round(traj[12], 2),
        "d20": round(traj[20], 2), "ended_by20": traj["end20"],
        "took_at_once": took_at_once, "took_any_next": took_any,
        "sustained": sustained, "score": score_for(h["result"], h["side"]),
        "spend": spend, "gift": None if gift is None else round(gift, 4),
        "tc": h["tc"], "fen": h["fen"], "played_uci": played,
    }


def pct(a, b):
    return f"{100*a/b:5.1f}%" if b else "   - "


def main():
    hits = {f"{h['gid']}-{h['ply']}": h for h in json.load(open(sys.argv[1]))}
    eng = {json.loads(l)["key"]: json.loads(l) for l in open(sys.argv[2])}
    rows = [classify(hits[k], eng[k]) for k in hits if k in eng]
    print(f"{len(rows)} of {len(hits)} hits have engine results\n")
    with open(sys.argv[3], "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # cross-check against the committed depth-18 cache, where keys overlap
    if len(sys.argv) > 4:
        cache = json.load(open(sys.argv[4]))["evals"]
        diffs = []
        for r in rows:
            c = cache.get(r["fen"] + "|" + r["played_uci"])
            if c:
                diffs.append((abs(c["fb"] - r["s0"]), abs(c["fa"] - r["s1"])))
        if diffs:
            import statistics as st
            print(f"cache overlap {len(diffs)}: median |dfb| {st.median(d[0] for d in diffs)}"
                  f"  median |dfa| {st.median(d[1] for d in diffs)}"
                  f"  share both within 50cp "
                  f"{pct(sum(1 for a, b in diffs if a <= 50 and b <= 50), len(diffs))}\n")

    n = len(rows)
    order = ["hang", "other_loss", "missed_win", "no_mat", "noise"]
    c = Counter(r["cls"] for r in rows)
    print("class           n   share  sustained  took-at-once  score  med-spend  after-gift")
    for k in order:
        rs = [r for r in rows if r["cls"] == k]
        if not rs:
            continue
        sp = sorted(r["spend"] for r in rs if r["spend"] is not None)
        med = sp[len(sp) // 2] if sp else None
        gifts = [r for r in rs if r["gift"] is not None]
        print(f"{k:12s} {len(rs):4d}  {pct(len(rs), n)}  "
              f"{pct(sum(r['sustained'] for r in rs), len(rs))}     "
              f"{pct(sum(r['took_at_once'] for r in rs), len(rs))}     "
              f"{sum(r['score'] for r in rs)/len(rs):.2f}   {med}s      "
              f"{pct(sum(1 for r in gifts if r['gift'] >= 0.10), len(gifts))}")
    allr = rows
    print(f"{'ALL':12s} {n:4d}          {pct(sum(r['sustained'] for r in allr), n)}     "
          f"{pct(sum(r['took_at_once'] for r in allr), n)}     "
          f"{sum(r['score'] for r in allr)/n:.2f}")

    print("\nhang + other_loss that also missed a win:",
          sum(r["also_missed_win"] for r in rows))
    print("\nreal hangs by shape:")
    hs = [r for r in rows if r["cls"] == "hang"]
    for s, k in Counter(r["shape"] for r in hs).most_common():
        print(f"  {s:42s} {k:4d}  {pct(k, len(hs))}")
    print("\nclass by original label:")
    for lab in ("missed their threat", "hung it myself"):
        rs = [r for r in rows if r["label"] == lab]
        cc = Counter(r["cls"] for r in rs)
        print(f"  {lab:20s} n={len(rs):3d}  " +
              "  ".join(f"{k} {pct(cc[k], len(rs))}" for k in order))
    print("\nclass by depth-12 severity (wp_error12):")
    for lo, hi in ((0.05, 0.10), (0.10, 0.20), (0.20, 1.01)):
        rs = [r for r in rows if lo <= r["wp_error12"] < hi]
        cc = Counter(r["cls"] for r in rs)
        print(f"  [{lo:.2f},{hi:.2f}) n={len(rs):3d}  " +
              "  ".join(f"{k} {pct(cc[k], len(rs))}" for k in order))
    print("\nclass by block:")
    for blk in ("2024H2", "Q1-2025", "Q2-2025", "Q3-2025", "Q4-2025", "2026", "TREAT"):
        rs = [r for r in rows if r["block"] == blk]
        cc = Counter(r["cls"] for r in rs)
        print(f"  {blk:8s} n={len(rs):3d}  " +
              "  ".join(f"{k} {pct(cc[k], len(rs))}" for k in order))


if __name__ == "__main__":
    main()
