#!/usr/bin/env python3
"""build_study_review — the "Review your own games" group for /chess-study.

    python3 build_study_review.py          write review_lessons.json and review_games.json
    python3 build_study_review.py --facts  print the per-game facts and stop

Inputs (no engine or network needed here):
  chess/study/review_pick.json    the 30 games (review/evaluate.py picks them: the
                                  most recent group F block losses not used by any
                                  other chess-study deck)
  chess/study/review_engine.json  Stockfish 16, depth 16 on every position; depth 20
                                  MultiPV 4 before each deciding move and depth 20
                                  after it (review/deep.py)

Where a game turned is review/keys.py (definitions in its docstring). The kind
of mistake is computed from the depth-20 lines, 1 pawn / 3 piece / 5 rook /
9 queen:
  mate      the reply line after his move mates him
  material  after his move, their best line (6 plies) leaves him >= 2 points
            worse off than before the move, and >= 2 worse than his best line
  missed    he had a forced mate and his move gave it up, or his best line
            (7 plies) wins >= 2 points that the played line does not
  position  none of those: nothing is lost on the board yet, the position is worse
The builder asserts every move it names is legal and refuses a card whose
accepted moves include the move he played.
"""
import os, sys, json, statistics
import chess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "review"))
from studycards import write_deck, mv  # noqa: E402
import scanlib  # noqa: E402
import keys  # noqa: E402

STUDY = os.path.join(HERE, "..", "study")
GAMES = json.load(open(os.path.join(STUDY, "review_pick.json")))
CACHE = json.load(open(os.path.join(STUDY, "review_engine.json")))
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
NAME = scanlib.NAME
KINDS = ["They could win material", "They had a mating attack", "I missed a win of my own",
         "Nothing was lost yet: my position just got worse"]
GUESS = ["I lost material", "I got mated or attacked", "My position slowly got worse", "The clock", "Not sure"]


def P(*paras):
    return "".join("<p>%s</p>" % x for x in paras)


def clock(s):
    s = max(0, int(round(s)))
    return "%d:%02d" % (s // 60, s % 60)


def chance(cp_white, me):
    c = cp_white if me else -cp_white
    if c >= 9000:
        return "100% (you had a forced mate)"
    if c <= -9000:
        return "0% (they had a forced mate)"
    return pct(keys.wp(cp_white, me))


def pct(x):
    return "%d%%" % round(100 * x)


def mat(b, me):
    return sum(VAL[p.piece_type] * (1 if p.color == me else -1) for p in b.piece_map().values())


def npm(b):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.piece_type not in (chess.PAWN, chess.KING))


def line_mat(b, pv, plies, me):
    b = b.copy()
    for u in pv[:plies]:
        b.push_uci(u)
    return mat(b, me)


def variation(b, pv, n):
    ms = []
    bb = b.copy()
    for u in pv[:n]:
        m = chess.Move.from_uci(u)
        assert m in bb.legal_moves, (b.fen(), u)
        ms.append(m)
        bb.push(m)
    return b.variation_san(ms), bb


def me_cp(cp_white, me):
    return cp_white if me else -cp_white


def spent(g, j):
    """Seconds he spent on ply j (1-based): his clock after his previous move minus after this one, plus increment."""
    inc = 2 if g["tc"] == "180+2" else 0
    base = 180 if g["tc"] == "180+2" else 300
    prev = g["clocks"][j - 3] if j >= 3 else base
    return prev - g["clocks"][j - 1] + inc, prev


def fullmove(j):
    return (j + 1) // 2


def mlabel(j, san):
    return "%d%s%s" % (fullmove(j), "." if j % 2 == 1 else "...", san)


