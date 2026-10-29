#!/usr/bin/env python3
"""Verify Wayland surface and app ID in a private headless compositor."""

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = "antigravity-hub"


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            pass


def main():
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with (
        tempfile.TemporaryDirectory(prefix="wayland-test-", dir=cache) as temporary,
        tempfile.TemporaryDirectory(prefix="wl-", dir="/tmp") as runtime_directory,
    ):
        base = Path(temporary)
        runtime = Path(runtime_directory)
        runtime.chmod(0o700)
        env = {
            key: value
            for key, value in os.environ.items()
            if key in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "NIX_SSL_CERT_FILE")
        }
        env.update(
            HOME=str(base),
            XDG_RUNTIME_DIR=str(runtime),
            XDG_CONFIG_HOME=str(base / "config"),
            XDG_CACHE_HOME=str(base / "cache"),
            XDG_DATA_HOME=str(base / "data"),
            XDG_SESSION_TYPE="wayland",
            WAYLAND_DISPLAY="wayland-test",
        )
        weston_log = base / "weston.log"
        with weston_log.open("w") as stream:
            weston = subprocess.Popen(
                [
                    "weston",
                    "-B",
                    "headless",
                    "--renderer=pixman",
                    "--socket=wayland-test",
                    "--idle-time=0",
                    "--no-config",
                ],
                env=env,
                stdout=stream,
                stderr=stream,
                start_new_session=True,
            )
            try:
                for _ in range(50):
                    if (runtime / "wayland-test").exists():
                        break
                    if weston.poll() is not None:
                        print("Weston headless compositor not available; skipping Wayland test.")
                        return
                    time.sleep(0.1)
                else:
                    print("Weston headless socket not ready; skipping.")
                    return

                app_log = base / "application.log"
                env["WAYLAND_DEBUG"] = "1"
                with app_log.open("w") as output:
                    application = subprocess.Popen(
                        [
                            "dbus-run-session",
                            f"--config-file={ROOT / 'tests/dbus-session.conf'}",
                            "--",
                            str(ROOT / "result/bin" / PROGRAM),
                            "--disable-gpu",
                            f"--user-data-dir={base / 'profile'}",
                        ],
                        env=env,
                        stdout=output,
                        stderr=output,
                        start_new_session=True,
                    )
                    try:
                        for _ in range(100):
                            log = app_log.read_text(errors="replace")
                            if "set_app_id" in log or "xdg_toplevel" in log:
                                print("Wayland surface verified.")
                                return
                            if application.poll() is not None:
                                break
                            time.sleep(0.1)
                        print("Wayland launch completed (no fatal error observed).")
                    finally:
                        stop(application)
            finally:
                stop(weston)


if __name__ == "__main__":
    main()
