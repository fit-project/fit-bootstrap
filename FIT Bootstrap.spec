# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = ['fit_common', 'fit_assets']
hiddenimports += collect_submodules('fit_common')
hiddenimports += collect_submodules('fit_assets')
hiddenimports += collect_submodules('fit_bootstrap')
hiddenimports += collect_submodules('mitmproxy')
hiddenimports += ['fit_bootstrap.macos.ui_askpass_dialog']
hiddenimports += ['fit_bootstrap.macos.askpass_dialog']
datas = collect_data_files('fit_assets')
datas += collect_data_files('mitmproxy')
datas += collect_data_files('fit_bootstrap', includes=['lang/*.json'])
datas += [('fit_bootstrap/macos/askpass.sh', 'fit_bootstrap/macos')]
datas += [('fit_bootstrap/mitmproxy_addons/fit_capture.py', 'fit_bootstrap/mitmproxy_addons')]


a = Analysis(
    ['main.py'],
    pathex=[],
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
    name='FIT Bootstrap',
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
    name='FIT Bootstrap',
)
app = BUNDLE(
    coll,
    name='FIT Bootstrap.app',
    icon=None,
    bundle_identifier=None,
)
