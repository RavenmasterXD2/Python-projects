from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QMessageBox, QFrame, QStackedWidget, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QRect
from PyQt6.QtGui import QPixmap, QColor, QPainter
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ICONS_DIR = DATA_DIR / "icons"
SEC_FILE = DATA_DIR / "security.json"


def _shield_pixmap(size=36) -> QPixmap:
    src = ICONS_DIR / "security.png"
    if src.exists():
        pm = QPixmap(str(src))
        if not pm.isNull():
            return pm.scaled(size, size,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
  
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainterPath
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(138, 43, 226))
    p.setPen(QColor(93, 26, 168))
    w = h = size
    pts = [(w*0.15, h*0.25), (w*0.5, h*0.05), (w*0.85, h*0.25), (w*0.85, h*0.60), (w*0.5, h*0.95), (w*0.15, h*0.60)]
    path = QPainterPath()
    path.moveTo(*pts[0])
    for x, y in pts[1:]:
        path.lineTo(x, y)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pm

def _warn_disable(parent, title, body) -> bool:
    resp = QMessageBox.warning(
        parent, title, body,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return resp == QMessageBox.StandardButton.Yes

def _load_state() -> dict:
    try:
        if SEC_FILE.exists():
            return json.loads(SEC_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_state(obj: dict):
    try:
        SEC_FILE.parent.mkdir(parents=True, exist_ok=True)
        SEC_FILE.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception:
        pass


class OptionsApp(QMainWindow):
    """
    Options panel styled like a security center:
    - Menu band across the top (Real-time, Firewall, etc.)
    - Each page contains persisted toggles
    - Smooth page switch (fade+slide) with cleanup so buttons keep working
    - Fixed, non-draggable, shows near bottom-right (left of clock)
    """
    def __init__(self, desktop):
        super().__init__(desktop)
        self.desktop = desktop
        self.setObjectName("SecurityManager")
        self.state = _load_state()
        self._animating = False 

      
        self.setWindowFlags(
            Qt.WindowType.SubWindow |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setFixedSize(900, 600)

       
        self.setStyleSheet("""
            #SecurityManager { background: #1f1f1f; }
            QLabel { color: #eaeaea; }
            QCheckBox { color: #d0d0d0; font-size: 11pt; }
            QPushButton[role="band"] {
                color: #eaeaea; background: #2a2a2a; border: 1px solid #3b3b3b;
                border-radius: 9px; padding: 8px 12px; font-weight: 600;
            }
            QPushButton[role="band"]:hover { background: #333; }
            QPushButton[role="band"][active="true"] { background: #3a2a57; border-color: #5e3ea4; }
            QFrame#Card { background: #262626; border: 1px solid #3a3a3a; border-radius: 12px; }
            QLabel.desc { color: #bdbdbd; }
            QLabel.section { color: #ffffff; font-size: 13.5pt; font-weight: 700; }
        """)

     
        container = QWidget(self)
        self.setCentralWidget(container)
        root = QVBoxLayout(container)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(_shield_pixmap(36))
        icon.setFixedSize(36, 36)
        title = QLabel("PyOS Options")
        title.setStyleSheet("font-size: 20pt; font-weight: 800; color: #ffffff;")
        header.addWidget(icon)
        header.addSpacing(10)
        header.addWidget(title)
        header.addStretch(1)
        root.addLayout(header)

        band = QHBoxLayout()
        band.setSpacing(8)
        self.band_buttons: list[QPushButton] = []

        def add_btn(text: str):
            b = QPushButton(text)
            b.setProperty("role", "band")
            b.setProperty("active", False)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setMinimumHeight(38)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.band_buttons.append(b)
            band.addWidget(b)
            return b

        self.btn_rt      = add_btn("Real-time")
        self.btn_vtp     = add_btn("Virus & Threat")
        self.btn_account = add_btn("Account")
        self.btn_fw      = add_btn("Firewall & Network")
        self.btn_app     = add_btn("App & Browser")
        self.btn_device  = add_btn("Device Security")
        self.btn_perf    = add_btn("Performance & Integrity")
        band.addStretch(1)
        root.addLayout(band)

        
        self.pages = QStackedWidget(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.pages)
        root.addWidget(scroll, 1)

        
        self.pg_rt      = self._page_realtime()
        self.pg_vtp     = self._page_virus_threat()
        self.pg_account = self._page_account()
        self.pg_fw      = self._page_firewall()
        self.pg_app     = self._page_app_browser()
        self.pg_device  = self._page_device()
        self.pg_perf    = self._page_performance()

        for p in (self.pg_rt, self.pg_vtp, self.pg_account, self.pg_fw,
                  self.pg_app, self.pg_device, self.pg_perf):
            self.pages.addWidget(p)

        
        self.btn_rt.clicked.connect(lambda: self._switch_to(0))
        self.btn_vtp.clicked.connect(lambda: self._switch_to(1))
        self.btn_account.clicked.connect(lambda: self._switch_to(2))
        self.btn_fw.clicked.connect(lambda: self._switch_to(3))
        self.btn_app.clicked.connect(lambda: self._switch_to(4))
        self.btn_device.clicked.connect(lambda: self._switch_to(5))
        self.btn_perf.clicked.connect(lambda: self._switch_to(6))

        
        self._switch_to(0, animate=False)

    
    def mousePressEvent(self, e): e.ignore()
    def mouseMoveEvent(self, e): e.ignore()
    def mouseReleaseEvent(self, e): e.ignore()

  
    def showEvent(self, event):
        super().showEvent(event)
        margin = 8
        taskbar_h = 50
        x = self.desktop.width() - self.width() - margin
        y = self.desktop.height() - taskbar_h - self.height() - margin
        self.setGeometry(QRect(x, y, self.width(), self.height()))


    def _card(self, title_text: str, desc_text: str | None, toggles: list[tuple[str, str | None, str]]):
        card = QFrame(objectName="Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("section")
        title.setProperty("class", "section")
        v.addWidget(title)

        if desc_text:
            desc = QLabel(desc_text)
            desc.setObjectName("desc")
            desc.setProperty("class", "desc")
            desc.setWordWrap(True)
            v.addWidget(desc)

        for key, danger, label in toggles:
            cb = QCheckBox(label)
            cb.setChecked(bool(self.state.get(key, True)))
            if danger:
                cb.stateChanged.connect(lambda st, k=key, c=cb, d=danger: self._on_toggle_with_warning(k, c, d))
            else:
                cb.stateChanged.connect(lambda st, k=key, c=cb: self._on_toggle(k, c))
            v.addWidget(cb)

        return card

    def _on_toggle(self, key: str, cb: QCheckBox):
        self.state[key] = cb.isChecked()
        _save_state(self.state)

    def _on_toggle_with_warning(self, key: str, cb: QCheckBox, danger: str):
        if cb.isChecked():  
            return self._on_toggle(key, cb)
        ok = _warn_disable(
            self, "This setting protects your device",
            f"{danger}\n\nAre you sure you want to turn it OFF?"
        )
        if not ok:
            cb.blockSignals(True); cb.setChecked(True); cb.blockSignals(False)
        else:
            self._on_toggle(key, cb)

    
    def _page_realtime(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "Real-time Protection",
            "Continuously monitors and blocks threats as they appear.",
            [
                ("rt_scanning", "Disabling real-time scanning may expose your system to live threats.", "Enable real-time scanning"),
                ("rt_cloud", "Turning this off reduces detection accuracy and speed.", "Cloud-delivered protection"),
                ("rt_samples", None, "Automatic sample submission"),
                ("rt_tamper", "Disabling tamper protection allows malicious apps to alter security settings.", "Tamper protection"),
            ]
        ))
        lay.addWidget(self._card(
            "Ransomware Protection",
            "Protects important folders from unauthorized changes and suspicious apps.",
            [
                ("rt_cfa", "Turning this off can allow ransomware to encrypt your files.", "Controlled folder access"),
                ("rt_suspicious", None, "Block suspicious activity"),
            ]
        ))
        lay.addStretch(1)
        return page

    def _page_virus_threat(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "Virus & Threat Protection",
            "Scan options and automatic updates for malware definitions.",
            [
                ("vtp_updates", "Without updates, new threats may not be detected.", "Automatic definition updates"),
                ("vtp_removable", None, "Scan removable drives"),
                ("vtp_archives", None, "Scan archives"),
                ("vtp_behavior", "Disabling behavior analysis can miss zero-day malware.", "Heuristic/behavior analysis"),
            ]
        ))
        lay.addStretch(1)
        return page

    def _page_account(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "Account Security",
            "Secure sign-in and identity protection.",
            [
                ("acc_wake_signin", None, "Require sign-in on wake"),
                ("acc_passwordless", "Turning this off may reduce account security.", "Passwordless sign-in (PIN/Hello)"),
                ("acc_weak_pw", None, "Block weak passwords"),
                ("acc_lockout", "Disabling lockout increases risk of account takeover.", "Account lockout on brute force"),
            ]
        ))
        lay.addStretch(1)
        return page

    def _page_firewall(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "Firewall & Network Security",
            "Filter network traffic and block unauthorized connections.",
            [
                ("fw_enable", "Disabling the firewall exposes your device to network attacks.", "Enable firewall (all profiles)"),
                ("fw_inbound_block", "Turning this off may allow remote access to services.", "Block inbound by default"),
                ("fw_notify", None, "Notify on app block"),
                ("fw_stealth", None, "Stealth mode (drop pings)"),
            ]
        ))
        lay.addStretch(1)
        return page

    def _page_app_browser(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "App & Browser Control",
            "Protects against malicious websites, files, and exploits.",
            [
                ("ab_smartscreen_apps", "Disabling SmartScreen can allow untrusted apps to run.", "SmartScreen for apps"),
                ("ab_smartscreen_dl", None, "SmartScreen for downloads"),
                ("ab_exploit", "Turning this off weakens memory protection (DEP/ASLR).", "Exploit protection (DEP/ASLR)"),
                ("ab_pua", None, "Block potentially unwanted apps (PUA)"),
            ]
        ))
        lay.addStretch(1)
        return page

    def _page_device(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "Device Security",
            "Core isolation, secure boot, and hardware security features.",
            [
                ("dev_secure_boot", None, "Secure Boot status check"),
                ("dev_core_isolation", "Disabling memory integrity can allow kernel-level attacks.", "Core isolation / Memory integrity"),
                ("dev_firmware", None, "Firmware protection"),
                ("dev_tpm", None, "TPM health monitoring"),
            ]
        ))
        lay.addStretch(1)
        return page

    def _page_performance(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(12)
        lay.addWidget(self._card(
            "Device Performance & Integrity",
            "Monitors device health and integrity.",
            [
                ("perf_storage", None, "Storage health checks"),
                ("perf_batt_thermal", None, "Battery/thermal health checks"),
                ("perf_file_integrity", "Turning this off can hide corruption or tampering.", "Integrity checks on critical files"),
                ("perf_maintenance", None, "Periodic maintenance scans"),
            ]
        ))
        lay.addStretch(1)
        return page

  
    def _mark_band_active(self, active_btn: QPushButton):
        for b in self.band_buttons:
            b.setProperty("active", b is active_btn)
            b.style().unpolish(b); b.style().polish(b); b.update()

    def _switch_to(self, idx: int, animate: bool = True):
        current = self.pages.currentWidget()
        self.pages.setCurrentIndex(idx)
        target = self.pages.currentWidget()

        btn = [self.btn_rt, self.btn_vtp, self.btn_account, self.btn_fw,
               self.btn_app, self.btn_device, self.btn_perf][idx]
        self._mark_band_active(btn)

        if not animate or current is None or current is target:
            if target.graphicsEffect() is not None:
                target.setGraphicsEffect(None)
            return

        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        if current.graphicsEffect() is not None:
            current.setGraphicsEffect(None)
        if target.graphicsEffect() is not None:
            target.setGraphicsEffect(None)

        ce = QGraphicsOpacityEffect(current)
        te = QGraphicsOpacityEffect(target)
        current.setGraphicsEffect(ce)
        target.setGraphicsEffect(te)
        ce.setOpacity(1.0); te.setOpacity(0.0)

        area = self.pages.rect()
        start_geo = QRect(area.x() + int(area.width()*0.06), area.y(), area.width(), area.height())
        target.setGeometry(start_geo)

        fade_out = QPropertyAnimation(ce, b"opacity")
        fade_out.setDuration(140); fade_out.setStartValue(1.0); fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)

        fade_in = QPropertyAnimation(te, b"opacity")
        fade_in.setDuration(220); fade_in.setStartValue(0.0); fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        slide_in = QPropertyAnimation(target, b"geometry")
        slide_in.setDuration(220); slide_in.setStartValue(start_geo); slide_in.setEndValue(area)
        slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _cleanup():
            target.setGraphicsEffect(None)
            current.setGraphicsEffect(None)

        fade_in.finished.connect(_cleanup)
        fade_out.start(); fade_in.start(); slide_in.start()


def launch(parent, desktop):
    win = OptionsApp(desktop)
    win.show()
    return win
