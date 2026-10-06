"""Shared helpers for testing the scripts under tools/.

The tools are standalone scripts with hyphenated names, so they cannot be
imported by name.  load_script() loads one from its path instead.  The fake
servers below stand in for an OpenAI-compatible model server and for a file
server, so no test needs a GPU, a model, or the network.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterator

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
MODEL_EVAL = TOOLS / "model-eval"


def load_script(path: Path, name: str) -> ModuleType:
    """Import a script by file path.  Its `if __name__ == "__main__"` block does not run."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def run_eval() -> ModuleType:
    return load_script(MODEL_EVAL / "run-eval.py", "run_eval")


@pytest.fixture(scope="session")
def gguf_arch() -> ModuleType:
    return load_script(TOOLS / "gguf-arch.py", "gguf_arch")


@pytest.fixture(autouse=True)
def no_proxies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep requests to the local fake servers away from any configured proxy."""
    for var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")


def all_tasks() -> list[dict[str, Any]]:
    """Every task in every tier file that exists, with the tier filled in."""
    tasks: list[dict[str, Any]] = []
    for path in sorted(MODEL_EVAL.glob("tasks*.json")):
        with open(path) as f:
            for t in json.load(f)["tasks"]:
                t.setdefault("tier", "core")
                tasks.append(t)
    return tasks


def task_by_prompt() -> dict[str, str]:
    return {t["prompt"]: t["id"] for t in all_tasks()}


# ------------------------------------------------------------- fake model server
def completion(content: str, finish: str = "stop", reasoning: str = "") -> tuple[int, Any]:
    """A chat-completions body in the shape llama-server returns."""
    message = {"role": "assistant", "content": content, "reasoning_content": reasoning}
    body = {
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "timings": {"predicted_per_second": 50.0},
    }
    return 200, body


class FakeModelServer:
    """An OpenAI-compatible server that answers from a script.

    `reply(model, task_id)` returns (status, body).  The default answers "ok".
    Every request is recorded as (model, task_id).
    """

    def __init__(self, served: list[str]) -> None:
        self.served = served
        self.reply: Callable[[str, str], tuple[int, Any]] = lambda model, task_id: completion("ok")
        self.requests: list[tuple[str, str]] = []
        self.prompts = task_by_prompt()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _send(self, status: int, body: Any) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                if self.path.endswith("/models"):
                    self._send(200, {"object": "list", "data": [{"id": m} for m in fake.served]})
                else:
                    self._send(404, {"error": {"message": "not found"}})

            def do_POST(self) -> None:
                length = int(self.headers["Content-Length"])
                req = json.loads(self.rfile.read(length))
                if not self.path.endswith("/chat/completions"):
                    self._send(404, {"error": {"message": "not found"}})
                    return
                if req["model"] not in fake.served:
                    self._send(404, {"error": {"message": "model not found"}})
                    return
                task_id = fake.prompts.get(req["messages"][-1]["content"], "?")
                fake.requests.append((req["model"], task_id))
                status, body = fake.reply(req["model"], task_id)
                self._send(status, body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.endpoint = self.base + "/v1/chat/completions"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def count(self, task_id: str) -> int:
        return sum(1 for _, t in self.requests if t == task_id)

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def model_server() -> Iterator[FakeModelServer]:
    server = FakeModelServer(served=["model-a", "model-b"])
    yield server
    server.close()


# -------------------------------------------------------------- fake file server
class FakeFileServer:
    """Serves one file, with the behaviours resume-dl.py has to cope with.

    head_length:   whether HEAD reports Content-Length
    honour_range:  whether GET answers a Range request with 206
    get_statuses:  error statuses to return for the next GETs, before serving
    """

    def __init__(self, content: bytes) -> None:
        self.content = content
        self.head_length = True
        self.honour_range = True
        self.head_status = 200
        self.get_statuses: list[int] = []
        self.gets = 0
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def do_HEAD(self) -> None:
                self.send_response(fake.head_status)
                if fake.head_length and fake.head_status == 200:
                    self.send_header("Content-Length", str(len(fake.content)))
                self.end_headers()

            def do_GET(self) -> None:
                fake.gets += 1
                if fake.get_statuses:
                    status = fake.get_statuses.pop(0)
                    self.send_response(status)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                rng = self.headers.get("Range")
                if rng and fake.honour_range:
                    start = int(rng.split("=")[1].split("-")[0])
                    body = fake.content[start:]
                    self.send_response(206)
                    self.send_header(
                        "Content-Range",
                        f"bytes {start}-{len(fake.content) - 1}/{len(fake.content)}",
                    )
                else:
                    body = fake.content
                    self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/model.gguf"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def file_server() -> Iterator[FakeFileServer]:
    server = FakeFileServer(b"GGUF" + bytes(range(256)) * 64)
    yield server
    server.close()
