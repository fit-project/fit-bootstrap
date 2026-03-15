# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

SPEC_DIR = Path(globals().get("SPECPATH", Path.cwd())).resolve()
REPO_ROOT = SPEC_DIR.parent.parent.parent


version_value = os.environ.get("FIT_BUILD_VERSION")
if not version_value:
    raise RuntimeError(
        "FIT_BUILD_VERSION is required (example: FIT_BUILD_VERSION=1.0.0)."
    )
version_file_path = REPO_ROOT / "_version.py"
version_file_path.write_text(f'__version__ = "{version_value}"\n', encoding="utf-8")

hiddenimports = ['fit_common', 'fit_assets']
hiddenimports += collect_submodules('fit_common')
hiddenimports += collect_submodules('fit_assets')
hiddenimports += collect_submodules('fit_bootstrap')
hiddenimports += collect_submodules('mitmproxy')
hiddenimports += ['fit_bootstrap.macos.ui_askpass_dialog']
hiddenimports += ['fit_bootstrap.macos.askpass_dialog']
datas = collect_data_files('fit_assets')
datas += collect_data_files('fit_common', includes=['lang/*.json'])
datas += collect_data_files('mitmproxy')
datas += [
    (str(path), 'fit_bootstrap/lang')
    for path in sorted((REPO_ROOT / 'fit_bootstrap' / 'lang').glob('*.json'))
]
datas += [(str(REPO_ROOT / 'fit_bootstrap/macos/askpass.sh'), 'fit_bootstrap/macos')]
datas += collect_data_files("fit_bootstrap", includes=["fit_screen_recorder_binaries/macos_arm64/fit-screen-recoder"])
datas += [
    (
        str(REPO_ROOT / 'fit_bootstrap/mitmproxy_addons/fit_capture.py'),
        'fit_bootstrap/mitmproxy_addons',
    )
]
datas.append((str(version_file_path), "."))


a = Analysis(
    [str(REPO_ROOT / "main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='fit-bootstrap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='fit-bootstrap',
)
app = BUNDLE(
    coll,
    name='FitBootstrap.app',
    icon=None,
    bundle_identifier="org.fit-project.fit.bootstrap",
    version=version_value,
)

if version_file_path.exists():
    try:
        version_file_path.unlink()
    except OSError:
        pass
