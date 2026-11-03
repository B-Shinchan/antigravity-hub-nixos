#!/usr/bin/env python3
"""Generate structured GitHub Release notes for Google Antigravity Hub."""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = ROOT / "package.nix"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    if not PACKAGE_FILE.exists():
        sys.exit(f"Error: {PACKAGE_FILE} not found")

    content = PACKAGE_FILE.read_text()

    # Extract version
    version_match = re.search(r'version = "([^"]+)";', content)
    version = version_match.group(1) if version_match else "unknown"

    # Extract hash
    hash_match = re.search(r'hash = "(sha256-[^"]+)";', content)
    sri_hash = hash_match.group(1) if hash_match else "unknown"

    # Extract download URL and build ID
    url_match = re.search(
        r'url = "https://storage\.googleapis\.com/antigravity-public/antigravity-hub/([0-9.]+)-([0-9]+)/linux-x64/Antigravity\.tar\.gz";',
        content,
    )
    if url_match:
        build = url_match.group(2)
        url = url_match.group(0).replace('url = "', '').rstrip('";')
    else:
        build = "unknown"
        url = f"https://storage.googleapis.com/antigravity-public/antigravity-hub/{version}/linux-x64/Antigravity.tar.gz"

    if not tag:
        tag = f"v{version}"

    # Determine title
    rev_match = re.search(r"-([0-9]+)$", tag)
    if rev_match:
        title = f"Google Antigravity Hub v{version} (Packaging Revision {rev_match.group(1)})"
    else:
        title = f"Google Antigravity Hub v{version} (NixOS Release)"

    body = f"""### Google Antigravity Hub `{version}` (Build `{build}`)

Official vendor binary packaging of **Google Antigravity 2.0** (Standalone Agent Hub & Mission Control) for NixOS.

#### Upstream Artifact Details

| Property | Value |
| :--- | :--- |
| **Application** | Google Antigravity Hub (Agent Mission Control) |
| **Upstream Version** | `{version}` |
| **Build Identifier** | `{build}` |
| **Upstream Source** | [Official Google Cloud Storage Archive]({url}) |
| **x86_64-linux SRI** | `{sri_hash}` |

#### Automated CI Verification

- **Flake Evaluation**: Verified Flake outputs and Nix formatting (`nix flake check`)
- **Package Build**: Compiled sandboxed FHS environment with bubblewrap and autoPatchelf (`nix build`)
- **Desktop Integration**: Validated XDG desktop entry (`antigravity-hub.desktop`) and icon specification
- **Runtime Check**: Executable headless startup and binary link sanity test (`scripts/check-runtime.sh`)

#### Installation & Pinning

##### Immediate Run
```bash
nix run github:B-Shinchan/antigravity-hub-nixos/{tag}
```

##### Flake Input (`flake.nix`)
Pin this specific release in your system flake:
```nix
inputs.antigravity-hub.url = "github:B-Shinchan/antigravity-hub-nixos/{tag}";
```

##### NixOS Module (`configuration.nix`)
```nix
imports = [ inputs.antigravity-hub.nixosModules.default ];
programs.antigravity-hub.enable = true;
```

##### Home Manager (`home.nix`)
```nix
home.packages = [
  inputs.antigravity-hub.packages.${{pkgs.stdenv.hostPlatform.system}}.default
];
```

---
> [!NOTE]
> **Antigravity Hub vs. Antigravity IDE**:
> - **Antigravity Hub** (this repository): Google's standalone agent mission control application (`antigravity-hub`).
> - **Antigravity IDE**: Google's agent-first code editor built on VS Code (`antigravity-ide`), packaged at [B-Shinchan/antigravity-ide-nixos](https://github.com/B-Shinchan/antigravity-ide-nixos).
>
> Both applications can run simultaneously with fully isolated desktop identities and window matching.
"""

    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as f:
            f.write(f"title={title}\n")

    print(body.strip())


if __name__ == "__main__":
    main()
