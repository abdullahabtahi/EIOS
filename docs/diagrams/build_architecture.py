"""Builds docs/diagrams/eios-architecture.svg (24 cm x 10 cm, 100 units per cm).

Every component, Google Cloud service and path comes from EIOS/src, EIOS/infra and docs/agent-architecture.md
(the same sources as EIOS/web-prototype/src/components/landing/data/architecture.ts). Run: python3 build_architecture.py
Blue is reserved for Google Cloud services (solid pills and the platform strip); icon tiles use other hues.
"""
from html import escape
from pathlib import Path

W, H = 2400, 1000
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CHIP, CANVAS = "#ececec", "#dedfe0", "#f7f7f5"
GBLUE = "#1a56c4"
ONT_BG, ONT_LINE = "#dfe7f6", "#8aa6dd"
AMBER, AMBER_TXT = "#c98a12", "#8a5f08"

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=24, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


def tw(s: str, size: int, k: float = 0.56) -> float:
    return len(s) * size * k


def pill_number(x, y, n):
    add(f'<rect x="{x}" y="{y - 16}" width="52" height="30" rx="15" fill="{CANVAS}" stroke="#8a8d93" stroke-width="1.5"/>')
    text(x + 26, y + 6, str(n), 19, 500, INK, "middle")


def pill(right, y, label):
    """Solid Google Cloud pill straddling the top edge of the element it belongs to."""
    w = 11.4 * len(label) + 28
    add(f'<rect x="{right - w}" y="{y - 25}" width="{w}" height="29" rx="14.5" fill="{GBLUE}"/>')
    text(right - w / 2, y - 4, label, 19, 600, "#ffffff", "middle")


def panel(x, y, w, h, title, n, fill=PANEL, line=RULE, sub=None):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{line}" stroke-width="1.5"/>')
    pill_number(x + 14, y, n)
    text(x + 16, y + 48, title, 28, 500, INK, spacing=0.2)
    if sub:
        text(x + 16, y + 76, sub, 18, 400, INK2)


TILE = {
    "slate": ("#d3e2e6", "#3f7a8a"),
    "purple": ("#dccffa", "#7a56d6"),
    "green": ("#cdeed6", "#2e9e5b"),
    "amber": ("#fbe3b8", "#c98a12"),
    "red": ("#f8d2cf", "#d0443b"),
    "grey": ("#d4d6da", "#5c6068"),
}


