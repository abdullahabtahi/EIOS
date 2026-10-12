"""``python -m tools.prompt_lock (check|update) [--repo-root DIR] [--prompts-dir DIR]``.

Exits 0 pass, 1 findings, 2 tool or configuration error. ``--prompts-dir`` defaults to
``<repo root>/prompts``; a relative value is resolved against the repo root.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from eios.common.errors import ToolError
from tools.common.cli import ExitCode, run_tool
from tools.common.findings import Finding
from tools.prompt_lock.lock import check_prompts, update_lock

TOOL = "prompt_lock"
COMMANDS = {"check": check_prompts, "update": update_lock}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ToolError(f"{self.prog}: {message}")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="python -m tools.prompt_lock", description="Locked prompt guard")
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--prompts-dir", type=Path, default=None)
    return parser


def _prompts_dir(repo_root: Path, option: Path | None) -> Path:
    if option is None:
        return repo_root / "prompts"
    return option if option.is_absolute() else repo_root / option


def main(argv: Sequence[str]) -> int:
    try:
        args = _parser().parse_args(list(argv))
    except ToolError as exc:
        print(f"{TOOL}: error: {exc}", file=sys.stderr)
        return int(ExitCode.ERROR)
    command = COMMANDS[args.command]
    prompts_dir = _prompts_dir(args.repo_root, args.prompts_dir)

    def func(_: argparse.Namespace) -> Sequence[Finding]:
        findings = command(prompts_dir, args.repo_root)
        print(f"{TOOL} {args.command}: {len(findings)} findings")
        return findings

    return run_tool(TOOL, func, ["--repo-root", str(args.repo_root)])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
