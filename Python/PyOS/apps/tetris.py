
from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget
from pathlib import Path
import json
import random

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SETTINGS_PATH = DATA_DIR / "tetris_settings.json"
SCORES_PATH   = DATA_DIR / "tetris_scores.json"

def _qcolor(v, default="#000000"):
    """Safely convert hex/tuple/QColor to QColor."""
    if isinstance(v, QColor):
        return v
    if isinstance(v, (tuple, list)) and 3 <= len(v) <= 4:
        return QColor(*v)
    if isinstance(v, str):
        c = QColor(v)
        if c.isValid():
            return c
    return QColor(default)

DEFAULTS = {
    "board_w": 10,
    "board_h": 20,
    "sidebar_w": 180,
    "speed_ms": 500,     
    "bg_color": "#202225",
    "grid_color": "#2b2f34",
    "frame_color": "#4c525a",
    "hud_text_color": "#ffffff",
    "ghost_color": "#ffffff",
    "ghost_alpha": 60,   
    "draw_grid": True,
    "soft_drop_points": 1,
    "hard_drop_points": 2,
}


PIECE_COLORS = {
    "I": "#00cbe6", 
    "O": "#e6d300", 
    "T": "#a653e6",  
    "S": "#4ad153",  
    "Z": "#e64d4d", 
    "J": "#4a71d1",
    "L": "#e69b32",  
}


SHAPES = {
    "I": [
        [(0,1),(1,1),(2,1),(3,1)],
        [(2,0),(2,1),(2,2),(2,3)],
        [(0,2),(1,2),(2,2),(3,2)],
        [(1,0),(1,1),(1,2),(1,3)],
    ],
    "O": [
        [(1,1),(2,1),(1,2),(2,2)],
        [(1,1),(2,1),(1,2),(2,2)],
        [(1,1),(2,1),(1,2),(2,2)],
        [(1,1),(2,1),(1,2),(2,2)],
    ],
    "T": [
        [(1,0),(0,1),(1,1),(2,1)],
        [(1,0),(1,1),(2,1),(1,2)],
        [(0,1),(1,1),(2,1),(1,2)],
        [(1,0),(0,1),(1,1),(1,2)],
    ],
    "S": [
        [(1,0),(2,0),(0,1),(1,1)],
        [(1,0),(1,1),(2,1),(2,2)],
        [(1,1),(2,1),(0,2),(1,2)],
        [(0,0),(0,1),(1,1),(1,2)],
    ],
    "Z": [
        [(0,0),(1,0),(1,1),(2,1)],
        [(2,0),(1,1),(2,1),(1,2)],
        [(0,1),(1,1),(1,2),(2,2)],
        [(1,0),(0,1),(1,1),(0,2)],
    ],
    "J": [
        [(0,0),(0,1),(1,1),(2,1)],
        [(1,0),(2,0),(1,1),(1,2)],
        [(0,1),(1,1),(2,1),(2,2)],
        [(1,0),(1,1),(0,2),(1,2)],
    ],
    "L": [
        [(2,0),(0,1),(1,1),(2,1)],
        [(1,0),(1,1),(1,2),(2,2)],
        [(0,1),(1,1),(2,1),(0,2)],
        [(0,0),(1,0),(1,1),(1,2)],
    ],
}
BAG_ORDER = list(SHAPES.keys())

def load_settings():
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except Exception:
        data = {}
    out = DEFAULTS.copy()
    out.update({k:v for k,v in data.items() if k in DEFAULTS})
  
    out["board_w"] = max(6, int(out["board_w"]))
    out["board_h"] = max(10, int(out["board_h"]))
    out["sidebar_w"] = max(120, int(out["sidebar_w"]))
    out["speed_ms"] = max(80, int(out["speed_ms"]))
    out["ghost_alpha"] = max(0, min(255, int(out["ghost_alpha"])))
    out["draw_grid"] = bool(out["draw_grid"])
    out["soft_drop_points"] = max(0, int(out["soft_drop_points"]))
    out["hard_drop_points"] = max(0, int(out["hard_drop_points"]))
    return out

