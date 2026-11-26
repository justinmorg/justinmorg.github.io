"""Lesson text for tr_lessons (build_study_trades.py). Figures from
notes/2026-11-25-trades-from-level.md; change both together."""

CARDS = [
    ("TRL-what", "What was checked", [
        "<b>Every moment in your games where material was exactly level and an even trade was on offer.</b> That covers your Lichess 3+2 and 5+0 games from mid-2024 through the 900-game block, your moves and your opponents'. It came to 30,177 moments in 5,098 games.",
        "<b>An even trade</b> here means a knight or bishop for a knight or bishop, a rook for a rook, or a queen for a queen, where the other side can take back.",
        "<b>A trade &ldquo;costs&rdquo;</b> when it gives up 5 or more points of winning chance out of 100 compared with the engine's best move. When the game is balanced, that is about half a pawn. Costly trades were re-checked with a deeper engine search, and the numbers held.",
    ]),
    ("TRL-even", "When the game is even, trading is safe", [
        "When the position is balanced, your trades cost on <b>14%</b> of moves. Your other moves in the same positions cost on <b>40%</b>. Your opponents look the same: 15% against 37%.",
        "So taking an even trade from an even position, in the Caro or anywhere else, is a sound default. Your belief holds there.",
        "This doesn't mean the trade is the <i>best</i> move. It means a trade rarely loses ground, while a non-trading move often does.",
        "The same goes when you are slightly worse: trading costs you far less often than other moves (23% against 46%).",
    ]),
    ("TRL-better", "When you're better, your trades give it back", [
        "<b>When you are clearly better on the board</b> (the engine says +1.5 or more for you, with material still level), your trades cost on <b>40%</b> of moves. That makes them no safer than your other moves there (43%).",
        "Your opponents, when they are clearly better, trade at a cost on <b>32%</b> of moves, well below their other moves (47%). The deeper engine puts it at 41% for you against 26% for them. A gap that size is very unlikely to be chance.",
        "<b>It is mostly bishop and knight trades.</b> It shows most in the London, and in the Caro Advance after move 12, where you are often better once the opening is over. In the Caro Exchange there is no gap.",
        "<b>Why it happens:</b> when material is level but you are better, your edge is made of where your pieces stand. Trade off your best piece and the edge goes with it.",
    ]),
    ("TRL-clock", "Trading when short of time", [
        "With <b>20 seconds or less</b>, you take an available even trade 78% of the time, against 56% for your opponents.",
        "Trading didn't change how many mistakes you made over the next ten moves, either way. The trade itself wasn't a mistake more often than your other moves.",
        "<b>What it means:</b> simplifying when short of time looks fine. The caveat is that this rests on only about 100 games at that clock, so a real effect of a few mistakes per 100 moves either way could hide in it (the range runs from 3 fewer to 8 more; your usual rate there is 13).",
    ]),
    ("TRL-do", "What to practise", [
        "<b>Before an even trade, look at the evaluation first.</b> If it is level or you are worse, trading is fine. If you are better, ask: <i>what does this trade get me?</i>",
        "Good answers: it wins material, it removes their best defender, it gets their active piece off the board, or it leads to an ending you know is won. If there is no answer, keep the pieces on and improve your worst piece.",
        "<b>The deck &ldquo;Trade or keep?&rdquo;</b> is your own positions where you were better with material level. In some, the trade you played threw the edge away. In others, the trade really was the best move. Decide first, then play a move.",
    ]),
]
