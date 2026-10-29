import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "updater", Path(__file__).resolve().parents[1] / "scripts/update.py"
)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Downloads - Antigravity</title></head>
<body>
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/linux-x64/Antigravity.tar.gz">Linux x64</a>
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/linux-arm/Antigravity.tar.gz">Linux ARM</a>
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/darwin-x64/Antigravity.dmg">macOS x64</a>
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/darwin-arm/Antigravity.dmg">macOS ARM</a>
</body>
</html>
"""

NEWER_HTML = """
<!DOCTYPE html>
<html>
<body>
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.29.0-6800000000000000/linux-x64/Antigravity.tar.gz">Linux x64</a>
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.29.0-6800000000000000/linux-arm/Antigravity.tar.gz">Linux ARM</a>
</body>
</html>
"""

DUMMY_PKG = """{
  lib,
  stdenv,
}:
let
  version = "2.28.1";
  src = fetchurl {
    url = "https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/linux-x64/Antigravity.tar.gz";
    hash = "sha256-FbFVeOQy6kMuf8kKxi4UCoRO6ylWU69yql/Vo2SU3vc=";
  };
in {}
"""


class TestAntigravityHubUpdater(unittest.TestCase):
    def test_parse_release_success(self):
        ver, build, urls = u.parse_release(SAMPLE_HTML)
        self.assertEqual(ver, "2.28.1")
        self.assertEqual(build, "6709500728705024")
        self.assertIn("linux-x64", urls)
        self.assertEqual(
            urls["linux-x64"],
            "https://storage.googleapis.com/antigravity-public/antigravity-hub/2.28.1-6709500728705024/linux-x64/Antigravity.tar.gz",
        )

    def test_parse_release_no_urls(self):
        with self.assertRaises(ValueError):
            u.parse_release("<html><body>Empty</body></html>")

    def test_parse_release_conflicting_versions(self):
        conflict_html = SAMPLE_HTML + (
            '<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/'
            '2.30.0-9999999999999999/linux-x64/Antigravity.tar.gz">Conflict</a>'
        )
        with self.assertRaises(ValueError):
            u.parse_release(conflict_html)

    def test_compare_versions(self):
        self.assertEqual(u.compare_versions("2.28.1", "2.28.0"), 1)
        self.assertEqual(u.compare_versions("2.28.1", "2.28.1"), 0)
        self.assertEqual(u.compare_versions("2.28.1", "2.29.0"), -1)
        self.assertEqual(u.compare_versions("2.29.0", "2.28.10"), 1)

    def test_extract_current_and_update_content(self):
        cur_v, cur_h = u._extract_current(DUMMY_PKG)
        self.assertEqual(cur_v, "2.28.1")
        self.assertEqual(cur_h, "sha256-FbFVeOQy6kMuf8kKxi4UCoRO6ylWU69yql/Vo2SU3vc=")

        new_hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
        new_url = "https://storage.googleapis.com/antigravity-public/antigravity-hub/2.29.0-6800000000000000/linux-x64/Antigravity.tar.gz"
        updated = u.update_content(DUMMY_PKG, "2.29.0", "6800000000000000", new_hash, new_url)
        self.assertIn('version = "2.29.0";', updated)
        self.assertIn(f'url = "{new_url}";', updated)
        self.assertIn(f'hash = "{new_hash}";', updated)

    def test_refuse_downgrade(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_file = Path(tmpdir) / "package.nix"
            pkg_file.write_text(DUMMY_PKG)
            older_html = """
<a href="https://storage.googleapis.com/antigravity-public/antigravity-hub/2.27.0-6500000000000000/linux-x64/Antigravity.tar.gz">Older</a>
"""
            with (
                mock.patch.object(u, "PACKAGE_FILE", pkg_file),
                mock.patch.object(u, "fetch_page", return_value=older_html),
                mock.patch("sys.argv", ["update.py"]),
                self.assertRaises(ValueError) as ctx,
            ):
                u.main()
            self.assertIn("Refusing upstream downgrade", str(ctx.exception))

    def test_dry_run_does_not_modify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_file = Path(tmpdir) / "package.nix"
            pkg_file.write_text(DUMMY_PKG)
            with (
                mock.patch.object(u, "PACKAGE_FILE", pkg_file),
                mock.patch.object(u, "fetch_page", return_value=NEWER_HTML),
                mock.patch("sys.argv", ["update.py", "--dry-run"]),
            ):
                u.main()
            self.assertEqual(pkg_file.read_text(), DUMMY_PKG)

    def test_already_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_file = Path(tmpdir) / "package.nix"
            pkg_file.write_text(DUMMY_PKG)
            output_file = Path(tmpdir) / "gh_output"
            with (
                mock.patch.object(u, "PACKAGE_FILE", pkg_file),
                mock.patch.object(u, "fetch_page", return_value=SAMPLE_HTML),
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output_file)}),
                mock.patch("sys.argv", ["update.py"]),
            ):
                u.main()
            self.assertIn("has_update=false", output_file.read_text())


if __name__ == "__main__":
    unittest.main()
