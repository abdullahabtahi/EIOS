"""Builds docs/diagrams/eios-features.svg (24 cm x 10 cm, 100 units per cm).

Issue tree, two levels: one governing question (what a regulated team needs to defend an AI-assisted decision) and
four MECE branches in the order a case travels: Signal, Evidence, Decision, Record. Evidence and Decision are drawn
larger because they carry the claim "trust by construction". Chip colour: solid blue = a Google service, grey = open
source. Run: python3 build_features.py
"""
from html import escape
from pathlib import Path

W, H = 2400, 1000
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CHIP, CANVAS = "#ececec", "#dedfe0", "#f7f7f5"
GBLUE = "#1a56c4"
M, GAP = 30, 44
G, O = "g", "o"

# (number, title, subtitle, features, chips)
BRANCHES = [
    (1, "SIGNAL", "Know what matters", [
        "Alerts ranked into a focused queue",
        "Rings, geo risk and partner churn found by engines",
        "Causal graph, forecast and what-if for executives"],
     [("BigQuery Graph", G), ("scikit-learn", O), ("NetworkX", O)], False, 0.86),
    (2, "EVIDENCE", "See the whole case, cited", [
        "One ontology over contract-checked data",
        "Gemini briefs each role; every figure is checked against an engine",
        "Regulation quoted by sentence number"],
     [("Pub/Sub", G), ("Gemini on Vertex AI", G), ("Agent Search", G), ("DuckDB", O)], True, 1.14),
    (3, "DECISION", "A person holds the key", [
        "AI proposes; no approve tool exists",
        "A signed request that expires; a second person approves",
        "Role-based access; PII tokenised before the model"],
     [("Cloud KMS", G), ("Identity Platform", G), ("Secret Manager", G)], True, 1.14),
    (4, "RECORD", "Prove it later", [
        "Hash-chained decision ledger",
        "Evidence sealed with each approval",
        "SLOs, red-line tests and a restore drill"],
     [("Firestore", G), ("Cloud Storage", G), ("Cloud Trace", G)], False, 0.86),
]

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=30, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


def _greedy(s: str, per: int) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        if cur and len(cur) + 1 + len(word) > per:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur]


def wrap(s: str, width: float, size: float) -> list[str]:
    """Greedy wrap, then narrow the measure until the line count would grow: balanced lines, no orphans."""
    per = max(8, int(width / (size * 0.53)))
    n = len(_greedy(s, per))
    while per > 8 and len(_greedy(s, per - 1)) == n:
        per -= 1
    return _greedy(s, per)


def chip_w(label: str, kind: str, size: float) -> float:
    return len(label) * size * (0.60 if kind == G else 0.56) + 30


def draw_chips(x, y, w, chips, size=22, ch=40, gap=10):
    cx, cy = 0.0, 0.0
    for label, kind in chips:
        cw = chip_w(label, kind, size)
        if cx and cx + cw > w:
            cx, cy = 0.0, cy + ch + gap
        px, py = x + cx, y + cy
        if kind == G:
            add(f'<rect x="{px}" y="{py}" width="{cw}" height="{ch}" rx="{ch / 2}" fill="{GBLUE}"/>')
            text(px + cw / 2, py + ch / 2 + 8, label, size, 600, "#ffffff", "middle")
        else:
            add(f'<rect x="{px}" y="{py}" width="{cw}" height="{ch}" fill="{CHIP}" stroke="#c0c1c4" stroke-width="1.2"/>')
            text(px + cw / 2, py + ch / 2 + 8, label, size, 500, INK, "middle")
        cx += cw + gap


def pill_number(x, y, n, hi):
    add(f'<rect x="{x}" y="{y}" width="64" height="44" rx="22" fill="{INK if hi else CANVAS}" stroke="{INK if hi else "#8a8d93"}" stroke-width="2"/>')
    text(x + 32, y + 31, str(n), 27, 600, "#ffffff" if hi else INK, "middle")


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="24cm" height="10cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

TOP, PH = 34, 800
avail = W - 2 * M - GAP * 3
total_w = sum(b[6] for b in BRANCHES)
x = M
panels = []
for n, title, sub, feats, chips, hi, wt in BRANCHES:
    w = avail * wt / total_w
    panels.append((x, w))
    fill, stroke, sw = ("#ffffff", INK, 3) if hi else (PANEL, RULE, 1.5)
    add(f'<rect x="{x}" y="{TOP}" width="{w}" height="{PH}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    pill_number(x + 28, TOP + 28, n, hi)
    text(x + 28, TOP + 140, title, 50, 700, INK, spacing=1)
    text(x + 28, TOP + 188, sub, 29, 400, INK2)
    add(f'<line x1="{x + 28}" y1="{TOP + 214}" x2="{x + w - 28}" y2="{TOP + 214}" stroke="{RULE}" stroke-width="2"/>')
    fy = TOP + 268
    for f in feats:
        lines = wrap(f, w - 28 - 28 - 30, 30)
        add(f'<rect x="{x + 28}" y="{fy - 17}" width="12" height="12" fill="{GBLUE if hi else INK2}"/>')
        for i, ln in enumerate(lines):
            text(x + 58, fy + i * 40, ln, 30, 500 if hi else 400, INK)
        fy += len(lines) * 40 + 38
    chip_y = TOP + PH - 28 - 40
    rows = 1
    cx = 0.0
    for label, kind in chips:
        cw = chip_w(label, kind, 22)
        if cx and cx + cw > w - 56:
            rows += 1
            cx = 0.0
        cx += cw + 10
    draw_chips(x + 28, chip_y - (rows - 1) * 50, w - 56, chips)
    x += w + GAP

# flow chevrons between panels
for i in range(3):
    px = panels[i][0] + panels[i][1]
    cy = TOP + 100
    add(f'<path d="M {px + 12} {cy - 22} L {px + GAP - 12} {cy} L {px + 12} {cy + 22}" fill="none" stroke="{INK2}" stroke-width="4" stroke-linejoin="miter"/>')

# bracket under Evidence and Decision
bx1, bx2 = panels[1][0], panels[2][0] + panels[2][1]
by = TOP + PH + 26
add(f'<path d="M {bx1} {by} L {bx1} {by + 22} L {bx2} {by + 22} L {bx2} {by}" fill="none" stroke="{INK}" stroke-width="3"/>')
text((bx1 + bx2) / 2, by + 70, "TRUST BY CONSTRUCTION", 30, 700, INK, "middle", 1.5)
text((bx1 + bx2) / 2, by + 108, "The model explains. It cannot approve, and it cannot show a figure no engine produced.", 27, 400, INK2, "middle")

# legend (right of bracket, left of bracket)
ly = by + 62
lx = panels[3][0]
add(f'<rect x="{lx}" y="{ly - 20}" width="56" height="28" rx="14" fill="{GBLUE}"/>')
text(lx + 70, ly + 2, "Google Cloud service", 24, 400, INK)
add(f'<rect x="{lx}" y="{ly + 22}" width="46" height="28" fill="{CHIP}" stroke="#c0c1c4" stroke-width="1.2"/>')
text(lx + 70, ly + 46, "Open source", 24, 400, INK)

add("</svg>")
Path(__file__).with_name("eios-features.svg").write_text("\n".join(out))
print("ok")
