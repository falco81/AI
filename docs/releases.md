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
