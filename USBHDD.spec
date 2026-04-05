# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for USBHDD Secure Storage.
Builds a single-file executable for the current platform.

Usage:
    pyinstaller USBHDD.spec
"""

import sys

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Flask internals
        "flask",
        "flask.templating",
        "flask_wtf",
        "flask_wtf.csrf",
        "wtforms",
        "wtforms.validators",
        # Werkzeug
        "werkzeug",
        "werkzeug.security",
        "werkzeug.utils",
        # Cryptography
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat.primitives.asymmetric.rsa",
        "cryptography.hazmat.primitives.asymmetric.padding",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.primitives.serialization",
        "cryptography.hazmat.backends",
        "cryptography.hazmat.backends.openssl",
        "cryptography.x509",
        "cryptography.x509.oid",
        # Pillow
        "PIL",
        "PIL.Image",
        "PIL.ImageOps",
        # Gunicorn
        "gunicorn",
        "gunicorn.app.base",
        "gunicorn.workers.gthread",
        "gunicorn.glogging",
        # Standard library modules sometimes missed
        "sqlite3",
        "hashlib",
        "threading",
        "socket",
        "webbrowser",
        "email.mime.multipart",
        # Jinja2 / MarkupSafe
        "jinja2",
        "markupsafe",
        # blinker / click / itsdangerous
        "blinker",
        "click",
        "itsdangerous",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy packages
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "notebook",
        "pytest",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="USBHDD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX can break cryptography .so files – keep off
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # Keep console: shows URL + Ctrl+C works
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,    # None = current arch; CI overrides per platform
    codesign_identity=None,
    entitlements_file=None,
    # macOS .app bundle icon (optional, place USBHDD.icns next to spec)
    icon=None,
)

# macOS: also wrap in a .app bundle
if sys.platform == "darwin":
    app_bundle = BUNDLE(
        exe,
        name="USBHDD.app",
        icon=None,
        bundle_identifier="com.usbhdd.securestorage",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
        },
    )
