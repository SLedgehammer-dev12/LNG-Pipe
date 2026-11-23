"""Frozen-safe desktop launcher for the LNG Pipeline Flow Simulator."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import signal
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _log_path() -> Path:
    if sys.platform == "darwin":
        log_dir = Path.home() / "Library" / "Logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "LNGSimulator.log"
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        log_dir = Path(local_app) / "LNGSimulator"
    else:
        log_dir = Path.home() / ".local" / "state" / "LNGSimulator"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "launcher.log"


def _configure_logging() -> logging.Logger:
    log_file = _log_path()
    # Windowed PyInstaller apps (especially on Windows) may start with None stdout/stderr.
    if getattr(sys, "frozen", False) or sys.stdout is None or sys.stderr is None:
        stream = open(log_file, "a", encoding="utf-8", buffering=1)
        if sys.stdout is None or getattr(sys, "frozen", False):
            sys.stdout = stream
        if sys.stderr is None or getattr(sys, "frozen", False):
            sys.stderr = stream

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )
    return logging.getLogger("lng_launcher")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def _open_browser_when_ready(
    url: str,
    health_url: str,
    logger: logging.Logger,
    timeout_s: float = 45.0,
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.5) as resp:
                if resp.status == 200:
                    logger.info("Streamlit health check ready at %s", url)
                    port_file = os.environ.get("LNG_URL_FILE")
                    if port_file:
                        Path(port_file).write_text(url, encoding="utf-8")
                    if os.environ.get("LNG_NO_BROWSER") != "1":
                        webbrowser.open(url, new=2)
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)
    logger.warning("Timed out waiting for Streamlit health endpoint at %s", health_url)


def main() -> int:
    logger = _configure_logging()
    root = _bundle_root()
    app_path = root / "app.py"

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)

    if not app_path.is_file():
        logger.error("Could not find app.py under %s", root)
        return 1

    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"
    health_url = f"{url}/_stcore/health"
    logger.info("Starting LNG Pipeline Flow Simulator at %s (root=%s)", url, root)

    def _handle_signal(signum: int, _frame: object) -> None:
        logger.info("Received signal %s; shutting down", signum)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    threading.Thread(
        target=_open_browser_when_ready,
        args=(url, health_url, logger),
        daemon=True,
    ).start()

    # Disable Streamlit development mode & file watcher inside frozen bundles.
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE", "false")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]

    try:
        from streamlit.web import cli as stcli

        stcli.main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        logger.info("Streamlit exited with code %s", code)
        return code
    except Exception:
        logger.exception("Unhandled error starting Streamlit desktop app")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
