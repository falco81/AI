# ai — installing it

## The short version

```bash
tar xzf ai-1.0.2.tar.gz
cd ai-1.0.2
sudo ./install.sh --server-name ai.example.local
```

It installs what it needs, makes the first account and prints its password.
Then open `https://ai.example.local/`, sign in, choose a password of your own,
and start Claude Code from *Terminals* - or first install it, from *Settings →
Claude Code* (or `--claude` here).

To see what it would do without doing it: `sudo ./install.sh --dry-run`.

## What it needs

- AlmaLinux / Rocky / RHEL 9 or 10, or Debian 12 / Ubuntu 24.04.
- Python 3.9 or newer (the system's), tmux, nginx and PHP-FPM 8.x - all
  installed by install.sh. PHP is brought onto a release fixed for php2shell,
  as otp's installer does, and guarded meanwhile.
- Claude Code for each Linux account the terminals run as (root's by default):
  `curl -fsSL https://claude.ai/install.sh | bash`, or from the pages.

## What it installs, and where

| What | Where |
|---|---|
| the daemon | `/usr/local/lib/ai/ai.py`, linked as `/usr/local/bin/ai` |
| its root parts | `/usr/local/lib/ai/ai_os.py` (clock, SSH keys, updates), `ai_upgrade.py` (new versions) |
| the release keys it trusts | `/usr/local/lib/ai/release-keys/` |
| what it is set up with | `/etc/ai/config.json` - what is saved on the pages lives in the database and wins |
| everything it records | `/var/lib/ai/ai.db` (SQLite) |
| the terminals' tmux sockets | `/var/lib/ai/tmux/<account>/sock` |
| its own log | `/var/log/ai/ai.log` |
| the API token the page uses | `/run/ai/api-token` (group `ai-web`) |
| the pages | `/var/www/ai/` |
| the service | `/etc/systemd/system/ai.service` |
| nginx | `/etc/nginx/conf.d/ai.conf`, certificate in `/etc/nginx/certs/ai.pem` |
| PHP-FPM | the pool `ai.conf` (user `ai-www`), `99-php2shell.ini` |

`ai.service` runs as root: it starts terminals as whichever Linux account an
account of the pages is given, and looks after the machine. The page itself
runs as `ai-www` and can reach nothing but the daemon's API. Whoever signs in
as an administrator is, in effect, root on the server - as with SSH: give the
pages a strong password and keep them on your own networks (`--allow`).

## Every option

```
--server-name HOST     the pages' host name (default: this machine's)
--allow CIDR[,..]      who may reach the pages (default: RFC 1918; "all" for everybody)
--admin-user NAME      the first account (admin)
--admin-password PASS  its password (otherwise one is made and printed)
--cert FILE --key FILE the TLS certificate and key (otherwise a self-signed one)
--claude               install Claude Code for root as well
--no-claude            do not offer it
--port N               the daemon's API port on 127.0.0.1 (default 9871)
--php-stream X.Y       the AppStream PHP stream for a machine with no PHP yet (8.3)
--no-php-update        leave PHP as it is
--upgrade              replace the program and the pages, restart; keep the rest
--rewrite-nginx        write the nginx file afresh
--uninstall            remove the service and the pages; keep the data (asks)
--dry-run              print what would happen
--yes                  never ask
```

## Upgrading, uninstalling

```bash
sudo ./install.sh --upgrade      # the terminals go on running
sudo ./install.sh --uninstall    # /var/lib/ai and /etc/ai kept
```

From the pages: *Settings → Upgrades* (see [docs/releases.md](docs/releases.md)).
