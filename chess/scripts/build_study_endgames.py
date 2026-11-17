#!/usr/bin/env python3
"""build_study_endgames — endgame lessons and drills for /chess-study.

Decks:
  eg_lessons  authored lessons, tablebase-verified move by move
  eg_square   "does the pawn queen?" choice cards (generated, tablebase-keyed)
  eg_kpk      king-and-pawn only-move cards (generated, tablebase-keyed)
  eg_rook     rook-ending method drills: Lucena, Philidor, rook behind the pawn
  eg_own      his own passed-pawn endgame errors (Stockfish-judged; see below)
  k1, k2      conversion play-outs from his own games (spec K)

Study order follows notes/2026-11-16-plateau-fresh-review.md, addendum:
passed pawns (support before pushing), king activity, rook endings, pawn
endings, trade pieces when ahead.

Keys: eg_lessons / eg_square / eg_kpk / eg_rook are exact (7-man tablebase).
eg_own is the one deck here whose key is an engine verdict (Stockfish 17.1,
depth 20), because "which move keeps the game" in a 12-piece ending has no
rule-based answer. The cards say so.
"""
import os, sys, random, json, urllib.parse
from collections import defaultdict
import chess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import studylib, scanlib, tbprobe, enginecheck
from studycards import *
from studyauthor import S, Q, C, build, fmt, inline, number_line
from hanging import winprob

SIZES = {"square": 16, "kpk_win": 14, "kpk_draw": 14, "own": 24, "k1": 40, "k2": 40}