def facts(g):
    me = chess.WHITE if g["me"] == "w" else chess.BLACK
    r = keys.analyse(g, CACHE)
    B = keys.boards(g)
    f = {"g": g, "me": me, "r": r, "B": B, "n": r["n"], "W": r["W"], "cps": r["cps"]}
    f["how"] = ("lost on time" if g["termination"] == "Time forfeit" else
                "were checkmated" if B[-1].is_checkmate() else "resigned")
    f["spend"] = {j: spent(g, j)[0] for j in r["mine"]}
    k = r["key"]
    f["key"] = k
    if not k:
        return f
    pre, post = B[k - 1], B[k]
    played = chess.Move.from_uci(g["moves"][k - 1])
    f["pre"], f["post"], f["played"] = pre, post, played
    f["played_san"] = pre.san(played)
    f["spent"], f["clock_before"] = spent(g, k)
    f["clock_opp"] = g["clocks"][k - 2] if k >= 2 else None
    f["wb"], f["wa"] = r["W"][k - 1], r["W"][k]
    mpv = CACHE[keys.fen4(pre)]["mpv"]
    best_cp = me_cp(mpv[0][1], me)
    f["mpv"] = mpv
    # accepted: within 50cp of best (or mates when best mates), never the played move, and clearly better than it
    acc = []
    for u, cpw, pv in mpv:
        c = me_cp(cpw, me)
        if u == played.uci():
            continue
        if (best_cp >= 9000 and c >= 9000) or (best_cp < 9000 and best_cp - c <= 50):
            if keys.wp(cpw, me) >= f["wa"] + 0.10:
                acc.append((u, cpw, pv))
    assert acc, g["gid"]
    f["acc"] = acc
    ref = CACHE[keys.fen4(post)].get("ref")
    f["ref"] = ref
    m0 = mat(pre, me)
    f["mat0"] = m0
    f["npm"] = npm(pre)
    best_pv = mpv[0][2]
    mbest = line_mat(pre, best_pv, min(7, len(best_pv) - (1 - len(best_pv) % 2)), me)
    rpv = ref[1] if ref else []
    nref = min(6, len(rpv) - len(rpv) % 2)
    mref = line_mat(post, rpv, nref, me) if ref else mat(post, me)
    f["mbest"], f["mref"] = mbest, mref
    if ref and me_cp(ref[0], me) <= -9000:
        kind = 1
    elif post.is_checkmate():
        kind = 1
    elif best_cp >= 9000 and f["wa"] < 0.9:
        kind = 2
        f["missed_mate"] = 10000 - best_cp
    elif m0 - mref >= 2 and mbest - mref >= 2:
        kind = 0
    elif mbest - m0 >= 2 and mbest - mref >= 2:
        kind = 2
    else:
        kind = 3
    f["kind"] = kind
    # why a piece was there to take: scanlib's cause classes on his move
    f["cause"] = None
    if kind == 0 and rpv:
        first = chess.Move.from_uci(rpv[0])
        d = scanlib.delta(pre, played)
        for h in d["hangs"]:
            if h["move"] == first:
                f["cause"] = h.get("why")
        if f["cause"] is None and d.get("exchange") and first.to_square == played.to_square:
            f["cause"] = "exchange"
    return f


CAUSE_TEXT = {
    "stale": "the piece was already under attack before your move. Nothing about your move created the problem; an old threat was still standing and had gone invisible. That is the commonest way you lose material.",
    "check": "the piece was already capturable, and the check you were answering hit it too. Before choosing how to get out of check, ask what else that check attacks.",
    "lands": "the piece you moved could be taken where it landed. Look 2, part one: is the square safe?",
    "leaves": "the piece you moved had been guarding something, and stopped. Look 2, part two: what did it leave?",
    "opens": "moving it opened a line from one of their long-range pieces onto something of yours.",
    "blocks": "the piece you moved got in the way of one of your own pieces that was guarding something.",
    "exchange": "the trade you started loses material once you count it all the way through.",
}

NOTE = {0: "they could win material", 1: "they had a mating attack", 2: "missed a win of my own", 3: "my position got worse"}

QUESTION = {
    0: "After my move, what can they take?",
    1: "After my move, what checks do they have?",
    2: "Before I move: what can I take, and what checks do I have?",
    3: "What is my plan, and what does this move give them?",
}


def ref_text(f):
    """The punishment, in words, from the depth-20 line after his move."""
    post, me = f["post"], f["me"]
    if post.is_checkmate():
        return "It was checkmate on the spot."
    cp, pv = f["ref"]
    n = min(len(pv), 6 if f["kind"] != 1 else 8)
    line, _ = variation(post, pv, n)
    first = post.san(chess.Move.from_uci(pv[0]))
    if f["kind"] == 1:
        mate_in = 10000 - abs(cp)
        return "Their best reply is %s, and it's a forced mate%s. The line: %s." % (
            mv(first), " in %d" % mate_in if 0 < mate_in < 20 else "", line)
    if f["kind"] == 0:
        lost = f["mat0"] - f["mref"]
        return "Their best reply is %s, and a few moves later you have lost %d point%s of material compared with before your move (pawn 1, piece 3, rook 5, queen 9). The line: %s." % (
            mv(first), lost, "s" if lost != 1 else "", line)
    d = f["mref"] - f["mat0"]
    if d == 0:
        tail = "Material stays level with where it was; the position is just worse for you afterwards."
    elif d < 0:
        tail = "You end up %d point%s down, no more than your best line also gave back." % (-d, "s" if d != -1 else "")
    else:
        tail = "You're %d point%s up on the count after it, but the position is worse." % (d, "s" if d != 1 else "")
    return "Their best reply is %s. Line: %s. %s" % (mv(first), line, tail)


