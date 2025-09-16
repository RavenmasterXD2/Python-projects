
import os, sys


import PyQt6, os
_pyqt6_dir = os.path.dirname(PyQt6.__file__)
_qt6_dir   = os.path.join(_pyqt6_dir, "Qt6")
_qt_bin    = os.path.join(_qt6_dir, "bin")
_qt_res    = os.path.join(_qt6_dir, "resources")
_qt_trn    = os.path.join(_qt6_dir, "translations")

if hasattr(os, "add_dll_directory") and os.path.isdir(_qt_bin):
    os.add_dll_directory(_qt_bin)

if _qt_bin:
    os.environ.setdefault("QTWEBENGINE_PROCESS_PATH", os.path.join(_qt_bin, "QtWebEngineProcess.exe"))
if _qt_res:
    os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", _qt_res)
if _qt_trn:
    os.environ.setdefault("QTWEBENGINE_TRANSLATIONS_PATH", _qt_trn)


os.environ.setdefault("QT_OPENGL", "software")        
os.environ.setdefault("QT_ANGLE_PLATFORM", "warp")    
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")   


_chromium_flags = [
    "--disable-gpu",
    "--disable-gpu-compositing",
    "--in-process-gpu",              
    "--use-angle=swiftshader",       
    "--use-gl=angle",
    "--disable-features=Vulkan,UseSkiaRenderer", 
    "--enable-webgl=false",
    "--disable-webgl",
    "--disable-accelerated-2d-canvas",
    "--disable-logging",
    "--log-level=3",
]

existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
if existing:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = existing + " " + " ".join(_chromium_flags)
else:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(_chromium_flags)


from PyQt6.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)



from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)


try:
    from PyQt6.QtWebEngineCore import QtWebEngine, QWebEngineSettings
    QtWebEngine.initialize()
   
    gs = QWebEngineSettings.globalSettings()
    gs.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, False)
    gs.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, False)
   
    gs.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
    print("QtWebEngine.initialize() done")
except Exception as e:
    print("QtWebEngine.initialize() failed:", e)


print("Qt bin added:", 'QTWEBENGINE_PROCESS_PATH' in os.environ, os.environ.get('QTWEBENGINE_PROCESS_PATH', ''))

import json


USERS_FILE = "data/users.json"
FILES_FILE = "data/files.json"

def is_installed():
    return os.path.exists(USERS_FILE) and os.path.exists(FILES_FILE)

if __name__ == "__main__":
    if not is_installed():
        print("Launching Installer...")
        import installer
        installer.run_installer()
    else:
        print("Launching Login...")
        import login
        login.run_login()
