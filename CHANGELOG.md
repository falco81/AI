# ai — what changed

Every change is a new version: the number is in `ai.py` (`ai --version`), on
the pages (Settings → About), in the name of the folder and of the archive.

## 1.0.17

- **One tile a conversation in the list**: before 1.0.16 picking a conversation up again started a new terminal
  each time, and with *with the ended ones* the list showed the same chat many times over beside the one
  running it. The terminals that held the same conversation are merged by themselves: the running one - else
  the newest - is kept, the ended copies forgotten. An ended tile is matched only by the conversation it was
  started with, never by a guess from the times.

## 1.0.16

- **A chat keeps its tile**: each chat with Claude Code is given its conversation's ID when it starts
  (`--session-id`), and ai keeps it. Picking a conversation up again (Conversations, the Overview, the chat's
  menu) goes back into the terminal that holds it - opened if it still runs, started again in its own place if
  it ended, with its name and its pin - instead of a new tile. *Start it again* and *Restart* go on with the
  chat's own conversation (`--resume`), not the folder's last one or an empty new one; a `/clear` or a
  `/resume` inside the chat is followed.
- **Close** in the terminal's bar: back to the start page, the chat goes on running on the server.
- **Every version of the models**: Fable 5.1 and 5, Opus 5.5 to 4.6, Sonnet 5.5 to 4.6, Haiku 5.5 and 4.5 by
  name, beside the families (always their newest) - in the new terminal dialog, the start page and Claude
  Code's settings.
- **F5 anywhere keeps the page**: a page opened at its address (Settings -> Network, Time, the Overview's usage,
  the Claude Code tab) asked for its data before the scripts that load it were there, and stayed empty.

## 1.0.15

- The ⋯ of a chat in the list of terminals is in the row's bottom right corner: at the top it lay over the
  chat's name and its state. The state (running, ended, open) is never cut short any more.
- The figures of the Overview's usage line up: each tile's figure on one line whatever its label wraps to, the
  tiles across the whole width, every number of the tables in one font with digits of one width.

## 1.0.14

- **The scroll bar moves with the history again**: Claude Code's full-screen look (now its default for many
  accounts) keeps its history to itself, where the bar beside the terminal could only be a jog wheel standing
  still. Claude Code is started drawing itself the classic way (`CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1`), so
  everything it says is in tmux's history: the bar shows where you are, History shows all of it, a finger
  scrolls it. Settings -> Claude Code -> *Claude Code written into the terminal's history* (on) turns it off;
  `/tui` in a chat switches that one. Chats already running keep their look until started again.
- **The time zone is saved**: the Time pane is drawn again every 10 seconds, and a zone chosen in the list
  drawn before that went into a draft thrown away - the save put in the old one. The draft is refreshed in
  place now.
- **A window over a window goes back to the one under it**: choosing a folder from the new terminal dialog,
  and every question asked twice ("Delete it?"), opens over the dialog; Close or No returns to it as it was.
- **Where a chat may start, said where it is chosen**: the new terminal dialog says whether the folder of the
  chats limits it (or that it may start anywhere), with the way to Settings -> Claude Code -> *The folder of
  the chats*.
- The banner's link to a new version opens Settings -> Upgrades itself, not only Settings.

## 1.0.13

- **What the chats used, on the Overview**: every chat with Claude Code of the accounts you may see, with its
  answers, tokens (written, sent, cache) and an estimated cost at Anthropic's list prices; the same by day, hour
  of the day, model, account and folder, as cost or as tokens, over 7 days to a year. A chat opens in its
  terminal, or is picked up again with `--resume`; found and sorted by newest, dearest, longest. A Claude
  subscription is not billed by the token: the cost is there to compare by.
- **Even spacing in the Claude Code tab**: the account and project bar, the heading, each card and the row of
  tiles are 16 pixels apart everywhere - the tiles touched the card above them.

## 1.0.12

- **The right button anywhere on the list of terminals**, not only on a chat: a new Claude Code or shell, picking
  up a conversation, the ended ones shown or not, finding a terminal, the list kept open or hiding itself, read
  again. A finger held still does the same on a tablet.

