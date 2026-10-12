# validation overlay

Replaces `evals/registry.yaml` with one valid `validation`-tier suite, `failing-validation`, whose script writes its report and exits 1 (validation evaluation failed: score below baseline). The failure is a suite failure, not a registry error.