# ================================================================== lessons
def lessons():
    L = []

    # ---------------------------------------------------------- overview
    L.append(build("EL-overview", "Where your endgames leak, and the order to fix it", "read first, two minutes", False, [
        S("""<b>What the games say.</b> In endgames that are close (neither side clearly winning) you make a big error on about 10.5% of moves. Your opponents, in the same games, about 8.8%. That gap is not the clock: it is the same after matching for time left. In endgames where you are already winning comfortably you are as good as they are or better.

So the work is on close endgames, and the cuts below say where in them."""),
        S("""<b>Where the gap is widest.</b>
<ul class="tight"><li><b>You have a passed pawn:</b> 12.5% against 9.3%. With the pawn on the fifth rank or further: 14.8% against 10.0%.</li>
<li><b>King moves and pawn moves</b> are where the extra errors are. Rook moves are fine.</li>
<li><b>Rook endings:</b> 9.2% against 7.3%. They are in about three of every ten of your endgames; rooks with minor pieces are in seven of ten.</li>
<li><b>Up a pawn or two:</b> 9.7% against 7.2%.</li></ul>
A caution: about 45 different cuts were tried to get these, so treat them as a pointer for what to study, not as proven findings. You are one to two points worse on nearly every cut. The gap is broad, and these are the places it is widest or most frequent."""),
        S("""<b>The order of the lessons.</b>
<ol class="tight"><li><b>Support before pushing.</b> A passed pawn goes forward with its king or rook, not ahead of them.</li>
<li><b>King in front of the pawn.</b> Opposition, key squares, and how to defend against it.</li>
<li><b>The square of the pawn.</b> Whether a king catches a running pawn, without counting.</li>
<li><b>Rook endings:</b> the winning position (Lucena), the drawing position (Philidor), and rooks behind passed pawns.</li>
<li><b>Trading:</b> pieces when ahead, pawns when behind. King to the centre when the queens come off.</li></ol>
The rule inside each lesson is standard teaching. The data only chose the order. Every position in these lessons with seven pieces or fewer has been checked move by move against an endgame tablebase, which is a complete solved table, so "wins" and "draws" here are facts and not engine opinions."""),
    ]))

    # ---------------------------------------------------------- support before pushing
    L.append(build("EL-support", "Support before pushing", "passed pawns: your widest gap", False, [
        S("""<b>Push, or bring the king?</b> White to move. The pawn is passed and nothing stops `e4`.

It is the wrong move. `e4` draws. `Ke4` wins.""",
          fen="8/8/4k3/8/3K4/4P3/8/8 w - - 0 1", arrows="e3e4:r d4e4:g", tb="W"),
        S("""After `e4` the black king takes up its post in front of the pawn with `Kd6`. Your king can never get past it. This position is a draw, and the next lesson shows the defence in full.""",
          play="e4 Kd6", tb="D"),
        S("""After `Ke4` the king leads and the pawn follows behind it. Black has to give way to one side, and the white king goes round the other.

The pawn does not move until the king has cleared its road. That is the whole idea, and it is the same idea in every ending with a passed pawn.""",
          fen="8/8/4k3/8/3K4/4P3/8/8 w - - 0 1", play="Ke4 Kd6 Kf5", tb="W"),
        S("""<b>The same question with rooks on.</b> White to move, a pawn up. `e6` looks natural and throws the win away.""",
          fen="4k3/R7/8/3KP3/8/8/8/5r2 w - - 0 1", arrows="e5e6:r d5e6:g", tb="W"),
        S("""After `e6` your king has lost its shelter: the square e6 was where it would have hidden from checks. Now the rook checks from behind for ever. Draw.""",
          play="e6 Rd1+ Kc6 Rc1+ Kd6 Rd1+", tb="D"),
        S("""`Ke6` instead. King first. The king keeps its shelter in front of the pawn, `Ra8+` is in the air, and the pawn comes up behind the king later. This wins.""",
          fen="4k3/R7/8/3KP3/8/8/8/5r2 w - - 0 1", play="Ke6", arrows="a7a8:y", tb="W"),
        S("""<b>Before you push a passed pawn, three questions.</b>
<ol class="tight"><li>Once it has moved, is it attacked more times than it is defended?</li>
<li>Is the square in front of it one I control, or will a piece simply sit there and block it?</li>
<li>Could the king or the rook step up first instead?</li></ol>
If in doubt, improve the helper and push next move. A passed pawn that waits one move is still a passed pawn.

Your own games agree with this. With a passed pawn on the board your extra errors are spread over every kind of move, and you push it exactly as often as your opponents do. So the problem is not too much pushing or too little. It is the order: pawn first, helpers second.

The deck <i>Your passed pawns</i> has positions from your own games to practise on."""),
    ]))

    # ---------------------------------------------------------- king in front: opposition
    L.append(build("EL-opposition", "King in front of the pawn", "opposition and key squares", False, [
        S("""<b>One position, two results.</b> King and pawn against king. If it is Black's move here, White wins. If it is White's move, it is a draw.

The reason is called the <b>opposition</b>: the kings face each other with one square between them, and whoever has to move must step aside and let the other king through.""",
          fen="8/3k4/8/3K4/3P4/8/8/8 b - - 0 1", tb="W"),
        S("""Black to move has to give way. `Ke7`, and the white king goes round the other side with `Kc6`. This is <b>outflanking</b>.""",
          play="Ke7 Kc6", arrows="d5c6:g", tb="W"),
        S("""`Kd8` `Kd6`. Opposition again. Not the pawn yet: `d5` here would let Black draw with `Kc8`.""",
          play="Kd8 Kd6", tb="W"),
        S("""`Ke8` `Kc7`. The king now guards d6, d7 and d8, every square the pawn has to cross. Only now does the pawn run.""",
          play="Ke8 Kc7", marks="d6:g d7:g d8:g", tb="W"),
        S("""Back to the start, but with White to move. White has to give way instead. Whatever the king does, the black king stays in front, and pushing the pawn only walks into stalemate. Draw.""",
          fen="8/3k4/8/3K4/3P4/8/8/8 w - - 0 1", play="Ke5 Ke7 d5 Kd7 d6 Kd8 Ke6 Ke8 d7+ Kd8 Kd6", tb="D"),
        S("""<b>Key squares.</b> You do not have to work out the opposition every time. For a pawn that has not crossed the middle of the board, the three squares two ranks in front of it are its key squares. Here: d5, e5 and f5 for the pawn on e3.

If your king reaches any one of them, the position is won, whoever is to move.""",
          fen="8/8/4k3/8/3K4/4P3/8/8 w - - 0 1", marks="d5:y e5:y f5:y", tb="W"),
        S("""`Ke4` takes the opposition. `Kd6` `Kf5`: outflank, and the king is on a key square.""",
          play="Ke4 Kd6 Kf5", marks="d5:y e5:y f5:y", tb="W"),
        S("""The pattern repeats all the way up the board. Opposition (`Ke5`), outflank (`Kf6`), and only then does the pawn step up behind the king.""",
          play="Ke7 Ke5 Kd7 Kf6 Kc6 e4 Kd7 e5 Ke8 Ke6", tb="W"),
        S("""King on the sixth rank in front of its pawn. This wins whoever is to move. Here `Kd8` `Kf7`, and the pawn walks through e6, e7, e8.""",
          play="Kd8 Kf7", marks="e6:g e7:g e8:g", tb="W"),
        S("""<b>The exception: rook's pawns.</b> With an a-pawn or an h-pawn there is no outside to go round. If the defending king gets to the corner in front of the pawn, it is a draw however well your king stands.

So when you are trading down to a single pawn, a rook's pawn is the one to avoid being left with, and the one to leave your opponent with.""",
          fen="k7/8/K7/P7/8/8/8/8 w - - 0 1", tb="D"),
    ]))

    # ---------------------------------------------------------- defending K+P
    L.append(build("EL-defend", "Defending against a lone pawn", "straight back, then face the king", True, [
        S("""You are Black, a pawn down, and the pawn has just come to the sixth rank. Your king has three squares to go back to. One of them draws.""",
          fen="8/4k3/8/3KP3/8/8/8/8 w - - 0 1", play="e6", marks="d8:y e8:y f8:y", tb="D"),
        S("""`Ke8`. <b>Straight back.</b> From here you can answer whichever side the white king comes up.""",
          play="Ke8", tb="D"),
        S("""`Kd6` `Kd8`. Their king steps up beside the pawn and you face it. You have the opposition.""",
          play="Kd6 Kd8", tb="D"),
        S("""`e7+` `Ke8` `Ke6`. Stalemate. If White backs off instead, you do the same thing again. Draw.""",
          play="e7+ Ke8 Ke6", tb="D"),
        S("""The same position with the wrong retreat: `Kd8` instead of straight back. Now `Kd6` and it is White who has the opposition.""",
          fen="8/4k3/8/3KP3/8/8/8/8 w - - 0 1", play="e6 Kd8 Kd6", tb="W"),
        S("""`Ke8` `e7` `Kf7` `Kd7`, and the pawn queens.

<b>The defender's rule, in three parts:</b> stay in front of the pawn. When you are pushed back, go straight back. When their king steps up beside the pawn, step in front of it.""",
          play="Ke8 e7 Kf7 Kd7", tb="W"),
    ]))

    # ---------------------------------------------------------- square
    L.append(build("EL-square", "The square of the pawn", "does the king catch it?", False, [
        S("""A pawn runs for the queening square and a king chases it. You do not need to count moves.

Draw a square with the pawn in one corner and the queening square in another. Here the pawn on b4 has four steps to go, so the square is b4, f4, f8, b8.

<b>If the king is inside the square, or can step into it on its move, it catches the pawn. If not, the pawn queens.</b>""",
          fen="8/8/8/6k1/1P6/8/8/7K w - - 0 1", marks="b4:y f4:y f8:y b8:y", arrows="b4b8:y b8f8:y f8f4:y f4b4:y", tb="W"),
        S("""Here the king on g5 is outside the square and it is White's move. The pawn simply runs, and the king stays one step short the whole way.""",
          play="b5 Kf5 b6 Ke6 b7 Kd7 b8=Q", tb="W"),
        S("""The same position with Black to move. `Kf5` steps into the square.""",
          fen="8/8/8/6k1/1P6/8/8/7K b - - 0 1", play="Kf5", marks="b4:y f4:y f8:y b8:y", tb="D"),
        S("""Now the king keeps pace along the diagonal and arrives in time to take the pawn.""",
          play="b5 Ke5 b6 Kd6 b7 Kc7", tb="D"),
        S("""<b>A pawn on its starting square</b> can jump two squares, so draw the square as if the pawn already stood on the third rank. Here that is b3, g3, g8, b8. The king on h4 is outside it, so with White to move the pawn queens.""",
          fen="8/8/8/8/7k/8/1P6/7K w - - 0 1", marks="b3:y g3:y g8:y b8:y", tb="W"),
        S("""<b>When to use it.</b> Before you trade the last pieces into a pawn race, or let one pawn go to chase another, draw the square first.

One caution. The rule is for a lone pawn against a lone king. If the attacker's king can block the defender's path, or another pawn is in the way, count the moves instead."""),
    ]))

    # ---------------------------------------------------------- Lucena
    L.append(build("EL-lucena", "Rook endings: the winning position", "Lucena, or building a bridge", False, [
        S("""Most rook endings with one extra pawn come down to two positions. This is the winning one.

Your pawn is on the seventh rank, your king is in front of it, and their king is cut off by your rook. One problem: your king is boxed in. If it steps out, their rook checks it straight back in.""",
          fen="6K1/4k1P1/8/8/8/8/7r/5R2 w - - 0 1", tb="W"),
        S("""`Re1+` first. Push their king one file further away.""",
          play="Re1+ Kd7", tb="W"),
        S("""`Re4`. <b>The key move: the rook goes to the fourth rank.</b> It will be a shelter for your king, four ranks up the board. This is the bridge.""",
          play="Re4", arrows="e1e4:g", tb="W"),
        S("""Black can only wait. Now the king steps out, and walks down the board towards the checking rook.""",
          play="Rh1 Kf7 Rf1+ Kg6 Rg1+ Kf6 Rf1+ Kg5 Rg1+", tb="W"),
        S("""`Rg4`. The rook blocks the last check. The checks are over and the pawn queens.

<b>What to remember:</b> pawn on the seventh with the king in front of it; rook to the fourth rank; king out and towards the rook; block.""",
          play="Rg4", arrows="e4g4:g", tb="W"),
    ]))

    # ---------------------------------------------------------- Philidor
    L.append(build("EL-philidor", "Rook endings: the drawing position", "Philidor, or the third-rank defence", True, [
        S("""This is the drawing one. You are Black and a pawn down. Your king stands on the queening square. The defence has two halves.""",
          fen="4k3/R7/8/3KP3/8/8/8/1r6 b - - 0 1", tb="D"),
        S("""<b>First half: rook to your third rank</b> (the sixth, when you are Black). `Rb6`. It keeps their king from stepping forward. They can check, and your king just steps to e7 and back.""",
          play="Rb6", arrows="b6h6:y", tb="D"),
        S("""The only way for White to make progress is to push the pawn. `e6`. <b>That push is your signal.</b>""",
          play="e6", tb="D"),
        S("""<b>Second half: rook to the far end of the board.</b> `Rb1`. Now that the pawn stands on e6, their king has lost the square where it would have hidden from checks.""",
          play="Rb1", arrows="b6b1:g", tb="D"),
        S("""Check from behind, for ever. The king has nowhere to hide. Draw.""",
          play="Kd6 Rd1+ Ke5 Re1+ Kf6 Rf1+", tb="D"),
        S("""<b>What loses.</b> The same ending with the rook sitting passively on the back rank. `Kf6` and the king walks in, the pawn follows to e6 and e7, and the passive rook can do nothing about it. With a centre pawn, this is lost.

So: rook on the third rank until the pawn advances, then to the far end and check.""",
          fen="1r2k3/R7/8/4PK2/8/8/8/8 w - - 0 1", play="Kf6", flip=False, tb="W"),
    ]))

    # ---------------------------------------------------------- rook behind
    L.append(build("EL-rookbehind", "Rooks belong behind passed pawns", "yours or theirs", False, [
        S("""<b>Behind your own pawn.</b> Every step the pawn takes gives your rook more room, and their rook is stuck in front of it as a blocker. Here White wins by simply walking the king up to b7.""",
          fen="r7/P5k1/8/8/3K4/8/8/R7 w - - 0 1", tb="W"),
        S("""The king arrives, the blocking rook has to move away, and the pawn queens.""",
          play="Kc5 Kf7 Kb6 Ke7 Kb7 Rd8 a8=Q", tb="W"),
        S("""<b>The same pawn and the same kings, with the rooks swapped.</b> Now your rook is the one stuck in front, and theirs is behind the pawn. This is a draw.

Your rook cannot leave a8 without letting the pawn go. When your king comes up to free it, their rook checks from behind and there is nowhere to hide.""",
          fen="R7/P5k1/8/8/3K4/8/8/r7 w - - 0 1", tb="D"),
        S("""<b>The same rule from the other side.</b> When they have the passed pawn, your rook goes behind it. From there it attacks the pawn all the way up the board and keeps its freedom, and their rook ends up tied to defending.

In your close rook endings the extra errors are in king and pawn moves, and your rook moves are as good as your opponents'. So read this lesson as being about the pawn: before it advances, ask where its rook is."""),
    ]))

    # ---------------------------------------------------------- trading / king
    L.append(build("EL-trades", "What to trade, and where the king goes", "two rules of thumb", False, [
        S("""<b>Ahead: trade pieces. Behind: trade pawns.</b>

The reason is that a piece cannot win by itself. King and knight against king is a draw. King and bishop against king is a draw. An extra piece wins only because it helps a pawn to queen. So the side that is ahead needs pawns left on the board, and the side that is behind wants them gone."""),
        S("""White is a whole knight up. It is Black's move, and Black draws on the spot.""",
          fen="8/8/6kp/8/3NK1P1/8/8/8 b - - 0 1", tb="D"),
        S("""`h5`. It offers to trade the last pair of pawns. After `gxh5+` `Kxh5` White has king and knight against a bare king, which cannot be won.""",
          play="h5 gxh5+ Kxh5", tb="D"),
        S("""The same position with White to move. `Kf4` stops the trade: now `h5` is met by `g5`, keeping the pawn. White keeps the pawn, and the extra knight wins.""",
          fen="8/8/6kp/8/3NK1P1/8/8/8 w - - 0 1", play="Kf4", tb="W"),
        S("""`h5` `g5`. The pawn steps past and stays on the board. This is winning.

When you are ahead, every pawn trade deserves a second look. When you are behind, pawn trades are your friend, and the last pawn is the one to hunt.""",
          play="h5 g5", tb="W"),
        S("""<b>King to the centre once the queens are off.</b> In the middlegame the king hides. In the endgame it is a strong piece, and the pawn lessons show why: the result usually depends on which king gets in front of which pawn first.

In your endgames without queens your king stands slightly further from the centre than your opponents' kings do. The difference is small. But the first two or three moves after the queens come off are the cheapest moment to fix it: if nothing is hanging and there is nothing to take, the king move towards the centre is rarely wrong."""),
    ]))
    return L


