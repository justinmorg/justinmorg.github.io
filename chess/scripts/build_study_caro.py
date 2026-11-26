#!/usr/bin/env python3
"""build_study_caro — Caro-Kann by variety, for /chess-study (2026-11-26).

Parked idea 1 of 2026-11-25 ("Caro by variety"). Three decks:

  caro_lessons (CK)  lesson cards: how to tell the varieties apart, what your
                     games say about each, and the plans that answer White's
                     set-up. Figures are from caro/analyze.py, setups.py,
                     breaks.py, kside.py, kingzone.py (exploratory, not
                     pre-registered; see notes/2026-11-26-caro-varieties.md),
                     typed into caro_lesson_figures below with their source.
                     Every line is legality-checked and every `ev=` range and
                     move answer is checked with Stockfish 17.1 depth 20.
  caro_which (CW)    "Which Caro is this?": positions from his games after
                     White's 6th-9th move; name the variety, then pick the plan.
                     Keys come from the move order (caro/classify.py), not an
                     engine.
  caro_moves (CB)    "Good idea or mistake?": his own Caro positions where he
                     played a theme move (kingside pawn move; ...d4 in the
                     Advance; ...e5 in the Exchange). Judge the move he played,
                     then find a good one. Engine-keyed (Stockfish 17.1 depth 18)
                     from chess/study/caro_moments.json, written by
                     caro/select_moments.py. About 40% of the moves were fine.
                     Positions are level or close, so no card states the
                     evaluation before the answer (Justin, 2026-11-25).

Engine cache: chess/study/engine_cache_caro.json. A rebuild with the cache and
caro_moments.json present needs no engine.
"""
import os, sys, json, random
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "caro"))
import enginecheck
enginecheck.CACHE = os.path.join(HERE, "..", "study", "engine_cache_caro.json")
import studylib
from studycards import write_deck, after, gsub, game_link, mv
from studyauthor import S, Q, C, build, number_line
from classify import caro_games

START = chess.STARTING_FEN
MOMENTS = os.path.join(HERE, "..", "study", "caro_moments.json")
YEAR = {"2023": "2023", "2024rest": "2024", "2024h2": "2024", "2025q1": "2025", "2025q2": "2025", "2025q3": "2025",
        "2025q4": "2025", "2026": "2026", "pending": "2026", "2026_fblock": "2026"}
FAMNAME = {"advance": "Advance", "exchange": "Exchange", "classical": "4.Nxe4 Nf6"}

# ---------------------------------------------------------------- figures
# Lichess 3+2 / 5+0, every annotated block 2023-2026 plus pending: 1,871 Caro
# games as Black. "Big mistake" = P1 = one move that drops your winning chance
# by 15 points or more (of 100), Stockfish 16 depth 12. Panel = the 15 thread-9
# panel players (same rating band) in their own Caro games as Black, 681 games.
F = dict(
    n_all=1871,
    adv=(532, 49), exc=(483, 51), exc_nod4=(99, 53), nxe4=(141, 46), panov=(50, 44), bc4=(187, 48),
    # P1 per 100 own moves, moves 13-30: him / panel
    mg_adv=(8.4, 9.8), mg_exc=(8.5, 10.4), mg_nxe4=9.3,
    # P1 per 100 own moves, moves 4-12
    op_adv=4.0, op_exc=3.3, op_nxe4=5.5,
    # mean winning chance after own move 10 and 25
    wp_adv=(52, 50), wp_exc=(51, 45), wp_nxe4=(44, 39),
    # Exchange split by White's set-up (setups.py, /tmp/c3.py; opponents' rating equal, +1 Elo both)
    exc_c3=(137, 45, 45, 37), exc_nc3=(379, 52, 54, 49),
    # Advance 4.dxc5 (setups.py): games, score, winning chance after move 12
    adv_dxc5=(30, 42, 38), adv_c3=(156, 44), adv_nf3=(90, 56),
    # theme moves, own moves 6-30: his P1 % (n) / panel P1 % (n)  (breaks.py)
    d4_adv=(26, 114, 23, 13), e5_exc=(27, 93, 25, 20), f6_adv=(22, 107, 12, 40), g5_adv=(26, 39, 6, 16),
    g5_nxe4=(33, 30),
    # kingside pawn moves (kside.py): his P1% on them / on other moves; panel same
    kside=(12.3, 7.1, 11.9, 8.0),
    # kingzone.py: share of big mistakes answered by a check or a move next to your king
    king=(40, 36, 39),
    # engine, depth 20, White's view
    ev_nf6=0.29, ev_bf5=0.36,
)


