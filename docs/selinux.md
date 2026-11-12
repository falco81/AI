# SELinux and the system's trusted roots

Since 1.0.91. Both came from otp, made for one server: the daemon runs as root and does
each step itself, re-checking every input. otp needs a separate root helper for that.

## SELinux

**Settings → Access → SELinux**, or on the server:

```
ai --selinux-check [--json]          how it stands; exits 1 while something is missing
ai --selinux prepare                 disabled: permissive at the next start; permissive: what ai needs put in
ai --selinux enforce                 enforcing, now and after a restart (asks, or --yes)
ai --selinux permissive              back to permissive, now and after a restart
ai --selinux-report [FILE]           what SELinux says here, as one .tar.gz
```

### What ai needs of it

| what | why |
|---|---|
| module `ai_server` (`deploy/ai_server.cil`) | `/run/ai` and the API token in it labelled `httpd_var_run_t`, so that php-fpm (`httpd_t`) may read the token; systemd may hand `/run/ai` over (`init_t … setattr`) |
| `/var/www/ai` as `httpd_sys_content_t` | the pages |
| `httpd_can_network_connect` | the pages ask the daemon on `127.0.0.1:9871` |
| a port as `postgresql_port_t` / `mysqld_port_t` | only a database on this machine listening outside 5432 / 3306 |
| a port as `http_port_t` | only nginx listening for the pages outside the ports httpd may bind already |

A port that the policy already gives to another service is never taken (`semanage port -a`, never `-m`):
that service could not bind it at its next start.

### The steps

Nothing happens by itself. Disabled stays disabled until somebody asks.

1. **Make it ready (permissive)**, while it is disabled: `SELINUX=permissive` in `/etc/selinux/config`,
   `/.autorelabel` so every file is labelled at the next start, `selinux=0` taken off the kernel's command line
   (grubby) where it is there. The machine is not restarted; restart it when it suits.
2. **Put in what ai needs**, once permissive: the module, the boolean, the ports, `restorecon` of ai's files.
   When it changed anything, what SELinux refused before no longer counts (the time is kept in
   `/var/lib/ai/selinux-applied`, root's).
3. **Switch to enforcing**, only when nothing is missing and nothing was refused. If something was still missing,
   it is put in at this point and the switch is refused: SELinux runs permissive for a while with it first.
4. **Back to permissive** at once if something stops working (or `setenforce 0` on the machine).

What was refused is read with `ausearch -m AVC,USER_AVC -ts boot`, only for the programs ai works with (httpd,
PostgreSQL, MariaDB, systemd, chronyd…) and ai's own paths. Refusals that the policy loaded now allows are not
counted (`audit2why`: *would be allowed by active policy*). This happens when a newer module or a boolean has
settled them.

The daemon looks 2 minutes after it starts, then every half hour, and at once when asked. When enforcing is on
and something ai needs is missing, a card goes to **Settings → Upgrades → To be done by hand**
(`selinux-needs`). SELinux switched off behind ai's back has its own card (`selinux-off`, 1.0.85).

### The report

*Download the report* gives one `.tar.gz` with the mode, the configuration, the labels of ai's paths, the
booleans and ports, the modules, what was refused (raw, grouped, `audit2why`, `audit2allow`) and the processes.
It holds nothing secret. Send it to whoever writes the module when SELinux refuses something that ai's module
does not cover yet. The page says so: *ai does not know this one yet*.

### Install, upgrade, uninstall

`install.sh` (and every upgrade, which runs it) puts in `policycoreutils`, `libselinux-utils`,
`policycoreutils-python-utils`, `audit` and `selinux-policy-targeted` on dnf systems, and starts auditd when
SELinux is on. It puts `ai_server.cil` beside the program and loads it with `semodule -i`. The module is loaded
only when it differs from the copy last loaded (`ai_server.cil.in-policy`). It also sets the boolean and
relabels. `--uninstall` takes the module out (`semodule -r ai_server`).

## The system's trusted roots

**Settings → Certificates and TLS → Trusted roots of the system**, or on the server:

```
ai --os-roots [--json]               what ai added, what others put there, the system's own list
ai --os-roots-add FILE               PEM (a chain adds each authority) or one certificate in DER; - for stdin
ai --os-roots-remove SHA256          12 characters of its fingerprint at least (asks, or --yes)
```

Certificate authorities of your own are put into the trust of the whole operating system, in the system's own way:

| system | folder | tool |
|---|---|---|
| RHEL, AlmaLinux, Rocky | `/etc/pki/ca-trust/source/anchors/*.pem` | `update-ca-trust extract` |
| Debian, Ubuntu | `/usr/local/share/ca-certificates/*.crt` | `update-ca-certificates` |

The distribution's own list is never touched. Both tools merge the folder with it every time they run, also
when an update of `ca-certificates` runs them. ai's files are named `ai-<first 16 of the SHA-256>.pem` (`.crt`),
root's and 0644. ai lists, writes and removes only those. Anything else in the folder is shown and left alone.
ai never writes into a folder that is a link or that others may write.

Every certificate is read by openssl before it is kept:

- **refused**: not an authority (CA:FALSE, or no basicConstraints), a key usage without keyCertSign, a private
  key anywhere in the text
- **said**: run out, not valid yet, an RSA key under 2048 bits, SHA-1 or MD5 (the crypto policy refuses those),
  an intermediate whose root is neither among these nor added with it

What is wanted is the whole set (`oscerts:want` in the database). The daemon brings the machine to it at once
when it changes, at its start, and every half hour. How that went is in `oscerts:node`. The tool runs only when
a file changed. Afterwards each certificate is looked for in the system's list (*not in the system's trust yet*
until it is there). If it could not be done, a card goes to To be done by hand (`osroots-failed`).

