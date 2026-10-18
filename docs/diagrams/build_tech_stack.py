"""Builds docs/diagrams/eios-tech-stack.svg (24 cm x 10 cm, 100 units per cm).

Every technology appears once, under the one job it does for EIOS (MECE). The inventory comes from
EIOS/pyproject.toml, EIOS/web-prototype/package.json, EIOS/infra, the Dockerfiles, .github/workflows and the
imports under EIOS/src. Chip colour: solid blue = a Google service, grey = open source, outlined = anything else
(commercial, source-available, public data). Run: python3 build_tech_stack.py
"""
from html import escape
from pathlib import Path

W, H = 2400, 1000
FONT = "'Avenir Next','Helvetica Neue',Helvetica,Arial,sans-serif"
INK, INK2, RULE = "#1b1d21", "#464a51", "#cfd0d2"
PANEL, CHIP, CANVAS = "#ececec", "#dedfe0", "#f7f7f5"
GBLUE = "#1a56c4"
M = 30

G, O, X = "g", "o", "x"  # Google service, open source, other

# (number, title, subtitle, chips, note lines)
ROW1 = [
    (1, "SEE", "Screens and maps", [
        ("Next.js 16.4", O), ("React 19.3", O), ("TypeScript 5", O), ("Tailwind CSS 4", O), ("Base UI", O), ("Radix UI", O),
        ("lucide-react", O), ("class-variance-authority", O), ("clsx", O), ("tailwind-merge", O), ("tw-animate-css", O), ("Schibsted Grotesk", O), ("deck.gl 9.4", O), ("vis.gl React Google Maps", O),
        ("Google Maps JavaScript API", G)], []),
    (2, "SERVE", "APIs and services", [
        ("Python 3.14", O), ("FastAPI", O), ("Starlette", O), ("Uvicorn", O), ("Pydantic 2", O), ("httpx", O), ("Node.js 22", O)], []),
    (3, "THINK", "Agents and models", [
        ("Vertex AI", G), ("Gemini 3.5 Flash-Lite", G), ("Gemini 3.5 Flash", G), ("Gemini 3.8 Flash", G), ("Agent Search", G),
        ("Google ADK 2.11", O), ("google-genai SDK", O)], []),
    (4, "COMPUTE", "Analytics and statistics", [
        ("NumPy", O), ("SciPy", O), ("scikit-learn", O), ("pandas", O), ("Polars", O), ("NetworkX", O)],
     ["Methods: ridge regression,", "IsolationForest, discrete-time", "hazard, placebo refuters, AIPW"]),
    (5, "DATA", "Stores, streams and graph", [
        ("BigQuery", G), ("BigQuery Graph", G), ("Firestore", G), ("Cloud Storage", G), ("Pub/Sub", G),
        ("DuckDB", O), ("Apache Parquet", O), ("PyArrow", O), ("JSON Schema", O), ("PyYAML", O)], []),
    (6, "SOURCES", "Public data and lists", [
        ("IPinfo Lite", X), ("Tor exit list", X), ("AWS IP ranges", X), ("Google Cloud IP ranges", X), ("X4BNet VPN lists", X),
        ("Overture Maps", X), ("FATF lists", X), ("EU high-risk list", X), ("Basel AML Index", X), ("ICIJ Offshore Leaks", X),
        ("World Bank WDI", X), ("Natural Earth", X), ("Five regulatory documents", X), ("Synthetic worlds (Faker)", O), ("pycountry (ISO codes)", O)], []),
]
ROW2 = [
    (7, "PROTECT", "Identity, secrets, signing, screening", [
        ("Cloud KMS", G), ("Secret Manager", G), ("Identity Platform", G), ("Model Armor", G), ("Workload Identity Federation", G),
        ("cryptography", O), ("limits", O), ("Firebase SDK 13", O)], []),
    (8, "RUN", "Cloud runtime and observability", [
        ("Cloud Run", G), ("Cloud Trace", G), ("Cloud Logging", G), ("Cloud Monitoring", G), ("Cloud Billing budgets", G),
        ("OpenTelemetry", O), ("Arize Phoenix (local)", X)], []),
    (9, "SHIP", "Build, package, deploy", [
        ("Cloud Build", G), ("Artifact Registry", G), ("GitHub Actions", X), ("Terraform", X), ("Docker", O), ("uv", O), ("npm", O),
        ("Make", O), ("TFLint", O)], []),
    (10, "PROVE", "Test, evaluate, scan", [
        ("pytest", O), ("pytest-xdist", O), ("pytest-cov", O), ("Vitest", O), ("Vite 8", O), ("jsdom", O), ("Testing Library", O), ("mypy", O), ("Ruff", O), ("ESLint", O), ("Promptfoo", O), ("Newman", O),
        ("pip-audit", O), ("python-hcl2", O), ("Firestore emulator", G), ("CodeQL", X), ("Dependabot", X), ("SonarQube", O)], []),
]
MAKE = [("Antigravity IDE", G), ("Jules", G), ("Gemini Flash 3.1", G), ("Gemini 4 Argon", G), ("Claude Code", X), ("Magnific MCP", X), ("Seedance 2.5", X), ("Impeccable", X), ("Playwright", O), ("ffmpeg", O),
        ("libwebp", O), ("librsvg", O), ("Pillow", O)]

