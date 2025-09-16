from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QStyle,
    QToolButton, QVBoxLayout, QHBoxLayout, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QDateTime, QPointF, QSize, QEasingCurve,
    QPropertyAnimation, QRect, QParallelAnimationGroup, QAbstractAnimation
)
from PyQt6.QtGui import QPixmap, QFont, QIcon, QColor
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent
ICON_START   = BASE_DIR / "data" / "icons" / "start_raven.png"
ICON_SNAKE   = BASE_DIR / "data" / "icons" / "snake.png"
ICON_BROWSER = BASE_DIR / "data" / "icons" / "browser.png"
ICON_TETRIS  = BASE_DIR / "data" / "icons" / "tetris.png"
ICON_CALCULATOR = BASE_DIR / "data" / "icons" / "calculator.png"
ICON_CALENDAR   = BASE_DIR / "data" / "icons" / "calendar.png"
ICON_TERMINAL   = BASE_DIR / "data" / "icons" / "terminal.png"


if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _qcolor(v, fallback="#000000"):
    if isinstance(v, QColor):
        return v
    if isinstance(v, (tuple, list)) and 3 <= len(v) <= 4:
        return QColor(*v)
    c = QColor(str(v))
    return c if c.isValid() else QColor(fallback)

def _hex(c: QColor) -> str:
    return "#{:02X}{:02X}{:02X}".format(c.red(), c.green(), c.blue())



class AppWindow(QWidget):
    """Draggable app window with minimize/close and taskbar icon.
       Supports embedding a central widget via set_central_widget()."""
    def __init__(self, title="App", width=400, height=300, icon_pixmap=None, parent=None, desktop=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setGeometry(120, 120, width, height)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self._drag_origin = None

        self.desktop = desktop
        self.icon_pixmap = icon_pixmap
        self.taskbar_btn = None
        self._is_minimized = False
        self._content = None  

      
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setGeometry(width - 35, 5, 30, 25)
        self.close_btn.clicked.connect(self.close)

        self.min_btn = QPushButton("—", self)
        self.min_btn.setGeometry(width - 70, 5, 30, 25)
        self.min_btn.clicked.connect(self.minimize_window)

       
        self.apply_theme(self.desktop.get_theme_colors() if self.desktop else None)

        self.add_taskbar_icon()
        self.show()

    
    def apply_theme(self, theme: dict | None):
       
        window_bg = _qcolor((theme or {}).get("window_bg", "#2e2e2e"), "#2e2e2e")
        border    = _qcolor((theme or {}).get("window_border", "#555555"), "#555555")
        text      = _qcolor((theme or {}).get("text", "#ffffff"), "#ffffff")
        btn_bg    = _qcolor((theme or {}).get("button", "#666666"), "#666666")
        btn_hover = _qcolor((theme or {}).get("button_hover", "#777777"), "#777777")
        danger    = _qcolor((theme or {}).get("danger", "#b33"), "#b33")
        accent    = _qcolor((theme or {}).get("accent", "#8a2be2"), "#8a2be2")

        self.setStyleSheet(f"""
            AppWindow {{
                background-color: {_hex(window_bg)};
                border: 2px solid {_hex(border)};
                border-radius: 6px;
            }}
        """)
      
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_hex(danger)}; color: white; border:none; border-radius:4px;
            }}
            QPushButton:hover {{ filter: brightness(108%); }}
            QPushButton:pressed {{ filter: brightness(92%); }}
        """)
        self.min_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_hex(btn_bg)}; color: white; border:none; border-radius:4px;
            }}
            QPushButton:hover {{ background: {_hex(btn_hover)}; }}
            QPushButton:pressed {{ background: {_hex(accent)}; }}
        """)

    def set_central_widget(self, widget: QWidget):
        self._content = widget
        widget.setParent(self)
        widget.move(8, 35)
        widget.resize(self.width() - 16, self.height() - 43)
        widget.show()
        self.close_btn.raise_()
        self.min_btn.raise_()

    def resizeEvent(self, event):
        w = self.width()
        self.close_btn.setGeometry(w - 35, 5, 30, 25)
        self.min_btn.setGeometry(w - 70, 5, 30, 25)
        if self._content is not None:
            self._content.setGeometry(8, 35, self.width() - 16, self.height() - 43)
            self.close_btn.raise_()
            self.min_btn.raise_()
        return super().resizeEvent(event)


    def add_taskbar_icon(self):
        if not self.desktop:
            return
        btn = QPushButton(self.desktop.taskbar)
        btn.setText("")
        if self.icon_pixmap is not None and not self.icon_pixmap.isNull():
            btn.setIcon(QIcon(self.icon_pixmap))
            btn.setIconSize(self.icon_pixmap.size())
        else:
            fallback = QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_FileIcon)
            btn.setIcon(QIcon(fallback))
            btn.setIconSize(fallback.size())
        btn.setFlat(True)
        btn.setGeometry(100 + 50 * len(self.desktop.taskbar_icons), 5, 40, 40)
        btn.clicked.connect(self.toggle_min_restore)
        btn.show()
        self.taskbar_btn = btn
        self.desktop.taskbar_icons.append(btn)

    def toggle_min_restore(self):
        if self._is_minimized:
            self.showNormal()
            self.raise_()
            self.activateWindow()
            self._is_minimized = False
        else:
            self.minimize_window()

    def minimize_window(self):
        self.hide() 
        self._is_minimized = True

    def closeEvent(self, event):
        if self.taskbar_btn and self.taskbar_btn in self.desktop.taskbar_icons:
            self.taskbar_btn.deleteLater()
            self.desktop.taskbar_icons.remove(self.taskbar_btn)
        super().closeEvent(event)

  
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition()

    def mouseMoveEvent(self, event):
        if self._drag_origin:
            delta = event.globalPosition() - self._drag_origin
            self.move(self.x() + int(delta.x()), self.y() + int(delta.y()))
            self._drag_origin = event.globalPosition()

    def mouseReleaseEvent(self, event):
        self._drag_origin = None


