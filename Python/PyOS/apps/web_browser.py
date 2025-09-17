
import os
import re
import urllib.parse

from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTabWidget, QLabel, QFileDialog, QMenu, QStyle
)

from desktop import AppWindow  


WEBENGINE_AVAILABLE = True
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import (
        QWebEngineProfile,
        QWebEngineDownloadRequest,
        QWebEnginePage,
    )
except Exception:
    WEBENGINE_AVAILABLE = False
    QWebEngineView = object  

print(f"PyOS: WebEngine available? {WEBENGINE_AVAILABLE}")


BOOKMARKS_FILE = os.path.join("data", "bookmarks.json")
def load_bookmarks() -> list[dict]:
    try:
        import json
        if os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []

def save_bookmarks(bm: list[dict]):
    try:
        import json
        os.makedirs(os.path.dirname(BOOKMARKS_FILE), exist_ok=True)
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bm, f, indent=2)
    except Exception:
        pass


HOMEPAGE = "https://www.google.com"

def normalize_input_to_url(text: str) -> str:
    text = text.strip()
    if not text:
        return HOMEPAGE
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", text):
        return text
    if "." in text or re.match(r"^localhost(:\d+)?($|/)", text):
        return "http://" + text
    return f"https://www.google.com/search?q={urllib.parse.quote(text)}"



