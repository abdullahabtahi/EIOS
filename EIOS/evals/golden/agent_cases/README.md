# Golden agent cases

Written from the workstation jobs in `docs/agent-architecture.md` section 1, not from the legacy dialogues in
`evals/golden/dialogues/` (those name tools that exist nowhere and stay untouched under `dialogue-evals`).
Cases name capabilities, never tools; `src/eios/agent_gates/capability_map.yaml` maps them per runtime.
A file holds a list of cases. Format: `specs/022-agent-quality-gates/contracts/golden-case.md`.
Starting size is deliberately lean `[ASSUMPTION]`; grow after the baseline shows the spread. `held_out.yaml` holds the `validation` and `sealed` splits; see `docs/agent-eval-splits.md` before editing it.
