#!/usr/bin/env python3
"""Rebuild the priority (P) drill set in chess-drills/index.html as two modes.

Mode A - the threat already exists in the position. Question is answerable from
         the FEN alone: which of my squares is loose? No dependence on the move
         I actually played.
Mode B - nothing was loose beforehand; my move created the hang. The position is
         shown *before* the move, the move is named in text, and the question is
         what refutes it. Unique answer in every case.

Boards are rendered client-side from the FEN, so the page carries no engine,
no eval bar and no state from a previous Lichess session.

Tick keys are stable ids derived from (gid, ply), so future rebuilds preserve
progress even if the ordering or the split changes.

Input is the hits file written by hanging.py:

    python3 chess/scripts/hanging.py corpus.pgn light   # -> /home/claude/hits_light.json
    python3 chess/scripts/build_drills2.py              # -> chess-drills/index.html

(An earlier session called this file motifs.json. Same thing, same schema -
it is hanging.py's output. Nothing in this repo produces a "motifs.json".)

Usage:  python3 build_drills2.py [hits_light.json] [index.html]

Both arguments default relative to this script's location in the repo, so it
works from any clone directory without editing.
"""
import json, re, html, os, sys, re, chess
HERE = os.path.dirname(os.path.abspath(__file__))          # <repo>/chess/scripts
REPO = os.path.dirname(os.path.dirname(HERE))              # <repo>
sys.path.insert(0, HERE)
from hanging import see

HITS = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/hits_light.json"
PAGE = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "chess-drills/index.html")

NAME = {chess.PAWN:"pawn", chess.KNIGHT:"knight", chess.BISHOP:"bishop",
        chess.ROOK:"rook", chess.QUEEN:"queen"}


def loose_squares(fen, thresh=150):
    """Squares the opponent can already win material on, if I do nothing."""
    b = chess.Board(fen)
    nb = b.copy(stack=False)
    nb.push(chess.Move.null())
    king = b.king(b.turn)
    out = {}
    for m in nb.legal_moves:
        if not nb.is_capture(m) or m.to_square == king:
            continue
        s = see(nb, m)
        if s >= thresh:
            sq = chess.square_name(m.to_square)
            if s > out.get(sq, (0, None))[0]:
                out[sq] = (s, nb.san(m), NAME.get(b.piece_type_at(m.to_square), "piece"))
    return out


def ev(cp):
    if cp >= 10000:  return "mate"
    if cp <= -10000: return "mated"
    return f"{cp/100:+.1f}"


def card(r, mode, key):
    fen  = r["fen"]
    side = r["side"]
    link = "https://lichess.org/analysis/standard/" + fen.replace(" ", "_") + f"?color={side}"
    game = f"https://lichess.org/{r['gid']}#{r['ply']-1}"
    cost = round(r["wp_error"] * 100)
    opp  = html.escape(r["opp"] or "?")
    chk  = ' <span class="flag">you are in check</span>' if r["in_check"] else ""

    if mode == "A":
        sqs = loose_squares(fen)
        ask = "Which of your squares is already loose?"
        hint = (f'<span class="dim">{len(sqs)} squares</span>' if len(sqs) > 1 else "")
        bits = ", ".join(
            f"<strong>{s}</strong> (your {v[2]} &mdash; they play <strong>{html.escape(v[1])}</strong>, "
            f"winning {v[0]/100:.1f})"
            for s, v in sorted(sqs.items(), key=lambda kv: -kv[1][0]))
        answer = f"<p>{bits}</p>"
        extra = (f'<p class="dim">In the game you played {html.escape(r["move_played"])} '
                 f'and it cost you {cost} win% points.</p>')
    else:
        ask = (f'You played <strong>{html.escape(r["move_played"])}</strong>. '
               f'Picture it on the board. What refutes it?')
        hint = ""
        answer = (f'<p><strong>{html.escape(r["their_capture"])}</strong>, winning '
                  f'{r["see_after"]/100:.1f} pawns. Nothing was hanging before your move &mdash; '
                  f'this one you created.</p>')
        extra = f'<p class="dim">Eval {ev(r["cp_before"])} &rarr; {ev(r["cp_after"])}, {cost} win% points.</p>'

    return f"""<article class="drill" id="d{key}" data-n="{key}">
  <div class="body">
    <h3>Move {r['fullmove']} &middot; you're {side.capitalize()} &middot; <span class="ev">{ev(r['cp_before'])}</span>{chk}</h3>
    <div class="board" data-fen="{fen}" data-flip="{1 if side=='black' else 0}"></div>
    <p class="ask">{ask} {hint}</p>
    <details class="spoil"><summary>Answer</summary>
      {answer}
      {extra}
      <p class="meta dim">vs {opp} ({html.escape(r['opp_elo'] or '?')}) &middot; {r['date']}</p>
      <div class="acts">
        <a class="btn ghost" href="{link}" target="_blank" rel="noopener">Explore on Lichess</a>
        <a class="btn ghost" href="{game}" target="_blank" rel="noopener">The real game</a>
      </div>
    </details>
    <label class="done"><input type="checkbox" data-n="{key}"> Spotted it</label>
  </div>
</article>"""


