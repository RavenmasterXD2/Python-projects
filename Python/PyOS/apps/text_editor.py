
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QApplication, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut

from desktop import AppWindow

DEFAULT_SAVE_DIR = os.path.join("data", "userfiles")


class TextEditorWindow(AppWindow):
    """
    Notepad-style editor:
      - New / Open / Save / Save As
      - Ctrl+N / Ctrl+O / Ctrl+S shortcuts
      - Applies OS theme via apply_os_colors(colors)
    """
    def __init__(self, parent=None, desktop=None):
       
        style = QApplication.instance().style()
        pm = style.standardPixmap(QStyle.StandardPixmap.SP_FileIcon).scaled(24, 24)
        super().__init__(title="Text Editor", width=700, height=500,
                         icon_pixmap=pm, parent=parent, desktop=desktop)

       
        self.file_path = None
        self._dirty = False

        
        os.makedirs(DEFAULT_SAVE_DIR, exist_ok=True)

       
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 35, 8, 8)   
        root.setSpacing(8)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_open = QPushButton("Open")
        self.btn_save = QPushButton("Save")
        self.btn_save_as = QPushButton("Save As")
        for b in (self.btn_new, self.btn_open, self.btn_save, self.btn_save_as):
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_open)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_save_as)
        toolbar.addStretch(1)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._mark_dirty)

        
        self.editor.setStyleSheet("""
            background-color: #2E2E2E;
            color: #FFFFFF;
            font-family: Consolas, monospace;
            font-size: 12pt;
            selection-background-color: #264f78;
            selection-color: #ffffff;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 6px;
        """)

        root.addLayout(toolbar)
        root.addWidget(self.editor, 1)

       
        self.btn_new.clicked.connect(self.new_file)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save_as.clicked.connect(self.save_file_as)

        
        QShortcut(QKeySequence.StandardKey.New, self, activated=self.new_file)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.open_file)
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save_file)

        self._refresh_title()

        
        if hasattr(desktop, "current_colors") and isinstance(desktop.current_colors, dict):
            self.apply_os_colors(desktop.current_colors)

    
    def apply_os_colors(self, colors: dict):
        """Called by Settings to sync with OS theme."""
        
        self.setStyleSheet(
            f"background-color: {colors.get('window_bg', '#2E2E2E')}; "
            f"color: {colors.get('text', '#FFFFFF')}; "
            f"border: 2px solid #555; border-radius:5px;"
        )
       
        self.editor.setStyleSheet(f"""
            background-color: {colors.get('window_bg', '#2E2E2E')};
            color: {colors.get('text', '#FFFFFF')};
            font-family: Consolas, monospace;
            font-size: 12pt;
            selection-background-color: #264f78;
            selection-color: #ffffff;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 6px;
        """)
       
        if hasattr(self, "close_btn"):
            self.close_btn.setStyleSheet(f"background:#b33; color:{colors.get('text', '#FFFFFF')}; border:none; border-radius:4px;")
        if hasattr(self, "min_btn"):
            self.min_btn.setStyleSheet(f"background:#666; color:{colors.get('text', '#FFFFFF')}; border:none; border-radius:4px;")
        self.update()
        self.repaint()

   
    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self._refresh_title()

    def _refresh_title(self):
        name = self.file_path if self.file_path else "Untitled"
        if self._dirty:
            name += " *"
        self.setWindowTitle(f"Text Editor - {name}")

    def _maybe_prompt_save(self) -> bool:
        if not self._dirty:
            return True
        resp = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Save them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        if resp == QMessageBox.StandardButton.Yes:
            return self.save_file()
        if resp == QMessageBox.StandardButton.No:
            return True
        return False  

   
    def new_file(self):
        if not self._maybe_prompt_save():
            return
        self.editor.clear()
        self.file_path = None
        self._dirty = False
        self._refresh_title()

    def open_file(self):
        if not self._maybe_prompt_save():
            return
        start_dir = DEFAULT_SAVE_DIR if os.path.isdir(DEFAULT_SAVE_DIR) else "."
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Text File", start_dir, "Text Files (*.txt);;All Files (*.*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.file_path = path
            self._dirty = False
            self._refresh_title()
        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))

    def save_file(self):
        if not self.file_path:
            return self.save_file_as()
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self._dirty = False
            self._refresh_title()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            return False

    def save_file_as(self):
        start_dir = DEFAULT_SAVE_DIR if os.path.isdir(DEFAULT_SAVE_DIR) else "."
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", os.path.join(start_dir, "document.txt"),
            "Text Files (*.txt);;All Files (*.*)"
        )
        if not path:
            return False
        self.file_path = path
        return self.save_file()


def launch(parent, desktop):
    """Entry point called from desktop.py to open the text editor."""
    return TextEditorWindow(parent=parent, desktop=desktop)
