#!/usr/bin/env python3
"""build_study_routine — the move-routine decks for /chess-study.

Decks (specs/README.md, S-scan-ladder.md, W-walkthroughs.md):
  routine   authored lesson: the four-step routine, the two looks, what a threat is
  anatomy   A: his own hangs taken apart by cause (read-only)
  walk      W: three worked walkthroughs of the routine on stretches of his games
  s1..s6    S: the scan ladder; s5b = different-piece threats

Every key and every sentence about attacks/captures is computed by scanlib
(legal moves, attack maps, SEE). The depth-12 PGN evals are used only to
select positions (refuse hopeless ones, require that a "hang" actually cost
something). Deterministic: fixed seeds, sorted inputs; rerun is byte-identical.
"""
import os, sys, random, json
from collections import defaultdict
import chess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studylib, study_table, scanlib
from studycards import *

SIZES = {"s1": 40, "s2": 60, "s3": 60, "s4": 100, "s5": 100, "s5b": 40, "s6": 60}
BLOCK_PREF = {"pending": 0, "2023": 1, "2024rest": 1, "2024h2": 1, "2025q1": 2, "2025q2": 2,
              "2025q3": 2, "2025q4": 2, "2026": 3}
WHY_WORD = {"stale": "It was already there", "check": "A check that also hit something",
            "lands": "Lands", "exchange": "Lost exchange", "leaves": "Leaves",
            "opens": "Opens a line", "blocks": "Blocks a defender", "other": "Other"}


def U(u):
    return chess.Move.from_uci(u)


def pool(rows, drilled):
    out = []
    for r in rows:
        if r["gid"] in drilled or r["fm"] < 12 or r["fm"] > 40 or r["npm"] < 16:
            continue
        if r["ev_b"] is None or r["ev_a"] is None or not (-500 <= r["ev_b"] <= 700):
            continue
        out.append(r)
    out.sort(key=lambda r: (r["gid"], r["ply"]))
    return out


def pick(cands, n, seed, used=None, per_game=1):
    """Deterministic sample, at most `per_game` per game, older/undrilled blocks first."""
    rnd = random.Random(seed)
    cands = sorted(cands, key=lambda r: (r["gid"], r["ply"]))
    rnd.shuffle(cands)
    cands.sort(key=lambda r: BLOCK_PREF.get(r["block"], 9))
    out, cnt = [], defaultdict(int)
    for r in cands:
        if used is not None and (r["gid"], r["ply"]) in used:
            continue
        if cnt[r["gid"]] >= per_game:
            continue
        cnt[r["gid"]] += 1
        out.append(r)
        if used is not None:
            used.add((r["gid"], r["ply"]))
        if len(out) >= n:
            break
    return out


def mix(groups, seed):
    out = [r for g in groups for r in g]
    random.Random(seed).shuffle(out)
    return out


def sub(r):
    yr = (r["date"] or "")[:4]
    return gsub(r, r["me"], r["fm"], "%s &middot; %s" % (fam(r["opening"]), yr))


def sanlist(board, moves):
    return ", ".join(mv(board.san(m)) for m in moves)


def caps_sentence(board, caps, none="Nothing."):
    if not caps:
        return none
    return " ".join(cap_text(board, c).capitalize() + "." if False else cap_text(board, c) + "." for c in caps)


# ------------------------------------------------------------------ S1
def card_s1(r):
    b = chess.Board(r["fen"])
    me = r["me"]
    v = scanlib.view(b, not me)
    theirs = scanlib.checks(v)
    mine = scanlib.checks(b)
    k1 = sorted({SQ(m.from_square) for m in theirs})
    k2 = sorted({SQ(m.from_square) for m in mine})
    steps = [
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "ask": "Suppose it were their move. Tap every piece of theirs that could give check.",
         "none": "None of them can", "key": k1,
         "rarrows": [[m.uci(), "r"] for m in theirs],
         "rtext": ("Their checks: %s." % sanlist(v, theirs)) if theirs else "They have no checks."},
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "ask": "Now yours. Tap every piece of yours that can give check.",
         "none": "None of mine can", "key": k2,
         "rarrows": [[m.uci(), "g"] for m in mine],
         "rtext": ("Your checks: %s." % sanlist(b, mine)) if mine else "You have no checks."},
    ]
    return {"k": "S1-%s-%d" % (r["gid"], r["ply"]), "t": "Checks, both sides", "sub": sub(r),
            "flip": not me, "links": [game_link(r["gid"], r["ply"], me)], "steps": steps}


def deck_s1(P, used):
    c = []
    for r in P:
        if r["check"]:
            continue
        c.append(r)
    rich, rest = [], []
    for r in pick(c, 400, 11):
        b = chess.Board(r["fen"])
        n1 = len(scanlib.checks(scanlib.view(b, not r["me"])))
        n2 = len(scanlib.checks(b))
        (rich if (n1 >= 1 and n2 >= 1) else rest).append(r)
    n = SIZES["s1"]
    sel = mix([rich[: int(n * .7)], rest[: n - int(n * .7)]], 12)
    for r in sel:
        used.add((r["gid"], r["ply"]))
    return [card_s1(r) for r in sel]


