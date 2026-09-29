#!/usr/bin/env python3
"""PyKids file explorer: a small full-screen file manager for opening files.

    files.py [--start FOLDER] [--new]

--new opens straight into "New file here" (in my_code/) with the name box
ready; Esc there leaves you in the explorer to pick another folder.

Shows lessons/ and my_code/ one folder at a time, with a preview. The
screen is drawn on the terminal; the answer goes to file descriptor 3:

    open<TAB>PATH             open this file
    new<TAB>FOLDER<TAB>NAME   make a new file (./learn cleans the name and creates it)

Nothing is written if the kid closes it with Esc.
"""
import curses
import locale
import os
import re
import sys
import time
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPS = ["lessons", "my_code"]          # the top level shows only these

locale.setlocale(locale.LC_ALL, "")
FANCY = "utf" in locale.getpreferredencoding(False).lower().replace("-", "")
ICON = {
    "dir": "📁", "file": "🐍", "new": "✨", "newdir": "📂", "up": "  ", "title": "🐍",
} if FANCY else {
    "dir": "[]", "file": "  ", "new": "+ ", "newdir": "+/", "up": "  ", "title": "",
}

KEYWORDS = ("and as break class continue def elif else except finally for from global if "
            "import in is lambda not or pass return try while with yield True False None").split()
TOKENS = re.compile(r"(?P<comment>#.*)|(?P<string>\"[^\"]*\"?|'[^']*'?)|\b(?P<kw>%s)\b"
                    % "|".join(KEYWORDS))


# ---------------------------------------------------------------- text helpers

def cell_width(ch):
    if unicodedata.combining(ch) or ch == "️":
        return 0
    return 2 if unicodedata.east_asian_width(ch) in "WF" else 1


def text_width(s):
    return sum(cell_width(c) for c in s)


def clip(s, width):
    """Cut s to fit in `width` terminal cells, adding … if it was cut."""
    if text_width(s) <= width:
        return s
    out, used = "", 0
    for ch in s:
        w = cell_width(ch)
        if used + w > width - 1:
            break
        out += ch
        used += w
    return out + "…"


def clean_name(name):
    """Same rules as ./learn: "Rocket Game.py" -> "rocket_game"."""
    name = name.strip()
    if name.endswith(".py"):
        name = name[:-3]
    name = name.lower().replace(" ", "_").replace("-", "_")
    return re.sub(r"[^a-z0-9_]", "", name)


# ---------------------------------------------------------------- folders

class Entry:
    def __init__(self, kind, name, path=""):
        self.kind, self.name, self.path = kind, name, path

    @property
    def label(self):
        if self.kind == "up":
            return f"{ICON['up']} ..  back"
        if self.kind == "dir":
            return f"{ICON['dir']} {self.name}/"
        return f"{ICON[self.kind]} {self.name}"


def entries(folder):
    if folder == "":
        items = [Entry("new", "New file", "my_code")]
        items += [Entry("dir", t, t) for t in TOPS if os.path.isdir(os.path.join(ROOT, t))]
        return items
    items = [Entry("up", ".."), Entry("new", "New file here", folder)]
    if folder.split("/")[0] == "my_code":
        items.append(Entry("newdir", "New folder here", folder))
    try:
        names = sorted(os.listdir(os.path.join(ROOT, folder)), key=str.lower)
    except OSError:
        names = []
    for n in names:
        if not n.startswith(".") and n != "__pycache__" and os.path.isdir(os.path.join(ROOT, folder, n)):
            items.append(Entry("dir", n, f"{folder}/{n}"))
    for n in names:
        if n.endswith(".py") and os.path.isfile(os.path.join(ROOT, folder, n)):
            items.append(Entry("file", n, f"{folder}/{n}"))
    return items


def parent(folder):
    return folder.rsplit("/", 1)[0] if "/" in folder else ""


# ---------------------------------------------------------------- the explorer

