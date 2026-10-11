"""Validate and execute a trusted-source alpha ZIP. This is not a sandbox."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile

from scripts.build_source import MAX_SOURCE_MEMBERS

LOOPBACK_SMOKE = r'''
import http.client
import json
from pathlib import Path
from threading import Thread
import claimbranch
from claimbranch.application.server import ReviewServer

assert Path(claimbranch.__file__).resolve().is_relative_to(Path.cwd())
with ReviewServer(example=True) as server:
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    def request(path, value=None, extra=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        headers = {"Origin": server.origin, "Content-Type": "application/json"}
        headers.update(extra or {})
        try:
            connection.request("GET" if value is None else "POST", path,
                               None if value is None else json.dumps(value), headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()
    try:
        for route in ("/", "/app.js", "/graph.js", "/app.css"):
            status, headers, raw = request(route)
            assert status == 200 and raw, route
            assert headers["Cache-Control"] == "no-store"
        status, headers, raw = request("/api/session", {"bootstrap": server.bootstrap})
        assert status == 200
        state = json.loads(raw)
        assert state["state"]["accepted_writes"] == 0
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, _, _ = request("/api/accept", {"revision": state["revision"]},
                               {"Cookie": cookie, "X-ClaimBranch-CSRF": state["csrf"]})
        assert status == 503
        assert server.workspace.state()["accepted_writes"] == 0
    finally:
        server.shutdown()
        thread.join(timeout=2)
        assert not thread.is_alive()
print("loopback-ok")
'''


def _unpack(artifact, destination):
    with zipfile.ZipFile(artifact) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(infos) > MAX_SOURCE_MEMBERS or sum(info.file_size for info in infos) > 5 * 1024 * 1024:
            raise ValueError("source-preview archive exceeds its budget")
        if len(names) != len(set(names)) or "artifact.json" not in names:
            raise ValueError("invalid source-preview inventory")
        for info in infos:
            path = PurePosixPath(info.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in info.filename or ":" in info.filename
                    or path.as_posix() != info.filename or info.is_dir()
                    or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG)):
                raise ValueError("invalid source-preview member")
        manifest = json.loads(archive.read("artifact.json"))
        if (type(manifest) is not dict or set(manifest) != {"schema_version", "kind", "python", "authorization_verified", "files"}
                or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
                or manifest["kind"] != "personal-terminal-alpha" or manifest["python"] != "3.13"
                or manifest["authorization_verified"] is not False or type(manifest["files"]) is not dict
                or set(manifest["files"]) != set(names) - {"artifact.json"}):
            raise ValueError("invalid source-preview manifest")
        contents = {name: archive.read(name) for name in names}
        for name, expected in manifest["files"].items():
            if hashlib.sha256(contents[name]).hexdigest() != expected:
                raise ValueError("source-preview hash mismatch")
        for name, raw in contents.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)


def check_source_artifact(artifact, *, temp_root=None):
    if sys.version_info[:2] != (3, 13):
        raise ValueError("artifact smoke requires the declared Python 3.13 runtime")
    with tempfile.TemporaryDirectory(prefix="claimbranch-배포 검사-", dir=temp_root) as directory:
        destination = Path(directory).resolve()
        _unpack(artifact, destination)
        if (destination / "tests").exists() or (destination / "scripts").exists():
            raise ValueError("runtime artifact must not need repository tests/scripts")
        checks = []
        for name, arguments, expected in (
                ("doctor", ["-m", "claimbranch", "doctor", "--json"], 0),
                ("saturation", ["-m", "claimbranch", "demo", "saturation", "--json"], 0),
                ("paper", ["-m", "claimbranch", "demo", "paper", "--variant", "recorded", "--scenario", "challenges", "--json"], 0),
                ("paper-draft", ["-m", "claimbranch", "demo", "paper", "--workflow", "--variant", "recorded", "--json"], 0),
                ("paper-episodes", ["-m", "claimbranch", "demo", "paper", "--episodes", "--variant", "recorded", "--json"], 0),
                ("paper-provider", ["-m", "claimbranch", "demo", "paper", "--provider", "--variant", "recorded", "--json"], 0),
                ("tui", ["-m", "claimbranch", "demo", "tui", "--layout", "three", "--snapshot"], 0),
                ("loopback", ["-c", LOOPBACK_SMOKE], 0)):
            result = subprocess.run([sys.executable, "-E", "-s", "-B", *arguments], cwd=destination,
                                    capture_output=True, text=True, encoding="utf-8", timeout=30, shell=False)
            if result.returncode != expected:
                raise ValueError(name + " artifact smoke failed: " + (result.stderr or result.stdout)[-2000:])
            if name == "doctor":
                value = json.loads(result.stdout)
                if (value["paper_replay"] != "ready" or value["authorization_verified"] is not False
                        or value["personal_workspace"] != "ready" or value["storage"]["encrypted"] is not False):
                    raise ValueError("artifact doctor readiness mismatch")
            elif name == "saturation":
                if not all(item["golden_match"] and item["authorization_verified"] is False for item in json.loads(result.stdout)):
                    raise ValueError("artifact replay mismatch")
            elif name == "paper":
                value = json.loads(result.stdout)
                if value["authorization_verified"] is not False or value["potentially_affected_claim_ids"] != ["claim-pruning", "claim-pruning-detail", "thesis"]:
                    raise ValueError("artifact paper impact mismatch")
            elif name == "paper-draft":
                value = json.loads(result.stdout)
                if (value["authorization_verified"] is not False or not value["source_unchanged"]
                        or not value["initial_draft_blank"] or value["context"]["schema_version"] != 2
                        or value["state"]["accepted_writes"] != 0 or not value["state"]["draft"]["ai_influenced"]
                        or [item["contributor"] for item in value["review"]["judgment"]["history"]] != ["ai", "human"]):
                    raise ValueError("artifact paper draft/provenance mismatch")
                preview, review = value["changes_preview"]["preview"], value["changes_review"]
                if (preview["selection"]["selected"] != ["edge-pruning", "interpretation"]
                        or preview["selection"]["required"] != ["claim-pruning-detail"]
                        or preview["selection"]["omitted"] != ["replication"]
                        or review["preview_digest"] != value["changes_preview"]["digest"]
                        or review["disposition"] != "deferred" or review["acceptance_available"] is not False
                        or review["authorization_verified"] is not False
                        or preview["impact"]["unchanged_evidence_ids"] != ["obs-1", "obs-2"]):
                    raise ValueError("artifact selected scientific review mismatch")
            elif name == "paper-episodes":
                value = json.loads(result.stdout)
                followup = value["followup"]
                if (not all(followup[key] for key in ("replayed_work_matches", "wording_started_blank", "postimage_matches_review", "work_unchanged", "wording_retained", "review_cleared"))
                        or len(followup["pending_work"]["items"]) != 4
                        or followup["pending_work"]["history_digest"] != followup["preview"]["history_digest"]
                        or followup["current"]["history_digest"] != followup["preview"]["history_digest"]
                        or followup["preview"]["source_verified"] is not False
                        or followup["review"]["disposition"] != "deferred"
                        or followup["review"]["write_available"] is not False
                        or followup["authorization_verified"] is not False or followup["accepted_writes"] != 0):
                    raise ValueError("artifact conditional work/manuscript review mismatch")
                now = {node["id"]: node for node in value["current"]["nodes"]}
                then = {node["id"]: node for node in value["at_first_close"]["nodes"]}
                if (value["authorization_verified"] is not False or value["accepted_writes"] != 0
                        or not value["golden_match"] or not value["earlier_draft_retained"] or not value["new_draft_blank"]
                        or not value["reviewed_candidate_matches_example"] or not value["merge_review_cleared"]
                        or not value["branch_draft_started_blank"] or not value["branch_source_unchanged"] or not value["branch_draft_retained"]
                        or [cmd["operation_type"] for cmd in value["branch_preview"]["commands"]] != ["create-reasoning-branch", "record-interpretation"]
                        or value["branch_preview"]["acceptance_available"] is not False
                        or value["merge_preview"]["preview"]["selection"]["required"] != ["edge-pruning", "interpretation-two"]
                        or value["merge_review"]["sealed_review"]["disposition"] != "deferred"
                        or len(value["merge_review"]["sealed_review"]["source_judgments"]) != 2
                        or value["merge_review"]["acceptance_available"] is not False
                        or len(value["timeline"]["episodes"]) != 2 or len(value["current"]["judgments"]) != 2
                        or now["obs-1"]["content"]["value"] != "1.2" or then["obs-1"]["content"]["value"] != "0.4"
                        or not any(item["contributor"] == "ai" for item in value["current"]["judgments"][0]["history"])):
                    raise ValueError("artifact cumulative paper history mismatch")
            elif name == "paper-provider":
                value = json.loads(result.stdout)
                cases = value["cases"]
                if (value["authorization_verified"] is not False or not value["source_unchanged"]
                        or value["independent_runs"] is not True
                        or [case["name"] for case in cases] != ["adopted", "cancelled", "edited", "expired", "refused"]
                        or [case["arrival"]["attempt"]["state"] for case in cases] != ["proposed", "cancelled", "stale", "expired", "failed"]):
                    raise ValueError("artifact provider arrival mismatch")
                for case in cases:
                    state = case["state"]
                    authors = [item["contributor"] for item in case["review"]["judgment"]["history"]]
                    records = case["outbound"]["request"]["context"]["records"]
                    questions = [item["fields"] for item in records if item["kind"] == "draft"]
                    if (state["authorization_verified"] is not False or state["accepted_writes"] != 0
                            or not case["manual_review_available"] or not case["trace_identity_retained"]
                            or authors != (["ai", "human"] if case["name"] == "adopted" else ["human"])
                            or state["traces"][0]["payload_availability"] != "erased"
                            or state["traces"][0]["disposition"] != ("refused" if case["name"] == "refused" else "proposed")
                            or len(questions) != 1 or questions[0]["statement"] != case["question"]
                            or "interpretation" not in [item["id"] for item in records]
                            or len(state["attempts"]) != 1
                            or (case["name"] != "adopted" and case["arrival"]["proposal"] is not None)):
                        raise ValueError("artifact provider continuation/provenance mismatch")
            elif name == "tui":
                if "ClaimBranch" not in result.stdout or "SYNTHETIC" not in result.stdout or "\x1b" in result.stdout:
                    raise ValueError("artifact terminal snapshot mismatch")
            elif result.stdout.strip() != "loopback-ok":
                raise ValueError("artifact loopback did not finish")
            checks.append(name)
        code=Path(__file__).with_name("personal_alpha_smoke.py").read_text()
        result=subprocess.run([sys.executable,"-E","-s","-B","-c",code],cwd=destination,
                              capture_output=True,text=True,encoding="utf-8",timeout=90,shell=False)
        if result.returncode or json.loads(result.stdout)!=["personal-pty","personal-rescue"]:
            raise ValueError("artifact personal journey failed: "+(result.stderr or result.stdout)[-2000:])
        checks.extend(["personal-pty","personal-rescue"])
    return {"kind": "personal-terminal-alpha", "checks": checks, "authorization_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(check_source_artifact(args.artifact), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
