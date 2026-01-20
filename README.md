# FIT Bootstrap

FIT Bootstrap is a core module of the FIT ecosystem, responsible for preparing and validating the operating system environment before executing FIT applications, including privilege escalation, system configuration, and security checks.

It is responsible for executing all required pre-flight checks, handling privilege separation, and performing OS-specific setup tasks that cannot be safely managed by the main application itself.

At the moment, FIT Bootstrap is used by:

- **fit-web** (scraper module)
- **fit** (bundled application)

In the future, it may be reused by additional FIT modules.

---

## Features

- Cross-platform support (macOS, Windows, Linux)
- Separation of **user phase** and **admin/root phase**
- Works both in:
  - development mode (Poetry)
  - bundled mode (PyInstaller)
- No graphical user interface (GUI)
- Controlled execution flow before launching the main application

---

## Responsibilities

FIT Bootstrap is responsible for:

### General
- Verifying system prerequisites
- Detecting execution context (dev vs bundle)
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

## Execution Modes

### Development mode

Used when running the application through Poetry.

```bash
poetry run python -m fit_bootstrap