# ================================================================== rook method drills
def rook_drills():
    D = []
    lucena = [
        ("ER-lucena-g", "6K1/4k1P1/8/8/8/8/7r/5R2 w - - 0 1", ["Re1+", "Kd7", "Re4", "Rh1", "Kf7", "Rf1+", "Kg6", "Rg1+", "Kf6", "Rf1+", "Kg5", "Rg1+", "Rg4"]),
        ("ER-lucena-b", "1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1", ["Rd1+", "Ke7", "Rd4", "Ra1", "Kc7", "Rc1+", "Kb6", "Rb1+", "Kc6", "Rc1+", "Kb5", "Rb1+", "Rb4"]),
    ]
    for key, fen, line in lucena:
        D.append(build(key, "Build the bridge", "White to play and win", False, [
            Q("Their king is one file from your pawn. What first?", line[0],
              "The check drives their king a file further away.", fen=fen,
              hint="a rook check"),
            Q("Now the key move of the whole method.", line[2],
              "Rook to the fourth rank: the bridge.", play=line[1],
              hint="the rook goes to the fourth rank"),
            Q("They wait. Your king has to come out.", line[4],
              "Out from in front of the pawn. The checks start now, and the king walks towards them.", play=line[3]),
            S("The king walks down the board towards the rook, check by check.", play=" ".join(line[5:12])),
            Q("One more check to deal with. Finish the method.", line[12],
              "The rook blocks. There are no more checks and the pawn queens."),
        ]))
    # Philidor, as Black and (mirrored) as White
    ph = "4k3/R7/8/3KP3/8/8/8/1r6 b - - 0 1"
    D.append(build("ER-philidor-b", "Hold the draw", "Black to play and draw", True, [
        Q("You are a pawn down with your king on the queening square. Where does the rook go?", "Rb6",
          "The third-rank defence. Their king cannot step forward.", fen=ph, hint="your third rank, which is the sixth for Black"),
        Q("They pushed the pawn. That is the signal. Where does the rook go now?", "Rb1",
          "To the far end. Their king has lost its shelter on e6.", play="e6", hint="as far away as possible"),
        Q("Their king comes forward, threatening mate. Your move.", "Rd1+",
          "Check from behind.", play="Kd6"),
        Q("And again.", "Re1+", "The checks do not run out. Draw.", play="Ke5"),
    ]))
    mb = chess.Board(ph).mirror()         # colours swapped, board flipped: White defends
    def msan(b, san):
        return san
    D.append(build("ER-philidor-w", "Hold the draw", "White to play and draw", False, [
        Q("You are a pawn down with your king on the queening square. Where does the rook go?", "Rb3",
          "The third-rank defence. Their king cannot step forward.", fen=mb.fen(), hint="your third rank"),
        Q("They pushed the pawn. That is the signal. Where does the rook go now?", "Rb8",
          "To the far end. Their king has lost its shelter on e3.", play="e3", hint="as far away as possible"),
        Q("Their king comes forward, threatening mate. Your move.", "Rd8+",
          "Check from behind.", play="Kd3"),
        Q("And again.", "Re8+", "The checks do not run out. Draw.", play="Ke4"),
    ]))
    # push or king
    D.append(build("ER-kingfirst", "Push or king?", "White to play and win", False, [
        Q("A pawn up. One move wins here, and the natural-looking one draws.", "Ke6",
          "King first. It keeps its shelter in front of the pawn and threatens `Ra8+`. The pawn follows behind the king.",
          fen="4k3/R7/8/3KP3/8/8/8/5r2 w - - 0 1",
          bad={"e6": "`e6` takes away your own king's shelter. Their rook checks from behind for ever: draw."}),
    ]))
    # rook behind the pawn, both sides (unique tablebase solutions found by search)
    rb = [
        ("8/8/P4k2/8/5r2/8/8/3RK3 w - - 0 1", "Ra1", "win"),
        ("8/7k/P7/8/7r/4R3/8/3K4 b - - 0 1", "Ra4", "draw"),
        ("8/8/P5k1/3r4/8/8/5K2/2R5 w - - 0 1", "Ra1", "win"),
        ("6R1/8/P4k2/8/8/7r/3K4/8 b - - 0 1", "Ra3", "draw"),
        ("8/6k1/r7/8/P7/3K4/5R2/8 w - - 0 1", "Ra2", "win"),
        ("7R/8/1P4k1/8/8/8/r7/3K4 b - - 0 1", "Rb2", "draw"),
        ("8/3k4/3r3P/8/8/8/4KR2/8 w - - 0 1", "Rh2", "win"),
        ("8/k7/8/8/2R4P/2K5/5r2/8 b - - 0 1", "Rh2", "draw"),
    ]
    for i, (fen, san, goal) in enumerate(rb):
        white = fen.split()[1] == "w"
        own = goal == "win"
        D.append(build("ER-behind-%d" % (i + 1), "Where does the rook go?",
                       "%s to play and %s" % ("White" if white else "Black", goal), not white, [
            Q("There is a passed pawn on the board. One move %s; every other move %s." % (
                "wins" if own else "draws", "lets it slip" if own else "loses"), san,
              "Behind the pawn. %s" % ("From there the rook supports it all the way up the board." if own else
                                      "From there the rook attacks it all the way up the board, and their rook is tied to it."),
              fen=fen, hint="rooks belong behind passed pawns"),
        ]))
    # trade the last pawn
    D.append(build("ER-tradepawn", "A knight down", "Black to play and draw", True, [
        Q("You are a whole knight down. Find the idea that draws.", "h5",
          "Trade the last pair of pawns. King and knight cannot win against a bare king.",
          fen="8/8/6kp/8/3NK1P1/8/8/8 b - - 0 1", hint="when you are behind, trade pawns",
          also=None),
    ]))
    D.append(build("ER-keeppawn", "A knight up", "White to play and win", False, [
        Q("You are a knight up, and they are about to play h5 and trade the last pawns. Stop it with the king.", "Kf4",
          "Now h5 is answered by g5, and the pawn stays on the board.",
          fen="8/8/6kp/8/3NK1P1/8/8/8 w - - 0 1", hint="you want to answer h5 with g5"),
    ]))
    return D


