# ai — what changed

Every change is a new version: the number is in `ai.py` (`ai --version`), on
the pages (Settings → About), in the name of the folder and of the archive.

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
