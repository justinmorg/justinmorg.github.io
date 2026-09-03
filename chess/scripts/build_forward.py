#!/usr/bin/env python3
"""Build group F - the play-forward drill - into chess-drills/index.html.

Why this exists. Group P shows a position and says, in effect, "something is
wrong here - find it." That is the pre-flagged task the R notes and
forcingtest.py already show is *not* the deficit: when a card forces a look,
the look works (87% on own forcing moves in matched controls). The failure in
games is that the look never fires, on considered quiet moves, with nothing
flagging the position. A drill that flags the position trains the wrong half.

Group F reproduces the mechanism instead of the symptom:

  * Each card is a *window* of consecutive own moves from a real game - the
    moves actually played, replayed one at a time, opponent replies included.
  * At every step the task is the H2 check: the move you played is shown on the
    board; picture the position it creates; does anything hang to a capture?
    Answer SAFE or HANGS, then see the verdict.
  * The window starts 3-5 own moves before a floored group P hit and may run
    0-2 own moves past it, so the position of the error inside the window is
    not knowable from the card. A threat that appears mid-window and is not
    dealt with is therefore *stale* by the time it costs material - the
    standing-threat mechanism the oppmove.py section identified.
  * Roughly a fifth of the cards are decoys: windows from the same kind of
    position (winning middlegame, eligible moves) in which nothing ever hangs.
    "Safe" has to be a real answer or the card is doing the scanning for you.

Every step carries a ground-truth label computed with hanging.py's own SEE
machinery, so the verdicts are consistent with the corpus:

  H  hangs      - after the move the opponent has a capture with SEE >= 150 and
                  the engine agrees it cost >= 0.02 win-probability. Correct
                  answer: HANGS.
  C  compensated- SEE finds material but the eval does not move (>= 150 SEE,
                  wp_error <= 0.02). There is compensation elsewhere. Correct
                  answer: SAFE, and the verdict says why.
  S  clean      - nothing hangs. Correct answer: SAFE. If the engine still
                  disliked the move (wp_error > 0.10) the verdict says so and
                  says it is not this drill's error.

Progress lives in localStorage under `drills.forward.v1`, keyed
`F-{gid}-{ply}` (hit windows, ply = the hit's ply) or `F-{gid}-{ply}-d`
(decoys, ply = the window's first own move). Group F cards carry no
class="drill" and no tick box, so the 260-drill counter never sees them, on
the group R precedent. The page records, per answered step, the answer, whether
it was right, the label, and seconds taken; "Copy my F results as JSON"
exports the lot.

**The in-page hit rate is not an outcome measure.** It will improve with
familiarity whether or not anything transfers. The pre-registered outcome is
in chess/README.md, "Pre-registration: group F".

Usage:
    python3 chess/scripts/hanging.py corpus.pgn light   # -> /home/claude/hits_light.json
    python3 chess/scripts/build_forward.py [corpus.pgn] [hits_light.json] [index.html]

Idempotent: the F block, CSS and JS are bracketed by markers and replaced
whole on every run. Window lengths and the decoy sample are seeded from game
ids, so the output is byte-identical across runs on the same inputs.
"""
import json, html, os, sys, re, hashlib, random
import chess, chess.pgn

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from hanging import see, threat_after, parse_eval, winprob, npm, USER

CORPUS = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/corpus.pgn"
HITS   = sys.argv[2] if len(sys.argv) > 2 else "/home/claude/hits_light.json"
PAGE   = sys.argv[3] if len(sys.argv) > 3 else os.path.join(REPO, "chess-drills/index.html")

FLOOR = 0.02          # same win%-error floor as build_drills2.py

# Odometer for the pre-registered treatment block (chess/README.md,
# "Pre-registration: group F"). The page reads the live rated-blitz game
# count from the public Lichess API and shows (count - ODO_BASE) / ODO_TARGET.
# ODO_BASE is the API's perfs.blitz.games on the morning after the first F
# session; it is an odometer only - the block itself is defined by game
# timestamps, so this number being a few games off changes nothing. The count
# includes every blitz control, so it only tracks the block while the games
# being played are 3+2 / 5+0. No rating is fetched or shown, on purpose.
ODO_USER = "jamorgan"
ODO_BASE = 5964        # 2026-09-02
ODO_TARGET = 900
N_DECOY = 60          # ~20% of the set
SEED = 23