# ================================================================== generated: square
def square_cards():
    rnd = random.Random(101)
    out, seen = [], set()
    want = {("w", True): 4, ("w", False): 4, ("b", True): 4, ("b", False): 4}
    tries = 0
    while sum(want.values()) > 0 and tries < 4000:
        tries += 1
        pf = rnd.randrange(8)
        pr = rnd.choice([2, 3, 4, 5])                 # rank number
        eff = 3 if pr == 2 else pr
        n = 8 - eff
        promo = chess.square(pf, 7)
        psq = chess.square(pf, pr - 1)
        bk = rnd.randrange(64)
        stm = rnd.choice("wb")
        d = chess.square_distance(bk, promo)
        if abs(d - (n if stm == "w" else n + 1)) > 1 or bk == psq:
            continue                                   # close calls only
        # white king far away, on the side away from the black king
        side = [f for f in range(8) if abs(f - pf) >= 4]
        if not side:
            continue
        wk = chess.square(rnd.choice(side), rnd.choice([0, 1]))
        b = chess.Board(None)
        b.set_piece_at(psq, chess.Piece(chess.PAWN, chess.WHITE))
        b.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
        b.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
        b.turn = stm == "w"
        if not b.is_valid() or b.is_check():
            continue
        if chess.square_distance(bk, psq) <= 1 and stm == "b":
            continue                                   # can just take it
        if chess.square_rank(bk) < pr - 1:
            continue                                   # king behind the pawn: not the textbook picture
        caught_rule = d <= (n if stm == "w" else n + 1)
        if want[(stm, caught_rule)] <= 0:
            continue
        k = b.board_fen() + stm
        if k in seen:
            continue
        res = tbprobe.result_white(b.fen())
        if (res == "D") != caught_rule or res == "B":
            continue                                   # the plain rule does not decide this one
        seen.add(k)
        want[(stm, caught_rule)] -= 1
        # square corners, towards the king
        direction = 1 if chess.square_file(bk) >= pf else -1
        f2 = pf + direction * n
        if not (0 <= f2 <= 7):
            direction = -direction
            f2 = pf + direction * n
        corners = [chess.square(pf, eff - 1), chess.square(f2, eff - 1), chess.square(f2, 7), promo]
        cs = [SQ(c) for c in corners]
        marks = " ".join("%s:y" % c for c in cs)
        arrows = " ".join("%s%s:y" % (cs[i], cs[(i + 1) % 4]) for i in range(4))
        inside = d <= n
        where = "inside" if inside else "outside"
        lead = "The square runs %s, %s, %s, %s%s. " % (cs[0], cs[1], cs[2], cs[3],
                                                         " (the pawn is on its starting square, so the square is drawn from the third rank)" if pr == 2 else "")
        if stm == "w":
            ex = lead + "The king on %s is %s it, and it is White's move. %s" % (
                SQ(bk), where, "The king keeps pace and takes the pawn." if caught_rule else "The pawn runs and the king is a step short.")
        else:
            ex = lead + "The king on %s is %s it, and it is Black's move. %s" % (
                SQ(bk), where, ("It is already in the square and stays in it." if inside else "It steps into the square and catches the pawn.")
                if caught_rule else "Even with the move it cannot get into the square. The pawn queens.")
        out.append(build("EQ-%s-%s" % (b.board_fen().replace("/", ""), stm), "Does the pawn queen?",
                         "%s to move" % ("White" if stm == "w" else "Black"), False, [
            C("%s to move. Does the pawn get through?" % ("White" if stm == "w" else "Black"),
              ["It queens", "The king catches it"], 1 if caught_rule else 0, ex, fen=b.fen(),
              rmarks=marks, rarrows=arrows),
        ]))
    random.Random(102).shuffle(out)
    return out


