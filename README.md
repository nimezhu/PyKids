# 🐍 PyKids

A small Python learning setup that runs in the terminal. Your code is on the left and its output is on the right. The code runs again every time you save.

## Get it

```bash
git clone https://github.com/nimezhu/PyKids.git
cd PyKids
```

## Setup (once)

**Debian / Ubuntu**

```bash
sudo apt install tmux micro python3-tk python3-pyflakes
```

**macOS** (with [Homebrew](https://brew.sh))

```bash
brew install tmux micro python-tk pyflakes
```

**Windows**: install WSL (Ubuntu), then follow the Debian / Ubuntu steps inside it.

**Android** ([Termux](https://termux.dev))

```bash
pkg install tmux micro python ncurses-utils
pip install pyflakes
```

The phone keyboard has no F-keys, so add them to Termux's extra-keys row. Put this line in
`~/.termux/termux.properties`, then run `termux-reload-settings`:

```
extra-keys = [['ESC','CTRL','TAB','F1','F2','F5','UP','DOWN']]
```

On a narrow screen (under 80 columns, like a phone held upright) the code goes on top and the
output below; turn the phone sideways and they switch to side by side.

**What the packages are for**

| Package | Why |
|---|---|
| tmux 3.0+ | the two-pane cockpit (F1/F2 popups need 3.2; older versions open a new tab instead) |
| micro | the editor (or use vim: `./learn --vim`) |
| pyflakes | micro marks mistakes, like misspelled names, in the margin when you save |
| python3-tk | turtle opens a real window (without it, turtle draws in the web browser) |

If you downloaded a zip instead of using `git clone`, run `chmod +x learn` once.

## Use

| Command | What it does |
|---|---|
| `./learn` | Start menu (see below) |
| `./learn open` | Go straight to the file list |
| `./learn lessons/05_if.py` | Open this file directly |
| `./learn new my_game` | Create `my_code/my_game.py` and open it (`new games/snake` makes a folder too) |
| `./learn --vim` | Use vim instead of micro (lasts until you quit) |
| `./learn stop` | Close everything |

The **start menu** needs one key: **c** continues the file you had open last time, **l** opens the
next lesson, **o** opens the file list, **n** makes a new program, and **q** quits. Enter picks the
first choice.

The **file explorer** (also on **F2**) is a full-screen file manager: the folder's files on the
left, a preview of the chosen file (or folder) on the right, or below it on a narrow screen. It
starts in the folder of the file you had open last, or at the top (`lessons/` and `my_code/`).

| Key | What it does |
|---|---|
| **↑ ↓**, PgUp/PgDn, Home/End | Move |
| **Enter** or **→** | Open the file, or go into the 📁 folder |
| **←** or Backspace (or `..`) | Back to the folder above |
| typing a name | Jump to it (`pl` → `playground.py`) |
| mouse / tap | Click to choose, click again (or double-click) to open; the wheel scrolls |
| **Esc** | Close |

Every folder has **✨ New file here**, and folders in `my_code/` also have **📂 New folder here**,
so kids can keep things tidy in folders like `games/` and `art/`. The name is typed in the bottom
bar, which shows what it will become (`Moon Base` → `moon_base.py`).

It's `.kit/files.py`, using Python's built-in curses. If a Python has no curses, you get a
numbered menu instead: numbers open folders and files, **0** makes a new file, **f** a new
folder, and **b** goes back. Inside `lessons/`, typing `5` opens `05_if.py`.

## Keys inside the cockpit

| Key | What it does |
|---|---|
| **Ctrl-S** or **F5** | Save, which also runs the code |
| **F1** | Cheat sheet (editor keys + Python basics) |
| **Ctrl-/** | Turn comments on/off for the line or selection |
| **Tab** | Finish a word you've already used, or indent the selected lines |
| **F2** | Open another file (each one gets a tab in the bottom bar; click a tab to switch) |
| **Ctrl-C** (in OUTPUT) | Stop a program that's running |
| **Enter** (in OUTPUT) | Run the code again |
| **Ctrl-Q** | Close this file (closing the last one exits) |
| Mouse | Click a pane to move into it. Click the OUTPUT pane to type answers for `input()` |

## Turtle without a window

When a turtle window can't open, turtle programs draw in a web browser instead. This happens on
Termux, over SSH, on WSL without a Linux GUI, or wherever tkinter isn't installed. Your code
doesn't change: it's still `import turtle`.

- The OUTPUT pane shows the link, like `http://127.0.0.1:8765` (each open file gets its own
  number: 8765, 8766, ...).
- On Termux, macOS and WSL the browser opens by itself the first time something is drawn.
- The page redraws every time you save, and the bar at the top says when the program has
  finished or had an error.

It can do everything drawing needs: moving and turning, colours, fills, `circle`, `dot`, `write`,
`stamp`, shapes, `speed` and `tracer`.

Games work too: timers (`ontimer`) and keys (`onkey`, `onkeypress`, `onkeyrelease`, `listen`).
Press the keys in the web page. On a phone or tablet the page shows buttons for the keys your
program uses. If you forget `screen.listen()`, the page reminds you. `done()` waits for the web page to
open (so a game doesn't play out while the browser is still starting), then keeps the game
running until you press Ctrl-C in OUTPUT or save again. Clicks (`onclick`, `ondrag`, ...) and pop-up
questions (`textinput`, `numinput`) don't work there yet, and say so if you use them.

To choose for yourself, set `PYKIDS_TURTLE` before the first `./learn` (or after `./learn stop`):

```bash
PYKIDS_TURTLE=web ./learn      # always the web page
PYKIDS_TURTLE=window ./learn   # always a real window
```

## Layout

```
learn           launcher (start menu → file explorer → tmux window: editor | runner)
.kit/files.py   the file explorer (full screen, keys and mouse)
.kit/run.py     watches the file, reruns it on save, shows errors with a plain-English hint
.kit/tmux.conf  tmux settings (on a private socket, so your own tmux isn't affected)
.kit/micro/     micro config just for this project (your own ~/.config/micro isn't used)
                plug/pykids: indents after a ":" and un-indents after return/break/pass
.kit/webturtle/ turtle that draws in a web page when there's no window (served by run.py)
.kit/cheatsheet.txt  shown by F1
lessons/        01_hello … 11_hungry_turtle, each ends with a 🧩 CHALLENGE
my_code/        the kid's own files (only playground.py is kept in git)
```
