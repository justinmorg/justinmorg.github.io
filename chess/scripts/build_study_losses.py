#!/usr/bin/env python3
"""build_study_losses — the "Where your games are lost" lesson deck for /chess-study.

    python3 build_study_losses.py

Reads chess/study/losses_examples.json (facts picked and engine-checked by
chess/scripts/visibility/select_examples.py: Stockfish 16, depth 18 for every
eval quoted, depth-14 self-play for the 15-move material lines) and writes
chess-study/data/losses.json. No engine or network needed here.

Every sentence about an example is computed from those facts; the builder
asserts the claims it makes (a capture really was a capture, material really
moved) and refuses to write a card that fails. The statistics in the bullet
introductions come from chess/notes/2026-11-25-material-segments-and-visibility.md.
"""
import os, sys, json
import chess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from studycards import write_deck, mv  # noqa: E402
from hanging import see  # noqa: E402

SRC = os.path.join(HERE, "..", "study", "losses_examples.json")
EX = json.load(open(SRC, encoding="utf-8"))
NUM = {1: "a", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
NAMES = ["queen", "rook", "bishop", "knight", "pawn"]


def P(*paras):
    return "".join("<p>%s</p>" % x for x in paras)


def clock(s):
    s = max(0, int(round(s)))
    return "%d:%02d" % (s // 60, s % 60)


def ev(cp):
    if cp >= 9000:
        return "a forced mate for you"
    if cp <= -9000:
        return "a forced mate against you"
    return "%+.1f" % (cp / 100.0)


def pct(x):
    return "%d%%" % round(100 * x)


def count_words(d):
    out = []
    for n in NAMES:
        k = d.get(n, 0)
        if k > 0:
            out.append("%s %s%s" % (NUM.get(k, str(k)), n, "s" if k > 1 else ""))
    return " and ".join(out) if len(out) <= 2 else ", ".join(out[:-1]) + " and " + out[-1]


def net_words(n):
    if n == 0:
        return "even"
    return "%s %d" % ("up" if n > 0 else "down", abs(n))


def material(f):
    mine, theirs = {}, {}
    for n in NAMES:
        d = f["my_pieces"][n] - f["their_pieces"][n]
        if d > 0:
            mine[n] = d
        elif d < 0:
            theirs[n] = -d
    net = f["pmat"]
    if not mine and not theirs:
        s = "material is even"
    elif mine and not theirs:
        s = "you're up %s" % count_words(mine)
    elif theirs and not mine:
        s = "you're down %s" % count_words(theirs)
    else:
        s = "you have %s against their %s, so %s on the count" % (count_words(mine), count_words(theirs), net_words(f["raw_mat"]))
    if f["raw_mat"] != net:
        s += " until you take back the piece they just captured; after that you're %s" % net_words(net)
    return s


def numbered(fen, sans, upto=None):
    b = chess.Board(fen)
    moves = []
    for s in sans[:upto]:
        m = b.parse_san(s)
        moves.append(m)
        b.push(m)
    return chess.Board(fen).variation_san(moves), b


def upto_recapture(fen, sans, n):
    """Show n plies, plus the next one if it takes straight back on the square of the last capture,
    so a line never stops in the middle of a trade that the count already assumes is finished."""
    b = chess.Board(fen)
    for x in sans[:n]:
        b.push_san(x)
    if n < len(sans) and b.move_stack and len(b.move_stack) == n:
        last = b.move_stack[-1]
        prev = b.copy(); prev.pop()
        nxt = b.parse_san(sans[n])
        if prev.is_capture(last) and nxt.to_square == last.to_square and b.is_capture(nxt):
            return n + 1
    return n


def link(f):
    url = "https://lichess.org/%s%s#%d" % (f["gid"], "" if f["white"] else "/black", f["ply"] - 1)
    return url


def header(f, n):
    who = "White" if f["white"] else "Black"
    end = {"resigned": "you resigned", "checkmated": "you were checkmated", "lost on time": "you lost on time"}[f["how"]]
    return P("<b>Game %d of 3.</b> Move %d, you're %s. Lost: %s on move %d. <a href=\"%s\" target=\"_blank\" rel=\"noopener\">Open it on Lichess</a> (opens just before the move)."
             % (n, f["fullmove"], who, end, f["last_fm"], link(f)),
             "<b>At the board:</b> %s. Clocks: you %s, them %s. Queens %s."
             % (material(f), clock(f["myclk"]), clock(f["opclk"]), "on" if f["queens_on"] else "off"))


def verdict(f):
    return P("They had just played %s. You played %s (black arrow). The engine's move was %s (blue arrow)."
             % (mv(f["last_san"]), mv(f["played_san"]), mv(f["best_san"])),
             "Engine: %s before your move, %s after it. Your expected result: %s, then %s."
             % (ev(f["cp_best"]), ev(f["cp_after"]), pct(f["E_before"]), pct(f["E_after"])))


def pre_step(f, n, extra=""):
    return {"type": "show", "fen": f["fen"], "last": f["last"], "flip": not f["white"],
            "arrows": [[f["played"], "k"], [f["best"], "g"]],
            "text": header(f, n) + verdict(f) + extra}


def real_note(f):
    """What the real opponent did next, in material terms."""
    if f.get("real_next_pmat") is None:
        return P("You resigned straight after this move.")
    took = f["real_next_pmat"] <= f["pmat"] - 2
    line, _ = numbered(f["fen_after"], f["real_next"], 3)
    if took:
        return P("In the game: %s. By your next turn you were %s, so this one announced itself." % (line, net_words(f["real_next_pmat"])))
    return P("In the game: %s. By your next turn material was still %s: nothing told you anything had happened." % (line, net_words(f["real_next_pmat"])))


def punish_step(f, extra=""):
    line, _ = numbered(f["fen_after"], f["reply_pv"], 4)
    return {"type": "show", "fen": f["fen_after"], "last": f["played"], "flip": not f["white"],
            "arrows": [[f["reply_pv_uci"][0], "r"]],
            "text": P("<b>The punishment the engine sees</b> (red arrow): %s" % line) + real_note(f) + extra}


def took_step(f):
    b = chess.Board(f["fen_after"])
    rep = chess.Move.from_uci(f["real_reply"])
    assert b.is_capture(rep), f["gid"]
    assert f["real_next_pmat"] <= f["pmat"] - 2, f["gid"]
    return {"type": "show", "fen": f["fen_real_next"], "last": f["real_reply"], "flip": not f["white"],
            "arrows": [[f["real_reply"], "r"]],
            "text": P("They replied %s (red arrow) and took it. At your next turn you were %s on the count, against %s before your move. No doubt about this one: it showed up the very next move."
                      % (mv(f["real_reply_san"]), net_words(f["real_next_pmat"]), net_words(f["pmat"])))}


def tier2_steps(f):
    h = f["hit"] + 1                       # my turns along the best line until the material is in
    line, b = numbered(f["fen"], f["best_line"], upto_recapture(f["fen"], f["best_line"], 2 * h))
    gain = f["traj_best"][h] - f["pmat"]
    assert min(f["traj_best"][h:]) - f["pmat"] >= 2, f["gid"]
    assert max(abs(t - f["pmat"]) for t in f["traj_played"]) < 2, f["gid"]
    first = chess.Move.from_uci(f["best"])
    pre = chess.Board(f["fen"])
    cap = pre.is_capture(first)
    lead = ("The engine's move was a capture you could make right away." if cap and h == 1 else
            "The win took %d moves to collect." % h)
    return {"type": "show", "fen": b.fen(), "flip": not f["white"],
            "text": P("<b>What was there.</b> %s The line: %s. After it you'd have been %s on the count, against %s before." % (lead, line, net_words(f["traj_best"][h]), net_words(f["pmat"])),
                      "What you played lost nothing you could count: on the engine's line after your move, material stays within a pawn of where it was. So nothing on the board told you a chance had gone.")}


def tier3_steps(f):
    j = f["hit"]
    line, b = numbered(f["fen_after"], f["played_line"], upto_recapture(f["fen_after"], f["played_line"], 2 * j + 1))
    after = f["traj_played"][j]
    assert after - f["pmat"] <= -2 and j >= 3 and max(f["traj_played"][j:]) - f["pmat"] <= -2, f["gid"]
    return {"type": "show", "fen": b.fen(), "flip": not f["white"],
            "text": P("<b>%s</b> The engine plays both sides on from your move: %s." % (
                          "Nothing goes at first." if min(f["traj_played"][:j]) - f["pmat"] >= 0 else "At first it costs a pawn at most.", line),
                      "Material only goes on your move %d after the mistake: from here you're %s on the count, against %s before it. A long way from the move that caused it."
                      % (j + 1, net_words(after), net_words(f["pmat"]))) + real_note(f)}


def tier4_steps(f):
    lo = min(f["traj_played"]) - f["pmat"]
    hi = max(f["traj_played"]) - f["pmat"]
    assert lo > -2 and hi < 2, f["gid"]
    line, _ = numbered(f["fen_after"], f["reply_pv"], 6)
    return {"type": "show", "fen": f["fen_after"], "last": f["played"], "flip": not f["white"],
            "arrows": [[f["reply_pv_uci"][0], "r"]],
            "text": P("<b>No material ever moves.</b> The engine played 15 moves on for both sides, once from your move and once from its own. Material stays within a pawn of even on both lines. Its reply here (red arrow): %s." % line,
                      "The %s pawns you lost on the engine's scale are all in where the pieces stand. I haven't tried to say why. That needs a person looking at the position, and a guess from me would be worth less than your own look."
                      % ("%.1f" % (f["cp_loss"] / 100.0))) + real_note(f)}


def grab_text(f):
    b = chess.Board(f["fen"])
    best = max([see(b, m) for m in b.legal_moves if b.is_capture(m)] + [0])
    assert best < 200, f["gid"]
    what = "none of your captures here wins material" if best <= 0 else "no capture here wins more than a pawn"
    return "But nothing was left hanging: %s. The position got better for you without anything you could count." % what


def gift_steps(f, n):
    b0 = chess.Board(f["fen_before_their_move"])
    assert b0.turn != (chess.WHITE if f["white"] else chess.BLACK)
    first = {"type": "show", "fen": f["fen"], "last": f["last"], "flip": not f["white"],
             "text": header(f, n) + P("<b>Their mistake.</b> They had just played %s. The engine had the game at %s for you before that move and %s after it. That's their mistake."
                                      % (mv(f["their_move_san"]), ev(f["cp_before_their_move"]), ev(f["cp_best"])),
                                      grab_text(f))}
    second = {"type": "show", "fen": f["fen"], "last": f["last"], "flip": not f["white"],
              "arrows": [[f["played"], "k"], [f["best"], "g"]],
              "text": P("<b>Your reply.</b> You played %s (black arrow). The engine's move was %s (blue arrow)." % (mv(f["played_san"]), mv(f["best_san"])),
                        "Engine: %s before your move, %s after it. Your expected result: %s, then %s. The gift was handed straight back."
                        % (ev(f["cp_best"]), ev(f["cp_after"]), pct(f["E_before"]), pct(f["E_after"])))}
    return [first, second]


def double_steps(f, n):
    g = f["second"]
    s1 = pre_step(f, n)
    s2 = {"type": "show", "fen": g["fen"], "last": g["last"], "flip": not g["white"],
          "arrows": [[g["played"], "k"], [g["best"], "g"]],
          "text": P("<b>One move later.</b> They played %s. You played %s (black arrow); the engine's move was %s (blue arrow)." % (mv(g["last_san"]), mv(g["played_san"]), mv(g["best_san"])),
                    "Engine: %s before, %s after. Your expected result: %s, then %s. Two mistakes in a row."
                    % (ev(g["cp_best"]), ev(g["cp_after"]), pct(g["E_before"]), pct(g["E_after"])))}
    return [s1, s2]


def examples(bul):
    fs = EX[bul]
    assert len(fs) == 3, (bul, len(fs))
    steps = []
    for n, f in enumerate(fs, 1):
        if bul in ("uppiece", "tier1"):
            steps += [pre_step(f, n), took_step(f)]
        elif bul == "tier2":
            steps += [pre_step(f, n), tier2_steps(f)]
        elif bul == "tier3":
            steps += [pre_step(f, n), tier3_steps(f)]
        elif bul == "tier4":
            steps += [pre_step(f, n), tier4_steps(f)]
        elif bul == "giftback":
            steps += gift_steps(f, n)
        elif bul == "double":
            steps += double_steps(f, n)
        else:
            steps += [pre_step(f, n), punish_step(f)]
    return steps, [["Game %d" % n, link(f)] for n, f in enumerate(fs, 1)]


def card(key, title, sub, intro, bul=None, outro=None):
    steps = [{"type": "show", "text": x} for x in intro]
    links = None
    if bul:
        ex, links = examples(bul)
        steps += ex
    if outro:
        steps.append({"type": "show", "text": outro})
    c = {"k": "M-" + key, "t": title, "sub": sub, "steps": steps}
    if links:
        c["links"] = links
    return c


CARDS = [
    card("how", "How this was measured", "read first",
         [P("<b>What this is.</b> Every move from 4,605 of your Lichess 3+2 games (2,225 of them losses), sorted by things you can see during a game: material, clocks, whether queens are on. Then every mistake placed on a scale from &ldquo;obvious next move&rdquo; to &ldquo;only an engine would know.&rdquo;"),
          P("<b>What counts as a mistake.</b> Your <b>expected result</b> is how often you score from a position, given the engine's evaluation and both clocks. The model behind it was fitted on your own games, so it knows your real conversion rate. A move is a mistake if it drops your expected result by 10 points or more, for example from 60% to 50%.",
            "Clocks matter here. With both players short of time, the same engine drop counts about 15&ndash;20% less, because a low clock makes any position less certain."),
          P("<b>Material</b> is what you would count at the board: pawn 1, knight or bishop 3, rook 5, queen 9. A trade that's half done counts as level: if they just took a piece you can take straight back, that piece is counted as back.",
            "<b>Engine numbers</b> are in pawns from your side: +1.0 means about a pawn better for you. Every engine number on these cards is a fresh Stockfish check at depth 18, deeper than the depth-12 numbers used to find the examples.",
            "<b>The examples</b> are three lost games per point, picked at random from the ones that fit and kept only if the deeper check agreed. Each has a Lichess link that opens just before the move.")]),

    card("up12", "Ahead by a pawn or two", "part 1 &middot; material",
         [P("<b>Being a pawn or two up is where you make mistakes most often.</b>",
            "In your lost games, up 1&ndash;2 pawns is 12.5% of your moves but 25% of the damage. You make a mistake about once every 5 moves there (21 per 100), against once every 8 when material is even (13 per 100). The average one costs 23 points of expected result.",
            "It's the state that feels safest, and it's the most mistake-dense one you have. These mistakes come in every kind: about a quarter lose material within three moves, and the rest don't show up as material straight away.")],
         "up12",
         P("<b>So what.</b> &ldquo;I'm a pawn up&rdquo; is a signal you can actually read during a game, and it's the moment your error rate is highest. That's the conversion problem from earlier work, now in terms you can see at the board.")),

    card("uppiece", "Up a piece: the biggest mistakes", "part 1 &middot; material",
         [P("<b>When you're up a piece or more, your mistakes are rarer but the largest of all.</b>",
            "In lost games, up a piece or more is 5% of your moves and 11% of the damage. The average mistake there costs 30 points, more than anywhere else.",
            "The typical one is handing material straight back. 37% of your mistakes made a piece up lose material within three moves, the highest share of any material state. In all three games below the opponent took it on the very next move.")],
         "uppiece"),

    card("even", "Even material: where the worst move happens", "part 1 &middot; material",
         [P("<b>Even material carries its fair share of the damage, and the single worst move most often.</b>",
            "Even material is 34% of moves in your lost games and 36% of the damage, about par. But take the one costliest move of each lost game: 41% of them were played at even material, and 33% at even material with queens on.",
            "In 72% of those, the engine called the position roughly level beforehand (your chances between 35% and 65%). The game was there to be played, and one move gave it away. The three games below are exactly that: the costliest move of each.")],
         "even"),

    card("queens", "Queens on", "part 1 &middot; queens",
         [P("<b>With queens on, you make mistakes almost twice as often.</b>",
            "In lost games, positions with both queens on are 57% of your moves but 72% of the damage: 14 mistakes per 100 moves against 8 with queens off. Three in four of the costliest moves of your lost games came with queens on.",
            "For the examples I picked games where the engine's punishment starts with their queen. That's the thing to see in each: what their queen can reach after your move.")],
         "queens"),

    card("clock", "The clock gap mostly doesn't matter", "part 1 &middot; clocks",
         [P("<b>Being ahead or behind on the clock barely changes how often you make mistakes.</b>",
            "Mistakes per 100 moves in lost games: 9.1 with you under 20 seconds, 10.9 when you're 30+ seconds behind, 11.6 when clocks are within 30 seconds, 13.7 when you're 30+ seconds ahead. If anything, more when ahead on time.",
            "Under 20 seconds you make fewer mistakes per move but bigger ones: 24.5 points on average, against about 21 otherwise. Part of &ldquo;fewer&rdquo; is the measure itself: it discounts mistakes when clocks are low.",
            "The examples are big mistakes under 20 seconds, from positions the engine liked for you. They're real, but they're not where most of your losses come from.")],
         "lowclock"),

    card("down", "Down a piece: little left to lose", "part 1 &middot; material",
         [P("<b>Your mistakes when a piece or more down barely register, and that isn't good defence.</b>",
            "In lost games, down a piece or more is 26.5% of your moves but only 5.7% of the damage (2.6 mistakes per 100 moves).",
            "By then your expected result is already close to zero, so a further mistake has little left to take away. That's why there are no examples here: this point is about the measure, not about a kind of mistake.")]),

    card("tier1", "Seen at once: material gone within 3 moves", "part 2 &middot; how visible",
         [P("<b>These are the mistakes you'd know about straight away, and they do the most damage.</b>",
            "To place each mistake on the scale, I had the engine play the game on 15 moves from your move and from its own best move, and compared the material.",
            "In 24% of your mistakes you lose material or get mated within three moves. They are 41% of the damage in your lost games and the biggest per mistake (29 points). When the material could be taken on the very next move, real opponents took it 71% of the time.",
            "These are the hangs the two looks are aimed at. In the three games below, the opponent took it on the next move.")],
         "tier1"),

    card("tier2", "Missed a quick win", "part 2 &middot; how visible",
         [P("<b>12% of your mistakes are chances you didn't take, and these never feel like mistakes.</b>",
            "The opponent left something you could have won within three moves, and you played something else. You lost nothing you could count, so nothing bad happens on the board. They are 11% of the damage in your lost games.",
            "Catching these means asking the mirror image of Look 1: not &ldquo;what can they take?&rdquo; but &ldquo;what did their move leave that I can take?&rdquo;")],
         "tier2"),

    card("tier3", "Material goes 4&ndash;15 moves later", "part 2 &middot; how visible",
         [P("<b>A third of your mistakes only cost material much later, and most of that third is really positional.</b>",
            "In 33% of your mistakes, the engine's line wins material from you only 4 to 15 moves on. A caution before reading too much into that: when I ran the same test on good moves, 20% landed here too. Engine lines that long drift.",
            "So read this group as mostly positional, with some real delayed tactics mixed in. The three below are the real kind: in each, the loss holds up when the engine plays the line out.")],
         "tier3"),

    card("tier4", "Nothing is ever taken", "part 2 &middot; how visible",
         [P("<b>31% of your mistakes never cost material within 15 moves. The position just gets worse.</b>",
            "They are 22% of the damage in your lost games. With the 4&ndash;15-move group, which is mostly the same thing, this is the part of your mistakes that no check for hanging pieces will ever reach.",
            "Altogether, about two-thirds of your mistakes, and a bit over half of the damage, give no material signal for at least three moves.")],
         "tier4"),

    card("gift", "After their mistake, when nothing can be taken", "part 3 &middot; after a mistake",
         [P("<b>Your hunch was right: when the opponent's mistake leaves nothing to grab, you often don't notice it happened.</b>",
            "After an opponent's mistake that leaves material you can win, you give much of the advantage back 18% of the time. After one that leaves nothing you can take, 35% of the time. On an ordinary move at the same evaluation, the rate is 6&ndash;15%.",
            "I re-checked 500 of these with a deeper engine to rule out a measurement artifact, and the gap held. Some of it is that these positions often need one exact move. But the size of the gap fits &ldquo;didn't register that anything changed.&rdquo;")],
         "giftback",
         P("<b>So what.</b> The cue you can actually see: their move changed the position, the engine would say in your favour, and yet nothing is hanging. That is the moment you most often hand it back.")),

    card("double", "After your own mistake", "part 3 &middot; after a mistake",
         [P("<b>After a mistake of yours, the next move is about twice as likely to be one too, whether or not you could have seen the first.</b>",
            "Your next move is 1.5&ndash;2 times as likely to be a mistake as normal for its position. It's 2.0 times after mistakes that lost material within three moves, and 1.8 times after mistakes that never cost material at all.",
            "So it isn't a reaction to noticing a blunder; you can't react to what you didn't see. More likely the position is harder, or the same blind spot is still there.")],
         "double"),

    card("limits", "What this can and can't tell you", "read last",
         [P("<b>Exploratory, not a test set up in advance.</b> The cut points (a pawn or two, 20 seconds, three moves) were chosen once and not tuned, but nothing here was pre-registered.",
            "About 1 in 5 mistakes shrinks below the 10-point line when re-checked with a deeper engine (82% hold up). The 15-move engine lines get fuzzy toward the end, which is why the 4&ndash;15-move group gets a caution.",
            "Three examples per point show what each kind looks like. They don't prove the numbers; the numbers come from thousands of moves.")]),
]


def main():
    deck = {"id": "losses", "title": "Where your games are lost", "cards": CARDS}
    r = write_deck(deck)
    print("losses: %d cards, %d bytes" % (len(r["keys"]), r["bytes"]))


if __name__ == "__main__":
    main()
