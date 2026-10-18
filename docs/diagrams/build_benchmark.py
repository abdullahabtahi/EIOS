"""Builds docs/diagrams/eios-benchmark.svg (24 cm x 10 cm, 100 units per cm).

Every number is a `[MEASURED]` result on the synthetic seeded worlds, taken from the repo as of 2026-10-18:
  live eval  EIOS/evals/reports/live_final (246 live turns, Gemini 3.5 Flash-Lite, git 99f29ba): pass counts and
             faithfulness from report.json; median and p95 latency recomputed from records.jsonl
  held-out   EIOS/evals/reports/live_sealed (7 cases x 3 repeats, run once)
  engines    docs/executive-engine.md, docs/operations-engine.md, docs/geospatial-milestones.md,
             docs/operations-engine.md (partner lead time)
  web        docs/evidence/cloud-run-performance-cwv-report.md (one page, one machine)
  safety     docs/evidence/financial-redteam-audit.md, README (Model Armor 1 of 15)
Not used on purpose: evals/reports/baseline_benchmarks.json (hardcoded constants, not a measurement).
Run: python3 build_benchmark.py
"""
from html import escape
from pathlib import Path

W, H = 2400, 1000
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CANVAS = "#ececec", "#f7f7f5"
GBLUE = "#1a56c4"
M, GAP = 40, 28

# (title, subtitle, [(number, label)])
COLUMNS = [
    ("ANSWER QUALITY", "246 live turns on Gemini", [
        ("200 / 213", "verdicts passed"),
        ("96.8%", "of figures traced to an engine result"),
        ("40 / 42", "on the held-out set, run once")]),
    ("SPEED", "Same live run, and the deployed app", [
        ("2.7 s", "median turn, 4.6 s at p95, 0 timeouts"),
        ("< 1 ms", "what-if shock, against a 200 ms budget"),
        ("1.7 s", "page load (LCP) on Cloud Run, CLS 0.006")]),
    ("ENGINES VS PLANTED TRUTH", "Synthetic worlds with a known answer", [
        ("0.74×", "forecast error vs a naive guess; 90% interval held 87%"),
        ("1.5%", "largest error in the causal fit"),
        ("1.00 / 0.99", "precision and recall, ring lens")]),
    ("SAFETY AND INTEGRITY", "Checks the system enforces", [
        ("15 / 15", "red-team probes passed (a small set)"),
        ("11 / 11", "planted data breaches quarantined, 0 healthy events refused"),
        ("2,807 / 2,807", "rows restored in the recovery drill")]),
]

# (figure, what it is)
MISSES = [
    ("13", "of 213 verdicts failed; the reasons are published"),
    ("20–33%", "of eval turns ran on fixture data, not the engines"),
    ("Not measured", "cost per turn and time saved per case"),
    ("No load test", "Cloud Run under concurrent users is untested"),
]

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=28, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


def wrap(s: str, width: float, size: float) -> list[str]:
    per = max(8, int(width / (size * 0.53)))
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > per:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur]


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="24cm" height="10cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

text(M, 80, "Measured, not claimed: 246 live turns, 96.8% of figures traced to an engine.", 54, 700, INK)
text(M, 122, "Gemini 3.5 Flash-Lite on Google Cloud, 18 October. Synthetic seeded worlds, not production data. The limits are on the slide.", 27, 400, INK2)

TOP, PH = 150, 540
cw = (W - 2 * M - 3 * GAP) / 4
for i, (title, sub, metrics) in enumerate(COLUMNS):
    x = M + i * (cw + GAP)
    add(f'<rect x="{x}" y="{TOP}" width="{cw}" height="{PH}" fill="{PANEL}" stroke="{RULE}" stroke-width="1.5"/>')
    text(x + 26, TOP + 50, title, 30, 700, INK, spacing=1.2)
    text(x + 26, TOP + 86, sub, 23, 400, INK2)
    add(f'<line x1="{x + 26}" y1="{TOP + 108}" x2="{x + cw - 26}" y2="{TOP + 108}" stroke="{RULE}" stroke-width="2"/>')
    y = TOP + 180
    for num, label in metrics:
        text(x + 26, y, num, 68, 700, GBLUE)
        for j, ln in enumerate(wrap(label, cw - 52, 24)):
            text(x + 26, y + 36 + j * 29, ln, 24, 400, INK)
        y += 108 + (29 if len(wrap(label, cw - 52, 24)) > 1 else 0) + 8

# misses strip
my = TOP + PH + 24
mh = H - 46 - my
add(f'<rect x="{M}" y="{my}" width="{W - 2 * M}" height="{mh}" fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
text(M + 28, my + 46, "KNOWN LIMITS", 28, 700, INK, spacing=1.5)
text(M + 28 + 330, my + 46, "Published, not hidden", 25, 400, INK2)
mw = (W - 2 * M - 56) / len(MISSES)
for i, (fig, what) in enumerate(MISSES):
    x = M + 28 + i * mw
    if i:
        add(f'<line x1="{x - 18}" y1="{my + 70}" x2="{x - 18}" y2="{my + mh - 20}" stroke="{RULE}" stroke-width="2"/>')
    text(x, my + 118, fig, 46, 700, INK)
    for j, ln in enumerate(wrap(what, mw - 40, 24)):
        text(x, my + 152 + j * 29, ln, 24, 400, INK2)

text(M, H - 14, "Sources: live and held-out runs in evals/reports, engine, operations and geo docs, Cloud Run web-vitals report (one page, one machine). Counts are verdicts, not turns.", 19, 400, INK2)

add("</svg>")
Path(__file__).with_name("eios-benchmark.svg").write_text("\n".join(out))
print("ok")
