# Browser UI suite

Drives the full five-stage Data Studio workflow in a real Chromium instance and
asserts 34 checks, including an independent observation that the SPA issues
**zero external network requests**.

## Running

```bash
# 1. Start the server with the built SPA
cd /path/to/aethermask
export PYTHONPATH=$PWD
AETHERMASK_STATIC_DIR=$PWD/frontend/dist \
  python3 -m uvicorn api.server:app --host 0.0.0.0 --port 8000

# 2. In a scratch directory WITH network access (staging host only):
npm install playwright && npx playwright install chromium

# 3. Run the suite
node ui_flow.mjs
```

Expected output:

```
ALL 34 UI CHECKS PASSED
External requests: 0
```

Screenshots are written to `tests/ui/screenshots/` by default (override with the `SHOTS` environment variable).

## What it asserts

- header, air-gap badge and 5-stage rail render
- lexicon capacity panel reports the expanded surrogate count
- ingest → profile: risk grade, finding distribution, expandable column detail
- transform: 8 cover domains + 2 numeric modes, new v2 domains selectable,
  passphrase strength meter
- vault: isomorphism banner 73/73, parity Σ|Δ| = 0, split compare, column
  ledger, AES-256-GCM badge, chart tab switch, TanStack v9 `aria-sort`
- restore: artifact/vault handoff, re-identification completes, restored grid
- attestation drawer: browser-observed egress section reports NONE
- renders correctly under `prefers-reduced-motion: reduce`
- 0 external requests, 0 console/page errors
