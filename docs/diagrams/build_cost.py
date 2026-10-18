"""Builds docs/diagrams/eios-cost.svg (24 cm x 10 cm, 100 units per cm).

The cost of the system as built: every Google Cloud service EIOS runs on (from EIOS/infra, the Dockerfiles and the
Cloud Build config), grouped by the four jobs of the feature diagram, each with what it is billed on and a monthly
estimate, plus the guard the build puts on that spend. Scenario: an illustrative mid-size APAC bank, 50,000 alerts a
year, 2,500 investigated cases (about 208 a month, 8 copilot turns each). Model prices are October 2026 web figures
and the token counts, team size and rates are assumptions. Model Armor is not priced: no price was found. The
slide claims a break-even, not a saving: time to disposition is not measured yet (lighthouse M1).
Run: python3 build_cost.py
"""
from html import escape
from pathlib import Path

W, H = 2400, 1000
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CANVAS = "#ececec", "#f7f7f5"
GBLUE = "#1a56c4"
M, GAP = 40, 28

# Services shown, one by one: Gemini on Vertex AI, Agent Search, Model Armor, BigQuery, BigQuery Graph, Firestore,
# Pub/Sub, Cloud Storage, Cloud KMS, Secret Manager, Identity Platform, Cloud Run, Artifact Registry, Cloud Build,
# Cloud Logging, Cloud Monitoring, Cloud Trace.
N_SERVICES = 17

# (service, billed on, low $/month, high $/month, label); low is None when no price was found
COLUMNS = [
    ("THINK", "Agents and models", [
        ("Google ADK", "open source agent framework", 0, 0, "$0"),
        ("Gemini on Vertex AI", "per token, 8 turns a case", 13, 58, "$13–58"),
        ("Agent Search", "per query, about 2 a case", 1, 1, "≈ $1"),
        ("Model Armor", "per screened turn", None, None, "not priced")],
     "One redraft, then fail closed. Rate limit per operator."),
    ("DATA", "Stores, streams and graph", [
        ("BigQuery", "storage, 100 MB cap per query", 0.5, 1, "< $1"),
        ("BigQuery Graph", "Enterprise slots, baseline 0", 0, 25, "≤ $25"),
        ("Firestore", "reads and writes per turn", 0.5, 1, "< $1"),
        ("Pub/Sub, Cloud Storage", "per GiB", 1, 2, "< $2")],
     "An idle graph reservation costs nothing. 30 s query timeout."),
    ("TRUST", "Identity, keys, secrets", [
        ("Cloud KMS", "one key, per signature", 0.1, 1, "< $1"),
        ("Secret Manager", "per secret version", 0.1, 1, "< $1"),
        ("Identity Platform", "first 50,000 users free", 0, 0, "$0")],
     "Requests expire in 15 min. The AI has no approve tool."),
    ("RUN", "Runtime, deploy, observe", [
        ("Cloud Run", "1 vCPU, 2 GiB, one warm instance", 23, 93, "$23–93"),
        ("Artifact Registry, Cloud Build", "per GiB, per build minute", 1, 2, "< $2"),
        ("Logging, Monitoring, Trace", "above the free tier", 0, 5, "< $5")],
     "Budget alerts at 50, 80 and 100%. Images deploy by digest."),
]

BUILD, PEOPLE, CLOUD = 750_000, 810_000, 6_000
TOTAL = BUILD + PEOPLE + CLOUD
YEARLY = TOTAL / 3
REVIEW_LOW, REVIEW_HIGH = 1_500_000, 3_500_000
BE_LOW, BE_HIGH = YEARLY / REVIEW_HIGH, YEARLY / REVIEW_LOW

priced = [r for c in COLUMNS for r in c[2] if r[2] is not None]
LO = sum(r[2] for r in priced)
HI = sum(r[3] for r in priced)

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=28, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="24cm" height="10cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

text(M, 80, f"{N_SERVICES} Google Cloud services, under $200 a month. The real cost is people.", 54, 700, INK)
text(M, 122, "What it costs to run EIOS as built. Illustrative: a mid-size APAC bank, 50,000 alerts a year, about 208 investigated cases a month.", 27, 400, INK2)

