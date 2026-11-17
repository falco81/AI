# New versions

## Where they are

`https://github.com/falco81/AI/tree/main/release` - the last ten
`ai-X.Y.Z.tar.gz`. The repository itself is the newest package unpacked.
*Settings → Upgrades* looks there once a day (`upgrade_check`), and with
`upgrade_auto` puts a newer one in by itself at `upgrade_auto_hour`. From the
command line: `ai --upgrade-check`, `ai --upgrade-online`.

## What makes it safe

Every package is signed: `MANIFEST` lists the SHA-256 of every file and
`MANIFEST.sig` is its Ed25519 signature. A server takes a package only when the
signature is by a key in `/usr/local/lib/ai/release-keys/` (put there by
install.sh, root's alone), every file is the one signed and nothing else is in
it, and it is not older than what runs there. Then its own `install.sh
--upgrade --yes` runs, in a systemd unit of its own; the terminals go on.

## Making one

```bash
# the version in ai.py raised, CHANGELOG.md says what is new in it
python3 tools/release.py
```

It writes MANIFEST and MANIFEST.sig, checks the signature against
`deploy/release-keys/`, packs `release/ai-X.Y.Z.tar.gz`, checks it as a server
would, and keeps the ten newest. The private key is never in the repository:
`AI_RELEASE_KEY` (the PEM itself), `AI_RELEASE_KEY_FILE`, or
`~/.ai-release/ai-release-1.key`.

## While an upgrade runs (1.0.96)

The pages follow an upgrade while the things that serve them restart. Those are ai.service, then nginx and
php-fpm. Root writes how far the upgrade is into `/var/www/ai/.upgrade.json`. This is a small JSON file
(`state`, `id`, `version`, `from`, `by`, `part`, `parts`, `words`, `started`, `at`, `said`, `downgrade`), and PHP
reads it straight from disk:

| Writer | When |
|---|---|
| the daemon | `running` 1 of N ("root checks the package") when it starts an upgrade; `done` / `failed` from `status.json` when root's helper ended it before or around install.sh |
| `install.sh --upgrade` | `running` at each `step`, `done` after "Done", `failed` from its EXIT trap (killed too: INT, HUP, TERM) |
| `ai_upgrade.py` | `failed` when it refuses the package or breaks |

While the daemon is away, every call gets `503 {"upgrading": …}`. `?api=upgrade-state` works without the
daemon. `/healthz` says `maintenance`. A `running` state is believed for 30 minutes and an ended one for
10 minutes. The page shows a band under the header and asks every two seconds. When the upgrade is done, the
page reloads itself once. If it failed, the page shows a red band with the reason. To see it without upgrading,
write the file by hand. A JSON object with `"state": "running"`, a version, `part`/`parts` and `"at"` set to
now will do.
