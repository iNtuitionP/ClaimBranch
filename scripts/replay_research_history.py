"""Replay frozen portable research candidates; no provider, store or OS approval."""
import argparse
import json
from pathlib import Path

from claimbranch.core.canonical import ContractError
from claimbranch.fixtures import replay_example


FIXTURES = Path(__file__).resolve().parents[1] / "tests/fixtures/saturation"


def replay_fixture(variant):
    return replay_example(variant, root=FIXTURES)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("manual", "recorded", "both"), default="both")
    args = parser.parse_args(argv)
    variants = ("manual", "recorded") if args.variant == "both" else (args.variant,)
    try:
        results = []
        for variant in variants:
            history = replay_fixture(variant)
            view = history.view("main")
            results.append({"variant": variant, "golden_match": True, "operations": len(history.commands),
                "observations": len(view["evidence"]), "claim_status": view["claim"]["status"],
                "ai_influenced": any(item["contributor"] == "ai" for item in view["judgment"]["history"]),
                "authorization_verified": False})
        print(json.dumps(results, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ContractError) as error:
        print(json.dumps({"status": "error", "reason": str(error), "authorization_verified": False}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