## 1.0.11

- **The pinned menu of the settings moves the page aside again**: pinning it moved the Claude Code tab's page
  instead (the first of the two on the page), so the settings stayed under the menu. Pointed at, the menu lies
  over the page as otp's does; pinned, the page is beside it - exactly as otp.
- The banner saying a new version is out is in the banner's own colour, not the browser's visited purple, which
  could not be read on its yellow; every link of the pages is in their blue, visited or not.

## 1.0.10

- **A scroll bar for Claude Code full-screen**: Claude Code's full-screen look keeps its history itself, so
  tmux had none and the bar beside the terminal hid itself. It is now a jog wheel there - dragged up goes back,
  down comes on, its ends a page - and a finger on the terminal moves it, as the mouse wheel does.
- **The rails do not move under the pointer**: the list of terminals slides out with the pin, *New terminal* and
  every chat's icon exactly where they were; what an item of a rail says is shown beside the rail, not over the items.
- **The right button in the Files tab**: on a file or a folder (open, a new Claude Code in it, copy the path,
  a new folder or file in it, download, rename, delete) and on the list (new folder or file, upload, a new
  Claude Code, copy the path, read again); a finger held still does the same on a tablet.

## 1.0.9

- **The history on a tablet**: a finger on the terminal moves back through tmux's history and on again, a bar
  on its right is always there to drag or tap, *Back to now* returns; **History** shows every line tmux keeps,
  with its colours, in a window that scrolls by finger - copied or downloaded.
- **A finger held still is the right button**: on the terminal, the chats, the files and the folders.
- **The folder of the chats** (Settings → Claude Code): a new chat starts in it or under it only - the daemon
  refuses the rest; the folder picker starts there, never goes above it, and makes, renames and deletes
  folders and files (buttons, right button, a finger held still). The chat's own files make new files too.
- **Starting as on claude.ai**: a greeting, a box to write the task in, the folder, model, permission mode and
  effort as chips, Enter starts Claude Code on it; the chats going on as cards below.
- **Every option of Claude Code** in the new chat dialog as fields - name, effort, fallback model, every
  permission mode, allowed / denied / built-in tools, more folders, the system prompt added or replaced, the
  agent, MCP configs, settings and their sources, plugin folders, worktree, fork, session ID, autocompact,
  Remote Control, verbose, debug, safe mode, bare, restricted, Chrome, IDE, brief, no slash commands, a screen
  reader, the first message, a session in the background - kept as how the account's chats start when asked.
- **The Claude Code tab**, for an account and a project: settings (fields and JSON), permissions (allow, ask,
  deny), hooks, memory (CLAUDE.md), MCP servers (added, removed, checked, let in), agents, commands, skills,
  output styles, plugins and marketplaces, background sessions (opened, logs, stopped, removed), usage by day,
  model and folder, keybindings, the sign-in and the doctor.
- The model, the permission mode, the more words and the last folder of a new chat are remembered again: they
  were dropped by the daemon.

## 1.0.8

- **Settings → Accounts as otp's**: every account in one row with its role chosen right there and the same
  buttons in the same places - its Linux account and folders, a new password typed by the administrator,
  stop or let it sign in, remove it, **put its columns back as they come**, reset its second step - a button
  that does not apply dimmed and saying why; how many tables each has laid out; *Signed in now* as otp's,
  each sign-in ended with a question first.
- **The menus hide themselves with their pin on every screen 981 px wide or more**, whatever the browser says
  about a touch screen or a mouse; narrower, they lie across the top as before.

## 1.0.7

- **The menu of the settings in otp's order**: Claude Code, Signing in (codes by e-mail and SMS, message
  texts), Mail (mail, outgoing mail), Access (accounts, certificates and TLS, firewall), Server (network,
  time, restart, system updates, SSH keys), Data (the database, backups, export and import), Updates.
