## Summary of Changes

Describe the problem solved or the feature/improvement introduced.

## Motivation & Context

Why is this change necessary? Link to any relevant issue (`Fixes #...`).

## Pre-submission Checklist

- [ ] Evaluated and passed local flake checks: `nix flake check --print-build-logs`
- [ ] Successfully built the derivation locally: `nix build .#default`
- [ ] Verified desktop integration: `python3 scripts/check-desktop.py $(nix build .#default --no-link --print-out-paths)`
- [ ] Formatted Python scripts and Nix expressions: `ruff format scripts tests` & `nix fmt`
- [ ] Tested dry-run of update script: `python3 scripts/update.py --dry-run`
- [ ] Preserved uncorrupted binaries and proper `StartupWMClass` matching
- [ ] No hardcoded user paths or machine-specific assumptions introduced