out: list[str] = []


def add(s: str) -> None:
    out.append(s)


def text(x, y, s, size=18, weight=400, fill=INK, anchor="start", spacing=0):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{sp}>{escape(s)}</text>')


def chip_w(label: str, kind: str) -> float:
    return len(label) * (10.4 if kind == G else 9.6) + 26


CH, CGAP, CSIZE = 34, 8, 18


def flow(x, y, w, chips):
    """Lay chips left to right, wrapping at width w. Returns (placements, height)."""
    placed, cx, cy = [], 0.0, 0.0
    for label, kind in chips:
        cw = chip_w(label, kind)
        if cx and cx + cw > w:
            cx, cy = 0.0, cy + CH + CGAP
        placed.append((x + cx, y + cy, cw, label, kind))
        cx += cw + CGAP
    return placed, cy + CH


def draw_chip(cx, cy, cw, label, kind):
    if kind == G:
        add(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{CH}" rx="{CH / 2}" fill="{GBLUE}"/>')
        text(cx + cw / 2, cy + 23, label, CSIZE, 600, "#ffffff", "middle")
    elif kind == O:
        add(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{CH}" fill="{CHIP}" stroke="#c0c1c4" stroke-width="1.2"/>')
        text(cx + cw / 2, cy + 23, label, CSIZE, 500, INK, "middle")
    else:
        add(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{CH}" fill="#ffffff" stroke="#8a8d93" stroke-width="1.5"/>')
        text(cx + cw / 2, cy + 23, label, CSIZE, 500, INK, "middle")


def pill_number(x, y, n):
    add(f'<rect x="{x}" y="{y - 16}" width="{52 if n > 9 else 46}" height="30" rx="15" fill="{CANVAS}" stroke="#8a8d93" stroke-width="1.5"/>')
    text(x + (26 if n > 9 else 23), y + 6, str(n), 19, 600, INK, "middle")


def panel_height(w, chips, notes):
    _, h = flow(0, 0, w - 32, chips)
    return 96 + h + (len(notes) * 24 + 14 if notes else 0) + 20


def draw_panels(row, y, widths, height):
    x = M
    for (n, title, sub, chips, notes), w in zip(row, widths):
        add(f'<rect x="{x}" y="{y}" width="{w}" height="{height}" fill="{PANEL}" stroke="{RULE}" stroke-width="1.5"/>')
        pill_number(x + 14, y, n)
        text(x + 16, y + 48, title, 28, 600, INK, spacing=0.3)
        text(x + 16, y + 74, sub, 18, 400, INK2)
        placed, h = flow(x + 16, y + 92, w - 32, chips)
        for p in placed:
            draw_chip(*p)
        if notes:
            for i, ln in enumerate(notes):
                text(x + 16, y + 92 + h + 30 + i * 24, ln, 18, 400, INK2)
        x += w + 20


def solve_widths(row, total, weights):
    s = sum(weights)
    avail = total - 20 * (len(row) - 1)
    return [avail * wt / s for wt in weights]


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="24cm" height="10cm" viewBox="0 0 {W} {H}" font-family="{FONT}">')
add(f'<rect width="{W}" height="{H}" fill="{CANVAS}"/>')

TOTAL = W - 2 * M
w1 = solve_widths(ROW1, TOTAL, [1.22, 0.66, 0.80, 0.78, 0.90, 1.52])
w2 = solve_widths(ROW2, TOTAL, [0.95, 0.85, 0.9, 1.45])
h1 = max(panel_height(w, r[3], r[4]) for w, r in zip(w1, ROW1))
h2 = max(panel_height(w, r[3], r[4]) for w, r in zip(w2, ROW2))

STRIP_H = 112
extra = H - M - (22 + 50 + h1 + 22 + 50 + h2 + 22 + STRIP_H)
if extra > 0:
    h1 += extra / 2
    h2 += extra / 2
y = 22
text(M + 2, y + 24, "THE PRODUCT", 24, 600, INK, spacing=0.4)
text(M + 190, y + 24, "what runs for users, in the order a request travels", 19, 400, INK2)
y1 = y + 50
draw_panels(ROW1, y1, w1, h1)
y = y1 + h1 + 22
text(M + 2, y + 24, "THE FOUNDATIONS", 24, 600, INK, spacing=0.4)
text(M + 250, y + 24, "how it is trusted, run, shipped and proven", 19, 400, INK2)
y2 = y + 50
draw_panels(ROW2, y2, w2, h2)

# make strip + counts + legend
sy = y2 + h2 + 22
sh = H - M - sy
add(f'<rect x="{M}" y="{sy}" width="{TOTAL}" height="{sh}" fill="{PANEL}" stroke="{RULE}" stroke-width="1.5"/>')
pill_number(M + 14, sy, 11)
text(M + 84, sy + 40, "MAKE", 26, 600, INK, spacing=0.3)
text(M + 84 + 100, sy + 40, "used to create the landing page and these diagrams", 18, 400, INK2)
mx = M + 16
for label, kind in MAKE:
    cw = chip_w(label, kind)
    draw_chip(mx, sy + 62, cw, label, kind)
    mx += cw + CGAP

allchips = [c for r in ROW1 + ROW2 for c in r[3]] + MAKE
n_g = sum(1 for _, k in allchips if k == G)
n_o = sum(1 for _, k in allchips if k == O)
n_x = sum(1 for _, k in allchips if k == X)
ly = sy + 40
rx = M + TOTAL - 16
legend = [(G, f"Google service ({n_g})"), (O, f"Open source ({n_o})"), (X, f"Other: commercial, source-available, public data ({n_x})")]
widths = [chip_w("", k) + 230 if i < 2 else 560 for i, (k, _) in enumerate(legend)]
lx = rx - sum(widths)
for (k, label), wd in zip(legend, widths):
    if k == G:
        add(f'<rect x="{lx}" y="{ly - 18}" width="52" height="24" rx="12" fill="{GBLUE}"/>')
    elif k == O:
        add(f'<rect x="{lx}" y="{ly - 18}" width="42" height="24" fill="{CHIP}" stroke="#c0c1c4" stroke-width="1.2"/>')
    else:
        add(f'<rect x="{lx}" y="{ly - 18}" width="42" height="24" fill="#ffffff" stroke="#8a8d93" stroke-width="1.5"/>')
    text(lx + 62, ly, label, 18, 400, INK)
    lx += wd

add("</svg>")
Path(__file__).with_name("eios-tech-stack.svg").write_text("\n".join(out))
print("ok", round(y1 + h1), round(y2 + h2), round(sy), n_g, n_o, n_x, len(MAKE))
