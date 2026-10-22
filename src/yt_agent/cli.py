"""JSON CLI. Approval is deliberately absent from Service.call/model tools."""

import argparse
import json
import signal
import sys

from .policy import Rejected, dumps
from .service import Service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("call", help="Read one {tool,arguments} JSON request from stdin")
    approval = sub.add_parser("approve", help="Operator-only: approve the exact local plan")
    approval.add_argument("identifier")
    show = sub.add_parser("show-plan", help="Operator-only: display the stored plan")
    show.add_argument("identifier")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        service = Service()
        if args.command == "approve":
            result = service.approve(args.identifier)
        elif args.command == "show-plan":
            _, result, _ = service.read_plan(args.identifier)
        else:
            raw = sys.stdin.buffer.read(16385)
            if len(raw) > 16384:
                raise Rejected("Request exceeds 16 KiB")
            try:
                request = json.loads(raw)
            except (ValueError, UnicodeError, RecursionError) as exc:
                raise Rejected("Expected valid JSON") from exc
            result = service.call(request)
        print(dumps({"ok": True, "result": result}))
    except Rejected as exc:
        print(dumps({"ok": False, "error": str(exc)}))
        sys.exit(1)
    except KeyboardInterrupt:
        print(dumps({"ok": False, "error": "Cancelled"}))
        sys.exit(130)
    except Exception:
        print(dumps({"ok": False, "error": "Local operation failed; inspect local configuration and permissions"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