ai's own connections (mail, SMS, ACME, the proxy, upgrades from the web) use `ssl.create_default_context()`.
On a Python with an OpenSSL of its own that would look somewhere empty, the daemon points `SSL_CERT_FILE` at the
system's list at its start. The page says whether ai's connections use the system's list.

### For the tests

The folder, the system's list, the tool and the package can each be pointed elsewhere:
`AI_OSROOTS_FLAVOUR`, `AI_OSROOTS_DIR`, `AI_OSROOTS_BUNDLE`, `AI_OSROOTS_EXTRACT`, `AI_OSROOTS_PKG`. SELinux has
the same hooks: `AI_SELINUX_CONFIG`, `AI_SELINUX_RELABEL`, `AI_SELINUX_CMDLINE`, `AI_SELINUX_CIL`,
`AI_SELINUX_LABELS`, `AI_SELINUX_AUDITD`. `test/checks.py` runs both against fake tools on `PATH` and never
touches the machine's own trust or policy.

## The whole chain of the pages' certificate (1.0.93)

A web server that sends its certificate without the intermediate that signed it is trusted by browsers, which
fetch the missing link themselves. Everything else refuses it: Python, curl, openssl, Java, Go, acme's pairing,
monitoring agents, mobile apps (`unable to get local issuer certificate`). Before ai puts a certificate into nginx,
it checks the chain against the system's roots. Uploaded, requested, ACME and acme push certificates are all
checked, the ECDSA twin too. When a link is missing, ai fetches it from the certificate's
*Authority Information Access → CA Issuers* address (DER, PEM or PKCS#7, up to 4 steps) and keeps it with the
certificate. nginx then sends it. A root is never sent. After the reload, ai connects to `127.0.0.1:443` as a
client that fetches nothing and records the result. If that client does not trust the certificate, ai writes an
event and shows a notice at the top. Check it from anywhere:

```
openssl s_client -connect NAME:443 -servername NAME -showcerts </dev/null
```

The output should list at least two certificates and end with `Verify return code: 0 (ok)`.

### Upload the missing authority (1.0.95)

Sometimes ai cannot fetch the intermediate: the certificate names no *CA Issuers* address, the machine has no
way out, or the certificate is from a private CA. Then *Upload the missing authority* on the card of the
certificate takes that authority alone (PEM, `.cer`, `.crt`, `.der`). The dialog names the authority that is
missing. An intermediate goes into the chain in order from the certificate. A root is kept beside it to check
with and is never sent; the card then says *a private root: only clients that trust it take it*. A private key,
or an authority that did not sign the chain's last link, is refused. The button beside it is *Complete the
chain* while the chain is incomplete and *Check the chain* once it is complete.
