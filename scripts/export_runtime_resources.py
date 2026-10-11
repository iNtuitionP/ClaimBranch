"""Copy/check the explicit runtime fixture inventory; originals remain canonical."""
import argparse
from pathlib import Path

from claimbranch.fixtures import replay_example
from claimbranch.validation.truth_packet import ARTIFACT_ROLES, TruthPacketValidator


ROOT = Path(__file__).resolve().parents[1]


def require_unlinked(path, root):
    """Reject links inside the checkout, without rejecting system temp aliases."""
    path.relative_to(root)
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError("runtime resource must not be a symlink")
        if candidate == root:
            break


def resource_bytes(root=ROOT):
    root = Path(root).resolve(strict=True)
    source = root / "tests/fixtures"
    names = ["saturation/truth-packet/" + name for name in ("manifest.json", *ARTIFACT_ROLES)]
    for variant in ("manual", "recorded"):
        for folder, stem in (("saturation", "research-" + variant), ("paper-argument", variant), ("paper-series", variant)):
            names.extend(folder + "/" + stem + suffix for suffix in (".json", ".golden.json"))
    for name in names:
        path = source / name
        require_unlinked(path, root)
        if not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise ValueError("runtime resource exceeds its regular-file budget")
    validator = TruthPacketValidator(source / "saturation/truth-packet")
    validator.validate()
    if validator.errors:
        raise ValueError("source fixture validation failed: " + "; ".join(validator.errors))
    for variant in ("manual", "recorded"):
        for paper, series, folder in ((False, False, "saturation"), (True, False, "paper-argument"), (False, True, "paper-series")):
            replay_example(variant, paper=paper, series=series, root=source / folder)
    result = {}
    for name in sorted(names):
        path = source / name
        require_unlinked(path, root)
        result[name] = path.read_bytes()
    return result


def check_resources(root=ROOT):
    root = Path(root).resolve(strict=True)
    expected = resource_bytes(root)
    destination = root / "claimbranch/data"
    if destination.is_symlink():
        raise ValueError("runtime resource directory must not be a symlink")
    paths = tuple(destination.rglob("*"))
    for path in paths:
        require_unlinked(path, root)
    present = {path.relative_to(destination).as_posix() for path in paths if path.is_file()}
    if present != set(expected):
        raise ValueError("runtime resource inventory differs; run python -m scripts.export_runtime_resources")
    for name, raw in expected.items():
        target = destination / name
        require_unlinked(target, root)
        if target.read_bytes() != raw:
            raise ValueError("runtime resource is stale or linked: " + name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check:
            check_resources()
            print("Runtime resources are current")
        else:
            for name, raw in resource_bytes().items():
                target = ROOT / "claimbranch/data" / name
                require_unlinked(target, ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            check_resources()
            print("Generated claimbranch/data from verified fixture sources")
        return 0
    except (OSError, ValueError) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
