"""Bundled candidate examples shared by source and packaged applications."""
from pathlib import Path

from .core.canonical import ContractError, canonical_bytes, decode
from .core.research_history import ResearchHistory


DATA = Path(__file__).with_name("data")


def replay_example(variant="manual", *, paper=False, series=False, root=None):
    if variant not in ("manual", "recorded"):
        raise ContractError("unknown example variant")
    root = root if root is not None else DATA / ("paper-series" if series else "paper-argument" if paper else "saturation")
    stem = variant if paper or series else "research-" + variant
    value = decode((root / (stem + ".json")).read_bytes())
    required = {"profile", "seed", "commands"} | ({"classification"} if paper or series else set())
    version = 3 if series else 2 if paper else 1
    if (type(value) is not dict or set(value) != required
            or value["profile"] != f"portable-research/v{version}"
            or ((paper or series) and value["classification"] != "synthetic-example")
            or type(value["seed"]) is not dict or value["seed"].get("schema_version") != version
            or type(value["commands"]) is not list):
        raise ContractError("unknown frozen-history profile")
    history = ResearchHistory.replay(canonical_bytes(value["seed"]), tuple(canonical_bytes(cmd) for cmd in value["commands"]))
    if history.manifest() + b"\n" != (root / (stem + ".golden.json")).read_bytes():
        raise ContractError("replayed history differs from its frozen golden")
    return history


def replay_merge_example(variant='manual'):
    """Explicit rehearsal at the last merge boundary of the verified series."""
    history = replay_example(variant, series=True)
    boundary = max(index for index, raw in enumerate(history.commands)
                   if decode(raw)['operation_type'] == 'apply-selected-merge')
    return ResearchHistory.replay(history.seed, history.commands[:boundary])
