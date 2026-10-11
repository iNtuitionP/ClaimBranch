"""Replay the separately identified synthetic paper example, never private data."""
from pathlib import Path

from claimbranch.fixtures import replay_example


FIXTURES = Path(__file__).resolve().parents[1] / "tests/fixtures/paper-argument"


def replay_fixture(variant="manual"):
    return replay_example(variant, paper=True, root=FIXTURES)
