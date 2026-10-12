"""A small, valid synthetic ``infra/`` tree plus helpers to derive faulty variants.

The tree mirrors the conventions of the real ``infra/`` layout: one root per environment with a
``backend "gcs"`` prefix, a ``service_identity`` module call per service named
``identity_<service>``, ``run_service`` calls named ``service_<service>``, a ``secret_store`` call
with ``signing_key_enabled``, and an ``eval_truth_store`` call with label-to-member maps.

Every function returns new data; tests derive faulty trees with ``patched`` or by changing the
identity rows, never by editing a shared object. Project references and bucket names are
placeholders; nothing here names a real cloud project.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import yaml

ENVIRONMENTS = ("dev", "stage", "prod-like")
SERVICES = ("skeleton_edge", "skeleton_core", "pipeline", "eval_harness", "release_candidate")
RUNTIME_SERVICES = ("skeleton_edge", "skeleton_core")
TRUTH_READERS = ("eval_harness", "pipeline")
RC_IMPERSONATOR = "workflow=release-candidate.yml"

IdentityRow = Mapping[str, object]

_RC_PRINCIPAL = (
    "principalSet://iam.googleapis.com/${var.pool}/attribute.workflow_ref/"
    "${var.repo}/.github/workflows/release-candidate.yml@refs/heads/main"
)


def _identity_module(service: str) -> str:
    roles = "local.runtime_roles" if service in RUNTIME_SERVICES else '["roles/logging.logWriter"]'
    impersonation = ""
    if service == "release_candidate":
        impersonation = (
            f'  impersonator_members = {{ release_candidate_workflow = "{_RC_PRINCIPAL}" }}\n'
            "  require_attribute_restricted_impersonation = true\n"
        )
    return f"""
module "identity_{service}" {{
  source     = "../../modules/service_identity"
  project_id = var.project_id
  service    = "{service}"
  roles      = {roles}
{impersonation}}}
"""


def _run_service_module(service: str, min_instances: int) -> str:
    return f"""
module "service_{service}" {{
  source                = "../../modules/run_service"
  count                 = var.image == null ? 0 : 1
  service               = "{service}"
  service_account_email = module.identity_{service}.email
  stateful              = true
  min_instances         = {min_instances}
}}
"""


def env_main(
    name: str,
    *,
    project: str | None = None,
    prefix: str | None = None,
    min_instances: int | None = None,
    signing: bool | None = None,
    extra: str = "",
) -> str:
    """The root module of one environment; keyword arguments produce faulty variants."""
    prod_like = name == "prod-like"
    project_ref = project if project is not None else f"placeholder-{name}-project"
    state_prefix = prefix if prefix is not None else f"envs/{name}"
    instances = min_instances if min_instances is not None else (1 if prod_like else 0)
    enabled = signing if signing is not None else prod_like
    parts = [
        f"""terraform {{
  backend "gcs" {{
    prefix = "{state_prefix}"
  }}
}}

variable "project_id" {{
  type    = string
  default = "{project_ref}"
}}

provider "google" {{
  project = var.project_id
}}

locals {{
  environment   = "{name}"
  runtime_roles = ["roles/logging.logWriter", "roles/monitoring.metricWriter"]
}}
"""
    ]
    parts.extend(_identity_module(service) for service in SERVICES)
    parts.extend(_run_service_module(service, instances) for service in RUNTIME_SERVICES)
    parts.append(f"""
module "secret_store" {{
  source              = "../../modules/secret_store"
  project_id          = var.project_id
  signing_key_enabled = {str(enabled).lower()}
}}

module "eval_truth_store" {{
  source = "../../modules/eval_truth_store"