def lessons(eng):
    L = []
    a, e, x = F["adv"], F["exc"], F["nxe4"]
    L.append(build("CK-which", "Which Caro is it?", "one question on move three", True, [
        S("""You have played %d Caro-Kanns in these games. Almost all of them fall into three families, and you can tell which one you are in from a single question:

<b>What did White do with the e4 pawn on move three?</b>""" % F["n_all"]),
        S("""<b>Pushed it: the Advance.</b> White's pawns on d4 and e5 lock the centre and point at your kingside. You have played this %d times and scored %d%%.

The plan in one line: <b>attack d4</b>, the base of the chain.""" % a,
          fen=START, play="e4 c6 d4 d5 e5", marks="d4:r e5:y"),
        S("""<b>Traded it: the Exchange.</b> No chain, open files. You have played it %d times and scored %d%%. If White follows up with `c4` it becomes the Panov, which has its own lesson in the Openings group.

It also arrives without d4: after `Nf3` or `Bc4` and then `exd5` `cxd5`, the pawns look the same and the same ideas apply.

The plan in one line: <b>queenside</b>. Rooks to the c- and b-files, and the b-pawn forward.""" % e,
          fen=START, play="e4 c6 d4 d5 exd5 cxd5", marks="d5:g d4:y"),
        S("""<b>Defended it with a knight: you take.</b> `Nc3` (or `Nd2`) `dxe4` `Nxe4`. Strictly this family is called the main line; the "Classical" is the name for `Bf5` here.

<b>You never play `Bf5`.</b> You play `Nf6`, %d times, scoring %d%%. That is your weakest Caro, so it gets its own lesson below. The engine rates the two moves the same (about a quarter of a pawn for White either way), so the move is not the problem.""" % x,
          fen=START, play="e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6", arrows="f6e4:y"),
        S("""Why it matters which one you are in: the same move can be right in one and wrong in another. Trading your light-squared bishop for the knight on f3 is a good idea in the Advance, because that knight guards d4. In the other two it is just a trade.

<b>Which family, then which plan.</b> The next card is what your games say about each."""),
    ]))

    L.append(build("CK-data", "What your Caro games say", "where it goes wrong, and where it doesn't", True, [
        S("""<b>The short answer: you do not make more mistakes in the Caro than players at your level.</b> What costs you is two specific set-ups by White, and one family of moves.

A "big mistake" here means one move that drops your winning chance by 15 points or more out of 100. In the middle of the game (moves 13 to 30) you make %.1f per 100 moves in the Advance and %.1f in the Exchange. Fifteen players at your rating, in their own Caro games, make %.1f and %.1f. So you are, if anything, slightly cleaner.""" % (
            F["mg_adv"][0], F["mg_exc"][0], F["mg_adv"][1], F["mg_exc"][1])),
        S("""<b>Where you lose ground:</b>

<b>Your 4...Nf6 line.</b> %d%% from %d games. You are already slightly behind by move 10 (your average winning chance %d out of 100) and it keeps slipping (%d by move 25). It also has your highest opening mistake rate: %.1f per 100 moves, against %.1f in the Advance and %.1f in the Exchange.

<b>The Exchange when White plays c3.</b> %d games, %d%%. Your winning chance goes from %d to %d between moves 12 and 25. Against the knight on c3 instead: %d games, %d%%. Same-rated opponents in both, and you are not making more mistakes per move against c3. White is simply playing a set-up with a clear plan, and you need one too.

<b>The Advance with 4.dxc5.</b> %d games, %d%%, and you are behind by move 12 (%d). A small sample, but the games share a pattern, covered in the Advance lesson.""" % (
            F["nxe4"][1], F["nxe4"][0], F["wp_nxe4"][0], F["wp_nxe4"][1], F["op_nxe4"], F["op_adv"], F["op_exc"],
            F["exc_c3"][0], F["exc_c3"][1], F["exc_c3"][2], F["exc_c3"][3], F["exc_nc3"][0], F["exc_nc3"][1],
            F["adv_dxc5"][0], F["adv_dxc5"][1], F["adv_dxc5"][2])),
        S("""<b>The moves that go wrong:</b> pawn moves that open lines.

Kingside pawn moves (any move of your f-, g- or h-pawn that is not a capture) are a big mistake %.0f%% of the time, against %.0f%% for everything else. That is true at your level generally (the fifteen players: %.0f%% against %.0f%%), and you play them no more often than they do. So it is not a flaw of yours. It is the most dangerous move in this opening, for everyone.

Two central pawn pushes are as risky: `d4` in the Advance (a big mistake in %d%% of your %d tries) and `e5` in the Exchange (%d%% of %d). Peers are about the same.

Where you do look worse than peers, on small samples: `f6` in the Advance (%d%% against %d%%) and `g5` in the Advance (%d%% against %d%%).""" % (
            F["kside"][0], F["kside"][1], F["kside"][2], F["kside"][3], F["d4_adv"][0], F["d4_adv"][1],
            F["e5_exc"][0], F["e5_exc"][1], F["f6_adv"][0], F["f6_adv"][2], F["g5_adv"][0], F["g5_adv"][2])),
        S("""<b>Where the damage lands:</b> %d%% of your big mistakes are answered by a check or a move right next to your king. Peers: %d to %d%%. Again the opening, not you: the Caro sends the light-squared bishop out early, and it often gets traded, so your castled king has one defender fewer than in most openings.

<b>So what to do.</b> Learn the plan for the two set-ups that hurt (the next three lessons), and treat every kingside pawn move as a move that needs a reason. The "Good idea or mistake?" deck is your own positions where you played exactly those moves.

<i>How sure is this?</i> Exploratory: nothing here was predicted in advance, and the peer samples for single moves are small (13 to 40 moves). The 4...Nf6 and c3 results come from your games alone, 137 to 141 games each, so a difference of a few percent could be luck; the drift in winning chance is the steadier signal.""" % F["king"]),
    ]))

    # ---------------------------------------------------------- Advance
    L.append(build("CK-advance", "The Advance: walls and the d4 target", "and what to do against 4.dxc5", True, [
        S("""<b>White's method:</b> a pawn chain d4 and e5. It gives White space on the kingside, and against that you have one target: <b>d4</b>, the base of the chain.

You know the moves (the Openings group has them): `c5`, `Nc6`, `Bg4` to remove d4's defender, `e6`, the knight to f5 and the queen to b6. You score %d%% against `c3` and %d%% against `Nf3`, and you are usually better after move 12. That is the part to keep.""" % (F["adv_c3"][1], F["adv_nf3"][1]),
          fen=START, play="e4 c6 d4 d5 e5 c5 c3 Nc6 Nf3 cxd4 cxd4 Bg4", marks="d4:r", arrows="g4f3:b c6d4:b"),
        S("""<b>The idea that ties your mistakes together: your d5 and e6 pawns are walls.</b> Behind them sits your king, and in front of them White's pieces are pointed at your position.

This is your game. You traded the bishop for the knight (fine), White took with the queen, then gave up the bishop on c6. Now the queen on f3 looks down the long diagonal, and the only thing between it and c6 is your d5 pawn.""",
          fen=START, play="e4 c6 d4 d5 e5 c5 dxc5 Nc6 Nf3 Bg4 h3 Bxf3 Qxf3 e6 Bb5 Ne7 Bg5 Qa5+ Nc3 Nf5 Bxc6+ bxc6 O-O",
          arrows="f3c6:r", marks="d5:y"),
        S("""You played `d4`, hitting the knight. The wall moved and `Qxc6` was mate.

`Bxc5` takes your pawn back and you would have been better. Nothing complicated was missed. A pawn that was blocking a line stopped blocking it.""",
          play="d4 Qxc6#", ev=None),
        S("""<b>The other wall: f7.</b> The pawn on f7 guards two squares, e6 and g6. Play `f6` and both lose their guard.

Another of your games. White's queen has just come to g4.""",
          fen=START, play="e4 c6 Nf3 d5 e5 c5 d4 Nc6 Bb5 e6 O-O Ne7 dxc5 Nf5 Bxc6+ bxc6 c3 Bxc5 Nbd2 Ba6 Re1 O-O Nb3 Be7 Nbd4 Nxd4 Qxd4 c5 Qg4",
          arrows="g4e6:y", marks="e6:y f7:y"),
        Q("Your move. Find something safe here.", ["Bd3", "Kh8"], "Either keeps the walls up. In the game you played `f6`, and `Qxe6+` won the pawn with check and the bishop on a6 next.",
          bad={"f6": "That takes f7's guard off e6: `Qxe6+` wins a pawn with check, and the bishop on a6 hangs next."},
          hint="The queen on g4 is aimed at e6 and g7. Do not loosen either."),
        S("""<b>When is ...f6 right?</b> When it hits e5 and the squares it gives up are covered: your king is not castled on that side yet, or e6 is defended by a piece and nothing of White's can reach g6. Then ...f6 opens the f-file for your rook, which is the other way to attack the chain.

The test before any f-, g- or h-pawn move: <b>which square does this pawn stop guarding, and can a White piece get there?</b>"""),
        S("""<b>Against 4.dxc5.</b> White gives up the chain to grab a pawn. You have answered `Nc6` almost every time, and you score %d%% here.

The cleaner move is `e6`, and the bishop takes back on c5. The pawn comes back, the bishop is on a good diagonal, and you never needed the knight on c6, which is exactly where the queen-and-bishop tricks above land.""" % F["adv_dxc5"][1],
          fen=START, play="e4 c6 d4 d5 e5 c5 dxc5"),
        Q("Your move.", ["e6"], "Then `Bxc5`. `Nc6` is playable too, but it puts a knight on the square White's bishop and queen are aiming at.",
          also=["Nc6"], hint="Get the pawn back with a piece that wants to be on c5."),
        S("""<b>One more thing from your trade check:</b> in the Advance you are usually a little better after move 12, and that is where your even trades handed the edge back. Before trading in the Advance, ask whether your pieces are doing more than White's. They usually are."""),
    ], engine=eng))

    # ---------------------------------------------------------- Exchange
    L.append(build("CK-exchange", "The Exchange: when White plays c3", "a queenside plan against a kingside one", True, [
        S("""<b>Two White set-ups.</b> With the knight on c3 the position stays symmetrical and you do fine: %d%% from %d games. With the pawn on c3 and the bishop on d3, White has a plan, and you score %d%% from %d games, sliding from a %d to a %d winning chance between moves 12 and 25.""" % (
            F["exc_nc3"][1], F["exc_nc3"][0], F["exc_c3"][1], F["exc_c3"][0], F["exc_c3"][2], F["exc_c3"][3]),
          fen=START, play="e4 c6 d4 d5 exd5 cxd5 Bd3 Nc6 c3 Nf6 Bf4 Bg4 Qb3 Qd7 Nd2 e6 Ngf3", marks="c3:y d3:y"),
        S("""<b>White's plan:</b> the kingside. Bishop on d3, queen to c2, knight to e5, sometimes f4, all aimed at <b>h7</b>. In your c3 games White put a knight on e5 in 41%% and the bishop on d3 in 43%%, twice as often as in the other Exchange games.

<b>Your plan:</b> the queenside. Bishop out, castle, rooks to c8 and b8, then `b5` and `b4` to hit the pawn on c3. When it goes, White is left with a weak pawn on c3 or d4 and you have an open file. You already push the b-pawn in half these games. Good.""",
          play="Bd6 Bxd6 Qxd6 O-O O-O Rfe1 Rab8", arrows="b7b5:b b5b4:b b8b4:b d3h7:r f3e5:r", ev=(0.0, 0.7)),
        S("""<b>The race means h7 needs a guard.</b> Your light-squared bishop often leaves for f3 (it is a fine trade), and then the knight on f6 is h7's only defender. When that knight moves or is traded, h7 is the first thing to look at.

Your game: White has just recaptured on h5 with the queen.""",
          fen=START, play="e4 c6 Nf3 d5 exd5 cxd5 d4 Nc6 Bb5 Bg4 O-O Nf6 h3 Bxf3 Qxf3 e6 Bg5 Be7 Nc3 O-O Ne2 Rc8 c3 a6 Bd3 b5 Nf4 Na5 Nh5 Nxh5 Qxh5",
          arrows="d3h7:r h5h7:r", marks="h7:r"),
        Q("Your move.", ["g6"], "Blocks the bishop and takes the queen's squares. In the game `Bxg5` was met by `Qxh7` mate.",
          bad={"Bxg5": "`Qxh7` is mate. The knight that guarded h7 was traded on h5."},
          hint="Count what hits h7, and what defends it."),
        S("""<b>The other risky move: `e5`.</b> It looks active, but it opens the e-file and leaves your d5 pawn alone in the middle. In your Exchange games it was a big mistake %d%% of the time (%d tries). Peers: about the same. Only push it when d5 is solidly covered and nothing is lined up on the e-file.

Your game: rooks are on the c-file and your knights are active. You played `e5`, and `Nxd5` simply took the pawn.""" % (F["e5_exc"][0], F["e5_exc"][1]),
          fen=START, play="e4 c6 Nf3 d5 exd5 cxd5 d4 Nc6 c3 Bg4 Be2 Nf6 Bf4 e6 h3 Bxf3 Bxf3 Bd6 Bxd6 Qxd6 Nd2 O-O O-O Rac8 Re1 a6 g4 b5 Nb3 Nd7 Qd2 a5 Nc1 b4 Ne2 bxc3 bxc3 Nb6 a4 Nc4 Qf4 Qxf4 Nxf4 Nd2 Bg2 Rfe8 Rad1 Ne4 Rc1",
          marks="d5:y c3:y"),
        Q("Your move.", ["Nd6", "Red8"], "Keep the pressure on c3 and leave d5 where it is. That is the queenside plan working: White's pawns on c3 and a4 are the targets.",
          bad={"e5": "`Nxd5`. The pawn on d5 lost the e6 pawn's support."},
          hint="Look at what White's c3 and a4 pawns need."),
        S("""<b>In one line:</b> against c3 and Bd3, push on the queenside, keep a guard on h7, and leave your e- and kingside pawns alone until there is a reason. Against `Qb3` early, `Qd7` (it is in the Openings group)."""),
    ], engine=eng))

    # ---------------------------------------------------------- 4.Nxe4 Nf6
    L.append(build("CK-nf6", "Your 4...Nf6 line", "keep the queens, guard h7", True, [
        S("""After `Nxe4` `Nf6`, White almost always takes: `Nxf6+`, and you take back towards the middle with `exf6`. White took in %d of your %d games here, and you recaptured with the e-pawn every time.""" % (77, F["nxe4"][0]),
          fen=START, play="e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Nxf6+ exf6"),
        S("""<b>Read the pawns.</b> On the queenside White has four pawns (a, b, c, d) against your three. On the kingside you have four against three, but two of yours are doubled, so they cannot make a passed pawn.

That means one thing: <b>endgames favour White.</b> With the queens off, White's extra queenside pawn eventually becomes a passed pawn and yours never will. So you want pieces on the board and quick development. This is the one Caro line where your habit of taking every even trade is wrong.""",
          marks="a2:y b2:y c2:y d4:y f7:b f6:b", ev=(0.0, 0.6)),
        S("""<b>The set-up:</b> `Bd6`, castle, rook to e8, and then the knight goes the long way: d7, f8, and on to g6 or e6.""",
          play="Nf3 Bd6 Bd3 O-O O-O Re8 c3 Nd7 Qc2", arrows="d3h7:r c2h7:r"),
        Q("White has lined up the bishop and queen on h7. Your move.", ["Nf8"], "The knight on f8 guards h7 for good, and from there it reaches g6 and e6. This is the standard regrouping in this line, and the engine's top choice here.",
          also=["h6"], hint="One of your pieces can cover h7 permanently."),
        S("""Your f6 pawn helps too: it keeps White's knight off e5 and g5. That is why this structure holds up.

<b>Two warnings from your games.</b> Pushing your kingside pawns strips the king: `g5` was a big mistake in %d%% of your %d tries in this line. And the bishop sacrifice on h7 appears in game after game when h7 has no knight next to it. Get the knight to f8 before anything else on the kingside.""" % F["g5_nxe4"]),
        S("""<b>If White does not take on f6:</b> `Ng5` has its own card in the Openings group (`h6`, kick it at once). `Ng3` is answered by normal development: `Bg4` or `Bf5`, `e6`, `Bd6` or `Be7`."""),
    ], engine=eng))
    return L


