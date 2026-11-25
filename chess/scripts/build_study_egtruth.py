#!/usr/bin/env python3
"""build_study_egtruth — endgame truth-check decks for /chess-study (2026-11-25).

    python3 build_study_egtruth.py TB_ROWS.csv.gz ENG_ROWS.csv.gz

Inputs are the per-ply tables written by chess/scripts/egtruth/analyze.py
(run extract.py -> tb.py -> engine.py -> analyze.py first; see
notes/2026-11-25-endgame-truth-and-time.md). Decks:

  eg_tb   "Win it or hold it": his own <= 7-man positions where he let a
          tablebase win go or lost a tablebase draw, and only one to three
          moves kept the result. Key is exact (Lichess 7-man tablebase).
  eg_om   "One move or many?": his own close > 7-man endgame positions.
          Half are only-move positions he missed; half are positions where
          lots of moves were fine and he spent 10s+ anyway. Engine-keyed
          (Stockfish 17.1, depth 18, MultiPV 5); the cards say so.
  eg_tm   lesson cards: what the truth check and the time map found.

Own caches, so the shared caches pruned by build_study_endgames.py are not
touched: chess/study/tb_cache_egtruth.json, chess/study/engine_cache_egtruth.json.
A rebuild with both caches present needs no network and no engine.
"""
import os, sys, json, math, random
import pandas as pd
import chess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tbprobe, enginecheck
tbprobe.CACHE = os.path.join(HERE, "..", "study", "tb_cache_egtruth.json")
enginecheck.CACHE = os.path.join(HERE, "..", "study", "engine_cache_egtruth.json")
from studycards import write_deck, after, gsub, game_link, mv
from studyauthor import number_line

NORM = {"win": "win", "cursed-win": "draw", "draw": "draw", "blessed-loss": "draw", "loss": "loss",
        "maybe-win": "win", "maybe-loss": "loss"}
RES = {"win": "a win", "draw": "a draw", "loss": "lost"}
SIZES = {"tb_win": 16, "tb_draw": 14, "om_only": 15, "om_lots": 15}
ERA_YEAR = {"2024h2": "2024", "2025q1": "2025", "2025q2": "2025", "2025q3": "2025", "2025q4": "2025",
            "2026": "2026", "pending": "2026", "2026_fblock": "2026"}


def wp(cp):
    if cp >= 10000:
        return 1.0
    if cp <= -10000:
        return 0.0
    cp = max(-1000, min(1000, cp))
    return 1 / (1 + math.exp(-0.00368208 * cp))


def mover_result(p, uci):
    """Result for the side that plays `uci`, after it."""
    return NORM.get(tbprobe.FLIP.get(p["moves"][uci]["category"], ""), None)


def ended(score):
    return {1.0: "you won the game", 0.5: "the game was drawn", 0.0: "you lost the game"}[score]


def tb_line(fen, n=8):
    b = chess.Board(fen)
    sans = []
    for _ in range(n):
        if b.is_game_over() or chess.popcount(b.occupied) > 7:
            break
        p = tbprobe.probe(b.fen())
        if not p["order"]:
            break
        m = chess.Move.from_uci(p["order"][0])
        sans.append(b.san(m))
        b.push(m)
    return sans