# ================================================================== generated: K+P only moves
def kpk_tags(b, m):
    """Plain-language reason for a king-and-pawn only move, from the geometry."""
    a = after(b, m)
    me = b.turn
    mk, ok = a.king(me), a.king(not me)
    pawn = list(a.pieces(chess.PAWN, chess.WHITE))[0]
    pf, pr = chess.square_file(pawn), chess.square_rank(pawn)
    tags = []
    df, dr = abs(chess.square_file(mk) - chess.square_file(ok)), abs(chess.square_rank(mk) - chess.square_rank(ok))
    if (df == 0 and dr == 2) or (dr == 0 and df == 2):
        tags.append("It takes the opposition: the kings face each other and the other side has to give way.")
    if me == chess.WHITE:
        if b.piece_type_at(m.from_square) == chess.KING:
            kf, kr = chess.square_file(mk), chess.square_rank(mk)
            if pr <= 3 and kr == pr + 2 and abs(kf - pf) <= 1:
                tags.append("The king lands on a key square, two ranks in front of the pawn.")
            elif kr > pr and abs(kf - pf) <= 1:
                tags.append("The king goes in front of its pawn.")
        else:
            tags.append("Here the pawn move is right: the king has already done its work, or the pawn move keeps the opposition.")
    else:
        kf, kr = chess.square_file(mk), chess.square_rank(mk)
        if kf == pf and kr > pr:
            tags.append("The king stays on the pawn's file, in front of it.")
    if not tags:
        tags.append("It is the only move. Play through the line below to see why.")
    return " ".join(tags[:2])


