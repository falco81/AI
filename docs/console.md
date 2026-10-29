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
  (tmux; Ctrl+b d leaves it running), starts it again or ends it; New Claude
  Code and New shell ask for the folder and the Linux account.
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
ai --users                           # the accounts; --add-user, --passwd, --set-role…
ai --set upgrade_auto=1              # a setting
ai --osup check                      # the system's updates; --osup upgrade, followed here
ai --upgrade-online                  # a new version of ai
```

`ai --help` lists every one.