def load_highscore():
    try:
        if SCORES_PATH.exists():
            with open(SCORES_PATH, "r", encoding="utf-8") as f:
                o = json.load(f)
                return int(o.get("highscore", 0))
    except Exception:
        pass
    return 0

def save_highscore(score):
    try:
        SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SCORES_PATH, "w", encoding="utf-8") as f:
            json.dump({"highscore": int(score)}, f)
    except Exception:
        pass


class TetrisApp(QWidget):
    """Tetris widget embedded inside an AppWindow (see desktop.launch_app)."""
    def __init__(self, parent=None, theme: dict | None = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(560, 540) 
        self.s = load_settings()


        if theme:
        
            self.bg_color = _qcolor(theme.get("window_bg", self.s["bg_color"]), self.s["bg_color"])
         
            self.frame_color = _qcolor(theme.get("window_border", self.s["frame_color"]), self.s["frame_color"])
       
            self.hud_text = _qcolor(theme.get("text", self.s["hud_text_color"]), self.s["hud_text_color"])
          
            derived_grid = QColor(self.hud_text)
            derived_grid = derived_grid.darker(300)
            self.grid_color = _qcolor(theme.get("grid_color", derived_grid), self.s["grid_color"])
        else:
           
            self.bg_color     = _qcolor(self.s["bg_color"], "#202225")
            self.grid_color   = _qcolor(self.s["grid_color"], "#2b2f34")
            self.frame_color  = _qcolor(self.s["frame_color"], "#4c525a")
            self.hud_text     = _qcolor(self.s["hud_text_color"], "#ffffff")

        self.ghost_color  = _qcolor(self.s["ghost_color"], "#ffffff")
        self.ghost_alpha  = self.s["ghost_alpha"]


        self.BW = self.s["board_w"]
        self.BH = self.s["board_h"]
        self.SIDEBAR = self.s["sidebar_w"]

     
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.level = 1
        self.score = 0
        self.lines_cleared = 0
        self.highscore = load_highscore()

        self.board = [[None for _ in range(self.BW)] for _ in range(self.BH)]
        self.current = None 
        self.next_queue = []
        self.paused = False
        self.game_over = False

        self._refill_bag()
        self._spawn_piece()
        self._update_speed()
        self.timer.start(self._current_speed)

   
    def _refill_bag(self):
        bag = BAG_ORDER[:]
        random.shuffle(bag)
        self.next_queue += bag

    def _spawn_piece(self):
        if len(self.next_queue) < 7:
            self._refill_bag()
        shape = self.next_queue.pop(0)
        rot = 0
        x = (self.BW - 4) // 2
        y = 0
        self.current = [shape, rot, x, y]
        if self._collides(shape, rot, x, y):
            self.game_over = True
            self.timer.stop()
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)

    def _cells(self, shape, rot, x, y):
        for (cx, cy) in SHAPES[shape][rot]:
            yield (x + cx, y + cy)

    def _collides(self, shape, rot, x, y):
        for (cx, cy) in self._cells(shape, rot, x, y):
            if cx < 0 or cx >= self.BW or cy < 0 or cy >= self.BH:
                return True
            if self.board[cy][cx] is not None:
                return True
        return False

    def _lock_piece(self):
        shape, rot, x, y = self.current
        color = _qcolor(PIECE_COLORS.get(shape, "#cccccc"), "#cccccc")
        for (cx, cy) in self._cells(shape, rot, x, y):
            if 0 <= cy < self.BH and 0 <= cx < self.BW:
                self.board[cy][cx] = color
        self._clear_lines()
        self._spawn_piece()

    def _clear_lines(self):
        new_rows = [row for row in self.board if any(cell is None for cell in row)]
        cleared = self.BH - len(new_rows)
        if cleared > 0:
            self.lines_cleared += cleared
            self.score += (40, 100, 300, 1200)[cleared-1] * self.level
            
            for _ in range(cleared):
                new_rows.insert(0, [None for _ in range(self.BW)])
            self.board = new_rows
            
            self.level = 1 + self.lines_cleared // 10
            self._update_speed()

    def _update_speed(self):
        
        base = self.s["speed_ms"]
        self._current_speed = max(80, int(base - (self.level-1)*35))
        if self.timer.isActive():
            self.timer.start(self._current_speed)

    def hard_drop_distance(self, shape, rot, x, y):
        d = 0
        while not self._collides(shape, rot, x, y + d + 1):
            d += 1
        return d

    def rotate(self, dir=1):
        if not self.current or self.paused or self.game_over:
            return
        shape, rot, x, y = self.current
        new_rot = (rot + dir) % 4
      
        for dx in (0, -1, 1, -2, 2):
            if not self._collides(shape, new_rot, x + dx, y):
                self.current[1] = new_rot
                self.current[2] = x + dx
                self.update()
                return

    def move(self, dx, dy):
        if not self.current or self.paused or self.game_over:
            return
        shape, rot, x, y = self.current
        nx, ny = x + dx, y + dy
        if not self._collides(shape, rot, nx, ny):
            self.current[2], self.current[3] = nx, ny
            
            if dy > 0 and dx == 0:
                self.score += self.s["soft_drop_points"]
            self.update()
        elif dy > 0 and dx == 0:
            
            self._lock_piece()
            self.update()

    def hard_drop(self):
        if not self.current or self.paused or self.game_over:
            return
        shape, rot, x, y = self.current
        d = self.hard_drop_distance(shape, rot, x, y)
        self.current[3] += d
        self.score += d * self.s["hard_drop_points"]
        self._lock_piece()
        self.update()

    def tick(self):
        if self.paused or self.game_over:
            return
        self.move(0, 1)

 
    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.move(-1, 0)
        elif k in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.move(1, 0)
        elif k in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.move(0, 1)
        elif k in (Qt.Key.Key_Up,):
            self.rotate(+1)
        elif k in (Qt.Key.Key_Z,):
            self.rotate(-1)
        elif k in (Qt.Key.Key_X,):
            self.rotate(+1)
        elif k in (Qt.Key.Key_Space,):
            self.hard_drop()
        elif k in (Qt.Key.Key_P,):
            self.paused = not self.paused
            self.update()
        elif k in (Qt.Key.Key_N, Qt.Key.Key_R):
            self.new_game()
        elif k in (Qt.Key.Key_G,): 
            self.s["draw_grid"] = not self.s["draw_grid"]
            self.update()
        else:
            super().keyPressEvent(e)

    def new_game(self):
        self.level = 1
        self.score = 0
        self.lines_cleared = 0
        self.board = [[None for _ in range(self.BW)] for _ in range(self.BH)]
        self.next_queue.clear()
        self._refill_bag()
        self._spawn_piece()
        self.game_over = False
        self.paused = False
        self._update_speed()
        self.update()

    def _layout_metrics(self):
        w = max(1, self.width())
        h = max(1, self.height())
        sb = self.SIDEBAR
        cell = min((w - sb - 24) // self.BW, (h - 24) // self.BH)
        cell = max(14, int(cell))
        grid_w = cell * self.BW
        grid_h = cell * self.BH
        gx = 12
        gy = (h - grid_h) // 2
        sdx = gx + grid_w + 12
        return cell, gx, gy, grid_w, grid_h, sdx, 12, h - 24

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QBrush(self.bg_color))

        cell, gx, gy, grid_w, grid_h, sdx, sdy, sd_h = self._layout_metrics()

        
        p.setPen(QPen(self.frame_color, 2))
        p.drawRect(gx-1, gy-1, grid_w+2, grid_h+2)

       
        if self.s["draw_grid"]:
            p.setPen(QPen(self.grid_color, 1))
            for x in range(self.BW+1):
                X = gx + x*cell
                p.drawLine(X, gy, X, gy+grid_h)
            for y in range(self.BH+1):
                Y = gy + y*cell
                p.drawLine(gx, Y, gx+grid_w, Y)

       
        for y in range(self.BH):
            for x in range(self.BW):
                col = self.board[y][x]
                if col is not None:
                    self._draw_cell(p, gx, gy, cell, x, y, col)

        
        if self.current and not self.game_over:
            shape, rot, x, y = self.current
            d = self.hard_drop_distance(shape, rot, x, y)
            ghost = QColor(self.ghost_color)
            ghost.setAlpha(self.ghost_alpha)
            for (cx, cy) in self._cells(shape, rot, x, y + d):
                self._draw_cell(p, gx, gy, cell, cx, cy, ghost)

        
        if self.current and not self.game_over:
            shape, rot, x, y = self.current
            col = _qcolor(PIECE_COLORS.get(shape, "#cccccc"))
            for (cx, cy) in self._cells(shape, rot, x, y):
                self._draw_cell(p, gx, gy, cell, cx, cy, col)

        
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 30)))
        p.drawRoundedRect(sdx, sdy, self.SIDEBAR-24, sd_h, 10, 10)

        
        p.setPen(self.hud_text)
        p.setFont(QFont("Segoe UI", 12))
        y = sdy + 8
        def line(txt):
            nonlocal y
            p.drawText(sdx+12, y+18, txt)
            y += 26

        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(sdx+12, y+22, "TETRIS")
        y += 36
        p.setFont(QFont("Segoe UI", 12))
        line(f"Score: {self.score}")
        line(f"High:  {self.highscore}")
        line(f"Level: {self.level}")
        line(f"Lines: {self.lines_cleared}")
        y += 10
        p.drawText(sdx+12, y+22, "Next:")
        y += 36

      
        if self.next_queue:
            shape = self.next_queue[0]
            preview_cell = int(cell * 0.8)
            box_w = 4 * preview_cell
            box_h = 4 * preview_cell
            bx = sdx + (self.SIDEBAR-24 - box_w)//2
            by = y
            pc = _qcolor(PIECE_COLORS.get(shape, "#cccccc"))
            for (cx, cy) in SHAPES[shape][0]:
                rx = bx + cx*preview_cell
                ry = by + cy*preview_cell
                p.setPen(QPen(QColor(0,0,0,160), 1))
                p.setBrush(QBrush(pc))
                p.drawRoundedRect(rx+1, ry+1, preview_cell-2, preview_cell-2, 4, 4)

     
        if self.paused:
            self._overlay(p, "PAUSED")
        if self.game_over:
            self._overlay(p, "GAME OVER\nN = New Game")

        p.end()

    def _overlay(self, p: QPainter, text: str):
      
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0, 140)))
        p.drawRect(self.rect())

      
        p.setPen(self.hud_text)
        p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        fm = p.fontMetrics()

        lines = [ln for ln in text.splitlines() if ln.strip() != ""]
        line_h = fm.height()
        total_h = len(lines) * line_h
        y = (self.height() - total_h) // 2 + fm.ascent()

        for ln in lines:
            w = fm.horizontalAdvance(ln)
            x = (self.width() - w) // 2
            p.drawText(x, y, ln)
            y += line_h

    def _draw_cell(self, p: QPainter, gx, gy, cell, x, y, color: QColor):
        X = gx + x*cell
        Y = gy + y*cell
        p.setPen(QPen(QColor(0,0,0,160), 1))
        p.setBrush(QBrush(color))
        p.drawRoundedRect(X+1, Y+1, cell-2, cell-2, 4, 4)


def launch(container_parent, desktop=None):
    from desktop import AppWindow
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap
    style = QApplication.instance().style()
    pm = style.standardPixmap(style.StandardPixmap.SP_FileIcon).scaled(24,24)
    win = AppWindow(title="Tetris", width=760, height=640, parent=container_parent, desktop=desktop, icon_pixmap=pm)
    widget = TetrisApp(win)
    win.set_central_widget(widget)
    win.show()
