import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from cam_proxy_pi_display.collector import Snapshot, fetch_health, problem_set
from tests.fixtures import load_fixture


class _Handler(BaseHTTPRequestHandler):
    status = 200
    body = b"{}"
    delay = 0.0

    def do_GET(self):  # noqa: N802
        import time

        time.sleep(self.delay)
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    handler = type("H", (_Handler,), {})
    srv = HTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv, handler, f"http://127.0.0.1:{srv.server_port}/api/local/health"
    srv.shutdown()
    srv.server_close()


def test_fetch_ok(server):
    _, h, url = server
    h.body = json.dumps(load_fixture("pi-ok")).encode()
    health, err = fetch_health(url, 5)
    assert err is None
    assert health["schema"] == 1
    assert health["items"][0]["id"] == "camera"


def test_fetch_http_error(server):
    _, h, url = server
    h.status = 404
    h.body = b'{"error":"not_found"}'
    health, err = fetch_health(url, 5)
    assert health is None
    assert err == "HTTP 404"


def test_fetch_bad_json(server):
    _, h, url = server
    h.body = b"<html>"
    health, err = fetch_health(url, 5)
    assert health is None
    assert err == "bad answer"


def test_fetch_wrong_schema(server):
    _, h, url = server
    h.body = json.dumps({"schema": 2, "items": []}).encode()
    health, err = fetch_health(url, 5)
    assert health is None
    assert err == "API schema 2 not supported"


def test_fetch_timeout(server):
    _, h, url = server
    h.delay = 1.0
    health, err = fetch_health(url, 0.2)
    assert health is None
    assert err == "timeout"


def test_fetch_refused():
    health, err = fetch_health("http://127.0.0.1:9/api/local/health", 1)
    assert health is None
    assert err == "connection refused"


def test_problem_set_from_items():
    ok = Snapshot(health=load_fixture("pi-ok"), error=None, fetched_at=0, local={})
    assert problem_set(ok) == frozenset()
    bad = Snapshot(health=load_fixture("pi-problems"), error=None, fetched_at=0, local={})
    assert problem_set(bad) == frozenset({"camera", "stream", "events", "disk", "cpuTemp"})


def test_problem_set_unreachable():
    s = Snapshot(health=None, error="timeout", fetched_at=0, local={})
    assert problem_set(s) == frozenset({"proxy-unreachable"})
