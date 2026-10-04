# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Differential privacy integration option alongside bijective affine transformations.
- Streaming parquet transformer for multi-gigabyte files exceeding host memory.

## [2.1.0] - 2026-10-04

### Added
- Independent Audit Stage (Stage 6): Dedicated UI surface and `/api/v1/verify` endpoint recomputing all statistical invariants directly from raw source, sanitized output, and vault credentials.
- Command Palette (`Ctrl-K` / `Cmd-K`): Keyboard-first accessible launcher for pipeline navigation, actions, downloads, and attestation.
- Dry-Run Preview Mode: Transient split-screen diff and parity charts without persisting or sealing encrypted vaults.
- Client-Side Egress Watchdog: Browser-level interceptor patching `fetch` and `XMLHttpRequest` with `PerformanceObserver` tracking to ensure zero external network calls from the SPA.
- Two new domain profiles: `space_recon_to_earth_observation` and `cni_to_facilities_management`.
- Comprehensive GitHub open-source scaffolding (`pyproject.toml`, issue templates, PR template, CI workflows, security policies).

### Changed
- Frontend UI rewritten to modern React 19, Vite 8, Tailwind CSS v4 (CSS-first), Motion 13, and TanStack Table v9.
- Total surrogate capacity expanded to **142,894** across 10 bundled domain profiles.
- Pytest compatibility added across verification suites while maintaining direct script invocation.
- Defensive environment configuration loading with explicit type checking.

### Fixed
- Handling of legacy CR newlines and non-UTF-8 character encodings in CSV ingest.
- Potential numeric identifier collisions when source IDs contain irregular formatting.
- Strict relative path resolution in UI integration test harnesses.

## [2.0.0] - 2026-08-15

### Added
- Multi-table relational preservation: Foreign key graph discovery and consistent surrogate propagation across table boundaries.
- Offline deterministic Named Entity Recognition (NER) covering 12 entity types without remote downloads.
- Domain profiles for `biodefence_to_agriculture` and `finint_to_retail_analytics`.
- Redacting profiler mode for privacy-preserving schema inspection.

### Changed
- Cryptographic vault upgraded to Argon2id (m=256 MiB, t=4, p=2) + HKDF-SHA256 + AES-256-GCM.
- Ingestion engine ported to Polars vectorised execution engine.

## [1.0.0] - 2026-02-01

### Added
- Initial release of AetherMask offline isomorphic engine.
- 6 initial domain profiles (`defense_to_logistics`, `aerospace_to_civil_aviation`, `cyberwar_to_smartgrid`, `nuclear_to_civil_energy`, `naval_to_commercial_shipping`, `generic_pii_redaction`).
- Lossless round-trip restoration using encrypted `.ciphermap` envelopes.
- FastAPI server with egress sentinel middleware.
- Headless CLI interface (`cli/aethermask.py`).
