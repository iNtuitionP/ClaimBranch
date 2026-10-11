"""Bounded Secure Enclave key reconstruction across disposable processes.

--check creates no credential. --exercise creates a new synthetic key with
user-presence access control and interaction disabled, saves its encrypted
representation in an owned non-Git temporary directory, and measures reopen,
noninteractive signing denial and one-byte tampering. Constructor success or an
unclassified constructor error cannot prove integrity; this measurement returns
incomplete evidence (exit 3), never a passing integrity check. No sandbox container, Keychain
entry, existing credential, authorization receipt or research source is used.

--review first offers human-operated preparation of a new test key, followed by
a fixed review in a separate process. It verifies the bound public signature and
checks noninteractive denial again afterward. No failure triggers an automatic
switch from --exercise to interaction.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import secrets
import subprocess
import sys
import tempfile

from claimbranch.core.canonical import ContractError, decode, digest_text, integer
from scripts.probes.macos_authorization import ProbeError, temporary_root


SOURCE = Path(__file__).with_name("native") / "MacKeyReopen.swift"
COMMON = {"schema_version", "mode", "status", "process_id", "authorization_verified", "product_custody_verified"}
IDENTITY = {"public_key_digest", "representation_digest"}
ERROR = {"error_domain", "error_code"}
REVIEW = IDENTITY | {"review_digest", "challenge_digest"}
AUTHENTICATION = {"explicit_authentication_succeeded", "signing_started"}
CANCELLATION = {"cancel_source", "cancel_trigger", "cancel_error_domain", "cancel_error_code"}
DENIALS = {("NSOSStatusErrorDomain", -25308), ("com.apple.LocalAuthentication", -1004)}
GATE_CHECKS = {"cancel_before_start", "cancel_during_signing", "late_success", "single_start",
               "native_cancel", "wrong_error_domain", "finish_once", "success_before_deadline",
               "cancelled_creation", "late_creation", "creation_before_deadline",
               "unauthenticated_success_rejected", "failed_authentication_does_not_sign",
               "cancelled_authentication_does_not_sign", "late_authentication_does_not_sign",
               "authentication_callback_once", "native_cancel_survives_close_race",
               "app_invalidation_is_not_native_user_cancel", "missing_callback_is_not_invented"}


def review_message(review_digest, public_key_digest, representation_digest, nonce):
    try:
        for value in (review_digest, public_key_digest, representation_digest, nonce):
            digest_text(value)
    except ContractError as error:
        raise ProbeError("review binding requires four SHA-256-shaped values") from error
    return ("claimbranch:key-reopen-review:v1\n" + "\n".join(
        (review_digest, public_key_digest, representation_digest, nonce))).encode("ascii")


def public_bytes(value, minimum, maximum):
    if type(value) is not str or len(value) > 4 * ((maximum + 2) // 3):
        raise ProbeError("bounded base64 public material required")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, UnicodeError) as error:
        raise ProbeError("invalid public material encoding") from error
    if not minimum <= len(raw) <= maximum or base64.b64encode(raw).decode("ascii") != value:
        raise ProbeError("noncanonical or oversized public material")
    return raw


def validate(value, mode):
    if (type(value) is not dict or value.get("mode") != mode or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1 or value.get("authorization_verified") is not False
            or value.get("product_custody_verified") is not False):
        raise ProbeError("native custody output has invalid identity or authority")
    status = value.get("status")
    allowed = {"check": {"available", "unavailable", "error"}, "create": {"created", "error"},
               "reopen": {"reopened", "key_rejected", "error"},
               "deny": {"interaction_denied", "signature_without_interaction", "key_rejected", "error"},
               "review": {"matched", "cancelled", "expired", "error"},
               "prepare": {"created", "cancelled", "expired", "error"},
               "verify": {"verified", "rejected", "error"}, "gate-check": {"checked"}}
    if mode not in allowed or type(status) is not str or status not in allowed[mode]:
        raise ProbeError("unknown native custody phase/status")
    extra = (CANCELLATION.copy() if mode == "prepare" and status == "cancelled" else
             set() if mode == "prepare" and status == "expired" else
             REVIEW | {"signature_verified", "public_key_x963", "signature_der"} if status == "matched" else
             REVIEW | {"signature_verified"} | CANCELLATION if status == "cancelled" else
             REVIEW | {"signature_verified"} if status in ("expired", "verified", "rejected") else
             {"checks"} if status == "checked" else
             IDENTITY | ERROR if status == "interaction_denied" else
             IDENTITY if status in ("created", "reopened", "signature_without_interaction") else
             {"secure_enclave_available"} if status in ("available", "unavailable") else ERROR)
    if mode == "review" and status in ("matched", "cancelled", "expired"):
        extra |= AUTHENTICATION
    if set(value) != COMMON | extra:
        raise ProbeError("native custody result contains unexpected or missing fields")
    try:
        integer(value["process_id"], 1)
        for key in REVIEW & extra:
            digest_text(value[key])
        if ERROR <= extra:
            integer(value["error_code"], -(2**31), 2**31 - 1)
            if type(value["error_domain"]) is not str or not 1 <= len(value["error_domain"]) <= 128:
                raise ContractError("bounded native error domain required")
    except ContractError as error:
        raise ProbeError(str(error)) from error
    if status in ("available", "unavailable") and value["secure_enclave_available"] is not (status == "available"):
        raise ProbeError("native capability result disagrees with status")
    if "signature_verified" in extra and value["signature_verified"] is not (status in ("matched", "verified")):
        raise ProbeError("native review status and signature result disagree")
    if AUTHENTICATION <= extra:
        if (any(type(value[k]) is not bool for k in AUTHENTICATION)
                or value["signing_started"] != value["explicit_authentication_succeeded"]
                or (status == "matched" and not value["signing_started"])):
            raise ProbeError("signing requires successful explicit authentication in the current review")
    if status == "cancelled" and value["cancel_source"] not in ("review", "native"):
        raise ProbeError("unknown cancellation source")
    if status == "cancelled":
        domain, code = value["cancel_error_domain"], value["cancel_error_code"]
        if (value["cancel_trigger"] not in ("native_callback", "review_button", "window_close", "application_terminate")
                or ((domain is None) != (code is None))
                or (domain is not None and (type(domain) is not str or not 1 <= len(domain) <= 128
                                           or type(code) is not int or not -(2**31) <= code < 2**31))):
            raise ProbeError("invalid bounded cancellation diagnostics")
        native_cancel = (domain, code) in {("com.apple.LocalAuthentication", -2), ("NSOSStatusErrorDomain", -128)}
        expected = "native" if native_cancel or value["cancel_trigger"] == "native_callback" else "review"
        if value["cancel_source"] != expected:
            raise ProbeError("cancellation source disagrees with observed callback/trigger")
    if status == "matched":
        public = public_bytes(value["public_key_x963"], 65, 65)
        public_bytes(value["signature_der"], 8, 72)
        if public[0] != 4 or hashlib.sha256(public).hexdigest() != value["public_key_digest"]:
            raise ProbeError("returned public key disagrees with its identity")
    if status == "checked" and (type(value["checks"]) is not dict or set(value["checks"]) != GATE_CHECKS
                                or any(type(v) is not bool for v in value["checks"].values())):
        raise ProbeError("invalid native lifecycle checks")
    return value


def decode_result(completed, mode):
    try:
        raw = completed.stdout.encode("utf-8")
        if len(raw) > 4096:
            raise ContractError("native result exceeds its byte bound")
        value = validate(decode(raw), mode)
    except (AttributeError, UnicodeError, ContractError) as error:
        raise ProbeError("invalid bounded native JSON") from error
    failure = value["status"] in ("error", "key_rejected", "signature_without_interaction")
    if completed.returncode != (1 if failure else 0):
        raise ProbeError("native custody status and exit disagree")
    return value


def assess(created, reopened, denied, tampered, control):
    for value, mode in zip((created, reopened, denied, tampered, control), ("create", "reopen", "deny", "reopen", "reopen")):
        validate(value, mode)
    if ([v["status"] for v in (created, reopened, denied, control)] != [
            "created", "reopened", "interaction_denied", "reopened"]
            or tampered["status"] not in ("key_rejected", "reopened")):
        raise ProbeError("key reopen, interaction denial or tamper/control was not observed")
    if len({v["process_id"] for v in (created, reopened, denied, tampered, control)}) != 5:
        raise ProbeError("independent native process observations required")
    if any(value[key] != created[key] for value in (reopened, denied, control) for key in IDENTITY):
        raise ProbeError("key identity or encrypted representation changed across processes")
    if (denied["error_domain"], denied["error_code"]) not in DENIALS:
        raise ProbeError("unknown signing error is not an observed interaction denial")
    if tampered["status"] == "reopened" and tampered["representation_digest"] == created["representation_digest"]:
        raise ProbeError("tamper exercise did not present a changed representation")
    # No native reconstruction error has been established as an integrity
    # failure. Authentication denial or an unknown error cannot supply that proof.
    return {"status": "incomplete",
            "public_key_digest": created["public_key_digest"],
            "same_public_identity": True, "noninteractive_signing_denied": True,
            "tamper_integrity_verified": False, "tampered_reopen_status": tampered["status"],
            "tamper_error": {key: tampered[key] for key in ERROR} if ERROR <= set(tampered) else None,
            "valid_representation_reopens_after_tamper": True,
            "denial": {key: denied[key] for key in ERROR}, "authorization_verified": False,
            "product_custody_verified": False}


def assess_review(created, reopened, denied, reviewed, verified, after, *, nonce):
    values = (created, reopened, denied, reviewed)
    for value, mode in zip(values, ("prepare", "reopen", "deny", "review")):
        validate(value, mode)
    if ([v["status"] for v in values[:3]] != ["created", "reopened", "interaction_denied"]
            or reviewed["status"] not in ("matched", "cancelled", "expired")):
        raise ProbeError("restart review prerequisites or result are missing")
    if reviewed["status"] == "matched":
        validate(verified, "verify")
        validate(after, "deny")
        if verified["status"] != "verified" or after["status"] != "interaction_denied":
            raise ProbeError("independent signature check or post-review denial failed")
        if any(verified[key] != reviewed[key] for key in REVIEW):
            raise ProbeError("independent verification belongs to another review")
        values += (verified, after)
    elif verified is not None or after is not None:
        raise ProbeError("terminal review cannot consume a later verification")
    if len({v["process_id"] for v in values}) != len(values):
        raise ProbeError("restart review requires separate process observations")
    if any(value[key] != created[key] for value in values[1:] for key in IDENTITY):
        raise ProbeError("restart review key or representation changed")
    for value in (denied, after) if after is not None else (denied,):
        if (value["error_domain"], value["error_code"]) not in DENIALS:
            raise ProbeError("unclassified signing error is not interaction denial")
    message = review_message(reviewed["review_digest"], created["public_key_digest"],
                             created["representation_digest"], nonce)
    if hashlib.sha256(message).hexdigest() != reviewed["challenge_digest"]:
        raise ProbeError("review does not bind this challenge and key")
    result = {"status": "review_observed" if reviewed["status"] == "matched" else reviewed["status"],
              "signature_after_restart_verified": reviewed["status"] == "matched",
              "noninteractive_signing_denied_before": True,
              "noninteractive_signing_denied_after": after is not None,
              "same_public_identity": True, "public_key_digest": created["public_key_digest"],
              "review_digest": reviewed["review_digest"], "challenge_digest": reviewed["challenge_digest"],
              "authorization_verified": False, "product_custody_verified": False}
    result.update({key: reviewed[key] for key in AUTHENTICATION})
    if reviewed["status"] == "cancelled":
        result.update({key: reviewed[key] for key in CANCELLATION})
    return result


def probe(*, exercise=False, review=False):
    if type(exercise) is not bool or type(review) is not bool or (exercise and review):
        raise ProbeError("select exactly one explicit custody exercise")
    if sys.platform != "darwin":
        return {"status": "unsupported", "authorization_verified": False, "product_custody_verified": False}
    with tempfile.TemporaryDirectory(prefix="claimbranch-key-reopen-", dir=temporary_root()) as directory:
        root = Path(directory)
        binary = root / "key-reopen"
        built = subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(binary)],
                               capture_output=True, text=True, timeout=90, check=False)
        if built.returncode:
            raise ProbeError("custody helper build failed: " + built.stderr[:1600])
        def run(mode, *arguments, input=None):
            return decode_result(subprocess.run([str(binary), mode, *arguments], cwd=root, capture_output=True,
                                                input=input, text=True, timeout=105 if mode in ("prepare", "review") else 15,
                                                check=False), mode)
        result = run("check")
        if result["status"] == "available":
            if review:
                result = foreground_measurement(run)
            elif exercise:
                created = expect(run("create"), "created")
                reopened, denied = reopen_and_deny(run, created)
                result = tamper_measurement(root, run, created, reopened, denied)
        if not (exercise or review) and (root / "enclave-key.bin").exists():
            raise ProbeError("capability check unexpectedly created key material")
    return {**result, "cleanup_verified": True}


def expect(value, status):
    if value["status"] != status:
        raise ProbeError("custody measurement stopped: " + json.dumps(
            {key: value[key] for key in {"mode", "status"} | ERROR if key in value}, sort_keys=True))
    return value


def reopen_and_deny(run, created):
    reopened = expect(run("reopen"), "reopened")
    denied = expect(run("deny"), "interaction_denied")
    if (len({v["process_id"] for v in (created, reopened, denied)}) != 3
            or any(v[key] != created[key] for v in (reopened, denied) for key in IDENTITY)
            or (denied["error_domain"], denied["error_code"]) not in DENIALS):
        raise ProbeError("key continuity or noninteractive denial preflight failed")
    return reopened, denied


def foreground_measurement(run):
    created = run("prepare")
    if created["status"] in ("cancelled", "expired"):
        return {"status": created["status"], "phase": "prepare", "signature_after_restart_verified": False,
                "authorization_verified": False, "product_custody_verified": False,
                **({key: created[key] for key in CANCELLATION} if created["status"] == "cancelled" else {})}
    expect(created, "created")
    reopened, denied = reopen_and_deny(run, created)
    nonce = secrets.token_hex(32)
    arguments = (created["public_key_digest"], created["representation_digest"], nonce)
    reviewed = run("review", *arguments)
    if reviewed["status"] == "error":
        raise ProbeError("foreground review failed: " + json.dumps(
            {key: reviewed[key] for key in ERROR}, sort_keys=True))
    verified = after = None
    if reviewed["status"] == "matched":
        verified = expect(run("verify", *arguments, input=json.dumps(
            {key: reviewed[key] for key in ("public_key_x963", "signature_der")})), "verified")
        after = run("deny")
    return assess_review(created, reopened, denied, reviewed, verified, after, nonce=nonce)


def tamper_measurement(root, run, created, reopened, denied):
    fd = os.open(root / "enclave-key.bin", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or not 1 <= info.st_size <= 16_384):
            raise ProbeError("unexpected owned encrypted-key file")
        original = os.read(fd, 16_385)
        if hashlib.sha256(original).hexdigest() != created["representation_digest"]:
            raise ProbeError("saved key representation differs from the native creation result")
        changed = bytearray(original)
        changed[len(changed) // 2] ^= 1
        def write(raw):
            os.lseek(fd, 0, os.SEEK_SET)
            view = memoryview(raw)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise ProbeError("could not write owned tamper/control bytes")
                view = view[count:]
            os.ftruncate(fd, len(raw))
            os.fsync(fd)
        try:
            write(changed)
            tampered = run("reopen")
        finally:
            write(original)
        control = run("reopen")
        return assess(created, reopened, denied, tampered, control)
    finally:
        os.close(fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--exercise", action="store_true")
    group.add_argument("--review", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = probe(exercise=args.exercise, review=args.review)
    except (OSError, subprocess.TimeoutExpired, ProbeError) as error:
        result = {"status": "error", "reason": str(error), "authorization_verified": False, "product_custody_verified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in ("available", "review_observed") else 3 if result["status"] in (
        "unavailable", "unsupported", "incomplete", "cancelled", "expired") else 1


if __name__ == "__main__":
    raise SystemExit(main())