def glyph(kind, x, y, c):
    s = 1.8
    if kind == "grid":
        for dx in (0, 11):
            for dy in (0, 11):
                add(f'<rect x="{x + 6 + dx}" y="{y + 6 + dy}" width="8" height="8" fill="none" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "net":
        add(f'<path d="M14 8L6 20H22Z" transform="translate({x} {y + 2})" fill="none" stroke="{c}" stroke-width="{s}"/>')
        for px, py in ((14, 8), (6, 20), (22, 20)):
            add(f'<circle cx="{x + px}" cy="{y + py + 2}" r="3" fill="{c}"/>')
    elif kind == "lines":
        for dy in (8, 14, 20):
            add(f'<path d="M{x + 7} {y + dy}h14" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "db":
        add(f'<ellipse cx="{x + 14}" cy="{y + 9}" rx="8" ry="3.5" fill="none" stroke="{c}" stroke-width="{s}"/>')
        add(f'<path d="M{x + 6} {y + 9}v11c0 2 3.6 3.5 8 3.5s8-1.5 8-3.5v-11" fill="none" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "bolt":
        add(f'<path d="M{x + 15} {y + 5}l-7 11h6l-2 8 8-12h-6z" fill="{c}"/>')
    elif kind == "shield":
        add(f'<path d="M{x + 14} {y + 5}l8 3v7c0 5-3.5 8-8 10-4.5-2-8-5-8-10v-7z" fill="none" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "doc":
        add(f'<path d="M{x + 8} {y + 5}h9l5 5v14h-14z" fill="none" stroke="{c}" stroke-width="{s}"/>')
        add(f'<path d="M{x + 11} {y + 16}h8M{x + 11} {y + 20}h8" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "key":
        add(f'<circle cx="{x + 10}" cy="{y + 14}" r="4.5" fill="none" stroke="{c}" stroke-width="{s}"/>')
        add(f'<path d="M{x + 14.5} {y + 14}h9M{x + 20} {y + 14}v4" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "pin":
        add(f'<path d="M{x + 14} {y + 24}c-6-6-8-9-8-12a8 8 0 0 1 16 0c0 3-2 6-8 12z" fill="none" stroke="{c}" stroke-width="{s}"/>')
        add(f'<circle cx="{x + 14}" cy="{y + 12}" r="2.5" fill="{c}"/>')
    elif kind == "chart":
        for i, hgt in enumerate((7, 12, 17)):
            add(f'<rect x="{x + 7 + i * 6}" y="{y + 23 - hgt}" width="4" height="{hgt}" fill="{c}"/>')


def chip(x, y, w, label, tile="grey", gl="grid", tag=None, h=None, sub=None, fill=CHIP, bold=False):
    h = h or (72 if sub else 54)
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#c0c1c4" stroke-width="1.2"/>')
    bg, fg = TILE[tile]
    ty = y + (h - 36) / 2
    add(f'<rect x="{x + 8}" y="{ty}" width="36" height="36" fill="{bg}" stroke="{fg}" stroke-opacity="0.35" stroke-width="1"/>')
    glyph(gl, x + 12, ty + 4, fg)
    if sub:
        text(x + 58, y + h / 2 - 3, label, 24, 500 if bold else 400)
        text(x + 58, y + h / 2 + 22, sub, 19, 400, INK2)
    else:
        text(x + 58, y + h / 2 + 8, label, 24, 500 if bold else 400)
    if tag:
        pill(x + w - 10, y, tag)
    return y + h


def stack(x, w, y, specs, gap):
    for spec in specs:
        label, tile, gl, tag, sub = spec[:5]
        opts = spec[5] if len(spec) > 5 else {}
        y = chip(x, y, w, label, tile, gl, tag=tag, sub=sub, **opts) + gap
    return y


def arrow(x1, y1, x2, y2, both=False, color="#5d616a", width=3):
    a = x1 + 14 if both else x1
    add(f'<path d="M{a} {y1}L{x2 - 14} {y2}" stroke="{color}" stroke-width="{width}" fill="none"/>')
    add(f'<path d="M{x2} {y2}l-17 -9v18z" fill="{color}"/>')
    if both:
        add(f'<path d="M{x1} {y1}l17 -9v18z" fill="{color}"/>')


# ---------------------------------------------------------------- layout
M = 30
TOP, BOT = 36, 780
WIDTHS = {1: 305, 2: 335, 3: 380, 4: 380, 5: 380, 6: 320}
GUT = 48
P, cur = {}, M
for k in range(1, 7):
    P[k] = (cur, WIDTHS[k])
    cur += WIDTHS[k] + GUT
CW = lambda k: P[k][1] - 24
CX = lambda k: P[k][0] + 12
Y0 = TOP + 108

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="24cm" height="10cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

# 1 Workstations + operators
x, w = P[1]
panel(x, TOP, w, BOT - TOP, "WORKSTATIONS", 1, sub="Next.js on Cloud Run")
ws = (("AML investigator", "slate", "net"), ("Partner manager", "green", "chart"), ("Executive", "purple", "chart"),
      ("Compliance & audit", "amber", "doc"), ("Data operations", "grey", "lines"), ("Geospatial", "red", "pin"))
y = Y0
for lbl, t, g in ws:
    chip(CX(1), y, CW(1), lbl, t, g, tag="BigQuery Graph" if lbl == "Geospatial" else None)
    y += 68
by = y + 12
add(f'<rect x="{CX(1)}" y="{by}" width="{CW(1)}" height="{BOT - 18 - by}" fill="{CANVAS}" stroke="{RULE}" stroke-width="1.2"/>')
pill(CX(1) + CW(1) - 10, by, "Identity Platform")
text(CX(1) + 14, by + 38, "OPERATORS", 20, 500, INK, spacing=0.5)
for i, (r, d) in enumerate((("analyst", "triage and propose"), ("approver", "second signature"), ("compliance_head", "verify the ledger"))):
    text(CX(1) + 14, by + 76 + i * 50, r, 22, 500)
    text(CX(1) + 14, by + 98 + i * 50, d, 18, 400, INK2)

# 2 Gateway + APIs
x, w = P[2]
panel(x, TOP, w, BOT - TOP, "GATEWAY + APIS", 2, sub="Public web, private API")
stack(CX(2), CW(2), Y0, (
    ("Next.js web", "slate", "grid", "Cloud Run", "only public surface"),
    ("FastAPI gateway", "slate", "lines", "Cloud Run", "private, rate-limited"),
    ("Token check", "green", "shield", "Identity Platform", "role bound to principal"),
    ("Evidence replay", "amber", "doc", None, "re-derives a bundle"),
    ("Telemetry", "grey", "chart", "Cloud Trace", "no prompt text kept"),
), 36)

# 3 Agents
x, w = P[3]
panel(x, TOP, w, BOT - TOP, "AGENTS · GOOGLE ADK", 3, sub="One LoopAgent per workstation")
LOOP_H = 330
add(f'<rect x="{CX(3)}" y="{Y0 - 6}" width="{CW(3)}" height="{LOOP_H}" fill="{CANVAS}" stroke="#8a8d93" stroke-width="1.5" stroke-dasharray="8 6"/>')
text(CX(3) + 14, Y0 + 24, "ADK LoopAgent", 20, 500, INK, spacing=0.3)
text(CX(3) + CW(3) - 14, Y0 + 24, "max 3 passes", 18, 400, INK2, "end")
stack(CX(3) + 14, CW(3) - 28, Y0 + 52, (
    ("Prefetcher", "slate", "bolt", None, "calls the selected tool", {"h": 62}),
    ("Drafter · Gemini", "purple", "net", "Vertex AI", "writes from tool results", {"h": 62}),
    ("Assembler", "green", "shield", None, "deterministic, fails closed", {"h": 62, "bold": True}),
), 24)
stack(CX(3), CW(3), Y0 - 6 + LOOP_H + 34, (
    ("Model Armor", "red", "shield", "Model Armor", "screens prompt and reply", {"h": 62}),
    ("Sessions + briefs", "amber", "db", "Firestore", "ADK session service", {"h": 62}),
    ("Regulation search", "slate", "doc", "Agent Search", "quoted by sentence", {"h": 62}),
), 30)

# 4 Ontology
x, w = P[4]
panel(x, TOP, w, BOT - TOP, "ONTOLOGY", 4, fill=ONT_BG, line=ONT_LINE, sub="The only way in")
PORT_H = 82
chip(CX(4), Y0, CW(4), "Governed tool port", "slate", "key", h=PORT_H, sub="28 typed, scoped capabilities", fill="#c5d5f3", bold=True)
text(CX(4) + 6, Y0 + PORT_H + 32, "No approve or execute tool exists.", 20, 500, INK)
y4 = Y0 + PORT_H + 64
ACTION_Y = None
for lbl, t, g, tag, sub, bold in (("Metric registry", "slate", "lines", None, "one definition per metric", False),
                                    ("Entity graph", "purple", "net", "BigQuery Graph", "GQL queries, hubs collapsed", False),
                                    ("Metric auditor", "green", "shield", None, "numbers must trace to a tool", False),
                                    ("Action Intents", "amber", "bolt", None, "signed, expiring proposals", True)):
    end = chip(CX(4), y4, CW(4), lbl, t, g, tag=tag, sub=sub, h=62, bold=bold)
    if lbl == "Action Intents":
        ACTION_Y = y4 + 31
    y4 = end + 28
rb = y4 - 4
add(f'<rect x="{CX(4)}" y="{rb}" width="{CW(4)}" height="{BOT - 18 - rb}" fill="{CANVAS}" stroke="{ONT_LINE}" stroke-width="1.2"/>')
text(CX(4) + 14, rb + 34, "Red lines RL-1 to RL-7", 22, 500)
text(CX(4) + 14, rb + 60, "models never compute or write", 18, 400, INK2)

# 5 Logic + data
x, w = P[5]
panel(x, TOP, w, BOT - TOP, "LOGIC · ENGINES", 5, sub="Deterministic. Models never compute.")
y = stack(CX(5), CW(5), Y0, (
    ("Alert triage, typologies", "slate", "lines", None, None, {"h": 50}),
    ("Churn hazard", "green", "chart", None, None, {"h": 50}),
    ("Causal SCM", "amber", "net", None, None, {"h": 50}),
    ("Forecast + what-if", "grey", "chart", None, None, {"h": 50}),
), 24)
text(CX(5) + 4, y + 22, "DATA SOURCES", 20, 500, INK, spacing=0.5)
stack(CX(5), CW(5), y + 48, (
    ("Seeded worlds", "grey", "db", None, None, {"h": 50}),
    ("Reference + IP intel", "slate", "db", "BigQuery", None, {"h": 50}),
    ("Regulation corpus", "amber", "doc", "Agent Search", None, {"h": 50}),
    ("Ingestion, DuckDB state", "green", "bolt", "Pub/Sub", None, {"h": 50}),
), 24)

# 6 Systems of action + key
x, w = P[6]
panel(x, TOP, w, BOT - TOP, "SYSTEMS OF ACTION", 6, sub="Agents propose, people approve")
ACT0 = Y0 + 36
stack(CX(6), CW(6), Y0, (
    ("Intent hub", "amber", "bolt", None, "validates and signs", {"h": 66}),
    ("Cloud KMS signer", "red", "key", "Cloud KMS", "ECDSA P-256", {"h": 66}),
    ("Four-eyes approval", "green", "shield", "Firestore", "proposer cannot approve", {"h": 66}),
    ("WORM ledger", "slate", "lines", "Firestore", "SHA-256 hash chain", {"h": 66}),
    ("Evidence bundles", "grey", "doc", None, "id is the content hash", {"h": 66}),
), 30)
ky = BOT - 18 - 150
add(f'<rect x="{CX(6)}" y="{ky}" width="{CW(6)}" height="150" fill="{CANVAS}" stroke="{RULE}" stroke-width="1.2"/>')
text(CX(6) + 14, ky + 34, "KEY", 19, 500, INK, spacing=0.6)
add(f'<rect x="{CX(6) + 14}" y="{ky + 50}" width="64" height="26" rx="13" fill="{GBLUE}"/>')
text(CX(6) + 94, ky + 70, "Google Cloud service", 19, 400, INK)
add(f'<path d="M{CX(6) + 14} {ky + 102}h52" stroke="#5d616a" stroke-width="3"/><path d="M{CX(6) + 80} {ky + 102}l-17 -9v18z" fill="#5d616a"/>')
text(CX(6) + 94, ky + 109, "request and reply", 19, 400, INK)
add(f'<path d="M{CX(6) + 14} {ky + 134}h52" stroke="{AMBER}" stroke-width="3"/><path d="M{CX(6) + 80} {ky + 134}l-17 -9v18z" fill="{AMBER}"/>')
text(CX(6) + 94, ky + 141, "propose, then sign", 19, 400, INK)

# flows
gx = lambda k: (P[k][0] + P[k][1] + 2, P[k + 1][0] - 2)
arrow(*gx(1)[:1], Y0 + 27, gx(1)[1], Y0 + 27, both=True)
arrow(*gx(2)[:1], Y0 + 74 + 36 + 36, gx(2)[1], Y0 + 74 + 36 + 36, both=True)
arrow(*gx(3)[:1], Y0 + PORT_H // 2, gx(3)[1], Y0 + PORT_H // 2, both=True)
# panel 4 -> 5: one arrow into a bracket that spans every engine and data source
rx = P[4][0] + P[4][1]
bx = P[5][0] - 12
arrow(rx + 2, Y0 + PORT_H // 2, bx + 2, Y0 + PORT_H // 2, both=True)
add(f'<path d="M{bx} {Y0 + 14}V{BOT - 36}" stroke="#5d616a" stroke-width="3" fill="none"/>')
# propose path: Action Intents -> under the engines -> Intent hub
pb = BOT + 26
ax = rx + 8
add(f'<path d="M{rx} {ACTION_Y}H{ax}V{pb}H{P[6][0] - 16}V{ACT0}H{P[6][0] - 12}" stroke="{AMBER}" stroke-width="3.2" fill="none"/>')
add(f'<path d="M{P[6][0] - 1} {ACT0}l-17 -9v18z" fill="{AMBER}"/>')
text((rx + P[6][0]) / 2, pb - 8, "propose, then sign, then ledger", 19, 600, AMBER_TXT, "middle")

# security + platform strip
sy = 836
add(f'<rect x="{M}" y="{sy}" width="{W - 2 * M}" height="{H - M - sy}" fill="{PANEL}" stroke="{RULE}" stroke-width="1.5"/>')
pill_number(M + 14, sy, 7)
text(M + 84, sy + 40, "SECURITY, PLATFORM & OBSERVABILITY ON GOOGLE CLOUD", 24, 500, INK, spacing=0.2)
items = (("Model Armor", "screens prompts"), ("Identity Platform", "operator sign-in"), ("Cloud KMS", "signs intents"),
         ("Secret Manager", "HMAC salt, keys"), ("Workload Identity Federation", "CI without keys"),
         ("Artifact Registry + Cloud Build", "images by digest"), ("Cloud Run", "web public, API private"), ("Cloud Trace", "spans per turn"))
inner = W - 2 * M - 28
need = [max(tw(n, 22), tw(r, 18, 0.5)) + 40 for n, r in items]
gap = (inner - sum(need)) / (len(items) - 1)
cx = M + 14
for (name, role), wd in zip(items, need):
    add(f'<rect x="{cx}" y="{sy + 60}" width="{wd}" height="76" fill="{CHIP}" stroke="#c0c1c4" stroke-width="1.2"/>')
    add(f'<rect x="{cx}" y="{sy + 60}" width="6" height="76" fill="{GBLUE}"/>')
    text(cx + 20, sy + 94, name, 22, 500, INK)
    text(cx + 20, sy + 120, role, 18, 400, INK2)
    cx += wd + gap

add("</svg>")
Path(__file__).with_name("eios-architecture.svg").write_text("\n".join(out))
print("ok")
