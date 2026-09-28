#!/usr/bin/env python3
"""Output pane for PyKids.

    run.py FILE          watch FILE and re-run it every time it is saved
    run.py --child FILE  (internal) run FILE once, printing kid-friendly errors

When a real turtle window can't open (no tkinter, or no screen: Termux,
SSH), turtle programs draw in a web page instead; see webturtle/.
PYKIDS_TURTLE=web or =window forces one or the other.
"""
import json
import os
import runpy
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GREEN, YELLOW, CYAN = "\033[31m", "\033[32m", "\033[33m", "\033[36m"

WEBTURTLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webturtle")


# ---------------------------------------------------------------- child mode

def hint_for(exc):
    """A short, plain-English tip for the most common beginner errors."""
    name = type(exc).__name__
    if isinstance(exc, (IndentationError, TabError)):
        return ("The spaces at the start of a line are wrong. Lines inside an\n"
                "if / for / while / def need 4 spaces, and lines that belong\n"
                "together must line up exactly.")
    if isinstance(exc, SyntaxError):
        return ("Python couldn't read this line. Look for:\n"
                "  - a missing  :  at the end of if / for / while / def\n"
                "  - a missing  )  or  \"  (brackets and quotes come in pairs)\n"
                "  - a typo, like 'pritn' instead of 'print'")
    if isinstance(exc, NameError):
        word = getattr(exc, "name", None) or "that word"
        return (f"Python doesn't know the name '{word}'.\n"
                "Check the spelling (capital letters matter!), and make sure\n"
                "you created it BEFORE the line that uses it.\n"
                "Did you mean text? Then put it in quotes: \"hello\"")
    if isinstance(exc, ZeroDivisionError):
        return "You tried to divide by zero. Even Python can't do that!"
    if isinstance(exc, TypeError):
        return ("You mixed up types of things - maybe text and a number.\n"
                "  number -> text:  str(5)      text -> number:  int(\"5\")\n"
                "Also check a function got the right number of values.")
    if isinstance(exc, ValueError):
        return ("That value doesn't fit. A common one: int(\"hello\") -\n"
                "you can only turn text that looks like a number into a number.")
    if isinstance(exc, IndexError):
        return ("You asked for a position in a list that doesn't exist.\n"
                "Remember: counting starts at 0, so a list of 3 things has\n"
                "positions 0, 1 and 2.")
    if isinstance(exc, KeyError):
        return "That key isn't in the dictionary. Check the spelling."
    if isinstance(exc, AttributeError):
        return ("That thing doesn't have that ability (method).\n"
                "Check the spelling after the dot.")
    if isinstance(exc, ModuleNotFoundError):
        return (f"Python can't find the module '{exc.name}'.\n"
                "Check the spelling, or ask a grown-up to install it.")
    if isinstance(exc, RecursionError):
        return "A function kept calling itself forever. It needs a way to stop!"
    if isinstance(exc, FileNotFoundError):
        return "That file doesn't exist. Check the name and the folder."
    if name == "NotInWebTurtle":
        return ("The web turtle can draw, but it can't do this yet.\n"
                "Keys, clicks and timers need a real turtle window.")
    if name == "TurtleGraphicsError":
        return ("The turtle didn't understand that. Check the spelling of\n"
                "colour names (like \"red\") and shapes (like \"turtle\").")
    return f"Something went wrong ({name}). Read the red line above carefully!"


def show_error(exc, path):
    real = os.path.realpath(path)
    print()
    print(f"{RED}{BOLD}Oops! {type(exc).__name__}{RESET}{RED}: {exc}{RESET}")

    # Where did it happen? Only show lines from the kid's own file.
    if isinstance(exc, SyntaxError) and exc.lineno:
        where = [(exc.lineno, (exc.text or "").rstrip("\n"))]
    else:
        where = [(f.lineno, f.line or "")
                 for f in traceback.extract_tb(exc.__traceback__)
                 if os.path.realpath(f.filename) == real]
    for lineno, line in where[-3:]:
        print(f"{YELLOW}  line {lineno}:{RESET}  {line.strip()}")
    if isinstance(exc, SyntaxError) and exc.text and exc.offset:
        stripped = exc.text.rstrip("\n")
        indent = len(stripped) - len(stripped.lstrip())
        col = max(exc.offset - 1 - indent, 0)
        print(" " * (len(f"  line {exc.lineno}:  ") + col) + f"{RED}^{RESET}")

    print()
    print(f"{CYAN}💡 Hint:{RESET}")
    for line in hint_for(exc).splitlines():
        print(f"   {line}")


