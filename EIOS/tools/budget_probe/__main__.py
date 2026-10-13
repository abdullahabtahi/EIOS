import argparse
import json
import os
import sys
import typing
from pathlib import Path

from eios.common.errors import BoundaryValidationError, EiosError
from tools.budget_probe.payload import (
    PublishError,
    PubSubPublisher,
    build_message,
    load_settings,
    validate_topic,
)


def main(argv: list[str] | None = None, publisher: typing.Any = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--env", required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--topic")
    parser.add_argument("--dry-run", action="store_true")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    try:
        settings = load_settings(args.repo_root, args.env)
        message = build_message(settings, args.threshold)

        if args.dry_run:
            print(json.dumps({"payload": message.payload, "dry_run": True}))
            return 0

        topic = args.topic or os.environ.get("EIOS_BUDGET_TOPIC")
        if not topic:
            print("topic missing", file=sys.stderr)
            return 2
        topic = validate_topic(topic)

        pub = publisher or PubSubPublisher()
        msg_id = pub.publish(topic, message.data, message.attributes)
        print(
            json.dumps(
                {"message_id": msg_id, "dry_run": False, "probe_id": message.attributes["probe_id"]}
            )
        )
        return 0
    except (BoundaryValidationError, EiosError, PublishError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