def h(s):
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)

# ---------------------------------------------------------------- per-move labelling
def label_move(board, move, cp_before_me, cp_after_me, in_check):
    """Ground truth for one own move, using hanging.py's exact probes."""
    nb = board.copy(stack=False)
    nb.push(chess.Move.null())
    my_king = board.king(board.turn)
    before_see, before_mv = 0, None
    for m in nb.legal_moves:
        if not nb.is_capture(m) or m.to_square == my_king:
            continue
        s = see(nb, m)
        if s > before_see:
            before_see, before_mv = s, m
    after = board.copy(stack=False)
    after.push(move)
    after_see, after_mv = threat_after(board, move, after)
    wp_err = winprob(cp_before_me) - winprob(cp_after_me)

    if after_see >= 150 and wp_err > FLOOR:
        lab = "H"
    elif after_see >= 150:
        lab = "C"
    else:
        lab = "S"
    return {
        "L": lab,
        "cap": after.san(after_mv) if after_mv else "",
        "sv": after_see,
        "std": 1 if (before_see >= 150 and after_see >= 150) else 0,
        "fixed": 1 if (before_see >= 150 and after_see < 150) else 0,
        "bcap": nb.san(before_mv) if before_mv else "",
        "cb": cp_before_me, "ca": cp_after_me,
        "we": round(wp_err, 3),
        "chk": 1 if in_check else 0,
    }


def walk(game, me):
    """One pass over a game: list of own-move records with everything F needs."""
    board = game.board()
    prev_eval = 0
    ply = 0
    node = game
    recs = []
    last_opp = None     # (uci, san) of the opponent's most recent move
    while node.variations:
        node = node.variations[0]
        move = node.move
        mover = board.turn
        ply += 1
        e = parse_eval(node.comment, mover == chess.WHITE)
        if mover == me:
            cp_b = prev_eval if me == chess.WHITE else -prev_eval
            cp_a_w = e if e is not None else prev_eval
            cp_a = cp_a_w if me == chess.WHITE else -cp_a_w
            r = label_move(board, move, cp_b, cp_a, board.is_check())
            r.update({
                "ply": ply, "fm": board.fullmove_number,
                "fen": board.fen(), "m": move.uci(), "s": board.san(move),
                "pm": last_opp[0] if last_opp else "", "ps": last_opp[1] if last_opp else "",
                "elig": int(board.fullmove_number > 12 and npm(board, "light") > 14 and cp_b >= 150),
            })
            recs.append(r)
        else:
            last_opp = (move.uci(), board.san(move))
            if recs:
                recs[-1]["r"] = move.uci(); recs[-1]["rs"] = board.san(move)
        board.push(move)
        prev_eval = e if e is not None else prev_eval
    return recs


# ---------------------------------------------------------------- build windows
hits = [r for r in json.load(open(HITS)) if r["wp_error"] > FLOOR]
hit_keys = {(r["gid"], r["ply"]) for r in hits}
hit_by_gid = {}
for r in hits:
    hit_by_gid.setdefault(r["gid"], []).append(r["ply"])

games = {}
with open(CORPUS) as fh:
    while True:
        g = chess.pgn.read_game(fh)
        if g is None:
            break
        gid = g.headers.get("GameId", "")
        hw, hb = g.headers.get("White", ""), g.headers.get("Black", "")
        me = chess.WHITE if USER == hw else chess.BLACK if USER == hb else None
        if me is None:
            continue
        games[gid] = (g, me)

if not games:
    sys.exit(f"ERROR: no games for USER={USER!r} in {CORPUS}")

STEP_FIELDS = ("fen", "m", "s", "r", "rs", "pm", "ps", "L", "cap", "sv", "std",
               "fixed", "bcap", "cb", "ca", "we", "chk", "fm", "ply")

