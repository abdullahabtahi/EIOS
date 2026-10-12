# Contract: Provenance and Labelling Conventions

**Feature**: F00 | **Requirements**: FR-029..FR-031 | **Constitution**: V, VI | **Tool**: `tools/label_check`

Design-time contract for how figures and claims are tagged and how the checker enforces it.

## Tags

| Tag | Meaning | Evidence required |
|---|---|---|
| `[BRIEF]` | Cited from `docs/brief/*` | Citation to the brief file and section |
| `[ASSUMPTION]` | Stated assumption, not verified | Owner and a "verify by" note or linked spike |
| `[ILLUSTRATIVE]` | Example value for explanation only | None; must never feed a metric or a shown KPI |
| `[TARGET]` | A commitment to measure, not a claim | Metric name and where it will be reported |
| `[SPIKE]` | Unverified until a spike closes with an ADR | Spike id (`S-NN`) |

The tag set lives in `config/labels.yaml`; the checker reads it, so adding a tag is a configuration change plus a constitution-aligned decision record.

## Numeric-claim rule

A figure in a governed document, config value or shown output MUST carry exactly one tag, or trace to one of:

1. a brief citation,
2. a generator run: seed + revision + dataset hash,
3. an eval report path under `evals/reports/`.

Untagged and untraceable figures fail `label_check` with file, line and the offending literal.

## Forbidden literals

`config/forbidden_literals.yaml` lists patterns the checker rejects everywhere unless allowlisted:

| Class | Examples of what is matched | Why |
|---|---|---|
| Real competitor or vendor brand names used as competitors | pattern list maintained in the file | Constitution V |
| Pinned library, model or price versions without a tag | version-shaped strings next to tool, model or price words | No unverified pins |
| Secret-shaped strings | key/token/private-key patterns | Engineering Constraints |

## Allowlist

Per-file entries in `config/label_allowlist.yaml`:

```yaml
- path: <repo-relative path>
  literal: <exact string or pattern id>
  reason: <non-empty, reviewed text>
```

An entry without a reason is rejected. An entry whose file or literal no longer exists is reported as stale.

## Checker behaviour

| Situation | Result |
|---|---|
| Untagged figure in a scanned file | fail, with location |
| Tag not in `labels.yaml` | fail |
| `[SPIKE]` tag without a valid `S-NN` reference | fail |
| Forbidden literal, not allowlisted | fail |
| Allowlist entry with empty reason | fail |
| Prototype paths (`FEIOS/`, `DESIGN.MD`, `DESIGN_PLAN.md`) | excluded by configuration, listed in the report |
| Clean run | pass, prints scanned-file count |

Runs in the `pr` workflow as a blocking gate; the report is stored as evidence on the Pipeline Run Record.

## Tests owned by F00

- One fixture per failure row above fails with the expected message.
- A clean fixture passes.
- Removing a tag from a config value that requires one fails the gateway config loader as well as `label_check`.