def best_text(f):
    pre, me = f["pre"], f["me"]
    u, cpw, pv = f["mpv"][0]
    line, _ = variation(pre, pv, min(len(pv), 5))
    s = "The engine's move was %s (line: %s)." % (mv(pre.san(chess.Move.from_uci(u))), line)
    if f.get("missed_mate"):
        s += " That's a forced mate%s, which your move let go." % (" in %d" % f["missed_mate"] if 0 < f["missed_mate"] < 20 else "")
    elif f["kind"] == 2:
        s += " That wins %d point%s of material that your move let go." % (f["mbest"] - f["mref"], "s" if f["mbest"] - f["mref"] != 1 else "")
    others = [pre.san(chess.Move.from_uci(a[0])) for a in f["acc"] if a[0] != u]
    if others:
        s += " About as good: %s." % ", ".join(mv(x) for x in others)
    return s


def game_step(f, ask_extra=""):
    g, B = f["g"], f["B"]
    plies = []
    for j, u in enumerate(g["moves"], 1):
        m = chess.Move.from_uci(u)
        plies.append([B[j - 1].san(m), B[j].fen(), u, g["clocks"][j - 1]])
    st = {"type": "game", "fen": chess.STARTING_FEN, "first": "w", "fm0": 1, "me": g["me"],
          "base": 180 if g["tc"] == "180+2" else 300, "plies": plies, "key": f["key"],
          "also": f["r"]["also"],
          "ask": "Step through the game. Stop on the move of yours where you think it was lost, and tap the button." + ask_extra,
          "none": "No move lost it"}
    return st


