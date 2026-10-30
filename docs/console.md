# The ai console and the command line

## The console

`ai --console` - ai by its menus, on the server's own screen or over SSH,
taken whole from otp's console: the same screen, windows, forms, lists and
live views. With `ai --console-at-login on` (what install.sh sets the first
time) it opens by itself when **root** signs in; **q** leaves it for the
ordinary shell, and `ai --console` opens it again. It never opens inside a
terminal of the pages (tmux), for a command run over SSH, scp/sftp, or with
`AI_NO_CONSOLE=1`.

```
  Main menu

     1  Status and checks
     2  Live log
     3  Terminals (Claude Code, shells)
     4  Accounts of the pages
     5  Settings
     6  Firewall and access
     7  The server: network, time, updates, SSH keys, certificate, power
     8  Upgrades
     9  The service

 Up/Down move   Enter choose   Esc back   ! shell   q leave
```

- It opens on the **live log**; Esc goes to the menu. Whatever is typed in a
  live view is a grep; Esc clears it, Esc again goes back.
- **Terminals**: the list of terminals - Enter on one opens it right here
  (tmux; Ctrl+b d leaves it running), starts it again, *changes it* (name,
  folder, model, effort, permissions - the chat starts again, going on with
  its conversation), ends it or takes an ended one off the list; New Claude
  Code asks for the folder, the Linux account, the model (any version), the
  effort and the permission mode, New shell for the folder and the account.
  *What the chats used* is the Overview's Claude Code part as text: tokens and
  the cost at list prices, by model, account and folder, and each chat.
- **Settings**: every setting, and *The picture of the sign-in page* - one of
  the drawings, none, or a picture of your own uploaded from a file here.
- **Data**: the copies, the backups, the export - and *The database server*:
  where it listens, and kept to IPv4 (127.0.0.1 only).
- **Firewall and access**: how it stands, *Open HTTP and HTTPS*, a port let
  in, a rule taken away, ai's rules on or off, who may reach the pages, and
  Keep / put the old back for a change on trial.
- Every action is the `ai …` command its window shows in its title, run as
  it would be typed - the console can do nothing the command line cannot.

```bash
ai --console-at-login off      # root lands in the shell; ai --console still works
ai --console-at-login on
```

## Colour

In colour on a terminal - with python3-colorama when it is installed
(install.sh installs it), with the same escape sequences written by hand when
it is not. Plain when piped, with `--no-color`, or `NO_COLOR=1`; `--json` for
scripts.

## The commands people actually type

```bash
ai                                   # what it is doing (= --status)
ai --check                           # tmux, Claude Code, nginx, PHP, the certificate, the firewall
ai --open-web                        # HTTP and HTTPS let in (firewalld, ufw or iptables)
ai --fw status                       # ai's rules, and what it lets in by itself
ai --fw-open 8080 --from 10.0.0.0/8  # a port of your own (goes back unless kept)
ai --change-keep fw                  # keep it
ai --pages-from 192.168.0.0/16       # who may reach the pages (all = everybody)
ai --sessions                        # the terminals
ai --attach ID                       # one of them, here
ai --new /srv/project --continue     # Claude Code there, its last conversation
ai --new /srv/chats/x --model claude-opus-5-5 --effort high --mode acceptEdits
ai --edit ID --model sonnet --effort max   # a chat's choices changed; it goes on with its conversation
ai --forget ended                    # every ended terminal off the list (or one: --forget ID)
ai --usage --days 7                  # what the chats used, and what it costs
ai --signin-art spark                # the picture of the sign-in (no name: which one it is)
ai --signin-logo /root/logo.svg      # a picture of your own there; --signin-logo-forget
ai --db-ipv4                         # where the database server listens; --db-ipv4 only: 127.0.0.1
ai --users                           # the accounts; --add-user, --passwd, --set-role…
ai --set upgrade_auto=1              # a setting
ai --osup check                      # the system's updates; --osup upgrade, followed here
ai --upgrade-online                  # a new version of ai
```

`ai --help` lists every one.
