import os
from pathlib import Path
import sys


root = Path(SPECPATH).resolve()
retoc_binary = Path(os.environ['RETOC_BINARY']).resolve()
app_name = os.environ.get('COLORFUL_RIVALS_APP_NAME', 'Colorful Rivals')

datas = [
    (str(root / name), '.')
    for name in ('asset-map.json', 'colors.json', 'empty.pak', 'settings.json')
]
datas.extend([
    (str(root / 'template'), 'template'),
    (str(root / 'assets'), 'assets'),
    (str(root / 'licenses'), 'licenses'),
    (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
])

analysis = Analysis(
    [str(root / 'app.py')],
    pathex=[str(root)],
    binaries=[(str(retoc_binary), 'retoc')],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name=app_name,
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
    icon=str(root / 'assets' / 'TXR.ico'),
)

if sys.platform == 'darwin':
    app = BUNDLE(
        executable,
        name=f'{app_name}.app',
        icon=str(root / 'assets' / 'TXR.ico'),
        bundle_identifier='io.github.covium.colorful-rivals',
    )