def tb_line(fen, n=8):
    b = chess.Board(fen)
    sans = []
    for _ in range(n):
        if b.is_game_over():
            break
        p = tbprobe.probe(b.fen())
        if not p["order"]:
            break
        m = chess.Move.from_uci(p["order"][0])
        sans.append(b.san(m))
        b.push(m)
    return sans, b


def kpk_cards():
    rnd = random.Random(201)
    win, draw, seen = [], [], set()
    tries = 0
    while (len(win) < SIZES["kpk_win"] or len(draw) < SIZES["kpk_draw"]) and tries < 6000:
        tries += 1
        pf = rnd.choice([1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6, 0, 7])
        pr = rnd.choice([1, 2, 3, 4, 5])               # 0-based rank 2..6
        psq = chess.square(pf, pr)
        wk = chess.square(min(7, max(0, pf + rnd.randint(-2, 2))), min(7, max(0, pr + rnd.randint(-2, 2))))
        bk = chess.square(min(7, max(0, pf + rnd.randint(-2, 2))), min(7, max(0, pr + rnd.randint(1, 3))))
        if len({psq, wk, bk}) < 3:
            continue
        stm = rnd.choice([True, False])
        b = chess.Board(None)
        b.set_piece_at(psq, chess.Piece(chess.PAWN, chess.WHITE))
        b.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
        b.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
        b.turn = stm
        if not b.is_valid() or b.is_check():
            continue
        k = b.board_fen() + ("w" if stm else "b")
        if k in seen:
            continue
        seen.add(k)
        if stm and len(win) >= SIZES["kpk_win"]:
            continue
        if not stm and len(draw) >= SIZES["kpk_draw"]:
            continue
        # skip the trivial: pawn simply en prise, or simply takeable
        if stm and b.is_attacked_by(chess.BLACK, psq) and not b.is_attacked_by(chess.WHITE, psq):
            continue
        if not stm and b.is_attacked_by(chess.BLACK, psq) and not b.is_attacked_by(chess.WHITE, psq):
            continue
        p = tbprobe.probe(b.fen())
        goal = p["category"]
        if (stm and goal != "win") or (not stm and goal != "draw"):
            continue
        g, keep, others = tbprobe.keeping_moves(b.fen())
        if len(keep) != 1 or len(others) < 2:
            continue
        u = list(keep)[0]
        m = chess.Move.from_uci(u)
        san = b.san(m)
        if "=" in san:
            continue
        note = kpk_tags(b, m)
        sans, endb = tb_line(after(b, m).fen(), 7)
        line = number_line(b, [san] + sans)
        items = [
            Q("%s to play and %s. Only one move does it." % ("White" if stm else "Black", "win" if stm else "draw"),
              san, note, fen=b.fen(), strict=True),
            S("With best play from both sides it goes on: <span class=\"mv\">%s</span>%s" % (
                line, "." if not endb.is_stalemate() else ", stalemate."), play=" ".join(sans)),
        ]
        card = build("EK-%s-%s" % (b.board_fen().replace("/", ""), "w" if stm else "b"),
                     "Win it" if stm else "Hold it", "%s to move" % ("White" if stm else "Black"), not stm, items)
        (win if stm else draw).append(card)
    out = win + draw
    random.Random(202).shuffle(out)
    return out


# ================================================================== own games: endgame scan
NPV = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def npm(b):
    return sum(v * len(b.pieces(pt, c)) for pt, v in NPV.items() for c in (True, False))


def is_endgame(b):
    n = npm(b)
    queens = len(b.pieces(chess.QUEEN, True)) + len(b.pieces(chess.QUEEN, False))
    return b.fullmove_number >= 13 and (n <= 26 or (queens == 0 and n <= 32))


def eg_type(b):
    q = bool(b.pieces(chess.QUEEN, True) or b.pieces(chess.QUEEN, False))
    r = bool(b.pieces(chess.ROOK, True) or b.pieces(chess.ROOK, False))
    mn = bool(b.pieces(chess.KNIGHT, True) or b.pieces(chess.KNIGHT, False) or
              b.pieces(chess.BISHOP, True) or b.pieces(chess.BISHOP, False))
    if not (q or r or mn):
        return "pawn ending"
    if q:
        return "queen ending" if not (r or mn) else "queens and pieces"
    if r and not mn:
        return "rook ending"
    if mn and not r:
        return "minor-piece ending"
    return "rooks and minor pieces"


def passed_pawns(b, color):
    out = []
    for sq in b.pieces(chess.PAWN, color):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        ahead = range(r + 1, 8) if color else range(0, r)
        blocked = False
        for ff in (f - 1, f, f + 1):
            if not 0 <= ff <= 7:
                continue
            for rr in ahead:
                p = b.piece_at(chess.square(ff, rr))
                if p and p.piece_type == chess.PAWN and p.color != color:
                    blocked = True
        if not blocked:
            out.append(sq)
    return out


CNT = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight"]


def material_words(b, color):
    parts = []
    for pt, nm in ((chess.QUEEN, "queen"), (chess.ROOK, "rook"), (chess.BISHOP, "bishop"), (chess.KNIGHT, "knight")):
        n = len(b.pieces(pt, color))
        if n == 1:
            parts.append(nm)
        elif n > 1:
            parts.append("%s %ss" % (CNT[n], nm))
    n = len(b.pieces(chess.PAWN, color))
    parts.append("%s pawn%s" % (CNT[n], "" if n == 1 else "s"))
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return parts[0]


def replay(g):
    b = chess.Board()
    for ply, u in enumerate(g["moves"]):
        yield ply, b, chess.Move.from_uci(u)
        b.push(chess.Move.from_uci(u))


def how_ended(g):
    r = {1.0: "you won", 0.5: "it was drawn", 0.0: "you lost"}[g["score"]]
    if "Time" in g["termination"] and g["score"] == 0.0:
        r = "you lost on time"
    return r


