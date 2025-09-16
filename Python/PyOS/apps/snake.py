
from __future__ import annotations

import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint
from PyQt6.QtGui import QPainter, QFont, QPen, QBrush, QColor, QIcon
from PyQt6.QtWidgets import QWidget, QStyle


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAVE_FILE = DATA_DIR / "snake.json"
SETTINGS_FILE = DATA_DIR / "snake_settings.json"
THEME_FILE = DATA_DIR / "theme.json"
ICON_FILE = DATA_DIR / "icons" / "snake.png"


@dataclass
class Theme:
    text_color: str = "#ffffff"
    window_bg: str = "#1a1a1a"
    taskbar_color: str = "#111111"
    desktop_bg: str = "#0d0d0f"


@dataclass
class SnakeSettings:
    grid_w: int = 24
    grid_h: int = 18
    speed_ms: int = 110           
    wrap_mode: bool = True        
    show_grid: bool = True
    hud_at_bottom: bool = True    

    @classmethod
    def load(cls) -> "SnakeSettings":
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        base = asdict(cls())
        base["grid_w"] = _coerce_int(data.get("grid_w", base["grid_w"]), base["grid_w"], 6, 200)
        base["grid_h"] = _coerce_int(data.get("grid_h", base["grid_h"]), base["grid_h"], 6, 200)
        base["speed_ms"] = _coerce_int(data.get("speed_ms", base["speed_ms"]), base["speed_ms"], 30, 2000)
        base["wrap_mode"] = _coerce_bool(data.get("wrap_mode", base["wrap_mode"]), base["wrap_mode"])
        base["show_grid"] = _coerce_bool(data.get("show_grid", base["show_grid"]), base["show_grid"])
        base["hud_at_bottom"] = _coerce_bool(data.get("hud_at_bottom", base["hud_at_bottom"]), base["hud_at_bottom"])
        return cls(**base)

    def save(self) -> None:
        try:
            SETTINGS_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        except Exception as e:
            print("[Snake] Failed to save settings:", e)



def _coerce_int(v, default, lo=None, hi=None):
    try:
        i = int(v)
        if lo is not None:
            i = max(lo, i)
        if hi is not None:
            i = min(hi, i)
        return i
    except Exception:
        return default


def _coerce_bool(v, default):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "1", "yes", "y", "on"}:
            return True
        if s in {"false", "0", "no", "n", "off"}:
            return False
    return default


def _qcolor(v, default="#000000"):
    if isinstance(v, QColor):
        return v
    if isinstance(v, (tuple, list)) and 3 <= len(v) <= 4:
        return QColor(*v)
    if isinstance(v, str):
        c = QColor(v)
        if c.isValid():
            return c
    return QColor(default)


def _normalize_theme_value(v, default_hex: str) -> str:
    """Return a valid '#RRGGBB' string for QColor/tuple/hex input, else default."""
    if isinstance(v, QColor):
        return v.name()  
    if isinstance(v, (tuple, list)) and 3 <= len(v) <= 4:
        c = QColor(*v)
        return c.name() if c.isValid() else default_hex
    if isinstance(v, str):
        c = QColor(v)
        return v if c.isValid() else default_hex
    return default_hex


def _load_theme_file() -> Theme:
    try:
        data = json.loads(THEME_FILE.read_text(encoding="utf-8"))
        return Theme(
            text_color=str(data.get("text_color", Theme.text_color)),
            window_bg=str(data.get("window_bg", Theme.window_bg)),
            taskbar_color=str(data.get("taskbar_color", Theme.taskbar_color)),
            desktop_bg=str(data.get("desktop_bg", Theme.desktop_bg)),
        )
    except Exception:
        return Theme()


def _load_save() -> dict:
    try:
        return json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"high_score": 0}


def _save_save(obj: dict) -> None:
    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        SAVE_FILE.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception as e:
        print("[Snake] Failed to persist save:", e)



