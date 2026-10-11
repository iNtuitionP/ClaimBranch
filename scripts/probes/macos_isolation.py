"""Compare baseline and App Sandbox access to owned synthetic resources only.

No provider, research file, installed app, existing permissions, account,
entitlement profile or global settings are changed. The generated worker is
signed ad hoc. Cleanup is attempted for its exact owned resources; a blocked
cleanup is reported and prevents further experiments on that host.
"""

import argparse
import errno
import json
from pathlib import Path
import plistlib
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid

from scripts.probes.macos_authorization import ProbeError, temporary_root


SOURCE = Path(__file__).with_name("native") / "MacSandboxWorker.swift"


def assess(baseline, restricted, unchanged):
    for kind in ("read", "write", "network"):
        initial = baseline.get(kind, {})
        if initial.get("allowed") is not True or type(initial.get("errno")) is not int or initial["errno"] != 0:
            raise ProbeError("Baseline did not establish access: " + kind)
        result = restricted.get(kind, {})
        if result.get("allowed") is not False or type(result.get("errno")) is not int or result["errno"] not in (errno.EACCES, errno.EPERM):
            raise ProbeError("No observed sandbox denial: " + kind)
    if not unchanged:
        raise ProbeError("Protected synthetic bytes changed")
    return {"status": "denial_observed", "baseline": baseline, "restricted": restricted,
            "protected_bytes_unchanged": True, "provider_isolation_verified": False,
            "authorization_verified": False}


def probe():
    if sys.platform != "darwin":
        return {"status": "unsupported", "provider_isolation_verified": False,
                "authorization_verified": False}
    pending = sorted(path.name for path in (Path.home() / "Library" / "Containers").glob("org.claimbranch.sandboxprobe.*"))
    pending_scripts = sorted(path.name for path in (Path.home() / "Library" / "Application Scripts").glob("org.claimbranch.sandboxprobe.*"))
    if pending or pending_scripts:
        return {"status": "blocked_cleanup", "pending_containers": pending,
                "pending_application_scripts": pending_scripts,
                "cleanup_verified": False, "provider_isolation_verified": False,
                "authorization_verified": False}
    identifier = "org.claimbranch.sandboxprobe." + uuid.uuid4().hex
    container = Path.home() / "Library" / "Containers" / identifier
    if container.exists() or container.is_symlink():
        raise ProbeError("Refusing a preexisting container")
    with tempfile.TemporaryDirectory(prefix="claimbranch-mac-isolation-", dir=temporary_root()) as directory:
        root = Path(directory)
        plain = root / "worker"
        built = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(plain)],
                               capture_output=True, text=True, timeout=90)
        if built.returncode:
            raise ProbeError("Worker build failed: " + built.stderr[:1600])
        content = root / "protected.txt"
        original = b"Owned synthetic record; no research content.\n"
        content.write_bytes(original)
        app = root / "Worker.app"
        executable = app / "Contents" / "MacOS" / "worker"
        executable.parent.mkdir(parents=True)
        shutil.copy2(plain, executable)
        (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": identifier, "CFBundleExecutable": "worker",
            "CFBundlePackageType": "APPL", "CFBundleVersion": "1"}))
        entitlements = root / "entitlements.plist"
        entitlements.write_bytes(plistlib.dumps({"com.apple.security.app-sandbox": True}))
        signed = subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", "--entitlements", str(entitlements), str(app)],
                                capture_output=True, text=True, timeout=15)
        if signed.returncode:
            raise ProbeError("Ad-hoc worker signing failed: " + signed.stderr[:1200])
        report = {"status": "error", "authorization_verified": False, "provider_isolation_verified": False}
        try:
            with socket.socket() as server:
                server.bind(("127.0.0.1", 0))
                server.listen(4)
                port = str(server.getsockname()[1])

                def run(binary):
                    result = subprocess.run([str(binary), str(content), port],
                                            capture_output=True, text=True, timeout=15)
                    if result.returncode:
                        raise ProbeError("Worker did not return access results: " + result.stderr[:1200])
                    try:
                        decoded = json.loads(result.stdout)
                    except ValueError as error:
                        raise ProbeError("Invalid worker response") from error
                    if not isinstance(decoded, dict):
                        raise ProbeError("Invalid worker response")
                    return decoded

                baseline = run(plain)
                if content.read_bytes() != original + b"probe-write\n":
                    raise ProbeError("Baseline write was not observed")
                content.write_bytes(original)
                restricted = run(executable)
                report = assess(baseline, restricted, content.read_bytes() == original)
        except (OSError, subprocess.TimeoutExpired, ProbeError) as error:
            report["reason"] = str(error)
        finally:
            # The identifier is fresh and checked absent before starting the owned
            # child. Do not follow a replacement link or remove any other container.
            cleanup_errors = []
            owned_paths = (container, Path.home() / "Library" / "Application Scripts" / identifier)
            for owned in owned_paths:
                if owned.is_symlink():
                    cleanup_errors.append("Owned path became a link: " + str(owned))
                elif owned.exists():
                    try:
                        shutil.rmtree(owned)
                    except OSError as error:
                        cleanup_errors.append(str(owned) + " (errno " + str(error.errno) + ")")
            report["cleanup_verified"] = not cleanup_errors
            if cleanup_errors:
                report["observation_status"] = report["status"]
                report["status"] = "cleanup_failed"
                report["cleanup_errors"] = cleanup_errors
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        result = probe()
    except (OSError, subprocess.TimeoutExpired, ProbeError) as error:
        result = {"status": "error", "reason": str(error), "authorization_verified": False,
                  "provider_isolation_verified": False}
    print(json.dumps(result, sort_keys=True))
    return {"denial_observed": 0, "unsupported": 3, "blocked_cleanup": 3, "cleanup_failed": 1, "error": 1}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
