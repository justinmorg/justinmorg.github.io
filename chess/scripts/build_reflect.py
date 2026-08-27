#!/usr/bin/env python3
"""Build group R — the reflection set — on chess-drills/index.html.

Thread 2 found where level games are decided: a permanent >=200cp drop on a
*considered* move in a quiet, piece-heavy position at moves 13-25, with nothing
hanging. That is a judgment failure, and no groupby can say what kind. Group R
puts those positions in front of the player and asks him to articulate — before
seeing the answer — what he saw, what the idea was, what he was worried about.
The notes accumulate in localStorage and export as JSON, so a batch of them can
be read back for the pattern.

Selection (from firstdrop.py's output, thr 200 / N=5):
    level at middlegame entry, first drop permanent, fullmove 13-25,
    npm_light >= 13, hang_label == none, opponent's previous move quiet,
    not in check, Lichess blocks only (game links; matches group P's
    Lichess-only precedent), top 40 by wp_error.

Usage:
    python3 chess/scripts/firstdrop.py /home/claude/features   # first
    python3 chess/scripts/build_reflect.py [features_dir] [index.html]

Idempotent: replaces the existing gR section, nav link, CSS and JS blocks in
place; running it twice produces a byte-identical page. It never touches the
gP/gA/gB/gC/gD blocks or the 260-drill counter — reflection cards carry no
class="drill" and no data-n checkbox, deliberately, so paint() never sees them.

Engine: depth-16 Stockfish "what was better" line per position (deeper than
the corpus's depth 12 on purpose — these are the positions being studied, and
the spoiler should be trustworthy). Cached in features_dir/reflect_engine.json
so rebuilds don't redo ~2 min of engine time. Engine path: $STOCKFISH_PATH,
default /home/claude/sf/x/usr/games/stockfish, same as annotate.py.

Storage keys: notes live under localStorage 'drills.reflect.v1' as
{"R-<gid>-<ply>": {"t": text, "ts": epoch_ms}}. Stable ids on the group P
precedent — rebuilds and reorderings keep notes attached to their positions.
Nothing writes to 'drills.done.v1'; the reset button does not clear notes.
"""
import glob
import gzip
import html
import json
import os
import sys

import chess
import chess.engine
import chess.pgn
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

FEAT = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/features"
PAGE = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "chess-drills/index.html")
SF = os.environ.get("STOCKFISH_PATH", "/home/claude/sf/x/usr/games/stockfish")
CACHE = os.path.join(FEAT, "reflect_engine.json")

N_CARDS = 40
LICHESS_BLOCKS = {"2024H2", "Q1-2025", "Q2-2025", "Q3-2025", "2026"}
LICHESS_FILES = sorted(glob.glob(os.path.join(REPO, "chess/data/jamorgan_*_analyzed.pgn.gz")))


# ---------------------------------------------------------------- selection
def select():
    fd = pd.read_csv(os.path.join(FEAT, "firstdrop", "firstdrop_200.csv"))
    lv = pd.read_csv(os.path.join(FEAT, "firstdrop", "level_games.csv"))
    level = set(lv[lv.entry_bucket == "level"].gid)
    sel = fd[fd.gid.isin(level) & (fd.rec5 == False)                      # noqa: E712
             & fd.fullmove.between(13, 25) & (fd.npm_light >= 13)
             & (fd.hang_label == "none") & (fd.opp_prev_kind == "quiet")
             & (fd.in_check == 0) & fd.block.isin(LICHESS_BLOCKS)]
    if len(sel) < N_CARDS:
        sys.exit(f"ERROR: only {len(sel)} candidates; expected >= {N_CARDS}")
    return sel.sort_values("wp_error", ascending=False).head(N_CARDS)


