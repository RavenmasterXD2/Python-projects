
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QColor, QIcon, QTextCharFormat, QFont, QKeySequence, QAction
from PyQt6.QtWidgets import (
    QWidget, QCalendarWidget, QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QTimeEdit, QDialog, QDialogButtonBox, QLabel,
    QMessageBox, QSizePolicy, QStyle
)



DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAVE_FILE = DATA_DIR / "calendar.json"
ICON_FILE = DATA_DIR / "icons" / "calendar.png"



def _hx(v, default="#000000") -> str:
    """Return #RRGGBB from QColor/str/tuple, or default."""
    if isinstance(v, QColor):
        return v.name()
    if isinstance(v, (tuple, list)) and 3 <= len(v) <= 4:
        c = QColor(*v)
        return c.name() if c.isValid() else default
    if isinstance(v, str):
        c = QColor(v)
        return v if c.isValid() else default
    return default


def _load_db() -> dict:
    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        return json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {} 


def _save_db(db: dict) -> None:
    try:
        SAVE_FILE.write_text(json.dumps(db, indent=2), encoding="utf-8")
    except Exception as e:
        print("[Calendar] save failed:", e)


@dataclass
class Event:
    id: str
    title: str
    time: str  
    notes: str

    @classmethod
    def new(cls, title="", when: QTime | None = None, notes=""):
        t = (when or QTime.currentTime()).toString("HH:mm")
        return cls(id=str(uuid.uuid4()), title=title, time=t, notes=notes)



