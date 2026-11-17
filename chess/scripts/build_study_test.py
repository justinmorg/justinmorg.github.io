#!/usr/bin/env python3
"""build_study_test — the phone test suite for /chess-study.

    https://justinmorg.github.io/chess-study/?test=1

Writes chess-study/data/test.json and test_index.json: nine cards on made-up
positions (no corpus position, no real card) that exercise every step type
and control of the card runner, each followed by "verify" steps where the
tester records whether it worked. Test mode stores under `study.test.v1`, so
real progress (`study.v1`) is never touched, and the test hub's "Copy test
report" button exports device details, automatic checks and the answers.
"""
import os, json, urllib.parse
import chess
from studycards import write_deck, OUT

START = chess.STARTING_FEN
E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
D4 = "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1"
PROMO = "8/4P3/8/8/8/8/k7/4K3 w - - 0 1"
LUCENA = "6K1/4k1P1/8/8/8/8/7r/5R2 w - - 0 1"


def p(*paras):
    return "".join("<p>%s</p>" % x for x in paras)


def show(text, fen=START, **kw):
    return dict({"type": "show", "fen": fen, "text": p(*text) if isinstance(text, (list, tuple)) else p(text)}, **kw)


def verify(ask, options=None, fen=None):
    st = {"type": "verify", "ask": ask}
    if options:
        st["options"] = options
    if fen:
        st["fen"] = fen
    return st


