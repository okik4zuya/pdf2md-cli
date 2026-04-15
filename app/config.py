import os
import sys


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # app/ is one level inside the project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR     = get_base_dir()
POPPLER_PATH = os.path.join(BASE_DIR, "poppler", "Library", "bin")
TESSERACT_PATH = os.path.join(BASE_DIR, "tesseract", "tesseract.exe")
