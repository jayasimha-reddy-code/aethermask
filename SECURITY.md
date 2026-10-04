# Security Policy

AetherMask is engineered for mission-critical, air-gapped environments handling sensitive, proprietary, and classified data structures. Security, confidentiality, and cryptographic integrity are paramount.

## Supported Versions

Only the latest minor release receives security fixes and backports.

| Version | Supported          | Security Status |
| ------- | ------------------ | --------------- |
| 2.1.x   | :white_check_mark: | Current stable (supported) |
| 2.0.x   | :white_check_mark: | Critical security patches only |
| < 2.0   | :x:                | End of life |

## Reporting a Vulnerability

**Please do NOT file public GitHub issues for security vulnerabilities.**

If you discover a potential vulnerability, leakage vector, or bypass of our air-gap invariants:

1. **Email Details:** Send an encrypted or plain report to **security@aethermask.org**.
2. **Include Information:**
   - Affected component (`core.engine`, `core.security`, `api.server`, or frontend).
   - Detailed proof of concept (PoC) or reproducer dataset.
   - Operating environment and Python/Node versions.
   - Any observed egress or unexpected network activity.
3. **Acknowledgment:** We commit to acknowledging receipt within **48 hours**.
4. **Assessment & Remediation:** We will provide an assessment and mitigation timeline within **5 business days**.
5. **Coordinated Disclosure:** We adhere to standard 90-day coordinated vulnerability disclosure guidelines, or sooner upon mutual agreement.

## Threat Model & Invariants

AetherMask operates under explicit architectural invariants:

1. **Strict Air-Gap:** Under `AETHERMASK_BLOCK_EGRESS=1`, no outbound socket connection to non-loopback destinations is permitted. Any attempt will immediately raise `OSError` and be recorded as an audit event.
2. **Cryptographic Vault Separation:** Mappings are encrypted with AES-256-GCM derived via Argon2id (t=4, m=256 MiB, p=2) + HKDF-SHA256. Plaintext mappings are never written to disk or transmitted over the wire.
3. **No External CDN/Assets:** The Data Studio SPA operates with strict `default-src 'self'` Content-Security-Policy. All fonts, styles, scripts, and images must be self-contained in the offline bundle.
4. **Isomorphism Scope:** Statistical isomorphism provides mathematical preservation of distributions, counts, and topologies for analytical utility. It is a semantic relabelling mechanism, not differential privacy or k-anonymity. Auxiliary dataset linkage attacks remain relevant if categorical distinct counts are unique in external reference databases.
