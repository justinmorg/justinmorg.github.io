#!/usr/bin/env python3
"""build_study_openings — opening lessons and drills for /chess-study.

Scope is a patch, not a repertoire (README "After the treatment block", item 2):
  - the repeat errors confirmed in README "Opening errors are almost never
    repeats" (Englund, Panov ...Bf5, Advance ...Bh5);
  - the London position reached ~80 times a year and resolved five ways
    (README "Where the book stops"), i.e. the ...Nc6 set-ups;
  - Caro-Kann plans, Advance against Exchange (asked for 2026-10);
  - a default against first moves with book depth 0 (1.c4 and friends).

Every line is replayed for legality. Every drill answer, and every position
carrying an `ev=` range, is checked with Stockfish 17.1 at depth 20 through
enginecheck (cached). Game counts and scores quoted on cards come from the
3+2 / 5+0 Lichess blocks plus data/pending (5,580 games) and are computed
here, not typed in: see `stat()`.
"""
import os, sys
import chess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studylib, enginecheck
from studycards import *
from studyauthor import S, Q, C, build

START = chess.STARTING_FEN
_games = None


def stat(prefix, me, nxt=None):
    """(games, score%) for games of mine as `me` starting with the SAN prefix;
    with nxt, restricted to that next move."""
    global _games
    if _games is None:
        _games = studylib.load()
    sans = prefix.split()
    if nxt:
        sans = sans + [nxt]
    n, sc = 0, 0.0
    for g in _games:
        if g["me"] != me or len(g["moves"]) < len(sans):
            continue
        b = chess.Board()
        ok = True
        for i, s in enumerate(sans):
            try:
                m = b.parse_san(s)
            except Exception:
                ok = False
                break
            if m.uci() != g["moves"][i]:
                ok = False
                break
            b.push(m)
        if ok:
            n += 1
            sc += g["score"]
    return n, (round(100.0 * sc / n) if n else 0)


def ns(prefix, me, nxt=None):
    n, p = stat(prefix, me, nxt)
    return "%d games, %d%%" % (n, p)


W, B = True, False