# ------------------------------------------------------------------ eg_tb
def tb_cards(path):
    t = pd.read_csv(path)
    t = t[(t.mine == 1) & (t.tberr == 1) & (t.keep.between(1, 3)) & t.tb_before.isin(["win", "draw"])]
    t = t.sort_values(["gid", "ply"]).groupby("gid").head(1)
    rnd = random.Random(501)
    rows = list(t.itertuples())
    rnd.shuffle(rows)
    rows.sort(key=lambda r: 0 if r.era == "treat" else 1)          # recent games first
    out = {"win": [], "draw": []}
    for r in rows:
        goal = r.tb_before
        if len(out[goal]) >= SIZES["tb_" + goal]:
            continue
        b = chess.Board(r.fen)
        if b.is_game_over():
            continue
        p = tbprobe.probe(r.fen)
        if NORM.get(p["category"]) != goal or r.uci not in p["moves"]:
            continue                                  # cache disagrees with the analysis table: skip
        keep = [u for u in p["order"] if mover_result(p, u) == goal]
        if not 1 <= len(keep) <= 3 or r.uci in keep:
            continue
        me = b.turn
        accept, bad = {}, {}
        for u in keep:
            m = chess.Move.from_uci(u)
            accept[u] = {"san": b.san(m), "fen": after(b, m).fen(),
                         "note": "That keeps %s." % ("the win" if goal == "win" else "the draw")}
        played_res = mover_result(p, r.uci)
        bad[r.uci] = "%s is what you played in the game. After it the position is %s with best play." % (
            mv(b.san(chess.Move.from_uci(r.uci))), RES[played_res])
        n = len(keep)
        ask = "%s to move. This position is %s, and %s keep%s it. Find %s." % (
            "White" if me else "Black", "winning" if goal == "win" else "a draw",
            "only one move" if n == 1 else "only %s moves" % ["", "", "two", "three"][n], "s" if n == 1 else "",
            "it" if n == 1 else "one")
        main = keep[0]
        line = tb_line(after(b, chess.Move.from_uci(main)).fen())
        lb = after(b, chess.Move.from_uci(main))
        st1 = {"type": "move", "fen": r.fen, "ask": ask, "accept": accept, "main": main, "bad": bad,
               "wrong": "That lets it go: with best play it is no longer %s. Try again, or ask to be shown." % (
                   "a win" if goal == "win" else "a draw"),
               "text": "<p>From your game: %s. %s, and %s.</p>" % (
                   r.etype, "You played %s here" % mv(b.san(chess.Move.from_uci(r.uci))), ended(r.score))}
        steps = [st1]
        if line:
            end = lb.copy()
            for s in line:
                end.push_san(s)
            steps.append({"type": "show", "fen": end.fen(),
                          "text": "<p>Tablebase line (perfect play from both sides): <span class=\"mv\">%s</span>.</p>" %
                                  number_line(b, [b.san(chess.Move.from_uci(main))] + line)})
        out[goal].append({"k": "TB-%s-%d" % (r.gid, r.ply), "t": "Win it" if goal == "win" else "Hold it",
                          "sub": gsub(None, me, b.fullmove_number, "%s &middot; %s" % (r.etype, ERA_YEAR.get(r.block, ""))),
                          "flip": not me, "links": [game_link(r.gid, r.ply, me)], "steps": steps})
        tbprobe.save()
    cards = out["win"] + out["draw"]
    random.Random(502).shuffle(cards)
    return cards, {k: len(v) for k, v in out.items()}


def pvline(b, ucis, n=6):
    x, sans = b.copy(stack=False), []
    for u in ucis[:n]:
        m = chess.Move.from_uci(u)
        if m not in x.legal_moves:
            break
        sans.append(x.san(m))
        x.push(m)
    return number_line(b, sans)


