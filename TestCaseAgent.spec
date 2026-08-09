# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置:TestCaseAgent 桌面应用(Windows exe / macOS app)。

用法:
    pyinstaller TestCaseAgent.spec --noconfirm --clean
产物:
    Windows -> dist/TestCaseAgent/TestCaseAgent.exe
    macOS   -> dist/TestCaseAgent.app
"""

from PyInstaller.utils.hooks import collect_data_files

import os
import sys

block_cipher = None

# imageio-ffmpeg 的 ffmpeg 二进制(PyInstaller hook 若缺失则手动收集)
datas = []
try:
    datas += collect_data_files("imageio_ffmpeg")
except Exception:  # noqa: BLE001
    pass

# 显式绑定 Python 自带的 OpenSSL DLL(UPX 压缩会破坏导出表导致 _ssl 加载失败)
binaries = []
_py_dlls = os.path.join(sys.base_prefix, "DLLs")
for _dll in ("libcrypto-3-x64.dll", "libssl-3-x64.dll"):
    _p = os.path.join(_py_dlls, _dll)
    if os.path.exists(_p):
        binaries.append((_p, "."))

a = Analysis(
    ["run_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TestCaseAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # 关键:UPX 会破坏 OpenSSL DLL
    console=False,                 # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TestCaseAgent",
)

# macOS 下额外生成 .app 包
if "darwin" in __import__("sys").platform:
    app = BUNDLE(
        coll,
        name="TestCaseAgent.app",
        icon="assets/icon.icns",
        bundle_identifier="com.testcaseagent.app",
    )
