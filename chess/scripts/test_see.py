import chess
from hanging import see

CASES = [
    # (fen, uci, expected, description)
    ("4k3/8/8/3p4/8/8/8/3RK3 w - - 0 1", "d1d5", 100,
     "rook takes undefended pawn = +100"),
    ("4k3/8/2p5/3p4/8/8/8/3RK3 w - - 0 1", "d1d5", -400,
     "rook takes pawn defended by pawn = 100-500"),
    ("4k3/8/2p5/3p4/8/8/3R4/3RK3 w - - 0 1", "d2d5", -300,
     "doubled rooks: RxP, pxR, RxP = 100-500+100"),
    ("4k3/8/2n5/3p4/8/8/8/3RKB2 w - - 0 1", "f1d3", 0,
     "bishop not capturing -> 0"),
    ("4k3/8/8/3n4/8/8/8/3RK3 w - - 0 1", "d1d5", 300,
     "rook wins undefended knight"),
    ("4k3/8/2p5/3n4/8/8/8/3RK3 w - - 0 1", "d1d5", -200,
     "R takes N defended by pawn = 300-500 = -200 (exchange down)"),
    ("4k3/8/8/3p4/4P3/8/8/4K3 w - - 0 1", "e4d5", 100,
     "pawn takes pawn"),
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e2e4", 0,
     "quiet move -> 0"),
    # x-ray: rook behind rook on the d-file
    ("3rk3/8/8/3p4/8/8/3R4/3RK3 w - - 0 1", "d2d5", 100,
     "R takes P, RxR, RxR: net +100 (x-ray battery wins)"),
    # king may not recapture into a defended square
    ("4k3/8/8/3pK3/8/8/8/3R4 w - - 0 1", "e5d5", 100,
     "king takes undefended pawn"),
]

fails = 0
for fen, uci, exp, desc in CASES:
    b = chess.Board(fen)
    m = chess.Move.from_uci(uci)
    got = see(b, m)
    ok = "ok " if got == exp else "FAIL"
    if got != exp:
        fails += 1
    print(f"{ok} {got:>6} (exp {exp:>6})  {desc}")
print("\nfailures:", fails)
raise SystemExit(1 if fails else 0)
