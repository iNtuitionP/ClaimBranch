"""Actual read-only empty-target checks; synthetic binding, no enrollment authority."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from claimbranch.application.mac_runtime import SOURCE
from claimbranch.core.canonical import canonical_bytes


def enrollment_read_helpers():
    enrollment = SOURCE.with_name('Enrollment.swift').read_text()
    source = SOURCE.read_text()
    return (enrollment[enrollment.index('func localDirectory('):enrollment.index('func localCreate(')] +
            enrollment[enrollment.index('func custodyScratch('):enrollment.index('func enrollmentWriter(')] +
            source[source.index('func sameKeyFile('):source.index('func reopenKey(')])


@unittest.skipUnless(sys.platform == 'darwin', 'native protected target requires macOS')
class NativeInitialTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='cb-initial-target-native-')
        cls.addClassCleanup(cls.temporary.cleanup)
        root = Path(cls.temporary.name)
        program = root/'check.swift'
        program.write_text('import Foundation\nimport Darwin\n'
            'enum DeliveryError: Error { case invalid, io, timeout }\n'
            'func hexText(_ text: String,_ n: Int) -> Bool { text.utf8.count == n && text.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }\n' +
            enrollment_read_helpers() + r'''
do {
    let raw = try FileHandle.standardInput.readToEnd()!
    let value = try JSONSerialization.jsonObject(with:raw) as! [String:String]
    if value["identity"] == "inspect" {
        let fd = try localDirectory(value["path"]!); defer { close(fd) }
        print(try localIdentity(fd))
    } else {
        try initialProtectedEmpty(value["path"]!, value["identity"]!, value["id"]!)
        print("empty-target")
    }
} catch { fputs("target-refused\n",stderr); exit(2) }
''')
        cls.binary = root/'check'
        result = subprocess.run(['/usr/bin/xcrun','swiftc',str(program),'-o',str(cls.binary)],capture_output=True,timeout=90)
        if result.returncode: raise AssertionError(result.stderr.decode())

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='cb-initial-target-case-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.target = self.root/'protected'; self.target.mkdir(mode=0o700)
        self.local_id = 'd'*64
        self.binding = self.target/'binding'; self.binding.write_bytes(self.local_id.encode()); self.binding.chmod(0o600)
        self.identity = self.run_target(identity='inspect').stdout.decode().strip()

    def run_target(self, **changes):
        value = {'path':str(self.target),'identity':getattr(self,'identity','inspect'),'id':self.local_id,**changes}
        return subprocess.run([str(self.binary)],input=canonical_bytes(value),capture_output=True,timeout=10)

    def check(self, accepted=True, **changes):
        result = self.run_target(**changes)
        self.assertEqual(0 if accepted else 2,result.returncode,result.stderr)
        self.assertEqual(b'empty-target\n' if accepted else b'',result.stdout)
        self.assertEqual(b'' if accepted else b'target-refused\n',result.stderr)

    def test_exact_bound_empty_target_is_read_only(self):
        before = self.binding.stat()
        directory_before = self.target.stat()
        self.check(); self.check()
        self.assertEqual(self.local_id.encode(),self.binding.read_bytes())
        after=self.binding.stat()
        for field in ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns'):
            self.assertEqual(getattr(before,field),getattr(after,field))
            self.assertEqual(getattr(directory_before,field),getattr(self.target.stat(),field))
        self.assertEqual(['binding'],sorted(p.name for p in self.target.iterdir()))

    def test_existing_genesis_pending_or_unknown_state_is_preserved(self):
        for name in ['genesis.enc','accepted.sqlite','pending','foreign']:
            with self.subTest(name=name):
                file = self.target/name; file.write_bytes(b'preserve existing state')
                self.check(False)
                self.assertEqual(b'preserve existing state',file.read_bytes()); file.unlink()
        folder = self.target/'records';folder.mkdir();self.check(False);folder.rmdir()
        link=self.target/'dangling';link.symlink_to('missing');self.check(False)
        self.assertTrue(link.is_symlink())

    def test_missing_wrong_or_malformed_binding_refuses(self):
        self.check(False,id='e'*64)
        self.check(False,id='bad-id')
        self.binding.write_bytes(self.local_id.encode()+b'\n');self.check(False)
        self.binding.unlink();self.check(False)

    def test_linked_or_nonprivate_binding_refuses(self):
        saved=self.root/'binding';self.binding.rename(saved)
        self.binding.symlink_to(saved);self.check(False);self.binding.unlink()
        os.link(saved,self.binding);self.check(False);self.binding.unlink()
        self.binding.write_bytes(self.local_id.encode());self.binding.chmod(0o644);self.check(False)
        self.binding.unlink();os.mkfifo(self.binding);self.check(False)

    def test_replaced_target_and_symlink_target_refuse(self):
        old=self.root/'old';self.target.rename(old);self.target.mkdir(mode=0o700)
        self.binding.write_bytes(self.local_id.encode());self.binding.chmod(0o600);self.check(False)
        self.binding.unlink();self.target.rmdir();self.target.symlink_to(old,target_is_directory=True);self.check(False)

    def test_private_mode_and_exact_directory_identity_are_required(self):
        self.target.chmod(0o710);self.check(False)
        self.target.chmod(0o700);self.check(False,identity='0:0:0:0')

    def test_safe_custody_scratch_is_retained_but_unsafe_scratch_refuses(self):
        for suffix in ('canary','renamed','created'):
            scratch=self.target/('.cb-denial-'+'a'*64+'-'+suffix)
            scratch.write_bytes(b'canary');scratch.chmod(0o600)
            self.check();self.assertEqual(b'canary',scratch.read_bytes());scratch.unlink()
        scratch=self.target/('.cb-denial-'+'a'*64+'-canary')
        scratch.write_bytes(b'canary');scratch.chmod(0o600)
        scratch.chmod(0o644);self.check(False)
        scratch.chmod(0o600);scratch.write_bytes(b'x'*129);self.check(False)
        scratch.unlink();scratch.symlink_to(self.binding);self.check(False);scratch.unlink()
        os.link(self.binding,scratch);self.check(False);scratch.unlink()
        os.mkfifo(scratch);self.check(False);scratch.unlink()
        scratch.mkdir(mode=0o600);self.check(False);scratch.rmdir()

    def test_scratch_near_misses_are_foreign_entries(self):
        for name in ['.cb-denial-'+'a'*63+'-canary','.cb-denial-'+'A'*64+'-canary',
                     '.cb-denial-'+'a'*64+'-canaryx','.cb-denial-'+'a'*64+'-unknown']:
            with self.subTest(name=name):
                file=self.target/name;file.write_bytes(b'foreign');file.chmod(0o600)
                self.check(False);self.assertEqual(b'foreign',file.read_bytes());file.unlink()

    def test_target_populated_after_empty_check_later_call_refuses(self):
        self.check()
        committed=self.target/'genesis.enc';committed.write_bytes(b'new state')
        self.check(False);self.assertEqual(b'new state',committed.read_bytes())
