# Copies, backups and putting them back

## Copies of the database

One SQLite file, `/var/lib/ai/ai.db`, holds everything of this program: the
accounts and their second step, the settings, the events, the list of
terminals, the certificate and TLS of the pages, the firewall. Every night at
`db_copy_hour` a copy is made with SQLite's own backup (consistent while in
use), packed with the key its secrets are sealed with and `config.json`, into
`/var/lib/ai/copies`; the newest `db_copy_keep` are kept.

*Settings → Database* lists them, makes one now, downloads one, and puts one
back - a copy of what is there now is made first. On the command line:

```
ai --db-copies
ai --db-copy
ai --db-restore /var/lib/ai/copies/ai-copy-20261029-020000.tar.gz --yes
```

## Backups to other machines

*Settings → Backups*: destinations - a folder (an NFS or other mount), FTP,
FTPS (explicit or implicit, a client certificate if it wants one, its
certificate checked or pinned), SFTP or SCP (a key made here or your own, or a
password; the host key trusted once), SMB (a Windows or Samba share, its
domain, SMB3 encryption). *Try it* writes a file there and takes it away
again.

A backup is the database, its key and `config.json`, with a manifest of
checksums and `RESTORE.md` - the exact steps. It is always locked with the
password of the backups (`openssl enc -aes-256-cbc -pbkdf2 -iter 600000`), so
openssl alone opens it on any machine; without a password nothing is sent.
Daily or weekly at a time of your choice, or *Back up now*; old ones go as the
count and the age kept say.

```
ai --backups
ai --backup-now
ai --backup-file /root/
ai --restore-bundle ai-backup-ai-server-20261029-041500.tar.gz.enc --yes
systemctl restart ai
```

The password may come from `AI_BACKUP_PASSWORD` or `--passphrase-file FILE`.

Not in a backup: the files of the Linux accounts - their projects and
`~/.claude` (Claude Code's own sign-in and conversations). Back those up as
files.

## The configuration as one file

*Settings → Export and import*: the settings, the accounts, the certificate and
TLS, who may reach the pages, the firewall and the mail server's authorities.
With the secrets it is locked with a passphrase made then and shown once.
Imported, the firewall comes in as a change on trial - kept, or back by itself.

```
ai --export-config /root/ai-config.json [--with-secrets]
ai --import-config /root/ai-config.json [--replace] --yes
```
