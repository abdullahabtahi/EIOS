"""Builds docs/diagrams/eios-process-flow.svg (24 cm x 10 cm, 100 units per cm).

One case, end to end: AML case CR84920 from the engine over the seeded world (figures in
EIOS/web-prototype/src/components/landing/data/ring.ts). Decision rights are from docs/lighthouse.md section 3; the signed
intent, its 15-minute expiry, four-eyes approval and the execution receipt are from
EIOS/src/eios/ontology/actions/intent_hub.py. Run: python3 build_process_flow.py
"""
from html import escape
from pathlib import Path

W, H = 2400, 1000
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CHIP, CANVAS = "#ececec", "#dedfe0", "#f7f7f5"
GBLUE = "#1a56c4"
ONT_BG, ONT_LINE = "#dfe7f6", "#8aa6dd"
AMBER, AMBER_TXT, RED = "#c98a12", "#8a5f08", "#c0392b"
GREY_ARROW = "#5d616a"

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=20, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


def pill(right, y, label, fill=GBLUE, size=19):
    w = 11.4 * len(label) + 28
    add(f'<rect x="{right - w}" y="{y - 25}" width="{w}" height="29" rx="14.5" fill="{fill}"/>')
    text(right - w / 2, y - 4, label, size, 600, "#ffffff", "middle")


def num_pill(x, y, n):
    add(f'<rect x="{x}" y="{y - 16}" width="52" height="32" rx="16" fill="{CANVAS}" stroke="#8a8d93" stroke-width="1.5"/>')
    text(x + 26, y + 7, str(n), 20, 600, INK, "middle")


TILE = {
    "slate": ("#d3e2e6", "#3f7a8a"), "purple": ("#dccffa", "#7a56d6"), "green": ("#cdeed6", "#2e9e5b"),
    "amber": ("#fbe3b8", "#c98a12"), "red": ("#f8d2cf", "#d0443b"), "grey": ("#d4d6da", "#5c6068"), "person": ("#ffffff", "#1b1d21"),
}