class WebBrowserWindow(AppWindow):
    def __init__(self, parent=None, desktop=None):
        pm = QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_BrowserReload).scaled(24, 24)
        super().__init__("Web Browser", width=1100, height=720, icon_pixmap=pm, parent=parent, desktop=desktop)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 35, 8, 8)
        root.setSpacing(6)

       
        tb = QHBoxLayout()
        self.btn_back   = self._icon_btn(QStyle.StandardPixmap.SP_ArrowBack, "Back")
        self.btn_fwd    = self._icon_btn(QStyle.StandardPixmap.SP_ArrowForward, "Forward")
        self.btn_reload = self._icon_btn(QStyle.StandardPixmap.SP_BrowserReload, "Reload")
        self.btn_home   = self._icon_btn(QStyle.StandardPixmap.SP_DirHomeIcon, "Home")

        self.address = QLineEdit()
        self.address.setPlaceholderText("Search or enter address")
        self.address.setClearButtonEnabled(True)

        self.btn_go = QPushButton("Go")
        self.btn_tab_new = QPushButton("+"); self.btn_tab_new.setFixedWidth(28)
        self.btn_bookmarks = QPushButton("★"); self.btn_bookmarks.setFixedWidth(28)

        for b in (self.btn_back, self.btn_fwd, self.btn_reload, self.btn_home, self.btn_go, self.btn_tab_new, self.btn_bookmarks):
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        tb.addWidget(self.btn_back); tb.addWidget(self.btn_fwd); tb.addWidget(self.btn_reload); tb.addWidget(self.btn_home)
        tb.addSpacing(8); tb.addWidget(self.address, 1); tb.addWidget(self.btn_go); tb.addSpacing(8)
        tb.addWidget(self.btn_bookmarks); tb.addWidget(self.btn_tab_new)
        root.addLayout(tb)

        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_current_changed)
        root.addWidget(self.tabs, 1)

        
        self.bm_menu = QMenu(self)
        self.btn_bookmarks.setMenu(self.bm_menu)
        self.bm_menu.aboutToShow.connect(self.populate_bookmarks_menu)

        
        self.btn_back.clicked.connect(self.nav_back)
        self.btn_fwd.clicked.connect(self.nav_forward)
        self.btn_reload.clicked.connect(self.reload_or_stop)
        self.btn_home.clicked.connect(lambda: self.load_in_current(HOMEPAGE))
        self.btn_go.clicked.connect(self.on_go_clicked)
        self.btn_tab_new.clicked.connect(lambda: self.new_tab(HOMEPAGE))
        self.address.returnPressed.connect(self.on_go_clicked)

       
        QShortcut(QKeySequence("Ctrl+L"), self, activated=lambda: (self.address.setFocus(), self.address.selectAll()))
        QShortcut(QKeySequence("Ctrl+T"), self, activated=lambda: self.new_tab(HOMEPAGE))
        QShortcut(QKeySequence("Ctrl+W"), self, activated=lambda: self.close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Alt+Left"), self, activated=self.nav_back)
        QShortcut(QKeySequence("Alt+Right"), self, activated=self.nav_forward)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.reload_or_stop)

        
        if WEBENGINE_AVAILABLE:
            try:
                profile = QWebEngineProfile.defaultProfile()
                profile.downloadRequested.connect(self.on_download_requested)
            except Exception:
                pass
            self.new_tab(HOMEPAGE)
        else:
            self._show_no_engine_message()

        
        if hasattr(desktop, "current_colors"):
            self.apply_os_colors(desktop.current_colors)

        self.raise_()
        self.activateWindow()
        print("Browser window constructed. Tabs:", self.tabs.count(), "WebEngine available:", WEBENGINE_AVAILABLE)

        
        QApplication.instance().aboutToQuit.connect(lambda: self.close())

   
    def closeEvent(self, event):
        try:
            for i in range(self.tabs.count() - 1, -1, -1):
                w = self.tabs.widget(i)
                self.tabs.removeTab(i)
                try:
                    w.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass
        super().closeEvent(event)

   
    def _icon_btn(self, std_icon: QStyle.StandardPixmap, fallback_text: str) -> QPushButton:
        btn = QPushButton(); btn.setFlat(True); btn.setFixedSize(34, 28)
        icon = QApplication.instance().style().standardIcon(std_icon)
        if not icon.isNull():
            btn.setIcon(icon); btn.setIconSize(QSize(18, 18))
        else:
            btn.setText(fallback_text)
        return btn

   
    def new_tab(self, url: str | None = None):
        if not WEBENGINE_AVAILABLE:
            self._show_no_engine_message(); return
        view = BrowserView(self)
        idx = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(idx)
        view.urlChanged.connect(self.on_view_url_changed)
        view.titleChanged.connect(lambda title, v=view: self._set_tab_title_for(v, title))
        view.loadStarted.connect(self.on_load_started)
        view.loadFinished.connect(self.on_load_finished)
        view.load(QUrl(url or HOMEPAGE))

    def close_tab(self, index: int):
        if index < 0: return
        w = self.tabs.widget(index)
        if w: w.deleteLater()
        self.tabs.removeTab(index)

    def on_current_changed(self, index: int):
        view = self.current_view()
        if WEBENGINE_AVAILABLE and isinstance(view, QWebEngineView):
            self.address.setText(view.url().toString())
        self._update_nav_enabled()

    def current_view(self):
        return self.tabs.currentWidget()

    def _set_tab_title_for(self, view, title: str):
        i = self.tabs.indexOf(view)
        if i >= 0:
            self.tabs.setTabText(i, (title[:20] + "…") if len(title) > 20 else title or "New Tab")

    
    def nav_back(self):
        v = self.current_view()
        if WEBENGINE_AVAILABLE and isinstance(v, QWebEngineView): v.back()
        self._update_nav_enabled()

    def nav_forward(self):
        v = self.current_view()
        if WEBENGINE_AVAILABLE and isinstance(v, QWebEngineView): v.forward()
        self._update_nav_enabled()

    def reload_or_stop(self):
        v = self.current_view()
        if not (WEBENGINE_AVAILABLE and isinstance(v, QWebEngineView)): return
        if getattr(self, "_loading", False):
            try: v.stop()
            except Exception: pass
        else:
            v.reload()

    def on_go_clicked(self):
        self.load_in_current(normalize_input_to_url(self.address.text()))

    def load_in_current(self, url: str):
        v = self.current_view()
        if WEBENGINE_AVAILABLE and isinstance(v, QWebEngineView):
            v.load(QUrl(url))

    def on_view_url_changed(self, url: QUrl):
        if self.current_view() is self.sender():
            self.address.setText(url.toString()); self._update_nav_enabled()

    def on_load_started(self):
        self._loading = True

    def on_load_finished(self, ok: bool):
        self._loading = False

    def _update_nav_enabled(self):
        v = self.current_view()
        if WEBENGINE_AVAILABLE and isinstance(v, QWebEngineView):
            try:
                self.btn_back.setEnabled(v.history().canGoBack())
                self.btn_fwd.setEnabled(v.history().canGoForward())
            except Exception:
                self.btn_back.setEnabled(True); self.btn_fwd.setEnabled(True)

    def on_download_requested(self, item: 'QWebEngineDownloadRequest'):
        try: suggested = item.downloadFileName()
        except Exception: suggested = "download.bin"
        base_dir = os.path.join("data", "downloads"); os.makedirs(base_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Save file", os.path.join(base_dir, suggested), "All Files (*.*)")
        if not path:
            try: item.cancel()
            except Exception: pass
            return
        try: item.setDownloadFileName(os.path.basename(path))
        except Exception: pass
        try:
            ddir = os.path.dirname(path)
            if hasattr(item, "setDownloadDirectory"): item.setDownloadDirectory(ddir)
        except Exception: pass
        try: item.accept()
        except Exception: pass

   
    def populate_bookmarks_menu(self):
        self.bm_menu.clear()
        add_act = self.bm_menu.addAction("Add current page…")
        add_act.triggered.connect(self.add_current_bookmark)
        self.bm_menu.addSeparator()
        bms = load_bookmarks()
        if not bms:
            empty_act = self.bm_menu.addAction("(no bookmarks)"); empty_act.setEnabled(False); return
        for bm in bms:
            title = bm.get("title") or bm.get("url", "")
            act = self.bm_menu.addAction(title)
            act.triggered.connect(lambda checked=False, url=bm.get("url", ""): self.load_in_current(url))
        self.bm_menu.addSeparator()
        clear_act = self.bm_menu.addAction("Clear all bookmarks")
        clear_act.triggered.connect(self.clear_bookmarks)

    def add_current_bookmark(self):
        if not WEBENGINE_AVAILABLE: return
        v = self.current_view()
        if not isinstance(v, QWebEngineView): return
        url = v.url().toString(); title = v.title() or url
        bms = load_bookmarks(); bms.append({"title": title, "url": url}); save_bookmarks(bms)

    def clear_bookmarks(self): save_bookmarks([])

    def apply_os_colors(self, colors: dict):
        text = colors.get("text", "#FFFFFF"); window_bg = colors.get("window_bg", "#2E2E2E")
        self.setStyleSheet(f"background-color: {window_bg}; color: {text}; border: 2px solid #555; border-radius:5px;")
        self.address.setStyleSheet(f"background-color: {window_bg}; color: {text}; border: 1px solid #444; border-radius:4px; padding:4px;")
        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{
                background-color: {window_bg};
                color: {text};
                padding: 6px 10px;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabWidget::pane {{ border: 1px solid #444; border-radius: 6px; }}
        """)

    def _show_no_engine_message(self):
        wrapper = QWidget(); vbox = QVBoxLayout(wrapper); vbox.setContentsMargins(16, 16, 16, 16)
        lbl = QLabel(
            "<h3>PyQt WebEngine not available</h3>"
            "<p>To use the Web Browser, install with:</p>"
            "<pre>pip install PyQt6-WebEngine</pre>"
        ); lbl.setTextFormat(Qt.TextFormat.RichText)
        vbox.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        idx = self.tabs.addTab(wrapper, "WebEngine not installed"); self.tabs.setCurrentIndex(idx)



if WEBENGINE_AVAILABLE:
    class BrowserView(QWebEngineView):
        def __init__(self, host_window: WebBrowserWindow):
            super().__init__(host_window); self._host = host_window
        def createWindow(self, _type: QWebEnginePage.WebWindowType):
            self._host.new_tab(); return self._host.current_view()
else:
    class BrowserView: pass


def launch(parent, desktop):
    return WebBrowserWindow(parent=parent, desktop=desktop)