# ---------------------------------------------------------------- extraction
def extract(sel):
    """Walk the Lichess analyzed files; for each selected (gid, ply) return
    FEN before the move, the played SAN, opponent's previous SAN and headers."""
    want = {g: int(p) for g, p in zip(sel.gid, sel.ply)}
    out = {}
    for path in LICHESS_FILES:
        with gzip.open(path, "rt") as fh:
            while True:
                game = chess.pgn.read_game(fh)
                if game is None:
                    break
                gid = game.headers.get("GameId", "")
                if gid not in want:
                    continue
                target = want[gid]
                board = game.board()
                ply = 0
                prev_san = None
                for mv in game.mainline_moves():
                    ply += 1
                    if ply == target:
                        out[gid] = {
                            "fen": board.fen(),
                            "played": board.san(mv),
                            "opp_prev": prev_san,
                            "white": game.headers.get("White", "?"),
                            "black": game.headers.get("Black", "?"),
                            "welo": game.headers.get("WhiteElo", "?"),
                            "belo": game.headers.get("BlackElo", "?"),
                            "date": game.headers.get("UTCDate", "?").replace(".", "-"),
                        }
                        break
                    prev_san = board.san(mv)
                    board.push(mv)
    missing = set(want) - set(out)
    if missing:
        sys.exit(f"ERROR: {len(missing)} selected gids not found in Lichess "
                 f"files, e.g. {sorted(missing)[:3]}")
    return out


def validate(sel, ext):
    """Hard-exit unless the replay agrees with the features tables — the
    project's validate-before-trusting rule."""
    for _, r in sel.iterrows():
        e = ext[r.gid]
        b = chess.Board(e["fen"])
        side = "white" if b.turn == chess.WHITE else "black"
        me = e["white"] if side == "white" else e["black"]
        if me != "jamorgan":
            sys.exit(f"ERROR: {r.gid} ply {r.ply}: side to move is {me}, "
                     f"not jamorgan — ply misalignment")
        if b.fullmove_number != r.fullmove:
            sys.exit(f"ERROR: {r.gid}: fullmove {b.fullmove_number} != "
                     f"features {r.fullmove}")
        if isinstance(r.opp_prev_san, str) and r.opp_prev_san and \
                e["opp_prev"] != r.opp_prev_san:
            sys.exit(f"ERROR: {r.gid}: opp prev {e['opp_prev']} != "
                     f"features {r.opp_prev_san}")


# ---------------------------------------------------------------- engine
def engine_lines(sel, ext):
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE))
    todo = [(r.gid, int(r.ply)) for _, r in sel.iterrows()
            if f"{r.gid}-{r.ply}" not in cache]
    if todo:
        if not os.path.exists(SF):
            sys.exit(f"ERROR: stockfish not at {SF} — see README "
                     f"'Stockfish in a fresh sandbox'")
        eng = chess.engine.SimpleEngine.popen_uci(SF)
        eng.configure({"Threads": 1})
        for gid, ply in todo:
            b = chess.Board(ext[gid]["fen"])
            info = eng.analyse(b, chess.engine.Limit(depth=16))
            pv = info["pv"][:3]
            sans, bb = [], b.copy()
            for mv in pv:
                sans.append(bb.san(mv))
                bb.push(mv)
            cache[f"{gid}-{ply}"] = " ".join(sans)
        eng.quit()
        json.dump(cache, open(CACHE, "w"), indent=0, sort_keys=True)
    return cache


# ---------------------------------------------------------------- render
def ev(cp):
    if cp >= 10000:
        return "mate"
    if cp <= -10000:
        return "mated"
    return f"{cp / 100:+.1f}"


