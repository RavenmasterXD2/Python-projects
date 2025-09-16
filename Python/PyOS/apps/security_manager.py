from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton,
    QMessageBox, QFrame, QStackedWidget, QSizePolicy, QScrollArea,
    QListWidget, QListWidgetItem, QProgressBar
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QColor, QPainter
from pathlib import Path
import json, re

BASE_DIR = Path(__file__).resolve().parent.parent  
DATA_DIR  = BASE_DIR / "data"
ICONS_DIR = DATA_DIR / "icons"
SEC_FILE  = DATA_DIR / "security.json"


EXCEPTIONS = {
    "core.sys",
    
    "boot.asm",
    "loader.asm",
    "boot.bin",
   
    "entry.asm",
    "kernel.c",
    "idt.c",
    "isr.c",
    "irq.c",
    "paging.c",
    "heap.c",
    "console.c",
    "keyboard.c",
    "timer.c",
    "syscall.c",
   
    "string.c",
    "stdio.c",
    "stdlib.c",
    "sys.c",
    
    "vga.c",
    "ata.c",
    "fs.c",
    "rtc.c",
   
    "init.c",
    "shell.c",
    
    "echo.c",
    "cat.c",
    "ls.c",
    
    "link.ld",
    "Makefile",
}



def _shield_pixmap(size=96) -> QPixmap:  
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
    pts = [(w*0.15, h*0.25), (w*0.5, h*0.05), (w*0.85, h*0.25),
           (w*0.85, h*0.60), (w*0.5, h*0.95), (w*0.15, h*0.60)]
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


SUSPICIOUS_EXT = {
    ".exe", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh",
    ".scr", ".pif", ".ps1", ".psm1", ".dll", ".sys", ".msi", ".reg", ".hta", ".lua", ".c"
}
SUSPICIOUS_NAME_PAT = re.compile(r"(keylog|stealer|rat|hacktool|backdoor|miner|ransom|trojan)", re.I)
SUSPICIOUS_TEXT_PAT = re.compile(
    r"(powershell\s+-enc|cmd\.exe\s+/c|bitsadmin|reg\s+add|vssadmin\s+delete|cipher\s+/w:|"
    r"mimikatz|certutil\s+-urlcache)", re.I
)

class ScannerWorker(QThread):
    progress = pyqtSignal(int, str)       
    found    = pyqtSignal(str)             
    done     = pyqtSignal(int, int, int)  
    log      = pyqtSignal(str)

    def __init__(self, root: Path, mode: str = "quick", parent=None):
        super().__init__(parent)
        self.root = Path(root)
        self.mode = mode       
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _iter_quick_paths(self):
        targets = [
            BASE_DIR / "apps",
            BASE_DIR / "data",
            BASE_DIR / "downloads",
            BASE_DIR / "temp",
        ]
        for t in targets:
            if not t.exists():
                continue
            base_depth = len(t.parts)
            for path in t.rglob("*"):
                if self._cancel:
                    return
                if path.is_file():
                    depth = len(path.parts) - base_depth
                    if depth <= 3:
                        if (path.suffix.lower() in SUSPICIOUS_EXT
                                or SUSPICIOUS_NAME_PAT.search(path.name)):
                            yield path

    def _iter_full_paths(self):
        blacklist = {"node_modules", "__pycache__", ".git", ".venv", "venv"}
        for path in self.root.rglob("*"):
            if self._cancel:
                return
            if any(part.lower() in blacklist for part in path.parts):
                continue
            if path.is_file():
                yield path

    def _looks_suspicious(self, p: Path) -> bool:
       
        if p.name in EXCEPTIONS:
            return False

        name = p.name
        if p.suffix.lower() in SUSPICIOUS_EXT:
            return True
        if SUSPICIOUS_NAME_PAT.search(name):
            return True
        
        try:
            with open(p, "rb") as f:
                chunk = f.read(8192)
            try:
                txt = chunk.decode("utf-8", errors="ignore")
            except Exception:
                txt = ""
            if txt and SUSPICIOUS_TEXT_PAT.search(txt):
                return True
        except Exception:
            pass
        return False

    def run(self):
        try:
            paths = list(self._iter_quick_paths() if self.mode == "quick" else self._iter_full_paths())
        except Exception as e:
            self.log.emit(f"Enumeration error: {e}")
            paths = []

        total = len(paths) or 1
        scanned = 0
        threats = 0
        errors  = 0

        for i, p in enumerate(paths, 1):
            if self._cancel:
                break
            try:
                suspicious = self._looks_suspicious(p)
                if suspicious:
                    threats += 1
                   
                    rel = "/" + str(p.resolve()).replace("\\", "/")
                    idx = rel.lower().find("/pyos/")
                    rel = rel[idx:] if idx >= 0 else rel
                    self.found.emit(rel)
            except Exception:
                errors += 1

            scanned += 1
            percent = int((i / total) * 100)
            self.progress.emit(percent, str(p))

        self.done.emit(scanned, threats, errors)


