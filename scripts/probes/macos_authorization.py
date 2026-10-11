"""Owned synthetic macOS presence experiment, never production authority.

--check compiles and queries capabilities without a prompt or credential.
--review displays one fixed synthetic review and requires actual human input.
Only a fresh process-lifetime key is used; no persistent credential is created. No research paths or
provider input are accepted; Windows remains a separate platform adapter.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE = Path(__file__).with_name("native") / "MacAuthority.swift"


class ProbeError(RuntimeError):
    """A native result could not establish the requested bounded observation."""


def temporary_root():
    root = Path(tempfile.gettempdir()).resolve(strict=True)
    if not root.is_dir() or any((p / ".git").exists() for p in (root, *root.parents)):
        raise ProbeError("A temporary directory outside Git is required")
    return root


def decode_result(completed):
    try:
        result = json.loads(completed.stdout)
    except (ValueError, TypeError) as error:
        raise ProbeError("Native probe did not return one JSON result") from error
    if not isinstance(result, dict):
        raise ProbeError("Native probe returned an invalid result")
    if result.get("authorization_verified") is not False:
        raise ProbeError("An experiment cannot issue product authorization")
    if completed.returncode not in (0, 1):
        raise ProbeError("Native probe exited unexpectedly")
    status = result.get("status")
    if status not in ("available", "unavailable", "matched", "cancelled", "expired", "error"):
        raise ProbeError("Native probe returned an unknown status")
    if completed.returncode != (1 if status == "error" else 0):
        raise ProbeError("Native status and exit code disagree")
    if status in ("cancelled", "expired") and (
        result.get("presence_verified") is not False or result.get("signature_verified") is not False
        or result.get("key_storage") != "ephemeral"
        or any(key in result for key in ("signature_der", "public_key_x963", "message"))
    ):
        raise ProbeError("Cancelled or expired results cannot retain authorization material")
    if result.get("status") == "matched" and not all(
        result.get(key) is True for key in
        ("presence_verified", "signature_verified", "private_export_denied")
    ):
        raise ProbeError("A matching result requires presence, signature and key evidence")
    if status == "matched" and (result.get("key_storage") != "ephemeral"
                                 or result.get("persistent_custody_verified") is not False):
        raise ProbeError("This probe cannot establish persistent key custody")
    return result


def probe(*, review=False):
    if sys.platform != "darwin":
        return {"status": "unsupported", "authorization_verified": False,
                "reason": "This adapter requires macOS; no native call was made."}
    root = temporary_root()
    with tempfile.TemporaryDirectory(prefix="claimbranch-mac-authority-", dir=root) as directory:
        binary = Path(directory) / "authority"
        built = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(binary)],
                               capture_output=True, text=True, timeout=90, check=False)
        if built.returncode:
            raise ProbeError("Native build failed: " + built.stderr[:2000])
        command = [str(binary), "--review"] if review else [str(binary), "--check"]
        return decode_result(subprocess.run(command, capture_output=True, text=True,
                                            timeout=105 if review else 15, check=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--review", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = probe(review=args.review)
    except (OSError, subprocess.TimeoutExpired, ProbeError) as error:
        result = {"status": "error", "reason": str(error), "authorization_verified": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in ("available", "matched", "cancelled") else (
        3 if result["status"] in ("unsupported", "unavailable", "expired") else 1)


if __name__ == "__main__":
    raise SystemExit(main())