def cards():
    C = []
    C.append({"k": "T-1-board", "t": "Test 1: the board", "sub": "nothing to answer except the checks", "flip": False, "steps": [
        show(["This is the normal starting position, seen from White's side.",
              "There should be four arrows (green, red, blue, gold) and two shaded squares (e4 gold, d5 red)."],
             arrows=[["e2e4", "g"], ["d7d5", "r"], ["g1f3", "b"], ["b8c6", "y"]], marks=[["e4", "y"], ["d5", "r"]]),
        verify("All 32 pieces drawn, white at the bottom, small letters and numbers on the edge squares?", fen=START),
        verify("Four arrows in four colours and two shaded squares were visible on the previous screen? (Use the back arrow to look again.)", fen=START),
        show("The same position seen from Black's side. The white pieces should now be at the top, and the squares e2 and e4 should be tinted yellow as a last move.",
             fen=E4, flip=True, last="e2e4"),
        verify("Board flipped, with the last move tinted?", fen=E4),
        verify("Did the small back arrow (&larr;) take you to the previous screen when you tried it?"),
    ]})
    C.append({"k": "T-2-tap", "t": "Test 2: tapping squares", "sub": "three tap questions", "flip": False, "steps": [
        {"type": "tap", "fen": START, "ask": "Tap both white knights, then press Done.", "key": ["b1", "g1"], "none": "Nothing to tap",
         "rtext": "Both knights should now be shaded green."},
        verify("Each tapped square got a dark outline, the button counted them, and after Done both turned green with &ldquo;Found 2 of 2&rdquo;?"),
        {"type": "tap", "fen": START, "ask": "Now get it wrong on purpose: tap the knight on b1 and the rook on a1, then Done.", "key": ["b1", "g1"],
         "rtext": "Expected: b1 green (found), g1 red (missed), a1 gold (extra).", "rarrows": [["g1f3", "g"]]},
        verify("One green, one red, one gold square, a colour legend under the text, and a green arrow from g1?"),
        {"type": "tap", "fen": START, "ask": "Tap nothing. Press the button, which should read &ldquo;None of them&rdquo;.", "key": [], "none": "None of them",
         "rtext": "Expected verdict: Right, nothing."},
        verify("With nothing tapped the button read &ldquo;None of them&rdquo;, and the verdict was &ldquo;Right, nothing&rdquo;?"),
        {"type": "tap", "fen": START, "text": p("The next answer should change the board."), "ask": "Tap the pawn on e2, then Done.", "key": ["e2"],
         "rfen": E4, "rlast": "e2e4", "rtext": "The pawn should now stand on e4."},
        verify("After Done the board itself changed, with the pawn on e4?"),
        verify("Tapping a selected square a second time un-selected it? (Restart the card to try, if you did not notice.)"),
    ]})
    C.append({"k": "T-3-move", "t": "Test 3: playing a move", "sub": "tap the piece, then the square", "flip": False, "steps": [
        {"type": "move", "fen": START, "ask": "Play e4: tap the pawn on e2, then the square e4.", "main": "e2e4",
         "accept": {"e2e4": {"san": "e4", "fen": E4, "note": "The pawn should have moved.", "arrows": [["e7e5", "r"]]}}},
        verify("The pawn got an outline when tapped, moved to e4, &ldquo;Right.&rdquo; appeared, and a red arrow e7 to e5 was drawn?"),
        {"type": "move", "fen": START,
         "text": p("Four things in order on this screen.", "1. Play Nf3 (g1 then f3): a specific message about Nf3.", "2. Play e3 (e2 then e3): &ldquo;Not wrong&rdquo;.",
                   "3. Press Hint.", "4. Press Show me."),
         "ask": "The move wanted is d4, but do the four things above first.", "main": "d2d4", "hint": "this is the hint text: the queen's pawn.",
         "accept": {"d2d4": {"san": "d4", "fen": D4, "note": "This is the answer text."}},
         "alt": {"e2e3": "This is the neutral message for e3."},
         "bad": {"g1f3": "This is the specific message for Nf3."}, "wrong": "This is the general wrong-move message."},
        verify("Nf3 gave &ldquo;Not that one&rdquo; with the specific message, and the piece did not move?"),
        verify("e3 gave &ldquo;Not wrong&rdquo; with the neutral message?"),
        verify("Hint showed the hint text, and Show me then moved the pawn to d4 with &ldquo;Shown&rdquo;?"),
        {"type": "move", "fen": PROMO, "ask": "Promote: tap the pawn on e7, then e8.", "main": "e7e8q",
         "accept": {"e7e8q": {"san": "e8=Q", "fen": "4Q3/8/8/8/8/8/k7/4K3 b - - 0 1", "note": "A white queen should stand on e8."}}},
        verify("A queen appeared on e8?"),
        {"type": "move", "fen": START, "ask": "Do not move anything. Press &ldquo;Nothing wins a piece&rdquo;.", "none": "Nothing wins a piece",
         "noneOk": True, "noneText": "This is the nothing-there text.", "accept": {}},
        verify("&ldquo;Right.&rdquo; with the nothing-there text?"),
    ]})
    C.append({"k": "T-4-choice", "t": "Test 4: multiple choice", "sub": "answer wrongly on purpose", "flip": False, "steps": [
        {"type": "choice", "fen": START, "ask": "Is this the starting position? Answer No on purpose.", "options": ["Yes", "No", "Not sure"], "answer": 0,
         "explain": "This is the explanation text.", "rmarks": [["e1", "g"], ["e8", "g"]]},
        verify("Three buttons, then &ldquo;Not quite&rdquo; with the explanation, and both kings shaded green?"),
        verify("The button &ldquo;I think the key is wrong&rdquo; appeared under the answer and changed to &ldquo;Flagged, thanks&rdquo; when pressed?"),
    ]})
    fq = urllib.parse.quote(LUCENA)
    C.append({"k": "T-5-playout", "t": "Test 5: play-out links", "sub": "this one leaves the page", "flip": False, "steps": [
        {"type": "playout", "fen": LUCENA,
         "text": p("A textbook rook ending, White to move. Press each of the two buttons once, look at what Lichess shows, come back, then press Won and Lost once each."),
         "play": [["Play it against the computer", "https://lichess.org/?fen=%s#ai" % fq],
                  ["Open the board", "https://lichess.org/analysis/standard/%s?color=white" % LUCENA.replace(" ", "_")]]},
        verify("&ldquo;Play it against the computer&rdquo;: what did Lichess show?",
               ["Worked: play-the-computer setup, this position", "Lichess opened, wrong position or no setup", "Asked me to log in", "Nothing opened"], fen=LUCENA),
        verify("&ldquo;Open the board&rdquo;: what did Lichess show?",
               ["Worked: analysis board, this position", "Lichess opened, wrong position", "Nothing opened"], fen=LUCENA),
        verify("Back on the card, did pressing Won and Lost add an &ldquo;Attempts so far&rdquo; line?"),
        verify("Did the links open in a new tab or in the Lichess app, so that coming back kept your place?",
               ["Yes, kept my place", "No, the page reloaded or lost my place"]),
    ]})
    C.append({"k": "T-6-nav", "t": "Test 6: getting around", "sub": "links and the card buttons", "flip": False,
              "links": [["The real game", "https://lichess.org/analysis"]], "steps": [
        show(["Under the board there is a blue link, &ldquo;The real game&rdquo;. On real cards it opens your game at that move; here it just opens a Lichess board.",
              "At the very bottom are three buttons: &larr; Card, Restart card, Card &rarr;. Try &larr; Card (it goes to test 5), then come forward again."]),
        verify("The blue link opened Lichess?"),
        verify("&larr; Card and Card &rarr; moved between cards, and Restart card went back to this card's first screen?"),
        verify("The bar at the top (&larr; All, the deck name, 6 / 9) stayed in view while scrolling?"),
        verify("Text size comfortable to read, and buttons easy to hit with a thumb?", ["Yes", "No, too small", "No, too big"]),
    ]})
    C.append({"k": "T-7-long", "t": "Test 7: a long card", "sub": "progress bar and scrolling", "flip": True, "steps":
        [show("Screen %d of 12. Keep pressing Next. The row of small bars above the board should fill from the left." % (i + 1),
              fen=E4 if i % 2 else START, last=("e2e4" if i % 2 else None)) for i in range(12)] +
        [verify("The progress bars filled as you went, and each Next jumped back to the top of the card?")]})
    for st in C[-1]["steps"]:
        if st.get("last") is None:
            st.pop("last", None)
    C.append({"k": "T-8-speed", "t": "Test 8: speed", "sub": "does it keep up", "flip": False, "steps": [
        {"type": "tap", "fen": START, "ask": "Tap all sixteen white pieces and pawns as fast as you can, then Done.",
         "key": [f + r for r in "12" for f in "abcdefgh"], "rtext": "All sixteen should be green."},
        verify("Every tap registered, with no lag and no accidental zooming or text selection?", ["Yes", "No, taps were missed", "No, the page zoomed or selected text"]),
    ]})
    C.append({"k": "T-9-memory", "t": "Test 9: does it remember", "sub": "the last one", "flip": False, "steps": [
        show(["Press &larr; All at the top. The test page should say how many of the 9 cards you have answered.",
              "Then close this tab completely, open the link again, and check that the count is still there. Come back to this card to answer."], fen=START),
        verify("The count on the test page matched what you had done?"),
        verify("After closing and reopening the tab, the count was still there?", ["Yes", "No, it reset", "Have not tried"]),
    ]})
    return C


def main():
    deck = {"id": "test", "title": "Test suite", "cards": cards()}
    info = write_deck(deck)
    man = {"built": "2026-11-16", "lede": "", "groups": [{"title": "Test", "blurb": "", "decks": [
        {"id": "test", "tag": "T", "kind": "drill", "title": "Test suite", "blurb": "", "keys": info["keys"]}]}]}
    json.dump(man, open(os.path.join(OUT, "test_index.json"), "w"), separators=(",", ":"), sort_keys=True)
    print("test deck: %d cards, %d steps" % (len(info["keys"]), sum(len(c["steps"]) for c in deck["cards"])))


if __name__ == "__main__":
    main()
