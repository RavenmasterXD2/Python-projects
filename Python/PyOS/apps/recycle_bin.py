
import os, json, shutil, uuid, time
from datetime import datetime

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QStyle
)

from desktop import AppWindow

TRASH_DIR = os.path.join("data", "trash")
ROOT_DIR  = os.path.join("data", "userfiles")


def ensure_dirs():
    os.makedirs(TRASH_DIR, exist_ok=True)
    os.makedirs(ROOT_DIR, exist_ok=True)


def trash_items():
    """Yield dicts for each trashed entry (read metadata.json)."""
    ensure_dirs()
    for entry in os.listdir(TRASH_DIR):
        tpath = os.path.join(TRASH_DIR, entry)
        if not os.path.isdir(tpath):
            continue
        meta_path = os.path.join(tpath, "metadata.json")
        if not os.path.exists(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["_trash_path"] = tpath
            yield meta
        except Exception:
            continue


def human_bytes(n):
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def path_size(path):
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except Exception:
            return 0
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        for fname in files:
            try:
                total += os.path.getsize(os.path.join(root, fname))
            except Exception:
                pass
    return total


def safe_within_root(path):
    root = os.path.abspath(ROOT_DIR)
    p = os.path.abspath(path)
    return os.path.commonpath([root, p]) == root


class RecycleBinWindow(AppWindow):
    """
    Recycle Bin with Restore, Delete Selected, Empty Bin.
    Shows Name, Original Path, Deleted At, Size.
    """
    def __init__(self, parent=None, desktop=None):
        pm = QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_TrashIcon).scaled(24, 24)
        super().__init__("Recycle Bin", width=720, height=480, icon_pixmap=pm, parent=parent, desktop=desktop)

        ensure_dirs()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 35, 8, 8)
        root.setSpacing(8)

       
        bar = QHBoxLayout()
        self.btn_restore = QPushButton("Restore")
        self.btn_delete  = QPushButton("Delete Selected")
        self.btn_empty   = QPushButton("Empty Bin")
        self.btn_refresh = QPushButton("Refresh")

        for b in (self.btn_restore, self.btn_delete, self.btn_empty, self.btn_refresh):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            bar.addWidget(b)
        bar.addStretch(1)
        root.addLayout(bar)

       
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        root.addWidget(self.list, 1)

       
        self.status = QLabel("")
        root.addWidget(self.status)

       
        self.btn_refresh.clicked.connect(self.load_items)
        self.btn_empty.clicked.connect(self.empty_bin)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_restore.clicked.connect(self.restore_selected)
        self.list.itemDoubleClicked.connect(lambda *_: self.restore_selected())

       
        QShortcut(QKeySequence("Delete"), self, activated=self.delete_selected)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.load_items)

       
        if hasattr(desktop, "current_colors"):
            self.apply_os_colors(desktop.current_colors)

       
        self.load_items()

    def apply_os_colors(self, colors: dict):
        text = colors.get("text", "#FFFFFF")
        window_bg = colors.get("window_bg", "#2E2E2E")
        self.setStyleSheet(
            f"background-color: {window_bg}; color: {text}; "
            f"border: 2px solid #555; border-radius: 5px;"
        )
        if hasattr(self, "close_btn"):
            self.close_btn.setStyleSheet(f"background:#b33; color:{text}; border:none; border-radius:4px;")
        if hasattr(self, "min_btn"):
            self.min_btn.setStyleSheet(f"background:#666; color:{text}; border:none; border-radius:4px;")
        self.status.setStyleSheet(f"color:{text};")
        self.update(); self.repaint()

    def load_items(self):
        self.list.clear()
        count = 0
        total_bytes = 0
        for meta in sorted(trash_items(), key=lambda m: m.get("deleted_at", 0), reverse=True):
            tdir = meta["_trash_path"]
            data_path = os.path.join(tdir, meta["stored_name"])
            size = path_size(data_path)
            total_bytes += size

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, meta)  
            deleted_str = datetime.fromtimestamp(meta.get("deleted_at", time.time())).strftime("%Y-%m-%d %H:%M")
            item.setText(
                f"{meta.get('name','(unknown)')}\n"
                f"from: {meta.get('original_path','?')}\n"
                f"deleted: {deleted_str}   size: {human_bytes(size)}"
            )
            self.list.addItem(item)
            count += 1

        self.status.setText(f"{count} item(s) - {human_bytes(total_bytes)} total")

    def selected_metas(self):
        metas = []
        for item in self.list.selectedItems():
            meta = item.data(Qt.ItemDataRole.UserRole)
            if meta: metas.append(meta)
        return metas

    def delete_selected(self):
        metas = self.selected_metas()
        if not metas:
            return
        resp = QMessageBox.question(
            self, "Delete Permanently",
            f"Permanently delete {len(metas)} item(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        for meta in metas:
            tdir = meta.get("_trash_path")
            try:
                shutil.rmtree(tdir, ignore_errors=True)
            except Exception:
                pass
        self.load_items()

    def empty_bin(self):
        resp = QMessageBox.question(
            self, "Empty Bin",
            "Delete ALL items permanently?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        for item in list(trash_items()):
            try:
                shutil.rmtree(item["_trash_path"], ignore_errors=True)
            except Exception:
                pass
        self.load_items()

    def restore_selected(self):
        metas = self.selected_metas()
        if not metas:
            return
        restored = 0
        for meta in metas:
            tdir = meta.get("_trash_path")
            orig = meta.get("original_path")
            stored_name = meta.get("stored_name")
            is_dir = meta.get("is_dir", False)
            data_path = os.path.join(tdir, stored_name)

            
            if not (orig and safe_within_root(orig)):
                continue

            dest = orig
            
            if os.path.exists(dest):
                base = os.path.basename(dest)
                parent = os.path.dirname(dest)
                stem, ext = os.path.splitext(base)
                i = 1
                while True:
                    candidate = os.path.join(parent, f"{stem} (restored {i}){ext}")
                    if not os.path.exists(candidate):
                        dest = candidate
                        break
                    i += 1

            try:
               
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(data_path, dest)
               
                shutil.rmtree(tdir, ignore_errors=True)
                restored += 1
            except Exception as e:
                print("Restore failed:", e)

        if restored:
            QMessageBox.information(self, "Recycle Bin", f"Restored {restored} item(s).")
        self.load_items()


def launch(parent, desktop):
    return RecycleBinWindow(parent=parent, desktop=desktop)
