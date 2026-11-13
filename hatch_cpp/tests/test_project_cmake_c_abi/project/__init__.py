import os
import sys

if sys.platform == "win32":
    os.add_dll_directory(os.path.join(os.path.dirname(__file__), "lib"))
