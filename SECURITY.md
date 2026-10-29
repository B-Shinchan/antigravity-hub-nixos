# Security Policy

## Supported Versions

Only the latest release published on the `main` branch of this repository is supported.

| Version | Supported |
| :--- | :--- |
| Latest `main` release | :white_check_mark: |
| Older commits | :x: |

---

## Reporting a Vulnerability

If you discover a security vulnerability or packaging flaw in this repository:

1. **Do not create a public issue**.
2. Open a private [Security Advisory](https://github.com/B-Shinchan/antigravity-hub-nixos/security/advisories/new) on GitHub or contact the maintainer directly.
3. Include details of the vulnerability, reproduction steps, and any potential impact.

---

## Binary Provenance & Verification

- Binaries are downloaded exclusively from official Google Cloud Storage endpoints: `https://storage.googleapis.com/antigravity-public/antigravity-hub/...`.
- All downloads are validated against SHA-256 Subresource Integrity (SRI) hashes recorded in `package.nix`.
- Automated updates verify upstream hash computation before any package derivation is updated.
- Sandboxing is enforced at runtime via bubblewrap (`buildFHSEnv`) ensuring strict user namespaces and read-only host filesystem bindings where appropriate.