# ---------------------------------------------------------------- caro_which
PLANS = ["Pressure d4: ...c5, ...Nc6, ...Qb6, ...Nf5, the bishop for the f3 knight",
         "Queenside: rooks to c- and b-files, ...b5 and ...b4",
         "Knights first, hold d5, then trade pieces against the isolated pawn",
         "Develop fast, keep queens on, knight to f8 to guard h7"]
VARS = ["Advance", "Exchange", "Panov", "4.Nxe4 Nf6"]
WHY = {0: "The pawn chain d4-e5 is locked. Its base, d4, is the target, and every piece has a job against it.",
       1: "Symmetrical pawns, and your half-open file is the c-file. The plan is on the queenside, with the b-pawn as the battering ram.",
       2: "White's c-pawn went to c4, so d4 will end up isolated. Blockade d5 with a piece, and the more pieces are traded, the weaker that pawn gets.",
       3: "Your doubled f-pawns cannot make a passed pawn and White's queenside majority can, so endgames favour White. Keep the queens on and guard h7."}


def which_cards():
    gs = caro_games()
    pools = {0: [], 1: [], 2: [], 3: []}
    for g in gs:
        s = g["sans16"]
        if g["var"] == "advance" and s[2] == "d4" and "c5" in s[5:8]:
            pools[0].append(g)
        elif g["var"] in ("exchange",) and g["struct"] == "carlsbad":
            pools[1].append(g)
        elif g["var"] == "panov":
            pools[2].append(g)
        elif g["var"] == "classical_nf6" and len(s) > 9 and s[8] == "Nxf6+" and s[9] == "exf6":
            pools[3].append(g)
    cards = []
    drilled = studylib.drilled_gids()
    for k, pool in pools.items():
        rnd = random.Random(700 + k)
        pool = [g for g in pool if g["gid"] not in drilled]
        rnd.shuffle(pool)
        n = 0
        for g in pool:
            ply = rnd.choice([12, 14, 16, 18])          # Black to move after White's 7th-10th
            if len(g["moves"]) <= ply + 2:
                continue
            b = chess.Board()
            for u in g["moves"][:ply]:
                b.push(chess.Move.from_uci(u))
            # Panov must have c4 played, 4.Nxe4 must show exf6
            if k == 2 and "c2c4" not in g["moves"][:ply]:
                continue
            if b.is_check():
                continue
            last = g["moves"][ply - 1]
            sub = gsub(None, chess.BLACK, b.fullmove_number, YEAR.get(g["block"], ""))
            moves_txt = number_line(chess.Board(), [x for x in g["sans16"][:min(ply, 12)]])
            cards.append({"k": "CW-%s-%d" % (g["gid"], ply), "t": "Which Caro is this?", "sub": sub, "flip": True,
                          "links": [game_link(g["gid"], ply, False)],
                          "steps": [
                              {"type": "choice", "fen": b.fen(), "last": last,
                               "ask": "Which Caro are you in?", "options": VARS, "answer": k,
                               "explain": "<b>%s.</b> It started %s." % (VARS[k], '<span class="mv">%s</span>' % moves_txt)},
                              {"type": "choice", "fen": b.fen(), "last": last,
                               "ask": "So what is your plan?", "options": PLANS, "answer": k,
                               "explain": WHY[k]},
                          ]})
            n += 1
            if n >= 6:
                break
    random.Random(711).shuffle(cards)
    return cards


