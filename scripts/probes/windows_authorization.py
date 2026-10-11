"""Read-only A2 WebAuthn capability query, NEVER proof of authorization.

Calls two discovery APIs only. No credential enumeration, creation, deletion,
enrollment, prompt, receipt, key export, network, or research-state access.
Availability is only a prerequisite for a later foreground experiment.
"""

import argparse
import ctypes
import json
import os
import sys


class ProbeError(RuntimeError):
    """Windows did not return a successful capability observation."""

    def __init__(self, message, *, api_version=None):
        super().__init__(message)
        self.api_version = api_version


def _read_capabilities():
    # Restrict loading to the OS directory, never a DLL in the working tree.
    library = ctypes.WinDLL("webauthn.dll", winmode=0x00000800)
    version = library.WebAuthNGetApiVersionNumber
    version.argtypes = []
    version.restype = ctypes.c_uint32
    available = library.WebAuthNIsUserVerifyingPlatformAuthenticatorAvailable
    available.argtypes = [ctypes.POINTER(ctypes.c_int32)]
    available.restype = ctypes.c_int32
    api_version = version()
    observed = ctypes.c_int32()
    result = available(ctypes.byref(observed))
    if result != 0:  # The documented success value is S_OK.
        raise ProbeError(
            f"WebAuthn capability query failed (HRESULT 0x{result & 0xffffffff:08x})",
            api_version=api_version,
        )
    return api_version, bool(observed.value)


def probe_capabilities():
    """Report observed prerequisites without equating availability with consent."""
    report = {"status": "unsupported", "api_version": None,
              "platform_authenticator_available": None,
              "authorization_verified": False}
    if os.name != "nt":
        return dict(report, reason="This capability query requires Windows.")
    try:
        version, available = _read_capabilities()
    except (OSError, AttributeError, ProbeError) as error:
        # A failed Windows call is not evidence of denied access or absence.
        reason = str(error) if isinstance(error, ProbeError) else \
            "System WebAuthn DLL or required discovery export could not be loaded."
        return dict(report, status="error", reason=reason,
                    api_version=error.api_version if isinstance(error, ProbeError) else None)
    report.update(api_version=version, platform_authenticator_available=available)
    if version < 4:
        return dict(report, status="unavailable", reason=
                    "API version 4 is required for the candidate disposable-credential cleanup path.")
    if not available:
        return dict(report, status="unavailable", reason=
                    "No user-verifying platform authenticator was reported; no enrollment attempted.")
    return dict(report, status="available", reason=
                "Capability prerequisites observed only; foreground authorization remains unverified.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True,
                        help="Query capabilities without creating a credential or prompting")
    parser.parse_args(argv)
    report = probe_capabilities()
    print(json.dumps(report, sort_keys=True))
    return {"available": 0, "unsupported": 3, "unavailable": 3, "error": 1}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
