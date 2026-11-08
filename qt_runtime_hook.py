"""Keep the bundled Qt and Shiboken directories on Windows' DLL search path."""

import os
import sys

if sys.platform == "win32" and hasattr(sys, "_MEIPASS"):
    _bundle_root = sys._MEIPASS
    _dll_dirs = [
        os.path.join(_bundle_root, "PySide6"),
        os.path.join(_bundle_root, "shiboken6"),
        _bundle_root,
    ]
    _dll_dir_handles = []
    for _dll_dir in _dll_dirs:
        if os.path.isdir(_dll_dir):
            _dll_dir_handles.append(os.add_dll_directory(_dll_dir))
    os.environ["PATH"] = os.pathsep.join(_dll_dirs + [os.environ.get("PATH", "")])