# ------------------------------------------------------------------ S2
def card_s2(r):
    b = chess.Board(r["fen"])
    me = r["me"]
    v = scanlib.view(b, not me)
    theirs = scanlib.captures(v)
    best = {}
    for c in theirs:
        t = c["move"].to_square
        if t not in best or c["see"] > best[t]["see"]:
            best[t] = c
    kA = sorted(SQ(t) for t in best)
    kB = sorted(SQ(t) for t, c in best.items() if c["see"] >= 100)
    mine = scanlib.captures(b)
    bestm = {}
    for c in mine:
        t = c["move"].to_square
        if t not in bestm or c["see"] > bestm[t]["see"]:
            bestm[t] = c
    kC = sorted(SQ(t) for t, c in bestm.items() if c["see"] >= 100)
    lines = [cap_text(v, best[t]) + "." for t in sorted(best, key=lambda t: -best[t]["see"])]
    order = sorted(bestm, key=lambda t: -bestm[t]["see"])
    linesm = [cap_text(b, bestm[t]) + "." for t in order if bestm[t]["see"] >= 100]
    rest = [t for t in order if bestm[t]["see"] < 100]
    if rest:
        linesm.append("Your other captures (%s) do not win anything." % ", ".join(mv(b.san(bestm[t]["move"])) for t in rest[:4]))
    steps = [
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "ask": "Suppose it were their move. Tap every piece or pawn of yours they could legally capture, good capture or bad.",
         "none": "They can capture nothing", "key": kA,
         "rarrows": [[best[t]["move"].uci(), "r"] for t in best],
         "rtext": "The red arrows are their captures."},
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "arrows": [[best[t]["move"].uci(), "r"] for t in best],
         "ask": "Of those, tap the ones where the capture wins them material (a pawn or more after the recaptures).",
         "none": "None of them wins anything", "key": kB,
         "rtext": " ".join(lines) if lines else "They had no captures at all."},
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "ask": "Your side. Tap every piece or pawn of theirs you could capture and come out ahead (a pawn or more).",
         "none": "Nothing wins material", "key": kC,
         "rarrows": [[bestm[t]["move"].uci(), "g"] for t in bestm if bestm[t]["see"] >= 100],
         "rtext": " ".join(linesm) if linesm else "You have no captures at all."},
    ]
    return {"k": "S2-%s-%d" % (r["gid"], r["ply"]), "t": "Takes: what can be captured", "sub": sub(r),
            "flip": not me, "links": [game_link(r["gid"], r["ply"], me)], "steps": steps}