def child(path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    if os.environ.get("PYKIDS_WEBTURTLE"):
        sys.path.insert(0, WEBTURTLE)   # `import turtle` gets the web one
    sys.argv = [path]
    try:
        runpy.run_path(path, run_name="__main__")
    except KeyboardInterrupt:
        sys.exit(130)
    except SystemExit:
        raise
    except BaseException as exc:
        show_error(exc, path)
        sys.exit(1)


# ---------------------------------------------------------------- web turtle

def want_web_turtle():
    mode = os.environ.get("PYKIDS_TURTLE", "auto")
    if mode in ("web", "window"):
        return mode == "web"
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return True
    if sys.platform in ("darwin", "win32"):
        return False
    if not os.environ.get("DISPLAY"):   # tkinter always needs X (XWayland counts)
        return True
    # DISPLAY can be set with nothing behind it (WSL without WSLg, a stale
    # SSH session), so really try. Destroyed before it is ever shown.
    try:
        probe = subprocess.run([sys.executable, "-c", "import tkinter; tkinter.Tk().destroy()"],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=5)
        return probe.returncode != 0
    except subprocess.TimeoutExpired:   # e.g. an X server address that never answers
        return True


class TurtleServer:
    """A tiny web server on this machine only. Turtle programs post their
    drawing steps to /draw; the page at / gets them live from /events."""

    MAX_OPS = 200_000   # stop a forever-loop from eating all the memory

    def __init__(self):
        with open(os.path.join(WEBTURTLE, "page.html"), "rb") as f:
            self.page = f.read()
        self.cond = threading.Condition()
        self.run = 0
        self.msgs = []      # everything for the current run, so a new tab can catch up
        self.ops = 0
        self.full = False
        self.clients = 0
        self.opened = False

        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(server.page)))
                    self.end_headers()
                    self.wfile.write(server.page)
                elif self.path == "/events":
                    server.stream(self)
                else:
                    self.send_error(404)

            def do_POST(self):
                prefix = "/draw?run="
                if not self.path.startswith(prefix) or not self.path[len(prefix):].isdigit():
                    self.send_error(404)
                    return
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(server.add(int(self.path[len(prefix):]), body))
                self.send_header("Content-Length", "0")
                self.end_headers()

        for port in range(8765, 8785):   # one per open file, so pick a free one
            try:
                self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
                break
            except OSError:
                continue
        else:
            raise OSError("no free port for the web turtle")
        self.httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{port}/"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def _post(self, msg):   # call with self.cond held
        self.msgs.append(json.dumps(msg, separators=(",", ":")))
        self.cond.notify_all()

    def new_run(self, name):
        with self.cond:
            self.run += 1
            self.msgs, self.ops, self.full = [], 0, False
            self._post({"type": "reset", "file": name})
            return self.run

    def end_run(self, code):
        with self.cond:
            self._post({"type": "end", "code": code})

    def add(self, run, body):
        try:
            ops = json.loads(body)
            assert isinstance(ops, list)
        except (ValueError, AssertionError):
            return 400
        with self.cond:
            if run != self.run:
                return 409          # an old run that was just replaced
            if self.full or self.ops + len(ops) > self.MAX_OPS:
                if not self.full:
                    self.full = True
                    self._post({"type": "full"})
                return 413
            self.ops += len(ops)
            self._post({"type": "ops", "ops": ops})
            first = not self.opened and self.clients == 0
            self.opened = True
        if first:
            self.open_browser()
        return 204

    def open_browser(self):
        # Only where it is sure to open a real browser, never a text one in this pane.
        if shutil.which("termux-open-url"):
            cmd = ["termux-open-url", self.url]
        elif sys.platform == "darwin":
            cmd = ["open", self.url]
        elif shutil.which("explorer.exe"):  # WSL: the Windows browser
            cmd = ["explorer.exe", self.url]
        elif shutil.which("xdg-open") and os.environ.get("DISPLAY"):
            cmd = ["xdg-open", self.url]
        else:
            return
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)

    def stream(self, handler):
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Cache-Control", "no-cache")
        handler.end_headers()
        with self.cond:
            self.clients += 1
        run, pos = None, 0
        try:
            while True:
                with self.cond:
                    if run == self.run and pos >= len(self.msgs):
                        self.cond.wait(15)
                    if run != self.run:
                        run, pos = self.run, 0
                    new = self.msgs[pos:]
                    pos += len(new)
                out = "".join(f"data: {m}\n\n" for m in new) if new else ": still here\n\n"
                handler.wfile.write(out.encode())
                handler.wfile.flush()
        except OSError:
            pass    # the tab was closed
        finally:
            with self.cond:
                self.clients -= 1