def glyph(kind, x, y, c):
    s = 1.8
    if kind == "person":
        add(f'<circle cx="{x + 14}" cy="{y + 10}" r="4.6" fill="none" stroke="{c}" stroke-width="{s}"/>')
        add(f'<path d="M{x + 5} {y + 24}c0-6 4-9 9-9s9 3 9 9" fill="none" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "diamond":
        add(f'<path d="M{x + 14} {y + 4}l9 10-9 10-9-10z" fill="{c}"/>')
    elif kind == "net":
        add(f'<path d="M14 8L6 20H22Z" transform="translate({x} {y + 2})" fill="none" stroke="{c}" stroke-width="{s}"/>')
        for px, py in ((14, 8), (6, 20), (22, 20)):
            add(f'<circle cx="{x + px}" cy="{y + py + 2}" r="3" fill="{c}"/>')
    elif kind == "lines":
        for dy in (8, 14, 20):
            add(f'<path d="M{x + 7} {y + dy}h14" stroke="{c}" stroke-width="{s}"/>')
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
    elif kind == "db":
        add(f'<ellipse cx="{x + 14}" cy="{y + 9}" rx="8" ry="3.5" fill="none" stroke="{c}" stroke-width="{s}"/>')
        add(f'<path d="M{x + 6} {y + 9}v11c0 2 3.6 3.5 8 3.5s8-1.5 8-3.5v-11" fill="none" stroke="{c}" stroke-width="{s}"/>')
    elif kind == "chart":
        for i, hgt in enumerate((7, 12, 17)):
            add(f'<rect x="{x + 7 + i * 6}" y="{y + 23 - hgt}" width="4" height="{hgt}" fill="{c}"/>')


def chip(x, y, w, lines, tile, gl, tag=None, h=66, fill=CHIP, stroke="#c0c1c4", sw=1.2, weight=400, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
    bg, fg = TILE[tile]
    ty = y + (h - 36) / 2
    add(f'<rect x="{x + 8}" y="{ty}" width="36" height="36" fill="{bg}" stroke="{fg}" stroke-opacity="0.4" stroke-width="1"/>')
    glyph(gl, x + 12, ty + 4, fg)
    n = len(lines)
    top = y + (h - n * 24) / 2 + 18
    for i, ln in enumerate(lines):
        text(x + 58, top + i * 25, ln, 20, weight)
    if tag:
        pill(x + w - 10, y, tag)


def card(x, y, w, h, title, lines, gl="person", tile="person", gate=False, blocked=False, pill_label=None):
    stroke, sw, dash = ("#8a8d93", 1.4, None)
    if gate:
        stroke, sw = AMBER, 3
    if blocked:
        stroke, sw, dash = RED, 2, "8 6"
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#ffffff" stroke="{stroke}" stroke-width="{sw}"{d}/>')
    bg, fg = TILE["amber"] if gate else (TILE["red"] if blocked else TILE[tile])
    add(f'<rect x="{x + 10}" y="{y + 14}" width="38" height="38" fill="{bg}" stroke="{fg}" stroke-opacity="0.5" stroke-width="1"/>')
    glyph("diamond" if gate else gl, x + 15, y + 19, fg)
    text(x + 62, y + 40, title, 24, 500)
    for i, ln in enumerate(lines):
        text(x + 62, y + 70 + i * 25, ln, 19, 400, INK2)
    if pill_label:
        pill(x + w - 10, y, pill_label, fill=(AMBER if gate else RED))


def varrow(x, y1, y2, both=False, color=GREY_ARROW, width=3):
    up = y2 < y1
    a = y1 + (-14 if up else 14) if both else y1
    b = y2 + (14 if up else -14)
    add(f'<path d="M{x} {a}L{x} {b}" stroke="{color}" stroke-width="{width}"/>')
    add(f'<path d="M{x} {y2}l-9 {17 if up else -17}h18z" fill="{color}"/>')
    if both:
        add(f'<path d="M{x} {y1}l-9 {-17 if up else 17}h18z" fill="{color}"/>')


def harrow(x1, x2, y, color=GREY_ARROW, width=3):
    add(f'<path d="M{x1} {y}L{x2 - 14} {y}" stroke="{color}" stroke-width="{width}"/>')
    add(f'<path d="M{x2} {y}l-17 -9v18z" fill="{color}"/>')


# ---------------------------------------------------------------- geometry
M = 30
LABEL_W = 280
CW, GAP = 384, 28
X0 = M + LABEL_W + 20
COLS = [X0 + i * (CW + GAP) for i in range(5)]
HEAD_Y = 30
L1 = (126, 150)
L2 = (L1[0] + L1[1] + 24, 330)
L3 = (L2[0] + L2[1] + 24, 240)
FOOT_Y = L3[0] + L3[1] + 16
X_END = COLS[-1] + CW

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="24cm" height="10cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

# lanes
for (y, h), fill, line in ((L1, PANEL, RULE), (L2, ONT_BG, ONT_LINE), (L3, PANEL, RULE)):
    add(f'<rect x="{M}" y="{y}" width="{X_END - M + 12}" height="{h}" fill="{fill}" stroke="{line}" stroke-width="1.5"/>')

# header
text(M + 6, HEAD_Y + 38, "WHO USES EIOS", 24, 500, INK, spacing=0.3)
text(M + 6, HEAD_Y + 68, "People above and below, EIOS between", 18, 400, INK2)
STAGES = (("An alert fires", "what starts it"), ("EIOS builds the case", "how EIOS helps"), ("A person decides", "what the human does"),
          ("A second person approves", "who else must agree"), ("The proof is sealed", "what is left behind"))
for i, (name, q) in enumerate(STAGES):
    num_pill(COLS[i], HEAD_Y + 30, i + 1)
    text(COLS[i] + 66, HEAD_Y + 38, name, 26, 600, INK)
    text(COLS[i] + 66, HEAD_Y + 68, q, 19, 400, INK2)
add(f'<path d="M{COLS[0]} {HEAD_Y + 86}H{X_END}" stroke="#8a8d93" stroke-width="2"/>')
add(f'<path d="M{X_END} {HEAD_Y + 86}l-14 -7v14z" fill="#8a8d93"/>')

# lane labels
def lane_label(y, h, blocks):
    cy = y + 14
    for title, lines in blocks:
        bh = 12 + 34 + len(lines) * 24 + 10
        add(f'<rect x="{M + 10}" y="{cy}" width="{LABEL_W - 10}" height="{bh}" fill="#ffffff" stroke="#8a8d93" stroke-width="1.2"/>')
        text(M + 24, cy + 38, title, 25, 500)
        for i, ln in enumerate(lines):
            text(M + 24, cy + 64 + i * 24, ln, 19, 400, INK2)
        cy += bh + 12


lane_label(L1[0], L1[1], [("Investigator", ["AML analyst. Reviews the", "dossier, edits the draft,", "proposes the action."])])
lane_label(L2[0], L2[1], [("EIOS", ["The AI system on Google", "Cloud. It reads, assembles,", "drafts and proposes. It never", "approves, signs or files."])])
lane_label(L3[0], L3[1], [("Approver", ["Second officer. Authorises,", "never initiates."]),
                          ("Compliance head", ["Owns thresholds, signs off", "the SAR, verifies the ledger."])])

# human cards
c1y, c3y = L1[0] + 14, L3[0] + 14
card(COLS[0], c1y, CW, L1[1] - 28, "Opens the top alert", ["Case CR84920 is first", "in the queue."])
card(COLS[1], c1y, CW, L1[1] - 28, "Reads one cited screen", ["Not five systems. Every", "number shows its source."])
card(COLS[2], c1y, CW, L1[1] - 28, "Reviews, edits, decides", ["Edits the report and asks", "to hold the withdrawals."], gate=True, pill_label="HUMAN DECISION")
card(COLS[3], c1y, CW, L1[1] - 28, "Cannot approve own hold", ["Two people are required:", "the proposer can\u2019t approve."], blocked=True, pill_label="BLOCKED BY DESIGN")
card(COLS[0], c3y, CW, L3[1] - 28, "Sets what triggers alerts", ["The compliance head owns", "the alert thresholds."])
card(COLS[3], c3y, CW, L3[1] - 28, "Approves the hold", ["A second officer reviews the", "evidence and signs off.", "It expires if nobody acts."], gate=True, pill_label="HUMAN DECISION")
card(COLS[4], c3y, CW, L3[1] - 28, "Verifies and signs off", ["Checks the record is intact", "and signs off the report.", "Filing stays a human decision."])

# EIOS cells
ey, eh = L2[0] + 10, L2[1] - 20
for x in COLS:
    add(f'<rect x="{x}" y="{ey}" width="{CW}" height="{eh}" fill="{CANVAS}" stroke="{ONT_LINE}" stroke-width="1.5"/>')
CWI = CW - 24
ix = lambda i: COLS[i] + 12
y0 = ey + 36
GAPY = 30

def col(i, spec):
    y = y0
    for s in spec:
        kind = s[0]
        if kind == "chip":
            _, lines, tile, gl, tag, h = s
            chip(ix(i), y, CWI, lines, tile, gl, tag=tag, h=h)
        elif kind == "alert":
            _, lines, h = s
            chip(ix(i), y, CWI, lines, "amber", "bolt", h=h, fill="#fff6e4", stroke=AMBER, sw=3, weight=500)
            pill(ix(i) + CWI - 10, y, "TRIGGER", fill=AMBER)
        elif kind == "rule":
            _, lines, h = s
            chip(ix(i), y, CWI, lines, "red", "shield", h=h, fill="#ffffff", stroke="#8a8d93", sw=1.6, weight=500)
        y += s[-1] + GAPY

col(0, [("chip", ["Every transaction is", "checked on arrival"], "green", "bolt", "Pub/Sub", 60),
        ("chip", ["Detection ranks every", "alert, riskiest first"], "slate", "chart", None, 60),
        ("alert", ["$8,000 deposited against", "$500 declared (16×),", "then 96% withdrawn"], 88)])
col(1, [("chip", ["Spots a ring: 23 accounts", "share a device and payment"], "purple", "net", "BigQuery Graph", 66),
        ("chip", ["Ignores a public gateway", "used by 142 strangers"], "slate", "net", None, 66),
        ("chip", ["Quotes the exact rule", "that applies"], "amber", "doc", "Agent Search", 66)])
col(2, [("chip", ["Drafts the case summary", "and the report (SAR)"], "purple", "net", "Vertex AI", 66),
        ("rule", ["No number without proof:", "unverified drafts refused"], 66),
        ("chip", ["Questions and answers", "are screened for abuse"], "red", "shield", "Model Armor", 66)])
col(3, [("chip", ["The proposal is turned", "into a signed request"], "amber", "bolt", None, 66),
        ("chip", ["Digitally signed; expires", "in 15 minutes"], "red", "key", "Cloud KMS", 66),
        ("rule", ["The AI can only propose.", "It cannot approve or act."], 66)])
col(4, [("chip", ["The hold is carried out", "once; a receipt is kept"], "green", "bolt", None, 66),
        ("chip", ["Each approval is added to", "a record that can\u2019t be edited"], "slate", "lines", "Firestore", 66),
        ("chip", ["The evidence is sealed so", "anyone can re-check it"], "grey", "doc", None, 66)])

# hand-off arrows between people and EIOS
cx = lambda i: COLS[i] + 90
l1_bottom = L1[0] + L1[1] - 14
l3_top = L3[0] + 14
varrow(cx(0), ey, l1_bottom, color=GREY_ARROW)
varrow(cx(1), ey, l1_bottom, both=True)
varrow(cx(2), ey, l1_bottom, both=True)
# blocked hand-off: the proposer cannot approve
add(f'<path d="M{cx(3)} {ey}V{l1_bottom}" stroke="{RED}" stroke-width="3" stroke-dasharray="8 6"/>')
mx, my = cx(3), (ey + l1_bottom) / 2
add(f'<circle cx="{mx}" cy="{my}" r="13" fill="#ffffff" stroke="{RED}" stroke-width="2.5"/>')
add(f'<path d="M{mx - 6} {my - 6}l12 12M{mx + 6} {my - 6}l-12 12" stroke="{RED}" stroke-width="2.5"/>')
varrow(cx(0), l3_top, ey + eh, color=GREY_ARROW)
varrow(cx(3), ey + eh, l3_top, both=True, color=AMBER)
varrow(cx(4), ey + eh, l3_top)

# spine between EIOS cells
midy = ey + eh // 2
harrow(COLS[0] + CW + 1, COLS[1] - 1, midy)
harrow(COLS[1] + CW + 1, COLS[2] - 1, midy)
harrow(COLS[2] + CW + 1, COLS[3] - 1, midy, color=AMBER)
harrow(COLS[3] + CW + 1, COLS[4] - 1, midy, color=AMBER)

# footer: tagline, disclosure, legend
add(f'<text x="{M + 4}" y="{FOOT_Y + 32}" font-size="28" font-weight="600" xml:space="preserve"><tspan fill="{INK2}">The AI proposes.</tspan><tspan fill="{AMBER_TXT}">&#160;&#160;People decide.</tspan><tspan fill="{GBLUE}">&#160;&#160;The record remembers.</tspan></text>')
text(X_END + 12, FOOT_Y + 30, "Case CR84920 is engine output on the seeded world; ids and figures are synthetic.", 18, 400, INK2, "end")
lx, ly = M + 4, FOOT_Y + 66
add(f'<rect x="{lx}" y="{ly - 18}" width="56" height="24" rx="12" fill="{GBLUE}"/>')
text(lx + 68, ly, "Google Cloud service", 18, 400, INK)
lx += 290
add(f'<rect x="{lx}" y="{ly - 18}" width="34" height="24" fill="#ffffff" stroke="#8a8d93" stroke-width="1.4"/>')
text(lx + 46, ly, "a person", 18, 400, INK)
lx += 170
add(f'<rect x="{lx}" y="{ly - 18}" width="34" height="24" fill="{CHIP}" stroke="#c0c1c4" stroke-width="1.2"/>')
text(lx + 46, ly, "EIOS", 18, 400, INK)
lx += 120
add(f'<rect x="{lx}" y="{ly - 18}" width="34" height="24" fill="#ffffff" stroke="{AMBER}" stroke-width="3"/>')
text(lx + 46, ly, "a human decision", 18, 400, INK)
lx += 230
add(f'<path d="M{lx} {ly - 6}h40" stroke="{GREY_ARROW}" stroke-width="3"/><path d="M{lx + 52} {ly - 6}l-14 -8v16z" fill="{GREY_ARROW}"/>')
text(lx + 64, ly, "hand-off", 18, 400, INK)
lx += 190
add(f'<path d="M{lx} {ly - 6}h40" stroke="{AMBER}" stroke-width="3"/><path d="M{lx + 52} {ly - 6}l-14 -8v16z" fill="{AMBER}"/>')
text(lx + 64, ly, "propose, sign, ledger", 18, 400, INK)

add("</svg>")
Path(__file__).with_name("eios-process-flow.svg").write_text("\n".join(out))
print("ok", FOOT_Y, X_END)
