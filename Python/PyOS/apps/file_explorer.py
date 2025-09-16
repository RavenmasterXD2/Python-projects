
import os
import shutil
import json, uuid, time   

from PyQt6.QtCore import Qt, QDir, QModelIndex, QSize
from PyQt6.QtGui import QKeySequence, QShortcut, QFileSystemModel
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QListView, QLineEdit, QPushButton,
    QLabel, QMessageBox, QInputDialog, QStyle
)


from desktop import AppWindow


ROOT_DIR = os.path.join("data", "userfiles")
TRASH_DIR = os.path.join("data", "trash")

def ensure_trash():
    os.makedirs(TRASH_DIR, exist_ok=True)

def move_to_trash(path: str):
    """
    Move a file/dir into data/trash/<uuid> with metadata.json:
    { original_path, name, stored_name, is_dir, deleted_at }
    """
    ensure_trash()
    tid = str(uuid.uuid4())
    tdir = os.path.join(TRASH_DIR, tid)
    os.makedirs(tdir, exist_ok=True)

    name = os.path.basename(path)
    is_dir = os.path.isdir(path)
    stored_name = name  

   
    meta = {
        "original_path": os.path.abspath(path),
        "name": name,
        "stored_name": stored_name,
        "is_dir": is_dir,
        "deleted_at": time.time(),
    }
    with open(os.path.join(tdir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

   
    dest = os.path.join(tdir, stored_name)
    shutil.move(path, dest)


def ensure_root():
    os.makedirs(ROOT_DIR, exist_ok=True)
    return os.path.abspath(ROOT_DIR)


def within_root(path: str) -> bool:
    root = os.path.abspath(ROOT_DIR)
    p = os.path.abspath(path)
    return os.path.commonpath([root, p]) == root


def is_text_like(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".txt", ".md", ".py", ".json", ".csv", ".log", ".ini", ".cfg", ".yaml", ".yml"}


class FileExplorerWindow(AppWindow):
    """
    A safe, themed file explorer sandboxed to data/userfiles.
    Left: directory tree, Right: file list, Toolbar + Address bar.
    """
    def __init__(self, parent=None, desktop=None):
        style = QApplication.instance().style()
        pm = style.standardPixmap(QStyle.StandardPixmap.SP_ComputerIcon).scaled(24, 24)
        super().__init__(title="File Explorer", width=920, height=560, icon_pixmap=pm, parent=parent, desktop=desktop)

        ensure_root()

      
        self.history: list[str] = []
        self.history_index: int = -1
        self.current_path = os.path.abspath(ROOT_DIR)

     
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 35, 8, 8)
        root.setSpacing(6)

      
        tb = QHBoxLayout()
        self.btn_back    = self._tb_button(QStyle.StandardPixmap.SP_ArrowBack, "Back")
        self.btn_forward = self._tb_button(QStyle.StandardPixmap.SP_ArrowForward, "Forward")
        self.btn_up      = self._tb_button(QStyle.StandardPixmap.SP_ArrowUp, "Up")
        self.btn_new     = self._tb_button(QStyle.StandardPixmap.SP_FileDialogNewFolder, "New Folder")
        self.btn_rename  = self._tb_button(QStyle.StandardPixmap.SP_FileDialogDetailedView, "Rename")
        self.btn_delete  = self._tb_button(QStyle.StandardPixmap.SP_TrashIcon, "Delete")
        self.btn_refresh = self._tb_button(QStyle.StandardPixmap.SP_BrowserReload, "Refresh")

        for b in (self.btn_back, self.btn_forward, self.btn_up, self.btn_new, self.btn_rename, self.btn_delete, self.btn_refresh):
            tb.addWidget(b)

        tb.addSpacing(10)

        self.address = QLineEdit(self.current_path)
        self.address.setClearButtonEnabled(True)
        self.address.setPlaceholderText("Path inside data/userfiles …")
        tb.addWidget(self.address, 1)

        self.btn_go = QPushButton("Go")
        self.btn_go.setFixedHeight(28)
        tb.addWidget(self.btn_go)

        root.addLayout(tb)

        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(self.splitter, 1)

        
        self.dir_model = QFileSystemModel(self)
        self.dir_model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        self.dir_model.setRootPath(self.current_path)

        self.tree = QTreeView()
        self.tree.setModel(self.dir_model)
        self.tree.setRootIndex(self.dir_model.index(self.current_path))
        self.tree.setHeaderHidden(True)
        a = self.tree
        a.setAnimated(True)
        a.setIndentation(18)
        a.setSortingEnabled(True)
        a.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        
        self.file_model = QFileSystemModel(self)
        self.file_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.file_model.setRootPath(self.current_path)

        self.list = QListView()
        self.list.setModel(self.file_model)
        self.list.setRootIndex(self.file_model.index(self.current_path))
        self.list.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.list.setUniformItemSizes(True)

        self.splitter.addWidget(self.tree)
        self.splitter.addWidget(self.list)
        self.splitter.setSizes([240, 680])

        
        self.status = QLabel("")
        root.addWidget(self.status)

       
        self.btn_back.clicked.connect(self.nav_back)
        self.btn_forward.clicked.connect(self.nav_forward)
        self.btn_up.clicked.connect(self.nav_up)
        self.btn_new.clicked.connect(self.new_folder)
        self.btn_rename.clicked.connect(self.rename_selected)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_go.clicked.connect(self.on_go)

        self.address.returnPressed.connect(self.on_go)

        self.tree.selectionModel().selectionChanged.connect(self.on_tree_selection)
        self.list.doubleClicked.connect(self.on_list_double_clicked)

        
        QShortcut(QKeySequence("Alt+Left"),   self, activated=self.nav_back)
        QShortcut(QKeySequence("Alt+Right"),  self, activated=self.nav_forward)
        QShortcut(QKeySequence("Alt+Up"),     self, activated=self.nav_up)
        QShortcut(QKeySequence("Delete"),     self, activated=self.delete_selected)
        QShortcut(QKeySequence("F2"),         self, activated=self.rename_selected)
        QShortcut(QKeySequence("F5"),         self, activated=self.refresh)
        QShortcut(QKeySequence("Ctrl+N"),     self, activated=self.new_folder)

        
        self.navigate(self.current_path, push_history=True)
        self.update_buttons()
        self.update_status()

        
        if hasattr(desktop, "current_colors"):
            self.apply_os_colors(desktop.current_colors)

    
    def _tb_button(self, std_icon: QStyle.StandardPixmap, fallback_text: str) -> QPushButton:
        btn = QPushButton()
        btn.setFlat(True)
        btn.setFixedSize(32, 28)
        icon = QApplication.instance().style().standardIcon(std_icon)
        if not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(18, 18))
        else:
            btn.setText(fallback_text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    
    def navigate(self, path: str, push_history: bool = True):
        path = os.path.abspath(path)
        if not within_root(path):
            QMessageBox.warning(self, "Blocked", "Navigation outside data/userfiles is not allowed.")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Not found", f"Path does not exist:\n{path}")
            return

        self.current_path = path
        self.address.setText(self.current_path)

        
        self.tree.setCurrentIndex(self.dir_model.index(self.current_path))
        self.tree.expand(self.dir_model.index(self.current_path))
        self.list.setRootIndex(self.file_model.index(self.current_path))

        
        if push_history:
            self.history = self.history[: self.history_index + 1]
            self.history.append(self.current_path)
            self.history_index = len(self.history) - 1

        self.update_buttons()
        self.update_status()

    def update_buttons(self):
        self.btn_back.setEnabled(self.history_index > 0)
        self.btn_forward.setEnabled(self.history_index >= 0 and self.history_index < len(self.history) - 1)
        self.btn_up.setEnabled(within_root(os.path.dirname(self.current_path)) and self.current_path != ensure_root())

    def update_status(self):
        try:
            count = len(os.listdir(self.current_path))
        except Exception:
            count = 0
        self.status.setText(f"{self.current_path}   —   {count} item(s)")

    def nav_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.navigate(self.history[self.history_index], push_history=False)

    def nav_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.navigate(self.history[self.history_index], push_history=False)

    def nav_up(self):
        parent_dir = os.path.dirname(self.current_path)
        if within_root(parent_dir):
            self.navigate(parent_dir)

    def on_go(self):
        raw = self.address.text().strip()
        if not raw:
            return
        cand = os.path.abspath(raw)
        if not within_root(cand):
            cand = os.path.abspath(os.path.join(ROOT_DIR, raw))
        self.navigate(cand)

    def on_tree_selection(self, *_):
        idxs = self.tree.selectionModel().selectedIndexes()
        if not idxs:
            return
        path = self.dir_model.filePath(idxs[0])
        if os.path.isdir(path):
            self.navigate(path)

    def on_list_double_clicked(self, index: QModelIndex):
        path = self.file_model.filePath(index)
        if os.path.isdir(path):
            self.navigate(path)
        else:
            self.open_file(path)

  
    def new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        dest = os.path.join(self.current_path, name.strip())
        if not within_root(dest):
            QMessageBox.warning(self, "Blocked", "Cannot create folder outside sandbox.")
            return
        try:
            os.makedirs(dest, exist_ok=False)
            self.refresh()
        except FileExistsError:
            QMessageBox.warning(self, "Exists", "A file or folder with that name already exists.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def selected_path(self) -> str | None:
        idxs = self.list.selectionModel().selectedIndexes()
        if not idxs:
            return None
        return self.file_model.filePath(idxs[0])

    def rename_selected(self):
        path = self.selected_path()
        if not path:
            return
        base = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=base)
        if not ok or not new_name.strip():
            return
        dest = os.path.join(os.path.dirname(path), new_name.strip())
        if not within_root(dest):
            QMessageBox.warning(self, "Blocked", "Cannot move/rename outside sandbox.")
            return
        try:
            os.rename(path, dest)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def delete_selected(self):
        path = self.selected_path()
        if not path:
            return
        resp = QMessageBox.question(
            self, "Move to Recycle Bin",
            f"Move to Recycle Bin:\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            move_to_trash(path)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not move to Recycle Bin:\n{e}")


    def refresh(self):
        cur = self.current_path
        self.dir_model.setRootPath("")
        self.file_model.setRootPath("")
        self.dir_model.setRootPath(cur)
        self.file_model.setRootPath(cur)
        self.tree.setRootIndex(self.dir_model.index(cur))
        self.list.setRootIndex(self.file_model.index(cur))
        self.tree.expand(self.dir_model.index(cur))
        self.update_status()

    def open_file(self, path: str):
        if not is_text_like(path):
            QMessageBox.information(self, "Open", "This file type isn't supported yet in PyOS.")
            return
        try:
            from apps import text_editor
            ed = text_editor.TextEditorWindow(parent=self.parent(), desktop=self.desktop)
            with open(path, "r", encoding="utf-8") as f:
                ed.editor.setPlainText(f.read())
            ed.file_path = path
            ed._dirty = False
            ed._refresh_title()
            if hasattr(self.desktop, "current_colors"):
                ed.apply_os_colors(self.desktop.current_colors)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open in Text Editor:\n{e}")

    
    def apply_os_colors(self, colors: dict):
        """Called by Settings to sync with OS theme."""
        text = colors.get("text", "#FFFFFF")
        window_bg = colors.get("window_bg", "#2E2E2E")

        self.setStyleSheet(
            f"background-color: {window_bg}; "
            f"color: {text}; "
            f"border: 2px solid #555; border-radius:5px;"
        )
        self.address.setStyleSheet(
            f"background-color: {window_bg}; color: {text}; border: 1px solid #444; border-radius:4px; padding:4px;"
        )
        self.status.setStyleSheet(f"color: {text};")

        view_css = f"""
            background-color: {window_bg};
            color: {text};
            selection-background-color: #264f78;
            selection-color: #ffffff;
            border: 1px solid #444;
            border-radius: 4px;
        """
        self.tree.setStyleSheet("QTreeView{" + view_css + "}")
        self.list.setStyleSheet("QListView{" + view_css + "}")

        if hasattr(self, "close_btn"):
            self.close_btn.setStyleSheet(f"background:#b33; color:{text}; border:none; border-radius:4px;")
        if hasattr(self, "min_btn"):
            self.min_btn.setStyleSheet(f"background:#666; color:{text}; border:none; border-radius:4px;")

        self.update()
        self.repaint()


def launch(parent, desktop):
    return FileExplorerWindow(parent=parent, desktop=desktop)