def card(r, e, better):
    fen = e["fen"]
    b = chess.Board(fen)
    side = "white" if b.turn == chess.WHITE else "black"
    opp = e["black"] if side == "white" else e["white"]
    oelo = e["belo"] if side == "white" else e["welo"]
    key = f"R-{r.gid}-{r.ply}"
    link = ("https://lichess.org/analysis/standard/"
            + fen.replace(" ", "_") + f"?color={side}")
    game = f"https://lichess.org/{r.gid}#{int(r.ply) - 1}"
    cost = round(r.wp_error * 100)
    spend = f"{r.spend:.0f}" if pd.notna(r.spend) else "?"
    return f"""<article class="rcard" id="d{key}" data-k="{key}" data-fen="{fen}" data-played="{html.escape(e['played'])}" data-fm="{int(r.fullmove)}" data-side="{side}" data-cpb="{int(r.cp_before)}" data-cpa="{int(r.cp_after)}" data-spend="{spend}">
  <div class="body">
    <h3>Move {int(r.fullmove)} &middot; you're {side.capitalize()} &middot; <span class="ev">{ev(r.cp_before)}</span> &middot; you thought for {spend}s</h3>
    <div class="board" data-fen="{fen}" data-flip="{1 if side == 'black' else 0}"></div>
    <p class="ask">{opp_line(e)} You played <strong>{html.escape(e['played'])}</strong>.</p>
    <p class="ask dim">Before opening the answer: why this move? What did you see in the position, what was the idea, and what (if anything) were you worried about?</p>
    <textarea class="rnote" data-k="{key}" rows="4" placeholder="What I saw / the plan / what I was worried about&hellip;"></textarea>
    <p class="rsaved dim" data-k="{key}"></p>
    <details class="spoil"><summary>What happened</summary>
      <p>Eval {ev(r.cp_before)} &rarr; <strong>{ev(r.cp_after)}</strong> &mdash; this move cost {cost} win% points and the game never recovered. Deeper engine (depth 16) prefers <strong>{html.escape(better)}</strong>.</p>
      <p class="dim">Nothing was hanging and the opponent's last move was quiet &mdash; this is a judgment position, which is exactly why it's here. After reading the line, add to your note what you missed.</p>
      <p class="meta dim">vs {html.escape(opp)} ({html.escape(oelo)}) &middot; {e['date']}</p>
      <div class="acts">
        <a class="btn ghost" href="{link}" target="_blank" rel="noopener">Explore on Lichess</a>
        <a class="btn ghost" href="{game}" target="_blank" rel="noopener">The real game</a>
      </div>
    </details>
  </div>
</article>"""


def opp_line(e):
    if e["opp_prev"]:
        return (f"Your opponent just played the quiet move "
                f"<strong>{html.escape(e['opp_prev'])}</strong>.")
    return "It's your move."


CSS = """/* group R — reflection */
.rcard{padding:1.1rem 0;border-top:1px solid var(--rule)}
.rcard.noted .body{opacity:.62}
.rnote{width:100%;box-sizing:border-box;font:inherit;font-size:.92rem;color:var(--ink);
background:#fff;border:1px solid var(--rule);border-radius:2px;padding:.55rem .6rem;resize:vertical}
.rnote:focus{outline:2px solid var(--board)}
.rsaved{min-height:1em;margin:.25rem 0 .4rem;font-size:.78rem}
.rprog{font-family:'Roboto Mono',monospace;font-size:.85rem;margin:.2rem 0 .8rem}
.rexport{margin:.4rem 0 0}
"""

JS = """
(function(){
  var RKEY='drills.reflect.v1';
  function rget(){ try{return JSON.parse(localStorage.getItem(RKEY))||{} }catch(e){return {} } }
  function rset(s){ try{localStorage.setItem(RKEY,JSON.stringify(s))}catch(e){} }
  function rpaint(){
    var s=rget(),c=0,n=0;
    document.querySelectorAll('.rcard').forEach(function(el){
      n++;
      var k=el.dataset.k, has=s[k]&&s[k].t&&s[k].t.trim();
      el.classList.toggle('noted',!!has);
      if(has)c++;
    });
    var p=document.getElementById('rprog');
    if(p)p.textContent=c+' / '+n+' written';
  }
  document.querySelectorAll('.rnote').forEach(function(t){
    var s=rget(),k=t.dataset.k;
    if(s[k]&&s[k].t)t.value=s[k].t;
  });
  var timers={};
  document.addEventListener('input',function(e){
    var t=e.target.closest('.rnote'); if(!t)return;
    var k=t.dataset.k;
    clearTimeout(timers[k]);
    timers[k]=setTimeout(function(){
      var s=rget();
      if(t.value.trim()) s[k]={t:t.value,ts:Date.now()}; else delete s[k];
      rset(s); rpaint();
      var m=document.querySelector('.rsaved[data-k="'+k+'"]');
      if(m){m.textContent='saved';setTimeout(function(){m.textContent=''},1200);}
    },600);
  });
  var ex=document.getElementById('rexport');
  if(ex)ex.addEventListener('click',function(){
    var s=rget(),out=[];
    document.querySelectorAll('.rcard').forEach(function(el){
      var k=el.dataset.k, note=s[k]&&s[k].t?s[k].t:'';
      if(!note.trim())return;
      out.push({key:k,fen:el.dataset.fen,played:el.dataset.played,
        move:+el.dataset.fm,side:el.dataset.side,spend:el.dataset.spend,
        cp_before:+el.dataset.cpb,cp_after:+el.dataset.cpa,note:note});
    });
    var txt=JSON.stringify(out,null,1);
    (navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject())
      .then(function(){ex.textContent='Copied '+out.length+' notes as JSON';
        setTimeout(function(){ex.textContent='Copy my notes as JSON'},1600);})
      .catch(function(){prompt('Copy:',txt);});
  });
  rpaint();
})();
"""


