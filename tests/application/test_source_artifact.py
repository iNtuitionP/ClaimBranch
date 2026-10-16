import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import subprocess
import sys
import unittest
import zipfile
from unittest.mock import patch

from scripts.build_source import build_source
from scripts.check_source_artifact import check_source_artifact
from scripts.export_runtime_resources import check_resources


ROOT = Path(__file__).resolve().parents[2]


class SourceArtifactTests(unittest.TestCase):
    def test_reproducible_runtime_inventory_and_isolated_launch(self):
        with tempfile.TemporaryDirectory(prefix="claimbranch-package-") as directory:
            root = Path(directory)
            first, second = root / "first.zip", root / "second.zip"
            build_source(first)
            build_source(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertEqual(163, len(names))
                self.assertEqual((ROOT / "LICENSE").read_bytes(), archive.read("LICENSE"))
                self.assertEqual(len(names), len(set(names)))
                self.assertFalse(any(name.startswith(("scripts/", "tests/", ".git/")) or "__pycache__" in name for name in names))
                manifest = json.loads(archive.read("artifact.json"))
                self.assertEqual("personal-terminal-alpha", manifest["kind"])
                self.assertFalse(manifest["authorization_verified"])
                self.assertEqual(set(names) - {"artifact.json"}, set(manifest["files"]))
                for name, expected in manifest["files"].items():
                    self.assertEqual(expected, hashlib.sha256(archive.read(name)).hexdigest())
            result = check_source_artifact(first, temp_root=root)
            self.assertEqual(["doctor", "saturation", "paper", "paper-draft", "paper-episodes", "paper-provider", "tui", "loopback", "personal-pty", "personal-rescue", "paper-profile-pty", "paper-profile-rescue"], result["checks"])
            self.assertEqual("personal-terminal-alpha", result["kind"])
            self.assertFalse(result["authorization_verified"])

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "owned.zip"
            target.write_bytes(b"keep existing")
            with self.assertRaises(FileExistsError):
                build_source(target)
            self.assertEqual(b"keep existing", target.read_bytes())

    def test_builder_refuses_checker_member_limit_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); package=root/'claimbranch'; package.mkdir()
            (root / 'LICENSE').write_bytes((ROOT / 'LICENSE').read_bytes())
            # 161 runtime modules plus START-HERE, LICENSE and manifest exceed
            # the explicitly supported 163-member artifact by one.
            for index in range(161):
                (package/f'module_{index}.py').write_text('# bounded source\n',encoding='utf-8')
            target=root/'oversized-inventory.zip'
            with patch('scripts.build_source.check_resources'), self.assertRaisesRegex(ValueError,'inventory'):
                build_source(target,root=root)
            self.assertFalse(target.exists())

    def test_stale_resource_or_link_cannot_enter_an_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(ROOT / "LICENSE", root / "LICENSE")
            shutil.copytree(ROOT / "claimbranch", root / "claimbranch", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "tests/fixtures", root / "tests/fixtures")
            check_resources(root)
            target = root / "claimbranch/data/paper-argument/manual.json"
            original = target.read_bytes()
            target.write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                build_source(root / "stale.zip", root=root)
            self.assertFalse((root / "stale.zip").exists())
            target.write_bytes(original)
            private = root / "never-package.py"
            private.write_text("raise RuntimeError('not part of the runtime')", encoding="utf-8")
            link = root / "claimbranch/unexpected.py"
            link.symlink_to(private)
            with self.assertRaises(ValueError):
                build_source(root / "linked.zip", root=root)
            self.assertFalse((root / "linked.zip").exists())

    def test_tampered_and_escaping_archives_are_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good = root / "good.zip"
            build_source(good)
            for index, member in enumerate(('claimbranch/__init__.py', '../outside.py',
                                            '/outside.py', 'a//b', 'a\\b', 'a:b')):
                bad = root / ('bad-%s.zip' % index)
                tampered = index == 0
                with zipfile.ZipFile(good) as source, zipfile.ZipFile(bad, 'w') as destination:
                    for info in source.infolist():
                        if info.filename == 'claimbranch/__init__.py':
                            destination.writestr(member, b"raise RuntimeError('tampered')")
                        else:
                            destination.writestr(info, source.read(info))
                with self.assertRaisesRegex(ValueError, 'hash mismatch' if tampered else 'invalid source-preview member'):
                    check_source_artifact(bad, temp_root=root)
                self.assertFalse((root / 'outside.py').exists())

    def test_extracted_runtime_refusal_and_actual_missing_curses_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / 'source.zip'
            build_source(artifact)
            from scripts.check_source_artifact import _unpack
            destination = root / 'extracted'
            destination.mkdir()
            _unpack(artifact, destination)
            for old in (True, False):
                program = """import runpy, sys
OLD = %s
if OLD:
    sys.version_info = (3, 9, 6)
class DenyImports:
    def find_spec(self, fullname, path=None, target=None):
        if OLD and (fullname.startswith('claimbranch.application') or fullname.startswith('claimbranch.core')):
            raise AssertionError('application imported')
        if fullname in ('curses', '_curses'):
            raise ImportError('missing curses')
sys.meta_path.insert(0, DenyImports())
sys.argv = ['claimbranch', 'doctor', '--json']
runpy.run_module('claimbranch', run_name='__main__')
""" % old
                result = subprocess.run([sys.executable, '-E', '-s', '-B', '-c', program],
                    cwd=destination, capture_output=True, text=True, timeout=15)
                self.assertEqual((3, ''), (result.returncode, result.stderr))
                value = json.loads(result.stdout)
                self.assertEqual('not-run' if old else 'ready', value['synthetic_replay'])
                self.assertIsNone(value['prerequisites']['unix-curses']) if old else self.assertFalse(value['prerequisites']['unix-curses'])



if __name__ == "__main__":
    unittest.main()
