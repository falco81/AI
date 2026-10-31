# Signing in, the second step, mail, SMS and TLS

Everything here is as otp does it - the same code, the same pages - with
ai's own words where they differ.

## Signing in

A name and a password, checked by the daemon (PBKDF2-SHA256). Wrong ones are
counted by address and by name: at `login_max_fails` within `login_lock_min`
minutes the address or the name is locked out for that long. *Settings →
Accounts → Locked out* lists what is counted and clears it; so does

```
ai --lockouts
ai --unlock 192.0.2.7        # an address, a name, or all
```

## The second step

`Settings → Signing in → The second step of signing in, for everybody`
(`ai --admin-2fa on`). After a right password the pages ask for a code too.
The first time, each account chooses how and proves it:

- **an authenticator app** - a QR code (made here, no package) scanned once;
  the app's code of now, or one period either side (`totp_window`), each
  code good once;
- **a code by e-mail** - where mail is set up;
- **a code by SMS** - where SMS is set up.

Until the step is given, the sign-in can do nothing else: no page, no
terminal, no file. Once given, it becomes a sign-in of its own (the one the
password opened is ended). A sign-in left at the step ends after a quarter
of an hour. Switching it on ends every other sign-in.

An account that lost its phone: *Accounts → the account → Reset the second
step*, or as root `ai --reset-2fa NAME`. Its app or address is forgotten and
it sets one up again at its next sign-in.

The keys of the apps, the mail server's password, the SMS gateway's key and
password, the backups' password and the certificate's key are sealed in the
database with `/var/lib/ai/secrets.key` (HMAC-SHA256 keystream and tag, as
otp): a copy of the database alone opens none of them.

## Mail

*Settings → Mail*: through a mail server (SMTP: STARTTLS, TLS, or none;
PLAIN, LOGIN, CRAM-MD5, XOAUTH2 or none), or straight to the recipients'
servers (their MX, looked up here). *Try it* sends a test and shows every
step; an authority of your own is added below it. `ai --mail-test ADDRESS`
does the same.

Notices: `notify_to` gets by mail what Events marks as a warning or a
failure - a backup that did not go, a failed upgrade, a newer version - at
most once every `notify_gap_min` minutes, the rest together in the next one.

## SMS

*Settings → Codes by e-mail and SMS*: an HTTP gateway (its URL, method, body, headers and key),
a GSM modem on this machine (a file into the spool of smstools3 or
gammu-smsd), or a Teltonika gateway (TRB140, RUT…) through RutOS's API, its
certificate read from it and trusted with a click.

*Settings → Message texts* holds every word of the mails and the SMS of a
code, in Czech and English, edited as otp's are: written into the mail as it
arrives (bold, italic, a colour, a link), the parts filled in when it is sent
as blue chips, previewed, sent as a sample, put back as it comes. A mail of a
code is HTML with a plain-text part (or plain text only: `code_mail_fmt`).

*Settings → Outgoing mail* is otp's: every mail goes through it - tried at
once, and what the receiving side does not take yet (greylisting, a server
away, a full mailbox) tried again by itself, for `mail_retry_hours` (a code
only while it is good); refused for good it is shown as failed. Sent again or
taken out by hand, searched by field (`to:*@example.cz state:waiting
tries:>2`); the list is kept `mail_keep_days`. What a mail held is sealed while
it waits and thrown away once it went. An SMS sent is written into the events.

## The certificate and TLS

*Settings → Certificates and TLS*: PEM files (in any order, or all in one)
or a PFX / PKCS#12 with its password; a request (CSR) made here, its key
waiting until the certificate comes back; or a self-signed one. The chain is
sorted and checked against the root given. *TLS settings*: standard (TLS 1.2
and 1.3, ECDHE), Mozilla intermediate (with DHE, DH parameters), modern (TLS
1.3 only) or a cipher list of your own; DH parameters of RFC 7919 or made
here; HSTS. Everything is written into nginx and `nginx -t` asked before it
is reloaded - what nginx refuses is never put in.

```
ai --cert
ai --tls-import site.crt site.key chain.pem
ai --tls-preset intermediate --tls-dh ffdhe2048 --tls-hsts 31536000
```

## php2shell

An administrator is told on every page when the PHP running the pages may be
without the fix for php2shell (CVE-2026-109618, CVE-2026-109619); the pages
never let PHP parse a request body, so they are guarded either way.

On AlmaLinux / Rocky / RHEL 9 install.sh puts PHP on the stream `php:8.3`
(8.3.36 has the fix) - on EL 8, which has no php:8.3, on `php:8.2` (8.2.35) -
on an install and on every upgrade: an older PHP, or a newer one without the
fix, is moved there with `dnf module reset`, `dnf module enable` and
`dnf distro-sync 'php*'`, and php-fpm is restarted. A newer PHP that has the
fix is kept.

```bash
./install.sh --upgrade --php-stream 8.3   # this stream whatever PHP is there now
./install.sh --upgrade --no-php-update    # PHP left alone
```

## IPv6

nginx listens on IPv6 whenever the kernel has it: its `[::]` lines are put in
after every change under Settings -> Network and when the daemon starts. The
firewall's rules of ai are written for IPv4 and IPv6 alike. A database server
on this machine can be kept to IPv4 under Settings -> The database -> *Only
IPv4 (127.0.0.1)*: it then listens on 127.0.0.1 alone.