def build():
    sel = select()
    print(f"selected {len(sel)} positions, wp_error "
          f"{sel.wp_error.min():.2f}-{sel.wp_error.max():.2f}")
    ext = extract(sel)
    validate(sel, ext)
    print("replay validation OK (side, fullmove, opponent's previous move)")
    lines = engine_lines(sel, ext)

    cards = "".join(card(r, ext[r.gid], lines[f"{r.gid}-{r.ply}"])
                    for _, r in sel.iterrows())
    block = f"""<section class="group" id="gR">
  <header class="ghead"><span class="gletter alt">R</span><h2>Reflection &mdash; where level games are decided</h2></header>
  <p class="blurb">Not a drill &mdash; a notebook. The corpus says your level games are decided by one move: a <strong>considered</strong> move in a quiet, piece-heavy position around moves 13&ndash;25, with nothing hanging. These are the {N_CARDS} such moves that cost the most. For each one: sit with the position, then write down &mdash; honestly, in your own words &mdash; why you played what you played. What you saw, what the plan was, what you were worried about. <em>Then</em> open the answer.</p>
  <p class="blurb">The notes save in this browser and survive rebuilds. When you've written a batch, <strong>Copy my notes as JSON</strong> and bring them to a session &mdash; the whole point is to read them together and find what you're seeing and what you're systematically not.</p>
  <p class="rprog" id="rprog">0 / {N_CARDS} written</p>
  <button class="btn ghost rexport" id="rexport">Copy my notes as JSON</button>
  {cards}
</section>"""

    src = open(PAGE).read()

    # section: replace existing gR, else insert before <footer>
    if '<section class="group" id="gR">' in src:
        start = src.index('<section class="group" id="gR">')
        end = src.index("<footer>", start)
        src = src[:start] + block + "\n\n" + src[end:]
    else:
        src = src.replace("<footer>", block + "\n\n<footer>", 1)

    # nav link after D
    if '<a href="#gR">R</a>' not in src:
        src = src.replace('<a href="#gD">D</a>', '<a href="#gD">D</a><a href="#gR">R</a>', 1)

    # css, marked
    cssblk = "/*R-CSS*/" + CSS + "/*R-CSS-END*/"
    if "/*R-CSS*/" in src:
        s, e = src.index("/*R-CSS*/"), src.index("/*R-CSS-END*/") + len("/*R-CSS-END*/")
        src = src[:s] + cssblk + src[e:]
    else:
        src = src.replace("footer{margin-top:3rem;", cssblk + "footer{margin-top:3rem;", 1)

    # js, marked, its own script tag before </body>
    jsblk = "<script>/*R-JS*/" + JS + "/*R-JS-END*/</script>"
    if "/*R-JS*/" in src:
        s = src.index("<script>/*R-JS*/")
        e = src.index("/*R-JS-END*/</script>") + len("/*R-JS-END*/</script>")
        src = src[:s] + jsblk + src[e:]
    else:
        src = src.replace("</body>", jsblk + "\n</body>", 1)

    open(PAGE, "w").write(src)
    print(f"group R: {N_CARDS} cards -> {PAGE} ({len(src):,} bytes)")


if __name__ == "__main__":
    build()
