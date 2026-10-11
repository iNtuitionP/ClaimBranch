"""Bounded HTTP loopback surface for synthetic data only, never an authority UI.

Plain HTTP cookies do not provide the production Secure-cookie/OS boundary.
Host/Origin/CSRF/bootstrap checks are defense in depth for this local prototype.
"""
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from threading import BoundedSemaphore, RLock
import time

from claimbranch.core.canonical import ContractError, decode
from .workspace import DemoWorkspace, Unavailable


ASSETS = Path(__file__).with_name("web")
ROUTES = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/graph.js": ("graph.js", "text/javascript; charset=utf-8"),
          "/app.css": ("app.css", "text/css; charset=utf-8")}
COMMANDS = {"edit": ("text", "rationale"), "load-example": (), "preview-request": (), "request-proposal": ("request_id",),
            "cancel-request": (), "use-proposal": (), "prepare": ("selected", "disposition", "answers"),
            "preview-result": (), "not-now": (), "accept": (), "erase-trace": ("request_id",)}


def same_secret(candidate, expected):
    return isinstance(candidate, str) and candidate.isascii() and secrets.compare_digest(candidate, expected)


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, *, clock=None, example=False):
        self.clock = clock or (lambda: int(time.time()))
        self.lock = RLock()
        self.slots = BoundedSemaphore(8)
        self.workspace = DemoWorkspace(clock=self.clock, example=example)
        self.bootstrap = secrets.token_urlsafe(32)
        self.cookie = secrets.token_urlsafe(32)
        self.csrf = secrets.token_urlsafe(32)
        self.started = self.clock()
        self.session_started = None
        self.generation = 0
        self.assets = {route: (ASSETS.joinpath(name).read_bytes(), content_type)
                       for route, (name, content_type) in ROUTES.items()}
        super().__init__(("127.0.0.1", 0), ReviewHandler)
        self.host = f"127.0.0.1:{self.server_port}"
        self.origin = f"http://{self.host}"
        self.cookie_name = f"cb_demo_{self.server_port}"

    @property
    def launch_url(self):
        return self.origin + "/#bootstrap=" + self.bootstrap

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def current(self):
        return {"state": self.workspace.state(), "revision": self.generation, "csrf": self.csrf,
                "expires_at": self.session_started + 900}


class ReviewHandler(BaseHTTPRequestHandler):
    server_version = "ClaimBranchDemo"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        pass  # Never log fragment credentials, drafts, request bodies or cookies.

    def _send(self, status, value, *, content_type="application/json; charset=utf-8", cookie=None):
        raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(raw)

    def _host_ok(self):
        return self.headers.get_all("Host", []) == [self.server.host]

    def _authenticated(self):
        server = self.server
        if server.session_started is None or server.workspace is None:
            return False
        if not server.session_started <= server.clock() < server.session_started + 900:
            server.workspace = None  # Expired sessions cannot expose the volatile draft.
            return False
        try:
            values = self.headers.get_all("Cookie", [])
            if len(values) != 1:
                return False
            cookie = SimpleCookie(values[0])
            value = cookie.get(server.cookie_name)
            return value is not None and same_secret(value.value, server.cookie)
        except (CookieError, TypeError):
            return False

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "invalid host"})
        if self.path in self.server.assets:
            raw, content_type = self.server.assets[self.path]
            return self._send(200, raw, content_type=content_type)
        with self.server.lock:
            if self.path == "/api/state":
                if not self._authenticated():
                    return self._send(401, {"error": "session unavailable; restart the synthetic demo"})
                return self._send(200, self.server.current())
        self._send(404, {"error": "unknown route"})

    def do_POST(self):
        if not self._host_ok() or self.headers.get_all("Origin", []) != [self.server.origin]:
            return self._send(403, {"error": "invalid origin or host"})
        if self.headers.get("Transfer-Encoding") or self.headers.get_all("Content-Type", []) != ["application/json"]:
            return self._send(415, {"error": "bounded JSON required"})
        lengths = self.headers.get_all("Content-Length", [])
        if (len(lengths) != 1 or not 1 <= len(lengths[0]) <= 5 or not lengths[0].isascii()
                or not lengths[0].isdecimal() or not 0 < int(lengths[0]) <= 65536):
            return self._send(413, {"error": "invalid body length"})
        try:
            raw = self.rfile.read(int(lengths[0]))
            value = decode(raw)
            if len(raw) != int(lengths[0]) or type(value) is not dict:
                raise ContractError("JSON object required")
        except (ContractError, OSError):
            return self._send(400, {"error": "invalid bounded JSON"})
        with self.server.lock:
            server = self.server
            if self.path == "/api/session":
                token = value.get("bootstrap")
                if (set(value) != {"bootstrap"} or type(token) is not str or not server.bootstrap
                        or not server.started <= server.clock() < server.started + 120
                        or not same_secret(token, server.bootstrap)):
                    return self._send(403, {"error": "bootstrap invalid or already used; restart the demo"})
                server.bootstrap = ""
                server.session_started = server.clock()
                cookie = f"{server.cookie_name}={server.cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age=900"
                return self._send(200, server.current(), cookie=cookie)
            if not self._authenticated():
                return self._send(401, {"error": "session unavailable; restart the synthetic demo"})
            csrf = self.headers.get_all("X-ClaimBranch-CSRF", [])
            if len(csrf) != 1 or not same_secret(csrf[0], server.csrf):
                return self._send(403, {"error": "invalid CSRF token"})
            action = self.path.removeprefix("/api/")
            if self.path != "/api/" + action or action not in COMMANDS:
                return self._send(404, {"error": "unknown command"})
            if set(value) != {*COMMANDS[action], "revision"} or type(value["revision"]) is not int:
                return self._send(400, {"error": "unknown or missing command fields"})
            if value["revision"] != server.generation:
                return self._send(409, {"error": "another tab changed this session; reload before reviewing"})
            try:
                getattr(server.workspace, action.replace("-", "_"))(*(value[key] for key in COMMANDS[action]))
            except Unavailable:
                return self._send(503, {"error": "실제 승인은 아직 준비되지 않았습니다. 합성 결과 미리보기만 가능합니다."})
            except ContractError as error:
                return self._send(422, {"error": str(error)})
            server.generation += 1
            return self._send(200, server.current())
