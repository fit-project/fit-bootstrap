# FIT Bootstrap

FIT Bootstrap is a core module of the FIT ecosystem, responsible for preparing and validating the operating system environment before executing FIT applications, including privilege escalation, system configuration, and security checks.
Version `1.0.0` targets macOS only.

It is responsible for executing all required pre-flight checks, handling privilege separation, and performing OS-specific setup tasks that cannot be safely managed by the main application itself.

At the moment, FIT Bootstrap is used by:

- **fit-web** (scraper module)
- **fit** (bundled application)

In the future, it may be reused by additional FIT modules.

---

## Features

- Cross-platform support (macOS, Windows, Linux)
- Windows and Linux support is planned for future releases.
- Separation of **user phase** and **admin/root phase**
- Works in development mode (Poetry)
- Optional local bundle testing via PyInstaller (`FIT Bootstrap.spec`)
- GUI is limited in development mode in this release to macOS admin/certificate prompt dialogs when required
- Controlled execution flow before launching the main application

---

## Responsibilities

FIT Bootstrap is responsible for:

### General
- Verifying system prerequisites
- Detecting execution context (development mode; local bundle testing only)
- Managing execution phases (user / admin)
- Aborting execution if mandatory conditions are not met

### macOS-specific
- Handling Gatekeeper and quarantine flags
- Requesting and validating administrator privileges
- Temporarily configuring system proxy
- Installing and removing the mitmproxy Certificate Authority
- Managing tcpdump permissions and execution

---

## Architecture Overview

FIT Bootstrap runs **before** the main FIT application and decides:

1. Whether the environment is valid
2. Whether elevated privileges are required
3. Which actions must be executed as root
4. When it is safe to launch the target application

The bootstrap process is fully deterministic and blocks execution if any mandatory step fails.

---

## Dependencies

Main dependencies are:

- **Python** >=3.12,<3.14
- **Poetry** (recommended for development)
- [`fit-common`](https://github.com/fit-project/fit-common)  – shared utility and core logic
- [`fit-assets`](https://github.com/fit-project/fit-assets)  – UI resources and assets

See `pyproject.toml` for full details.

### For local development and testing
```bash
pip install pyinstaller mitmproxy pyside6
```
`FIT Bootstrap.spec` is kept for local testing only. No production bundle is released in `v1.0.0`.
---

## Local checks (same as CI)

Run these commands before opening a PR, so failures are caught locally first.

### What each tool does
- `pytest`: runs automated tests (`unit`, `contract`, `integration` and `e2e` suites).
- `ruff`: checks code style and common static issues (lint).
- `mypy`: performs static type checking on annotated Python code.
- `bandit`: scans source code for common security anti-patterns.
- `pip-audit`: checks installed dependencies for known CVEs.

### 1) Base setup
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install . pytest ruff mypy "bandit[toml]" pip-audit
python -m pip install --upgrade "setuptools>=78.1.1"
```

### 2) Test suite
```bash
export QT_QPA_PLATFORM=offscreen

# unit tests
pytest -m unit -q tests

# contract tests
pytest -m contract -q tests

# integration tests
pytest -m integration -q tests

# end-to-end smoke tests
pytest -m e2e -q tests
```

### 3) Quality and security checks
```bash
ruff check fit_bootstrap tests
mypy fit_bootstrap
bandit -c pyproject.toml -r fit_bootstrap -q -ll -ii
PIPAPI_PYTHON_LOCATION="$(python -c 'import sys; print(sys.executable)')" \
  python -m pip_audit --progress-spinner off
```

Note: `pip-audit` may print a skip message for `fit-assets`, `fit-bootstrap` and `fit-common` because it is a local package and not published on PyPI.
Note: if `pip-audit` reports a `Flask` vulnerability in local development, it is usually a transitive dependency from a locally installed `mitmproxy`; this does not affect project CI because `mitmproxy` is not part of the CI dependency set for `v1.0.0`.

---

## Installation

``` bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install poetry
    poetry lock
    poetry install
    poetry run python main.py
```

---

## Contributing
1. Fork this repository.  
2. Create a new branch (`git checkout -b feat/my-feature`).  
3. Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).  
4. Submit a Pull Request describing your modification.
