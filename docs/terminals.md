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

## The right mouse button

On the terminal: copy what is selected, paste, select or copy the whole
screen, a file for Claude, the files of the chat, Claude Code's commands, a
longer text, the whole window, clearing the screen - then what the list
offers for the chat. Shift with the right button gives the browser's own
menu. tmux's own menu on that button is switched off.

On a chat in the list (or its ⋯, as on claude.ai): open it, open it in a
new window, **pin** it (pinned chats stay at the top, kept with your
account, so they are pinned wherever you sign in), **rename** it in its row
(Enter keeps the name, Esc does not), its files, a new Claude Code in its
folder, the command to attach it on the server, start it again, end it.

## The files of a chat

*Files* in the terminal's bar opens the chat's own folder beside it - the
folder it was started in and what is under it, never above it (the daemon
refuses a path outside it). The right button on a file hands it to Claude
(`@path`), opens, downloads, renames or deletes it; files dropped onto the
list are uploaded into the folder shown. The whole server stays under the
*Files* tab for an administrator.

## The list of terminals

At the edge of the screen as otp's menu of settings: a strip of icons that
slides out when pointed at, and stays out once pinned (the pin at its top,
or the first button of the terminal's bar). On a phone the list and the
terminal take the screen in turn.

## Nothing ends by closing the browser

Each terminal is a tmux session on the server. Closing the browser, losing
the connection, signing out, the sign-in running out or restarting ai ends
none of them: the next sign-in - from here or from any other computer -
finds them running, Claude Code in the middle of what it was doing. Several
places may be signed in at the same time and look at the same terminal live;
the window typed in last sets its size. Signing out closes only that
window's view (*Sign out everywhere*, under your name, ends every sign-in -
still no terminal).

## On the server

```
ai --sessions         every terminal, running or ended
ai --attach ID        the same terminal here; Ctrl+b d leaves it running
```