class SecurityManagerApp(QWidget):
    """
    Security Center with a menu band, working (persisted) toggles,
    warnings on risky disables, robust page switching (fade in only),
    and a scanner (Quick / Full) with progress + results + exceptions.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SecurityManager")
        self.state = _load_state()
        self._scan_thread: ScannerWorker | None = None
        self._animating = False  

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
            QListWidget { background: #262035; color: #eaeaea; border: 1px solid #403050; border-radius: 8px; }
            QProgressBar { background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 6px; height: 18px; }
            QProgressBar::chunk { background: #8a2be2; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

       
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(_shield_pixmap(96))
        icon.setFixedSize(96, 96)
        title = QLabel("PyOS Security Manager")
        title.setStyleSheet("font-size: 22pt; font-weight: 800; color: #ffffff;")
        header.addWidget(icon)
        header.addSpacing(12)
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
        self.btn_scan    = add_btn("Scanner")  
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
        self.pg_scan    = self._page_scanner() 

        for p in (self.pg_rt, self.pg_vtp, self.pg_account, self.pg_fw,
                  self.pg_app, self.pg_device, self.pg_perf, self.pg_scan):
            self.pages.addWidget(p)

       
        self.btn_rt.clicked.connect(lambda: self._switch_to(0))
        self.btn_vtp.clicked.connect(lambda: self._switch_to(1))
        self.btn_account.clicked.connect(lambda: self._switch_to(2))
        self.btn_fw.clicked.connect(lambda: self._switch_to(3))
        self.btn_app.clicked.connect(lambda: self._switch_to(4))
        self.btn_device.clicked.connect(lambda: self._switch_to(5))
        self.btn_perf.clicked.connect(lambda: self._switch_to(6))
        self.btn_scan.clicked.connect(lambda: self._switch_to(7))

      
        self._switch_to(0, animate=False)

    
    def _card(self, title_text: str, desc_text: str | None, toggles: list[tuple[str, str | None, str]]):
        """
        Build a card with a section title, optional description, and a set of toggles.
        Each toggle: (key, danger_message_or_None, label_text)
        """
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

    
    def _page_scanner(self):
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(4,4,4,4); lay.setSpacing(10)

        title = QLabel("Scanner")
        title.setObjectName("section")
        title.setProperty("class", "section")
        lay.addWidget(title)

        desc = QLabel("Scan your PyOS files for suspicious items. Quick Scan checks common areas; Full Scan checks everything under /PyOS.")
        desc.setObjectName("desc"); desc.setProperty("class", "desc")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        
        ctl = QHBoxLayout()
        self.btn_quick = QPushButton("▶ Quick Scan")
        self.btn_full  = QPushButton("⏱ Full Scan")
        self.btn_cancel = QPushButton("✖ Cancel")
        self.btn_cancel.setEnabled(False)
        ctl.addWidget(self.btn_quick)
        ctl.addWidget(self.btn_full)
        ctl.addStretch(1)
        ctl.addWidget(self.btn_cancel)
        lay.addLayout(ctl)

        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.lbl_current = QLabel("Idle.")
        self.lbl_current.setStyleSheet("color:#bfbfd6;")
        lay.addWidget(self.progress)
        lay.addWidget(self.lbl_current)

       
        self.results = QListWidget()
        self.results.setMinimumHeight(240)
        lay.addWidget(self.results, 1)

      
        self.btn_quick.clicked.connect(lambda: self._start_scan("quick"))
        self.btn_full.clicked.connect(lambda: self._start_scan("full"))
        self.btn_cancel.clicked.connect(self._cancel_scan)

        return page

   
    def _mark_band_active(self, active_btn: QPushButton):
        for b in self.band_buttons:
            b.setProperty("active", b is active_btn)
            b.style().unpolish(b); b.style().polish(b); b.update()

    def _switch_to(self, idx: int, animate: bool = True):
       
        if self._animating:
            return
        if idx == self.pages.currentIndex():
           
            btns = [self.btn_rt, self.btn_vtp, self.btn_account, self.btn_fw,
                    self.btn_app, self.btn_device, self.btn_perf, self.btn_scan]
            self._mark_band_active(btns[idx])
            return

        btns = [self.btn_rt, self.btn_vtp, self.btn_account, self.btn_fw,
                self.btn_app, self.btn_device, self.btn_perf, self.btn_scan]
        self._mark_band_active(btns[idx])

        old_page = self.pages.currentWidget()
    
        if old_page is not None and old_page.graphicsEffect() is not None:
            old_page.setGraphicsEffect(None)

     
        self.pages.setCurrentIndex(idx)
        new_page = self.pages.currentWidget()

        if not animate or old_page is None:
            eff = new_page.graphicsEffect()
            if eff is not None:
                new_page.setGraphicsEffect(None)
            return

        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        ne = QGraphicsOpacityEffect(new_page)
        new_page.setGraphicsEffect(ne)
        ne.setOpacity(0.0)

        anim = QPropertyAnimation(ne, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        self._animating = True

        def _cleanup():
           
            new_page.setGraphicsEffect(None)
            if old_page is not None and old_page.graphicsEffect() is not None:
                old_page.setGraphicsEffect(None)
            self._animating = False

        anim.finished.connect(_cleanup)
        anim.start()

   
    def _start_scan(self, mode: str):
        if self._scan_thread and self._scan_thread.isRunning():
            QMessageBox.information(self, "Scanner", "A scan is already running.")
            return

        self.results.clear()
        self.progress.setValue(0)
        self.lbl_current.setText("Preparing scan...")

        th = ScannerWorker(BASE_DIR, mode=mode)
        th.progress.connect(self._on_scan_progress)
        th.found.connect(self._on_scan_found)
        th.done.connect(self._on_scan_done)
        th.log.connect(self._on_scan_log)
        self._scan_thread = th

        self.btn_quick.setEnabled(False)
        self.btn_full.setEnabled(False)
        self.btn_cancel.setEnabled(True)

        th.start()

    def _cancel_scan(self):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.cancel()
            self.lbl_current.setText("Cancelling...")

   
    def _on_scan_progress(self, pct: int, path: str):
        self.progress.setValue(max(0, min(100, pct)))
        if len(path) > 90:
            path = path[:44] + " … " + path[-44:]
        self.lbl_current.setText(path)

    def _on_scan_found(self, relpath: str):
        QListWidgetItem(f"⚠ Threat: {relpath}", self.results)

    def _on_scan_done(self, scanned: int, threats: int, errors: int):
        QListWidgetItem(f"- Scan completed. Files scanned: {scanned}, threats: {threats}, errors: {errors}", self.results)
        self.btn_quick.setEnabled(True)
        self.btn_full.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_current.setText("Idle.")

    def _on_scan_log(self, msg: str):
        QListWidgetItem(f"• {msg}", self.results)