# ---------------------------------------------------------------- build
rows = json.load(open(HITS))

# The win%-error floor. hanging.py's raw output includes hits where SEE finds
# material but the eval doesn't move (compensation elsewhere), and the correct
# answer in those is "ignore it" - the opposite of the reflex being drilled.
# TIERS below start at the floor, so unfiltered input would render the right
# cards under the wrong headline counts. Filter here so they agree.
#
# Raised 0.02 -> 0.05 on 2026-09-03. SEE looks at one square and cannot see a
# counter-threat elsewhere, so the "is it compensated" question rests entirely
# on the eval; at a 2-point floor that is inside depth-12's own wobble. A
# depth-18 audit of all 239 cards found 21 (8.8%) were not errors at all, 8 of
# them the engine's top move. In the <=0.05 band the false-positive rate is
# 41%; above 0.10 it is 0.5%. See verify_labels.py and the README's
# "Label audit".
FLOOR = 0.05
rows = [r for r in rows if r["wp_error"] > FLOOR]

A = sorted([r for r in rows if r["label"] == "missed their threat"], key=lambda r: -r["wp_error"])
B = sorted([r for r in rows if r["label"] == "hung it myself"],      key=lambda r: -r["wp_error"])

TIERS = [(0.50, 1.01, "Threw the game outright",
          "A win became a loss on one move."),
         (0.30, 0.50, "Threw most of it",
          "Still alive afterwards, but you handed back the bulk of it in a single move."),
         (0.10, 0.30, "Real damage",
          "A clear chunk of the win gone &mdash; a comfortable game turned into a fight."),
         (FLOOR, 0.10, "Leaks",
          "Small individually, common collectively. Skim for the recurring shape.")]


def tiered(rs, mode):
    out, nav = [], []
    for i, (lo, hi, title, blurb) in enumerate(TIERS, 1):
        grp = [r for r in rs if lo <= r["wp_error"] < hi]
        if not grp:
            continue
        gid = f"g{mode}{i}"
        nav.append((f"{mode}{i}", gid))
        cards = "".join(card(r, mode, f"{mode}-{r['gid']}-{r['ply']}") for r in grp)
        out.append(f"""<section class="group" id="{gid}">
  <header class="ghead"><span class="gletter alt">{mode}{i}</span><h2>{title}</h2></header>
  <p class="blurb">{blurb} <strong>{len(grp)} positions.</strong></p>
  {cards}
</section>""")
    return "".join(out), nav


secA, navA = tiered(A, "A")
secB, navB = tiered(B, "B")

block = f"""<section class="group" id="gP">
  <header class="ghead"><span class="gletter alt">P</span><h2>Priority &mdash; hanging material</h2></header>
  <p class="blurb">The single biggest source of thrown-away wins, and the reason this set sits ahead of the endgame drills. Across 1,515 blitz games there are <strong>{len(A)+len(B)} middlegame moves</strong> you played while <strong>already winning by +1.5 or more</strong>, where a capture worth at least a pawn and a half was on the board and you played something else. They split into two different skills, so they're now two different drills.</p>
  <p class="blurb"><strong>Group A &mdash; the scan.</strong> {len(A)} positions where the threat was <em>already there</em> before you moved. The question is answerable from the position alone: which of your squares is loose? Give yourself <strong>fifteen seconds</strong>, name the square out loud, then open the answer. 79% have exactly one; the rest have two. This is the one to run now.</p>
  <p class="blurb"><strong>Group B &mdash; the check before you commit.</strong> {len(B)} positions where nothing was hanging until your move created it. The board shows the position <em>before</em> you moved and the move is named underneath &mdash; picture it, then find the punishment. Unique answer every time. Do these after A.</p>
  <p class="blurb dim">Neither group is played out against the computer. Fifteen seconds, name it, move on &mdash; the skill is the scan, not the calculation.</p>
</section>
{secA}{secB}"""

