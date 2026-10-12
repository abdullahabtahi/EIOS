# eval_smoke overlay

Replaces `evals/registry.yaml` with one valid `eval_smoke`-tier suite, `failing-eval-smoke`, whose script writes its report and exits 1 (smoke evaluation failed: score below baseline). The failure is a suite failure, not a registry error.
