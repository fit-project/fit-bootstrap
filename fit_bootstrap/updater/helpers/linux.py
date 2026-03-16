"""Linux updater helper script renderer."""

from __future__ import annotations

from pathlib import Path


def render_linux_helper_script(
    *,
    manifest: dict[str, object],
    script_path: Path,
    manifest_path: Path,
    helper_dir: Path,
) -> str:
    _ = (manifest, script_path, manifest_path, helper_dir)
    return """#!/bin/sh
set -eu
echo "Linux external helper is not implemented yet" >&2
exit 1
"""
