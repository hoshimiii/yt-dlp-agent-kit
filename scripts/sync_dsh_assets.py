"""Keep DSH's distributable skill and schema identical to the canonical files."""

import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    pairs = [(root / "src/yt_agent/tools.json", root / "adapters/dsh/tools.json"),
             (root / "LICENSE", root / "adapters/dsh/LICENSE")]
    for source in (root / "skills/yt-media").rglob("*"):
        if source.is_file():
            pairs.append((source, root / "adapters/dsh/skills/yt-media" / source.relative_to(root / "skills/yt-media")))
    for source, destination in pairs:
        if args.check:
            if not destination.is_file() or source.read_bytes() != destination.read_bytes():
                raise SystemExit(f"Stale generated asset: {destination.relative_to(root)}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    print(f"DSH assets {'verified' if args.check else 'synchronized'}: {len(pairs)}")


if __name__ == "__main__":
    main()
