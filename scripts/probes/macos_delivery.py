"""Measure mutually checked native peers with disposable synthetic local IPC.

Temporary ad-hoc identities prove exact code matching, not distributed product
identity or worker confinement. No credential, sandbox, authorization receipt,
protected store, real research input or network connection is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import select
import shutil
import stat
import subprocess
import sys
import tempfile

from claimbranch.core.canonical import ContractError, decode
from scripts.probes.macos_authorization import ProbeError, temporary_root

SOURCE = Path(__file__).with_name("native") / "MacDelivery.swift"
ROLES = {"gateway", "broker", "worker"}
MODES = {"valid", "changed", "wrong-project", "cancel", "stale", "oversized", "truncated"}
OUTCOMES = {"received", "peer_rejected", "binding_rejected", "replay_rejected", "cancelled", "expired", "input_rejected"}


def binding():
    return json.dumps({"format": "claimbranch-private-delivery-probe/v1", "project": "synthetic-project",
                       "operation": hashlib.sha256(b"synthetic exact operation").hexdigest(),
                       "nonce": secrets.token_hex(32)}, sort_keys=True, separators=(",", ":")).encode()


def owned_root(root):
    root = Path(root)
    info = root.lstat()
    if (root.is_symlink() or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700 or root.resolve() != root):
        raise ProbeError("a resolved, owned 0700 temporary directory is required")
    if len(os.fsencode(root / "s")) >= 104:
        raise ProbeError("native socket path exceeds macOS sockaddr_un bound")
    return root


def build(root):
    root = owned_root(root)
    binary = root / "native"
    if binary.exists() or binary.is_symlink():
        raise ProbeError("native build destination already exists")
    built = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(binary)],
                           capture_output=True, text=True, timeout=90)
    if built.returncode:
        raise ProbeError("delivery helper build failed: " + built.stderr[:2400])
    peers = {}
    for role in sorted(ROLES):
        path = root / role
        # Owned disposable directory; never overwrite an existing helper.
        with binary.open("rb") as source, path.open("xb") as destination:
            shutil.copyfileobj(source, destination)
        path.chmod(0o700)
        identifier = "org.claimbranch.deliveryprobe." + role
        signed = subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime",
                                 "--identifier", identifier, str(path)], capture_output=True, timeout=15)
        if signed.returncode:
            raise ProbeError("temporary ad-hoc signing failed")
        inspected = subprocess.run(["/usr/bin/codesign", "-d", "--verbose=4", str(path)],
                                   capture_output=True, text=True, timeout=15)
        hashes = re.findall(r"^CDHash=([0-9a-f]{40})$", inspected.stderr, re.MULTILINE)
        if inspected.returncode or len(hashes) != 1:
            raise ProbeError("cannot pin native code identity")
        peers[role] = {"path": str(path), "requirement": f'identifier "{identifier}" and cdhash H"{hashes[0]}"'}
    return peers


def result(raw, kind):
    if len(raw) > 4096:
        raise ProbeError("native delivery output exceeds its bound")
    try:
        value = decode(raw)
    except ContractError as error:
        raise ProbeError("invalid native delivery JSON") from error
    common = {"schema_version", "status", "authorization_verified"}
    fields = {"ready": set(), "client": {"peer_verified", "binding_sent"},
              "server": {"outcomes", "consumed"}}[kind]
    if (type(value) is not dict or set(value) != common | fields or type(value["schema_version"]) is not int
            or value["schema_version"] != 1 or value["authorization_verified"] is not False):
        raise ProbeError("invalid delivery result shape or authority")
    if kind == "ready" and value["status"] != "ready":
        raise ProbeError("native receiver did not become ready")
    if kind == "client":
        if (type(value["status"]) is not str or value["status"] not in OUTCOMES or any(type(value[k]) is not bool for k in fields)
                or (value["binding_sent"] and not value["peer_verified"])
                or (not value["binding_sent"] and value["status"] != "peer_rejected")):
            raise ProbeError("invalid client observation")
    if kind == "server":
        if (value["status"] != "completed" or type(value["consumed"]) is not int or value["consumed"] not in (0, 1)
                or type(value["outcomes"]) is not list or not 1 <= len(value["outcomes"]) <= 16
                or any(type(v) is not str or v not in OUTCOMES for v in value["outcomes"])
                or value["outcomes"].count("received") != value["consumed"]):
            raise ProbeError("invalid single-consumption observation")
    return value


def exchange(root, peers, clients, *, server_role="gateway", old_binding=None, expired=False):
    root = owned_root(root)
    if (server_role not in ROLES or type(expired) is not bool or not 1 <= len(clients) <= 16
            or any(role not in ROLES or mode not in MODES or target not in ROLES for role, mode, target in clients)):
        raise ProbeError("bounded synthetic peers and cases required")
    if old_binding is not None and (type(old_binding) is not bytes or not 1 <= len(old_binding) <= 512):
        raise ProbeError("bounded prior synthetic binding required")
    socket = root / "s"
    if socket.exists() or socket.is_symlink():
        raise ProbeError("socket destination already exists")
    current = binding()
    process = subprocess.Popen([peers[server_role]["path"], "server", str(socket), peers["broker"]["requirement"],
                                str(len(clients)), "expired" if expired else "current"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=root, bufsize=0)
    observations = []
    try:
        process.stdin.write(current)
        process.stdin.close()
        process.stdin = None
        if not select.select([process.stdout], [], [], 10)[0]:
            raise ProbeError("native receiver readiness timed out")
        result(process.stdout.readline(4097), "ready")
        for role, mode, target in clients:
            data = old_binding if mode == "stale" else current
            if data is None:
                raise ProbeError("stale case requires a previous binding")
            completed = subprocess.run([peers[role]["path"], "client", str(socket), peers[target]["requirement"],
                                        mode, "synthetic"], input=data, capture_output=True, cwd=root, timeout=8)
            if completed.returncode:
                raise ProbeError("native sender did not return a bounded observation")
            observations.append(result(completed.stdout, "client"))
        stdout, _ = process.communicate(timeout=8)
        if process.returncode:
            raise ProbeError("native receiver failed")
        received = result(stdout, "server")
        if len(received["outcomes"]) != len(clients) or socket.exists() or socket.is_symlink():
            raise ProbeError("native exchange count or cleanup mismatch")
        return {"server": received, "clients": observations, "authorization_verified": False}
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)


def probe(*, exercise=False):
    if type(exercise) is not bool:
        raise ProbeError("explicit exercise choice required")
    if sys.platform != "darwin":
        return {"status": "unsupported", "authorization_verified": False}
    with tempfile.TemporaryDirectory(prefix="cb-ipc-", dir=temporary_root()) as directory:
        root = Path(directory).resolve()
        peers = build(root)
        if not exercise:
            report = {"status": "built", "authorization_verified": False, "peer_delivery_verified": False}
        else:
            cases = [
                ([("worker", "valid", "gateway"), ("broker", "wrong-project", "gateway"),
                  ("broker", "changed", "gateway"), ("broker", "valid", "gateway"),
                  ("broker", "valid", "gateway")], {}, ["peer_rejected", "binding_rejected", "binding_rejected", "received", "replay_rejected"]),
                ([("broker", "valid", "gateway")], {"server_role": "worker"}, None),
                ([("broker", "cancel", "gateway"), ("broker", "valid", "gateway")], {}, ["cancelled", "cancelled"]),
                ([("broker", "stale", "gateway")], {"old_binding": binding()}, ["binding_rejected"]),
                ([("broker", "valid", "gateway")], {"expired": True}, ["expired"]),
                ([("broker", "oversized", "gateway")], {}, ["input_rejected"]),
                ([("broker", "truncated", "gateway")], {}, ["input_rejected"]),
            ]
            for clients, options, expected in cases:
                value = exchange(root, peers, clients, **options)
                if expected is None:
                    if value["clients"][0]["binding_sent"] or value["clients"][0]["peer_verified"] or value["server"]["consumed"]:
                        raise ProbeError("wrong receiver was trusted")
                elif (value["server"]["outcomes"] != expected or value["server"]["consumed"] != expected.count("received")
                      or [client["status"] for client in value["clients"]] != expected
                      or not all(client["peer_verified"] for client in value["clients"])):
                    raise ProbeError("native rejection or consumption gate failed")
            report = {"status": "observed", "peer_delivery_verified": True, "cases": len(cases),
                      "authorization_verified": False, "product_identity_verified": False,
                      "worker_isolation_verified": False}
    report["cleanup_verified"] = not root.exists()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--exercise", action="store_true")
    args = parser.parse_args(argv)
    try:
        value = probe(exercise=args.exercise)
    except (OSError, subprocess.TimeoutExpired, ProbeError) as error:
        value = {"status": "error", "reason": str(error), "authorization_verified": False}
    print(json.dumps(value, sort_keys=True))
    return 0 if value["status"] == "observed" else 3 if value["status"] in ("built", "unsupported") else 1


if __name__ == "__main__":
    raise SystemExit(main())