# ---------------------------------------------------------------- caro_moves
def pvline(b, ucis, n=8):
    x, sans = b.copy(stack=False), []
    for u in ucis[:n]:
        m = chess.Move.from_uci(u)
        if m not in x.legal_moves:
            break
        sans.append(x.san(m)); x.push(m)
    return number_line(b, sans)


def near_king(b, sq):
    k = b.king(chess.BLACK)
    return abs(chess.square_file(k) - chess.square_file(sq)) <= 2 and abs(chess.square_rank(k) - chess.square_rank(sq)) <= 3


VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def black_material(b, ucis, n=8):
    """Black's material balance at the last quiet point of the line (the move just
    played was not a capture and gives no check), so a cut mid-exchange is not read
    as a loss."""
    x = b.copy(stack=False)
    bal = lambda y: sum(VAL.get(p.piece_type, 0) * (1 if p.color == chess.BLACK else -1) for p in y.piece_map().values())
    last = bal(x)
    for u in ucis[:n]:
        m = chess.Move.from_uci(u)
        if m not in x.legal_moves:
            break
        cap = x.is_capture(m)
        x.push(m)
        if not cap and not x.is_check():
            last = bal(x)
    return last


def why_bad(c, b):
    """One plain sentence on what the played move gave up: the square it stopped
    guarding (if White's reply uses it) or the material by the end of the line."""
    m = chess.Move.from_uci(c["uci"])
    a = after(b, m)
    pv = c["played_pv"]
    lost = black_material(b, c["good"][0][2]) - black_material(b, pv)
    tail = ""
    if 1 <= lost <= 5:
        tail = " By the end of that line you are %s behind where the better move leaves you." % (
            {1: "a pawn", 2: "two pawns", 3: "a piece", 4: "a piece and a pawn", 5: "a rook's worth"}[lost])
    if len(pv) < 2:
        return tail.strip()
    r = chess.Move.from_uci(pv[1])
    if r not in a.legal_moves:
        return tail.strip()
    rs = a.san(r)
    sq = chess.square_name(r.to_square)
    if c["theme"] == "kside" and m.from_square == chess.F7 and r.to_square in (chess.E6, chess.G6):
        return ("The f7 pawn was guarding %s, and White's answer %s lands right there." % (sq, mv(rs))) + tail
    if c["theme"] == "d4" and chess.D5 in chess.SquareSet(chess.between(r.from_square, r.to_square)):
        return ("The d5 pawn was blocking that line. With it gone, %s comes through." % mv(rs)) + tail
    if c["theme"] == "e5" and r.to_square in (chess.D5, chess.E5, chess.D4):
        return ("With the e-pawn gone from e6, d5 loses its support and the centre opens: %s." % mv(rs)) + tail
    if c["theme"] == "kside" and (a.gives_check(r) or near_king(a, r.to_square)):
        return ("The %s-pawn was part of your king's cover, and White goes straight there: %s." % (
            chess.square_name(m.from_square)[0], mv(rs))) + tail
    if a.gives_check(r) or near_king(a, r.to_square):
        return ("White's answer goes at your king: %s." % mv(rs)) + tail
    if tail:
        return tail.strip()
    return "No material goes, but White's pieces get much more active."


