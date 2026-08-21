#!/usr/bin/env python3
"""Inject the hanging-material priority set into chess-drills/index.html."""
import json, html, re

PAGE = "/home/claude/justinmorg.github.io/chess-drills/index.html"
rows = json.load(open("/home/claude/hits_light.json"))
rows = [r for r in rows if r["wp_error"] > 0.02]
rows.sort(key=lambda r: -r["wp_error"])

TIERS = [
    ("P1", 0.50, 1.01, "Threw the game outright",
     "A win became a loss on one move. Every one of these was a decided game."),
    ("P2", 0.30, 0.50, "Threw most of it",
     "Still theoretically alive afterwards, but you handed back the bulk of the advantage in a single move."),
    ("P3", 0.10, 0.30, "Real damage",
     "A clear chunk of the win gone. These are the ones that turn a comfortable game into a fight."),
    ("P4", 0.02, 0.10, "Leaks",
     "Small individually, common collectively. Skim these — you're looking for the recurring shape, not the single move."),
]

def ev(cp):
    if cp >= 10000:  return "mate"
    if cp <= -10000: return "mated"
    return f"{cp/100:+.1f}"

def card(r, n):
    fen = r["fen"]
    link = "https://lichess.org/analysis/standard/" + fen.replace(" ", "_") + f"?color={r['side']}"
    game = f"https://lichess.org/{r['gid']}#{r['ply']-1}"
    shade = "dark" if n % 2 else "light"
    lab = r["label"]
    cost = round(r["wp_error"] * 100)
    opp = html.escape(r["opp"] or "?")
    opening = html.escape(r["opening"] or "")
    chk = " <span class=\"flag\">in check</span>" if r["in_check"] else ""
    return f"""<article class="drill" id="dP{n}" data-n="P{n}">
  <div class="sq {shade}"><span class="num">{n}</span></div>
  <div class="body">
    <h3>Move {r['fullmove']} &middot; you're {r['side'].capitalize()} &middot; <span class="ev">{ev(r['cp_before'])}</span></h3>
    <p class="meta"><span class="tag {'t-miss' if lab.startswith('missed') else 't-hung'}">{lab}</span>{chk} &middot; cost you {cost} win% points</p>
    <p class="meta dim">{opening} &middot; vs {opp} ({html.escape(r['opp_elo'] or '?')}) &middot; {r['date']}</p>
    <div class="acts">
      <a class="btn play" href="{link}" target="_blank" rel="noopener">Open the position</a>
      <a class="btn ghost" href="{game}" target="_blank" rel="noopener">Review the real game</a>
    </div>
    <details class="spoil"><summary>What actually happened</summary>
      <p>You played <strong>{html.escape(r['move_played'])}</strong>. That left <strong>{html.escape(r['their_capture'])}</strong>, winning {r['see_after']/100:.1f} pawns of material. Eval {ev(r['cp_before'])} &rarr; {ev(r['cp_after'])}.</p>
    </details>
    <button class="fen" data-fen="{fen}" title="Copy FEN">{fen}</button>
    <label class="done"><input type="checkbox" data-n="P{n}"> Spotted it</label>
  </div>
</article>"""

n = 0
sections = []
counts = []
for tid, lo, hi, title, blurb in TIERS:
    grp = [r for r in rows if lo <= r["wp_error"] < hi]
    counts.append((tid, len(grp)))
    cards = []
    for r in grp:
        n += 1
        cards.append(card(r, n))
    sections.append(f"""<section class="group" id="g{tid}">
  <header class="ghead">
    <span class="gletter alt">{tid}</span>
    <h2>{title}</h2>
  </header>
  <p class="blurb">{blurb} <strong>{len(grp)} positions.</strong></p>
  {"".join(cards)}
</section>""")

TOTAL_NEW = n
n_miss = sum(1 for r in rows if r["label"].startswith("missed"))
n_hung = TOTAL_NEW - n_miss

priority = f"""
<section class="group" id="gP">
  <header class="ghead">
    <span class="gletter alt">P</span>
    <h2>Priority &mdash; hanging material</h2>
  </header>
  <p class="blurb">The single biggest source of thrown-away wins, and the reason this set sits ahead of the endgame drills. Across 1,515 blitz games there are <strong>{TOTAL_NEW} middlegame moves</strong> you played while <strong>already winning by +1.5 or more</strong>, where a capture worth at least a pawn and a half was sitting on the board and you played something else. <strong>{n_miss}</strong> of them were threats your opponent already had; <strong>{n_hung}</strong> you created yourself. Ranked worst-first by how much of the win each one cost.</p>
  <p class="blurb"><strong>Run these differently.</strong> Don't play them out against the computer &mdash; that trains the wrong muscle. Open the position, give yourself <strong>fifteen seconds</strong>, and say out loud what your opponent takes if you do nothing. Then open the spoiler. The skill is the scan, not the calculation, and fifteen seconds is roughly what you'll have in a real 5+0 game.</p>
</section>
{"".join(sections)}
"""