class DesktopIcon(QLabel):
    """Draggable desktop icon with separate text label and click-to-open.
       - Very low drag threshold (≈2px)
       - Cursor-anchored dragging (no lag/offset)
       - Centered label 'pill' under icon
    """
    DRAG_THRESHOLD = 2  

    def __init__(self, name, pixmap, parent=None, on_click=lambda: None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.setFixedSize(pixmap.size())
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.on_click = on_click
        self._press_pos: QPointF | None = None       
        self._grab_offset = None                        
        self._dragging = False

      
        self.text_label = QLabel(name, parent)
        self.text_label.setStyleSheet("""
            color: #fff;
            font-family: "Segoe UI", "Inter", Arial, sans-serif;
            font-size: 11pt;
            padding: 2px 8px;
            background: rgba(0,0,0,0.28);
            border-radius: 8px;
        """)
        self.text_label.setFont(QFont("Segoe UI", 11))
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _reposition_label(self):
        self.text_label.adjustSize()
        lx = self.x() + (self.width() - self.text_label.width()) // 2
        ly = self.y() + self.height() + 5
        self.text_label.move(lx, ly)

    def set_initial_position(self, x, y):
        self.move(x, y)
        self._reposition_label()
        self.show()
        self.text_label.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position()
            self._grab_offset = self._press_pos.toPoint()
            self._dragging = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            return
        delta = event.position() - self._press_pos
        if not self._dragging and (abs(delta.x()) > self.DRAG_THRESHOLD or abs(delta.y()) > self.DRAG_THRESHOLD):
            self._dragging = True
        if self._dragging:
            global_pos = event.globalPosition().toPoint()
            new_top_left_global = global_pos - self._grab_offset
            parent_pos = self.parent().mapFromGlobal(new_top_left_global)
            self.move(parent_pos)
            self._reposition_label()

    def mouseReleaseEvent(self, event):
        try:
            if self._press_pos is not None and not self._dragging:
                if self.on_click:
                    self.on_click()
        finally:
            self._press_pos = None
            self._grab_offset = None
            self._dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)