def lessons(eng):
    L = []
    tabA, tabB = "d4 d5 Bf4 Nf6 e3 Nc6", "d4 d5 Bf4 Nc6 e3 Nf6"
    nA, nB = stat(tabA, W), stat(tabB, W)
    nf3 = [stat(tabA, W, "Nf3"), stat(tabB, W, "Nf3")]
    c4 = [stat(tabA, W, "c4"), stat(tabB, W, "c4")]
    def pool(x):
        n = x[0][0] + x[1][0]
        return n, round((x[0][0] * x[0][1] + x[1][0] * x[1][1]) / float(n))
    pn, pc = pool(nf3), pool(c4)
    qb3 = stat("d4 d5 Bf4 Nc6 e3 Bf5 c4 e6 Nc3 Bb4", W, "Qb3")
    bb4 = stat("d4 d5 Bf4 Nc6 e3 Bf5 c4 e6 Nc3 Bb4", W)

    # ---------------------------------------------------------- London vs ...Nc6
    L.append(build("OL-london-nc6", "London: when the knight comes to c6", "the one position you keep re-solving", False, [
        S("""This position, with knights on c6 and f6, is the one place in your London where you stop and think. It has come up %d times by two move orders, and you have tried five different fourth moves, at nearly four seconds each.

Your results do not depend on the choice: `Nf3` has scored %d%% (%d games) and `c4` %d%% (%d games). So this lesson is not fixing a bad move. It is about having one answer, so the clock stays with you.""" % (
            nA[0] + nB[0], pn[1], pn[0], pc[1], pc[0]),
          fen=START, play=tabB),
        S("""<b>What Black is up to.</b> The knight on c6 blocks Black's own c-pawn, so the usual ...c5 is off the table. Instead Black has two quick ideas: the bishop to f5 and the knight to b4, both aimed at c2; or ...e5 in one go.""",
          arrows="c8f5:r c6b4:r f5c2:r e7e5:y"),
        S("""<b>One move for every order: `c4`.</b> You already play it when the bishop comes to f5 first, so nothing new to learn. It hits d5 while the c6 knight is in the way of ...c6, and it opens a4 and b3 for your queen.

`Nf3` is just as good. Pick one and stop choosing.""",
          play="c4", ev=(0.1, 0.9)),
        S("""<b>Thing one: ...Nb4 is a mistake, and `Qa4+` punishes it.</b> The knight has left c6, so the check cannot be blocked comfortably and the knight on b4 is hanging at the end of it.""",
          fen=START, play="d4 d5 Bf4 Nc6 e3 Bf5 c4 Nb4 Qa4+", arrows="a4e8:g a4b4:g", ev=(0.7, 3.0)),
        S("""If the knight goes home with `Nc6`, then `cxd5` `Qxd5` `Nc3`. Your knight comes out with tempo on the queen, the knight on c6 is still pinned, and `Nb5` hitting c7 is next. Black has moved the same knight three times and is losing material.""",
          play="Nc6 cxd5 Qxd5 Nc3", arrows="c3b5:y a4c6:g", ev=(1.2, 5.0)),
        S("""<b>Thing two: ...e5 is answered with the bishop.</b> `Bxe5`, and after `Nxe5` `dxe5` you are simply a pawn up. Taking with the d-pawn instead hands Black the initiative for the pawn.""",
          fen=START, play="d4 d5 Bf4 Nc6 e3 Bf5 c4 e5 Bxe5", ev=(0.7, 3.0)),
        S("""<b>Thing three: the pin on c3.</b> After `e6` `Nc3` `Bb4` you have played `Qb3` in %d of %d games and scored %d%% with it. It looks active and wins nothing, and the engine puts it about two-thirds of a pawn behind plain development.""" % (
            qb3[0], bb4[0], qb3[1]),
          fen=START, play="d4 d5 Bf4 Nc6 e3 Bf5 c4 e6 Nc3 Bb4", arrows="d1b3:r"),
        S("""`Nf3`, then `Rc1` and the bishop out. If you want the centre settled first, `cxd5` is fine too. These moves are interchangeable.

<b>The rule that covers all of it:</b> in the ...Nc6 lines the queen goes to a4 with check when the knight jumps to b4, and otherwise stays home until you have castled. `Qb3` is not your move while a knight can hit it from b4 or a5.""",
          play="Nf3", ev=(0.0, 1.0)),
    ], engine=eng))

    # ---------------------------------------------------------- Englund
    e2nf3 = stat("d4 e5 Nf3", B)
    e2nf3nc6 = stat("d4 e5 Nf3", B, "Nc6")
    e4e3 = stat("d4 e5 dxe5 Nc6 Nf3 Qe7 e3", B)
    e4e3q = stat("d4 e5 dxe5 Nc6 Nf3 Qe7 e3", B, "Qb4+")
    ed5 = stat("d4 e5 d5", B)
    ed5f5 = stat("d4 e5 d5", B, "f5")
    eall = stat("d4 e5", B)
    L.append(build("OL-englund", "Englund: the spots where your games repeat", "a patch, not an endorsement", True, [
        S("""You have played the Englund %d times in these games and scored %d%%. The engine thinks it costs Black about a pawn from move one, and nothing in this lesson changes that. Whether to keep it is a separate decision.

What this lesson does is narrower. A handful of positions come up again and again, and in each you tend to play the same second-best move. Those are cheap to fix.""" % eall,
          fen=START, play="d4 e5"),
        S("""<b>They decline with `Nf3`.</b> You have answered `Nc6` in %d of %d games. It runs into `d5` and the knight gets kicked around.

`e4` instead. The pawn gains time on the knight and you are already comfortable. (`exd4` is also fine.)""" % (e2nf3nc6[0], e2nf3[0]),
          play="Nf3 e4", arrows="e4f3:g", ev=(-1.0, 0.2)),
        S("""<b>They push past with `d5`.</b> You nearly always play `f5` (%d of %d). The engine prefers plain development by about four-fifths of a pawn: `Bc5`, then ...d6 and ...Nf6. The pawn on d5 has given you the c5 square for free, so use it.""" % (ed5f5[0], ed5[0]),
          fen=START, play="d4 e5 d5 Bc5", arrows="f8c5:g", ev=(-0.8, 0.4)),
        S("""<b>They play `c3`, `e3` or `c4` instead of taking.</b> Just take: `exd4`. You get a normal position with equal chances and no gambit to justify.""",
          fen=START, play="d4 e5 c3 exd4", ev=(-0.3, 0.8)),
        S("""<b>The main line.</b> `dxe5` `Nc6` `Nf3` `Qe7`. Now it depends on White's fourth move.

Against `e3` you have played `Qb4+` in %d of %d games, and it is an error every time. There is no bishop on d2 to trap and no pawn on b2 worth the time: White just develops with tempo. Take the pawn back, `Nxe5`.""" % (e4e3q[0], e4e3[0]),
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 e3 Nxe5", ev=(0.2, 1.2)),
        S("""Against `Qd5` the check is wrong again. `f6` is the move: it breaks up the e5 pawn and gets your pieces out.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Qd5 f6", ev=(0.2, 1.4)),
        S("""<b>The line the opening is played for.</b> `Bf4` `Qb4+` `Bd2` `Qxb2`. If White now defends with `Bc3`, the bishop move you know: `Bb4`.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Bc3 Bb4", arrows="b4c3:g"),
        S("""`Qd2` loses on the spot to `Bxc3` `Qxc3` `Qc1` mate.""",
          play="Qd2 Bxc3 Qxc3 Qc1#"),
        S("""But when White takes, `Bxb4`, recapture with the <b>knight</b>. `Nxb4` threatens both the rook on a1 and a fork on c2, and White cannot cover both.

In your games you took the rook at once with `Qxa1` every time. That is still good for you, but after `Bd2` the queen is short of squares and most of the advantage is gone.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Bc3 Bb4 Bxb4 Nxb4", arrows="b4c2:g b2a1:g", ev=(-9.0, -2.5)),
        S("""<b>White plays it properly: `Nc3`.</b> Now `Bb4` `Rb1` `Qa3`, and you are at the position where your clock use triples. There are three White moves and one answer to each.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Rb1 Qa3"),
        S("""`Rb3`: the queen has exactly one square. `Qa5`.""",
          play="Rb3 Qa5"),
        S("""`Nb5`: take the bishop with check first, `Bxd2+`, and only then `Qxa2`. Taking on a2 at once runs into `Rxb4`, and after the recapture `Nxc7+` forks king and rook.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Rb1 Qa3 Nb5 Bxd2+ Qxd2 Qxa2"),
        S("""`Nd5`: the refutation you know from the White side. `Bxd2+` `Qxd2` `Kd8` is the best there is. You are worse here, by about two pawns in the engine's view, and there is no trick that fixes it. This is the real price of the opening against someone who knows it.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Rb1 Qa3 Nd5 Bxd2+ Qxd2 Kd8", ev=(1.2, 3.5)),
        S("""<b>The other knight jump: `Nd5` a move earlier,</b> before Rb1. `Bxd2+` `Nxd2`, and now c7 is hit. You have played `Qxe5` here every time. It walks into `Nc4`, which hits the queen and renews the threat on c7.

`Kd8` covers c7 first. The e5 pawn will still be there next move.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Nd5 Bxd2+ Nxd2 Kd8", arrows="d5c7:r"),
        S("""<b>One more.</b> When White plays `Nc3` on move three, before Nf3, do not play `Qe7` out of habit: `Nd5` hits the queen and c7 at once. Take the pawn, `Nxe5`.""",
          fen=START, play="d4 e5 dxe5 Nc6 Nc3 Nxe5", ev=(0.2, 1.3)),
    ], engine=eng))

    # ---------------------------------------------------------- Caro plans
    h3 = stat("e4 c6 d4 d5 e5 c5 c3 Nc6 Nf3 cxd4 cxd4 Bg4 h3", B)
    h3h5 = stat("e4 c6 d4 d5 e5 c5 c3 Nc6 Nf3 cxd4 cxd4 Bg4 h3", B, "Bh5")
    pan = stat("e4 c6 d4 d5 exd5 cxd5 c4 Nc6 Nc3", B)
    panbf5 = stat("e4 c6 d4 d5 exd5 cxd5 c4 Nc6 Nc3", B, "Bf5")
    L.append(build("OL-caro-plans", "Caro-Kann: Advance against Exchange", "what you are playing for in each", True, [
        S("""You have said the Caro feels less understood than the London: the moves are known, the plans are not. The short version is that the pawn structure tells you the plan, and the Advance and the Exchange are two different structures with two different jobs."""),
        S("""<b>The Advance.</b> White's pawns on d4 and e5 form a chain pointing at your kingside. A chain is attacked at its base, and the base is d4. Everything you do in this line is about d4.

Your move `c5` hits it first. `Nc6` hits it second.""",
          fen=START, play="e4 c6 d4 d5 e5 c5 c3 Nc6 Nf3 cxd4 cxd4", marks="d4:r", arrows="c6d4:g"),
        S("""`Bg4`. Two reasons, both about d4. The bishop gets outside your pawns before ...e6 shuts the door. And it pins, or trades itself for, the f3 knight, which is d4's main defender.""",
          play="Bg4", arrows="g4f3:g f3d4:y"),
        S("""Then `e6`, the knight from g8 to e7 and on to f5, and the queen to b6. That is three attackers on one pawn, with the bishop tying down its defender. Which of ...Nge7 and ...Qb6 comes first does not matter.

This is the position to carry in your head: every piece has a job and the job is d4.""",
          play="Be2 e6 O-O Nge7 Nc3 Nf5", arrows="f5d4:g c6d4:g g4f3:g", marks="d4:r", ev=(-0.6, 0.7)),
        S("""<b>Your one repeat error here.</b> When White plays `h3`, you have retreated to h5 in %d of %d games. Then `g4` and `e6` follow, and White has the initiative.

Take the knight. `Bxf3`. If the queen recaptures, `Nxd4` wins the base of the chain. If the pawn recaptures, White's kingside is wrecked. This is what the bishop went to g4 for.""" % (h3h5[0], h3[0]),
          fen=START, play="e4 c6 d4 d5 e5 c5 c3 Nc6 Nf3 cxd4 cxd4 Bg4 h3 Bxf3", arrows="c6d4:g", ev=(-2.0, -0.4)),
        S("""<b>The Exchange.</b> No chain, no base, no target on d4. The pawns are symmetrical except for one thing: you have a half-open c-file and White has a half-open e-file.

So the job changes. First, develop without getting the bishop stuck: knights to c6 and f6, bishop out to g4 or f5, and only then ...e6.""",
          fen=START, play="e4 c6 d4 d5 exd5 cxd5 Bd3 Nc6 c3 Nf6 Bf4 Bg4", arrows="c8c3:y"),
        S("""The one move to know: `Qb3` hits b7 and d5 together. `Qd7` covers both. (`Qc8` and `Na5` are equally good. It does not matter which.)""",
          play="Qb3 Qd7", arrows="b3b7:r b3d5:r", ev=(-0.3, 0.8)),
        S("""Then ...e6, ...Bd6, castle. In the middlegame your plan is on the queenside: rooks to the c-file and b-file, and the b-pawn up to b4 to make c3 a target. It is called the minority attack. White's play is on the kingside and the e-file.

Advance: hit d4. Exchange: c-file and the b-pawn.""",
          play="Nd2 e6 Ngf3 Bd6", arrows="b7b5:g b5b4:g", ev=(-0.4, 0.9)),
        S("""<b>The Panov, `c4`.</b> A third structure: White is going to end up with an isolated pawn on d4, and until then has pressure on d5. Here the order of your moves matters.

After `Nc6` `Nc3` you have played `Bf5` in %d of %d games. It loses about a piece's worth: `cxd5` hits the knight, which has no good square, and d5 is gone.""" % (panbf5[0], pan[0]),
          fen=START, play="e4 c6 d4 d5 exd5 cxd5 c4 Nc6 Nc3 Bf5 cxd5", arrows="d5c6:r", ev=(1.8, 5.0)),
        S("""In the Panov the knights come first and the bishop stays home until d5 is secure. `Nf6`, then `e6`, then the bishop to e7 or b4.

When White finally takes on d5 you recapture with a piece, and you have what you want: a knight sitting on d5 in front of an isolated pawn. From there, trade minor pieces. The fewer pieces left, the weaker that pawn gets.""",
          fen=START, play="e4 c6 d4 d5 exd5 cxd5 c4 Nf6 Nc3 e6 Nf3 Be7 cxd5 Nxd5", marks="d4:r d5:g", ev=(-0.2, 0.8)),
    ], engine=eng))

    # ---------------------------------------------------------- Caro small fixes
    ng5 = stat("e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Ng5", B)
    bb3 = stat("e4 c6 Bc4 d5 exd5 cxd5 Bb3", B)
    bb3a5 = stat("e4 c6 Bc4 d5 exd5 cxd5 Bb3", B, "a5")
    L.append(build("OL-caro-small", "Caro-Kann: two small things", "one worth fixing, one not", True, [
        S("""<b>Worth fixing: the knight on g5.</b> After `Nc3` `dxe4` `Nxe4` `Nf6`, some opponents dodge the trade with `Ng5`. You have met it %d times and scored %d%%, and you have tried seven different replies.

The knight is aiming at f7 with a bishop coming to c4. Do not let it settle.""" % ng5,
          fen=START, play="e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Ng5", arrows="g5f7:r f1c4:y"),
        S("""`h6`. Ask the question at once. The knight has to retreat, and its trip has gained nothing. Then develop normally: ...Bf5 or ...Bg4, ...e6.

With the sample this small the 31%% could be luck. But one reply is still better than seven.""" % (),
          play="h6", arrows="h6g5:g", ev=(-0.6, 0.3)),
        S("""<b>Not worth fixing: `a5` against the bishop on b3.</b> After `Bc4` `d5` `exd5` `cxd5` `Bb3` you play `a5` nearly every time (%d of %d). The engine likes plain development about a third of a pawn more.

You score %d%% from here, and a third of a pawn in the opening is inside the noise at any level you will play at. Keep it if you like it. It is a move that does not matter.""" % (bb3a5[0], bb3[0], bb3[1]),
          fen=START, play="e4 c6 Bc4 d5 exd5 cxd5 Bb3 a5"),
    ], engine=eng))

    # ---------------------------------------------------------- flank
    c4 = stat("c4", B)
    c4e5 = stat("c4", B, "e5")
    b3 = stat("b3", B, "e5")
    e3 = stat("e3", B, "e5")
    L.append(build("OL-flank", "First moves you have no reply to", "1.c4, 1.b3, 1.e3, 1.g3, 1.f4", True, [
        S("""Against 1.e4 and 1.d4 your first moves are automatic. Against everything else there is no settled reply at all: about 70 games a year start with you thinking on move one.

Mostly the results are fine. Against `b3` your ...e5 has scored %d%% (%d games), against `e3` %d%% (%d). The exception is `c4`: %d games, and %d%% with ...e5. That is a small sample and could be chance, but it is also the one of these where ...e5 leads to positions you have never studied.""" % (
            b3[1], b3[0], e3[1], e3[0], c4[0], c4e5[1])),
        S("""<b>Rule one: if they let you, take the centre.</b> Against `b3` and `e3`, keep doing what works: `e5`, then ...d5 or ...Nc6, and develop. Nothing to learn.""",
          fen=START, play="b3 e5 Bb2 Nc6 e3 d5", ev=(-0.7, 0.3)),
        S("""<b>Rule two: against `c4`, play your Caro pawns.</b> `c6`, then `d5`. You already know what these pawns do.""",
          fen=START, play="c4 c6", arrows="d7d5:g", ev=(-0.1, 0.7)),
        S("""If White plays `e4`, you are in a Caro-Kann. After `d5` `exd5` `cxd5` `d4` it is the Panov from the Caro lesson: knights first.""",
          play="e4 d5 exd5 cxd5 d4 Nf6", ev=(-0.1, 0.7)),
        S("""If White takes twice instead, `cxd5`, do not rush to take back with the queen. `Nf6` first, and the pawn on d5 falls anyway.""",
          fen=START, play="c4 c6 e4 d5 exd5 cxd5 cxd5 Nf6", arrows="f6d5:g", ev=(-0.2, 0.6)),
        S("""If White keeps it quiet with `Nf3` and `g3`, set up the London with colours reversed: pawns on c6, d5 and e6, bishop outside them first. Here `Bg4` is a shade better than f5, because a queen on b3 then has less to hit.""",
          fen=START, play="c4 c6 Nf3 d5 g3 Nf6 Bg2 Bg4", ev=(-0.2, 0.8)),
        S("""If White plays `d4`, it is a Slav. One thing to know. When White has knights on both c3 and f3, the bishop does <b>not</b> come out: `Bf5` runs into `cxd5` and `Qb3`, hitting b7 and d5. It is the same trick you use yourself in the London.

Play `e6` instead and develop behind the pawns: ...Nbd7, ...Bd6, castle.""",
          fen=START, play="c4 c6 d4 d5 Nf3 Nf6 Nc3 e6", ev=(-0.1, 0.8)),
        S("""<b>Rule three: `g3`, `f4` and the rest.</b> `d5` on move one, then the same set-up: ...c6 if the d-pawn needs support, bishop out to f5 or g4, ...e6, ...Nf6. Against 1.Nf3 you already play ...d5 and score well. Leave that alone.

None of this needs memorising past move three. The point is that move one stops costing time."""),
    ], engine=eng))
    return L


def drills(eng):
    D = []

    def d(key, sub, flip, prefix, method, note, also=None, bad=None, ask=None, tol=70, hint=None):
        b = chess.Board()
        sans = prefix.split()
        for s in sans:
            b.push_san(s)
        from studyauthor import number_line
        line = number_line(chess.Board(), sans)
        return build("OD-" + key, "Your move", sub, flip, [
            Q(ask or "What do you play?", method, note, fen=START, play=prefix, also=also, bad=bad, tol=tol, hint=hint,
              text="<span class=\"mv\">%s</span>" % line),
        ], engine=eng)

    Lw, En, Ca, Fl = "London &middot; you're White", "Englund &middot; you're Black", "Caro-Kann &middot; you're Black", "Flank openings &middot; you're Black"
    D += [
        d("lon-tabiya", Lw, False, "d4 d5 Bf4 Nc6 e3 Nf6", "c4", "One answer for every move order. It hits d5 while the knight blocks ...c6.",
          also=["Nf3"]),
        d("lon-nb4", Lw, False, "d4 d5 Bf4 Nc6 e3 Bf5 c4 Nb4", "Qa4+", "The knight has left c6, so the check wins time and the knight on b4 is loose.",
          bad={"Na3": "`Na3` holds c2 but lets Black off. There is a move that punishes ...Nb4."}),
        d("lon-nb4-2", Lw, False, "d4 d5 Bf4 Nf6 e3 Nc6 Nf3 Bf5 c4 Nb4", "Qa4+", "Same idea with the knights on f3 and f6: after ...c6 the queen simply takes on b4.",
          bad={"Na3": "`Na3` holds c2 but lets Black off. There is a move that punishes ...Nb4."}),
        d("lon-e5", Lw, False, "d4 d5 Bf4 Nc6 e3 Bf5 c4 e5", "Bxe5", "With the bishop. After ...Nxe5, dxe5 you are a clean pawn up.",
          bad={"dxe5": "`dxe5` keeps the pawn but hands Black the initiative. Take with the piece.",
               "cxd5": "`cxd5` lets Black off with ...Bb4+. There is a move that just wins a pawn."}),
        d("lon-bb4", Lw, False, "d4 d5 Bf4 Nc6 e3 Bf5 c4 e6 Nc3 Bb4", "Nf3", "Plain development. The queen stays home until you have castled.",
          also=["cxd5", "Rc1"], bad={"Qb3": "`Qb3` is the move you usually play here. It wins nothing and the engine puts it two-thirds of a pawn behind simple development."}),
        d("lon-e6", Lw, False, "d4 d5 Bf4 Nf6 e3 Nc6 Nf3 Bf5 c4 e6", "Nc3", "Develop. `c5`, gaining space, is just as good.",
          also=["c5"], bad={"Qb3": "`Qb3` runs into ...Nb4, and now it is your c2 that is under fire."}),
        d("eng-nf3", En, True, "d4 e5 Nf3", "e4", "The pawn gains time on the knight, and you are already comfortable.",
          also=["exd4"], bad={"Nc6": "`Nc6` is what you usually play. It runs into d5 and the knight gets kicked."}),
        d("eng-d5", En, True, "d4 e5 d5", "Bc5", "The d5 pawn has given you c5. Develop onto it.",
          also=["Nf6", "Bb4+"], bad={"f5": "`f5` is your usual move here. The engine prefers plain development by about four-fifths of a pawn."}),
        d("eng-c3", En, True, "d4 e5 c3", "exd4", "Just take. A normal, equal position.", also=["e4"]),
        d("eng-e3", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 e3", "Nxe5", "Take the pawn back. There is nothing on b2 worth a queen trip.",
          bad={"Qb4+": "`Qb4+` only helps White develop: Nc3, and the queen has to move again."}),
        d("eng-qd5", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Qd5", "f6", "Break up the e5 pawn and get the pieces out.",
          bad={"Qb4+": "`Qb4+` loses time again: Nc3, and the queen on d5 is still defending e5."}, tol=40),
        d("eng-nc3-3", En, True, "d4 e5 dxe5 Nc6 Nc3", "Nxe5", "Take the pawn. The queen stays home.",
          also=["Bb4"], bad={"Qe7": "`Qe7` out of habit runs into Nd5, hitting the queen and c7."}),
        d("eng-bc3", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Bc3", "Bb4", "The pin. Now Qd2 loses to ...Bxc3 and ...Qc1 mate."),
        d("eng-bxb4", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Bc3 Bb4 Bxb4", "Nxb4", "With the knight: it threatens the rook and a fork on c2 together.",
          bad={"Qxa1": "`Qxa1` is what you have played. It is still good, but after Bd2 the queen is short of squares. There is something much stronger.",
               "Qxb4+": "`Qxb4+` gives most of it back. Look at what the knight can do."}),
        d("eng-rb1", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Rb1", "Qa3", "The only square that keeps the bishop on b4 defended."),
        d("eng-rb3", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Rb1 Qa3 Rb3", "Qa5", "The only square."),
        d("eng-nb5", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Rb1 Qa3 Nb5", "Bxd2+", "Check first, then ...Qxa2.",
          bad={"Qxa2": "`Qxa2` at once runs into Rxb4, and after the recapture Nxc7+ forks king and rook.",
               "Qa5": "`Qa5` is about a pawn worse in the engine's view. Trade the bishop off with check first."}),
        d("eng-nd5", En, True, "d4 e5 dxe5 Nc6 Nf3 Qe7 Bf4 Qb4+ Bd2 Qxb2 Nc3 Bb4 Nd5 Bxd2+ Nxd2", "Kd8", "Cover c7 first. The pawn on e5 is not going anywhere.",
          also=["Nb4"], bad={"Qxe5": "`Qxe5` is what you have played every time. Nc4 hits the queen and c7 again."}),
        d("caro-h3", Ca, True, "e4 c6 d4 d5 e5 c5 c3 Nc6 Nf3 cxd4 cxd4 Bg4 h3", "Bxf3", "This is what the bishop came to g4 for. Qxf3 loses d4; gxf3 wrecks the kingside.",
          bad={"Bh5": "`Bh5` is your usual move. g4 and then e6 follow, and White has the initiative."}),
        d("caro-panov", Ca, True, "e4 c6 d4 d5 exd5 cxd5 c4", "Nf6", "Knights first in the Panov. The bishop waits until d5 is secure.",
          also=["Nc6", "e6"]),
        d("caro-panov-bf5", Ca, True, "e4 c6 d4 d5 exd5 cxd5 c4 Nc6 Nc3", "Nf6", "Knights first. `e6` is fine too.",
          also=["e6"], bad={"Bf5": "`Bf5` is the move you have played here every time. cxd5 hits the knight and d5 falls."}),
        d("caro-panov-cxd5", Ca, True, "e4 c6 d4 d5 exd5 cxd5 c4 Nc6 cxd5", "Qxd5", "The only good recapture. The knight on c6 is attacked, so there is no time for anything else."),
        d("caro-ng5", Ca, True, "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Ng5", "h6", "Kick it at once. The knight has to retreat and its trip has gained nothing.",
          also=["c5", "Bg4", "Bf5"]),
        d("caro-qb3", Ca, True, "e4 c6 d4 d5 exd5 cxd5 Bd3 Nc6 c3 Nf6 Bf4 Bg4 Qb3", "Qd7", "Covers b7 and d5 together.",
          also=["Qc8", "Na5"]),
        d("flank-c4", Fl, True, "c4", "c6", "Your Caro pawns. ...d5 next, whatever White does.",
          also=["e5"]),
        d("flank-c4-e4", Fl, True, "c4 c6 e4", "d5", "And it is a Caro-Kann."),
        d("flank-cxd5", Fl, True, "c4 c6 e4 d5 exd5 cxd5 cxd5", "Nf6", "No hurry. The pawn on d5 falls anyway, and your queen is not exposed in the centre.",
          also=["Qxd5"]),
        d("flank-slav", Fl, True, "c4 c6 d4 d5 Nf3 Nf6 Nc3", "e6", "With both white knights out, the bishop stays in. Develop behind the pawns.",
          also=["dxc4", "a6"], bad={"Bf5": "`Bf5` runs into cxd5 and Qb3, hitting b7 and d5: the trick you play yourself in the London."}),
        d("flank-reti", Fl, True, "c4 c6 Nf3 d5 g3 Nf6 Bg2", "Bg4", "The London with colours reversed: bishop out, then ...e6.",
          also=["Bf5", "g6", "dxc4"]),
        d("flank-b3", Fl, True, "b3", "e5", "They let you, so take the centre. `d5` is just as good.", also=["d5"]),
    ]
    return D


def main():
    eng = enginecheck.Engine(depth=20)
    try:
        a = write_deck({"id": "op_lessons", "title": "Opening lessons", "cards": lessons(eng)})
        b = write_deck({"id": "op_drills", "title": "Your move", "cards": drills(eng)})
    finally:
        eng.close()
    for x in (a, b):
        print("%-10s %4d cards %7d bytes" % (x["id"], len(x["keys"]), x["bytes"]))


if __name__ == "__main__":
    main()