def moves_cards():
    data = json.load(open(MOMENTS))
    cards = []
    for c in data:
        b = chess.Board(c["fen"])
        me = chess.BLACK
        san = c["san"]
        good = c["good"]
        best = good[0]
        bsan = b.san(chess.Move.from_uci(best[0]))
        if c["kind"] == "bad":
            cost = round(100 * (c["best_w"] - c["played_w"]))
            exp = ("<b>A mistake.</b> After %s, White's best is: <span class=\"mv\">%s</span>. %s "
                   "It cost about %d points of winning chance out of 100. Better was %s: <span class=\"mv\">%s</span>." % (
                       mv(san), pvline(b, c["played_pv"]), why_bad(c, b), cost, mv(bsan), pvline(b, best[2])))
            ans = 1
        else:
            others = [b.san(chess.Move.from_uci(g[0])) for g in good if g[0] != c["uci"]][:2]
            exp = ("<b>A good move.</b> Here it holds up: <span class=\"mv\">%s</span>. Worth a look: which square did the pawn "
                   "stop guarding, and why can't White use it? %s" % (pvline(b, c["played_pv"]),
                                              ("Also good: %s." % ", ".join(mv(o) for o in others)) if others else ""))
            ans = 0
        accept = {g[0]: {"san": b.san(chess.Move.from_uci(g[0])), "fen": after(b, chess.Move.from_uci(g[0])).fen()} for g in good}
        bad = {}
        if c["kind"] == "bad":
            bad[c["uci"]] = "%s is the game move, and it is the mistake." % mv(san)
        steps = [
            {"type": "choice", "fen": c["fen"], "last": c["moves"][-1],
             "ask": "In the game you played %s here. Good idea, or a mistake?" % mv(san),
             "options": ["Good idea", "Mistake"], "answer": ans, "explain": exp},
            {"type": "move", "fen": c["fen"], "last": c["moves"][-1],
             "ask": "Now play a good move." + (" The game move counts." if c["kind"] == "fine" else ""),
             "accept": accept, "main": best[0], "bad": bad,
             "wrong": "Not one of the engine's good options here. Try another, or ask to be shown.",
             "text": "<p class=\"dim\">Judged by Stockfish 17.1 at depth 18. Good = within 5 points of winning chance of its best move.</p>"},
        ]
        extra = " &middot; ".join(x for x in (FAMNAME[c["fam"]], YEAR.get(c["block"], "")) if x)
        cards.append({"k": "CB-%s-%d" % (c["gid"], c["ply"]), "t": "Good idea or mistake?",
                      "sub": gsub(None, me, b.fullmove_number, extra), "flip": True,
                      "links": [game_link(c["gid"], c["ply"], False)], "steps": steps})
    random.Random(1127).shuffle(cards)
    return cards


def main():
    eng = enginecheck.Engine(depth=20)
    try:
        print("caro_lessons", write_deck({"id": "caro_lessons", "title": "Caro-Kann by variety", "cards": lessons(eng)})["bytes"])
    finally:
        eng.close()
    w = which_cards()
    print("caro_which", len(w), write_deck({"id": "caro_which", "title": "Which Caro is this?", "cards": w})["bytes"])
    m = moves_cards()
    print("caro_moves", len(m), write_deck({"id": "caro_moves", "title": "Good idea or mistake?", "cards": m})["bytes"])


if __name__ == "__main__":
    main()
