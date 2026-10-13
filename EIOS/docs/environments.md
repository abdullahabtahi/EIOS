# Environments (T087)

Three environments share one set of modules (`infra/modules/`) and are composed by one root each (`infra/envs/dev`, `infra/envs/stage`, `infra/envs/prod-like`). Each root owns its project reference and its state prefix and references nothing from another environment. Promotion moves images by digest, never data (research R-06).

**[ASSUMPTION]** Each environment is one isolated cloud project. Project boundaries give hard IAM and quota isolation at low cost; if a client mandates a different boundary, only the bootstrap project map and the tfvars change.

## Differences

| Aspect | dev | stage | prod-like |
|---|---|---|---|
| Cloud project | its own | its own | its own |
| State prefix | `envs/dev` | `envs/stage` | `envs/prod-like` |
| Stateful service `min_instances` | 0 `[ASSUMPTION]` | 0 `[ASSUMPTION]` | 1 `[ASSUMPTION]` (never 0) |
| Warm start required | no | no | yes |
| Signing key (ECDSA P-256) | not created | not created | created |
| Evidence retention default | 7 days `[ASSUMPTION]` | 30 days `[ASSUMPTION]` | 365 days `[ASSUMPTION]` |
| Evidence retention lock | off | off | on (irreversible) |
| Firestore and service deletion protection | off | off | on |
| Apply approval | none | none | required (GitHub environment reviewers) |

Everything else is identical on purpose: the same five service identities, the same eval-truth rules, the same guardrails, the same module versions. prod-like is "like production" in resilience and signing, not in scale; instance ceilings stay small `[ASSUMPTION]`.

Why prod-like keeps instances warm: the gateway counters and replay cache are stateful, and a cold start must not drop a counter window. The static check `infra.prod_like.min_instances` fails any prod-like stateful service with a minimum below 1.

## Identities

Five identities exist per environment, defined in `infra/identities.yaml` and created by the `service_identity` module: `skeleton_edge`, `skeleton_core`, `pipeline`, `eval_harness`, `release_candidate`. Roles are explicit lists; wildcards, `roles/owner` and `roles/editor` are rejected by variable validation and by the static check.

Ground-truth access:

| Identity | Open split bucket | Sealed split bucket |
|---|---|---|
| `skeleton_edge`, `skeleton_core` (runtime) | no | no |
| `pipeline`, `eval_harness` | read | no |
| `release_candidate` | no | read |

## How the release-candidate identity is impersonated

The `release_candidate` service account has exactly one impersonation binding: the principal set `attribute.workflow_ref/<owner>/<repository>/.github/workflows/release-candidate.yml@<ref>` of the CI federation pool, granted `roles/iam.workloadIdentityUser`. `<ref>` defaults to `refs/heads/main` `[ASSUMPTION]` (variable `release_candidate_git_ref`).

Consequences:

1. Only a run of the release-candidate workflow file, from that ref, in the allowed repository, can obtain tokens for the identity. No human, no other workflow, no runtime service can.
2. The module refuses any impersonator that is not an attribute-restricted principal set (`require_attribute_restricted_impersonation = true`), so a repository-wide binding cannot be added by accident.
3. Its only data grant is read on the sealed bucket, which holds the sealed split. The sealed split is evaluated by CI on release candidates only (CLAUDE.md, testing and evaluation).

The workflow-ref claim and its mapping are `[ASSUMPTION]` (owner: platform engineer, verify by the first real bootstrap run) until a real run confirms them (see `docs/runbooks/bootstrap.md`).

## Secrets and signing

Secret Manager holds containers only; values are added out of band and never appear in Terraform. The signing key ring and key exist only where `signing_key_enabled` is true. The key is asymmetric signing with ECDSA P-256; the core service may sign and the edge may read the public key. Nothing may sign except through that permission, which is consistent with "no autonomous write-back" (CLAUDE.md invariant 5).

## Not verified without a cloud account

Static validation only: nothing here was applied. Unverified until a real project exists: provider behaviour at apply time, org-policy permissions, federation claim mapping, Firestore TTL and database settings, KMS settings and retention-lock behaviour. Tracked as `[ASSUMPTION]` in `docs/runbooks/bootstrap.md`.

## Recorded exceptions (hackathon deployment, eios-hackathon-prod)
- `enforce_guardrails = false`: the deploying identity has no `orgpolicy.policyAdmin`. Service-account-key and public-bucket
  guardrails are not enforced by policy in this project; the code never creates keys or public buckets. Re-enable when granted.
- `allow_public_invocation = true` on `cockpit_web` only: judges must reach the demo without an IAM allowlist. The application
  authenticates every operator; the API is private.
- `evidence_lock_retention = false`: avoids an irreversible 365-day bucket lock in a throwaway project.