def deck_s2(P, used):
    hot, mid = [], []
    for r in pick([r for r in P if not r["check"]], 500, 21, used=None):
        b = chess.Board(r["fen"])
        v = scanlib.view(b, not r["me"])
        caps = scanlib.captures(v)
        if len({c["move"].to_square for c in caps}) < 2:
            continue
        (hot if any(c["see"] >= 100 for c in caps) else mid).append(r)
    n = SIZES["s2"]
    sel = mix([hot[: n // 2], mid[: n - n // 2]], 22)
    for r in sel:
        used.add((r["gid"], r["ply"]))
    return [card_s2(r) for r in sel]


# ------------------------------------------------------------------ S3
def loose_text(b, color, L):
    if not L:
        return "None."
    out = []
    for x in L:
        why = {"undefended": "nothing defends it", "cheaper": "something cheaper attacks it",
               "both": "undefended and attacked"}[x["why"]]
        out.append("%s: %s" % (pname(b, x["sq"], the=False).capitalize(), why))
    pins = []
    for sq in chess.scan_forward(b.occupied_co[color]):
        if b.piece_type_at(sq) in (chess.PAWN, chess.KING):
            continue
        if sq in [x["sq"] for x in L]:
            continue
        pd = scanlib.pinned_defenders(b, color, sq)
        if pd and len(pd) == len(b.attackers(color, sq)):
            pins.append("%s is defended only by a pinned piece, so treat it as loose too (the key does not count it)" % pname(b, sq).capitalize())
    return "; ".join(out) + "." + (" " + ". ".join(pins) + "." if pins else "")


def card_s3(r):
    b = chess.Board(r["fen"])
    me = r["me"]
    Lm = scanlib.loose(b, me)
    Lt = scanlib.loose(b, not me)
    steps = [
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "ask": "Tap every loose piece of yours: a knight, bishop, rook or queen that nothing defends, or that something cheaper attacks.",
         "none": "None of mine are loose", "key": sorted(SQ(x["sq"]) for x in Lm),
         "rtext": loose_text(b, me, Lm)},
        {"type": "tap", "fen": b.fen(), "last": r["last"],
         "ask": "Now theirs. Tap every loose piece of theirs.",
         "none": "None of theirs are loose", "key": sorted(SQ(x["sq"]) for x in Lt),
         "rtext": loose_text(b, not me, Lt)},
    ]
    return {"k": "S3-%s-%d" % (r["gid"], r["ply"]), "t": "Loose pieces", "sub": sub(r),
            "flip": not me, "links": [game_link(r["gid"], r["ply"], me)], "steps": steps}


def deck_s3(P, used):
    sel = pick([r for r in P if not r["check"]], SIZES["s3"], 31, used=used)
    return [card_s3(r) for r in sel]


# ------------------------------------------------------------------ S4
def delta_sentences(b, m, d):
    """Plain sentences for lands / leaves / opens / blocks, from scanlib.delta."""
    a = d["after"]
    out = []
    landed = pname(a, m.to_square)
    if d["lands"]:
        bestc = max(d["lands"], key=lambda c: c["see"])
        if b.is_capture(m):
            if d["exchange"]:
                out.append("<b>Lands:</b> you captured, and the whole exchange on %s costs you material: %s." % (SQ(m.to_square), cap_text(a, bestc)))
            else:
                out.append("<b>Lands:</b> they can recapture on %s with %s, and the trade is fair or better for you." % (SQ(m.to_square), mv(a.san(bestc["move"]))))
        elif bestc["see"] >= scanlib.WIN:
            out.append("<b>Lands:</b> %s can be taken where it stands: %s." % (landed, cap_text(a, bestc)))
        elif bestc["see"] >= 100:
            out.append("<b>Lands:</b> %s can be taken (%s), which costs you a pawn." % (landed, mv(a.san(bestc["move"]))))
        else:
            out.append("<b>Lands:</b> %s can be taken (%s), but it is defended or it is a fair trade." % (landed, mv(a.san(bestc["move"]))))
    else:
        out.append("<b>Lands:</b> nothing can capture on %s." % SQ(m.to_square))
    bits = []
    for x in d["leaves"]:
        c = x["cap"]
        if c is not None and c["see"] >= 100:
            bits.append("it was guarding %s, and now %s" % (pname(a, x["sq"]), cap_text(a, c)))
    for x in d["opens"]:
        c = x["cap"]
        if c is not None and c["see"] >= 100:
            bits.append("it opened the line from %s to %s, and now %s" % (pname(a, x["slider"]), pname(a, x["target"]), cap_text(a, c)))
    for x in d["blocks"]:
        c = x["cap"]
        if c is not None and c["see"] >= 100:
            bits.append("it now stands between %s and %s, which that piece was defending, and %s" % (pname(a, x["slider"]), pname(a, x["target"]), cap_text(a, c)))
    seen = {x["sq"] for x in d["leaves"]} | {x["target"] for x in d["opens"]} | {x["target"] for x in d["blocks"]}
    for h in d["hangs"]:
        if h["why"] == "other" and h["move"].to_square not in seen:
            bits.append("the count on %s changed, and now %s" % (SQ(h["move"].to_square), cap_text(a, h)))
    if bits:
        out.append("<b>Leaves:</b> " + "; ".join(bits) + ".")
    else:
        out.append("<b>Leaves:</b> nothing it was guarding or blocking is now short.")
    return out


def card_s4(r):
    b = chess.Board(r["fen"])
    me = r["me"]
    m = U(r["move"])
    d = scanlib.delta(b, m)
    a = d["after"]
    san = r["san"]
    land_hang = any(h["why"] in ("lands", "exchange") for h in d["hangs"])
    ans = 2 if land_hang else (1 if d["lands"] else 0)
    else_sq = sorted({SQ(h["move"].to_square) for h in d["hangs"] if h["why"] not in ("lands", "exchange", "stale", "check")})
    sents = delta_sentences(b, m, d)
    hang_arrows = [[h["move"].uci(), "r"] for h in d["hangs"]]
    steps = [
        {"type": "choice", "fen": b.fen(), "last": r["last"],
         "text": "<p>You are about to play %s. The board still shows the position before it.</p>" % mv(san),
         "ask": "Lands: once it is played, can %s be captured on %s?" % ("the piece" if b.piece_type_at(m.from_square) != chess.PAWN else "the pawn", SQ(m.to_square)),
         "options": ["No", "Yes, but fair or defended", "Yes, and it loses material"], "answer": ans,
         "explain": sents[0], "rarrows": [[m.uci(), "b"]]},
        {"type": "tap", "fen": b.fen(), "last": r["last"], "arrows": [[m.uci(), "b"]],
         "text": "<p>Still before %s.</p>" % mv(san),
         "ask": "Leaves: tap anything else of yours they could win once it is played, because the move stopped guarding it, opened a line to it, or cut off its defender.",
         "none": "Nothing else", "key": else_sq, "rfen": a.fen(), "rlast": m.uci(), "rarrows": hang_arrows,
         "rtext": sents[1] + " The board now shows the position after the move."},
    ]
    return {"k": "S4-%s-%d" % (r["gid"], r["ply"]), "t": "Lands, leaves", "sub": sub(r),
            "flip": not me, "links": [game_link(r["gid"], r["ply"], me)], "steps": steps}


def deck_s4(P, used):
    base = [r for r in P if not r["check"] and not r["stale"]]
    clean = [r for r in base if not r["hangs"] and not r["lands"]]
    fair = [r for r in base if not r["hangs"] and r["lands"]]
    land = [r for r in base if r["hangs"] and r["hangs"][0][3] in ("lands", "exchange") and r["took"] and r["ev_b"] - r["ev_a"] >= 150]
    leave = [r for r in base if r["hangs"] and r["hangs"][0][3] in ("leaves", "opens", "blocks") and r["took"] and r["ev_b"] - r["ev_a"] >= 150]
    n = SIZES["s4"]
    sel = mix([pick(clean, int(n * .3), 41, used), pick(fair, int(n * .2), 42, used),
               pick(land, int(n * .25), 43, used), pick(leave, n - int(n * .3) - int(n * .2) - int(n * .25), 44, used)], 45)
    return [card_s4(r) for r in sel]


# ------------------------------------------------------------------ S5
def threat_note(v, t, top_gain, top_san):
    b1 = after(v, t["first"])
    b2 = after(b1, chess.Move.null())
    s2 = b2.san(t["second"])
    if t["mate"]:
        what = "Then %s is mate." % mv(s2)
    else:
        what = "Then %s wins %s." % (mv(s2), gain_text(b2, t["second"], t["gain"]))
    kind = "" if t["same_piece"] else " A different piece does the capturing: the first move only cleared the way or removed a guard."
    rank = " That is the biggest one." if t["gain"] >= top_gain else " It works, but the biggest was %s." % top_san
    return what + kind + rank


def card_s5(r, key, hint=None):
    b = chess.Board(r["fen"])
    me = r["me"]
    v = scanlib.view(b, not me)
    T = scanlib.threats(b, not me)
    steps_text = "<p>They get two moves in a row. Checks and captures on the first move do not count here; this is about quiet first moves.</p>"
    st = {"type": "move", "fen": v.fen(), "last": r["last"], "text": steps_text,
          "ask": "Find the pair that wins the most. Tap the piece of theirs that moves first, then the square it goes to.",
          "none": "Nothing wins a piece", "accept": {}, "wrong": "That first move does not set up a win of a piece or a mate. Try again, or ask to be shown."}
    if hint:
        st["hint"] = hint
    if not T:
        st["noneOk"] = True
        st["noneText"] = "No quiet move of theirs sets up the win of a piece or a mate next move. Most positions are like this."
    else:
        top = T[0]
        top_san = mv(v.san(top["first"]))
        for t in T:
            b1 = after(v, t["first"])
            st["accept"][t["first"].uci()] = {"san": v.san(t["first"]), "fen": b1.fen(),
                                             "arrows": [[t["second"].uci(), "r"]],
                                             "note": threat_note(v, t, top["gain"], top_san)}
        st["main"] = top["first"].uci()
    return {"k": "%s-%s-%d" % (key, r["gid"], r["ply"]), "t": "Two moves in a row" + (": a different piece" if key == "S5b" else ""),
            "sub": sub(r), "flip": not me, "links": [game_link(r["gid"], r["ply"], me)], "steps": [st]}


def deck_s5(P, used):
    base = pick([r for r in P if not r["check"] and not r["stale"]], 900, 51)
    yes, no, diff = [], [], []
    for r in base:
        T = scanlib.threats(chess.Board(r["fen"]), not r["me"])
        if not T:
            no.append(r)
            continue
        top = T[0]["gain"]
        tops = [t for t in T if t["gain"] >= top]
        if all(not t["same_piece"] for t in tops):
            diff.append(r)
        else:
            yes.append(r)
    n = SIZES["s5"]
    sel = mix([yes[: int(n * .5)], diff[: int(n * .08)], no[: n - int(n * .5) - int(n * .08)]], 52)
    for r in sel:
        used.add((r["gid"], r["ply"]))
    d2 = [r for r in diff if (r["gid"], r["ply"]) not in used][: SIZES["s5b"]]
    for r in d2:
        used.add((r["gid"], r["ply"]))
    hint = "the piece that captures is not the piece that moves first."
    return [card_s5(r, "S5") for r in sel], [card_s5(r, "S5b", hint) for r in d2]


# ------------------------------------------------------------------ S6 / shared move screens
def look1_step(r, first):
    b = chess.Board(r["fen"])
    me = r["me"]
    v = scanlib.view(b, not me, force=True)
    stale = scanlib.winning_captures(v)
    key = sorted({SQ(c["move"].to_square) for c in stale})
    if first:
        lead = "<p>Move %d. %s</p>" % (r["fm"], "They just played %s." % mv(prev_san(r)) if r["last"] else "")
    else:
        lead = "<p>They played %s.%s</p>" % (mv(prev_san(r)), " You are in check." if r["check"] else "")
    best = {}
    for c in stale:
        t = c["move"].to_square
        if t not in best or c["see"] > best[t]["see"]:
            best[t] = c
    rt = " ".join(cap_text(v, c).replace("takes", "would take") + "." for c in best.values()) if best else "Nothing of yours can be won right now."
    return {"type": "tap", "fen": b.fen(), "last": r["last"], "text": lead,
            "ask": "Look 1. Tap anything of yours they can win right now (a piece or more).",
            "none": "Nothing", "key": key, "rarrows": [[c["move"].uci(), "r"] for c in best.values()], "rtext": rt}


def prev_san(r):
    """SAN of the opponent's move that led to row r's position."""
    return r.get("prev_san") or "their move"


def look2_step(r):
    b = chess.Board(r["fen"])
    m = U(r["move"])
    d = scanlib.delta(b, m)
    a = d["after"]
    key = sorted({SQ(h["move"].to_square) for h in d["hangs"]})
    best = {}
    for h in d["hangs"]:
        t = h["move"].to_square
        if t not in best or h["see"] > best[t]["see"]:
            best[t] = h
    if best:
        parts = []
        for h in best.values():
            parts.append("%s. <span class=\"dim\">%s.</span>" % (cap_text(a, h).capitalize() if False else cap_text(a, h), WHY_WORD[h["why"]]))
        rt = " ".join(parts)
    else:
        rt = "Nothing to take after %s." % mv(r["san"])
    return {"type": "tap", "fen": b.fen(), "last": r["last"],
            "text": "<p>You played %s. The board still shows the position before it.</p>" % mv(r["san"]),
            "ask": "Look 2: lands, leaves. Tap anything they can win once it is played. If it is the moved piece itself, tap the square it lands on.",
            "none": "Nothing", "key": key, "rfen": a.fen(), "rlast": m.uci(),
            "rarrows": [[h["move"].uci(), "r"] for h in best.values()], "rtext": rt}


def add_prev_san(rows_by_game, games):
    for g in games:
        rs = rows_by_game.get(g["gid"])
        if not rs:
            continue
        b = chess.Board()
        sans = []
        for u in g["moves"]:
            m = U(u)
            sans.append(b.san(m))
            b.push(m)
        for r in rs:
            r["prev_san"] = sans[r["ply"] - 1] if r["ply"] > 0 else None
            r["next_san"] = sans[r["ply"] + 1] if r["ply"] + 1 < len(sans) else None


def windows(by_game, drilled, seed, n_hang, n_decoy):
    rnd = random.Random(seed)
    hang_w, decoy_w = [], []
    for gid in sorted(by_game):
        if gid in drilled:
            continue
        rs = by_game[gid]                       # consecutive own moves from own move 10
        idx = {r["ply"]: i for i, r in enumerate(rs)}
        g_rnd = random.Random(gid + str(seed))
        # first real hang in the game
        first = None
        for i, r in enumerate(rs):
            if r["hangs"]:
                if r["took"] and r["ev_b"] is not None and r["ev_a"] is not None and r["ev_b"] - r["ev_a"] >= 150 \
                        and r["ev_b"] >= -150 and r["fm"] >= 14 and r["npm"] >= 14:
                    first = i
                break
        if first is not None and first >= 3:
            pre = g_rnd.randint(3, min(5, first))
            post = g_rnd.randint(0, 1)
            w = rs[first - pre: first + 1 + post]
            if all(not x["hangs"] for x in w[:pre]) and all(x["ev_b"] is not None for x in w):
                hang_w.append((BLOCK_PREF.get(rs[0]["block"], 9), gid, w))
        # decoy: a clean stretch
        clean = [i for i in range(len(rs) - 5) if 12 <= rs[i]["fm"] <= 26
                 and all(not rs[j]["hangs"] and not rs[j]["stale"] for j in range(i, i + 6))
                 and rs[i]["ev_b"] is not None and -300 <= rs[i]["ev_b"] <= 600 and rs[i + 5]["npm"] >= 14]
        if clean:
            i = clean[g_rnd.randrange(len(clean))]
            ln = g_rnd.randint(4, 6)
            decoy_w.append((BLOCK_PREF.get(rs[0]["block"], 9), gid, rs[i: i + ln]))
    rnd.shuffle(hang_w)
    hang_w.sort(key=lambda x: x[0])
    rnd.shuffle(decoy_w)
    decoy_w.sort(key=lambda x: x[0])
    hg = hang_w[:n_hang]
    used = {x[1] for x in hg}
    dc = [x for x in decoy_w if x[1] not in used][:n_decoy]
    return hg, dc


def card_s6(w):
    r0 = w[0]
    steps = []
    for i, r in enumerate(w):
        steps.append(look1_step(r, i == 0))
        steps.append(look2_step(r))
    return {"k": "S6-%s-%d" % (r0["gid"], r0["ply"]), "t": "The two looks, %d moves running" % len(w), "sub": sub(r0),
            "flip": not r0["me"], "links": [game_link(r0["gid"], r0["ply"], r0["me"])], "steps": steps}


def deck_s6(by_game, drilled):
    n = SIZES["s6"]
    hg, dc = windows(by_game, drilled, 61, int(n * .72), n - int(n * .72))
    allw = [x[2] for x in hg] + [x[2] for x in dc]
    random.Random(62).shuffle(allw)
    return [card_s6(w) for w in allw], {x[1] for x in hg} | {x[1] for x in dc}


# ------------------------------------------------------------------ A: anatomy of a hang
LOOK = {"stale": "Look 1 catches this: the piece could be taken before you chose a move.",
        "check": "This one starts with their check. When a check arrives, ask what else the checking piece attacks before you answer it.",
        "lands": "Look 2 catches this: where does the piece land, and what can take it there?",
        "exchange": "Look 2 catches this: you captured on a square where they have more takers than you, or cheaper ones.",
        "leaves": "Look 2 catches this: what was the piece guarding before it moved?",
        "opens": "Look 2 catches this: what line did the piece open when it left its square?",
        "blocks": "Look 2 catches this: the piece landed between a defender and the thing it defended."}


def card_anatomy(r):
    b = chess.Board(r["fen"])
    me = r["me"]
    m = U(r["move"])
    d = scanlib.delta(b, m)
    a = d["after"]
    cap = U(r["nxt"])
    h = [x for x in d["hangs"] if x["move"].to_square == cap.to_square][0]
    hc = [c for c in scanlib.captures(a) if c["move"] == cap]
    hcap = hc[0] if hc else h
    why = h["why"]
    v = scanlib.view(b, not me, force=True)
    stale = scanlib.winning_captures(v)
    best = {}
    for c in stale:
        t = c["move"].to_square
        if t not in best or c["see"] > best[t]["see"]:
            best[t] = c
    if best:
        t1 = "Before you choose a move, Look 1: what can they take right now? " + " ".join(cap_text(v, c).replace("takes", "would take") + "." for c in best.values())
    else:
        t1 = "Before you choose a move, Look 1: what can they take right now? Nothing that wins material."
    if r["check"]:
        t1 = "It is check. " + t1.replace("Before you choose a move, Look 1: what can they take right now?", "Before answering it, Look 1: what else can they take right now?")
    sents = delta_sentences(b, m, d)
    a2 = after(a, cap)
    steps = [
        {"type": "show", "fen": b.fen(), "last": r["last"],
         "text": "<p>They have just played %s.</p><p>%s</p>" % (mv(r["prev_san"]), t1),
         "arrows": [[c["move"].uci(), "r"] for c in best.values()]},
        {"type": "show", "fen": b.fen(), "last": r["last"], "arrows": [[m.uci(), "b"]],
         "text": "<p>You played %s (black arrow).</p><p>%s</p><p>%s</p>" % (mv(r["san"]), sents[0], sents[1])},
        {"type": "show", "fen": a2.fen(), "last": cap.uci(),
         "text": "<p>They replied %s: it %s.</p><p><b>Cause: %s.</b> %s</p>" % (
             mv(a.san(cap)), cap_text(a, hcap).split("</span> ", 1)[1], WHY_WORD[why].lower(), LOOK[why])},
    ]
    return {"k": "A-%s-%d" % (r["gid"], r["ply"]), "t": WHY_WORD[why], "sub": sub(r), "flip": not me, "_san": r["san"],
            "links": [game_link(r["gid"], r["ply"], me)], "steps": steps}


def deck_anatomy(by_game, drilled, skip_games):
    firsts = []
    for gid in sorted(by_game):
        if gid in drilled or gid in skip_games:
            continue
        for r in by_game[gid]:
            if r["hangs"]:
                if r["took"] and r["ev_b"] is not None and r["ev_a"] is not None and r["ev_b"] >= -100 \
                        and r["ev_b"] - r["ev_a"] >= 200 and 12 <= r["fm"] <= 34 and r["npm"] >= 14:
                    firsts.append(r)
                break
    want = [("stale", 8), ("lands", 6), ("exchange", 5), ("leaves", 6), ("opens", 4), ("check", 4), ("blocks", 2)]
    out = []
    for why, n in want:
        c = [r for r in firsts if r["took_why"] == why]
        out += pick(c, n, 70 + len(out))
    return [card_anatomy(r) for r in out]


# ------------------------------------------------------------------ W: walkthroughs
def walk_screens(r, last_in_walk=False):
    b = chess.Board(r["fen"])
    me = r["me"]
    opp = not me
    m = U(r["move"])
    v = scanlib.view(b, opp, force=True)
    out = []
    # 1. their move
    stale_all = scanlib.winning_captures(v)
    bysq = {}
    for c in stale_all:
        sq = c["move"].to_square
        if sq not in bysq or c["see"] > bysq[sq]["see"]:
            bysq[sq] = c
    stale = list(bysq.values())
    pawn_caps = [c for c in scanlib.captures(v) if 100 <= c["see"] < scanlib.WIN]
    T = [] if (b.is_check() or stale) else scanlib.threats(b, opp)
    t = "<p><b>Step 1, their move.</b> They played %s.%s</p>" % (mv(r["prev_san"]), " It is check." if r["check"] else "")
    arrows = []
    if stale:
        t += "<p>What can they take now? " + " ".join(cap_text(v, c).replace("takes", "would take") + "." for c in stale[:3]) + " That has to be dealt with on this move.</p>"
        arrows = [[c["move"].uci(), "r"] for c in stale[:3]]
    else:
        t += "<p>What can they take now? Nothing that wins a piece.%s</p>" % (
            " (A pawn is loose: %s.)" % mv(v.san(pawn_caps[0]["move"])) if pawn_caps else "")
        if not b.is_check():
            if T:
                top = T[0]
                b1 = after(v, top["first"])
                b2 = after(b1, chess.Move.null())
                t += "<p>If they moved again: %s, and then %s. %d such idea%s in all; the routine only needs the biggest.</p>" % (
                    mv(v.san(top["first"])),
                    ("%s is mate" % mv(b2.san(top["second"]))) if top["mate"] else
                    ("%s wins %s" % (mv(b2.san(top["second"])), gain_text(b2, top["second"], top["gain"]))),
                    len(T), "" if len(T) == 1 else "s")
                arrows = [[top["first"].uci(), "y"], [top["second"].uci(), "r"]]
            else:
                t += "<p>If they moved again: nothing that wins a piece. This is the usual answer.</p>"
    out.append({"type": "show", "fen": b.fen(), "last": r["last"], "text": t, "arrows": arrows})
    # 2. inventory
    Lm, Lt = scanlib.loose(b, me), scanlib.loose(b, opp)
    t = "<p><b>Step 2, inventory.</b> Your loose pieces (red squares): %s</p><p>Theirs (blue squares): %s</p>" % (
        loose_text(b, me, Lm), loose_text(b, opp, Lt))
    out.append({"type": "show", "fen": b.fen(), "last": r["last"], "text": t,
                "marks": [[SQ(x["sq"]), "r"] for x in Lm] + [[SQ(x["sq"]), "g"] for x in Lt]})
    # 3. candidates + the move + lands/leaves on the pre-move board
    chk = scanlib.checks(b)
    wins = scanlib.winning_captures(b)
    d = scanlib.delta(b, m)
    a = d["after"]
    t = "<p><b>Step 3, candidates.</b> Your checks: %s. Your captures that win material: %s.</p>" % (
        sanlist(b, chk) if chk else "none", sanlist(b, [c["move"] for c in wins]) if wins else "none")
    t += "<p>You played %s (black arrow).</p>" % mv(r["san"])
    sents = delta_sentences(b, m, d)
    t += "<p><b>Step 4, safety check, before letting go of the piece.</b> %s %s</p>" % (sents[0], sents[1])
    arr = [[m.uci(), "b"]] + [[c["move"].uci(), "r"] for c in d["lands"][:2]]
    out.append({"type": "show", "fen": b.fen(), "last": r["last"], "text": t, "arrows": arr})
    # 4. after
    oc = scanlib.checks(a)
    hang = {}
    for h in d["hangs"]:
        sq = h["move"].to_square
        if sq not in hang or h["see"] > hang[sq]["see"]:
            hang[sq] = h
    t = "<p>The position after %s. Their checks: %s.</p>" % (mv(r["san"]), sanlist(a, oc) if oc else "none")
    if hang:
        t += "<p><b>Verdict: this leaves something.</b> " + " ".join(cap_text(a, h) + " (%s)." % WHY_WORD[h["why"]].lower() for h in hang.values()) + "</p>"
    else:
        before_pawn = {c["move"].to_square for c in scanlib.captures(v) if c["see"] >= 100}
        newp = [c for c in scanlib.captures(a) if 100 <= c["see"] < scanlib.WIN and c["move"].to_square not in before_pawn]
        if newp:
            t += "<p><b>Verdict: no piece to take, but a pawn goes:</b> %s.</p>" % mv(a.san(newp[0]["move"]))
        else:
            t += "<p><b>Verdict: nothing to take.</b></p>"
    l1 = "something to deal with" if stale else "nothing"
    l2 = "nothing"
    if hang:
        l2 = "a problem" if any(h["why"] not in ("stale", "check") for h in hang.values()) else "nothing new (the Look 1 item is still there)"
    t += "<p class=\"dim\">Blitz version of this move. Look 1 (what can they take): %s. Look 2 (lands, leaves): %s.</p>" % (l1, l2)
    out.append({"type": "show", "fen": a.fen(), "last": m.uci(), "text": t,
                "arrows": [[h["move"].uci(), "r"] for h in hang.values()]})
    return out


def find_walks(by_game, drilled, skip):
    """Candidate stretches for W1 (clean, threats met), W2 (lands/leaves hang), W3 (stale)."""
    w1, w2, w3 = [], [], []
    for gid in sorted(by_game):
        if gid in drilled or gid in skip:
            continue
        rs = by_game[gid]
        if rs[0]["block"] not in ("2023", "2024rest", "2024h2", "2025q1", "2025q2"):
            continue
        op = rs[0]["opening"]
        for i in range(len(rs) - 6):
            w = rs[i: i + 6]
            if not (13 <= w[0]["fm"] <= 18) or w[-1]["npm"] < 16:
                continue
            if any(x["ev_b"] is None or x["ev_a"] is None for x in w):
                continue
            # no unrelated large drop that the commentary would have to ignore
            drops = [x["ev_b"] - x["ev_a"] for x in w]
            n_stale = sum(1 for x in w if x["stale"] and not x["check"])
            n_hang = sum(1 for x in w if x["hangs"])
            if rs[0]["me"] and "London" in op and n_hang == 0 and n_stale >= 2 and max(drops) < 120 \
                    and all(-150 <= x["ev_b"] <= 500 for x in w) and sum(1 for x in w if x["check"]) <= 1:
                w1.append(w)
            hi = [j for j, x in enumerate(w) if x["hangs"]]
            if (not rs[0]["me"]) and "Caro" in op and hi == [4] and w[4]["took"] and w[4]["took_why"] in ("lands", "leaves") \
                    and w[4]["ev_b"] >= -100 and w[4]["ev_b"] - w[4]["ev_a"] >= 200 and max(drops[:4]) < 120 \
                    and not any(x["stale"] for x in w[:5]):
                w2.append(w)
            # stale: capturable at own move j (not hanging before), left alone, taken after j+1 or j+2
            for j in (2, 3):
                x, y = w[j], w[j + 1]
                if x["stale"] and not x["check"] and not w[j - 1]["hangs"] and not w[j - 1]["stale"] \
                        and x["hangs"] and x["hangs"][0][3] == "stale" and not x["took"] \
                        and y["stale"] and y["hangs"] and y["hangs"][0][3] == "stale" and y["took"] \
                        and x["stale"][0][0][2:4] == y["nxt"][2:4] and x["ev_b"] >= -100 and max(drops[:j]) < 120 \
                        and "x" not in x["san"] and "x" not in y["san"] and x["ev_b"] - y["ev_a"] >= 250 \
                        and len(x["stale"]) == 1:
                    w3.append(w[: j + 3] if j + 3 <= 6 else w)
    return w1, w2, w3


def card_walk(w, key, title, intro, closing):
    r0 = w[0]
    steps = [{"type": "show", "fen": r0["fen"], "last": r0["last"], "text": intro}]
    for r in w:
        steps += walk_screens(r)
    last = w[-1]
    steps.append({"type": "show", "fen": steps[-1]["fen"], "last": steps[-1].get("last"), "text": closing})
    return {"k": key, "t": title, "sub": sub(r0), "flip": not r0["me"],
            "links": [game_link(r0["gid"], r0["ply"], r0["me"])], "steps": steps}


def walk_summary(w):
    """Computed closing line: which moves had something for the routine to find."""
    bits = []
    for r in w:
        if r["stale"] and not r["hangs"]:
            bits.append("Move %d: Look 1 found something to deal with, and %s dealt with it." % (r["fm"], mv(r["san"])))
        elif r["hangs"]:
            why = r["hangs"][0][3]
            if why in ("stale", "check"):
                bits.append("Move %d: Look 1 had the answer and %s did not deal with it." % (r["fm"], mv(r["san"])))
            else:
                bits.append("Move %d: %s was the move Look 2 would have stopped (%s)." % (r["fm"], mv(r["san"]), WHY_WORD[why].lower()))
    quiet = len(w) - len(bits)
    return "<ul class=\"tight\">" + "".join("<li>%s</li>" % x for x in bits) + "</ul><p>On the other %d move%s both looks said nothing. That is normal, and it is the point: the routine is usually a few seconds of nothing, and it only pays on the move where it is not.</p>" % (quiet, "" if quiet == 1 else "s")


def deck_walk(by_game, drilled, skip):
    w1, w2, w3 = find_walks(by_game, drilled, skip)
    rnd = random.Random(81)
    cards = []
    spec = [
        (w1, "W1", "Walkthrough 1: nothing goes wrong",
         "<p>Six of your moves in a row from a London game, with the full routine run on each one. Nothing gets lost in this stretch. Twice or more the opponent attacks something and you deal with it.</p><p>Read it like a worked example in a textbook. There is nothing to answer.</p>"),
        (w2, "W2", "Walkthrough 2: the move creates the problem",
         "<p>Six of your moves from a Caro-Kann game. Five are fine. One puts a piece where it can be taken, or stops guarding something. Watch which step of the routine is the one that would have caught it.</p>"),
        (w3, "W3", "Walkthrough 3: the stale one",
         "<p>A stretch where one of your pieces becomes capturable, stays capturable while you play something else, and is then taken. Step 1 repeats the same unanswered item on consecutive screens. That repetition is what going stale looks like.</p>"),
    ]
    info = {}
    for cands, key, title, intro in spec:
        info[key] = len(cands)
        if not cands:
            continue
        cands = sorted(cands, key=lambda w: (w[0]["gid"], w[0]["ply"]))
        # prefer the stretch with the most to say
        def richness(w):
            return (sum(1 for x in w if x["stale"]) + sum(1 for x in w if x["lands"]), w[0]["gid"])
        if key == "W1":
            cands.sort(key=richness, reverse=True)
        w = cands[0]
        closing = "<p><b>What this stretch shows.</b></p>" + walk_summary(w)
        cards.append(card_walk(w, "%s-%s-%d" % (key, w[0]["gid"], w[0]["ply"]), title, intro, closing))
    return cards, info


# ------------------------------------------------------------------ authored lesson: the routine
def deck_routine(anat_cards, s5_cards, s5b_cards):
    def first(cards, title):
        return [c for c in cards if c["t"] == title][0]
    stale = first(anat_cards, WHY_WORD["stale"])
    lands = first(anat_cards, WHY_WORD["lands"])
    leaves = first(anat_cards, WHY_WORD["leaves"])
    same = [c for c in s5_cards if not c["steps"][0].get("noneOk")
            and "different piece" not in c["steps"][0]["accept"][c["steps"][0]["main"]]["note"]][0]
    diff = s5b_cards[0]

    def board(c, i, text):
        st = dict(c["steps"][i])
        st["text"] = text
        st["flip"] = c["flip"]
        return st

    def threat_screen(c, lead):
        st = c["steps"][0]
        acc = st["accept"][st["main"]]
        return {"type": "show", "fen": st["fen"], "flip": c["flip"],
                "arrows": [[st["main"], "y"]] + acc["arrows"],
                "text": lead + "<p>Gold arrow: the quiet first move, %s. Red arrow: what it sets up. %s</p>" % (
                    mv(acc["san"]), acc["note"].replace(" That is the biggest one.", ""))}

    steps = [
        {"type": "show", "text":
            "<p><b>Why a routine at all.</b> Your games say your tactical eye is fine: when the best move is a capture or a check, you find it about 87% of the time. What goes missing is the moment of looking. Pieces get left where they can be taken, and you spend more time on those moves than on ordinary ones, not less.</p>"
            "<p>So the fix is not more calculation. It is two short looks that happen on every move, whether or not anything is there.</p>"},
        {"type": "show", "text":
            "<p><b>The blitz version: two looks.</b></p>"
            "<ul class=\"tight\"><li><b>Look 1, when they move:</b> what of mine can they take right now? If their move was a check, what else does the checking piece attack?</li>"
            "<li><b>Look 2, move chosen, hand not yet moved:</b> lands, leaves. Where does my piece land and what can take it there? What was it guarding or blocking?</li></ul>"
            "<p>That is all that fits in 3+2. Count attackers and defenders only when a piece is attacked and both looks otherwise come up clean.</p>"},
        board(stale, 0, "<p><b>Look 1, in one of your games.</b></p>" + stale["steps"][0]["text"]),
        board(stale, 2, "<p>You played %s instead, and they took it. About four in ten of the pieces you lose this way are like this one. Nothing needed picturing: the capture was on the board as it stood.</p>" % mv(stale["_san"])),
        board(lands, 1, "<p><b>Look 2, lands.</b></p>" + lands["steps"][1]["text"]),
        board(leaves, 1, "<p><b>Look 2, leaves.</b></p>" + leaves["steps"][1]["text"]),
        {"type": "show", "text":
            "<p><b>The slow version: four steps.</b> For correspondence games, cards, and any game with real time.</p>"
            "<ol class=\"tight\"><li><b>Their move.</b> What does it attack now? What did it stop guarding, or unblock? Then: if they moved again right now, what would they do?</li>"
            "<li><b>Inventory.</b> Which of my pieces are loose (undefended, or attacked by something cheaper)? Which of theirs?</li>"
            "<li><b>Candidates.</b> My checks, captures and threats first, then quiet moves. No idea at all: improve the worst-placed piece. Ahead in material: trade pieces, not pawns.</li>"
            "<li><b>Safety check</b> on the move chosen, before playing it: lands, leaves, then their checks and captures in the new position. If something fails, back to step 3.</li></ol>"
            "<p>The two looks are steps 1 and 4 with everything else squeezed out.</p>"},
        {"type": "show", "text":
            "<p><b>What a threat is.</b> A threat is a quiet move (no capture, no check) that sets up a capture or a mate on the move after. The practical question is the one in step 1: <i>if they moved twice in a row, what would they do?</i></p>"
            "<p>A typical middlegame position of yours has about three such ideas for the opponent, and one in ten has eight or more. So do not try to list them. Find the biggest one.</p>"},
        threat_screen(same, "<p><b>The common kind: the same piece moves twice.</b> In about 86% of two-move ideas the piece that moves first is also the piece that captures. You already picture these.</p>"),
        threat_screen(diff, "<p><b>The kind you said you cannot picture: a different piece captures.</b> One piece steps aside, or drives a guard away, and another piece takes. It is about one idea in seven.</p>"),
        {"type": "show", "text":
            "<p><b>How the decks fit together.</b></p>"
            "<ul class=\"tight\"><li><b>Anatomy of a hang:</b> your own lost pieces taken apart by cause. Read these first.</li>"
            "<li><b>Walkthroughs:</b> the whole routine run move after move on three stretches of your games.</li>"
            "<li><b>S1 to S3:</b> warm-ups. Checks, captures, loose pieces, on the board as it stands.</li>"
            "<li><b>S4:</b> lands and leaves, with the move named but not shown.</li>"
            "<li><b>S5:</b> two moves in a row, biggest threat only. S5b is the different-piece kind.</li>"
            "<li><b>S6:</b> the two looks on four to six consecutive moves of a real game. This is the one that replaces the old play-forward cards.</li></ul>"
            "<p>Every answer key in these decks is worked out from the rules alone: legal moves, what attacks what, and who comes out ahead if everything trades on a square. No engine. The cost: a capture the key calls winning is occasionally a bad idea for a reason the count cannot see (a pin, a counter-threat). Each answer has an <i>I think the key is wrong</i> button for that.</p>"},
    ]
    return [{"k": "R-routine", "t": "The two looks and the four steps", "sub": "read once, about five minutes",
             "flip": False, "steps": steps}]


def main():
    games = studylib.load()
    rows = study_table.load()
    drilled = studylib.drilled_gids()
    by_game = defaultdict(list)
    for r in rows:
        by_game[r["gid"]].append(r)
    for g in by_game.values():
        g.sort(key=lambda r: r["ply"])
    add_prev_san(by_game, games)
    P = pool(rows, drilled)
    used = set()
    decks = {}
    s6, s6_games = deck_s6(by_game, drilled)
    decks["s6"] = s6
    walk, winfo = deck_walk(by_game, drilled, s6_games)
    walk_games = {c["k"].split("-")[1] for c in walk}
    decks["walk"] = walk
    decks["anatomy"] = deck_anatomy(by_game, drilled, s6_games | walk_games)
    skip = s6_games | walk_games | {c["k"].split("-")[1] for c in decks["anatomy"]}
    P = [r for r in P if r["gid"] not in skip]
    decks["s1"] = deck_s1(P, used)
    decks["s2"] = deck_s2(P, used)
    decks["s3"] = deck_s3(P, used)
    decks["s4"] = deck_s4(P, used)
    decks["s5"], decks["s5b"] = deck_s5(P, used)
    decks["routine"] = deck_routine(decks["anatomy"], decks["s5"], decks["s5b"])
    out = {}
    TITLES = {"routine": "The routine", "anatomy": "Anatomy of a hang", "walk": "Worked walkthroughs", "s1": "S1 Checks",
              "s2": "S2 Takes", "s3": "S3 Loose pieces", "s4": "S4 Lands, leaves",
              "s5": "S5 Two moves in a row", "s5b": "S5b A different piece", "s6": "S6 The two looks"}
    for k, cards in decks.items():
        out[k] = write_deck({"id": k, "title": TITLES[k], "cards": cards})
    for k in out:
        print("%-8s %4d cards %7d bytes" % (k, len(out[k]["keys"]), out[k]["bytes"]))
    print("walk candidates:", winfo)


if __name__ == "__main__":
    main()
