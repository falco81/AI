# How ai is put together

```
  browser ──HTTPS──▶ nginx ──▶ php-fpm pool "ai" (ai-www) ──▶ ┌── ai.py (root) ──────────────┐
             │                 index.php: relays only          │ JSON API 127.0.0.1:9871      │
             │                                                 │ accounts, sign-ins, settings │
             ├── /ws/term (WebSocket) ───────────────────────▶ │ terminals ─▶ tmux client     │──▶ tmux server
             └── /files/  (the file itself the body) ────────▶ │ files                        │    per Linux account,
                                                               │ the server (ai_os.py)        │    in a systemd scope
                                                               │ upgrades (ai_upgrade.py)     │    of its own
                                                               └──────────────────────────────┘
```

**The daemon decides everything.** `ai.py` is one file using the Python
standard library: the API the page asks (with the token from
`/run/ai/api-token` and the person's session), the WebSocket of the terminals,
the files, the accounts, the settings, the server's panes and new versions,
and the command line. The page holds no logic; nginx hands the terminals and
the files to the daemon straight, with the same session cookie, which the
daemon checks - and that the request came from this page (Origin, a header of
its own on every write).

**A terminal** is a tmux session `ai-<id>` on the tmux server of the Linux
account it runs as (`/var/lib/ai/tmux/<account>/sock`). That server is
started in a systemd scope of its own, outside `ai.service`, so stopping,
restarting or upgrading ai ends no terminal. A browser window looking at a
terminal is one tmux client in a pseudo-terminal of the daemon's, joined to
the window's WebSocket; closing the window ends that client only. A program
that ends leaves its last screen (`remain-on-exit`): start it again or close
it. `ai --attach ID` opens the same terminal on the server's own console.

**Claude Code** is started through the login shell of its account, so its
`~/.local/bin` and profile count, with the words chosen for that terminal
(`--model`, `--permission-mode`, `--continue`, `--resume ID`…) and those in
*Settings → Claude Code*. Its conversations are read from
`~/.claude/projects/*/*.jsonl` for the list - never written.

**The server's panes** are otp's own (`system.js`, from otp's admin.js) and
the daemon answers them in otp's shape, for one node. What root does there -
chrony, root's authorized_keys, dnf/apt - is `ai_os.py`, taken from otp's
root helper. A change of the network, the firewall or who may reach the pages
is *on trial*: it goes back by itself after `revert_s` seconds unless *Keep
it* is pressed.

**Settings** are layered as in otp: the defaults, then `/etc/ai/config.json`,
then what was saved on the pages (in the database).