# ------------------------------------------------------------------ eg_om
def om_cards(path, eng):
    c = pd.read_csv(path)
    c = c[c.mine == 1]
    c = c[c.spent.notna()]
    only = c[(c.good == 1) & (c.deeperr == 1) & (c.gap >= 0.2)]
    lots = c[(c.good == 4) & (c.deeperr == 0) & (c.spent >= 10)]
    out = {"only": [], "lots": []}
    for kind, s in (("only", only), ("lots", lots)):
        s = s.sort_values(["gid", "ply"]).groupby("gid").head(1)
        rows = list(s.itertuples())
        random.Random(511 if kind == "only" else 512).shuffle(rows)
        rows.sort(key=lambda r: 0 if r.era == "treat" else 1)
        for r in rows:
            if len(out[kind]) >= SIZES["om_" + kind]:
                break
            b = chess.Board(r.fen)
            if b.is_check():
                continue
            me = b.turn
            tops = eng.best(r.fen, 5, depth=18)
            mc = [(u, cp if me else -cp, pv) for u, cp, pv in tops]
            w = [wp(x[1]) for x in mc]
            if not 0.2 <= w[0] <= 0.85:
                continue
            played = r.uci
            pcp = eng.move_eval(r.fen, played, depth=18)[0]
            pw = wp(pcp if me else -pcp)
            if kind == "only":
                if len(w) < 2 or w[0] - w[1] < 0.15 or mc[0][0] == played or w[0] - pw < 0.15:
                    continue
                good = [mc[0]]
            else:
                good = [x for x, ww in zip(mc, w) if w[0] - ww <= 0.06]
                if len(good) < 4 or w[0] - pw > 0.08:
                    continue
            accept = {}
            for u, cp, pv in good:
                m = chess.Move.from_uci(u)
                accept[u] = {"san": b.san(m), "fen": after(b, m).fen()}
            psan = b.san(chess.Move.from_uci(played))
            gsans = ", ".join(mv(b.san(chess.Move.from_uci(x[0]))) for x in good)
            if kind == "only":
                cost = round(100 * (w[0] - w[1]))
                bsan = b.san(chess.Move.from_uci(mc[0][0]))
                ssan = b.san(chess.Move.from_uci(mc[1][0]))
                sec = "%d second%s" % (r.spent, "" if r.spent == 1 else "s")
                if mc[1][0] == played:
                    game = "In the game you played %s, the second choice, after %s." % (mv(psan), sec)
                else:
                    game = "In the game you spent %s and played %s." % (sec, mv(psan))
                explain = ("One move matters. %s keeps the game; the engine's next choice, %s, already costs about %d "
                           "points of winning chance out of 100. %s A likely continuation after %s: "
                           "<span class=\"mv\">%s</span>." % (mv(bsan), mv(ssan), cost, game, mv(bsan), pvline(b, mc[0][2])))
                ask2 = "Now find the move."
                bad = {played: "%s is what you played in the game. It costs about %d points of winning chance out of 100." % (
                    mv(psan), round(100 * (w[0] - pw)))}
                wrong = "Not that one. Only one move keeps the game here. Try again, or ask to be shown."
                title = "One move matters"
            else:
                explain = ("Lots of moves are fine: %s all keep the game within a few points of the engine's best. "
                           "In the game you spent %d seconds here. This is where to save clock: pick a sensible move and go." % (
                               gsans, r.spent))
                ask2 = "Play a good move, fast. Any of them counts."
                bad = {}
                wrong = "Not one of the engine's good options here. Try another, or ask to be shown."
                title = "Lots of moves are fine"
            steps = [
                {"type": "choice", "fen": r.fen,
                 "ask": "%s to move. Before choosing a move: does one move matter here, or will lots of moves do?" % (
                     "White" if me else "Black"),
                 "options": ["One move matters", "Lots of moves are fine"], "answer": 0 if kind == "only" else 1,
                 "explain": explain},
                {"type": "move", "fen": r.fen, "ask": ask2, "accept": accept, "main": good[0][0], "bad": bad,
                 "wrong": wrong,
                 "text": "<p class=\"dim\">Judged by Stockfish 17.1 at depth 18, not a tablebase.</p>"},
            ]
            out[kind].append({"k": "OM-%s-%d" % (r.gid, r.ply), "t": title,
                              "sub": gsub(None, me, b.fullmove_number, "%s &middot; %s" % (r.etype, ERA_YEAR.get(r.block, ""))),
                              "flip": not me, "links": [game_link(r.gid, r.ply, me)], "steps": steps,
                              "_kind": kind})
            eng.save()
    cards = out["only"] + out["lots"]
    random.Random(513).shuffle(cards)
    # the title gives the answer away; use a neutral title on the deck card
    for cd in cards:
        cd["t"] = "One move or many?"
    return cards, {k: len(v) for k, v in out.items()}


# ------------------------------------------------------------------ eg_tm
def P(*paras):
    return "".join("<p>%s</p>" % x for x in paras)


