"""A stand-in for Python's turtle module that draws in a web browser.

PyKids uses it when a real turtle window can't open (no tkinter, or no
screen: Termux, SSH). run.py serves the page; this module works out
where every turtle goes, like the real one does, and sends the drawing
steps there. Key presses come back from the page the other way.

Drawing, keys and timers work. Clicks and pop-up questions raise
NotInWebTurtle.
"""
import atexit
import collections
import heapq
import itertools
import json
import math
import os
import sys
import threading
import time
import urllib.error
import urllib.request

_URL = os.environ.get("PYKIDS_WEBTURTLE", "")
_RUN = os.environ.get("PYKIDS_WEBTURTLE_RUN", "0")


class TurtleGraphicsError(Exception):
    """Same name as the real turtle's error, e.g. for a bad colour."""


class Terminator(Exception):
    pass


class NotInWebTurtle(Exception):
    """A real turtle feature the web turtle can't do (yet)."""


# ---------------------------------------------------------------- sending

class _Sender:
    """Collects drawing steps and posts them to run.py in small batches."""

    def __init__(self):
        self.ops = []
        self.ops_lock = threading.Lock()
        self.send_lock = threading.Lock()   # keeps batches in order
        self.stopped = False
        # Ignore http_proxy settings: the server is on this machine.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        threading.Thread(target=self._loop, daemon=True).start()
        atexit.register(self.flush)

    def add(self, op):
        with self.ops_lock:
            self.ops.append(op)
            full = len(self.ops) >= 500
        if full:
            self.flush()

    def _loop(self):
        while True:
            time.sleep(0.05)
            self.flush()

    def flush(self):
        with self.send_lock:
            with self.ops_lock:
                ops, self.ops = self.ops, []
            if not ops or not _URL or self.stopped:
                return
            data = json.dumps(ops, separators=(",", ":")).encode()
            req = urllib.request.Request(f"{_URL}draw?run={_RUN}", data=data,
                                         headers={"Content-Type": "application/json"})
            try:
                self.opener.open(req, timeout=5).close()
            except urllib.error.HTTPError as e:
                if e.code == 413:
                    self.stopped = True
                    print("\n🐢 That's a LOT of drawing! The web turtle stopped here.",
                          file=sys.stderr)
            except OSError:
                self.stopped = True
                print("\n🐢 Can't reach the drawing page any more.", file=sys.stderr)


_sender = _Sender()
_send = _sender.add


def _r(v):
    return round(v, 2)


# ---------------------------------------------------------------- colours

