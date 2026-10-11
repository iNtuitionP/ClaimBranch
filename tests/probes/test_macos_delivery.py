"""Actual kernel peer checks on disposable native binaries, never approval."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.probes.macos_authorization import ProbeError, temporary_root
from scripts.probes.macos_delivery import build, binding, exchange, probe, result


@unittest.skipUnless(sys.platform == "darwin", "native peer checks require macOS")
class NativeDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cb-ipc-", dir=temporary_root())
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.peers = build(cls.root)

    def test_kernel_identity_and_exact_binding_allow_only_one_delivery(self):
        result = exchange(self.root, self.peers, [
            ("worker", "valid", "gateway"), ("broker", "wrong-project", "gateway"),
            ("broker", "changed", "gateway"),
            ("broker", "valid", "gateway"), ("broker", "valid", "gateway")])
        self.assertEqual(["peer_rejected", "binding_rejected", "binding_rejected", "received", "replay_rejected"], result["server"]["outcomes"])
        self.assertEqual(1, result["server"]["consumed"])
        self.assertFalse(result["server"]["authorization_verified"])
        self.assertTrue(all(item["peer_verified"] for item in result["clients"]))
        self.assertFalse((self.root / "s").exists())

    def test_broker_rejects_wrong_signed_receiver_before_releasing_binding(self):
        result = exchange(self.root, self.peers, [("broker", "valid", "gateway")], server_role="worker")
        self.assertEqual("peer_rejected", result["clients"][0]["status"])
        self.assertFalse(result["clients"][0]["peer_verified"])
        self.assertFalse(result["clients"][0]["binding_sent"])
        self.assertEqual(0, result["server"]["consumed"])

    def test_old_session_expiry_and_malformed_frames_never_consume(self):
        result = exchange(self.root, self.peers, [("broker", "stale", "gateway")], old_binding=binding())
        self.assertEqual(["binding_rejected"], result["server"]["outcomes"])
        for mode, expected in (("oversized", "input_rejected"), ("truncated", "input_rejected")):
            with self.subTest(mode=mode):
                result = exchange(self.root, self.peers, [("broker", mode, "gateway")])
                self.assertEqual([expected], result["server"]["outcomes"])
                self.assertEqual(0, result["server"]["consumed"])
        result = exchange(self.root, self.peers, [("broker", "valid", "gateway")], expired=True)
        self.assertEqual(["expired"], result["server"]["outcomes"])
        self.assertEqual(0, result["server"]["consumed"])

    def test_cancel_is_terminal_for_this_binding(self):
        result = exchange(self.root, self.peers, [("broker", "cancel", "gateway"), ("broker", "valid", "gateway")])
        self.assertEqual(["cancelled", "cancelled"], result["server"]["outcomes"])
        self.assertEqual(0, result["server"]["consumed"])

    def test_matching_signed_code_without_runtime_hardening_is_rejected(self):
        path = self.root / "unhardened"
        shutil.copyfile(self.peers["broker"]["path"], path)
        path.chmod(0o700)
        signed = subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "0",
                                 "--identifier", "org.claimbranch.deliveryprobe.broker", str(path)], capture_output=True, timeout=15)
        self.assertEqual(0, signed.returncode, signed.stderr)
        inspected = subprocess.run(["/usr/bin/codesign", "-d", "--verbose=4", str(path)], capture_output=True, text=True, timeout=15)
        self.assertEqual(0, inspected.returncode, inspected.stderr)
        codehash, = re.findall(r"^CDHash=([0-9a-f]{40})$", inspected.stderr, re.MULTILINE)
        peers = dict(self.peers, broker={"path": str(path), "requirement":
                         f'identifier "org.claimbranch.deliveryprobe.broker" and cdhash H"{codehash}"'})
        value = exchange(self.root, peers, [("broker", "valid", "gateway")])
        self.assertEqual(["peer_rejected"], value["server"]["outcomes"])
        self.assertEqual(0, value["server"]["consumed"])
        self.assertFalse(value["clients"][0]["binding_sent"])

    def test_existing_socket_destination_is_preserved(self):
        path = self.root / "s"
        try:
            path.write_bytes(b"owned sentinel")
            with self.assertRaises(ProbeError):
                exchange(self.root, self.peers, [("broker", "valid", "gateway")])
            self.assertEqual(b"owned sentinel", path.read_bytes())
        finally:
            path.unlink()


class DeliveryDriverTests(unittest.TestCase):
    def test_native_status_cannot_claim_authority_or_hide_duplicate_consumption(self):
        value = {"schema_version": 1, "authorization_verified": False, "status": "completed",
                 "consumed": 1, "outcomes": ["received", "replay_rejected"]}
        self.assertEqual(value, result(json.dumps(value).encode(), "server"))
        for update in ({"authorization_verified": True}, {"consumed": True}, {"consumed": 0},
                       {"outcomes": ["received", "received"]}, {"outcomes": ["assumed"]}, {"extra": "secret"}):
            with self.subTest(update=update), self.assertRaises(ProbeError):
                result(json.dumps(dict(value, **update)).encode(), "server")
        client = {"schema_version": 1, "authorization_verified": False, "status": "received",
                  "peer_verified": True, "binding_sent": True}
        for update in ({"peer_verified": False}, {"binding_sent": False}, {"status": []}, {"peer_verified": 1}):
            with self.subTest(update=update), self.assertRaises(ProbeError):
                result(json.dumps(dict(client, **update)).encode(), "client")

    def test_unsupported_host_does_no_native_work(self):
        with patch("scripts.probes.macos_delivery.sys.platform", "win32"), \
                patch("scripts.probes.macos_delivery.build") as compile_native:
            result = probe(exercise=True)
        compile_native.assert_not_called()
        self.assertEqual("unsupported", result["status"])
        self.assertFalse(result["authorization_verified"])


if __name__ == "__main__":
    unittest.main()