class SnakeApp(QWidget):
    """
    Controls:
      • Arrow Keys / WASD - move
      • Space - pause/resume
      • R - restart
      • + / - - change speed
      • G - toggle grid
      • B - toggle HUD position (bottom/top)
      • Esc - close window (let the parent handle it if embedded)
    """

    PADDING = 8  

    def __init__(self, parent=None, theme: dict | None = None):
        super().__init__(parent)
     
        try:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self.setMinimumSize(560, 460)

           
            try:
                if ICON_FILE.exists():
                    self.setWindowIcon(QIcon(str(ICON_FILE)))
                else:
                    self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
            except Exception as e:
                print("[Snake] Icon setup failed:", e)

           
            if theme:
                self.theme = Theme(
                    text_color=_normalize_theme_value(theme.get("text"), Theme.text_color),
                    window_bg=_normalize_theme_value(theme.get("window_bg"), Theme.window_bg),
                    taskbar_color=_normalize_theme_value(theme.get("taskbar_color"), Theme.taskbar_color),
                    desktop_bg=_normalize_theme_value(theme.get("desktop_bg"), Theme.desktop_bg),
                )
            else:
                self.theme = _load_theme_file()

            
            self._grid_color = _qcolor(self.theme.text_color).darker(300)  
            self._hud_bg = _qcolor(self.theme.window_bg).darker(115)

       
            self.settings = SnakeSettings.load()

       
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._tick)
            self.tick_ms = int(max(30, self.settings.speed_ms)) 
            self.timer.start(self.tick_ms)

            
            self.grid_w = int(max(6, self.settings.grid_w))
            self.grid_h = int(max(6, self.settings.grid_h))
            self.cell = 24  

           
            self.score = 0
            self.high_score = int(_load_save().get("high_score", 0))
            self.paused = False
            self.game_over = False
            self.wrap_mode = bool(self.settings.wrap_mode)
            self.show_grid = bool(self.settings.show_grid)
            self.hud_bottom = bool(self.settings.hud_at_bottom)

            
            self.dir = QPoint(1, 0)      
            self.next_dir = QPoint(1, 0)

            
            cx, cy = self.grid_w // 2, self.grid_h // 2
            self.snake: list[QPoint] = [QPoint(cx - i, cy) for i in range(4)]
            self.food = self._rand_food()
        except Exception as e:
            print("[Snake] __init__ failed:", e)

   
    def _compute_layout(self):
        """Compute board rect, HUD rect, and cell size based on current widget size."""
        pad = self.PADDING
        W = max(1, self.width() - 2 * pad)
        H = max(1, self.height() - 2 * pad)

      
        base_hud = 32

        avail_w, avail_h = W, max(1, H - base_hud)
        cell_guess = min(avail_w // self.grid_w, avail_h // self.grid_h)
        hud_h = max(28, int(max(28, cell_guess) * 0.9))

        avail_h = max(1, H - hud_h)
        cell = max(10, min(W // self.grid_w, avail_h // self.grid_h))
        board_w = cell * self.grid_w
        board_h = cell * self.grid_h

        board_x = pad + (W - board_w) // 2
        if self.hud_bottom:
            board_y = pad
            hud_y = pad + board_h
        else:
            board_y = pad + hud_h
            hud_y = pad

        board_rect = QRectF(board_x, board_y, board_w, board_h)
        hud_rect = QRectF(pad, hud_y, W, hud_h)
        return cell, board_rect, hud_rect

    
    def resizeEvent(self, event):
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        
        p.fillRect(self.rect(), QBrush(_qcolor(self.theme.window_bg)))

      
        self.cell, board_rect, hud_rect = self._compute_layout()

       
        if self.show_grid:
            grid_pen = QPen(self._grid_color)
            grid_pen.setWidth(1)
            grid_pen.setCosmetic(True)
            p.setPen(grid_pen)
            for x in range(self.grid_w + 1):
                X = int(board_rect.left() + x * self.cell)
                p.drawLine(X, int(board_rect.top()), X, int(board_rect.bottom()))
            for y in range(self.grid_h + 1):
                Y = int(board_rect.top() + y * self.cell)
                p.drawLine(int(board_rect.left()), Y, int(board_rect.right()), Y)

        
        p.setPen(Qt.PenStyle.NoPen)
        head_brush = QBrush(Qt.BrushStyle.SolidPattern)
        body_brush = QBrush(Qt.BrushStyle.SolidPattern)

        for i, pt in enumerate(self.snake):
            x = int(board_rect.left() + pt.x() * self.cell)
            y = int(board_rect.top() + pt.y() * self.cell)
            rect = QRectF(x + 1, y + 1, self.cell - 2, self.cell - 2)
            if i == 0:
                head_brush.setColor(_qcolor("#FFFFFF"))
                p.setBrush(head_brush)
            else:
                body_brush.setColor(_qcolor("#A0A0A0"))
                p.setBrush(body_brush)
            p.drawRect(rect)

        fx = int(board_rect.left() + self.food.x() * self.cell)
        fy = int(board_rect.top() + self.food.y() * self.cell)
        p.setBrush(QBrush(_qcolor("#E85050")))
        p.drawEllipse(QRectF(fx + 3, fy + 3, self.cell - 6, self.cell - 6))

      
        self._paint_hud(p, hud_rect)

       
        if self.paused:
            self._overlay_text(p, board_rect, ["PAUSED", "Space to resume"])
        elif self.game_over:
            self._overlay_text(p, board_rect, ["GAME OVER", "R to restart"])

        p.end()

    def _paint_hud(self, p: QPainter, hud_rect: QRectF):
        p.fillRect(hud_rect, QBrush(self._hud_bg))

        p.setPen(QPen(_qcolor(self.theme.text_color)))
        font = QFont("Segoe UI, Inter, Arial", max(12, int(hud_rect.height() * 0.55)))
        font.setBold(True)
        p.setFont(font)

        left_text = f"Score: {self.score}"
        right_text = f"High: {self.high_score}   {'Wrap' if self.wrap_mode else 'Walls'}   {self.tick_ms}ms"

        p.drawText(
            hud_rect.adjusted(10, 0, -10, 0),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            left_text,
        )
        p.drawText(
            hud_rect.adjusted(10, 0, -10, 0),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
            right_text,
        )

    def _overlay_text(self, p: QPainter, rect: QRectF, lines: list[str]):
        """Dim background and center each line cleanly (no overlap/glitch)."""
        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 140)))
        p.drawRect(rect)

        
        p.setPen(_qcolor(self.theme.text_color))
        font = QFont("Segoe UI, Inter, Arial", max(14, int(self.cell * 0.9)))
        font.setBold(True)
        p.setFont(font)
        fm = p.fontMetrics()

       
        line_h = fm.height()
        total_h = len(lines) * line_h
        y = int(rect.top() + (rect.height() - total_h) / 2 + fm.ascent())

        for ln in lines:
            w = fm.horizontalAdvance(ln)
            x = int(rect.left() + (rect.width() - w) / 2)
            p.drawText(x, y, ln)
            y += line_h

  
    def _tick(self):
        if self.paused or self.game_over:
            self.update()
            return

        if (self.next_dir + self.dir) != QPoint(0, 0):
            self.dir = QPoint(self.next_dir)

        new_head = QPoint(self.snake[0].x() + self.dir.x(), self.snake[0].y() + self.dir.y())

        if self.wrap_mode:
            new_head.setX((new_head.x() + self.grid_w) % self.grid_w)
            new_head.setY((new_head.y() + self.grid_h) % self.grid_h)
        else:
            if not (0 <= new_head.x() < self.grid_w and 0 <= new_head.y() < self.grid_h):
                self._set_game_over()
                return

        if new_head in self.snake:
            self._set_game_over()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            if self.score > self.high_score:
                self.high_score = self.score
                _save_save({"high_score": self.high_score})
            self.food = self._rand_food()
        else:
            self.snake.pop()

        self.update()

    def _rand_food(self) -> QPoint:
        free = {(x, y) for x in range(self.grid_w) for y in range(self.grid_h)} - {(p.x(), p.y()) for p in self.snake}
        if not free:
            return QPoint(0, 0)
        x, y = random.choice(list(free))
        return QPoint(x, y)

    def _set_game_over(self):
        self.game_over = True
        self.timer.stop()
        self.update()

    def _restart(self):
        self.score = 0
        self.paused = False
        self.game_over = False
        self.dir = QPoint(1, 0)
        self.next_dir = QPoint(1, 0)
        cx, cy = self.grid_w // 2, self.grid_h // 2
        self.snake = [QPoint(cx - i, cy) for i in range(4)]
        self.food = self._rand_food()
        self.timer.start(self.tick_ms)
        self.update()

  
    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            if self.dir.x() != 1:
                self.next_dir = QPoint(-1, 0)
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            if self.dir.x() != -1:
                self.next_dir = QPoint(1, 0)
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            if self.dir.y() != 1:
                self.next_dir = QPoint(0, -1)
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            if self.dir.y() != -1:
                self.next_dir = QPoint(0, 1)

        elif key == Qt.Key.Key_Space:
            if not self.game_over:
                self.paused = not self.paused
                if self.paused:
                    self.timer.stop()
                else:
                    self.timer.start(self.tick_ms)
                self.update()
        elif key == Qt.Key.Key_R:
            self._restart()
        elif key == Qt.Key.Key_Escape:
            parent = self.window()
            try:
                parent.close()
            except Exception:
                pass

        
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._set_speed(max(30, self.tick_ms - 10))
        elif key == Qt.Key.Key_Minus:
            self._set_speed(min(1000, self.tick_ms + 10))
        elif key == Qt.Key.Key_G:
            self.show_grid = not self.show_grid
            self.settings.show_grid = self.show_grid
            self.settings.save()
            self.update()
        elif key == Qt.Key.Key_B:
            self.hud_bottom = not self.hud_bottom
            self.settings.hud_at_bottom = self.hud_bottom
            self.settings.save()
            self.update()
        else:
            super().keyPressEvent(event)

    def _set_speed(self, ms: int):
        self.tick_ms = int(ms)
        self.timer.stop()
        self.timer.start(self.tick_ms)
        self.settings.speed_ms = self.tick_ms
        self.settings.save()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    w = SnakeApp()  
    w.setWindowTitle("Snake - PyOS")
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec())
