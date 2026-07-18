"""Start the uvicorn server on a background thread and know when it's ready.

The UI port is **fixed** (default 8777) on purpose: the Yoto OAuth redirect URI
is registered once against that exact address, so we must not drift to a random
port. If the port is already in use, another copy of the app is almost certainly
already running — callers should just open the browser to it and exit
(single-instance behavior).
"""
from __future__ import annotations

import socket
import threading
import time

import uvicorn

from ..config import get_config


class AlreadyRunningError(RuntimeError):
    """The fixed port is taken — another instance is (probably) already running."""


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


class ServerHandle:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start(self, *, wait: bool = True, timeout: float = 15.0) -> "ServerHandle":
        from .app import app

        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        if wait:
            self._wait_ready(timeout)
        return self

    def _wait_ready(self, timeout: float) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._server and self._server.started:
                return
            time.sleep(0.05)
        raise RuntimeError("The app's server did not start in time.")

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)


def start_server(*, wait: bool = True, port: int | None = None) -> ServerHandle:
    cfg = get_config()
    host, port = cfg.host, (port if port is not None else cfg.port)
    if _port_in_use(host, port):
        raise AlreadyRunningError(f"http://{host}:{port}")
    return ServerHandle(host, port).start(wait=wait)
