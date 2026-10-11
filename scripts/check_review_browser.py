"""Opt-in real Chrome smoke for the synthetic UI, using only the stdlib.

Runs an explicitly named existing browser in a temporary profile. No downloads,
native authentication, protected operations, live providers or private inputs.
This exercises Chromium keyboard/focus/reflow; it is not a VoiceOver/NVDA pass.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import tempfile
from threading import Thread
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

from claimbranch.application.server import ReviewServer


class CDP:
    def __init__(self, url):
        parsed = urlsplit(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=10)
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        self.socket.sendall((f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        self.buffer = b""
        while b"\r\n\r\n" not in self.buffer:
            self.buffer += self.socket.recv(4096)
        header, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        if not header.startswith(b"HTTP/1.1 101") or expected not in header:
            raise RuntimeError("Chrome refused the local debugging connection")
        self.sequence = 0

    def read(self, size):
        while len(self.buffer) < size:
            part = self.socket.recv(max(4096, size - len(self.buffer)))
            if not part:
                raise RuntimeError("Chrome debugging connection closed")
            self.buffer += part
        result, self.buffer = self.buffer[:size], self.buffer[size:]
        return result

    def send(self, value):
        body = json.dumps(value).encode()
        mask = secrets.token_bytes(4)
        size = len(body)
        header = bytes((0x81, 0x80 | size)) if size < 126 else bytes((0x81, 0xFE)) + struct.pack("!H", size)
        self.socket.sendall(header + mask + bytes(value ^ mask[index % 4] for index, value in enumerate(body)))

    def receive(self):
        parts = []
        while True:
            first, second = self.read(2)
            size = second & 127
            if size == 126:
                size = struct.unpack("!H", self.read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.read(8))[0]
            if second & 128 or size > 4 * 1024 * 1024 or first & 15 not in (0, 1):
                raise RuntimeError("unexpected bounded debugging frame")
            parts.append(self.read(size))
            if first & 128:
                return json.loads(b"".join(parts))

    def call(self, method, params=None):
        self.sequence += 1
        self.send({"id": self.sequence, "method": method, "params": params or {}})
        while True:
            result = self.receive()
            if result.get("id") == self.sequence:
                if "error" in result:
                    raise RuntimeError(str(result["error"]))
                return result["result"]

    def evaluate(self, expression):
        result = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in result:
            raise RuntimeError(str(result["exceptionDetails"]))
        return result.get("result", {}).get("value")

    def wait(self, expression):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.evaluate(expression):
                return
            time.sleep(0.03)
        raise AssertionError("browser condition timed out: " + expression + "\n" + str(self.evaluate("document.body.innerText")))

    def click(self, element):
        self.wait(f"!document.getElementById({json.dumps(element)}).disabled")
        self.evaluate(f"document.getElementById({json.dumps(element)}).click()")
        self.wait("!busy")
        self.wait("document.getElementById('error').hidden")

    def draft(self, text, rationale):
        self.evaluate(f"document.getElementById('draft').value = {json.dumps(text)}; document.getElementById('draft').dispatchEvent(new Event('input')); document.getElementById('rationale').value = {json.dumps(rationale)}; document.getElementById('rationale').dispatchEvent(new Event('input'))")


def exercise(cdp, server, width, screenshot_dir):
    cdp.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
    cdp.call("Emulation.setFocusEmulationEnabled", {"enabled": True})
    cdp.call("Page.bringToFront")
    cdp.call("Page.navigate", {"url": server.launch_url})
    cdp.wait(f"location.port === '{server.server_port}' && document.getElementById('workspace') && !document.getElementById('workspace').hidden")
    assert cdp.evaluate("document.getElementById('draft').value === '' && location.hash === ''")
    assert cdp.evaluate("document.documentElement.scrollWidth <= innerWidth"), "horizontal overflow"
    assert cdp.evaluate("[...document.querySelectorAll('button')].every(b => b.hidden || b.getBoundingClientRect().height === 0 || b.getBoundingClientRect().height >= 44)")
    # Actual keyboard activation, then input/review path.
    cdp.evaluate("document.getElementById('save').focus()")
    assert cdp.evaluate("document.activeElement.id === 'save'"), "save button did not receive focus"
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": "\r", "unmodifiedText": "\r"})
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
    cdp.wait("document.getElementById('status').textContent.includes('유지했습니다')")
    text = "민감도만으로 손상 순서를 설명하기 어렵다."
    reason = "가지치기와 양자화는 예상과 다르고, 압축은 해당 조건에서만 부합한다. 메커니즘은 아직 확인하지 않았다."
    cdp.draft(text, reason)
    cdp.click("prepare")
    cdp.wait("document.activeElement.id === 'review'")
    assert cdp.evaluate("document.getElementById('review-rationale').textContent.includes('메커니즘')")
    cdp.click("preview-result")
    assert cdp.evaluate("document.getElementById('candidate-debts').children.length === 1")
    cdp.click("not-now")
    assert cdp.evaluate("document.getElementById('review').hidden && document.getElementById('draft').value.length > 0")
    cdp.wait("document.activeElement.id === 'draft'")
    # Selecting only the experiment cannot copy the omitted interpretation into
    # manuscript wording. Re-selecting the claim restores the connected preview.
    cdp.evaluate("document.getElementById('select-claim').click(); document.getElementById('select-experiment').click()")
    cdp.click("prepare")
    assert cdp.evaluate("document.getElementById('before').textContent === document.getElementById('after').textContent")
    assert cdp.evaluate("document.getElementById('manuscript-note').textContent.includes('문장 후보를 만들지 않았습니다')")
    cdp.click("preview-result")
    assert cdp.evaluate("document.getElementById('candidate-debts').textContent.includes('원고 영향 검토')")
    assert not server.workspace.state()["result"]["has_manuscript_candidate"]
    cdp.click("not-now")
    cdp.evaluate("document.getElementById('select-claim').click(); document.getElementById('select-experiment').click()")
    cdp.click("request-preview")
    cdp.click("request-cancel")
    assert len(server.workspace.broker.sent) == 0
    # An unfinished human reading must remain accessible after AI adoption.
    unfinished = "아직 이유를 작성하지 않은 나의 해석. " * 40
    cdp.draft(unfinished, "")
    cdp.click("request-preview")
    cdp.click("request-send")
    cdp.click("proposal-use")
    cdp.wait("document.activeElement.id === 'draft'")
    assert server.workspace.state()["before_proposal"] == {"text": unfinished, "rationale": ""}
    assert cdp.evaluate("!document.getElementById('before-proposal').hidden")
    cdp.evaluate("document.querySelector('#before-proposal summary').focus()")
    cdp.wait("document.activeElement === document.querySelector('#before-proposal summary')")
    cdp.call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13, "text": "\r", "unmodifiedText": "\r"})
    cdp.call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
    cdp.wait("document.getElementById('before-proposal').open")
    assert cdp.evaluate("document.getElementById('before-proposal-text').textContent") == unfinished
    assert cdp.evaluate("document.documentElement.scrollWidth <= innerWidth"), "draft recovery overflows the viewport"
    cdp.draft(text + " 추가 확인 필요.", reason)
    cdp.evaluate("document.querySelector('input[value=deferred]').click()")
    cdp.click("prepare")
    cdp.click("preview-result")
    assert cdp.evaluate("document.getElementById('candidate-debts').children.length === 2")
    assert cdp.evaluate("document.getElementById('contributions').textContent.includes('AI 원문')")
    assert server.workspace.state()["accepted_writes"] == 0
    # Same-session browser reload recovers the server draft and reviewed scope.
    cdp.call("Page.reload")
    cdp.wait("performance.getEntriesByType('navigation')[0].type === 'reload' && document.getElementById('workspace') && !document.getElementById('workspace').hidden && document.getElementById('draft').value.length > 0")
    assert cdp.evaluate("document.querySelector('input[value=deferred]').checked")
    assert cdp.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if screenshot_dir:
        cdp.evaluate("window.scrollTo(0,0)")
        screenshot = cdp.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        (screenshot_dir / f"review-{width}.png").write_bytes(base64.b64decode(screenshot["data"]))
    # Malicious provider text is displayed literally in the actual browser.
    cdp.click("not-now")
    server.workspace.frozen["normalized_text"] = '<img src=x onerror="window.pwned=1"><script>window.pwned=1</script>'
    cdp.click("request-preview")
    cdp.click("request-send")
    assert cdp.evaluate("document.querySelectorAll('#proposal-text img, #proposal-text script').length === 0 && !window.pwned")
    print(json.dumps({"viewport": width, "manual": "pass", "selected_wording": "pass", "recorded_ai": "pass", "same_session_reload": "pass",
                      "literal_provider_text": "pass", "keyboard_focus_reflow": "pass", "authorization_verified": False}), flush=True)


def exercise_graph(cdp, server, width, screenshot_dir):
    cdp.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": 1100, "deviceScaleFactor": 1, "mobile": False})
    cdp.call("Page.navigate", {"url": server.launch_url})
    cdp.wait(f"location.port === '{server.server_port}' && document.querySelectorAll('.graph-node').length === 8 && !document.getElementById('graph-panel').hidden")
    assert cdp.evaluate("document.documentElement.scrollWidth <= innerWidth")
    cdp.evaluate("document.querySelector('[data-node-id=\"optional-experiment\"]').click()")
    assert cdp.evaluate("document.getElementById('graph-detail-status').textContent.includes('미실행')")
    assert cdp.evaluate("document.querySelector('[data-node-id=\"optional-experiment\"]').getAttribute('aria-pressed') === 'true'")
    assert cdp.evaluate("document.getElementById('graph-detail-links').textContent.includes('검증할 계획')")
    # Keyboard activation follows an actual graph relationship back to the claim.
    cdp.evaluate("document.querySelector('#graph-detail-links button').focus()")
    cdp.call("Input.dispatchKeyEvent", {"type":"keyDown", "key":"Enter", "code":"Enter", "windowsVirtualKeyCode":13, "text":"\r"})
    cdp.call("Input.dispatchKeyEvent", {"type":"keyUp", "key":"Enter", "code":"Enter", "windowsVirtualKeyCode":13})
    cdp.wait("document.querySelector('[data-node-id=\"C-01\"]').getAttribute('aria-pressed') === 'true'")
    if width > 720:
        cdp.wait("document.querySelectorAll('#graph-wires > g').length === 12")
    if screenshot_dir:
        cdp.evaluate("document.getElementById('graph-panel').scrollIntoView({block:'start'})")
        cdp.evaluate("document.fonts.ready.then(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))")
        clip = cdp.evaluate("(() => {const r=document.getElementById('graph-panel').getBoundingClientRect(); return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1};})()")
        shot = cdp.call("Page.captureScreenshot", {"format":"png", "captureBeyondViewport":True, "clip":clip})
        (screenshot_dir / f"argument-graph-{width}.png").write_bytes(base64.b64decode(shot["data"]))
        if width > 720:
            cdp.evaluate("document.activeElement.blur(); document.querySelector('[data-node-id=\"optional-experiment\"]').click()")
            clip = cdp.evaluate("(() => {const r=document.getElementById('graph-panel').getBoundingClientRect(); return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1};})()")
            shot = cdp.call("Page.captureScreenshot", {"format":"png", "captureBeyondViewport":True, "clip":clip})
            (screenshot_dir / "argument-experiment.png").write_bytes(base64.b64decode(shot["data"]))
    # Edits and scope changes invalidate the current drawing, then regenerate it.
    cdp.draft("A revised interpretation <script>window.pwned=1</script>", "Recheck the three observations.")
    assert cdp.evaluate("document.getElementById('graph-content').hidden")
    cdp.click("prepare")
    assert cdp.evaluate("document.getElementById('graph-nodes').textContent.includes('<script>') && !window.pwned")
    cdp.evaluate("document.getElementById('select-experiment').click()")
    assert cdp.evaluate("document.getElementById('graph-content').hidden")
    cdp.click("prepare")
    assert cdp.evaluate("document.querySelector('[data-node-id=\"optional-experiment\"]').classList.contains('scope-omitted')")
    assert not next(edge for edge in server.workspace.state()["review"]["graph"]["edges"] if edge["kind"] == "tests")["included"]
    assert server.workspace.state()["accepted_writes"] == 0
    print(json.dumps({"viewport":width, "graph":"pass", "nodes":8, "relations":12,
                      "keyboard_inspector":"pass", "omissions_and_stale_graph":"pass", "authorization_verified":False}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chrome", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path, help="Existing output directory for synthetic review and graph PNGs")
    args = parser.parse_args()
    if not args.chrome.is_file() or (args.screenshots and not args.screenshots.is_dir()):
        parser.error("existing browser executable and screenshot directory required")
    with tempfile.TemporaryDirectory(prefix="claimbranch-browser-") as temporary:
        profile = Path(temporary)
        with open(profile / "chrome.log", "wb") as log:
            chrome = subprocess.Popen([str(args.chrome), "--headless=new", "--no-first-run", "--no-default-browser-check",
                      "--disable-background-networking", "--disable-component-update", "--disable-sync", "--no-proxy-server",
                      "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1", f"--user-data-dir={profile}", "about:blank"], stdout=log, stderr=log)
            cdp = None
            try:
                deadline = time.monotonic() + 15
                while not (profile / "DevToolsActivePort").exists():
                    if chrome.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("existing Chrome did not start its local debug endpoint")
                    time.sleep(0.05)
                port = int((profile / "DevToolsActivePort").read_text().splitlines()[0])
                with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                    pages = json.load(response)
                cdp = CDP(next(page["webSocketDebuggerUrl"] for page in pages if page["type"] == "page"))
                cdp.call("Page.enable")
                for width in (1440, 390):
                    for example in (False, True):
                        with ReviewServer(example=example) as server:
                            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
                            thread.start()
                            try:
                                (exercise_graph if example else exercise)(cdp, server, width, args.screenshots)
                            finally:
                                server.shutdown()
                                thread.join(timeout=3)
            finally:
                if cdp:
                    cdp.socket.close()
                chrome.terminate()
                try:
                    chrome.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    chrome.kill()
                    chrome.wait(timeout=5)


if __name__ == "__main__":
    main()
