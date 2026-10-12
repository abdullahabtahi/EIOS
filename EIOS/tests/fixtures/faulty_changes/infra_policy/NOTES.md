# infra_policy overlay

Adds `infra/identities.yaml` in which `skeleton_edge` has two rows in `dev` (a shared identity) and `skeleton_core` is granted the wildcard role `roles/*`. The environment roots are also absent, so the policy reports those too.