TOP, PH = 150, 572
cw = (W - 2 * M - 3 * GAP) / 4
for i, (title, sub, rows, guard) in enumerate(COLUMNS):
    x = M + i * (cw + GAP)
    add(f'<rect x="{x}" y="{TOP}" width="{cw}" height="{PH}" fill="{PANEL}" stroke="{RULE}" stroke-width="1.5"/>')
    text(x + 26, TOP + 52, title, 36, 700, INK, spacing=1.2)
    text(x + 26, TOP + 88, sub, 25, 400, INK2)
    add(f'<line x1="{x + 26}" y1="{TOP + 108}" x2="{x + cw - 26}" y2="{TOP + 108}" stroke="{RULE}" stroke-width="2"/>')
    y = TOP + 146
    for name, meter, lo, hi, label in rows:
        if name == "Google ADK":
            add(f'<rect x="{x + 26}" y="{y - 22}" width="14" height="14" fill="{INK2}"/>')
        else:
            add(f'<rect x="{x + 26}" y="{y - 22}" width="14" height="14" rx="7" fill="{GBLUE}"/>')
        text(x + 54, y, name, 27, 700, INK)
        text(x + cw - 26, y + 2, label, 30, 700, INK2 if lo is None else GBLUE, "end")
        text(x + 54, y + 30, meter, 21, 400, INK2)
        y += 84
    gy = TOP + PH - 100
    add(f'<rect x="{x + 26}" y="{gy}" width="{cw - 52}" height="76" fill="#ffffff" stroke="{RULE}" stroke-width="1.5"/>')
    add(f'<path d="M {x + 42} {gy + 28} l 8 8 l 15 -17" fill="none" stroke="{GBLUE}" stroke-width="4"/>')
    lines, cur = [], ""
    for wd in guard.split():
        if cur and len(cur) + 1 + len(wd) > 31:
            lines.append(cur)
            cur = wd
        else:
            cur = f"{cur} {wd}".strip()
    lines.append(cur)
    for j, ln in enumerate(lines[:2]):
        text(x + 78, gy + 30 + j * 28, ln, 21, 500, INK)

# bottom band: the three numbers
by = TOP + PH + 24
bh = 186
add(f'<rect x="{M}" y="{by}" width="{W - 2 * M}" height="{bh}" fill="#ffffff" stroke="{INK}" stroke-width="2.5"/>')
c1, c2, c3 = M + 28, M + 640, M + 1190
text(c1, by + 98, f"${round(LO)}–{round(HI)}", 80, 700, GBLUE)
text(c1, by + 136, "a month, the whole stack", 28, 500, INK)
text(c1, by + 168, "excluding Model Armor, not priced", 21, 400, INK2)
add(f'<line x1="{c2 - 28}" y1="{by + 24}" x2="{c2 - 28}" y2="{by + bh - 24}" stroke="{RULE}" stroke-width="2"/>')
text(c2, by + 98, "$0.07–0.29", 80, 700, GBLUE)
text(c2, by + 136, "variable cost per case", 28, 500, INK)
text(c2, by + 168, "Gemini is over 95% of it", 21, 400, INK2)
add(f'<line x1="{c3 - 28}" y1="{by + 24}" x2="{c3 - 28}" y2="{by + bh - 24}" stroke="{RULE}" stroke-width="2"/>')

# 3-year stacked bar
sx, sw, sy, sh = c3, W - M - 28 - c3, by + 66, 52
text(sx, by + 42, "3-YEAR COST, ABOUT $1.6M", 24, 700, INK, spacing=1.2)
bw = sw * BUILD / TOTAL
pw = sw * PEOPLE / TOTAL
add(f'<rect x="{sx}" y="{sy}" width="{bw}" height="{sh}" fill="{INK}"/>')
add(f'<rect x="{sx + bw}" y="{sy}" width="{pw}" height="{sh}" fill="{INK2}"/>')
add(f'<rect x="{sx + bw + pw}" y="{sy}" width="{max(3.0, sw * CLOUD / TOTAL)}" height="{sh}" fill="{GBLUE}"/>')
text(sx + 14, sy + 35, "Build, once  48%", 26, 600, "#ffffff")
text(sx + bw + 14, sy + 35, "Run people  52%", 26, 600, "#ffffff")
add(f'<line x1="{sx + sw - 1}" y1="{sy + sh}" x2="{sx + sw - 1}" y2="{sy + sh + 20}" stroke="{GBLUE}" stroke-width="3"/>')
text(sx + sw, sy + sh + 42, "Cloud 0.4%", 24, 700, GBLUE, "end")
text(sx, sy + sh + 42, f"Pays back at a {round(BE_LOW * 100)}–{round(BE_HIGH * 100)}% cut in review effort, measured next", 23, 500, INK)

text(M, H - 12, "Illustrative estimates. Prices: Google Cloud pricing pages and October 2026 web figures. Token counts, team size (6 for 24 weeks, then 3 FTE) and rates are assumptions. Review cost is a vendor range.", 19, 400, INK2)

add("</svg>")
Path(__file__).with_name("eios-cost.svg").write_text("\n".join(out))
print("ok", round(LO, 1), round(HI, 1), round(YEARLY), round(BE_LOW * 100, 1), round(BE_HIGH * 100, 1))