# ------------------------------------------------------------------ K: conversion play-outs
def playout_cards(games, eng16):
    drilled = studylib.drilled_gids()
    cands = {"k1": [], "k2": []}
    for g in games:
        if g["score"] == 1.0 or g["gid"] in drilled:
            continue
        me = g["me"]
        seen_types, got = set(), {}
        for ply, b, m in replay(g):
            if b.turn != me or ply < 2 or ply + 2 >= len(g["moves"]):
                continue
            if not is_endgame(b):
                continue
            t = eg_type(b)
            if t in seen_types:
                continue                      # first position of each ending type, on my move
            seen_types.add(t)
            ev = studylib.my_pov(g["evals"][ply - 1], me)
            ev2 = studylib.my_pov(g["evals"][ply + 1], me)
            if ev is None or ev2 is None:
                continue
            deck = "k1" if 100 <= ev <= 300 else ("k2" if 300 < ev <= 600 else None)
            if deck and abs(ev2 - ev) <= 150 and not b.is_check() and chess.popcount(b.occupied) >= 5 \
                    and not scanlib.winning_captures(b) and not scanlib.winning_captures(scanlib.view(b, not me) or b):
                rank = {"rook ending": 0, "pawn ending": 1, "minor-piece ending": 2, "rooks and minor pieces": 3}.get(t, 4)
                if deck not in got or rank < got[deck][0]:
                    got[deck] = (rank, (g, ply, b.copy(stack=False), ev))
        for deck, (rank, c) in got.items():
            cands[deck].append(c)
    out = {}
    for deck, level in (("k1", 4), ("k2", 5)):
        rnd = random.Random(301 if deck == "k1" else 302)
        cs = cands[deck]
        cs.sort(key=lambda x: (x[0]["gid"], x[1]))
        rnd.shuffle(cs)
        # rook endings and passed-pawn positions first (plateau note, addendum)
        def pri(x):
            b, me = x[2], x[0]["me"]
            t = eg_type(b)
            return (0 if t == "rook ending" else 1 if t == "rooks and minor pieces" else 2 if t == "pawn ending" else 3,
                    0 if passed_pawns(b, me) else 1)
        cs.sort(key=pri)
        quota = {"rook ending": 16, "rooks and minor pieces": 12, "pawn ending": 5, "minor-piece ending": 5,
                 "queen ending": 1, "queens and pieces": 1}
        cards = []
        for g, ply, b, ev in cs:
            if len(cards) >= SIZES[deck]:
                break
            t = eg_type(b)
            if quota.get(t, 0) <= 0:
                continue
            # refuse positions whose stored eval a deeper search contradicts, and forced mates
            top = eng16.best(b.fen(), 1, depth=18)[0]
            cp = top[1] if g["me"] else -top[1]
            lo, hi = (60, 380) if deck == "k1" else (250, 800)
            if not (lo <= cp <= hi):
                continue
            quota[t] -= 1
            me = g["me"]
            pp = passed_pawns(b, me)
            fenq = urllib.parse.quote(b.fen())
            text = "<p><b>You:</b> %s. <b>They:</b> %s. It is your move.</p>" % (material_words(b, me), material_words(b, not me))
            text += "<p>In the game %s. Play it out against the computer until it is won.</p>" % how_ended(g)
            text += "<p class=\"dim\">On the Lichess screen choose <b>%s</b>, strength <b>%d</b>, Unlimited. Lichess starts on Random side and whatever strength you used last, so set both each time. Raise the strength a level when you have won three in a row.</p>" % (
                "White" if g["me"] else "Black", level)
            tag = t + (", you have a passed pawn" if pp else "")
            cards.append({"k": "%s-%s-%d" % (deck.upper(), g["gid"], ply), "t": tag[0].upper() + tag[1:],
                          "sub": gsub(None, me, b.fullmove_number, "%s &middot; %s" % (fam(g["opening"]), g["date"][:4])),
                          "flip": not me, "links": [game_link(g["gid"], ply, me)],
                          "steps": [{"type": "playout", "fen": b.fen(), "text": text,
                                     "marks": [[SQ(s), "g"] for s in pp],
                                     "play": [["Play it against the computer", "https://lichess.org/?fen=%s#ai" % fenq],
                                              ["Open the board", "https://lichess.org/analysis/standard/%s?color=%s" % (
                                                  b.fen().replace(" ", "_"), "white" if me else "black")]]}]})
        out[deck] = cards
    return out