# ---------------------------------------------------------------- watch mode

def mtime(path):
    try:
        return os.stat(path).st_mtime_ns
    except FileNotFoundError:
        return None


def banner(path):
    sys.stdout.write("\033[2J\033[3J\033[H")
    stamp = time.strftime("%H:%M:%S")
    print(f"{BOLD}{GREEN}▶ Running {os.path.basename(path)}{RESET}  {DIM}{stamp}{RESET}")
    print(f"{DIM}{'─' * 40}{RESET}")
    sys.stdout.flush()


def footer(code):
    print()
    print(f"{DIM}{'─' * 40}{RESET}")
    if code == 0:
        print(f"{GREEN}✅ Finished!{RESET}")
    elif code in (130, -signal.SIGINT):
        print(f"{YELLOW}⏹  Stopped.{RESET}")
    else:
        print(f"{RED}❌ Your program had an error - see the hint above.{RESET}")
    print(f"{DIM}Save your code to run again, or press Enter here.{RESET}")
    sys.stdout.flush()


def drain_stdin():
    """Throw away anything typed while the program wasn't asking for it."""
    while select.select([sys.stdin], [], [], 0)[0]:
        if not os.read(sys.stdin.fileno(), 1024):
            break


def watch(path):
    # Ctrl-C should stop the kid's program, not this watcher.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    child_cmd = [sys.executable, "-u", os.path.abspath(__file__), "--child", os.path.abspath(path)]
    turtle = None
    if want_web_turtle():
        try:
            turtle = TurtleServer()
        except OSError:
            pass    # turtle programs will then say tkinter is missing

    while True:
        if mtime(path) is None:
            sys.stdout.write("\033[2J\033[H")
            print(f"{YELLOW}Waiting for {path} to exist...{RESET}")
            while mtime(path) is None:
                time.sleep(0.5)

        seen = mtime(path)
        banner(path)
        env = None
        if turtle:
            run = turtle.new_run(os.path.basename(path))
            env = dict(os.environ, PYKIDS_WEBTURTLE=turtle.url, PYKIDS_WEBTURTLE_RUN=str(run))
        proc = subprocess.Popen(child_cmd, cwd=os.path.dirname(os.path.abspath(path)), env=env,
                                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))

        # Running: restart right away if the file is saved again.
        restarted = False
        while proc.poll() is None:
            time.sleep(0.2)
            if mtime(path) != seen:
                proc.kill()
                proc.wait()
                restarted = True
        if restarted:
            time.sleep(0.15)  # let the editor finish writing
            continue

        footer(proc.returncode)
        if turtle:
            turtle.end_run(proc.returncode)
        drain_stdin()

        # Finished: wait for a save or an Enter key.
        while mtime(path) == seen:
            if select.select([sys.stdin], [], [], 0.3)[0]:
                drain_stdin()
                break
        time.sleep(0.15)


def main():
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--child":
        child(args[1])
    elif len(args) == 1:
        watch(args[0])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
