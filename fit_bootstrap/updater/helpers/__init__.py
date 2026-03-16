"""OS-specific updater helper renderers."""

from __future__ import annotations

from pathlib import Path

from .linux import render_linux_helper_script
from .macos import render_macos_helper_script
from .windows import render_windows_helper_script


def render_helper_script(
    *,
    platform: str,
    manifest: dict[str, object],
    script_path: Path,
    manifest_path: Path,
    helper_dir: Path,
) -> str:
    if platform == "macos":
        return render_macos_helper_script(
            manifest=manifest,
            script_path=script_path,
            manifest_path=manifest_path,
            helper_dir=helper_dir,
        )
    if platform == "lin":
        return render_linux_helper_script(
            manifest=manifest,
            script_path=script_path,
            manifest_path=manifest_path,
            helper_dir=helper_dir,
        )
    if platform == "win":
        return render_windows_helper_script(
            manifest=manifest,
            script_path=script_path,
            manifest_path=manifest_path,
            helper_dir=helper_dir,
        )
    raise RuntimeError(f"unsupported platform for helper rendering: {platform}")


__all__ = ["render_helper_script", "render_macos_helper_script"]
