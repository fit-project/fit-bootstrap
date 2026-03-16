"""Windows updater helper script renderer."""

from __future__ import annotations

from pathlib import Path


def render_windows_helper_script(
    *,
    manifest: dict[str, object],
    script_path: Path,
    manifest_path: Path,
    helper_dir: Path,
) -> str:
    _ = (manifest, script_path, manifest_path, helper_dir)
    return """@echo off
echo Windows external helper is not implemented yet 1>&2
exit /b 1
"""
