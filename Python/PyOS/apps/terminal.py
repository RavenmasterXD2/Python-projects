# apps/terminal.py
from __future__ import annotations

import os
import re
import shlex
import sys
import time
import platform
from pathlib import Path
from typing import Callable, Dict, List, Tuple

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import (
    QColor, QFont, QTextCursor, QAction, QKeySequence, QDesktopServices, QTextOption, QIcon
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QLabel,
    QSizePolicy, QStyle, QApplication, QCompleter
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]  
DATA_DIR = PROJECT_ROOT / "data"
ICON_FILE = DATA_DIR / "icons" / "terminal.png"


def _hx(v, default="#d7d7d7") -> str:
    if isinstance(v, QColor):
        return v.name()
    if isinstance(v, (tuple, list)) and 3 <= len(v) <= 4:
        c = QColor(*v)
        return c.name() if c.isValid() else default
    if isinstance(v, str):
        c = QColor(v)
        return v if c.isValid() else default
    return default

def clamp_to_root(path: Path) -> Path:
    """Prevent escaping the project root."""
    try:
        p = path.resolve()
    except Exception:
        p = path
    try:
        if PROJECT_ROOT in p.parents or p == PROJECT_ROOT:
            return p
    except Exception:
        pass
    return PROJECT_ROOT

def human_size(n: int) -> str:
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024.0
    return f"{n:.0f}PB"

