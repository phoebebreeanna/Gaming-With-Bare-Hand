# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('assets', 'assets'),
    ('logic/data', 'logic/data'),
    ('logic/conf', 'logic/conf'),
    ('logic/chatbot/data', 'logic/chatbot/data'),
    ('logic/chatbot/chroma_db', 'logic/chatbot/chroma_db'),
    ('hockey_game', 'hockey_game'),
]
binaries = []
# pygame/gesture_pipeline are only reached via a dynamic on-disk import (re-exec
# of the frozen binary with --run-hockey / --run-pipeline), so PyInstaller's
# static analysis can't see them - list them explicitly.
hiddenimports = [
    'pygame', 'logic.gesture_pipeline',
    'tiktoken_ext.openai_public', 'tiktoken_ext',
]
for _pkg in (
    'numpy', 'cv2', 'mediapipe', 'scipy', 'sklearn',
    'torch', 'pygame', 'chromadb', 'llama_cpp',
    'llama_index', 'transformers', 'tokenizers', 'huggingface_hub',
    'sentence_transformers', 'certifi', 'openai', 'httpx', 'httpcore',
    'tiktoken',
):
    tmp_ret = collect_all(_pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['libiconv'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HandMouse',
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
    icon=['assets/logo/hand_gesture_icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HandMouse',
)
app = BUNDLE(
    coll,
    name='HandMouse.app',
    icon='assets/logo/hand_gesture_icon.icns',
    bundle_identifier='com.handmouse.app',
)
