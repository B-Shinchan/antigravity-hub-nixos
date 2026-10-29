#!/usr/bin/env python3
"""Check installed desktop entries and icon assets without a graphical session."""

import configparser
import struct
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
application_name = "Antigravity Hub"
launcher = root / "bin/antigravity-hub"
expected_entries = {"antigravity-hub.desktop", "antigravity.desktop"}
found_entries = {p.name for p in (root / "share/applications").glob("*.desktop")}
assert found_entries == expected_entries, f"Expected {expected_entries}, found {found_entries}"
entry = root / "share/applications/antigravity-hub.desktop"
subprocess.run(["desktop-file-validate", str(entry)], check=True)
config = configparser.ConfigParser(interpolation=None, strict=True)
config.optionxform = str
config.read(entry)
main = config["Desktop Entry"]
assert main["StartupWMClass"] in ("antigravity", "Antigravity")
assert main["Name"] == application_name
assert main["Type"] == "Application"
assert "Development;" in main["Categories"]
assert launcher.is_file() and launcher.stat().st_mode & 0o111, "Launcher is not executable"

icon = main["Icon"]
assert "/" not in icon, "Prefer a theme icon name"
icons = [p for p in (root / "share").rglob("*") if p.name in (icon + ".png", icon + ".svg")]
assert icons, f"Missing icon: {icon}"
for path in icons:
    assert path.is_file(), f"Broken icon: {path}"
    if path.suffix == ".png" and "x" in path.parent.parent.name:
        dimensions = path.parent.parent.name.split("x")
        if all(d.isdigit() for d in dimensions):
            with path.open("rb") as stream:
                header = stream.read(24)
            assert header[:8] == b"\x89PNG\r\n\x1a\n"
            assert struct.unpack(">II", header[16:24]) == tuple(map(int, dimensions)), (
                f"Wrong icon dimensions: {path}"
            )
for path in (root / "share").rglob("*"):
    assert not path.is_symlink() or path.exists(), f"Broken desktop asset symlink: {path}"
print(f"Validated {application_name} launcher, desktop actions, and icon assets successfully.")
