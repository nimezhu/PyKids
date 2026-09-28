# 🐍 PyKids

A small Python learning setup that runs in the terminal. Your code is on the left and its output is on the right. The code runs again every time you save.

## Setup (once)

Debian / Ubuntu:

```bash
sudo apt install tmux fzf micro python3-tk python3-pyflakes
# python3-tk: only needed for turtle
# pyflakes:   micro marks mistakes (like misspelled names) in the margin when you save
chmod +x learn
```

macOS (with [Homebrew](https://brew.sh)):

```bash
brew install tmux fzf micro python-tk pyflakes
chmod +x learn
```

Windows: use WSL (Ubuntu) and follow the Debian / Ubuntu steps. Turtle windows need Windows 11 (WSLg).

Needs tmux 3.0 or newer (popups for F1/F2 need 3.2; older versions open them in a new tab instead).

## Use

| Command | What it does |
|---|---|
| `./learn` | Pick a file from a list and open it |
| `./learn lessons/05_if.py` | Open this file directly |
| `./learn new my_game` | Create `my_code/my_game.py` and open it |
| `./learn --vim` | Use vim instead of micro (lasts until you quit) |
| `./learn stop` | Close everything |

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

## Layout

```
learn           launcher (fzf picker → tmux window: editor | runner)
.kit/run.py     watches the file, reruns it on save, shows errors with a plain-English hint
.kit/tmux.conf  tmux settings (on a private socket, so your own tmux isn't affected)
.kit/micro/     micro config just for this project (your own ~/.config/micro isn't used)
                plug/pykids: indents after a ":" and un-indents after return/break/pass
.kit/cheatsheet.txt  shown by F1
lessons/        01_hello … 10_guess_game, each ends with a 🧩 CHALLENGE
my_code/        the kid's own files
```
