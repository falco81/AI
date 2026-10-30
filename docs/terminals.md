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

## The history, on a tablet as well

The page is one more tmux client, so the history is tmux's (50 000 lines a
terminal): the mouse wheel goes back through it by itself. On an iPad or a
phone **a finger on the terminal** moves it up and down, and **the bar on its
right** - always there, wide enough for a finger - is dragged or tapped to a
place; *Back to now* returns to the live screen. **History** in the bar (and
*The whole history* on the right button) shows every line tmux keeps, with
its colours, in a window of its own that scrolls as any page does - copied or
downloaded as text.

Claude Code is started drawing itself the classic way
(`CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1`, Settings -> Claude Code -> *Claude
Code written into the terminal's history*), so all it says is in tmux's
history and the bar shows where you are.

Claude Code in its full-screen look (`/tui fullscreen`, the one that says
*Jump to bottom (ctrl+End)*) keeps its history itself, on the terminal's
alternate screen, and tmux has none to show. The bar is then a jog wheel:
its thumb stays in the middle, dragged up goes back, dragged down comes on,
and a click on the arrows' ends is a page; a finger on the terminal moves it
too. They are turned into the mouse wheel for Claude Code (or Page Up / Page
Down for a program that asked for no mouse), so only someone who may type
into the terminal can do it.

## Starting a chat

The start of *Terminals* is claude.ai's: write the task in the box, choose the
folder, the model, the permission mode and the effort in the chips under it,
and Enter starts Claude Code on it in that folder - it goes on on the server.
*Every option…* opens the full dialog, which has every option of Claude
Code's command line as a field: its name, effort, fallback model, the
permission modes, allowed and denied tools, the built-in tools, more folders,
a system prompt added or replaced, the agent, MCP configs, settings and their
sources, plugin folders, a worktree, fork, a session ID, autocompact, Remote
Control, verbose, debug, safe mode, bare, restricted, Chrome, the IDE, brief,
no slash commands, a screen reader, and the first message - kept with the
account as how its chats start, when asked.

**The folder of the chats** (Settings → Claude Code): when set, a chat starts
in it or in a folder under it, and nowhere else - the daemon refuses the rest.
The folder picker starts there and never goes above it; it makes, renames and
deletes folders and files by its buttons, the right mouse button, or a finger
held still on a tablet.

## Files for Claude

A file dropped onto the terminal, pasted into it, or chosen with *File for
Claude* is written into `.ai-uploads/` of the working directory (Settings →
Claude Code → *Where files given to Claude go*; it gets a `.gitignore` of its
own) and its path typed into the terminal: a picture becomes `[Image #1]`,
another file `@path`, for Claude to read.

## Only the terminal

The four corners in the terminal's bar put the terminal alone over the whole
screen - no bar, no buttons. In Chrome and Edge the keys are locked, so Esc
reaches the terminal (Claude Code needs it); hold Esc to come back. Where a
browser cannot give the screen to the terminal alone, it covers the whole
window and Esc twice comes back. The × in the corner, shown when the mouse
moves, comes back too.

## The right mouse button

In a terminal the right button pastes, as in PuTTY, and what is selected is
copied by itself (the browser asks once whether the page may read the
clipboard). Ctrl with the right button opens the menu. Under your account
(Language and letters) the right button can open the menu instead.

Alt codes work as in Windows: hold Alt, type the digits on the numeric
keypad, let Alt go - Alt+64 is @, Alt+0228 is ä.

The menu, on the terminal: copy what is selected, paste, select or copy the whole
screen, a file for Claude, the files of the chat, Claude Code's commands, a
longer text, the whole window, clearing the screen - then what the list
offers for the chat. Shift with the right button gives the browser's own
menu. tmux's own menu on that button is switched off.

On a tablet a finger held still on the terminal, a chat, a file or a folder
is the right button.

In the *Files* tab: on a file or a folder - open it, a new Claude Code in
it, copy its path, a new folder or file in it, download, rename, delete; on
the list where there is no row - a new folder or file, upload, a new Claude
Code, copy the path, read it again.

Anywhere else on the list of terminals: a new Claude Code or shell, picking
up a conversation, the ended ones shown or not, finding a terminal, every
ended one taken off the list at once, the list kept open or hiding itself,
read again.

On a chat in the list (or its ⋯, as on claude.ai): open it, open it in a
new window, **pin** it (pinned chats stay at the top, kept with your
account, so they are pinned wherever you sign in), **rename** it in its row
(Enter keeps the name, Esc does not), its files, a new Claude Code in its
folder, the command to attach it on the server, start it again, end it.

## Files only in the folder of the chats

Settings -> Claude Code -> *Files only in the folder of the chats* keeps the
Files tab, the files of a chat, downloads and uploads in the folder of the
chats and under it - for every account, administrators too.

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
or the first button of the terminal's bar). Sliding out, nothing in it moves:
the pin, *New terminal* and every chat's icon stay exactly where they were
under the pointer. The menu of the settings and of the Claude Code tab is otp's:
pointed at it lies over the page, pinned the page moves aside beside it. On a phone the list and the
terminal take the screen in turn.

## A chat and its tile

A chat with Claude Code is given its conversation's ID when it starts, and
keeps its tile in the list: picking that conversation up again (Conversations,
the Overview, its menu) opens the tile if it runs, or starts it again in its
own place - name and pin kept - if it ended; *Start it again* and *Restart*
resume that conversation (`--resume`). A `/clear` or `/resume` inside the chat
is followed: the tile holds the conversation it wrote last. **Close** in the
terminal's bar only leaves it: back to the start page, it goes on running.

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
