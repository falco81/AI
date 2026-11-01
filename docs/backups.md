# Copies, backups and putting them back

## The database

One database holds everything of this program: the accounts and their second
step, the settings, the events, the outgoing mail, the list of terminals, the
certificate and TLS of the pages, the firewall. It is a SQLite file on this
machine (`/var/lib/ai/ai.db`) unless `/etc/ai/config.json` says otherwise -
MariaDB or PostgreSQL, on this machine or another. The secrets in it are sealed
with `/var/lib/ai/secrets.key`, kept beside it, and every copy and every dump is
kept with that key beside it (`NAME.key`).

The address of the database (`db_engine`, `db_host`, `db_port`, `db_name`,
`db_user`, `db_password`, `db_timeout_s`, `db_tls`, `db_tls_ca`) is the only
setting kept in the config file alone: a database cannot hold the address of
itself.

### Moving it to another engine - and back

*Settings → The database → Which one it is → **Move to another database…*** (1.0.54)
is a wizard, with **Back** and **Next**:

1. **Where to** - the file on this machine (SQLite), MariaDB or PostgreSQL;
2. **How to reach it** - the server, port, database, account, its password
   (empty: one is made) and how the connection is encrypted;
3. **What is there** - it is reached and said what it holds; where the database
   and the account are not there yet, an administrator of that server makes them
   (used for this one move, stored nowhere); a database that already holds
   records of ai is emptied only when that is agreed - never the one in use;
4. **Go** - what will happen, and whether to switch over at the end;
5. **Moving** - one job: a copy of everything here, the other database made and
   emptied as agreed, everything carried in, every table counted on both sides
   (a move that lost anything stops there), the address written into the config
   file and the daemon started again on it. The terminals go on running.

Until that last step nothing here changes and nothing is written into the
config file - a move that fails leaves the installation as it was. On the
command line: `ai --db-move sqlite|mariadb|postgres --db-host … --db-name …
--db-user … --db-admin root` (its password in `AI_DB_ADMIN_PASSWORD`),
`--empty-first`, `--no-switch`, `--yes`; in `ai --console` under Data.

Going back is the same wizard with the file chosen. The installer puts in
what the engine in use needs (`python3-psycopg2` or `python3-PyMySQL` and the
client tools for the dumps); `install.sh --with-db postgres|mariadb` puts them
in beforehand. `--no-db-restart` takes away the rule that lets the pages
restart PostgreSQL after tuning it.

### Copies and dumps

- A **copy** is every row of every table as a portable file
  (`ai-YYYYMMDD-HHMMSS.json.gz` in `/var/lib/ai/backups`): it goes back into
  any of the three engines.
- A **dump** is made every night at `backup_at` (when `backup_daily` is on) by
  the engine's own program - SQLite's own backup, `pg_dump`, `mariadb-dump` -
  into `/var/lib/ai/dumps`; it goes back into the engine it came off, and can
  be put back by somebody who has never heard of this program. Where that
  program is missing a copy is made instead.

The newest `backup_keep` of each are kept. Either is downloaded with the key
that opens its secrets, locked with a passphrase you give (one `.with-key.tar`
file), or without it; and put back from a kept one or a file sent from the
page - read, checked and shown first, a copy of what it replaces made before
anything changes.

The same pane shows the disk it is on and how fast it grows, what is in each
table, checks the database, gives the disk back (VACUUM / OPTIMIZE / VACUUM
FULL), forgets old records, erases the collected data (the events, the
outgoing mail, the ended terminals - never the accounts or the settings), and
tunes a MariaDB or PostgreSQL server for the machine it runs on.

On the command line:

```
ai --db-copies                       # the copies and the dumps kept
ai --db-copy                         # a copy now (--dump: a dump)
ai --db-restore /var/lib/ai/backups/ai-20261029-033000.json.gz --yes
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
