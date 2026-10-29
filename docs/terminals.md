# The terminals

## Keys

Everything a terminal knows goes in: letters with Ctrl or Alt, the arrows,
Home/End, Page Up/Down, Insert/Delete, F1-F12, with Shift, Ctrl and Alt as a
terminal sends them; Czech letters and AltGr characters as typed.

| | |
|---|---|
| Shift+Enter, Alt+Enter, Ctrl+Enter | a new line in Claude Code's input (sent as Esc Enter) |
| Ctrl+C | with something selected: copy; otherwise Ctrl+C |
| Ctrl+Shift+C | copy |
| Ctrl+V, Ctrl+Shift+V | paste - text as text; files and pictures are handed to Claude |
| Shift + mouse | select text (the mouse is tmux's otherwise: wheel = history) |
| *All keys* | the terminal over the whole screen, and Ctrl+W, Ctrl+T, Ctrl+N, Ctrl+Tab, Esc, F11 given to it too (Keyboard Lock - Chrome, Edge); hold Esc to come back |

The row under the terminal has the keys a phone lacks - Ctrl and Alt held for
the next key, Esc, Tab, Shift+Tab, the arrows, Home/End, PgUp/PgDn, Ins/Del,
F1-F12, Ctrl+C/D/R/O/T/L/Z - and *History*, which scrolls back (tmux copy
mode; q comes back).

## Files for Claude

A file dropped onto the terminal, pasted into it, or chosen with *File for
Claude* is written into `.ai-uploads/` of the working directory (Settings →
Claude Code → *Where files given to Claude go*; it gets a `.gitignore` of its
own) and its path typed into the terminal: a picture becomes `[Image #1]`,
another file `@path`, for Claude to read.

## On the server

```
ai --sessions         every terminal, running or ended
ai --attach ID        the same terminal here; Ctrl+b d leaves it running
```