- **The menu hides itself and has its pin** on a computer with a touch screen as well: it was only so where
  the browser said there was a mouse and nothing else (the list of terminals likewise).
- **The address of the database saved as otp saves it**: with Save, into `/etc/ai/config.json` - and only once
  that database opens and its tables are put right; it was refused before.

## 1.0.6

- **The database as otp's**: SQLite, **MariaDB or PostgreSQL**, on this machine or another. *Settings → The
  database* is otp's pane: fill the address in, **try it**, **set it up** (the database and an account with
  rights on it alone, its password made here; the server's administrator used once and kept nowhere),
  **carry everything across**, **start using it** - and back the same way. What is here is never touched by
  any of it. The address is the only setting kept in `/etc/ai/config.json` alone.
- **Dumps by the engine's own program** every night (SQLite's backup, `pg_dump`, `mariadb-dump`) and
  **portable copies** that go into any of the three; both downloaded with the key of their secrets locked with
  a passphrase (or without it), and put back from the list or from a file sent - read and shown first, a copy
  of what is replaced made before. The disk it is on and how fast it grows, every table, check it, give the
  disk back, forget old records, erase the collected data, and the database server tuned for its machine.
- **Otp's outgoing mail**: every mail is tried at once, and what the other side does not take yet
  (greylisting, a server away) is tried again by itself - a code while it is good; refused for good it is
  failed. Sent again or taken out by hand, searched by field, counted in a badge in the menu. A test mail
  goes straight (every step shown) or through it.
- **Otp's message texts designer**: the mail of a code is otp's HTML mail with its plain text part, edited as
  it arrives - bold, italic, colours, links, the parts filled in as blue chips - in Czech and English; the
  SMS beside a phone, counted in parts; previewed, sent as a sample, put back as it comes. The texts of 1.0.5
  are carried over.
- **Upgrades and Accounts as otp's**: this server, the web with the newer versions to choose from, a package
  dropped in and held until Upgrade, going back to a safe version with what changed, the upgrade with how far
  it is, what root said last; the accounts in otp's order.
- The installer: `--with-db mariadb|postgres` puts in the driver and the client tools beforehand (the engine in
  use gets them by itself on an upgrade), `--no-db-restart`.
- A second daemon that cannot have the port no longer writes its own token over the running one's.
- Going back is possible to 1.0.6 at the oldest: the tables changed.

## 1.0.5

- **The files of a chat** beside its terminal: its own folder and what is under it, never above it (the
  daemon refuses a path outside it); the right button hands a file to Claude (`@path`), opens, downloads,
  renames or deletes it; files dropped onto the list are uploaded there.
- **The right mouse button**, with a menu drawn as claude.ai draws one: on the terminal - copy, paste,
  select or copy the screen, a file for Claude, the chat's files, commands, clear the screen - and on a chat
  in the list (or its ⋯): open, open in a new window, pin, rename in its row, its files, a new Claude Code in
  its folder, the command to attach it, start it again, end it. tmux's own menu on that button is off.
- **Pinned chats** at the top of the list, kept with the account (wherever you sign in).
- **The list of terminals and the menu of settings hide themselves** at the edge of the screen as otp's do,
  slide out when pointed at, and stay out once pinned; not pinned is the default, as in otp.
- Signing out (or a sign-in ended by an administrator) closes that window's view of a terminal - never the
  terminal; **Sign out everywhere** under your name. Several sign-ins at once see the same terminals live.

## 1.0.4

What otp has and ai had not yet - taken over from otp 1.0.161, its code and its pages:

- **The second step of signing in**: an authenticator app (a QR code made here), a code by e-mail or by
  SMS; for everybody when switched on (`ai --admin-2fa on`), set up by each account at its first sign-in,
  reset from Accounts or with `ai --reset-2fa NAME`. Until it is given, a sign-in can do nothing else.
- **Secrets sealed** in the database with `/var/lib/ai/secrets.key`, as otp seals them.
- **Locked out**: the addresses and names counted after wrong passwords and codes, listed and cleared
  (Accounts; `ai --lockouts`, `ai --unlock`).