# ------------------------------------------------------------------ own passed-pawn errors
def own_cards(games, eng):
    """Close endgames, own passed pawn on the board, a big error at depth 12,
    re-judged by Stockfish 17.1 at depth 20. Engine-keyed; the card says so."""
    drilled = studylib.drilled_gids()
    cands = []
    for g in games:
        if g["gid"] in drilled or g["block"] not in ("2025q3", "2025q4", "2026", "pending", "2025q2"):
            continue
        me = g["me"]
        n_game = 0
        for ply, b, m in replay(g):
            if b.turn != me or ply < 2 or ply + 1 >= len(g["moves"]):
                continue
            ev_b = studylib.my_pov(g["evals"][ply - 1], me)
            ev_a = studylib.my_pov(g["evals"][ply], me)
            if ev_b is None or ev_a is None:
                continue
            if not is_endgame(b) or b.is_check():
                continue
            if not (-150 <= ev_b <= 400):
                continue
            if winprob(ev_b) - winprob(ev_a) < 0.15:
                continue
            pp = passed_pawns(b, me)
            if not pp:
                continue
            if chess.popcount(b.occupied) > 16:
                continue
            if n_game >= 1:
                break
            n_game += 1
            cands.append((g, ply, b.copy(stack=False), m, pp, ev_b, ev_a))
    rnd = random.Random(401)
    cands.sort(key=lambda x: (x[0]["gid"], x[1]))
    rnd.shuffle(cands)
    # passed pawn far advanced first, rook endings first
    cands.sort(key=lambda x: (0 if eg_type(x[2]) in ("rook ending", "pawn ending") else 1,
                              0 if any((chess.square_rank(s) if x[0]["me"] else 7 - chess.square_rank(s)) >= 4 for s in x[4]) else 1))
    cards, kinds = [], defaultdict(int)
    for g, ply, b, m, pp, ev_b, ev_a in cands:
        if len(cards) >= SIZES["own"]:
            break
        me = g["me"]
        tops = eng.best(b.fen(), 4)
        best_cp = tops[0][1] if me else -tops[0][1]
        played_cp, played_pv = eng.move_eval(b.fen(), m.uci())
        played_cp = played_cp if me else -played_cp
        if not (-120 <= best_cp <= 450):
            continue
        if best_cp - played_cp < 150:
            continue                                    # the deeper search does not confirm the error
        good = [t for t in tops if ((t[1] if me else -t[1]) >= best_cp - 50)]
        if len(good) > 2 or m.uci() in [t[0] for t in good]:
            continue
        second = [t for t in tops if t not in good]
        if second and best_cp - (second[0][1] if me else -second[0][1]) < 100:
            continue                                    # no clear gap below the accepted set
        bm = chess.Move.from_uci(good[0][0])
        pt = b.piece_type_at(bm.from_square)
        pushed = b.piece_type_at(m.from_square) == chess.PAWN and m.from_square in pp
        if pt == chess.KING:
            kind = "king"
            why = "The king move comes first. The pawn can wait a move; the king could not."
        elif pt == chess.ROOK:
            fpawn = {chess.square_file(s) for s in pp}
            kind = "rook"
            why = "The rook move comes first." + (" It goes to the passed pawn's file." if chess.square_file(bm.to_square) in fpawn else "")
        elif pt == chess.PAWN and bm.from_square in pp:
            kind = "push"
            why = "Here the push was right, and waiting was the error. The three questions answer yes: the pawn is safe where it lands and the square in front of it is yours."
        elif pt == chess.PAWN:
            kind = "pawn"
            why = "A pawn move elsewhere was needed first."
        else:
            kind = "piece"
            why = "The piece move comes first."
        if kinds[kind] >= (9 if kind in ("king", "rook") else 5):
            continue
        kinds[kind] += 1
        # lines
        pvb = chess.Board(b.fen())
        best_sans = []
        for u in good[0][2][:6]:
            mm = chess.Move.from_uci(u)
            if mm not in pvb.legal_moves:
                break
            best_sans.append(pvb.san(mm))
            pvb.push(mm)
        pb = chess.Board(b.fen())
        played_sans = []
        for u in played_pv[:6]:
            mm = chess.Move.from_uci(u)
            if mm not in pb.legal_moves:
                break
            played_sans.append(pb.san(mm))
            pb.push(mm)
        cost = winprob(best_cp) - winprob(played_cp)
        accept = {}
        for t in good:
            mm = chess.Move.from_uci(t[0])
            tb_, tsans = chess.Board(b.fen()), []
            for u in t[2][:6]:
                x = chess.Move.from_uci(u)
                if x not in tb_.legal_moves:
                    break
                tsans.append(tb_.san(x))
                tb_.push(x)
            accept[t[0]] = {"san": b.san(mm), "fen": after(b, mm).fen(),
                            "note": (why if t == good[0] else "The engine rates this as good as its first choice, %s." % mv(b.san(bm))) +
                            " A likely continuation: <span class=\"mv\">%s</span>." % number_line(b, tsans)}
        pp_txt = " and ".join(SQ(s) for s in pp)
        lead = "<p>Your game, %s. You have %s on %s.</p><p>You played %s here%s, and it cost about %d points of winning chance out of 100.</p>" % (
            eg_type(b), "a passed pawn" if len(pp) == 1 else "passed pawns", pp_txt, mv(b.san(m)), " (pushing it)" if pushed else "", round(cost * 100))
        st = {"type": "move", "fen": b.fen(), "last": g["moves"][ply - 1], "text": lead,
              "marks": [[SQ(s), "g"] for s in pp],
              "ask": "Find the better move. Ask the three questions first: is the pawn safe after it moves, who holds the square in front of it, can the king or rook step up instead?",
              "accept": accept, "main": good[0][0],
              "bad": {m.uci(): "That is the move you played. After it the engine expects <span class=\"mv\">%s</span>." % number_line(b, played_sans)},
              "wrong": "The engine does not rate that move within half a pawn of its best. Try again, or ask to be shown."}
        cards.append({"k": "EO-%s-%d" % (g["gid"], ply), "t": "Your passed pawns",
                      "sub": gsub(None, me, b.fullmove_number, "%s &middot; %s" % (fam(g["opening"]), g["date"][:4])),
                      "flip": not me, "links": [game_link(g["gid"], ply, me)], "steps": [st]})
    random.Random(402).shuffle(cards)
    return cards, dict(kinds)


def main():
    games = studylib.load()
    eng = enginecheck.Engine(depth=20)
    out = {}
    try:
        out["eg_lessons"] = write_deck({"id": "eg_lessons", "title": "Endgame lessons", "cards": lessons()})
        out["eg_rook"] = write_deck({"id": "eg_rook", "title": "Rook-ending methods", "cards": rook_drills()})
        out["eg_square"] = write_deck({"id": "eg_square", "title": "The square of the pawn", "cards": square_cards()})
        out["eg_kpk"] = write_deck({"id": "eg_kpk", "title": "King and pawn: the only move", "cards": kpk_cards()})
        tbprobe.save()
        own, kinds = own_cards(games, eng)
        out["eg_own"] = write_deck({"id": "eg_own", "title": "Your passed pawns", "cards": own})
        print("own kinds:", kinds)
        k = playout_cards(games, eng)
        out["k1"] = write_deck({"id": "k1", "title": "K1 Small edge", "cards": k["k1"]})
        out["k2"] = write_deck({"id": "k2", "title": "K2 Should be over", "cards": k["k2"]})
        tbprobe.save_pruned()
    finally:
        tbprobe.save()
        eng.close()
    for k in out:
        print("%-10s %4d cards %7d bytes" % (k, len(out[k]["keys"]), out[k]["bytes"]))


if __name__ == "__main__":
    main()
