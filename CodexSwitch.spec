# -*- mode: python ; coding: utf-8 -*-
import platform, sys
from pathlib import Path

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

a = Analysis(
    ["codex_switch_win.py"],
    pathex=[str(Path.cwd())],
    binaries=[
        ("assets/moonbridge.exe", "."),   # bundled proxy binary
    ],
    datas=[
        ("assets/icon.png", "."),         # tray icon
    ],
    hiddenimports=[
        "tkinter", "tkinter.ttk",
        "pystray", "PIL", "PIL.Image", "PIL.ImageDraw",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

if IS_MAC:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="CodexSwitch",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon="assets/icon.icns",
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=False,
        upx_exclude=[],
        name="CodexSwitch",
    )
    app = BUNDLE(
        coll,
        name="CodexSwitch.app",
        icon="assets/icon.icns",
        bundle_identifier="com.codexswitch.app",
        info_plist={
            "CFBundleName": "CodexSwitch",
            "CFBundleDisplayName": "CodexSwitch",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "NSHumanReadableCopyright": "CodexSwitch",
        },
    )
else:
    # Windows: single-file executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="CodexSwitch",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon="assets/icon.ico",
    )
