import http.client
import json
from threading import Thread
import unittest
from unittest.mock import patch

from claimbranch.application.server import ReviewServer


class ReviewSessionTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.server = ReviewServer(clock=lambda: self.now)
        self.thread = Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.cookie = self.csrf = None
        self.revision = 0

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def request(self, path, value=None, *, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        request_headers = {"Origin": self.server.origin, "Content-Type": "application/json"}
        if self.cookie:
            request_headers["Cookie"] = self.cookie
            request_headers["X-ClaimBranch-CSRF"] = self.csrf
        request_headers.update(headers or {})
        body = raw if raw is not None else json.dumps(value).encode() if value is not None else None
        try:
            connection.request("POST" if body is not None else "GET", path, body, request_headers)
            response = connection.getresponse()
            payload = response.read()
            value = json.loads(payload) if "application/json" in response.getheader("Content-Type", "") else payload
            return response.status, dict(response.getheaders()), value
        finally:
            connection.close()

    def connect(self):
        token = self.server.bootstrap
        status, headers, body = self.request("/api/session", {"bootstrap": token})
        self.assertEqual(200, status)
        self.cookie = headers["Set-Cookie"].split(";", 1)[0]
        self.csrf = body["csrf"]
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        return token

    def command(self, name, **fields):
        status, headers, body = self.request("/api/" + name, {"revision": self.revision, **fields})
        if status == 200:
            self.revision = body["revision"]
        return status, headers, body

    def test_bootstrap_one_use_fragment_not_in_page_or_network_query(self):
        token = self.connect()
        self.assertEqual(403, self.request("/api/session", {"bootstrap": token})[0])
        self.assertEqual(403, self.request("/api/session", {"bootstrap": "한글"})[0])
        status, headers, page = self.request("/")
        self.assertEqual(200, status)
        self.assertNotIn(token.encode(), page)
        self.assertEqual("no-store", headers["Cache-Control"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual("DENY", headers["X-Frame-Options"])
        self.assertEqual(404, self.request("/?bootstrap=" + token)[0])

    def test_host_origin_csrf_and_foreign_cookie_are_denied_without_changes(self):
        self.connect()
        for headers in ({"Host": "evil.example"}, {"Origin": "http://evil.example"},
                        {"Origin": "null"}, {"Origin": ""}, {"X-ClaimBranch-CSRF": "bad"},
                        {"Cookie": "cb_demo_wrong=bad"}):
            with self.subTest(headers=headers):
                status, _, _ = self.request("/api/edit", {"revision": 0, "text": "unsafe", "rationale": "reason"}, headers=headers)
                self.assertIn(status, (401, 403))
                self.assertEqual("", self.server.workspace.text)

    def test_two_tabs_cannot_overwrite_a_newer_draft_and_reconnect_reads_current(self):
        self.connect()
        self.assertEqual(200, self.command("edit", text="판단", rationale="근거")[0])
        self.assertEqual(409, self.request("/api/edit", {"revision": 0, "text": "stale", "rationale": "stale"})[0])
        state = self.request("/api/state")[2]
        self.assertEqual("판단", state["state"]["draft"]["text"])
        self.assertEqual(1, state["revision"])
        self.assertEqual(0, state["state"]["accepted_writes"])

    def test_expired_bootstrap_and_session_are_terminal(self):
        self.now = 1120
        self.assertEqual(403, self.request("/api/session", {"bootstrap": self.server.bootstrap})[0])
        self.now = 1000
        self.connect()
        self.command("edit", text="private draft", rationale="reason")
        self.now = 1900
        self.assertEqual(401, self.request("/api/state")[0])
        self.assertIsNone(self.server.workspace)
        self.now = 1100
        self.assertEqual(401, self.request("/api/state")[0])

    def test_malformed_duplicate_oversized_and_arbitrary_commands_do_not_mutate(self):
        self.connect()
        for raw in (b'{"revision":0,"revision":0}', b'{"revision":NaN}', b'x' * 65537):
            with self.subTest(length=len(raw)):
                self.assertIn(self.request("/api/edit", raw=raw)[0], (400, 413))
        self.assertEqual(400, self.command("edit", text="x", rationale="y", path="/tmp/real")[0])
        self.assertEqual(404, self.command("import-project", path="/tmp/real")[0])
        self.assertEqual(404, self.request("/../workspace.py")[0])
        self.assertEqual("", self.server.workspace.text)

    def test_excessive_decimal_content_length_is_rejected_without_crashing_the_handler(self):
        self.connect()
        with patch.object(self.server, "handle_error") as unexpected_error:
            self.assertEqual(413, self.request("/api/edit", raw=b"{}", headers={"Content-Length": "9" * 5000})[0])
            unexpected_error.assert_not_called()
        self.assertEqual("", self.request("/api/state")[2]["state"]["draft"]["text"])

    def test_manual_flow_and_unavailable_authority_share_core_contracts(self):
        self.connect()
        self.command("edit", text="Sensitivity alone is insufficient.", rationale="The operators differ.")
        status, _, body = self.command("prepare", selected=["claim-status"], disposition="not-required", answers=[])
        self.assertEqual(200, status)
        self.assertIn("I-01", body["state"]["review"]["required"])
        self.assertEqual(["manuscript"], self.command("preview-result")[2]["state"]["result"]["candidate_debts"])
        self.assertEqual(503, self.command("accept")[0])
        self.assertEqual(0, self.server.workspace.state()["accepted_writes"])
        self.assertIsNone(self.command("not-now")[2]["state"]["review"])

    def test_rendering_uses_text_sinks_and_arbitrary_ai_text_never_enters_html(self):
        self.connect()
        attack = '<img src=x onerror="window.pwned=1"><script>alert(1)</script>'
        self.command("edit", text=attack, rationale="문자 그대로 검토")
        self.assertEqual(attack, self.request("/api/state")[2]["state"]["draft"]["text"])
        self.assertNotIn(attack.encode(), self.request("/")[2])
        script = self.request("/app.js")[2]
        for sink in (b"innerHTML", b"outerHTML", b"eval(", b"document.write", b"localStorage"):
            self.assertNotIn(sink, script)

    def test_independent_servers_use_distinct_ports_credentials_and_drafts(self):
        self.connect()
        with ReviewServer(clock=lambda: self.now) as other:
            self.assertNotEqual(self.server.server_port, other.server_port)
            self.assertNotEqual(self.server.cookie_name, other.cookie_name)
            self.assertNotEqual(self.server.csrf, other.csrf)
            self.assertNotEqual(self.server.cookie, other.cookie)
            self.assertEqual("", other.workspace.text)


if __name__ == "__main__":
    unittest.main()