class EventDialog(QDialog):
    def __init__(self, parent=None, theme: dict | None = None, event: Event | None = None):
        super().__init__(parent)
        self.setWindowTitle("Event")
        self.setModal(True)

        # theme
        bg = _hx((theme or {}).get("window_bg", "#202225"))
        tx = _hx((theme or {}).get("text", "#ffffff"))
        btn = _hx((theme or {}).get("button", "#303030"))
        btn_h = _hx((theme or {}).get("button_hover", "#3a3a3a"))
        accent = _hx((theme or {}).get("accent", "#8a2be2"))
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; color: {tx}; }}
            QLineEdit, QTextEdit, QTimeEdit {{
                background: {bg}; color: {tx};
                border: 1px solid #555; border-radius: 6px; padding: 6px;
                selection-background-color: {accent};
            }}
            QLabel {{ color: {tx}; }}
            QPushButton {{
                background: {btn}; color: {tx};
                border: 1px solid #4a4a4a; border-radius: 8px; padding: 6px 10px;
            }}
            QPushButton:hover {{ background: {btn_h}; }}
        """)

        v = QVBoxLayout(self)
        self.title_edit = QLineEdit(self)
        self.time_edit = QTimeEdit(self)
        self.time_edit.setDisplayFormat("HH:mm")
        self.notes_edit = QTextEdit(self)
        self.notes_edit.setFixedHeight(120)

        form = QVBoxLayout()
        form.addWidget(QLabel("Title:"))
        form.addWidget(self.title_edit)
        form.addWidget(QLabel("Time:"))
        form.addWidget(self.time_edit)
        form.addWidget(QLabel("Notes:"))
        form.addWidget(self.notes_edit)
        v.addLayout(form)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, parent=self)
        v.addWidget(bb)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)

        if event:
            self.title_edit.setText(event.title)
            try:
                self.time_edit.setTime(QTime.fromString(event.time, "HH:mm"))
            except Exception:
                pass
            self.notes_edit.setPlainText(event.notes)

    def get(self) -> tuple[str, QTime, str]:
        return self.title_edit.text().strip(), self.time_edit.time(), self.notes_edit.toPlainText().strip()



class CalendarApp(QWidget):
    """
    Theme-aware calendar with day agenda and persistent events.
    Accepts theme=dict with keys: window_bg, text, button, button_hover, accent, window_border
    """
    def __init__(self, parent=None, theme: dict | None = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.db: dict = _load_db()

       
        try:
            if ICON_FILE.exists():
                self.setWindowIcon(QIcon(str(ICON_FILE)))
        except Exception:
            pass

      
        self.col_bg = _hx(self.theme.get("window_bg", "#1f1f1f"))
        self.col_tx = _hx(self.theme.get("text", "#ffffff"))
        self.col_btn = _hx(self.theme.get("button", "#303030"))
        self.col_btn_h = _hx(self.theme.get("button_hover", "#3a3a3a"))
        self.col_accent = _hx(self.theme.get("accent", "#8a2be2"))
        self.col_frame = _hx(self.theme.get("window_border", "#555555"))

        self.setStyleSheet(f"background:{self.col_bg}; color:{self.col_tx};")

       
        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setNavigationBarVisible(True)
        self.calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self._style_calendar()

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search today’s events…")
        self.search.setClearButtonEnabled(True)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: {self.col_bg}; color: {self.col_tx};
                border: 1px solid {self.col_frame}; border-radius: 8px; padding: 8px 10px;
                selection-background-color: {self.col_accent};
            }}
        """)

        self.list = QListWidget(self)
        self.list.setStyleSheet(f"""
            QListWidget {{
                background: {self.col_bg}; color: {self.col_tx};
                border: 1px solid {self.col_frame}; border-radius: 8px;
            }}
            QListWidget::item {{ padding: 8px; }}
            QListWidget::item:selected {{
                background: {self.col_accent}; color: white;
            }}
        """)
        self.list.setSelectionMode(self.list.SelectionMode.SingleSelection)

        self.btn_new = QPushButton("New", self)
        self.btn_edit = QPushButton("Edit", self)
        self.btn_del = QPushButton("Delete", self)

        for b in (self.btn_new, self.btn_edit, self.btn_del):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {self.col_btn}; color: {self.col_tx};
                    border: 1px solid #4a4a4a; border-radius: 10px; padding: 8px 12px;
                }}
                QPushButton:hover {{ background: {self.col_btn_h}; }}
            """)

       
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.setContentsMargins(12, 12, 6, 12)
        right = QVBoxLayout()
        right.setContentsMargins(6, 12, 12, 12)

        left.addWidget(self.calendar, 1)
        right.addWidget(self.search)
        right.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_del)
        right.addLayout(btn_row)

        root.addLayout(left, 3)
        root.addLayout(right, 2)

        
        self.calendar.selectionChanged.connect(self._on_date_changed)
        self.search.textChanged.connect(self._refilter_list)
        self.list.itemDoubleClicked.connect(lambda _: self._edit_selected())
        self.btn_new.clicked.connect(self._add_event)
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_del.clicked.connect(self._delete_selected)

       
        a_new = QAction(self); a_new.setShortcut(QKeySequence("Ctrl+N")); a_new.triggered.connect(self._add_event); self.addAction(a_new)
        a_find= QAction(self); a_find.setShortcut(QKeySequence("Ctrl+F")); a_find.triggered.connect(self.search.setFocus); self.addAction(a_find)
        a_edit= QAction(self); a_edit.setShortcut(QKeySequence(Qt.Key.Key_Return)); a_edit.triggered.connect(self._edit_selected); self.addAction(a_edit)
        a_del = QAction(self); a_del.setShortcut(QKeySequence(Qt.Key.Key_Delete)); a_del.triggered.connect(self._delete_selected); self.addAction(a_del)

       
        self._refresh_marks()
        self._on_date_changed()

    
    def _style_calendar(self):
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background: {self.col_bg}; color: {self.col_tx};
                border: 1px solid {self.col_frame}; border-radius: 10px;
            }}
            QCalendarWidget QToolButton {{
                background: {self.col_btn}; color: {self.col_tx};
                border: 1px solid #4a4a4a; border-radius: 8px; padding: 4px 8px;
            }}
            QCalendarWidget QToolButton:hover {{ background: {self.col_btn_h}; }}
            QCalendarWidget QAbstractItemView:enabled {{
                selection-background-color: {self.col_accent};
                selection-color: white;
                background: {self.col_bg}; color: {self.col_tx};
                outline: none;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: transparent; }}
        """)

    def _refresh_marks(self):
        """Bold the dates that have events."""
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())  
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.DemiBold)
        fmt.setForeground(QColor(self.col_accent))
        for datestr, items in self.db.items():
            if not items:
                continue
            y, m, d = map(int, datestr.split("-"))
            self.calendar.setDateTextFormat(QDate(y, m, d), fmt)

    
    def _selected_date_key(self) -> str:
        d: QDate = self.calendar.selectedDate()
        return d.toString("yyyy-MM-dd")

    def _on_date_changed(self):
        key = self._selected_date_key()
        items = list(self.db.get(key, []))
        items.sort(key=lambda ev: ev.get("time", "23:59"))
        self._fill_list(items)
        self._refilter_list()  

    def _fill_list(self, items: list[dict]):
        self.list.clear()
        for ev in items:
            title = ev.get("title", "(Untitled)")
            time = ev.get("time", "")
            line = f"{time}  -  {title}" if time else title
            it = QListWidgetItem(line)
            it.setData(Qt.ItemDataRole.UserRole, ev)
            self.list.addItem(it)

    def _refilter_list(self):
        query = self.search.text().strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            show = (query in it.text().lower()) if query else True
            it.setHidden(not show)

  
    def _add_event(self):
        d = EventDialog(self, theme=self.theme)
        if d.exec() == QDialog.DialogCode.Accepted:
            title, when, notes = d.get()
            if not title:
                title = "(Untitled)"
            ev = Event.new(title=title, when=when, notes=notes)
            key = self._selected_date_key()
            self.db.setdefault(key, []).append(asdict(ev))
            _save_db(self.db)
            self._refresh_marks()
            self._on_date_changed()

    def _current_item(self) -> tuple[int, dict] | None:
        it = self.list.currentItem()
        if not it:
            return None
        idx = self.list.row(it)
        ev = it.data(Qt.ItemDataRole.UserRole) or {}
        return idx, ev

    def _edit_selected(self):
        cur = self._current_item()
        if not cur:
            return
        idx, ev = cur
        ev_obj = Event(id=ev.get("id", str(uuid.uuid4())),
                       title=ev.get("title", ""),
                       time=ev.get("time", ""),
                       notes=ev.get("notes", ""))
       
        try:
            t = QTime.fromString(ev_obj.time or "09:00", "HH:mm")
        except Exception:
            t = QTime.currentTime()
        dlg = EventDialog(self, theme=self.theme, event=Event(ev_obj.id, ev_obj.title, ev_obj.time or t.toString("HH:mm"), ev_obj.notes))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, when, notes = dlg.get()
            key = self._selected_date_key()
            if key not in self.db:
                self.db[key] = []
           
            self.db[key][idx] = {"id": ev_obj.id, "title": title or "(Untitled)", "time": when.toString("HH:mm"), "notes": notes}
            _save_db(self.db)
            self._on_date_changed()

    def _delete_selected(self):
        cur = self._current_item()
        if not cur:
            return
        idx, ev = cur
        if QMessageBox.question(self, "Delete", f"Delete '{ev.get('title','(Untitled)')}'?") != QMessageBox.StandardButton.Yes:
            return
        key = self._selected_date_key()
        try:
            del self.db[key][idx]
            if not self.db[key]:
                del self.db[key]
        except Exception:
            pass
        _save_db(self.db)
        self._refresh_marks()
        self._on_date_changed()



if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    w = CalendarApp(theme={
        "window_bg": QColor("#1E1B29"),
        "text": QColor("#FFFFFF"),
        "button": QColor("#322e46"),
        "button_hover": QColor("#3e3956"),
        "accent": QColor("#8a2be2"),
        "window_border": QColor("#5a4a85"),
    })
    w.setWindowTitle("Calendar - PyOS")
    w.resize(900, 580)
    w.show()
    sys.exit(app.exec())
