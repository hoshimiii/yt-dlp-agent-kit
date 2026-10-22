"""Opt-in, fixed public fixture smoke test; never run automatically on install."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from yt_agent.policy import Policy
from yt_agent.service import Service

URL = "https://media.w3.org/2010/05/bunny/trailer.mp4"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Permit one <=5 MiB download of the fixed W3C fixture")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / ".cache" / "live"
    service = Service(Policy(state_root=str(root / "state"), download_root=str(root / "downloads"),
                             allowed_hosts=("media.w3.org",), allow_downloads=args.download,
                             max_media_bytes=5 * 1024 * 1024, timeout_seconds=45))
    result = {"tested_at": datetime.now(timezone.utc).isoformat(), "fixture": URL}
    exit_code = 0
    try:
        result["metadata"] = service.inspect(URL)
        if args.download:
            plan = service.plan_download(URL)
            service.approve(plan["plan_id"])
            result["download"] = service.download(plan["plan_id"])
    except Exception as exc:
        result["error"] = str(exc)
        exit_code = 1
    root.mkdir(parents=True, exist_ok=True)
    (root / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
