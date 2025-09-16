
import os, json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QApplication, QColorDialog, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


from desktop import AppWindow

SETTINGS_FILE = os.path.join("data", "settings.json")


DEFAULTS = {
    "text":       "#FFFFFF",  
    "desktop_bg": "#1E1E1E",
    "taskbar_bg": "#333333",
    "start_bg":   "#444444",
    "window_bg":  "#2E2E2E",  
}

def load_colors_from_disk() -> dict:
    """Read colors from settings.json, merging with defaults."""
    os.makedirs("data", exist_ok=True)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved = data.get("colors", {})
            return {**DEFAULTS, **saved}
        except Exception:
            return DEFAULTS.copy()
    return DEFAULTS.copy()

def save_colors_to_disk(colors: dict) -> bool:
    os.makedirs("data", exist_ok=True)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"colors": colors}, f, indent=2)
        return True
    except Exception:
        return False

def set_live_colors(desktop, colors: dict) -> None:
    """Remember the currently applied colors on the desktop instance."""
    desktop.current_colors = {**DEFAULTS, **colors}  

def get_live_colors(desktop) -> dict:
    """Prefer the desktop's currently applied colors; fall back to disk; then defaults."""
    if hasattr(desktop, "current_colors") and isinstance(desktop.current_colors, dict):
        return {**DEFAULTS, **desktop.current_colors}
    return load_colors_from_disk()

def apply_colors_live(desktop, colors: dict) -> None:
    """
    Apply colors to the running OS (desktop + taskbar + start menu + open app windows),
    store them on the desktop, and push them into open app windows (like Text Editor).
    """
 
    set_live_colors(desktop, colors)

    
    desktop.central_widget.setStyleSheet(f"background-color: {colors['desktop_bg']};")
    desktop.taskbar.setStyleSheet(f"background-color: {colors['taskbar_bg']};")
    desktop.start_menu.setStyleSheet(f"background-color: {colors['start_bg']}; border-radius: 10px;")

   
    app = QApplication.instance()
    app.setStyleSheet(f"""
        QWidget {{ color: {colors['text']}; }}
        QPushButton {{ color: {colors['text']}; }}
        QLabel {{ color: {colors['text']}; }}
        QMenu {{ color: {colors['text']}; }}
    """)

   
    desktop.time_label.setStyleSheet(f"color: {colors['text']};")
    desktop.date_label.setStyleSheet(f"color: {colors['text']};")
    desktop.start_btn.setStyleSheet(f"color: {colors['text']};")

    
    for w in desktop.central_widget.findChildren(AppWindow):
        if hasattr(w, "apply_os_colors") and callable(getattr(w, "apply_os_colors")):
            w.apply_os_colors(colors)
        else:
            w.setStyleSheet(
                f"background-color: {colors['window_bg']}; "
                f"color: {colors['text']}; "
                f"border: 2px solid #555; border-radius:5px;"
            )
            if hasattr(w, "close_btn"):
                w.close_btn.setStyleSheet(f"background:#b33; color:{colors['text']}; border:none; border-radius:4px;")
            if hasattr(w, "min_btn"):
                w.min_btn.setStyleSheet(f"background:#666; color:{colors['text']}; border:none; border-radius:4px;")
        w.update()
        w.repaint()


class ColorRow(QWidget):
    """Row with label + swatch + 'Change' button."""
    def __init__(self, title: str, key: str, colors: dict):
        super().__init__()
        self.key = key
        self.colors = colors

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel(title)
        self.swatch = QLabel("  ")
        self.swatch.setFixedSize(48, 22)
        self.swatch.setStyleSheet(f"background-color: {self.colors[self.key]}; border: 1px solid #555;")
        self.btn = QPushButton("Change")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self.pick)

        row.addWidget(self.title_lbl)
        row.addStretch(1)
        row.addWidget(self.swatch)
        row.addWidget(self.btn)

    def pick(self):
        col = QColorDialog.getColor(
            QColor(self.colors[self.key]),
            parent=self,
            title=f"Pick {self.key} color"
        )
        if col.isValid():
            hexc = col.name()  
            self.colors[self.key] = hexc
            self.swatch.setStyleSheet(f"background-color: {hexc}; border: 1px solid #555;")


class SettingsWindow(AppWindow):
    """
    Settings app with live color controls:
      - Text Color (global)
      - Desktop Background
      - Taskbar Color
      - Start Menu Color
      - Window Background (for AppWindow & apps like Text Editor)
    Apply = live preview; Save = persist to data/settings.json
    """
    def __init__(self, parent=None, desktop=None):
        pm = QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_DesktopIcon).scaled(24, 24)
        super().__init__("Settings", width=460, height=480, icon_pixmap=pm, parent=parent, desktop=desktop)

        self.desktop_ref = desktop
        self.colors = get_live_colors(self.desktop_ref)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 35, 8, 8)
        root.setSpacing(10)

        title = QLabel("Customize Colors")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        root.addWidget(title)

        
        self.rows = [
            ColorRow("Text Color",         "text",       self.colors),
            ColorRow("Desktop Background", "desktop_bg", self.colors),
            ColorRow("Taskbar Color",      "taskbar_bg", self.colors),
            ColorRow("Start Menu Color",   "start_bg",   self.colors),
            ColorRow("Window Background",  "window_bg",  self.colors),
        ]
        for r in self.rows:
            root.addWidget(r)

        root.addStretch(1)

       
        btns = QHBoxLayout()
        self.apply_btn = QPushButton("Apply")
        self.save_btn  = QPushButton("Save as default")
        self.close_btn = QPushButton("Close")
        for b in (self.apply_btn, self.save_btn, self.close_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        btns.addWidget(self.apply_btn)
        btns.addWidget(self.save_btn)
        btns.addStretch(1)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

       
        self.apply_btn.clicked.connect(self.on_apply)
        self.save_btn.clicked.connect(self.on_save)
        self.close_btn.clicked.connect(self.close)

        
        self.on_apply()

    def on_apply(self):
        apply_colors_live(self.desktop_ref, self.colors)

    def on_save(self):
       
        set_live_colors(self.desktop_ref, self.colors)
        if save_colors_to_disk(self.desktop_ref.current_colors):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Settings", "Theme saved.")
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Settings", "Could not save theme. Check file permissions.")


def launch(parent, desktop):
    """Entry point used by desktop.py"""
    return SettingsWindow(parent=parent, desktop=desktop)
