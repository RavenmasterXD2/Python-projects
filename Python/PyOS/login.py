
import os
from PyQt6.QtCore import QLibraryInfo, Qt, QCoreApplication


QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)


try:
    binaries_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.BinariesPath)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(binaries_path)
except Exception as e:
    print("add_dll_directory failed:", e)


try:
    resources_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.ResourcesPath)
    translations   = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", resources_path)
    os.environ.setdefault("QTWEBENGINE_PROCESS_PATH", os.path.join(binaries_path, "QtWebEngineProcess.exe"))
    os.environ.setdefault("QTWEBENGINE_TRANSLATIONS_PATH", translations)
except Exception as e:
    print("env setup failed:", e)


os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

import json
import time
from desktop import Desktop
from PyQt6.QtWidgets import QApplication
import sys



USERS_FILE = "data/users.json"

def run_login():
    print("PyOS Login")
    
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    
    username = input("Username: ")
    password = input("Password: ")
    
    for user in users:
        if user["username"] == username and user["password"] == password:
            print("Login successful!")
            time.sleep(1)
            
            
            app = QApplication(sys.argv)
            app.setStyleSheet("""
                QWidget { color: #ffffff; }
                QPushButton { color: #ffffff; }
                QLabel { color: #ffffff; }
                QMenu { color: #ffffff; }
            """)

            desktop = Desktop(user, fullscreen=True)  
            sys.exit(app.exec())
            return

    print("Invalid credentials. Try again.")
    run_login()