class Explorer:
    def __init__(self, scr, start):
        self.scr = scr
        self.folder = start
        self.items = entries(start)
        self.sel = 0
        self.top = 0
        self.remember = {}           # folder -> selected index, for coming back
        self.typed, self.typed_at = "", 0.0
        self.answer = None
        self.list_rows = (0, 0)      # screen rows of the list, for mouse clicks
        self.list_cols = (0, 0)
        self.setup_colors()
        self.select_first_useful()

    # ---- colours

    def setup_colors(self):
        self.c = {k: curses.A_NORMAL for k in "bar sel dir comment string kw dim num".split()}
        if not curses.has_colors():
            self.c.update(bar=curses.A_REVERSE, sel=curses.A_REVERSE, dir=curses.A_BOLD)
            return
        curses.start_color()
        try:
            curses.use_default_colors()
            bg = -1
        except curses.error:
            bg = curses.COLOR_BLACK
        rich = curses.COLORS >= 256
        pairs = {   # same blues as the tmux status bar
            "bar": (curses.COLOR_WHITE, 25 if rich else curses.COLOR_BLUE),
            "sel": (curses.COLOR_BLACK, 45 if rich else curses.COLOR_CYAN),
            "dir": (33 if rich else curses.COLOR_BLUE, bg),
            "comment": (244 if rich else curses.COLOR_CYAN, bg),
            "string": (34 if rich else curses.COLOR_GREEN, bg),
            "kw": (170 if rich else curses.COLOR_MAGENTA, bg),
            "dim": (245 if rich else curses.COLOR_WHITE, bg),
            "num": (240 if rich else curses.COLOR_YELLOW, bg),
        }
        for i, (name, (fg, b)) in enumerate(pairs.items(), start=1):
            curses.init_pair(i, fg, b)
            self.c[name] = curses.color_pair(i)
        self.c["bar"] |= curses.A_BOLD
        self.c["dir"] |= curses.A_BOLD
        self.c["kw"] |= curses.A_BOLD

    # ---- moving around

    def select_first_useful(self):
        """Start on the first file or folder rather than on "..", "New file"."""
        for i, e in enumerate(self.items):
            if e.kind in ("dir", "file"):
                self.sel = i
                return

    def go(self, folder, select_path=None):
        self.remember[self.folder] = self.sel
        self.folder = folder
        self.items = entries(folder)
        self.top = 0
        self.typed = ""
        if select_path is not None:
            self.sel = next((i for i, e in enumerate(self.items)
                             if e.kind == "dir" and e.path == select_path), 0)
        elif folder in self.remember:
            self.sel = min(self.remember[folder], len(self.items) - 1)
        else:
            self.sel = 0
            self.select_first_useful()

    def move(self, delta):
        self.sel = max(0, min(len(self.items) - 1, self.sel + delta))

    def back(self):
        if self.folder:
            self.go(parent(self.folder), select_path=self.folder)

    def activate(self):
        e = self.items[self.sel]
        if e.kind == "up":
            self.back()
        elif e.kind == "dir":
            self.go(e.path)
        elif e.kind == "file":
            self.answer = f"open\t{e.path}"
        elif e.kind == "new":
            name = self.ask(f"{ICON['new']} New file in {e.path}/: ", ".py")
            if name:
                self.answer = f"new\t{e.path}\t{name}"
        elif e.kind == "newdir":
            name = self.ask(f"{ICON['newdir']} New folder in {e.path}/: ", "/")
            if name:
                os.makedirs(os.path.join(ROOT, e.path, clean_name(name)), exist_ok=True)
                self.go(f"{e.path}/{clean_name(name)}")

    def type_to_jump(self, ch):
        now = time.monotonic()
        self.typed = (self.typed if now - self.typed_at < 1.2 else "") + ch.lower()
        self.typed_at = now
        names = [(i, e.name.lower()) for i, e in enumerate(self.items) if e.kind in ("dir", "file")]
        for match in (lambda n: n.startswith(self.typed), lambda n: self.typed in n):
            hit = next((i for i, n in names if match(n)), None)
            if hit is not None:
                self.sel = hit
                return

    # ---- drawing

    def put(self, y, x, text, attr=0, width=None):
        h, w = self.scr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        room = w - x - (1 if y == h - 1 else 0)     # never write the bottom-right cell
        width = room if width is None else min(width, room)
        if width <= 0:
            return
        text = clip(text, width)
        try:
            self.scr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def fill(self, y, x, width, attr):
        h, w = self.scr.getmaxyx()
        width = min(width, w - x - (1 if y == h - 1 else 0))    # exact fit: no "…"
        self.put(y, x, " " * max(0, width), attr)

    def layout(self):
        h, w = self.scr.getmaxyx()
        body_top, body_bottom = 1, h - 2            # title bar, then the list, then the key bar
        if w >= 70:                                 # list | preview
            lw = max(30, w * 2 // 5)
            return (body_top, body_bottom, 0, lw), (body_top, body_bottom, lw + 1, w - lw - 1), "side"
        if h >= 22:                                 # list above preview (phones held upright)
            split = body_top + (body_bottom - body_top) * 3 // 5
            return (body_top, split, 0, w), (split + 1, body_bottom, 0, w), "below"
        return (body_top, body_bottom, 0, w), None, "none"

    def draw(self, footer=None):
        scr = self.scr
        scr.erase()
        h, w = scr.getmaxyx()
        where = (self.folder + "/") if self.folder else "PyKids"
        self.fill(0, 0, w, self.c["bar"])
        self.put(0, 1, f"{ICON['title']} Open a file   {ICON['newdir'] if FANCY else ''} {where}".rstrip(),
                 self.c["bar"])

        (lt, lb, lx, lw), pv, mode = self.layout()
        rows = max(1, lb - lt)
        self.list_rows, self.list_cols = (lt, lt + rows), (lx, lx + lw)
        if self.sel < self.top:
            self.top = self.sel
        if self.sel >= self.top + rows:
            self.top = self.sel - rows + 1
        for i, e in enumerate(self.items[self.top:self.top + rows]):
            idx = self.top + i
            attr = self.c["dir"] if e.kind == "dir" else (self.c["dim"] if e.kind in ("up",) else 0)
            if idx == self.sel:
                attr = self.c["sel"] | curses.A_BOLD
                self.fill(lt + i, lx, lw, attr)
            self.put(lt + i, lx + 1, e.label, attr, lw - 2)
        if len(self.items) > rows:          # a little scroll hint
            self.put(lb - 1, lx + lw - 3, "↓" if self.top + rows < len(self.items) else " ", self.c["dim"])
            if self.top > 0:
                self.put(lt, lx + lw - 3, "↑", self.c["dim"])

        if pv:
            pt, pb, px, pw = pv
            if mode == "side":
                for y in range(pt, pb):
                    self.put(y, px - 1, "│", self.c["dim"])
            else:
                self.put(pt - 1, px, "─" * pw, self.c["dim"])
            self.draw_preview(pt, pb, px + 1, pw - 2)

        self.draw_footer(footer)
        scr.refresh()

    def draw_preview(self, top, bottom, x, width):
        e = self.items[self.sel]
        rows = bottom - top
        if e.kind == "file":
            self.put(top, x, f"{ICON['file']} {e.path}", curses.A_BOLD, width)
            try:
                with open(os.path.join(ROOT, e.path), encoding="utf-8", errors="replace") as f:
                    lines = f.read(20000).splitlines()
            except OSError:
                lines = ["(can't read this file)"]
            for n, line in enumerate(lines[:rows - 2], start=1):
                self.put(top + 1 + n, x, f"{n:3} ", self.c["num"])
                self.draw_code(top + 1 + n, x + 4, line.replace("\t", "    "), width - 4)
        elif e.kind == "dir":
            self.put(top, x, f"{ICON['dir']} {e.path}/", curses.A_BOLD, width)
            inside = [i for i in entries(e.path) if i.kind in ("dir", "file")]
            if not inside:
                self.put(top + 2, x, "(empty)", self.c["dim"], width)
            for n, i in enumerate(inside[:rows - 2]):
                self.put(top + 2 + n, x, i.label, self.c["dir"] if i.kind == "dir" else 0, width)
        else:
            text = {
                "up": f"Back to {parent(self.folder) or 'the top'}",
                "new": f"Make a brand new Python file in {e.path}/",
                "newdir": f"Make a new folder in {e.path}/ to keep files together",
            }[e.kind]
            self.put(top, x, text, self.c["dim"], width)

    def draw_code(self, y, x, line, width):
        """One line of Python with comments, strings and keywords coloured."""
        end = x + width

        def run(text, attr):
            nonlocal x
            if x < end and text:
                self.put(y, x, text, attr, end - x)
            x += text_width(text)

        pos = 0
        for m in TOKENS.finditer(line):
            run(line[pos:m.start()], 0)
            run(m.group(), self.c[m.lastgroup])
            pos = m.end()
        run(line[pos:], 0)

    def draw_footer(self, footer):
        h, w = self.scr.getmaxyx()
        self.fill(h - 1, 0, w, self.c["bar"])
        if footer is not None:
            self.put(h - 1, 1, footer, self.c["bar"])
        elif self.typed and time.monotonic() - self.typed_at < 1.2:
            self.put(h - 1, 1, f"jump to: {self.typed}", self.c["bar"])
        else:
            wide = "↑↓ move   Enter/→ open   ← back   type a name to jump   Esc close"
            short = "↑↓ Enter open  ← back  Esc close"
            self.put(h - 1, 1, wide if w > len(wide) + 2 else short, self.c["bar"])

    # ---- asking for a name, inside the bottom bar

    def ask(self, prompt, ending):
        text = ""
        curses.curs_set(1)
        try:
            while True:
                shown = clean_name(text)
                hint = f"   → {shown}{ending}" if shown and shown != text else ""
                footer = f"{prompt}{text}"
                self.draw(footer + hint)
                h, w = self.scr.getmaxyx()
                try:
                    self.scr.move(h - 1, min(w - 2, 1 + text_width(footer)))
                except curses.error:
                    pass
                ch = self.scr.get_wch()
                if ch in ("\n", "\r", curses.KEY_ENTER):
                    return text if clean_name(text) else None
                if ch == "\x1b":
                    return None
                if ch in (curses.KEY_BACKSPACE, "\x7f", "\b"):
                    text = text[:-1]
                elif isinstance(ch, str) and ch.isprintable():
                    text += ch
        finally:
            curses.curs_set(0)

    # ---- the loop

    def run(self, new=False):
        curses.curs_set(0)
        self.scr.keypad(True)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        curses.mouseinterval(0)     # report presses right away; a second press opens
        if new:                     # "New program": go straight to the name box
            self.sel = next(i for i, e in enumerate(self.items) if e.kind == "new")
            self.activate()
        while self.answer is None:
            self.draw()
            try:
                ch = self.scr.get_wch()
            except KeyboardInterrupt:
                return
            rows = max(1, self.list_rows[1] - self.list_rows[0])
            if ch in (curses.KEY_UP,):
                self.move(-1)
            elif ch in (curses.KEY_DOWN,):
                self.move(1)
            elif ch == curses.KEY_PPAGE:
                self.move(-rows)
            elif ch == curses.KEY_NPAGE:
                self.move(rows)
            elif ch == curses.KEY_HOME:
                self.sel = 0
            elif ch == curses.KEY_END:
                self.sel = len(self.items) - 1
            elif ch in ("\n", "\r", curses.KEY_ENTER, curses.KEY_RIGHT):
                self.activate()
            elif ch in (curses.KEY_LEFT, curses.KEY_BACKSPACE, "\x7f", "\b"):
                self.back()
            elif ch == "\x1b":
                return
            elif ch == curses.KEY_MOUSE:
                self.mouse()
            elif isinstance(ch, str) and ch.isprintable() and ch != " ":
                self.type_to_jump(ch)

    def mouse(self):
        try:
            _, x, y, _, bstate = curses.getmouse()
        except curses.error:
            return
        wheel_up = getattr(curses, "BUTTON4_PRESSED", 0)
        wheel_down = getattr(curses, "BUTTON5_PRESSED", 0)
        if wheel_up and bstate & wheel_up:
            self.move(-3)
        elif wheel_down and bstate & wheel_down:
            self.move(3)
        elif bstate & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED | curses.BUTTON1_DOUBLE_CLICKED):
            (t, b), (l, r) = self.list_rows, self.list_cols
            idx = self.top + (y - t)
            if t <= y < b and l <= x < r and idx < len(self.items):
                if idx == self.sel:     # click the chosen one again (or double-click): open it
                    self.activate()
                else:
                    self.sel = idx


def main():
    args = sys.argv[1:]
    new = "--new" in args
    start = args[args.index("--start") + 1].strip("/") if "--start" in args[:-1] else ""
    if start.split("/")[0] not in TOPS or not os.path.isdir(os.path.join(ROOT, start)):
        start = ""
    if new and start.split("/")[0] != "my_code":    # new programs go in my_code/
        start = "my_code" if os.path.isdir(os.path.join(ROOT, "my_code")) else ""
    os.environ.setdefault("ESCDELAY", "25")     # Esc closes right away

    def explore(scr):
        ex = Explorer(scr, start)
        ex.run(new)
        return ex.answer

    try:
        answer = curses.wrapper(explore)
    except KeyboardInterrupt:                    # Ctrl-C closes it, like Esc
        answer = None
    if answer:
        try:
            os.write(3, (answer + "\n").encode())
        except OSError:                          # run by hand: no fd 3
            print(answer)


if __name__ == "__main__":
    main()
