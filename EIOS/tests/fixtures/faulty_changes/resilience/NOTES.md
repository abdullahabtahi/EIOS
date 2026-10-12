# resilience overlay

Replaces `evals/registry.yaml` with one valid `validation`-tier suite whose id starts with `resilience-`, which writes its report and exits 1 (service did not recover after restart). The resilience gate selects suites by that id prefix. The failure is a suite failure, not a registry error.