def tm_cards():
    """Lesson cards. Figures from notes/2026-11-25-endgame-truth-and-time.md."""
    L = []
    L.append({"k": "TM-what", "t": "What was checked", "steps": [{"type": "show", "text": P(
        "<b>Every endgame move</b>, yours and your opponents', from your Lichess 3+2 and 5+0 games from mid-2024 through the 900-game block.",
        "<b>Small endgames</b> (seven pieces or fewer, kings and pawns included) were checked against the endgame tablebase: a solved table, so &ldquo;winning&rdquo; and &ldquo;mistake&rdquo; there are facts. That was 18,209 moves from 857 games.",
        "<b>Bigger close endgames</b> (neither side clearly winning) were re-checked with a stronger engine search than the one used on your games so far, which also counted how many moves were fine in each position. That was 38,466 moves from 2,005 games. A sample was checked again deeper still: 90% of the mistakes held up, the same for you and your opponents.")}]})
    L.append({"k": "TM-small", "t": "Small endgames: you are as good as they are", "steps": [{"type": "show", "text": P(
        "<b>When the tablebase says you are winning</b>, you let the win slip on 4.2% of moves. Your opponents, in the same spot, 4.8%.",
        "<b>When it is a draw and a losing move exists</b>, you lose the draw on 9.1% of moves, they do on 10.0%.",
        "The first time you reach a tablebase win in a game you go on to win 77% of the time; your opponents 80%. That difference is small enough to be chance.",
        "<b>What it means:</b> king-and-pawn and simple rook endings are not where your endgame points go. The basic-technique drills are still worth a pass, but they are not the priority.")}]})
    L.append({"k": "TM-big", "t": "Bigger endgames: the gap is real", "steps": [{"type": "show", "text": P(
        "In close endgames with eight or more pieces, you make a big mistake (a drop of 15 or more points of winning chance out of 100) on <b>12.2%</b> of moves. Your opponents, in the same games, <b>10.3%</b>. The stronger engine agrees with the earlier finding, and it holds in the 900-game block too (11.4% against 9.5%).",
        "<b>Where it is widest:</b> rook endings (10.9% against 8.4%), bishop-and-knight endings (11.9% against 8.4%), pawn moves (13.5% against 10.7%), and any position with a passed pawn on the board, yours or theirs.",
        "So your endgame gap starts while there is still a fair amount of wood on the board, and it is mostly gone by the time things are simple.")}]})
    L.append({"k": "TM-time", "t": "Nobody spends more time when it matters", "steps": [{"type": "show", "text": P(
        "In one position in five, <b>only one move</b> keeps the game. In more than half, <b>lots of moves</b> are fine.",
        "You spend about the same time on both: a typical move takes 2 to 3 seconds either way. Your opponents do exactly the same. Neither of you notices the critical moments, and on only-move positions both of you go wrong about one time in five.",
        "Thinking longer in the game does not show up as fewer mistakes, but that is partly because the hard positions are the ones that get thought about. The useful habit is upstream of thinking: <b>noticing</b> that this is a one-move position.")}]})
    L.append({"k": "TM-easy", "t": "Half your extra mistakes come when lots of moves were fine", "steps": [{"type": "show", "text": P(
        "Compared with your opponents, about 435 extra mistakes over these games. About half of them, <b>225</b>, came in positions where four or more moves were fine.",
        "<b>Low clock makes it sharp:</b> with 20 seconds or less, in positions where lots of moves work, you go wrong on <b>11.0%</b> of moves; your opponents with the same clock, <b>5.4%</b>. With more time the gap shrinks to about a point and a half.",
        "About a quarter of these mistakes leave something capturable. Most are quieter: a king or pawn step that lets their pawn or rook in. More of yours are king and pawn moves than theirs.",
        "<b>What it means:</b> when the clock is short and nothing is going on, a quick <i>safe</i> move beats a quick <i>active</i> one. Before a king or pawn move, one look: what does it stop guarding?")}]})
    L.append({"k": "TM-do", "t": "What to practise", "steps": [{"type": "show", "text": P(
        "<b>One move or many?</b> Before each endgame move, a one-second sort: is something forcing going on (a check, a pawn race, a piece attacked, their passed pawn moving)? If yes, spend the time. If no, play a safe move and save the clock.",
        "<b>The decks:</b> &ldquo;One move or many?&rdquo; trains the sort on your own positions: half are only-move spots you missed, half are spots where you spent 10 seconds or more and anything sensible was fine. &ldquo;Win it or hold it&rdquo; is your own small endgames where one to three moves kept the result, checked against the tablebase.",
        "Then the passed-pawn deck and the rook-ending methods, because that is where the bigger-endgame gap is widest.")}]})
    return L


def main(tbrows, engrows):
    eng = enginecheck.Engine(depth=18)
    print("eg_tm", write_deck({"id": "eg_tm", "title": "What the endgame check found", "cards": tm_cards()})["bytes"])
    try:
        tb, ntb = tb_cards(tbrows)
        print("eg_tb", ntb, write_deck({"id": "eg_tb", "title": "Win it or hold it", "cards": tb})["bytes"])
        om, nom = om_cards(engrows, eng)
        print("eg_om", nom, write_deck({"id": "eg_om", "title": "One move or many?", "cards": om})["bytes"])
    finally:
        eng.close()
        tbprobe.save()


if __name__ == "__main__":
    main(*sys.argv[1:])