  reader_members = {{
    pipeline     = module.identity_pipeline.member
    eval_harness = module.identity_eval_harness.member
  }}
  sealed_reader_members = {{
    release_candidate = module.identity_release_candidate.member
  }}
}}
""")
    parts.append(extra)
    return "".join(parts)


def _module_files(
    name: str, variables: Sequence[str], outputs: Sequence[str], body: str
) -> dict[str, str]:
    base = f"infra/modules/{name}"
    variable_text = "".join(f'variable "{v}" {{\n  type = any\n}}\n\n' for v in variables)
    output_text = "".join(f'output "{o}" {{\n  value = "placeholder"\n}}\n\n' for o in outputs)
    return {
        f"{base}/variables.tf": variable_text or "# no variables\n",
        f"{base}/outputs.tf": output_text or "# no outputs\n",
        f"{base}/main.tf": body,
    }


_SECRET_STORE_BODY = """resource "google_kms_crypto_key" "signing" {
  count   = var.signing_key_enabled ? 1 : 0
  name    = "signing"
  purpose = "ASYMMETRIC_SIGN"

  version_template {
    algorithm = "EC_SIGN_P256_SHA256"
  }
}
"""

_EVAL_TRUTH_BODY = """resource "google_storage_bucket" "truth" {
  name                        = "truth-${var.project_id}"
  location                    = "EU"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket" "sealed" {
  name                        = "sealed-${var.project_id}"
  location                    = "EU"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_storage_bucket_iam_member" "reader" {
  for_each = var.reader_members
  bucket   = google_storage_bucket.truth.name
  role     = "roles/storage.objectViewer"
  member   = each.value
}

resource "google_storage_bucket_iam_member" "sealed_reader" {
  for_each = var.sealed_reader_members
  bucket   = google_storage_bucket.sealed.name
  role     = "roles/storage.objectViewer"
  member   = each.value
}
"""


def _modules() -> dict[str, str]:
    files: dict[str, str] = {}
    files.update(
        _module_files(
            "service_identity",
            ("project_id", "service", "roles", "impersonator_members"),
            ("email", "member"),
            'resource "terraform_data" "identity" {\n  input = var.service\n}\n',
        )
    )
    files.update(
        _module_files(
            "run_service",
            ("service", "service_account_email", "min_instances"),
            ("uri",),
            'resource "terraform_data" "service" {\n  input = var.service\n}\n',
        )
    )
    files.update(
        _module_files(
            "secret_store",
            ("project_id", "signing_key_enabled"),
            ("signing_key_id",),
            _SECRET_STORE_BODY,
        )
    )
    files.update(
        _module_files(
            "eval_truth_store",
            ("project_id", "reader_members", "sealed_reader_members"),
            ("bucket",),
            _EVAL_TRUTH_BODY,
        )
    )
    return files


def identity_rows() -> list[dict[str, object]]:
    """One valid row per service per environment."""
    rows: list[dict[str, object]] = []
    for environment in ENVIRONMENTS:
        for service in SERVICES:
            rows.append(
                {
                    "service": service,
                    "environment": environment,
                    "roles": ["roles/logging.logWriter"],
                    "can_read_eval_truth": service in TRUTH_READERS,
                    "impersonable_by": [RC_IMPERSONATOR] if service == "release_candidate" else [],
                }
            )
    return rows


def render_identities(rows: Sequence[IdentityRow]) -> str:
    return yaml.safe_dump({"identities": [dict(row) for row in rows]}, sort_keys=False)


def good_files() -> dict[str, str]:
    """A valid tree: three environments, four modules, one identities file."""
    files = _modules()
    for environment in ENVIRONMENTS:
        files[f"infra/envs/{environment}/main.tf"] = env_main(environment)
    files["infra/identities.yaml"] = render_identities(identity_rows())
    return files


def patched(files: Mapping[str, str], path: str, old: str, new: str) -> dict[str, str]:
    """Copy of ``files`` with ``old`` replaced by ``new`` in ``path`` (``old`` must be present)."""
    text = files[path]
    if old not in text:
        raise AssertionError(f"{old!r} not found in {path}")
    return {**files, path: text.replace(old, new)}


def with_file(files: Mapping[str, str], path: str, text: str) -> dict[str, str]:
    return {**files, path: text}
