# PyInstaller onedir bundle: keeps startup faster than one-file for MediaPipe.
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

os.environ.setdefault("QT_API", "pyside6")

root = Path(SPECPATH)
# Legacy Solutions load model graphs and TFLite models by package path.
# Collect only those runtime assets; collect_all would bundle unused GenAI/tests/JAX.
datas = collect_data_files("mediapipe", includes=["modules/**"])
binaries = []
hiddenimports = [
    "mediapipe.python.solutions.hands",
    "mediapipe.python.solutions.selfie_segmentation",
    "mediapipe.python.solutions.pose",
    "mediapipe.python.solutions.drawing_utils",
    "mediapipe.python.solutions.drawing_styles",
    "pyvirtualcam",
]

assets = root / "assets"
if assets.is_dir():
    datas.append((str(assets), "assets"))

a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(root / "qt_runtime_hook.py")],
    excludes=["pytest", "IPython", "notebook"],
    noarchive=False,
    optimize=0,
)
# OpenCV's hook may collect an older VC runtime at the bundle root while
# PySide6 ships a newer one. Windows can load the older DLL first, causing
# QtWidgets to fail with "The specified procedure could not be found".
# Use PySide6's redistributables consistently for every collected copy.
runtime_dir = Path(sys.prefix) / "Lib" / "site-packages" / "PySide6"
runtime_names = {
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
}
for index, (destination, source, typecode) in enumerate(a.binaries):
    runtime_source = runtime_dir / Path(destination).name
    if Path(destination).name.lower() in runtime_names and runtime_source.is_file():
        a.binaries[index] = (destination, str(runtime_source), typecode)

# PyInstaller can mistakenly pick ICU 78 from the build environment's Poppler
# PATH. Qt expects the Windows ICU ABI (unversioned symbols), so do not bundle
# those unrelated Poppler DLLs over the Windows system ICU.
a.binaries = [
    item for item in a.binaries
    if Path(item[0]).name.lower() not in {"icuuc.dll", "icudt78.dll"}
]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HandEffectApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
bundle = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="HandEffectApp",
)
