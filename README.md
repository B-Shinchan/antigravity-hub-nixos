# antigravity-hub-nixos

Always-up-to-date NixOS flake packaging the official upstream binary of **Google Antigravity 2.0 (Antigravity Hub)** — the standalone agentic AI coding command center and desktop application.

Features automated daily upstream checks, integrity validation, and unattended release updates via GitHub Actions.

## Overview

- **Application:** Google Antigravity (Antigravity Hub)
- **Publisher:** Google LLC
- **Homepage:** [https://antigravity.google](https://antigravity.google)
- **Version:** `2.28.1`
- **Executable:** `antigravity-hub`
- **Distribution Method:** Official Google Cloud Storage tarball (`Antigravity.tar.gz`) from `antigravity.google/download`

## Relationship to Google Antigravity IDE

This repository packages the standalone **Antigravity 2.0 Agent Hub** desktop application. If you are looking for Google's VS Code-based code editor, see [antigravity-nixos](https://github.com/B-Shinchan/antigravity-nixos).

Both applications are engineered to coexist without interference:
- **Antigravity Hub:** Executable `antigravity-hub`, Desktop Entry `antigravity-hub.desktop`, User Data `~/.config/Antigravity`
- **Antigravity IDE:** Executable `antigravity-ide`, Desktop Entry `antigravity-ide.desktop`, User Data `~/.config/Antigravity IDE`

## Installation

### Flake

Add `antigravity-hub-nixos` to your `flake.nix` inputs:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    antigravity-hub.url = "github:B-Shinchan/antigravity-hub-nixos";
  };

  outputs = { self, nixpkgs, antigravity-hub, ... }: {
    # In your home-manager or nixos configuration:
    # environment.systemPackages = [ antigravity-hub.packages.${system}.default ];
    # OR
    # home.packages = [ antigravity-hub.packages.${system}.default ];
  };
}
```

### Run directly with Nix

```bash
nix run github:B-Shinchan/antigravity-hub-nixos
```

## Automated Updates

The GitHub Actions workflow runs daily at 06:00 UTC (11:30 AM IST). It:
1. Fetches the latest release metadata and edge delivery URLs from the official Google download page.
2. Compares the upstream version with the currently pinned version.
3. Downloads the official binary and calculates its SHA-256 SRI hash.
4. Executes unit tests (`tests/test_update.py`), Nix formatting, desktop validations, and build checks.
5. Commits and publishes updates automatically only after all checks pass.

## License

The packaging code is licensed under the MIT License. Google Antigravity is proprietary software provided by Google LLC under its own license terms.
