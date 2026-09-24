# AetherMask · CipherShift

**A 100% offline, air-gapped semantic obfuscation, anonymization and lossless
de-anonymization platform.**

> **Version 2.1** — expanded lexicon (**142,894** unique surrogates across
> **10** cover domains), rebuilt Data Studio GUI on React 19 · Vite 8 ·
> Tailwind v4 · Motion 13 · TanStack Table v9 · Recharts 3, a browser-side
> egress watchdog that independently enforces the air-gap, and three new
> workflow surfaces: a **Ctrl-K command palette**, a no-artifact **dry-run
> preview**, and a standalone **independent audit** stage that re-verifies a
> sanitized artifact from the raw files alone.

AetherMask ingests confidential datasets (PostgreSQL, CSV, XLSX, Parquet, JSON,
SQL dumps), projects every sensitive column name, categorical token and
narrative entity into a realistic non-classified cover domain, and emits a
sanitized artifact that is **statistically indistinguishable from the original
for analytical purposes** — plus an AES-256-GCM encrypted `.ciphermap` vault
that permits exact, lossless re-identification.

---

## 1. Verified guarantees

All claims below are enforced by executable assertions, not documentation.
**192/192 checks pass** — 92 engine + 48 API + 44 browser UI + 8 audit-flow
end-to-end.

| # | Guarantee | How it is enforced | Evidence |
|---|-----------|--------------------|----------|
| G1 | **100% air-gapped** | Egress sentinel wraps `socket.connect`; test suite monkey-patches the entire socket module and runs the full pipeline | `test_airgap` |
| G2 | **Statistical isomorphism** | Row/null/cardinality equality, categorical frequency multisets, group-by vectors, correlation matrices, time-series curves | `test_isomorphism`, `verify_fidelity()` |
| G3 | **Deterministic bijectivity** | `BijectiveMap` raises on any many-to-one collapse or key remap; HMAC-driven surrogate allocation | `test_bijectivity` |
| G4 | **Cryptographic vault** | Argon2id → HKDF → AES-256-GCM with the manifest header bound as AAD, plus an independent HMAC-SHA256 | `test_vault` |
| G5 | **Lossless round-trip** | `original == restore(mask(original))` byte-for-byte, including free-text narrative and downstream BI aggregates | `test_roundtrip` |
| G6 | **No browser-side egress** | `fetch`/`XHR` patched to reject non-same-origin URLs; `PerformanceObserver` catches sub-resource loads | Playwright UI suite |

```
$ python3 tests/test_full_suite.py     →  ALL 90 CHECKS PASSED
$ python3 tests/test_api.py            →  ALL 48 API CHECKS PASSED
$ node flow.mjs   (Playwright)         →  ALL 34 UI CHECKS PASSED
                                          External requests: 0
```

### The isomorphism contract

For an original relation `R` and its masked image `M = T(R)`:

```
|R| = |M|                                    row count
nulls(R.c)      = nulls(M.T(c))              null topology
|distinct(R.c)| = |distinct(M.T(c))|         cardinality
P(R.c = v)      = P(M.T(c) = T(v))           categorical distribution
R.a ⋈ R.b       ≡ M.T(a) ⋈ M.T(b)            join / FK topology
numeric columns : identity, or declared affine y = ax + b (a ≠ 0)
T is injective on every domain it touches    1↔1, invertible
```

Because `T` is a *relabelling* (a graph isomorphism on the value lattice),
every count, ratio, aggregate, histogram bucket, cluster assignment and
trendline is numerically identical. In the default `identity` numeric mode all
numeric aggregates are **bit-identical**.

Measured on the bundled 420-row sample: `Σ|Δ| = 0` across every aggregate
bucket; Pearson correlation matrices agree to `< 1e-12`.

---

## 2. Architecture

```
aethermask/
├── core/
│   ├── ontology.py    Domain-shift matrices, surrogate pools, sensitivity
│   │                  rules, offline NER patterns  (pure data, auditable)
│   ├── lexicon.py     Expanded surrogate pools + 2 extra cover domains,
│   │                  composed deterministically from auditable stems
│   ├── nlp.py         Deterministic rule-based NER + optional local spaCy
│   ├── profiler.py    Schema introspection, PK/FK discovery, risk scoring
│   ├── ingest.py      CSV/TSV/XLSX/Parquet/JSON/SQL-dump/PostgreSQL readers
│   ├── engine.py      OfflineIsomorphicEngine — bijective transform + verify
│   ├── security.py    CipherVault — Argon2id, AES-256-GCM, HMAC, fingerprints
│   └── serialize.py   Faithful re-emission in the source physical format
├── api/server.py      FastAPI app, egress sentinel, strict CSP
├── cli/aethermask.py  Terminal workflow for headless air-gapped hosts
├── frontend/          Data Studio SPA — see §10
│   ├── src/lib/       api.ts · types.ts · motion.ts · format.ts
│   │                  useEgressWatch.ts (client-side air-gap enforcement)
│   └── src/components/  DataStudio · DataGrid · ParityCharts · SplitCompare
│                        ProfilePanel · Controls · Attestation · ui/Primitives
├── tests/             Engine suite (90) and API suite (48)
├── docker/Dockerfile  3-stage build; runtime installs with --no-index
└── docker-compose.offline.yml    network_mode: "none"
```

