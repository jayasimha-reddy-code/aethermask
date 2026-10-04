# Contributing to AetherMask

Thank you for your interest in contributing to AetherMask! We welcome contributions from engineers, cryptographers, data architects, and security researchers.

Because AetherMask is designed for high-assurance, air-gapped deployments, all contributions must strictly adhere to our architectural standards, typing requirements, and test suites.

---

## 1. Code of Conduct

All contributors are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat all members of the community with professionalism and respect.

---

## 2. Development Setup

### Prerequisites
- **Python**: 3.10, 3.11, 3.12, or 3.13
- **Node.js**: >= 20.19 (Node 22 recommended)
- **Docker** (optional, for air-gapped container testing)

### Setup Steps
1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/aethermask.git
   cd aethermask
   ```
2. Create and activate a clean virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install Python dependencies and development tooling:
   ```bash
   pip install -e ".[dev,test]"
   ```
4. Build the offline frontend SPA:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

---

## 3. Branching & Commit Conventions

### Branch Naming
Create focused branches branching off `main`:
- `feat/feature-name` for new capabilities
- `fix/bug-description` for bug fixes
- `refactor/scope-cleanup` for refactoring without behavior change
- `docs/doc-update` for documentation improvements
- `perf/optimization` for performance improvements

### Conventional Commits
All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification:

```text
<type>(<scope>): <short imperative summary>

[optional longer description explaining why and what changed]

[optional issue reference, e.g. Closes #12]
```

#### Allowed Types:
- `feat`: A new feature or capability.
- `fix`: A bug fix.
- `docs`: Documentation-only changes.
- `refactor`: Code change that neither fixes a bug nor adds a feature.
- `perf`: A code change that improves performance.
- `test`: Adding or correcting tests.
- `chore`: Maintenance tasks, dependency updates, build tooling.

---

## 4. Quality & Testing Standards

Before submitting a pull request, all test suites and linters must pass locally.

### Linting & Formatting
```bash
# Python linting and formatting validation
ruff check core api cli tests
ruff format --check core api cli tests

# Frontend TypeScript validation
cd frontend && npm test && cd ..
```

### Test Execution
```bash
# Run pytest verification suite (all 10 top-level modules, 140 assertions)
pytest

# Run standalone engine verification
python tests/test_full_suite.py

# Run standalone API integration suite
python tests/test_api.py
```

### Air-Gap Rules for Contributors
- **Never introduce dynamic remote dependencies**: No remote CDN links, no Google Fonts, no external model downloads during runtime.
- **Strict Network Isolation**: Any code added to `core` must execute entirely on local CPU and memory.
- **Determinism**: Transformations must be strictly deterministic given a `(domain_profile, seed)` pair. Never rely on unseeded RNG, host-dependent dictionary ordering, or non-deterministic hash iteration.

---

## 5. Pull Request Guidelines

1. **Keep PRs atomic:** Address one feature, fix, or improvement per pull request.
2. **Add tests:** Every new feature or bug fix must include corresponding automated tests in `tests/test_full_suite.py` or `tests/test_api.py`.
3. **Verify Documentation:** Update `README.md`, docstrings, or schemas if configuration options or API contracts change.
4. **Clean Git History:** Rebase onto `main` before submitting; avoid noisy merge commits.
