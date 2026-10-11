"""Actual native reads of synthetic associations; no GUI/key or accepted write."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from claimbranch.application.mac_runtime import SOURCE
from claimbranch.core.canonical import canonical_bytes, decode
from tests.application.test_project_work import AssociationFixture
from tests.application.test_mac_initial_target import enrollment_read_helpers


@unittest.skipUnless(sys.platform == 'darwin', 'native source checks require macOS')
class NativeInitialSourceTests(AssociationFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='cb-native-source-test-')
        cls.addClassCleanup(cls.temporary.cleanup)
        root = Path(cls.temporary.name)
        source = SOURCE.read_text()
        helpers = source[source.index('func initialIdentifier('):source.index('func signingOperation(')]
        # Compile the production filesystem helper with a minimal request holder.
        # This checks real file access, not enrollment/presence/accepted authority.
        support = SOURCE.with_name('InitialSource.swift').read_text()
        program = root/'check.swift'
        program.write_text('import Foundation\nimport Darwin\nimport CryptoKit\n' +
            'enum DeliveryError: Error { case invalid, io, timeout }\n' +
            'func hashHex(_ raw: Data) -> String { SHA256.hash(data:raw).map { String(format:"%02x",$0) }.joined() }\n' +
            'func hexText(_ text: String,_ n: Int) -> Bool { text.utf8.count == n && text.utf8.allSatisfy { (48...57).contains($0) || (97...102).contains($0) } }\n' +
            'func visibleReviewText(_ text: String) -> String { text }\n' +
            # Only path/number helpers are needed; exclude the full seed parser.
            helpers[:helpers.index('func initializationOperation(')] +
            enrollment_read_helpers() +
            'struct NativeEnrollment { let directory: String; let body: [String:String]; let id: String }\n' +
            'struct ReviewSigningRequest { let operation: [String: Any]; let enrollment: NativeEnrollment? }\n' + support + r'''
do {
    let raw = try FileHandle.standardInput.readToEnd()!
    var operation = try JSONSerialization.jsonObject(with:raw) as! [String:Any]
    if let target = operation["inspect_target"] as? String {
        let fd = try localDirectory(target); defer { close(fd) }
        print(try localIdentity(fd)); exit(0)
    }
    if let inputs = operation["budget"] as? [Double], inputs.count == 4 {
        print(initialSigningAllowance(inputs[0],inputs[1],inputs[2],inputs[3])); exit(0)
    }
    let binding = operation.removeValue(forKey:"enrollment") as? [String:String]
    let enrollment = binding.map { NativeEnrollment(directory:$0["directory"]!,body:$0,id:$0["id"]!) }
    try ReviewSigningRequest(operation:operation,enrollment:enrollment).checkInitialSource()
    print("checked")
} catch { fputs("source-refused\n",stderr); exit(2) }
''')
        cls.binary = root/'check'
        result = subprocess.run(['/usr/bin/xcrun','swiftc',str(program),'-o',str(cls.binary)],
                                capture_output=True,timeout=90)
        if result.returncode:
            raise AssertionError(result.stderr.decode())

    def setUp(self):
        super().setUp()
        self.association = decode(self.preview().payload)
        # Synthetic target holder only; this does not create a native enrollment.
        directory = self.root/'enrolled'; directory.mkdir(mode=0o700)
        protected = directory/'protected'; protected.mkdir(mode=0o700)
        binding = protected/'binding'; binding.write_bytes(b'd'*64);binding.chmod(0o600)
        checked = subprocess.run([str(self.binary)],input=canonical_bytes({'inspect_target':str(protected)}),capture_output=True,timeout=10)
        self.assertEqual(0,checked.returncode,checked.stderr)
        self.enrollment={'directory':str(directory),'id':'d'*64,
                         'protected_identity':checked.stdout.decode().strip()}

    def check(self, association=None, *, accepted=True):
        operation = {'action':'initialize-project','association':association or self.association,'enrollment':self.enrollment}
        result = subprocess.run([str(self.binary)], input=canonical_bytes(operation),
                                capture_output=True,timeout=10)
        self.assertEqual(0 if accepted else 2,result.returncode,result.stderr)
        self.assertEqual(b'checked\n' if accepted else b'',result.stdout)
        self.assertEqual(b'' if accepted else b'source-refused\n',result.stderr)

    def restamp(self):
        info = self.manuscript.stat()
        self.association['source'].update(file_identity={'device':str(info.st_dev),'inode':str(info.st_ino)},
            size=str(info.st_size),mtime_ns=str(info.st_mtime_ns),ctime_ns=str(info.st_ctime_ns))

    def test_exact_source_and_workspace_are_read_only(self):
        before = self.manuscript.stat()
        self.check()
        self.assertEqual(self.source,self.manuscript.read_bytes())
        self.assertEqual(before.st_mtime_ns,self.manuscript.stat().st_mtime_ns)
        self.assertEqual([],list(self.workspace.iterdir()))

    def test_initial_source_route_refuses_nonempty_enrolled_target(self):
        self.check()
        record=Path(self.enrollment['directory'])/'protected/genesis.enc'
        record.write_bytes(b'existing protected state')
        self.check(accepted=False)
        self.assertEqual(b'existing protected state',record.read_bytes())

    def test_changed_bytes_refuse_even_with_current_forged_stamps(self):
        self.manuscript.write_bytes(self.source.replace(b'synthetic',b'different'))
        self.restamp()
        self.check(accepted=False)

    def test_replaced_source_same_bytes_refuses_identity(self):
        replacement = self.paper/'replacement.tex'; replacement.write_bytes(self.source)
        replacement.replace(self.manuscript)
        self.check(accepted=False)

    def test_missing_source_and_private_workspace_refuse(self):
        self.manuscript.unlink(); self.check(accepted=False)
        self.manuscript.write_bytes(self.source); self.restamp()
        self.workspace.chmod(0o710); self.check(accepted=False)

    def test_links_hardlinks_and_special_files_refuse(self):
        original = self.paper/'original.tex'; self.manuscript.rename(original)
        self.manuscript.symlink_to(original); self.check(accepted=False)
        self.manuscript.unlink(); os.link(original,self.manuscript)
        self.restamp(); self.check(accepted=False)
        self.manuscript.unlink(); os.mkfifo(self.manuscript)
        self.restamp(); self.check(accepted=False)

    def test_nested_git_and_linked_parent_refuse(self):
        nested = self.paper/'nested'; nested.mkdir()
        target = nested/'paper.tex'; target.write_bytes(self.source)
        self.association = decode(self.preview(manuscript='nested/paper.tex').payload)
        (nested/'.git').mkdir(); self.check(accepted=False)
        (nested/'.git').rmdir()
        moved = self.paper/'moved'; nested.rename(moved); nested.symlink_to(moved,target_is_directory=True)
        self.check(accepted=False)

    def test_marker_and_utf8_validation_cannot_be_forged_with_hashes(self):
        for raw in [self.source.replace(b'id=anchor',b'id=other'),self.source+self.source,b'\xff'+self.source,
                    self.source.replace(b'\n',b'\r\n')]:
            self.manuscript.write_bytes(raw); self.restamp()
            self.association['source']['source_digest'] = hashlib.sha256(raw).hexdigest()
            self.check(accepted=False)

    def test_git_directory_substitution_is_independently_refused(self):
        other = self.root/'other'; other.mkdir()
        subprocess.run(['/usr/bin/git','init','-q',str(other)],check=True)
        git = other/'.git'; info = git.stat()
        for prefix in ['git','git_common']:
            self.association['source'][prefix+'_dir'] = os.fsencode(git).hex()
            self.association['source'][prefix+'_identity'] = {'device':str(info.st_dev),'inode':str(info.st_ino)}
        self.check(accepted=False)

    def test_in_git_workspace_and_replaced_workspace_refuse(self):
        work = self.paper/'private';work.mkdir(mode=0o700);info=work.stat()
        value = decode(canonical_bytes(self.association))
        value.update(workspace=os.fsencode(work).hex(),workspace_identity={'device':str(info.st_dev),'inode':str(info.st_ino)})
        self.check(value,accepted=False)
        moved = self.root/'old-work';self.workspace.rename(moved);self.workspace.mkdir(mode=0o700)
        self.check(accepted=False)

    def test_unicode_filename_bytes_are_retained_and_unavailable_path_refuses(self):
        for name in ['e\u0301 원고.tex','é 원고.tex']:
            (self.paper/name).write_bytes(self.source)
            association = decode(self.preview(manuscript=name).payload)
            self.assertEqual(os.fsencode(name).hex(),association['source']['manuscript'])
            self.check(association)
        self.assertEqual(1,len([p for p in self.paper.iterdir() if p.name.endswith(' 원고.tex')]))

        self.association['source']['manuscript'] = b'raw-\xff.tex'.hex()
        self.check(accepted=False)

    def test_unicode_git_root_survives_byte_exact_native_discovery(self):
        moved = self.root/'e\u0301 논문'
        self.paper.rename(moved); self.paper=moved; self.manuscript=moved/'paper.tex'
        self.check(decode(self.preview().payload))

    def test_git_config_fifo_is_bounded_without_a_prompt(self):
        import time
        import errno
        fifo = self.root/'blocked-config'; os.mkfifo(fifo)
        config = self.paper/'.git/config'
        config.write_text(config.read_text()+'\n[include]\npath = '+str(fifo)+'\n')
        start = time.monotonic(); self.check(accepted=False)
        elapsed = time.monotonic()-start
        self.assertGreaterEqual(elapsed,4.5)
        self.assertLess(elapsed,9)
        with self.assertRaises(OSError) as raised:
            os.open(fifo,os.O_WRONLY|os.O_NONBLOCK)
        self.assertEqual(errno.ENXIO,raised.exception.errno)

    def test_workspace_cannot_contain_paper_or_git_admin(self):
        self.root.chmod(0o700); info=self.root.stat()
        value=decode(canonical_bytes(self.association))
        value.update(workspace=os.fsencode(self.root).hex(),workspace_identity={'device':str(info.st_dev),'inode':str(info.st_ino)})
        self.check(value,accepted=False)

    def test_firmlink_alias_cannot_hide_workspace_containing_paper(self):
        alias=Path('/System/Volumes/Data')/self.root.relative_to('/')
        self.assertTrue(alias.is_dir(),'supported Mac needs the Data firmlink alias')
        self.assertTrue(os.path.samefile(alias,self.root))
        self.assertNotEqual(os.path.realpath(alias),os.path.realpath(self.root))
        info=alias.stat()
        value=decode(canonical_bytes(self.association))
        value.update(workspace=os.fsencode(alias).hex(),workspace_identity={'device':str(info.st_dev),'inode':str(info.st_ino)})
        self.check(value,accepted=False)

    def test_workspace_in_separate_worktree_or_bare_repository_refuses(self):
        for bare in [False,True]:
            other=self.root/('bare' if bare else 'separate'); other.mkdir()
            subprocess.run(['/usr/bin/git','init','-q']+(['--bare'] if bare else [])+[str(other)],check=True)
            work=other/'private';work.mkdir(mode=0o700);info=work.stat()
            value=decode(canonical_bytes(self.association))
            value.update(workspace=os.fsencode(work).hex(),workspace_identity={'device':str(info.st_dev),'inode':str(info.st_ino)})
            self.check(value,accepted=False)

    def test_dot_tex_without_basename_refuses_even_with_forged_binding(self):
        self.manuscript.rename(self.paper/'.tex'); self.manuscript=self.paper/'.tex'
        self.restamp(); self.association['source']['manuscript']=b'.tex'.hex()
        self.check(accepted=False)

    def test_legacy_action_does_not_load_initial_source(self):
        self.manuscript.unlink()
        record=Path(self.enrollment['directory'])/'protected/genesis.enc'
        record.write_bytes(b'existing state')
        result=subprocess.run([str(self.binary)],input=canonical_bytes({'action':'record-interpretation','enrollment':self.enrollment}),capture_output=True,timeout=10)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(b'checked\n',result.stdout)
        self.assertEqual(b'existing state',record.read_bytes())

    def test_initial_gate_reserves_expiry_and_peer_check_time(self):
        for inputs,expected in [([145,200,0,100],24),([1000,40,0,100],29),
                                ([1000,200,0,100],90),([120,200,0,100],-1)]:
            result=subprocess.run([str(self.binary)],input=canonical_bytes({'budget':inputs}),capture_output=True,timeout=10)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertEqual(expected,float(result.stdout))


class InitialSourceResourceTests(unittest.TestCase):
    def test_resource_bytes_and_link_bounds_are_part_of_the_build_pin(self):
        from unittest.mock import patch
        from claimbranch.application.mac_runtime import _source_bytes
        from claimbranch.core.canonical import ContractError
        with tempfile.TemporaryDirectory(prefix='cb-source-resources-') as folder:
            root = Path(folder); source=root/SOURCE.name
            source.write_bytes(SOURCE.read_bytes())
            for name in ('Enrollment.swift','InitialSource.swift'):
                (root/name).write_bytes(SOURCE.with_name(name).read_bytes())
            with patch('claimbranch.application.mac_runtime.SOURCE',source):
                before = _source_bytes()
                helper = root/'InitialSource.swift'; original=helper.read_bytes()
                helper.write_bytes(original+b'\n// explicit source change\n')
                self.assertNotEqual(before,_source_bytes())
                helper.write_bytes(b'x'*65537)
                with self.assertRaises(ContractError): _source_bytes()
                helper.unlink();helper.symlink_to(SOURCE.with_name('InitialSource.swift'))
                with self.assertRaises(ContractError): _source_bytes()
                helper.unlink();helper.write_bytes(original)
                source.write_bytes(source.read_bytes().replace(b'// CLAIMBRANCH_INITIAL_SOURCE_SUPPORT',b''))
                with self.assertRaises(ContractError): _source_bytes()