_CSS_NAMES = set("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond
blue blueviolet brown burlywood cadetblue chartreuse chocolate coral
cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray
darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid
darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod
gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki
lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue
lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue
mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen
mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod
palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon
sandybrown seagreen seashell sienna silver skyblue slateblue slategray
slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet
wheat white whitesmoke yellow yellowgreen
""".split())


def _css(color):
    """Turn a turtle colour ("red", "#ff0000", (1, 0, 0)) into CSS, or raise."""
    if isinstance(color, str):
        name = color.strip().lower().replace(" ", "")
        if name in _CSS_NAMES:
            return name
        if name.startswith("#") and len(name) in (4, 7) and \
                all(c in "0123456789abcdef" for c in name[1:]):
            return name
        for g in ("gray", "grey"):   # tk's gray0 ... gray100
            if name.startswith(g) and name[len(g):].isdigit() and int(name[len(g):]) <= 100:
                v = round(int(name[len(g):]) * 2.55)
                return f"rgb({v},{v},{v})"
        raise TurtleGraphicsError(f"bad color string: {color}")
    try:
        r, g, b = color
    except (TypeError, ValueError):
        raise TurtleGraphicsError(f"bad color arguments: {color}") from None
    mode = Screen()._colormode
    if mode == 1.0:
        if not all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in (r, g, b)):
            raise TurtleGraphicsError(f"bad color sequence: {color}  "
                                      "(numbers must be 0 to 1, or use colormode(255))")
        r, g, b = (round(v * 255) for v in (r, g, b))
    elif not all(isinstance(v, int) and 0 <= v <= 255 for v in (r, g, b)):
        raise TurtleGraphicsError(f"bad color sequence: {color}  (numbers must be 0 to 255)")
    return f"rgb({r},{g},{b})"


def _color_arg(args):
    """pencolor("red") / pencolor((1, 0, 0)) / pencolor(1, 0, 0) -> one value."""
    return args[0] if len(args) == 1 else args


# ---------------------------------------------------------------- Vec2D

class Vec2D(tuple):
    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    def __add__(self, other):
        return Vec2D(self[0] + other[0], self[1] + other[1])

    def __sub__(self, other):
        return Vec2D(self[0] - other[0], self[1] - other[1])

    def __mul__(self, other):
        if isinstance(other, Vec2D):
            return self[0] * other[0] + self[1] * other[1]
        return Vec2D(self[0] * other, self[1] * other)

    def __rmul__(self, other):
        return Vec2D(self[0] * other, self[1] * other)

    def __neg__(self):
        return Vec2D(-self[0], -self[1])

    def __abs__(self):
        return math.hypot(*self)

    def rotate(self, angle):
        c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        return Vec2D(self[0] * c - self[1] * s, self[0] * s + self[1] * c)

    def __getnewargs__(self):
        return (self[0], self[1])

    def __repr__(self):
        return "(%.2f,%.2f)" % self


# ---------------------------------------------------------------- names

_SHAPES = ("arrow", "turtle", "circle", "square", "triangle", "classic", "blank")
_SPEEDS = {"fastest": 0, "fast": 10, "normal": 6, "slow": 3, "slowest": 1}

# Real turtle features that aren't in the web turtle, so we can say so
# instead of a confusing "has no attribute" error.
_REAL_TURTLE_ONLY = {
    "begin_poly", "end_poly", "get_poly", "get_shapepoly", "clearstamp",
    "clearstamps", "onclick", "ondrag", "onrelease", "pen", "resizemode",
    "settiltangle", "setundobuffer", "shapetransform", "shearfactor", "tilt",
    "tiltangle", "undo", "undobufferentries",
}
_REAL_SCREEN_ONLY = {
    "addshape", "bgpic", "getcanvas", "numinput", "onclick", "onscreenclick",
    "register_shape", "setworldcoordinates", "textinput",
}


def _not_here(name):
    return NotInWebTurtle(f"{name}() doesn't work in the web turtle yet.")


# ---------------------------------------------------------------- keys and timers
# Like the real turtle, key handlers and timers run in the main thread:
# inside mainloop()/done(), update(), and while a turtle walks.

_keys_in = collections.deque()          # ("press" | "release", keyname) from the page
_keys_cond = threading.Condition()
_timers = []                            # heap of (when, n, function)
_timer_n = itertools.count()
_busy = False                           # already running a handler?


def _read_keys():
    try:
        with _sender.opener.open(f"{_URL}keys?run={_RUN}") as stream:
            for line in stream:
                ev = json.loads(line)
                with _keys_cond:
                    _keys_in.append((ev["t"], ev["k"]))
                    _keys_cond.notify()
    except (OSError, ValueError, KeyError):
        pass    # the run was replaced, or the program is ending


def _events_waiting():
    return bool(_keys_in) or bool(_timers and _timers[0][0] <= time.monotonic())


def _run_events():
    """Run handlers for keys that came in and timers that are due."""
    global _busy
    if _busy:           # a handler moved a turtle; don't start another inside it
        return False
    _busy = True
    ran = False
    try:
        while _keys_in:
            kind, key = _keys_in.popleft()
            ran = Screen()._key_event(kind, key) or ran
        now = time.monotonic()
        due = []
        while _timers and _timers[0][0] <= now:
            due.append(heapq.heappop(_timers)[2])
        for fun in due:     # timers set by these run next time, not in this loop
            fun()
            ran = True
    finally:
        _busy = False
    return ran


# ---------------------------------------------------------------- Screen

class _Screen:
    def __init__(self):
        self._bg = "white"
        self._colormode = 1.0
        self._size = (800, 600)
        self._instant = False
        self._turtles = []
        self._on_press = {}     # keyname (None = any key) -> function
        self._on_release = {}
        self._listening = False
        self._stop = False

    def __getattr__(self, name):
        if name in _REAL_SCREEN_ONLY:
            raise _not_here(name)
        raise AttributeError(f"'_Screen' object has no attribute '{name}'")

    def bgcolor(self, *args):
        if not args:
            return self._bg
        c = _color_arg(args)
        _send({"op": "bg", "c": _css(c)})
        self._bg = c

    def colormode(self, cmode=None):
        if cmode is None:
            return self._colormode
        if cmode == 1.0:
            self._colormode = 1.0
        elif cmode == 255:
            self._colormode = 255

    def setup(self, width=0.5, height=0.75, startx=None, starty=None):
        # Fractions are of a "screen"; 0.5 x 0.75 gives the usual 800 x 600.
        w = width * 1600 if isinstance(width, float) and width <= 1 else width
        h = height * 800 if isinstance(height, float) and height <= 1 else height
        self._size = (int(w), int(h))
        _send({"op": "world", "w": self._size[0], "h": self._size[1]})

    def screensize(self, canvwidth=None, canvheight=None, bg=None):
        if canvwidth is None and canvheight is None and bg is None:
            return self._size
        if canvwidth and canvheight:
            self.setup(canvwidth, canvheight)
        if bg is not None:
            self.bgcolor(bg)

    def window_width(self):
        return self._size[0]

    def window_height(self):
        return self._size[1]

    def title(self, titlestring):
        _send({"op": "title", "s": str(titlestring)})

    def tracer(self, n=None, delay=None):
        if n is None:
            return 0 if self._instant else 1
        self._instant = not n

    def update(self):
        _run_events()
        _sender.flush()

    def delay(self, delay=None):
        if delay is None:
            return 10

    def mode(self, mode=None):
        if mode is None:
            return "standard"
        if mode != "standard":
            raise _not_here(f"mode({mode!r})")

    def getshapes(self):
        return sorted(_SHAPES)

    def turtles(self):
        return list(self._turtles)

    def clear(self):
        _send({"op": "clearscreen"})
        self._bg = "white"

    clearscreen = clear

    def reset(self):
        for t in self._turtles:
            t.reset()

    resetscreen = reset

    # ---- keys and timers

    def _bind(self, handlers, fun, key):
        if fun is None:
            handlers.pop(key, None)
        elif not callable(fun):
            raise TurtleGraphicsError(
                f"onkey needs a function name without (): onkey(jump, {key!r}), not onkey(jump(), ...)")
        else:
            handlers[key] = fun
        keys = sorted({k for k in (*self._on_press, *self._on_release) if k is not None})
        any_key = None in self._on_press
        _send({"op": "keys", "keys": keys, "any": any_key})

    def onkeyrelease(self, fun, key):
        self._bind(self._on_release, fun, key)

    onkey = onkeyrelease    # same as the real turtle: onkey fires when the key comes up

    def onkeypress(self, fun, key=None):
        self._bind(self._on_press, fun, key)

    def listen(self, xdummy=None, ydummy=None):
        if not self._listening:
            self._listening = True
            _send({"op": "listen"})
            _sender.flush()
            threading.Thread(target=_read_keys, daemon=True).start()

    def _key_event(self, kind, key):
        handlers = self._on_press if kind == "press" else self._on_release
        fun = handlers.get(key) or (handlers.get(None) if kind == "press" else None)
        if fun:
            fun()
        return bool(fun)

    def ontimer(self, fun, t=0):
        if not callable(fun):
            raise TurtleGraphicsError(
                f"ontimer needs a function name without (): ontimer(move, {t}), not ontimer(move(), {t})")
        heapq.heappush(_timers, (time.monotonic() + t / 1000, next(_timer_n), fun))

    def mainloop(self):
        # The real turtle waits here until you close the window. With nothing
        # to wait for (no keys, no timers) the web page keeps the drawing, so
        # the program can just finish.
        _sender.flush()
        if not (_timers or self._on_press or self._on_release):
            return
        print("🐢 Playing! Keys go to the web page. Press Ctrl-C here to stop.", flush=True)
        while not self._stop:
            if _run_events():
                _sender.flush()             # show what the handlers drew right away
            if not (_timers or self._on_press or self._on_release):
                break                       # the last timer finished
            wait = min(0.5, max(0.0, _timers[0][0] - time.monotonic())) if _timers else 0.5
            with _keys_cond:
                if not _keys_in:
                    _keys_cond.wait(wait)
        _sender.flush()

    done = mainloop
    exitonclick = mainloop

    def bye(self):
        self._stop = True


_screen = None


def Screen():
    global _screen
    if _screen is None:
        _screen = _Screen()
    return _screen


TurtleScreen = _Screen


# ---------------------------------------------------------------- Turtle

class Turtle:
    _count = 0

    def __init__(self, shape="classic", undobuffersize=1000, visible=True):
        self.screen = Screen()
        Turtle._count += 1
        self._id = Turtle._count
        self.screen._turtles.append(self)
        self._fullcircle = 360.0
        if shape not in _SHAPES:
            raise TurtleGraphicsError(f"There is no shape named {shape}")
        self._shape = shape
        self._setup_state()
        self._visible = bool(visible)
        self._announce()

    def _setup_state(self):
        self._x = self._y = 0.0
        self._h = 0.0                    # degrees, 0 = east, counterclockwise
        self._down = True
        self._width = 1
        self._speed = 3
        self._pc, self._fc = "black", "black"     # what the kid gave us
        self._pcss, self._fcss = "black", "black"
        self._visible = True
        self._stretch = (1, 1, 1)
        self._fill = None                 # list of corners while filling

    def _announce(self):
        _send({"op": "new", "t": self._id, "x": _r(self._x), "y": _r(self._y),
               "h": _r(self._h), **self._look()})

    def _look(self):
        return {"pc": self._pcss, "fc": self._fcss, "shape": self._shape,
                "vis": self._visible, "size": list(self._stretch)}

    def _send_look(self):
        _send({"op": "look", "t": self._id, **self._look()})

    def __getattr__(self, name):
        if name in _REAL_TURTLE_ONLY:
            raise _not_here(name)
        raise AttributeError(f"'Turtle' object has no attribute '{name}'")

    def __repr__(self):
        return f"<turtle.Turtle object {self._id}>"

    # ---- moving

    def _sp(self):
        return 0 if self.screen._instant else self._speed

    def _goto(self, x, y, draw=None):
        draw = self._down if draw is None else draw
        _send({"op": "move", "t": self._id, "x": _r(x), "y": _r(y), "d": int(draw),
               "c": self._pcss, "w": self._width, "sp": self._sp()})
        self._x, self._y = x, y
        if self._fill is not None:
            self._fill.append([_r(x), _r(y)])
        if not self.screen._instant and _events_waiting():
            _run_events()   # like the real turtle: keys work while it walks

    def _turn(self, degrees, instant=False):
        self._h = (self._h + degrees) % 360
        _send({"op": "turn", "t": self._id, "d": _r(degrees),
               "sp": 0 if instant else self._sp()})

    def _deg(self, angle):
        return angle * 360.0 / self._fullcircle

    def forward(self, distance):
        a = math.radians(self._h)
        self._goto(self._x + distance * math.cos(a), self._y + distance * math.sin(a))

    def back(self, distance):
        self.forward(-distance)

    def left(self, angle):
        self._turn(self._deg(angle))

    def right(self, angle):
        self._turn(-self._deg(angle))

    def goto(self, x, y=None):
        if y is None:
            x, y = x
        self._goto(x, y)

    def setx(self, x):
        self._goto(x, self._y)

    def sety(self, y):
        self._goto(self._x, y)

    def teleport(self, x=None, y=None, *, fill_gap=False):
        self._goto(self._x if x is None else x, self._y if y is None else y, draw=False)

    def setheading(self, to_angle):
        delta = (self._deg(to_angle) - self._h + 180) % 360 - 180
        self._turn(delta)

    def home(self):
        self.goto(0, 0)
        self.setheading(0)

    def circle(self, radius, extent=None, steps=None):
        # Same polygon as the real turtle, so drawings end up identical.
        if extent is None:
            extent = self._fullcircle
        if steps is None:
            frac = abs(extent) / self._fullcircle
            steps = 1 + int(min(11 + abs(radius) / 6.0, 59.0) * frac)
        w = self._deg(1.0 * extent / steps)
        w2 = 0.5 * w
        length = 2.0 * radius * math.sin(math.radians(w2))
        if radius < 0:
            length, w, w2 = -length, -w, -w2
        self._turn(w2, instant=True)
        for _ in range(steps):
            self.forward(length)
            self._turn(w, instant=True)
        self._turn(-w2, instant=True)

    # ---- where am I?

    def position(self):
        return Vec2D(self._x, self._y)

    def xcor(self):
        return self._x

    def ycor(self):
        return self._y

    def heading(self):
        return (self._h * self._fullcircle / 360.0) % self._fullcircle

    def _point(self, x, y):
        if y is not None:
            return x, y
        if isinstance(x, Turtle):
            return x._x, x._y
        return x

    def towards(self, x, y=None):
        px, py = self._point(x, y)
        angle = math.degrees(math.atan2(py - self._y, px - self._x)) % 360
        return angle * self._fullcircle / 360.0

    def distance(self, x, y=None):
        px, py = self._point(x, y)
        return math.hypot(px - self._x, py - self._y)

    def degrees(self, fullcircle=360.0):
        self._fullcircle = fullcircle

    def radians(self):
        self._fullcircle = 2 * math.pi

    # ---- pen

    def penup(self):
        self._down = False

    def pendown(self):
        self._down = True

    def isdown(self):
        return self._down

    def pensize(self, width=None):
        if width is None:
            return self._width
        self._width = width

    def speed(self, speed=None):
        if speed is None:
            return self._speed
        if speed in _SPEEDS:
            speed = _SPEEDS[speed]
        elif 0.5 < speed < 10.5:
            speed = int(round(speed))
        else:
            speed = 0
        self._speed = speed

    def pencolor(self, *args):
        if not args:
            return self._pc
        c = _color_arg(args)
        self._pcss, self._pc = _css(c), c
        self._send_look()

    def fillcolor(self, *args):
        if not args:
            return self._fc
        c = _color_arg(args)
        self._fcss, self._fc = _css(c), c
        self._send_look()

    def color(self, *args):
        if not args:
            return self._pc, self._fc
        if len(args) == 2:
            pc, fc = args
        else:
            pc = fc = _color_arg(args)
        self._pcss, self._fcss = _css(pc), _css(fc)
        self._pc, self._fc = pc, fc
        self._send_look()

    def begin_fill(self):
        self._fill = [[_r(self._x), _r(self._y)]]
        _send({"op": "fillstart", "t": self._id})

    def end_fill(self):
        if self._fill is not None:
            _send({"op": "fill", "t": self._id, "pts": self._fill, "c": self._fcss})
            self._fill = None

    def filling(self):
        return self._fill is not None

    def dot(self, size=None, *color):
        if not color:
            if isinstance(size, (str, tuple)):
                css, size = _css(size), None
            else:
                css = self._pcss
        else:
            css = _css(_color_arg(color))
        if not size:
            size = self._width + max(self._width, 4)
        _send({"op": "dot", "t": self._id, "x": _r(self._x), "y": _r(self._y),
               "size": size, "c": css})

    def write(self, arg, move=False, align="left", font=("Arial", 8, "normal")):
        if align not in ("left", "center", "right"):
            raise TurtleGraphicsError(f"align must be 'left', 'center' or 'right', not {align!r}")
        font = tuple(font) + ("Arial", 8, "normal")[len(font):]
        text = str(arg)
        _send({"op": "write", "t": self._id, "x": _r(self._x), "y": _r(self._y),
               "s": text, "a": align, "f": list(font[:3]), "c": self._pcss})
        if move and align != "right":
            # About how wide the text is (the page measures it exactly).
            width = len(text) * font[1] * 0.75
            self._goto(self._x + (width if align == "left" else width / 2), self._y,
                       draw=False)

    def clear(self):
        _send({"op": "clear", "t": self._id})

    def reset(self):
        self.clear()
        self._setup_state()
        _send({"op": "home", "t": self._id})
        self._send_look()

    # ---- how the turtle looks

    def shape(self, name=None):
        if name is None:
            return self._shape
        if name not in _SHAPES:
            raise TurtleGraphicsError(f"There is no shape named {name}")
        self._shape = name
        self._send_look()

    def shapesize(self, stretch_wid=None, stretch_len=None, outline=None):
        if stretch_wid is None and stretch_len is None and outline is None:
            return self._stretch
        w, l, o = self._stretch
        if stretch_wid is not None:
            w = stretch_wid
            l = stretch_wid if stretch_len is None else stretch_len
        elif stretch_len is not None:
            l = stretch_len
        if outline is not None:
            o = outline
        self._stretch = (w, l, o)
        self._send_look()

    def hideturtle(self):
        self._visible = False
        self._send_look()

    def showturtle(self):
        self._visible = True
        self._send_look()

    def isvisible(self):
        return self._visible

    _stamps = 0

    def stamp(self):
        Turtle._stamps += 1
        _send({"op": "stamp", "t": self._id})
        return Turtle._stamps

    def clone(self):
        twin = Turtle.__new__(Turtle)
        twin.__dict__.update(self.__dict__)
        Turtle._count += 1
        twin._id = Turtle._count
        twin._fill = None
        self.screen._turtles.append(twin)
        twin._announce()
        return twin

    def getscreen(self):
        return self.screen

    def getturtle(self):
        return self

    # short names, like the real turtle
    fd = forward
    bk = backward = back
    lt = left
    rt = right
    setpos = setposition = goto
    seth = setheading
    pos = position
    pu = up = penup
    pd = down = pendown
    width = pensize
    st = showturtle
    ht = hideturtle
    turtlesize = shapesize
    getpen = getturtle


Pen = RawTurtle = RawPen = Turtle

# ---------------------------------------------------------------- module level
# turtle.forward(100) etc. use one hidden turtle, like the real module.

_anon = None


def getturtle():
    global _anon
    if _anon is None:
        _anon = Turtle()
    return _anon


getpen = getturtle


def _turtle_function(name):
    def f(*args, **kwargs):
        return getattr(getturtle(), name)(*args, **kwargs)
    f.__name__ = name
    return f


def _screen_function(name):
    def f(*args, **kwargs):
        return getattr(Screen(), name)(*args, **kwargs)
    f.__name__ = name
    return f


for _name in """forward fd back bk backward left lt right rt goto setpos setposition
        setx sety teleport setheading seth home circle position pos xcor ycor heading
        towards distance degrees radians penup pu up pendown pd down isdown pensize
        width speed pencolor fillcolor color begin_fill end_fill filling dot write
        clear reset shape shapesize turtlesize hideturtle ht showturtle st isvisible
        stamp clone getscreen""".split():
    globals()[_name] = _turtle_function(_name)

for _name in """bgcolor colormode setup screensize window_width window_height title
        tracer update delay mode getshapes turtles clearscreen resetscreen mainloop
        done exitonclick bye onkey onkeypress onkeyrelease listen ontimer""".split():
    globals()[_name] = _screen_function(_name)

del _name


def __getattr__(name):
    if name in _REAL_TURTLE_ONLY or name in _REAL_SCREEN_ONLY:
        raise _not_here(name)
    raise AttributeError(f"module 'turtle' has no attribute '{name}'")


if _URL:
    print(f"🐢 Your drawing is in the web browser:  {_URL}")