nav = "".join(f'<a href="#{g}">{t}</a>' for t, g in navA + navB)

src = open(PAGE).read()
start = src.index('<section class="group" id="gP">')
end   = src.index('<section class="group" id="gC">')
src = src[:start] + block + "\n" + src[end:]

# nav: replace the old P1..P4 links
src = re.sub(r'<a href="#gP">P</a>(<a href="#gP\d">P\d</a>)+', f'<a href="#gP">P</a>{nav}', src)

# board renderer + styles, injected once
if "renderBoards" not in src:
    css = """.board{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);width:min(300px,78vw);aspect-ratio:1;
margin:.7rem 0;border:2px solid var(--ink);border-radius:2px;overflow:hidden;font-size:min(34px,8.6vw);line-height:1}
.board i{display:flex;align-items:center;justify-content:center;font-style:normal;color:#111;font-family:'Apple Symbols','Segoe UI Symbol','Noto Sans Symbols 2','DejaVu Sans',serif}
.board i.d{background:var(--board)} .board i.l{background:var(--cream)}
.board i.w{color:#fff;text-shadow:0 0 1px #000,0 0 2px #000}
.ask{font-size:.95rem;margin:.5rem 0 .3rem}
.ask .dim{font-size:.82rem}
"""
    js = """
  var GL={p:'\\u265F\\uFE0E',n:'\\u265E\\uFE0E',b:'\\u265D\\uFE0E',r:'\\u265C\\uFE0E',q:'\\u265B\\uFE0E',k:'\\u265A\\uFE0E'};
  function renderBoards(){
    document.querySelectorAll('.board:not([data-done])').forEach(function(el){
      var rows=el.dataset.fen.split(' ')[0].split('/'), flip=el.dataset.flip==='1', cells=[];
      rows.forEach(function(row,r){
        var f=0;
        for(var i=0;i<row.length;i++){
          var c=row[i];
          if(c>='1'&&c<='8'){ for(var k=0;k<+c;k++){cells.push([r,f++,null]);} }
          else { cells.push([r,f++,c]); }
        }
      });
      if(flip) cells.reverse();
      el.innerHTML=cells.map(function(c){
        var dark=((c[0]+c[1])%2)===1, p=c[2];
        var g=p?GL[p.toLowerCase()]:'';
        var white=p&&p===p.toUpperCase();
        return '<i class="'+(dark?'d':'l')+(white?' w':'')+'">'+g+'</i>';
      }).join('');
      el.dataset.done='1';
    });
  }
  renderBoards();
"""
    src = src.replace("footer{margin-top:3rem;", css + "footer{margin-top:3rem;", 1)
    src = src.replace("  function get(){", js + "  function get(){", 1)

# The tick counter total is written into three places in the page and was
# hardcoded at 260. Raising the floor changed how many P cards exist, so it is
# now derived from the page itself on every build - a stale denominator is a
# silently wrong progress bar.
n_drills = src.count('class="drill"')
src = re.sub(r'(<span id="ptext">0 / )\d+(</span>)', lambda m: m.group(1) + str(n_drills) + m.group(2), src)
src = re.sub(r"(var KEY='drills\.done\.v1', total=)\d+", lambda m: m.group(1) + str(n_drills), src)
src = re.sub(r"(Clear all )\d+( ticks\?)", lambda m: m.group(1) + str(n_drills) + m.group(2), src)
print(f"tick counter total: {n_drills}")

open(PAGE, "w").write(src)
print(f"Mode A: {len(A)}   Mode B: {len(B)}   total {len(A)+len(B)}")
print(f"page: {len(src):,} bytes")