def pack(recs, lo, hi):
    """Only the first step carries a FEN; the page replays the moves itself.
    (Every step's FEN is kept during the build for the self-check below.)"""
    out = []
    for j, r in enumerate(recs[lo:hi]):
        d = {k: r.get(k, "") for k in STEP_FIELDS if k != "fen"}
        if j == 0:
            d["fen"] = r["fen"]
        else:
            d.pop("pm", None); d.pop("ps", None)   # the page takes these from the previous step's reply
        d["_fen"] = r["fen"]
        out.append(d)
    return out

cards = []
walked = {}
def get_recs(gid):
    if gid not in walked:
        g, me = games[gid]
        walked[gid] = (walk(g, me), me)
    return walked[gid]

# --- hit windows
for r in hits:
    gid, ply = r["gid"], r["ply"]
    if gid not in games:
        continue
    recs, me = get_recs(gid)
    idx = next((i for i, x in enumerate(recs) if x["ply"] == ply), None)
    if idx is None:
        continue
    assert recs[idx]["L"] == "H", (gid, ply, recs[idx]["L"])
    seed = h(f"{gid}-{ply}")
    kb = 3 + seed % 3            # 3..5 own moves before
    ka = (seed // 3) % 3         # 0..2 own moves after
    lo = max(0, idx - kb)
    hi = min(len(recs), idx + 1 + ka)
    cards.append({
        "k": f"F-{gid}-{ply}", "gid": gid, "side": "white" if me == chess.WHITE else "black",
        "opp": html.escape(r["opp"] or "?"), "elo": html.escape(r["opp_elo"] or "?"), "date": r["date"],
        "decoy": 0, "cost": round(r["wp_error"] * 100),
        "steps": pack(recs, lo, hi),
    })

# --- decoy windows: eligible, winning, and nothing hangs anywhere in the window
rng = random.Random(SEED)
cands = []
for gid in sorted(games):
    recs, me = get_recs(gid)
    n = len(recs)
    for i in range(n):
        if not recs[i]["elig"]:
            continue
        L = 4 + h(f"{gid}-{recs[i]['ply']}-d") % 4       # 4..7 own moves
        if i + L > n:
            continue
        win = recs[i:i + L]
        if any(x["L"] == "H" for x in win):
            continue
        if any(x["we"] > 0.10 for x in win):             # keep decoys genuinely quiet
            continue
        cands.append((gid, i, L))
rng.shuffle(cands)
seen_g = set()
decoys = []
for gid, i, L in cands:
    if gid in seen_g:
        continue
    seen_g.add(gid)
    decoys.append((gid, i, L))
    if len(decoys) >= N_DECOY:
        break
for gid, i, L in decoys:
    recs, me = get_recs(gid)
    g = games[gid][0]
    opp = g.headers.get("Black") if me == chess.WHITE else g.headers.get("White")
    elo = g.headers.get("BlackElo") if me == chess.WHITE else g.headers.get("WhiteElo")
    cards.append({
        "k": f"F-{gid}-{recs[i]['ply']}-d", "gid": gid,
        "side": "white" if me == chess.WHITE else "black",
        "opp": html.escape(opp or "?"), "elo": html.escape(elo or "?"),
        "date": g.headers.get("UTCDate", "").replace(".", "-"),
        "decoy": 1, "cost": 0, "steps": pack(recs, i, i + L),
    })

# deterministic interleave so hits and decoys are not separable by position
cards.sort(key=lambda c: h(c["k"] + "-order"))

n_steps = sum(len(c["steps"]) for c in cards)
n_H = sum(1 for c in cards for s in c["steps"] if s["L"] == "H")
n_C = sum(1 for c in cards for s in c["steps"] if s["L"] == "C")
n_hit = sum(1 for c in cards if not c["decoy"])
n_dec = len(cards) - n_hit

# Self-check: the page replays UCI moves on a plain 64-square array with its
# own castling / en-passant / promotion handling. Verify here, with
# python-chess, that replaying each card's moves from its first FEN lands on
# every stored intermediate FEN, so a client-side replay bug cannot ship as a
# wrong board. (The JS mirrors this logic; a mismatch here means the data is
# inconsistent, which is the only failure a static check can catch.)
for c in cards:
    b = chess.Board(c["steps"][0]["fen"])
    for j, st in enumerate(c["steps"]):
        assert b.fen() == st["_fen"], (c["k"], j)
        b.push_uci(st["m"])
        if st["r"]:
            b.push_uci(st["r"])
    for st in c["steps"]:
        del st["_fen"]

data = json.dumps(cards, separators=(",", ":"))

# ---------------------------------------------------------------- page assembly
blurb = f"""<!--F-START--><section class="group" id="gF">
  <header class="ghead"><span class="gletter alt">F</span><h2>Play forward &mdash; the check before you commit</h2></header>
  <p class="blurb"><strong>Run this first, ahead of the P scans.</strong> The P cards tell you something is wrong and ask you to find it. That is the half you are already good at &mdash; when a card forces a look, the look works. What goes wrong in games is that the look never fires: you choose a quiet move, never scan the position it creates, and a capture that was sitting there the whole time finally lands. This drill reproduces that, not the symptom.</p>
  <p class="blurb">Each card replays <strong>a run of moves you actually played</strong>, one at a time, opponent replies included. First pick your own move in your head. Then the move you played is <em>named, not shown</em> &mdash; the board stays put. <strong>Picture the position that move creates. Does anything hang to a capture?</strong> Answer, then the move appears with the verdict, then the opponent replies and you go again. Somewhere in most cards is a move that cost you a piece; you are not told which, and some threats appear early and only cash in later. About one card in five is a <em>decoy</em> where nothing ever hangs, so <strong>&ldquo;safe&rdquo; has to be a real answer</strong>.</p>
  <p class="blurb dim">{len(cards)} cards ({n_hit} from hanging-material games, {n_dec} decoys), {n_steps} decisions, of which {n_H} hang. Aim to decide in under ten seconds &mdash; the moves that cost you games took eight. Your hit rate here is practice feedback, not the outcome; the outcome is the hanging-material rate in your next games, and that is pre-registered in the README.</p>
  <div class="fodo" id="fodo"><span class="fodo-t" id="fodo-t">Games toward the test block: checking&hellip;</span><span class="bar"><i id="fodo-b"></i></span></div>
  <div id="fstats" class="fstats"></div>
  <div id="fstage" class="fstage"></div>
  <p class="rexport"><button id="fexport" class="btn ghost">Copy my F results as JSON</button> <button id="freset" class="btn ghost">Reset F progress</button></p>
</section>
<script type="application/json" id="fdata">{data}</script>
<!--F-END-->"""

css = """/*F-CSS*/
.fodo{display:flex;align-items:baseline;gap:.6rem;margin:.2rem 0 .5rem;font-family:'Roboto Mono',monospace;font-size:.8rem;color:var(--ink)}
.fodo .bar{flex:1}
.fstage{margin:.6rem 0 0}
.fcard{border-top:1px solid var(--rule);padding:1rem 0}
.fcard h3{font-family:'Saira Condensed',sans-serif;font-weight:600;font-size:1.12rem;margin:.1rem 0 .25rem;line-height:1.2}
.fboard{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);width:min(340px,86vw);aspect-ratio:1;
margin:.7rem 0;border:2px solid var(--ink);border-radius:2px;overflow:hidden;font-size:min(38px,9.6vw);line-height:1}
.fboard i{display:flex;align-items:center;justify-content:center;font-style:normal;color:#111;font-family:'Apple Symbols','Segoe UI Symbol','Noto Sans Symbols 2','DejaVu Sans',serif;position:relative}
.fboard i.d{background:var(--board)} .fboard i.l{background:var(--cream)}
.fboard i.w{color:#fff;text-shadow:0 0 1px #000,0 0 2px #000}
.fboard i.hl{box-shadow:inset 0 0 0 3px var(--flag)}
.fboard i.ho{box-shadow:inset 0 0 0 3px #3A3D2E}
.frow{display:flex;align-items:center;justify-content:space-between;gap:.6rem;flex-wrap:wrap}
.fstep{font-family:'Roboto Mono',monospace;font-size:.78rem;color:var(--muted)}
.ftimer{font-family:'Roboto Mono',monospace;font-size:.95rem;min-width:3.2em;text-align:right}
.ftimer.late{color:var(--flag)}
.fask{font-size:.98rem;margin:.5rem 0 .4rem}
.fmove{font-family:'Roboto Mono',monospace;font-weight:500;font-size:1.05rem}
.fbtns{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}
.fbtns .btn{cursor:pointer;font-size:1.02rem;padding:.6rem 1rem}
.fbtns .btn.play{background:var(--ink);color:var(--paper);border:0}
.fbtns .btn.warn{background:var(--flag);color:var(--paper);border:0}
.fverdict{border-left:3px solid var(--rule);padding:.2rem 0 .2rem .8rem;margin:.6rem 0;font-size:.95rem}
.fverdict.ok{border-color:var(--board)} .fverdict.bad{border-color:var(--flag)}
.fverdict strong.tag{font-family:'Saira Condensed',sans-serif;text-transform:uppercase;letter-spacing:.04em}
.fsum{font-family:'Roboto Mono',monospace;font-size:.85rem;margin:.4rem 0}
.fstats{font-family:'Roboto Mono',monospace;font-size:.8rem;color:var(--muted);margin:.2rem 0 .6rem;line-height:1.5}
.fnav{display:flex;gap:.5rem;flex-wrap:wrap;margin:.6rem 0 0}
.fnav .btn{cursor:pointer}
/*F-CSS-END*/"""

js = r"""/*F-JS*/
(function(){
  var FKEY='drills.forward.v1', ODO_USER=%r, ODO_BASE=%d, ODO_TARGET=%d;
  var cards=JSON.parse(document.getElementById('fdata').textContent);
  var GL={p:'\u265F\uFE0E',n:'\u265E\uFE0E',b:'\u265D\uFE0E',r:'\u265C\uFE0E',q:'\u265B\uFE0E',k:'\u265A\uFE0E'};
  var mem={};   // in-memory fallback so a blocked localStorage still lets a session run
  function fget(){ try{var v=JSON.parse(localStorage.getItem(FKEY)); if(v)return v; }catch(e){} return mem; }
  function fset(s){ mem=s; try{localStorage.setItem(FKEY,JSON.stringify(s))}catch(e){} }

  // ---- board model: 64-array, index 0 = a8, 63 = h1 (FEN order)
  function fromFen(fen){
    var b=[],rows=fen.split(' ')[0].split('/');
    rows.forEach(function(row){ for(var i=0;i<row.length;i++){var c=row[i];
      if(c>='1'&&c<='8'){for(var k=0;k<+c;k++)b.push('');} else b.push(c);} });
    return b;
  }
  function sq(u){ return (8-(+u[1]))*8 + (u.charCodeAt(0)-97); }
  function apply(b,uci){
    var f=sq(uci.slice(0,2)), t=sq(uci.slice(2,4)), p=b[f], white=p===p.toUpperCase();
    b[f]='';
    if(p.toLowerCase()==='p'){
      if((f%8)!==(t%8) && b[t]===''){ b[Math.floor(f/8)*8+(t%8)]=''; }   // en passant
      if(uci.length>4){ p=white?uci[4].toUpperCase():uci[4]; }           // promotion
    }
    if(p.toLowerCase()==='k' && Math.abs((t%8)-(f%8))===2){              // castling
      var rank=Math.floor(f/8)*8, ks=(t%8)===6;
      var rf=rank+(ks?7:0), rt=rank+(ks?5:3);
      b[rt]=b[rf]; b[rf]='';
    }
    b[t]=p;
    return b;
  }
  function render(el,b,flip,hl,cls){
    var cells=[];
    for(var i=0;i<64;i++)cells.push(i);
    if(flip)cells.reverse();
    el.innerHTML=cells.map(function(i){
      var r=Math.floor(i/8),f=i%8,dark=((r+f)%2)===1,p=b[i];
      var g=p?GL[p.toLowerCase()]:'', white=p&&p===p.toUpperCase();
      var h=hl&&hl.indexOf(i)>=0?' '+cls:'';
      return '<i class="'+(dark?'d':'l')+(white?' w':'')+h+'">'+g+'</i>';
    }).join('');
  }
  function ev(cp){ if(cp>=10000)return 'mate'; if(cp<=-10000)return 'mated'; return (cp>=0?'+':'')+(cp/100).toFixed(1); }
  function pawns(cp){ return (cp/100).toFixed(1); }

  // ---- state
  var stage=document.getElementById('fstage'), stats=document.getElementById('fstats');
  var ci=-1, si=0, phase=0, t0=0, tick=null, board=null, card=null;

  function firstUnfinished(){
    var s=fget();
    for(var i=0;i<cards.length;i++){ var e=s[cards[i].k]; if(!e||!e.done)return i; }
    return -1;
  }
  function stepsDone(){
    var s=fget(),n=0,h=0,hc=0,sf=0,sfc=0,tt=[];
    Object.keys(s).forEach(function(k){ (s[k].steps||[]).forEach(function(x){
      n++; tt.push(x.t);
      if(x.L==='H'){h++; if(x.c)hc++;} else {sf++; if(x.c)sfc++;}
    });});
    tt.sort(function(a,b){return a-b});
    return {n:n,h:h,hc:hc,sf:sf,sfc:sfc,med:tt.length?tt[Math.floor(tt.length/2)]:0,
      cards:Object.keys(s).filter(function(k){return s[k].done}).length};
  }
  function paintStats(){
    var d=stepsDone();
    if(!d.n){stats.textContent=cards.length+' cards. Nothing answered yet.';return;}
    stats.innerHTML=d.cards+' / '+cards.length+' cards &middot; '+d.n+' decisions &middot; '+
      'caught '+d.hc+' of '+d.h+' hanging moves ('+(d.h?Math.round(100*d.hc/d.h):0)+'%) &middot; '+
      'false alarms '+(d.sf-d.sfc)+' of '+d.sf+' safe moves ('+(d.sf?Math.round(100*(d.sf-d.sfc)/d.sf):0)+'%) &middot; '+
      'median '+(d.med/1000).toFixed(1)+'s';
  }

  function startTimer(el){
    t0=Date.now(); clearInterval(tick);
    tick=setInterval(function(){ var s=(Date.now()-t0)/1000; el.textContent=s.toFixed(0)+'s'; el.classList.toggle('late',s>10); },250);
  }
  function stopTimer(){ clearInterval(tick); return Date.now()-t0; }

  function show(i){
    ci=i; card=cards[i]; si=0; phase=0;
    if(!card){ stage.innerHTML='<p class="blurb">All '+cards.length+' cards done. Reset to run them again.</p>'; return; }
    board=fromFen(card.steps[0].fen);
    draw();
  }
  function draw(){
    var st=card.steps[si], flip=card.side==='black', n=card.steps.length;
    var hl=[],cls='ho';
    var b=board.slice();
    var ask, btns;
    if(phase===0){
      var pm=si===0?st.pm:card.steps[si-1].r, ps=si===0?st.ps:card.steps[si-1].rs;
      if(pm){hl=[sq(pm.slice(0,2)),sq(pm.slice(2,4))];}
      ask='<p class="fask">'+(ps?'They played <span class="fmove">'+ps+'</span>. ':'')+'Your move. Choose it in your head'+(st.chk?' <span class="flag">you are in check</span>':'')+'.</p>';
      btns='<div class="fbtns"><button class="btn play" data-act="reveal">Show what I played</button></div>';
    } else if(phase===1){
      // board stays on the pre-move position: the move is named, not shown
      ask='<p class="fask">You played <span class="fmove">'+st.s+'</span>. <strong>Without seeing it, picture the position after that move. What can they take or check?</strong> Does anything hang?</p>';
      btns='<div class="fbtns"><button class="btn ghost" data-act="ans" data-a="S">Safe</button><button class="btn warn" data-act="ans" data-a="H">Something hangs</button></div>';
    } else {
      b=apply(b,st.m); hl=[sq(st.m.slice(0,2)),sq(st.m.slice(2,4))]; cls='hl';
      {
        ask=verdictHtml(st, card._last);
        btns='<div class="fbtns"><button class="btn play" data-act="next">'+(si+1<n?'Next move':'Finish card')+'</button></div>';
      }
    }
    stage.innerHTML='<div class="fcard">'+
      '<div class="frow"><h3>Move '+st.fm+' &middot; you\'re '+(card.side==='white'?'White':'Black')+' &middot; <span class="ev">'+ev(st.cb)+'</span></h3>'+
      '<span class="ftimer" id="ftimer"></span></div>'+
      '<div class="fstep">card '+(ci+1)+' of '+cards.length+' &middot; decision '+(si+1)+' of '+n+'</div>'+
      '<div class="fboard" id="fboard"></div>'+ask+btns+
      (phase===2&&si+1>=n?summaryHtml():'')+
      '<div class="fnav"><button class="btn ghost" data-act="skip">Skip card</button></div>'+
      '</div>';
    render(document.getElementById('fboard'),b,flip,hl,cls);
    if(phase===1)startTimer(document.getElementById('ftimer'));
  }
  function verdictHtml(st,a){
    var right=(a==='H')===(st.L==='H'), out='';
    var tag=right?'Right':'Wrong', k=right?'ok':'bad';
    if(st.L==='H'){
      out='<p><strong class="tag">'+tag+'.</strong> <strong>'+st.cap+'</strong> wins '+pawns(st.sv)+' pawns. '+
        (st.std?'That threat was <em>already on the board</em> before this move'+(st.bcap?' ('+st.bcap+')':'')+' &mdash; it went stale and you played past it.':'Nothing was hanging until this move created it.')+
        ' Eval '+ev(st.cb)+' &rarr; '+ev(st.ca)+', '+Math.round(st.we*100)+' win% points.</p>';
    } else if(st.L==='C'){
      out='<p><strong class="tag">'+tag+'.</strong> '+st.cap+' does take material ('+pawns(st.sv)+'), but the engine says the move is fine: '+ev(st.cb)+' &rarr; '+ev(st.ca)+'. There is compensation &mdash; a bigger capture, a check, or a counter-threat. The scan should find the capture <em>and</em> conclude it does not matter.</p>';
    } else {
      out='<p><strong class="tag">'+tag+'.</strong> Nothing hangs.'+
        (st.fixed?' There <em>was</em> a threat before this move'+(st.bcap?' ('+st.bcap+')':'')+' and this dealt with it.':'')+
        (st.we>0.10?' The engine still disliked the move ('+ev(st.cb)+' &rarr; '+ev(st.ca)+'), but no material was loose &mdash; that is a different error and not what this drill checks.':'')+'</p>';
    }
    return '<div class="fverdict '+k+'">'+out+'</div>';
  }
  function summaryHtml(){
    var s=fget()[card.k]||{steps:[]}, st=s.steps||[], c=st.filter(function(x){return x.c}).length;
    var hidx=[]; card.steps.forEach(function(x,i){ if(x.L==='H')hidx.push(i+1); });
    var link='https://lichess.org/'+card.gid+'#'+(card.steps[0].ply-1);
    return '<div class="fsum">'+c+' / '+st.length+' right. '+(card.decoy?'Decoy card &mdash; nothing hung anywhere.':'Hanging move'+(hidx.length>1?'s':'')+' at decision '+hidx.join(', ')+'.')+
      ' <a href="'+link+'" target="_blank" rel="noopener">The real game</a> &middot; vs '+card.opp+' ('+card.elo+') &middot; '+card.date+'</div>';
  }

  stage.addEventListener('click',function(e){
    var b=e.target.closest('button[data-act]'); if(!b)return;
    var act=b.dataset.act, st=card&&card.steps[si];
    if(act==='reveal'){ phase=1; draw(); return; }
    if(act==='ans'){
      var t=stopTimer(), a=b.dataset.a, right=(a==='H')===(st.L==='H');
      var s=fget(); var ent=s[card.k]||{steps:[]};
      ent.steps=ent.steps.filter(function(x){return x.ply!==st.ply});
      ent.steps.push({ply:st.ply,L:st.L,a:a,c:right?1:0,t:t,ts:Date.now()});
      if(si+1>=card.steps.length){ent.done=Date.now();}
      s[card.k]=ent; fset(s); card._last=a; phase=2; paintStats(); draw(); return;
    }
    if(act==='next'){
      if(si+1>=card.steps.length){ show(firstUnfinished()); return; }
      board=apply(board,st.m); if(st.r)board=apply(board,st.r);
      si++; phase=0; draw(); return;
    }
    if(act==='skip'){ var j=(ci+1)%cards.length, k=0; while(k<cards.length){ var ee=fget()[cards[j].k]; if(!ee||!ee.done)break; j=(j+1)%cards.length; k++; } show(k<cards.length?j:-1); return; }
  });
  document.getElementById('fexport').addEventListener('click',function(){
    var s=fget(),out=[];
    Object.keys(s).forEach(function(k){ out.push({key:k,done:s[k].done||null,steps:s[k].steps||[]}); });
    var txt=JSON.stringify(out,null,1), b=this;
    (navigator.clipboard?navigator.clipboard.writeText(txt):Promise.reject())
      .then(function(){b.textContent='Copied '+out.length+' cards as JSON';setTimeout(function(){b.textContent='Copy my F results as JSON'},1600);})
      .catch(function(){prompt('Copy:',txt);});
  });
  document.getElementById('freset').addEventListener('click',function(){
    if(confirm('Clear all group F answers? (P/R/endgame progress is untouched.)')){ fset({}); paintStats(); show(firstUnfinished()); }
  });
  paintStats(); show(firstUnfinished());

  // ---- odometer: rated blitz games since the drill began, toward the 900-game block
  (function(){
    var t=document.getElementById('fodo-t'), b=document.getElementById('fodo-b');
    if(!t||!window.fetch)return;
    fetch('https://lichess.org/api/user/'+ODO_USER,{headers:{'Accept':'application/json'}})
      .then(function(r){return r.ok?r.json():Promise.reject(r.status)})
      .then(function(u){
        var g=u&&u.perfs&&u.perfs.blitz&&u.perfs.blitz.games;
        if(typeof g!=='number'){t.textContent='Games toward the test block: count unavailable';return;}
        var n=Math.max(0,g-ODO_BASE), pct=Math.min(100,100*n/ODO_TARGET);
        t.innerHTML=(n>=ODO_TARGET?'<strong>'+n+' / '+ODO_TARGET+' &mdash; block is full; test it when you are ready</strong>':n+' / '+ODO_TARGET+' rated blitz games since the drill began');
        b.style.width=pct+'%';
      })
      .catch(function(){t.textContent='Games toward the test block: could not reach Lichess';});
  })();
})();
/*F-JS-END*/"""
js = js.replace("ODO_USER=%r, ODO_BASE=%d, ODO_TARGET=%d",
                f"ODO_USER={ODO_USER!r}, ODO_BASE={ODO_BASE}, ODO_TARGET={ODO_TARGET}")

src = open(PAGE).read()

# F block: replace between markers, else insert before gP
if "<!--F-START-->" in src:
    src = re.sub(r"<!--F-START-->.*?<!--F-END-->", lambda m: blurb, src, flags=re.S)
else:
    src = src.replace('<section class="group" id="gP">', blurb + '\n<section class="group" id="gP">', 1)

# nav link
if 'href="#gF"' not in src:
    src = src.replace('<nav class="jump"><a href="#gP">P</a>', '<nav class="jump"><a href="#gF">F</a><a href="#gP">P</a>', 1)

# css
if "/*F-CSS*/" in src:
    src = re.sub(r"/\*F-CSS\*/.*?/\*F-CSS-END\*/", lambda m: css, src, flags=re.S)
else:
    src = src.replace("footer{margin-top:3rem;", css + "footer{margin-top:3rem;", 1)

# js: its own script tag, after the R script
if "/*F-JS*/" in src:
    src = re.sub(r"/\*F-JS\*/.*?/\*F-JS-END\*/", lambda m: js, src, flags=re.S)
else:
    src = src.replace("/*R-JS-END*/</script>", "/*R-JS-END*/</script>\n<script>" + js + "</script>", 1)

open(PAGE, "w").write(src)
print(f"cards: {len(cards)} ({n_hit} hit windows, {n_dec} decoys)  steps: {n_steps}  "
      f"H: {n_H} ({100*n_H/n_steps:.1f}%)  C: {n_C}  page: {len(src):,} bytes")