### Ten bundled domain profiles

`pool_capacity` is the per-profile addressable surrogate space (the sum of that
profile's ten pools); the 142,894 figure is the de-duplicated union across all
profiles, since the large shared pools (`PLACE`, `PERSON`, `GENERIC`) are
reused rather than re-counted.

| Key | Projection | Token rules | Pool capacity |
|-----|-----------|------------:|--------------:|
| `defense_to_logistics` | Kinetic defense / joint fires → commercial freight & haulage | 191 | 83,267 |
| `aerospace_to_civil_aviation` | Combat aviation / air tasking → scheduled commercial aviation | 233 | 70,299 |
| `cyberwar_to_smartgrid` | Offensive & defensive cyber ops → distribution-grid SCADA telemetry | 86 | 76,058 |
| `nuclear_to_civil_energy` | Strategic deterrent / fissile inventory → civil power generation | 216 | 76,048 |
| `naval_to_commercial_shipping` | Naval operations / sea control → container liner shipping | 213 | 72,982 |
| `generic_pii_redaction` | Enterprise records with PII → neutral corporate directory | 38 | 78,631 |
| `biodefence_to_agriculture` **(v2)** | Biological & chemical defence → commercial crop science | 89 | 71,836 |
| `finint_to_retail_analytics` **(v2)** | Financial intelligence / sanctions → retail commerce analytics | 86 | 70,656 |
| `space_recon_to_earth_observation` **(v2.1)** | Overhead collection / IMINT → commercial earth observation | 78 | 70,892 |
| `cni_to_facilities_management` **(v2.1)** | CNI protection / threat assessment → corporate facilities management | 77 | 71,546 |

**142,894 unique surrogates** and **1,307 token-shift rules** in total, plus
**35 sensitivity detectors** and **27 offline NER patterns**.

#### How the pools are built

`core/lexicon.py` composes large pools from short, human-reviewable stem lists
via a deterministic cartesian product (`_compose()`), then sorts and
de-duplicates. This is intentional:

* **Reproducible** — no RNG, no host entropy, no dict-ordering dependence, so
  a `.ciphermap` produced on one machine unseals identically on another.
* **Auditable** — an accreditor reviews ~80 stems, not 5,000 strings.
* **Collision-resistant** — large pools mean high-cardinality columns rarely
  exhaust a pool and fall back to numeric suffixing, so masked data keeps
  reading like genuine civil-sector records.

v1.0 pool entries are preserved as the **prefix** of every expanded pool, so
mappings generated by v1.0 for a given (profile, seed) remain reproducible.

Example of the `defense_to_logistics` projection:

```
missile_control    → mission_control      strike_squadron   → logistics_fleet
warhead_yield      → cargo_capacity       target_latitude   → waypoint_lat
kill_probability   → completion_probability   classification → handling_tier
"12th Strike Squadron" → "Meridian Cargo Lines"
"Target BASTION"       → "Pemberton Depot"
"ALPHA-1"              → "Hauler-Quartz"
```

---

## 3. Cryptographic design

```
passphrase ──Argon2id(t=4, m=256 MiB, p=2, 16B salt)──▶ 32-byte master key
master key ──HKDF-SHA256(info="aethermask/v1/enc")────▶ AES-256 key
master key ──HKDF-SHA256(info="aethermask/v1/mac")────▶ HMAC key

payload    = zlib(canonical_json(mapping))
ciphertext = AES-256-GCM(key, 12B nonce, aad = canonical manifest header)
vault_hmac = HMAC-SHA256(mac_key, aad ‖ ciphertext ‖ tag)
```

* The mapping is **never** written to disk in plaintext.
* The header — including `schema_fingerprint` and the KDF parameters — is bound
  into the AEAD as AAD, so editing any field invalidates decryption.
* Fresh salt and nonce per seal (semantic security).
* Constant-time comparisons; no secret-dependent branching.

`.ciphermap` manifest:

```json
{
  "version": "1.0",
  "cipher_suite": "AES-256-GCM-Argon2id",
  "salt": "<hex>", "nonce": "<hex>", "auth_tag": "<hex>",
  "schema_fingerprint": "<sha256 of original columns and types>",
  "kdf": { "algorithm": "argon2id", "time_cost": 4,
           "memory_cost_kib": 262144, "parallelism": 2 },
  "plaintext_sha256": "<hex>", "vault_hmac": "<hex>",
  "encrypted_payload": "<base64 ciphertext>"
}
```

Decrypted payload:

```json
{ "columns": {"orig": "anon"}, "values": {"orig": "anon"},
  "table_names": {...}, "transform_params": {...},
  "column_meta": {...}, "schema": {...} }
```

---

## 4. Running it

### Local (development / single workstation)

```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build:fast && cd ..
python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

### Air-gapped container (production)

```bash
# 1. On a connected STAGING host — the only place a network is used:
docker compose -f docker-compose.offline.yml build
docker save aethermask:1.0.0 | gzip > aethermask-1.0.0.tar.gz

# 2. Transfer the tarball via approved removable media.

# 3. On the AIR-GAPPED host:
docker load < aethermask-1.0.0.tar.gz
docker compose -f docker-compose.offline.yml up -d aethermask
```

`network_mode: "none"` gives the container **only a loopback interface** — no
default route, no DNS, no reachable peers. Exfiltration is impossible at the
kernel network-namespace level, not merely by policy. The container also runs
`read_only`, as UID 10001, with `cap_drop: ALL` and `no-new-privileges`.

If operators need browser access over TCP, the `lan` profile uses an
`internal: true` bridge (no NAT to the outside world) published on host
loopback only:

```bash
docker compose -f docker-compose.offline.yml --profile lan up -d
```

### CLI (headless hosts)

```bash
python3 cli/aethermask.py profile    data.csv
python3 cli/aethermask.py obfuscate  data.csv --passphrase-file pw.txt \
        --profile defense_to_logistics --outdir ./out
python3 cli/aethermask.py restore    out/data_sanitized.csv out/data.ciphermap \
        --passphrase-file pw.txt
python3 cli/aethermask.py verify     data.csv out/data_sanitized.csv \
        out/data.ciphermap --passphrase-file pw.txt
python3 cli/aethermask.py attest
```

Passphrases are read from a file or an interactive prompt — never from `argv`,
so they cannot leak into shell history or the process table.

---

## 5. API

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/health` | Liveness + air-gap flag |
| GET | `/api/v1/profiles` | Domain-profile catalogue |
| GET | `/api/v1/attestation` | Full offline compliance report |
| POST | `/api/v1/profile` | Schema + sensitivity analysis (**no data retained**) |
| POST | `/api/v1/preview` | Dry-run split-screen + chart parity |
| POST | `/api/v1/obfuscate` | File → sanitized artifact + encrypted `.ciphermap` |
| POST | `/api/v1/restore` | Sanitized + `.ciphermap` + passphrase → exact original |
| POST | `/api/v1/verify` | Independent isomorphism audit of a triple |

`/api/v1/profile` uses a **redacting profiler**: every statistic (counts,
cardinality, frequency shape) is returned verbatim while all sample values and
category labels are redacted, so a schema analysis can be shared low-side
without disclosing the contents it describes.

---

## 6. Re-identifying downstream analytical output

Inversion operates on the **token lattice**, not on row identity. A Tableau
export, a pivot table, or a model scorecard produced from masked data — with
computed columns that never existed in the source schema — restores correctly:

```python
masked_report = masked.group_by("risk_level").agg(
    pl.col("dispatch_runs").sum().alias("total_runs"))

restored = OfflineIsomorphicEngine.restore(
    {"missions": masked_report}, payload).tables["missions"]
# -> "risk_level" becomes "threat_level", categories are re-identified,
#    and "total_runs" (a derived measure) keeps its exact numeric values.
```

---

## 7. Operational security notes

* **Separate the artifact from the vault.** Store the `.ciphermap` and its
  passphrase on different media from the sanitized dataset. Together they
  reconstruct the confidential source; apart, neither discloses anything.
* **The passphrase is unrecoverable.** There is no escrow, no reset, no backdoor.
* **Numeric identity mode leaks distributions by design.** That is the point —
  analytical fidelity is a requirement. If the *numeric values themselves* are
  sensitive (e.g. exact yields), use `numeric_mode="affine"`; note that affine
  shifts preserve shape, so they are obfuscation, not differential privacy.
* **Cardinality is preserved, therefore so is re-identification risk from
  auxiliary data.** A masked column with 5 distinct values still has 5. This
  system provides *semantic* cover, not k-anonymity or differential privacy.
  Pair it with access control and aggregation thresholds where linkage attacks
  are in scope.
* **The `seed` determines all surrogates.** Reusing a seed across datasets
  produces consistent surrogates (useful for joining across releases) but links
  those releases together. Use a fresh random seed per release when unlinkability
  matters — the API defaults to `uuid4().hex`.

---

## 8. Offline NLP

The deterministic rule-based NER backbone (39 patterns across PERSON, ORG,
SITE, ASSET, PROJECT, CALLSIGN, GRID, COORD, CLASSIFICATION, EMAIL, IP, SERIAL)
has **zero dependencies** and always runs first, so output is reproducible on
any host.

An optional local statistical layer activates if a spaCy model is present in
the image:

```bash
# Add to the offline wheelhouse before building:
pip download spacy en_core_web_sm -d wheelhouse
# or point at a model directory:
export AETHERMASK_SPACY_MODEL=/opt/models/en_core_web_sm
```

Statistical spans are assigned priority 5 — below every rule — so enabling the
model can only *add* protection, never change an existing mapping. That keeps
`.ciphermap` files portable between a minimal appliance and a full image.
`spacy.load` is only ever given a local path or an installed package name; no
download code path exists in this module.

---

## 9. Performance

Vectorised Polars execution, measured on 2 vCPU:

| Workload | Mask | Restore |
|----------|------|---------|
| 420 rows × 17 cols | 0.09 s | 0.02 s |
| 200 000 rows × 5 cols | 1.5 s | 0.3 s |

Bijections are built over the **distinct domain** of each column and applied
with a single vectorised `replace_strict`, so cost scales with cardinality
rather than row count.

---

*AetherMask (CipherShift) v1.0 — all computation local, no external network
dependencies, AES-256-GCM / Argon2id / HMAC-SHA256.*

---

## 10. Data Studio GUI (v2.1)

### Stack

| Package | Version | Note |
|---------|--------:|------|
| React | 19.3 | concurrent rendering |
| Vite | 8.3 | Rolldown bundler; relative `base` for any mount point |
| Tailwind CSS | 4.3 | **CSS-first** — no `tailwind.config.js`, no PostCSS, no autoprefixer |
| Motion | 13.4 | the renamed, actively-developed successor to `framer-motion` |
| TanStack Table | 9.2 | atom-store rewrite |
| Recharts | 3.10 | local SVG rendering only |
| TypeScript | 7.0 | full strict mode, zero errors |
| lucide-react | 1.47 | tree-shaken inline SVG icons |

Build: `cd frontend && npm install && npm run build` (runs `tsc --noEmit`
first, then Vite). Output lands in `frontend/dist/` with **relative** asset
URLs, and FastAPI serves it via `AETHERMASK_STATIC_DIR`.

### Migration notes (v1 → v2)

These are the breaking changes that had to be handled; they are recorded here
because each one silently produces a broken build if missed.

* **`framer-motion` → `motion`.** Import from `motion/react`. The old package
  is incompatible with React 19 and is no longer actively developed.
* **Tailwind v4 is CSS-first.** `@tailwind base/components/utilities` is
  replaced by a single `@import "tailwindcss"`; the theme lives in an
  `@theme {}` block in `src/index.css`. `tailwind.config.js` and
  `postcss.config.js` were **deleted** — keeping them alongside
  `@tailwindcss/vite` breaks the build. Class-based dark mode now needs an
  explicit `@custom-variant dark`.
* **Never pair Tailwind `transition-*` utilities with Motion-animated
  properties** — the two systems fight over the same CSS property. Motion owns
  every animated property in this codebase.
* **TanStack Table v9 is a ground-up rewrite**: `useReactTable` → `useTable`,
  `getCoreRowModel()` → `createCoreRowModel()`, and row models + feature
  modules are registered *together* through `tableFeatures({...})` passed as
  the `features` option. Features are opt-in — `getVisibleCells()` does not
  exist until `columnVisibilityFeature` is registered.
* **Rollup 5 (via Vite 8)** types `manualChunks` as a function, not an object.
* **Vite 8 requires Node ≥ 20.19**; the Docker frontend stage uses `node:22`.

### Motion design language

Animation is meaning-bearing, never decorative. All variants are centralised in
`src/lib/motion.ts`:

| Variant | Meaning it encodes |
|---------|--------------------|
| `stageVariants` | Directional slide — forward through the pipeline reads L→R, back reads R→L, so the operator always knows which way they moved |
| `revealVariants` | Server-returned content settles downward: "this is new data" |
| `listVariants` | Staggered children convey list cardinality and lead the eye in reading order |
| `verdictVariants` | A spring *settle* used **only** for the isomorphism/restore verdict, so a result feels decisive |
| `layoutId` pills | The active-tab and active-profile indicators physically travel between options rather than popping |

**Accessibility.** The app is wrapped in `<MotionConfig reducedMotion="user">`,
which neutralises every transform/position animation for users who set
`prefers-reduced-motion` (WCAG 2.3.3) while leaving opacity crossfades. Nothing
spins, parallaxes or flashes; no animation repeats >3×/sec (WCAG 2.3.1).
`whileFocus` mirrors `whileHover` everywhere so keyboard users get identical
feedback, and all scale effects stay under 1.1×. Verified by rendering the full
app under Playwright's `reducedMotion: 'reduce'`.

**Bundle cost.** `LazyMotion` + the `m` component ship ~4.6 kB of animation
runtime instead of the ~34 kB full `motion` component. `strict` mode makes any
accidental use of heavyweight `<motion.*>` throw during development.

### Client-side air-gap enforcement

`src/lib/useEgressWatch.ts` patches `fetch` and `XMLHttpRequest.open` at module
scope. Any request that resolves to an origin other than the page's own is
**rejected**, not merely logged, and a `PerformanceObserver` passively catches
sub-resource loads (images, styles) that bypass both APIs. The ledger is shown
live in the header badge and itemised in the attestation drawer.

This is deliberately **independent of the server's self-report**: `/api/v1/attestation`
is what the backend claims, while the watchdog is what the browser actually
observed. `src/lib/api.ts` adds a second guard (`assertRelative`) that throws if
any code path ever tries to build a non-relative request URL.

### v2.1 workflow surfaces

Three additions close the gap between the API surface and what the GUI could
actually reach.

**Command palette (`Ctrl`/`Cmd` + `K`).** A fuzzy launcher over every action in
the app — stage navigation, run/reset, artifact and vault download, attestation.
Implemented against the WAI-ARIA combobox pattern: the text input keeps DOM
focus while the highlighted option is advertised through
`aria-activedescendant` (roving *virtual* focus, so screen readers announce each
option without focus actually moving), `Tab` is trapped while open, and focus is
restored to the invoking control on close. The active-row highlight is a Motion
`layoutId` shared element rather than an animated `background-position`.

**Dry-run preview.** Collapsible panel inside the transform stage that calls
`/api/v1/preview` — full split-screen diff, column ledger and parity charts for
the first *N* rows, producing **no vault and no downloadable artifact**. Lets an
operator tune the cover domain and numeric mode before committing to a sealed
run.

**Independent audit stage (stage 6).** Surfaces `/api/v1/verify` as a
first-class workflow: drop in an original, a sanitized artifact and a
`.ciphermap`, supply the passphrase, and the server **recomputes every aggregate
from the three raw files** — row counts, per-column cardinality, null counts,
numeric sums — rather than trusting the fidelity report the masking run emitted
about itself. The verdict banner, progress meter and filterable check list
(with an *only failures* toggle) make it usable as an acceptance gate. A
*Load from this session* shortcut wires the current run's three artifacts
straight in.

Both dialogs (attestation drawer, command palette) implement the full keyboard
contract — `Escape` to dismiss, focus trap while open, focus restored to the
invoking element — and toasts announce every terminal outcome, with errors
given `role="alert"` and made sticky rather than auto-dismissing.

### Verification

Two Playwright harnesses drive real browsers against the built bundle.

`flow.mjs` walks the full six-stage workflow and asserts **44 checks**: the
isomorphism banner reports 73/73, the parity table shows Σ|Δ| = 0, TanStack v9
sorting toggles `aria-sort`, the profile picker renders every profile the
catalogue advertises (asserted against a live `/profiles` fetch, never a
hard-coded count), the round-trip restores 420 rows exactly, `Ctrl-K` opens the
palette with a correct combobox contract, `Escape` closes both overlays and
restores focus, the app renders under forced reduced-motion, and — recorded
independently by the test's own request listener — **0 external network
requests** and 0 console errors.

`audit_e2e.mjs` adds **8 checks** that run a genuine masking pass and then feed
the resulting triple back through the audit stage, confirming the independent
recomputation agrees on every aggregate.

```
ALL 44 UI CHECKS PASSED          External requests: 0
ALL 8 AUDIT E2E CHECKS PASSED    42 of 42 recomputed checks agree
```
