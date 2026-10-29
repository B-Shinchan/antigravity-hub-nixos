# Contributing to Google Antigravity Hub NixOS Packaging

Thank you for your interest in improving this package! We welcome bug reports, packaging enhancements, and documentation fixes.

---

## Code of Conduct

Please keep interactions respectful, constructive, and focused on improving the NixOS packaging.

---

## Local Development & Validation

Before submitting a Pull Request, ensure that all checks pass in your local checkout:

```bash
# 1. Run all Flake checks (formatting, tests, desktop validation)
nix flake check --print-build-logs

# 2. Build the package locally
nix build .#default --print-build-logs

# 3. Test updater script in dry-run mode
python3 scripts/update.py --dry-run

# 4. Run test suite
python3 -m unittest discover -s tests -v

# 5. Check formatting with ruff and nixfmt
ruff check scripts tests
nix fmt -- --check *.nix
```

---

## Submitting Pull Requests

1. **Focus on single concerns**: Keep PRs focused on one bug fix or feature.
2. **Do not manually edit version/hashes**: The GitHub Actions workflow updates upstream hashes automatically every 24 hours. If an urgent bump is needed, run `python3 scripts/update.py` and commit the resulting `package.nix` change.
3. **Preserve compatibility**: Do not break standard Freedesktop desktop entries, Wayland Ozone flags, or FHS bubblewrap sandbox requirements.

---

## Upstream References

- Google Antigravity Official Site: <https://antigravity.google>
- Download Page: <https://antigravity.google/download>
- Nixpkgs Manual & Guidelines: <https://nixos.org/manual/nixpkgs/unstable/>