- **Mail**: SMTP or straight to the recipients' MX, a test with every step, the authorities of your own;
  notices of warnings and failures by mail.
- **SMS**: an HTTP gateway, a modem's spool or a Teltonika gateway, a test, its certificates.
- **Message texts** in Czech and English, edited on the pages; **Outgoing mail**: every mail and SMS sent.
- **Certificates and TLS** as otp's: PEM or PFX uploaded, a request (CSR) made here, self-signed; the chain
  sorted and checked; standard, intermediate, modern or custom TLS, DH parameters, HSTS
  (`ai --tls-import`, `--tls-preset`, `--tls-dh`, `--tls-hsts`).
- **The database**: a copy every night with its key, downloaded, put back (`ai --db-copy`, `--db-restore`).
- **Backups to other machines**: a folder, FTP, FTPS, SFTP, SCP, SMB; locked with a password, on a schedule,
  RESTORE.md beside each, put back from the pages or with `ai --restore-bundle`.
- **Export and import** of the whole configuration, with the secrets locked by a passphrase.
- **Going back to an older version** - only to a safe one (`ai --downgrade-check`, `ai --downgrade`).
- **About**: what the server runs on, Python to PHP's extensions.
- **The columns of every table** laid out per person (otp's cols.js); your own settings to a file and back.
- The PHP running the pages said when it may be without the php2shell fix.
- The settings rail grouped as otp's: Access, Messages, Server, Data, Updates.
- The console: the second step, the locked out, a reset, the copies, backups, export, a test mail, going back.
- install.sh puts in smbclient (samba-client) for backups to a share.

## 1.0.3 — 29 October 2026

**The command line and the console, as otp's**
- `ai --console`: otp's console, whole - the menus on a text screen, windows
  and forms, lists to scroll, the live log and the journal with grep as you
  type - with ai's menus: status and checks, terminals (opened right there in
  tmux, started, ended), accounts, settings, firewall and access, the server
  (network, time, updates, SSH keys, certificate, power), upgrades, the
  service. It opens by itself when root signs in (`ai --console-at-login
  on|off`); never inside a terminal of the pages.
- In colour, as otp's: colorama when it is there (install.sh installs
  python3-colorama), the same escape sequences by hand when it is not; every
  table and line coloured; `--help` in two columns; `--json` and `--no-color`.
- New commands: `--check`, `--open-web` (HTTP and HTTPS let in by firewalld,
  ufw or iptables), `--fw status|on|off`, `--fw-open PORT [--from CIDR]`,
  `--fw-del N`, `--pages-from`, `--change-keep`, `--change-back`, `--net`,
  `--ntp`, `--osup check|upgrade|status`, `--sshkeys`, `--sshkey-add`,
  `--cert`, `--reboot`, `--poweroff`, `--screen`, `--end`, `--restart-term`,
  `--again`, `--new … --shell|--continue|--pick|--model`, `--del-user`,
  `--disable-user`, `--enable-user`, `--set-role`, `--set-run-as`,
  `--end-sign-ins`, `--sign-ins`, `--log`, `--set KEY=VALUE`,
  `--upgrade-status`.

## 1.0.2 — 29 October 2026

**install.sh gone through against otp's, line by line**
- The first account: a password given is neither printed at the end nor said
  to be changed; one made by the installer is printed and has to be changed at
  the first sign-in (it did not have to).
- Who may reach the pages is checked before anything is installed, and the
  address you are signed in from over SSH, if it is not among them, is offered
  to be added - not shut out of the pages you just installed.
- php-fpm is reloaded, not restarted - the other PHP sites of the machine go
  on - and started when it was not running.
- Python 3.9 or newer is checked; a command that fails says on which line.
- Debian and Ubuntu get the SSH client only, not an SSH server.
- `--rewrite-nginx` keeps the file there before in /etc/nginx/ai-backups/
  (the last ten).
- At the end, the pages' address by IP too, for until the name is in DNS.
- Without `SSH_CLIENT` (installed from the console) it stopped at once.

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
