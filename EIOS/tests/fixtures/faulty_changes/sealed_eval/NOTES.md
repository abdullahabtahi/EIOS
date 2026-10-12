# sealed_eval overlay

Replaces `evals/registry.yaml` with one valid `sealed`-tier suite, `failing-sealed-eval`, whose script writes its report and exits 1 (sealed evaluation failed: release candidate below baseline). The gate runs it under the release-candidate workflow, the only identity allowed to execute the sealed tier. The failure is a suite failure, not a registry error.