class StartMenu(QWidget):
    """Animated Start menu: slide + fade, nicer buttons + power icon."""
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            StartMenu {
                background: rgba(30,30,33,0.96);
                border: 1px solid #444;
                border-radius: 12px;
            }
        """)
        self.setVisible(False)
        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.opacity.setOpacity(0.0)

       
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

  
        self.btn_text = QPushButton("Text Editor", self)
        self.btn_settings = QPushButton("Settings", self)
        self.btn_security = QPushButton("Security Manager", self)
      
        try:
            sec_icon_path = BASE_DIR / "data" / "icons" / "security.png"
            if sec_icon_path.exists():
                self.btn_security.setIcon(QIcon(str(sec_icon_path)))
                self.btn_security.setIconSize(QSize(18, 18))
        except Exception:
            pass


        for b in (self.btn_text, self.btn_settings, self.btn_security):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(40)
            b.setStyleSheet("""
                QPushButton {
                    color: #e9e9ef;
                    font-family: "Segoe UI", "Inter", Arial, sans-serif;
                    font-size: 12.5pt;
                    background: #3a3a3f;
                    border: 1px solid #4a4a4f;
                    border-radius: 10px;
                }
                QPushButton:hover { background: #48484e; }
                QPushButton:pressed { background: #2f2f33; }
            """)


        bottom = QHBoxLayout()
        bottom.addStretch(1)

   
        style = QApplication.instance().style()
        power_icon = QIcon.fromTheme("system-shutdown")
        if power_icon.isNull():
            for sp in (
                QStyle.StandardPixmap.SP_TitleBarCloseButton,
                QStyle.StandardPixmap.SP_BrowserStop,
                QStyle.StandardPixmap.SP_MediaStop,
            ):
                ic = style.standardIcon(sp)
                if not ic.isNull():
                    power_icon = ic
                    break

        self.btn_power = QToolButton(self)
        self.btn_power.setIcon(power_icon)
        self.btn_power.setIconSize(QSize(22, 22))
        self.btn_power.setToolTip("Shutdown")
        self.btn_power.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_power.setFixedSize(40, 40) 
        self.btn_power.setStyleSheet("""
            QToolButton {
                background: #8a2be2;       /* purple */
                border: 1px solid #5d1aa8;
                border-radius: 20px;       /* circle: radius = size/2 */
                padding: 0;
            }
            QToolButton:hover  { background: #9b3bf1; }
            QToolButton:pressed{ background: #7520cc; }
        """)
        bottom.addWidget(self.btn_power)

        root.addWidget(self.btn_text)
        root.addWidget(self.btn_settings)
        root.addWidget(self.btn_security)
        root.addLayout(bottom)

       
        self.anim_group = None
        self.target_rect = QRect()

    def set_geometry_target(self, rect: QRect):
        """Set where the menu should rest when fully open."""
        self.target_rect = QRect(rect)

    def show_animated(self):
        if self.isVisible() or self.target_rect.isNull():
            return

     
        start_rect = QRect(self.target_rect)
        start_rect.moveTop(start_rect.top() + 24) 
        self.setGeometry(start_rect)
        self.setVisible(True)

        pos_anim = QPropertyAnimation(self, b"geometry")
        pos_anim.setStartValue(start_rect)
        pos_anim.setEndValue(self.target_rect)
        pos_anim.setDuration(180)
        pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_anim = QPropertyAnimation(self.opacity, b"opacity")
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setDuration(160)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_group = QParallelAnimationGroup(self)
        self.anim_group.addAnimation(pos_anim)
        self.anim_group.addAnimation(fade_anim)
        self.anim_group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def hide_animated(self):
        if not self.isVisible():
            return

        end_rect = QRect(self.target_rect)
        end_rect.moveTop(end_rect.top() + 24)

        pos_anim = QPropertyAnimation(self, b"geometry")
        pos_anim.setStartValue(self.geometry())
        pos_anim.setEndValue(end_rect)
        pos_anim.setDuration(140)
        pos_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        fade_anim = QPropertyAnimation(self.opacity, b"opacity")
        fade_anim.setStartValue(self.opacity.opacity())
        fade_anim.setEndValue(0.0)
        fade_anim.setDuration(140)
        fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        self.anim_group = QParallelAnimationGroup(self)
        self.anim_group.addAnimation(pos_anim)
        self.anim_group.addAnimation(fade_anim)
        self.anim_group.finished.connect(lambda: self.setVisible(False))
        self.anim_group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)



class Desktop(QMainWindow):
    def __init__(self, user, fullscreen=False):
        super().__init__()
        self.user = user
        self.fullscreen = fullscreen
        self.taskbar_icons = []
        self.taskbar = None
        self.time_label = None
        self.date_label = None
        self.start_menu = None
        self.central_widget = None
        self.start_btn = None
        self.desktop_icons = []
        self.options_btn = None
        self.options_window = None



        self.init_ui()
        self.show()

   
    def get_theme_colors(self) -> dict:
        """
        Returns a color dict the apps/windows can use. Pulls from self.current_colors
        if your Settings app applied them; otherwise returns sensible defaults.
        """
        c = getattr(self, "current_colors", {}) or {}
        return {
            "window_bg":     _qcolor(c.get("window_bg", "#2e2e2e")),
            "window_border": _qcolor(c.get("window_border", "#555555")),
            "text":          _qcolor(c.get("text", "#ffffff")),
            "button":        _qcolor(c.get("button", "#666666")),
            "button_hover":  _qcolor(c.get("button_hover", "#777777")),
            "danger":        _qcolor(c.get("danger", "#b33")),
            "accent":        _qcolor(c.get("accent", "#8a2be2")),
        }

    def toggle_options(self):
        try:
            
            if getattr(self, "options_window", None) and self.options_window.isVisible():
                
                self.options_window.hide()
                return

           
            if not getattr(self, "options_window", None):
                from apps.options import OptionsApp
                self.options_window = OptionsApp(self)
                
                self.options_window.destroyed.connect(lambda: setattr(self, "options_window", None))

            
            if hasattr(self.options_window, "_position_near_clock"):
                self.options_window._position_near_clock()
            self.options_window.show()
            self.options_window.raise_()
            self.options_window.activateWindow()
        except Exception as e:
            print("Options toggle error:", e)

    def init_ui(self):
        if self.fullscreen:
            self.showFullScreen()
        else:
            self.setGeometry(100, 100, 1200, 800)

        self.setWindowTitle(f"PyOS - {self.user['username']}")

      
        self.central_widget = QWidget(self)
        self.central_widget.setGeometry(0, 0, self.width(), self.height())
        self.central_widget.setStyleSheet("background-color: #1E1E1E;")
        self.setCentralWidget(self.central_widget)

     
        self.taskbar = QWidget(self.central_widget)
        self.taskbar.setGeometry(0, self.height() - 50, self.width(), 50)
        self.taskbar.setStyleSheet("background-color: #333;")

      
        self.start_btn = QPushButton("", self.taskbar)
        self.start_btn.setGeometry(6, 3, 44, 44) 
        self.start_btn.setToolTip("Start")
        self.start_btn.setFlat(True)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.start_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; padding: 0; }
            QPushButton:hover { background: transparent; }
            QPushButton:pressed { background: transparent; }
        """)
        if ICON_START.exists():
            self.start_btn.setIcon(QIcon(str(ICON_START)))
        else:
            fallback = QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_DesktopIcon)
            self.start_btn.setIcon(QIcon(fallback))
        self.start_btn.setIconSize(self.start_btn.size())

       
        self.time_label = QLabel(self.taskbar)
        self.time_label.setStyleSheet("color: white;")
        self.time_label.setFont(QFont("Segoe UI", 12))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.time_label.setGeometry(self.width() - 120, 0, 110, 25)

        self.date_label = QLabel(self.taskbar)
        self.date_label.setStyleSheet("color: white;")
        self.date_label.setFont(QFont("Segoe UI", 10))
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.date_label.setGeometry(self.width() - 120, 25, 110, 25)

      
        self.options_btn = QToolButton(self.taskbar)
        self.options_btn.setText("⚙️")
        self.options_btn.setToolTip("Options")
        self.options_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.options_btn.setStyleSheet("QToolButton { border: none; color: white; }")
        self.options_btn.setGeometry(self.width() - 155, 11, 24, 24)
        try:
            self.options_btn.clicked.disconnect()
        except Exception:
            pass
        self.options_btn.clicked.connect(self.toggle_options)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

        
        self.start_menu = StartMenu(self.central_widget)
        self.start_btn.clicked.connect(self.toggle_start_menu)
        self._wire_start_menu_actions()
       
        self.add_icon("My Computer", QStyle.StandardPixmap.SP_ComputerIcon, 30, 30,
                      lambda: self.launch_app("File Explorer"))
        self.add_icon("Recycle Bin", QStyle.StandardPixmap.SP_TrashIcon, 130, 30,
                      lambda: self.launch_app("Recycle Bin"))

        
        if ICON_BROWSER.exists():
            self.add_icon_image("Web Browser", ICON_BROWSER, 230, 30,
                                lambda: self.launch_app("Web Browser"))
        else:
            self.add_icon("Web Browser", QStyle.StandardPixmap.SP_DriveNetIcon, 230, 30,
                          lambda: self.launch_app("Web Browser"))

      
        if ICON_SNAKE.exists():
            self.add_icon_image("Snake", ICON_SNAKE, 330, 30,
                                lambda: self.launch_app("Snake"))
        else:
            self.add_icon("Snake", QStyle.StandardPixmap.SP_MediaPlay, 330, 30,
                          lambda: self.launch_app("Snake"))

     
        if ICON_TETRIS.exists():
            self.add_icon_image("Tetris", ICON_TETRIS, 430, 30,
                                lambda: self.launch_app("Tetris"))
        else:
            self.add_icon("Tetris", QStyle.StandardPixmap.SP_MediaPlay, 430, 30,
                          lambda: self.launch_app("Tetris"))

       
        if ICON_CALCULATOR.exists():
            self.add_icon_image("Calculator", ICON_CALCULATOR, 530, 30, lambda: self.launch_app("Calculator"))
        else:
            self.add_icon("Calculator", QStyle.StandardPixmap.SP_FileDialogDetailedView, 530, 30,
                        lambda: self.launch_app("Calculator"))

        
        if ICON_CALENDAR.exists():
            self.add_icon_image("Calendar", ICON_CALENDAR, 630, 30, lambda: self.launch_app("Calendar"))
        else:
            self.add_icon("Calendar", QStyle.StandardPixmap.SP_DirHomeIcon, 630, 30,
                        lambda: self.launch_app("Calendar"))

       
        if ICON_TERMINAL.exists():
            self.add_icon_image("Command Prompt", ICON_TERMINAL, 730, 30, lambda: self.launch_app("Command Prompt"))
        else:
            self.add_icon("Command Prompt", QStyle.StandardPixmap.SP_ComputerIcon, 730, 30,
                        lambda: self.launch_app("Command Prompt"))

       
        try:
            from apps.settings import load_colors_from_disk, apply_colors_live
            saved = load_colors_from_disk()
            apply_colors_live(self, saved) 
        except Exception as e:
            print("Theme load failed:", e)
  

        
        self._position_start_menu()

  
    def _wire_start_menu_actions(self):
        self.start_menu.btn_text.clicked.connect(lambda: self._open_from_start("Text Editor"))
        self.start_menu.btn_settings.clicked.connect(lambda: self._open_from_start("Settings"))
        self.start_menu.btn_power.clicked.connect(self._shutdown_safely)
        self.start_menu.btn_security.clicked.connect(lambda: self._open_from_start("Security Manager"))


    def _shutdown_safely(self):
        """Hide menu cleanly and quit on the next event loop tick."""
        try:
            if self.start_menu and self.start_menu.isVisible():
                self.start_menu.hide_animated()
        except Exception:
            pass
        QTimer.singleShot(0, QApplication.instance().quit)

    def _open_from_start(self, app_name):
        self.start_menu.hide_animated()
        self.launch_app(app_name)

  
    def add_icon(self, name, standard_icon_enum, x, y, on_click):
        pm = QApplication.instance().style().standardPixmap(standard_icon_enum).scaled(64, 64)
        icon = DesktopIcon(name, pm, self.central_widget, on_click)
        icon.set_initial_position(x, y)
        self.desktop_icons.append(icon)

    def add_icon_image(self, name, image_path: Path, x, y, on_click):
        image_path = Path(image_path)
        if image_path.exists():
            pm = QPixmap(str(image_path))
        else:
            pm = QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_FileIcon)
        pm = pm.scaled(64, 64)
        icon = DesktopIcon(name, pm, self.central_widget, on_click)
        icon.set_initial_position(x, y)
        self.desktop_icons.append(icon)


    def _position_start_menu(self):
        """Anchor start menu to the bottom-left above the taskbar."""
        if not self.taskbar or not self.start_menu:
            return
        menu_w, menu_h = 260, 220
        margin = 6
        x = margin
        y = self.height() - self.taskbar.height() - menu_h - margin
        self.start_menu.set_geometry_target(QRect(x, y, menu_w, menu_h))
        if self.start_menu.isVisible():
            
            self.start_menu.setGeometry(self.start_menu.target_rect)

    def toggle_start_menu(self):
        if not self.start_menu:
            return
        if self.start_menu.isVisible():
            self.start_menu.hide_animated()
        else:
            self._position_start_menu()
            self.start_menu.show_animated()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        try:
            if self.taskbar is not None:
                self.taskbar.setGeometry(0, self.height() - 50, self.width(), 50)
            if self.time_label is not None:
                self.time_label.setGeometry(self.width() - 120, 0, 110, 25)
            if self.date_label is not None:
                self.date_label.setGeometry(self.width() - 120, 25, 110, 25)
            self._position_start_menu()
            if hasattr(self, "options_btn") and self.options_btn is not None:
                self.options_btn.setGeometry(self.width() - 155, 11, 24, 24)
        except Exception as e:
            print("resizeEvent (guarded) issue:", e)

   
    def update_clock(self):
        now = QDateTime.currentDateTime()
        self.time_label.setText(now.toString("HH:mm"))
        self.date_label.setText(now.toString("dd:MM:yyyy"))

   
    def launch_app(self, app_name):
        style = QApplication.instance().style()
        theme = self.get_theme_colors()

        
        if app_name == "Text Editor":
            from apps import text_editor
            text_editor.launch(self.central_widget, self)
            return
        if app_name == "Settings":
            from apps import settings
            settings.launch(self.central_widget, self)
            return
        if app_name in ("File Explorer", "My Computer"):
            from apps import file_explorer
            file_explorer.launch(self.central_widget, self)
            return
        if app_name == "Recycle Bin":
            from apps import recycle_bin
            recycle_bin.launch(self.central_widget, self)
            return
        if app_name in ("Web Browser", "Browser"):
            from apps import web_browser
            web_browser.launch(self.central_widget, self)
            return

        if app_name == "Snake":
            try:
                from apps.snake import SnakeApp
            except Exception as e:
                print("Snake module missing:", e)
                return

         
            if ICON_SNAKE.exists():
                pm = QPixmap(str(ICON_SNAKE)).scaled(24, 24)
            else:
                pm = style.standardPixmap(QStyle.StandardPixmap.SP_FileIcon).scaled(24, 24)

            win = AppWindow(title="Snake", width=720, height=540,
                            parent=self.central_widget, desktop=self, icon_pixmap=pm)
            win.apply_theme(theme)
            
            try:
                snake_widget = SnakeApp(win, theme=theme)  
            except TypeError:
                snake_widget = SnakeApp(win)               
              
                setattr(snake_widget, "theme_colors", theme)
            win.set_central_widget(snake_widget)
            win.show()
            return

        if app_name == "Tetris":
            try:
                from apps.tetris import TetrisApp
            except Exception as e:
                print("Tetris module missing:", e)
                return

            if ICON_TETRIS.exists():
                pm = QPixmap(str(ICON_TETRIS)).scaled(24, 24)
            else:
                pm = style.standardPixmap(QStyle.StandardPixmap.SP_MediaPlay).scaled(24, 24)

            win = AppWindow(title="Tetris", width=760, height=640,
                            parent=self.central_widget, desktop=self, icon_pixmap=pm)
            win.apply_theme(theme)
            
            try:
                widget = TetrisApp(win, theme=theme)
            except TypeError:
                widget = TetrisApp(win)
                setattr(widget, "theme_colors", theme)
            win.set_central_widget(widget)
            win.show()
            return

        if app_name == "Calculator":
            try:
                from apps.calculator import CalculatorApp
            except Exception as e:
                print("Calculator import failed:", e); return
            style = QApplication.instance().style()
            if ICON_CALCULATOR.exists():
                pm = QPixmap(str(ICON_CALCULATOR)).scaled(24,24)
            else:
                pm = style.standardPixmap(QStyle.StandardPixmap.SP_FileDialogDetailedView).scaled(24,24)
            win = AppWindow(title="Calculator", width=380, height=520, parent=self.central_widget, desktop=self, icon_pixmap=pm)
            theme = self.get_theme_colors()
            widget = CalculatorApp(win, theme=theme)
            win.set_central_widget(widget)
            win.apply_theme(theme)
            win.show()
            return

        if app_name == "Calendar":
            from apps.calendar import CalendarApp
            pm = QPixmap(str(ICON_CALENDAR)).scaled(24,24) if ICON_CALENDAR.exists() \
                else QApplication.instance().style().standardPixmap(QStyle.StandardPixmap.SP_DirHomeIcon).scaled(24,24)
            win = AppWindow(title="Calendar", width=900, height=580, parent=self.central_widget, desktop=self, icon_pixmap=pm)
            theme = self.get_theme_colors()
            widget = CalendarApp(win, theme=theme)
            win.set_central_widget(widget)
            win.apply_theme(theme)
            win.show()
            return


        if app_name in ("Command Prompt", "Terminal"):
            from apps import terminal
            terminal.launch(self.central_widget, self)
            return

        if app_name == "Options":
            if self.options_window and self.options_window.isVisible():
               
                self.options_window.close()
                self.options_window = None
            else:
                from apps.options import OptionsApp
                self.options_window = OptionsApp(self)
                self.options_window.show()
            return

        if app_name == "Security Manager":
            try:
                from apps.security_manager import SecurityManagerApp
            except Exception as e:
                print("Security Manager import failed:", e)
                return

        
            sec_icon = BASE_DIR / "data" / "icons" / "security.png"
            if sec_icon.exists():
                pm = QPixmap(str(sec_icon)).scaled(24, 24)
            else:
                pm = self.style().standardPixmap(QStyle.StandardPixmap.SP_MessageBoxWarning).scaled(24, 24)

         
            win = AppWindow(
                title="Security Manager",
                width=1100, height=780,  
                parent=self.central_widget, desktop=self, icon_pixmap=pm
            )



            
            widget = SecurityManagerApp(win)
            win.set_central_widget(widget)
            win.apply_theme(self.get_theme_colors())
            win.show()
            return

            
       
        pm = style.standardPixmap(QStyle.StandardPixmap.SP_FileIcon).scaled(24, 24)
        win = AppWindow(title=app_name, parent=self.central_widget, desktop=self, icon_pixmap=pm)
        win.apply_theme(theme)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    user = {"username": "DemoUser"}
    desktop = Desktop(user, fullscreen=True)
    sys.exit(app.exec())
