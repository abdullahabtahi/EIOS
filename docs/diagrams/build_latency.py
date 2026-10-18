"""Builds docs/diagrams/eios-latency.svg (10 cm x 11 cm, 100 units per cm): the visual for the latency slide.

One copilot turn, to scale. Sources, all in docs/assistant-latency.md:
  before  median first turn 10.4 s: the model 3.4 to 4.4 s, Firestore session writes 5.2 to 6.2 s (6 to 8 awaited
          transactions, one per ADK event), Model Armor 0.7 to 0.9 s. Drawn at 3.8 / 5.8 / 0.8 s, which sum to 10.4 s.
  after   median first turn 4.2 s once the session writes go behind the reply (the writes still happen, in order,
          after the answer is returned).
  now     live_final: median 2.7 s and p95 4.6 s over 246 live turns (recomputed from records.jsonl). A separate run,
          so it is drawn as an outline, not as a third step of the same probe.
The individual write spans are drawn schematically. Run: python3 build_latency.py
"""
from html import escape
from pathlib import Path

W, H = 1000, 1100
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CANVAS = "#ececec", "#f7f7f5"
GBLUE, GLIGHT = "#1a56c4", "#7da2e6"
X0, SCALE = 50, 80  # 80 units per second

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=28, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


def sx(seconds: float) -> float:
    return X0 + seconds * SCALE


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="10cm" height="11cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

text(X0, 70, "Where the time went", 50, 700, INK)
text(X0, 112, "One copilot turn, drawn to scale", 27, 400, INK2)

BH = 96

# Row A: before
ya = 190
text(X0, ya, "Before", 34, 700, INK)
text(W - X0, ya, "10.4 s", 52, 700, INK, "end")
by = ya + 30
add(f'<rect x="{sx(0)}" y="{by}" width="{0.8 * SCALE}" height="{BH}" fill="{GLIGHT}"/>')
add(f'<rect x="{sx(0.8)}" y="{by}" width="{3.8 * SCALE}" height="{BH}" fill="{GBLUE}"/>')
w0 = sx(4.6)
n, gap = 7, 5
seg = (5.8 * SCALE - gap * (n - 1)) / n
for i in range(n):
    add(f'<rect x="{w0 + i * (seg + gap)}" y="{by}" width="{seg}" height="{BH}" fill="{INK}"/>')
text(sx(0.8) + 18, by + 58, "Model 3.8 s", 28, 600, "#ffffff")
text(sx(0), by + BH + 30, "Armor 0.8 s", 22, 500, INK2)
text(sx(10.4), by + BH + 30, "Firestore session writes 5.8 s", 24, 700, INK, "end")
text(sx(10.4), by + BH + 58, "6 to 8 transactions, each awaited", 22, 400, INK2, "end")

# Row B: after write-behind
yb = 450
text(X0, yb, "After write-behind sessions", 34, 700, INK)
text(W - X0, yb, "4.2 s", 52, 700, GBLUE, "end")
by = yb + 30
add(f'<rect x="{sx(0)}" y="{by}" width="{4.2 * SCALE}" height="{BH}" fill="{GBLUE}"/>')
text(sx(0) + 18, by + 58, "Model and screening", 28, 600, "#ffffff")
add(f'<rect x="{sx(4.2)}" y="{by}" width="{6.2 * SCALE}" height="{BH}" fill="none" stroke="{INK2}" stroke-width="3" stroke-dasharray="12 8"/>')
text(sx(4.2) + 24, by + 44, "Writes still happen, in order,", 23, 500, INK2)
text(sx(4.2) + 24, by + 74, "after the reply is sent", 23, 500, INK2)
text(sx(4.2), by + BH + 30, "Answer returned", 22, 700, GBLUE)

# Row C: now
yc = 720
text(X0, yc, "Now, over 246 live turns", 34, 700, INK)
text(W - X0, yc, "2.7 s", 52, 700, GBLUE, "end")
by = yc + 30
add(f'<rect x="{sx(0)}" y="{by}" width="{2.7 * SCALE}" height="{BH}" fill="#dbe6fa" stroke="{GBLUE}" stroke-width="3"/>')
text(sx(0) + 18, by + 58, "Median", 28, 600, GBLUE)
add(f'<line x1="{sx(4.6)}" y1="{by - 8}" x2="{sx(4.6)}" y2="{by + BH + 8}" stroke="{INK}" stroke-width="4"/>')
text(sx(4.6) + 14, by + 58, "p95 4.6 s", 26, 700, INK)
text(sx(0), by + BH + 30, "A separate run, so drawn as an outline", 22, 400, INK2)

# axis
ay = 930
add(f'<line x1="{sx(0)}" y1="{ay}" x2="{sx(10.4)}" y2="{ay}" stroke="{INK2}" stroke-width="2"/>')
for s in (0, 2, 4, 6, 8, 10):
    add(f'<line x1="{sx(s)}" y1="{ay - 8}" x2="{sx(s)}" y2="{ay + 8}" stroke="{INK2}" stroke-width="2"/>')
    text(sx(s), ay + 36, f"{s} s", 22, 400, INK2, "middle")

foot = [
    "Bars 1 and 2: medians from the same probe, a laptop in the Philippines",
    "calling us-central1. Write spans are drawn schematically.",
    "Bar 3: the live evaluation of 18 October, a separate run.",
]
for i, ln in enumerate(foot):
    text(X0, 1006 + i * 28, ln, 20, 400, INK2)

add("</svg>")
Path(__file__).with_name("eios-latency.svg").write_text("\n".join(out))
print("ok")