def card_game(i, f):
    g, me = f["g"], f["me"]
    k = f["key"]
    who = "White" if me else "Black"
    last_fm = fullmove(f["n"])
    oppelo = g.get("opp_elo") or "?"
    t = "Game %d: %s, lost move %d" % (i, (g["opening"].split(":")[0] or "Opening")[:30], last_fm)
    sub = "%s &middot; you're %s vs a %s &middot; %s" % (g["date"].replace(".", "-"), who, oppelo, g["tc"].replace("+", "+"))
    link = ["The game on Lichess", "https://lichess.org/%s%s#%d" % (g["gid"], "" if me else "/black", (k - 1) if k else f["n"])]
    intro = P("You %s on move %d. Treat this the way you'd treat a game you just finished: no engine, no evaluation bar." % (f["how"], last_fm),
              "<b>Step 1, the gut call.</b> Before you look at a single move: what do you think lost it?")
    steps = [{"type": "verify", "fen": chess.STARTING_FEN, "flip": not me, "text": intro,
              "ask": "Your first guess (not scored, just recorded):", "options": GUESS}]
    gs = game_step(f)
    W = f["W"]
    if not k:
        # no move lost it
        endw = W[-1]
        if f["how"] == "lost on time":
            longest = sorted(f["spend"].items(), key=lambda x: -x[1])[:3]
            lt = ", ".join("%s (%ds)" % (mv(mlabel(j, gs["plies"][j - 1][0])), s) for j, s in longest)
            c20 = [g["clocks"][j - 1] for j in f["r"]["mine"] if fullmove(j) == 20]
            gs["rtext"] = P("Nothing on the board lost this one. Your chances were %s when your flag fell on move %d; you were winning." % (pct(endw), last_fm),
                            "Where the time went: your three longest thinks were %s.%s" % (lt, (" At move 20 you had %s left." % clock(c20[0])) if c20 else ""),
                            "<b>The question for next time:</b> when you're clearly winning and the clock is low, what's the simplest safe move? Trade pieces, push nothing risky, and move fast.")
        else:
            post = f["B"][-1]
            replies = [post.san(m) for m in post.legal_moves]
            gs["rtext"] = P("Nothing on the board lost this one. You resigned on move %d in a position the engine calls level (your chances: %s)." % (last_fm, pct(endw)),
                            "From that position you had %s legal replies, including %s. Maybe you had to go, or the check looked worse than it was. If it was the second: check the escape squares before giving up." % (len(replies), ", ".join(mv(x) for x in replies[:4])))
        gs["rok"] = "Right, no single move."
        gs["rno"] = ""
        gs["ralso"] = "That move was costly, but you got back to a good position afterwards."
        steps.append(gs)
        steps.append({"type": "show", "fen": f["B"][-1].fen(), "flip": not me,
                      "text": P("<b>Your note for this game:</b> \"%s\"" % ("Won position, lost on time." if f["how"] == "lost on time" else "Resigned a level position."),
                                "Compare with your first guess.")})
        return {"k": "RV-%s-0" % g["gid"], "t": t, "sub": sub, "flip": not me, "links": [link], "steps": steps,
                "_kind": "clock" if f["how"] == "lost on time" else "resign", "_f": f}
    pre, post = f["pre"], f["post"]
    lab = mlabel(k, f["played_san"])
    peak = f["r"]["peak"]
    was = ""
    if W[peak] >= 0.70 and peak <= k - 3 and W[peak] >= f["wb"] + 0.10:
        was = " Earlier, after move %d, your chances had been %s." % (fullmove(peak), chance(f["cps"][peak], me))
    gs["rtext"] = P("The game turned on %s. Your winning chances were %s before it and %s after it, and you never got back to even chances.%s"
                    % (mv(lab), chance(f["cps"][k - 1], me), chance(f["cps"][k], me), was),
                    "You had %s on your clock and spent %ds on the move." % (clock(f["clock_before"]), round(f["spent"])))
    gs["rok"] = ""
    gs["rno"] = "The moment is marked with a red outline in the move list, and the board has jumped there."
    gs["ralso"] = "You lost a lot there too, but you were still in the game afterwards. The one that decided it is marked in red, and the board has jumped there."
    steps.append(gs)
    pa = [[f["played"].uci(), "r"]]
    expl = ref_text(f)
    if f["kind"] == 2:
        u = f["mpv"][0][0]
        expl = "You had %s, which %s. After your move: %s" % (
            mv(pre.san(chess.Move.from_uci(u))),
            "was a forced mate" if f.get("missed_mate") else "won %d points of material" % (f["mbest"] - f["mref"]), expl)
    if f["cause"]:
        expl += " Why it was there to take: " + CAUSE_TEXT[f["cause"]]
    steps.append({"type": "choice", "fen": pre.fen(), "last": g["moves"][k - 2] if k >= 2 else None, "flip": not me,
                  "arrows": pa, "text": P("<b>Step 3, name it.</b> You played %s (red arrow)." % mv(lab)),
                  "ask": "What was wrong with it?", "options": KINDS, "answer": f["kind"], "explain": expl,
                  "rarrows": [[f["ref"][1][0], "y"]] if f["ref"] else []})
    accept = {}
    for u, cpw, pv in f["acc"]:
        m = chess.Move.from_uci(u)
        b2 = pre.copy()
        b2.push(m)
        accept[u] = {"san": pre.san(m), "fen": b2.fen(),
                     "note": "Your chances after it: %s, against %s after %s." % (pct(keys.wp(cpw, me)), pct(f["wa"]), mv(f["played_san"]))}
    steps.append({"type": "move", "fen": pre.fen(), "last": g["moves"][k - 2] if k >= 2 else None, "flip": not me,
                  "text": P("<b>Step 4, the better move.</b> Now you can think like the engine would."),
                  "ask": "Find a better move than %s." % mv(f["played_san"]), "accept": accept, "main": f["acc"][0][0],
                  "wrong": "Not one of the engine's choices. Try again, or ask to be shown."})
    endg = " It was an endgame, which is where your extra seconds should go." if f["npm"] <= 13 else ""
    steps.append({"type": "show", "fen": pre.fen(), "last": g["moves"][k - 2] if k >= 2 else None, "flip": not me,
                  "arrows": [[f["played"].uci(), "r"], [f["mpv"][0][0], "g"]],
                  "text": P(best_text(f) + endg,
                            "<b>Step 5, one line.</b> If this were your notebook: <i>Move %d, %s, %s on the clock. Next time ask: %s</i>" % (fullmove(k), NOTE[f["kind"]], clock(f["clock_before"]), QUESTION[f["kind"]][0].lower() + QUESTION[f["kind"]][1:]),
                            "Compare with your first guess. If the engine's move still makes no sense to you, open the game and save it: that's a gap in understanding, not in looking.")})
    return {"k": "RV-%s-%d" % (g["gid"], k), "t": t, "sub": sub, "flip": not me, "links": [link], "steps": steps,
            "_kind": ["material", "mate", "missed", "position"][f["kind"]], "_f": f}


