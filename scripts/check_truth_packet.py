#!/usr/bin/env python3
"""Repository adapter for the shared source-packet validator."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from claimbranch.validation.truth_packet import *  # Preserve contributor imports.
from claimbranch.validation.truth_packet import main as validate_main

DEFAULT_PACKET = ROOT / "tests/fixtures/saturation/truth-packet"


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    return validate_main(["--packet", str(DEFAULT_PACKET), *args])


if __name__ == "__main__":
    raise SystemExit(main())
