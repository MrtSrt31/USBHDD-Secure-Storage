"""
USBHDD Secure Storage – Launcher
Starts the Flask/Gunicorn server and opens the browser automatically.
Works both as a plain Python script and as a PyInstaller frozen executable.
"""
import os
import sys
import socket
import threading
import time
import webbrowser

# ── Path fix for PyInstaller onefile mode ────────────────────────────────────
# sys._MEIPASS is the temp extraction dir; the user-writable dir is next to
# the executable. backend.py already handles this via get_app_path().
if getattr(sys, "frozen", False):
    # Make sure imports find bundled packages
    sys.path.insert(0, sys._MEIPASS)


def find_free_port(start: int = 8143) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def wait_and_open_browser(url: str, delay: float = 1.5) -> None:
    """Open the default browser after the server has had time to start."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def run_with_gunicorn(port: int) -> None:
    """Run via Gunicorn (production, preferred)."""
    import backend  # noqa: imported for side-effects (init_db etc.)
    from gunicorn.app.base import BaseApplication

    cert = backend.CERT_FILE
    key  = backend.KEY_FILE

    class App(BaseApplication):
        def __init__(self, application, options=None):
            self.options     = options or {}
            self.application = application
            super().__init__()

        def load_config(self):
            for k, v in self.options.items():
                self.cfg.set(k.lower(), v)

        def load(self):
            return self.application

    options = {
        "bind":             f"0.0.0.0:{port}",
        "workers":          1,       # Must stay 1: SQLite + daemon thread
        "threads":          4,       # Handle 4 concurrent requests
        "worker_class":     "gthread",
        "certfile":         cert,
        "keyfile":          key,
        "timeout":          120,
        "graceful_timeout": 30,
        "loglevel":         "warning",
    }

    print(_banner(port))
    App(backend.app, options).run()


def run_with_flask(port: int) -> None:
    """Fall back to Flask dev server when Gunicorn is not available."""
    import backend  # noqa

    cert = backend.CERT_FILE
    key  = backend.KEY_FILE

    print(_banner(port))
    backend.app.run(
        host="0.0.0.0",
        port=port,
        ssl_context=(cert, key),
        use_reloader=False,
        threaded=True,
    )


def _banner(port: int) -> str:
    sep = "=" * 58
    return (
        f"\n{sep}\n"
        f"  USBHDD Secure Storage\n"
        f"  https://localhost:{port}\n"
        f"{sep}\n"
        f"  Browser will open automatically.\n"
        f"  Press Ctrl+C to stop the server.\n"
        f"{sep}\n"
    )


if __name__ == "__main__":
    port = find_free_port(8143)
    url  = f"https://localhost:{port}"

    # Open browser in background after server starts
    threading.Thread(
        target=wait_and_open_browser, args=(url,), daemon=True
    ).start()

    try:
        run_with_gunicorn(port)
    except ImportError:
        run_with_flask(port)