def all_facts():
    return [facts(g) for g in GAMES]


def summary(F):
    K = [f for f in F if f["key"]]
    kinds = [sum(1 for f in K if f["kind"] == i) for i in range(4)]
    S = {"n": len(F), "nk": len(K), "kinds": kinds,
         "clock": sum(1 for f in F if not f["key"] and f["how"] == "lost on time"),
         "resign": sum(1 for f in F if not f["key"] and f["how"] != "lost on time"),
         "move_med": statistics.median(fullmove(f["key"]) for f in K),
         "move_lo": min(fullmove(f["key"]) for f in K), "move_hi": max(fullmove(f["key"]) for f in K),
         "clk_med": statistics.median(f["clock_before"] for f in K),
         "clk_low": sum(1 for f in K if f["clock_before"] < 30),
         "spent_med": statistics.median(f["spent"] for f in K),
         "spent_all": statistics.median(s for f in F for j, s in f["spend"].items() if fullmove(j) >= 10),
         "winning": sum(1 for f in K if f["W"][f["r"]["peak"]] >= 0.70 and f["r"]["peak"] < f["key"]),
         "first": F[0]["g"]["date"].replace(".", "-"), "last": F[-1]["g"]["date"].replace(".", "-")}
    return S


def lessons(S):
    forcing = S["kinds"][0] + S["kinds"][1]
    cards = []
    cards.append({"k": "RVL-why", "t": "Why review, and why now", "steps": [{"type": "show", "text": P(
        "<b>Reviewing a loss is the one study habit that keeps pointing your other study at the right thing.</b> A drill trains one skill; a review tells you which skill the last game actually needed.",
        "Your rate of leaving material hanging has been flat for two years of blitz, against weaker and stronger opponents alike. More games alone haven't moved it. A few minutes after a loss turns the game into one line: where it turned, what kind of mistake, and the question that would have caught it.",
        "Keep it small or it won't last. <b>Losses only. Three to five minutes. Not every game</b>: one or two a day is plenty, and skip it when you're annoyed. It must not become another data project.",
        "These cards teach the routine on your %d most recent losses (%s to %s). Do a few at a time. After that, do the same thing on Lichess after your own games." % (S["n"], S["first"], S["last"]))}]})
    cards.append({"k": "RVL-steps", "t": "The routine: five steps", "steps": [{"type": "show", "text": P(
        "<b>1. Gut call.</b> Before looking at anything: why do you think you lost? One phrase. This is the part that trains your judgment, because you find out later whether you were right.",
        "<b>2. Step through with the engine off.</b> No evaluation bar, no arrows. Just the moves and the clocks.",
        "<b>3. Find the turning point.</b> The move of yours after which the game was never level again. Not the last blunder before resigning; the first moment it went from playable to lost. Then name it: what kind of mistake was it (next card)?",
        "<b>4. Turn the engine on and check.</b> Did you find the same move? What was better? If the engine's move makes no sense to you even after a minute, save the position. That's a gap in understanding, and it's worth asking about.",
        "<b>5. Write one line.</b> Move number, kind of mistake, clock, and the question that would have caught it. Example: <i>Move 21, they could win material, 2:00 on the clock. Next time ask: after my move, what can they take?</i>")}]})
    cards.append({"k": "RVL-kinds", "t": "Naming the mistake: four kinds", "steps": [{"type": "show", "text": P(
        "Every turning point in these cards gets one of four names, plus a fifth for games the board didn't decide. Each name comes with the question that would have caught it.",
        "<b>They could win material.</b> Your move let them take something, at once or after a short forcing line. Question: <i>after my move, what can they take?</i>",
        "<b>They had a mating attack.</b> Your move let them in at your king. Question: <i>after my move, what checks do they have?</i>",
        "<b>I missed a win of my own.</b> You had a forced mate or a material win and played something else. Question: <i>before I move, what can I take, and what checks do I have?</i>",
        "<b>Nothing was lost yet: my position just got worse.</b> No material changes hands, but the engine's line leaves you clearly worse. Usually a quiet move without a plan. Question: <i>what is my plan, and what does this move give them?</i>",
        "<b>No move lost it.</b> You lost on time with a good position, or resigned one. The review then is about the clock, not the moves.",
        "How the cards decide the name: the engine's best line for each side over the next few moves, with pawn 1, piece 3, rook 5, queen 9. Losing 2 points or more counts as losing material.")}]})
    cards.append({"k": "RVL-data", "t": "What your last %d losses say" % S["n"], "steps": [{"type": "show", "text": P(
        "<b>In %d of the %d games where one move decided it, that move let your opponent do something forcing</b>: win material (%d games) or start a mating attack (%d). Look 1, &ldquo;after my move, what can they take or check?&rdquo;, would have been the question in most of these games." % (forcing, S["nk"], S["kinds"][0], S["kinds"][1]),
        "The rest: %d where your position just got worse with no material lost, and %d where you missed a win of your own. In %d game%s you lost on time from a good position, and in %d you resigned a level one." % (S["kinds"][3], S["kinds"][2], S["clock"], "s" if S["clock"] != 1 else "", S["resign"]),
        "<b>It wasn't the clock.</b> At the turning point you had a median of %s left (only %d of %d had under half a minute), and you spent a median of %ss on the deciding move, against %ss on a typical move from move 10 on. You took a bit longer and still missed it, which is the same picture as your two-year data: the time is there, the check isn't." % (clock(S["clk_med"]), S["clk_low"], S["nk"], ("%g" % S["spent_med"]), ("%g" % S["spent_all"])),
        "The turning point came around move %d, in the middlegame (range %d to %d). In %d of the %d you had been winning earlier (70%% chances or better) and let it go." % (round(S["move_med"]), S["move_lo"], S["move_hi"], S["winning"], S["nk"]),
        "<b>So what:</b> expect the review to keep naming the same kind of mistake. That's useful, not boring: a tally of your one-line notes over a few weeks tells you whether the two looks are starting to stick.",
        "<span class=\"dim\">How this was measured: Stockfish 16 at depth 16 on every position of the %d games; deeper (depth 20) on each deciding move. Winning chances use Lichess's scale. The turning point is the first of your moves, once you had dropped below 40%% for good, that cost at least 15 points of winning chances. Thirty games is a small sample: read the counts as rough shares, not exact rates.</span>" % S["n"])}]})
    cards.append({"k": "RVL-lichess", "t": "Doing it after your own games", "steps": [{"type": "show", "text": P(
        "After a loss on Lichess, open the game's analysis board and keep the computer evaluation switched off for steps 1 to 3. Step through with the arrows.",
        "Step 4: switch the engine on, or request a computer analysis, and jump to the move you picked. The evaluation graph is a fast way to see whether the real turning point was earlier.",
        "Step 5: write your gut call in the game's private Notes tab on Lichess before you analyse, then add the result to the Review log at the top of this page. It keeps the weekly count of mistake types and how often your gut call was right. If one kind dominates, that's what your next ten-minute windows should go to.",
        "If an engine move makes no sense after a minute, add it to a private Lichess study (say, \"Positions I don't get\"), one chapter per position, from the analysis board menu. Those are worth bringing to a chat, or to a video on that idea.",
        "Short on time? Steps 1, 3 and 5 alone are worth doing: the gut call, the turning point, the one line.")}]})
    return cards


def main():
    F = all_facts()
    S = summary(F)
    cards = []
    for i, f in enumerate(reversed(F), 1):          # most recent first
        cards.append(card_game(i, f))
    write_deck({"id": "review_games", "title": "Review your losses", "cards": cards})
    write_deck({"id": "review_lessons", "title": "How to review a game", "cards": lessons(S)})
    print("review: %d lessons, %d games" % (len(lessons(S)), len(cards)), S)


if __name__ == "__main__" and "--facts" not in sys.argv:
    main()

if __name__ == "__main__" and "--facts" in sys.argv:
    for i, f in enumerate(all_facts(), 1):
        g = f["g"]
        if not f["key"]:
            print(i, g["gid"], "no key", f["how"]); continue
        print(i, g["gid"], g["me"], mlabel(f["key"], f["played_san"]), "%.0f->%.0f" % (100 * f["wb"], 100 * f["wa"]),
              ["material", "mate", "missed", "position"][f["kind"]], f["cause"], "m0", f["mat0"], "mbest", f["mbest"], "mref", f["mref"],
              "npm", f["npm"], "clk", f["clock_before"], "spent", f["spent"], "acc", [a[0] for a in f["acc"]], "ref", f["ref"][1][:4] if f["ref"] else None)
