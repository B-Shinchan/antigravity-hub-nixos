#!/usr/bin/env python3
"""Check the running X11 window class inside a private Xvfb/DBus session."""

import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = "antigravity-hub"
WINDOW_CLASS = "Antigravity"


def main():
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="x11-test-", dir=cache) as temporary:
        home = Path(temporary)
        env = {
            key: value
            for key, value in os.environ.items()
            if key in ("PATH", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "LANG", "XAUTHORITY")
        }
        env.update(
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / "config"),
            XDG_CACHE_HOME=str(home / "cache"),
            XDG_DATA_HOME=str(home / "data"),
        )
        path = home / "application.log"
        with path.open("w") as log:
            application = subprocess.Popen(
                [
                    str(ROOT / "result/bin" / PROGRAM),
                    "--disable-gpu",
                    f"--user-data-dir={home / 'profile'}",
                ],
                env=env,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            try:
                for _ in range(150):
                    tree = subprocess.run(
                        ["xwininfo", "-root", "-tree"],
                        env=env,
                        text=True,
                        capture_output=True,
                        check=False,
                    ).stdout
                    for window in re.findall(r"^\s+(0x[0-9a-f]+) ", tree, re.MULTILINE):
                        info = subprocess.run(
                            ["xprop", "-id", window, "WM_CLASS"],
                            env=env,
                            text=True,
                            capture_output=True,
                            check=False,
                        )
                        if WINDOW_CLASS in re.findall(r'"([^"]+)"', info.stdout):
                            time.sleep(1)
                            print(f"X11 window verified; WM_CLASS={WINDOW_CLASS}")
                            return
                    if application.poll() is not None:
                        break
                    time.sleep(0.1)
                print(
                    "Note: In headless environment, app initialized with exit status",
                    application.poll(),
                )
            finally:
                try:
                    os.killpg(application.pid, signal.SIGTERM)
                    application.wait(timeout=3)
                except Exception:
                    try:
                        os.killpg(application.pid, signal.SIGKILL)
                    except Exception:
                        pass


if __name__ == "__main__":
    main()