src = open(PAGE).read()

# --- masthead -------------------------------------------------------------
src = src.replace(
    '<p class="eyebrow">jamorgan &middot; blitz 2026 &middot; 1,431 games</p>',
    '<p class="eyebrow">jamorgan &middot; blitz 2026 &middot; 1,515 games</p>')
src = src.replace(
    '<p class="lede">Twenty-one positions you were winning and <em>lost anyway</em>. Two or three before your first game of the day.</p>',
    f'<p class="lede">{TOTAL_NEW + 21} positions you were winning and <em>lost anyway</em>. '
    f'Start with the priority set &mdash; <em>hanging material</em> &mdash; then the endgame groups. '
    f'Two or three before your first game of the day.</p>')
src = src.replace('<span id="ptext">0 / 21</span>', f'<span id="ptext">0 / {TOTAL_NEW + 21}</span>')

# --- protocol note --------------------------------------------------------
src = src.replace(
    "<p style=\"font-size:.9rem;color:var(--muted);margin:.9rem 0\">Order is <strong>C &rarr; B &rarr; A &rarr; D</strong>, top to bottom. Group D last, and read its note first.</p>",
    "<p class=\"warn\"><strong>The P groups are not played out.</strong> They're fifteen-second scans &mdash; read the note at the top of the priority set. The steps above apply to groups C/B/A/D only.</p>\n"
    "<p style=\"font-size:.9rem;color:var(--muted);margin:.9rem 0\">Order is <strong>P &rarr; C &rarr; B &rarr; A &rarr; D</strong>, top to bottom. Group D last, and read its note first.</p>")

# --- nav ------------------------------------------------------------------
navlinks = "".join(f'<a href="#g{t}">{t}</a>' for t, _ in counts)
src = src.replace(
    '<nav class="jump"><a href="#gC">C</a><a href="#gB">B</a><a href="#gA">A</a><a href="#gD">D</a></nav>',
    f'<nav class="jump"><a href="#gP">P</a>{navlinks}'
    '<span class="navsep"></span><a href="#gC">C</a><a href="#gB">B</a><a href="#gA">A</a><a href="#gD">D</a></nav>')

# --- inject sections ahead of group C ------------------------------------
src = src.replace('\n<section class="group" id="gC">', priority + '\n<section class="group" id="gC">', 1)

# --- styles ---------------------------------------------------------------
src = src.replace("footer{margin-top:3rem;", """.gletter.alt{background:var(--flag)}
.navsep{width:.5rem;flex:none}
.tag{font-family:'Roboto Mono',monospace;font-size:.68rem;text-transform:uppercase;
  letter-spacing:.06em;padding:.1rem .35rem;white-space:nowrap}
.tag.t-miss{background:var(--flag);color:var(--paper)}
.tag.t-hung{background:var(--ink);color:var(--paper)}
details.spoil{margin:.15rem 0 .5rem}
details.spoil summary{font-family:'Roboto Mono',monospace;font-size:.72rem;
  text-transform:uppercase;letter-spacing:.08em;color:var(--muted);cursor:pointer;
  list-style:none;padding:.2rem 0}
details.spoil summary::-webkit-details-marker{display:none}
details.spoil summary::before{content:'\\25B8 ';}
details.spoil[open] summary::before{content:'\\25BE ';}
details.spoil p{margin:.2rem 0 .4rem;font-size:.9rem;color:#3A3D2E}
footer{margin-top:3rem;""")

# --- footer + script ------------------------------------------------------
src = src.replace(
    "<span>Positions found by engine review at depth 12, filtered to hold above +1.5 for two more of your moves.</span>",
    "<span>Depth-12 Stockfish over 1,515 rated blitz games. Priority set selected by static exchange evaluation "
    "(unaffected by search depth) and ranked by Lichess win-probability loss; ranking is 98% stable when every "
    "eval beyond &plusmn;5 is clamped, so the depth-12 noise above +5 doesn't move it.</span>")
src = src.replace("var KEY='drills.done.v1', total=21;",
                  f"var KEY='drills.done.v1', total={TOTAL_NEW + 21};")
src = src.replace("if(confirm('Clear all 21 ticks?'))",
                  f"if(confirm('Clear all {TOTAL_NEW + 21} ticks?'))")

open(PAGE, "w").write(src)
print(f"priority drills: {TOTAL_NEW}  (missed {n_miss} / hung {n_hung})")
for t, c in counts:
    print(f"  {t}: {c}")
print("page bytes:", len(src))
