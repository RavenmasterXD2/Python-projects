
from __future__ import annotations

import ast
import operator as op
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QSizePolicy, QStyle
)


_ALLOWED = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Mod: op.mod, ast.Pow: op.pow, ast.USub: op.neg, ast.UAdd: op.pos,
    ast.FloorDiv: op.floordiv,
}
def _eval_ast(node):
    if isinstance(node, ast.Num):         
        return node.n
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("const")
    if isinstance(node, ast.BinOp):
        return _ALLOWED[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        return _ALLOWED[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.Expr):
        return _eval_ast(node.value)
    raise ValueError("bad expr")

def safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")
    return _eval_ast(tree.body)

def _qcolor(v, default="#000000"):
    c = QColor(v)
    return c if c.isValid() else QColor(default)


class CalculatorApp(QWidget):
    """
    Theme-aware calculator.
    Accepts theme=dict with keys: window_bg, text, button, button_hover, accent
    """
    def __init__(self, parent=None, theme: dict | None = None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        
        
        def col(key, fallback):
            v = (theme or {}).get(key, fallback)
            return v.name() if isinstance(v, QColor) else str(v)
        self.col_bg     = col("window_bg",     "#1f1f1f")
        self.col_text   = col("text",          "#ffffff")
        self.col_btn    = col("button",        "#303030")
        self.col_btn_h  = col("button_hover",  "#3a3a3a")
        self.col_accent = col("accent",        "#8a2be2")

        
        self.display = QLineEdit(self)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setReadOnly(False)
        self.display.setText("")
        self.display.setPlaceholderText("0")
        self.display.setFont(QFont("Segoe UI", 20))
        self.display.setStyleSheet(f"""
            QLineEdit {{
                background: {self.col_bg};
                color: {self.col_text};
                border: 2px solid #555;
                border-radius: 8px;
                padding: 14px;
                selection-background-color: {self.col_accent};
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(8)
        root.addLayout(grid)

        
        buttons = [
            ("C",  0,0,1,1,"fn"),  ("⌫", 0,1,1,1,"fn"), ("(", 0,2,1,1,"fn"), (")", 0,3,1,1,"fn"),
            ("7",  1,0,1,1,"num"), ("8", 1,1,1,1,"num"), ("9", 1,2,1,1,"num"), ("÷", 1,3,1,1,"op"),
            ("4",  2,0,1,1,"num"), ("5", 2,1,1,1,"num"), ("6", 2,2,1,1,"num"), ("×", 2,3,1,1,"op"),
            ("1",  3,0,1,1,"num"), ("2", 3,1,1,1,"num"), ("3", 3,2,1,1,"num"), ("−", 3,3,1,1,"op"),
            ("±",  4,0,1,1,"fn"),  ("0", 4,1,1,1,"num"), (".", 4,2,1,1,"num"), ("+", 4,3,1,1,"op"),
            ("=",  5,0,1,4,"eq"),
        ]

        for text, r, c, rs, cs, kind in buttons:
            b = QPushButton(text, self)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            b.setMinimumHeight(48)
            if kind == "eq":
                b.setStyleSheet(f"""
                    QPushButton {{ background: {self.col_accent}; color: white; border: none; border-radius: 10px; }}
                    QPushButton:hover {{ filter: brightness(1.06); }}
                    QPushButton:pressed {{ filter: brightness(0.92); }}
                """)
            elif kind == "op":
                b.setStyleSheet(f"""
                    QPushButton {{ background: {self.col_btn}; color: {self.col_accent}; border: 1px solid #4a4a4a; border-radius: 10px; }}
                    QPushButton:hover {{ background: {self.col_btn_h}; }}
                """)
            elif kind == "fn":
                b.setStyleSheet(f"""
                    QPushButton {{ background: {self.col_btn}; color: {self.col_text}; border: 1px solid #4a4a4a; border-radius: 10px; }}
                    QPushButton:hover {{ background: {self.col_btn_h}; }}
                """)
            else:  
                b.setStyleSheet(f"""
                    QPushButton {{ background: {self.col_btn}; color: {self.col_text}; border: 1px solid #4a4a4a; border-radius: 10px; }}
                    QPushButton:hover {{ background: {self.col_btn_h}; }}
                """)
            b.clicked.connect(lambda _, t=text: self.on_button(t))
            grid.addWidget(b, r, c, rs, cs)

       
        for ch in "0123456789.+-*/()":
            act = QAction(self)
            act.setShortcut(ch)
            act.triggered.connect(lambda _, t=ch: self.on_key_char(t))
            self.addAction(act)
        
        enter = QAction(self); enter.setShortcut(Qt.Key.Key_Return); enter.triggered.connect(lambda: self.on_button("=")); self.addAction(enter)
        enter2= QAction(self); enter2.setShortcut(Qt.Key.Key_Enter);  enter2.triggered.connect(lambda: self.on_button("=")); self.addAction(enter2)
        bk   = QAction(self); bk.setShortcut(Qt.Key.Key_Backspace); bk.triggered.connect(lambda: self.on_button("⌫")); self.addAction(bk)
        esc  = QAction(self); esc.setShortcut(Qt.Key.Key_Escape); esc.triggered.connect(lambda: self.window().close()); self.addAction(esc)

        self.setStyleSheet(f"background:{self.col_bg};")

    
    def on_key_char(self, ch: str):
        text = self.display.text()
        repl = ch.replace("*", "×").replace("/", "÷").replace("-", "−")
        self.display.setText(text + repl)

    def on_button(self, t: str):
        txt = self.display.text()
        if t == "C":
            self.display.clear()
            return
        if t == "⌫":
            self.display.setText(txt[:-1])
            return
        if t == "±":
            if txt.startswith("−"):
                self.display.setText(txt[1:])
            elif txt.startswith("-"):
                self.display.setText(txt[1:])
            else:
                self.display.setText("−" + txt)
            return
        if t == "=":
            self.evaluate()
            return
        
        self.display.setText(txt + t)

    def _normalized(self, s: str) -> str:
        
        return (s.replace("×", "*")
                 .replace("÷", "/")
                 .replace("−", "-")
                 .replace(",", "."))

    def evaluate(self):
        expr = self._normalized(self.display.text().strip())
        if not expr:
            return
        try:
            val = safe_eval(expr)
            
            if int(val) == val:
                self.display.setText(str(int(val)))
            else:
                self.display.setText(str(val))
        except Exception:
            self.display.setText("Error")


def launch(container_parent, desktop=None):
    from desktop import AppWindow
    from PyQt6.QtWidgets import QApplication
    style = QApplication.instance().style()
    pm = style.standardPixmap(QStyle.StandardPixmap.SP_FileDialogDetailedView).scaled(24,24)
    win = AppWindow(title="Calculator", width=380, height=520, parent=container_parent, desktop=desktop, icon_pixmap=pm)
    theme = desktop.get_theme_colors() if desktop else {}
    widget = CalculatorApp(win, theme=theme)
    win.set_central_widget(widget)
    win.apply_theme(theme if desktop else None)
    win.show()
