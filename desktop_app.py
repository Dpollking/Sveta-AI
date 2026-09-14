"""Desktop launcher — packaged into a single .exe with PyInstaller.

Starts the FastAPI backend in a background thread, then opens it in a
native window (pywebview) instead of a browser tab, so double-clicking
the .exe gives a plain "chat window" experience per the user's request.
The admin panel stays reachable at /admin on the same local port while
the app is running, for anyone who wants it.
"""
import socket
import threading
import time

import uvicorn
import webview

from backend.main import app

HOST = "127.0.0.1"
PORT = 8765


def _port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, PORT)) == 0


def _run_server() -> None:
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    uvicorn.Server(config).run()


def main() -> None:
    if not _port_open():
        threading.Thread(target=_run_server, daemon=True).start()
        for _ in range(150):
            if _port_open():
                break
            time.sleep(0.1)

    webview.create_window(
        "Света",
        f"http://{HOST}:{PORT}/",
        width=460,
        height=820,
        min_size=(360, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
