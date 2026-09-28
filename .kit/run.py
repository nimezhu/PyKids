#!/usr/bin/env python3
"""Output pane for PyKids.

    run.py FILE          watch FILE and re-run it every time it is saved
    run.py --child FILE  (internal) run FILE once, printing kid-friendly errors
"""
import os
import runpy
import select
import signal
import subprocess
import sys
import time
import traceback

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
RED, GREEN, YELLOW, CYAN = "\033[31m", "\033[32m", "\033[33m", "\033[36m"


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

    while True:
        if mtime(path) is None:
            sys.stdout.write("\033[2J\033[H")
            print(f"{YELLOW}Waiting for {path} to exist...{RESET}")
            while mtime(path) is None:
                time.sleep(0.5)

        seen = mtime(path)
        banner(path)
        proc = subprocess.Popen(child_cmd, cwd=os.path.dirname(os.path.abspath(path)),
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
