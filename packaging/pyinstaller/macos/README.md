# macOS Bundle Build (PyInstaller)

This folder contains the macOS PyInstaller spec for `fit-bootstrap`.

## Prerequisites

- macOS host
- project virtual environment available at `.venv`
- dependencies installed

## Build `.app`

From repository root:

```bash
source .venv/bin/activate
pip install pyinstaller
FIT_BUILD_VERSION=1.0.0 .venv/bin/python -m PyInstaller packaging/pyinstaller/macos/fit-bootstrap.spec --noconfirm --clean
```

Output:

- `dist/FitBootstrap.app`

`FIT_BUILD_VERSION` is required by the spec and must be set explicitly.

## Build `.dmg`

From repository root:

```bash
./packaging/scripts/build_macos_dmg.sh dist/FitBootstrap.app 1.0.0 dist/dmg
```

Output:

- `dist/dmg/fit-bootstrap-portable-1.0.0-macos-<arch>.dmg`
