# ai — what changed

Every change is a new version: the number is in `ai.py` (`ai --version`), on
the pages (Settings → About), in the name of the folder and of the archive.

## 1.0.1 — 29 October 2026

**install.sh asks, as otp's does**
- A fresh install asks *A few questions* before it does anything, Enter keeping
  what is in brackets: the pages' hostname (FQDN), who may reach the pages, the
  first account and its password (typed twice, unseen; empty = one made and
  printed), the Linux account the terminals run as (made when it is not there),
  and whether to install Claude Code for root. The hostname was taken from the
  machine without asking. `--yes` takes what is in brackets, as before.
- A setting changed on the command line (`ai --setting`) is taken by the
  running daemon within a minute.

## 1.0.0 — 29 October 2026

**The first version: Claude Code on the server, from the browser**
- Terminals of Claude Code and shells in tmux, one tmux server per Linux
  account in a systemd scope of its own: closing the browser, losing the
  connection or restarting ai ends none of them. xterm.js on a WebSocket,
  reconnected by itself; several windows on one terminal; the last screen of
  one that ended kept; started again, ended, renamed, opened in a window of
  its own; `ai --attach` on the server.
- The whole keyboard: Ctrl and Alt combinations, arrows, F1-F12, Shift+Enter
  for a new line, copy and paste, and *All keys* (Keyboard Lock) for the keys
  a browser keeps; Ctrl, Alt and the special keys on screen for a phone;
  Claude Code's commands from a list; a box for long text.
- Files: a browser of the server's files with upload (button, drag and drop,
  Ctrl+V), download (folders as .zip), text files edited, pictures shown; files
  and pictures dropped or pasted into a terminal handed to Claude.
- Conversations: every one Claude Code kept, by folder, resumed in a new
  terminal.
- Claude Code installed, updated and checked for each Linux account from the
  pages; the model, the permission mode and more words per terminal.
- Accounts: administrators and users, each with the Linux account its
  terminals run as and the folders of its files; Linux accounts made here.
- The server, as otp 1.0.161 draws it: firewall and who may reach the pages,
  network, time, system updates, root's SSH keys, restart and power off;
  certificate and TLS; changes that could cut you off taken back unless kept.
- New versions signed (Ed25519), from GitHub or sent from the pages, put in by
  hand or by themselves; the last ten in release/.
- Czech and English.
