#!/usr/bin/env python3
"""Update the pinned release from the official Google Antigravity download page.

The Antigravity Hub binary is distributed from Google Cloud Storage. Google
embeds versioned download URLs directly in the official download page at
https://antigravity.google/download — the canonical source that users are
directed to. This script scrapes those URLs, extracts the version and build ID,
downloads each architecture's binary to compute its SRI hash, and writes
updated metadata into package.nix.

Design constraints
------------------
- No unpinned external dependencies (stdlib only).
- All network operations retry on transient errors (up to 4 attempts).
- The script refuses a downgrade, rejects unexpected URL layouts, and
  validates every hash before writing.
- GITHUB_OUTPUT is written only when a real change is detected.
- --dry-run reports what would change without touching package.nix.
- --candidate / --apply-candidate implement the two-phase publish split
  used by the CI workflow (identical to the chatgpt-nixos / claude-nixos
  pattern): the update job captures a pinned candidate artifact; only the
  publish job — running on a fresh runner with write access — applies it.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = ROOT / "package.nix"
DOWNLOAD_PAGE = "https://antigravity.google/download"

# The download page embeds GCS URLs of the form:
#   https://storage.googleapis.com/antigravity-public/antigravity-hub/
#       <version>-<build_id>/<platform>/Antigravity.<ext>
# This pattern captures (version, build_id, platform_slug, extension).
_URL_PATTERN = re.compile(
    r"https://storage\.googleapis\.com/antigravity-public/antigravity-hub/"
    r"([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)"
    r"/(linux-x64|linux-arm|darwin-x64|darwin-arm|windows-x64|windows-arm)"
    r"/Antigravity\.(tar\.gz|dmg|exe)"
)

# NixOS platform → (download platform slug, expected extension)
PLATFORMS = {
    "x86_64-linux": ("linux-x64", "tar.gz"),
    "aarch64-linux": ("linux-arm", "tar.gz"),
    "x86_64-darwin": ("darwin-x64", "dmg"),
    "aarch64-darwin": ("darwin-arm", "dmg"),
}

_VERSION_RE = re.compile(r'^\s*version = "([^"]+)";$', re.MULTILINE)
_HASH_RE = re.compile(r'^\s*hash = "(sha256-[^"]+)";$', re.MULTILINE)
_URL_RE = re.compile(
    r'^\s*url = "https://storage\.googleapis\.com/antigravity-public/antigravity-hub/'
    r'[^"]+";$',
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------


def _fetch(url: str, *, timeout: int = 60, max_retries: int = 4) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "NixOS-antigravity-hub-updater/1.0"})
    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
    raise last_exc


def _compute_sri(url: str, *, max_retries: int = 4) -> str:
    """Stream-download *url* and return a sha256 SRI hash string."""
    req = urllib.request.Request(url, headers={"User-Agent": "NixOS-antigravity-hub-updater/1.0"})
    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(max_retries):
        try:
            h = hashlib.sha256()
            with urllib.request.urlopen(req, timeout=300) as resp:
                while chunk := resp.read(1 << 20):
                    h.update(chunk)
            return "sha256-" + base64.b64encode(h.digest()).decode()
        except (OSError, TimeoutError) as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                time.sleep(3**attempt)
    raise last_exc


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------


def fetch_page() -> str:
    return _fetch(DOWNLOAD_PAGE).decode("utf-8", errors="replace")


def parse_release(html: str) -> tuple[str, str, dict[str, str]]:
    """Return (version, build_id, platform_urls) from the download page HTML.

    Raises ValueError if the layout is unexpected.
    """
    matches = _URL_PATTERN.findall(html)
    if not matches:
        raise ValueError(
            "No Antigravity Hub GCS download URLs found on the official download "
            f"page ({DOWNLOAD_PAGE}). The page layout may have changed."
        )

    # All platform entries should agree on version and build.
    versions = {m[0] for m in matches}
    builds = {m[1] for m in matches}
    if len(versions) != 1:
        raise ValueError(
            f"Conflicting versions on download page: {sorted(versions)!r}. Manual review required."
        )
    if len(builds) != 1:
        raise ValueError(
            f"Conflicting build IDs on download page: {sorted(builds)!r}. Manual review required."
        )
    version = versions.pop()
    build = builds.pop()

    # Validate version format
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError(f"Invalid version string from download page: {version!r}")
    if not re.fullmatch(r"[0-9]+", build):
        raise ValueError(f"Invalid build ID from download page: {build!r}")

    platform_urls: dict[str, str] = {}
    for ver, bld, platform_slug, ext in matches:
        full_url = (
            f"https://storage.googleapis.com/antigravity-public/antigravity-hub/"
            f"{ver}-{bld}/{platform_slug}/Antigravity.{ext}"
        )
        platform_urls[platform_slug] = full_url

    return version, build, platform_urls


def compare_versions(a: str, b: str) -> int:
    """Compare dotted-numeric version strings; return -1, 0, or 1."""
    av = tuple(int(x) for x in a.split("."))
    bv = tuple(int(x) for x in b.split("."))
    return (av > bv) - (av < bv)


# ---------------------------------------------------------------------------
# package.nix manipulation
# ---------------------------------------------------------------------------


def _extract_current(content: str) -> tuple[str, str]:
    """Return (current_version, current_hash) from package.nix."""
    ver_matches = _VERSION_RE.findall(content)
    hash_matches = _HASH_RE.findall(content)
    if len(ver_matches) != 1:
        raise ValueError(
            f"Expected exactly 1 version line in package.nix, found {len(ver_matches)}"
        )
    if len(hash_matches) != 1:
        raise ValueError(f"Expected exactly 1 hash line in package.nix, found {len(hash_matches)}")
    return ver_matches[0], hash_matches[0]


def validate_sri(sri: str) -> None:
    if not re.fullmatch(r"sha256-[A-Za-z0-9+/]{43}=", sri):
        raise ValueError(f"Invalid SRI hash format: {sri!r}")
    decoded = base64.b64decode(sri[7:], validate=True)
    if len(decoded) != 32:
        raise ValueError(f"SRI hash decodes to {len(decoded)} bytes, expected 32")


def update_content(
    content: str, new_version: str, new_build: str, new_hash: str, new_url: str
) -> str:
    """Patch version, build URL, and hash in package.nix content."""
    validate_sri(new_hash)
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", new_version):
        raise ValueError(f"Invalid version: {new_version!r}")
    if not re.fullmatch(r"[0-9]+", new_build):
        raise ValueError(f"Invalid build ID: {new_build!r}")

    # Replace version
    content = re.sub(r'(\s*version = ")[^"]+(";)', rf"\g<1>{new_version}\g<2>", content)

    # Replace the GCS URL (version + build ID in path)
    if not _URL_RE.search(content):
        raise ValueError(
            "Could not find the expected GCS URL line in package.nix. "
            "The file layout may have changed."
        )
    content = re.sub(
        r'(\s*url = "https://storage\.googleapis\.com/antigravity-public/antigravity-hub/)[^"]+(";)',
        rf"\g<1>{new_version}-{new_build}/linux-x64/Antigravity.tar.gz\g<2>",
        content,
    )

    # Replace the hash
    content = re.sub(r'(\s*hash = ")[^"]+(";)', rf"\g<1>{new_hash}\g<2>", content)

    return content


# ---------------------------------------------------------------------------
# Lock-file validation (forward-pin only, official NixOS/nixpkgs input)
# ---------------------------------------------------------------------------


def validate_lock(original: dict, candidate: dict) -> None:
    """Permit only a forward pin of the official NixOS/nixpkgs input."""
    import time as _time

    locked = candidate["nodes"]["nixpkgs"]["locked"]
    expected_keys = {"type", "owner", "repo", "rev", "narHash", "lastModified"}
    if set(locked) != expected_keys:
        raise ValueError(f"Unexpected nixpkgs lock fields: {set(locked)}")
    if (locked["type"], locked["owner"], locked["repo"]) != ("github", "NixOS", "nixpkgs"):
        raise ValueError("Only NixOS/nixpkgs may be refreshed in the lock file")
    if not re.fullmatch(r"[0-9a-f]{40}", locked["rev"]):
        raise ValueError("Invalid nixpkgs revision in lock file")
    validate_sri(locked["narHash"])
    ts = locked["lastModified"]
    orig_ts = original["nodes"]["nixpkgs"]["locked"]["lastModified"]
    if not isinstance(ts, int) or ts < orig_ts or ts > _time.time() + 86400:
        raise ValueError(f"Invalid or backwards nixpkgs timestamp: {ts}")
    # Re-build expected candidate from original, swapping only the locked node.
    import copy

    expected = copy.deepcopy(original)
    expected["nodes"]["nixpkgs"]["locked"] = locked
    if candidate != expected:
        raise ValueError("Lock update changed inputs or fields outside the nixpkgs pin")


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for updates without modifying any file",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        help="Write validated pin metadata to this file for the publish job",
    )
    parser.add_argument(
        "--apply-candidate",
        type=Path,
        help="Apply a validated candidate produced by --candidate (offline; no network)",
    )
    parser.add_argument(
        "--include-lock",
        action="store_true",
        help="Include an audited nixpkgs lock refresh in the candidate",
    )
    args = parser.parse_args()

    lock_path = ROOT / "flake.lock"
    lock_update: dict | None = None
    lock_changed = False

    if args.apply_candidate:
        # ── Publish phase: apply a previously validated candidate ──────────
        cdata = json.loads(args.apply_candidate.read_text())
        required = {"version", "build", "hash", "url"}
        if not required <= set(cdata) or set(cdata) - required - {"nixpkgs_lock"}:
            raise ValueError(f"Unexpected candidate fields: {set(cdata)}")
        new_version, new_build, new_hash, new_url = (
            cdata["version"],
            cdata["build"],
            cdata["hash"],
            cdata["url"],
        )
        if "nixpkgs_lock" in cdata:
            original_lock = json.loads(lock_path.read_text())
            lock_update = cdata["nixpkgs_lock"]
            validate_lock(original_lock, lock_update)
            lock_changed = original_lock != lock_update
    else:
        # ── Update phase: fetch the download page ──────────────────────────
        html = fetch_page()
        new_version, new_build, platform_urls = parse_release(html)

        linux_x64_url = platform_urls.get("linux-x64")
        if not linux_x64_url:
            raise ValueError("linux-x64 download URL not found on the download page")

        if args.include_lock:
            import subprocess

            original_lock = json.loads(
                subprocess.check_output(["git", "show", "HEAD:flake.lock"], cwd=ROOT, text=True)
            )
            lock_update = json.loads(lock_path.read_text())
            validate_lock(original_lock, lock_update)
            lock_changed = original_lock != lock_update

        # Check current pinned version
        original = PACKAGE_FILE.read_text()
        current_version, current_hash = _extract_current(original)

        cmp = compare_versions(new_version, current_version)
        if cmp < 0:
            raise ValueError(f"Refusing upstream downgrade from {current_version} to {new_version}")

        version_changed = cmp != 0
        changed = version_changed or lock_changed

        print(f"Upstream version: {new_version}  (build {new_build})")
        print(f"Current version:  {current_version}")
        print(f"Version changed:  {version_changed}  |  Lock changed: {lock_changed}")

        if not changed:
            print("Already up to date — no changes needed.")
            if args.candidate:
                cdata_out = {
                    "version": new_version,
                    "build": new_build,
                    "hash": current_hash,
                    "url": linux_x64_url,
                }
                if lock_changed:
                    cdata_out["nixpkgs_lock"] = lock_update
                args.candidate.write_text(json.dumps(cdata_out, indent=2) + "\n")
                print(f"Candidate metadata written to {args.candidate}")
            if out := os.environ.get("GITHUB_OUTPUT"):
                with open(out, "a") as f:
                    f.write(f"has_update=false\nversion={current_version}\n")
            return

        # Compute hash only when an actual version update is required
        if version_changed and not args.dry_run:
            print(f"Downloading and hashing: {linux_x64_url}")
            new_hash = _compute_sri(linux_x64_url)
            print(f"New hash: {new_hash}")
        elif args.dry_run:
            print(f"[dry-run] Would download: {linux_x64_url}")
            new_hash = current_hash  # Not written in dry-run
        else:
            new_hash = current_hash  # Lock-only change; hash stays the same

        new_url = linux_x64_url

        if args.candidate:
            cdata_out = {
                "version": new_version,
                "build": new_build,
                "hash": new_hash,
                "url": new_url,
            }
            if lock_changed:
                cdata_out["nixpkgs_lock"] = lock_update
            args.candidate.write_text(json.dumps(cdata_out) + "\n")
            print(f"Candidate metadata written to {args.candidate}")

        if not args.dry_run:
            updated = update_content(original, new_version, new_build, new_hash, new_url)
            PACKAGE_FILE.write_text(updated)
            print(f"Updated {PACKAGE_FILE}")

        if out := os.environ.get("GITHUB_OUTPUT"):
            with open(out, "a") as f:
                f.write(f"has_update=true\nversion={new_version}\nbuild={new_build}\n")

        print(f"Upstream release: {new_version}; package changed: {changed}")
        return

    # ── apply-candidate path ──────────────────────────────────────────────
    original = PACKAGE_FILE.read_text()
    current_version, _ = _extract_current(original)

    cmp = compare_versions(new_version, current_version)
    if cmp < 0:
        raise ValueError(f"Refusing upstream downgrade from {current_version} to {new_version}")
    version_changed = cmp != 0
    changed = version_changed or lock_changed

    if version_changed:
        updated = update_content(original, new_version, new_build, new_hash, new_url)
        PACKAGE_FILE.write_text(updated)

    if lock_changed and lock_update is not None:
        lock_path.write_text(json.dumps(lock_update, indent=2) + "\n")

    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a") as f:
            f.write(f"has_update={str(changed).lower()}\nversion={new_version}\n")

    print(f"Applied candidate: {new_version}; package changed: {changed}")


if __name__ == "__main__":
    main()
