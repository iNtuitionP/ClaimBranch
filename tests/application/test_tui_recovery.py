import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.tui_model import TerminalWorkspace
from claimbranch.fixtures import replay_example


@unittest.skipUnless(os.name == 'posix', 'private terminal recovery uses Unix file locks')
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'drafts.json'
        self.history = replay_example('manual', paper=True)
        self.app = TerminalWorkspace(self.history)

    def open(self, app=None):
        from claimbranch.application.tui_recovery import DraftRecovery
        store = DraftRecovery(self.path, app or self.app)
        self.addCleanup(store.close)
        return store

    def test_roundtrip_separates_cancelled_edit_kept_note_and_branches(self):
        original = self.history.manifest()
        store = self.open()
        self.app.select('obs-1')
        self.app.keep_note('kept note')
        self.app.unfinished[('main', 'obs-1', 'note')] = ['not kept yet']
        self.app.switch_ref()
        self.app.keep_note('alternative note')
        store.save(self.app)
        store.close()
        restored = TerminalWorkspace(self.history)
        self.open(restored)
        self.assertEqual(self.app.notes, restored.notes)
        self.assertEqual(self.app.unfinished, restored.unfinished)
        self.assertEqual('alternative', restored.ref)
        self.assertEqual(original, self.history.manifest())
        self.assertEqual(0o600, self.path.stat().st_mode & 0o777)

    def test_exclusive_session_and_atomic_failure_preserve_previous_checkpoint(self):
        store = self.open()
        self.app.keep_note('previous')
        store.save(self.app)
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'already open'):
            self.open()
        self.app.keep_note('new')
        with patch('claimbranch.application.tui_recovery.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError): store.save(self.app)
        self.assertEqual(original, self.path.read_bytes())

    def test_wrong_history_malformed_and_symlink_are_never_overwritten(self):
        store = self.open()
        store.save(self.app)
        store.close()
        raw = json.loads(self.path.read_text())
        raw['history'] = 'wrong'
        self.path.write_text(json.dumps(raw))
        old = self.path.read_bytes()
        with self.assertRaises(ValueError): self.open()
        self.assertEqual(old, self.path.read_bytes())
        self.path.write_text('{}')
        with self.assertRaises(ValueError): self.open()
        self.path.unlink()
        target = self.path.with_name('unrelated')
        target.write_text('untouched')
        self.path.symlink_to(target)
        with self.assertRaises((ValueError, OSError)): self.open()
        self.assertEqual('untouched', target.read_text())

    def test_git_tree_is_rejected_before_creating_any_files(self):
        (self.path.parent / '.git').mkdir()
        with self.assertRaisesRegex(ValueError, 'outside Git'): self.open()
        self.assertFalse(self.path.exists())
        self.assertFalse(self.path.with_suffix('.json.lock').exists())

    def test_deeply_nested_json_fails_without_a_traceback_or_overwrite(self):
        raw = '[' * 2000 + '0' + ']' * 2000
        self.path.write_text(raw)
        self.path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'Malformed|invalid'): self.open()
        self.assertEqual(raw, self.path.read_text())


if __name__ == '__main__': unittest.main()