class TerminalApp(QWidget):
    """
    PyOS Command Prompt with many commands.
    Accepts theme=dict keys: window_bg, text, accent, button, button_hover
    """

    PROMPT_SYM = ">"
    PAGER_LINES = 18

    def __init__(self, parent=None, theme: dict | None = None):
        super().__init__(parent)
        self.theme = theme or {}
        self.cwd: Path = PROJECT_ROOT
        self.history: List[str] = []
        self.hist_index: int = -1
        self._more_active: bool = False
        self._more_buffer: List[str] = []
        self._more_title: str = ""
        self._killed: bool = False

        
        self.col_bg   = _hx(self.theme.get("window_bg", "#16161a"))
        self.col_tx   = _hx(self.theme.get("text", "#eaeaea"))
        self.col_ac   = _hx(self.theme.get("accent", "#8a2be2"))
        self.col_dim  = "#9aa1ac"

       
        try:
            if ICON_FILE.exists():
                self.setWindowIcon(QIcon(str(ICON_FILE)))
        except Exception:
            pass

       
        self.out = QPlainTextEdit(self)
        self.out.setReadOnly(True)
        self.out.setUndoRedoEnabled(False)
        self.out.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.out.setFont(QFont("Cascadia Code, Consolas, Menlo, monospace", 12))
        self.out.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {self.col_bg};
                color: {self.col_tx};
                border: 1px solid #444;
                border-radius: 10px;
                padding: 8px;
            }}
        """)

        self.prompt_label = QLabel(self)
        self.prompt_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.prompt_label.setFont(QFont("Cascadia Mono, Consolas, monospace", 12))
        self._refresh_prompt_label()

        self.inp = QLineEdit(self)
        self.inp.setFont(QFont("Cascadia Code, Consolas, Menlo, monospace", 12))
        self.inp.returnPressed.connect(self._on_enter)
        self.inp.setStyleSheet(f"""
            QLineEdit {{
                background: {self.col_bg};
                color: {self.col_tx};
                border: 1px solid #444;
                border-radius: 10px;
                padding: 6px 8px;
            }}
        """)

      
        self._mk_action("Ctrl+L", self._cmd_cls)      
        self._mk_action("Ctrl+C", self._cmd_cancel)  
        self._mk_action("Ctrl+K", lambda: self.inp.clear())
        self._mk_action("Up", self._hist_prev)
        self._mk_action("Down", self._hist_next)

       
        self.commands: Dict[str, Tuple[str, Callable[[List[str]], None]]] = {}
        self._register_commands()

       
        self._build_completer()

       
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.addWidget(self.out, 1)
        row = QHBoxLayout()
        row.addWidget(self.prompt_label, 0)
        row.addWidget(self.inp, 1)
        root.addLayout(row)

       
        self._println(f"PyOS Command Prompt  Python {platform.python_version()} on {platform.system()}")
        self._println(f"Root: {PROJECT_ROOT}")
        self._println("Type 'help' for a list of commands.\n")
        self._show_prompt()

   
    def _mk_action(self, key, fn):
        a = QAction(self); a.setShortcut(QKeySequence(key)); a.triggered.connect(fn); self.addAction(a)

    def _refresh_prompt_label(self):
        self.prompt_label.setText(f"{str(self.cwd)} {self.PROMPT_SYM}")
        self.prompt_label.setStyleSheet(f"color: {self.col_ac}; padding-right: 8px;")

    def _print(self, s: str):
        self.out.moveCursor(QTextCursor.MoveOperation.End)
        self.out.insertPlainText(s)
        self.out.moveCursor(QTextCursor.MoveOperation.End)

    def _println(self, s: str = ""):
        self._print(s + "\n")

    def _show_prompt(self):
        self._refresh_prompt_label()
        self.inp.setFocus()

    def _hist_prev(self):
        if not self.history:
            return
        if self.hist_index < 0:
            self.hist_index = len(self.history) - 1
        else:
            self.hist_index = max(0, self.hist_index - 1)
        self.inp.setText(self.history[self.hist_index])

    def _hist_next(self):
        if not self.history:
            return
        if self.hist_index >= len(self.history) - 1:
            self.hist_index = -1
            self.inp.clear()
        else:
            self.hist_index = min(len(self.history) - 1, self.hist_index + 1)
            self.inp.setText(self.history[self.hist_index])

    def _build_completer(self):
        words = set()
        words.update(list(getattr(self, "commands", {}).keys()))
        words.update(list(getattr(self, "aliases", {}).keys()))
        try:
            for p in self.cwd.iterdir():
                words.add(p.name)
        except Exception:
            pass
        comp = QCompleter(sorted(words), self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        self.inp.setCompleter(comp)

    def _on_enter(self):
        if self._more_active:
            
            cmd = self.inp.text().strip().lower()
            if cmd in ("q", "quit"):
                self._pager_end()
            else:
                self._pager_step()
            self.inp.clear()
            return

        line = self.inp.text()
        self._println(f"{self.prompt_label.text()} {line}")
        self.inp.clear()

        if line.strip():
            self.history.append(line)
            self.hist_index = -1

        try:
            self._execute(line)
        except Exception as e:
            self._println(f"Error: {e}")
        self._show_prompt()
        self._build_completer()

    def _execute(self, line: str):
       
        for part in [p for p in line.split("&&") if p.strip()]:
            args = shlex.split(part, posix=False)
            if not args:
                continue
            cmd = args[0].lower()
            rest = args[1:]

           
            if cmd not in self.commands and cmd in self.aliases:
                cmd = self.aliases[cmd]

            if cmd in self.commands:
                _desc, fn = self.commands[cmd]
                fn(rest)
            else:
                self._println(f"'{cmd}' is not recognized as an internal command. Type 'help'.")
        
        self.out.moveCursor(QTextCursor.MoveOperation.End)

   
    def _all_command_names(self) -> List[str]:
        names = list(self.commands.keys())
        if hasattr(self, "aliases"):
            names += list(self.aliases.keys())
        return names

    def _register(self, name: str, desc: str, fn: Callable[[List[str]], None]):
        self.commands[name] = (desc, fn)

    def _register_commands(self):
        self.aliases: Dict[str, str] = {
            "ls": "dir",
            "cat": "type",
            "md": "mkdir",
            "rd": "rmdir",
            "ren": "rename",
            "mv": "move",
            "cp": "copy",
            "del": "erase",
            "cls": "clear",
            "pwd": "cd",
            "grep": "findstr",
        }

        
        self._register("dir",      "List directory. Options: /s recursive, /b bare", self._cmd_dir)
        self._register("tree",     "Show directory tree. Options: /f files, /l <depth>", self._cmd_tree)
        self._register("cd",       "Change directory. 'cd' to show current.", self._cmd_cd)
        self._register("mkdir",    "Create directory.", self._cmd_mkdir)
        self._register("rmdir",    "Remove empty directory. Use /s for recursive.", self._cmd_rmdir)
        self._register("touch",    "Create empty file or update timestamp.", self._cmd_touch)
        self._register("erase",    "Delete file(s). Supports wildcards.", self._cmd_erase)
        self._register("copy",     "Copy file to destination.", self._cmd_copy)
        self._register("move",     "Move/Rename file.", self._cmd_move)
        self._register("rename",   "Rename file.", self._cmd_rename)
        self._register("type",     "Print file contents.", self._cmd_type)
        self._register("more",     "Page through a text file. Keys: Enter/Space next, Q quit.", self._cmd_more)
        self._register("head",     "Head of file. Usage: head <file> [n]", self._cmd_head)
        self._register("tail",     "Tail of file. Usage: tail <file> [n]", self._cmd_tail)
        self._register("findstr",  "Find text in files. Options: /s recurse", self._cmd_findstr)
        self._register("wc",       "Word/line/byte count. Usage: wc <file>", self._cmd_wc)

        
        self._register("help",     "Show available commands or help <name>.", self._cmd_help)
        self._register("clear",    "Clear screen.", self._cmd_cls)
        self._register("ver",      "Show PyOS / Python version.", self._cmd_ver)
        self._register("whoami",   "Show current user.", self._cmd_whoami)
        self._register("hostname", "Show machine hostname.", self._cmd_hostname)
        self._register("time",     "Show current time.", self._cmd_time)
        self._register("date",     "Show current date.", self._cmd_date)
        self._register("history",  "Show command history.", self._cmd_history)

        
        self._register("env",      "List environment variables.", self._cmd_env)
        self._register("set",      "Set var: set NAME=VALUE  | show var: set NAME", self._cmd_set)
        self._register("unset",    "Unset var.", self._cmd_unset)
        self._register("path",     "Show PATH variable entries.", self._cmd_path)
        self._register("which",    "Find an executable in PATH.", self._cmd_which)

        
        self._register("ping",     "Fake ping. Usage: ping <host> [-n N]", self._cmd_ping)
        self._register("ipconfig", "Fake IP configuration.", self._cmd_ipconfig)

        
        self._register("echo",     "Echo text.", self._cmd_echo)
        self._register("color",    "Change terminal colors: color <fg> <bg> (hex)", self._cmd_color)
        self._register("open",     "Open file or folder with system.", self._cmd_open)

        
        self._register("exit",     "Close terminal window.", self._cmd_exit)

   
    def _cmd_help(self, args: List[str]):
        if args:
            name = args[0].lower()
            if name in self.aliases:
                name = self.aliases[name]
            if name in self.commands:
                desc, _ = self.commands[name]
                self._println(f"{name}: {desc}")
                return
            self._println(f"No help for '{args[0]}'.")
            return
        
        maxlen = max(len(n) for n in self.commands.keys())
        self._println("Commands:")
        for n, (d, _) in sorted(self.commands.items()):
            self._println(f"  {n.ljust(maxlen)}  {d}")
        if self.aliases:
            self._println("\nAliases:")
            for a, b in sorted(self.aliases.items()):
                self._println(f"  {a} -> {b}")

    def _cmd_cls(self):
        self.out.clear()

    def _cmd_cancel(self):
        if self._more_active:
            self._pager_end()
            self._println("^C")
        else:
            self._println("^C (nothing to cancel)")

    def _cmd_ver(self, _=None):
        self._println("PyOS Terminal 1.0")
        self._println(f"Python {platform.python_version()}  •  Qt {QT_VERSION_STRING()}  •  {platform.system()}")

    def _cmd_whoami(self, _=None):
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "raven"
        self._println(user)

    def _cmd_hostname(self, _=None):
        self._println(platform.node() or "PyOS-Host")

    def _cmd_time(self, _=None):
        self._println(time.strftime("%H:%M:%S"))

    def _cmd_date(self, _=None):
        self._println(time.strftime("%Y-%m-%d"))

    def _cmd_history(self, _=None):
        for i, line in enumerate(self.history[-200:], start=max(1, len(self.history)-len(self.history[-200:])+1)):
            self._println(f"{i:4}  {line}")

    
    def _cmd_env(self, _=None):
        for k, v in sorted(os.environ.items()):
            self._println(f"{k}={v}")

    def _cmd_set(self, args: List[str]):
        if not args:
            self._cmd_env()
            return
        line = " ".join(args)
        if "=" in line:
            name, val = line.split("=", 1)
            os.environ[name] = val
            self._println(f"{name}={val}")
        else:
            val = os.environ.get(line, "")
            self._println(f"{line}={val}")

    def _cmd_unset(self, args: List[str]):
        for name in args:
            os.environ.pop(name, None)

    def _cmd_path(self, _=None):
        p = os.environ.get("PATH", "")
        for entry in p.split(os.pathsep):
            self._println(entry)

    def _cmd_which(self, args: List[str]):
        if not args:
            self._println("Usage: which <name>")
            return
        name = args[0]
        exts = ["", ".exe", ".bat", ".cmd", ".py"]
        
        for ext in exts:
            cand = (self.cwd / (name + ext)).resolve()
            if cand.exists() and cand.is_file():
                self._println(str(cand))
                return
        
        for folder in os.environ.get("PATH", "").split(os.pathsep):
            for ext in exts:
                cand = Path(folder) / (name + ext)
                if cand.exists():
                    self._println(str(cand))
                    return
        self._println("Not found.")

   
    def _iter_files(self, base: Path, recursive: bool):
        if not recursive:
            for p in sorted(base.iterdir()):
                yield p
        else:
            for root, dirs, files in os.walk(base):
                root_p = Path(root)
                for d in sorted(dirs):
                    yield root_p / d
                for f in sorted(files):
                    yield root_p / f

    def _cmd_dir(self, args: List[str]):
        recursive = "/s" in [a.lower() for a in args]
        bare = "/b" in [a.lower() for a in args]

        base = self.cwd
        files = list(self._iter_files(base, recursive))
        if not files:
            self._println("(empty)")
            return
        total_size = 0
        for p in files:
            try:
                st = p.stat()
            except Exception:
                st = None
            if bare:
                self._println(str(p.relative_to(self.cwd)))
            else:
                typ = "<DIR>" if p.is_dir() else "     "
                size = "" if p.is_dir() else human_size(st.st_size if st else 0)
                total_size += (st.st_size if (st and p.is_file()) else 0)
                self._println(f"{st.st_mtime if st else 0:>10.0f}  {typ:5}  {size:>8}  {p.name}")
        if not recursive:
            self._println(f"\nTotal size: {human_size(total_size)}")

    def _cmd_tree(self, args: List[str]):
        show_files = "/f" in [a.lower() for a in args]
        depth = None
        if "/l" in [a.lower() for a in args]:
            try:
                i = args.index("/l")
                depth = int(args[i+1])
            except Exception:
                pass

        def walk(base: Path, prefix: str = "", level: int = 0):
            if depth is not None and level > depth:
                return
            entries = []
            for p in sorted(base.iterdir()):
                if p.is_dir() or show_files:
                    entries.append(p)
            for i, p in enumerate(entries):
                last = (i == len(entries)-1)
                branch = "└── " if last else "├── "
                self._println(prefix + branch + p.name)
                if p.is_dir():
                    walk(p, prefix + ("    " if last else "│   "), level+1)

        self._println(self.cwd.name)
        walk(self.cwd)

    def _cmd_cd(self, args: List[str]):
        if not args:
            self._println(str(self.cwd))
            return
        tgt = args[0]
        if tgt == "~":
            newp = clamp_to_root(PROJECT_ROOT)
        else:
            newp = clamp_to_root((self.cwd / tgt).resolve())
        if newp.exists() and newp.is_dir():
            self.cwd = newp
            self._refresh_prompt_label()
        else:
            self._println("The system cannot find the path specified.")

    def _cmd_mkdir(self, args: List[str]):
        if not args:
            self._println("Usage: mkdir <name>")
            return
        p = clamp_to_root(self.cwd / args[0])
        try:
            p.mkdir(parents=True, exist_ok=True)
            self._println(f"Created: {p}")
        except Exception as e:
            self._println(f"mkdir failed: {e}")

    def _cmd_rmdir(self, args: List[str]):
        if not args:
            self._println("Usage: rmdir <name> [/s]")
            return
        recursive = "/s" in [a.lower() for a in args]
        name = args[0]
        p = clamp_to_root(self.cwd / name)
        try:
            if recursive:
                for root, dirs, files in os.walk(p, topdown=False):
                    for f in files:
                        Path(root, f).unlink(missing_ok=True)
                    for d in dirs:
                        Path(root, d).rmdir()
                p.rmdir()
            else:
                p.rmdir()
            self._println(f"Removed: {p}")
        except Exception as e:
            self._println(f"rmdir failed: {e}")

    def _cmd_touch(self, args: List[str]):
        if not args:
            self._println("Usage: touch <file>")
            return
        p = clamp_to_root(self.cwd / args[0])
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8"):
                os.utime(p, None)
            self._println(f"Touched: {p.name}")
        except Exception as e:
            self._println(f"touch failed: {e}")

    def _expand_glob(self, pattern: str) -> List[Path]:
        ps = list((self.cwd).glob(pattern))
        return [clamp_to_root(p) for p in ps]

    def _cmd_erase(self, args: List[str]):
        if not args:
            self._println("Usage: erase <file|pattern>")
            return
        for pat in args:
            targets = self._expand_glob(pat)
            if not targets:
                self._println(f"Not found: {pat}")
                continue
            for p in targets:
                try:
                    if p.is_dir():
                        self._println(f"Skipping dir: {p.name}")
                        continue
                    p.unlink(missing_ok=True)
                    self._println(f"Deleted: {p.name}")
                except Exception as e:
                    self._println(f"delete failed: {p.name}: {e}")

    def _cmd_copy(self, args: List[str]):
        if len(args) < 2:
            self._println("Usage: copy <src> <dst>")
            return
        src = clamp_to_root((self.cwd / args[0]).resolve())
        dst = clamp_to_root((self.cwd / args[1]).resolve())
        try:
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                data = src.read_bytes()
                dst.write_bytes(data)
                self._println(f"Copied: {src.name} -> {dst}")
            else:
                self._println("Source is not a file.")
        except Exception as e:
            self._println(f"copy failed: {e}")

    def _cmd_move(self, args: List[str]):
        if len(args) < 2:
            self._println("Usage: move <src> <dst>")
            return
        src = clamp_to_root((self.cwd / args[0]).resolve())
        dst = clamp_to_root((self.cwd / args[1]).resolve())
        try:
            src.rename(dst)
            self._println(f"Moved/Renamed: {src} -> {dst}")
        except Exception as e:
            self._println(f"move failed: {e}")

    def _cmd_rename(self, args: List[str]):
        self._cmd_move(args)

    def _cmd_type(self, args: List[str]):
        if not args:
            self._println("Usage: type <file>")
            return
        p = clamp_to_root(self.cwd / args[0])
        try:
            text = p.read_text(encoding="utf-8")
            self._println(text)
        except Exception as e:
            self._println(f"type failed: {e}")

    def _cmd_more(self, args: List[str]):
        if not args:
            self._println("Usage: more <file>")
            return
        p = clamp_to_root(self.cwd / args[0])
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            self._println(f"more failed: {e}")
            return
        self._more_buffer = lines
        self._more_title = p.name
        self._more_active = True
        self._println(f"-- {p.name} --  ({len(lines)} lines)  [Enter/Space = next, Q = quit]")
        self._pager_step()

    def _pager_step(self):
        if not self._more_active:
            return
        chunk = self._more_buffer[: self.PAGER_LINES]
        self._more_buffer = self._more_buffer[self.PAGER_LINES :]
        for ln in chunk:
            self._println(ln)
        if not self._more_buffer:
            self._pager_end()
        else:
            self._print("[--More--] ")

    def _pager_end(self):
        self._more_active = False
        self._more_buffer = []
        self._println("")

    def _cmd_head(self, args: List[str]):
        if not args:
            self._println("Usage: head <file> [n]")
            return
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        p = clamp_to_root(self.cwd / args[0])
        try:
            lines = p.read_text(encoding="utf-8").splitlines()[:n]
            for ln in lines:
                self._println(ln)
        except Exception as e:
            self._println(f"head failed: {e}")

    def _cmd_tail(self, args: List[str]):
        if not args:
            self._println("Usage: tail <file> [n]")
            return
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        p = clamp_to_root(self.cwd / args[0])
        try:
            lines = p.read_text(encoding="utf-8").splitlines()[-n:]
            for ln in lines:
                self._println(ln)
        except Exception as e:
            self._println(f"tail failed: {e}")

    def _cmd_findstr(self, args: List[str]):
        if not args:
            self._println("Usage: findstr <pattern> [path] [/s]")
            return
        recurse = "/s" in [a.lower() for a in args]
        
        args = [a for a in args if a.lower() != "/s"]
        pattern = args[0]
        root = clamp_to_root(self.cwd / (args[1] if len(args) > 1 else "."))
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            self._println(f"Invalid regex: {e}")
            return
        count = 0
        iterable = (root.rglob("*") if recurse else root.glob("*"))
        for p in iterable:
            try:
                if p.is_file():
                    for i, ln in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                        if rx.search(ln):
                            self._println(f"{p.relative_to(self.cwd)}:{i}: {ln}")
                            count += 1
            except Exception:
                pass
        self._println(f"Matches: {count}")

    def _cmd_wc(self, args: List[str]):
        if not args:
            self._println("Usage: wc <file>")
            return
        p = clamp_to_root(self.cwd / args[0])
        try:
            data = p.read_text(encoding="utf-8")
            lines = data.splitlines()
            words = sum(len(l.split()) for l in lines)
            self._println(f"{len(lines)} {words} {len(data.encode('utf-8'))} {p.name}")
        except Exception as e:
            self._println(f"wc failed: {e}")

   
    def _cmd_ping(self, args: List[str]):
        if not args:
            self._println("Usage: ping <host> [-n N]")
            return
        host = args[0]
        n = 4
        if "-n" in args:
            try:
                n = int(args[args.index("-n")+1])
            except Exception:
                pass
        for i in range(n):
            self._println(f"Pinging {host} with 32 bytes of data: Reply from 127.0.0.1: time={1+i}ms TTL=64")
        self._println(f"Ping statistics for {host}: Packets: Sent = {n}, Received = {n}, Lost = 0 (0% loss)")

    def _cmd_ipconfig(self, _=None):
        self._println("Windows IP Configuration (PyOS fake)")
        self._println("")
        self._println("Ethernet adapter PyOS-LAN:")
        self._println("   Connection-specific DNS Suffix  . : pyos.local")
        self._println("   IPv4 Address. . . . . . . . . . . : 192.168.56.101")
        self._println("   Subnet Mask . . . . . . . . . . . : 255.255.255.0")
        self._println("   Default Gateway . . . . . . . . . : 192.168.56.1")

 
    def _cmd_echo(self, args: List[str]):
        self._println(" ".join(args))

    def _cmd_color(self, args: List[str]):
        if len(args) < 2:
            self._println("Usage: color <fg_hex> <bg_hex>   e.g. color #eaeaea #16161a")
            return
        fg, bg = args[0], args[1]
        if not QColor(fg).isValid() or not QColor(bg).isValid():
            self._println("Invalid color(s). Use hex like #rrggbb.")
            return
        self.col_tx, self.col_bg = fg, bg
        self.out.setStyleSheet(f"QPlainTextEdit{{background:{bg};color:{fg};border:1px solid #444;border-radius:10px;padding:8px;}}")
        self.inp.setStyleSheet(f"QLineEdit{{background:{bg};color:{fg};border:1px solid #444;border-radius:10px;padding:6px 8px;}}")
        self._println(f"Colors set to fg={fg} bg={bg}")

    def _cmd_open(self, args: List[str]):
        if not args:
            self._println("Usage: open <file|folder>")
            return
        p = clamp_to_root((self.cwd / args[0]).resolve())
        if not p.exists():
            self._println("Not found.")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(p))  
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
            self._println(f"Opened: {p}")
        except Exception as e:
            self._println(f"open failed: {e}")

    def _cmd_exit(self, _=None):
        try:
            self.window().close()
        except Exception:
            self.close()


def QT_VERSION_STRING():
    try:
        from PyQt6.QtCore import QT_VERSION_STR  
        return QT_VERSION_STR
    except Exception:
        return "6.x"


def launch(container_parent, desktop=None):
    from desktop import AppWindow
    from PyQt6.QtGui import QPixmap
    style = QApplication.instance().style()
    if ICON_FILE.exists():
        pm = QPixmap(str(ICON_FILE)).scaled(24, 24)
    else:
        pm = style.standardPixmap(QStyle.StandardPixmap.SP_ComputerIcon).scaled(24, 24)
    win = AppWindow(title="Command Prompt", width=900, height=560,
                    parent=container_parent, desktop=desktop, icon_pixmap=pm)
    theme = desktop.get_theme_colors() if desktop else {}
    widget = TerminalApp(win, theme=theme)
    win.set_central_widget(widget)
    win.apply_theme(theme if desktop else None)
    win.show()
