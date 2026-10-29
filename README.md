# ai

Claude Code on a server, from a web browser.

What used to be an SSH session to the server - Claude Code (and a shell when
one is wanted) in a terminal - is a page: every key and every command of
Claude Code, the screen live as it is drawn. Each terminal runs in tmux on the
server, so closing the browser, losing the connection or restarting this
program ends nothing: the terminal goes on, the pages list it, and it is
opened again from any computer - where it was left.

Files go both ways: dropped onto the terminal or pasted into it (Ctrl+V -
files, pictures, text) they are handed to Claude; dropped onto *Files* they go
into the working directory; any file or folder (as a .zip) is fetched back.
Every conversation Claude Code kept is listed and picked up again
(`claude --resume`) in its folder.

Around it, what the server needs looking after, from the same pages and drawn
exactly as otp draws them: the accounts that may sign in (each with the Linux
account its terminals run as), the certificate, who may reach the pages, the
firewall, the network address, the clock, root's SSH keys, the system's
updates, restarting - and new versions of ai itself, fetched from GitHub,
checked (signed) and put in, by hand or by themselves.

The same engine as [otp](https://github.com/falco81/OTP): one Python file and
the standard library for the daemon, PHP pages that only relay to it, nginx in
front. No pip packages, no Node.js on the server (Claude Code itself aside).

```
    ai --console               everything by its menus (opens by itself when root signs in)
    ai --status                what it is doing, in one screen
    ai --check                 every part of it, checked
    ai --open-web              HTTP and HTTPS let in by the firewall
    ai --sessions              the terminals, running and ended
    ai --attach ID             one of them, here (Ctrl+b d leaves it running)
    ai --new /srv/project      a new Claude Code terminal there
    ai --add-user NAME --role admin
    ai --upgrade-online        the newest version: fetched, checked, put in
```

In colour (colorama), `--json` for scripts; the console and every command:
[docs/console.md](docs/console.md).

## What is in it

| | |
|---|---|
| terminals | Claude Code or a shell, in any folder; tmux underneath (one server per Linux account, in a systemd scope of its own); xterm.js on a WebSocket; reconnects by itself; several windows on one terminal; the whole keyboard - Ctrl/Alt combinations, arrows, F1-F12, Shift+Enter for a new line, and *All keys* (Keyboard Lock) for Ctrl+W, Ctrl+T, Esc…; Ctrl and Alt keys and the special keys on screen for a phone; Claude Code's commands from a list; a box to write long text in |
| files | a browser of the server's files; upload by button, drag and drop or Ctrl+V; download of files and of folders as .zip; text files opened and edited; pictures shown; a file for Claude written into `.ai-uploads/` of the working directory and its path typed in (a picture becomes `[Image #1]`) |
| conversations | every conversation in `~/.claude/projects`, by folder, searched, resumed |
| Claude Code | installed, updated and checked for each Linux account from the pages (Anthropic's installer or npm); signed in in a terminal; the model, the permission mode and more words chosen per terminal; an environment for all of them |
| accounts | administrators and users; a user has terminals of their own only, as the Linux account given, and files in their folders; Linux accounts made from the pages; sign-ins listed and ended; pauses after wrong passwords, the locked out listed and cleared; the columns of every table laid out per person; your own settings to a file and back |
| second step | after the password a code too, for everybody when switched on: an authenticator app (QR code), or a code by e-mail or SMS; set up by each account at its first sign-in, reset by an administrator or `ai --reset-2fa` |
| mail and SMS | SMTP (STARTTLS, TLS, PLAIN, LOGIN, CRAM-MD5, XOAUTH2) or straight to the recipients' MX; SMS through an HTTP gateway, a modem's spool (smstools3, gammu) or a Teltonika; the mails and SMS of a code edited in otp's designer, in Czech and English, as they arrive; otp's outgoing mail - what the other side did not take yet tried again by itself (greylisting), sent again or taken out by hand; notices of warnings and failures by mail |
| certificate and TLS | PEM or PFX uploaded, a request (CSR) made here, or self-signed; the chain checked; standard, Mozilla intermediate or modern TLS, DH parameters, HSTS - nginx asked before it is reloaded |
| data | SQLite, MariaDB or PostgreSQL, moved from one to another from the pages (try, set up, carry everything across, start using it) and back; a dump by the engine's own program every night and portable copies, with the key its secrets are sealed with, downloaded and put back; the database server tuned for its machine; backups to a folder, FTP, FTPS, SFTP, SCP or SMB, locked (AES-256), on a schedule, put back from the pages; the whole configuration exported and imported |
| the server | otp's own panes: firewall (iptables or firewalld) and who may reach the pages, network (NetworkManager), time (chrony), system updates (dnf/apt, followed live), root's SSH keys, restart and power off - changes that could cut you off go back by themselves unless kept |
| upgrades | signed packages (Ed25519) from `https://github.com/falco81/AI/tree/main/release`, the last ten kept there; looked for daily, put in on a click or by themselves; or a package sent from the pages; back to an older version only where that is safe; the terminals go on running through it |
| languages | Czech and English, chosen per person |

Installing it: [INSTALL.md](INSTALL.md). How it is put together:
[docs/how-it-works.md](docs/how-it-works.md). The terminals in detail:
[docs/terminals.md](docs/terminals.md). Signing in, the second step, mail, SMS and TLS:
[docs/security.md](docs/security.md). Copies, backups and putting them back:
[docs/backups.md](docs/backups.md). New versions and how they are made:
[docs/releases.md](docs/releases.md).

## Checking it

```
python3 test/checks.py
```
