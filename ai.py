#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai - Claude Code on a server, from a web browser, in one Python file.

The pages are what an SSH session to the server was: Claude Code (and a
shell, when one is wanted) in a terminal drawn in the browser, live, with
every key and every command it knows. Each one runs in tmux on the server,
so closing the browser, losing the connection or restarting this service
ends nothing - the session goes on, and the pages list it to go back to.
Files go both ways: dropped or pasted into the terminal for Claude to read,
or into the working directory, and any file of it fetched back.

Around it, what a server needs looking after from the same pages: the
accounts that may sign in, its network address, the firewall, the
certificate, root's SSH keys, the system's updates, the clock, and new
versions of this program, fetched and checked from the web.

    ai --status                what it is doing, in one screen
    ai --sessions              the terminals running, and whose
    ai --attach ID             one of them, here in this terminal
    ai --add-user NAME         an account for the pages
    ai --passwd NAME           a new password for one
    ai --upgrade-check         whether a newer version is out
    ai --help                  all of it

With nothing at all on the command line it says what it is doing; the
daemon itself is `ai --daemon` (systemd starts it).

The Python standard library and nothing else. The same engine as otp:
one daemon that decides everything, PHP pages that only relay to it.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import binascii
import collections
import fcntl
import ftplib
import getpass
import grp
import hashlib
import hmac
import html
import io
import ipaddress
import json
import mimetypes
import os
import pwd
import re
import secrets
import select
import fnmatch
import shlex
import shutil
import signal
import smtplib
import socket
import sqlite3
import ssl
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import termios
import threading
import time
import uuid
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

__version__ = '1.0.20'

# ---------------------------------------------------------------------------
# Paths and defaults
# ---------------------------------------------------------------------------
CONFIG_FILE = Path(os.environ.get('AI_CONFIG', '/etc/ai/config.json'))
STATE_DIR = Path(os.environ.get('AI_STATE', '/var/lib/ai'))
DB_FILE = STATE_DIR / 'ai.db'
UPGRADE_DIR = STATE_DIR / 'upgrade'
JOBS_DIR = STATE_DIR / 'jobs'
TMUX_DIR = STATE_DIR / 'tmux'
RUN_DIR = Path(os.environ.get('AI_RUN', '/run/ai'))
TOKEN_FILE = RUN_DIR / 'api-token'
LOG_DIR = Path(os.environ.get('AI_LOGDIR', '/var/log/ai'))
LOG_FILE = LOG_DIR / 'ai.log'
LIB_DIR = Path(os.environ.get('AI_LIB', '/usr/local/lib/ai'))
HERE = Path(__file__).resolve().parent
WEB_GROUP = 'ai-web'
NGINX_CONF = Path(os.environ.get('AI_NGINX_CONF', '/etc/nginx/conf.d/ai.conf'))
CERT_DIR = Path(os.environ.get('AI_CERT_DIR', '/etc/nginx/certs'))
CERT_FILE = CERT_DIR / 'ai.pem'
KEY_FILE = CERT_DIR / 'ai.key'
NO_SYSTEM = bool(os.environ.get('AI_NO_SYSTEM'))     # tests: never touch the machine

ROLES = ('admin', 'user')
ROLE_WORDS = {'admin': 'administrator', 'user': 'user'}

DEFAULTS = {
    'api_port': 9871,
    'ui_lang': 'cs',
    'site_name': '',
    'session_idle_h': 12,
    'session_max_h': 168,
    'login_max_fails': 8,
    'login_lock_min': 15,
    'password_min': 10,
    'upgrade_url': 'https://github.com/falco81/AI/tree/main/release',
    'upgrade_check': True,
    'upgrade_auto': False,
    'upgrade_auto_hour': 3,
    'claude_cmd': 'claude',
    'claude_args': '',
    'claude_env': '',
    'claude_classic': True,
    'term_lang': 'C.UTF-8',
    'default_run_as': 'root',
    'default_cwd': '',
    'chat_root': '',
    'chat_upload_dir': '.ai-uploads',
    'upload_most_mb': 4096,
    'retain_events_days': 180,
    'ended_keep_days': 14,
    'revert_s': 120,
    'debug': False,
    # the second step of signing in (otp's admin_2fa)
    'admin_2fa': False,
    'admin_2fa_app': True,
    'admin_2fa_mail': True,
    'totp_window': 1,
    'code_digits': 6,
    'code_ttl_s': 300,
    # mail (otp's Settings -> Mail)
    'mail_mode': 'off',
    'smtp_host': '',
    'smtp_port': 0,
    'smtp_security': 'starttls',
    'smtp_auth': 'auto',
    'smtp_user': '',
    'smtp_password': '',
    'smtp_verify': True,
    'smtp_timeout_s': 20,
    'mail_from': '',
    'mail_from_name': '',
    'mail_reply_to': '',
    'mail_helo': '',
    'mail_direct_port': 25,
    'mail_direct_tls': 'if-offered',
    'mail_dns': '',
    'mail_lang': 'cs',
    'sms_mode': 'off',
    'sms_url': '',
    'sms_method': 'POST',
    'sms_body': '',
    'sms_headers': '',
    'sms_token': '',
    'sms_spool_dir': '/var/spool/sms/outgoing',
    'sms_prefix': '+420',
    'sms_ok_status': '',
    'sms_tel_host': '',
    'sms_tel_https': True,
    'sms_tel_verify': False,
    'sms_tel_user': 'admin',
    'sms_tel_password': '',
    'sms_tel_api': 'rest',
    'sms_tel_modem': '',
    'sms_plain': True,
    'admin_2fa_sms': True,
    'notify_to': '',
    'notify_level': 'warn',
    'notify_gap_min': 15,
    # copies of the database (otp's Database pane)
    'backup_daily': True,
    'backup_at': '03:30',
    'backup_keep': 14,
    'upgrade_downgrade': True,
    'mail_retry_hours': 24,
    'mail_keep_days': 14,
    'code_lang': 'cs',
    'code_mail_fmt': 'html',
    # backups to other machines (otp's)
    'rbackup': False,
    'rbackup_at': '04:15',
    'rbackup_every': 'daily',
    'rbackup_day': 7,
    'rbackup_keep': 30,
    'rbackup_keep_days': 0,
    'rbackup_password': '',
}
# Kept sealed in the database (secrets.key), never shown back to the pages.
SEALED_KEYS = ('smtp_password', 'rbackup_password', 'sms_token', 'sms_tel_password')

# The settings the pages show, pane by pane. Everything else in DEFAULTS is
# set in /etc/ai/config.json or by its own page (the firewall, the network...).
SCHEMA = [
    # key, pane, kind, label, help, extra
    ('site_name', 'about', 'str', 'Name of this installation',
     'What the pages call this server, beside its host name. Empty: the host name alone.', {}),
    ('ui_lang', 'about', 'choice', 'Language of the pages',
     'For whoever has not chosen one of their own (the account menu).',
     {'choices': [['cs', 'Čeština'], ['en', 'English']]}),
    ('claude_cmd', 'claude', 'str', 'The command that starts Claude Code',
     'Looked up on the PATH of the account a terminal runs as (its login shell, so ~/.local/bin '
     'counts), or a full path.', {}),
    ('claude_args', 'claude', 'str', 'Always started with',
     'Words added to every start of Claude Code, as on its command line - for example '
     '--model opus. Each new terminal can add its own.', {}),
    ('claude_env', 'claude', 'text', 'Environment of every terminal',
     'One NAME=value a line, set in every terminal started from here (an API key, a proxy, '
     'DISABLE_AUTOUPDATER=1...). Lines starting with # are ignored.', {'secret': True}),
    ('claude_classic', 'claude', 'bool', 'Claude Code written into the terminal\'s history',
     'On: Claude Code draws itself the classic way (CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1), so what it '
     'says goes into tmux\'s history - the scroll bar beside the terminal shows where you are, History '
     'shows all of it, a finger scrolls it on a tablet. Off: its full-screen look, which keeps the history '
     'itself (the bar is then only a jog wheel). /tui in Claude Code switches one chat.', {}),
    ('term_lang', 'claude', 'str', 'Language and characters of the terminals',
     'LANG of every terminal. A UTF-8 one is needed for Claude Code to draw itself.', {}),
    ('default_run_as', 'claude', 'str', 'Runs as, unless the account says otherwise',
     'The Linux account a terminal runs as for an account that has none of its own.', {}),
    ('chat_root', 'claude', 'str', 'The folder of the chats',
     'A new chat starts in this folder or in one under it, and nowhere else: the folder picker '
     'offers it and what is under it, never the rest of the machine. Empty: anywhere the account '
     'may go.', {}),
    ('default_cwd', 'claude', 'str', 'Working directory offered first',
     'The directory a new terminal starts in, unless one is chosen. Empty: the home directory '
     'of the account it runs as.', {}),
    ('chat_upload_dir', 'claude', 'str', 'Where files given to Claude go',
     'A file dropped or pasted into a terminal is written here - a folder inside the working '
     'directory, or a full path - and its path typed into the terminal. It gets a .gitignore '
     'of its own, so git leaves it alone.', {}),
    ('upload_most_mb', 'claude', 'int', 'Largest file taken (MB)',
     'A file sent from the browser, to the working directory or to Claude.', {'min': 1, 'max': 65536}),
    ('ended_keep_days', 'claude', 'int', 'Ended terminals kept (days)',
     'How long a terminal that has ended stays in the list, to look at its last screen.',
     {'min': 0, 'max': 365}),
    ('session_idle_h', 'people', 'int', 'Signed out after (hours without a click)',
     'A sign-in nobody used for this long ends by itself. The terminals go on running.',
     {'min': 1, 'max': 720}),
    ('session_max_h', 'people', 'int', 'Signed out after at most (hours)',
     'However much it is used, a sign-in ends after this long.', {'min': 1, 'max': 8760}),
    ('login_max_fails', 'people', 'int', 'Wrong passwords before a pause',
     'From one address or for one name; then nobody signs in from there for the pause below.',
     {'min': 3, 'max': 100}),
    ('login_lock_min', 'people', 'int', 'The pause (minutes)', '', {'min': 1, 'max': 1440}),
    ('password_min', 'people', 'int', 'Shortest password', '', {'min': 8, 'max': 128}),
    ('revert_s', 'fw', 'int', 'Changes that could cut you off go back after (seconds)',
     'A change of the network, the firewall or who may reach the pages is taken back by itself '
     'unless it is kept within this time - pressed Keep it, from the old address or the new.',
     {'min': 30, 'max': 3600}),
    ('retain_events_days', 'db', 'int', 'Keep the events (days)', '', {'min': 7, 'max': 3650}),
    ('upgrade_url', 'upgrade', 'str', 'Where new versions are looked for',
     'A GitHub folder (https://github.com/OWNER/REPO/tree/BRANCH/FOLDER), a web page or a '
     'folder listing with ai-X.Y.Z.tar.gz links, or one package\'s address. HTTPS only.', {}),
    ('upgrade_downgrade', 'upgrade', 'bool', 'Offer going back to an older version',
     'Going back to an older version on these pages - only to one that is safe on this database. Off: the '
     'card is not shown, and ai --downgrade alone does it.', {}),
    ('upgrade_check', 'upgrade', 'bool', 'Look once a day',
     'Whether there is a newer version - it is only said, unless the next switch is on too.', {}),
    ('upgrade_auto', 'upgrade', 'bool', 'Put a newer version in by itself',
     'Once a day, at the hour below: a newer signed version found there is fetched, checked and '
     'put in. The terminals go on running; the pages reconnect after a few seconds.', {}),
    ('upgrade_auto_hour', 'upgrade', 'int', 'At what hour', 'Local time of this server, 0-23.',
     {'min': 0, 'max': 23}),
    ('debug', 'about', 'bool', 'Debug log', 'Writes far more into /var/log/ai/ai.log.', {}),
    ('db_engine', 'db', 'choice', 'The database',
     'Which database everything is kept in: a SQLite file on this machine, or a MariaDB or a PostgreSQL '
     'server. Kept in config.json, not in the database - changed only by the steps of the card below '
     '(try it, set it up, carry everything across, start using it).',
     {'choices': [['sqlite', 'the file on this machine (SQLite)'], ['mariadb', 'MariaDB'],
                  ['postgres', 'PostgreSQL']], 'file': True}),
    ('db_host', 'db', 'str', 'Server', 'Its name or address. Empty: this machine.',
     {'file': True, 'when': ['db_engine', 'sqlite-not']}),
    ('db_port', 'db', 'int', 'Port', '0: the engine\'s own (3306, 5432).',
     {'min': 0, 'max': 65535, 'file': True, 'when': ['db_engine', 'sqlite-not']}),
    ('db_name', 'db', 'str', 'Database', 'Letters, digits and _ only.',
     {'file': True, 'when': ['db_engine', 'sqlite-not']}),
    ('db_user', 'db', 'str', 'Account', 'The account this program signs in to it with.',
     {'file': True, 'when': ['db_engine', 'sqlite-not']}),
    ('db_password', 'db', 'password', 'Password', 'Kept in config.json (root only). Set it up makes one.',
     {'secret': True, 'file': True, 'when': ['db_engine', 'sqlite-not']}),
    ('db_timeout_s', 'db', 'int', 'Wait for it (s)', 'How long a connection is waited for.',
     {'min': 1, 'max': 300, 'file': True, 'when': ['db_engine', 'sqlite-not']}),
    ('db_tls', 'db', 'choice', 'Encrypted', 'How the connection to the server is encrypted.',
     {'choices': [['', 'as the driver decides'], ['require', 'encrypted, the certificate not checked'],
                  ['verify-ca', 'encrypted, signed by the authority below'],
                  ['verify-full', 'encrypted, the authority and the name checked']], 'file': True,
      'when': ['db_engine', 'sqlite-not']}),
    ('db_tls_ca', 'db', 'str', 'The authority of its certificate (a file)', 'A PEM file on this machine.',
     {'file': True, 'when': ['db_tls', ['verify-ca', 'verify-full']]}),
    ('backup_daily', 'db', 'bool', 'A copy every night',
     'A copy of everything - every row of every table, in a shape any of the three engines takes back - '
     'with the key its secrets are sealed with beside it, into /var/lib/ai/backups; and a dump by the '
     'engine\'s own program into /var/lib/ai/dumps.', {}),
    ('backup_at', 'db', 'str', 'At', 'When, as HH:MM on this machine\'s clock.',
     {'when': ['backup_daily', [True]]}),
    ('backup_keep', 'db', 'int', 'Copies kept', 'Of each kind; older ones are taken away.',
     {'min': 1, 'max': 365, 'when': ['backup_daily', [True]]}),
    ('rbackup', 'backup', 'bool', 'Backups to the destinations on a schedule',
     'A backup is made and sent to every destination switched on, at the time below. Back up now '
     'sends one whenever wanted.', {}),
    ('rbackup_at', 'backup', 'str', 'At', 'When, as HH:MM on this machine\'s clock.',
     {'when': ['rbackup', [True]]}),
    ('rbackup_every', 'backup', 'choice', 'How often', 'daily, or weekly on the day below.',
     {'choices': [['daily', 'daily'], ['weekly', 'weekly']], 'when': ['rbackup', [True]]}),
    ('rbackup_day', 'backup', 'int', 'On (1 Monday - 7 Sunday)', 'The day of a weekly backup.',
     {'min': 1, 'max': 7, 'when': ['rbackup_every', ['weekly']]}),
    ('rbackup_keep', 'backup', 'int', 'Backups kept at each destination',
     'How many of this server\'s backups each destination keeps; the oldest go once a new one is there.',
     {'min': 1, 'max': 1000}),
    ('rbackup_keep_days', 'backup', 'int', 'And none older than (days)',
     'Older ones are taken away too - 0: only the count above decides.', {'min': 0, 'max': 3650}),
    ('rbackup_password', 'backup', 'password', 'The password of the backups',
     'Every backup is locked with it (AES-256, opened with ai or with openssl alone). Keep it apart '
     'from the backups: without it none of them can be opened. Without one nothing is sent.', {'secret': True}),
    ('admin_2fa', 'people', 'bool', 'The second step of signing in, for everybody',
     'After a right password these pages ask for a code too: from an authenticator app, or sent '
     'by e-mail. The first time, each account chooses how and proves it; Accounts → Reset the '
     'second step, or ai --reset-2fa NAME as root, takes it away again. Switched on, every other '
     'sign-in ends, so each gives its second step.', {}),
    ('admin_2fa_app', 'people', 'bool', 'Offered: an authenticator app',
     'Google or Microsoft Authenticator, FreeOTP, 1Password... - a QR code scanned once.',
     {'when': ['admin_2fa', [True]]}),
    ('admin_2fa_mail', 'people', 'bool', 'Offered: a code by e-mail',
     'Only where sending mail is set up (Settings → Mail).', {'when': ['admin_2fa', [True]]}),
    ('admin_2fa_sms', 'people', 'bool', 'Offered: a code by SMS',
     'Only where sending SMS is set up (Settings → SMS).', {'when': ['admin_2fa', [True]]}),
    ('code_lang', 'codes', 'choice', 'Language of the codes',
     'The language of a mail or SMS with a code, where the page it was asked from says none.',
     {'choices': [['cs', 'Čeština'], ['en', 'English']]}),
    ('code_mail_fmt', 'codes', 'choice', 'A mail with a code is', '',
     {'choices': [['html', 'HTML - with the plain text beside it'], ['text', 'plain text only']]}),
    ('sms_mode', 'codes', 'choice', 'How SMS is sent',
     'An SMS gateway with an HTTP API (most operators and services), a GSM modem on this machine run '
     'by smstools3 or gammu-smsd (a file into its spool folder), or a Teltonika gateway (TRB140, RUT…) '
     'on the network through its own API. Off: no code goes by SMS.',
     {'choices': [['off', 'off - no SMS is sent'], ['http', 'an SMS gateway with an HTTP API'],
                  ['spool', 'a modem on this machine - a file into the spool of smstools / gammu'],
                  ['teltonika', 'a Teltonika gateway (TRB140, RUT…) on the network']]}),
    ('sms_prefix', 'codes', 'str', 'Country code for numbers written without one',
     'A number typed as 603 123 456 becomes +420603123456. Empty: a number has to be typed with its '
     'country code.', {'when': ['sms_mode', ['http', 'spool', 'teltonika']]}),
    ('sms_plain', 'codes', 'bool', 'Without accents (one SMS, not two)',
     'A letter with an accent makes the whole SMS the wide alphabet, 70 characters a part instead of 160.',
     {'when': ['sms_mode', ['http', 'spool', 'teltonika']]}),
    ('sms_url', 'codes', 'str', 'The gateway\'s address (URL)',
     'Where the message is sent. {to} is the number (+420…), {to_digits} the number without +, {text} '
     'the message, {token} the key below. https://sms.example.cz/api/send?to={to}&text={text}',
     {'when': ['sms_mode', ['http']]}),
    ('sms_method', 'codes', 'choice', 'HTTP method', 'POST sends the body below; GET only the address.',
     {'choices': [['POST', 'POST'], ['GET', 'GET']], 'when': ['sms_mode', ['http']]}),
    ('sms_token', 'codes', 'password', 'The gateway\'s key ({token})',
     'Its API key or password, kept sealed in the database and put where {token} is written.',
     {'secret': True, 'when': ['sms_mode', ['http']]}),
    ('sms_ok_status', 'codes', 'str', 'The gateway said it was sent when the answer holds',
     'Some gateways answer 200 to everything: a word their answer holds only when it was sent. Empty: any 2xx.',
     {'when': ['sms_mode', ['http']]}),
    ('sms_body', 'codes', 'text', 'What is sent (body)',
     'For POST. Starting with { it is JSON: {"to": "{to}", "text": "{text}"}; otherwise a form: '
     'to={to}&text={text}. Empty: the address alone.', {'when': ['sms_mode', ['http']]}),
    ('sms_headers', 'codes', 'text', 'Headers', 'One a line, Name: value - Authorization: Bearer {token}.',
     {'when': ['sms_mode', ['http']]}),
    ('sms_spool_dir', 'codes', 'str', 'The spool folder',
     'smstools3: /var/spool/sms/outgoing. A file "To: 420…" and the text is written there and the '
     'modem\'s daemon sends it.', {'when': ['sms_mode', ['spool']]}),
    ('sms_tel_host', 'codes', 'str', 'The Teltonika\'s address', 'The gateway on the network: 192.168.1.1, or host:port.',
     {'when': ['sms_mode', ['teltonika']]}),
    ('sms_tel_api', 'codes', 'choice', 'Its interface',
     'RutOS 7 offers its own API out of the box; the older Post/Get service has to be switched on by hand.',
     {'choices': [['rest', 'RutOS\'s own API (/api, RutOS 7 - the default)'],
                  ['cgi', 'the older Post/Get SMS service (/cgi-bin/sms_send)']], 'when': ['sms_mode', ['teltonika']]}),
    ('sms_tel_modem', 'codes', 'str', 'Its modem', 'Which modem sends - 1-1, 3-1… Empty: the one the gateway names first.',
     {'when': ['sms_mode', ['teltonika']]}),
    ('sms_tel_https', 'codes', 'bool', 'Over HTTPS', 'HTTPS keeps its password and the codes off the wire.',
     {'when': ['sms_mode', ['teltonika']]}),
    ('sms_tel_verify', 'codes', 'bool', 'Check its certificate',
     'Checked against the certificates imported below - the gateway\'s own or the authority that signed it; '
     'with none imported, against the authorities this machine trusts. Off: any certificate is taken.',
     {'when': ['sms_mode', ['teltonika']]}),
    ('sms_tel_user', 'codes', 'str', 'Its user', 'An account of the gateway that may use its API.',
     {'when': ['sms_mode', ['teltonika']]}),
    ('sms_tel_password', 'codes', 'password', 'Its password', 'Kept sealed in the database. Never shown again.',
     {'secret': True, 'when': ['sms_mode', ['teltonika']]}),
    ('totp_window', 'people', 'int', 'Codes of the app taken this many periods early or late',
     'A period is 30 s. 1 forgives a phone half a minute out; 0 takes only the code of now.',
     {'min': 0, 'max': 4, 'when': ['admin_2fa', [True]]}),
    ('code_digits', 'codes', 'int', 'Digits of a code sent by mail', '',
     {'min': 6, 'max': 8, 'when': ['admin_2fa', [True]]}),
    ('code_ttl_s', 'codes', 'int', 'A code sent is good for (s)', '',
     {'min': 60, 'max': 1800, 'when': ['admin_2fa', [True]]}),
    ('mail_mode', 'mail', 'choice', 'Sending mail',
     'How a mail of these pages leaves this machine: through your mail server, or straight to '
     'the recipient\'s (its MX record, looked up here) - which many networks block on port 25.',
     {'choices': [['off', 'off - no mail is sent'], ['smtp', 'through a mail server (SMTP)'],
                  ['direct', 'straight to the recipients\' servers (MX)']]}),
    ('smtp_host', 'mail', 'str', 'Mail server',
     'The mail server\'s name or address: smtp.example.cz, or a relay in your network.',
     {'when': ['mail_mode', ['smtp']]}),
    ('smtp_port', 'mail', 'int', 'Port',
     '0 picks the usual one for the encryption: 587 for STARTTLS, 465 for TLS, 25 without.',
     {'min': 0, 'max': 65535, 'when': ['mail_mode', ['smtp']]}),
    ('smtp_security', 'mail', 'choice', 'Encryption',
     'STARTTLS on 587 is what most servers want; SMTPS on 465 is TLS from the first byte.',
     {'choices': [['starttls', 'STARTTLS - plain, then encrypted (587)'], ['tls', 'TLS from the start (465)'],
                  ['starttls-if', 'STARTTLS where the server offers it'], ['none', 'none - plain text (25)']],
      'when': ['mail_mode', ['smtp']]}),
    ('smtp_auth', 'mail', 'choice', 'Signing in',
     'How this machine signs in to the server. None where the relay lets this machine send as it is.',
     {'choices': [['auto', 'what the server offers'], ['none', 'none - the server lets this machine send'],
                  ['plain', 'PLAIN'], ['login', 'LOGIN'], ['cram-md5', 'CRAM-MD5'],
                  ['xoauth2', 'XOAUTH2 (the password is the access token)']],
      'when': ['mail_mode', ['smtp']]}),
    ('smtp_user', 'mail', 'str', 'Account', '', {'when': ['mail_mode', ['smtp']]}),
    ('smtp_password', 'mail', 'password', 'Password',
     'Kept sealed in the database; never shown again. Empty keeps the one saved.',
     {'secret': True, 'when': ['mail_mode', ['smtp']]}),
    ('smtp_verify', 'mail', 'bool', 'Check the server\'s certificate',
     'Off only for a server with a certificate nobody signed - its password then goes to whoever '
     'answers in its place.', {'when': ['mail_mode', ['smtp']]}),
    ('smtp_timeout_s', 'mail', 'int', 'Wait for the server (s)', '',
     {'min': 3, 'max': 300, 'when': ['mail_mode', ['smtp', 'direct']]}),
    ('mail_from', 'mail', 'str', 'From (address)',
     'The address the mails come from - one your mail server lets this machine send as.',
     {'when': ['mail_mode', ['smtp', 'direct']]}),
    ('mail_from_name', 'mail', 'str', 'From (name)', '', {'when': ['mail_mode', ['smtp', 'direct']]}),
    ('mail_reply_to', 'mail', 'str', 'Replies to', 'Empty: to the From address.',
     {'when': ['mail_mode', ['smtp', 'direct']]}),
    ('mail_helo', 'mail', 'str', 'This machine calls itself (EHLO)', 'Empty: its host name.',
     {'when': ['mail_mode', ['smtp', 'direct']]}),
    ('mail_direct_port', 'mail', 'int', 'Port of the recipients\' servers', '',
     {'min': 1, 'max': 65535, 'when': ['mail_mode', ['direct']]}),
    ('mail_direct_tls', 'mail', 'choice', 'Encryption to the recipients\' servers', '',
     {'choices': [['if-offered', 'encrypted where the server offers it'],
                  ['required', 'always encrypted, the certificate checked']],
      'when': ['mail_mode', ['direct']]}),
    ('mail_dns', 'mail', 'str', 'DNS servers for the recipients\' domains',
     'Addresses, separated by commas. Empty: the ones this machine uses (/etc/resolv.conf).',
     {'when': ['mail_mode', ['direct']]}),
    ('mail_lang', 'mail', 'choice', 'Language of the mail', '',
     {'choices': [['cs', 'Čeština'], ['en', 'English']], 'when': ['mail_mode', ['smtp', 'direct']]}),
    ('mail_retry_hours', 'mail', 'int', 'Try a mail not delivered for (hours)',
     'A mail the other side did not take yet (greylisting, a server away, a full mailbox) is tried again '
     'by itself, ever less often, for this long; then it is given up.',
     {'min': 1, 'max': 168, 'when': ['mail_mode', 'off-not']}),
    ('mail_keep_days', 'mail', 'int', 'Keep the list of mails sent for (days)',
     'Outgoing mail lists what went and what did not; what a mail held is never kept once it went.',
     {'min': 1, 'max': 365, 'when': ['mail_mode', 'off-not']}),
    ('notify_to', 'mail', 'str', 'Notices go to',
     'Addresses, separated by commas, that are told by mail what Events marks as a warning or a '
     'failure - a backup that did not go, a newer version, an account locked out. Empty: nobody.',
     {'when': ['mail_mode', ['smtp', 'direct']]}),
    ('notify_level', 'mail', 'choice', 'What they are told', '',
     {'choices': [['warn', 'warnings and failures'], ['error', 'failures only']],
      'when': ['mail_mode', ['smtp', 'direct']]}),
    ('notify_gap_min', 'mail', 'int', 'At most one notice mail every (minutes)',
     'What happens in between goes in the next one, together.',
     {'min': 1, 'max': 1440, 'when': ['mail_mode', ['smtp', 'direct']]}),
]
SCHEMA_KEYS = {s[0]: s for s in SCHEMA}

# The database this program opens: kept in config.json alone (otp's
# FILE_ONLY_KEYS) - a database cannot hold its own address, and a machine
# whose database will not open still has to be put right from its pages.
DB_DEFAULTS = {'db_engine': 'sqlite', 'db_host': '', 'db_port': 0, 'db_name': 'ai', 'db_user': 'ai',
               'db_password': '', 'db_timeout_s': 10, 'db_tls': '', 'db_tls_ca': ''}
DEFAULTS.update(DB_DEFAULTS)
FILE_ONLY_KEYS = tuple(DB_DEFAULTS)

CONFIG = dict(DEFAULTS)


def load_file_config_all():
    c = dict(DEFAULTS)
    c.update(load_file_config())
    return c


def load_file_config():
    try:
        with open(CONFIG_FILE, encoding='utf-8') as f:
            got = json.load(f)
        if isinstance(got, dict):
            return {k: v for k, v in got.items() if not k.startswith('_')}
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        log('%s cannot be read: %s' % (CONFIG_FILE, e), 'warn')
    return {}


def config_rebuild(store=None):
    """The defaults, then config.json, then what was saved on the pages."""
    c = dict(DEFAULTS)
    c.update(load_file_config())
    if store is not None:
        try:
            for k, v in store.settings_all().items():
                if k in DEFAULTS and k not in FILE_ONLY_KEYS:
                    c[k] = v
        except Exception:                               # noqa: BLE001 - the file's values, then
            pass
    CONFIG.clear()
    CONFIG.update(c)
    return c


# ---------------------------------------------------------------------------
# The log this daemon writes about itself
# ---------------------------------------------------------------------------
LOG_LOCK = threading.Lock()
LOG_TO_FILE = [False]
LOG_TO_STDERR = [False]        # the daemon's own; the command line says what it does itself
LOG_SPARE = {}


def log(text, level='info'):
    if level == 'debug' and not CONFIG.get('debug'):
        return
    line = '%s %-5s %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), level, text)
    with LOG_LOCK:
        if LOG_TO_FILE[0]:
            try:
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            except OSError:
                pass
        if LOG_TO_STDERR[0] or level in ('error', 'crit'):
            try:
                sys.stderr.write(line + '\n')
                sys.stderr.flush()
            except (OSError, ValueError):
                pass


def log_sparing(key, text, level='warn', every=600):
    """The same complaint at most once in `every` seconds."""
    now = time.time()
    if now - LOG_SPARE.get(key, 0) >= every:
        LOG_SPARE[key] = now
        log(text, level)


# ---------------------------------------------------------------------------
# Small things, said once
# ---------------------------------------------------------------------------
def now_ts():
    return time.time()


def host_name():
    try:
        return socket.gethostname()
    except OSError:
        return 'localhost'


def run(cmd, timeout=60, input=None, env=None, check=False, **kw):
    """A command, its output as text: (returncode, stdout, stderr)."""
    try:
        got = subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout,
                             env=env, **kw)
    except FileNotFoundError:
        if check:
            raise ValueError('%s is not on this machine' % cmd[0])
        return 127, '', '%s: not found' % cmd[0]
    except subprocess.TimeoutExpired:
        if check:
            raise ValueError('%s did not finish in %d s' % (cmd[0], timeout))
        return 124, '', 'timed out after %d s' % timeout
    if check and got.returncode != 0:
        raise ValueError('%s: %s' % (os.path.basename(cmd[0]),
                                     (got.stderr or got.stdout or '').strip()[-400:] or
                                     'exit %d' % got.returncode))
    return got.returncode, got.stdout, got.stderr


def which(name):
    return shutil.which(name, path=os.environ.get('PATH', '') +
                        ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')


def write_atomic(path, data, mode=0o640, uid=None, gid=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb' if isinstance(data, bytes) else 'w') as f:
            f.write(data)
        os.chmod(tmp, mode)
        if uid is not None or gid is not None:
            try:
                os.chown(tmp, -1 if uid is None else uid, -1 if gid is None else gid)
            except OSError:
                pass
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_text(path, most=1 << 20, default=''):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read(most)
    except OSError:
        return default


def ver_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split('.')[:3])
    except ValueError:
        return (0, 0, 0)


def clean_line(text, most=200):
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(text or ''))[:most].strip()


def systemd_here():
    return os.path.isdir('/run/systemd/system') and bool(which('systemd-run')) and not NO_SYSTEM


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
PW_ROUNDS = 310000


def hash_password(password):
    salt = secrets.token_bytes(16)
    got = hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'), salt, PW_ROUNDS)
    return 'pbkdf2_sha256$%d$%s$%s' % (PW_ROUNDS, base64.b64encode(salt).decode('ascii'),
                                       base64.b64encode(got).decode('ascii'))


def check_password(password, stored):
    try:
        kind, rounds, salt, want = str(stored or '').split('$')
        if kind != 'pbkdf2_sha256':
            return False
        got = hashlib.pbkdf2_hmac('sha256', str(password).encode('utf-8'),
                                  base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(got, base64.b64decode(want))
    except (ValueError, TypeError):
        return False


def password_problem(password, name=''):
    p = str(password or '')
    if len(p) < int(CONFIG.get('password_min') or 10):
        return 'at least %d characters' % int(CONFIG.get('password_min') or 10)
    if name and p.lower() == str(name).lower():
        return 'not the name itself'
    if len(set(p)) < 4:
        return 'more than the same few characters again and again'
    return ''


def new_password():
    alphabet = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(16))


NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._@-]{0,63}\Z')
LINUX_NAME_RE = re.compile(r'^[a-z_][a-z0-9_-]{0,31}\Z')


# ---------------------------------------------------------------------------
# From otp: secrets sealed, one-time codes, QR codes, sending mail
# ---------------------------------------------------------------------------
# Taken over from otp as they are there (otp.py 1.0.161), so that the second
# step of signing in, the mails of these pages and the secrets kept in the
# database work the same way and are checked the same way.
def debugging(what):
    return bool(CONFIG.get('debug')) and bool(CONFIG.get('debug_' + what, 1))


# Secrets kept in the database (the mail server's password, the accounts'
# authenticator keys, the remote backups' passwords) are sealed with a key in
# a file of its own, /var/lib/ai/secrets.key - as otp seals them: a copy of
# the database alone opens none of them. Built from HMAC-SHA256 alone - a
# keystream and a tag - because the standard library has no cipher.
SEALED = 'sealed:1:'


def scrub_secret(text):
    """Words that may carry a database password (a conninfo in an error, say)
    with the password taken out, before they are logged or shown."""
    # A quoted value whole, up to the quote a space or the end follows (so
    # one with spaces, \' or SQL's '' inside goes too); otherwise up to the
    # next space - taking a quote with it rather than leaving a letter of
    # the password behind.
    return re.sub(r"(password\s*=\s*)('.*?'(?=\s|$)|\S+)", r'\1***', str(text or ''),
                  flags=re.I | re.S)


def sealing_key_path():
    return Path(STATE_DIR) / 'secrets.key'


_KEY_CACHE = {}
_KEY_LOCK = threading.Lock()


def sealing_key(make=False):
    """The key every secret in the database is sealed with. Read once and
    kept while the file is unchanged (1.0.33) - it was read from disk for
    every secret opened, every token in a list of thousands. Made only where
    there is none, and then with O_EXCL, so two processes starting at once
    cannot each make one of their own."""
    path = sealing_key_path()
    try:
        st = os.stat(str(path))
        stamp = (st.st_mtime_ns, st.st_size, st.st_ino)
    except FileNotFoundError:
        stamp = None
    except OSError:
        stamp = 'unreadable'
    if stamp is not None and stamp != 'unreadable':
        got = _KEY_CACHE.get(str(path))
        if got and got[0] == stamp:
            return got[1]
    try:
        key = bytes.fromhex(path.read_text(encoding='ascii').strip())
    except FileNotFoundError:
        key = None
    except (OSError, ValueError):
        key = b''
    if key and len(key) == 32:
        if stamp and stamp != 'unreadable':
            _KEY_CACHE[str(path)] = (stamp, key)
        return key
    if not make:
        return b''
    if key is not None:
        raise OSError('%s is there but cannot be read as a key - it is never replaced, '
                      'because every token sealed with it would be lost' % path)
    with _KEY_LOCK:
        key = secrets.token_bytes(32)
        # Written whole beside it, then linked into place (1.0.94): created
        # empty first, another process starting just then read an empty
        # key and stopped.
        tmp = '%s.new-%d-%s' % (path, os.getpid(), secrets.token_hex(4))
        # A name nobody made before, never through a link (1.0.101), and
        # given to the folder's owner while it is still open.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            if os.geteuid() == 0:
                st = os.stat(str(path.parent))
                os.fchown(fd, st.st_uid, st.st_gid)
        except OSError:
            pass
        with os.fdopen(fd, 'w', encoding='ascii') as f:
            f.write(key.hex() + '\n')
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tmp, str(path))
        except FileExistsError:
            # Made by somebody else a moment ago: theirs is the key.
            os.unlink(tmp)
            return sealing_key(make=False) or b''
        os.unlink(tmp)
        log('a new key to seal secrets with was made: %s - keep a copy of it beside every '
            'copy of the database' % path, 'warn')
    return key


def _seal_stream(key, nonce, size):
    out = bytearray()
    block = 0
    while len(out) < size:
        out += hmac.new(key, b'stream' + nonce + block.to_bytes(8, 'big'),
                        hashlib.sha256).digest()
        block += 1
    return bytes(out[:size])


SEALED2 = 'sealed:2:'
# Set once every token's secrets carry the name they belong to (1.0.33): from
# then on a secret of a token sealed the old way, without it, is not opened.
BIND_STRICT = {'tokens': False}


def token_bind(name):
    """What a token's sealed secrets are tied to: its name. Copied into
    another token's row, they no longer open (1.0.33)."""
    return 'token:' + str(name or '').strip().lower()


def seal_secret(text, bind=None):
    """Sealed with the key of this installation: a keystream from HMAC-SHA256,
    then a tag over it. With `bind`, the tag covers that too (sealed:2:), so
    the value opens only where it was sealed for."""
    key = sealing_key(make=True)
    if not key:
        raise OSError('no key to seal with')
    data = str(text).encode('utf-8')
    nonce = secrets.token_bytes(16)
    hide = hmac.new(key, b'hide', hashlib.sha256).digest()
    sign = hmac.new(key, b'sign', hashlib.sha256).digest()
    body = bytes(a ^ b for a, b in zip(data, _seal_stream(hide, nonce, len(data))))
    if bind is not None:
        tag = hmac.new(sign, b'2|' + str(bind).encode('utf-8') + b'|' + nonce + body,
                       hashlib.sha256).digest()[:16]
        return SEALED2 + base64.urlsafe_b64encode(nonce + body + tag).decode('ascii')
    tag = hmac.new(sign, nonce + body, hashlib.sha256).digest()[:16]
    return SEALED + base64.urlsafe_b64encode(nonce + body + tag).decode('ascii')


def unseal_secret(value, bind=None):
    """The secret back, or None where this machine's key is not the one it was
    sealed with - or, for one bound to a place, where it is not that place. A
    value never sealed is given back as it is."""
    if not isinstance(value, str):
        return value
    if value.startswith(SEALED2):
        v2, prefix = True, SEALED2
    elif value.startswith(SEALED):
        v2, prefix = False, SEALED
    else:
        if value and bind is not None and str(bind).startswith('token:') and \
                BIND_STRICT.get('tokens'):
            # A token's key that was never sealed (1.0.101): every one was
            # sealed at start, so this one was written by somebody without
            # the key - taken for nothing.
            return None
        return value
    if not v2 and bind is not None and str(bind).startswith('token:') and \
            BIND_STRICT.get('tokens'):
        return None
    if v2 and bind is None:
        return None
    key = sealing_key()
    try:
        raw = base64.urlsafe_b64decode(value[len(prefix):].encode('ascii'))
    except (ValueError, TypeError):
        return None
    if not key or len(raw) < 32:
        return None
    nonce, body, tag = raw[:16], raw[16:-16], raw[-16:]
    sign = hmac.new(key, b'sign', hashlib.sha256).digest()
    signed = (b'2|' + str(bind).encode('utf-8') + b'|' if v2 else b'') + nonce + body
    if not hmac.compare_digest(tag, hmac.new(sign, signed, hashlib.sha256).digest()[:16]):
        return None
    hide = hmac.new(key, b'hide', hashlib.sha256).digest()
    try:
        return bytes(a ^ b for a, b in zip(body, _seal_stream(hide, nonce, len(body)))
                     ).decode('utf-8')
    except UnicodeDecodeError:
        return None

# ---------------------------------------------------------------------------
# One-time passwords: RFC 4226 (HOTP) and RFC 6238 (TOTP)
# ---------------------------------------------------------------------------
# What the phone does, done again here: the key and the number of thirty-
# second periods since 1970 go through HMAC, and six digits are cut out of the
# answer. Nothing in this needs anything but hashlib and hmac.
HASHES = {'SHA1': hashlib.sha1, 'SHA256': hashlib.sha256, 'SHA512': hashlib.sha512}


def b32_clean(text):
    """A base32 key as somebody may have written it - small letters, spaces,
    dashes, no padding - as the bytes it stands for. ValueError if it is not
    base32 at all."""
    said = re.sub(r'[\s\-]', '', str(text or '')).upper().rstrip('=')
    if not said or not re.match(r'^[A-Z2-7]+\Z', said):
        raise ValueError('that is not a base32 key (A-Z and 2-7)')
    pad = '=' * ((8 - len(said) % 8) % 8)
    return base64.b32decode(said + pad)


def b32_new(size=20):
    """A fresh key: 160 bits, the size RFC 4226 recommends, as base32."""
    return base64.b32encode(secrets.token_bytes(size)).decode('ascii').rstrip('=')


def hotp(key, counter, digits=6, algorithm='SHA1'):
    """The code for one counter value, as a string of `digits` digits."""
    if isinstance(key, str):
        key = b32_clean(key)
    mac = hmac.new(key, struct.pack('>Q', int(counter)),
                   HASHES.get(str(algorithm).upper(), hashlib.sha1)).digest()
    at = mac[-1] & 0x0F
    code = struct.unpack('>I', mac[at:at + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** int(digits))).zfill(int(digits))


def totp_step(when=None, period=30):
    return int((time.time() if when is None else float(when)) // int(period))


def totp(key, when=None, digits=6, period=30, algorithm='SHA1'):
    return hotp(key, totp_step(when, period), digits, algorithm)


def totp_match(key, code, when=None, digits=6, period=30, algorithm='SHA1', window=1):
    """Which period the code belongs to - its step number - or None.

    Looked for in this period first and then outwards, one step either side
    at a time, so that when two would do the nearest one is the answer.
    Compared in constant time, every one of them.
    """
    code = re.sub(r'\s', '', str(code or ''))
    if not re.fullmatch(r'[0-9]+', code, re.ASCII) or len(code) != int(digits):
        return None
    if isinstance(key, str):
        key = b32_clean(key)
    here = totp_step(when, period)
    found = None
    for off in [0] + [d for i in range(1, int(window) + 1) for d in (-i, i)]:
        if hmac.compare_digest(hotp(key, here + off, digits, algorithm), code) and found is None:
            found = here + off
    return found


def otpauth_uri(secret, label, issuer, digits=6, period=30, algorithm='SHA1'):
    """What the QR code holds: the Key URI Format every phone application
    reads (otpauth://totp/Issuer:label?secret=...&issuer=...)."""
    from urllib.parse import quote
    issuer = str(issuer or '').strip()
    who = (quote(issuer, safe='') + ':' if issuer else '') + quote(str(label), safe='@.')
    args = ['secret=' + str(secret).upper().replace('=', '')]
    if issuer:
        args.append('issuer=' + quote(issuer, safe=''))
    if str(algorithm).upper() != 'SHA1':
        args.append('algorithm=' + str(algorithm).upper())
    if int(digits) != 6:
        args.append('digits=%d' % int(digits))
    if int(period) != 30:
        args.append('period=%d' % int(period))
    return 'otpauth://totp/%s?%s' % (who, '&'.join(args))


def scratch_new(count, digits=8):
    """Recovery codes: `count` of them, `digits` long, none twice."""
# ---------------------------------------------------------------------------
# QR codes
# ---------------------------------------------------------------------------
# The picture the phone scans, made here rather than by a package: the
# standard (ISO/IEC 18004) in byte mode, every version, every level of error
# correction, the mask chosen the way the standard says. It comes out as SVG
# for the pages and as half-block characters for a terminal.
_QR_ECC_PER_BLOCK = {
    'L': (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
          28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    'M': (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
          26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    'Q': (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
          28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    'H': (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
          30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
}
_QR_BLOCKS = {
    'L': (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12,
          12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    'M': (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20,
          21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    'Q': (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25,
          27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    'H': (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30,
          32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
}
_QR_FORMAT = {'L': 1, 'M': 0, 'Q': 3, 'H': 2}


def _gf_mul(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z & 0xFF


def _rs_divisor(degree):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(len(result)):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < len(result):
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return result


def _rs_remainder(data, divisor):
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= _gf_mul(coef, factor)
    return result


def _qr_raw_modules(ver):
    result = (16 * ver + 128) * ver + 64
    if ver >= 2:
        align = ver // 7 + 2
        result -= (25 * align - 10) * align - 55
        if ver >= 7:
            result -= 36
    return result


def _qr_data_codewords(ver, ecl):
    return (_qr_raw_modules(ver) // 8
            - _QR_ECC_PER_BLOCK[ecl][ver] * _QR_BLOCKS[ecl][ver])


class QrCode(object):
    """One QR code: `modules[y][x]` is True where the square is dark."""

    def __init__(self, text, ecl='M'):
        data = text.encode('utf-8') if isinstance(text, str) else bytes(text)
        self.ecl = ecl
        for ver in range(1, 41):
            count_bits = 8 if ver <= 9 else 16
            need = 4 + count_bits + 8 * len(data)
            if need <= _qr_data_codewords(ver, ecl) * 8:
                break
        else:
            raise ValueError('that is too long for a QR code')
        self.version = ver
        self.size = ver * 4 + 17
        bits = []

        def put(value, n):
            for i in reversed(range(n)):
                bits.append((value >> i) & 1)
        put(0x4, 4)
        put(len(data), count_bits)
        for b in data:
            put(b, 8)
        capacity = _qr_data_codewords(ver, ecl) * 8
        put(0, min(4, capacity - len(bits)))
        put(0, (8 - len(bits) % 8) % 8)
        pad = 0xEC
        while len(bits) < capacity:
            put(pad, 8)
            pad ^= 0xEC ^ 0x11
        words = [int(''.join(str(b) for b in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
        all_words = self._with_ecc(words)
        size = self.size
        self.modules = [[False] * size for _ in range(size)]
        self.function = [[False] * size for _ in range(size)]
        self._function_patterns()
        self._codewords(all_words)
        best, best_penalty = 0, None
        for mask in range(8):
            self._mask(mask)
            self._format(mask)
            penalty = self._penalty()
            if best_penalty is None or penalty < best_penalty:
                best, best_penalty = mask, penalty
            self._mask(mask)
        self._mask(best)
        self._format(best)
        self.mask = best

    # ---- the pieces ------------------------------------------------------
    def _set(self, x, y, dark):
        self.modules[y][x] = bool(dark)
        self.function[y][x] = True

    def _function_patterns(self):
        size = self.size
        for i in range(size):
            self._set(6, i, i % 2 == 0)
            self._set(i, 6, i % 2 == 0)
        for x, y in ((3, 3), (size - 4, 3), (3, size - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < size and 0 <= yy < size:
                        self._set(xx, yy, max(abs(dx), abs(dy)) not in (2, 4))
        places = self._alignment_places()
        last = len(places) - 1
        for i, a in enumerate(places):
            for j, b in enumerate(places):
                if (i == 0 and j == 0) or (i == 0 and j == last) or (i == last and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._set(a + dx, b + dy, max(abs(dx), abs(dy)) != 1)
        self._format(0)
        if self.version >= 7:
            rem = self.version
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            value = self.version << 12 | rem
            for i in range(18):
                bit = (value >> i) & 1
                a, b = size - 11 + i % 3, i // 3
                self._set(a, b, bit)
                self._set(b, a, bit)

    def _alignment_places(self):
        ver = self.version
        if ver == 1:
            return []
        count = ver // 7 + 2
        step = (ver * 8 + count * 3 + 5) // (count * 4 - 4) * 2
        result = [self.size - 7 - i * step for i in range(count - 1)] + [6]
        return list(reversed(result))

    def _format(self, mask):
        data = _QR_FORMAT[self.ecl] << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        bit = lambda i: (bits >> i) & 1
        size = self.size
        for i in range(0, 6):
            self._set(8, i, bit(i))
        self._set(8, 7, bit(6))
        self._set(8, 8, bit(7))
        self._set(7, 8, bit(8))
        for i in range(9, 15):
            self._set(14 - i, 8, bit(i))
        for i in range(0, 8):
            self._set(size - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self._set(8, size - 15 + i, bit(i))
        self._set(8, size - 8, True)

    def _with_ecc(self, data):
        ver, ecl = self.version, self.ecl
        blocks_n = _QR_BLOCKS[ecl][ver]
        ecc_len = _QR_ECC_PER_BLOCK[ecl][ver]
        raw = _qr_raw_modules(ver) // 8
        short_n = blocks_n - raw % blocks_n
        short_len = raw // blocks_n
        divisor = _rs_divisor(ecc_len)
        blocks = []
        k = 0
        for i in range(blocks_n):
            take = short_len - ecc_len + (0 if i < short_n else 1)
            dat = data[k:k + take]
            k += take
            ecc = _rs_remainder(dat, divisor)
            if i < short_n:
                dat = dat + [0]
            blocks.append(dat + ecc)
        out = []
        for i in range(len(blocks[0])):
            for j, blk in enumerate(blocks):
                if i != short_len - ecc_len or j >= short_n:
                    out.append(blk[i])
        return out

    def _codewords(self, data):
        size = self.size
        i = 0
        right = size - 1
        total = len(data) * 8
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(size):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = size - 1 - vert if upward else vert
                    if not self.function[y][x] and i < total:
                        self.modules[y][x] = bool((data[i >> 3] >> (7 - (i & 7))) & 1)
                        i += 1
            right -= 2

    def _mask(self, mask):
        test = (lambda x, y: (x + y) % 2 == 0,
                lambda x, y: y % 2 == 0,
                lambda x, y: x % 3 == 0,
                lambda x, y: (x + y) % 3 == 0,
                lambda x, y: (x // 3 + y // 2) % 2 == 0,
                lambda x, y: x * y % 2 + x * y % 3 == 0,
                lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
                lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0)[mask]
        for y in range(self.size):
            row, fn = self.modules[y], self.function[y]
            for x in range(self.size):
                if not fn[x] and test(x, y):
                    row[x] = not row[x]

    def _penalty(self):
        size, m = self.size, self.modules
        score = 0
        lines = [m[y] for y in range(size)] + [[m[y][x] for y in range(size)]
                                                for x in range(size)]
        finder = ([True, False, True, True, True, False, True, False, False, False, False],
                  [False, False, False, False, True, False, True, True, True, False, True])
        for line in lines:
            run, last = 0, None
            for v in line:
                if v == last:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + run - 5
                    run, last = 1, v
            if run >= 5:
                score += 3 + run - 5
            for i in range(len(line) - 10):
                seg = line[i:i + 11]
                if seg == finder[0] or seg == finder[1]:
                    score += 40
        for y in range(size - 1):
            for x in range(size - 1):
                v = m[y][x]
                if v == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        dark = sum(sum(1 for v in row if v) for row in m)
        total = size * size
        k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
        score += k * 10
        return score

    # ---- drawn -------------------------------------------------------------
    def svg(self, scale=6, border=4, dark='#000', light='#fff'):
        """The code as an SVG picture, light squares and all - a phone needs
        the quiet zone round it, so it is part of the picture."""
        size = self.size + border * 2
        path = []
        for y in range(self.size):
            x = 0
            while x < self.size:
                if self.modules[y][x]:
                    start = x
                    while x < self.size and self.modules[y][x]:
                        x += 1
                    path.append('M%d %dh%dv1h-%dz' % (start + border, y + border,
                                                      x - start, x - start))
                else:
                    x += 1
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
                'height="%d" shape-rendering="crispEdges"><rect width="100%%" height="100%%" '
                'fill="%s"/><path d="%s" fill="%s"/></svg>'
                % (size, size, size * scale, size * scale, light, ''.join(path), dark))

    def terminal(self, border=2, invert=False):
        """The code as half-block characters, two rows of squares a line.
        Drawn for a dark terminal: a dark square is the terminal's own dark
        and a light one is a full block. `invert` for a light terminal."""
        size = self.size
        out = []
        def light(x, y):
            if x < 0 or y < 0 or x >= size or y >= size:
                return not invert
            return (not self.modules[y][x]) != invert
        for y in range(-border, size + border, 2):
            row = []
            for x in range(-border, size + border):
                top, bottom = light(x, y), light(x, y + 1)
                row.append('█' if top and bottom else
                           '▀' if top else '▄' if bottom else ' ')
            out.append(''.join(row))
        return '\n'.join(out)


def qr_svg(text, scale=6):
    return QrCode(text, 'M').svg(scale=scale)


def qr_data_uri(text, scale=6):
    return 'data:image/svg+xml;base64,' + base64.b64encode(
        qr_svg(text, scale).encode('ascii')).decode('ascii')

def describe_certificate(pem):
    """What a pasted certificate is, in words, or None if it is not one.

    Somebody importing a certificate authority wants to see that the right
    one landed - the name on it and when it runs out - and not a green tick
    that means "the text was saved". Python can read a certificate without
    any package being installed; what it cannot do without one is read it
    from a string, so it goes through a file that exists for a moment.
    """
    text = str(pem or '').strip()
    if '-----BEGIN CERTIFICATE-----' not in text:
        return None
    folder = None
    try:
        folder = tempfile.mkdtemp(prefix='ai-ca-')
        where = os.path.join(folder, 'ca.pem')
        with open(where, 'w', encoding='utf-8') as f:
            f.write(text if text.endswith('\n') else text + '\n')
        said = ssl._ssl._test_decode_cert(where)     # noqa: SLF001 - the only way in
        def one(pairs):
            out = {}
            for row in pairs or ():
                for key, value in row:
                    out[key] = value
            return out
        subject, issuer = one(said.get('subject')), one(said.get('issuer'))
        return {
            'subject': subject.get('commonName') or subject.get('organizationName') or '',
            'issuer': issuer.get('commonName') or issuer.get('organizationName') or '',
            'from': said.get('notBefore') or '',
            'until': said.get('notAfter') or '',
            'self_signed': subject == issuer,
            'count': text.count('-----BEGIN CERTIFICATE-----'),
        }
    except Exception:
        return None
    finally:
        if folder:
            shutil.rmtree(folder, ignore_errors=True)


PEM_BLOCK = re.compile(r'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+?-----END CERTIFICATE-----')


def split_certificates(pem):
    """Each certificate of a bundle, as its own PEM block, in order."""
    return [m.group(0).strip() for m in PEM_BLOCK.finditer(str(pem or ''))]


def describe_certificates(pem):
    """Every certificate of a bundle, one by one: who it is, who signed it,
    when it runs out and its fingerprint - so that one of several chains can
    be told apart from another and taken out by itself. (1.0.11)"""
    out = []
    for block in split_certificates(pem):
        said = describe_certificate(block) or {}
        try:
            fp = hashlib.sha256(ssl.PEM_cert_to_DER_cert(block)).hexdigest()
        except Exception:                               # noqa: BLE001
            fp = hashlib.sha256(block.encode()).hexdigest()
        said = dict(said, fingerprint=fp, readable=bool(said))
        said.pop('count', None)
        out.append(said)
    return out
def mail_checked(dest):
    dest = str(dest or '').strip()
    if not re.match(r'^[^@\s<>,;"]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,}\Z', dest):
        raise ValueError('that is not a mail address')
    return dest


def phone_checked(dest):
    """A number as +CCCNNN…: spaces, dashes and brackets taken out, the
    country code of the settings put before a number written without one."""
    raw = re.sub(r'[\s().\-/]', '', str(dest or ''))
    if raw.startswith('00'):
        raw = '+' + raw[2:]
    if not raw.startswith('+'):
        pre = str(CONFIG.get('sms_prefix') or '').strip()
        if not pre:
            raise ValueError('write the number with its country code: +420 603 123 456')
        digits = raw.lstrip('0')
        # 420603123456 written without its + (1.0.146): not +420420603123456.
        # Not a number dialled at home with its 0 (1.0.147): 0491 12345678
        # in Germany is 491..., and is not +49 1 12345678.
        if not raw.startswith('0') and pre.lstrip('+') and digits.startswith(pre.lstrip('+')) and \
                len(digits) - len(pre.lstrip('+')) >= 8:
            raw = '+' + digits
        else:
            raw = pre + digits
    if not re.match(r'^\+[1-9][0-9]{7,14}\Z', raw):
        raise ValueError('that is not a phone number - write it as +420 603 123 456')
    return raw


def dest_checked(kind, dest):
    if kind == 'mail':
        return mail_checked(dest)
    if kind == 'sms':
        return phone_checked(dest)
    return ''


def dest_masked(kind, dest):
    """What the VPN and the pages may say of where a code went."""
    dest = str(dest or '')
    if kind == 'mail' and '@' in dest:
        who, _, where = dest.partition('@')
        return '%s%s@%s' % (who[:1], '*' * max(2, min(len(who) - 1, 6)), where)
    if kind == 'sms' and len(dest) > 4:
        return '%s%s%s' % (dest[:4], '*' * (len(dest) - 7), dest[-3:])
    return dest


# ---------------------------------------------------------------------------
# Sending mail (1.0.20)
# ---------------------------------------------------------------------------
# A token's QR code, and if wanted its recovery codes, sent to the person it
# is for. Two ways out: through a mail server (SMTP relay, with STARTTLS,
# SMTPS or nothing, signing in with PLAIN, LOGIN, CRAM-MD5, XOAUTH2 or not at
# all), or straight to the server of the recipient's domain - its MX record,
# looked up here - with no relay at all. A certificate signed by an authority
# of your own is trusted once that authority is added, as for a directory.

MAIL_CA_META = 'mail_ca'
MAIL_DIRECT_DEADLINE_S = 60     # every MX of one domain together (1.0.59)


def mail_ca_pem(store):
    try:
        return str(store.get_meta(MAIL_CA_META) or '')
    except Exception:
        return ''


def mail_ca_set(store, pem, mode='add', fingerprint=''):
    """The authorities trusted for the mail server, each added and taken out
    by itself - the same as a directory's."""
    pem = str(pem or '').strip()
    have = split_certificates(mail_ca_pem(store))
    if mode == 'add':
        # Nothing sent is not "empty the list" (1.0.146): only 'clear' empties it.
        new = split_certificates(pem)
        if not new or not all(describe_certificate(b) for b in new):
            raise ValueError('that is not a certificate this can read: a PEM certificate '
                             'starts -----BEGIN CERTIFICATE-----')
        seen = {c['fingerprint'] for c in describe_certificates('\n'.join(have))}
        have += [b for b, c in zip(new, describe_certificates('\n'.join(new)))
                 if c['fingerprint'] not in seen]
    elif mode == 'drop':
        keep = [b for b, c in zip(have, describe_certificates('\n'.join(have)))
                if c['fingerprint'] != fingerprint]
        if len(keep) == len(have):
            raise ValueError('that certificate is not among the ones kept')
        have = keep
    elif mode == 'clear':
        have = []
    else:
        raise ValueError('add, drop or clear?')
    store.set_meta(MAIL_CA_META, '\n'.join(have))
    return describe_certificates('\n'.join(have))


def mail_tls(store, verify=None):
    verify = bool(CONFIG.get('smtp_verify', 1)) if verify is None else verify
    ctx = ssl.create_default_context()
    pem = mail_ca_pem(store)
    if pem.strip():
        try:
            ctx.load_verify_locations(cadata=pem)
        except (ssl.SSLError, ValueError) as e:
            raise MailError('the certificate authorities kept for mail cannot be read: %s' % e)
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class MailError(RuntimeError):
    """`permanent` (1.0.95): the receiving side said no for good (a 5xx) -
    not tried again. Anything else - a 4xx (greylisting), a server away -
    is, from the outgoing mail."""
    def __init__(self, said, steps=None, permanent=False):
        super(MailError, self).__init__(said)
        self.steps = steps or []
        self.permanent = bool(permanent)
        self.queued = None


# ---- the recipients' servers, without a library to ask DNS with -----------------
def own_dns():
    """The DNS servers set for mail going direct (`mail_dns`), if any."""
    good = []
    for w in re.split(r'[\s,;]+', str(CONFIG.get('mail_dns') or '')):
        try:
            good.append(str(ipaddress.ip_address(w)))
        except ValueError:
            pass
    return good


def dns_servers():
    if own_dns():
        return own_dns()
    out = []
    try:
        with open('/etc/resolv.conf') as f:
            for line in f:
                bits = line.split()
                if len(bits) >= 2 and bits[0] == 'nameserver':
                    out.append(bits[1])
    except OSError:
        pass
    return out or ['127.0.0.1']


def _dns_name(data, at):
    labels, jumped, end = [], False, at
    for _ in range(64):
        n = data[at]
        if n == 0:
            at += 1
            break
        if n & 0xC0 == 0xC0:
            if not jumped:
                end = at + 2
            at = ((n & 0x3F) << 8) | data[at + 1]
            jumped = True
            continue
        labels.append(data[at + 1:at + 1 + n].decode('ascii', 'replace'))
        at += 1 + n
    return '.'.join(labels), (end if jumped else at)


def _dns_ask(server, name, qtype, timeout):
    """One question to one DNS server: the raw answer. EDNS0 asks for room
    for a long answer; one that is cut short anyway is asked again over TCP
    (1.0.22)."""
    ident = secrets.randbits(16)
    q = struct.pack('>HHHHHH', ident, 0x0100, 1, 0, 0, 1)
    for label in name.split('.'):
        if not label:
            continue
        raw = label.encode('idna') if any(ord(c) > 127 for c in label) else label.encode()
        q += bytes([len(raw)]) + raw
    q += b'\x00' + struct.pack('>HH', qtype, 1)
    q += b'\x00' + struct.pack('>HHIH', 41, 4096, 0, 0)          # OPT: 4096 bytes
    fam = socket.AF_INET6 if ':' in server else socket.AF_INET
    s = socket.socket(fam, socket.SOCK_DGRAM)
    deadline = time.time() + timeout
    question = q[12:-11]                    # the name, the type and the class asked
    try:
        # connect(): only answers from the server asked are read at all.
        s.connect((server, 53))
        s.send(q)
        while True:
            left = deadline - time.time()
            if left <= 0:
                raise socket.timeout('no answer from %s' % server)
            s.settimeout(left)
            data = s.recv(65535)
            # Its own answer: the same ID, and the same question (1.0.33) -
            # and no waiting past the deadline however many others come.
            if len(data) >= 12 + len(question) and struct.unpack('>H', data[:2])[0] == ident \
                    and data[12:12 + len(question)].lower() == question.lower():
                break
    finally:
        s.close()
    if struct.unpack('>H', data[2:4])[0] & 0x0200:                # TC: cut short
        t = socket.create_connection((server, 53), timeout=timeout)
        try:
            t.sendall(struct.pack('>H', len(q)) + q)
            want, got = None, b''
            while want is None or len(got) < want + 2:
                chunk = t.recv(65535)
                if not chunk:
                    break
                got += chunk
                if want is None and len(got) >= 2:
                    want = struct.unpack('>H', got[:2])[0]
            data = got[2:]
        finally:
            t.close()
    return data


def _dns_records(data):
    """(rcode, [(type, name, rdata-offset, size)]) of an answer."""
    flags, qd, an = struct.unpack('>HHH', data[2:8])
    at = 12
    for _ in range(qd):
        _, at = _dns_name(data, at)
        at += 4
    out = []
    for _ in range(an):
        rname, at = _dns_name(data, at)
        rtype, _cls, _ttl, size = struct.unpack('>HHIH', data[at:at + 10])
        at += 10
        out.append((rtype, rname, at, size))
        at += size
    return flags & 0x0F, out


DNS_RCODES = {1: 'could not read the question', 2: 'failed (SERVFAIL)', 4: 'does not do that',
              5: 'refused to answer'}


def dns_mx_full(domain, timeout=5.0):
    """The mail servers of a domain, best first, and how they were found:
    ([(preference, host)], words). A domain with no MX record is its own
    mail server (RFC 5321) - but only when a DNS server said so, never
    because one failed to answer (1.0.22: a failed answer was taken for
    "no MX" and the mail went to the domain's own address)."""
    domain = str(domain).strip().strip('.').lower()
    try:                                       # dnspython, where it is installed
        if own_dns():
            # The DNS servers set for mail are the ones asked (1.0.59):
            # dnspython reads the system's, and with a split horizon its
            # NXDOMAIN was taken for the last word.
            raise ImportError('mail_dns is set')
        import dns.resolver                     # type: ignore
        try:
            ans = dns.resolver.resolve(domain, 'MX', lifetime=timeout * 2)
            got = sorted((int(r.preference), str(r.exchange).rstrip('.')) for r in ans)
            got = [g for g in got if g[1]]
            if got:
                return got, 'MX records (dnspython)'
        except dns.resolver.NXDOMAIN:
            raise MailError('the domain %s does not exist' % domain)
        except dns.resolver.NoAnswer:
            return [(0, domain)], 'no MX record: the domain itself (dnspython)'
        except Exception:                       # noqa: BLE001 - our own below
            pass
    except ImportError:
        pass
    trouble = []
    name = domain
    for server in dns_servers():
        name = domain
        for _hop in range(6):                   # a CNAME, followed
            try:
                data = _dns_ask(server, name, 15, timeout)
                rcode, recs = _dns_records(data)
            except (OSError, struct.error, IndexError, ValueError) as e:
                trouble.append('%s: %s' % (server, e))
                break
            if rcode == 3:
                raise MailError('the domain %s does not exist (DNS %s)' % (name, server))
            if rcode:
                trouble.append('%s %s' % (server, DNS_RCODES.get(rcode, 'answered %d' % rcode)))
                break
            mx, cname, nullmx = [], None, False
            try:
                for rtype, _rname, at, _size in recs:
                    if rtype == 15:
                        pref = struct.unpack('>H', data[at:at + 2])[0]
                        host, _ = _dns_name(data, at + 2)
                        if host and host != '.':
                            mx.append((pref, host.rstrip('.').lower()))
                        else:
                            nullmx = True
                    elif rtype == 5:
                        cname, _ = _dns_name(data, at)
            except (struct.error, IndexError, ValueError) as e:
                trouble.append('%s: an answer that does not read: %s' % (server, e))
                break
            if mx:
                return sorted(mx), 'MX records from DNS %s' % server
            if nullmx:
                return [], 'a null MX (DNS %s): the domain takes no mail' % server
            if cname and cname.lower() != name:
                name = cname.rstrip('.').lower()
                continue
            # A null MX (RFC 7505) is "0 ." - the domain takes no mail.
            return [(0, name)], 'no MX record (DNS %s): the domain itself' % server
    raise MailError('no DNS server could say where mail for %s goes%s' % (
        domain, (': ' + '; '.join(trouble)) if trouble else ''))


def dns_mx(domain, timeout=5.0):
    return dns_mx_full(domain, timeout)[0]


def dns_addrs(host, timeout=5.0):
    """The IPv4 and IPv6 addresses of a host (A and AAAA, a CNAME followed),
    asked of the same DNS servers as the MX records (1.0.23) - not of the
    system's resolver, which may be the very one that will not answer."""
    host = str(host).strip().strip('.').lower()
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        pass
    out, trouble = [], []
    for qtype in (1, 28):
        for server in dns_servers():
            name, done = host, False
            for _hop in range(6):
                try:
                    data = _dns_ask(server, name, qtype, timeout)
                    rcode, recs = _dns_records(data)
                except (OSError, struct.error, IndexError, ValueError) as e:
                    trouble.append('%s: %s' % (server, e))
                    break
                if rcode == 3:
                    done = True
                    break
                if rcode:
                    trouble.append('%s %s' % (server, DNS_RCODES.get(rcode, 'answered %d' % rcode)))
                    break
                cname, got = None, []
                try:
                    for rtype, _rname, at, size in recs:
                        if rtype == 1 and size == 4:
                            got.append(socket.inet_ntop(socket.AF_INET, data[at:at + 4]))
                        elif rtype == 28 and size == 16:
                            got.append(socket.inet_ntop(socket.AF_INET6, data[at:at + 16]))
                        elif rtype == 5:
                            cname, _ = _dns_name(data, at)
                except (struct.error, IndexError, ValueError, OSError) as e:
                    trouble.append('%s: an answer that does not read: %s' % (server, e))
                    break
                if got:
                    out += [g for g in got if g not in out]
                    done = True
                    break
                if cname and cname.rstrip('.').lower() != name:
                    name = cname.rstrip('.').lower()
                    continue
                done = True                     # no record of this type
                break
            if done:
                break
    if not out:
        raise MailError('no address found for %s%s' % (host, (': ' + '; '.join(trouble))
                                                       if trouble else ''))
    # IPv4 first: a machine with an IPv6 address and no IPv6 route waits out
    # the whole timeout on every server otherwise.
    return sorted(out, key=lambda a: ':' in a)


class _Deadline(object):
    """One conversation's whole time, not each read's (1.0.101): a server
    sending a byte every 19 s of a 20 s timeout held the thread - and a page
    waiting on it - for as long as it liked."""
    deadline = 0.0

    def _left(self):
        if not self.deadline:
            return None
        left = self.deadline - time.time()
        if left <= 0:
            raise smtplib.SMTPServerDisconnected('the mail server took longer than allowed')
        return left

    def _watch(self):
        """A watchman that ends the conversation at its deadline (1.0.103):
        the time of each read alone was set again line by line, so a server
        dripping its reply byte by byte held the thread past any deadline.
        Shut down, the socket ends whatever read waits on it."""
        if not self.deadline or getattr(self, '_watchman', None):
            return
        def expire():
            sock = getattr(self, 'sock', None)
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        t = threading.Timer(max(0.5, self.deadline - time.time()), expire)
        t.daemon = True
        t.start()
        self._watchman = t

    # The conversation into the log, with "Debug log" and "...every code sent"
    # on (1.0.113): what was said each way, never a password or the message.
    _SAFE = ('EHLO', 'HELO', 'MAIL', 'RCPT', 'DATA', 'QUIT', 'STARTTLS', 'RSET', 'NOOP')

    def _print_debug(self, *args):
        words = ' '.join(str(a) for a in args)
        m = re.match(r"^(send|reply):\s*(b?['\"])(.*)", words, re.S)
        if m and m.group(1) == 'send':
            body = m.group(3)
            head = body.split(' ', 1)[0].split('\\r')[0].upper()
            if head.startswith('AUTH'):
                words = 'send: AUTH %s <the credentials, not written>' % (
                    body.split(' ')[1] if ' ' in body else '')
            elif head not in self._SAFE:
                words = 'send: <%d characters - the message or the credentials, not written>' \
                    % len(body)
        log('mail %s: %s' % (getattr(self, '_host', '') or '?', words[:300]), 'debug')

    def close(self):
        t = getattr(self, '_watchman', None)
        if t is not None:
            t.cancel()
        return smtplib.SMTP.close(self)

    def getreply(self):
        self._watch()
        left = self._left()
        if left is not None and self.sock is not None:
            try:
                self.sock.settimeout(min(left, self.timeout or left))
            except OSError:
                pass
        return smtplib.SMTP.getreply(self)

    def send(self, s):
        left = self._left()
        if left is not None and self.sock is not None:
            try:
                self.sock.settimeout(min(left, self.timeout or left))
            except OSError:
                pass
        return smtplib.SMTP.send(self, s)


class _AddrSMTP(_Deadline, smtplib.SMTP):
    """smtplib, connecting to addresses already looked up; the host's name
    is still what the certificate is checked against. It keeps what the
    server answered to the message itself - "250 Ok: queued as 4Xy..." -
    which is what its own log is searched by (1.0.27)."""
    addrs = ()
    last_reply = None

    def data(self, msg):
        got = smtplib.SMTP.data(self, msg)
        self.last_reply = got
        return got

    def _get_socket(self, host, port, timeout):
        last = None
        for a in self.addrs or [host]:
            try:
                return socket.create_connection((a, port), timeout, self.source_address)
            except OSError as e:
                last = e
        raise last or OSError('no address to reach')


class _AddrSMTPS(_Deadline, smtplib.SMTP_SSL):
    addrs = ()
    last_reply = None

    def data(self, msg):
        got = smtplib.SMTP.data(self, msg)
        self.last_reply = got
        return got

    def _get_socket(self, host, port, timeout):
        sock = _AddrSMTP._get_socket(self, host, port, timeout)
        try:
            return self.context.wrap_socket(sock, server_hostname=self._host)
        except BaseException:
            sock.close()                # not left to the collector (1.0.59)
            raise


# ---- one conversation with one server ---------------------------------------------
def _xoauth2(user, token):
    return lambda challenge=None: 'user=%s\x01auth=Bearer %s\x01\x01' % (user, token)


def smtp_talk(store, host, port, security, auth, msg, to, steps, helo='', verify=None,
              timeout=None, direct=False):
    """Send one message through one server, writing down every step."""
    timeout = float(timeout or CONFIG.get('smtp_timeout_s') or 20)
    helo = str(helo or CONFIG.get('mail_helo') or socket.getfqdn() or 'localhost')
    ctx = mail_tls(store, verify)
    if direct and security == 'starttls-if':
        # TLS where offered, going straight to somebody's MX (1.0.59): their
        # certificate is not checked, as no mail server checks another's -
        # a self-signed one there failed every message to the domain, where
        # plain text would have gone. "required" still checks it.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    began = time.time()

    def step(what, ok=True, said=''):
        steps.append({'what': what, 'ok': ok, 'said': str(said or '')[:500]})
        if debugging('codes'):
            log('mail %s:%d: %s %s%s' % (host, port, 'ok' if ok else 'FAILED', what,
                                         (' - %s' % str(said)[:200]) if said else ''), 'debug')

    # Going direct, the recipients' servers are looked up by the same DNS
    # servers that gave their MX records - A, AAAA and CNAME (1.0.23).
    # Only here, and only for mail going straight to the recipients, are
    # the DNS servers of `mail_dns` asked; with none set it is the system's
    # own resolver (/etc/hosts, nsswitch), as for everything else. (1.0.23)
    addrs = ()
    if direct:
        try:
            if own_dns():
                addrs = tuple(dns_addrs(host))
                how = 'DNS ' + ', '.join(own_dns())
            else:
                addrs = tuple(sorted({a[4][0] for a in socket.getaddrinfo(
                    host, port, 0, socket.SOCK_STREAM)}, key=lambda a: ':' in a))
                how = 'the system resolver'
            step('looked up %s' % host, True, ', '.join(addrs) + ' · ' + how)
        except (MailError, OSError) as e:
            step('look up %s' % host, False, e)
            raise MailError('no address found for %s: %s' % (host, e), steps)
    try:
        if security == 'tls':
            conn = _AddrSMTPS(local_hostname=helo, timeout=timeout, context=ctx)
            if debugging('codes'):
                conn.set_debuglevel(1)
            conn.deadline = began + 4 * timeout
            conn.addrs = addrs
            conn._host = host           # the name its certificate is checked against
            code, said = conn.connect(host, port)
            if code != 220:
                conn.close()
                raise smtplib.SMTPConnectError(code, said)
            step('reached %s:%d over TLS' % (host, port), True,
                 '%d ms' % int((time.time() - began) * 1000))
        else:
            conn = _AddrSMTP(local_hostname=helo, timeout=timeout)
            if debugging('codes'):
                conn.set_debuglevel(1)
            conn.deadline = began + 4 * timeout
            conn.addrs = addrs
            # The name STARTTLS checks the certificate against (1.0.96):
            # smtplib keeps the one given when it is made - none here, the
            # address is connected to - and every server that offered
            # STARTTLS failed: "server_hostname cannot be an empty string".
            conn._host = host
            code, said = conn.connect(host, port)
            if code != 220:
                conn.close()
                raise smtplib.SMTPConnectError(code, said)
            step('reached %s:%d' % (host, port), True,
                 '%d ms' % int((time.time() - began) * 1000))
    except ssl.SSLCertVerificationError as e:
        step('reach the server %s:%d over TLS' % (host, port), False,
             'its certificate is not trusted: %s' % e.verify_message)
        raise MailError('the certificate of %s is not trusted - add the authority that '
                        'signed it, or switch the check off' % host, steps)
    except (OSError, smtplib.SMTPException) as e:
        step('reach the server %s:%d' % (host, port), False, e)
        raise MailError('%s:%d could not be reached: %s' % (host, port, e), steps)
    try:
        code, said = conn.ehlo()
        step('greeted it as %s' % helo, 200 <= code < 300, said.decode('utf-8', 'replace')
             .split('\n')[0] if isinstance(said, bytes) else said)
        if security in ('starttls', 'starttls-if'):
            if conn.has_extn('starttls'):
                try:
                    conn.starttls(context=ctx)
                except ssl.SSLCertVerificationError as e:
                    step('started TLS', False, 'its certificate is not trusted: %s'
                         % e.verify_message)
                    raise MailError('the certificate of %s is not trusted - add the authority '
                                    'that signed it, or switch the check off' % host, steps)
                conn.ehlo()
                cert = conn.sock.getpeercert() if hasattr(conn.sock, 'getpeercert') else None
                who = ''
                if cert:
                    who = ', '.join('%s=%s' % kv for part in cert.get('subject', ())
                                    for kv in part if kv[0] == 'commonName')
                step('started TLS', True, (conn.sock.version() if hasattr(conn.sock, 'version')
                                           else '') + ((' · ' + who) if who else ''))
            elif security == 'starttls':
                step('start TLS', False, 'the server does not offer STARTTLS')
                raise MailError('%s does not offer STARTTLS - choose TLS from the start, or '
                                'none' % host, steps)
            else:
                step('stayed in plain text', True, 'the server does not offer STARTTLS')
                if auth and auth != 'none' and not direct:
                    # Not the password in plain text (1.0.94): a STARTTLS taken
                    # out on the way would have had it read off the wire.
                    step('sign in', False, 'not without TLS: the password would go in plain text')
                    raise MailError('%s offered no STARTTLS, and the password is not sent in '
                                    'plain text - choose STARTTLS (required) or TLS from the '
                                    'start, or Security none if a plain connection is meant'
                                    % host, steps)
        if auth and auth != 'none' and not direct:
            user = str(CONFIG.get('smtp_user') or '')
            pw = unseal_secret(CONFIG.get('smtp_password') or '', 'setting:smtp_password') or ''
            offered = (conn.esmtp_features.get('auth') or '').upper().split()
            try:
                if auth == 'auto':
                    conn.login(user, pw)
                elif auth == 'xoauth2':
                    conn.auth('XOAUTH2', _xoauth2(user, pw), initial_response_ok=True)
                else:
                    conn.user, conn.password = user, pw
                    mech = {'plain': 'PLAIN', 'login': 'LOGIN', 'cram-md5': 'CRAM-MD5'}[auth]
                    fn = {'PLAIN': conn.auth_plain, 'LOGIN': conn.auth_login,
                          'CRAM-MD5': conn.auth_cram_md5}[mech]
                    conn.auth(mech, fn, initial_response_ok=(mech != 'CRAM-MD5'))
                step('signed in as %s (%s)' % (user, auth.upper()), True,
                     'it offers: %s' % (' '.join(offered) or 'nothing'))
            except smtplib.SMTPAuthenticationError as e:
                step('sign in as %s (%s)' % (user, auth.upper()), False,
                     '%s %s' % (e.smtp_code, (e.smtp_error or b'').decode('utf-8', 'replace')))
                raise MailError('the mail server did not take the account or the password',
                                steps)
            except smtplib.SMTPException as e:
                step('sign in as %s (%s)' % (user, auth.upper()), False,
                     '%s · it offers: %s' % (e, ' '.join(offered) or 'nothing'))
                raise MailError('signing in failed: %s' % e, steps)
        if msg is not None:
            refused = conn.send_message(msg, to_addrs=list(to))
            if refused:
                step('handed the message over', False, '; '.join(
                    '%s: %s' % (k, v) for k, v in refused.items()))
                raise MailError('the server refused %s' % ', '.join(refused), steps,
                                permanent=all(int((v or (0,))[0] or 0) >= 500
                                              for v in refused.values()))
            reply = getattr(conn, 'last_reply', None)
            said = ''
            if reply:
                said = ' · %s %s' % (reply[0], (reply[1] or b'').decode('utf-8', 'replace')
                                     if isinstance(reply[1], bytes) else reply[1])
            step('handed the message over', True, 'for %s%s' % (', '.join(to), said))
    except smtplib.SMTPRecipientsRefused as e:
        step('handed the message over', False, '; '.join(
            '%s: %s %s' % (k, v[0], v[1].decode('utf-8', 'replace') if isinstance(v[1], bytes)
                           else v[1]) for k, v in e.recipients.items()))
        raise MailError('the server would not take mail for %s' % ', '.join(e.recipients), steps,
                        permanent=all(int((v or (0,))[0] or 0) >= 500
                                      for v in e.recipients.values()))
    except smtplib.SMTPSenderRefused as e:
        step('handed the message over', False, '%s %s' % (e.smtp_code, (
            e.smtp_error or b'').decode('utf-8', 'replace')))
        raise MailError('the server would not take mail from %s' % e.sender, steps,
                        permanent=int(e.smtp_code or 0) >= 500)
    except (smtplib.SMTPException, OSError) as e:
        if not isinstance(e, MailError):
            step('talking to it', False, e)
            raise MailError('the conversation with %s broke off: %s' % (host, e), steps,
                            permanent=int(getattr(e, 'smtp_code', 0) or 0) >= 500)
        raise
    finally:
        try:
            conn.quit()
        except Exception:
            pass
        try:
            conn.close()        # the watchman goes too (1.0.103)
        except Exception:
            pass
    return steps


def mail_send(store, msg, to, mode=None):
    """Send `msg` to `to` ([addresses]) the way the settings say. Returns the
    steps; raises MailError with them where it failed."""
    mode = mode or CONFIG.get('mail_mode') or 'off'
    steps = []
    if mode == 'off':
        raise MailError('sending mail is switched off - Settings → Mail', steps)
    if mode == 'smtp':
        host = str(CONFIG.get('smtp_host') or '').strip()
        if not host:
            raise MailError('no mail server is set - Settings → Mail', steps)
        security = CONFIG.get('smtp_security') or 'starttls'
        port = int(CONFIG.get('smtp_port') or 0) or {'tls': 465, 'none': 25}.get(security, 587)
        return smtp_talk(store, host, port, security, CONFIG.get('smtp_auth') or 'auto', msg,
                         to, steps)
    # Straight to each domain's own server: one conversation per domain.
    by_domain = collections.OrderedDict()
    for one in to:
        by_domain.setdefault(one.rsplit('@', 1)[-1].lower(), []).append(one)
    port = int(CONFIG.get('mail_direct_port') or 25)
    for domain, who in by_domain.items():
        try:
            mxs, how = dns_mx_full(domain)
            mxs = [m for m in mxs if m[1] not in ('', '.')]
            if not mxs:
                raise MailError('%s takes no mail (its MX record is a null MX)' % domain,
                                permanent=True)
        except MailError as e:
            steps.append({'what': 'look up the mail servers of %s' % domain, 'ok': False,
                          'said': str(e)})
            raise MailError(str(e), steps, permanent=e.permanent)
        steps.append({'what': 'looked up the mail servers of %s' % domain, 'ok': True,
                      'said': ', '.join('%s (%d)' % (h, p) for p, h in mxs) + ' · ' + how})
        last = None
        # One deadline over every MX of the domain (1.0.59): four servers of
        # two addresses each at 20 s outlasted the page asking.
        deadline = time.time() + MAIL_DIRECT_DEADLINE_S
        for _pref, host in mxs[:4]:
            left = deadline - time.time()
            if left < 3:
                last = last or MailError('no time left to try %s' % host, steps)
                break
            try:
                smtp_talk(store, host, port,
                          'starttls' if CONFIG.get('mail_direct_tls') == 'required'
                          else 'starttls-if', 'none', msg, who, steps, direct=True,
                          timeout=min(float(CONFIG.get('smtp_timeout_s') or 20), left / 2))
                last = None
                break
            except MailError as e:
                last = e
        if last:
            raise MailError('no mail server of %s took it: %s' % (domain, last), steps,
                            permanent=getattr(last, 'permanent', False))
    return steps


# ---- the QR code as a picture every mail program shows ----------------------------


# ---------------------------------------------------------------------------
# From otp: SMS - an HTTP gateway, a modem's spool, or a Teltonika on the network
# ---------------------------------------------------------------------------
# For the codes of the second step of signing in sent by SMS. Taken over from
# otp 1.0.161 as it is there: the same gateways, the same checks, the same
# words in the log (never the text being sent).
STORE_NOW = {'store': None}
IS_DAEMON = [False]


# ---- sending -------------------------------------------------------------------------
class SmsError(RuntimeError):
    pass


def sms_plain(text):
    """The text without accents (1.0.81): one letter outside the GSM
    alphabet makes the whole SMS the wide one, 70 characters a part."""
    if not CONFIG.get('sms_plain', 1):
        return text
    import unicodedata
    out = unicodedata.normalize('NFKD', str(text))
    out = ''.join(c for c in out if not unicodedata.combining(c))
    return out.replace('–', '-').replace('—', '-').replace('„', '"').replace('“', '"')


# ---- a Teltonika gateway (TRB140, RUT…), as zigmon speaks to it (1.0.81) -----------
TELTONIKA = {'token': None, 'until': 0.0, 'modem': None, 'last': 0.0}
TELTONIKA_LOCK = threading.Lock()


def _tel_url(path, params=None):
    host = str(CONFIG.get('sms_tel_host') or '').strip().rstrip('/')
    if not host:
        raise SmsError('no address of the Teltonika gateway is set - Settings → Codes by e-mail '
                       'and SMS')
    scheme = 'https' if CONFIG.get('sms_tel_https', 1) else 'http'
    if '://' in host:
        scheme, host = host.split('://', 1)
    url = '%s://%s%s' % (scheme, host, path)
    if params:
        url += '?' + urllib.parse.urlencode(params)
    return url


SMS_CA_META = 'sms_ca'          # the gateway's certificates trusted (1.0.89)


def sms_ca_pem(store=None):
    store = store or STORE_NOW.get('store')
    if store is None:
        return ''
    try:
        return str(store.get_meta(SMS_CA_META) or '')
    except Exception:                                   # noqa: BLE001
        return ''


def sms_ca_set(store, pem, mode='add', fingerprint=''):
    """The certificates the Teltonika gateway is checked against - each added
    and taken out by itself, as the mail server's."""
    pem = str(pem or '').strip()
    have = split_certificates(sms_ca_pem(store))
    if mode == 'add':
        new = split_certificates(pem)
        if not new or not all(describe_certificate(b) for b in new):
            raise ValueError('that is not a certificate this can read: a PEM certificate '
                             'starts -----BEGIN CERTIFICATE-----')
        seen = {c['fingerprint'] for c in describe_certificates('\n'.join(have))}
        have += [b for b, c in zip(new, describe_certificates('\n'.join(new)))
                 if c['fingerprint'] not in seen]
    elif mode == 'drop':
        keep = [b for b, c in zip(have, describe_certificates('\n'.join(have)))
                if c['fingerprint'] != fingerprint]
        if len(keep) == len(have):
            raise ValueError('that certificate is not among the ones kept')
        have = keep
    elif mode == 'clear':
        have = []
    else:
        raise ValueError('add, drop or clear?')
    store.set_meta(SMS_CA_META, '\n'.join(have))
    return describe_certificates('\n'.join(have))


def _tel_is_name(host):
    host = host.split('://', 1)[-1].split('/')[0]
    if host.startswith('['):
        return False
    host = host.rsplit(':', 1)[0] if host.count(':') == 1 else host
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return True


def _tel_ssl():
    if not CONFIG.get('sms_tel_verify'):
        # A TRB makes its own certificate; nothing can check it.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    pem = sms_ca_pem()
    if not pem.strip():
        return ssl.create_default_context()
    # Only what was imported (1.0.89): the gateway's own certificate, or the
    # authority of your own that signed it. A gateway reached by its address
    # has no name to check against - its certificate is: the chain must end
    # in one of these.
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    try:
        ctx.load_verify_locations(cadata=pem)
    except (ssl.SSLError, ValueError) as e:
        raise SmsError('the certificates kept for the gateway cannot be read: %s' % e)
    # Any certificate imported is an anchor of its own (1.0.92): a TRB sends
    # only its own certificate, signed by a "ca" it never shows, and that
    # certificate alone - read from it - was refused as "unable to get local
    # issuer certificate". The strict checks of 3.13 are left out too: a
    # gateway's own certificate is not a web server's.
    ctx.verify_flags |= getattr(ssl, 'VERIFY_X509_PARTIAL_CHAIN', 0x80000)
    ctx.verify_flags &= ~getattr(ssl, 'VERIFY_X509_STRICT', 0x20)
    ctx.check_hostname = _tel_is_name(str(CONFIG.get('sms_tel_host') or ''))
    return ctx


def tel_peer_chain():
    """The certificates the gateway shows, read without checking them - for
    an administrator to look at and trust (1.0.89)."""
    host = str(CONFIG.get('sms_tel_host') or '').strip().rstrip('/')
    if not host:
        raise SmsError('no address of the Teltonika gateway is set')
    host = host.split('://', 1)[-1].split('/')[0]
    port = 443
    if host.startswith('['):
        name, _, rest = host[1:].partition(']')
        if rest.startswith(':'):
            port = int(rest[1:])
    elif host.count(':') == 1:
        name, port = host.split(':')
        port = int(port)
    else:
        name = host
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((name, port), timeout=10) as raw:
            with ctx.wrap_socket(raw, server_hostname=name if _tel_is_name(name) else None) as tls:
                chain = []
                if hasattr(tls, 'get_unverified_chain'):
                    try:
                        chain = [c if isinstance(c, bytes) else c.public_bytes(1)
                                 for c in tls.get_unverified_chain() or []]
                    except Exception:                   # noqa: BLE001
                        chain = []
                if not chain:
                    chain = [tls.getpeercert(binary_form=True)]
    except (OSError, ssl.SSLError) as e:
        raise SmsError('%s:%d could not be reached over TLS: %s' % (name, port, e))
    pems = [ssl.DER_cert_to_PEM_cert(d).strip() for d in chain if d]
    return '\n'.join(pems)


def _tel_password():
    pw = CONFIG.get('sms_tel_password') or ''
    return (unseal_secret(pw, 'setting:sms_tel_password') or '') if pw else ''


class _TelAnswer(object):
    """An answer already read - so that it could be written into the log."""

    def __init__(self, status, body):
        self.status, self._body = status, body

    def read(self, n=-1):
        got = self._body if n is None or n < 0 else self._body[:n]
        self._body = b'' if n is None or n < 0 else self._body[n:]
        return got

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_TEL_TEXT = threading.local()     # the text being sent, kept out of the debug log


def _tel_hidden(words):
    """A request or an answer as the debug log may hold it: no password,
    no token (1.0.113), and not the text with its live code (1.0.146)."""
    text = getattr(_TEL_TEXT, 'v', '') or ''
    if text:
        for form in {text, urllib.parse.quote(text, safe=''), urllib.parse.quote_plus(text),
                     json.dumps(text)[1:-1], json.dumps(text, ensure_ascii=False)[1:-1]}:
            if form:
                words = words.replace(form, '<the text, %d characters>' % len(text))
    words = re.sub(r'(?i)("(?:password|token)"\s*:\s*")[^"]*', r'\1***', words)
    words = re.sub(r'(?i)((?:password|token)=)[^&\s]*', r'\1***', words)
    return re.sub(r'(?i)(Bearer )\S+', r'\1***', words)


def _tel_open(req, timeout=20.0):
    loud = debugging('codes')
    began = time.time()
    if loud:
        body = req.data.decode('utf-8', 'replace') if isinstance(req.data, bytes) else ''
        log('sms: -> %s %s%s (waits %d s)' % (req.get_method(), _tel_hidden(req.full_url),
                                             (' ' + _tel_hidden(body)[:300]) if body else '',
                                             timeout), 'debug')
    try:
        r = urllib.request.urlopen(req, timeout=timeout, context=_tel_ssl()
                                   if req.full_url.startswith('https') else None)
        if not loud:
            return r
        with r:
            body = r.read(65536)
            status = getattr(r, 'status', 200)
        log('sms: <- HTTP %s in %.2f s: %s' % (status, time.time() - began, _tel_hidden(
            body.decode('utf-8', 'replace'))[:400]), 'debug')
        return _TelAnswer(status, body)
    except urllib.error.URLError as e:
        if loud:
            _tel_said_failed(e, began)
        # The certificate refused (1.0.89): nothing was sent, and the page
        # says what to do about it.
        if isinstance(getattr(e, 'reason', None), ssl.SSLCertVerificationError):
            raise SmsError('the gateway\'s certificate did not pass the check (%s): import its '
                           'certificate or the authority that signed it under Settings → Codes '
                           'by e-mail and SMS, or switch Check its certificate off'
                           % (getattr(e.reason, 'verify_message', '') or e.reason))
        raise
    except Exception as e:                              # noqa: BLE001
        if loud:
            _tel_said_failed(e, began)
        raise


def _tel_said_failed(e, began):
    extra = ''
    if isinstance(e, urllib.error.HTTPError):
        try:
            said = e.read(400)
            extra = ': ' + _tel_hidden(said.decode('utf-8', 'replace'))
            e.read = (lambda b: (lambda n=-1: b))(said)         # the caller reads it too
        except Exception:                               # noqa: BLE001
            pass
    log('sms: <- FAILED after %.2f s: %s %s%s' % (time.time() - began, type(e).__name__,
                                               getattr(e, 'reason', e), extra), 'debug')


def _tel_never_arrived(e):
    """Whether a failed request certainly never reached the gateway - a
    refused or reset connection. A read that timed out did reach it: the box
    took the message and has not answered, and sending it again is a second
    SMS on the person's phone (zigmon's lesson)."""
    if isinstance(e, socket.timeout):
        return False
    reason = getattr(e, 'reason', e)
    if isinstance(reason, socket.timeout):
        return False
    words = str(e).lower()
    if 'timed out' in words or 'timeout' in words:
        return False
    return isinstance(reason, (ConnectionRefusedError, ConnectionResetError,
                               ConnectionAbortedError, socket.gaierror)) or \
        any(w in words for w in ('refused', 'reset by peer', 'not known', 'no route',
                                 'broken pipe'))


def _tel_who():
    """What a login is for: another address, user or password is another
    login - a token kept from before a change is not used after it."""
    return hashlib.sha256(('%s|%s|%s|%s' % (CONFIG.get('sms_tel_host'), CONFIG.get('sms_tel_https'),
                                            CONFIG.get('sms_tel_user'), _tel_password()))
                          .encode('utf-8')).hexdigest()


def _tel_logout(token, who=None):
    """A login given back (1.0.152): every new one used to be left to run out
    on the box, which lists each as a session of its own until it does. Best
    effort, a few seconds at most - an older RutOS without it only says no."""
    if not token:
        return
    try:
        req = urllib.request.Request(_tel_url('/api/logout'), data=b'{}', method='POST',
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + token})
        with _tel_open(req, 4) as r:
            r.read(200)
    except Exception:                                   # noqa: BLE001
        pass


def _tel_drop_token():
    """The login in hand given back and forgotten."""
    old, TELTONIKA['token'] = TELTONIKA.get('token'), None
    _tel_logout(old)


def _tel_end_of_process():
    # A command that sent or tried something gives its login back as it ends
    # (1.0.152); the daemon keeps its one and renews it.
    if not IS_DAEMON[0] and TELTONIKA.get('token'):
        _tel_drop_token()


import atexit as _atexit                                # noqa: E402
_atexit.register(_tel_end_of_process)


def _tel_token(fresh=False):
    """A login on RutOS's own API: a token that lasts five minutes, renewed a
    minute before - one at a time: the one before is given back first."""
    now = time.time()
    if TELTONIKA.get('who') != _tel_who():
        # Another box or user: the old login is not this one's to give back
        # with its address gone - it runs out by itself there.
        TELTONIKA.update(token=None, modem=None, who=_tel_who())
    if not fresh and TELTONIKA['token'] and now < TELTONIKA['until']:
        return TELTONIKA['token']
    _tel_drop_token()
    body = json.dumps({'username': CONFIG.get('sms_tel_user') or 'admin',
                       'password': _tel_password()}).encode()
    tries = 0
    while True:
        tries += 1
        req = urllib.request.Request(_tel_url('/api/login'), data=body, method='POST',
                                     headers={'Content-Type': 'application/json'})
        try:
            with _tel_open(req, 15) as r:
                answer = json.loads(r.read() or b'{}')
            break
        except urllib.error.HTTPError as e:
            raise SmsError('the Teltonika would not let ai in (HTTP %d) - check its user and '
                           'password, and that the user may use the API' % e.code)
        except (urllib.error.URLError, OSError, ValueError) as e:
            # Signing in is asked again once (1.0.113): a box busy with the
            # modem leaves a login unanswered now and then, and asking again
            # sends nothing twice.
            if tries < 2 and not isinstance(e, ValueError):
                log('sms: the Teltonika did not answer the sign-in (%s) - asked again'
                    % getattr(e, 'reason', e), 'warn')
                time.sleep(1)
                continue
            raise SmsError('the Teltonika could not be reached%s: %s' % (
                ' (asked twice)' if tries > 1 else '', getattr(e, 'reason', e)))
    data = answer.get('data') or {}
    token = data.get('token') or answer.get('token') or ''
    if not token:
        raise SmsError('the Teltonika gave no token: %s' % json.dumps(answer)[:150])
    TELTONIKA['token'] = token
    TELTONIKA['until'] = now + max(30.0, float(data.get('expires') or 299) - 60)
    return token


def _tel_rest(path, method='GET', payload=None, timeout=20.0, again=True):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(_tel_url('/api' + path), data=data, method=method,
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': 'Bearer ' + _tel_token()})
    try:
        with _tel_open(req, timeout) as r:
            answer = json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        said = ''
        try:
            said = e.read(300).decode('utf-8', 'replace')
        except Exception:                               # noqa: BLE001
            pass
        if e.code in (401, 403) and again:
            TELTONIKA['token'] = None                   # gone stale - nothing to give back
            return _tel_rest(path, method, payload, timeout, again=False)
        raise SmsError('the Teltonika answered %s %s with HTTP %d %s' % (method, path, e.code,
                                                                         said))
    if answer.get('success') is False:
        raise SmsError('the Teltonika refused %s: %s' % (path, json.dumps(
            answer.get('errors') or answer)[:200]))
    return answer.get('data', answer)


def _tel_modem():
    if CONFIG.get('sms_tel_modem'):
        return str(CONFIG['sms_tel_modem']).strip()
    if TELTONIKA.get('who') != _tel_who():
        TELTONIKA.update(token=None, modem=None, who=_tel_who())
    if TELTONIKA['modem']:
        return TELTONIKA['modem']
    rows = _tel_rest('/modems/status') or []
    if isinstance(rows, dict):
        rows = [rows]
    first = next((r for r in rows if isinstance(r, dict) and r.get('id')), None)
    if not first:
        raise SmsError('the Teltonika named no modem')
    TELTONIKA['modem'] = str(first['id'])
    return TELTONIKA['modem']


def tel_send(to, text):
    """One SMS through a Teltonika, one at a time: the box sends one message
    after another, and a second asked for at once is taken and then left
    unanswered for a minute."""
    waited = time.time()
    with TELTONIKA_LOCK:
        gap = 2.0 - (time.time() - TELTONIKA['last'])
        if gap > 0:
            time.sleep(gap)
        loud = debugging('codes')
        if loud:
            log('sms: to %s, %d characters, through the Teltonika %s (%s), after %.1f s in the '
                'queue' % (to[:-3] + '***' if len(to) > 6 else to, len(text),
                           CONFIG.get('sms_tel_host'), CONFIG.get('sms_tel_api') or 'rest',
                           time.time() - waited), 'debug')
        began = time.time()
        _TEL_TEXT.v = text
        try:
            said = _tel_send(to, text)
            if loud:
                log('sms: done in %.1f s - %s' % (time.time() - began, said), 'debug')
            return said
        except Exception as e:
            if loud:
                log('sms: FAILED after %.1f s - %s' % (time.time() - began, e), 'debug')
            raise
        finally:
            _TEL_TEXT.v = ''
            TELTONIKA['last'] = time.time()


def _tel_send(to, text):
    parts = 1 if len(text) <= (160 if all(ord(c) < 128 for c in text) else 70) else 2
    timeout = 20.0 * parts
    if (CONFIG.get('sms_tel_api') or 'rest') == 'cgi':
        number = '00' + to.lstrip('+')                  # Teltonika's CGI wants 00420…
        url = _tel_url('/cgi-bin/sms_send', {'username': CONFIG.get('sms_tel_user') or '',
                                             'password': _tel_password(), 'number': number,
                                             'text': text})
        tries = 0
        while True:
            tries += 1
            try:
                with _tel_open(urllib.request.Request(url), timeout) as r:
                    said = r.read(400).decode('utf-8', 'replace').strip()
                break
            except urllib.error.HTTPError as e:
                raise SmsError('the Teltonika answered HTTP %d: %s' % (
                    e.code, e.read(200).decode('utf-8', 'replace')))
            except (urllib.error.URLError, OSError) as e:
                if tries < 3 and _tel_never_arrived(e):
                    time.sleep(tries)
                    continue
                if not _tel_never_arrived(e):
                    return 'no answer from the Teltonika in %d s - the SMS has most likely gone' \
                        % timeout
                raise SmsError('the Teltonika could not be reached: %s' % getattr(e, 'reason', e))
        if 'error' in said.lower() and not said.lower().startswith('ok'):
            raise SmsError('the Teltonika said: %s' % said[:200])
        return 'the Teltonika said: %s' % (said[:120] or 'OK')
    tries = 0
    while True:
        tries += 1
        try:
            # How long each step took, said with the answer (1.0.109): a
            # test that took long tells whether it was the login, finding
            # the modem or the sending itself - RutOS answers the send only
            # once the modem has given the SMS to the network.
            t0 = time.time()
            _tel_token()
            t1 = time.time()
            modem = _tel_modem()
            t2 = time.time()
            out = _tel_rest('/messages/actions/send', 'POST',
                            {'data': {'number': to, 'message': text, 'modem': modem}},
                            timeout=timeout)
            t3 = time.time()
            steps = []
            if t1 - t0 > 0.05:
                steps.append('signing in %.1f s' % (t1 - t0))
            if t2 - t1 > 0.05:
                steps.append('finding the modem %.1f s' % (t2 - t1))
            steps.append('the modem sending it %.1f s' % (t3 - t2))
            return 'the Teltonika took it (%s; %s)' % (', '.join(steps), json.dumps(out)[:60])
        except SmsError:
            raise
        except (urllib.error.URLError, OSError) as e:
            if tries < 3 and _tel_never_arrived(e):
                TELTONIKA['until'] = 0                  # a new connection, a new login
                time.sleep(tries)
                continue
            if not _tel_never_arrived(e):
                return 'no answer from the Teltonika in %d s - the SMS has most likely gone' \
                    % timeout
            raise SmsError('the Teltonika could not be reached: %s' % getattr(e, 'reason', e))


def tel_check():
    """Whether the gateway is there and takes the password - nothing sent."""
    if (CONFIG.get('sms_tel_api') or 'rest') == 'cgi':
        url = _tel_url('/cgi-bin/sms_list', {'username': CONFIG.get('sms_tel_user') or '',
                                             'password': _tel_password()})
        try:
            with _tel_open(urllib.request.Request(url), 15) as r:
                said = r.read(300).decode('utf-8', 'replace')
        except (urllib.error.URLError, OSError) as e:
            raise SmsError('the Teltonika could not be reached: %s' % getattr(e, 'reason', e))
        if 'error' in said.lower() and 'no messages' not in said.lower():
            raise SmsError('the Teltonika said: %s' % said.strip()[:150])
        return 'the Teltonika answered and took the password'
    _tel_token(fresh=True)
    TELTONIKA['modem'] = None
    return 'the Teltonika let ai in; its modem is %s' % _tel_modem()


# What a modem's status says, in the order shown (1.0.113). RutOS 7 names
# them so; a field it does not have is left out.
TEL_MODEM_FIELDS = (
    ('name', 'Modem'), ('model', 'Model'), ('operator', 'Operator'),
    ('ntype', 'Network'), ('conntype', 'Connection'), ('band', 'Band'),
    ('state', 'State'), ('operator_state', 'Registered'), ('netstate', 'Network state'),
    ('active_sim', 'SIM in use'), ('simstate', 'SIM'), ('pinstate', 'PIN'),
    ('signal_quality', 'Signal quality (%)'), ('rssi', 'RSSI (dBm)'), ('rsrp', 'RSRP (dBm)'),
    ('rsrq', 'RSRQ (dB)'), ('sinr', 'SINR (dB)'), ('temperature', 'Temperature (C)'),
    ('volte', 'VoLTE'), ('sms_center_address', 'SMS centre'), ('imei', 'IMEI'),
    ('version', 'Modem firmware'))


def tel_modem_words(row):
    out = [('id', str(row.get('id') or ''))]
    for k, words in TEL_MODEM_FIELDS:
        v = row.get(k)
        if v in (None, '', [], {}):
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v)[:80]
        out.append((words, str(v)[:80]))
    if len(out) < 4:
        # Another firmware, other names: what it said, plainly.
        for k, v in list(row.items())[:12]:
            if k != 'id' and isinstance(v, (str, int, float)) and str(v) != '':
                out.append((str(k)[:30], str(v)[:80]))
    return out


def tel_test():
    """The gateway tried, step by step, without sending anything (1.0.113):
    reached, signed in, its modems and what each says about the network."""
    mode = (CONFIG.get('sms_tel_api') or 'rest')
    host = str(CONFIG.get('sms_tel_host') or '').strip()
    out = {'ok': False, 'steps': [], 'modems': [], 'api': mode, 'host': host,
           'https': bool(CONFIG.get('sms_tel_https')),
           'checked': bool(CONFIG.get('sms_tel_https') and CONFIG.get('sms_tel_verify'))}
    if not host:
        out['steps'].append({'what': 'the address', 'ok': False, 'secs': 0,
                             'said': 'no address of the gateway is saved'})
        return out

    def step(what, fn):
        t = time.time()
        try:
            got = fn()
        except SmsError as e:
            out['steps'].append({'what': what, 'ok': False, 'secs': round(time.time() - t, 2),
                                 'said': str(e)})
            return None, False
        out['steps'].append({'what': what, 'ok': True, 'secs': round(time.time() - t, 2),
                             'said': got if isinstance(got, str) else ''})
        return got, True

    with TELTONIKA_LOCK:
        if mode == 'cgi':
            _x, ok = step('signing in (Post/Get)', tel_check)
            out['ok'] = ok
            return out
        TELTONIKA['modem'] = None
        _x, ok = step('signing in', lambda: (_tel_token(fresh=True) and 'let in as %s'
                                            % (CONFIG.get('sms_tel_user') or 'admin')))
        if not ok:
            return out
        rows, ok = step('its modems', lambda: _tel_rest('/modems/status'))
        if not ok:
            return out
        if isinstance(rows, dict):
            rows = [rows]
        rows = [r for r in (rows or []) if isinstance(r, dict)]
        want = str(CONFIG.get('sms_tel_modem') or '').strip()
        chosen = want or (str(rows[0].get('id')) if rows and rows[0].get('id') else '')
        for r in rows[:6]:
            out['modems'].append({'id': str(r.get('id') or ''), 'sends': str(r.get('id')) == chosen,
                                  'fields': tel_modem_words(r)})
        out['steps'][-1]['said'] = '%d modem(s)' % len(rows)
        if want and not any(str(r.get('id')) == want for r in rows):
            out['steps'].append({'what': 'the modem set', 'ok': False, 'secs': 0,
                                 'said': 'the gateway has no modem %s - it has %s' % (
                                     want, ', '.join(str(r.get('id')) for r in rows) or 'none')})
            return out
        if not chosen:
            out['steps'].append({'what': 'the modem', 'ok': False, 'secs': 0,
                                 'said': 'the gateway named no modem'})
            return out
        TELTONIKA['modem'] = chosen
        out['ok'] = True
    return out


def sms_send(to, text):
    """One SMS. Returns what the gateway said; raises SmsError."""
    mode = CONFIG.get('sms_mode') or 'off'
    if mode == 'off':
        raise SmsError('sending SMS is switched off - Settings → Codes by mail and SMS')
    text = sms_plain(text)
    if mode == 'teltonika':
        return tel_send(to, text)
    if mode == 'spool':
        folder = Path(str(CONFIG.get('sms_spool_dir') or '').strip())
        if not folder.is_dir():
            raise SmsError('the spool folder %s is not there' % folder)
        # smstools3: a file "To: 420…", an empty line, the text. Written
        # beside and renamed in, so the daemon never reads half of one.
        body = 'To: %s\nAlphabet: UTF-8\n\n%s\n' % (to.lstrip('+'), text)
        name = 'ai-%d-%s' % (int(time.time()), secrets.token_hex(4))
        tmp = folder / ('.' + name)
        try:
            with open(str(tmp), 'w', encoding='utf-8') as f:
                f.write(body)
            os.chmod(str(tmp), 0o664)
            os.rename(str(tmp), str(folder / name))
        except OSError as e:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise SmsError('it could not be written into %s: %s' % (folder, e))
        return 'written into %s as %s' % (folder, name)
    url = str(CONFIG.get('sms_url') or '').strip()
    if not url:
        raise SmsError('no gateway address is set - Settings → Codes by mail and SMS')
    token = unseal_secret(CONFIG.get('sms_token') or '', 'setting:sms_token') or '' if CONFIG.get('sms_token') else ''
    vals = {'to': to, 'to_digits': to.lstrip('+'), 'text': text, 'token': token}

    def fill(tpl, how):
        def one(m):
            k = m.group(1)
            v = vals.get(k)
            if v is None:
                return m.group(0)
            if how == 'url':
                return urllib.parse.quote(v, safe='')
            if how == 'json':
                return json.dumps(v)[1:-1]
            return v
        return re.sub(r'\{(to|to_digits|text|token)\}', one, tpl)
    full = fill(url, 'url')
    method = (CONFIG.get('sms_method') or 'POST').upper()
    tpl = str(CONFIG.get('sms_body') or '')
    data, ctype = None, None
    if method == 'POST':
        if tpl.strip().startswith('{'):
            data, ctype = fill(tpl, 'json').encode('utf-8'), 'application/json'
        elif tpl.strip():
            data, ctype = fill(tpl, 'url').encode('utf-8'), 'application/x-www-form-urlencoded'
        else:
            data = b''
    req = urllib.request.Request(full, data=data, method=method)
    if ctype:
        req.add_header('Content-Type', ctype)
    for line in str(CONFIG.get('sms_headers') or '').splitlines():
        if ':' in line:
            k, _, v = line.partition(':')
            if k.strip():
                req.add_header(k.strip(), fill(v.strip(), 'raw'))
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            said = r.read(4000).decode('utf-8', 'replace')
            status = r.status
    except urllib.error.HTTPError as e:
        _TEL_TEXT.v = text
        try:
            body = _tel_hidden(e.read(300).decode('utf-8', 'replace'))
        finally:
            _TEL_TEXT.v = ''
        raise SmsError('the gateway answered %d: %s' % (e.code, body))
    except (urllib.error.URLError, OSError) as e:
        raise SmsError('the gateway could not be reached: %s' % getattr(e, 'reason', e))
    want = str(CONFIG.get('sms_ok_status') or '').strip()
    # A gateway that says back what it was sent (1.0.147): not the code
    # into the events and the log with it.
    _TEL_TEXT.v = text
    try:
        said = _tel_hidden(said)
    finally:
        _TEL_TEXT.v = ''
    if want and want.lower() not in said.lower():
        raise SmsError('the gateway answered %d without "%s": %s' % (status, want, said[:300]))
    return 'the gateway answered %d%s' % (status, (': ' + said[:200]) if said.strip() else '')


# ---------------------------------------------------------------------------
# The database (otp's, 1.0.6)
# ---------------------------------------------------------------------------
# One of three, as on otp and isemon: a SQLite file on this machine unless
# somebody says otherwise, or a MariaDB or a PostgreSQL (config.json: db_engine,
# db_host, db_port, db_name, db_user, db_password, db_tls, db_tls_ca). The SQL
# is written once, with `?` for every value, and said in each engine's own
# words where they differ - the types, the numbering of rows, the placeholders.
# One connection, behind one lock (no cluster here, so no lanes).
class DbError(Exception):
    pass


SCHEMA_VERSION = 2

DB_SCHEMA = [
    ('meta', '''CREATE TABLE IF NOT EXISTS meta (
        k {K} PRIMARY KEY, v {B})'''),
    ('settings', '''CREATE TABLE IF NOT EXISTS settings (
        k {K} PRIMARY KEY, v {B}, at {N}, by_who {K})'''),
    ('users', '''CREATE TABLE IF NOT EXISTS users (
        name {K} PRIMARY KEY, pw {T}, role {K}, run_as {K}, roots {T}, disabled {I},
        must_change {I}, prefs {B}, note {T}, created {N}, last_login {N}, last_ip {K})'''),
    ('sessions', '''CREATE TABLE IF NOT EXISTS sessions (
        id {K} PRIMARY KEY, name {K}, created {N}, seen {N}, ip {K}, agent {T}, data {B})'''),
    ('events', '''CREATE TABLE IF NOT EXISTS events (
        id {ID}, at {N}, kind {K}, level {K}, who {K}, text {T})'''),
    ('terms', '''CREATE TABLE IF NOT EXISTS terms (
        id {K} PRIMARY KEY, owner {K}, run_as {K}, title {T}, kind {K}, cwd {T}, opts {T},
        created {N}, ended {N}, last_screen {B}, exit_status {I})'''),
    ('fails', '''CREATE TABLE IF NOT EXISTS fails (
        k {K} PRIMARY KEY, n {I}, first {N}, until_ts {N})'''),
]
DB_INDEXES = [
    'CREATE INDEX IF NOT EXISTS events_at ON events (at)',
    'CREATE INDEX IF NOT EXISTS events_kind_at ON events (kind, at)',
    'CREATE INDEX IF NOT EXISTS sessions_name ON sessions (name)',
]
DB_TYPES = {
    'sqlite': {'ID': 'INTEGER PRIMARY KEY AUTOINCREMENT', 'K': 'TEXT', 'T': 'TEXT',
               'B': 'TEXT', 'N': 'REAL', 'I': 'INTEGER'},
    # Compared byte for byte, as SQLite and PostgreSQL compare (otp 1.0.44).
    'mariadb': {'ID': 'BIGINT AUTO_INCREMENT PRIMARY KEY', 'K': 'VARCHAR(190) COLLATE utf8mb4_bin',
                'T': 'TEXT', 'B': 'MEDIUMTEXT', 'N': 'DOUBLE', 'I': 'BIGINT'},
    'postgres': {'ID': 'BIGSERIAL PRIMARY KEY', 'K': 'TEXT', 'T': 'TEXT', 'B': 'TEXT',
                 'N': 'DOUBLE PRECISION', 'I': 'BIGINT'},
}
DB_TABLES = [name for name, _ in DB_SCHEMA]
DB_ID_TABLES = ('events',)


class RawSql(str):
    """A statement sent as it is, with no parameters."""


def _qmarks(sql):
    """`?` as `%s`, for the two engines whose drivers want that."""
    return sql.replace('%', '%%').replace('?', '%s')


def db_tls_args(engine, mode=None, ca=None):
    mode = str((CONFIG.get('db_tls') if mode is None else mode) or '')
    ca = str((CONFIG.get('db_tls_ca') if ca is None else ca) or '')
    if not mode:
        return {}
    if engine == 'postgres':
        out = {'sslmode': mode}
        if ca:
            out['sslrootcert'] = ca
        return out
    if mode == 'require':
        return {'ssl': {'check_hostname': False, 'verify_mode': ssl.CERT_NONE}}
    got = {'ssl': {'check_hostname': mode == 'verify-full', 'verify_mode': True}}
    if ca:
        got['ssl']['ca'] = ca
    return got


class Db(object):
    """One database, of whichever engine."""
    STATEMENT_S = 120
    LOCK_S = 10
    DOWN_RETRY_S = 2

    def __init__(self, engine='sqlite', host='', port=0, name='ai', user='ai', password='',
                 timeout=10, path=None, tls=None, tls_ca=None, statement_s=None):
        self.engine = engine if engine in DB_TYPES else 'sqlite'
        self.statement_s = self.STATEMENT_S if statement_s is None else int(statement_s)
        host = str(host or '').strip()
        if host.startswith('[') and host.endswith(']'):
            host = host[1:-1]
        self.host, self.port, self.name = host, int(port or 0), name
        self.user, self.password, self.timeout = user, password, int(timeout or 10)
        self.path = Path(path) if path else DB_FILE
        self.tls, self.tls_ca = tls, tls_ca
        self.lock = threading.RLock()
        self.conn = None
        self.in_tx = False
        self.down_until = 0.0
        self.down_said = ''
        self.restoring = False
        self.connect()

    def where(self):
        if self.engine == 'sqlite':
            return str(self.path)
        return '%s@%s:%s/%s' % (self.user, self.host or 'localhost',
                                self.port or {'mariadb': 3306, 'postgres': 5432}[self.engine], self.name)

    def connect(self):
        with self.lock:
            if self.conn is None and time.time() < self.down_until:
                raise DbError(self.down_said or 'the database is not answering')
            try:
                self._connect()
                self.down_until = 0.0
            except DbError as e:
                self.down_until = time.time() + self.DOWN_RETRY_S
                self.down_said = str(e)
                raise

    def _connect(self):
        if self.engine == 'sqlite':
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None, timeout=30)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA journal_size_limit=67108864')
            except sqlite3.Error:
                pass
            self.conn = conn
            try:
                os.chmod(str(self.path), 0o600)
            except OSError:
                pass
        elif self.engine == 'mariadb':
            try:
                import pymysql
                import pymysql.cursors
            except ImportError:
                raise DbError('MariaDB is chosen and its Python driver is not installed: '
                              'dnf install python3-PyMySQL (apt install python3-pymysql)')
            try:
                self.conn = pymysql.connect(
                    host=self.host or 'localhost', port=self.port or 3306, user=self.user,
                    password=self.password, database=self.name, charset='utf8mb4', autocommit=True,
                    connect_timeout=self.timeout,
                    read_timeout=max(30, self.statement_s + 10) if self.statement_s else 300,
                    write_timeout=60, cursorclass=pymysql.cursors.DictCursor,
                    **db_tls_args('mariadb', self.tls, self.tls_ca))
            except Exception as e:
                raise DbError('MariaDB at %s could not be reached: %s' % (self.where(), e))
            for sql in ('SET SESSION innodb_lock_wait_timeout = %d' % self.LOCK_S,
                        'SET SESSION max_statement_time = %d' % self.statement_s):
                try:
                    with self.conn.cursor() as cur:
                        cur.execute(sql)
                except Exception:                       # noqa: BLE001
                    pass
        else:
            try:
                import psycopg2
                import psycopg2.extras
            except ImportError:
                raise DbError('PostgreSQL is chosen and its Python driver is not installed: '
                              'dnf install python3-psycopg2 (apt install python3-psycopg2)')
            try:
                self.conn = psycopg2.connect(
                    host=self.host or 'localhost', port=self.port or 5432, user=self.user,
                    password=self.password, dbname=self.name, connect_timeout=self.timeout,
                    keepalives=1, keepalives_idle=10, keepalives_interval=3, keepalives_count=3,
                    options='-c lock_timeout=%d -c statement_timeout=%d' % (
                        self.LOCK_S * 1000, self.statement_s * 1000),
                    **db_tls_args('postgres', self.tls, self.tls_ca))
                self.conn.autocommit = True
                self.conn.set_client_encoding('UTF8')
            except Exception as e:
                raise DbError('PostgreSQL at %s could not be reached: %s' % (self.where(), e))

    def close(self):
        with self.lock:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
            self.conn = None

    def _run(self, sql, args, fetch):
        if self.engine == 'sqlite':
            cur = self.conn.execute(sql, tuple(args or ()))
            rows = [dict(r) for r in cur.fetchall()] if fetch else None
            return rows, cur.rowcount, cur.lastrowid
        if self.engine == 'mariadb':
            cur = self.conn.cursor()
            try:
                if isinstance(sql, RawSql):
                    cur.execute(str(sql))
                else:
                    cur.execute(_qmarks(sql), tuple(args or ()))
                rows = [dict(r) for r in cur.fetchall()] if fetch else None
                return rows, cur.rowcount, cur.lastrowid
            finally:
                cur.close()
        import psycopg2.extras
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            if isinstance(sql, RawSql):
                cur.execute(str(sql))
            else:
                cur.execute(_qmarks(sql), tuple(a.replace('\x00', '�') if isinstance(a, str) and '\x00' in a
                                                else a for a in (args or ())))
            rows = [dict(r) for r in cur.fetchall()] if (fetch or cur.description) else None
            return rows, cur.rowcount, rows[0].get('id') if (rows and not fetch) else None
        finally:
            cur.close()

    @staticmethod
    def _gone(e):
        said = str(e).lower()
        return any(w in said for w in ('gone away', 'lost connection', 'server closed', 'connection already closed',
                                       'terminating connection', 'broken pipe', 'connection reset',
                                       'not connected', 'interfaceerror', 'cursor already closed',
                                       'connection has been closed', 'connection is closed',
                                       'could not receive data', 'connection timed out'))

    def query(self, sql, args=(), fetch=True):
        with self.lock:
            if self.conn is None:
                self.connect()
            try:
                return self._run(sql, args, fetch)
            except Exception as e:
                if self.engine == 'sqlite' or not (self._gone(e) or type(e).__name__ == 'InterfaceError'):
                    raise
                if self.in_tx:
                    self.close()
                    raise
                # Made again - and run once more only where that cannot do it twice.
                self.close()
                self.connect()
                said = str(e).lower()
                unsent = type(e).__name__ == 'InterfaceError' or any(
                    w in said for w in ('connection already closed', 'not connected', 'cursor already closed'))
                if sql.lstrip().upper().startswith(('SELECT', 'WITH', 'SHOW', 'EXPLAIN')) or unsent:
                    return self._run(sql, args, fetch)
                raise

    def rows(self, sql, args=()):
        return self.query(sql, args, True)[0]

    def row(self, sql, args=()):
        got = self.rows(sql, args)
        return got[0] if got else None

    def value(self, sql, args=(), default=None):
        got = self.row(sql, args)
        if not got:
            return default
        return list(got.values())[0]

    def run(self, sql, args=()):
        return self.query(sql, args, False)[1]

    def upsert(self, table, key, row):
        """One row by its primary key, made or changed in one statement."""
        keys = list(row.keys())
        cols = ', '.join(keys)
        marks = ', '.join('?' for _ in keys)
        rest = [k for k in keys if k != key]
        if self.engine == 'mariadb':
            sql = 'INSERT INTO %s (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s' % (
                table, cols, marks, ', '.join('%s = VALUES(%s)' % (k, k) for k in rest))
        else:
            sql = 'INSERT INTO %s (%s) VALUES (%s) ON CONFLICT (%s) DO UPDATE SET %s' % (
                table, cols, marks, key, ', '.join('%s = excluded.%s' % (k, k) for k in rest))
        return self.run(sql, tuple(row[k] for k in keys))

    def insert(self, table, row):
        keys = list(row.keys())
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table, ', '.join(keys), ', '.join('?' for _ in keys))
        if self.engine == 'postgres' and table in DB_ID_TABLES:
            sql += ' RETURNING id'
        return self.query(sql, [row[k] for k in keys], False)[2]

    @contextlib.contextmanager
    def unlimited(self):
        if self.engine == 'sqlite' or not self.statement_s:
            yield
            return
        off, on = (('SET statement_timeout = 0', 'SET statement_timeout = %d' % (self.statement_s * 1000))
                   if self.engine == 'postgres' else
                   ('SET SESSION max_statement_time = 0', 'SET SESSION max_statement_time = %d' % self.statement_s))
        with self.lock:
            try:
                self.run(RawSql(off))
            except Exception:                           # noqa: BLE001
                pass
            try:
                yield
            finally:
                try:
                    self.run(RawSql(on))
                except Exception:                       # noqa: BLE001
                    pass

    def make_tables(self):
        with self.unlimited():
            types = DB_TYPES[self.engine]
            if self.engine == 'sqlite':
                self._sqlite_renames()
            for _name, ddl in DB_SCHEMA:
                sql = ddl.format(**types)
                if self.engine == 'mariadb':
                    sql += ' DEFAULT CHARSET=utf8mb4'
                self.run(sql)
            for sql in DB_INDEXES:
                if self.engine == 'mariadb':
                    try:
                        self.run(sql)
                    except Exception as e:
                        if 'Duplicate key name' in str(e):
                            continue
                        if '1064' not in str(e) and 'syntax' not in str(e).lower():
                            raise
                        try:
                            self.run(sql.replace(' IF NOT EXISTS', ''))
                        except Exception as e2:
                            if 'Duplicate key name' not in str(e2):
                                raise
                else:
                    self.run(sql)
            self._add_missing_columns()
            if self.value('SELECT v FROM meta WHERE k = ?', ('schema',)) is None:
                self.run('INSERT INTO meta (k, v) VALUES (?, ?)', ('schema', str(SCHEMA_VERSION)))
            else:
                self.run('UPDATE meta SET v = ? WHERE k = ?', (str(SCHEMA_VERSION), 'schema'))

    def _sqlite_renames(self):
        """The names of 1.0.0-1.0.5 that MariaDB keeps for itself (BY, UNTIL),
        renamed once in a file made by them."""
        for table, old, new in (('settings', 'by', 'by_who'), ('fails', 'until', 'until_ts')):
            try:
                cols = [r['name'] for r in self.rows('PRAGMA table_info(%s)' % table)]
            except sqlite3.Error:
                continue
            if old in cols and new not in cols:
                self.run('ALTER TABLE %s RENAME COLUMN "%s" TO %s' % (table, old, new))

    def tables(self):
        if self.engine == 'sqlite':
            return [r['name'] for r in self.rows(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
        if self.engine == 'mariadb':
            return [list(r.values())[0] for r in self.rows(
                'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()')]
        return [r['tablename'] for r in self.rows(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")]

    def insert_many(self, table, keys, rows):
        if not rows:
            return 0
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table, ', '.join(keys), ', '.join('?' for _ in keys))
        with self.lock:
            if self.conn is None:
                self.connect()
            if self.engine == 'sqlite' and self.in_tx:
                self.conn.executemany(sql, rows)
            elif self.engine == 'sqlite':
                self.conn.execute('BEGIN')
                try:
                    self.conn.executemany(sql, rows)
                    self.conn.execute('COMMIT')
                except Exception:
                    self.conn.execute('ROLLBACK')
                    raise
            elif self.engine == 'mariadb':
                cur = self.conn.cursor()
                try:
                    cur.executemany(_qmarks(sql), rows)
                finally:
                    cur.close()
            else:
                import psycopg2.extras
                cur = self.conn.cursor()
                try:
                    rows = [tuple(a.replace('\x00', '�') if isinstance(a, str) and '\x00' in a else a
                                  for a in r) for r in rows]
                    psycopg2.extras.execute_batch(cur, _qmarks(sql), rows, page_size=500)
                finally:
                    cur.close()
        return len(rows)

    def columns(self, table):
        if self.engine == 'sqlite':
            return [r['name'] for r in self.rows('PRAGMA table_info(%s)' % table)]
        if self.engine == 'mariadb':
            return [r.get('COLUMN_NAME') or r.get('column_name') for r in self.rows(
                'SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() '
                'AND TABLE_NAME = ?', (table,))]
        return [r['column_name'] for r in self.rows(
            'SELECT column_name FROM information_schema.columns WHERE table_name = ? '
            'AND table_schema = current_schema()', (table,))]

    def _add_missing_columns(self):
        types = DB_TYPES[self.engine]
        for name, ddl in DB_SCHEMA:
            have = set(c.lower() for c in self.columns(name))
            body = ddl.format(**types).split('(', 1)[1].rsplit(')', 1)[0]
            for piece in re.split(r',\s*(?=[a-z_]+ )', body):
                piece = piece.strip()
                col = piece.split(' ', 1)[0].lower()
                if not col or col in have or col == 'id':
                    continue
                kind = re.sub(r'\s*(NOT NULL|UNIQUE|PRIMARY KEY).*$', '', piece.split(' ', 1)[1])
                try:
                    self.run('ALTER TABLE %s ADD COLUMN %s %s' % (name, col, kind))
                except Exception as e:
                    log('could not add the column %s.%s: %s' % (name, col, e), 'warn')

    def size(self):
        try:
            if self.engine == 'sqlite':
                return sum(os.path.getsize(str(self.path) + s) for s in ('', '-wal')
                           if os.path.exists(str(self.path) + s))
            if self.engine == 'mariadb':
                return int(self.value('SELECT SUM(data_length + index_length) FROM information_schema.TABLES '
                                      'WHERE table_schema = DATABASE()') or 0)
            return int(self.value('SELECT pg_database_size(current_database())') or 0)
        except Exception:
            return 0

    def version(self):
        try:
            if self.engine == 'sqlite':
                return 'SQLite ' + sqlite3.sqlite_version
            if self.engine == 'mariadb':
                return 'MariaDB ' + str(self.value('SELECT VERSION()'))
            return str(self.value('SELECT version()')).split(' on ')[0]
        except Exception as e:
            return '? (%s)' % e


def open_db(conf=None, path=None):
    """The database the settings name."""
    c = conf or CONFIG
    return Db(c.get('db_engine') or 'sqlite', c.get('db_host') or '', c.get('db_port') or 0,
              c.get('db_name') or 'ai', c.get('db_user') or 'ai', c.get('db_password') or '',
              c.get('db_timeout_s') or 10, path=path, tls=c.get('db_tls') or '', tls_ca=c.get('db_tls_ca') or '')


# ---- a copy of everything, in a shape any of the three engines takes back ---------------------
def machine_info():
    try:
        with open(str(CONFIG_FILE), encoding='utf-8') as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raw = {}
    except (OSError, ValueError):
        raw = {}
    conf = {k: ('(set - not kept in the copy)' if 'password' in k and v else v) for k, v in sorted(raw.items())}
    return {'config_file': str(CONFIG_FILE), 'config': conf, 'host': socket.getfqdn(),
            'in_use': {k: CONFIG.get(k) for k in ('db_engine', 'db_host', 'db_port', 'db_name')}}


def dump_tables(db, out, tables=None):
    """Every row of every table, as JSON a line, gzipped. The first line says
    what it is; each table starts with a line naming it."""
    import gzip
    with gzip.open(out if hasattr(out, 'write') else str(out), 'wt', encoding='utf-8') as f:
        f.write(json.dumps({'ai': __version__, 'schema': SCHEMA_VERSION, 'made': time.time(),
                            'engine': db.engine, 'machine': machine_info()}, default=str) + '\n')
        for table in (tables or DB_TABLES):
            f.write(json.dumps({'table': table}) + '\n')
            if table not in DB_ID_TABLES:
                for r in db.rows('SELECT * FROM %s' % table):
                    f.write(json.dumps(r, default=str) + '\n')
                continue
            last = 0
            while True:
                rows = db.rows('SELECT * FROM %s WHERE id > ? ORDER BY id LIMIT 2000' % table, (last,))
                for r in rows:
                    f.write(json.dumps(r, default=str) + '\n')
                if not rows:
                    break
                last = rows[-1]['id']
    return out


META_TRANSIENT = ('db_job:', 'upgrade:')


def load_tables(db, src, say=None, keep_sessions=False):
    """A copy made by `dump_tables` put back, over whatever is there - all of
    it or none of it."""
    import gzip
    db.make_tables()
    db.restoring = True
    try:
        with db.lock:
            if db.conn is None:
                db.connect()
            db.run('START TRANSACTION' if db.engine == 'mariadb' else 'BEGIN')
            db.in_tx = True
            try:
                counts = _load_tables(db, src, say, gzip, keep_sessions)
                db.in_tx = False
                db.run('COMMIT')
            except BaseException:
                db.in_tx = False
                try:
                    db.run('ROLLBACK')
                except Exception:                       # noqa: BLE001
                    pass
                raise
        if db.engine == 'postgres':
            for table in DB_ID_TABLES:
                try:
                    db.run("SELECT setval(pg_get_serial_sequence('%s', 'id'), "
                           "COALESCE((SELECT MAX(id) FROM %s), 0) + 1, false)" % (table, table))
                except Exception:
                    pass
        return counts
    finally:
        db.restoring = False


def _load_tables(db, src, say, gzip, keep_sessions):
    counts = {}
    batch, keys, table, have = [], None, None, set()

    def flush():
        if table and batch:
            db.insert_many(table, keys, batch)
            counts[table] += len(batch)
            if say:
                say(table, counts[table])
        del batch[:]

    with gzip.open(str(src), 'rt', encoding='utf-8') as f:
        head = json.loads(f.readline() or '{}')
        if 'ai' not in head:
            raise DbError('%s is not a copy made by ai' % src)
        for line in f:
            got = json.loads(line)
            if set(got.keys()) == {'table'}:
                flush()
                keys = None
                table = got['table']
                if table not in DB_TABLES or (keep_sessions and table == 'sessions'):
                    table = None
                    continue
                if table == 'meta':
                    db.run('DELETE FROM meta WHERE ' + ' AND '.join(
                        "k NOT LIKE '%s%%'" % p.replace("'", "") for p in META_TRANSIENT))
                else:
                    db.run('DELETE FROM %s' % table)
                have = set(c.lower() for c in db.columns(table))
                counts[table] = 0
                if say:
                    say(table, 0)
                continue
            if not table:
                continue
            row = {}
            for k, v in got.items():
                k = {'by': 'by_who', 'until': 'until_ts'}.get(k, k) if table in ('settings', 'fails') else k
                if k.lower() in have:
                    row[k] = v
            if table == 'meta':
                if str(row.get('k') or '').startswith(META_TRANSIENT):
                    continue
                db.run('DELETE FROM meta WHERE k = ?', (row.get('k'),))
            these = sorted(row.keys())
            if keys is not None and these != keys:
                flush()
            keys = these
            batch.append([row[k] for k in keys])
            if len(batch) >= 1000:
                flush()
        flush()
    return counts


def sqlite_to_copy(path, out):
    """A SQLite file of ai (a copy of 1.0.4-1.0.5, or one copied off a machine)
    as a copy any engine takes."""
    db = Db('sqlite', path=path)
    try:
        dump_tables(db, out, [t for t in DB_TABLES if t in db.tables()])
    finally:
        db.close()
    return out


class Store:
    """What the rest of ai asks of the database, of whichever engine: `q` for
    rows, `one` for a row, `x` to change and say how many."""

    def __init__(self, path=None, db=None, conf=None):
        self.path = str(path or DB_FILE)
        self.lock = threading.RLock()
        self.db = db or open_db(conf or load_file_config_all(), path=self.path)
        self.db.make_tables()
        self._renamed_settings()

    def _renamed_settings(self):
        """Settings of 1.0.4-1.0.5 under the names otp gives them (1.0.6)."""
        for old, new in (('events_keep_days', 'retain_events_days'), ('db_copy_on', 'backup_daily'),
                         ('db_copy_keep', 'backup_keep'), ('db_copy_hour', 'backup_at')):
            r = self.one('SELECT v FROM settings WHERE k=?', (old,))
            if not r:
                continue
            v = r['v']
            if old == 'db_copy_hour':
                try:
                    v = json.dumps('%02d:30' % int(json.loads(v)))
                except (ValueError, TypeError):
                    v = json.dumps('03:30')
            if not self.one('SELECT k FROM settings WHERE k=?', (new,)):
                self.x('UPDATE settings SET k=?, v=? WHERE k=?', (new, v, old))
            else:
                self.x('DELETE FROM settings WHERE k=?', (old,))

    def q(self, sql, args=()):
        return self.db.rows(sql, args)

    def one(self, sql, args=()):
        return self.db.row(sql, args)

    def x(self, sql, args=()):
        return self.db.run(sql, args)

    @property
    def engine(self):
        return self.db.engine

    def counts(self):
        return {t: int(self.db.value('SELECT COUNT(*) AS n FROM %s' % t, (), 0) or 0)
                for t in DB_TABLES if t not in ('meta',)}

    def delete_older(self, table, cut):
        """Rows older than `cut`, deleted in batches (otp's)."""
        gone, batch = 0, 1000
        for _ in range(1000000):
            if self.db.engine == 'mariadb':
                n = self.db.run('DELETE FROM %s WHERE at < ? LIMIT %d' % (table, batch), (cut,))
            else:
                n = self.db.run('DELETE FROM %s WHERE id IN (SELECT id FROM %s WHERE at < ? LIMIT %d)'
                                % (table, table, batch), (cut,))
            gone += int(n or 0)
            if not n or n < batch:
                break
            time.sleep(0.05)
        return gone

    def tidy(self):
        """What has been kept long enough, deleted."""
        said = {}
        days = int(CONFIG.get('retain_events_days') or 0)
        if days > 0:
            said['events'] = self.delete_older('events', time.time() - days * 86400)
        return said

    # -- meta and settings --------------------------------------------------
    def get_meta(self, k, default=None):
        r = self.one('SELECT v FROM meta WHERE k=?', (k,))
        return r['v'] if r else default

    def set_meta(self, k, v):
        self.db.upsert('meta', 'k', {'k': k, 'v': v})

    def meta_json(self, k, default=None):
        try:
            got = json.loads(self.get_meta(k) or 'null')
        except ValueError:
            got = None
        return default if got is None else got

    def set_meta_json(self, k, v):
        self.set_meta(k, json.dumps(v, default=str))

    def settings_all(self):
        out = {}
        for r in self.q('SELECT k, v FROM settings'):
            try:
                out[r['k']] = json.loads(r['v'])
            except ValueError:
                pass
        return out

    def set_setting(self, k, v, by=''):
        self.db.upsert('settings', 'k', {'k': k, 'v': json.dumps(v), 'at': time.time(), 'by_who': by})

    def drop_setting(self, k):
        self.x('DELETE FROM settings WHERE k=?', (k,))

    # -- events -------------------------------------------------------------
    def add_event(self, kind, text, level='info', who=''):
        self.x('INSERT INTO events(at,kind,level,who,text) VALUES(?,?,?,?,?)',
               (time.time(), kind, level, who or '', str(text)[:2000]))
        log('%s: %s' % (kind, text), 'info' if level in ('info', 'good') else 'warn')

    # -- sign-ins -----------------------------------------------------------
    def session_data(self, sid):
        r = self.one('SELECT data FROM sessions WHERE id=?', (sid,))
        try:
            got = json.loads((r or {}).get('data') or '{}')
        except ValueError:
            got = {}
        return got if isinstance(got, dict) else {}

    def session_merge(self, sid, change):
        with self.lock:
            data = self.session_data(sid)
            for k, v in change.items():
                if v is None:
                    data.pop(k, None)
                else:
                    data[k] = v
            self.x('UPDATE sessions SET data=? WHERE id=?', (json.dumps(data), sid))
        return data

    def session_take(self, sid, key):
        """Takes `key` out of the sign-in's data: True for the one that took it,
        so a code sent is good once, however many ask with it at once."""
        with self.lock:
            data = self.session_data(sid)
            if key not in data:
                return False
            data.pop(key)
            self.x('UPDATE sessions SET data=? WHERE id=?', (json.dumps(data), sid))
            return True

    # -- accounts -----------------------------------------------------------
    def user(self, name):
        return self.one('SELECT * FROM users WHERE name=?', (name,))

    def users(self):
        return self.q('SELECT * FROM users ORDER BY name')


# ---------------------------------------------------------------------------
# Accounts, sign-ins, and who may do what
# ---------------------------------------------------------------------------
class Refused(Exception):
    """A request that may not be done: said to the page as it is, with a status."""

    def __init__(self, words, status=400):
        Exception.__init__(self, words)
        self.status = status


def user_view(u, full=False):
    if not u:
        return None
    try:
        prefs = json.loads(u.get('prefs') or '{}')
    except ValueError:
        prefs = {}
    try:
        roots = json.loads(u.get('roots') or '[]')
    except ValueError:
        roots = []
    out = {'name': u['name'], 'role': u['role'], 'role_words': ROLE_WORDS.get(u['role'], u['role']),
           'run_as': run_as_of(u), 'run_as_own': u.get('run_as') or '', 'roots': roots,
           'disabled': bool(u['disabled']), 'must_change': bool(u['must_change']),
           'prefs': prefs, 'note': u.get('note') or '', 'created': u.get('created'),
           'last_login': u.get('last_login'), 'last_ip': u.get('last_ip') or ''}
    return out


def run_as_of(u):
    return (u.get('run_as') if u else '') or str(CONFIG.get('default_run_as') or 'root')


def linux_user(name):
    """(pwd entry) of a Linux account, or a Refused that says what is wrong."""
    if not LINUX_NAME_RE.match(str(name or '')):
        raise Refused('%r is not a Linux account name' % name)
    try:
        return pwd.getpwnam(name)
    except KeyError:
        raise Refused('there is no Linux account %s on this machine' % name)


def linux_groups(pw):
    try:
        return sorted({g.gr_gid for g in grp.getgrall() if pw.pw_name in g.gr_mem} | {pw.pw_gid})
    except (KeyError, OSError):
        return [pw.pw_gid]


def as_user_kwargs(pw):
    """What subprocess needs to run a command as that account (the daemon is root)."""
    if os.geteuid() != 0 or pw.pw_uid == os.geteuid():
        return {}
    return {'user': pw.pw_uid, 'group': pw.pw_gid, 'extra_groups': linux_groups(pw)}


def user_env(pw, extra=None):
    env = {
        'HOME': pw.pw_dir, 'USER': pw.pw_name, 'LOGNAME': pw.pw_name,
        'SHELL': pw.pw_shell or '/bin/bash',
        'PATH': ':'.join([pw.pw_dir + '/.local/bin', pw.pw_dir + '/.claude/local',
                          '/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin', '/sbin',
                          '/bin']),
        'LANG': str(CONFIG.get('term_lang') or 'C.UTF-8'),
        'TERM': 'xterm-256color', 'COLORTERM': 'truecolor',
    }
    for k in ('https_proxy', 'http_proxy', 'no_proxy', 'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY', 'TZ'):
        if os.environ.get(k):
            env[k] = os.environ[k]
    if extra:
        env.update(extra)
    return env


def env_lines(text):
    out = {}
    for line in str(text or '').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        if k.startswith('export '):
            k = k[7:].strip()
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]{0,127}\Z', k):
            out[k] = v.strip().strip('"').strip("'") if len(v.strip()) > 1 and \
                v.strip()[0] == v.strip()[-1] and v.strip()[0] in '"\'' else v.strip()
    return out


def roots_of(u):
    """Where an account may read and write files: anywhere for an administrator;
    for a user, its own folders, or the home of the account it runs as."""
    if u['role'] == 'admin':
        return ['/']
    try:
        roots = [r for r in json.loads(u.get('roots') or '[]') if isinstance(r, str) and r.startswith('/')]
    except ValueError:
        roots = []
    if not roots:
        try:
            roots = [linux_user(run_as_of(u)).pw_dir]
        except Refused:
            roots = []
    return [os.path.realpath(r) for r in roots]


def path_allowed(u, path):
    real = os.path.realpath(path)
    for r in roots_of(u):
        if r == '/' or real == r or real.startswith(r.rstrip('/') + '/'):
            return real
    raise Refused('%s is outside the folders this account may use' % path, 403)


class Auth:
    def __init__(self, store):
        self.store = store

    # -- the accounts -------------------------------------------------------
    def add_user(self, name, password, role='user', run_as='', roots=None, must_change=False,
                 note='', by=''):
        name = str(name or '').strip()
        if not NAME_RE.match(name):
            raise Refused('a name of letters, digits and . _ @ - (up to 64)')
        if role not in ROLES:
            raise Refused('the role is admin or user')
        if self.store.user(name):
            raise Refused('there is an account called %s already' % name)
        why = password_problem(password, name)
        if why:
            raise Refused('the password: %s' % why)
        if run_as:
            linux_user(run_as)
        self.store.x('INSERT INTO users(name,pw,role,run_as,roots,must_change,note,created) '
                     'VALUES(?,?,?,?,?,?,?,?)',
                     (name, hash_password(password), role, run_as or '',
                      json.dumps(clean_roots(roots or [])), 1 if must_change else 0,
                      clean_line(note, 300), time.time()))
        self.store.add_event('accounts', '%s made the account %s (%s%s)' % (
            by or 'the command line', name, ROLE_WORDS[role],
            ', runs as %s' % run_as if run_as else ''), 'info', who=by)

    def edit_user(self, name, by, role=None, run_as=None, roots=None, disabled=None, note=None):
        u = self.store.user(name)
        if not u:
            raise Refused('no such account', 404)
        sets, args, said = [], [], []
        if role is not None:
            if role not in ROLES:
                raise Refused('the role is admin or user')
            if u['role'] == 'admin' and role != 'admin' and self.admins_left(name) == 0:
                raise Refused('this is the last administrator: make another one first')
            sets.append('role=?'); args.append(role); said.append(ROLE_WORDS[role])
        if run_as is not None:
            run_as = str(run_as).strip()
            if run_as:
                linux_user(run_as)
            sets.append('run_as=?'); args.append(run_as)
            said.append('runs as %s' % (run_as or 'the default'))
        if roots is not None:
            sets.append('roots=?'); args.append(json.dumps(clean_roots(roots)))
            said.append('folders %s' % (', '.join(clean_roots(roots)) or 'its home'))
        if disabled is not None:
            if disabled and u['role'] == 'admin' and self.admins_left(name) == 0:
                raise Refused('this is the last administrator: make another one first')
            sets.append('disabled=?'); args.append(1 if disabled else 0)
            said.append('switched off' if disabled else 'switched on')
            if disabled:
                self.store.x('DELETE FROM sessions WHERE name=?', (name,))
        if note is not None:
            sets.append('note=?'); args.append(clean_line(note, 300))
        if not sets:
            return
        args.append(name)
        self.store.x('UPDATE users SET %s WHERE name=?' % ', '.join(sets), args)
        if said:
            self.store.add_event('accounts', '%s changed the account %s: %s' % (by, name, '; '.join(said)),
                                 'info', who=by)

    def admins_left(self, but):
        return len([u for u in self.store.users() if u['role'] == 'admin' and not u['disabled']
                    and u['name'] != but])

    def drop_user(self, name, by):
        u = self.store.user(name)
        if not u:
            raise Refused('no such account', 404)
        if u['role'] == 'admin' and self.admins_left(name) == 0:
            raise Refused('this is the last administrator: make another one first')
        self.store.x('DELETE FROM users WHERE name=?', (name,))
        self.store.x('DELETE FROM sessions WHERE name=?', (name,))
        self.store.add_event('accounts', '%s took the account %s away (its terminals go on '
                             'running)' % (by, name), 'warn', who=by)

    def set_password(self, name, password, by, must_change=False):
        u = self.store.user(name)
        if not u:
            raise Refused('no such account', 404)
        why = password_problem(password, name)
        if why:
            raise Refused('the password: %s' % why)
        self.store.x('UPDATE users SET pw=?, must_change=? WHERE name=?',
                     (hash_password(password), 1 if must_change else 0, name))
        self.store.add_event('accounts', '%s set a new password for %s' % (by, name)
                             if by != name else '%s changed their password' % name, 'info', who=by)

    # -- signing in ---------------------------------------------------------
    def _fail_keys(self, name, ip):
        return ['ip:' + str(ip or '?'), 'name:' + str(name or '').lower()]

    def locked(self, name, ip):
        now = time.time()
        for k in self._fail_keys(name, ip):
            r = self.store.one('SELECT * FROM fails WHERE k=?', (k,))
            if r and r['until_ts'] and r['until_ts'] > now:
                return int(r['until_ts'] - now)
        return 0

    def failed(self, name, ip):
        now = time.time()
        most = int(CONFIG.get('login_max_fails') or 8)
        pause = int(CONFIG.get('login_lock_min') or 15) * 60
        for k in self._fail_keys(name, ip):
            r = self.store.one('SELECT * FROM fails WHERE k=?', (k,))
            if not r or now - (r['first'] or 0) > pause:
                n, first = 1, now
            else:
                n, first = r['n'] + 1, r['first']
            until = now + pause if n >= most else 0
            self.store.db.upsert('fails', 'k', {'k': k, 'n': n, 'first': first, 'until_ts': until})

    def login(self, name, password, ip, agent=''):
        name = str(name or '').strip()
        wait = self.locked(name, ip)
        if wait:
            raise Refused('too many wrong passwords - try again in %d min' % max(1, wait // 60 + 1), 429)
        u = self.store.user(name)
        # The hash is worked out for a name nobody has too: a missing account
        # takes as long to refuse as a wrong password.
        ok = check_password(password, u['pw'] if u else hash_password('x'))
        if not u or not ok or u['disabled']:
            self.failed(name, ip)
            self.store.add_event('sign-in', 'a sign-in as %s from %s was refused (%s)' % (
                clean_line(name, 64) or '?', ip, 'switched off' if u and ok else 'wrong name or password'),
                'warn', who=name)
            raise Refused('wrong name or password', 401)
        for k in self._fail_keys(name, ip):
            self.store.x('DELETE FROM fails WHERE k=?', (k,))
        # With the second step on, the password opens a sign-in that can do
        # nothing but give it (MFA_ALLOWED) - as otp's administration.
        stage = mfa_stage(self.store, name) if CONFIG.get('admin_2fa') else ''
        token = self.session_new(name, ip, agent, {'mfa': stage} if stage else {})
        self.store.x('UPDATE users SET last_login=?, last_ip=? WHERE name=?', (time.time(), ip, name))
        self.store.add_event('sign-in', '%s signed in from %s%s' % (
            name, ip, ' - the second step still to give' if stage else ''), 'info', who=name)
        return token

    def session_new(self, name, ip, agent='', data=None, created=None):
        token = secrets.token_urlsafe(32)
        self.store.x('INSERT INTO sessions(id,name,created,seen,ip,agent,data) VALUES(?,?,?,?,?,?,?)',
                     (self.sid(token), name, created or time.time(), time.time(), ip,
                      clean_line(agent, 200), json.dumps(data or {})))
        return token

    @staticmethod
    def sid(token):
        return hashlib.sha256(str(token).encode('utf-8')).hexdigest()

    def who(self, token, touch=True):
        """The account a session token belongs to, or None."""
        if not token or not re.match(r'^[A-Za-z0-9_-]{16,128}\Z', str(token)):
            return None
        s = self.store.one('SELECT * FROM sessions WHERE id=?', (self.sid(token),))
        if not s:
            return None
        now = time.time()
        if now - (s['seen'] or 0) > float(CONFIG.get('session_idle_h') or 12) * 3600 or \
                now - (s['created'] or 0) > float(CONFIG.get('session_max_h') or 168) * 3600:
            self.store.x('DELETE FROM sessions WHERE id=?', (s['id'],))
            return None
        u = self.store.user(s['name'])
        if not u or u['disabled']:
            return None
        if touch and now - (s['seen'] or 0) > 30:
            self.store.x('UPDATE sessions SET seen=? WHERE id=?', (now, s['id']))
        u = dict(u)
        u['_sid'] = s['id']
        u['_created'] = s['created']
        u['_agent'] = s.get('agent') or ''
        try:
            data = json.loads(s.get('data') or '{}')
        except ValueError:
            data = {}
        u['_data'] = data if isinstance(data, dict) else {}
        u['_mfa'] = str(u['_data'].get('mfa') or '') if CONFIG.get('admin_2fa') else ''
        return u

    def logout(self, token):
        self.store.x('DELETE FROM sessions WHERE id=?', (self.sid(token),))

    def tidy(self):
        now = time.time()
        idle = float(CONFIG.get('session_idle_h') or 12) * 3600
        most = float(CONFIG.get('session_max_h') or 168) * 3600
        self.store.x('DELETE FROM sessions WHERE seen < ? OR created < ?', (now - idle, now - most))
        # A password given and its second step not, for a quarter of an hour: gone.
        self.store.x('DELETE FROM sessions WHERE data LIKE ? AND created < ?', ('%"mfa": "%', now - 900))
        self.store.x('DELETE FROM fails WHERE (until_ts = 0 OR until_ts < ?) AND first < ?',
                     (now, now - 86400))


def clean_roots(roots):
    if isinstance(roots, str):
        roots = re.split(r'[\n,]+', roots)
    out = []
    for r in roots or []:
        r = str(r).strip()
        if not r:
            continue
        if not r.startswith('/') or '\x00' in r or len(r) > 1024:
            raise Refused('a folder is a full path: %s' % r[:80])
        out.append(os.path.normpath(r))
    return out[:50]


# ---------------------------------------------------------------------------
# The terminals: tmux on the server, one server per Linux account
# ---------------------------------------------------------------------------
# Every terminal is a tmux session of its own, on a tmux server that runs as
# the Linux account the terminal is for, with its socket in
# /var/lib/ai/tmux/<account>/. The first one is started in a systemd scope of
# its own, outside ai.service: restarting the service, or upgrading it, ends
# no terminal. The pages attach a tmux client in a pseudo-terminal of the
# daemon's for every browser window looking at one, and closing the window
# ends that client only.
TERM_ID_RE = re.compile(r'^[a-f0-9]{8}\Z')
TMUX_FIELDS = ['session_name', 'session_created', 'session_attached', 'session_activity',
               'pane_dead', 'pane_dead_status', 'pane_current_path', 'pane_current_command',
               'pane_pid', 'window_width', 'window_height', 'pane_title']


def tmux_bin():
    return which('tmux') or 'tmux'


def tmux_conf():
    for p in (LIB_DIR / 'tmux.conf', HERE / 'deploy' / 'tmux.conf'):
        if p.is_file():
            return str(p)
    return '/dev/null'


# Claude Code's options a new chat may be started with (1.0.9): the name the
# page sends, the option, and what it takes. Nothing else of the page's goes
# onto the command line but the free words, which are the account's own.
CC_OPTIONS = [
    ('name', '--name', 'str'), ('effort', '--effort', ('low', 'medium', 'high', 'xhigh', 'max')),
    ('fallback_model', '--fallback-model', 'str'),
    ('allowed_tools', '--allowedTools', 'words'), ('disallowed_tools', '--disallowedTools', 'words'),
    ('tools', '--tools', 'str'), ('append_system_prompt', '--append-system-prompt', 'text'),
    ('system_prompt', '--system-prompt', 'text'), ('agent', '--agent', 'str'),
    ('mcp_config', '--mcp-config', 'words'), ('strict_mcp', '--strict-mcp-config', 'flag'),
    ('settings', '--settings', 'str'), ('setting_sources', '--setting-sources', 'str'),
    ('plugin_dirs', '--plugin-dir', 'each'), ('worktree', '--worktree', 'maybe'),
    ('autocompact', '--autocompact', 'str'), ('fork', '--fork-session', 'flag'),
    ('session_id', '--session-id', 'uuid'), ('verbose', '--verbose', 'flag'), ('debug', '--debug', 'maybe'),
    ('safe_mode', '--safe-mode', 'flag'), ('bare', '--bare', 'flag'), ('restricted', '--restricted', 'flag'),
    ('chrome', '--chrome', 'flag'), ('no_chrome', '--no-chrome', 'flag'), ('ide', '--ide', 'flag'),
    ('brief', '--brief', 'flag'), ('no_slash', '--disable-slash-commands', 'flag'),
    ('screen_reader', '--ax-screen-reader', 'flag'), ('remote_control', '--remote-control', 'maybe'),
    ('allow_skip', '--allow-dangerously-skip-permissions', 'flag'),
    ('exclude_dynamic', '--exclude-dynamic-system-prompt-sections', 'flag'),
]


def cc_option_args(opts):
    out = []
    for key, flag, kind in CC_OPTIONS:
        v = opts.get(key)
        if v in (None, '', False, []):
            continue
        if kind == 'flag':
            out.append(flag)
        elif kind == 'maybe':
            out.append(flag if v is True or str(v).strip() in ('', '1', 'true') else '%s=%s' % (flag, str(v).strip()))
        elif kind in ('words', 'each'):
            items = v if isinstance(v, list) else [x for x in re.split(r'[\n,]+', str(v)) if x.strip()]
            items = [str(x).strip() for x in items if str(x).strip()]
            if not items:
                continue
            if kind == 'each':
                for x in items:
                    out += [flag, x]
            else:
                out += [flag] + items
        elif kind == 'uuid':
            if not re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z', str(v)):
                raise Refused('a session ID is a UUID')
            out += [flag, str(v)]
        elif isinstance(kind, tuple):
            if str(v) not in kind:
                raise Refused('%s is one of %s' % (flag, ', '.join(kind)))
            out += [flag, str(v)]
        else:
            out += [flag, str(v)]
    return out


class Terms:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.cache = {'at': 0.0, 'live': {}}

    # -- one tmux server per account ------------------------------------------
    def sock_dir(self, pw):
        TMUX_DIR.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(str(TMUX_DIR), 0o711)
        except OSError:
            pass
        d = TMUX_DIR / pw.pw_name
        if not d.is_dir():
            d.mkdir(mode=0o700)
        st = os.lstat(str(d))
        if stat.S_ISLNK(st.st_mode):
            raise Refused('%s is a link - refused' % d)
        if os.geteuid() == 0 and (st.st_uid != pw.pw_uid or st.st_mode & 0o077):
            os.chown(str(d), pw.pw_uid, pw.pw_gid)
            os.chmod(str(d), 0o700)
        return d

    def sock(self, pw):
        return str(self.sock_dir(pw) / 'sock')

    def tmux(self, pw, args, timeout=20, input=None):
        cmd = [tmux_bin(), '-u', '-S', self.sock(pw), '-f', tmux_conf()] + list(args)
        try:
            got = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=input,
                                 env=user_env(pw), cwd=pw.pw_dir if os.path.isdir(pw.pw_dir) else '/',
                                 **as_user_kwargs(pw))
        except FileNotFoundError:
            raise Refused('tmux is not installed on this server (dnf install tmux / apt install tmux)', 500)
        except subprocess.TimeoutExpired:
            raise Refused('tmux did not answer in %d s' % timeout, 500)
        return got.returncode, got.stdout, got.stderr

    def server_up(self, pw):
        if not os.path.exists(str(TMUX_DIR / pw.pw_name / 'sock')):
            return False
        rc, _o, _e = self.tmux(pw, ['list-sessions'], timeout=10)
        return rc == 0

    def accounts(self):
        """The Linux accounts with a tmux server folder here."""
        out = []
        try:
            names = sorted(os.listdir(str(TMUX_DIR)))
        except OSError:
            return out
        for n in names:
            try:
                out.append(pwd.getpwnam(n))
            except KeyError:
                pass
        return out

    # -- what is running ------------------------------------------------------
    def live(self, fresh=False):
        """{id: {...tmux facts...}} for every terminal running, on every account."""
        with self.lock:
            if not fresh and time.time() - self.cache['at'] < 1.5:
                return self.cache['live']
            out = {}
            fmt = '\t'.join('#{%s}' % f for f in TMUX_FIELDS)
            for pw in self.accounts():
                if not os.path.exists(str(TMUX_DIR / pw.pw_name / 'sock')):
                    continue
                try:
                    rc, so, _se = self.tmux(pw, ['list-panes', '-a', '-F', fmt], timeout=10)
                except Refused:
                    continue
                if rc != 0:
                    continue
                for line in so.splitlines():
                    bits = line.split('\t')
                    if len(bits) != len(TMUX_FIELDS):
                        continue
                    f = dict(zip(TMUX_FIELDS, bits))
                    m = re.match(r'^ai-([a-f0-9]{8})$', f['session_name'])
                    if not m or m.group(1) in out:
                        continue
                    out[m.group(1)] = {
                        'run_as': pw.pw_name, 'tmux': f['session_name'],
                        'started': int(f['session_created'] or 0),
                        'viewers': int(f['session_attached'] or 0),
                        'activity': int(f['session_activity'] or 0),
                        'dead': f['pane_dead'] == '1',
                        'exit_status': int(f['pane_dead_status']) if f['pane_dead_status'].isdigit() else None,
                        'path': f['pane_current_path'], 'command': f['pane_current_command'],
                        'pid': int(f['pane_pid'] or 0) if f['pane_pid'].isdigit() else 0,
                        'cols': int(f['window_width'] or 0), 'rows': int(f['window_height'] or 0),
                        'pane_title': f['pane_title'],
                    }
            self.cache = {'at': time.time(), 'live': out}
            return out

    def row(self, tid):
        if not TERM_ID_RE.match(str(tid or '')):
            raise Refused('no such terminal', 404)
        r = self.store.one('SELECT * FROM terms WHERE id=?', (tid,))
        if not r:
            raise Refused('no such terminal', 404)
        return r

    def may(self, u, r):
        if u['role'] == 'admin' or r['owner'] == u['name']:
            return True
        raise Refused('that terminal is somebody else\'s', 403)

    def view(self, r, live):
        lv = live.get(r['id'])
        try:
            opts = json.loads(r['opts'] or '{}')
        except ValueError:
            opts = {}
        state = 'ended' if not lv else ('exited' if lv['dead'] else 'running')
        return {'id': r['id'], 'owner': r['owner'], 'run_as': r['run_as'], 'title': r['title'],
                'kind': r['kind'], 'cwd': r['cwd'], 'created': r['created'], 'ended': r['ended'],
                'state': state, 'viewers': lv['viewers'] if lv else 0,
                'activity': lv['activity'] if lv else (r['ended'] or r['created']),
                'path': lv['path'] if lv else r['cwd'], 'command': lv['command'] if lv else '',
                'exit_status': lv['exit_status'] if lv else r['exit_status'],
                'cols': lv['cols'] if lv else 0, 'rows': lv['rows'] if lv else 0,
                'pane_title': lv['pane_title'] if lv else '',
                'opts': {k: opts.get(k) for k in ('model', 'mode', 'resume', 'continue', 'args',
                                                  'command') if opts.get(k)}}

    def merge(self, live):
        """One tile a conversation (1.0.17): before 1.0.16 picking one up again
        started a new terminal each time, and the ended ones stayed in the list
        beside the one running it. Of the terminals holding one conversation,
        the running one - else the newest - is kept, the ended rest forgotten."""
        if time.time() - self.cache.get('merged', 0) < 60:
            return
        self.cache['merged'] = time.time()
        rows = self.store.q("SELECT * FROM terms WHERE kind='claude' ORDER BY created DESC")
        held = {}
        for r in rows:
            try:
                o = json.loads(r['opts'] or '{}')
            except ValueError:
                o = {}
            # An ended one by the conversation it was started with only - never
            # by a guess from the times, which may name another's.
            sid = str(o.get('sid') or (o.get('resume') if UUID_RE.match(str(o.get('resume') or '')) else '') or '')
            if r['id'] in live:
                try:
                    sid = self.claude_sid(r, others=set()) or sid
                except Exception:                   # noqa: BLE001 - a home that cannot be read
                    pass
            if sid:
                held.setdefault((r['run_as'], sid), []).append(r)
        for key, group in held.items():
            if len(group) < 2:
                continue
            keep = next((r for r in group if r['id'] in live), group[0])
            for r in group:
                if r is keep or r['id'] in live:
                    continue
                self.store.x('DELETE FROM terms WHERE id=?', (r['id'],))
                log('the terminal %s merged into %s: both held the conversation %s' % (r['id'], keep['id'], key[1][:8]))

    def list(self, u, ended=True):
        live = self.live()
        self.sync(live)
        try:
            self.merge(live)
        except Exception as e:                      # noqa: BLE001 - never in the way of the list
            log('merging the terminals of one conversation: %s' % e, 'warn')
        rows = self.store.q('SELECT * FROM terms ORDER BY created DESC')
        out = []
        for r in rows:
            if u['role'] != 'admin' and r['owner'] != u['name']:
                continue
            v = self.view(r, live)
            if v['state'] == 'ended' and not ended:
                continue
            out.append(v)
        return out

    def sync(self, live=None):
        """Terminals that ended are marked so, with their last screen kept;
        ones started by hand on our sockets (ai --new) are taken in."""
        live = self.live() if live is None else live
        known = {r['id']: r for r in self.store.q('SELECT * FROM terms')}
        for tid, lv in live.items():
            if tid not in known:
                self.store.x('INSERT INTO terms(id,owner,run_as,title,kind,cwd,created) VALUES(?,?,?,?,?,?,?)',
                             (tid, '', lv['run_as'], 'terminal ' + tid, 'shell', lv['path'],
                              lv['started'] or time.time()))
            elif known[tid]['ended']:
                self.store.x('UPDATE terms SET ended=NULL WHERE id=?', (tid,))
        for tid, r in known.items():
            if tid not in live and not r['ended']:
                self.store.x('UPDATE terms SET ended=? WHERE id=?', (time.time(), tid))
        keep = float(CONFIG.get('ended_keep_days') or 14) * 86400
        self.store.x('DELETE FROM terms WHERE ended IS NOT NULL AND ended < ?', (time.time() - keep,))

    # -- starting one -------------------------------------------------------------
    def claude_script(self, opts):
        """The shell words a Claude Code terminal runs: Claude Code with what was
        chosen, and a shell instead (saying why) when it is not installed."""
        cmd = str(CONFIG.get('claude_cmd') or 'claude').strip() or 'claude'
        args = []
        if opts.get('attach'):
            # A session Claude Code runs in the background, opened here.
            if not re.match(r'^[A-Za-z0-9_.-]{1,80}\Z', str(opts['attach'])):
                raise Refused('which background session?')
            return 'exec %s attach %s' % (shlex.quote(cmd), shlex.quote(str(opts['attach'])))
        if opts.get('resume'):
            args += ['--resume', str(opts['resume'])]
        elif opts.get('pick'):
            args += ['--resume']
        elif opts.get('continue'):
            args += ['--continue']
        if opts.get('model'):
            args += ['--model', str(opts['model'])]
        if opts.get('mode'):
            args += ['--permission-mode', str(opts['mode'])]
        for d in opts.get('add_dirs') or []:
            args += ['--add-dir', str(d)]
        args += cc_option_args(opts)
        try:
            args += shlex.split(str(CONFIG.get('claude_args') or ''))
            args += shlex.split(str(opts.get('args') or ''))
        except ValueError as e:
            raise Refused('the words to start Claude Code with: %s' % e)
        if str(opts.get('prompt') or '').strip():
            # The first message, after every option (a value of -w or --debug
            # may not swallow it).
            args += ['--', str(opts['prompt']).strip()]
        q = ' '.join(shlex.quote(a) for a in args)
        exe = shlex.quote(cmd)
        # Its history in tmux's (1.0.14): the full-screen look keeps it to
        # itself, where neither the scroll bar nor History can reach it.
        look = 'export CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1; ' if CONFIG.get('claude_classic', True) else ''
        return (look + 'if ! command -v %s >/dev/null 2>&1; then '
                'printf "\\n  Claude Code (%s) is not installed for %%s on this server.\\n'
                '  Install it from Settings - Claude Code, or here:\\n'
                '    curl -fsSL https://claude.ai/install.sh | bash\\n\\n" "$(id -un)"; '
                'exec "${SHELL:-/bin/bash}" -l; fi; exec %s %s' % (exe, cmd.replace('"', ''), exe, q))

    def new(self, u, kind='claude', cwd='', title='', opts=None, cols=160, rows=48, run_as=None, tid=None):
        """A terminal started - a new one, or (`tid`) an ended one of the list
        started again in its own place: its row, its name, its pin."""
        opts = dict(opts or {})
        if kind not in ('claude', 'shell', 'command'):
            raise Refused('a terminal is claude, shell or command')
        if kind == 'command' and u['role'] != 'admin':
            raise Refused('only an administrator starts a command', 403)
        who_as = run_as if (run_as and u['role'] == 'admin') else run_as_of(u)
        pw = linux_user(who_as)
        root = chat_root_of(pw)
        cwd = str(cwd or CONFIG.get('default_cwd') or root or pw.pw_dir).strip()
        if cwd.startswith('~'):
            cwd = pw.pw_dir + cwd[1:]
        if not cwd.startswith('/'):
            cwd = os.path.join(root or pw.pw_dir, cwd)
        cwd = os.path.normpath(cwd)
        path_allowed(u, cwd)
        if root and not path_under(cwd, root):
            raise Refused('a chat starts in %s or a folder under it (Settings - Claude Code - The folder '
                          'of the chats), not in %s' % (root, cwd))
        if not os.path.isdir(cwd):
            if opts.get('mkdir'):
                os.makedirs(cwd, exist_ok=True)
                if os.geteuid() == 0:
                    os.chown(cwd, pw.pw_uid, pw.pw_gid)
            else:
                raise Refused('%s is not a folder on this server' % cwd)
        revive = bool(tid)
        tid = tid or secrets.token_hex(4)
        name = 'ai-' + tid
        # Which conversation of Claude Code it holds (1.0.16): a new one is
        # given its ID here (--session-id), so that the chat is found again -
        # picked up, started again - in this terminal and not in a new one.
        sid = ''
        if kind == 'claude' and not opts.get('attach'):
            if opts.get('resume') and not opts.get('fork') and UUID_RE.match(str(opts['resume'])):
                sid = str(opts['resume'])
            elif opts.get('session_id'):
                sid = str(opts['session_id'])
            elif not any(opts.get(k) for k in ('resume', 'continue', 'pick', 'fork')):
                sid = str(uuid.uuid4())
                opts['session_id'] = sid
        if revive:
            # Whatever is left of it in tmux (a pane that ended, still shown) goes first.
            self.tmux(pw, ['kill-session', '-t', name])
        env = env_lines(CONFIG.get('claude_env'))
        env.update({'AI_TERMINAL': tid, 'LANG': str(CONFIG.get('term_lang') or 'C.UTF-8')})
        shell = pw.pw_shell if pw.pw_shell and os.path.exists(pw.pw_shell) and \
            not pw.pw_shell.endswith(('nologin', 'false')) else '/bin/bash'
        if kind == 'claude':
            argv = [shell, '-lc', self.claude_script(opts)]
            title = title or 'Claude · %s' % (os.path.basename(cwd.rstrip('/')) or '/')
        elif kind == 'shell':
            argv = [shell, '-l']
            title = title or 'shell · %s' % (os.path.basename(cwd.rstrip('/')) or '/')
        else:
            argv = [shell, '-lc', str(opts.get('command') or 'true')]
            title = title or clean_line(opts.get('command'), 60)
        cols = max(40, min(500, int(cols or 160)))
        rows = max(10, min(200, int(rows or 48)))
        args = ['new-session', '-d', '-s', name, '-x', str(cols), '-y', str(rows), '-c', cwd]
        for k, v in env.items():
            args += ['-e', '%s=%s' % (k, v)]
        args += ['--'] + argv
        with self.lock:
            if self.server_up(pw):
                rc, so, se = self.tmux(pw, args)
            else:
                rc, so, se = self.first(pw, args)
            if rc != 0:
                raise Refused('tmux would not start it: %s' % (se or so).strip()[:300], 500)
            self.cache['at'] = 0
        keep = {k: v for k, v in opts.items() if k in ('model', 'mode', 'resume', 'continue', 'pick',
                                                       'args', 'command', 'add_dirs')}
        if sid:
            keep['sid'] = sid
        if revive:
            self.store.x('UPDATE terms SET ended=NULL, last_screen=NULL, exit_status=NULL, cwd=?, opts=?, '
                         'title=? WHERE id=?', (cwd, json.dumps(keep), clean_line(title, 120), tid))
            self.store.add_event('terminals', '%s started "%s" again%s' % (
                u['name'], clean_line(title, 120), ' - its conversation %s' % opts['resume'][:8]
                if opts.get('resume') else ''), 'info', who=u['name'])
            return tid
        self.store.x('INSERT INTO terms(id,owner,run_as,title,kind,cwd,opts,created) VALUES(?,?,?,?,?,?,?,?)',
                     (tid, u['name'], pw.pw_name, clean_line(title, 120), kind, cwd, json.dumps(keep),
                      time.time()))
        self.store.add_event('terminals', '%s started %s "%s" as %s in %s' % (
            u['name'], {'claude': 'Claude Code', 'shell': 'a shell', 'command': 'a command'}[kind],
            clean_line(title, 120), pw.pw_name, cwd), 'info', who=u['name'])
        return tid

    def first(self, pw, args):
        """The first terminal of an account: its tmux server started in a systemd
        scope of its own, so that it outlives ai.service."""
        base = [tmux_bin(), '-u', '-S', self.sock(pw), '-f', tmux_conf()] + args
        env = user_env(pw)
        cwd = pw.pw_dir if os.path.isdir(pw.pw_dir) else '/'
        if os.geteuid() == 0 and systemd_here():
            cmd = ['systemd-run', '--scope', '--quiet', '--collect',
                   '--unit', 'ai-tmux-%s-%s' % (re.sub(r'[^a-z0-9_-]', '', pw.pw_name), secrets.token_hex(3)),
                   '--description', 'ai: the terminals of %s' % pw.pw_name]
            if pw.pw_uid != 0:
                cmd += ['--uid', str(pw.pw_uid), '--gid', str(pw.pw_gid)]
            cmd += ['--'] + base
            try:
                got = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env, cwd=cwd)
                if got.returncode == 0:
                    return got.returncode, got.stdout, got.stderr
                log('systemd-run would not start the tmux server of %s (%s); started directly' % (
                    pw.pw_name, (got.stderr or got.stdout).strip()[:200]), 'warn')
            except (OSError, subprocess.SubprocessError) as e:
                log('systemd-run: %s; the tmux server is started directly' % e, 'warn')
        got = subprocess.run(base, capture_output=True, text=True, timeout=30, env=env, cwd=cwd,
                             start_new_session=True, **as_user_kwargs(pw))
        return got.returncode, got.stdout, got.stderr

    # -- doing things to one --------------------------------------------------------
    def pw_of(self, r):
        return linux_user(r['run_as'])

    def capture(self, r, lines=40, escapes=False):
        pw = self.pw_of(r)
        args = ['capture-pane', '-p', '-J', '-t', 'ai-' + r['id'], '-S', '-' if lines == 'all' else str(-int(lines))]
        if escapes:
            args.insert(2, '-e')
        rc, so, se = self.tmux(pw, args, timeout=10)
        if rc != 0:
            return r.get('last_screen') or ''
        return so

    def send(self, r, text, enter=False, paste=True):
        pw = self.pw_of(r)
        target = 'ai-' + r['id']
        text = str(text or '')
        if text:
            if paste:
                buf = 'aiput' + secrets.token_hex(3)
                rc, so, se = self.tmux(pw, ['load-buffer', '-b', buf, '-'], input=text)
                if rc != 0:
                    raise Refused('tmux: %s' % (se or so).strip()[:200], 500)
                rc, so, se = self.tmux(pw, ['paste-buffer', '-p', '-d', '-b', buf, '-t', target])
            else:
                rc, so, se = self.tmux(pw, ['send-keys', '-t', target, '-l', '--', text])
            if rc != 0:
                raise Refused('tmux: %s' % (se or so).strip()[:200], 500)
        if enter:
            if text:
                time.sleep(0.15)
            self.tmux(pw, ['send-keys', '-t', target, 'Enter'])

    def keys(self, r, names):
        pw = self.pw_of(r)
        ok = [k for k in names if re.match(r'^(C-|M-|S-)*([A-Za-z0-9]|Enter|Escape|Tab|BTab|Up|Down|'
                                           r'Left|Right|Home|End|PageUp|PageDown|BSpace|DC|F\d{1,2}|Space)\Z', k)]
        if ok:
            self.tmux(pw, ['send-keys', '-t', 'ai-' + r['id']] + ok)

    def kill(self, u, r):
        pw = self.pw_of(r)
        try:
            screen = self.capture(r, 200)
        except Refused:
            screen = ''
        self.tmux(pw, ['kill-session', '-t', 'ai-' + r['id']])
        self.store.x('UPDATE terms SET ended=?, last_screen=? WHERE id=?', (time.time(), screen[-60000:], r['id']))
        self.cache['at'] = 0
        self.store.add_event('terminals', '%s ended the terminal "%s" (%s)' % (u['name'], r['title'], r['run_as']),
                             'info', who=u['name'])

    def restart(self, u, r):
        """Started again where it is. A chat with Claude Code goes on with its
        own conversation (1.0.16) - run again as it was, a new chat began a new,
        empty one each time, or failed on its session ID."""
        if r['kind'] == 'claude':
            return self.again(u, r)
        pw = self.pw_of(r)
        rc, so, se = self.tmux(pw, ['respawn-pane', '-k', '-t', 'ai-' + r['id']])
        if rc != 0:
            raise Refused('tmux: %s' % (se or so).strip()[:200], 500)
        self.cache['at'] = 0
        self.store.add_event('terminals', '%s started the terminal "%s" again' % (u['name'], r['title']),
                             'info', who=u['name'])
        return r['id']

    def claude_sid(self, r, others=None):
        """The conversation of Claude Code a terminal holds (1.0.16): the one it
        was started with - or, when another of its folder was written later
        while it ran and no other terminal holds that one, that one (a /clear
        or a /resume inside it moves on to another)."""
        try:
            opts = json.loads(r.get('opts') or '{}')
        except ValueError:
            opts = {}
        own = str(opts.get('sid') or (opts.get('resume') if UUID_RE.match(str(opts.get('resume') or '')) else '') or '')
        if r.get('kind') != 'claude':
            return own
        # Ended, it holds what it held: its transcript may well have been
        # written since - by the terminal that took the conversation over.
        if r.get('ended') and own:
            return own
        try:
            pw = self.pw_of(r)
        except Refused:
            return own
        if others is None:
            others = set()
            for x in self.store.q("SELECT id, opts FROM terms WHERE kind='claude' AND run_as=?", (r['run_as'],)):
                if x['id'] == r['id']:
                    continue
                try:
                    o = json.loads(x['opts'] or '{}').get('sid')
                except ValueError:
                    o = None
                if o:
                    others.add(o)
        start = float(r.get('created') or 0) - 5
        end = (float(r.get('ended') or 0) or time.time()) + 120
        for it in conversations(pw, r.get('cwd') or '', most=80):
            if it['id'] in others or not (start <= it['mtime'] <= end):
                continue
            return it['id']
        return own

    def again(self, u, r, sid=None, extra=None):
        """An ended terminal started afresh in its own place - its row, its
        name, its pin - with the same kind, folder and choices. A chat goes on
        with its own conversation (`sid`, or the one it held)."""
        try:
            opts = json.loads(r['opts'] or '{}')
        except ValueError:
            opts = {}
        for k in ('resume', 'continue', 'pick', 'sid', 'session_id'):
            opts.pop(k, None)
        opts.update(extra or {})
        if r['kind'] == 'claude':
            sid = sid or self.claude_sid(r)
            if sid:
                opts['resume'] = sid
            else:
                opts['continue'] = True
        return self.new(u, r['kind'] or 'shell', r['cwd'], r['title'], opts,
                        run_as=r['run_as'] if u['role'] == 'admin' else None, tid=r['id'])

    def holding(self, u, pw, sid):
        """The terminal of the list that holds a conversation of Claude Code -
        one this person may see - or None."""
        rows = self.store.q("SELECT * FROM terms WHERE kind='claude' AND run_as=? ORDER BY created DESC",
                            (pw.pw_name,))
        mine = [r for r in rows if u['role'] == 'admin' or r['owner'] == u['name']]
        for r in mine:
            try:
                if json.loads(r['opts'] or '{}').get('sid') == sid:
                    return r
            except ValueError:
                pass
        for r in mine:
            if self.claude_sid(r) == sid:
                return r
        return None

    def rename(self, u, r, title):
        title = clean_line(title, 120)
        if not title:
            raise Refused('a name, please')
        self.store.x('UPDATE terms SET title=? WHERE id=?', (title, r['id']))

    def forget(self, u, r):
        if r['id'] in self.live(True):
            raise Refused('it is still running - end it first')
        self.store.x('DELETE FROM terms WHERE id=?', (r['id'],))


# ---------------------------------------------------------------------------
# Claude Code's own conversations, to go back to
# ---------------------------------------------------------------------------
# Claude Code keeps each conversation as ~/.claude/projects/<folder>/<id>.jsonl.
# They are read here only for what the list needs - the folder it was in, its
# first words, when - and resumed with `claude --resume <id>` in that folder.
HISTORY_CACHE = {}
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z')


def _first_words(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get('type') == 'text' and c.get('text'):
                return c['text']
    return ''


def conversation_facts(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (path, st.st_mtime, st.st_size)
    if key in HISTORY_CACHE:
        return HISTORY_CACHE[key]
    facts = {'id': os.path.basename(path)[:-6], 'mtime': st.st_mtime, 'bytes': st.st_size,
             'cwd': '', 'first': '', 'summary': '', 'branch': '', 'messages': 0}
    try:
        with open(path, 'rb') as f:
            head = f.read(512 * 1024)
            if st.st_size > len(head):
                f.seek(max(len(head), st.st_size - 64 * 1024))
                tail = f.read()
            else:
                tail = b''
    except OSError:
        return None
    for raw in head.split(b'\n') + tail.split(b'\n')[1:]:
        if not raw.strip():
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(d, dict):
            continue
        t = d.get('type')
        if t == 'summary' and d.get('summary'):
            facts['summary'] = clean_line(d['summary'], 200)
        if t in ('user', 'assistant'):
            facts['messages'] += 1
        if not facts['cwd'] and d.get('cwd'):
            facts['cwd'] = str(d['cwd'])
        if not facts['branch'] and d.get('gitBranch'):
            facts['branch'] = str(d['gitBranch'])
        if t == 'user' and not facts['first'] and not d.get('isMeta'):
            words = _first_words((d.get('message') or {}).get('content'))
            if words and not words.startswith(('<command-', '<local-command', 'Caveat:')):
                facts['first'] = clean_line(words, 200)
    if st.st_size > len(head):
        facts['messages_more'] = True
    if len(HISTORY_CACHE) > 5000:
        HISTORY_CACHE.clear()
    HISTORY_CACHE[key] = facts
    return facts


def conversations(pw, cwd='', most=300):
    base = os.path.join(pw.pw_dir, '.claude', 'projects')
    found = []
    try:
        folders = os.listdir(base)
    except OSError:
        return []
    for d in folders:
        full = os.path.join(base, d)
        try:
            names = os.listdir(full)
        except OSError:
            continue
        for n in names:
            if n.endswith('.jsonl') and UUID_RE.match(n[:-6]):
                found.append(os.path.join(full, n))
    found.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    out = []
    for p in found:
        f = conversation_facts(p)
        if not f or (not f['first'] and not f['summary'] and f['messages'] < 2):
            continue
        if cwd and os.path.normpath(f['cwd'] or '') != os.path.normpath(cwd):
            continue
        out.append(dict(f, run_as=pw.pw_name))
        if len(out) >= most:
            break
    return out


# ---------------------------------------------------------------------------
# A terminal in the browser: a WebSocket to a tmux client in a pseudo-terminal
# ---------------------------------------------------------------------------
# RFC 6455, the part a browser speaks. Binary frames from the browser are
# keys; text frames are JSON - {"t": "resize", "c": cols, "r": rows} and
# {"t": "ping"}. Binary frames to the browser are what the terminal shows.
WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


class WsClosed(Exception):
    pass


class WebSocket:
    def __init__(self, sock):
        self.sock = sock
        self.wlock = threading.Lock()
        self.closed = False

    @staticmethod
    def accept_key(key):
        return base64.b64encode(hashlib.sha1((key + WS_GUID).encode('ascii')).digest()).decode('ascii')

    def _read(self, n):
        buf = b''
        while len(buf) < n:
            got = self.sock.recv(n - len(buf))
            if not got:
                raise WsClosed()
            buf += got
        return buf

    def recv(self):
        """(opcode, payload) of the next whole message."""
        parts, first_op = [], None
        while True:
            b1, b2 = self._read(2)
            fin, op = b1 & 0x80, b1 & 0x0F
            masked, n = b2 & 0x80, b2 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._read(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._read(8))[0]
            if n > 16 * 1024 * 1024:
                raise WsClosed()
            mask = self._read(4) if masked else b''
            data = self._read(n) if n else b''
            if masked:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data)) if n < 64 else \
                    (int.from_bytes(data, 'big') ^ int.from_bytes((mask * (n // 4 + 1))[:n], 'big')
                     ).to_bytes(n, 'big')
            if op >= 0x8:                       # control frames, in between
                if op == 0x8:
                    self.close()
                    raise WsClosed()
                if op == 0x9:
                    self.send(data, 0xA)
                continue
            if op != 0:
                first_op = op
            parts.append(data)
            if fin:
                return first_op, b''.join(parts)

    def send(self, data, op=0x2):
        if isinstance(data, str):
            data, op = data.encode('utf-8'), 0x1 if op == 0x2 else op
        n = len(data)
        head = bytes([0x80 | op])
        if n < 126:
            head += bytes([n])
        elif n < 65536:
            head += bytes([126]) + struct.pack('>H', n)
        else:
            head += bytes([127]) + struct.pack('>Q', n)
        with self.wlock:
            if self.closed and op != 0x8:
                raise WsClosed()
            try:
                self.sock.sendall(head + data)
            except OSError:
                self.closed = True
                raise WsClosed()

    def close(self, code=1000):
        if self.closed:
            return
        try:
            self.send(struct.pack('>H', code), 0x8)
        except WsClosed:
            pass
        self.closed = True


VIEWERS = {}                # tid -> set of viewer threads' names (for the list)
VIEWERS_LOCK = threading.Lock()


def term_pos(terms, pw, target):
    rc, so, _se = terms.tmux(pw, ['display-message', '-p', '-t', target,
                                  '#{history_size}|#{scroll_position}|#{pane_in_mode}|#{pane_height}|'
                                  '#{alternate_on}|#{mouse_any_flag}'], timeout=5)
    bits = [x.strip() for x in (so or '').strip().split('|')]
    num = lambda i: int(bits[i]) if len(bits) > i and bits[i].lstrip('-').isdigit() else 0
    return {'size': num(0), 'at': num(1) if num(2) else 0, 'mode': bool(num(2)), 'rows': num(3),
            'alt': bool(num(4)) and not num(2), 'mouse': bool(num(5))}


# Lines one turn of the wheel moves Claude Code's own history by (its
# full-screen renderer); a scroll of n lines is n / this many turns.
WHEEL_LINES = 3


def term_wheel(terms, pw, target, now, n):
    """A program on the alternate screen keeps its history itself (Claude Code
    full-screen, less, vim): tmux has none to move. It is moved as the mouse
    wheel moves it - wheel events written to the program, in the middle of
    its screen - or, where it asked for no mouse, by Page Up / Page Down."""
    if not n:
        return
    if now['mouse']:
        turns = min(400, max(1, (abs(n) + WHEEL_LINES - 1) // WHEEL_LINES))
        row = max(1, (now['rows'] or 24) // 3)
        seq = '\x1b[<%d;%d;%dM' % (64 if n > 0 else 65, 10, row)
        hexes = ['%02x' % b for b in seq.encode()] * turns
        for i in range(0, len(hexes), 4000):
            terms.tmux(pw, ['send-keys', '-t', target, '-H'] + hexes[i:i + 4000], timeout=5)
    else:
        pages = min(50, max(1, abs(n) // max(1, (now['rows'] or 24) - 2)))
        terms.tmux(pw, ['send-keys', '-t', target, '-N', str(pages), 'PPage' if n > 0 else 'NPage'], timeout=5)


def term_scroll(terms, pw, target, msg, readonly=False):
    """tmux's history moved: `scroll` by lines (more than 0 back, less than 0
    on), `scrollto` a place (0 the top, 1 the live screen), `live` back to it.
    On the alternate screen the program's own history instead (term_wheel) -
    which is typing into it, so not for someone only looking."""
    t = msg.get('t')
    now = term_pos(terms, pw, target)
    if t == 'pos':
        return now

    def keys(*a):
        terms.tmux(pw, ['send-keys', '-t', target, '-X'] + list(a), timeout=5)
    if now['alt']:
        if readonly:
            return now
        if t == 'live':
            terms.tmux(pw, ['send-keys', '-t', target, 'C-End'], timeout=5)
        elif t == 'scroll':
            term_wheel(terms, pw, target, now, max(-5000, min(5000, int(msg.get('n') or 0))))
        return term_pos(terms, pw, target)
    if t == 'live':
        if now['mode']:
            keys('cancel')
        return term_pos(terms, pw, target)
    if t == 'scroll':
        n = max(-5000, min(5000, int(msg.get('n') or 0)))
    else:
        frac = max(0.0, min(1.0, float(msg.get('f') or 0)))
        n = int(round((1 - frac) * now['size'])) - now['at']
    if n > 0:
        if not now['mode']:
            terms.tmux(pw, ['copy-mode', '-e', '-t', target], timeout=5)
        keys('-N', str(n), 'scroll-up')
    elif n < 0 and now['mode']:
        if now['at'] + n <= 0:
            keys('cancel')
        else:
            keys('-N', str(-n), 'scroll-down')
    return term_pos(terms, pw, target)


def term_bridge(daemon, ws, u, r, cols, rows, readonly=False):
    """One browser window looking at one terminal, until either side goes."""
    pw = linux_user(r['run_as'])
    terms = daemon.terms
    sock = terms.sock(pw)
    master, slave = os.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
    except OSError:
        pass

    def ctty():
        try:
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        except OSError:
            pass
    args = [tmux_bin(), '-u', '-S', sock, 'attach-session', '-t', 'ai-' + r['id']]
    if readonly:
        args.append('-r')
    env = user_env(pw, {'TERM': 'xterm-256color'})
    try:
        proc = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=slave, env=env,
                                cwd=pw.pw_dir if os.path.isdir(pw.pw_dir) else '/',
                                start_new_session=True, preexec_fn=ctty, close_fds=True,
                                **as_user_kwargs(pw))
    except OSError as e:
        os.close(master)
        os.close(slave)
        ws.send(json.dumps({'t': 'error', 'error': 'tmux: %s' % e}))
        ws.close()
        return
    os.close(slave)
    with VIEWERS_LOCK:
        VIEWERS.setdefault(r['id'], set()).add(threading.current_thread().name)
    done = threading.Event()

    sid = u.get('_sid')
    checked = [time.time()]

    def still_signed_in():
        """The sign-in this window came with, still there: signing out (or an
        administrator ending it) closes the window's view - never the terminal,
        which goes on running for the next sign-in, from here or anywhere."""
        if not sid or time.time() - checked[0] < 10:
            return True
        checked[0] = time.time()
        try:
            return bool(daemon.store.one('SELECT id FROM sessions WHERE id=?', (sid,)))
        except Exception:                               # noqa: BLE001 - the database away: not a sign-out
            return True

    def pump():
        try:
            while not done.is_set():
                try:
                    ready, _w, _x = select.select([master], [], [], 1.0)
                except (OSError, ValueError):
                    break
                if not still_signed_in():
                    try:
                        ws.send(json.dumps({'t': 'signed-out'}))
                    except WsClosed:
                        pass
                    break
                if not ready:
                    if proc.poll() is not None:
                        break
                    continue
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                ws.send(data)
        except WsClosed:
            pass
        finally:
            done.set()
            try:
                ws.send(json.dumps({'t': 'detached', 'code': proc.poll()}))
            except WsClosed:
                pass
            ws.close()
            try:
                ws.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
    t = threading.Thread(target=pump, name='ai-term-out-%s' % r['id'], daemon=True)
    t.start()
    try:
        while not done.is_set():
            try:
                op, data = ws.recv()
            except (WsClosed, OSError, ValueError):
                break
            if op == 0x2:
                if not readonly and data:
                    try:
                        os.write(master, data)
                    except OSError:
                        break
            elif op == 0x1:
                try:
                    msg = json.loads(data.decode('utf-8', 'replace'))
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue
                if msg.get('t') == 'resize':
                    try:
                        c = max(10, min(1000, int(msg.get('c') or 80)))
                        rr = max(3, min(500, int(msg.get('r') or 24)))
                        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', rr, c, 0, 0))
                    except (OSError, ValueError, TypeError):
                        pass
                elif msg.get('t') == 'in' and not readonly:
                    try:
                        os.write(master, str(msg.get('d') or '').encode('utf-8'))
                    except OSError:
                        break
                elif msg.get('t') == 'ping':
                    try:
                        ws.send(json.dumps({'t': 'pong', 'at': time.time()}))
                    except WsClosed:
                        break
                elif msg.get('t') in ('scroll', 'scrollto', 'live', 'pos'):
                    # Back through tmux's own history (1.0.9): a finger on a
                    # tablet, or the scroll bar beside the terminal, moves
                    # it as the mouse wheel does - in tmux's copy mode, which
                    # the pages leave again at the bottom.
                    try:
                        got = term_scroll(terms, pw, 'ai-' + r['id'], msg, readonly)
                        ws.send(json.dumps(dict(got, t='pos')))
                    except WsClosed:
                        break
                    except Exception:                   # noqa: BLE001 - tmux away for a moment
                        pass
    finally:
        done.set()
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
            except OSError:
                pass
        try:
            os.close(master)
        except OSError:
            pass
        with VIEWERS_LOCK:
            VIEWERS.get(r['id'], set()).discard(threading.current_thread().name)
        terms.cache['at'] = 0


# ---------------------------------------------------------------------------
# Files: the working directory's, both ways
# ---------------------------------------------------------------------------
TEXT_MOST = 2 * 1024 * 1024
SAFE_INLINE = re.compile(r'^(image/(png|jpeg|gif|webp|bmp|avif)|application/pdf|text/plain)$')


def file_entry(path, name):
    full = os.path.join(path, name)
    try:
        st = os.lstat(full)
    except OSError:
        return None
    link = stat.S_ISLNK(st.st_mode)
    if link:
        try:
            st2 = os.stat(full)
            kind = 'dir' if stat.S_ISDIR(st2.st_mode) else 'file'
            size = st2.st_size
        except OSError:
            kind, size = 'broken', 0
    else:
        kind = 'dir' if stat.S_ISDIR(st.st_mode) else ('file' if stat.S_ISREG(st.st_mode) else 'other')
        size = st.st_size
    try:
        owner = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        owner = str(st.st_uid)
    return {'name': name, 'kind': kind, 'link': link, 'size': size, 'mtime': st.st_mtime,
            'mode': stat.filemode(st.st_mode), 'owner': owner}


def files_list(u, path, hidden=True):
    path = path_allowed(u, path or '/')
    if not os.path.isdir(path):
        raise Refused('%s is not a folder' % path, 404)
    try:
        names = os.listdir(path)
    except PermissionError:
        raise Refused('%s may not be read' % path, 403)
    out = []
    for n in names:
        if not hidden and n.startswith('.'):
            continue
        e = file_entry(path, n)
        if e:
            out.append(e)
    out.sort(key=lambda e: (e['kind'] != 'dir', e['name'].lower()))
    up = os.path.dirname(path.rstrip('/')) or '/'
    try:
        path_allowed(u, up)
    except Refused:
        up = ''
    return {'path': path, 'up': up if path != '/' else '', 'entries': out[:10000],
            'more': len(out) > 10000, 'roots': roots_of(u)}


def owner_ids(u):
    """The uid and gid files made for an account are given: those of the Linux
    account its terminals run as."""
    try:
        pw = linux_user(run_as_of(u))
        return pw.pw_uid, pw.pw_gid
    except Refused:
        return None, None


def give(path, u):
    if os.geteuid() != 0:
        return
    uid, gid = owner_ids(u)
    if uid is not None:
        try:
            os.lchown(path, uid, gid)
        except OSError:
            pass


def safe_name(name):
    name = os.path.basename(str(name or '').replace('\\', '/')).strip()
    name = re.sub(r'[\x00-\x1f\x7f/]', '', name)
    if name in ('', '.', '..'):
        raise Refused('a file needs a name')
    return name[:255]


def free_name(folder, name):
    if not os.path.lexists(os.path.join(folder, name)):
        return name
    stem, ext = os.path.splitext(name)
    for i in range(1, 10000):
        n = '%s (%d)%s' % (stem, i, ext)
        if not os.path.lexists(os.path.join(folder, n)):
            return n
    raise Refused('no free name for %s' % name)


def chat_folder(daemon, u, r):
    """Where a file given to Claude in terminal r goes - made, with its .gitignore."""
    where = str(CONFIG.get('chat_upload_dir') or '.ai-uploads').strip()
    pw = linux_user(r['run_as'])
    if where.startswith('~'):
        where = pw.pw_dir + where[1:]
    base = where if where.startswith('/') else os.path.join(r['cwd'] or pw.pw_dir, where)
    base = os.path.normpath(base)
    path_allowed(u, base)
    if not os.path.isdir(base):
        os.makedirs(base, exist_ok=True)
        if os.geteuid() == 0:
            os.chown(base, pw.pw_uid, pw.pw_gid)
    gi = os.path.join(base, '.gitignore')
    if not os.path.exists(gi):
        try:
            with open(gi, 'w') as f:
                f.write('# files given to Claude Code from the ai pages\n*\n')
            if os.geteuid() == 0:
                os.chown(gi, pw.pw_uid, pw.pw_gid)
        except OSError:
            pass
    return base


def take_upload(rfile, length, dest_dir, name, u, overwrite=False, uid=None, gid=None):
    """The body of a request written down as a file: (path, size)."""
    most = int(CONFIG.get('upload_most_mb') or 4096) * 1024 * 1024
    if length is None or length < 0:
        raise Refused('the size of the file was not said (Content-Length)', 411)
    if length > most:
        raise Refused('that file is bigger than this server takes (%d MB at most)' % (most >> 20), 413)
    dest_dir = path_allowed(u, dest_dir)
    if not os.path.isdir(dest_dir):
        raise Refused('%s is not a folder' % dest_dir, 404)
    name = safe_name(name)
    if not overwrite:
        name = free_name(dest_dir, name)
    target = os.path.join(dest_dir, name)
    if os.path.isdir(target):
        raise Refused('%s is a folder' % target)
    fd, tmp = tempfile.mkstemp(prefix='.ai-up-', dir=dest_dir)
    got = 0
    try:
        with os.fdopen(fd, 'wb') as f:
            while got < length:
                lump = rfile.read(min(1 << 20, length - got))
                if not lump:
                    break
                f.write(lump)
                got += len(lump)
        if got != length:
            raise Refused('the file did not arrive whole (%d of %d bytes)' % (got, length))
        os.chmod(tmp, 0o644)
        if os.geteuid() == 0:
            if uid is None:
                uid, gid = owner_ids(u)
            if uid is not None:
                os.chown(tmp, uid, gid)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return target, got


def path_under(path, root):
    """`path` is `root` or inside it, links followed."""
    real, top = os.path.realpath(path), os.path.realpath(root)
    return real == top or real.startswith(top.rstrip('/') + '/')


def chat_root_of(pw=None):
    """The folder chats start in (Settings - Claude Code), ~ as the account's home."""
    root = str(CONFIG.get('chat_root') or '').strip()
    if not root:
        return ''
    if root.startswith('~') and pw is not None:
        root = pw.pw_dir + root[1:]
    return os.path.normpath(root) if root.startswith('/') else ''


def files_op(u, body):
    op = str(body.get('op') or '')
    path = str(body.get('path') or '')
    if not path.startswith('/'):
        raise Refused('a full path, please')
    # Kept inside a folder when the page says so (the chat's, the folder of
    # the chats): nothing above it is made, renamed or deleted from there.
    root = str(body.get('root') or '')
    if root:
        if not path_under(path, root):
            raise Refused('that is outside %s' % root, 403)
        if op in ('rename', 'delete') and os.path.realpath(path) == os.path.realpath(root):
            raise Refused('%s itself is not renamed or taken away from here' % root)
    if op == 'touch':
        full = os.path.join(path_allowed(u, path), safe_name(body.get('name')))
        path_allowed(u, full)
        if os.path.lexists(full):
            raise Refused('there is a %s there already' % os.path.basename(full))
        with open(full, 'x', encoding='utf-8'):
            pass
        give(full, u)
        return {'path': full}
    if op == 'mkdir':
        full = os.path.join(path_allowed(u, path), safe_name(body.get('name')))
        path_allowed(u, full)
        os.makedirs(full, exist_ok=False)
        give(full, u)
        return {'path': full}
    real = path_allowed(u, path)
    if op == 'rename':
        name = safe_name(body.get('name'))
        dest = os.path.join(os.path.dirname(real), name)
        path_allowed(u, dest)
        if os.path.lexists(dest):
            raise Refused('there is a %s there already' % name)
        os.rename(real, dest)
        return {'path': dest}
    if op == 'delete':
        if real in ('/', '/etc', '/usr', '/var', '/boot', '/root', '/home', '/bin', '/sbin', '/lib',
                    '/lib64', '/opt', '/srv') or real in roots_of(u):
            raise Refused('%s is not taken away from here' % real)
        if os.path.isdir(real) and not os.path.islink(real):
            shutil.rmtree(real)
        else:
            os.unlink(real)
        return {'path': real}
    if op == 'read':
        if not os.path.isfile(real):
            raise Refused('not a file', 404)
        size = os.path.getsize(real)
        if size > TEXT_MOST:
            raise Refused('it is %s - too big to show here; download it instead' % human_bytes(size))
        with open(real, 'rb') as f:
            data = f.read()
        if b'\x00' in data[:8192]:
            raise Refused('it is not text; download it instead')
        return {'path': real, 'text': data.decode('utf-8', 'replace'), 'size': size,
                'mtime': os.path.getmtime(real)}
    if op == 'write':
        text = str(body.get('text') or '')
        if len(text) > TEXT_MOST:
            raise Refused('too much text for here')
        if os.path.isdir(real):
            raise Refused('it is a folder')
        if body.get('mtime') and os.path.exists(real) and \
                abs(os.path.getmtime(real) - float(body['mtime'])) > 0.001:
            raise Refused('it was changed on the server since it was opened here - open it again')
        existed = os.path.exists(real)
        st = os.stat(real) if existed else None
        write_atomic(real, text.encode('utf-8'), mode=stat.S_IMODE(st.st_mode) if st else 0o644,
                     uid=st.st_uid if st else None, gid=st.st_gid if st else None)
        if not existed:
            give(real, u)
        return {'path': real, 'mtime': os.path.getmtime(real)}
    raise Refused('mkdir, touch, rename, delete, read or write')


def human_bytes(n):
    n = float(n or 0)
    for unit in ('B', 'kB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return ('%d %s' if unit == 'B' else '%.1f %s') % (n, unit)
        n /= 1024


# ---------------------------------------------------------------------------
# The machine: what it is, its network, firewall, certificate, keys, updates
# ---------------------------------------------------------------------------
# The daemon runs as root - it starts terminals as any account - so these are
# done here, each checked against the one shape its values may have before
# anything is written. A change that could cut the pages off (the network,
# the firewall, who may reach the pages) is "on trial": it goes back by
# itself after revert_s seconds unless somebody presses Keep it.
ADDR_RE = re.compile(r'^[0-9A-Fa-f:.]+(/[0-9]{1,3})?\Z')
HOST_RE = re.compile(r'^(?=.{1,253}\Z)([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)'
                     r'(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\Z')


def plain_ip(text, how='address'):
    text = str(text or '').strip()
    if not ADDR_RE.match(text):
        raise Refused('%r is not an address' % text[:60])
    try:
        got = {'address': ipaddress.ip_address, 'network': lambda t: ipaddress.ip_network(t, strict=False),
               'interface': ipaddress.ip_interface}[how](text)
    except ValueError:
        raise Refused('%r is not an address' % text[:60])
    return got


def os_release():
    out = {}
    for line in read_text('/etc/os-release').splitlines():
        k, _s, v = line.partition('=')
        out[k] = v.strip().strip('"')
    return out


def pkg_manager():
    if which('dnf'):
        return 'dnf'
    if which('apt-get'):
        return 'apt'
    return ''


def first_line(cmd, timeout=10):
    rc, so, se = run(cmd, timeout=timeout)
    return (so or se).strip().split('\n')[0] if rc in (0, 1) else ''


def machine_facts():
    osr = os_release()
    mem = {}
    for line in read_text('/proc/meminfo').splitlines():
        k, _s, v = line.partition(':')
        try:
            mem[k] = int(v.split()[0]) * 1024
        except (ValueError, IndexError):
            pass
    try:
        up = float(read_text('/proc/uptime').split()[0])
    except (ValueError, IndexError):
        up = 0
    try:
        load = os.getloadavg()
    except OSError:
        load = (0, 0, 0)
    disks = []
    for p in ('/', str(STATE_DIR), '/home', '/tmp'):
        try:
            d = shutil.disk_usage(p)
            if not any(x['total'] == d.total and x['free'] == d.free for x in disks):
                disks.append({'path': p, 'total': d.total, 'used': d.used, 'free': d.free})
        except OSError:
            pass
    addrs = []
    rc, so, _se = run(['ip', '-o', 'addr', 'show'], timeout=5)
    for line in so.splitlines() if rc == 0 else []:
        f = line.split()
        if len(f) >= 4 and f[1] != 'lo':
            try:
                ifc = ipaddress.ip_interface(f[3])
            except ValueError:
                continue
            if not ifc.ip.is_link_local:
                addrs.append({'dev': f[1].split('@')[0], 'addr': str(ifc)})
    php = ''
    for b in [which('php-fpm')] + sorted(Path('/usr/sbin').glob('php-fpm*')):
        if b:
            php = first_line([str(b), '-v'])
            if php:
                break
    return {
        'host': host_name(), 'os': osr.get('PRETTY_NAME') or sys.platform, 'kernel': os.uname().release,
        'arch': os.uname().machine, 'uptime': up, 'load': list(load), 'cpus': os.cpu_count() or 1,
        'mem_total': mem.get('MemTotal', 0), 'mem_avail': mem.get('MemAvailable', 0),
        'swap_total': mem.get('SwapTotal', 0), 'swap_free': mem.get('SwapFree', 0),
        'disks': disks, 'addrs': addrs,
        'software': {'ai': __version__, 'python': sys.version.split()[0],
                     'tmux': first_line([tmux_bin(), '-V']), 'nginx': first_line(['nginx', '-v']),
                     'php': php.split(' (')[0], 'openssl': first_line(['openssl', 'version']),
                     'node': first_line(['node', '--version']), 'git': first_line(['git', '--version'])},
        'pm': pkg_manager(),
    }


# ---- changes on trial: kept, or taken back ----------------------------------------
class Trials:
    def __init__(self, daemon):
        self.daemon = daemon
        self.lock = threading.Lock()

    def all(self):
        return self.daemon.store.meta_json('trials', {}) or {}

    def start(self, kind, words, undo, by):
        """`undo` is the JSON that trial_undo() takes to put things back."""
        with self.lock:
            t = self.all()
            secs = int(CONFIG.get('revert_s') or 120)
            t[kind] = {'kind': kind, 'words': words, 'undo': undo, 'by': by, 'at': time.time(),
                       'until': time.time() + secs}
            self.daemon.store.set_meta_json('trials', t)
        self.daemon.store.add_event('settings', '%s: %s - goes back in %d s unless kept' % (by, words, secs),
                                    'warn', who=by)

    def keep(self, kind, by):
        with self.lock:
            t = self.all()
            one = t.pop(kind, None)
            self.daemon.store.set_meta_json('trials', t)
        if one:
            self.daemon.store.add_event('settings', '%s kept: %s' % (by, one['words']), 'info', who=by)
        return bool(one)

    def back(self, kind, by):
        with self.lock:
            t = self.all()
            one = t.pop(kind, None)
            self.daemon.store.set_meta_json('trials', t)
        if not one:
            return False
        try:
            trial_undo(self.daemon, kind, one['undo'])
            self.daemon.store.add_event('settings', '%s taken back (%s): %s' % (
                one['words'], 'by ' + by if by else 'not kept in time', ''), 'warn', who=by)
        except Exception as e:                          # noqa: BLE001
            self.daemon.store.add_event('settings', 'taking back "%s" failed: %s' % (one['words'], e), 'bad')
        return True

    def tick(self):
        for kind, one in list(self.all().items()):
            if time.time() > float(one.get('until') or 0):
                self.back(kind, '')

    def view(self):
        return [dict(v, left=max(0, int(v['until'] - time.time())), undo=None)
                for v in self.all().values()]


# ---- who may reach the pages (nginx's allow lines) ------------------------------------
ACCESS_BEGIN = '# AI-ALLOW-BEGIN'
ACCESS_END = '# AI-ALLOW-END'


def access_read():
    text = read_text(NGINX_CONF)
    m = re.search(re.escape(ACCESS_BEGIN) + r'\n(.*?)\n\s*' + re.escape(ACCESS_END), text, re.S)
    if not m:
        return {'managed': False, 'all': True, 'nets': [], 'file': str(NGINX_CONF)}
    nets, everyone = [], False
    for line in m.group(1).splitlines():
        line = line.split('#')[0].strip().rstrip(';').strip()
        if line == 'allow all':
            everyone = True
        elif line.startswith('allow '):
            nets.append(line[6:].strip())
    return {'managed': True, 'all': everyone or not nets, 'nets': nets, 'file': str(NGINX_CONF)}


def access_apply(a):
    nets = []
    if not a.get('all'):
        for n in a.get('nets') or []:
            nets.append(str(plain_ip(n, 'network')))
        if not nets:
            raise Refused('who may reach the pages: everybody, or at least one network')
    text = read_text(NGINX_CONF, most=1 << 22)
    if ACCESS_BEGIN not in text:
        raise Refused('%s has no %s line: it was not written by install.sh' % (NGINX_CONF, ACCESS_BEGIN))
    pad = re.search(r'\n([ \t]*)' + re.escape(ACCESS_BEGIN), text)
    pad = pad.group(1) if pad else '        '
    lines = ['%sallow all;' % pad] if a.get('all') else ['%sallow %s;' % (pad, n) for n in nets]
    new = re.sub(re.escape(ACCESS_BEGIN) + r'\n.*?\n[ \t]*' + re.escape(ACCESS_END),
                 lambda m: ACCESS_BEGIN + '\n' + '\n'.join(lines) + '\n' + pad + ACCESS_END, text, flags=re.S)
    nginx_swap({NGINX_CONF: new})


def nginx_swap(files):
    """Files of nginx's replaced, checked with nginx -t and reloaded - or all put
    back as they were when nginx says no."""
    if NO_SYSTEM:
        for p, t in files.items():
            write_atomic(p, t, mode=0o644)
        return
    before = {}
    for p in files:
        try:
            with open(p, 'rb') as f:
                before[p] = (f.read(), os.stat(p).st_mode & 0o777)
        except OSError:
            before[p] = None
    for p, t in files.items():
        mode = 0o600 if str(p).endswith('.key') else 0o644
        write_atomic(p, t, mode=mode)
    rc, so, se = run(['nginx', '-t'], timeout=30)
    if rc != 0:
        for p, was in before.items():
            if was is None:
                try:
                    os.unlink(p)
                except OSError:
                    pass
            else:
                write_atomic(p, was[0], mode=was[1])
        raise Refused('nginx does not take it, so everything was put back: %s' % (se or so).strip()[-400:])
    run(['systemctl', 'reload', 'nginx'], timeout=30)


def access_change(daemon, a, by):
    old = access_read()
    access_apply(a)
    daemon.trials.start('access', 'who may reach the pages: %s' % (
        'everybody' if a.get('all') else ', '.join(a.get('nets') or [])), {'all': old['all'], 'nets': old['nets']}, by)


# ---- the certificate ----------------------------------------------------------------------
def cert_facts(pem_path=CERT_FILE):
    if not os.path.exists(pem_path):
        return {'there': False}
    rc, so, se = run(['openssl', 'x509', '-in', str(pem_path), '-noout', '-subject', '-issuer', '-dates',
                      '-fingerprint', '-sha256', '-ext', 'subjectAltName'], timeout=15)
    if rc != 0:
        rc, so, se = run(['openssl', 'x509', '-in', str(pem_path), '-noout', '-subject', '-issuer', '-dates',
                          '-fingerprint', '-sha256'], timeout=15)
    out = {'there': True, 'file': str(pem_path), 'raw': so}
    for line in so.splitlines():
        k, _s, v = line.partition('=')
        k = k.strip().lower()
        if k == 'subject':
            out['subject'] = v.strip()
        elif k == 'issuer':
            out['issuer'] = v.strip()
        elif k == 'notbefore':
            out['from'] = v.strip()
        elif k == 'notafter':
            out['until'] = v.strip()
            try:
                out['until_ts'] = datetime.strptime(v.strip(), '%b %d %H:%M:%S %Y %Z').replace(
                    tzinfo=timezone.utc).timestamp()
            except ValueError:
                pass
        elif 'fingerprint' in k:
            out['sha256'] = v.strip()
    m = re.search(r'Subject Alternative Name:\s*\n\s*(.+)', so)
    if m:
        out['names'] = [x.strip().split(':', 1)[-1] for x in m.group(1).split(',')]
    out['self_signed'] = out.get('subject') == out.get('issuer')
    return out


CERT_RE = re.compile(r'-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\s]+?-----END CERTIFICATE-----')
KEY_RE = re.compile(r'-----BEGIN ((RSA |EC )?PRIVATE KEY|ENCRYPTED PRIVATE KEY)-----[A-Za-z0-9+/=\s:,-]+?'
                    r'-----END \1-----')


def pubkey_of(pem, kind):
    with tempfile.NamedTemporaryFile('w', suffix='.pem', delete=False) as f:
        f.write(pem)
        p = f.name
    try:
        if kind == 'cert':
            rc, so, se = run(['openssl', 'x509', '-in', p, '-noout', '-pubkey'], timeout=15)
        else:
            rc, so, se = run(['openssl', 'pkey', '-in', p, '-pubout'], timeout=15)
    finally:
        os.unlink(p)
    if rc != 0:
        raise Refused('openssl cannot read the %s: %s' % ('certificate' if kind == 'cert' else 'key',
                                                            (se or so).strip()[:200]))
    return so.strip()


def cert_put(cert_text, key_text, chain_text=''):
    certs = CERT_RE.findall(str(cert_text or '') + '\n' + str(chain_text or ''))
    keys = KEY_RE.search(str(key_text or ''))
    if not certs:
        raise Refused('no certificate (-----BEGIN CERTIFICATE-----) in what was given')
    if not keys:
        raise Refused('no private key (-----BEGIN PRIVATE KEY-----) in what was given')
    if 'ENCRYPTED' in keys.group(0):
        raise Refused('the key is locked with a passphrase: give it unlocked (openssl pkey -in KEY -out NEW)')
    key = keys.group(0) + '\n'
    if pubkey_of(certs[0], 'cert') != pubkey_of(key, 'key'):
        raise Refused('the key does not belong to the certificate')
    nginx_swap({CERT_FILE: '\n'.join(c.strip() for c in certs) + '\n', KEY_FILE: key})


def cert_self(names, days=825):
    names = [n.strip() for n in names if n and n.strip()] or [host_name()]
    alt = []
    for n in names:
        try:
            alt.append('IP:' + str(ipaddress.ip_address(n)))
        except ValueError:
            if not HOST_RE.match(n.replace('*.', 'x.', 1)):
                raise Refused('%s is not a host name' % n[:60])
            alt.append('DNS:' + n)
    with tempfile.TemporaryDirectory(prefix='.ai-cert-') as work:
        k, c = os.path.join(work, 'k'), os.path.join(work, 'c')
        run(['openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-sha256', '-days', str(int(days)),
             '-keyout', k, '-out', c, '-subj', '/CN=%s' % names[0][:64],
             '-addext', 'subjectAltName=' + ','.join(alt)], timeout=120, check=True)
        nginx_swap({CERT_FILE: read_text(c), KEY_FILE: read_text(k)})


TLS_PRESETS = {
    # The ciphers ai and otp have always used: ECDHE only, AEAD only.
    'standard': {'protocols': ['TLSv1.2', 'TLSv1.3'], 'ciphers': (
        'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
        'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
        'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305')},
    # Mozilla's "intermediate": the same and the DHE ones (DH parameters).
    'intermediate': {'protocols': ['TLSv1.2', 'TLSv1.3'], 'ciphers': (
        'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:'
        'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:'
        'ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:'
        'DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-CHACHA20-POLY1305')},
    # Mozilla's "modern": TLS 1.3 alone - its ciphers are not chosen.
    'modern': {'protocols': ['TLSv1.3'], 'ciphers': ''},
}
DH_WORDS = {'none': 'none (ECDHE only needs none)',
            'ffdhe2048': 'RFC 7919 ffdhe2048', 'ffdhe3072': 'RFC 7919 ffdhe3072',
            'ffdhe4096': 'RFC 7919 ffdhe4096', 'gen2048': 'made here, 2048 bits',
            'gen3072': 'made here, 3072 bits (a minute or so)',
            'gen4096': 'made here, 4096 bits (several minutes)'}

def _openssl(args, data=None, env=None, what='openssl'):
    e = dict(os.environ)
    e.update(env or {})
    got = subprocess.run(['openssl'] + args, input=data, capture_output=True, env=e,
                         timeout=120)
    if got.returncode != 0:
        said = (got.stderr or got.stdout or b'').decode('utf-8', 'replace').strip()
        raise ValueError('%s: %s' % (what, (said.splitlines() or ['openssl said no'])[-1][:200]))
    return got.stdout


PEM_CERT = re.compile(r'-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\s]+?-----END CERTIFICATE-----')
PEM_KEY = re.compile(r'-----BEGIN ((?:RSA |EC |ENCRYPTED )?PRIVATE KEY)-----[A-Za-z0-9+/=\s:,-]+?'
                     r'-----END \1-----')


def cert_info(pem):
    """What a certificate says of itself, for the pages."""
    out = _openssl(['x509', '-noout', '-subject', '-issuer', '-startdate', '-enddate',
                    '-fingerprint', '-sha256', '-ext', 'subjectAltName', '-nameopt',
                    'RFC2253'], pem.encode(), what='the certificate').decode()
    info = {'san': []}
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('subject='):
            info['subject'] = line[8:].strip()
        elif line.startswith('issuer='):
            info['issuer'] = line[7:].strip()
        elif line.startswith('notBefore='):
            info['not_before'] = _cert_time(line[10:])
        elif line.startswith('notAfter='):
            info['not_after'] = _cert_time(line[9:])
        elif 'Fingerprint=' in line:
            info['fingerprint'] = line.split('=', 1)[1].strip()
        elif 'Subject Alternative Name' in line and i + 1 < len(lines):
            info['san'] = [x.strip().split(':', 1)[-1] for x in lines[i + 1].split(',')
                           if x.strip()]
    info['self_signed'] = info.get('subject') == info.get('issuer')
    cn = re.search(r'(?:^|,)CN=([^,]+)', info.get('subject') or '')
    info['cn'] = cn.group(1) if cn else ''
    try:
        pub = _openssl(['x509', '-noout', '-pubkey'], pem.encode()).decode()
        txt = _openssl(['pkey', '-pubin', '-noout', '-text'], pub.encode()).decode()
        m = re.search(r'\((\d+) bit\)', txt)
        info['key'] = ('%s %s bit' % ('EC' if 'ASN1 OID' in txt or 'NIST' in txt else 'RSA',
                                      m.group(1))) if m else ''
    except ValueError:
        info['key'] = ''
    return info


def _cert_time(text):
    try:
        return datetime.strptime(text.strip().replace('  ', ' '),
                                 '%b %d %H:%M:%S %Y %Z').replace(
            tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _pub_of_cert(pem):
    return _openssl(['x509', '-noout', '-pubkey'], pem.encode(), what='the certificate')


def _pub_of_key(pem):
    return _openssl(['pkey', '-pubout'], pem.encode(), what='the key')


def key_plain(pem, password=''):
    """A private key without its passphrase, as PEM."""
    return _openssl(['pkey', '-passin', 'env:AI_PW'], pem.encode(),
                    {'AI_PW': password or ''},
                    what='the key (a wrong or missing password?)').decode()


def cert_bundle(cert='', key='', chain='', root='', pfx=b'', password='', pending_key=''):
    """Whatever was sent - one PEM with everything in it, separate parts, or
    a PFX / PKCS#12 with or without a password - as the parts nginx needs:
    the certificate, its key, the chain up from it, the root. The key is the
    certificate's own or nothing is taken."""
    certs, keys = [], []
    if pfx:
        got = None
        for extra in ([], ['-legacy']):
            try:
                got = _openssl(['pkcs12', '-nodes', '-passin', 'env:AI_PW'] + extra, pfx,
                               {'AI_PW': password or ''}, what='the PFX / PKCS#12 file')
                break
            except ValueError as e:
                last = e
        if got is None:
            raise ValueError('%s - is the password right?' % last)
        text = got.decode('utf-8', 'replace')
        certs += [m.group(0) for m in PEM_CERT.finditer(text)]
        keys += [m.group(0) for m in PEM_KEY.finditer(text)]
    for part in (cert, chain, root, key):
        part = str(part or '')
        certs += [m.group(0) for m in PEM_CERT.finditer(part)]
        keys += [m.group(0) for m in PEM_KEY.finditer(part)]
    if not certs:
        raise ValueError('no certificate was found in what was sent (PEM, or a PFX / PKCS#12 '
                         'file)')
    if len(keys) > 1:
        raise ValueError('more than one private key was sent')
    if keys:
        key_pem = key_plain(keys[0], password)
    elif pending_key:
        key_pem = pending_key
    else:
        raise ValueError('no private key came with it: send the key too (or the PFX), or make '
                         'the request here first so the key is waiting')
    want = _pub_of_key(key_pem)
    leaf = next((c for c in certs if _pub_of_cert(c) == want), None)
    if not leaf:
        raise ValueError('none of the certificates is the one of this key')
    others = [c for c in certs if c != leaf]
    infos = {c: cert_info(c) for c in others}
    roots = [c for c in others if infos[c]['self_signed']]
    roots += [m.group(0) for m in PEM_CERT.finditer(str(root or '')) if m.group(0) not in roots]
    inter = [c for c in others if c not in roots]
    # The chain in order: each the issuer of the one before it.
    chain_out, at = [], cert_info(leaf)
    while inter:
        nxt = next((c for c in inter if infos[c].get('subject') == at.get('issuer')), None)
        if not nxt:
            chain_out += inter
            break
        chain_out.append(nxt)
        inter.remove(nxt)
        at = infos[nxt]
    info = cert_info(leaf)
    verify = ''
    if roots:
        with tempfile.TemporaryDirectory(prefix='ai-cert-') as t:
            def put(name, text):
                p = os.path.join(t, name)
                with open(p, 'w') as f:
                    f.write(text)
                return p
            args = ['verify', '-CAfile', put('root.pem', '\n'.join(roots) + '\n')]
            if chain_out:
                args += ['-untrusted', put('chain.pem', '\n'.join(chain_out) + '\n')]
            args.append(put('leaf.pem', leaf + '\n'))
            try:
                _openssl(args, what='the chain')
                verify = 'ok'
            except ValueError as e:
                verify = str(e)
    return {'cert': leaf + '\n', 'chain': ''.join(c + '\n' for c in chain_out),
            'root': ''.join(c + '\n' for c in roots), 'key': key_pem, 'info': info,
            'chain_info': [cert_info(c) for c in chain_out],
            'root_info': [cert_info(c) for c in roots], 'verify': verify}


def _san_ext(names):
    out = []
    for n in names:
        n = str(n).strip()
        if not n:
            continue
        try:
            plain_ip(n, 'address')
            out.append('IP:' + n)
        except (ValueError, Refused):
            if not re.match(r'^(\*\.)?[A-Za-z0-9.-]{1,253}\Z', n):
                raise ValueError('%r is not a name or an address' % n)
            out.append('DNS:' + n)
    return ','.join(out)


def _subject(cn, org='', unit='', country='', city=''):
    def esc(v):
        return re.sub(r'([/\\=+,])', r'\\\1', str(v).strip())
    if not cn or not re.match(r'^[A-Za-z0-9*.-]{1,64}\Z', cn):
        raise ValueError('the common name is a host name')
    s = '/CN=' + esc(cn)
    if org:
        s += '/O=' + esc(org)
    if unit:
        s += '/OU=' + esc(unit)
    if city:
        s += '/L=' + esc(city)
    if country:
        if not re.match(r'^[A-Za-z]{2}\Z', country):
            raise ValueError('the country is two letters (CZ)')
        s += '/C=' + country.upper()
    return s


def new_key(kind):
    if kind == 'ec':
        return _openssl(['genpkey', '-algorithm', 'EC', '-pkeyopt',
                         'ec_paramgen_curve:P-256']).decode()
    bits = {'rsa2048': 2048, 'rsa3072': 3072, 'rsa4096': 4096}.get(kind)
    if not bits:
        raise ValueError('the key is ec, rsa2048, rsa3072 or rsa4096')
    return _openssl(['genpkey', '-algorithm', 'RSA', '-pkeyopt',
                     'rsa_keygen_bits:%d' % bits]).decode()


def make_csr(cn, names, kind='rsa2048', **subject):
    key = new_key(kind)
    with tempfile.TemporaryDirectory(prefix='ai-csr-') as t:
        kf = os.path.join(t, 'k.pem')
        with open(kf, 'w') as f:
            f.write(key)
        csr = _openssl(['req', '-new', '-key', kf, '-subj', _subject(cn, **subject),
                        '-addext', 'subjectAltName=' + _san_ext([cn] + list(names))],
                       what='the request').decode()
    return key, csr


def make_selfsigned(cn, names, days=825, kind='rsa2048', **subject):
    key = new_key(kind)
    with tempfile.TemporaryDirectory(prefix='ai-crt-') as t:
        kf = os.path.join(t, 'k.pem')
        with open(kf, 'w') as f:
            f.write(key)
        crt = _openssl(['req', '-new', '-x509', '-key', kf, '-days', str(int(days)), '-subj',
                        _subject(cn, **subject), '-addext',
                        'subjectAltName=' + _san_ext([cn] + list(names))],
                       what='the certificate').decode()
    return key, crt



def tls_view(prof):
    """A profile as the pages may see it: no key."""
    if not prof:
        return None
    out = {k: v for k, v in prof.items() if k not in ('key', 'pending_key')}
    out['has_key'] = bool(prof.get('key'))
    out['pending'] = bool(prof.get('pending_key'))
    return out


def tls_policy_checked(b):
    preset = str(b.get('preset') or 'standard')
    if preset not in list(TLS_PRESETS) + ['custom']:
        raise ValueError('the TLS settings are standard, intermediate, modern or custom')
    out = {'preset': preset}
    if preset == 'custom':
        prot = b.get('protocols') or []
        if not isinstance(prot, list) or not prot or \
                any(p not in ('TLSv1.2', 'TLSv1.3') for p in prot):
            raise ValueError('the protocols are TLSv1.2 and/or TLSv1.3')
        out['protocols'] = [p for p in ('TLSv1.2', 'TLSv1.3') if p in prot]
        ciphers = str(b.get('ciphers') or '').strip()
        if ciphers:
            if not re.match(r'^[A-Za-z0-9_+!@=:.-]{1,2000}\Z', ciphers):
                raise ValueError('the ciphers are an OpenSSL cipher list')
            _openssl(['ciphers', ciphers], what='OpenSSL does not know that cipher list')
        out['ciphers'] = ciphers
    dh = str(b.get('dh') or 'none')
    if dh not in DH_WORDS:
        raise ValueError('the DH parameters are one of %s' % ', '.join(DH_WORDS))
    out['dh'] = dh
    out['prefer'] = bool(b.get('prefer'))
    try:
        # Not said is the two years nginx is shipped with (1.0.94), not none:
        # the first TLS change on the pages dropped HSTS without a word.
        hv = b.get('hsts')
        out['hsts'] = max(0, min(63072000, int(hv) if hv not in (None, '') else 63072000))
    except (TypeError, ValueError):
        raise ValueError('HSTS is a number of seconds')
    return out


# ---- the certificate and TLS of the pages, as otp's Certificates and TLS -----------------------
# Kept in meta 'web:tls': the certificate, its chain and root, the key (sealed),
# a request waiting for its certificate (its key sealed), and how TLS is
# spoken - the protocols and ciphers, DH parameters, HSTS. Put into nginx by
# the daemon itself (it is root): the files written, the lines of the server
# on 443 set, nginx -t, reload - or everything put back.
CA_FILE = CERT_DIR / 'ai-ca.pem'
DH_FILE = CERT_DIR / 'ai-dh.pem'
DH_EXPECT_S = {'gen2048': 15, 'gen3072': 120, 'gen4096': 600}
TLS_LOCK = threading.Lock()
TLS_STATE = {'state': '', 'said': [], 'progress': None, 'at': 0.0}


def tls_prof(store):
    got = store.meta_json('web:tls', None)
    return got if isinstance(got, dict) else None


def tls_keep(store, prof, by):
    prof = dict(prof)
    prof['at'] = time.time()
    prof['by'] = by
    store.set_meta_json('web:tls', prof)


def set_directive(block, name, value):
    """`name value;` in a server { } - replaced where it is, put in after
    server_name where it is not, taken out for None (otp_web.py's)."""
    lines = block.split('\n')
    depth, at, insert_at = 0, [], None
    for n, line in enumerate(lines):
        if depth == 1 and re.match(r'^\s*%s\s' % re.escape(name), line):
            at.append(n)
        if depth == 1 and insert_at is None and re.match(r'^\s*server_name\s', line):
            insert_at = n + 1
        depth += line.count('{') - line.count('}')
    if value is None:
        for n in reversed(at):
            del lines[n]
        return '\n'.join(lines)
    text = '    %-25s %s;' % (name, value)
    if at:
        lines[at[0]] = text
        for n in reversed(at[1:]):
            del lines[n]
    else:
        lines.insert(insert_at if insert_at is not None else 1, text)
    return '\n'.join(lines)


def nginx_tls_block(conf):
    """(before, the server { } that listens on 443, after) of nginx's file."""
    lines = conf.split('\n')
    depth, start = 0, None
    for n, line in enumerate(lines):
        if depth == 0 and re.match(r'^\s*server\s*\{', line):
            start = n
        depth += line.count('{') - line.count('}')
        if depth == 0 and start is not None:
            block = '\n'.join(lines[start:n + 1])
            if re.search(r'^\s*listen\s+[^;]*443', block, re.M):
                return '\n'.join(lines[:start]), block, '\n'.join(lines[n + 1:])
            start = None
    raise Refused('%s has no server { } listening on 443' % NGINX_CONF)


def tls_resolved(prof):
    preset = prof.get('preset') or 'standard'
    p = TLS_PRESETS.get(preset) or {'protocols': prof.get('protocols') or ['TLSv1.2', 'TLSv1.3'],
                                    'ciphers': prof.get('ciphers') or ''}
    return {'protocols': p['protocols'], 'ciphers': p['ciphers'] or TLS_PRESETS['standard']['ciphers'],
            'prefer': bool(prof.get('prefer')), 'dh': prof.get('dh') or 'none',
            'hsts': int(prof['hsts']) if prof.get('hsts') not in (None, '') else 63072000}


def tls_progress(words, step, expect=None):
    TLS_STATE['progress'] = {'words': words, 'step': step, 'total': 4, 'at': time.time(), 'now': time.time(),
                             'expect_s': expect}


def dh_pem(choice):
    if choice.startswith('ffdhe'):
        return _openssl(['genpkey', '-genparam', '-algorithm', 'DH', '-pkeyopt', 'group:%s' % choice],
                        what='the DH group %s' % choice).decode()
    tls_progress('making DH parameters of %s bits' % choice[3:], 2, DH_EXPECT_S.get(choice))
    return _openssl(['dhparam', choice[3:]], what='making DH parameters').decode()


def tls_apply(store, prof, by):
    """Into nginx: the files and the lines. Raises Refused where nginx says no."""
    t = tls_resolved(prof)
    files = {}
    tls_progress('reading nginx', 1)
    conf = read_text(NGINX_CONF)
    head, block, tail = nginx_tls_block(conf)
    said = []
    if prof.get('cert') and prof.get('key'):
        key = unseal_secret(prof['key'], 'web:tls')
        if not key:
            raise Refused('the key kept for the certificate cannot be opened here (secrets.key changed?)')
        files[CERT_FILE] = prof['cert'] + (prof.get('chain') or '')
        files[KEY_FILE] = key
        block = set_directive(block, 'ssl_certificate', str(CERT_FILE))
        block = set_directive(block, 'ssl_certificate_key', str(KEY_FILE))
        if prof.get('root'):
            files[CA_FILE] = prof['root'] + (prof.get('chain') or '')
            block = set_directive(block, 'ssl_trusted_certificate', str(CA_FILE))
        else:
            block = set_directive(block, 'ssl_trusted_certificate', None)
        said.append('certificate: %s' % ((prof.get('info') or {}).get('cn') or '?'))
    block = set_directive(block, 'ssl_protocols', ' '.join(t['protocols']))
    block = set_directive(block, 'ssl_ciphers', t['ciphers'])
    block = set_directive(block, 'ssl_prefer_server_ciphers', 'on' if t['prefer'] else 'off')
    if t['dh'] != 'none':
        if t['dh'] != prof.get('dh_made') or not DH_FILE.exists():
            files[DH_FILE] = dh_pem(t['dh'])
            prof['dh_made'] = t['dh']
        block = set_directive(block, 'ssl_dhparam', str(DH_FILE))
    else:
        block = set_directive(block, 'ssl_dhparam', None)
    if t['hsts']:
        block = set_directive(block, 'add_header Strict-Transport-Security', '"max-age=%d" always' % t['hsts'])
    else:
        block = set_directive(block, 'add_header Strict-Transport-Security', None)
    files[NGINX_CONF] = head + ('\n' if head else '') + block + ('\n' if tail else '') + tail
    tls_progress('nginx checks it and reloads', 3)
    nginx_swap(files)
    said.append('%s; %s; DH %s%s' % (' '.join(t['protocols']), 'ciphers as set' if prof.get('preset') == 'custom'
                                     else (prof.get('preset') or 'standard'), t['dh'],
                                     '; HSTS %d s' % t['hsts'] if t['hsts'] else '; no HSTS'))
    tls_keep(store, prof, by)
    store.add_event('system', '%s put the TLS of the pages into nginx: %s' % (by, '; '.join(said)), 'info', who=by)
    return said


def tls_apply_later(store, prof, by):
    """In a thread of its own: DH parameters made here take minutes."""
    if not TLS_LOCK.acquire(blocking=False):
        raise Refused('a change of the TLS is being put in already - wait for it', 409)
    TLS_STATE.update(state='working', said=[], at=time.time())

    def go():
        try:
            TLS_STATE['said'] = tls_apply(store, prof, by)
            TLS_STATE['state'] = 'done'
        except Exception as e:                          # noqa: BLE001
            TLS_STATE.update(state='failed', said=[str(e)])
            store.add_event('system', 'the TLS of the pages could not be put in: %s' % e, 'warn', who=by)
        finally:
            TLS_STATE['progress'] = None
            TLS_LOCK.release()
    threading.Thread(target=go, daemon=True).start()


def tls_reapply_if_needed(store):
    """At start: nginx's file written afresh (install.sh --rewrite-nginx) lost
    the TLS kept here - put back, as otp's root helper does."""
    prof = tls_prof(store)
    if not prof or NO_SYSTEM:
        return
    try:
        _h, block, _t = nginx_tls_block(read_text(NGINX_CONF))
    except Refused:
        return
    t = tls_resolved(prof)
    want = ['ssl_ciphers               %s;' % t['ciphers'], 'ssl_protocols             %s;' % ' '.join(t['protocols'])]
    if t['hsts']:
        want.append('"max-age=%d" always;' % t['hsts'])
    if t['dh'] != 'none':
        want.append('ssl_dhparam')
    if all(w in block for w in want):
        return
    log('the TLS kept for the pages is not in %s: put in again' % NGINX_CONF, 'warn')
    try:
        tls_apply_later(store, prof, 'ai (at start)')
    except Refused:
        pass


def cert_now_info():
    try:
        pem = read_text(CERT_FILE)
        m = PEM_CERT.search(pem)
        return cert_info(m.group(0)) if m else None
    except (OSError, ValueError, Refused):
        return None


# ---------------------------------------------------------------------------
# Backups to another machine (otp's, 1.0.109)
# ---------------------------------------------------------------------------
# One file that brings any loss back onto a machine installed from nothing:
# the whole database (accounts, settings, events, the list of terminals, the
# certificate and TLS, the firewall), the key its secrets are sealed with,
# the machine's config.json, a manifest with the checksum of each, and
# RESTORE.md - the exact steps. Locked with a password kept in the settings
# (openssl enc, AES-256-CBC, PBKDF2-SHA256: opened with ai, or with openssl
# alone on any machine). RESTORE.md and a .sha256 also go beside it, not
# locked, so the steps can be read before anything is opened.
#
# Where they go: a folder (an NFS or other mount), FTP, FTPS (explicit or
# implicit), SFTP, SCP or SMB, each with its name and password, SSH keys made
# here or brought, the server's host key or certificate checked, a client
# certificate for FTPS; old ones are taken away as kept-count and age say.
RB_KINDS = ('folder', 'ftp', 'ftps', 'sftp', 'scp', 'smb')
RB_KIND_WORDS = {'folder': 'a folder', 'ftp': 'FTP', 'ftps': 'FTPS', 'sftp': 'SFTP',
                 'scp': 'SCP (ssh)', 'smb': 'SMB (Windows share, Samba)'}
RB_PORTS = {'ftp': 21, 'ftps': 21, 'sftp': 22, 'scp': 22, 'smb': 445}
RB_SEALED = ('password', 'key', 'client_key', 'key_pass')
RB_BIND = 'rbackup'
RB_LOCK = threading.Lock()
RB_JOB = {'running': False, 'what': '', 'says': '', 'done': 0, 'whole': 0, 'error': '',
          'began': 0, 'ended': 0, 'result': None, 'by': ''}
RB_ITER = 600000
RB_NAME_RE = re.compile(r'^ai-backup-(?P<site>[A-Za-z0-9_.-]+?)-(?P<node>[A-Za-z0-9_.-]+)-'
                        r'(?P<stamp>\d{8}-\d{6})\.tar\.gz(?P<enc>\.enc)?\Z')
RB_TIMEOUT = 60


class RbError(Exception):
    pass


def rb_clean(text, what, most=200, pattern=None, empty=True):
    t = str(text if text is not None else '').strip()
    if not t and empty:
        return ''
    if len(t) > most or re.search(r'[\x00-\x1f\x7f]', t):
        raise ValueError('%s: at most %d characters, one line' % (what, most))
    if pattern and t and not re.match(pattern, t):
        raise ValueError('%s: %r is not one' % (what, t[:60]))
    return t


def rb_slug(text):
    return re.sub(r'[^A-Za-z0-9_.]+', '_', str(text or 'ai')).strip('_.')[:40] or 'ai'


# ---- the destinations ---------------------------------------------------------------
def rb_targets(store):
    try:
        got = json.loads(store.get_meta('rbackup:targets') or '[]')
    except ValueError:
        got = []
    return [t for t in got if isinstance(t, dict) and t.get('id')]


def rb_put_targets(store, targets):
    store.set_meta('rbackup:targets', json.dumps(targets))


def rb_target(store, tid):
    return next((t for t in rb_targets(store) if t['id'] == str(tid)), None)


def rb_secret(t, k):
    v = t.get(k) or ''
    return (unseal_secret(v, bind=RB_BIND) or '') if v else ''


def ssh_fingerprints(lines):
    """The SHA256 fingerprints of known_hosts lines, as ssh-keygen says them."""
    if not lines.strip() or not shutil.which('ssh-keygen'):
        return []
    got = subprocess.run(['ssh-keygen', '-lf', '-'], input=lines, capture_output=True,
                         text=True, timeout=20)
    return [x.strip() for x in got.stdout.splitlines() if x.strip()]


def rb_view(t):
    """A destination as the pages see it: nothing secret, what it has said."""
    out = {k: v for k, v in t.items() if k not in RB_SEALED}
    for k in RB_SEALED:
        out['has_' + k] = bool(t.get(k))
    out['kind_words'] = RB_KIND_WORDS.get(t.get('kind'), t.get('kind'))
    if t.get('password'):
        out['password'] = secret_shown(rb_secret(t, 'password'), last=True)
    if t.get('hostkey'):
        out['hostkey_fp'] = ssh_fingerprints(t['hostkey'])
    if t.get('client_cert'):
        try:
            out['client_cert_info'] = cert_info(t['client_cert'])
        except Exception:                               # noqa: BLE001
            out['client_cert_info'] = None
    if t.get('ca'):
        try:
            out['ca_info'] = cert_info(t['ca'])
        except Exception:                               # noqa: BLE001
            out['ca_info'] = None
    return out


def rb_checked(data, old=None):
    """A destination as typed on the pages, checked; secrets left out or as
    dots keep what was there."""
    old = dict(old or {})
    if not isinstance(data, dict):
        raise ValueError('a destination is an object')
    kind = str(data.get('kind') or old.get('kind') or '')
    if kind not in RB_KINDS:
        raise ValueError('the kind is one of %s' % ', '.join(RB_KINDS))
    t = {'id': old.get('id') or secrets.token_hex(6), 'kind': kind}
    t['name'] = rb_clean(data.get('name'), 'the name', 60) or \
        ('%s %s' % (RB_KIND_WORDS[kind], data.get('host') or data.get('path') or '')).strip()
    t['enabled'] = 1 if data.get('enabled', old.get('enabled', 1)) else 0
    t['path'] = rb_clean(data.get('path'), 'the folder', 400)
    if kind == 'folder':
        if not t['path'].startswith('/'):
            raise ValueError('the folder is a whole path on this machine (/mnt/backup/ai)')
        if re.search(r'(^|/)\.\.(/|$)', t['path']):
            raise ValueError('the folder has no .. in it')
    else:
        t['host'] = rb_clean(data.get('host'), 'the server', 253,
                             r'^[A-Za-z0-9][A-Za-z0-9.:_-]*\Z', empty=False)
        try:
            port = int(data.get('port') or RB_PORTS.get(kind) or 0)
        except (TypeError, ValueError):
            raise ValueError('the port is a number')
        if kind == 'ftps' and data.get('implicit') and not data.get('port'):
            port = 990
        if not 1 <= port <= 65535:
            raise ValueError('the port is 1 to 65535')
        t['port'] = port
        t['user'] = rb_clean(data.get('user'), 'the account', 128, r'^[^\s:@/\\]+\Z') or ''
        # Nothing a tool on the way reads as more (1.0.136): smbclient takes
        # ; as the next command whatever the quotes, ssh a leading - as an
        # option of its own.
        if t['user'].startswith('-'):
            raise ValueError('the account does not begin with -')
        if re.search(r'[;"]', t['path']) or t['path'].lstrip().startswith('-'):
            raise ValueError('the folder has no ; or " in it, and does not begin with -')
        if kind != 'smb' and re.search(r'(^|/)\.\.(/|$)', t['path']):
            raise ValueError('the folder has no .. in it')
        if kind == 'scp' and re.search(r'[^A-Za-z0-9._/~+@%=,-]', t['path']):
            # scp before OpenSSH 9 hands the far path to the shell there
            # (1.0.139): $( ), `, |, & and spaces ran or broke.
            raise ValueError('the folder (SCP) is letters, digits and . _ / ~ + @ % = , - '
                             'only - use SFTP for any other')
    pw = data.get('password')
    # The saved password goes only to the server it was saved for (1.0.149):
    # with another server typed in, Try it sent it there - to whoever the
    # administrator chose. Typed again for a new one.
    moved = bool(old) and (old.get('kind') != kind or
                           str(old.get('host') or '').lower() != str(t.get('host') or '').lower() or
                           int(old.get('port') or 0) != int(t.get('port') or 0))
    if (pw is None or is_masked(pw)) and moved and old.get('password'):
        raise ValueError('the server changed: type the password again')
    if pw is None or is_masked(pw):
        t['password'] = old.get('password') or ''
    else:
        pw = str(pw)
        if len(pw) > 512 or '\n' in pw or '\x00' in pw:
            raise ValueError('the password is one line, at most 512 characters')
        t['password'] = seal_secret(pw, bind=RB_BIND) if pw else ''
    if kind in ('sftp', 'scp'):
        for k in ('key', 'pub', 'ssh_cert', 'hostkey', 'key_pass'):
            if k in old:
                t[k] = old[k]
        if data.get('ssh_cert') is not None:
            c = str(data.get('ssh_cert') or '').strip()
            if c and not re.match(r'^[a-z0-9@.-]+-cert-v01@openssh\.com AAAA[A-Za-z0-9+/=]+( .*)?\Z',
                                  c):
                raise ValueError('the SSH certificate is the one line of a ...-cert.pub file')
            t['ssh_cert'] = c
    if kind in ('ftp', 'ftps'):
        t['passive'] = 0 if data.get('passive', old.get('passive', 1)) in (0, '0', False) else 1
    if kind == 'ftps':
        t['implicit'] = 1 if data.get('implicit', old.get('implicit')) else 0
        check = str(data.get('tls_check') or old.get('tls_check') or 'system')
        if check not in ('system', 'ca', 'pin', 'none'):
            raise ValueError('the server certificate is checked against system, ca, pin or none')
        t['tls_check'] = check
        for k in ('ca', 'pin', 'client_cert', 'client_key'):
            if k in old:
                t[k] = old[k]
        if data.get('ca') is not None:
            ca = str(data.get('ca') or '').strip()
            if ca and not PEM_CERT.search(ca):
                raise ValueError('the authority is a PEM certificate (-----BEGIN CERTIFICATE-----)')
            t['ca'] = '\n'.join(m.group(0) for m in PEM_CERT.finditer(ca)) + '\n' if ca else ''
        if data.get('pin') is not None:
            pin = re.sub(r'[^0-9A-Fa-f]', '', str(data.get('pin') or '')).lower()
            if pin and len(pin) != 64:
                raise ValueError('the pinned fingerprint is SHA-256: 64 hex digits')
            t['pin'] = pin
        if check == 'ca' and not t.get('ca'):
            raise ValueError('checked against an authority: give its certificate')
        if check == 'pin' and not t.get('pin'):
            raise ValueError('pinned: the fingerprint is needed - Try it shows the server\'s')
    if kind == 'smb':
        t['share'] = rb_clean(data.get('share'), 'the share', 80, r'^[^\\/:*?"<>|;-][^\\/:*?"<>|;]*\Z',
                              empty=False)
        t['domain'] = rb_clean(data.get('domain'), 'the domain', 64, r'^[A-Za-z0-9._-]+\Z')
        t['smb_encrypt'] = 1 if data.get('smb_encrypt', old.get('smb_encrypt', 1)) else 0
        if re.search(r'(^|[\\/])\.\.([\\/]|$)', t['path']):
            raise ValueError('the folder has no .. in it')
    for k in ('last', 'made'):
        if k in old:
            t[k] = old[k]
    return t


def rb_save(store, data, by):
    with RB_LOCK:
        targets = rb_targets(store)
        old = next((x for x in targets if x['id'] == str(data.get('id') or '')), None)
        if data.get('id') and not old:
            raise ValueError('no such destination')
        t = rb_checked(data, old)
        if old:
            targets = [t if x['id'] == t['id'] else x for x in targets]
        else:
            t['made'] = time.time()
            if len(targets) >= 20:
                raise ValueError('20 destinations at most')
            targets.append(t)
        rb_put_targets(store, targets)
    store.add_event('settings', '%s %s the backup destination %s (%s)' % (
        by, 'changed' if old else 'added', t['name'], RB_KIND_WORDS[t['kind']]), who=by)
    return t


def rb_set_fields(store, tid, by, said, **fields):
    with RB_LOCK:
        targets = rb_targets(store)
        t = next((x for x in targets if x['id'] == str(tid)), None)
        if not t:
            raise ValueError('no such destination')
        for k, v in fields.items():
            if v is None:
                t.pop(k, None)
            else:
                t[k] = v
        rb_put_targets(store, targets)
    if said:
        store.add_event('settings', '%s: the backup destination %s - %s' % (by, t['name'], said),
                        who=by)
    return t


def rb_delete(store, tid, by):
    with RB_LOCK:
        targets = rb_targets(store)
        t = next((x for x in targets if x['id'] == str(tid)), None)
        if not t:
            raise ValueError('no such destination')
        rb_put_targets(store, [x for x in targets if x['id'] != t['id']])
    store.add_event('settings', '%s took away the backup destination %s' % (by, t['name']),
                    'warn', who=by)


# ---- keys and certificates ----------------------------------------------------------
def ssh_keygen(comment):
    if not shutil.which('ssh-keygen'):
        raise ValueError('ssh-keygen is not on this machine (dnf install openssh-clients)')
    with tempfile.TemporaryDirectory(prefix='ai-key-') as d:
        path = os.path.join(d, 'k')
        got = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment,
                              '-f', path], capture_output=True, text=True, timeout=30)
        if got.returncode != 0:
            raise ValueError('ssh-keygen: %s' % (got.stderr or got.stdout).strip()[:200])
        with open(path) as f:
            private = f.read()
        with open(path + '.pub') as f:
            public = f.read().strip()
    return private, public


def rb_ssh_public_of(private, passphrase=''):
    """The public half of a private key given - and that it is one."""
    if not shutil.which('ssh-keygen'):
        raise ValueError('ssh-keygen is not on this machine (dnf install openssh-clients)')
    private = str(private or '').replace('\r\n', '\n').strip() + '\n'
    if 'PRIVATE KEY-----' not in private:
        raise ValueError('that is not a private key (-----BEGIN OPENSSH PRIVATE KEY----- or '
                         'another PEM private key)')
    with tempfile.TemporaryDirectory(prefix='ai-key-') as d:
        path = os.path.join(d, 'k')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(private)
        # The passphrase through SSH_ASKPASS, not on the command line where
        # `ps` shows it (1.0.136).
        env = dict(os.environ, DISPLAY=':0', SSH_ASKPASS_REQUIRE='force')
        if passphrase:
            ask = os.path.join(d, 'ask')
            with open(ask, 'w') as f:
                f.write('#!/bin/sh\nprintf "%s\\n" "$AI_RB_SECRET"\n')
            os.chmod(ask, 0o700)
            env.update(SSH_ASKPASS=ask, AI_RB_SECRET=passphrase)
            argv = ['ssh-keygen', '-y', '-f', path]
        else:
            argv = ['ssh-keygen', '-y', '-P', '', '-f', path]
        got = subprocess.run(argv, capture_output=True, text=True, timeout=20, env=env,
                             stdin=subprocess.DEVNULL)
    if got.returncode != 0:
        said = (got.stderr or got.stdout).strip()
        if 'passphrase' in said.lower() or 'incorrect' in said.lower():
            raise ValueError('the key is locked with a passphrase: give it too')
        raise ValueError('ssh-keygen does not read it: %s' % said[:200])
    return private, got.stdout.strip()


def rb_client_cert_make(cn, days=1825):
    """A key and a self-signed client certificate for FTPS."""
    key = new_key('ec')
    with tempfile.TemporaryDirectory(prefix='ai-crt-') as d:
        kf = os.path.join(d, 'k.pem')
        with open(kf, 'w') as f:
            f.write(key)
        os.chmod(kf, 0o600)
        cn = re.sub(r'[^A-Za-z0-9.@_-]', '', str(cn or 'ai-backup'))[:64] or 'ai-backup'
        crt = _openssl(['req', '-new', '-x509', '-key', kf, '-days', str(int(days)), '-subj',
                        '/CN=' + cn, '-addext', 'extendedKeyUsage=clientAuth',
                        '-addext', 'keyUsage=critical,digitalSignature'],
                       what='the certificate').decode()
    return key, crt


def rb_client_cert_given(text, password=''):
    """A client certificate brought: PEM (certificate and key, in any order)
    or PFX (base64 of it, with its password)."""
    text = str(text or '').strip()
    if 'BEGIN' in text:
        certs = [m.group(0) for m in PEM_CERT.finditer(text)]
        m = re.search(r'-----BEGIN (?:[A-Z ]*)PRIVATE KEY-----[\s\S]+?-----END (?:[A-Z ]*)'
                      r'PRIVATE KEY-----', text)
        if not certs or not m:
            raise ValueError('a client certificate needs its certificate and its private key')
        key = m.group(0) + '\n'
        if 'ENCRYPTED' in key:
            key = _openssl(['pkey', '-passin', 'env:AI_PW'], key.encode(),
                           env={'AI_PW': password}, what='the key (its password)').decode()
        if _pub_of_key(key).strip() != _pub_of_cert(certs[0]).strip():
            raise ValueError('the key is not the one of this certificate')
        return key, '\n'.join(certs) + '\n'
    try:
        pfx = base64.b64decode(text, validate=False)
    except (binascii.Error, ValueError):
        raise ValueError('neither PEM nor PFX')
    with tempfile.TemporaryDirectory(prefix='ai-pfx-') as d:
        pf = os.path.join(d, 'c.pfx')
        with open(pf, 'wb') as f:
            f.write(pfx)
        both = ''
        for extra in ([], ['-legacy']):
            try:
                both = _openssl(['pkcs12', '-in', pf, '-nodes', '-passin', 'env:AI_PW'] + extra,
                                env={'AI_PW': password}, what='the PFX (its password?)').decode()
                break
            except ValueError:
                if extra:
                    raise
    return rb_client_cert_given(both)


# ---- the transports ------------------------------------------------------------------
class RbFolder(object):
    def __init__(self, t):
        self.t = t
        self.dir = t['path']

    def open(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
        except OSError as e:
            raise RbError('the folder %s cannot be made: %s' % (self.dir, e))
        if not os.access(self.dir, os.W_OK):
            raise RbError('this machine may not write into %s' % self.dir)

    def put(self, local, name):
        part = os.path.join(self.dir, '.%s.part' % name)
        shutil.copyfile(local, part)
        os.chmod(part, 0o640)
        os.replace(part, os.path.join(self.dir, name))

    def get(self, name, local):
        shutil.copyfile(os.path.join(self.dir, rb_safe_name(name)), local)

    def list(self):
        out = []
        for e in os.scandir(self.dir):
            if e.is_file() and not e.name.startswith('.'):
                st = e.stat()
                out.append({'name': e.name, 'size': st.st_size, 'mtime': st.st_mtime})
        return out

    def delete(self, name):
        os.unlink(os.path.join(self.dir, rb_safe_name(name)))

    def close(self):
        pass


def rb_safe_name(name):
    name = str(name or '')
    if not re.match(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,200}\Z', name):
        raise RbError('not a file name of a backup: %r' % name[:80])
    return name


class _ImplicitFTP_TLS(ftplib.FTP_TLS):
    """FTPS on its own port (990): TLS from the first byte."""
    def connect(self, host='', port=0, timeout=-999, source_address=None):
        if host:
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.af = self.sock.family
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


class _ReuseMixin(object):
    """The data connection resumes the control connection's TLS session:
    vsftpd, ProFTPD and FileZilla Server refuse one that does not (522)."""
    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host,
                                            session=self.sock.session)
        return conn, size


class RbFtpTls(_ReuseMixin, ftplib.FTP_TLS):
    pass


class RbFtpTlsImplicit(_ReuseMixin, _ImplicitFTP_TLS):
    pass


class RbFtp(object):
    def __init__(self, t):
        self.t = t
        self.ftp = None
        self.tmp = None
        self.seen = {}

    def _context(self):
        t = self.t
        check = t.get('tls_check') or 'system'
        if check == 'ca':
            ctx = ssl.create_default_context(cadata=t.get('ca') or '')
        elif check == 'system':
            ctx = ssl.create_default_context()
        else:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if t.get('client_cert') and t.get('client_key'):
            self.tmp = tempfile.mkdtemp(prefix='ai-ftps-')
            cf, kf = os.path.join(self.tmp, 'c.pem'), os.path.join(self.tmp, 'k.pem')
            with open(cf, 'w') as f:
                f.write(t['client_cert'])
            fd = os.open(kf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(rb_secret(t, 'client_key'))
            ctx.load_cert_chain(cf, kf)
        return ctx

    def open(self):
        t = self.t
        try:
            if t['kind'] == 'ftps':
                cls = RbFtpTlsImplicit if t.get('implicit') else RbFtpTls
                self.ftp = cls(context=self._context(), timeout=RB_TIMEOUT)
                self.ftp.connect(t['host'], int(t['port']))
                if not t.get('implicit'):
                    self.ftp.auth()
                der = self.ftp.sock.getpeercert(True)
                fp = hashlib.sha256(der).hexdigest() if der else ''
                self.seen = {'fingerprint': fp}
                try:
                    pem = ssl.DER_cert_to_PEM_cert(der)
                    self.seen['cert'] = cert_info(pem)
                except Exception:                       # noqa: BLE001
                    pass
                if (t.get('tls_check') == 'pin') and fp != (t.get('pin') or ''):
                    raise RbError('the server answers with another certificate than the one '
                                  'pinned (SHA-256 %s)' % fp)
            else:
                self.ftp = ftplib.FTP(timeout=RB_TIMEOUT)
                self.ftp.connect(t['host'], int(t['port']))
            self.ftp.login(t.get('user') or 'anonymous', rb_secret(t, 'password'))
            if t['kind'] == 'ftps':
                self.ftp.prot_p()
            self.ftp.set_pasv(bool(t.get('passive', 1)))
            self._cd(t.get('path') or '')
        except ssl.SSLCertVerificationError as e:
            raise RbError('the server\'s certificate is not trusted: %s - check it against '
                          'its authority, or pin it' % e.verify_message)
        except ftplib.error_perm as e:
            raise RbError('the FTP server said: %s' % str(e)[:200])
        except (OSError, EOFError, ftplib.Error) as e:
            raise RbError(str(e)[:200] or e.__class__.__name__)

    def _cd(self, path):
        if not path:
            return
        if path.startswith('/'):
            self.ftp.cwd('/')
        for part in [p for p in path.split('/') if p]:
            try:
                self.ftp.cwd(part)
            except ftplib.error_perm:
                self.ftp.mkd(part)
                self.ftp.cwd(part)

    def put(self, local, name):
        with open(local, 'rb') as f:
            self.ftp.storbinary('STOR .%s.part' % name, f, blocksize=262144)
        try:
            self.ftp.delete(name)
        except ftplib.error_perm:
            pass
        self.ftp.rename('.%s.part' % name, name)

    def get(self, name, local):
        with open(local, 'wb') as f:
            self.ftp.retrbinary('RETR %s' % rb_safe_name(name), f.write, blocksize=262144)

    def list(self):
        out = []
        try:
            for name, facts in self.ftp.mlsd(facts=['type', 'size', 'modify']):
                if facts.get('type') == 'file':
                    m = facts.get('modify') or ''
                    try:
                        mt = datetime.strptime(m[:14], '%Y%m%d%H%M%S').replace(
                            tzinfo=timezone.utc).timestamp()
                    except ValueError:
                        mt = 0
                    out.append({'name': name, 'size': int(facts.get('size') or 0), 'mtime': mt})
            return out
        except ftplib.error_perm:
            pass
        for name in self.ftp.nlst():
            name = name.rsplit('/', 1)[-1]
            if name in ('.', '..'):
                continue
            try:
                size = self.ftp.size(name) or 0
            except ftplib.error_perm:
                continue            # a folder
            out.append({'name': name, 'size': size, 'mtime': 0})
        return out

    def delete(self, name):
        self.ftp.delete(rb_safe_name(name))

    def close(self):
        try:
            if self.ftp:
                self.ftp.quit()
        except Exception:                               # noqa: BLE001
            try:
                self.ftp.close()
            except Exception:                           # noqa: BLE001
                pass
        if self.tmp:
            shutil.rmtree(self.tmp, ignore_errors=True)


def ssh_keyscan(host, port):
    """The server's host keys, as known_hosts lines - and their fingerprints."""
    if not shutil.which('ssh-keyscan'):
        raise ValueError('ssh-keyscan is not on this machine (dnf install openssh-clients)')
    got = subprocess.run(['ssh-keyscan', '-T', '10', '-p', str(int(port)), host],
                         capture_output=True, text=True, timeout=30)
    lines = [x for x in got.stdout.splitlines() if x.strip() and not x.startswith('#')]
    if not lines:
        raise ValueError('%s:%s did not show a host key: %s' % (
            host, port, (got.stderr or '').strip().splitlines()[-1:] or 'no answer'))
    return '\n'.join(lines) + '\n', ssh_fingerprints('\n'.join(lines) + '\n')


class RbSsh(object):
    """SFTP (the sftp program) or SCP (scp, and ssh for the list and the
    deleting) - OpenSSH itself, the server's host key checked against the one
    trusted on the pages, a key of its own or a password."""
    def __init__(self, t):
        self.t = t
        self.d = None

    def open(self):
        t = self.t
        tools = ['ssh'] + (['sftp'] if t['kind'] == 'sftp' else ['scp'])
        for tool in tools:
            if not shutil.which(tool):
                raise RbError('%s is not on this machine (dnf install openssh-clients)' % tool)
        if not t.get('hostkey'):
            raise RbError('the server\'s host key is not trusted yet: Try it, then trust the '
                          'fingerprint it shows')
        self.d = tempfile.mkdtemp(prefix='ai-ssh-')
        kh = os.path.join(self.d, 'known_hosts')
        with open(kh, 'w') as f:
            f.write(t['hostkey'])
        self.opts = ['-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + kh,
                     '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=20',
                     '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=4',
                     '-o', 'LogLevel=ERROR', '-o', 'IdentitiesOnly=yes', '-F', '/dev/null']
        key = rb_secret(t, 'key')
        if key:
            kf = os.path.join(self.d, 'id')
            fd = os.open(kf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(key if key.endswith('\n') else key + '\n')
            self.opts += ['-i', kf]
            if t.get('ssh_cert'):
                cf = os.path.join(self.d, 'id-cert.pub')
                with open(cf, 'w') as f:
                    f.write(t['ssh_cert'] + '\n')
                self.opts += ['-o', 'CertificateFile=' + cf]
        else:
            self.opts += ['-o', 'IdentityFile=/dev/null']
        # A password (or the key's passphrase) through SSH_ASKPASS: never on
        # a command line, never in a file of anybody's.
        self.env = dict(os.environ, DISPLAY=':0', SSH_ASKPASS_REQUIRE='force')
        # Each prompt its own answer (1.0.139): with a password and a key that
        # has a passphrase, the password went to the key, and the key failed.
        pw = rb_secret(t, 'password') or rb_secret(t, 'key_pass')
        kp = rb_secret(t, 'key_pass') or rb_secret(t, 'password')
        ask = os.path.join(self.d, 'ask')
        with open(ask, 'w') as f:
            f.write('#!/bin/sh\ncase "$1" in\n  *assphrase*) printf "%s\\n" "$AI_RB_KEYPASS";;\n'
                    '  *) printf "%s\\n" "$AI_RB_SECRET";;\nesac\n')
        os.chmod(ask, 0o700)
        self.env.update(SSH_ASKPASS=ask, AI_RB_SECRET=pw, AI_RB_KEYPASS=kp)
        auths = ['publickey'] if key else []
        if rb_secret(t, 'password'):
            auths += ['password', 'keyboard-interactive']
        if not auths:
            raise RbError('neither a key nor a password is set')
        self.opts += ['-o', 'PreferredAuthentications=' + ','.join(auths),
                      '-o', 'NumberOfPasswordPrompts=1']
        if rb_secret(t, 'password') or rb_secret(t, 'key_pass'):
            # sftp -b asks ssh for batch mode, which takes no password; the
            # first value given wins, and this comes first.
            self.opts += ['-o', 'BatchMode=no']
        host = str(t['host']).strip('[]')
        self.dest = '%s@%s' % (t.get('user') or 'root', host)
        # scp and sftp read user@host:path - an IPv6 address in brackets
        # there (1.0.146), ssh takes it bare.
        self.rdest = '%s@[%s]' % (t.get('user') or 'root', host) if ':' in host else self.dest
        self.dir = (t.get('path') or '').rstrip('/') or '.'
        # Signed in and the folder made, at once - the errors said here.
        if t['kind'] == 'sftp':
            parts = [p for p in self.dir.split('/') if p and p != '.']
            cmds = []
            acc = '/' if self.dir.startswith('/') else ''
            for p in parts:
                acc = (acc + '/' + p) if acc not in ('', '/') else (acc + p)
                cmds.append('-mkdir "%s"' % acc)
            cmds.append('cd "%s"' % self.dir)
            self._sftp(cmds)
        else:
            self._ssh('mkdir -p -- %s && test -w %s' % (shlex.quote(self.dir),
                                                        shlex.quote(self.dir)))

    def _run(self, args, what, stdin=None, timeout=3600):
        got = subprocess.run(args, input=stdin, capture_output=True, text=True,
                             timeout=timeout, env=self.env, start_new_session=True)
        if got.returncode != 0:
            said = (got.stderr or got.stdout or '').strip().splitlines()
            said = [x for x in said if x.strip() and not x.startswith('Warning: Permanently')]
            tail = ' / '.join(said[-3:])[:300] or 'it said nothing (exit %d)' % got.returncode
            if 'Host key verification failed' in tail or 'REMOTE HOST IDENTIFICATION' in tail:
                tail = ('the server shows another host key than the one trusted - if it was '
                        'reinstalled on purpose, Try it and trust the new one')
            elif 'Permission denied' in tail:
                tail = 'the server did not let the account in (%s)' % tail
            raise RbError('%s: %s' % (what, tail))
        return got.stdout

    def _ssh(self, command):
        return self._run(['ssh'] + self.opts + ['-p', str(int(self.t['port'])), self.dest,
                                                command], 'ssh')

    def _sftp(self, cmds, timeout=3600):
        batch = os.path.join(self.d, 'batch')
        with open(batch, 'w') as f:
            f.write('\n'.join(cmds) + '\n')
        return self._run(['sftp'] + self.opts + ['-P', str(int(self.t['port'])), '-b', batch,
                                                 self.rdest], 'sftp', timeout=timeout)

    def put(self, local, name):
        name = rb_safe_name(name)
        if self.t['kind'] == 'sftp':
            self._sftp(['cd "%s"' % self.dir, 'put "%s" ".%s.part"' % (local, name),
                        '-rm "%s"' % name, 'rename ".%s.part" "%s"' % (name, name)])
        else:
            self._run(['scp'] + self.opts + ['-P', str(int(self.t['port'])), '-q', local,
                                             '%s:%s/.%s.part' % (self.rdest, self.dir, name)],
                      'scp')
            self._ssh('mv -f -- %s %s' % (shlex.quote('%s/.%s.part' % (self.dir, name)),
                                          shlex.quote('%s/%s' % (self.dir, name))))

    def get(self, name, local):
        name = rb_safe_name(name)
        if self.t['kind'] == 'sftp':
            self._sftp(['cd "%s"' % self.dir, 'get "%s" "%s"' % (name, local)])
        else:
            self._run(['scp'] + self.opts + ['-P', str(int(self.t['port'])), '-q',
                                             '%s:%s/%s' % (self.rdest, self.dir, name), local],
                      'scp')

    def list(self):
        if self.t['kind'] == 'sftp':
            text = self._sftp(['cd "%s"' % self.dir, 'ls -ln'])
        else:
            text = self._ssh('LC_ALL=C ls -ln -- %s' % shlex.quote(self.dir))
        out = []
        for line in text.splitlines():
            f = line.split(None, 8)
            if len(f) == 9 and f[0].startswith('-'):
                name = f[8].rsplit('/', 1)[-1]
                try:
                    out.append({'name': name, 'size': int(f[4]), 'mtime': 0})
                except ValueError:
                    pass
        return out

    def delete(self, name):
        name = rb_safe_name(name)
        if self.t['kind'] == 'sftp':
            self._sftp(['cd "%s"' % self.dir, 'rm "%s"' % name])
        else:
            self._ssh('rm -f -- %s' % shlex.quote('%s/%s' % (self.dir, name)))

    def close(self):
        if self.d:
            shutil.rmtree(self.d, ignore_errors=True)


class RbSmb(object):
    """SMB through smbclient: an authentication file of its own (never the
    password on a command line), SMB2 at least, SMB3 encryption when asked."""
    def __init__(self, t):
        self.t = t
        self.d = None

    def open(self):
        t = self.t
        if not shutil.which('smbclient'):
            raise RbError('smbclient is not on this machine (dnf install samba-client)')
        self.d = tempfile.mkdtemp(prefix='ai-smb-')
        auth = os.path.join(self.d, 'auth')
        fd = os.open(auth, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write('username = %s\npassword = %s\n' % (t.get('user') or 'guest',
                                                       rb_secret(t, 'password')))
            if t.get('domain'):
                f.write('domain = %s\n' % t['domain'])
        self.args = ['smbclient', '//%s/%s' % (t['host'], t['share']), '-A', auth,
                     '-p', str(int(t['port'])), '--option=client min protocol=SMB2',
                     '-t', str(RB_TIMEOUT)]
        if t.get('smb_encrypt'):
            self.args += ['--client-protection=encrypt']
        self.dir = (t.get('path') or '').replace('/', '\\').strip('\\')
        cmds = []
        acc = ''
        for p in [x for x in self.dir.split('\\') if x]:
            acc = (acc + '\\' + p) if acc else p
            cmds.append('mkdir "%s"' % acc)
        self._run(cmds + ['cd "\\%s"' % self.dir, 'ls'], ignore=('NT_STATUS_OBJECT_NAME_COLLISION',))

    def _run(self, cmds, ignore=(), timeout=3600):
        got = subprocess.run(self.args + ['-c', '; '.join(cmds)], capture_output=True, text=True,
                             timeout=timeout, cwd=self.d, start_new_session=True)
        text = (got.stdout or '') + (got.stderr or '')
        bad = [x for x in text.splitlines() if 'NT_STATUS_' in x and
               not any(i in x for i in ignore)]
        if got.returncode != 0 or bad:
            said = ' / '.join((bad or text.strip().splitlines() or ['no answer'])[-2:])[:300]
            if 'NT_STATUS_LOGON_FAILURE' in said:
                said = 'the server did not take the account and password (%s)' % said
            elif 'NT_STATUS_BAD_NETWORK_NAME' in said:
                said = 'there is no share %s on %s' % (self.t['share'], self.t['host'])
            elif 'protection' in said.lower() and 'unknown' in said.lower():
                said = ('this smbclient does not know --client-protection: switch "SMB3 '
                        'encryption required" off or install a newer samba-client')
            raise RbError('smbclient: %s' % said)
        return got.stdout or ''

    def _cd(self):
        return 'cd "\\%s"' % self.dir

    def put(self, local, name):
        name = rb_safe_name(name)
        self._run([self._cd(), 'put "%s" ".%s.part"' % (local, name), 'del "%s"' % name,
                   'rename ".%s.part" "%s"' % (name, name)], ignore=('NT_STATUS_NO_SUCH_FILE',
                                                                   'NT_STATUS_OBJECT_NAME_NOT_FOUND'))

    def get(self, name, local):
        self._run([self._cd(), 'get "%s" "%s"' % (rb_safe_name(name), local)])

    def list(self):
        out = []
        for line in self._run([self._cd(), 'ls']).splitlines():
            m = re.match(r'^\s\s(.+?)\s+([ADHNRS]*)\s+(\d+)\s+(\w{3} \w{3}\s+\d+ [\d:]+ \d{4})\s*$',
                         line)
            if m and 'D' not in m.group(2) and m.group(1) not in ('.', '..'):
                try:
                    mt = datetime.strptime(re.sub(r'\s+', ' ', m.group(4)),
                                           '%a %b %d %H:%M:%S %Y').timestamp()
                except ValueError:
                    mt = 0
                out.append({'name': m.group(1), 'size': int(m.group(3)), 'mtime': mt})
        return out

    def delete(self, name):
        self._run([self._cd(), 'del "%s"' % rb_safe_name(name)])

    def close(self):
        if self.d:
            shutil.rmtree(self.d, ignore_errors=True)


def rb_said(e):
    """An error in words, whatever library raised it."""
    if isinstance(e, EOFError):
        return 'the server closed the connection'
    if isinstance(e, socket.timeout):
        return 'the server did not answer in time'
    if isinstance(e, ssl.SSLCertVerificationError):
        return ('the server\'s certificate is not trusted: %s - check it against its authority, '
                'or pin it' % e.verify_message)
    if isinstance(e, ftplib.Error):
        return 'the FTP server said: %s' % str(e)[:300]
    return scrub_secret(str(e) or e.__class__.__name__)[:400]


def rb_transport(t):
    return {'folder': RbFolder, 'ftp': RbFtp, 'ftps': RbFtp, 'sftp': RbSsh, 'scp': RbSsh,
            'smb': RbSmb}[t['kind']](t)


def rb_try(t):
    """Signed in, a small file written, seen in the list, taken away again."""
    out = {'ok': False, 'steps': []}
    began = time.time()
    tr = rb_transport(t)
    try:
        tr.open()
        out['steps'].append('signed in, the folder is there')
        if getattr(tr, 'seen', None):
            out['server_cert'] = tr.seen
        name = 'ai-try-%s-%s.txt' % (rb_slug(node_name()), secrets.token_hex(4))
        with tempfile.NamedTemporaryFile('w', prefix='ai-try-', delete=False) as f:
            f.write('ai %s on %s tried this destination at %s - this file is taken away again\n'
                    % (__version__, node_name(), datetime.now().isoformat(timespec='seconds')))
            local = f.name
        try:
            tr.put(local, name)
        finally:
            os.unlink(local)
        out['steps'].append('a file written')
        names = [x['name'] for x in tr.list()]
        if name not in names:
            raise RbError('the file written is not in the list the server gives')
        out['steps'].append('it is in the list (%d file(s) there)' % len(names))
        tr.delete(name)
        out['steps'].append('taken away again')
        out['ok'] = True
    except Exception as e:                              # noqa: BLE001
        out['error'] = rb_said(e)
        if getattr(tr, 'seen', None):
            out['server_cert'] = tr.seen
    finally:
        tr.close()
    out['secs'] = round(time.time() - began, 1)
    return out


# ---- the backup itself -----------------------------------------------------------------
def secret_shown(value, last=True):
    said = str(value or '')
    if not said:
        return ''
    if not last:
        return '••••••••'
    return '•' * min(10, max(4, len(said) - 2)) + said[-2:] if len(said) > 4 else '•' * 6


def is_masked(value):
    return isinstance(value, str) and value.startswith('•')


def rb_password():
    pw = str(CONFIG.get('rbackup_password') or '')
    return (unseal_secret(pw, 'setting:rbackup_password') or '') if pw else ''


def rb_restore_md(m):
    """RESTORE.md: the exact steps, filled in with what this backup is."""
    enc = m.get('encrypted')
    name = m['file']
    tar = name[:-4] if enc else name
    site, node, ver = m.get('site') or 'ai', m.get('node') or '?', m.get('ai') or '?'
    lines = [
        '# Restoring ai from %s' % name, '',
        '| | |', '|---|---|',
        '| Made | %s |' % m.get('made_words'),
        '| Installation | %s |' % site,
        '| Server | %s (%s) |' % (node, m.get('host') or ''),
        '| ai | %s |' % ver,
        '| Locked | %s |' % ('yes - AES-256-CBC, PBKDF2-SHA256, %d rounds (openssl enc)' % RB_ITER if enc else
                             '**no** - anybody with the file has every secret: keep it as you would the server'),
        '| Accounts | %s |' % m.get('accounts', '?'),
        '', 'Everything is in it: the whole database (the accounts of the pages and their second step,',
        'every setting, the events, the list of terminals, the certificate and TLS of the pages, the',
        'firewall, who may reach the pages), the key its secrets are sealed with (`secrets.key`) and',
        'this machine\'s `/etc/ai/config.json`. Not in it: the files of the Linux accounts and their',
        'Claude Code (`~/.claude`) - back those up as files.', '',
        'Keep the password of the backups apart from the backups (a password vault): without it',
        'the file cannot be opened - by anybody.', '',
        '## 0. Check the file', '', '```bash',
        'sha256sum -c %s.sha256          # "%s: OK"' % (name, name), '```', '',
    ]
    if enc:
        lines += ['## 1. Open it', '',
                  'ai opens it by itself (step 3). With openssl alone, on any machine:', '',
                  '```bash',
                  'openssl enc -d -aes-256-cbc -pbkdf2 -iter %d -md sha256 -in %s -out %s' % (RB_ITER, name, tar),
                  '# it asks for the password of the backups',
                  'tar tzf %s                    # what is inside' % tar, '```', '']
    else:
        lines += ['## 1. It is not locked', '', '```bash', 'tar tzf %s' % tar, '```', '']
    lines += [
        'Inside: `ai-copy.json.gz` (the database, in a shape SQLite, MariaDB and PostgreSQL all take),',
        '`secrets.key`, `config.json`, `manifest.json` (a checksum of each file) and this file.', '',
        '## 2. A machine to put it on', '',
        'AlmaLinux / Rocky / RHEL 9 or Debian / Ubuntu. Install ai **%s or newer** the same way as' % ver,
        'the first time:', '', '```bash',
        'curl -fsSL https://raw.githubusercontent.com/falco81/AI/main/install.sh -o install.sh',
        'bash install.sh', '```', '',
        '## 3. Put it back', '', '```bash',
        'ai --restore-bundle %s          # shows what is in it, asks for the password' % name,
        'ai --restore-bundle %s --yes    # puts it back' % name,
        'systemctl restart ai', '```', '',
        'The password may come from the environment instead (`AI_BACKUP_PASSWORD`).', '',
        'What it does: a copy of what the new machine has is made first (/var/lib/ai/copies); then',
        'the database is replaced with the one in the backup and `secrets.key` is put in place.', '',
        '## By hand, without --restore-bundle', '', '```bash',
        'systemctl stop ai',
        'install -m 0600 secrets.key /var/lib/ai/secrets.key',
        'systemctl start ai',
        'ai --db-restore ai-copy.json.gz --yes   # into whichever database this machine uses', '```', '',
        '## 4. Check it', '', '```bash', 'ai --status', 'ai --users', '```', '',
        'Then sign in to the pages with an account from the backup.', '',
        '---', 'Made by ai %s on %s. The whole subject: docs/backups.md in the package.' % (__version__, node), '']
    return '\n'.join(lines)


def rb_manifest(store, base):
    pw = rb_password()
    try:
        accounts = len(store.users())
    except Exception:                                   # noqa: BLE001
        accounts = '?'
    return {'ai': __version__, 'made': time.time(),
            'made_words': datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z').strip(),
            'site': CONFIG.get('site_name') or 'ai', 'node': node_name(), 'host': socket.getfqdn(),
            'accounts': accounts, 'encrypted': bool(pw), 'iter': RB_ITER if pw else 0,
            'file': base + ('.tar.gz.enc' if pw else '.tar.gz'), 'files': {}}


def rb_base():
    return 'ai-backup-%s-%s-%s' % (rb_slug(CONFIG.get('site_name') or 'ai'), rb_slug(node_name()),
                                   datetime.now().strftime('%Y%m%d-%H%M%S'))


def rb_restore_guide(store):
    m = rb_manifest(store, rb_base())
    return {'md': rb_restore_md(m), 'name': 'RESTORE-%s.md' % rb_slug(node_name()), 'file': m['file']}


def rb_build(store, work, progress=None):
    """The backup, built in `work`: (path of the file to send, manifest, RESTORE.md)."""
    import tarfile

    def say(n, t):
        if progress:
            progress(n, 6, t)
    base = rb_base()
    inner = os.path.join(work, 'in')
    os.makedirs(inner, mode=0o700)
    say(1, 'the database is copied')
    # A copy any of the three engines takes back (otp's), not the engine's own file.
    dump_tables(store.db, os.path.join(inner, 'ai-copy.json.gz'))
    key = sealing_key(make=True)
    with open(os.path.join(inner, 'secrets.key'), 'w') as f:
        f.write(key.hex() + '\n')
    if CONFIG_FILE.is_file():
        shutil.copyfile(str(CONFIG_FILE), os.path.join(inner, 'config.json'))
    say(2, 'what is in it is counted')
    pw = rb_password()
    m = rb_manifest(store, base)
    for n in sorted(os.listdir(inner)):
        p = os.path.join(inner, n)
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        m['files'][n] = {'sha256': h.hexdigest(), 'bytes': os.path.getsize(p)}
    md = rb_restore_md(m)
    with open(os.path.join(inner, 'RESTORE.md'), 'w') as f:
        f.write(md)
    with open(os.path.join(inner, 'manifest.json'), 'w') as f:
        json.dump(m, f, indent=2, default=str)
    say(3, 'packed')
    tar = os.path.join(work, base + '.tar.gz')
    with tarfile.open(tar, 'w:gz', compresslevel=6) as tf:
        for n in sorted(os.listdir(inner)):
            tf.add(os.path.join(inner, n), arcname='%s/%s' % (base, n))
    shutil.rmtree(inner, ignore_errors=True)
    out = tar
    if pw:
        say(4, 'locked with the password of the backups')
        out = tar + '.enc'
        _openssl(['enc', '-aes-256-cbc', '-pbkdf2', '-iter', str(RB_ITER), '-md', 'sha256',
                  '-salt', '-in', tar, '-out', out, '-pass', 'env:AI_RB_PASS'],
                 env={'AI_RB_PASS': pw}, what='locking it')
        os.unlink(tar)
    h = hashlib.sha256()
    with open(out, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    m['sha256'] = h.hexdigest()
    m['bytes'] = os.path.getsize(out)
    with open(os.path.join(work, m['file'] + '.sha256'), 'w') as f:
        f.write('%s  %s\n' % (m['sha256'], m['file']))
    with open(os.path.join(work, base + '-RESTORE.md'), 'w') as f:
        f.write(md)
    return out, m, md


def rb_companions(name):
    if not RB_NAME_RE.match(name):
        return []
    base = name.split('.tar.gz')[0]
    return [name + '.sha256', base + '-RESTORE.md']


def rb_retain(tr, keep, days, now=None):
    """This server's backups at a destination beyond what is kept, taken away -
    never the newest."""
    now = now or time.time()
    mine = rb_slug(node_name())
    files = tr.list()
    names = set(x['name'] for x in files)
    ours = []
    for x in files:
        m = RB_NAME_RE.match(x['name'])
        if m and m.group('node') == mine and m.group('site') == rb_slug(CONFIG.get('site_name') or 'ai'):
            try:
                when_ = datetime.strptime(m.group('stamp'), '%Y%m%d-%H%M%S').timestamp()
            except ValueError:
                continue
            ours.append((when_, x['name']))
    ours.sort(reverse=True)
    gone = []
    for i, (when_, name) in enumerate(ours):
        if i == 0:
            continue
        if (keep and i >= keep) or (days and now - when_ > days * 86400):
            for n in [name] + [c for c in rb_companions(name) if c in names]:
                try:
                    tr.delete(n)
                except Exception:                       # noqa: BLE001
                    pass
            gone.append(name)
    return gone


def rb_run(store, by, only=None, progress=None):
    """Made once, sent to every destination switched on (or the ones asked)."""
    targets = [t for t in rb_targets(store) if (only and t['id'] in only) or (not only and t.get('enabled'))]
    if not targets:
        raise RbError('no destination is switched on')
    # Never sent unlocked: it holds the key every secret is sealed with.
    if not rb_password():
        raise RbError('the backups have no password: set one (Settings - Backups) - unlocked, a copy would '
                      'hand every secret of this server to whoever can read the destination')
    work = tempfile.mkdtemp(prefix='ai-rbackup-', dir=str(STATE_DIR))
    os.chmod(work, 0o700)
    began = time.time()
    run_ = {'at': began, 'by': by, 'node': node_name(), 'targets': [], 'ok': False}
    try:
        path, m, _md = rb_build(store, work, progress)
        run_.update(file=m['file'], bytes=m['bytes'], encrypted=m['encrypted'], accounts=m['accounts'])
        sha = os.path.join(work, m['file'] + '.sha256')
        md = os.path.join(work, m['file'].split('.tar.gz')[0] + '-RESTORE.md')
        for i, t in enumerate(targets):
            if progress:
                progress(5, 6, 'sent to %s (%d of %d)' % (t['name'], i + 1, len(targets)))
            one = {'id': t['id'], 'name': t['name'], 'kind': t['kind'], 'ok': False}
            t0 = time.time()
            tr = rb_transport(t)
            try:
                tr.open()
                tr.put(path, m['file'])
                tr.put(sha, os.path.basename(sha))
                tr.put(md, os.path.basename(md))
                got = {x['name']: x['size'] for x in tr.list()}
                if got.get(m['file']) not in (None, m['bytes']):
                    raise RbError('the server holds %s bytes of it, not %s' % (got.get(m['file']), m['bytes']))
                one['ok'] = True
                try:
                    one['taken_away'] = rb_retain(tr, int(CONFIG.get('rbackup_keep') or 0),
                                                  int(CONFIG.get('rbackup_keep_days') or 0))
                except Exception as e:                  # noqa: BLE001
                    one['retain_error'] = str(e)[:200]
            except Exception as e:                      # noqa: BLE001
                one['error'] = rb_said(e)
            finally:
                tr.close()
            one['secs'] = round(time.time() - t0, 1)
            run_['targets'].append(one)
            rb_set_fields(store, t['id'], '', '', last={'at': time.time(), 'ok': one['ok'],
                                                        'error': one.get('error') or '',
                                                        'file': m['file'], 'bytes': m['bytes']})
        run_['ok'] = all(x['ok'] for x in run_['targets'])
    except (RbError, OSError, ValueError, subprocess.SubprocessError) as e:
        run_['error'] = scrub_secret(str(e))[:400]
    finally:
        shutil.rmtree(work, ignore_errors=True)
    run_['secs'] = round(time.time() - began, 1)
    rb_history_add(store, run_)
    good = [x['name'] for x in run_['targets'] if x['ok']]
    bad = ['%s (%s)' % (x['name'], x.get('error')) for x in run_['targets'] if not x['ok']]
    store.add_event('backups', 'a backup of %s (%s) %s%s%s' % (
        node_name(), human_bytes(run_.get('bytes') or 0), ('went to ' + ', '.join(good)) if good else 'went nowhere',
        ('; not to ' + '; '.join(bad)) if bad else '', ('; ' + run_['error']) if run_.get('error') else ''),
        'info' if run_['ok'] else 'error', who=by)
    return run_


def rb_history(store):
    got = store.meta_json('rbackup:runs', []) or []
    return [x for x in got if isinstance(x, dict)]


def rb_history_forget(store, at=None, file=None):
    with RB_LOCK:
        runs = rb_history(store)
        if at is None:
            left = []
        else:
            left = [r for r in runs if not (abs(float(r.get('at') or 0) - float(at)) < 0.001 and
                                           str(r.get('file') or '') == str(file or ''))]
        store.set_meta_json('rbackup:runs', left)
        return len(runs) - len(left)


def rb_history_add(store, run_):
    with RB_LOCK:
        store.set_meta_json('rbackup:runs', ([run_] + rb_history(store))[:60])


def rb_job_start(store, by, only=None, what='backup', work=None):
    """In a thread of its own; the page follows RB_JOB."""
    with RB_LOCK:
        if RB_JOB['running']:
            raise ValueError('a backup is being made or put back already')
        RB_JOB.update(running=True, what=what, says='starting', done=0, whole=6, error='',
                      began=time.time(), ended=0, result=None, by=by)

    def progress(done, whole, says):
        RB_JOB.update(done=done, whole=whole, says=says)

    def go():
        try:
            RB_JOB['result'] = work(progress) if work else rb_run(store, by, only, progress)
            if isinstance(RB_JOB['result'], dict) and RB_JOB['result'].get('error'):
                RB_JOB['error'] = RB_JOB['result']['error']
        except Exception as e:                          # noqa: BLE001
            RB_JOB['error'] = scrub_secret(str(e))[:400]
            log('remote backup: %s' % e, 'error')
        finally:
            RB_JOB.update(running=False, ended=time.time())
    threading.Thread(target=go, name='rbackup', daemon=True).start()
    return dict(RB_JOB)


def rb_due(last_day):
    if not CONFIG.get('rbackup'):
        return None
    try:
        hh, mm = (int(x) for x in str(CONFIG.get('rbackup_at') or '04:15').split(':', 1))
    except ValueError:
        hh, mm = 4, 15
    now = datetime.now()
    if (now.hour, now.minute) < (hh, mm):
        return None
    if str(CONFIG.get('rbackup_every') or 'daily') == 'weekly' and now.isoweekday() != int(CONFIG.get('rbackup_day') or 7):
        return None
    today = now.strftime('%Y-%m-%d')
    return today if today != last_day else None


def rb_tick(daemon):
    """From the daemon's loop: the scheduled backup."""
    store = daemon.store
    day = rb_due(store.get_meta('rbackup:day') or '')
    if not day or RB_JOB['running']:
        return
    store.set_meta('rbackup:day', day)
    if not any(t.get('enabled') for t in rb_targets(store)):
        return
    rb_job_start(store, 'ai (scheduled)')


def rb_next_words():
    if not CONFIG.get('rbackup'):
        return ''
    from datetime import timedelta
    try:
        hh, mm = (int(x) for x in str(CONFIG.get('rbackup_at') or '04:15').split(':', 1))
    except ValueError:
        hh, mm = 4, 15
    now = datetime.now()
    nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    if str(CONFIG.get('rbackup_every')) == 'weekly':
        want = int(CONFIG.get('rbackup_day') or 7)
        while nxt.isoweekday() != want:
            nxt += timedelta(days=1)
    return nxt.isoformat(timespec='minutes')


# ---- putting one back -----------------------------------------------------------------
def rb_open(path, password, work):
    """A backup file opened into `work`: its folder and its manifest - every
    file checked against the checksum the manifest has."""
    import tarfile
    src = path
    with open(path, 'rb') as f:
        head = f.read(8)
    if head.startswith(b'Salted__'):
        if not password:
            raise RbError('the backup is locked: its password is needed')
        src = os.path.join(work, 'b.tar.gz')
        try:
            _openssl(['enc', '-d', '-aes-256-cbc', '-pbkdf2', '-iter', str(RB_ITER), '-md', 'sha256',
                      '-in', path, '-out', src, '-pass', 'env:AI_RB_PASS'], env={'AI_RB_PASS': password},
                     what='opening it')
        except ValueError:
            raise RbError('the password does not open it (or the file is damaged)')
    elif not head.startswith(b'\x1f\x8b'):
        raise RbError('that is not a backup of ai (neither locked nor a .tar.gz)')
    elif password:
        raise RbError('the backup is not locked, and backups of ai always are - it was not made by ai; not put in')
    out = os.path.join(work, 'x')
    os.makedirs(out, mode=0o700)
    with tarfile.open(src, 'r:gz') as tf:
        members = tf.getmembers()
        tops = set()
        for mb in members:
            parts = mb.name.split('/')
            if mb.name.startswith('/') or '..' in parts or not (mb.isfile() or mb.isdir()):
                raise RbError('the archive has a file it may not have: %r' % mb.name[:100])
            tops.add(parts[0])
        if len(tops) != 1:
            raise RbError('the archive is not one backup')
        total = sum(mb.size for mb in members if mb.isfile())
        try:
            free = shutil.disk_usage(work).free
        except OSError:
            free = None
        if free is not None and total > free - 256 * 1024 * 1024:
            raise RbError('unpacked it is %s, more than there is room for here (%s free)'
                          % (human_bytes(total), human_bytes(max(0, free))))
        for mb in members:
            if mb.isfile():
                dst = os.path.join(out, *mb.name.split('/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with tf.extractfile(mb) as s, open(dst, 'wb') as d:
                    shutil.copyfileobj(s, d)
    top = os.path.join(out, tops.pop())
    try:
        with open(os.path.join(top, 'manifest.json')) as f:
            m = json.load(f)
    except (OSError, ValueError):
        raise RbError('there is no manifest in it')
    for rel, want in (m.get('files') or {}).items():
        p = os.path.join(top, *rel.split('/'))
        h = hashlib.sha256()
        try:
            with open(p, 'rb') as f:
                for chunk in iter(lambda: f.read(1 << 20), b''):
                    h.update(chunk)
        except OSError:
            raise RbError('%s is missing from it' % rel)
        if h.hexdigest() != want.get('sha256'):
            raise RbError('%s is damaged (its checksum is not the one in the manifest)' % rel)
    if not os.path.exists(os.path.join(top, 'ai-copy.json.gz')) and not os.path.exists(os.path.join(top, 'ai.db')):
        raise RbError('there is no database in it - is it a backup of ai?')
    return top, m


def rb_restore(daemon, path, password, by):
    """Everything in a backup put back on this machine: the database and the
    key of its secrets. A copy of what is here is made first."""
    work = tempfile.mkdtemp(prefix='ai-putback-', dir=str(STATE_DIR))
    os.chmod(work, 0o700)
    try:
        top, m = rb_open(path, password, work)
        inner = os.path.join(top, 'ai-copy.json.gz')
        if not os.path.exists(inner):
            inner = os.path.join(top, 'ai.db')          # a backup of 1.0.4-1.0.5: a SQLite file
        keyf = os.path.join(top, 'secrets.key')
        got = db_file_restore(daemon.store, inner, by, key_file=keyf if os.path.exists(keyf) else None,
                              from_name=os.path.basename(str(path)), need_admin=False)
        before = got['safety']
        daemon.store.add_event('backups', '%s put back the backup %s (made %s on %s, ai %s)' % (
            by, os.path.basename(str(path)), m.get('made_words'), m.get('node'), m.get('ai')), 'warn', who=by)
        return {'manifest': m, 'safety': before}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def rb_fetch(store, tid, name, dst):
    t = rb_target(store, tid)
    if not t:
        raise ValueError('no such destination')
    if not RB_NAME_RE.match(str(name or '')):
        raise ValueError('not a backup of ai: %r' % str(name)[:80])
    tr = rb_transport(t)
    try:
        tr.open()
        tr.get(name, dst)
    finally:
        tr.close()


def rb_remote_list(store, tid):
    t = rb_target(store, tid)
    if not t:
        raise ValueError('no such destination')
    tr = rb_transport(t)
    try:
        tr.open()
        files = tr.list()
    finally:
        tr.close()
    names = set(x['name'] for x in files)
    out = []
    for x in files:
        m = RB_NAME_RE.match(x['name'])
        if not m:
            continue
        try:
            when_ = datetime.strptime(m.group('stamp'), '%Y%m%d-%H%M%S').timestamp()
        except ValueError:
            when_ = x.get('mtime') or 0
        out.append({'name': x['name'], 'bytes': x['size'], 'when': when_, 'node': m.group('node'),
                    'site': m.group('site'), 'encrypted': bool(m.group('enc')),
                    'mine': m.group('node') == rb_slug(node_name()), 'sha256': (x['name'] + '.sha256') in names})
    out.sort(key=lambda x: -x['when'])
    return out


RB_UPLOADS = STATE_DIR / 'rbackup-uploads'
RB_DOWNLOADS = STATE_DIR / 'rbackup-downloads'


def rb_tools():
    return {k: bool(shutil.which(k)) for k in ('ssh', 'sftp', 'scp', 'ssh-keygen', 'ssh-keyscan', 'smbclient', 'openssl')}


def rb_page(store):
    nodes = {}
    for r in rb_history(store):
        nodes.setdefault(r.get('node') or '?', r)
    return {'targets': [rb_view(t) for t in rb_targets(store)], 'runs': rb_history(store)[:40],
            'last_by_node': nodes, 'job': {k: v for k, v in RB_JOB.items()},
            'kinds': [{'kind': k, 'words': RB_KIND_WORDS[k], 'port': RB_PORTS.get(k)} for k in RB_KINDS],
            'tools': rb_tools(), 'node': node_name(), 'locked': bool(rb_password()), 'iter': RB_ITER,
            'site': CONFIG.get('site_name') or 'ai', 'next': rb_next_words(), 'uploads': str(RB_UPLOADS)}


def rb_tidy_files():
    now = time.time()
    for d in (RB_UPLOADS, RB_DOWNLOADS):
        try:
            for p in d.iterdir():
                if now - p.stat().st_mtime > 3600:
                    if p.is_dir():
                        shutil.rmtree(str(p), ignore_errors=True)
                    else:
                        p.unlink()
        except OSError:
            pass


# ---- power ------------------------------------------------------------------------------------
def power(what, by, store):
    if what not in ('reboot', 'poweroff', 'restart-ai', 'restart-web'):
        raise Refused('reboot, poweroff, restart-ai or restart-web')
    words = {'reboot': 'restarts the server', 'poweroff': 'switches the server off',
             'restart-ai': 'restarts ai.service (the terminals go on)',
             'restart-web': 'restarts nginx and php-fpm'}[what]
    store.add_event('system', '%s %s' % (by, words), 'warn', who=by)
    if NO_SYSTEM:
        return words
    if what in ('reboot', 'poweroff'):
        cmd = 'systemctl %s' % what
    elif what == 'restart-ai':
        cmd = 'systemctl restart ai.service'
    else:
        units = ' '.join(sorted({u for u in ['php-fpm'] + ['php%s-fpm' % p.name[7:] for p in
                                                         Path('/usr/sbin').glob('php-fpm?*')]}))
        cmd = 'systemctl restart nginx; for u in %s; do systemctl try-restart $u; done' % units
    if systemd_here():
        run(['systemd-run', '--on-active=3', '--collect', '--quiet', '--unit', 'ai-power-%d' % time.time(),
             '/bin/sh', '-c', cmd], timeout=20, check=True)
    else:
        subprocess.Popen(['/bin/sh', '-c', 'sleep 3; ' + cmd], start_new_session=True)
    return words


# ---- Linux accounts, for the terminals to run as ---------------------------------------------
def linux_accounts():
    out = []
    for p in pwd.getpwall():
        if p.pw_uid == 0 or (p.pw_uid >= 1000 and p.pw_uid < 60000):
            out.append({'name': p.pw_name, 'uid': p.pw_uid, 'home': p.pw_dir, 'shell': p.pw_shell})
    return sorted(out, key=lambda x: (x['uid'] != 0, x['name']))


def linux_add(name, sudo=False):
    if not LINUX_NAME_RE.match(str(name or '')):
        raise Refused('a Linux name: small letters, digits, _ and -, starting with a letter')
    try:
        pwd.getpwnam(name)
        raise Refused('there is a Linux account %s already' % name)
    except KeyError:
        pass
    run(['useradd', '-m', '-s', '/bin/bash', name], timeout=30, check=True)
    if sudo:
        for g in ('wheel', 'sudo'):
            try:
                grp.getgrnam(g)
                run(['usermod', '-aG', g, name], timeout=30, check=True)
                break
            except KeyError:
                continue


# ---------------------------------------------------------------------------
# New versions: from a package sent here, or from the web
# ---------------------------------------------------------------------------
# The package is checked by ai_upgrade.py - signed by a release key this
# machine trusts (/usr/local/lib/ai/release-keys/), every file the one signed -
# and put in by its own install.sh --upgrade, in a systemd unit of its own
# (ai-upgrade-*), apart from ai.service, which the upgrade restarts. The
# terminals are tmux's and go on running through it.
ONLINE_PKG_RE = re.compile(r'(?:^|/)(ai-(\d+)\.(\d+)\.(\d+)\.tar\.gz)(?:\?|#|$)')
UPGRADE_MOST = 64 * 1024 * 1024


def upgrader():
    for p in (LIB_DIR / 'ai_upgrade.py', HERE / 'deploy' / 'ai_upgrade.py'):
        if p.is_file():
            return str(p)
    raise Refused('ai_upgrade.py is not installed (%s)' % LIB_DIR, 500)


def upgrade_inspect(path):
    rc, so, se = run([sys.executable, '-I', upgrader(), '--inspect', str(path)], timeout=120)
    try:
        got = json.loads(so.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Refused('the package could not be checked: %s' % (se or so).strip()[-300:])
    if not got.get('ok'):
        raise Refused(got.get('said') or 'the package was refused')
    return got


def _online_get(url, limit=4 * 1024 * 1024, accept='*/*', timeout=30):
    if not str(url).startswith('https://'):
        raise Refused('only https:// addresses are asked: %s' % url)
    req = urllib.request.Request(url, headers={'User-Agent': 'ai/%s (+upgrade check)' % __version__,
                                               'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        final = r.geturl()
        if not str(final).startswith('https://'):
            raise Refused('it was sent on to an address that is not https: %s' % final)
        data = r.read(limit + 1)
        if len(data) > limit:
            raise Refused('the answer from %s is bigger than %d MB' % (url, limit >> 20))
        return data, r.headers.get('Content-Type') or '', final


def online_list(url):
    """The packages at `url`: [{'name', 'version', 'url', 'bytes'}], newest first."""
    url = str(url or '').strip()
    if not url:
        raise Refused('no address to look at (Settings - Upgrades)')
    found = {}

    def add(name, link, size=None):
        m = ONLINE_PKG_RE.search('/' + name)
        if not m or not str(link).startswith('https://'):
            return
        v = tuple(int(x) for x in m.group(2, 3, 4))
        found[m.group(1)] = {'name': m.group(1), 'version': '%d.%d.%d' % v, 'v': v, 'url': link,
                             'bytes': size}

    gh = re.match(r'^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/tree/([^/]+)(?:/(.*?))?)?/?$', url)
    m1 = ONLINE_PKG_RE.search(urllib.parse.urlparse(url).path)
    if m1:
        link = url
        b = re.match(r'^https://github\.com/([^/]+)/([^/]+)/blob/(.+)$', url)
        if b:
            link = 'https://raw.githubusercontent.com/%s/%s/%s' % b.groups()
        add(m1.group(1), link)
    elif gh:
        owner, repo, ref, folder = gh.group(1), gh.group(2), gh.group(3), gh.group(4) or ''
        api = 'https://api.github.com/repos/%s/%s/contents/%s' % (owner, repo, urllib.parse.quote(folder.strip('/')))
        if ref:
            api += '?ref=' + urllib.parse.quote(ref)
        try:
            data, _ct, _f = _online_get(api, accept='application/vnd.github+json')
            items = json.loads(data.decode('utf-8'))
        except Exception as e:                          # noqa: BLE001
            try:
                data, _ct, _f = _online_get(url)
            except Exception:                           # noqa: BLE001
                raise Refused('GitHub did not answer: %s' % (getattr(e, 'reason', None) or e))
            base = 'https://raw.githubusercontent.com/%s/%s/%s/%s' % (
                owner, repo, ref or 'HEAD', (folder.strip('/') + '/') if folder.strip('/') else '')
            items = [{'type': 'file', 'name': n, 'download_url': base + n}
                     for n in set(re.findall(r'ai-\d+\.\d+\.\d+\.tar\.gz', data.decode('utf-8', 'replace')))]
        for it in items if isinstance(items, list) else [items]:
            if isinstance(it, dict) and it.get('type') == 'file' and it.get('download_url'):
                add(str(it.get('name') or ''), str(it['download_url']), it.get('size'))
    else:
        data, ct, final = _online_get(url)
        text = data.decode('utf-8', 'replace')
        for href in re.findall(r'''href\s*=\s*["']([^"']+)["']''', text, re.I):
            link = urllib.parse.urljoin(final, html.unescape(href))
            mm = ONLINE_PKG_RE.search(urllib.parse.urlparse(link).path)
            if mm:
                add(mm.group(1), link)
    out = sorted(found.values(), key=lambda x: x['v'], reverse=True)
    for x in out:
        x.pop('v', None)
    return out


# Going back to an older version (otp's, 1.0.143): only to one that is safe -
# one that reads what the newer versions wrote into the database the same and
# has every security fix that matters. Each version says how far back it may
# go (DOWNGRADE_FLOOR); the highest of what ran on this database counts.
DOWNGRADE_FLOOR = '1.0.6'


def downgrade_floor(store):
    ran = store.meta_json('versions:floors', {}) or {}
    floors = [DOWNGRADE_FLOOR] + [str(v) for v in ran.values()]
    return max(floors, key=ver_tuple)


def versions_ran_note(store):
    ran = store.meta_json('versions:floors', {}) or {}
    if ran.get(__version__) != DOWNGRADE_FLOOR:
        ran[__version__] = DOWNGRADE_FLOOR
        store.set_meta_json('versions:floors', ran)


def changelog_entry(text, version):
    """One version's part of a CHANGELOG.md."""
    m = re.search(r'^## %s\s*$(.*?)(?=^## |\Z)' % re.escape(str(version or '')), str(text or ''), re.M | re.S)
    return ('## %s\n%s' % (version, m.group(1).rstrip())).strip() if m else ''


def changelog_between(version, here):
    """What going back from `here` to `version` gives up: the entries of the
    newer versions, from this machine's own CHANGELOG.md."""
    text = ''
    for p in (LIB_DIR / 'CHANGELOG.md', HERE / 'CHANGELOG.md'):
        if p.is_file():
            text = read_text(p, 2 << 20)
            break
    lost = []
    for m in re.finditer(r'^## (\d+\.\d+\.\d+)\s*$', text, re.M):
        v = m.group(1)
        if ver_tuple(version) < ver_tuple(v) <= ver_tuple(here):
            lost.append({'version': v, 'text': changelog_entry(text, v)})
    return {'from': 'here', 'entry': changelog_entry(text, version), 'lost': lost, 'here': here}


class Upgrades:
    def __init__(self, daemon):
        self.daemon = daemon
        self.lock = threading.Lock()
        self.busy = False

    @property
    def store(self):
        return self.daemon.store

    def look(self, by=''):
        url = str(CONFIG.get('upgrade_url') or '').strip()
        row = {'at': time.time(), 'url': url, 'by': by, 'here': __version__}
        try:
            got = online_list(url)
            row['packages'] = got[:12]
            row['newest'] = got[0] if got else None
            if got and ver_tuple(got[0]['version']) > ver_tuple(__version__):
                was = self.store.meta_json('upgrade:online', {}) or {}
                if (was.get('newest') or {}).get('version') != got[0]['version']:
                    self.store.add_event('upgrades', 'ai %s is out (%s)' % (got[0]['version'], url), 'info')
        except Exception as e:                          # noqa: BLE001
            row['error'] = str(getattr(e, 'reason', None) or e).split('\n')[0][:300]
        self.store.set_meta_json('upgrade:online', row)
        return row

    def status(self):
        st = {}
        try:
            st = json.loads(read_text(UPGRADE_DIR / 'status.json') or '{}')
        except ValueError:
            st = {}
        if st.get('state') == 'running' and time.time() - float(st.get('at') or 0) > 1800:
            st['state'] = 'lost'
        return st

    def view(self):
        online = self.store.meta_json('upgrade:online', {}) or {}
        newer = sorted((p for p in online.get('packages') or []
                        if ver_tuple(p.get('version')) > ver_tuple(__version__)),
                       key=lambda p: ver_tuple(p.get('version')), reverse=True)
        floor = downgrade_floor(self.store)
        older = []
        for p in sorted((p for p in online.get('packages') or [] if ver_tuple(p.get('version')) < ver_tuple(__version__)),
                        key=lambda p: ver_tuple(p.get('version')), reverse=True):
            one = dict(p)
            one['safe'] = ver_tuple(p.get('version')) >= ver_tuple(floor)
            if not one['safe']:
                one['why'] = 'older than %s, the oldest that is safe on this database' % floor
            older.append(one)
        st = self.status()
        hidden = self.store.get_meta('upgrade:hidden') == str(st.get('at'))
        return {'here': __version__, 'online': online, 'newer': newer, 'older': older, 'floor': floor,
                'url': CONFIG.get('upgrade_url'),
                'check': bool(CONFIG.get('upgrade_check')), 'auto': bool(CONFIG.get('upgrade_auto')),
                'status': None if hidden else st, 'log': '' if hidden else read_text(UPGRADE_DIR / 'last.log', 400000),
                'keys': sorted(p.name for p in (LIB_DIR / 'release-keys').glob('*.pub'))
                if (LIB_DIR / 'release-keys').is_dir() else []}

    # -- otp's Upgrades pane: one node, this server ---------------------------
    def held(self):
        """The package sent or fetched and checked, waiting for Upgrade."""
        h = self.store.meta_json('upgrade:held', None)
        if not isinstance(h, dict) or not h.get('path') or not os.path.isfile(str(h['path'])):
            return None
        return h

    def hold(self, path, info, by):
        h = {'path': str(path), 'version': info.get('version'), 'signed_by': info.get('signed_by'),
             'bytes': os.path.getsize(str(path)), 'by': by, 'at': time.time(),
             'changelog': changelog_entry(info.get('changelog') or '', info.get('version')),
             'downgrade': bool(info.get('older'))}
        was = self.held()
        if was and was['path'] != h['path']:
            try:
                os.unlink(was['path'])
            except OSError:
                pass
        self.store.set_meta_json('upgrade:held', h)
        self.store.add_event('upgrades', '%s sent ai %s, checked: signed by %s' % (by, h['version'], h['signed_by']),
                             who=by)
        return h

    def forget(self, by=''):
        h = self.held()
        if h:
            try:
                os.unlink(h['path'])
            except OSError:
                pass
        self.store.x('DELETE FROM meta WHERE k = ?', ('upgrade:held',))

    def plan(self):
        """The upgrade going on or the last one, as otp's plan of one node."""
        st = self.status()
        if not st or not st.get('state') or self.store.get_meta('upgrade:hidden') == str(st.get('at')):
            return None
        lines = (read_text(UPGRADE_DIR / 'last.log', 400000) or '').splitlines()
        parts = [x for x in lines if x.lstrip().startswith('==> ')]
        state = st.get('state')
        step = {'running': 'installing', 'done': 'done'}.get(state, 'failed')
        said = st.get('said') or {'running': 'install.sh --upgrade is running',
                                  'done': 'put in and started again', 'lost': 'it stopped saying how it goes'}.get(state, '')
        one = {'name': node_name(), 'state': step, 'said': said, 'at': st.get('at'), 'asked': st.get('at'),
               'tail': [x for x in lines if x.strip()][-12:], 'part': len(parts),
               'part_words': parts[-1].strip().lstrip('=> ').strip() if parts else ''}
        return {'id': str(st.get('at')), 'version': st.get('version'), 'by': st.get('by'), 'at': st.get('at'),
                'state': {'running': 'running', 'done': 'done'}.get(state, 'failed'),
                'downgrade': bool(st.get('downgrade')), 'steps': [one], 'drain_s': 0}

    def view_otp(self):
        online = self.store.meta_json('upgrade:online', {}) or {}
        newer = sorted((p for p in online.get('packages') or []
                        if ver_tuple(p.get('version')) > ver_tuple(__version__)),
                       key=lambda p: ver_tuple(p.get('version')), reverse=True)
        o = dict(online)
        o['here'] = __version__
        o['newer'] = bool(newer)
        o['newer_list'] = newer
        if newer:
            o['newest'] = newer[0]
        h = self.held()
        plan = self.plan()
        not_ready = []
        if h and plan and plan['state'] == 'running':
            not_ready.append('an upgrade is running')
        try:
            helper = bool(upgrader())
        except Refused:
            helper = False
        lines = (read_text(UPGRADE_DIR / 'last.log', 400000) or '').splitlines()
        return {'version': __version__, 'node': node_name(),
                'nodes': [{'name': node_name(), 'me': True, 'alive': True, 'version': __version__,
                           'at': time.time(), 'maintenance': {}}],
                'web': {'check': bool(CONFIG.get('upgrade_check')), 'online': o},
                'package': ({k: v for k, v in h.items() if k != 'path'} if h else None),
                'ready': bool(h) and not not_ready, 'not_ready': not_ready,
                'helper': helper, 'path_unit': helper, 'plan': plan,
                'log': lines[-400:], 'downgrade_on': bool(CONFIG.get('upgrade_downgrade', True)),
                'keys': sorted(p.name for p in (LIB_DIR / 'release-keys').glob('*.pub'))
                if (LIB_DIR / 'release-keys').is_dir() else []}

    def downgrade_list(self):
        url = CONFIG.get('upgrade_url')
        floor = downgrade_floor(self.store)
        vs = []
        for p in online_list(url):
            if ver_tuple(p['version']) >= ver_tuple(__version__):
                continue
            why = []
            if ver_tuple(p['version']) < ver_tuple(floor):
                why.append('older than %s, the oldest that is safe on this database: what the newer versions '
                           'wrote into it would not be read the same, or a security fix would be lost' % floor)
            vs.append({'version': p['version'], 'why': why, 'short': 'too old' if why else ''})
        return {'url': url, 'here': __version__, 'floor': floor, 'lowest': floor, 'versions': vs}

    def fetch(self, version, by, older=False):
        pk = [p for p in online_list(CONFIG.get('upgrade_url')) if p['version'] == str(version)]
        if not pk:
            raise Refused('ai %s is not at %s' % (version, CONFIG.get('upgrade_url')))
        if older:
            floor = downgrade_floor(self.store)
            if ver_tuple(pk[0]['version']) >= ver_tuple(__version__):
                raise Refused('ai %s is not older than %s, which runs here' % (version, __version__))
            if ver_tuple(pk[0]['version']) < ver_tuple(floor):
                raise Refused('ai %s is older than %s, the oldest that is safe on this database' % (version, floor))
        elif ver_tuple(pk[0]['version']) <= ver_tuple(__version__):
            raise Refused('ai %s is not newer than %s, which runs here' % (version, __version__))
        UPGRADE_DIR.mkdir(parents=True, exist_ok=True)
        data, _ct, final = _online_get(pk[0]['url'], limit=UPGRADE_MOST, timeout=300)
        path = UPGRADE_DIR / pk[0]['name']
        write_atomic(path, data, mode=0o600)
        try:
            info = upgrade_inspect(path)
        except Refused as e:
            path.unlink()
            self.store.add_event('upgrades', 'ai %s from %s was refused: %s' % (version, final, e), 'bad', who=by)
            raise
        return path, info

    def take(self, path, by, older=False):
        info = upgrade_inspect(path)
        if info.get('older') and not older:
            raise Refused('%s is older than %s, which runs here: going back is done with Going back to an '
                          'older version (or ai --downgrade VERSION)' % (info['version'], __version__))
        if info.get('older') and ver_tuple(info['version']) < ver_tuple(downgrade_floor(self.store)):
            raise Refused('%s is older than %s, the oldest that is safe on this database' % (
                info['version'], downgrade_floor(self.store)))
        return info

    def install(self, path, by, older=False):
        with self.lock:
            st = self.status()
            if st.get('state') == 'running':
                raise Refused('an upgrade is running already')
            if self.busy:
                raise Refused('an upgrade is being started already')
            self.busy = True
        try:
            info = self.take(path, by, older)
            write_atomic(UPGRADE_DIR / 'status.json', json.dumps({'state': 'running', 'version': info['version'],
                                                                  'by': by, 'at': time.time(),
                                                                  'downgrade': bool(info.get('older'))}), mode=0o600)
            self.store.x('DELETE FROM meta WHERE k = ?', ('upgrade:held',))
            write_atomic(UPGRADE_DIR / 'last.log', '', mode=0o600)
            cmd = [sys.executable if os.path.exists(sys.executable) else '/usr/bin/python3', '-I', upgrader(),
                   '--job', str(path), '--by', by or 'the pages']
            if info.get('older'):
                cmd += ['--floor', downgrade_floor(self.store)]
                # A copy of the database first: what the newer one wrote, kept.
                try:
                    make_backup(self.store, 'before going back to %s, by %s' % (info['version'], by))
                except Exception as e:                  # noqa: BLE001
                    log('a copy before going back could not be made: %s' % e, 'warn')
            self.store.add_event('upgrades', '%s is putting ai %s in (signed by %s)%s' % (
                by, info['version'], info.get('signed_by'), ' - going back from %s' % __version__
                if info.get('older') else ''), 'warn', who=by)
            if NO_SYSTEM:
                return info
            if systemd_here():
                run(['systemd-run', '--unit', 'ai-upgrade-%d' % time.time(), '--collect', '--quiet',
                     '--description', 'ai: putting in version %s' % info['version']] + cmd, timeout=30, check=True)
            else:
                subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return info
        finally:
            self.busy = False

    def tick(self):
        """Once a day: a look; and, where asked, the newer version put in."""
        if not CONFIG.get('upgrade_check') and not CONFIG.get('upgrade_auto'):
            return
        last = self.store.meta_json('upgrade:online', {}) or {}
        if last.get('url') == CONFIG.get('upgrade_url') and time.time() - float(last.get('at') or 0) < 86400:
            due = False
        else:
            due = True
        if due:
            last = self.look()
        if not CONFIG.get('upgrade_auto') or last.get('error'):
            return
        if time.localtime().tm_hour != int(CONFIG.get('upgrade_auto_hour') or 3):
            return
        newest = last.get('newest') or {}
        if not newest or ver_tuple(newest.get('version')) <= ver_tuple(__version__):
            return
        if self.store.get_meta('upgrade:auto-tried') == newest['version']:
            return
        self.store.set_meta('upgrade:auto-tried', newest['version'])
        try:
            path, _info = self.fetch(newest['version'], 'automatic upgrade')
            self.install(path, 'automatic upgrade')
        except Exception as e:                          # noqa: BLE001
            self.store.add_event('upgrades', 'the automatic upgrade to %s failed: %s' % (newest['version'], e), 'bad')


# ---------------------------------------------------------------------------
# Claude Code itself: installed or not, for which accounts
# ---------------------------------------------------------------------------
CLAUDE_CACHE = {}
INSTALL_NATIVE = 'curl -fsSL https://claude.ai/install.sh | bash'
INSTALL_NPM = 'npm install -g @anthropic-ai/claude-code'


def claude_facts(pw, fresh=False):
    hit = CLAUDE_CACHE.get(pw.pw_name)
    if hit and not fresh and time.time() - hit['at'] < 120:
        return hit
    cmd = str(CONFIG.get('claude_cmd') or 'claude')
    script = ('p=$(command -v %s 2>/dev/null) && { echo "path=$p"; echo "version=$(%s --version 2>/dev/null | '
              'head -n1)"; }; echo "node=$(node --version 2>/dev/null)"; echo "npm=$(npm --version 2>/dev/null)"'
              % (shlex.quote(cmd), shlex.quote(cmd)))
    shell = pw.pw_shell if pw.pw_shell and os.path.exists(pw.pw_shell) and \
        not pw.pw_shell.endswith(('nologin', 'false')) else '/bin/bash'
    out = {'account': pw.pw_name, 'home': pw.pw_dir, 'at': time.time(), 'path': '', 'version': '', 'node': '',
           'npm': ''}
    try:
        got = subprocess.run([shell, '-lc', script], capture_output=True, text=True, timeout=25,
                             env=user_env(pw), cwd=pw.pw_dir if os.path.isdir(pw.pw_dir) else '/',
                             **as_user_kwargs(pw))
        for line in got.stdout.splitlines():
            k, _s, v = line.partition('=')
            if k in out:
                out[k] = v.strip()
    except (OSError, subprocess.SubprocessError) as e:
        out['error'] = str(e)
    cred = os.path.join(pw.pw_dir, '.claude', '.credentials.json')
    out['signed_in'] = os.path.exists(cred)
    try:
        with open(os.path.join(pw.pw_dir, '.claude.json'), encoding='utf-8') as f:
            cj = json.load(f)
        acct = cj.get('oauthAccount') or {}
        if acct:
            out['signed_in'] = True
            out['email'] = acct.get('emailAddress') or ''
            out['org'] = acct.get('organizationName') or ''
    except (OSError, ValueError, AttributeError):
        pass
    out['api_key'] = 'ANTHROPIC_API_KEY' in env_lines(CONFIG.get('claude_env'))
    CLAUDE_CACHE[pw.pw_name] = out
    return out


# ---------------------------------------------------------------------------
# The API the web pages ask
# ---------------------------------------------------------------------------
ROUTES = {}


def route(method, path, admin=False, anon=False):
    def wrap(fn):
        ROUTES[(method, path)] = (fn, admin, anon)
        return fn
    return wrap


class Ctx:
    def __init__(self, daemon, who, body, query, ip, token=''):
        self.daemon, self.who, self.body, self.query, self.ip, self.token = daemon, who, body, query, ip, token

    def arg(self, name, default=''):
        v = self.query.get(name)
        return v[0] if v else default

    @property
    def name(self):
        return self.who['name'] if self.who else ''


def need_admin(c):
    if not c.who or c.who['role'] != 'admin':
        raise Refused('only an administrator may do that', 403)


@route('GET', '/api/health', anon=True)
def api_health(c):
    d = c.daemon
    return {'ok': True, 'version': __version__, 'lang': CONFIG.get('ui_lang'),
            'users': len(d.store.users()), 'database': {'ok': True}, 'host': host_name()}


@route('POST', '/api/auth/login', anon=True)
def api_login(c):
    token = c.daemon.auth.login(c.body.get('name'), c.body.get('password'), c.ip, c.body.get('agent') or '')
    name = str(c.body.get('name') or '').strip()
    u = c.daemon.store.user(name)
    stage = mfa_stage(c.daemon.store, name) if CONFIG.get('admin_2fa') else ''
    return {'token': token, 'who': None if stage else user_view(u), 'mfa': stage}


@route('POST', '/api/auth/logout')
def api_logout(c):
    if c.body.get('everywhere'):
        n = c.daemon.store.x('DELETE FROM sessions WHERE name=?', (c.name,))
        c.daemon.store.add_event('sign-in', '%s signed out everywhere (%d sign-in(s)); the terminals go on running'
                                 % (c.name, n), 'info', who=c.name)
        return {'ended': n}
    c.daemon.auth.logout(c.token)
    return {}


@route('GET', '/api/auth/whoami')
def api_whoami(c):
    if c.who.get('_mfa'):
        # Signed in with the password only: the page asks for the second step.
        return {'who': {'name': c.who['name'], 'mfa': c.who['_mfa']}, 'mfa': c.who['_mfa']}
    who = user_view(c.who)
    who['cols'] = user_cols(c.daemon.store, c.name)
    who['cols_edit'] = bool((c.who.get('_data') or {}).get('cols_edit'))
    who['mfa_kind'] = (mfa_get(c.daemon.store, c.name) or {}).get('kind') or ''
    return {'who': who}


@route('POST', '/api/auth/password')
def api_password(c):
    if not check_password(c.body.get('old'), c.who['pw']):
        raise Refused('the present password is not that', 403)
    c.daemon.auth.set_password(c.name, c.body.get('new'), c.name)
    return {}


@route('POST', '/api/auth/prefs')
def api_prefs(c):
    try:
        prefs = json.loads(c.who.get('prefs') or '{}')
    except ValueError:
        prefs = {}
    for k, v in (c.body.get('prefs') or {}).items():
        if k in PREF_KEYS:
            if v is None:
                prefs.pop(k, None)
            else:
                prefs[k] = v
    text = json.dumps(prefs)
    if len(text) > 64000:
        raise Refused('too much to keep')
    c.daemon.store.x('UPDATE users SET prefs=? WHERE name=?', (text, c.name))
    return {'prefs': prefs}


# ---- what this server runs on (as otp's About) --------------------------------------------------
_SOFTWARE = {'at': 0.0, 'state': None}


def _first_line(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ''
    text = (r.stdout or '') + (r.stderr or '')
    return (text.strip().splitlines() or [''])[0].strip()[:200]


def software_info(store=None):
    """What this server runs on (otp's, 1.0.99): ai, its Python and the modules
    it uses, the libraries under them, the programs beside it and the system -
    for Settings → About. Asked at most once an hour."""
    if time.time() - _SOFTWARE['at'] < 3600 and _SOFTWARE['state'] is not None:
        out = dict(_SOFTWARE['state'])
    else:
        import platform
        out = {'ai': __version__,
               'python': '%s %s' % (platform.python_implementation(), platform.python_version()),
               'python_path': os.path.realpath(sys.executable),
               'openssl': ssl.OPENSSL_VERSION, 'sqlite': sqlite3.sqlite_version,
               'kernel': '%s %s' % (platform.system(), platform.release()),
               'arch': platform.machine(), 'modules': {}, 'programs': {}}
        try:
            with open('/etc/os-release', encoding='utf-8') as f:
                rel = dict(l.strip().split('=', 1) for l in f if '=' in l)
            out['os'] = rel.get('PRETTY_NAME', '').strip('"')
        except OSError:
            out['os'] = ''
        for mod, attr in (('colorama', '__version__'),):
            try:
                m = __import__(mod)
                v = str(getattr(m, attr, '') or '').split(' ')[0]
                if mod == 'psycopg2':
                    lib = getattr(m, '__libpq_version__', 0)
                    if lib:
                        v += ' (libpq %d.%d)' % (lib // 10000, lib % 10000 // 100 if lib < 100000
                                                 else lib % 100)
                out['modules'][mod] = v
            except Exception:                           # noqa: BLE001
                out['modules'][mod] = ''
        progs = (('nginx', ['nginx', '-v']), ('php', ['php', '-v']),
                 ('php-fpm', None), ('tmux', ['tmux', '-V']), ('git', ['git', '--version']),
                 ('node', ['node', '--version']), ('npm', ['npm', '--version']),
                 ('ssh', ['ssh', '-V']), ('smbclient', ['smbclient', '--version']),
                 ('chrony', ['chronyd', '--version']),
                 ('openssl', ['openssl', 'version']), ('systemd', ['systemctl', '--version']),
                 ('iptables', ['iptables', '--version']),
                 ('firewalld', ['firewall-cmd', '--version']))
        for name, cmd in progs:
            if name == 'php-fpm':
                import glob
                fpm = sorted(glob.glob('/usr/sbin/php-fpm*') + glob.glob('/usr/sbin/php*-fpm*'))
                line = _first_line([fpm[-1], '-v']) if fpm else ''
            else:
                exe = shutil.which(cmd[0]) or next((p for p in ('/usr/sbin/' + cmd[0], '/sbin/' + cmd[0])
                                                    if os.path.exists(p)), None)
                line = _first_line([exe] + cmd[1:]) if exe else ''
            m = re.search(r'(\d+\.\d+(?:\.\d+)?[^\s,()]*)', line or '')
            if m and not re.search(r'(?i)denied|not found|error', line):
                out['programs'][name] = m.group(1)
            elif name == 'systemd':
                m = re.search(r'^systemd\s+(\d+)', line or '')
                if m:
                    out['programs'][name] = m.group(1)
        _SOFTWARE.update(at=time.time(), state=dict(out))
    # What changes without a restart, asked each time it is wanted.
    if store is not None:
        out['database'] = 'SQLite %s' % sqlite3.sqlite_version
    try:
        out['claude'] = (claude_facts(pwd.getpwnam(str(CONFIG.get('default_run_as') or 'root'))) or {}).get('version') or ''
    except (KeyError, Refused, OSError):
        out['claude'] = ''
    try:
        out['php_cli'] = (php_state() or {}).get('version') or ''
    except Exception:                                   # noqa: BLE001
        pass
    return out


# ---- PHP and php2shell (as otp's) ----------------------------------------------------------
# Whether the PHP running the pages has the php2shell fix (CVE-2026-109618,
# CVE-2026-109619): its version against the fixed releases, or the packages'
# changelog where a distribution backported it and kept the old number.
PHP_FIXED = {'8.2': (8, 2, 35), '8.3': (8, 3, 36), '8.4': (8, 4, 27), '8.5': (8, 5, 12)}
_PHP_STATE = {'at': 0, 'state': None}


def php_state():
    if time.time() - _PHP_STATE['at'] < 3600 and _PHP_STATE['state'] is not None:
        return _PHP_STATE['state']
    out = {'version': '', 'fixed': None, 'how': ''}
    php = shutil.which('php') or next((p for p in ('/usr/bin/php', '/usr/local/bin/php')
                                       if os.path.exists(p)), None)
    if php:
        try:
            out['version'] = subprocess.run([php, '-r', 'echo PHP_VERSION;'], capture_output=True,
                                            text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    m = re.match(r'^(\d+)\.(\d+)\.(\d+)', out['version'])
    if m:
        v = tuple(int(x) for x in m.groups())
        want = PHP_FIXED.get('%d.%d' % v[:2])
        if want and v >= want or (not want and v[:2] > (8, 5)):
            out.update(fixed=True, how='version')
    if not out['fixed']:
        said = ''
        rpm = shutil.which('rpm')
        if rpm:
            for pkg in ('php-fpm', 'php-common'):
                try:
                    said += subprocess.run([rpm, '-q', '--changelog', pkg], capture_output=True,
                                           text=True, timeout=20).stdout
                except (OSError, subprocess.SubprocessError):
                    pass
        else:
            import gzip
            import glob
            for f in glob.glob('/usr/share/doc/php*-fpm/changelog.Debian.gz') + glob.glob(
                    '/usr/share/doc/php*-common/changelog.Debian.gz'):
                try:
                    with gzip.open(f, 'rt', errors='replace') as g:
                        said += g.read(200000)
                except OSError:
                    pass
        if 'CVE-2026-109618' in said:
            out.update(fixed=True, how='changelog')
        elif out['version']:
            out['fixed'] = False
    _PHP_STATE.update(at=time.time(), state=out)
    return out


def status_chat_root(u):
    """The folder of the chats as the account's Linux account sees it."""
    try:
        return chat_root_of(linux_user(run_as_of(u)))
    except Refused:
        return chat_root_of(None)


def status_view(c):
    d = c.daemon
    problems = []
    if not which('tmux'):
        problems.append('tmux is not installed: no terminal can start (dnf install tmux)')
    st = d.upgrades.status()
    online = d.store.meta_json('upgrade:online', {}) or {}
    newest = online.get('newest') or {}
    cert = cert_facts() if c.who['role'] == 'admin' else {}
    if cert.get('until_ts') and cert['until_ts'] - time.time() < 14 * 86400:
        problems.append('the certificate of the pages runs out %s' % cert.get('until'))
    terms = d.terms.list(c.who, ended=False)
    return {
        'version': __version__, 'host': host_name(), 'site': CONFIG.get('site_name') or '',
        'who': user_view(c.who), 'problems': problems, 'trials': d.trials.view() if c.who['role'] == 'admin' else [],
        'terms_running': len([t for t in terms if t['state'] != 'ended']),
        'newer': newest.get('version') if newest and ver_tuple(newest.get('version')) > ver_tuple(__version__) else '',
        'upgrade_state': st.get('state') if st else '', 'started': d.started, 'now': time.time(),
        'php': php_state() if c.who['role'] == 'admin' else None,
        'mailq': mailq_counted(d.store) if c.who['role'] == 'admin' else {},
        'chat_root': status_chat_root(c.who),
    }


@route('GET', '/api/status')
def api_status(c):
    return status_view(c)


@route('GET', '/api/overview')
def api_overview(c):
    d = c.daemon
    out = status_view(c)
    out['terms'] = d.terms.list(c.who)
    if c.who['role'] == 'admin':
        out['machine'] = machine_facts()
        out['events'] = d.store.q('SELECT * FROM events ORDER BY id DESC LIMIT 12')
        out['signed_in'] = d.store.q('SELECT name, created, seen, ip FROM sessions ORDER BY seen DESC LIMIT 20')
        out['osup'] = d.store.meta_json('osup:check', None)
        out['cert'] = cert_facts()
    return out


# ---- the terminals ----------------------------------------------------------------------
@route('GET', '/api/usage')
def api_usage(c):
    """What the chats with Claude Code used (1.0.13): each chat, and by day,
    model, account, folder and hour - the Overview's statistics."""
    return chat_usage(c.daemon, c.who, int(c.arg('days', '30') or 30))


@route('GET', '/api/terms')
def api_terms(c):
    terms = c.daemon.terms.list(c.who)
    with VIEWERS_LOCK:
        for t in terms:
            t['here'] = len(VIEWERS.get(t['id'], ()))
    return {'terms': terms, 'run_as': run_as_of(c.who), 'admin': c.who['role'] == 'admin'}


@route('GET', '/api/term')
def api_term(c):
    tm = c.daemon.terms
    r = tm.row(c.arg('id'))
    tm.may(c.who, r)
    live = tm.live()
    v = tm.view(r, live)
    # The whole history of it (1.0.9): every line tmux keeps, with its colours
    # when asked - what a tablet cannot scroll back to in the terminal itself.
    lines = 'all' if c.arg('lines') == 'all' else max(5, min(2000, int(c.arg('lines', '40') or 40)))
    v['screen'] = tm.capture(r, lines, escapes=c.arg('ansi') == '1') if v['state'] != 'ended' \
        else (r.get('last_screen') or '')
    return {'term': v}


@route('POST', '/api/terms')
def api_terms_do(c):
    tm = c.daemon.terms
    do = str(c.body.get('do') or '')
    if do == 'new':
        tid = tm.new(c.who, str(c.body.get('kind') or 'claude'), str(c.body.get('cwd') or ''),
                     str(c.body.get('title') or ''), c.body.get('opts') or {},
                     int(c.body.get('cols') or 160), int(c.body.get('rows') or 48),
                     run_as=str(c.body.get('run_as') or '') or None)
        return {'id': tid}
    r = tm.row(c.body.get('id'))
    tm.may(c.who, r)
    if do == 'kill':
        tm.kill(c.who, r)
    elif do == 'restart':
        return {'id': tm.restart(c.who, r)}
    elif do == 'again':
        return {'id': tm.again(c.who, r)}
    elif do == 'rename':
        tm.rename(c.who, r, c.body.get('title'))
    elif do == 'forget':
        tm.forget(c.who, r)
    elif do == 'send':
        tm.send(r, c.body.get('text'), bool(c.body.get('enter')), paste=c.body.get('paste', True) is not False)
    elif do == 'keys':
        tm.keys(r, [str(k) for k in (c.body.get('keys') or [])][:50])
    else:
        raise Refused('new, kill, restart, again, rename, forget, send or keys')
    tm.cache['at'] = 0
    return {}


@route('GET', '/api/history')
def api_history(c):
    who_as = c.arg('run_as') if c.who['role'] == 'admin' and c.arg('run_as') else run_as_of(c.who)
    pw = linux_user(who_as)
    items = conversations(pw, c.arg('cwd'))
    if c.who['role'] != 'admin':
        ok = []
        for it in items:
            try:
                path_allowed(c.who, it['cwd'] or '/')
                ok.append(it)
            except Refused:
                pass
        items = ok
    return {'items': items, 'run_as': who_as}


@route('POST', '/api/history')
def api_history_do(c):
    tid_src = str(c.body.get('id') or '')
    if not UUID_RE.match(tid_src):
        raise Refused('which conversation?')
    who_as = str(c.body.get('run_as') or '') if c.who['role'] == 'admin' else run_as_of(c.who)
    pw = linux_user(who_as or run_as_of(c.who))
    cwd = str(c.body.get('cwd') or pw.pw_dir)
    opts = {'resume': tid_src}
    if c.body.get('model'):
        opts['model'] = str(c.body['model'])
    if c.body.get('mode'):
        opts['mode'] = str(c.body['mode'])
    # A conversation that has its terminal in the list goes back into it
    # (1.0.16) - its tile, its name, its pin - opened if it still runs, started
    # again there if it ended; only one without is given a new terminal.
    tm = c.daemon.terms
    held = tm.holding(c.who, pw, tid_src)
    if held:
        lv = tm.live().get(held['id'])
        if lv and not lv['dead']:
            return {'id': held['id'], 'already': True}
        extra = {k: opts[k] for k in ('model', 'mode') if k in opts}
        return {'id': tm.again(c.who, held, sid=tid_src, extra=extra), 'again': True}
    tid = c.daemon.terms.new(c.who, 'claude', cwd, str(c.body.get('title') or '')[:120] or
                             'Claude · %s' % (clean_line(c.body.get('first'), 40) or tid_src[:8]),
                             opts, int(c.body.get('cols') or 160), int(c.body.get('rows') or 48),
                             run_as=pw.pw_name)
    return {'id': tid}


@route('GET', '/api/claude')
def api_claude(c):
    names = {run_as_of(c.who)}
    if c.who['role'] == 'admin':
        names |= {run_as_of(u) for u in c.daemon.store.users()} | {'root'}
    out = []
    for n in sorted(names):
        try:
            out.append(claude_facts(linux_user(n), fresh=c.arg('fresh') == '1'))
        except Refused as e:
            out.append({'account': n, 'error': str(e)})
    return {'accounts': out, 'native': INSTALL_NATIVE, 'npm': INSTALL_NPM,
            'env_keys': sorted(env_lines(CONFIG.get('claude_env')).keys())}


@route('POST', '/api/claude')
def api_claude_do(c):
    do = str(c.body.get('do') or '')
    who_as = str(c.body.get('run_as') or run_as_of(c.who))
    if who_as != run_as_of(c.who):
        need_admin(c)
    pw = linux_user(who_as)
    cmd = str(CONFIG.get('claude_cmd') or 'claude')
    scripts = {
        'install': (INSTALL_NATIVE, 'installing Claude Code'),
        'npm': (INSTALL_NPM, 'installing Claude Code (npm)'),
        'update': ('%s update' % shlex.quote(cmd), 'updating Claude Code'),
        'doctor': ('%s doctor' % shlex.quote(cmd), 'claude doctor'),
        'login': (None, 'signing in to Claude'),
    }
    if do not in scripts:
        raise Refused('install, npm, update, doctor or login')
    CLAUDE_CACHE.pop(pw.pw_name, None)
    if do == 'login':
        tid = c.daemon.terms.new(c.who, 'claude', pw.pw_dir, 'Claude · sign in', {}, run_as=pw.pw_name)
        return {'id': tid}
    if c.who['role'] != 'admin':
        raise Refused('only an administrator installs or updates Claude Code', 403)
    script, words = scripts[do]
    full = '%s; rc=$?; echo; echo "== done ($rc) - press Enter to close"; read -r _' % script
    tid = c.daemon.terms.new(c.who, 'command', pw.pw_dir, words, {'command': full}, run_as=pw.pw_name)
    return {'id': tid}


# ---------------------------------------------------------------------------
# Claude Code's own configuration, from the pages (1.0.9)
# ---------------------------------------------------------------------------
# Everything Claude Code reads besides its command line, for one Linux account
# and, where it has one, one project folder: its settings (user, project,
# local), its memory (CLAUDE.md), the permissions and hooks inside the
# settings, its MCP servers, agents, commands, skills and output styles, its
# plugins and marketplaces, the sessions it runs in the background, and what
# the conversations used. Files are read and written here as that account
# (its owner, its modes); what Claude Code keeps itself (~/.claude.json, the
# MCP servers and plugins) is changed by Claude Code's own commands, run as
# that account. An account changes its own; an administrator any.
CC_FILES = {
    # kind: {scope: path relative to the home (user) or the project folder}
    'settings': {'user': '.claude/settings.json', 'project': '.claude/settings.json',
                 'local': '.claude/settings.local.json'},
    'memory': {'user': '.claude/CLAUDE.md', 'project': 'CLAUDE.md', 'local': 'CLAUDE.local.md'},
    'keybindings': {'user': '.claude/keybindings.json'},
    'mcp': {'project': '.mcp.json'},
}
CC_JSON = ('settings', 'keybindings', 'mcp')
# kind: (folder under .claude, the file of one by its name)
CC_DIRS = {'agent': ('agents', '%s.md'), 'command': ('commands', '%s.md'),
           'skill': ('skills', '%s/SKILL.md'), 'style': ('output-styles', '%s.md')}
CC_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,80}(/[A-Za-z0-9][A-Za-z0-9._-]{0,80}){0,3}\Z')
CC_MOST = 512 * 1024
CC_SCOPES = ('user', 'project', 'local')
CC_HOOK_EVENTS = ('PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'UserPromptSubmit', 'Notification',
                  'Stop', 'SubagentStart', 'SubagentStop', 'PreCompact', 'SessionStart', 'SessionEnd',
                  'PermissionRequest')
CC_USAGE_CACHE = {}


def cc_target(c, src):
    """(the Linux account, the project folder or '') a request is about."""
    who_as = str(src.get('as') or run_as_of(c.who)).strip()
    if who_as != run_as_of(c.who):
        need_admin(c)
    pw = linux_user(who_as)
    project = str(src.get('project') or '').strip()
    if project:
        if project.startswith('~'):
            project = pw.pw_dir + project[1:]
        project = os.path.normpath(project)
        path_allowed(c.who, project)
        if not os.path.isdir(project):
            raise Refused('%s is not a folder' % project)
    return pw, project


def cc_base(pw, project, scope):
    if scope == 'user':
        return Path(pw.pw_dir)
    if scope in ('project', 'local'):
        if not project:
            raise Refused('a project folder first: the settings of a project are in it')
        return Path(project)
    raise Refused('the scope is user, project or local')


def cc_path(pw, project, kind, scope, name=''):
    """Where one file of Claude Code's is, for that account and project."""
    if kind in CC_FILES:
        rel = CC_FILES[kind].get(scope)
        if not rel:
            raise Refused('%s has no %s scope' % (kind, scope))
        return cc_base(pw, project, scope) / rel
    if kind in CC_DIRS:
        if scope not in ('user', 'project'):
            raise Refused('agents, commands, skills and styles are the user\'s or the project\'s')
        name = str(name or '').strip().strip('/')
        if not CC_NAME_RE.match(name) or '..' in name:
            raise Refused('a name of letters, digits, . _ - (and / for a folder of commands)')
        folder, pattern = CC_DIRS[kind]
        return cc_base(pw, project, scope) / '.claude' / folder / (pattern % name)
    raise Refused('no such kind of file: %s' % kind)


def cc_inside(pw, project, path):
    """Never through a link to somewhere else."""
    real = os.path.realpath(str(path.parent))
    for top in (pw.pw_dir, project):
        if top and (real == os.path.realpath(top) or real.startswith(os.path.realpath(top).rstrip('/') + '/')):
            return
    raise Refused('%s leads outside the home and the project' % path)


def cc_mkdirs(pw, path):
    """The folders of `path` made as the account, as Claude Code would."""
    missing = []
    p = Path(path).parent
    while not p.exists():
        missing.append(p)
        p = p.parent
    for d in reversed(missing):
        d.mkdir(mode=0o755)
        if os.geteuid() == 0:
            try:
                os.chown(str(d), pw.pw_uid, pw.pw_gid)
            except OSError:
                pass


def cc_write(pw, project, path, text, kind):
    text = str(text if text is not None else '')
    if len(text.encode('utf-8')) > CC_MOST:
        raise Refused('too big for here (%s at most)' % human_bytes(CC_MOST))
    if kind in CC_JSON and text.strip():
        try:
            json.loads(text)
        except ValueError as e:
            raise Refused('that is not JSON: %s' % e)
    cc_mkdirs(pw, path)
    cc_inside(pw, project, path)
    mode = 0o600 if path.name.endswith('.local.json') else 0o644
    try:
        mode = stat.S_IMODE(os.stat(str(path)).st_mode)
    except OSError:
        pass
    write_atomic(path, text.encode('utf-8'), mode=mode, uid=pw.pw_uid, gid=pw.pw_gid)


def cc_front(text):
    """The --- name: / description: --- head of an agent, a command or a skill."""
    out = {}
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', text or '', re.S)
    if m:
        for line in m.group(1).splitlines():
            k, sep, v = line.partition(':')
            if sep and k.strip() and not k.startswith(' '):
                out[k.strip()] = v.strip().strip('"\'')
    return out


def cc_items(pw, project, kind):
    folder, pattern = CC_DIRS[kind]
    out = []
    for scope in ('user', 'project'):
        if scope == 'project' and not project:
            continue
        top = cc_base(pw, project, scope) / '.claude' / folder
        if not top.is_dir():
            continue
        files = sorted(top.glob('*/SKILL.md')) if kind == 'skill' else sorted(top.rglob('*.md'))
        for f in files[:500]:
            rel = str(f.parent.relative_to(top)) if kind == 'skill' else str(f.relative_to(top))[:-3]
            text = read_text(f, 16384)
            fm = cc_front(text)
            try:
                st = f.stat()
            except OSError:
                continue
            out.append({'scope': scope, 'name': rel, 'title': fm.get('name') or rel,
                        'description': fm.get('description') or '', 'model': fm.get('model') or '',
                        'tools': fm.get('tools') or fm.get('allowed-tools') or '', 'path': str(f),
                        'size': st.st_size, 'mtime': st.st_mtime})
    return out


def cc_run(pw, args, cwd=None, timeout=60, input=None):
    """Claude Code's own command, as the account, in its login shell's PATH."""
    cmd = str(CONFIG.get('claude_cmd') or 'claude').strip() or 'claude'
    shell = pw.pw_shell if pw.pw_shell and os.path.exists(pw.pw_shell) and \
        not pw.pw_shell.endswith(('nologin', 'false')) else '/bin/bash'
    where = cwd if cwd and os.path.isdir(cwd) else (pw.pw_dir if os.path.isdir(pw.pw_dir) else '/')
    try:
        got = subprocess.run([shell, '-lc', 'exec %s "$@"' % shlex.quote(cmd), 'claude'] + [str(a) for a in args],
                             capture_output=True, text=True, timeout=timeout, input=input,
                             env=user_env(pw, {'CI': '1', 'NO_COLOR': '1', 'TERM': 'dumb'}), cwd=where,
                             **as_user_kwargs(pw))
    except subprocess.TimeoutExpired:
        raise Refused('claude %s did not answer in %d s' % (' '.join(map(str, args[:3])), timeout), 504)
    except OSError as e:
        raise Refused('claude could not be run: %s' % e, 500)
    out = re.sub(r'\x1b\[[0-9;?]*[ -/]*[@-~]', '', got.stdout or '')
    err = re.sub(r'\x1b\[[0-9;?]*[ -/]*[@-~]', '', got.stderr or '')
    return got.returncode, out, err


def cc_run_json(pw, args, cwd=None, timeout=60):
    rc, out, err = cc_run(pw, args, cwd, timeout)
    try:
        return json.loads(out)
    except ValueError:
        raise Refused((err or out or 'no answer').strip()[-400:] or 'claude %s said nothing' % args[0])


def cc_hide(d):
    """An MCP server's settings without the values of its secrets."""
    d = dict(d or {})
    for k in ('env', 'headers'):
        if isinstance(d.get(k), dict):
            d[k] = {x: ('•••' if v else '') for x, v in d[k].items()}
    return d


def cc_mcp(pw, project):
    out = []
    try:
        with open(os.path.join(pw.pw_dir, '.claude.json'), encoding='utf-8') as f:
            cj = json.load(f)
    except (OSError, ValueError):
        cj = {}
    for name, d in sorted((cj.get('mcpServers') or {}).items()):
        out.append(dict(cc_hide(d), name=name, scope='user'))
    if project:
        mine = ((cj.get('projects') or {}).get(project) or {})
        for name, d in sorted((mine.get('mcpServers') or {}).items()):
            out.append(dict(cc_hide(d), name=name, scope='local'))
        try:
            with open(os.path.join(project, '.mcp.json'), encoding='utf-8') as f:
                pj = json.load(f)
        except (OSError, ValueError):
            pj = {}
        for name, d in sorted((pj.get('mcpServers') or {}).items()):
            out.append(dict(cc_hide(d), name=name, scope='project'))
        approved = mine.get('enabledMcpjsonServers') or []
        denied = mine.get('disabledMcpjsonServers') or []
        for one in out:
            if one['scope'] == 'project':
                one['approved'] = one['name'] in approved
                one['denied'] = one['name'] in denied
    return out


def usage_file_rows(path, st):
    """Every answer of one transcript that says what it used, once each (a
    message is written again for every block of it): (day, model, folder,
    input, output, cache written, cache read, timestamp). Kept while the file
    stays the same size and age."""
    key = (path, st.st_mtime, st.st_size)
    rows = CC_USAGE_CACHE.get(key)
    if rows is not None:
        return rows
    rows = []
    seen = set()
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if '"usage"' not in line:
                    continue
                try:
                    m = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(m, dict):
                    continue
                msg = m.get('message') or {}
                u = msg.get('usage') if isinstance(msg, dict) else None
                mid = (msg.get('id') if isinstance(msg, dict) else None) or m.get('uuid')
                if not isinstance(u, dict) or not u or mid in seen:
                    continue
                seen.add(mid)
                ts = str(m.get('timestamp') or '')
                rows.append((ts[:10], str(msg.get('model') or '?'),
                             str(m.get('cwd') or os.path.basename(os.path.dirname(path))),
                             int(u.get('input_tokens') or 0), int(u.get('output_tokens') or 0),
                             int(u.get('cache_creation_input_tokens') or 0),
                             int(u.get('cache_read_input_tokens') or 0), ts))
    except OSError:
        return None
    for k in [k for k in CC_USAGE_CACHE if k[0] == path]:
        CC_USAGE_CACHE.pop(k, None)
    CC_USAGE_CACHE[key] = rows
    return rows


# What a million tokens costs at Anthropic's list prices (1.0.13): input,
# output, cache read; writing the cache is 1.25 x input. Matched by the
# start of the model's name, the longest first. Only an estimate for
# comparison - a Claude subscription is not billed by the token at all.
MODEL_PRICES = [
    ('claude-fable-5-1', 10.0, 50.0, 0.25), ('claude-mythos-5-1', 10.0, 50.0, 0.25),
    ('claude-fable-5', 10.0, 50.0, 1.0), ('claude-mythos', 10.0, 50.0, 1.0),
    ('claude-opus-5-5', 4.0, 20.0, 0.20), ('claude-opus-5', 5.0, 25.0, 0.50),
    ('claude-opus-4-8', 5.0, 25.0, 0.50), ('claude-opus-4-7', 5.0, 25.0, 0.50),
    ('claude-opus-4-6', 5.0, 25.0, 0.50), ('claude-opus-4-5', 5.0, 25.0, 0.50),
    ('claude-opus-4', 15.0, 75.0, 1.50), ('claude-3-opus', 15.0, 75.0, 1.50),
    ('claude-sonnet-5-5', 2.0, 10.0, 0.20), ('claude-sonnet-5', 2.0, 10.0, 0.20),
    ('claude-sonnet', 3.0, 15.0, 0.30), ('claude-3-7-sonnet', 3.0, 15.0, 0.30),
    ('claude-3-5-sonnet', 3.0, 15.0, 0.30),
    ('claude-haiku-5-5', 0.10, 0.50, 0.01), ('claude-haiku-4-5', 1.0, 5.0, 0.10),
    ('claude-3-5-haiku', 0.80, 4.0, 0.08), ('claude-haiku', 1.0, 5.0, 0.10),
]
MODEL_PRICES.sort(key=lambda p: -len(p[0]))


def usage_cost(model, i, o, cw, cr):
    """Dollars at list prices, or None for a model not in the table."""
    m = str(model or '').lower()
    for name, pin, pout, pread in MODEL_PRICES:
        if m.startswith(name):
            return (i * pin + o * pout + cw * pin * 1.25 + cr * pread) / 1e6
    return None


def usage_accounts(who):
    """The Linux accounts whose chats someone may count: an administrator
    every one with Claude Code's transcripts, anybody else their own."""
    if who.get('role') != 'admin':
        try:
            return [linux_user(run_as_of(who))]
        except Refused:
            return []
    out = []
    for pw in pwd.getpwall():
        if pw.pw_uid != 0 and pw.pw_uid < 1000:
            continue
        if os.path.isdir(os.path.join(pw.pw_dir, '.claude', 'projects')):
            out.append(pw)
    return out


def chat_usage(daemon, who, days=30):
    """Every chat with Claude Code of the accounts someone may see, with what
    it used and what that would cost at list prices - and the same by day,
    model, account and folder. A chat is one transcript of Claude Code; the
    terminal of these pages it ran in is found by its account, its folder and
    its time."""
    days = max(1, min(366, int(days or 30)))
    since = time.time() - days * 86400
    cut = datetime.fromtimestamp(since).strftime('%Y-%m-%d')
    zero = lambda k: {'key': k, 'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0,
                      'messages': 0, 'cost': 0.0, 'chats': 0}
    total = zero('all')
    books = {'day': {}, 'model': {}, 'account': {}, 'project': {}, 'hour': {}}
    chats, unpriced = [], set()
    terms = daemon.store.q('SELECT id, owner, run_as, title, kind, cwd, created, ended, opts FROM terms')
    for pw in usage_accounts(who):
        top = Path(pw.pw_dir) / '.claude' / 'projects'
        for f in top.glob('*/*.jsonl'):
            try:
                st = f.stat()
            except OSError:
                continue
            if st.st_mtime < since or not UUID_RE.match(f.stem):
                continue
            rows = usage_file_rows(str(f), st)
            if not rows:
                continue
            ch = dict(zero(f.stem), id=f.stem, account=pw.pw_name, cwd='', first='', last='', models={})
            for day, model, cwd, i, o, cw, cr, ts in rows:
                if (day and day < cut) or model == '<synthetic>':
                    continue
                cost = usage_cost(model, i, o, cw, cr)
                if cost is None:
                    unpriced.add(model)
                    cost = 0.0
                ch['cwd'] = ch['cwd'] or cwd
                ch.setdefault('_dirs', set()).add(cwd)
                ch['first'] = min(ch['first'] or ts, ts) if ts else ch['first']
                ch['last'] = max(ch['last'], ts)
                ch['models'][model] = ch['models'].get(model, 0) + 1
                hour = ''
                if len(ts) >= 13:
                    try:
                        hour = '%02d' % datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone().hour
                    except ValueError:
                        hour = ts[11:13]
                for b in [ch, total] + [books[n].setdefault(k, zero(k)) for n, k in
                                        (('day', day), ('model', model), ('account', pw.pw_name),
                                         ('project', cwd), ('hour', hour)) if k]:
                    b['input'] += i
                    b['output'] += o
                    b['cache_write'] += cw
                    b['cache_read'] += cr
                    b['messages'] += 1
                    b['cost'] += cost
            if not ch['messages']:
                continue
            for m in ch['models']:
                books['model'][m]['chats'] += 1
            books['account'][pw.pw_name]['chats'] += 1
            for k in ch.pop('_dirs', ()):
                books['project'][k]['chats'] += 1
            total['chats'] += 1
            facts = conversation_facts(str(f)) or {}
            ch['title'] = facts.get('summary') or facts.get('first') or ''
            ch['models'] = sorted(ch['models'], key=lambda m: -ch['models'][m])
            ch['term'] = usage_term(terms, pw.pw_name, ch)
            chats.append(ch)
    chats.sort(key=lambda c: c['last'], reverse=True)
    for c in chats:
        c['cost'] = round(c['cost'], 4)
    out = {'days': days, 'total': dict(total, cost=round(total['cost'], 4)),
           'chats': chats[:500], 'more': max(0, len(chats) - 500), 'unpriced': sorted(unpriced),
           'accounts': [pw.pw_name for pw in usage_accounts(who)]}
    for n, b in books.items():
        rows = [dict(v, cost=round(v['cost'], 4)) for v in b.values()]
        if n in ('day', 'hour'):
            rows.sort(key=lambda x: x['key'])
        else:
            rows.sort(key=lambda x: (-x['cost'], -(x['input'] + x['output'])))
        out['by_' + n] = rows[:60] if n == 'project' else rows
    return out


def _ts_epoch(ts):
    try:
        return datetime.fromisoformat(str(ts).replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0.0


def usage_term(terms, account, ch):
    """The terminal of these pages a chat most likely ran in: Claude Code, the
    same account and folder, open while the chat began."""
    for t in terms:
        try:
            if t.get('run_as') == account and json.loads(t.get('opts') or '{}').get('sid') == ch['id']:
                return {'id': t['id'], 'title': t.get('title') or ''}
        except ValueError:
            pass
    t0 = _ts_epoch(ch['first'])
    best = None
    for t in terms:
        if t.get('kind') != 'claude' or t.get('run_as') != account:
            continue
        if os.path.normpath(str(t.get('cwd') or '')) != os.path.normpath(ch['cwd'] or ''):
            continue
        start, end = float(t.get('created') or 0), float(t.get('ended') or 0) or time.time()
        if t0 and start - 120 <= t0 <= end + 60:
            if best is None or float(t['created']) > float(best['created']):
                best = t
    return {'id': best['id'], 'title': best.get('title') or ''} if best else None


def cc_usage(pw, days=30):
    """What the conversations of an account used, from Claude Code's own
    transcripts: tokens by day, by model and by project folder."""
    top = Path(pw.pw_dir) / '.claude' / 'projects'
    since = time.time() - days * 86400
    by_day, by_model, by_project = {}, {}, {}
    total = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0, 'messages': 0, 'sessions': 0}
    if not top.is_dir():
        return {'days': days, 'total': total, 'by_day': [], 'by_model': [], 'by_project': []}
    for f in top.glob('*/*.jsonl'):
        try:
            st = f.stat()
        except OSError:
            continue
        if st.st_mtime < since:
            continue
        rows = usage_file_rows(str(f), st)
        if rows is None:
            continue
        cut = datetime.fromtimestamp(since).strftime('%Y-%m-%d')
        used = False
        for day, model, cwd, i, o, cw, cr, _ts in rows:
            if (day and day < cut) or model == '<synthetic>':
                continue
            used = True
            for book, k in ((by_day, day), (by_model, model), (by_project, cwd)):
                b = book.setdefault(k, {'key': k, 'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0,
                                        'messages': 0})
                b['input'] += i
                b['output'] += o
                b['cache_write'] += cw
                b['cache_read'] += cr
                b['messages'] += 1
            total['input'] += i
            total['output'] += o
            total['cache_write'] += cw
            total['cache_read'] += cr
            total['messages'] += 1
        if used:
            total['sessions'] += 1
    return {'days': days, 'total': total,
            'by_day': sorted(by_day.values(), key=lambda x: x['key']),
            'by_model': sorted(by_model.values(), key=lambda x: -(x['output'] + x['input'])),
            'by_project': sorted(by_project.values(), key=lambda x: -(x['output'] + x['input']))[:40]}


@route('GET', '/api/cc')
def api_cc(c):
    src = {'as': c.arg('as'), 'project': c.arg('project')}
    pw, project = cc_target(c, src)
    what = c.arg('what') or 'overview'
    base = {'as': pw.pw_name, 'home': pw.pw_dir, 'project': project}
    if what == 'overview':
        facts = claude_facts(pw)
        out = dict(base, facts=facts, files={}, counts={})
        for kind, scopes in CC_FILES.items():
            for scope in scopes:
                if scope != 'user' and not project:
                    continue
                p = cc_path(pw, project, kind, scope)
                out['files']['%s:%s' % (kind, scope)] = {'path': str(p), 'there': p.is_file(),
                                                        'size': p.stat().st_size if p.is_file() else 0}
        for kind in CC_DIRS:
            out['counts'][kind] = len(cc_items(pw, project, kind))
        out['mcp'] = len(cc_mcp(pw, project))
        if c.arg('auth') == '1':
            try:
                out['auth'] = cc_run_json(pw, ['auth', 'status'], project or None, 30)
            except Refused as e:
                out['auth'] = {'error': str(e)}
        return out
    if what == 'file':
        p = cc_path(pw, project, c.arg('kind'), c.arg('scope') or 'user', c.arg('name'))
        text = read_text(p, CC_MOST) if p.is_file() else ''
        return dict(base, path=str(p), there=p.is_file(), text=text,
                    mtime=p.stat().st_mtime if p.is_file() else None)
    if what == 'items':
        kind = c.arg('kind')
        if kind not in CC_DIRS:
            raise Refused('agent, command, skill or style')
        return dict(base, kind=kind, items=cc_items(pw, project, kind))
    if what == 'mcp':
        out = dict(base, servers=cc_mcp(pw, project))
        if c.arg('check') == '1':
            rc, so, se = cc_run(pw, ['mcp', 'list'], project or None, 90)
            out['check'] = (so or se).strip()
        return out
    if what == 'plugins':
        out = dict(base)
        out['installed'] = cc_run_json(pw, ['plugin', 'list', '--json'], project or None, 60)
        out['marketplaces'] = cc_run_json(pw, ['plugin', 'marketplace', 'list', '--json'], project or None, 60)
        if c.arg('available') == '1':
            try:
                out['available'] = cc_run_json(pw, ['plugin', 'list', '--available', '--json'], project or None, 120)
            except Refused as e:
                out['available_error'] = str(e)
        return out
    if what == 'agents':
        got = cc_run_json(pw, ['agents', '--json', '--all'], project or None, 30)
        return dict(base, sessions=got if isinstance(got, list) else [])
    if what == 'logs':
        sid = c.arg('id')
        if not re.match(r'^[A-Za-z0-9_.-]{1,80}\Z', sid):
            raise Refused('which session?')
        rc, so, se = cc_run(pw, ['logs', sid], project or None, 30)
        return dict(base, text=(so or se))
    if what == 'usage':
        return dict(base, usage=cc_usage(pw, max(1, min(365, int(c.arg('days') or 30)))))
    if what == 'hooks':
        return dict(base, events=list(CC_HOOK_EVENTS))
    raise Refused('overview, file, items, mcp, plugins, agents, logs, usage or hooks')


@route('POST', '/api/cc')
def api_cc_do(c):
    b = c.body
    pw, project = cc_target(c, b)
    act = str(b.get('action') or '')
    st = c.daemon.store
    where = '%s%s' % (pw.pw_name, (' in ' + project) if project else '')
    if act in ('write', 'delete'):
        kind, scope = str(b.get('kind') or ''), str(b.get('scope') or 'user')
        p = cc_path(pw, project, kind, scope, b.get('name'))
        if act == 'write':
            if b.get('mtime') and p.is_file() and abs(p.stat().st_mtime - float(b['mtime'])) > 0.001:
                raise Refused('it was changed meanwhile (by Claude Code, or elsewhere) - load it again', 409)
            cc_write(pw, project, p, b.get('text'), kind)
            st.add_event('claude', '%s wrote %s (%s)' % (c.name, p, where), who=c.name)
            return {'message': 'saved: %s' % p, 'path': str(p), 'mtime': p.stat().st_mtime}
        cc_inside(pw, project, p)
        if not p.exists():
            raise Refused('%s is not there' % p, 404)
        if kind == 'skill':
            shutil.rmtree(str(p.parent))
        else:
            p.unlink()
        st.add_event('claude', '%s deleted %s (%s)' % (c.name, p, where), 'warn', who=c.name)
        return {'message': 'deleted: %s' % p}
    if act in ('mcp_add', 'mcp_remove', 'mcp_approve'):
        name = str(b.get('name') or '').strip()
        if not re.match(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z', name):
            raise Refused('the name of a server: letters, digits, _ . -')
        scope = str(b.get('scope') or 'local')
        if scope not in CC_SCOPES:
            raise Refused('the scope is user, project or local')
        if scope != 'user' and not project:
            raise Refused('a project folder first: a server of the %s scope belongs to one' % scope)
        if act == 'mcp_add':
            conf = b.get('config')
            if not isinstance(conf, dict) or not (conf.get('command') or conf.get('url')):
                raise Refused('a server is a command (stdio) or an address (http, sse)')
            rc, so, se = cc_run(pw, ['mcp', 'add-json', '-s', scope, name, json.dumps(conf)], project or None, 60)
        elif act == 'mcp_remove':
            rc, so, se = cc_run(pw, ['mcp', 'remove', '-s', scope, name], project or None, 60)
        else:
            # A server of .mcp.json let in (or kept out) for this project, as
            # Claude Code asks at its start.
            cj_path = os.path.join(pw.pw_dir, '.claude.json')
            try:
                with open(cj_path, encoding='utf-8') as f:
                    cj = json.load(f)
            except (OSError, ValueError):
                cj = {}
            mine = cj.setdefault('projects', {}).setdefault(project, {})
            on, off = set(mine.get('enabledMcpjsonServers') or []), set(mine.get('disabledMcpjsonServers') or [])
            (on.add if b.get('yes') else on.discard)(name)
            (off.discard if b.get('yes') else off.add)(name)
            mine['enabledMcpjsonServers'], mine['disabledMcpjsonServers'] = sorted(on), sorted(off)
            write_atomic(cj_path, json.dumps(cj, indent=2), mode=0o600, uid=pw.pw_uid, gid=pw.pw_gid)
            rc, so, se = 0, 'let in' if b.get('yes') else 'kept out', ''
        if rc != 0:
            raise Refused((se or so).strip()[-400:] or 'claude mcp said no')
        st.add_event('claude', '%s: MCP %s %s (%s, %s)' % (c.name, act[4:], name, scope, where), who=c.name)
        return {'message': (so or se).strip()[-400:] or 'done', 'servers': cc_mcp(pw, project)}
    if act in ('plugin', 'marketplace'):
        sub = str(b.get('sub') or '')
        allowed = {'plugin': ('install', 'uninstall', 'enable', 'disable', 'update'),
                   'marketplace': ('add', 'remove', 'update')}[act]
        if sub not in allowed:
            raise Refused('%s: one of %s' % (act, ', '.join(allowed)))
        target = str(b.get('target') or '').strip()
        if not re.match(r'^[A-Za-z0-9@:/._+~-]{1,300}\Z', target) and not (act == 'marketplace' and sub == 'update'):
            raise Refused('which plugin or marketplace?')
        args = (['plugin'] if act == 'plugin' else ['plugin', 'marketplace']) + [sub] + ([target] if target else [])
        if act == 'plugin' and b.get('scope') in CC_SCOPES and sub in ('install', 'uninstall', 'enable', 'disable'):
            args += ['--scope', b['scope']]
        rc, so, se = cc_run(pw, args, project or None, 300)
        if rc != 0:
            raise Refused((se or so).strip()[-500:] or 'claude %s said no' % ' '.join(args))
        st.add_event('claude', '%s: claude %s (%s)' % (c.name, ' '.join(args), where), who=c.name)
        return {'message': (so or se).strip()[-500:] or 'done'}
    if act in ('stop', 'rm', 'respawn'):
        sid = str(b.get('id') or '')
        if not re.match(r'^[A-Za-z0-9_.-]{1,80}\Z', sid):
            raise Refused('which session?')
        rc, so, se = cc_run(pw, [act, sid], project or None, 60)
        if rc != 0:
            raise Refused((se or so).strip()[-400:] or 'claude %s said no' % act)
        st.add_event('claude', '%s: claude %s %s (%s)' % (c.name, act, sid, where), who=c.name)
        return {'message': (so or se).strip()[-400:] or 'done'}
    if act == 'attach':
        sid = str(b.get('id') or '')
        if not re.match(r'^[A-Za-z0-9_.-]{1,80}\Z', sid):
            raise Refused('which session?')
        tid = c.daemon.terms.new(c.who, 'claude', project or pw.pw_dir, 'attach %s' % sid, {'attach': sid},
                                 run_as=pw.pw_name)
        return {'id': tid}
    if act == 'doctor':
        rc, so, se = cc_run(pw, ['doctor'], project or None, 90)
        return {'text': (so + ('\n' + se if se else '')).strip()}
    raise Refused('write, delete, mcp_add, mcp_remove, mcp_approve, plugin, marketplace, stop, rm, respawn, '
                  'attach or doctor')


# ---- the second step of signing in (otp's, 1.0.125) ------------------------------------------
# With admin_2fa on, a right password opens a sign-in that can do nothing yet
# but its second step (MFA_ALLOWED): a code from an app, or one sent by mail.
# The first time the account chooses how and proves it (enrol); after that it
# gives the code each time (check). The way chosen is the account's own, kept
# in meta 'adm2fa:<name>':
#   {'kind': 'app'|'mail', 'secret': sealed (app), 'dest': (mail), 'at', 'step'}
# Accounts → Reset the second step and ai --reset-2fa NAME take it away.
MFA_ALLOWED = ('/api/auth/mfa', '/api/auth/logout', '/api/auth/whoami')
MFA_SEND_GAP_S = 30
MFA_SEND_MOST = 5
MFA_LOCK = threading.Lock()
MFA_KIND_WORDS = {'app': 'an authenticator app', 'mail': 'a code by e-mail', 'sms': 'a code by SMS'}


def mfa_key(name):
    return 'adm2fa:' + str(name or '').strip().lower()


def mfa_get(store, name):
    got = store.meta_json(mfa_key(name))
    return got if isinstance(got, dict) else None


def mfa_all(store):
    out = {}
    for r in store.q("SELECT k, v FROM meta WHERE k LIKE 'adm2fa:%'"):
        try:
            v = json.loads(r['v'] or '{}')
        except ValueError:
            continue
        out[r['k'][len('adm2fa:'):]] = {'kind': v.get('kind'), 'at': v.get('at'),
                                        'dest': dest_masked(v.get('kind'), v.get('dest'))}
    return out


def mfa_reset(store, name, by):
    had = mfa_get(store, name)
    store.x('DELETE FROM meta WHERE k=?', (mfa_key(name),))
    store.add_event('accounts', '%s reset the second step of signing in of %s%s' % (
        by, name, ' (it was %s)' % MFA_KIND_WORDS.get(had.get('kind'), had.get('kind'))
        if had else ' (none was set up)'), 'warn', who=by)
    return bool(had)


def code_channels():
    """Which ways of sending a code can be used at all - set up, not off."""
    out = []
    if (CONFIG.get('mail_mode') or 'off') != 'off' and CONFIG.get('mail_from'):
        out.append('mail')
    mode = CONFIG.get('sms_mode') or 'off'
    if (mode == 'http' and CONFIG.get('sms_url')) or (mode == 'spool' and CONFIG.get('sms_spool_dir')) or \
            (mode == 'teltonika' and CONFIG.get('sms_tel_host')):
        out.append('sms')
    return out


def mfa_methods():
    out = []
    if CONFIG.get('admin_2fa_app', True):
        out.append('app')
    if CONFIG.get('admin_2fa_mail', True) and 'mail' in code_channels():
        out.append('mail')
    if CONFIG.get('admin_2fa_sms', True) and 'sms' in code_channels():
        out.append('sms')
    return out or ['app']


def mfa_stage(store, name):
    rec = mfa_get(store, name)
    if rec and rec.get('kind') in ('app', 'mail', 'sms'):
        return 'check'
    return 'enrol'


def code_new():
    digits = int(CONFIG.get('code_digits') or 6)
    return '%0*d' % (digits, secrets.randbelow(10 ** digits))


def code_hash(salt, code):
    key = sealing_key(make=True) or b''
    return hmac.new(key + b'|code', ('%s|%s' % (salt, code)).encode('utf-8'),
                    hashlib.sha256).hexdigest()


# ---- the texts of the codes (otp's CODE_TEXTS, the words of these pages) ----------------
# The second step of signing in to these pages, and checking the address or
# the number it goes to: the mail (HTML with a plain-text part, or plain text
# only - code_mail_fmt) and the SMS, in Czech and English. Changed on the
# pages under Settings → Message texts, as otp's.
CODE_PURPOSES = {
    'signin': {'p': '', 'subject': 'mail_subject', 'body': 'mail_body', 'sms': 'sms',
               'warn': True, 'note': 'h_warn', 'queue': 'code'},
    'verify': {'p': 'v_', 'subject': 'verify_subject', 'body': 'verify_body', 'sms': 'sms_verify',
               'warn': False, 'note': 'h_v_note', 'queue': 'verify'},
}


def code_purpose(purpose):
    return CODE_PURPOSES.get(purpose) or CODE_PURPOSES['verify']


CODE_TEXTS = {
    'cs': {
        'mail_subject': 'Kód pro přihlášení: {code}',
        'mail_body': ('Váš kód pro přihlášení na stránky {site} je\n\n    {code}\n\n'
                      'Platí {minutes} min a jen jednou. Pokud jste se právě nepřihlašovali, '
                      'kód nikomu nesdělujte a změňte si heslo - někdo ho zná.\n\n-- \n{site}'),
        'verify_subject': 'Ověření adresy: {code}',
        'verify_body': ('Kód pro ověření této adresy pro přihlašování na stránky {site} je\n\n'
                        '    {code}\n\nZadejte ho na stránce, kde si nastavujete druhý krok '
                        'přihlášení. Platí {minutes} min.\n\nPokud jste o nic nežádali, zprávu '
                        'smažte.\n\n-- \n{site}'),
        'sms': '{code} je váš kód pro přihlášení ({site}). Platí {minutes} min. Nikomu ho '
               'nesdělujte.',
        'sms_verify': '{code} je kód pro ověření tohoto čísla ({site}).',
        'h_title': 'Druhý krok přihlášení',
        'h_hello': 'Dobrý den, {name},', 'h_hello_anon': 'Dobrý den,',
        'h_lede': 'váš kód pro přihlášení k účtu <b>{account}</b>:',
        'h_lede_anon': 'váš kód pro přihlášení:',
        'h_facts': 'Zadejte ho na přihlašovací stránce. Platí {minutes} min a jen jednou.',
        'h_warn': 'Pokud jste se právě nepřihlašovali, kód nikomu nesdělujte a změňte si heslo '
                  '– někdo ho zná.',
        'h_foot': 'Posláno automaticky z {site}. Na tento e-mail neodpovídejte.',
        'h_v_title': 'Druhý krok přihlášení',
        'h_v_hello': 'Dobrý den, {name},', 'h_v_hello_anon': 'Dobrý den,',
        'h_v_lede': 'kód pro ověření této adresy pro přihlašování k účtu <b>{account}</b>:',
        'h_v_lede_anon': 'kód pro ověření této adresy pro přihlašování:',
        'h_v_facts': 'Zadejte ho na stránce, kde si nastavujete druhý krok přihlášení. Platí '
                     '{minutes} min.',
        'h_v_note': 'Pokud jste o nic nežádali, e-mail smažte – bez kódu se nic nezmění.',
        'h_v_foot': 'Posláno automaticky z {site}. Na tento e-mail neodpovídejte.',
    },
    'en': {
        'mail_subject': 'Your sign-in code: {code}',
        'mail_body': ('Your code to sign in to {site} is\n\n    {code}\n\nIt is good for '
                      '{minutes} min and once. If you are not signing in just now, tell nobody '
                      'the code and change your password - somebody knows it.\n\n-- \n{site}'),
        'verify_subject': 'Checking this address: {code}',
        'verify_body': ('The code to check this address for signing in to {site} is\n\n'
                        '    {code}\n\nType it on the page where you are setting up the second '
                        'step. It is good for {minutes} min.\n\nIf you asked for nothing, delete '
                        'this mail.\n\n-- \n{site}'),
        'sms': '{code} is your sign-in code ({site}). Good for {minutes} min. Tell nobody.',
        'sms_verify': '{code} is the code to check this number ({site}).',
        'h_title': 'Second step of signing in',
        'h_hello': 'Hello {name},', 'h_hello_anon': 'Hello,',
        'h_lede': 'your code to sign in as <b>{account}</b>:',
        'h_lede_anon': 'your code to sign in:',
        'h_facts': 'Type it on the sign-in page. It is good for {minutes} min and once.',
        'h_warn': 'If you are not signing in just now, tell nobody the code and change your '
                  'password - somebody knows it.',
        'h_foot': 'Sent automatically by {site}. Do not reply to this mail.',
        'h_v_title': 'Second step of signing in',
        'h_v_hello': 'Hello {name},', 'h_v_hello_anon': 'Hello,',
        'h_v_lede': 'the code to check this address for signing in as <b>{account}</b>:',
        'h_v_lede_anon': 'the code to check this address for signing in:',
        'h_v_facts': 'Type it on the page where you are setting up the second step. It is good '
                     'for {minutes} min.',
        'h_v_note': 'If you asked for nothing, delete this mail - without the code nothing '
                    'changes.',
        'h_v_foot': 'Sent automatically by {site}. Do not reply to this mail.',
    },
}


def code_lang():
    lang = str(CONFIG.get('code_lang') or CONFIG.get('mail_lang') or 'cs')
    return lang if lang in CODE_TEXTS else 'cs'


def mail_lang(lang=None):
    lang = lang or CONFIG.get('mail_lang') or 'cs'
    return lang if lang in CODE_TEXTS else 'en'


def site_words():
    return str(CONFIG.get('site_name') or host_name())


def code_words(key, lang=None, w=None, **kw):
    """One of the texts of codes, as Settings → Message texts has it, its
    {words} filled in."""
    if w is None:
        w = texts_for('code', lang if lang in CODE_TEXTS else code_lang())
    kw.setdefault('site', site_words())
    kw.setdefault('minutes', max(1, int(CONFIG.get('code_ttl_s') or 300) // 60))
    return w[key].format(**kw)


def mail_headers(msg, to, subject):
    from email.utils import formataddr, formatdate, make_msgid
    sender = str(CONFIG.get('mail_from') or '').strip()
    if not sender:
        raise MailError('no sender address is set - Settings → Mail → From (address)')
    msg['Subject'] = subject
    msg['From'] = formataddr((str(CONFIG.get('mail_from_name') or site_words()), sender))
    msg['To'] = ', '.join(to) if isinstance(to, (list, tuple)) else to
    if CONFIG.get('mail_reply_to'):
        msg['Reply-To'] = str(CONFIG.get('mail_reply_to'))
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=sender.rsplit('@', 1)[-1] or None)
    msg['Auto-Submitted'] = 'auto-generated'
    return msg


def mail_message(to, subject, body):
    """A mail of plain text (the notices)."""
    from email.message import EmailMessage
    msg = mail_headers(EmailMessage(), to, subject)
    msg.set_content(body)
    return msg


def test_mail(to, lang='cs'):
    from email.message import EmailMessage
    site = site_words()
    msg = mail_headers(EmailMessage(), to, ('Zkušební zpráva z %s' if lang == 'cs'
                                            else 'A test message from %s') % site)
    msg.set_content(('Tato zpráva ověřuje, že %s umí odesílat poštu. Není třeba nic dělat.'
                     if lang == 'cs' else 'This message checks that %s can send mail. '
                     'Nothing needs doing.') % site)
    return msg


def code_mail_html(code, purpose, lang, name='', display='', w=None):
    """The mail of a code (otp's): the blue band, the white card, the code in
    a grey box, the warning in orange - tables and styles on each element, as
    every mail program shows them alike. Its words as Settings → Message
    texts has them, or `w` - the editor's, not yet saved."""
    lang = lang if lang in CODE_TEXTS else code_lang()
    if w is None:
        w = texts_for('code', lang)
    h = lambda t: html.escape(str(t or ''), quote=True)
    site = site_words()
    issuer = str(CONFIG.get('totp_issuer') or '') or site
    minutes = max(1, int(CONFIG.get('code_ttl_s') or 300) // 60)
    acc = ('<span style="white-space:nowrap">%s</span>' % h(name).replace('@', '@&#8205;')
           if name else '')
    font = "font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
    rows = []
    cp = code_purpose(purpose)
    v = cp['p']
    hello = (w['h_%shello' % v].format(name=h(display)) if display
             else w['h_%shello_anon' % v].format())
    if hello.strip():
        rows.append('<p style="margin:0 0 6px;font-size:16px;color:#111827">%s</p>' % hello)
    lede = (w['h_%slede' % v].format(account=acc) if name
            else w['h_%slede_anon' % v].format())
    facts, note, warn = w['h_%sfacts' % v], w[cp['note']], cp['warn']
    if lede.strip():
        rows.append('<p style="margin:0 0 18px;font-size:15px;line-height:1.55;color:#374151">'
                    '%s</p>' % lede)
    spaced = ' '.join(code[i:i + 3] for i in range(0, len(code), 3)) if len(code) == 6 else code
    rows.append('<table role="presentation" width="100%%" cellspacing="0" cellpadding="0" '
                'border="0" style="margin:0 0 10px"><tr><td align="center">'
                '<table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr>'
                '<td align="center" bgcolor="#f3f4f6" style="padding:16px 30px;background:#f3f4f6;'
                'border:1px solid #e5e7eb;border-radius:12px;font-family:Consolas,Menlo,'
                '\'Courier New\',monospace;font-size:34px;font-weight:700;letter-spacing:6px;'
                'color:#111827;white-space:nowrap">%s</td></tr></table></td></tr></table>' % h(spaced))
    if facts.strip():
        rows.append('<p style="margin:0 0 22px;font-size:13.5px;line-height:1.5;color:#6b7280;'
                    'text-align:center;%s">%s</p>' % (font, facts.format(minutes=minutes)))
    else:
        rows.append('<div style="height:12px;line-height:12px;font-size:1px">&nbsp;</div>')
    note = note.format()
    if not note.strip():
        pass
    elif warn:
        rows.append('<table role="presentation" width="100%%" cellspacing="0" cellpadding="0" '
                    'border="0"><tr><td bgcolor="#fff7ed" style="padding:12px 16px;'
                    'background:#fff7ed;border-left:4px solid #f59e0b;font-size:13px;'
                    'line-height:1.5;color:#7c2d12;%s">%s</td></tr></table>' % (font, note))
    else:
        rows.append('<table role="presentation" width="100%%" cellspacing="0" cellpadding="0" '
                    'border="0"><tr><td bgcolor="#eff6ff" style="padding:12px 16px;'
                    'background:#eff6ff;border-left:4px solid #2563eb;font-size:13px;'
                    'line-height:1.5;color:#1e3a8a;%s">%s</td></tr></table>' % (font, note))
    subject = w[cp['subject']].format(code=code, site=site, minutes=minutes)
    title = w['h_%stitle' % v].format(site=site)
    foot = w['h_%sfoot' % v].format(site=h(site))
    return ('<!doctype html><html lang="%s" xmlns:v="urn:schemas-microsoft-com:vml" '
            'xmlns:o="urn:schemas-microsoft-com:office:office"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title>'
            '<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch>'
            '</o:OfficeDocumentSettings></xml><![endif]--></head>'
            '<body style="margin:0;padding:0;background:#f3f4f6;%s">'
            '<table role="presentation" width="100%%" cellspacing="0" cellpadding="0" '
            'border="0" bgcolor="#f3f4f6" style="background:#f3f4f6"><tr><td align="center" '
            'style="padding:28px 12px">'
            '<table role="presentation" width="560" cellspacing="0" cellpadding="0" border="0" '
            'bgcolor="#ffffff" style="max-width:560px;width:100%%;background:#ffffff;'
            'border-radius:14px;overflow:hidden;border:1px solid #e5e7eb">'
            '<tr><td bgcolor="#1e3a8a" style="background:#1e3a8a;padding:20px 28px;'
            'color:#ffffff;%s">'
            '<p style="margin:0;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;'
            'color:#c7d2fe">%s</p><p style="margin:4px 0 0;font-size:20px;font-weight:700;'
            'color:#ffffff">%s</p></td></tr>'
            '<tr><td style="padding:26px 28px;%s">%s</td></tr>'
            '<tr><td style="padding:14px 28px 22px;font-size:12px;color:#9ca3af;%s;'
            'border-top:1px solid #f3f4f6">%s</td></tr></table></td></tr></table></body></html>'
            % (lang, h(subject), font, font, h(issuer), h(title), font, ''.join(rows),
               font, foot))


def code_message(kind, to, code, purpose='signin', lang=None, name='', display='', fmt=None,
                 w=None):
    """The mail or the SMS text of a code. `w`: the words to use instead of
    those saved - the message texts editor's test."""
    from email.message import EmailMessage
    cp = code_purpose(purpose)
    if kind == 'sms':
        return code_words(cp['sms'], lang=lang, w=w, code=code)
    msg = mail_headers(EmailMessage(), to, code_words(cp['subject'], lang=lang, w=w, code=code))
    msg.set_content(code_words(cp['body'], lang=lang, w=w, code=code))
    if (fmt or ('text' if CONFIG.get('code_mail_fmt') == 'text' else 'html')) != 'text':
        msg.add_alternative(code_mail_html(code, purpose, lang, name, display, w=w),
                            subtype='html')
    return msg


# ---- the notices (ai's own: what Events marks as a warning or a failure) -----------------
NOTICE_TEXTS = {
    'cs': {'subject': '{site}: {n} {what}', 'body': 'Stránky {site} hlásí:\n\n{lines}\n\nVše je v Událostech: {url}\n',
           'what': ('upozornění', 'upozornění', 'upozornění')},
    'en': {'subject': '{site}: {n} {what}', 'body': '{site} says:\n\n{lines}\n\nEverything is in Events: {url}\n',
           'what': ('notice', 'notices', 'notices')},
}


# ---- an SMS ----------------------------------------------------------------------------
def send_sms(store, to, text, what, who=''):
    """An SMS sent now; what the gateway said, written into the events - never
    what it held."""
    STORE_NOW['store'] = store
    try:
        said = sms_send(to, text)
    except SmsError as e:
        store.add_event('sms', 'the SMS to %s (%s) was not sent: %s' % (dest_masked('sms', to), what, e),
                        'warn', who=who or None)
        raise
    store.add_event('sms', 'an SMS to %s (%s): %s' % (dest_masked('sms', to), what, str(said or 'sent')[:300]),
                    who=who or None)
    return said


# ---------------------------------------------------------------------------
# The outgoing mail (otp's, 1.0.95)
# ---------------------------------------------------------------------------
# Every mail goes through here: tried at once, and what the receiving side
# did not take yet - greylisting's "try again later", a server away, a full
# mailbox - waits and is tried again, for mail_retry_hours (a code to sign
# in with only while it is good). Kept in the database as rows of meta under
# keys of their own; the pages can send one again or take it away. What a
# mail holds - a code - is sealed while it waits and thrown away once it went.
MAILQ_PREFIX = 'mailq:'
MAILB_PREFIX = 'mailb:'
MAILQ_DELAYS = (60, 120, 300, 600, 900, 1800)           # then every hour
MAILQ_CODE_DELAYS = (30, 60)                            # then every minute
MAILQ_KIND_WORDS = {'code': 'a code to sign in', 'verify': 'a code to check an address',
                    'test': 'a test', 'notice': 'notices', 'other': 'a mail'}
MAILQ_STATES = ('sending', 'waiting', 'sent', 'failed', 'expired')
MAILQ_LOCK = threading.Lock()


def mailq_new_id():
    return '%013d-%s' % (int(time.time() * 1000), secrets.token_hex(4))


def mailq_read(store, qid):
    raw = store.get_meta(MAILQ_PREFIX + qid)
    if not raw:
        return None, None
    try:
        return json.loads(raw), raw
    except ValueError:
        return None, None


def mailq_cas(store, qid, raw, rec):
    """Written only over what was read: of two writers, one wins."""
    return bool(store.db.run('UPDATE meta SET v = ? WHERE k = ? AND v = ?',
                             (json.dumps(rec), MAILQ_PREFIX + qid, raw)))


def mailq_body(store, qid):
    sealed = store.get_meta(MAILB_PREFIX + qid)
    if not sealed:
        return None
    raw = unseal_secret(sealed, 'mailq:' + qid)
    if not raw:
        return None
    try:
        import email
        import email.policy
        return email.message_from_bytes(base64.b64decode(raw), policy=email.policy.default)
    except Exception:                                   # noqa: BLE001
        return None


def mailq_body_drop(store, qid):
    store.db.run('DELETE FROM meta WHERE k = ?', (MAILB_PREFIX + qid,))


def mailq_delay(rec):
    n = int(rec.get('tries') or 1)
    row = MAILQ_CODE_DELAYS if rec.get('kind') in ('code', 'verify') else MAILQ_DELAYS
    last = 60 if row is MAILQ_CODE_DELAYS else 3600
    return row[n - 1] if 0 < n <= len(row) else last


def mailq_subject_kept(subject, kind):
    """The subject as the outgoing-mail list shows it: a code's mail has the
    code in its subject - kept as dots there. The mail itself, sealed, still
    has it."""
    said = str(subject or '')[:300]
    if kind in ('code', 'verify'):
        said = re.sub(r'\d{4,10}', '••••••', said)
    return said


def mail_deliver(store, msg, to, kind='other', name='', by='', purpose='', expires=None):
    """A mail sent now, and kept for another try when it was not taken.
    Returns the steps; raises MailError (with .queued = the state it is left
    in: waiting, failed) when it did not go now."""
    if (CONFIG.get('mail_mode') or 'off') == 'off':
        raise MailError('sending mail is switched off - Settings → Mail', [])
    to = [str(x) for x in (to or [])]
    qid = mailq_new_id()
    now = time.time()
    rec = {'qid': qid, 'created': now, 'node': node_name(), 'kind': kind,
           'purpose': str(purpose or ''), 'name': str(name or ''), 'by': str(by or ''),
           'to': to, 'subject': mailq_subject_kept(msg.get('Subject'), kind),
           'size': 0, 'state': 'sending', 'tries': 0, 'last_try': now, 'next_at': 0,
           'expires': float(expires) if expires else
           now + 3600 * int(CONFIG.get('mail_retry_hours') or 24),
           'history': [], 'said': '', 'steps': []}
    data = msg.as_bytes()
    rec['size'] = len(data)
    store.set_meta(MAILB_PREFIX + qid, seal_secret(base64.b64encode(data).decode('ascii'),
                                                   'mailq:' + qid))
    store.set_meta(MAILQ_PREFIX + qid, json.dumps(rec))
    return mailq_attempt(store, qid, msg=msg, raise_err=True, claimed=True)


def mailq_attempt(store, qid, msg=None, raise_err=False, claimed=False):
    rec, raw = mailq_read(store, qid)
    if not rec:
        return None
    now = time.time()
    if not claimed:
        if rec.get('state') not in ('waiting',):
            return None
        rec.update(state='sending', last_try=now, node=node_name())
        if not mailq_cas(store, qid, raw, rec):
            return None                 # taken by another meanwhile
        raw = json.dumps(rec)
    if msg is None:
        msg = mailq_body(store, qid)
    if msg is None:
        rec.update(state='expired', said='what the mail held is gone - it cannot be sent')
        store.set_meta(MAILQ_PREFIX + qid, json.dumps(rec))
        return None
    err = None
    try:
        steps = mail_send(store, msg, rec.get('to') or [])
    except MailError as e:
        err, steps = e, e.steps
    except Exception as e:                              # noqa: BLE001
        err, steps = MailError(str(e) or e.__class__.__name__, []), []
    rec['tries'] = int(rec.get('tries') or 0) + 1
    rec['last_try'] = now
    rec['steps'] = steps[-12:]
    rec['history'] = (rec.get('history') or [])[-19:] + [{
        'at': now, 'node': node_name(), 'ok': err is None,
        'said': (str(err) if err else (([s for s in steps if s.get('ok')] or [{}])[-1]
                                       .get('said') or 'sent'))[:400]}]
    who = ', '.join(rec.get('to') or [])
    if err is None:
        rec.update(state='sent', sent_at=now, said=rec['history'][-1]['said'], next_at=0)
        store.set_meta(MAILQ_PREFIX + qid, json.dumps(rec))
        mailq_body_drop(store, qid)
        if rec['tries'] > 1:
            store.add_event('mail', 'the mail to %s (%s) went on try %d' % (
                who, MAILQ_KIND_WORDS.get(rec.get('kind'), 'a mail'), rec['tries']))
        return steps
    rec['said'] = str(err)[:400]
    if err.permanent:
        rec['state'] = 'failed'
        store.add_event('mail', 'the mail to %s (%s) was refused for good: %s' % (
            who, MAILQ_KIND_WORDS.get(rec.get('kind'), 'a mail'), str(err)[:300]), 'error')
    elif now >= float(rec.get('expires') or 0):
        rec['state'] = 'expired'
        store.add_event('mail', 'the mail to %s (%s) was given up after %d tries: %s' % (
            who, MAILQ_KIND_WORDS.get(rec.get('kind'), 'a mail'), rec['tries'],
            str(err)[:300]), 'error')
    else:
        rec['state'] = 'waiting'
        rec['next_at'] = min(now + mailq_delay(rec), float(rec.get('expires') or now))
        if rec['tries'] == 1:
            store.add_event('mail', 'the mail to %s (%s) did not go yet - tried again from '
                            'the outgoing mail: %s' % (
                                who, MAILQ_KIND_WORDS.get(rec.get('kind'), 'a mail'),
                                str(err)[:300]), 'warn')
    store.set_meta(MAILQ_PREFIX + qid, json.dumps(rec))
    if rec['state'] in ('expired',):
        mailq_body_drop(store, qid)
    err.queued = rec['state']
    err.next_at = rec.get('next_at')
    err.qid = qid
    if raise_err:
        raise err
    return None


def mailq_all(store, open_only=False):
    """Every mail remembered - or, `open_only`, those still to do something
    with."""
    out = []
    sql = "SELECT k, v FROM meta WHERE k LIKE 'mailq:%'"
    if open_only:
        sql += (" AND (v LIKE '%\"state\": \"waiting\"%' OR v LIKE '%\"state\": \"sending\"%'"
                " OR v LIKE '%\"state\": \"failed\"%')")
    for r in store.db.rows(sql):
        try:
            rec = json.loads(r['v'] or '{}')
        except ValueError:
            continue
        rec['qid'] = r['k'][len(MAILQ_PREFIX):]
        out.append(rec)
    out.sort(key=lambda x: -float(x.get('created') or 0))
    return out


MAILQ_FULL_AT = [0.0]


def mailq_tick(store):
    """What the outgoing mail does every few seconds."""
    if not MAILQ_LOCK.acquire(False):
        return
    try:
        now = time.time()
        keep_s = 86400 * int(CONFIG.get('mail_keep_days') or 14)
        sent_now = 0
        paused = (CONFIG.get('mail_mode') or 'off') == 'off'
        # All of them - to forget the old ones - every ten minutes; the open
        # ones every time.
        full = now - MAILQ_FULL_AT[0] > 600
        if full:
            MAILQ_FULL_AT[0] = now
        for rec in mailq_all(store, open_only=not full):
            qid = rec['qid']
            state = rec.get('state')
            if state in ('sent', 'failed', 'expired') and \
                    now - float(rec.get('sent_at') or rec.get('last_try') or
                                rec.get('created') or 0) > keep_s:
                store.db.run('DELETE FROM meta WHERE k IN (?, ?)',
                             (MAILQ_PREFIX + qid, MAILB_PREFIX + qid))
                continue
            if state == 'failed' and now > float(rec.get('expires') or 0):
                # Refused for good stays "refused for good", not "given up":
                # what it held goes, the reason stays.
                if store.get_meta(MAILB_PREFIX + qid):
                    mailq_body_drop(store, qid)
                continue
            if paused and rec.get('kind') not in ('code', 'verify'):
                continue        # kept as it is until mail is switched on again
            if state in ('waiting', 'sending') and \
                    now > float(rec.get('expires') or 0) + (0 if state != 'sending' else 600):
                _, raw = mailq_read(store, qid)
                if raw:
                    rec.pop('qid', None)
                    rec.update(state='expired', next_at=0, said=rec.get('said') or 'not sent in time')
                    if mailq_cas(store, qid, raw, rec):
                        mailq_body_drop(store, qid)
                continue
            if paused:
                # Mail switched off: nothing tried while it is - and nothing
                # but a code past its time given up for it either.
                continue
            if state == 'sending' and now - float(rec.get('last_try') or 0) > 600:
                # Left half way by a daemon that stopped: tried again.
                _, raw = mailq_read(store, qid)
                if raw:
                    rec.pop('qid', None)
                    rec.update(state='waiting', next_at=now, node=node_name())
                    mailq_cas(store, qid, raw, rec)
                continue
            if state != 'waiting':
                continue
            if float(rec.get('next_at') or 0) > now or sent_now >= 25:
                continue
            sent_now += 1
            try:
                mailq_attempt(store, qid)
            except Exception as e:                      # noqa: BLE001
                log('the outgoing mail %s: %s' % (qid, e), 'warn')
    finally:
        MAILQ_LOCK.release()


def mailq_counts(store):
    c = collections.Counter()
    for r in store.db.rows("SELECT v FROM meta WHERE k LIKE 'mailq:%'"):
        m = re.search(r'"state": "([a-z]+)"', r['v'] or '')
        if m:
            c[m.group(1)] += 1
    return {k: int(c.get(k, 0)) for k in MAILQ_STATES}


def mailq_view(rec):
    """A row as the pages see it: no body, never."""
    out = {k: rec.get(k) for k in ('qid', 'created', 'node', 'kind', 'purpose', 'name', 'by',
                                    'to', 'subject', 'size', 'state', 'tries', 'last_try',
                                    'next_at', 'expires', 'sent_at', 'said')}
    out['kind_words'] = MAILQ_KIND_WORDS.get(rec.get('kind'), 'a mail')
    out['subject'] = mailq_subject_kept(out.get('subject'), rec.get('kind'))
    return out


MAILQ_RETRY_WHY = {}


def mailq_retry(store, qids, by=''):
    """Tried again now."""
    done, skipped = [], []
    MAILQ_RETRY_WHY.clear()
    for qid in qids:
        rec, raw = mailq_read(store, qid)
        if not rec or rec.get('state') not in ('waiting', 'failed'):
            skipped.append(qid)
            continue
        if not store.get_meta(MAILB_PREFIX + qid):
            skipped.append(qid)
            continue
        if time.time() > float(rec.get('expires') or 0):
            # Asked by hand: given the time of a new mail again - a code to
            # sign in with is not, it is no good any more.
            if rec.get('kind') in ('code', 'verify'):
                skipped.append(qid)
                MAILQ_RETRY_WHY['code'] = MAILQ_RETRY_WHY.get('code', 0) + 1
                continue
            rec['expires'] = time.time() + 3600 * int(CONFIG.get('mail_retry_hours') or 24)
        rec.update(state='waiting', next_at=0, node=node_name())
        if mailq_cas(store, qid, raw, rec):
            done.append(qid)
        else:
            skipped.append(qid)
    if done:
        store.add_event('mail', '%s asked for %d mail(s) of the outgoing mail to be sent again '
                        'now' % (by or 'somebody', len(done)), who=by or None)
        threading.Thread(target=lambda: [mailq_attempt(store, q) for q in done],
                         name='mail-again', daemon=True).start()
    return done, skipped


def mailq_drop(store, qids, by=''):
    n = 0
    for qid in qids:
        n += int(store.db.run('DELETE FROM meta WHERE k = ?', (MAILQ_PREFIX + qid,)) or 0)
        store.db.run('DELETE FROM meta WHERE k = ?', (MAILB_PREFIX + qid,))
    if n:
        store.add_event('mail', '%s took %d mail(s) out of the outgoing mail' % (
            by or 'somebody', n), 'warn', who=by or None)
    return n


def mailq_search_row(r):
    return {'to': ' '.join(r.get('to') or []), 'state': r.get('state') or '',
            'kind': r.get('kind') or '', 'name': r.get('name') or '', 'by': r.get('by') or '',
            'said': r.get('said') or '', 'subject': mailq_subject_kept(r.get('subject'), r.get('kind')),
            'tries': int(r.get('tries') or 0)}


MAILQ_FIELDS = [('to', 'whom it goes to', 'to:*@example.cz'),
                ('state', 'waiting, sending, sent, failed or expired', 'state:waiting'),
                ('kind', 'code, verify, test or notice', 'kind:code'),
                ('name', 'the account it is about', 'name:novak*'),
                ('said', 'what the receiving server said', 'said~greylist'),
                ('tries', 'how many times it was tried', 'tries:>2'),
                ('by', 'who had it sent', 'by:admin'),
                ('subject', 'its subject', 'subject~code')]


def mailq_match(row, q):
    """The search words of otp's lists, as far as the outgoing mail needs them:
    words found anywhere, field:value (with * for anything), field~words
    (contained), field:>n / field:<n, and - or ! before one for NOT."""
    try:
        parts = shlex.split(q)
    except ValueError:
        raise ValueError('a " that is not closed')
    whole = ' '.join(str(v) for v in row.values()).lower()
    for p in parts:
        neg = p[:1] in ('-', '!') and len(p) > 1
        if neg:
            p = p[1:]
        m = re.match(r'^([a-z_]+)(:|~|=)(.*)\Z', p, re.I | re.S)
        if m and m.group(1).lower() in row:
            k, op, want = m.group(1).lower(), m.group(2), m.group(3).lower()
            have = str(row[k]).lower()
            if k == 'tries' and re.match(r'^[<>]=?\d+\Z', want):
                n, lim = int(row[k]), int(want.lstrip('<>='))
                ok = {'>': n > lim, '<': n < lim, '>=': n >= lim, '<=': n <= lim}[re.match(r'^[<>]=?', want).group(0)]
            elif op == '~':
                ok = want in have
            else:
                vals = have.split() if k == 'to' else [have]
                ok = any(fnmatch.fnmatchcase(v, want if '*' in want else want) for v in vals)
        elif m:
            raise ValueError('%s: the outgoing mail has no such field - it has %s'
                             % (m.group(1), ', '.join(f[0] for f in MAILQ_FIELDS)))
        else:
            ok = p.lower().strip('*') in whole
        if ok == neg:
            return False
    return True


# ---------------------------------------------------------------------------
# The texts of the messages, edited on the pages (otp's, 1.0.103)
# ---------------------------------------------------------------------------
# Every word a person gets from this server - the mails and the SMS of a code
# - in both languages, as it is written here in CODE_TEXTS, unless changed in
# Settings → Message texts. What is changed is kept in the database (meta
# texts:<message>:<lang>, the fields changed only). Put back to the default,
# a text is exactly as it was before it was changed.
import html.parser as _html_parser

TEXT_MESSAGES = [
    {'id': 'code_mail', 'kind': 'mail', 'group': 'code', 'purpose': 'signin',
     'title': 'The sign-in code by mail',
     'says': 'Sent when somebody signs in to these pages with the second step by mail.',
     'fields': [
         ('mail_subject', 'line', 'Subject', ('code', 'minutes', 'site'), 'subject'),
         ('h_title', 'line', 'The band at the top', ('site',), 'layout'),
         ('h_hello', 'rich', 'Greeting', ('name',), 'layout'),
         ('h_lede', 'rich', 'What it is', ('account',), 'layout'),
         ('h_facts', 'rich', 'Under the code', ('minutes',), 'layout'),
         ('h_warn', 'rich', 'The warning', (), 'layout'),
         ('h_foot', 'rich', 'The foot', ('site',), 'layout'),
         ('h_hello_anon', 'rich', 'Greeting when the name is not known', (), 'other'),
         ('h_lede_anon', 'rich', 'What it is when the account is not known', (), 'other'),
         ('mail_body', 'text', 'The plain text version', ('code', 'minutes', 'site'), 'plain'),
     ]},
    {'id': 'verify_mail', 'kind': 'mail', 'group': 'code', 'purpose': 'verify',
     'title': 'Checking an address',
     'says': 'Sent when somebody sets up the second step by mail, to check the address.',
     'fields': [
         ('verify_subject', 'line', 'Subject', ('code', 'minutes', 'site'), 'subject'),
         ('h_v_title', 'line', 'The band at the top', ('site',), 'layout'),
         ('h_v_hello', 'rich', 'Greeting', ('name',), 'layout'),
         ('h_v_lede', 'rich', 'What it is', ('account',), 'layout'),
         ('h_v_facts', 'rich', 'Under the code', ('minutes',), 'layout'),
         ('h_v_note', 'rich', 'The note', (), 'layout'),
         ('h_v_foot', 'rich', 'The foot', ('site',), 'layout'),
         ('h_v_hello_anon', 'rich', 'Greeting when the name is not known', (), 'other'),
         ('h_v_lede_anon', 'rich', 'What it is when the account is not known', (), 'other'),
         ('verify_body', 'text', 'The plain text version', ('code', 'minutes', 'site'), 'plain'),
     ]},
    {'id': 'sms_code', 'kind': 'sms', 'group': 'code', 'title': 'The sign-in code by SMS',
     'says': 'Sent when somebody signs in to these pages with the second step by SMS.',
     'fields': [('sms', 'text', 'The SMS', ('code', 'minutes', 'site'), 'sms')]},
    {'id': 'sms_verify', 'kind': 'sms', 'group': 'code', 'title': 'Checking a number',
     'says': 'Sent when somebody sets up the second step by SMS, to check the number.',
     'fields': [('sms_verify', 'text', 'The SMS', ('code', 'minutes', 'site'), 'sms')]},
]
TEXT_LANGS = ('cs', 'en')
TEXT_PLACEHOLDERS = {
    'code': 'the code', 'minutes': 'minutes it is good for', 'site': 'the server’s name',
    'name': 'the person’s name', 'account': 'the account', 'dest': 'where it was sent'}
TEXT_FIELD_MOST = {'line': 300, 'rich': 3000, 'text': 4000}
TEXT_CACHE = {}
TEXT_CACHE_S = 5.0
TEXT_LOCK = threading.Lock()


def text_message(mid):
    return next((m for m in TEXT_MESSAGES if m['id'] == mid), None)


def text_defaults(group, lang):
    return dict(CODE_TEXTS.get(lang) or CODE_TEXTS['cs'])


def text_saved(store, mid, lang):
    """What is saved for one message in one language: {'f': {...}, 'at', 'by'}."""
    try:
        got = json.loads(store.get_meta('texts:%s:%s' % (mid, lang)) or 'null')
    except ValueError:
        got = None
    if not isinstance(got, dict) or not isinstance(got.get('f'), dict):
        return {'f': {}, 'at': None, 'by': None}
    return got


def texts_for(group, lang):
    """The words of one group in one language - the defaults with what was
    changed on the pages over them. Read again every few seconds; if the
    database cannot be asked, the defaults, never nothing."""
    lang = lang if lang in TEXT_LANGS else 'cs'
    key = (group, lang)
    now = time.time()
    with TEXT_LOCK:
        got = TEXT_CACHE.get(key)
        if got and now - got[0] < TEXT_CACHE_S:
            return dict(got[1])
    words = text_defaults(group, lang)
    store = STORE_NOW.get('store')
    if store is not None:
        try:
            for m in TEXT_MESSAGES:
                if m['group'] != group:
                    continue
                keys = {f[0] for f in m['fields']}
                for k, v in text_saved(store, m['id'], lang)['f'].items():
                    if k in keys and isinstance(v, str):
                        words[k] = v
        except Exception as e:                          # noqa: BLE001
            log_sparing('texts', 'the message texts could not be read - the defaults are used: '
                        '%s' % str(e).split('\n')[0][:200], 'warn')
            return text_defaults(group, lang)
    with TEXT_LOCK:
        TEXT_CACHE[key] = (now, words)
    return dict(words)


def texts_forget():
    with TEXT_LOCK:
        TEXT_CACHE.clear()


# ---- what may be written ---------------------------------------------------------
class _RichClean(_html_parser.HTMLParser):
    """HTML of a text in a mail, kept to what mail programs show alike: bold,
    italic, underline, a colour, a link, a line break. Everything else goes,
    its text stays."""
    COLOR = re.compile(r'\s*(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,'
                       r'\s*\d{1,3}\s*\))\s*\Z')

    def __init__(self):
        _html_parser.HTMLParser.__init__(self, convert_charrefs=True)
        self.out = []
        self.stack = []

    @staticmethod
    def _style(attrs):
        st = {}
        for part in str(dict(attrs).get('style') or '').split(';'):
            k, _, v = part.partition(':')
            if k.strip():
                st[k.strip().lower()] = v.strip().lower()
        return st

    def _open_styled(self, st, color=None):
        opened = []
        c = color or st.get('color')
        if c and self.COLOR.match(c):
            self.out.append('<span style="color:%s">' % c.strip())
            opened.append('span')
        if st.get('font-weight') in ('bold', 'bolder', '600', '700', '800', '900'):
            self.out.append('<b>')
            opened.append('b')
        if st.get('font-style') == 'italic':
            self.out.append('<i>')
            opened.append('i')
        if 'underline' in (st.get('text-decoration') or '') + (st.get('text-decoration-line') or ''):
            self.out.append('<u>')
            opened.append('u')
        return opened

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'br':
            self.out.append('<br>')
            return
        if tag in ('b', 'strong'):
            self.out.append('<b>')
            self.stack.append((tag, ['b']))
        elif tag in ('i', 'em'):
            self.out.append('<i>')
            self.stack.append((tag, ['i']))
        elif tag == 'u':
            self.out.append('<u>')
            self.stack.append((tag, ['u']))
        elif tag == 'a':
            href = str(dict(attrs).get('href') or '').strip()
            if re.match(r'(https?://|mailto:)[^\s"<>]+\Z', href, re.I):
                self.out.append('<a href="%s" style="color:#1d4ed8">' % html.escape(href, quote=True))
                self.stack.append((tag, ['a']))
            else:
                self.stack.append((tag, []))
        elif tag in ('span', 'font'):
            st = self._style(attrs)
            self.stack.append((tag, self._open_styled(
                st, dict(attrs).get('color') if tag == 'font' else None)))
        elif tag in ('div', 'p'):
            # A new paragraph typed in the editor is a line break here.
            if self.out and not self.out[-1].endswith('<br>'):
                self.out.append('<br>')
            self.stack.append((tag, []))
        else:
            self.stack.append((tag, []))

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                while len(self.stack) > i:
                    _t, opened = self.stack.pop()
                    for o in reversed(opened):
                        self.out.append('</%s>' % o)
                return

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == 'br':
            self.out.append('<br>')

    def handle_data(self, data):
        if any(t in ('script', 'style', 'title', 'head') for t, _o in self.stack):
            return
        self.out.append(html.escape(data, quote=False))

    def result(self):
        while self.stack:
            _t, opened = self.stack.pop()
            for o in reversed(opened):
                self.out.append('</%s>' % o)
        text = ''.join(self.out)
        text = re.sub(r'(<br>)+\Z', '', text)
        return re.sub(r'\A(<br>)+', '', text).strip()


def text_rich_clean(value):
    p = _RichClean()
    p.feed(str(value or ''))
    p.close()
    return p.result()


def text_samples(lang='cs'):
    return {'code': '482913', 'minutes': max(1, int(CONFIG.get('code_ttl_s') or 300) // 60),
            'site': site_words(), 'name': 'Jan Novák' if lang == 'cs' else 'Jan Novak',
            'account': 'jan.novak', 'dest': 'j•••@example.cz'}


def text_check(field, value):
    """A field's new text, cleaned, or ValueError saying what is wrong."""
    import string
    key, kind, label, allowed, _where = field
    if value is not None and not isinstance(value, str):
        raise ValueError('%s: a piece of text' % label)
    value = str(value if value is not None else '')
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    if kind != 'text':
        value = value.replace('\n', ' ')
    value = ''.join(c for c in value if c in '\n\t' or ord(c) >= 32)
    if kind == 'rich':
        value = text_rich_clean(value)
    else:
        value = value.strip() if kind == 'line' else value.strip('\n ')
    if len(value) > TEXT_FIELD_MOST[kind]:
        raise ValueError('%s: at most %d characters' % (label, TEXT_FIELD_MOST[kind]))
    try:
        parts = list(string.Formatter().parse(value))
    except ValueError:
        raise ValueError('%s: a { or } on its own - write it twice, {{ or }}' % label)
    for _lit, name, spec, conv in parts:
        if name is None:
            continue
        if name in allowed and (spec or conv):
            raise ValueError('%s: write {%s} with nothing after its name' % (label, name))
        if name not in allowed:
            raise ValueError('%s: {%s} is not something this text can have - it can have %s'
                             % (label, name, ', '.join('{%s}' % a for a in allowed) or 'none'))
    try:
        value.format(**text_samples())
    except (ValueError, IndexError, KeyError) as e:
        raise ValueError('%s: a { or } on its own - write it twice, {{ or }} (%s)' % (label, e))
    if field[4] in ('subject', 'sms') and not value.strip():
        raise ValueError('%s cannot be empty' % label)
    if field[4] in ('sms', 'plain') and 'code' in allowed and '{code}' not in value:
        raise ValueError('%s: the text has to say {code} - the code itself is put there' % label)
    return value


# ---- what the editor shows -------------------------------------------------------
TEXT_MARK = '⟦f:%s⟧'


def text_words(mid, lang, fields=None, mark=False):
    """The words of a message's group with those of the editor (`fields`,
    not yet saved) over the saved ones; `mark`: each field of this message
    as a mark the editor puts its box in."""
    m = text_message(mid)
    w = texts_for(m['group'], lang)
    for k, v in (fields or {}).items():
        if any(f[0] == k for f in m['fields']):
            w[k] = v
    if mark:
        for f in m['fields']:
            w[f[0]] = TEXT_MARK % f[0]
    return w


def text_render(store, mid, lang, fields=None, mark=False):
    """A message as it would go out, with sample values: the mail's HTML,
    its subject and its text; the SMS."""
    m = text_message(mid)
    w = text_words(mid, lang, fields, mark)
    smp = text_samples(lang)
    out = {'id': mid, 'lang': lang}
    if m['kind'] == 'mail':
        out['html'] = code_mail_html(smp['code'], m['purpose'], lang, smp['account'], smp['name'],
                                     w=w)
        sub = w[code_purpose(m['purpose'])['subject']]
        body = w[code_purpose(m['purpose'])['body']]
        out['subject'] = sub.format(**smp)
        out['text'] = body.format(**smp)
    else:
        text = w[m['fields'][0][0]].format(**smp)
        out['sms'] = sms_plain(text) if CONFIG.get('sms_plain', True) else text
        out['sms_written'] = text
    return out


def text_state(store, mid=None):
    """Every message, its fields, their defaults and what is saved now."""
    out = []
    for m in TEXT_MESSAGES:
        if mid and m['id'] != mid:
            continue
        one = {'id': m['id'], 'kind': m['kind'], 'title': m['title'], 'says': m['says'],
               'short': m.get('short') or m['title'],
               'fields': [], 'saved': {}}
        for lang in TEXT_LANGS:
            sv = text_saved(store, m['id'], lang)
            one['saved'][lang] = {'at': sv.get('at'), 'by': sv.get('by'),
                                  'changed': sorted(k for k in sv['f']
                                                    if any(f[0] == k for f in m['fields']))}
        for key, kind, label, allowed, where in m['fields']:
            f = {'key': key, 'kind': kind, 'label': label, 'where': where,
                 'placeholders': list(allowed), 'default': {}, 'value': {}}
            for lang in TEXT_LANGS:
                d = text_defaults(m['group'], lang).get(key, '')
                f['default'][lang] = d
                f['value'][lang] = text_saved(store, m['id'], lang)['f'].get(key, d)
            one['fields'].append(f)
        out.append(one)
    return out


class TextConflict(ValueError):
    pass


def text_save(store, mid, lang, fields, by, was_at=None):
    """The fields of a message in one language saved; those equal to their
    default are not kept (so a default changed in a later version reaches
    them). Refused if somebody else saved it meanwhile (`was_at`)."""
    m = text_message(mid)
    if not m or lang not in TEXT_LANGS:
        raise ValueError('no such message or language')
    k = 'texts:%s:%s' % (mid, lang)
    raw = store.get_meta(k)
    now = text_saved(store, mid, lang)
    if was_at is not None and (now.get('at') or 0) != (was_at or 0):
        raise TextConflict('%s changed these words meanwhile (%s) - load them again'
                           % (now.get('by') or 'somebody',
                              datetime.fromtimestamp(float(now.get('at') or 0)).strftime('%d-%m-%Y %H:%M')))
    defaults = text_defaults(m['group'], lang)
    keep = dict(now['f'])
    for f in m['fields']:
        if f[0] not in fields:
            continue
        v = text_check(f, fields[f[0]])
        if v == defaults.get(f[0]):
            keep.pop(f[0], None)
        else:
            keep[f[0]] = v
    new = {'f': keep, 'at': time.time(), 'by': by}
    if raw is None:
        store.set_meta(k, json.dumps(new))
    elif not store.db.run('UPDATE meta SET v = ? WHERE k = ? AND v = ?', (json.dumps(new), k, raw)):
        raise TextConflict('somebody saved these words at the same moment - load them again')
    texts_forget()
    return new


def text_reset(store, mid, lang, keys=None):
    """A message in one language - or only `keys` of it - back to its default."""
    m = text_message(mid)
    if not m or lang not in TEXT_LANGS:
        raise ValueError('no such message or language')
    k = 'texts:%s:%s' % (mid, lang)
    if not keys:
        store.db.run('DELETE FROM meta WHERE k = ?', (k,))
    else:
        for _round in range(8):
            raw = store.get_meta(k)
            if raw is None:
                break
            now = text_saved(store, mid, lang)
            for key in keys:
                now['f'].pop(key, None)
            if store.db.run('UPDATE meta SET v = ? WHERE k = ? AND v = ?',
                            (json.dumps(dict(now, at=time.time())), k, raw)):
                break
    texts_forget()


def texts_from_before(store):
    """The texts ai 1.0.5 kept (meta 'texts': {lang: {key: text}}) carried
    over once into otp's shape, where a field of the same meaning exists."""
    old = store.meta_json('texts', None)
    if not isinstance(old, dict):
        return
    where = {'code_subject': ('code_mail', 'mail_subject'), 'code_body': ('code_mail', 'mail_body'),
             'verify_subject': ('verify_mail', 'verify_subject'), 'verify_body': ('verify_mail', 'verify_body'),
             'sms_code': ('sms_code', 'sms'), 'sms_verify': ('sms_verify', 'sms_verify')}
    for lang, got in old.items():
        if lang not in TEXT_LANGS or not isinstance(got, dict):
            continue
        for key, text in got.items():
            if key not in where or not isinstance(text, str) or not text.strip():
                continue
            mid, field = where[key]
            try:
                text_save(store, mid, lang, {field: text.replace('{code}', '{code}')}, 'ai 1.0.5')
            except ValueError:
                pass
    store.x('DELETE FROM meta WHERE k = ?', ('texts',))


def code_send(store, kind, to, code, purpose='signin', name='', lang=None, fmt=None, display=''):
    """A code sent now, with the code taken out of whatever the server said
    (an SMS gateway that echoes the message would put a live code into the
    events and the log). A mail goes through the outgoing mail: greylisted,
    it is tried again while the code is good."""
    def hide(t):
        return str(t).replace(str(code), '******') if code else str(t)
    lang = lang if lang in CODE_TEXTS else code_lang()
    try:
        if kind == 'mail':
            msg = code_message('mail', to, code, purpose, lang=lang, name=name, display=display, fmt=fmt)
            try:
                steps = mail_deliver(store, msg, [to], kind=code_purpose(purpose)['queue'],
                                     name=name, purpose=purpose,
                                     expires=time.time() + int(CONFIG.get('code_ttl_s') or 300))
            except MailError as e:
                if e.queued == 'waiting':
                    return hide('not taken yet (%s) - it waits in the outgoing mail and is tried again' % e)
                raise
            last = [s for s in steps if s.get('ok')]
            return hide((last[-1].get('said') or 'sent') if last else 'sent')
        if kind == 'sms':
            return hide(send_sms(store, to, code_message('sms', to, code, purpose, lang=lang),
                                 MAILQ_KIND_WORDS[code_purpose(purpose)['queue']], name))
    except MailError as e:
        new = MailError(hide(e), steps=e.steps, permanent=e.permanent)
        for a, v in vars(e).items():
            if a not in ('steps', 'permanent'):
                setattr(new, a, v)
        raise new
    except SmsError as e:
        raise SmsError(hide(e))
    raise ValueError('codes go by mail or SMS only')



def mfa_lang(c):
    got = str(c.body.get('lang') or c.arg('lang') or '')
    return got if got in CODE_TEXTS else None


def _mfa_code_ok(saved, code):
    if not saved or time.time() > float(saved.get('exp') or 0):
        return False
    return hmac.compare_digest(code_hash(saved.get('salt') or '', str(code or '').strip()),
                               str(saved.get('hash') or ''))


def _mfa_send(c, kind, dest, field):
    data = c.who.get('_data') or {}
    sid = c.who['_sid']
    t = time.time()
    if t - float(data.get('mfa_sent_at') or 0) < MFA_SEND_GAP_S:
        raise Refused('a code went a moment ago - wait half a minute for another', 429)
    n = int(data.get('mfa_sent') or 0)
    if n >= MFA_SEND_MOST:
        raise Refused('that is %d codes for this sign-in: sign in again for more' % MFA_SEND_MOST, 429)
    code, salt = code_new(), secrets.token_hex(8)
    saved = {'hash': code_hash(salt, code), 'salt': salt, 't': t,
             'exp': t + int(CONFIG.get('code_ttl_s') or 300)}
    try:
        said = code_send(c.daemon.store, kind, dest, code, 'verify' if field == 'mfa_new' else 'signin',
                         name=c.name, lang=mfa_lang(c))
    except (MailError, SmsError, ValueError, OSError) as e:
        c.daemon.store.add_event('sign-in', 'the code of the second step for %s could not be sent (%s): %s' % (
            c.name, kind, e), 'warn', who=c.name)
        raise Refused('the code could not be sent: %s' % e, 502)
    new = dict(saved, kind=kind, dest=dest) if field == 'mfa_new' else saved
    c.daemon.store.session_merge(sid, {field: new, 'mfa_sent_at': t, 'mfa_sent': n + 1})
    log('the second step of %s: a code sent by %s to %s (%s)' % (c.name, kind, dest_masked(kind, dest), said))
    return dest_masked(kind, dest)


def _mfa_done(c, how):
    """The second step given: a sign-in of its own from here on - the one the
    password alone opened is ended, not made whole (otp 1.0.149)."""
    d = c.daemon
    data = {k: v for k, v in (c.who.get('_data') or {}).items()
            if k not in ('mfa', 'mfa_new', 'mfa_code', 'mfa_sent_at', 'mfa_sent')}
    token = d.auth.session_new(c.name, c.ip, c.who.get('_agent') or '', data, created=c.who.get('_created'))
    d.store.x('DELETE FROM sessions WHERE id=?', (c.who['_sid'],))
    d.store.add_event('sign-in', '%s gave the second step (%s) from %s' % (c.name, how, c.ip), who=c.name)
    return token


def _mfa_wrong(c):
    c.daemon.auth.failed(c.name, c.ip)
    wait = c.daemon.auth.locked(c.name, c.ip)
    if wait:
        c.daemon.store.add_event('sign-in', '%s is locked out after wrong codes of the second step, from %s' % (
            c.name, c.ip), 'warn', who=c.name)
        raise Refused('too many wrong codes - try again in %d min' % max(1, wait // 60 + 1), 429)


@route('GET', '/api/auth/mfa')
def api_mfa(c):
    stage = c.who.get('_mfa')
    rec = mfa_get(c.daemon.store, c.name) or {}
    new = (c.who.get('_data') or {}).get('mfa_new') or {}
    return {'name': c.name, 'display': '', 'stage': stage, 'methods': mfa_methods(),
            'kind': rec.get('kind') if stage == 'check' else '',
            'dest': dest_masked(rec.get('kind'), rec.get('dest')) if stage == 'check' else '',
            'started': {'kind': new.get('kind'), 'dest': dest_masked(new.get('kind'), new.get('dest'))}
            if new else None,
            'digits': 6 if (stage == 'check' and rec.get('kind') == 'app') else int(CONFIG.get('code_digits') or 6)}


@route('POST', '/api/auth/mfa')
def api_mfa_do(c):
    stage = c.who.get('_mfa')
    if not stage:
        raise Refused('this sign-in has no second step to give', 409)
    st = c.daemon.store
    name = c.name
    act = str(c.body.get('action') or '')
    data = c.who.get('_data') or {}
    wait = c.daemon.auth.locked(name, c.ip)
    if wait and act in ('enrol_confirm', 'check'):
        raise Refused('too many wrong codes - try again in %d min' % max(1, wait // 60 + 1), 429)
    if act in ('enrol_start', 'enrol_confirm') and (stage != 'enrol' or mfa_stage(st, name) != 'enrol'):
        raise Refused('this account has its second step set up already - sign in again', 409)
    if act == 'enrol_start':
        kind = str(c.body.get('kind') or '')
        if kind not in mfa_methods():
            raise Refused('that way is not offered here')
        if kind == 'app':
            secret = b32_new(20)
            st.session_merge(c.who['_sid'], {'mfa_new': {
                'kind': 'app', 'secret': seal_secret(secret, 'adm2fa-new:' + name.lower())}})
            uri = otpauth_uri(secret, name, '%s (ai)' % site_words())
            return {'kind': 'app', 'qr': qr_data_uri(uri), 'uri': uri,
                    'secret': ' '.join(secret[i:i + 4] for i in range(0, len(secret), 4))}
        try:
            dest = mail_checked(c.body.get('dest')) if kind == 'mail' else phone_checked(c.body.get('dest'))
        except ValueError as e:
            raise Refused(str(e))
        return {'kind': kind, 'sent_to': _mfa_send(c, kind, dest, 'mfa_new')}
    if act == 'enrol_confirm':
        new = data.get('mfa_new') or {}
        if not new.get('kind'):
            raise Refused('choose a way first')
        code = re.sub(r'\s', '', str(c.body.get('code') or ''))
        rec = {'kind': new['kind'], 'at': time.time(), 'by': name}
        if new['kind'] == 'app':
            secret = unseal_secret(new.get('secret'), 'adm2fa-new:' + name.lower())
            step = totp_match(secret, code, digits=6, window=int(CONFIG.get('totp_window') or 1)) \
                if secret else None
            if step is None:
                _mfa_wrong(c)
                raise Refused('that code is not right - the one the app shows now')
            rec.update(secret=seal_secret(secret, mfa_key(name)), step=step)
        else:
            if not _mfa_code_ok(new, code):
                _mfa_wrong(c)
                raise Refused('that code is not right, or no longer good - send another')
            rec['dest'] = new['dest']
        with MFA_LOCK:
            if mfa_stage(st, name) != 'enrol':
                raise Refused('this account has its second step set up already - sign in again', 409)
            st.set_meta_json(mfa_key(name), rec)
        token = _mfa_done(c, 'set up now: %s' % MFA_KIND_WORDS.get(rec['kind']))
        st.add_event('accounts', '%s set up the second step of signing in: %s%s' % (
            name, MFA_KIND_WORDS.get(rec['kind']),
            ' (%s)' % dest_masked(rec['kind'], rec.get('dest')) if rec.get('dest') else ''), who=name)
        return {'message': 'the second step is set up', 'done': True, 'token': token}
    if act == 'send':
        if stage != 'check':
            raise Refused('set the second step up first', 409)
        rec = mfa_get(st, name) or {}
        if rec.get('kind') not in ('mail', 'sms'):
            raise Refused('the code comes from the app - nothing is sent')
        if rec['kind'] not in code_channels():
            raise Refused('codes by %s cannot be sent from here now: another administrator resets your '
                          'second step (Accounts), or root with  ai --reset-2fa %s' % (
                              'mail' if rec['kind'] == 'mail' else 'SMS', name), 503)
        return {'sent_to': _mfa_send(c, rec['kind'], rec.get('dest'), 'mfa_code')}
    if act == 'check':
        if stage != 'check':
            raise Refused('set the second step up first', 409)
        code = re.sub(r'\s', '', str(c.body.get('code') or ''))
        rec = mfa_get(st, name) or {}
        if rec.get('kind') == 'app':
            with MFA_LOCK:
                rec = mfa_get(st, name) or {}
                secret = unseal_secret(rec.get('secret'), mfa_key(name))
                step = totp_match(secret, code, digits=6, window=int(CONFIG.get('totp_window') or 1)) \
                    if secret else None
                # A code is good once.
                if step is None or step <= int(rec.get('step') or 0):
                    _mfa_wrong(c)
                    raise Refused('that code is not right' if step is None else
                                  'that code was used already - wait for the next one')
                rec['step'] = step
                st.set_meta_json(mfa_key(name), rec)
        else:
            if not _mfa_code_ok(data.get('mfa_code'), code) or not st.session_take(c.who['_sid'], 'mfa_code'):
                _mfa_wrong(c)
                raise Refused('that code is not right, or no longer good - send another')
        for k in c.daemon.auth._fail_keys(name, c.ip):
            st.x('DELETE FROM fails WHERE k=?', (k,))
        token = _mfa_done(c, MFA_KIND_WORDS.get(rec.get('kind')))
        return {'message': 'signed in', 'done': True, 'token': token}
    raise Refused('no such thing to do')


# ---- who is locked out (otp's, 1.0.112) -------------------------------------------------------
def lockouts_view(store):
    now = time.time()
    pause = int(CONFIG.get('login_lock_min') or 15) * 60
    limit = int(CONFIG.get('login_max_fails') or 8)
    rows = []
    for r in store.q('SELECT * FROM fails ORDER BY first DESC'):
        by, _s, who = str(r['k']).partition(':')
        locked = bool(r['until_ts'] and r['until_ts'] > now)
        forgets = max(float(r['until_ts'] or 0), float(r['first'] or 0) + pause)
        if forgets <= now:
            continue
        rows.append({'kind': 'admin', 'who': who, 'key': r['k'], 'by': 'address' if by == 'ip' else 'name',
                     'what': 'signing in to these pages', 'words': 'wrong passwords',
                     'fails': int(r['n'] or 0), 'limit': limit, 'locked': locked,
                     'until': float(r['until']) if locked else None, 'forgets': forgets,
                     'first': float(r['first'] or 0), 'last': float(r['first'] or 0), 'others': []})
    rows.sort(key=lambda x: (not x['locked'], -x['last']))
    return rows


def lockouts_clear(store, keys=None, by=''):
    if keys is None:
        n = store.x('DELETE FROM fails')
    else:
        n = sum(store.x('DELETE FROM fails WHERE k=?', (str(k),)) for k in keys)
    if n:
        store.add_event('sign-in', '%s cleared %d lockout(s) and count(s) of wrong passwords' % (
            by or 'root', n), 'warn', who=by)
    return n


@route('GET', '/api/lockouts', admin=True)
def api_lockouts(c):
    return {'now': time.time(), 'cluster': False,
            'nodes': [{'node': host_name(), 'fresh': True, 'rows': lockouts_view(c.daemon.store)}]}


@route('POST', '/api/lockouts', admin=True)
def api_lockouts_do(c):
    act = c.body.get('action')
    if act == 'clear_all':
        n = lockouts_clear(c.daemon.store, None, c.name)
        return {'message': 'cleared: %d' % n, 'told': []}
    if act == 'clear':
        kind = str(c.body.get('who') or '')
        keys = [k for k in ('ip:' + kind, 'name:' + kind.lower())]
        n = lockouts_clear(c.daemon.store, keys, c.name)
        return {'message': 'cleared: %d' % n, 'told': []}
    raise Refused('clear or clear_all')


# ---- mail: test, the authorities trusted, notices -------------------------------------------
@route('GET', '/api/mail', admin=True)
def api_mail(c):
    STORE_NOW['store'] = c.daemon.store
    return {'mode': CONFIG.get('mail_mode') or 'off', 'channels': code_channels(),
            'from': CONFIG.get('mail_from') or '', 'lang': CONFIG.get('mail_lang') or 'cs',
            'ca_list': describe_certificates(mail_ca_pem(c.daemon.store)),
            'sms_ca_list': describe_certificates(sms_ca_pem(c.daemon.store)),
            'notices': c.daemon.store.meta_json('notify:last', {}) or {}}


@route('POST', '/api/mail', admin=True)
def api_mail_do(c):
    act = c.body.get('action')
    st = c.daemon.store
    if act == 'test':
        try:
            to = mail_checked(c.body.get('to'))
        except ValueError as e:
            raise Refused(str(e))
        b = c.body
        began = time.time()
        queued = str(b.get('via') or '') == 'queue'
        try:
            lang = str(b.get('lang') or 'cs')
            if b.get('kind') in ('code', 'verify'):
                # The mail of a sign-in code, or of checking an address -
                # with a code that opens nothing.
                msg = code_message('mail', to, code_new(),
                                   'signin' if b.get('kind') == 'code' else 'verify',
                                   lang=lang if lang in CODE_TEXTS else None, name='jan.novak',
                                   display='Jan Novák' if lang == 'cs' else 'John Doe')
            else:
                msg = test_mail(to, lang)
            # Through the outgoing mail, as codes go: tried now, and if the
            # other side does not take it yet (greylisting) tried again by
            # itself - or straight, once, with every step said here.
            if queued:
                steps = mail_deliver(st, msg, [to], kind='test', by=c.name, purpose='test')
            else:
                steps = mail_send(st, msg, [to])
        except MailError as e:
            st.add_event('mail', 'a test mail to %s failed: %s' % (to, e), 'warn', who=c.name)
            return {'sent': False, 'said': str(e), 'steps': e.steps,
                    'queued': getattr(e, 'queued', None) if queued else None,
                    'took_ms': int((time.time() - began) * 1000)}
        st.add_event('mail', '%s sent a test mail%s to %s%s' % (
            c.name, {'code': ' shaped as a sign-in code\'s',
                     'verify': ' shaped as an address check\'s'}.get(b.get('kind'), ''), to,
            mail_reply_words(steps)), who=c.name)
        return {'sent': True, 'said': 'sent to %s' % to, 'steps': steps,
                'queued': 'sent' if queued else None, 'took_ms': int((time.time() - began) * 1000)}
    if act == 'ca':
        try:
            got = mail_ca_set(st, c.body.get('ca'), c.body.get('mode') or 'add', c.body.get('fingerprint') or '')
        except ValueError as e:
            raise Refused(str(e))
        st.add_event('mail', '%s changed the authorities trusted for the mail server (%d now)' % (c.name, len(got)),
                     'info', who=c.name)
        return {'message': '%d certificate(s) kept' % len(got), 'ca_list': got}
    STORE_NOW['store'] = st
    if act == 'sms_test':
        # An SMS the way a sign-in code goes, with a code that opens nothing (otp's).
        try:
            to = phone_checked(c.body.get('to'))
        except ValueError as e:
            raise Refused(str(e))
        began = time.time()
        try:
            said = send_sms(st, to, code_message('sms', to, code_new(), 'verify'), 'a test', c.name)
        except SmsError as e:
            st.add_event('settings', 'a test SMS to %s failed: %s' % (dest_masked('sms', to), e), 'warn', who=c.name)
            return {'sent': False, 'said': str(e), 'took_ms': int((time.time() - began) * 1000)}
        st.add_event('settings', '%s sent a test SMS to %s' % (c.name, dest_masked('sms', to)), who=c.name)
        return {'sent': True, 'said': str(said or ''), 'to': to, 'took_ms': int((time.time() - began) * 1000)}
    if act == 'tel_test':
        began = time.time()
        got = tel_test()
        got['took_ms'] = int((time.time() - began) * 1000)
        bad = [x for x in got['steps'] if not x['ok']]
        st.add_event('settings', '%s tried the SMS gateway %s: %s' % (
            c.name, got.get('host') or '?', 'it answers' if got['ok'] else (bad[0]['said'] if bad else 'it did not answer')),
            'info' if got['ok'] else 'warn', who=c.name)
        return got
    if act == 'sms_ca_fetch':
        try:
            pem = tel_peer_chain()
        except SmsError as e:
            raise Refused(str(e), 502)
        return {'pem': pem, 'certs': describe_certificates(pem)}
    if act == 'sms_ca':
        mode = str(c.body.get('mode') or 'add')
        try:
            got = sms_ca_set(st, c.body.get('ca'), mode, str(c.body.get('fingerprint') or ''))
        except ValueError as e:
            raise Refused(str(e))
        st.add_event('settings', '%s %s the certificates of the SMS gateway' % (
            c.name, {'add': 'added to', 'drop': 'took one out of'}.get(mode, 'emptied')), who=c.name)
        return {'sms_ca_list': got, 'message': 'the SMS gateway is checked against %d certificate(s)' % len(got)}
    raise Refused('no such thing to do')


@route('GET', '/api/texts', admin=True)
def api_texts(c):
    st = c.daemon.store
    STORE_NOW['store'] = st
    mid = c.arg('render')
    if mid:
        if not text_message(mid):
            raise Refused('no such message', 404)
        lang = c.arg('lang') if c.arg('lang') in TEXT_LANGS else 'cs'
        return text_render(st, mid, lang, mark=c.arg('mark') == '1')
    return {'messages': text_state(st), 'placeholders': TEXT_PLACEHOLDERS,
            'langs': list(TEXT_LANGS), 'may_change': True,
            'samples': {lang: text_samples(lang) for lang in TEXT_LANGS},
            'sender': '%s <%s>' % (CONFIG.get('mail_from_name') or site_words(), CONFIG.get('mail_from') or ''),
            'sms_plain': bool(CONFIG.get('sms_plain', True)), 'node': node_name(), 'ha': False}


@route('POST', '/api/texts', admin=True)
def api_texts_do(c):
    st, b = c.daemon.store, c.body
    STORE_NOW['store'] = st
    act = str(b.get('action') or '')
    mid = str(b.get('id') or '')
    m = text_message(mid)
    lang = str(b.get('lang') or '')
    if not m or lang not in TEXT_LANGS:
        raise Refused('no such message or language')
    fields = b.get('fields') if isinstance(b.get('fields'), dict) else {}
    if act == 'preview':
        # What the editor holds now, each field checked and cleaned as a
        # save would - and said which one is wrong, not saved.
        clean, bad = {}, {}
        for f in m['fields']:
            if f[0] in fields:
                try:
                    clean[f[0]] = text_check(f, fields[f[0]])
                except ValueError as e:
                    bad[f[0]] = str(e)
        out = text_render(st, mid, lang, clean)
        out['bad'] = bad
        out['clean'] = clean
        return out
    if act == 'save':
        try:
            new = text_save(st, mid, lang, fields, c.name, was_at=b.get('was_at') if 'was_at' in b else None)
        except TextConflict as e:
            raise Refused(str(e), 409)
        except ValueError as e:
            raise Refused(str(e))
        st.add_event('settings', '%s changed the texts of “%s” (%s)' % (c.name, m['title'], lang.upper()), who=c.name)
        return {'message': 'saved - these words are sent from now on', 'saved': new,
                'state': text_state(st, mid)[0]}
    if act == 'reset':
        keys = [str(k) for k in (b.get('keys') or []) if isinstance(k, str)]
        text_reset(st, mid, lang, keys or None)
        st.add_event('settings', '%s put %s of “%s” (%s) back as it comes'
                     % (c.name, 'the texts' if not keys else ', '.join(keys), m['title'], lang.upper()),
                     'warn', who=c.name)
        return {'message': 'put back as it comes', 'state': text_state(st, mid)[0]}
    if act == 'test':
        to = str(b.get('to') or '').strip()
        clean = {}
        for f in m['fields']:
            if f[0] in fields:
                try:
                    clean[f[0]] = text_check(f, fields[f[0]])
                except ValueError as e:
                    raise Refused(str(e))
        w = text_words(mid, lang, clean)
        smp = text_samples(lang)
        try:
            if m['kind'] == 'sms':
                to = dest_checked('sms', to)
                text = w[m['fields'][0][0]].format(**smp)
                said = send_sms(st, to, sms_plain(text) if CONFIG.get('sms_plain', True) else text,
                                'a sample of the texts', c.name)
            else:
                to = dest_checked('mail', to)
                msg = code_message('mail', to, smp['code'], m['purpose'], lang=lang,
                                   name=smp['account'], display=smp['name'], fmt='html', w=w)
                steps = mail_deliver(st, msg, [to], kind='test', by=c.name, purpose='texts')
                last = [x for x in steps if x.get('ok')]
                said = (last[-1].get('said') or 'sent') if last else 'sent'
        except ValueError as e:
            raise Refused(str(e))
        except (MailError, SmsError) as e:
            raise Refused(str(e), 502)
        st.add_event('settings', '%s sent a sample of “%s” (%s) to %s' % (c.name, m['title'], lang.upper(), to),
                     who=c.name)
        return {'message': 'sent to %s with sample values: %s' % (to, said)}
    raise Refused('no such thing to do with the texts')


# ---- the outgoing mail on the pages (otp's) ---------------------------------------------
MAILQ_COUNT_CACHE = [0.0, {}]


def mailq_counted(store):
    """What waits and what failed, for the badge beside Outgoing mail -
    counted at most every 10 s."""
    now = time.time()
    if now - MAILQ_COUNT_CACHE[0] > 10:
        try:
            MAILQ_COUNT_CACHE[1] = mailq_counts(store)
        except Exception:                               # noqa: BLE001
            pass
        MAILQ_COUNT_CACHE[0] = now
    return MAILQ_COUNT_CACHE[1]


@route('GET', '/api/mailq', admin=True)
def api_mailq(c):
    """The outgoing mail: what waits, what went, what failed."""
    st = c.daemon.store
    q = c.arg('q')
    state = c.arg('state')
    every = mailq_all(st)
    rows = [r for r in every
            if (not state or r.get('state') == state or
                (state == 'open' and r.get('state') in ('waiting', 'sending', 'failed')))]
    base = {'node': node_name(), 'retry_hours': int(CONFIG.get('mail_retry_hours') or 24),
            'keep_days': int(CONFIG.get('mail_keep_days') or 14), 'mode': CONFIG.get('mail_mode') or 'off'}
    if q.strip():
        try:
            rows = [r for r in rows if mailq_match(mailq_search_row(r), q)]
        except ValueError as e:
            return dict(base, rows=[], total=0, q_error=str(e), counts={k: 0 for k in MAILQ_STATES})
    try:
        limit = max(1, min(1000, int(c.arg('limit') or 100)))
        offset = max(0, int(c.arg('offset') or 0))
    except ValueError:
        limit, offset = 100, 0
    counts = collections.Counter(r.get('state') for r in every)
    MAILQ_COUNT_CACHE[0] = 0
    return dict(base, rows=[mailq_view(r) for r in rows[offset:offset + limit]], total=len(rows),
                counts={k: int(counts.get(k, 0)) for k in MAILQ_STATES})


@route('GET', '/api/mailq/one', admin=True)
def api_mailq_one(c):
    st = c.daemon.store
    rec, _raw = mailq_read(st, c.arg('id'))
    if not rec:
        raise Refused('that mail is not in the outgoing mail any more', 404)
    out = mailq_view(rec)
    out['history'] = rec.get('history') or []
    out['steps'] = rec.get('steps') or []
    out['has_body'] = bool(st.get_meta(MAILB_PREFIX + c.arg('id')))
    return out


@route('POST', '/api/mailq', admin=True)
def api_mailq_do(c):
    st, b = c.daemon.store, c.body
    act = str(b.get('action') or '')
    ids = b.get('ids') or []
    if not isinstance(ids, list) or not all(isinstance(x, str) and re.fullmatch(r'[0-9]{13}-[0-9a-f]{8}', x)
                                            for x in ids):
        raise Refused('ids is a list of the mails\' own ids')
    if act in ('retry_all', 'drop_sent', 'drop_failed'):
        want = {'retry_all': ('waiting', 'failed'), 'drop_sent': ('sent',),
                'drop_failed': ('failed', 'expired')}[act]
        ids = [r['qid'] for r in mailq_all(st) if r.get('state') in want]
        act = 'retry' if act == 'retry_all' else 'drop'
    MAILQ_COUNT_CACHE[0] = 0
    if act == 'retry':
        if (CONFIG.get('mail_mode') or 'off') == 'off':
            raise Refused('sending mail is switched off - Settings → Mail', 409)
        done, skipped = mailq_retry(st, ids, c.name)
        codes = MAILQ_RETRY_WHY.get('code', 0)
        rest = len(skipped) - codes
        msg = '%d mail(s) are being sent again now' % len(done)
        if codes:
            msg += ' - %d code(s) to sign in with are past their time and no good any more' % codes
        if rest:
            msg += ' - %d could not be (sent already, or what they held is gone)' % rest
        return {'done': len(done), 'skipped': len(skipped), 'message': msg}
    if act == 'drop':
        n = mailq_drop(st, ids, c.name)
        return {'done': n, 'message': '%d mail(s) taken out of the outgoing mail' % n}
    raise Refused('no such thing to do with the outgoing mail')


@route('GET', '/api/suggest', admin=True)
def api_suggest(c):
    """The fields of a list, or what one of them holds - what the search box
    over it offers as somebody types (otp's; the outgoing mail's)."""
    if c.arg('list') != 'mailq':
        return {'fields': [], 'values': []}
    field = c.arg('field').lower()
    if not field:
        return {'fields': [list(f) for f in MAILQ_FIELDS]}
    typed = c.arg('typed')[:120]
    got = collections.Counter()
    for r in mailq_all(c.daemon.store):
        v = str(mailq_search_row(r).get(field) or '')
        for one in (v.split() if field == 'to' else [v]):
            if one and (not typed or typed.strip('*').lower() in one.lower()):
                got[one] += 1
    return {'values': [{'val': v, 'n': n} for v, n in got.most_common(15)]}


def mail_reply_words(steps):
    """What the receiving server said when it took the message, for the
    event: its queue id is what its own log can be searched by."""
    last = (steps or [{}])[-1].get('said', '') if steps else ''
    return (' - the server said: %s' % last.split(' · ', 1)[1]) if ' · ' in last else ''


def notify_tick(store):
    """What Events marked as a warning or a failure, mailed to notify_to - at
    most once every notify_gap_min, the rest together in the next one."""
    to = [x for x in re.split(r'[,;\s]+', str(CONFIG.get('notify_to') or '')) if x]
    if not to or (CONFIG.get('mail_mode') or 'off') == 'off' or not CONFIG.get('mail_from'):
        return
    state = store.meta_json('notify:last', {}) or {}
    last_id = int(state.get('id') or 0)
    if not last_id:
        top = store.one('SELECT MAX(id) AS n FROM events')
        store.set_meta_json('notify:last', {'id': int((top or {}).get('n') or 0), 'at': time.time()})
        return
    if time.time() - float(state.get('at') or 0) < int(CONFIG.get('notify_gap_min') or 15) * 60:
        return
    levels = ('error',) if CONFIG.get('notify_level') == 'error' else ('warn', 'error', 'bad')
    rows = store.q('SELECT * FROM events WHERE id > ? AND level IN (%s) ORDER BY id LIMIT 200' %
                   ','.join('?' * len(levels)), [last_id] + list(levels))
    if not rows:
        return
    lang = mail_lang()
    t = NOTICE_TEXTS[lang]
    w = t['what']
    n = len(rows)
    what = w[0] if n == 1 else (w[1] if lang != 'cs' or n < 5 else w[2])
    lines = '\n'.join('%s  %s  %s' % (datetime.fromtimestamp(r['at']).strftime('%Y-%m-%d %H:%M:%S'),
                                      r['kind'], r['text']) for r in rows)
    site = site_words()
    subject = t['subject'].format(site=site, n=n, what=what)
    body = t['body'].format(site=site, lines=lines, url='https://%s/#events' % host_name())
    new = {'id': rows[-1]['id'], 'at': time.time(), 'sent': n}
    try:
        mail_deliver(store, mail_message(to, subject, body), to, kind='notice', purpose='notices')
        new['said'] = 'sent %d to %s' % (n, ', '.join(to))
    except MailError as e:
        new['said'] = 'could not be sent: %s' % e
        if not getattr(e, 'queued', None) == 'waiting':
            new['id'] = last_id             # tried again after the gap
        log_sparing('notify', 'the notices could not be mailed: %s' % e)
    store.set_meta_json('notify:last', new)


# ---- how somebody laid out the tables (otp's cols.js, as on isemon) -----------------------------
# Kept with the account (meta 'cols:<name>'); "Edit the columns" is switched
# on for one sign-in only, in its data, so signing out turns it off again.
COLS_MOST_TABLES = 300
COLS_MOST_COLUMNS = 60
COLS_MOST_BYTES = 60000
SETTINGS_FILE_KIND = 'ai-user-settings'


def clean_cols(cols):
    """A layout as the page sent it, reduced to what a layout can hold:
    `{table: {"w": {column: pixels}, "o": [order], "h": [hidden],
    "v": [optional shown], "s": [empty columns], "t": when}}` and nothing
    else. Anything not understood is dropped rather than kept."""
    if cols == [] or cols is None:
        cols = {}                       # PHP passes an empty object on as []
    if not isinstance(cols, dict):
        raise ValueError('a layout of the columns is an object of tables')
    out = {}

    def names(v, most):
        return [str(c)[:80] for c in v[:most] if isinstance(c, (str, int))] \
            if isinstance(v, list) else []

    for key, one in list(cols.items())[:COLS_MOST_TABLES]:
        key = str(key)[:160]
        if not key or not isinstance(one, dict):
            continue
        kept = {}
        widths = one.get('w')
        if isinstance(widths, dict):
            w = {}
            for col, px in list(widths.items())[:COLS_MOST_COLUMNS]:
                try:
                    px = int(round(float(px)))
                except (TypeError, ValueError, OverflowError):
                    continue
                w[str(col)[:80]] = max(24, min(3000, px))
            if w:
                kept['w'] = w
        for k in ('o', 'h', 'v'):
            got = names(one.get(k), COLS_MOST_COLUMNS)
            if got:
                kept[k] = got
        sp = [c for c in names(one.get('s'), 20) if re.match(r'^~\d{1,4}\Z', c)]
        if sp:
            kept['s'] = sp
        if kept:
            try:
                kept['t'] = int(float(one.get('t') or 0))
            except (TypeError, ValueError, OverflowError):
                kept['t'] = 0
            out[key] = kept
    if len(json.dumps(out, separators=(',', ':'))) > COLS_MOST_BYTES:
        raise ValueError('that layout of the columns is too big to keep (more than %d '
                         'characters)' % COLS_MOST_BYTES)
    return out


def user_cols(store, name):
    got = store.meta_json('cols:' + str(name), {})
    return got if isinstance(got, dict) else {}


def put_user_cols(store, name, cols):
    cols = clean_cols(cols or {})
    if cols:
        store.set_meta_json('cols:' + str(name), cols)
    else:
        store.x('DELETE FROM meta WHERE k=?', ('cols:' + str(name),))
    return cols


PREF_KEYS = ('lang', 'font', 'theme', 'favs', 'recent', 'files_hidden', 'rail', 'keys', 'paste', 'pins',
             'model', 'mode', 'args', 'last_cwd', 'cc_opts', 'term_colors')


def clean_prefs(prefs):
    if prefs == [] or prefs is None:
        prefs = {}
    if not isinstance(prefs, dict):
        raise ValueError('the choices are an object')
    out = {}
    for k, v in prefs.items():
        if k not in PREF_KEYS:
            continue
        if k == 'lang' and str(v) not in ('cs', 'en'):
            raise ValueError('no such language here: %s' % v)
        out[k] = v
    if len(json.dumps(out)) > 64000:
        raise ValueError('too much to keep')
    return out


@route('POST', '/api/auth/columns')
def api_columns(c):
    """Anybody signed in: this is how the page looks to that one person."""
    b = c.body
    st = c.daemon.store
    sid = c.who['_sid']
    if 'edit' in b:
        st.session_merge(sid, {'cols_edit': 1 if b.get('edit') else None})
        if 'cols' not in b:
            return {'edit': bool(b.get('edit'))}
    reset = bool(b.get('reset'))
    editing = bool(st.session_data(sid).get('cols_edit'))
    if not reset and not editing:
        raise Refused('switch on "Edit the columns" under your name first: the columns are not being '
                      'edited from this sign-in', 409)
    try:
        kept = put_user_cols(st, c.name, {} if reset else (b.get('cols') or {}))
    except ValueError as e:
        raise Refused(str(e))
    if reset:
        st.add_event('accounts', '%s put the columns of every table back as they come' % c.name, who=c.name)
    return {'tables': len(kept), 'edit': editing}


@route('GET', '/api/auth/settings')
def api_my_settings(c):
    """What a person has set for themselves on the page, as one object that
    can be saved to a file and read back. Never the password or the role."""
    try:
        prefs = json.loads(c.who.get('prefs') or '{}')
    except ValueError:
        prefs = {}
    return {'name': c.name, 'version': __version__, 'kind': SETTINGS_FILE_KIND,
            'settings': {'columns': user_cols(c.daemon.store, c.name), 'prefs': prefs}}


@route('POST', '/api/auth/settings')
def api_my_settings_put(c):
    got = c.body.get('settings')
    st = c.daemon.store
    if not isinstance(got, dict):
        raise Refused('that is not a file of settings: there is no "settings" in it')
    ignored = sorted(k for k in got if k not in ('columns', 'prefs'))
    try:
        cols = clean_cols(got['columns'] or {}) if 'columns' in got else None
        prefs = clean_prefs(got['prefs'] or {}) if 'prefs' in got else None
    except (ValueError, TypeError, AttributeError) as e:
        raise Refused('in that file: %s' % e)
    took = {}
    if cols is not None:
        took['columns'] = len(put_user_cols(st, c.name, cols))
    if prefs is not None:
        try:
            have = json.loads(c.who.get('prefs') or '{}')
        except ValueError:
            have = {}
        have.update(prefs)
        st.x('UPDATE users SET prefs=? WHERE name=?', (json.dumps(have), c.name))
        took['prefs'] = len(prefs)
    if not took:
        raise Refused('nothing in that file is a setting this version keeps')
    st.add_event('accounts', '%s read their own settings back from a file (%s)' % (
        c.name, ', '.join('%s: %d' % kv for kv in took.items())), who=c.name)
    return {'took': took, 'ignored': ignored}


# ---- settings, accounts, events ---------------------------------------------------------------
def setting_value(k, v):
    s = SCHEMA_KEYS[k]
    kind, extra = s[2], s[5]
    if kind == 'bool':
        return bool(v) and str(v) not in ('0', 'false', 'off')
    if kind == 'int':
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise Refused('%s: a whole number' % s[3])
        if 'min' in extra and n < extra['min'] or 'max' in extra and n > extra['max']:
            raise Refused('%s: between %s and %s' % (s[3], extra.get('min'), extra.get('max')))
        return n
    if kind == 'choice':
        if str(v) not in [x[0] for x in extra['choices']]:
            raise Refused('%s: one of the choices' % s[3])
        return str(v)
    v = str(v if v is not None else '')
    if kind in ('str', 'password'):
        v = v.strip()
        if '\n' in v or len(v) > 2000:
            raise Refused('%s: one line' % s[3])
    if len(v) > 64000:
        raise Refused('%s: too long' % s[3])
    if k == 'upgrade_url' and v and not v.startswith('https://'):
        raise Refused('the address of new versions is https://')
    if k == 'default_run_as' and v:
        linux_user(v)
    if k in ('mail_from', 'mail_reply_to') and v:
        try:
            mail_checked(v)
        except ValueError as e:
            raise Refused('%s: %s' % (s[3], e))
    if k in ('rbackup_at', 'backup_at') and not re.match(r'^([01]?\d|2[0-3]):[0-5]\d\Z', v):
        raise Refused('%s: HH:MM, as 04:15' % s[3])
    if k == 'notify_to' and v:
        try:
            v = ', '.join(mail_checked(x) for x in re.split(r'[,;\s]+', v) if x)
        except ValueError as e:
            raise Refused('%s: %s' % (s[3], e))
    return v


def settings_panes():
    """{pane: [keys]} in the order the schema has them (otp's PANES)."""
    out = {}
    for k, pane, _kind, _l, _h, _e in SCHEMA:
        out.setdefault(pane, []).append(k)
    return out


def settings_only_when():
    """otp's ONLY_WHEN: a setting that only means something while another one
    says so - [master, '1' | value | 'value-not' | [values]]."""
    out = {}
    for k, _pane, _kind, _l, _h, extra in SCHEMA:
        w = extra.get('when')
        if not w:
            continue
        master, want = w
        if isinstance(want, list):
            if want == [True]:
                want = '1'
            elif len(want) == 1:
                want = str(want[0])
            else:
                want = [str(x) for x in want]
        out[k] = [master, want]
    return out


def settings_state(store, may_change=True):
    """Every setting as otp's pages draw it: its value and default, its name
    and words, whether it is secret, and where its value comes from."""
    saved = store.settings_all()
    try:
        written = {r['k']: {'at': r['at'], 'by': r['by_who']} for r in store.q('SELECT k, at, by_who FROM settings')}
    except Exception:                                   # noqa: BLE001
        written = {}
    in_file = load_file_config()
    out = []
    for k, pane, kind, label, help_, extra in SCHEMA:
        v = CONFIG.get(k)
        d = DEFAULTS.get(k)
        source = 'saved' if k in saved and k not in FILE_ONLY_KEYS else ('file' if k in in_file else 'default')
        one = {'key': k, 'pane': pane, 'name': label, 'says': help_, 'short': '', 'source': source,
               'source_says': {'saved': 'saved on these pages', 'file': 'from config.json',
                               'default': 'the built-in default'}[source],
               'file_only': k in FILE_ONLY_KEYS, 'in_file': k in in_file, 'secret': bool(extra.get('secret')),
               'tall': kind == 'text', 'node_key': False}
        if kind == 'bool':
            one['value'], one['default'] = (1 if v else 0), bool(d)
        elif kind == 'int':
            one['value'], one['default'] = v, d
            one['min'], one['max'] = extra.get('min', 0), extra.get('max', 10 ** 9)
        else:
            one['value'], one['default'] = v if v is not None else '', d if d is not None else ''
        if kind == 'choice':
            one['choices'] = [x[0] for x in extra['choices']]
            one['choice_words'] = {x[0]: x[1] for x in extra['choices']}
        if kind == 'password' or extra.get('secret'):
            plain = unseal_secret(v, 'setting:' + k) if kind == 'password' and k not in FILE_ONLY_KEYS else v
            one['set'] = bool(v)
            one['value'] = secret_shown(plain or '') if (may_change and kind == 'password') else \
                (plain if may_change else '')
        if k in written and k in saved:
            one['saved_at'], one['saved_by'] = written[k]['at'], written[k]['by']
        out.append(one)
    return out


@route('GET', '/api/settings')
def api_settings(c):
    admin = c.who['role'] == 'admin'
    return {'settings': settings_state(c.daemon.store, admin), 'panes': settings_panes(),
            'only_when': settings_only_when(), 'config_file': str(CONFIG_FILE), 'node': node_name(),
            'cluster': False, 'may_change': admin}


@route('POST', '/api/settings', admin=True)
def api_settings_do(c):
    values = c.body.get('settings') if isinstance(c.body.get('settings'), dict) else (c.body.get('values') or {})
    if not isinstance(values, dict):
        raise Refused('values is an object')
    said, saved = [], []
    file_side = {}
    for k, v in values.items():
        if k not in SCHEMA_KEYS:
            raise Refused('%s: there is no such setting' % k)
        if k in FILE_ONLY_KEYS:
            # The address of the database (otp's): written into the config
            # file, never the database - and only once it opens.
            if (SCHEMA_KEYS[k][2] == 'password' or SCHEMA_KEYS[k][5].get('secret')) and is_masked(v):
                continue
            try:
                file_side[k] = setting_value(k, v if v is not None else DEFAULTS.get(k))
            except Refused as e:
                raise Refused('%s: %s' % (k, e))
            continue
        if v is None:
            c.daemon.store.drop_setting(k)
            said.append('%s back to its default' % k)
            saved.append(k)
            continue
        if (SCHEMA_KEYS[k][2] == 'password' or SCHEMA_KEYS[k][5].get('secret')) and is_masked(v):
            continue                    # its dots: the one saved is kept
        try:
            nv = setting_value(k, v)
        except Refused as e:
            raise Refused('%s: %s' % (k, e))
        if SCHEMA_KEYS[k][2] == 'password':
            if not nv:
                continue                # empty: the one saved is kept
            nv = seal_secret(nv, 'setting:' + k)
        if nv == DEFAULTS.get(k) and SCHEMA_KEYS[k][2] != 'password':
            c.daemon.store.drop_setting(k)
        else:
            c.daemon.store.set_setting(k, nv, c.name)
        saved.append(k)
        said.append('%s = %s' % (k, '(hidden)' if SCHEMA_KEYS[k][5].get('secret') else json.dumps(nv)[:80]))
    if file_side:
        if any(k in DB_KEYS for k in file_side) and (
                file_side.get('db_engine', CONFIG.get('db_engine')) != 'sqlite' or
                CONFIG.get('db_engine') != 'sqlite'):
            test = dict(CONFIG)
            test.update(file_side)
            try:
                probe = open_db(test)
                try:
                    probe.make_tables()
                finally:
                    probe.close()
            except Exception as e:                      # noqa: BLE001
                raise Refused('the database could not be used, so nothing was changed: %s'
                              % str(e).split('\n')[0][:300])
        write_file_settings(file_side)
        saved += sorted(file_side)
        said.append('the database settings go into %s and take effect when the service is restarted '
                    '(systemctl restart ai) - or with Start using it, which does that' % CONFIG_FILE)
    was_2fa = bool(CONFIG.get('admin_2fa'))
    config_rebuild(c.daemon.store)
    CLAUDE_CACHE.clear()
    if CONFIG.get('admin_2fa') and not was_2fa:
        # Every other sign-in gives its second step now, not when it ends.
        n = c.daemon.store.x('DELETE FROM sessions WHERE id<>?', (c.who.get('_sid') or '',))
        said.append('%d other sign-in(s) ended, to give the second step' % n)
    if said:
        c.daemon.store.add_event('settings', '%s changed: %s' % (c.name, '; '.join(said)), 'info', who=c.name)
    return {'message': '%d setting(s) saved.' % len(saved) + (' ' + said[-1] if file_side else ''),
            'saved': sorted(saved)}


@route('GET', '/api/users', admin=True)
def api_users(c):
    d = c.daemon
    mfa = mfa_all(d.store)
    users = []
    for u in d.store.users():
        one = user_view(u)
        one['mfa'] = mfa.get(u['name'].lower())
        one['cols_tables'] = len([k for k in user_cols(d.store, u['name']) if not str(k).startswith('_')])
        users.append(one)
    sessions = d.store.q('SELECT id, name, created, seen, ip, agent, data FROM sessions ORDER BY seen DESC')
    for s in sessions:
        try:
            s['mfa_pending'] = str(json.loads(s.pop('data') or '{}').get('mfa') or '')
        except ValueError:
            s['mfa_pending'] = ''
    return {'users': users, 'mfa_on': bool(CONFIG.get('admin_2fa')), 'mfa_methods': mfa_methods(),
            'sessions': sessions,
            'linux': linux_accounts(), 'me_sid': c.who.get('_sid'), 'default_run_as': CONFIG.get('default_run_as')}


@route('POST', '/api/users', admin=True)
def api_users_do(c):
    a, b = c.daemon.auth, c.body
    do = str(b.get('do') or '')
    if do == 'add':
        pw = str(b.get('password') or '') or new_password()
        if b.get('make_linux') and b.get('run_as'):
            try:
                pwd.getpwnam(str(b['run_as']))
            except KeyError:
                linux_add(str(b['run_as']), bool(b.get('sudo')))
        a.add_user(b.get('name'), pw, str(b.get('role') or 'user'), str(b.get('run_as') or ''),
                   b.get('roots') or [], must_change=b.get('must_change', True) is not False,
                   note=b.get('note') or '', by=c.name)
        return {'password': pw if not b.get('password') else ''}
    name = str(b.get('name') or '')
    if do == 'edit':
        a.edit_user(name, c.name, role=b.get('role'), run_as=b.get('run_as'),
                    roots=b.get('roots'), disabled=b.get('disabled'), note=b.get('note'))
    elif do == 'drop':
        if name == c.name:
            raise Refused('not your own account - sign in as another administrator for that')
        a.drop_user(name, c.name)
    elif do == 'password':
        pw = str(b.get('password') or '') or new_password()
        a.set_password(name, pw, c.name, must_change=b.get('must_change', True) is not False)
        c.daemon.store.x('DELETE FROM sessions WHERE name=? AND id<>?', (name, c.who.get('_sid') or ''))
        return {'password': pw if not b.get('password') else ''}
    elif do == 'end':
        c.daemon.store.x('DELETE FROM sessions WHERE id=?', (str(b.get('sid') or ''),))
        c.daemon.store.add_event('sign-in', '%s ended a sign-in of %s' % (c.name, name or '?'), 'info', who=c.name)
    elif do == 'reset_cols':
        put_user_cols(c.daemon.store, name, {})
        c.daemon.store.add_event('accounts', '%s put the columns of %s back as they come' % (c.name, name), who=c.name)
    elif do == 'mfa_reset':
        if not c.daemon.store.user(name):
            raise Refused('no such account', 404)
        had = mfa_reset(c.daemon.store, name, c.name)
        # Its sign-ins end: the next one sets a second step up again.
        if name != c.name:
            c.daemon.store.x('DELETE FROM sessions WHERE name=?', (name,))
        return {'message': 'reset - %s sets the second step up again at the next sign-in' % name
                if had else '%s had no second step set up' % name}
    elif do == 'linux':
        linux_add(str(b.get('run_as') or ''), bool(b.get('sudo')))
        c.daemon.store.add_event('accounts', '%s made the Linux account %s' % (c.name, b.get('run_as')), 'warn',
                                 who=c.name)
    else:
        raise Refused('add, edit, drop, password, end, mfa_reset or linux')
    return {}


@route('GET', '/api/events')
def api_events(c):
    per = max(10, min(500, int(c.arg('per', '100') or 100)))
    page = max(1, int(c.arg('page', '1') or 1))
    where, args = [], []
    if c.who['role'] != 'admin':
        where.append('who=?')
        args.append(c.name)
    q = c.arg('q').strip()
    if q:
        where.append('(text LIKE ? OR who LIKE ? OR kind LIKE ?)')
        args += ['%' + q + '%'] * 3
    if c.arg('kind'):
        where.append('kind=?')
        args.append(c.arg('kind'))
    w = (' WHERE ' + ' AND '.join(where)) if where else ''
    total = c.daemon.store.one('SELECT COUNT(*) AS n FROM events' + w, args)['n']
    rows = c.daemon.store.q('SELECT * FROM events%s ORDER BY id DESC LIMIT ? OFFSET ?' % w,
                            args + [per, (page - 1) * per])
    kinds = [r['kind'] for r in c.daemon.store.q('SELECT DISTINCT kind FROM events ORDER BY kind')]
    return {'events': rows, 'total': total, 'page': page, 'per': per, 'kinds': kinds}


@route('GET', '/api/log', admin=True)
def api_log(c):
    text = ''
    try:
        size = LOG_FILE.stat().st_size
        with open(LOG_FILE, 'rb') as f:
            f.seek(max(0, size - 200000))
            text = f.read().decode('utf-8', 'replace')
    except OSError:
        pass
    return {'text': text, 'file': str(LOG_FILE)}


# ---- the machine --------------------------------------------------------------------------------
@route('GET', '/api/machine', admin=True)
def api_machine(c):
    return {'machine': machine_facts(), 'paths': {'state': str(STATE_DIR), 'config': str(CONFIG_FILE),
                                                  'log': str(LOG_FILE), 'lib': str(LIB_DIR)}}


@route('GET', '/api/web', admin=True)
def api_web(c):
    prof = tls_prof(c.daemon.store)
    now = cert_now_info()
    current = bool(prof and now and (prof.get('info') or {}).get('fingerprint') == now.get('fingerprint')) \
        or (prof and not prof.get('cert'))
    p = dict(TLS_STATE['progress']) if TLS_STATE['progress'] else None
    if p:
        p['now'] = time.time()
    me = host_name()
    view = tls_view(prof)
    if view is not None:
        view['info'] = (prof or {}).get('info') or now
    return {'tls': {me: view}, 'cluster': False, 'may': True, 'presets': TLS_PRESETS, 'dh': DH_WORDS,
            'vip': {}, 'nodes': [{'name': me, 'me': True, 'host': socket.getfqdn(), 'address': '',
                                  'web': {'cert_now': now, 'state': TLS_STATE['state'] if TLS_STATE['state'] !=
                                          'done' else '', 'current': bool(current) and TLS_STATE['state'] != 'working',
                                          'said': TLS_STATE['said'], 'progress': p}}]}


@route('POST', '/api/web', admin=True)
def api_web_do(c):
    b, st = c.body, c.daemon.store
    act = str(b.get('action') or '')
    prof = tls_prof(st) or {'preset': 'standard', 'dh': 'none', 'hsts': 63072000}
    try:
        if act == 'tls_upload':
            pfx = base64.b64decode(b.get('pfx') or '') if b.get('pfx') else b''
            pend = unseal_secret(prof.get('pending_key'), 'web:tls-pending') if prof.get('pending_key') else ''
            got = cert_bundle(cert=b.get('cert') or '', pfx=pfx, password=b.get('password') or '',
                              pending_key=pend or '')
            got['key'] = seal_secret(got['key'], 'web:tls')
            prof.update(got)
            prof.pop('pending_key', None)
            prof.pop('csr', None)
            tls_apply_later(st, prof, c.name)
            return {'message': 'the certificate of %s is being put in' % (got['info'].get('cn') or '?')}
        if act == 'tls_csr':
            names = [x for x in re.split(r'[,\s]+', str(b.get('names') or '')) if x]
            key, csr = make_csr(str(b.get('cn') or '').strip(), names, str(b.get('kind') or 'rsa2048'),
                                org=b.get('org') or '', unit=b.get('unit') or '', country=b.get('country') or '',
                                city=b.get('city') or '')
            prof['pending_key'] = seal_secret(key, 'web:tls-pending')
            prof['csr'] = csr
            tls_keep(st, prof, c.name)
            st.add_event('system', '%s made a certificate request for %s' % (c.name, b.get('cn')), 'info', who=c.name)
            return {'csr': csr, 'tls': tls_view(prof)}
        if act == 'tls_csr_drop':
            prof.pop('pending_key', None)
            prof.pop('csr', None)
            tls_keep(st, prof, c.name)
            return {'message': 'the request and its key are gone'}
        if act == 'tls_selfsigned':
            names = [x for x in re.split(r'[,\s]+', str(b.get('names') or '')) if x]
            key, crt = make_selfsigned(str(b.get('cn') or '').strip(), names, int(b.get('days') or 825),
                                       str(b.get('kind') or 'rsa2048'), org=b.get('org') or '')
            got = cert_bundle(cert=crt, key=key)
            got['key'] = seal_secret(got['key'], 'web:tls')
            prof.update(got)
            tls_apply_later(st, prof, c.name)
            return {'message': 'a self-signed certificate for %s is being put in' % b.get('cn')}
        if act == 'tls_policy':
            prof.update(tls_policy_checked(b))
            tls_apply_later(st, prof, c.name)
            return {'message': 'the TLS settings are being put in'}
        if act == 'tls_pem':
            if prof.get('cert'):
                return {'pem': prof['cert'] + (prof.get('chain') or '')}
            return {'pem': read_text(CERT_FILE)}
        if act == 'tls_forget':
            st.x('DELETE FROM meta WHERE k=?', ('web:tls',))
            st.add_event('system', '%s let the TLS of the pages go: nginx keeps what it has' % c.name, 'info', who=c.name)
            return {'message': 'ai no longer looks after it - nginx keeps what it has'}
    except ValueError as e:
        raise Refused(str(e))
    raise Refused('no such thing to do')


# ---------------------------------------------------------------------------
# What otp's database page stands on (1.0.6)
# ---------------------------------------------------------------------------
BACKUP_DIR = STATE_DIR / 'backups'
DB_KEYS = ('db_engine', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password', 'db_timeout_s',
           'db_tls', 'db_tls_ca')


class ApiError(Refused):
    """otp's words for a refusal: the status first."""

    def __init__(self, status, said):
        Refused.__init__(self, said, status)


def write_replacing(path, text, mode=0o640, owner=None):
    """A file written beside itself and renamed over: never half of one."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        if owner is not None and os.geteuid() == 0:
            os.fchown(fd, owner[0], owner[1])
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def write_file_settings(changes, path=None):
    """A few settings changed in config.json, the rest of it left alone."""
    where = Path(path) if path else CONFIG_FILE
    try:
        with open(where, encoding='utf-8') as f:
            had = json.load(f)
        if not isinstance(had, dict):
            raise ValueError('it is not an object')
    except FileNotFoundError:
        had = {}
    except ValueError as e:
        raise OSError('%s is there but cannot be read (%s); put it right first - nothing was written to it'
                      % (where, str(e)[:120]))
    for key, value in changes.items():
        if key not in DEFAULTS:
            continue
        if value == DEFAULTS[key]:
            had.pop(key, None)
        else:
            had[key] = value
    try:
        mode = (os.stat(where).st_mode & 0o770) or 0o640
    except OSError:
        mode = 0o640
    write_replacing(where, json.dumps(had, indent=2, sort_keys=True, ensure_ascii=False) + '\n', mode)
    return where


def _bundle_key(passphrase, salt):
    return hashlib.scrypt(str(passphrase).encode('utf-8'), salt=salt, n=2 ** 15, r=8, p=1,
                          maxmem=64 * 1024 * 1024, dklen=32)


def bundle_lock(data, passphrase, kind):
    salt = secrets.token_bytes(16)
    key = _bundle_key(passphrase, salt)
    raw = json.dumps(data).encode('utf-8')
    nonce = secrets.token_bytes(16)
    hide = hmac.new(key, b'hide', hashlib.sha256).digest()
    sign = hmac.new(key, b'sign', hashlib.sha256).digest()
    body = bytes(a ^ b for a, b in zip(raw, _seal_stream(hide, nonce, len(raw))))
    tag = hmac.new(sign, kind.encode('utf-8') + b'\n' + salt + nonce + body, hashlib.sha256).digest()
    return {'kind': kind, 'format': 2, 'made': time.time(), 'from': node_name(), 'version': __version__,
            'locked': base64.b64encode(salt + nonce + body + tag).decode('ascii')}


def bundle_open(bundle, passphrase, kinds):
    if isinstance(bundle, str):
        try:
            bundle = json.loads(bundle)
        except ValueError:
            raise ValueError('that is not a locked file of ai: it is not JSON')
    if not isinstance(bundle, dict) or bundle.get('kind') not in kinds:
        raise ValueError('that is not a locked file of ai')
    try:
        raw = base64.b64decode(bundle.get('locked') or '')
    except (ValueError, TypeError):
        raise ValueError('the file is damaged')
    if len(raw) < 16 + 16 + 32:
        raise ValueError('the file is damaged')
    salt, nonce, body, tag = raw[:16], raw[16:32], raw[32:-32], raw[-32:]
    key = _bundle_key(passphrase, salt)
    sign = hmac.new(key, b'sign', hashlib.sha256).digest()
    signed = str(bundle.get('kind')).encode('utf-8') + b'\n' + salt + nonce + body
    if not hmac.compare_digest(tag, hmac.new(sign, signed, hashlib.sha256).digest()):
        raise ValueError('the passphrase is not the one the file was locked with')
    hide = hmac.new(key, b'hide', hashlib.sha256).digest()
    return json.loads(bytes(a ^ b for a, b in zip(body, _seal_stream(hide, nonce, len(body)))).decode('utf-8'))


def job_publish(job):
    store = STORE_NOW.get('store')
    if not store:
        return
    try:
        store.set_meta('db_job:' + node_name(), json.dumps(dict(job, node=node_name(), at=time.time()),
                                                           default=str))
    except Exception:                                   # noqa: BLE001
        pass


def job_read():
    """The job going on, or the last one - as the daemon has it."""
    if DB_JOB.get('running') or DB_JOB.get('ended'):
        return dict(DB_JOB, node=node_name())
    store = STORE_NOW.get('store')
    if store:
        try:
            one = json.loads(store.get_meta('db_job:' + node_name()) or 'null')
            if one and one.get('running'):
                one = dict(one, running=False, ended=float(one.get('at') or 0),
                           error=one.get('error') or 'it stopped with the service that ran it '
                           '(restarted, or the database was changed)')
            if one:
                return one
        except Exception:                               # noqa: BLE001
            pass
    return dict(DB_JOB)


# ---------------------------------------------------------------------------
# Copies of the database
# ---------------------------------------------------------------------------
BACKUP_ROOM_MIN = 128 << 20


def backup_room_check(store, folder=None):
    """Room left for a copy without filling the disk (1.0.149): a full disk
    under a SQLite database refused every sign-in until space was freed.
    What the copy may take - the database file itself at most - and 128 MB
    more must stay free."""
    try:
        free = shutil.disk_usage(str(folder or BACKUP_DIR)).free
    except OSError:
        return
    size = 0
    if store.db.engine == 'sqlite':
        try:
            size = os.path.getsize(str(store.db.path))
        except (OSError, TypeError):
            size = 0
    need = size + BACKUP_ROOM_MIN
    if free < need:
        raise ValueError('there is no room for a copy in %s: %d MB free, %d MB needed so that '
                         'the disk is not filled under the database - take old copies away, '
                         'or give the disk more room' % (folder or BACKUP_DIR, free >> 20,
                                                         need >> 20))


def make_backup(store, why='by hand'):
    """A copy of everything into the backups folder - and the key its secrets
    are sealed with beside it, because one without the other is nothing."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_room_check(store)
    stamp_ = datetime.now().strftime('%Y%m%d-%H%M%S')
    # A name of its own (two in one second overwrote each other) and written
    # under another until it is whole (1.0.59): a half file counted as a
    # kept copy and pushed a good one out.
    # The name taken with O_EXCL (1.0.61): two processes - the daemon's
    # nightly copy and a root --backup - in the same second both saw it free.
    base = stamp_
    for suffix in [''] + ['-' + c for c in 'bcdefghijklmnopqrstuvwxyz']:
        stamp_ = base + suffix
        out = BACKUP_DIR / ('ai-%s.json.gz' % stamp_)
        try:
            os.close(os.open(str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640))
            break
        except FileExistsError:
            continue
    else:
        raise ValueError('no free name for a copy in %s' % BACKUP_DIR)
    # A name nobody can have put there first, opened without following a
    # link, its mode and owner set on the open file (1.0.101): run by root
    # (--ha-resync, --backup) in a folder the service's account can write,
    # the name it wrote to was the service account's to point anywhere.
    part = BACKUP_DIR / ('.ai-%s-%s.json.gz.part' % (stamp_, secrets.token_hex(6)))
    owner = None
    try:
        fd = os.open(str(part), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640)
        os.fchmod(fd, 0o640)
        if owner:
            os.fchown(fd, owner[0], owner[1])
        with os.fdopen(fd, 'wb') as raw_f:
            dump_tables(store.db, raw_f)
        os.replace(str(part), str(out))
    except BaseException:
        try:
            out.unlink()            # the empty name taken, given back
        except OSError:
            pass
        raise
    finally:
        try:
            part.unlink()
        except OSError:
            pass
    key = sealing_key()
    if key:
        # Made by root on the command line (1.0.59): the service's own, or
        # the pages could neither list, download nor put it back.
        write_replacing(BACKUP_DIR / ('ai-%s.key' % stamp_), key.hex() + '\n', 0o600,
                        owner=owner)
    keep = int(CONFIG.get('backup_keep') or 14)
    copies = sorted(list(BACKUP_DIR.glob('ai-*.json.gz')) + [],
                    key=lambda f: f.stat().st_mtime)
    for old in copies[:-keep] if len(copies) > keep else []:
        for f in (old, old.with_name(old.name.replace('.json.gz', '.key'))):
            try:
                f.unlink()
            except OSError:
                pass
    store.add_event('backups', 'a copy of the database was made (%s): %s' % (why, out.name))
    return out


def backups():
    if not BACKUP_DIR.is_dir():
        return []
    out = []
    for f in sorted(list(BACKUP_DIR.glob('ai-*.json.gz')) + [],
                   key=lambda f: f.stat().st_mtime, reverse=True):
        st = f.stat()
        out.append({'name': f.name, 'size': st.st_size, 'at': st.st_mtime,
                    'key': f.with_name(f.name.replace('.json.gz', '.key')).exists()})
    return out


# ---------------------------------------------------------------------------
# Moving to another database, looking after the one in use, tuning its
# server - the database page, as isemon has it
# ---------------------------------------------------------------------------
ENGINE_WORDS = {'sqlite': 'the file on this machine (SQLite)', 'mariadb': 'MariaDB',
                'postgres': 'PostgreSQL'}
# DB_KEYS is 00_head's (1.0.94): a second one here, without db_tls and
# db_tls_ca, left the database's TLS out of the test before a save, of the
# cluster's bundle and of the move to another database.
DB_IDENT = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,62}\Z')


def file_db_settings():
    """The database settings as config.json has them now - Set it up writes
    the address and the password made there while the old database is
    still the one in use, and the steps after it must find them (1.0.37)."""
    try:
        with open(str(CONFIG_FILE), encoding='utf-8') as f:
            got = json.load(f)
        return {k: got[k] for k in DB_KEYS if k in got} if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def engine_asked(given):
    """The database the page means: what it typed, over what is set."""
    c = {k: CONFIG.get(k) for k in DB_KEYS}
    on_file = file_db_settings()
    for k, v in on_file.items():
        if k != 'db_engine':
            c[k] = v
    for k, v in (given or {}).items():
        if k not in DB_KEYS or v is None:
            continue
        if k == 'db_password' and is_masked(v):
            continue
        c[k] = v
    if c.get('db_engine') not in ('sqlite', 'mariadb', 'postgres'):
        raise ValueError('the engine is sqlite, mariadb or postgres')
    for k in ('db_name', 'db_user'):
        if c['db_engine'] != 'sqlite' and not DB_IDENT.match(str(c.get(k) or '')):
            raise ValueError('%s is letters, digits and _ only, starting with a letter' % k)
    return c


def db_open(c, statement_s=None):
    return Db(c.get('db_engine') or 'sqlite', c.get('db_host') or '', c.get('db_port') or 0,
              c.get('db_name') or 'ai', c.get('db_user') or 'ai', c.get('db_password') or '',
              c.get('db_timeout_s') or 10,
              tls=c.get('db_tls') if 'db_tls' in c else CONFIG.get('db_tls'),
              tls_ca=c.get('db_tls_ca') if 'db_tls_ca' in c else CONFIG.get('db_tls_ca'),
              statement_s=statement_s)


def db_own(store, statement_s=0):
    """A connection of its own to the database in use, for a long job
    (1.0.101): a VACUUM FULL, a check of every table - on the one every
    sign-in shares, each held them all for as long as it took. SQLite has
    one file and one connection: that one. Closed by the caller."""
    if store.db.engine == 'sqlite':
        return None
    return db_open({k: CONFIG.get(k) for k in DB_KEYS}, statement_s=statement_s)


def same_database(c, db):
    """Whether the page's database is the one in use."""
    if c.get('db_engine') != db.engine:
        return False
    if db.engine == 'sqlite':
        return True
    port = int(c.get('db_port') or {'mariadb': 3306, 'postgres': 5432}[db.engine])
    here = {'', 'localhost', '127.0.0.1', '::1'}
    a, b = str(c.get('db_host') or '').lower(), str(db.host or '').lower()
    return ((a == b or (a in here and b in here)) and port == int(db.port or port)
            and str(c.get('db_name')) == str(db.name))


def db_try(c):
    """Reach a database as this program would. Never raises."""
    out = {'reached': False, 'engine': c.get('db_engine'),
           'words': ENGINE_WORDS.get(c.get('db_engine'), c.get('db_engine'))}
    try:
        db = db_open(c)
    except Exception as e:
        out['trouble'] = str(e).split('\n')[0][:300]
        return out
    try:
        out['reached'] = True
        out['where'] = db.where()
        out['version'] = db.version()
        names = db.tables()
        ours = [t for t in DB_TABLES if t in names]
        out['tables'] = ours
        out['rows'] = sum(int(db.value('SELECT COUNT(*) FROM %s' % t) or 0)
                          for t in ours if t not in ('meta',))
        try:
            db.run('CREATE TABLE ai_probe (x INTEGER)')
            db.run('DROP TABLE ai_probe')
            out['writable'] = True
        except Exception as e:
            out['writable'] = False
            out['trouble'] = 'it answers, but this account may not make a table: %s' % (
                str(e).split('\n')[0][:200])
    except Exception as e:
        out['trouble'] = str(e).split('\n')[0][:300]
    finally:
        db.close()
    return out


def db_password_made():
    alphabet = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(24))


def db_make(c, admin_user, admin_password):
    """The database and its account, made by an administrator of that
    server who is used for this one connection and kept nowhere."""
    eng = c['db_engine']
    host = str(c.get('db_host') or '127.0.0.1')
    port = int(c.get('db_port') or {'mariadb': 3306, 'postgres': 5432}[eng])
    name, user, pw = c['db_name'], c['db_user'], c['db_password']
    done = []
    if eng == 'mariadb':
        import pymysql
        conn = pymysql.connect(host=host, port=port, user=admin_user, password=admin_password,
                               connect_timeout=int(c.get('db_timeout_s') or 10), autocommit=True)
        try:
            cur = conn.cursor()
            cur.execute('CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 '
                        'COLLATE utf8mb4_unicode_ci' % name)
            done.append('the database %s' % name)
            local = host in ('localhost', '127.0.0.1', '::1')
            for at in (('localhost', '127.0.0.1') if local else ('%',)):
                cur.execute("CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s", (user, at, pw))
                cur.execute("ALTER USER %s@%s IDENTIFIED BY %s", (user, at, pw))
                cur.execute('GRANT ALL PRIVILEGES ON `%s`.* TO %%s@%%s' % name, (user, at))
                done.append("the account '%s'@'%s', with every right on %s and none elsewhere"
                            % (user, at, name))
            cur.execute('FLUSH PRIVILEGES')
        finally:
            conn.close()
        return done
    import psycopg2
    conn = psycopg2.connect(host=host, port=port, user=admin_user, password=admin_password,
                            dbname='postgres', connect_timeout=int(c.get('db_timeout_s') or 10))
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (user,))
        if cur.fetchone():
            cur.execute('ALTER ROLE "%s" WITH LOGIN PASSWORD %%s' % user, (pw,))
            done.append('the account %s was there; its password is new' % user)
        else:
            cur.execute('CREATE ROLE "%s" WITH LOGIN PASSWORD %%s' % user, (pw,))
            done.append('the account %s' % user)
        cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (name,))
        if cur.fetchone():
            cur.execute('ALTER DATABASE "%s" OWNER TO "%s"' % (name, user))
            done.append('the database %s was there; %s owns it now' % (name, user))
        else:
            cur.execute("CREATE DATABASE \"%s\" OWNER \"%s\" ENCODING 'UTF8' TEMPLATE template0"
                        % (name, user))
            done.append('the database %s, owned by %s' % (name, user))
    finally:
        conn.close()
    conn = psycopg2.connect(host=host, port=port, user=admin_user, password=admin_password,
                            dbname=name, connect_timeout=int(c.get('db_timeout_s') or 10))
    conn.autocommit = True
    try:
        conn.cursor().execute('GRANT ALL ON SCHEMA public TO "%s"' % user)
    except Exception:
        pass
    finally:
        conn.close()
    return done


def db_empty(c):
    db = db_open(c)
    try:
        gone = []
        for t in reversed(DB_TABLES):
            if t in db.tables():
                db.run('DROP TABLE %s' % t)
                gone.append(t)
        return gone
    finally:
        db.close()


# ---- one long job at a time, which the page asks after ---------------------
DB_JOB = {'id': 0, 'what': '', 'running': False, 'done': 0, 'whole': 0, 'says': '',
          'error': '', 'result': None, 'began': 0, 'ended': 0}
DB_JOB_LOCK = threading.Lock()


def db_job(what, work):
    with DB_JOB_LOCK:
        if DB_JOB['running']:
            raise ValueError('%s is going on already' % DB_JOB['what'])
        DB_JOB.update({'id': DB_JOB['id'] + 1, 'what': what, 'running': True, 'done': 0,
                       'whole': 0, 'says': '', 'error': '', 'result': None,
                       'began': time.time(), 'ended': 0})

    def progress(done, whole, says):
        DB_JOB.update({'done': done, 'whole': whole, 'says': says})
        if time.time() - DB_JOB.get('_pub', 0) > 1:
            DB_JOB['_pub'] = time.time()
            job_publish({k: v for k, v in DB_JOB.items() if not k.startswith('_')})

    def run():
        try:
            DB_JOB['result'] = work(progress)
        except Exception as e:
            DB_JOB['error'] = scrub_secret(str(e).split('\n')[0][:400])
            log('%s failed: %s' % (what, scrub_secret(e)), 'error')
        finally:
            DB_JOB.update({'running': False, 'ended': time.time()})
            job_publish({k: v for k, v in DB_JOB.items() if not k.startswith('_')})

    def beat():
        # Said again every half minute, so the other node - or this one,
        # after a restart - can tell a job going on from one that died.
        while DB_JOB.get('running'):
            time.sleep(30)
            if DB_JOB.get('running'):
                job_publish({k: v for k, v in DB_JOB.items() if not k.startswith('_')})

    threading.Thread(target=run, name='db-job', daemon=True).start()
    threading.Thread(target=beat, name='db-job-beat', daemon=True).start()
    return dict(DB_JOB)


def db_move(store, c, by):
    """Everything here into the other database, through a copy."""
    def work(progress):
        progress(0, 0, 'making a copy of what is here')
        before = store.counts()
        copy = make_backup(store, 'before moving, by %s' % by)
        whole = sum(before.values())
        far = db_open(c)
        tally = {}
        try:
            def along(table, done):
                tally[table] = done
                progress(sum(tally.values()), whole, '%s: %s' % (table, done))
            load_tables(far, copy, say=along)
            after = {t: int(far.value('SELECT COUNT(*) FROM %s' % t) or 0)
                     for t in DB_TABLES if t != 'meta'}
        finally:
            far.close()
        short = {t: (before.get(t, 0), after.get(t, 0)) for t in after
                 if after.get(t, 0) < before.get(t, 0) and t not in ('sessions',)}
        store.add_event('settings', 'everything was carried into %s (%s), by %s'
                        % (ENGINE_WORDS.get(c['db_engine']), db_where(c), by), who=by)
        progress(whole, whole, 'done')
        return {'copy': copy.name, 'rows': sum(after.values()), 'short': short,
                'where': db_where(c)}
    return db_job('carrying everything across', work)


def db_where(c):
    if c.get('db_engine') == 'sqlite':
        return str(DB_FILE)
    return '%s@%s:%s/%s' % (c.get('db_user'), c.get('db_host') or 'localhost',
                            c.get('db_port') or {'mariadb': 3306, 'postgres': 5432}
                            [c['db_engine']], c.get('db_name'))


# ---- looking after the one in use --------------------------------------------
def db_table_sizes(db):
    """Rows and bytes of every table, as far as the engine says."""
    out = []
    sizes = {}
    try:
        if db.engine == 'mariadb':
            for r in db.rows('SELECT TABLE_NAME AS t, DATA_LENGTH + INDEX_LENGTH AS b, '
                             'DATA_FREE AS f FROM information_schema.DB_TABLES '
                             'WHERE TABLE_SCHEMA = DATABASE()'):
                sizes[r['t']] = (int(r['b'] or 0), int(r['f'] or 0))
        elif db.engine == 'postgres':
            for t in DB_TABLES:
                sizes[t] = (int(db.value('SELECT pg_total_relation_size(?)', (t,)) or 0), 0)
        else:
            try:
                for r in db.rows('SELECT name AS t, SUM(pgsize) AS b FROM dbstat GROUP BY name'):
                    sizes[r['t']] = (int(r['b'] or 0), 0)
            except Exception:
                pass
    except Exception:
        pass
    for t in DB_TABLES:
        try:
            n = int(db.value('SELECT COUNT(*) FROM %s' % t) or 0)
        except Exception:
            n = 0
        b, free = sizes.get(t, (None, 0))
        out.append({'table': t, 'rows': n, 'bytes': b, 'free': free})
    return out


def db_free_inside(db):
    """Room the engine holds that it would give back to the disk."""
    try:
        if db.engine == 'sqlite':
            pages = int(db.value('PRAGMA freelist_count') or 0)
            return pages * int(db.value('PRAGMA page_size') or 4096)
        if db.engine == 'mariadb':
            return int(db.value('SELECT SUM(DATA_FREE) FROM information_schema.DB_TABLES '
                                'WHERE TABLE_SCHEMA = DATABASE()') or 0)
        return int(db.value('SELECT COALESCE(SUM(n_dead_tup), 0) FROM pg_stat_user_tables') or 0)
    except Exception:
        return 0


def db_check(db):
    """Read the database through and say whether anything is broken."""
    said = []
    if db.engine == 'sqlite':
        got = [r for r in db.rows('PRAGMA integrity_check')]
        words = [list(r.values())[0] for r in got]
        return {'ok': words == ['ok'], 'said': words[:20]}
    if db.engine == 'mariadb':
        ok = True
        for t in DB_TABLES:
            for r in db.rows('CHECK TABLE %s' % t):
                v = {k.lower(): x for k, x in r.items()}
                if str(v.get('msg_type')).lower() in ('error', 'warning') or \
                        str(v.get('msg_text')).lower() not in ('ok', 'table is already up to date'):
                    ok = False
                    said.append('%s: %s' % (t, v.get('msg_text')))
        return {'ok': ok, 'said': said or ['every table: OK']}
    ok = True
    for t in DB_TABLES:
        try:
            n = db.value('SELECT COUNT(*) FROM %s' % t)
            said.append('%s: %s row(s) read' % (t, n))
        except Exception as e:
            ok = False
            said.append('%s: %s' % (t, str(e).split('\n')[0]))
    return {'ok': ok, 'said': said}


def db_statistics(db):
    """Fresh statistics for the planner - quick, nothing is locked."""
    if db.engine == 'sqlite':
        db.run('ANALYZE')
        db.run('PRAGMA optimize')
    elif db.engine == 'mariadb':
        for t in DB_TABLES:
            db.rows('ANALYZE TABLE %s' % t)
    else:
        db.run('ANALYZE')
    return 'the statistics of every table are fresh'


def db_give_back(store, progress):
    """Give the room deleted rows left back to the disk: VACUUM, OPTIMIZE
    TABLE, VACUUM FULL. Each holds a table shut while it works."""
    own = db_own(store)
    try:
        return _db_give_back(own or store.db, progress)
    finally:
        if own:
            own.close()


def _db_give_back(db, progress):
    before = db.size()
    if db.engine == 'sqlite':
        progress(0, 1, 'VACUUM')
        db.run('PRAGMA wal_checkpoint(TRUNCATE)')
        db.run('VACUUM')
        db.run('PRAGMA wal_checkpoint(TRUNCATE)')
    else:
        for i, t in enumerate(DB_TABLES):
            progress(i, len(DB_TABLES), t)
            if db.engine == 'mariadb':
                db.rows('OPTIMIZE TABLE %s' % t)
            else:
                db.run('VACUUM (FULL, ANALYZE) %s' % t)
    after = db.size()
    progress(1, 1, 'done')
    return {'before': before, 'after': after}


def db_prune(store, days):
    """Forget the events and the outgoing mail older than `days`."""
    edge = time.time() - int(days) * 86400 if int(days) > 0 else time.time() + 86400
    mails = [r['qid'] for r in mailq_all(store)
             if r.get('state') in ('sent', 'failed', 'expired') and float(r.get('created') or 0) < edge]
    return {'events': store.delete_older('events', edge), 'mailq': mailq_drop(store, mails)}


# ---- the server's own settings, for its machine (isemon's DbTune, smaller) --
def tune_machine(c, typed):
    """What the database server's machine has: read here when it is this
    machine, typed on the page when it is not."""
    host = str(c.get('db_host') or '').lower()
    local = host in ('', 'localhost', '127.0.0.1', '::1') or host == socket.gethostname().lower()
    facts = {'local': local, 'ram_gb': None, 'cpus': None, 'disk': None, 'avail': None,
             'ram': None, 'virtual': None, 'rotational': None,
             'source': 'this machine' if local else ''}
    if local:
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        facts['ram'] = int(line.split()[1]) * 1024
                    elif line.startswith('MemAvailable:'):
                        facts['avail'] = int(line.split()[1]) * 1024
            if facts['ram']:
                facts['ram_gb'] = round(facts['ram'] / 1073741824.0, 1)
        except OSError:
            pass
        facts['cpus'] = os.cpu_count()
        try:
            with open('/proc/cpuinfo') as f:
                facts['virtual'] = ' hypervisor' in f.read()
        except OSError:
            pass
        try:
            rot = [open(p).read().strip() for p in
                   [str(x) for x in Path('/sys/block').glob('*/queue/rotational')]
                   if not re.search(r'/(loop|ram|zram|sr|dm-)\d', p)]
            if rot:
                facts['rotational'] = all(r == '1' for r in rot)
        except OSError:
            pass
    for k in ('ram_gb', 'cpus'):
        if typed.get(k) not in (None, ''):
            try:
                v = float(str(typed[k]).replace(',', '.')) if k == 'ram_gb' else int(typed[k])
            except ValueError:
                raise ValueError('the memory is a number of GB, the processors a whole number')
            if k == 'ram_gb' and facts['ram_gb'] and abs(v - facts['ram_gb']) > 0.05 * v:
                facts['source'] = 'typed' if not local else facts['source']
            if k == 'cpus' and v != facts['cpus'] and not local:
                facts['source'] = 'typed'
            facts[k] = v
            if k == 'ram_gb':
                facts['ram'] = int(v * 1073741824)
    return facts


def tune_commit_ms(db):
    """How long the server takes to make one small write safe: the middle of
    twenty, each its own transaction, less a round trip."""
    if db.engine == 'sqlite':
        return None
    took, trip = [], []
    # A row of this node's own (1.0.59): two nodes measuring at once wrote
    # the same key, and replication stopped on the duplicate.
    probe = 'tune_probe:' + node_name()
    try:
        # The row is there to be written (1.0.44): an UPDATE of nothing
        # commits nothing and every disk looked fast.
        db.run('DELETE FROM meta WHERE k = ?', (probe,))
        db.run('INSERT INTO meta (k, v) VALUES (?, ?)', (probe, '0'))
        for _ in range(5):
            t = time.perf_counter()
            db.value('SELECT 1')
            trip.append(time.perf_counter() - t)
        for i in range(20):
            t = time.perf_counter()
            db.run('UPDATE meta SET v = ? WHERE k = ?', (str(i), probe))
            took.append(time.perf_counter() - t)
        db.run('DELETE FROM meta WHERE k = ?', (probe,))
    except Exception:                                   # noqa: BLE001
        return None
    took.sort()
    trip.sort()
    return max(0.0, (took[len(took) // 2] - trip[len(trip) // 2]) * 1000.0)


def tune_disk_guess(facts, commit_ms):
    """As isemon's: what the disk says of itself first - except in a virtual
    machine, where a disk says it spins whatever it is on - then how long a
    small write takes to be made safe."""
    rot = facts.get('rotational')
    if rot is False:
        return 'ssd', 'the disk says it does not spin'
    if rot is True and not facts.get('virtual'):
        return 'hdd', 'the disk says it spins'
    if commit_ms is not None:
        if commit_ms < 2.5:
            return 'ssd', 'a write is made safe in %.1f ms, which is an SSD' % commit_ms
        if commit_ms > 6:
            return 'hdd', 'a write is made safe in %.1f ms, which is a disk that spins' % commit_ms
    return 'ssd', ('not known for certain - most servers are on SSDs now; choose the other if '
                   'this one is not')


def _mb(n):
    n = int(n)
    return '%dGB' % (n // 1024) if n >= 1024 and n % 1024 == 0 else '%dMB' % n


def tune_plan(engine, m):
    """name -> (value, why, needs_restart)"""
    ram = int((m.get('ram_gb') or 4) * 1024)
    cpus = max(1, int(m.get('cpus') or 2))
    ssd = (m.get('disk') or 'ssd') == 'ssd'
    # Shared with ai itself (and nginx, PHP, Claude Code) when it is this machine.
    share = 0.8 if m.get('local') else 1.0
    if engine == 'postgres':
        sb = max(128, min(int(ram * share / 4), 16384))
        return {
            'shared_buffers': (_mb(sb), 'a quarter of the memory: the server’s own cache', True),
            'effective_cache_size': (_mb(int(ram * share * 3 / 4)),
                                     'how much the planner may assume is cached', False),
            'maintenance_work_mem': (_mb(max(64, min(ram // 16, 2048))),
                                     'for VACUUM and building indexes', False),
            'work_mem': (_mb(max(4, min(ram // 256, 64))), 'for each sort and hash', False),
            'wal_buffers': ('16MB', 'the write-ahead log’s buffer', True),
            'max_wal_size': ('4GB' if ssd else '2GB', 'fewer checkpoints under load', False),
            'min_wal_size': ('1GB', 'kept between checkpoints', False),
            'checkpoint_completion_target': ('0.9', 'checkpoints spread out', False),
            'random_page_cost': ('1.1' if ssd else '4', 'an SSD reads anywhere as fast', False),
            'effective_io_concurrency': ('200' if ssd else '2', 'reads the disk takes at once', False),
            'max_worker_processes': (str(max(8, cpus)), 'one per processor', True),
            'max_parallel_workers': (str(cpus), 'parallel queries over every processor', False),
            'max_parallel_workers_per_gather': (str(max(1, min(4, cpus // 2))),
                                                'per query', False),
        }
    pool = max(128, int(ram * share * (0.5 if m.get('local') else 0.7)) // 128 * 128)
    return {
        'innodb_buffer_pool_size': (str(pool * 1048576), 'the server’s own cache: %s'
                                    % _mb(pool), False),
        'innodb_log_file_size': (str(min(pool // 4, 2048) * 1048576),
                                 'a log large enough for a busy hour', True),
        'innodb_flush_method': ('O_DIRECT', 'no second copy in the system’s cache', True),
        'innodb_io_capacity': ('2000' if ssd else '200', 'what the disk takes per second', False),
        'innodb_io_capacity_max': ('4000' if ssd else '400', '...at most', False),
        'innodb_flush_neighbors': ('0' if ssd else '1', 'an SSD has no neighbours', False),
        'tmp_table_size': (str(64 * 1048576), 'in-memory temporary tables', False),
        'max_heap_table_size': (str(64 * 1048576), '...the same', False),
        'table_open_cache': ('2000', 'tables kept open', False),
    }


def tune_current(db, names):
    out = {}
    for n in names:
        try:
            if db.engine == 'postgres':
                out[n] = str(db.value('SHOW %s' % n))
            else:
                r = db.row("SHOW GLOBAL VARIABLES LIKE ?", (n,))
                out[n] = str(list(r.values())[1]) if r else ''
        except Exception:
            out[n] = ''
    return out


def tune_same(engine, a, b):
    def norm(v):
        v = str(v).strip()
        m = re.match(r'^(\d+(?:\.\d+)?)\s*(kB|MB|GB|TB)?\Z', v, re.I)
        if not m:
            return v.lower()
        mult = {'kb': 1, 'mb': 1024, 'gb': 1048576, 'tb': 1073741824}.get(
            (m.group(2) or '').lower(), None)
        return float(m.group(1)) * mult if mult else float(m.group(1))
    try:
        x, y = norm(a), norm(b)
        if isinstance(x, float) and isinstance(y, float) and max(x, y) >= 1024:
            # Memory: within a tenth is the same - what is free moves from one
            # look to the next, and a setting is not changed for that.
            return abs(x - y) <= 0.1 * max(x, y)
        return x == y
    except Exception:
        return str(a) == str(b)


def tune_connect(store, admin_user, admin_password):
    """The server, as an administrator when one is given, else as ourselves."""
    c = {k: CONFIG.get(k) for k in DB_KEYS}
    if admin_user:
        c['db_user'], c['db_password'] = admin_user, admin_password
        if c['db_engine'] == 'postgres':
            pass
    return db_open(c) if admin_user else store.db


def tune_last(store):
    try:
        return json.loads(store.get_meta('tune_last:' + node_name()) or 'null')
    except ValueError:
        return None


def tune_pending(db):
    if db.engine != 'postgres':
        return []
    try:
        return [r['name'] for r in db.rows('SELECT name FROM pg_settings WHERE pending_restart')]
    except Exception:                                   # noqa: BLE001
        return []


def tune_plan_for(store, typed, probe=True):
    db = store.db
    if db.engine == 'sqlite':
        raise ValueError('the file on this machine has no server to tune: this program sets '
                         'it up itself')
    c = {k: CONFIG.get(k) for k in DB_KEYS}
    typed = typed or {}
    m = tune_machine(c, typed)
    commit_ms = tune_commit_ms(db) if probe else None
    disk, why = tune_disk_guess(m, commit_ms)
    if typed.get('disk') in ('ssd', 'hdd') and typed['disk'] != disk:
        disk, why = typed['disk'], 'chosen'
    m['disk'], m['why'], m['commit_ms'] = disk, why, commit_ms
    out = {'engine': db.engine, 'words': ENGINE_WORDS.get(db.engine), 'where': db.where(),
           'version': str(db.version() or '').split(' on ')[0].split(',')[0],
           'size': int(db.size() or 0), 'machine': m, 'facts': m,
           'restart': tune_restart_ready(store), 'last': tune_last(store), 'rows': [],
           'items': []}
    try:
        if db.engine == 'postgres':
            out['connections'] = int(db.value('SHOW max_connections') or 0)
        else:
            r = db.row("SHOW GLOBAL VARIABLES LIKE 'max_connections'")
            out['connections'] = int(list(r.values())[1]) if r else 0
    except Exception:                                   # noqa: BLE001
        pass
    if not m.get('ram_gb') or not m.get('cpus'):
        out['need_facts'] = True
        return out
    plan = tune_plan(db.engine, m)
    now = tune_current(db, plan.keys())
    pending = set(tune_pending(db))
    last = out['last'] or {}
    mine = last.get('engine') == db.engine and not last.get('undone') \
        and last.get('where') == db.where()
    put = (last.get('set') or {}) if mine else {}
    rows = []
    for n, (v, why_, rs) in plan.items():
        same = tune_same(db.engine, now.get(n, ''), v)
        row = {'name': n, 'now': now.get(n, ''), 'want': v, 'why': why_, 'restart': rs,
               'takes': 'at the next start' if rs else 'at once', 'same': same,
               'change': not same, 'pending': n in pending}
        if n in pending and n in put and tune_same(db.engine, put[n], v):
            row.update(change=False, waiting=True)
        rows.append(row)
    out['rows'] = out['items'] = rows
    if db.engine == 'mariadb':
        out['snippet'] = out['cnf'] = (
            '# Written by ai %s for this machine, as zz-ai-tuning.cnf in /etc/my.cnf.d/\n'
            '# (or /etc/mysql/mariadb.conf.d/) so that the settings outlast a restart.\n'
            '[mariadb]\n' % __version__) + ''.join('%s = %s\n' % (r['name'], r['want'])
                                                    for r in rows)
    return out


def tune_apply(store, typed, admin_user, admin_password, by):
    plan = tune_plan_for(store, typed, probe=False)
    if plan.get('need_facts'):
        raise ValueError('say what the machine has first: its memory and its processors')
    db = tune_connect(store, admin_user, admin_password)
    done, later, failed = [], [], []
    before = json.loads(store.get_meta('tune_before:' + node_name()) or '{}')
    try:
        for r in plan['rows']:
            if not r['change']:
                continue
            before.setdefault(r['name'], r['now'])
            try:
                if plan['engine'] == 'postgres':
                    db.run("ALTER SYSTEM SET %s = '%s'" % (r['name'], r['want'].replace("'", '')))
                    (later if r['restart'] else done).append(r['name'])
                else:
                    if r['restart']:
                        later.append(r['name'])
                        continue
                    db.run('SET GLOBAL %s = %s' % (r['name'], r['want'] if r['want'].isdigit()
                                                  else "'%s'" % r['want']))
                    done.append(r['name'])
            except Exception as e:
                failed.append('%s: %s' % (r['name'], str(e).split('\n')[0][:160]))
        if plan['engine'] == 'postgres' and (done or later):
            db.run('SELECT pg_reload_conf()')
    finally:
        if db is not store.db:
            db.close()
    store.set_meta('tune_before:' + node_name(), json.dumps(before))
    if done or later:
        store.set_meta('tune_last:' + node_name(), json.dumps({
            'engine': plan['engine'], 'where': store.db.where(), 'at': time.time(), 'by': by,
            'set': {r['name']: r['want'] for r in plan['rows'] if r['name'] in done + later},
            'undone': 0}))
    store.add_event('settings', 'the database server was tuned for its machine by %s: %s'
                    % (by, ', '.join(done + later) or 'nothing'), 'warn', who=by)
    plan2 = tune_plan_for(store, typed, probe=False)
    plan2.update({'done': done, 'later': later, 'failed': failed})
    return plan2


TUNE_RESTART_MARK = CONFIG_FILE.parent / 'may-restart-database'


def tune_restart_unit():
    """The postgresql service on this machine, as systemd knows it, or ''."""
    try:
        said = subprocess.run(['systemctl', 'list-units', '--type=service', '--all', '--plain',
                               '--no-legend', '--no-pager', 'postgresql*'],
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ''
    found = []
    for line in said.stdout.splitlines():
        f = line.split()
        if len(f) >= 3 and f[2] == 'active' and \
                re.match(r'^postgresql(-\d+)?(@[\w.-]+)?\.service\Z', f[0]):
            found.append(f[0])
    return found[0] if len(found) == 1 else ''


def tune_restart_ready(store):
    db = store.db
    if db.engine != 'postgres':
        return {'may': False, 'unit': ''}
    host = str(CONFIG.get('db_host') or '').lower()
    if host not in ('', 'localhost', '127.0.0.1', '::1', socket.gethostname().lower()):
        return {'may': False, 'unit': 'postgresql',
                'why': 'PostgreSQL runs on another machine, which this program cannot restart'}
    unit = tune_restart_unit()
    if not unit:
        return {'may': False, 'unit': 'postgresql',
                'why': 'no single running postgresql service was found on this machine'}
    if not TUNE_RESTART_MARK.exists():
        return {'may': False, 'unit': unit,
                'why': 'install.sh has not let this program restart it (run install.sh --upgrade '
                       'without --no-db-restart)'}
    return {'may': True, 'unit': unit, 'why': ''}


def tune_restart(store, by):
    """PostgreSQL on this machine started again, for the settings that take
    only at a start - through systemd, where install.sh let this account do
    that - and waited for."""
    db = store.db
    ready = tune_restart_ready(store)
    if db.engine != 'postgres' or not ready['unit']:
        raise ValueError('no database server is running as a service on this machine')
    unit = ready['unit']
    if not TUNE_RESTART_MARK.exists():
        raise ValueError('this program may not restart %s: run  systemctl restart %s  as root'
                         % (unit, unit))
    waiting = tune_pending(db)
    if not waiting:
        raise ValueError('nothing waits for a restart')
    try:
        if str(db.value('SHOW huge_pages')).lower() == 'on':
            raise ValueError('huge_pages is on, and a start needs enough of them for the new '
                             'shared_buffers: check vm.nr_hugepages, then run  systemctl '
                             'restart %s  as root' % unit)
    except ValueError:
        raise
    except Exception:                                   # noqa: BLE001
        pass
    if 'shared_buffers' in waiting:
        try:
            want = int(db.value("SELECT pg_size_bytes(setting) FROM pg_file_settings WHERE "
                                "name = 'shared_buffers' AND applied = false ORDER BY seqno "
                                "DESC LIMIT 1") or 0)
        except Exception:                               # noqa: BLE001
            want = 0
        try:
            want = want or 0
            running = int(db.value("SELECT setting::bigint * 8192 FROM pg_settings WHERE "
                                   "name = 'shared_buffers'") or 0)
            avail = tune_machine({}, {}).get('avail') or 0
        except Exception:                               # noqa: BLE001
            running = avail = 0
        if want and avail and want - running > avail - 512 * 1048576:
            raise ValueError('the machine has %d MB free now, too little for shared_buffers of '
                             '%d MB - restarted now, PostgreSQL might not start. Free some '
                             'memory, or put back as it was' % (avail // 1048576,
                                                                 want // 1048576))
    began = time.time()
    try:
        said = subprocess.run(['systemctl', '--no-ask-password', '--no-block', 'restart', unit],
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as e:
        raise ValueError('systemctl: %s' % str(e)[:160])
    if said.returncode != 0:
        raise ValueError('%s was not restarted: %s - run  systemctl restart %s  as root'
                         % (unit, (said.stderr or said.stdout).strip()[:160], unit))
    store.add_event('settings', '%s restarted %s for the settings waiting for it: %s'
                    % (by, unit, ', '.join(waiting)), 'warn', who=by)
    time.sleep(2)
    back = False
    while time.time() < began + 62:
        try:
            state = subprocess.run(['systemctl', 'is-failed', unit], capture_output=True,
                                   text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            state = ''
        if state == 'failed':
            raise ValueError('%s did not start again - see  journalctl -u %s ; if it does not '
                             'start: as root, take the shared_buffers line out of '
                             'postgresql.auto.conf and run  systemctl start %s'
                             % (unit, unit, unit))
        try:
            started = float(db.value('SELECT extract(epoch from pg_postmaster_start_time())'))
            if started >= began - 1:
                back = True
                break
        except Exception:                               # noqa: BLE001
            pass
        time.sleep(1)
    if not back:
        raise ValueError('%s was asked to restart and has not answered yet - look again in a '
                         'minute' % unit)
    left = tune_pending(db)
    return {'unit': unit, 'waiting': waiting, 'still': left,
            'message': '%s started again%s' % (unit, '; still waiting: ' + ', '.join(left)
                                                if left else ': every setting is in effect')}


def tune_undo(store, admin_user, admin_password, by):
    before = json.loads(store.get_meta('tune_before:' + node_name()) or '{}')
    if not before:
        raise ValueError('nothing was changed here, so there is nothing to put back')
    db = tune_connect(store, admin_user, admin_password)
    done, failed = [], []
    try:
        for n, v in before.items():
            try:
                if store.db.engine == 'postgres':
                    db.run('ALTER SYSTEM RESET %s' % n)
                else:
                    db.run('SET GLOBAL %s = %s' % (n, v if str(v).isdigit() else "'%s'" % v))
                done.append(n)
            except Exception as e:
                failed.append('%s: %s' % (n, str(e).split('\n')[0][:160]))
        if store.db.engine == 'postgres':
            db.run('SELECT pg_reload_conf()')
    finally:
        if db is not store.db:
            db.close()
    store.set_meta('tune_before:' + node_name(), '')
    last = tune_last(store) or {}
    if last:
        last.update(undone=time.time(), undone_by=by)
        store.set_meta('tune_last:' + node_name(), json.dumps(last))
    store.add_event('settings', 'the database server’s settings were put back by %s: %s'
                    % (by, ', '.join(done)), 'warn', who=by)
    return {'done': done, 'failed': failed}

# ---------------------------------------------------------------------------
# The files kept beside the database, the disk under it, and putting one back
# ---------------------------------------------------------------------------
# As on isemon (1.10.160 on): two kinds of file are kept.
#
#   A *copy* is made by this program: every row of every table, written as a
#   portable file, which goes back into any of the three engines. That is
#   what carries an installation from the file to a server and back.
#
#   A *dump* is made by the engine's own program - pg_dump, mariadb-dump, or
#   for the file SQLite's own backup, which is the file. It is a fraction of
#   the size, the server's own tools read it, and it goes back into the
#   engine it came off.
#
# Every one of either kind has the key that opens the tokens beside it, in a
# file of its own, because one without the other is nothing.

DUMP_DIR = STATE_DIR / 'dumps'
DUMP_SUFFIX = {'sqlite': '.db', 'mariadb': '.sql.gz', 'postgres': '.pgc', 'copy': '.json.gz'}
DUMP_WORDS = {'sqlite': 'a copy of the file', 'mariadb': 'a MariaDB dump',
              'postgres': 'a PostgreSQL dump', 'copy': 'a portable copy'}
DUMP_TOOLS = {'sqlite': (),
              'mariadb': (('making one', ('mariadb-dump', 'mysqldump')),
                          ('putting one back', ('mariadb', 'mysql'))),
              'postgres': (('making one', ('pg_dump',)),
                           ('putting one back', ('pg_restore',)))}
# The names are the distribution's: Debian and Ubuntu call them otherwise.
_APT = bool(shutil.which('apt-get')) and not shutil.which('dnf')
DUMP_INSTALL = ({'mariadb': 'apt install mariadb-client (it is the client, not the server)',
                 'postgres': 'apt install postgresql-client (it is the client, not the server)'} if _APT else
                {'mariadb': 'dnf install mariadb (it is the client, not the server)',
                 'postgres': 'dnf install postgresql (it is the client, not the server)'})
DRIVERS = {'mariadb': ('pymysql', 'python3-pymysql' if _APT else 'python3-PyMySQL'),
           'postgres': ('psycopg2', 'python3-psycopg2')}
DUMP_NAME_RE = re.compile(r'^ai-(sqlite|mariadb|postgres|copy)?-?(\d{8}-\d{6})(?:-([a-z-]+))?'
                     r'(\.db|\.sql\.gz|\.pgc|\.json\.gz)$')


def drivers_state():
    """Whether the driver for each server engine is installed - said before
    somebody types an address rather than after they press a button."""
    out = {}
    for engine, (module, package) in DRIVERS.items():
        try:
            __import__(module)
            out[engine] = {'ready': True, 'package': package}
        except Exception as e:                          # noqa: BLE001
            out[engine] = {'ready': False, 'package': package,
                           'says': 'the driver %s is not installed (%s)' % (module, e)}
    return out


def dump_info(engine):
    """Which program tonight's dump will be made with, and whether it is here."""
    out = {'engine': engine, 'words': DUMP_WORDS.get(engine, engine),
           'suffix': DUMP_SUFFIX.get(engine, ''), 'where': str(DUMP_DIR),
           'install': DUMP_INSTALL.get(engine, ''), 'ready': True, 'why': ''}
    for what, names in DUMP_TOOLS.get(engine, ()):
        if not any(shutil.which(n) for n in names):
            out.update(ready=False, why='%s is not on this machine, so a dump cannot be %s'
                       % (names[0], 'made' if what == 'making one' else 'put back'))
            break
    return out


def _tool(names):
    for one in names:
        got = shutil.which(one)
        if got:
            return got
    raise ValueError('%s is not on this machine' % names[0])


def _db_conf():
    return {k: CONFIG.get(k) for k in DB_KEYS}


def safe_db_name(c):
    """The database's name, as it may stand on a command line: never one
    that reads as an option (1.0.33)."""
    name = str(c.get('db_name') or '')
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]{0,62}\Z', name):
        raise DbError('the database name %r is not letters, digits and _' % name[:60])
    return name


def _my_cnf(c):
    """A defaults file holding the password and nothing else, 0600, gone the
    moment the program has finished with it: `--password=` on a command line
    is readable by everybody on the machine while it runs."""
    handle, name = tempfile.mkstemp(prefix='ai-my-', suffix='.cnf')
    os.close(handle)
    os.chmod(name, 0o600)
    with open(name, 'w') as f:
        said = str(c.get('db_password') or '')
        if any(ord(ch) < 32 for ch in said):
            raise DbError('the database password has a line break or another control '
                          'character in it')
        f.write('[client]\npassword="%s"\n' % said.replace('\\', '\\\\').replace('"', '\\"'))
    return name


def _my_args(c, cnf):
    out = ['--defaults-extra-file=%s' % cnf,
           '--host=%s' % (str(c.get('db_host') or '127.0.0.1').strip('[]')),
           '--port=%d' % int(c.get('db_port') or 3306),
           '--user=%s' % (c.get('db_user') or '')]
    # The dump and restore tools encrypted as the daemon's own connection is
    # (1.0.36).
    mode = str((c.get('db_tls') if 'db_tls' in c else CONFIG.get('db_tls')) or '')
    ca = str((c.get('db_tls_ca') if 'db_tls_ca' in c else CONFIG.get('db_tls_ca')) or '')
    if mode:
        out.append('--ssl')
        if mode in ('verify-ca', 'verify-full'):
            out.append('--ssl-verify-server-cert')
        if ca:
            out.append('--ssl-ca=%s' % ca)
    return out


def _pg_args(c):
    return ['--host=%s' % (str(c.get('db_host') or '127.0.0.1').strip('[]')),
            '--port=%d' % int(c.get('db_port') or 5432),
            '--username=%s' % (c.get('db_user') or ''), '--no-password']


def _pg_env(c):
    env = dict(os.environ)
    env['PGPASSWORD'] = str(c.get('db_password') or '')
    env['PGCONNECT_TIMEOUT'] = str(int(c.get('db_timeout_s') or 10))
    mode = str((c.get('db_tls') if 'db_tls' in c else CONFIG.get('db_tls')) or '')
    ca = str((c.get('db_tls_ca') if 'db_tls_ca' in c else CONFIG.get('db_tls_ca')) or '')
    if mode:
        env['PGSSLMODE'] = mode
        if ca:
            env['PGSSLROOTCERT'] = ca
    return env


def _run(args, words, stdin=None, stdout=None, env=None, seconds=3600):
    try:
        got = subprocess.run(args, stdin=stdin, stdout=stdout if stdout is not None
                             else subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                             timeout=seconds)
    except subprocess.TimeoutExpired:
        raise ValueError('%s took longer than %d s and was stopped' % (words, seconds))
    if got.returncode != 0:
        said = (got.stderr or b'').decode('utf-8', 'replace').strip().split('\n')
        raise ValueError('%s failed: %s' % (words, (said[-1] if said else
                                                     'exit %d' % got.returncode)[:300]))
    return got.stdout


def _stamp():
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def _key_beside(path):
    p = str(path)
    for suf in ('.json.gz', '.sql.gz', '.pgc', '.db'):
        if p.endswith(suf):
            return Path(p[:-len(suf)] + '.key')
    return Path(p + '.key')


def _write_key_beside(path):
    key = sealing_key()
    if key:
        write_replacing(_key_beside(path), key.hex() + '\n', 0o600)


def _kind_of_name(name):
    for kind, suf in (('copy', '.json.gz'), ('mariadb', '.sql.gz'), ('postgres', '.pgc'),
                      ('sqlite', '.db')):
        if name.endswith(suf):
            return kind
    return ''


def _prune(folder, pattern, keep):
    files = sorted((f for f in folder.glob(pattern) if DUMP_NAME_RE.match(f.name)),
                   key=lambda f: f.stat().st_mtime)
    for old in files[:-keep] if keep > 0 and len(files) > keep else []:
        for f in (old, _key_beside(old)):
            try:
                f.unlink()
            except OSError:
                pass


def copy_engine(path):
    """Which engine a copy was taken off: its first line says."""
    import gzip
    try:
        with gzip.open(str(path), 'rt', encoding='utf-8') as f:
            return json.loads(f.readline() or '{}').get('engine') or ''
    except Exception:                                   # noqa: BLE001
        return ''


def kept_copies():
    """The copies this program made, newest first."""
    if not BACKUP_DIR.is_dir():
        return []
    out = []
    for f in sorted(list(BACKUP_DIR.glob('ai-*.json.gz')) + [],
                   key=lambda x: x.stat().st_mtime,
                    reverse=True):
        st = f.stat()
        out.append({'name': f.name, 'bytes': st.st_size, 'size': st.st_size, 'at': st.st_mtime,
                    'from': copy_engine(f), 'key': _key_beside(f).exists(), 'kind': 'copy'})
    return out


def kept_dumps(engine):
    """The dumps the engine made of itself, newest first."""
    if not DUMP_DIR.is_dir():
        return []
    out = []
    for f in sorted(DUMP_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        m = DUMP_NAME_RE.match(f.name)
        if not m:
            continue
        kind = _kind_of_name(f.name)
        came = m.group(1) or ''
        if kind == 'copy':
            came = copy_engine(f) or came
        st = f.stat()
        out.append({'name': f.name, 'bytes': st.st_size, 'at': st.st_mtime, 'kind': kind,
                    'from': came if kind != 'copy' else came,
                    'mine': kind == 'copy' or kind == engine,
                    'key': _key_beside(f).exists()})
    return out


def make_dump(store, label='daily', folder=None):
    """A dump of the database in use by its own engine's program - or, where
    that program is not on this machine, a portable copy in its place."""
    engine = store.db.engine
    folder = Path(folder) if folder else DUMP_DIR
    folder.mkdir(parents=True, exist_ok=True)
    backup_room_check(store, folder)            # never the disk filled (1.0.149)
    info = dump_info(engine)
    kind = engine if info['ready'] else 'copy'
    name = 'ai-%s-%s-%s%s' % (engine if kind != 'copy' else 'copy', _stamp(),
                              re.sub(r'[^a-z-]', '', label) or 'daily', DUMP_SUFFIX[kind])
    target = folder / name
    part = Path(str(target) + '.part')
    c = _db_conf()
    try:
        if kind == 'copy':
            dump_tables(store.db, part)
        elif engine == 'sqlite':
            # SQLite's own backup: a consistent copy of the file even while the
            # daemon writes to it.
            src = sqlite3.connect(str(store.db.path))
            dst = sqlite3.connect(str(part))
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
        elif engine == 'mariadb':
            import gzip
            tool = _tool(('mariadb-dump', 'mysqldump'))
            cnf = _my_cnf(c)
            try:
                raw = Path(str(part) + '.raw')
                with open(str(raw), 'wb') as out:
                    _run([tool] + _my_args(c, cnf) + [
                        '--single-transaction', '--quick', '--skip-lock-tables',
                        '--default-character-set=utf8mb4', '--no-tablespaces',
                        '--add-drop-table', '--skip-comments', safe_db_name(c)],
                        'mariadb-dump', stdout=out)
                with open(str(raw), 'rb') as src, gzip.open(str(part), 'wb', 6) as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                raw.unlink()
            finally:
                os.unlink(cnf)
        else:
            tool = _tool(('pg_dump',))
            _run([tool] + _pg_args(c) + ['--format=custom', '--compress=6', '--no-owner',
                                         '--no-privileges', '--file=%s' % part,
                                         '--dbname=%s' % safe_db_name(c)],
                 'pg_dump', env=_pg_env(c))
        os.chmod(str(part), 0o640)
        part.replace(target)
    finally:
        for left in (part, Path(str(part) + '.raw')):
            if left.exists():
                try:
                    left.unlink()
                except OSError:
                    pass
    _write_key_beside(target)
    if folder == DUMP_DIR:
        _prune(DUMP_DIR, 'ai-*', int(CONFIG.get('backup_keep') or 14))
    store.add_event('backups', 'made %s (%s): %s' % (
        DUMP_WORDS[kind], {'daily': 'every night', 'by-hand': 'by hand',
                           'download': 'to be downloaded'}.get(label, label), target.name))
    return target


# ---- what is in a file, without putting any of it back ------------------------
def _magic(path):
    with open(str(path), 'rb') as f:
        return f.read(16)


def _peek_copy(path):
    import gzip
    counts, admins, tables, table = {}, 0, 0, None
    with gzip.open(str(path), 'rt', encoding='utf-8') as f:
        head = json.loads(f.readline() or '{}')
        if 'ai' not in head:
            return None, 'that is not a copy made by ai'
        for line in f:
            got = json.loads(line)
            if set(got.keys()) == {'table'}:
                table = got['table']
                tables += 1
                counts.setdefault(table, 0)
                continue
            if table:
                counts[table] += 1
                if table == 'users' and got.get('role') == 'admin' \
                        and not got.get('disabled'):
                    admins += 1
    return {'kind': 'copy', 'from': head.get('engine') or '', 'version': head.get('ai'),
            'made': head.get('made'), 'counts': counts, 'admins': admins, 'tables': tables,
            'key': bool(head.get('key')), 'machine': head.get('machine')}, ''


def _peek_sqlite(path):
    try:
        con = sqlite3.connect('file:%s?mode=ro' % path, uri=True)
    except sqlite3.Error as e:
        return None, 'that file could not be opened: %s' % e
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        if 'users' not in names or 'settings' not in names:
            return None, 'that is not a database of ai: it has no accounts and no settings'
        counts = {t: con.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]
                  for t in DB_TABLES if t in names}
        admins = con.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND "
                             "COALESCE(disabled, 0) = 0").fetchone()[0]
    except sqlite3.Error as e:
        return None, 'that database could not be read: %s' % e
    finally:
        con.close()
    return {'kind': 'sqlite', 'counts': counts, 'admins': admins,
            'tables': len([t for t in DB_TABLES if t in names])}, ''


def _peek_mariadb(path):
    import gzip
    tables, admins, users, in_users = set(), 0, 0, False
    with gzip.open(str(path), 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith('CREATE TABLE'):
                got = re.search(r'CREATE TABLE `([^`]+)`', line)
                if got:
                    tables.add(got.group(1))
                continue
            first = line.startswith('INSERT INTO `users`')
            if first:
                in_users = True
            elif in_users and not line.startswith('('):
                in_users = False
            if in_users:
                admins += line.count(",'admin',")
                rest = line.split('VALUES', 1)[-1] if first else line
                users += rest.count('),(') + (1 if '(' in rest else 0)
                if line.rstrip().endswith(';'):
                    in_users = False
    if 'users' not in tables or 'settings' not in tables:
        return None, 'that dump is not one of ai - it has no accounts and no settings'
    return {'kind': 'mariadb', 'counts': {'users': users}, 'admins': admins,
            'tables': len(tables)}, ''


def _peek_postgres(path):
    tool = shutil.which('pg_restore')
    if not tool:
        return None, ('pg_restore is not on this machine, so what is in that dump cannot be '
                      'read: %s' % DUMP_INSTALL['postgres'])
    listed = _run([tool, '--list', str(path)], 'pg_restore --list', seconds=300)
    tables = set(re.findall(r'TABLE DATA\s+\S+\s+(\S+)', listed.decode('utf-8', 'replace')))
    if 'users' not in tables or 'settings' not in tables:
        return None, 'that dump is not one of ai - it has no accounts and no settings'
    rows = _run([tool, '--data-only', '--table=users', '--file=-', str(path)],
                'pg_restore', seconds=300).decode('utf-8', 'replace')
    users = admins = 0
    inside = False
    for line in rows.split('\n'):
        if line.startswith('COPY '):
            inside = True
            continue
        if inside:
            if line == '\\.':
                break
            users += 1
            if '\tadmin\t' in line:
                admins += 1
    return {'kind': 'postgres', 'counts': {'users': users}, 'admins': admins,
            'tables': len(tables)}, ''


def db_file_peek(path, engine, need_admin=True):
    """What is in a copy or a dump, and whether it may be put back here."""
    head = _magic(path)
    try:
        if head.startswith(b'SQLite format 3'):
            said, why = _peek_sqlite(path)
        elif head.startswith(b'PGDMP'):
            said, why = _peek_postgres(path)
        elif head[:2] == b'\x1f\x8b':
            import gzip
            with gzip.open(str(path), 'rb') as f:
                first = f.read(64)
            if first.startswith(b'{'):
                said, why = _peek_copy(path)
            else:
                said, why = _peek_mariadb(path)
        else:
            return None, 'that is neither a copy nor a dump made by ai'
    except Exception as e:                              # noqa: BLE001
        return None, 'that file could not be read: %s' % str(e).split('\n')[0][:200]
    if said is None:
        return None, why
    kind = said['kind']
    if kind not in ('copy', 'sqlite') and kind != engine:
        return None, ('that is %s, and this installation is on %s: a dump goes back only into '
                      'the engine it came off. Use a copy - a copy goes into any of the three.'
                      % (DUMP_WORDS[kind], ENGINE_WORDS.get(engine, engine)))
    if not said.get('admins'):
        # On the command line root makes one afterwards (1.0.62): a copy of
        # a server set up there alone was refused for good.
        if need_admin:
            return None, ('there is no administrator who can sign in in that file: putting '
                          'it back would lock everybody out of these pages (on the command line '
                          'it can be put back, and an account made after it)')
        said['no_admin'] = True
    said['bytes'] = Path(path).stat().st_size
    return said, ''


def _sqlite_to_copy(path, out):
    """A SQLite file of ours, as a copy: so that it goes back into whatever
    engine is in use, by the same road as every copy."""
    src = Db('sqlite', path=path)
    try:
        dump_tables(src, out, [t for t in DB_TABLES if t in src.tables()])
    finally:
        src.close()
    return out


def db_file_restore(store, path, by, key_file=None, from_name='', need_admin=True):
    """Put a copy or a dump back over everything. A copy of what is replaced
    is made first and kept with the others."""
    engine = store.db.engine
    said, why = db_file_peek(path, engine, need_admin)
    if said is None:
        raise ValueError(why)
    kind = said['kind']
    # A kept copy is read from a copy of its own (1.0.44): the safety copy
    # below rotates the kept ones, and the oldest - the one being put back -
    # would be the one it took away.
    held = []
    try:
        if Path(path).resolve().parent == Path(BACKUP_DIR).resolve():
            ext = ''.join(Path(path).suffixes[-2:]) if str(path).endswith('.gz') else Path(path).suffix
            fd, tmpname = tempfile.mkstemp(prefix='ai-putback-', suffix=ext, dir=str(STATE_DIR))
            os.close(fd)
            shutil.copyfile(str(path), tmpname)
            os.chmod(tmpname, 0o600)
            held.append(Path(tmpname))
            kf = Path(key_file) if key_file else None
            if kf and kf.exists():
                fd, kname = tempfile.mkstemp(prefix='ai-putback-', suffix='.key', dir=str(STATE_DIR))
                os.close(fd)
                shutil.copyfile(str(kf), kname)
                os.chmod(kname, 0o600)
                held.append(Path(kname))
                key_file = kname
            path = tmpname
        return _db_file_restore(store, path, by, key_file, from_name, kind)
    finally:
        for x in held:
            try:
                x.unlink()
            except OSError:
                pass


def _db_file_restore(store, path, by, key_file, from_name, kind):
    # The key that opens its secrets: beside a kept file, or inside a copy
    # that was downloaded with it.
    key_hex = ''
    if key_file and Path(key_file).exists():
        key_hex = Path(key_file).read_text().strip()
    elif kind == 'copy':
        import gzip
        with gzip.open(str(path), 'rt', encoding='utf-8') as f:
            key_hex = str(json.loads(f.readline() or '{}').get('key') or '')
    safety = make_backup(store, 'before putting %s back, by %s' % (from_name or 'a file', by))
    # Who is signed in stays as it is now (1.0.147): the copy's sign-ins came
    # back with it - one signed out since, or of a password changed since,
    # opened the pages again until it ran out.
    try:
        live_sessions = store.db.rows('SELECT * FROM sessions')
    except Exception:                                   # noqa: BLE001
        live_sessions = None
    c = _db_conf()
    if kind == 'copy':
        load_tables(store.db, path)
    elif kind == 'sqlite':
        fd, tmp = tempfile.mkstemp(prefix='ai-restore-', suffix='.json.gz', dir=str(STATE_DIR))
        os.close(fd)                    # not left open, one each time (1.0.139)
        tmp = Path(tmp)
        try:
            _sqlite_to_copy(path, tmp)
            load_tables(store.db, tmp)
        finally:
            tmp.unlink()
    elif kind == 'mariadb':
        import gzip
        tool = _tool(('mariadb', 'mysql'))
        with gzip.open(str(path), 'rb') as sent:
            for n, line in enumerate(sent):
                if line[:1] == b'\\' or line[:7].lower() == b'system ':
                    raise ValueError('line %d of the dump is a client command, not SQL. '
                                     'A dump this program made has none.' % (n + 1))
        cnf = _my_cnf(c)
        # The client is given the SQL itself: a gzip reader has no file
        # descriptor of its own to hand a program, so it is unpacked first.
        fd, raw = tempfile.mkstemp(prefix='ai-sql-', dir=str(STATE_DIR))
        os.close(fd)
        raw = Path(raw)
        try:
            with gzip.open(str(path), 'rb') as src, open(str(raw), 'wb') as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            with open(str(raw), 'rb') as sent:
                _run([tool] + _my_args(c, cnf) + ['--default-character-set=utf8mb4',
                                                  '--local-infile=0', '--binary-mode',
                                                  safe_db_name(c)],
                     'the MariaDB client', stdin=sent)
        finally:
            os.unlink(cnf)
            try:
                raw.unlink()
            except OSError:
                pass
    else:
        tool = _tool(('pg_restore',))
        _run([tool] + _pg_args(c) + ['--single-transaction', '--clean', '--if-exists',
                                     '--no-owner', '--no-privileges',
                                     '--dbname=%s' % safe_db_name(c), str(path)],
             'pg_restore', env=_pg_env(c))
    store.db.make_tables()
    if live_sessions is not None:
        try:
            store.db.run('DELETE FROM sessions')
            have = set(c.lower() for c in store.db.columns('sessions'))
            for r in live_sessions:
                row = {k: v for k, v in dict(r).items() if k.lower() in have}
                keys = sorted(row)
                store.db.insert_many('sessions', keys, [[row[k] for k in keys]])
        except Exception as e:                          # noqa: BLE001
            log('the sign-ins could not be kept as they were: %s' % e, 'warn')
    key_said = 'the key of its secrets stays as it was'
    if re.match(r'^[0-9a-f]{64}\Z', key_hex):
        now = sealing_key()
        if not now or now.hex() != key_hex:
            write_replacing(sealing_key_path(), key_hex + '\n', 0o600)
            _KEY_CACHE.clear()
            key_said = 'the key of its secrets came with it and is in use now'
    else:
        key_said = ('no key came with it: the secrets in it (the mail server\'s password, the apps of the '
                    'second step, the key of the certificate) open only if it was made here')
    config_rebuild(store)
    store.add_event('backups', '%s put the database back from %s (%s); what it replaced is in %s'
                    % (by, from_name or 'a file', DUMP_WORDS.get(kind, kind), safety.name),
                    'warn', who=by)
    return {'safety': safety.name, 'kind': kind, 'key': key_said}


# ---- the disk under it ----------------------------------------------------------
def note_size(store):
    """The size of the database, once a day, for how fast it grows."""
    try:
        sizes = json.loads(store.get_meta('db_sizes:' + node_name()) or '{}')
    except ValueError:
        sizes = {}
    today = datetime.now().strftime('%Y-%m-%d')
    if sizes.get('engine') != store.db.engine:
        sizes = {'engine': store.db.engine, 'days': {}}
    if today not in sizes['days']:
        sizes['days'][today] = int(store.db.size() or 0)
        for old in sorted(sizes['days'])[:-60]:
            del sizes['days'][old]
        store.set_meta('db_sizes:' + node_name(), json.dumps(sizes))
    return sizes


def db_growth(store):
    days = note_size(store).get('days', {})
    edge = (datetime.now().timestamp() - 15 * 86400)
    seen = sorted((d, b) for d, b in days.items()
                  if datetime.strptime(d, '%Y-%m-%d').timestamp() >= edge)
    if len(seen) < 2:
        return {'a_day': 0, 'over_days': 0}
    (d0, b0), (d1, b1) = seen[0], seen[-1]
    span = max(1, (datetime.strptime(d1, '%Y-%m-%d') - datetime.strptime(d0, '%Y-%m-%d')).days)
    return {'a_day': max(0, int((b1 - b0) / span)), 'over_days': span}


def _folder_bytes(folder):
    total = 0
    if Path(folder).is_dir():
        for f in Path(folder).iterdir():
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return total


def db_disk(store):
    db = store.db
    where = db.path.parent if db.engine == 'sqlite' else STATE_DIR
    out = {'where': str(where), 'total': 0, 'free': 0, 'share': 0, 'days_left': None,
           'holds': 'the database itself, its copies and its dumps' if db.engine == 'sqlite'
           else 'the copies and the dumps - the database itself is on the server'}
    try:
        u = shutil.disk_usage(str(where))
        out.update(total=u.total, free=u.free,
                   share=round(100.0 * (u.total - u.free) / u.total) if u.total else 0)
    except OSError:
        pass
    grew = db_growth(store)
    if grew['a_day'] and out['free']:
        out['days_left'] = int(out['free'] / grew['a_day'])
    parts = []
    if db.engine == 'sqlite':
        for suffix, what in (('', 'the database'), ('-wal', 'what is written, not yet folded in'),
                             ('-shm', 'the index of that')):
            f = Path(str(db.path) + suffix)
            if f.exists():
                parts.append({'name': f.name, 'what': what, 'bytes': f.stat().st_size})
    else:
        parts.append({'name': db.where(), 'what': 'the database, on the server',
                      'bytes': int(db.size() or 0)})
    parts.append({'name': str(BACKUP_DIR), 'what': 'the copies', 'bytes':
                  _folder_bytes(BACKUP_DIR)})
    parts.append({'name': str(DUMP_DIR), 'what': 'the dumps', 'bytes': _folder_bytes(DUMP_DIR)})
    return out, grew, parts


def db_cache(store):
    """The server's own cache, where it is left as installed and the database
    has outgrown it."""
    db = store.db
    if db.engine == 'sqlite':
        return None
    try:
        if db.engine == 'postgres':
            setting = 'shared_buffers'
            cache = int(db.value("SELECT setting::bigint * 8192 FROM pg_settings "
                                 "WHERE name = 'shared_buffers'") or 0)
        else:
            setting = 'innodb_buffer_pool_size'
            r = db.row("SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size'")
            cache = int(list(r.values())[1]) if r else 0
    except Exception:                                   # noqa: BLE001
        return None
    size = int(db.size() or 0)
    ram = 0
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    ram = int(line.split()[1]) * 1024
    except OSError:
        pass
    return {'engine': ENGINE_WORDS.get(db.engine), 'setting': setting, 'cache': cache,
            'size': size, 'ram': ram, 'low': bool(cache and size > cache)}


# ---- erasing what was collected -----------------------------------------------
# (key, the table, what of it - a WHERE, the name, what it is)
ERASABLE = [
    ('events', 'events', '', 'the event log',
     'what this program noted about itself: sign-ins, terminals started and ended, changes, copies, '
     'starts and stops.'),
    ('mailq', 'meta', "k LIKE 'mailq:%' OR k LIKE 'mailb:%'", 'the outgoing mail',
     'every mail sent or waiting, where it went and what the other side said. One still waiting is not '
     'sent any more.'),
    ('ended', 'terms', 'ended IS NOT NULL', 'the ended terminals',
     'the list of terminals that have ended, with their last screens. Running ones are not touched.'),
]


def db_erasable(store):
    groups = []
    for key, table, where, name, says in ERASABLE:
        groups.append({'key': key, 'name': name, 'says': says,
                       'rows': int(store.db.value('SELECT COUNT(*) FROM %s%s' % (
                           table, ' WHERE k LIKE \'mailq:%%\'' if key == 'mailq'
                           else (' WHERE ' + where if where else ''))) or 0)})
    return {'groups': groups, 'bytes': int(store.db.size() or 0)}


def db_erase_job(store, groups, tidy, by):
    tables = [(t, n, w) for k, t, w, n, _ in ERASABLE if k in groups]
    if not tables:
        raise ValueError('nothing was ticked')

    def work(progress):
        progress(0, len(tables) + 2, 'making a copy first')
        copy = make_backup(store, 'before erasing, by %s' % by)
        gone = {}
        for i, (t, n, w) in enumerate(tables):
            progress(i + 1, len(tables) + 2, 'emptying %s' % n)
            gone[n] = store.db.run('DELETE FROM %s%s' % (t, ' WHERE ' + w if w else '')) if w \
                else store.db.run('DELETE FROM %s' % t)
        given = None
        if tidy:
            progress(len(tables) + 1, len(tables) + 2, 'giving the disk back')
            given = db_give_back(store, lambda *a: None)
        store.add_event('settings', '%s erased %s (a copy was made first: %s)'
                        % (by, ', '.join(n for _, n in tables), copy.name), 'warn', who=by)
        progress(len(tables) + 2, len(tables) + 2, 'done')
        return {'erased': gone, 'copy': copy.name, 'given': given}
    return db_job('erasing the collected data', work)


# ---- the server's settings: what was done, what waits for a start ---------------
def tune_state(store):
    db = store.db
    out = {'engine': db.engine, 'last': None, 'pending': [], 'lost': [],
           'restart': {'may': False, 'unit': {'postgres': 'postgresql',
                                              'mariadb': 'mariadb'}.get(db.engine, '')}}
    try:
        last = json.loads(store.get_meta('tune_last:' + node_name()) or 'null')
    except ValueError:
        last = None
    out['last'] = last
    if db.engine == 'postgres':
        try:
            out['pending'] = [r['name'] for r in db.rows(
                'SELECT name FROM pg_settings WHERE pending_restart')]
        except Exception:                               # noqa: BLE001
            pass
    elif db.engine == 'mariadb' and last and not last.get('undone') \
            and last.get('engine') == 'mariadb':
        now = tune_current(db, list((last.get('set') or {}).keys()))
        out['lost'] = [n for n, v in (last.get('set') or {}).items()
                       if not tune_same('mariadb', now.get(n, ''), v)]
    return out
# ---- a copy or a dump with the key its secrets are sealed with (otp's 1.0.123) ----------
# A copy or a dump alone opens no secret anywhere else: the key that opens them
# is a file of its own (the .key beside it, /var/lib/ai/secrets.key). Downloaded
# from the page it can now go with the key in ONE file - a plain tar holding
#   ai-db.json           what it is (the file's name, size, sha256, where made)
#   <the file>           the copy or the dump, as it is
#   secrets.key.locked   the key, locked with a passphrase given on the page
#                        (scrypt, HMAC)
# and the same file sent back to Put a copy back / Put a dump back is opened
# with that passphrase and put back with its key. The passphrase is never
# kept: lost, the key in the file is lost with it.
DBKEY_KIND = 'ai-db-key'
DBKEY_TAR_KIND = 'ai-db-with-key'
DBKEY_SUFFIX = '.with-key.tar'
DB_UPLOADS = STATE_DIR / 'db-uploads'
DB_TICKETS_DIR = STATE_DIR / 'db-downloads'
DB_TICKETS = {}
DB_TICKETS_LOCK = threading.Lock()
DBKEY_MIN_PASS = 10


def _sha256_file(path):
    h = hashlib.sha256()
    with open(str(path), 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dbkey_passphrase_checked(passphrase):
    p = str(passphrase or '')
    if len(p) < DBKEY_MIN_PASS:
        raise ValueError('a passphrase of %d characters at least - it is all that guards the '
                         'key in the file' % DBKEY_MIN_PASS)
    return p


def dbkey_bundle(src, name, passphrase, work):
    """`src` (a copy or a dump called `name`) and this machine's key, locked
    with `passphrase`, in one tar in `work`. Its path."""
    passphrase = dbkey_passphrase_checked(passphrase)
    key = sealing_key()
    if not key:
        raise ValueError('this machine has no key its secrets are sealed with')
    sha = _sha256_file(src)
    locked = bundle_lock({'key': key.hex(), 'file': name, 'sha256': sha}, passphrase,
                         kind=DBKEY_KIND)
    head = {'kind': DBKEY_TAR_KIND, 'format': 1, 'file': name,
            'bytes': Path(src).stat().st_size, 'sha256': sha, 'made': time.time(),
            'node': node_name(), 'site': CONFIG.get('site_name') or '', 'version': __version__}
    out = Path(work) / (name + DBKEY_SUFFIX)
    with tarfile.open(str(out), 'w') as tf:
        for arc, data in (('ai-db.json', json.dumps(head, indent=1).encode('utf-8')),
                          ('secrets.key.locked', json.dumps(locked).encode('utf-8'))):
            ti = tarfile.TarInfo(arc)
            ti.size = len(data)
            ti.mtime = int(time.time())
            ti.mode = 0o600
            tf.addfile(ti, io.BytesIO(data))
        ti = tf.gettarinfo(str(src), arcname=name)
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ''
        ti.mode = 0o600
        with open(str(src), 'rb') as f:
            tf.addfile(ti, f)
    os.chmod(str(out), 0o600)
    return out


def dbkey_is_bundle(path):
    """Whether `path` is a file made by dbkey_bundle (its head, not its name)."""
    try:
        if not tarfile.is_tarfile(str(path)):
            return False
        with tarfile.open(str(path), 'r:') as tf:
            m = tf.getmember('ai-db.json')
            f = tf.extractfile(m)
            head = json.loads(f.read(1 << 16).decode('utf-8')) if f else {}
        return isinstance(head, dict) and head.get('kind') == DBKEY_TAR_KIND
    except (KeyError, OSError, ValueError, tarfile.TarError):
        return False


def dbkey_open(path, work, passphrase=None):
    """The file inside it, taken out into `work`, and - with the passphrase -
    the key next to it: (file, key file or None, head)."""
    try:
        tf = tarfile.open(str(path), 'r:')
    except (OSError, tarfile.TarError) as e:
        raise ValueError('that file does not open: %s' % e)
    with tf:
        members = {}
        for m in tf.getmembers():
            # Only plain files, by plain names: nothing it says goes anywhere
            # but where it is put.
            if not m.isreg() or '/' in m.name or m.name in ('', '.', '..') or '\\' in m.name:
                raise ValueError('that file holds something ai does not put in one: %s' % m.name)
            members[m.name] = m
        try:
            head = json.loads(tf.extractfile(members['ai-db.json']).read(1 << 16).decode('utf-8'))
            locked = json.loads(tf.extractfile(members['secrets.key.locked']).read(1 << 20)
                                .decode('utf-8'))
        except (KeyError, ValueError, AttributeError):
            raise ValueError('that is not a database with its key made by ai')
        name = os.path.basename(str(head.get('file') or ''))
        if head.get('kind') != DBKEY_TAR_KIND or not DUMP_NAME_RE.match(name) or name not in members:
            raise ValueError('that is not a database with its key made by ai')
        out = Path(work) / name
        src = tf.extractfile(members[name])
        fd = os.open(str(out), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
    if _sha256_file(out) != head.get('sha256'):
        raise ValueError('the file inside is not the one it was made with (damaged on the way?)')
    keyf = None
    if passphrase is not None:
        try:
            got = bundle_open(locked, str(passphrase), kinds=(DBKEY_KIND,))
        except ValueError as e:
            if 'passphrase' in str(e):
                raise ValueError('that passphrase does not open the key in the file')
            raise
        if got.get('sha256') != head.get('sha256') or \
                not re.match(r'^[0-9a-f]{64}\Z', str(got.get('key') or '')):
            raise ValueError('the key in the file is not the one made with it')
        keyf = Path(work) / 'secrets.key'
        write_replacing(keyf, got['key'] + '\n', 0o600)
    return out, keyf, head


def dbkey_keep_upload(tmp):
    """An upload kept for an hour to be put back with its passphrase: its id."""
    DB_UPLOADS.mkdir(mode=0o700, exist_ok=True)
    now = time.time()
    for p in DB_UPLOADS.iterdir():
        try:
            if now - p.stat().st_mtime > 3600:
                p.unlink()
        except OSError:
            pass
    up = secrets.token_hex(8)
    shutil.move(str(tmp), str(DB_UPLOADS / up))
    os.chmod(str(DB_UPLOADS / up), 0o600)
    return up


def dbkey_upload(up):
    if not re.match(r'^[0-9a-f]{16}\Z', str(up or '')):
        raise ValueError('which file?')
    p = DB_UPLOADS / up
    if not p.is_file():
        raise ValueError('the file sent is not here any more (an hour has gone by?): send it again')
    return p


def dbkey_ticket_put(path, name, who):
    """A file made for a download, waiting ten minutes for the one browser
    that asked for it: its ticket."""
    now = time.time()
    with DB_TICKETS_LOCK:
        for t, v in list(DB_TICKETS.items()):
            if now - v['at'] > 600:
                shutil.rmtree(str(v['dir']), ignore_errors=True)
                DB_TICKETS.pop(t, None)
        t = secrets.token_hex(16)
        DB_TICKETS[t] = {'path': Path(path), 'name': name, 'who': who, 'at': now,
                         'dir': Path(path).parent}
    return t


def dbkey_ticket_take(t, who):
    with DB_TICKETS_LOCK:
        v = DB_TICKETS.pop(str(t or ''), None)
    if not v or v['who'] != who or time.time() - v['at'] > 600:
        if v:
            shutil.rmtree(str(v['dir']), ignore_errors=True)
        return None
    return v


# ---- Settings → The database (otp's routes, through the pages' relay) -------------------------
# What otp sends as a file straight to the browser is put where /files/get
# hands it to this administrator (DB_TICKETS_DIR, taken away within the hour);
# what the browser sends goes by /files/put into DB_UPLOADS first.
def db_nightly(store):
    """At backup_at, once a day: the engine's own dump, or a portable copy
    where its program is missing - and the size noted, for how fast it grows."""
    if not CONFIG.get('backup_daily'):
        return
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        hh, mm = (int(x) for x in str(CONFIG.get('backup_at') or '03:30').strip().split(':', 1))
    except ValueError:
        hh, mm = 3, 30
    now = datetime.now()
    if store.get_meta('backup_day') == today or (now.hour, now.minute) < (hh, mm):
        return
    store.set_meta('backup_day', today)
    try:
        make_dump(store, 'daily')
    except Exception as e:                              # noqa: BLE001
        store.add_event('backups', 'the daily dump failed: %s' % e, 'error')
    try:
        note_size(store)
    except Exception:                                   # noqa: BLE001
        pass


def db_tidy_files():
    now = time.time()
    for d in (DB_TICKETS_DIR, DB_UPLOADS):
        try:
            for p in d.iterdir():
                if now - p.stat().st_mtime > 3600:
                    shutil.rmtree(str(p), ignore_errors=True) if p.is_dir() else p.unlink()
        except OSError:
            pass


def _db_files(store):
    db = store.db
    disk, grew, parts = db_disk(store)
    return {'copies': kept_copies(), 'dumps': kept_dumps(db.engine), 'dump': dump_info(db.engine),
            'keep': int(CONFIG.get('backup_keep') or 14), 'disk': disk, 'growth': grew,
            'parts': parts, 'cache': db_cache(store), 'drivers': drivers_state(),
            'erasable': db_erasable(store), 'tune': tune_state(store),
            'backup_dir': str(BACKUP_DIR), 'dump_dir': str(DUMP_DIR), 'uploads': str(DB_UPLOADS)}


@route('GET', '/api/db', admin=True)
def api_db(c):
    st = c.daemon.store
    db = st.db
    for d in (BACKUP_DIR, DUMP_DIR, DB_UPLOADS, DB_TICKETS_DIR):
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
    db_tidy_files()
    files = _db_files(st)
    return dict(files, **{'engine': db.engine, 'words': ENGINE_WORDS.get(db.engine), 'where': db.where(),
                          'version': db.version(), 'size': db.size(), 'free': db_free_inside(db),
                          'counts': st.counts(), 'tables': db_table_sizes(db), 'backups': backups(),
                          'key': str(sealing_key_path()), 'key_there': bool(sealing_key()),
                          'config_file': str(CONFIG_FILE), 'job': job_read(), 'node': node_name(),
                          'tuned': bool(json.loads(st.get_meta('tune_before:' + node_name()) or '{}')),
                          'retain': {'retain_events_days': CONFIG.get('retain_events_days')}})


def _kept_path(name, kind):
    name = os.path.basename(str(name or ''))
    if not DUMP_NAME_RE.match(name):
        raise ApiError(404, 'there is no such file')
    folder = DUMP_DIR if kind == 'dump' else BACKUP_DIR
    path = folder / name
    if not path.is_file():
        raise ApiError(404, 'there is no such file: %s' % name)
    return path


def _db_made_now(store, kind, folder):
    if kind == 'dump':
        return make_dump(store, 'download', folder=folder)
    path = Path(folder) / ('ai-copy-%s-download.json.gz' % _stamp())
    dump_tables(store.db, path)
    return path


def _db_upload_path(up):
    if not re.match(r'^[0-9a-f]{16}\Z', str(up or '')):
        raise ApiError(400, 'which file?')
    p = DB_UPLOADS / up
    if not p.is_file():
        raise ApiError(400, 'the file sent is not here any more (an hour has gone by?): send it again')
    return p


@route('POST', '/api/db', admin=True)
def api_db_do(c):
    st, b, by = c.daemon.store, c.body, c.name
    STORE_NOW['store'] = st
    act = b.get('action')
    if act == 'backup':
        try:
            out = make_backup(st, 'by %s' % by)
        except ValueError as e:
            raise ApiError(400, str(e))
        return {'message': 'a copy was made: %s' % out.name}
    if act == 'tidy':
        return {'message': 'tidied: %s' % st.tidy()}
    if act == 'job':
        return {'job': job_read()}
    if act == 'dump':
        try:
            out = make_dump(st, 'by-hand')
        except ValueError as e:
            raise ApiError(400, str(e))
        return {'name': out.name, 'bytes': out.stat().st_size, 'message': 'made: %s' % out.name}
    if act == 'download':
        # A kept one as it is, or one made now - without the key.
        if b.get('name'):
            path = _kept_path(b.get('name'), b.get('kind'))
            st.add_event('backups', '%s downloaded %s, without the key of its secrets' % (by, path.name), who=by)
            return {'path': str(path)}
        work = DB_TICKETS_DIR / secrets.token_hex(8)
        work.mkdir(mode=0o700, parents=True)
        try:
            path = _db_made_now(st, b.get('kind'), work)
        except ValueError as e:
            raise ApiError(400, str(e))
        st.add_event('backups', '%s downloaded %s, made for it, without the key of its secrets' % (by, path.name),
                     who=by)
        return {'path': str(path)}
    if act == 'download_ticket':
        dbkey_passphrase_checked(b.get('passphrase'))
        kind = 'dump' if b.get('kind') == 'dump' else ''
        work = DB_TICKETS_DIR / secrets.token_hex(8)
        work.mkdir(mode=0o700, parents=True)
        try:
            if b.get('name'):
                src = _kept_path(b.get('name'), kind)
                keyf = _key_beside(src)
                if keyf.is_file() and sealing_key() and keyf.read_text().strip() != sealing_key().hex():
                    raise ApiError(409, 'the key beside %s is not the one in use now: download it without the '
                                        'key, and the .key beside it from the machine' % src.name)
            else:
                src = _db_made_now(st, kind, work)
            out = dbkey_bundle(src, src.name, b.get('passphrase'), work)
            if src.parent == work:
                src.unlink()
        except ApiError:
            shutil.rmtree(str(work), ignore_errors=True)
            raise
        except ValueError as e:
            shutil.rmtree(str(work), ignore_errors=True)
            raise ApiError(400, str(e))
        st.add_event('backups', '%s downloaded %s WITH the key of its secrets, locked with a passphrase'
                     % (by, out.name), 'warn', who=by)
        return {'path': str(out), 'name': out.name}
    if act == 'upload_check':
        # A file the page sent (to DB_UPLOADS): what is in it.
        src = _db_upload_path(b.get('upload'))
        if dbkey_is_bundle(src):
            work = Path(tempfile.mkdtemp(prefix='ai-peek-', dir=str(STATE_DIR)))
            try:
                inner, _k, head = dbkey_open(src, work)
                said, why = db_file_peek(inner, st.db.engine)
            except ValueError as e:
                raise ApiError(400, str(e))
            finally:
                shutil.rmtree(str(work), ignore_errors=True)
            if said is None:
                raise ApiError(400, why)
            return {'says': said, 'upload': src.name, 'locked': True, 'file': head.get('file')}
        said, why = db_file_peek(src, st.db.engine)
        if said is None:
            raise ApiError(400, why)
        return {'says': said, 'upload': src.name, 'locked': False}
    if act == 'upload_restore':
        src = _db_upload_path(b.get('upload'))
        passphrase = str(b.get('passphrase') or '')
        locked = dbkey_is_bundle(src)
        if b.get('check') and locked:
            work = Path(tempfile.mkdtemp(prefix='ai-peek-', dir=str(STATE_DIR)))
            os.chmod(str(work), 0o700)
            try:
                inner, _k, _head = dbkey_open(src, work, passphrase)
                said, why = db_file_peek(inner, st.db.engine)
            except ValueError as e:
                raise ApiError(400, str(e))
            finally:
                shutil.rmtree(str(work), ignore_errors=True)
            if said is None:
                raise ApiError(400, why)
            said['with_key'] = True
            return {'says': said}

        def work_(progress):
            work = Path(tempfile.mkdtemp(prefix='ai-putback-', dir=str(STATE_DIR)))
            os.chmod(str(work), 0o700)
            try:
                if locked:
                    progress(1, 3, 'the file opened with its passphrase')
                    inner, keyf, head = dbkey_open(src, work, passphrase)
                    name = head.get('file') or 'a file with its key'
                else:
                    inner, keyf, name = src, None, 'a file sent from the page'
                progress(2, 3, 'put back')
                got = db_file_restore(st, inner, by, key_file=keyf, from_name=name)
                progress(3, 3, 'done')
                return got
            finally:
                shutil.rmtree(str(work), ignore_errors=True)
                try:
                    src.unlink()
                except OSError:
                    pass
        try:
            db_job('putting a database back', work_)
        except ValueError as e:
            raise ApiError(409, str(e))
        return {'message': 'the database is being put back', 'job': job_read()}
    if act in ('restore_kept', 'delete'):
        path = _kept_path(b.get('name'), b.get('kind'))
        if act == 'delete':
            for f in (path, _key_beside(path)):
                try:
                    f.unlink()
                except OSError:
                    pass
            st.add_event('backups', '%s deleted %s' % (by, path.name), 'warn', who=by)
            return {'message': '%s is deleted' % path.name}
        if b.get('check'):
            said, why = db_file_peek(path, st.db.engine)
            if said is None:
                raise ApiError(400, why)
            return {'says': said}
        try:
            return db_file_restore(st, path, by, key_file=_key_beside(path), from_name=path.name)
        except ValueError as e:
            raise ApiError(400, str(e))
    if act == 'erase':
        try:
            return {'job': db_erase_job(st, list(b.get('groups') or []), bool(b.get('tidy')), by)}
        except ValueError as e:
            raise ApiError(400, str(e))
    if act == 'tune_restart':
        try:
            return tune_restart(st, by)
        except ValueError as e:
            raise ApiError(400, str(e))
    try:
        if act in ('try', 'setup', 'empty', 'move', 'use'):
            cc = engine_asked(b.get('settings') or {})
            words = ENGINE_WORDS.get(cc['db_engine'])
            if act == 'try':
                got = db_try(cc)
                got['in_use'] = same_database(cc, st.db)
                return got
            if act == 'setup':
                if cc['db_engine'] == 'sqlite':
                    raise ApiError(400, 'the file on this machine needs no setting up')
                first = db_try(cc) if cc.get('db_password') else {'reached': False}
                fresh = ''
                if first.get('reached') and first.get('writable'):
                    made = ['the database and the account are there already, and it gets in']
                else:
                    who = str(b.get('admin_user') or '').strip()
                    if not who:
                        raise ApiError(400, 'an administrator of that server is needed to make a database and '
                                            'an account on it')
                    if not cc.get('db_password'):
                        fresh = cc['db_password'] = db_password_made()
                    made = db_make(cc, who, str(b.get('admin_password') or ''))
                write_file_settings({k: cc[k] for k in DB_KEYS if k != 'db_engine'})
                far = db_open(cc)
                try:
                    far.make_tables()
                finally:
                    far.close()
                got = db_try(cc)
                st.add_event('settings', '%s set up %s at %s' % (by, words, db_where(cc)), who=by)
                return {'made': made, 'password': fresh, 'kept_in': str(CONFIG_FILE), 'try': got,
                        'message': '%s at %s is ready' % (words, db_where(cc))}
            if same_database(cc, st.db) and act in ('empty', 'move'):
                raise ApiError(400, 'that is the database in use; this only ever touches the other one')
            if act == 'empty':
                got = db_try(cc)
                if not got.get('reached'):
                    raise ApiError(400, got.get('trouble') or 'it cannot be reached')
                gone = db_empty(cc)
                st.add_event('settings', '%s emptied %s at %s' % (by, words, db_where(cc)), 'warn', who=by)
                return {'message': 'emptied: %d table(s) thrown away' % len(gone)}
            if act == 'move':
                got = db_try(cc)
                if not got.get('reached'):
                    raise ApiError(400, got.get('trouble') or 'it cannot be reached')
                if not got.get('writable'):
                    raise ApiError(400, 'that account may not write to it')
                if got.get('rows'):
                    raise ApiError(400, 'there are %d record(s) in it already. Moving into a database that is '
                                        'not empty would mix two installations; empty it first if it really is '
                                        'spare.' % got['rows'])
                return {'job': db_move(st, cc, by)}
            if act == 'use':
                if same_database(cc, st.db):
                    raise ApiError(400, 'that is the database in use already')
                got = db_try(cc)
                if not got.get('reached'):
                    raise ApiError(400, got.get('trouble') or 'it cannot be reached')
                if not got.get('rows') and not b.get('even_empty'):
                    raise ApiError(400, 'it is empty: carry everything across first')
                if not b.get('even_older'):
                    try:
                        far = db_open(cc)
                        try:
                            there = float(far.value('SELECT MAX(at) FROM events') or 0)
                        finally:
                            far.close()
                        here = float(st.db.value('SELECT MAX(at) FROM events') or 0)
                    except Exception:                   # noqa: BLE001
                        there = here = 0
                    if there and here and there < here - 60:
                        raise ApiError(409, 'it holds an older copy: its newest event is from %s, this one\'s from '
                                            '%s. Empty it and carry everything across first, so nothing written '
                                            'since is left behind.' % (
                                                datetime.fromtimestamp(there).strftime('%d-%m-%Y %H:%M'),
                                                datetime.fromtimestamp(here).strftime('%d-%m-%Y %H:%M')))
                write_file_settings({k: cc[k] for k in DB_KEYS})
                st.add_event('settings', '%s switched the database to %s at %s; the daemon starts again on it'
                             % (by, words, db_where(cc)), 'warn', who=by)
                log('the database is now %s; starting again on it' % db_where(cc), 'warn')
                # systemd starts it again (Restart=always), on the new one; the
                # terminals go on (tmux is not the daemon's).
                threading.Timer(1.5, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()
                return {'message': 'the daemon starts again on %s in a moment' % words, 'restarting': True}
        if act == 'check':
            own = db_own(st)
            try:
                got = db_check(own or st.db)
            finally:
                if own:
                    own.close()
            st.add_event('settings', '%s checked the database: %s' % (by, 'nothing broken' if got['ok'] else 'TROUBLE'),
                         'info' if got['ok'] else 'warn', who=by)
            return got
        if act == 'statistics':
            own = db_own(st)
            try:
                return {'message': db_statistics(own or st.db)}
            finally:
                if own:
                    own.close()
        if act == 'give_back':
            def work(progress):
                got = db_give_back(st, progress)
                st.add_event('settings', '%s gave the disk back: %s -> %s' % (by, got['before'], got['after']), who=by)
                return got
            return {'job': db_job('giving the disk back', work)}
        if act == 'prune':
            days = 0 if b.get('everything') else int(b.get('days') or 0)
            if days < 1 and not b.get('everything'):
                raise ApiError(400, 'older than how many days? 1 at least')
            gone = db_prune(st, days)
            st.add_event('settings', '%s forgot the events older than %d day(s): %s' % (by, days, gone), 'warn', who=by)
            return {'message': 'forgotten: %d event(s), %d mail(s) of the outgoing mail' % (gone['events'], gone['mailq'])}
        if act == 'tune_plan':
            return tune_plan_for(st, b.get('machine') or {})
        if act == 'tune_apply':
            return tune_apply(st, b.get('machine') or {}, str(b.get('admin_user') or ''),
                              str(b.get('admin_password') or ''), by)
        if act == 'tune_undo':
            return tune_undo(st, str(b.get('admin_user') or ''), str(b.get('admin_password') or ''), by)
    except ApiError:
        raise
    except Refused:
        raise
    except ValueError as e:
        raise ApiError(400, str(e))
    except Exception as e:                              # noqa: BLE001
        raise ApiError(400, str(e).split('\n')[0][:300])
    raise ApiError(400, 'no such thing to do to the database')


# ---- the whole configuration as one file (as otp's Export and import) ---------------------
# The settings, the accounts of these pages, the firewall and who may reach
# the pages, the mail server's authorities and the TLS of the pages. Not the
# events nor the terminals: those go with a copy of the database. With the
# secrets (the password hashes, the sealed settings, the key of the
# certificate, the authenticator keys) it is locked with a passphrase made
# now and shown once.
def _phrase_key(phrase, salt):
    return hashlib.pbkdf2_hmac('sha256', str(phrase).encode('utf-8'), salt, 200000)


def lock_with(phrase, data):
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(16)
    key = _phrase_key(phrase, salt)
    raw = json.dumps(data).encode('utf-8')
    hide = hmac.new(key, b'hide', hashlib.sha256).digest()
    body = bytes(a ^ b for a, b in zip(raw, _seal_stream(hide, nonce, len(raw))))
    tag = hmac.new(hmac.new(key, b'sign', hashlib.sha256).digest(), nonce + body, hashlib.sha256).digest()
    return {'kind': 'ai-config-locked', 'salt': base64.b64encode(salt).decode(),
            'data': base64.b64encode(nonce + body + tag).decode()}


def open_with(phrase, locked):
    try:
        salt = base64.b64decode(locked['salt'])
        raw = base64.b64decode(locked['data'])
    except (KeyError, ValueError, TypeError):
        raise Refused('the locked part of the file is broken')
    key = _phrase_key(phrase, salt)
    nonce, body, tag = raw[:16], raw[16:-32], raw[-32:]
    if not hmac.compare_digest(tag, hmac.new(hmac.new(key, b'sign', hashlib.sha256).digest(), nonce + body,
                                             hashlib.sha256).digest()):
        raise Refused('the passphrase is not right')
    hide = hmac.new(key, b'hide', hashlib.sha256).digest()
    return json.loads(bytes(a ^ b for a, b in zip(body, _seal_stream(hide, nonce, len(body)))).decode('utf-8'))


def config_export(store, with_secrets=False):
    saved = store.settings_all()
    settings = {}
    for k, v in saved.items():
        if k not in SCHEMA_KEYS:
            continue
        if SCHEMA_KEYS[k][2] == 'password' or SCHEMA_KEYS[k][5].get('secret'):
            if with_secrets:
                settings[k] = unseal_secret(v, 'setting:' + k) if SCHEMA_KEYS[k][2] == 'password' else v
            continue
        settings[k] = v
    users = []
    for u in store.users():
        one = {k: u[k] for k in ('name', 'role', 'run_as', 'note', 'disabled')}
        one['roots'] = json.loads(u['roots'] or '[]')
        if with_secrets:
            one['pw'] = u['pw']
            rec = mfa_get(store, u['name'])
            if rec:
                rec = dict(rec)
                if rec.get('secret'):
                    rec['secret'] = unseal_secret(rec['secret'], mfa_key(u['name']))
                one['mfa'] = rec
        users.append(one)
    tls = tls_prof(store)
    if tls:
        tls = dict(tls)
        tls.pop('pending_key', None)
        if with_secrets and tls.get('key'):
            tls['key'] = unseal_secret(tls['key'], 'web:tls')
        else:
            tls.pop('key', None)
    out = {'kind': 'ai-config', 'version': __version__, 'host': host_name(), 'at': time.time(),
           'settings': settings, 'users': users, 'firewall': store.meta_json('fw:conf', None),
           'access': store.meta_json('fw:access', None), 'mail_ca': mail_ca_pem(store), 'tls': tls,
           'with_secrets': bool(with_secrets)}
    return out


def config_import(daemon, conf, by, replace=False, ip='127.0.0.1', wait=False):
    st = daemon.store
    if not isinstance(conf, dict) or conf.get('kind') != 'ai-config':
        raise Refused('that is not a configuration of ai (ai --export-config)')
    said = []
    sets = conf.get('settings') or {}
    n = 0
    for k, v in sets.items():
        if k not in SCHEMA_KEYS or k in ('upgrade_url',) and not str(v).startswith('https://'):
            continue
        nv = setting_value(k, v)
        if SCHEMA_KEYS[k][2] == 'password':
            nv = seal_secret(nv, 'setting:' + k) if nv else ''
        st.set_setting(k, nv, by)
        n += 1
    if replace:
        for k in list(st.settings_all()):
            if k not in sets and k in SCHEMA_KEYS and not (SCHEMA_KEYS[k][2] == 'password' and
                                                           not conf.get('with_secrets')):
                st.drop_setting(k)
    said.append('%d setting(s)' % n)
    names = []
    for u in conf.get('users') or []:
        name = str(u.get('name') or '')
        if not NAME_RE.match(name) or str(u.get('role')) not in ROLES:
            continue
        names.append(name)
        if name == by:
            continue                    # your own account is left as it is
        have = st.user(name)
        pw = u.get('pw') if u.get('pw') and str(u['pw']).startswith(('pbkdf2', 'scrypt')) else None
        run_as = str(u.get('run_as') or '')
        try:
            if run_as:
                linux_user(run_as)
        except Refused:
            run_as = ''
        if have:
            st.x('UPDATE users SET role=?, run_as=?, roots=?, note=?, disabled=? WHERE name=?',
                 (u['role'], run_as, json.dumps(clean_roots(u.get('roots') or [])), clean_line(u.get('note'), 300),
                  1 if u.get('disabled') else 0, name))
            if pw:
                st.x('UPDATE users SET pw=? WHERE name=?', (pw, name))
        else:
            st.x('INSERT INTO users(name,pw,role,run_as,roots,disabled,must_change,note,created) VALUES(?,?,?,?,?,?,?,?,?)',
                 (name, pw or hash_password(new_password()), u['role'], run_as,
                  json.dumps(clean_roots(u.get('roots') or [])), 1 if u.get('disabled') else 0, 0 if pw else 1,
                  clean_line(u.get('note'), 300), time.time()))
        if isinstance(u.get('mfa'), dict) and u['mfa'].get('kind') in ('app', 'mail', 'sms'):
            rec = dict(u['mfa'])
            if rec.get('secret'):
                rec['secret'] = seal_secret(rec['secret'], mfa_key(name))
            st.set_meta_json(mfa_key(name), rec)
    if replace:
        for u in st.users():
            if u['name'] not in names and u['name'] != by:
                st.x('DELETE FROM users WHERE name=?', (u['name'],))
                st.x('DELETE FROM sessions WHERE name=?', (u['name'],))
    said.append('%d account(s)' % len(names))
    if conf.get('mail_ca'):
        try:
            mail_ca_set(st, conf['mail_ca'], 'add')
            said.append('the mail server\'s authorities')
        except ValueError:
            pass
    config_rebuild(st)
    if isinstance(conf.get('tls'), dict) and conf['tls'].get('cert') and conf['tls'].get('key'):
        prof = dict(conf['tls'])
        prof['key'] = seal_secret(prof['key'], 'web:tls')
        if wait:
            tls_apply(st, prof, by)
            said.append('the certificate and TLS')
        else:
            tls_apply_later(st, prof, by)
            said.append('the certificate and TLS (being put in)')
    fw_new = conf.get('firewall') if isinstance(conf.get('firewall'), dict) else None
    ac_new = conf.get('access') if isinstance(conf.get('access'), dict) else None
    same = lambda a, b: json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)   # noqa: E731
    fw_was = st.meta_json('fw:conf', None) or {}
    if fw_new and same({k: fw_new.get(k) for k in ('on', 'off', 'rules')}, {k: fw_was.get(k) for k in ('on', 'off', 'rules')}):
        fw_new = None
    if ac_new and same(ac_new.get('pages'), (st.meta_json('fw:access', None) or {}).get('pages')):
        ac_new = None
    if fw_new or ac_new:
        b = dict(conf.get('firewall') or fw_conf(st))
        if isinstance(conf.get('access'), dict):
            b['access'] = conf['access']
        try:
            fw_save(daemon, b, by, ip)
            said.append('the firewall and who may reach the pages (as a change on trial - keep it)')
        except Refused as e:
            said.append('NOT the firewall: %s' % e)
    st.add_event('settings', '%s imported a configuration (%s): %s' % (by, 'exactly the file' if replace else
                                                                        'added to what was here', ', '.join(said)),
                 'warn', who=by)
    return 'imported: ' + ', '.join(said)


@route('GET', '/api/export', admin=True)
def api_export(c):
    conf = config_export(c.daemon.store, with_secrets=c.arg('secrets') == '1')
    if c.arg('secrets') == '1':
        phrase = '-'.join(secrets.token_hex(3) for _ in range(4))
        c.daemon.store.add_event('settings', '%s exported the configuration with its secrets' % c.name, 'warn',
                                 who=c.name)
        return {'bundle': dict(lock_with(phrase, conf), version=__version__, host=host_name()), 'passphrase': phrase}
    return {'config': conf}


@route('POST', '/api/import', admin=True)
def api_import(c):
    conf = c.body.get('config')
    if isinstance(conf, dict) and conf.get('kind') == 'ai-config-locked':
        conf = open_with(c.body.get('passphrase') or '', conf)
    return {'message': config_import(c.daemon, conf, c.name, bool(c.body.get('replace')), c.ip)}


# ---- Settings → Backups (otp's) ---------------------------------------------------------------
@route('GET', '/api/rbackup', admin=True)
def api_rbackup(c):
    for d in (RB_UPLOADS, RB_DOWNLOADS):
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
    rb_tidy_files()
    return rb_page(c.daemon.store)


def _rb_target_for(c, b):
    """The destination asked about: the one saved, with what is typed over it
    (Try it before Save)."""
    tid = str(b.get('id') or '')
    old = rb_target(c.daemon.store, tid) if tid else None
    if tid and not old:
        raise Refused('no such destination', 404)
    if isinstance(b.get('target'), dict):
        t = rb_checked(dict(b['target'], id=tid or None), old)
        if old:
            for k in ('key', 'pub', 'hostkey', 'client_cert', 'client_key', 'key_pass', 'ca', 'pin', 'ssh_cert'):
                if k in old and k not in t:
                    t[k] = old[k]
        return t
    if not old:
        raise Refused('which destination?')
    return old


def _rb_upload_path(b):
    up = str(b.get('upload') or '')
    if not re.match(r'^[0-9a-f]{16}\Z', up):
        raise ValueError('which file?')
    p = RB_UPLOADS / up
    if not p.is_file():
        raise ValueError('the file sent is not here any more: send it again')
    return p


@route('POST', '/api/rbackup', admin=True)
def api_rbackup_do(c):
    b = c.body
    st = c.daemon.store
    act = str(b.get('action') or '')
    by = c.name
    try:
        if act == 'save':
            t = rb_save(st, dict(b.get('target') or {}, id=b.get('id') or (b.get('target') or {}).get('id')), by)
            return {'message': 'saved', 'target': rb_view(t)}
        if act == 'delete':
            rb_delete(st, b.get('id'), by)
            return {'message': 'taken away'}
        if act == 'try':
            t = _rb_target_for(c, b)
            if t['kind'] in ('sftp', 'scp') and not t.get('hostkey'):
                lines, fps = ssh_keyscan(t['host'], t['port'])
                return {'hostkey_needed': True, 'hostkey': lines, 'fingerprints': fps,
                        'message': 'the server\'s host key is not trusted yet'}
            out = rb_try(t)
            st.add_event('settings', '%s tried the backup destination %s: %s' % (
                by, t['name'], 'it works' if out['ok'] else out.get('error')), who=by)
            if t.get('id') and rb_target(st, t['id']):
                rb_set_fields(st, t['id'], '', '', tried={'at': time.time(), 'ok': out['ok'],
                                                          'error': out.get('error') or ''})
            return out
        if act == 'hostkey_scan':
            t = _rb_target_for(c, b)
            lines, fps = ssh_keyscan(t['host'], t['port'])
            return {'hostkey': lines, 'fingerprints': fps}
        if act == 'hostkey_trust':
            t = _rb_target_for(c, b)
            lines = str(b.get('hostkey') or '')
            fresh, fps = ssh_keyscan(t['host'], t['port'])
            if sorted(x.strip() for x in lines.splitlines() if x.strip()) != \
                    sorted(x.strip() for x in fresh.splitlines() if x.strip()):
                raise ValueError('the server shows other host keys now than the ones shown: Try it again')
            rb_set_fields(st, t['id'], by, 'its host key trusted (%s)' % '; '.join(fps), hostkey=fresh)
            return {'message': 'trusted', 'fingerprints': fps}
        if act == 'hostkey_forget':
            t = _rb_target_for(c, b)
            rb_set_fields(st, t['id'], by, 'its host key forgotten', hostkey=None)
            return {'message': 'forgotten'}
        if act == 'keygen':
            t = _rb_target_for(c, b)
            private, public = ssh_keygen('ai-backup@%s' % node_name())
            rb_set_fields(st, t['id'], by, 'a new ssh key made here', key=seal_secret(private, bind=RB_BIND),
                          pub=public, key_pass=None)
            return {'message': 'made', 'pub': public}
        if act == 'key_paste':
            t = _rb_target_for(c, b)
            pp = str(b.get('passphrase') or '')
            private, public = rb_ssh_public_of(b.get('key'), pp)
            rb_set_fields(st, t['id'], by, 'an ssh key of their own given', key=seal_secret(private, bind=RB_BIND),
                          pub=public, key_pass=seal_secret(pp, bind=RB_BIND) if pp else None)
            return {'message': 'taken', 'pub': public}
        if act == 'key_download':
            t = _rb_target_for(c, b)
            private = rb_secret(t, 'key')
            if not private:
                raise Refused('there is no key', 404)
            st.add_event('settings', '%s downloaded the private ssh key of the backup destination %s' % (
                by, t['name']), 'warn', who=by)
            return {'pem': private if private.endswith('\n') else private + '\n',
                    'file': 'ai-backup-%s-key' % rb_slug(t['name'])}
        if act == 'key_forget':
            t = _rb_target_for(c, b)
            rb_set_fields(st, t['id'], by, 'its ssh key forgotten', key=None, pub=None, key_pass=None, ssh_cert=None)
            return {'message': 'forgotten'}
        if act == 'cert_make':
            t = _rb_target_for(c, b)
            key, crt = rb_client_cert_make(b.get('cn') or 'ai-backup-%s' % rb_slug(node_name()))
            rb_set_fields(st, t['id'], by, 'a client certificate made here', client_cert=crt,
                          client_key=seal_secret(key, bind=RB_BIND))
            return {'message': 'made', 'cert': crt, 'info': cert_info(crt)}
        if act == 'cert_given':
            t = _rb_target_for(c, b)
            key, crt = rb_client_cert_given(b.get('text'), str(b.get('password') or ''))
            rb_set_fields(st, t['id'], by, 'a client certificate of their own given', client_cert=crt,
                          client_key=seal_secret(key, bind=RB_BIND))
            return {'message': 'taken', 'cert': crt, 'info': cert_info(crt)}
        if act == 'cert_forget':
            t = _rb_target_for(c, b)
            rb_set_fields(st, t['id'], by, 'its client certificate forgotten', client_cert=None, client_key=None)
            return {'message': 'forgotten'}
        if act == 'pin':
            t = _rb_target_for(c, b)
            pin = re.sub(r'[^0-9a-f]', '', str(b.get('pin') or '').lower())
            if len(pin) != 64:
                raise ValueError('the fingerprint is SHA-256: 64 hex digits')
            rb_set_fields(st, t['id'], by, 'the server\'s certificate pinned (%s)' % pin, pin=pin, tls_check='pin')
            return {'message': 'pinned'}
        if act == 'run':
            only = [str(x) for x in (b.get('ids') or [])] or None
            return {'message': 'the backup is being made', 'job': rb_job_start(st, by, only), 'others': []}
        if act == 'job':
            return {'job': dict(RB_JOB)}
        if act == 'list':
            return {'files': rb_remote_list(st, b.get('id'))}
        if act == 'delete_file':
            t = rb_target(st, b.get('id'))
            name = str(b.get('name') or '')
            if not t or not RB_NAME_RE.match(name):
                raise ValueError('which backup?')
            tr = rb_transport(t)
            try:
                tr.open()
                names = set(x['name'] for x in tr.list())
                for n in [name] + [x for x in rb_companions(name) if x in names]:
                    tr.delete(n)
            finally:
                tr.close()
            st.add_event('backups', '%s deleted the backup %s at %s' % (by, name, t['name']), 'warn', who=by)
            return {'message': 'deleted'}
        if act == 'restore_md':
            return rb_restore_guide(st)
        if act == 'runs_forget':
            if b.get('all'):
                n = rb_history_forget(st)
                st.add_event('backups', '%s cleared the list of backups sent (%d line(s)); the backups stay where '
                             'they went' % (by, n), who=by)
                return {'message': 'the list is empty; the backups stay where they went', 'runs': rb_history(st)[:40]}
            try:
                at = float(b.get('at'))
            except (TypeError, ValueError):
                raise ValueError('which line?')
            if not rb_history_forget(st, at, b.get('file')):
                raise ValueError('that line is not on the list any more')
            return {'message': 'taken off the list', 'runs': rb_history(st)[:40]}
        if act == 'download':
            # A backup made now for the machine somebody is sitting at - or
            # one fetched from a destination: put where /files/get serves it
            # to this administrator, and taken away within the hour.
            RB_DOWNLOADS.mkdir(mode=0o700, parents=True, exist_ok=True)
            work = RB_DOWNLOADS / secrets.token_hex(8)
            work.mkdir(mode=0o700)
            tid, name = str(b.get('id') or ''), str(b.get('name') or '')
            if tid and name:
                rb_fetch(st, tid, name, str(work / name))
                st.add_event('backups', '%s downloaded the backup %s' % (by, name), 'warn', who=by)
                return {'path': str(work / name)}
            if not rb_password():
                raise Refused('without a password of the backups the file would hold every secret unlocked: '
                              'set the password first', 403)
            path, m, _md = rb_build(st, str(work))
            for p in work.iterdir():
                if str(p) != path:
                    p.unlink()
            st.add_event('backups', '%s downloaded a backup made for it (%s)' % (by, m['file']), 'info', who=by)
            return {'path': path}
        if act == 'peek':
            p = _rb_upload_path(b)
            with open(str(p), 'rb') as f:
                head = f.read(8)
            if not (head.startswith(b'Salted__') or head.startswith(b'\x1f\x8b')):
                p.unlink()
                raise ValueError('that is not a backup of ai')
            work = tempfile.mkdtemp(prefix='ai-peek-', dir=str(STATE_DIR))
            try:
                pw = str(b.get('password') or '') or rb_password()
                if head.startswith(b'Salted__') and not pw:
                    return {'upload': p.name, 'locked': True}
                try:
                    _top, m = rb_open(str(p), pw, work)
                except RbError as e:
                    return {'upload': p.name, 'locked': head.startswith(b'Salted__'), 'said': str(e)}
                return {'upload': p.name, 'locked': head.startswith(b'Salted__'), 'manifest': m}
            finally:
                shutil.rmtree(work, ignore_errors=True)
        if act == 'restore':
            password = str(b.get('password') or '') or rb_password()
            src = _rb_upload_path(b) if b.get('upload') else None
            if src is None:
                t = rb_target(st, b.get('id'))
                name = str(b.get('name') or '')
                if not t or not RB_NAME_RE.match(name):
                    raise ValueError('which backup?')
            daemon = c.daemon

            def work(progress):
                tmp = None
                try:
                    path = src
                    if path is None:
                        progress(1, 4, 'fetched from %s' % t['name'])
                        tmp = Path(tempfile.mkdtemp(prefix='ai-fetch-', dir=str(STATE_DIR)))
                        path = tmp / name
                        rb_fetch(st, t['id'], name, str(path))
                    progress(2, 4, 'opened and checked')
                    got = rb_restore(daemon, str(path), password, by)
                    progress(4, 4, 'put back')
                    return got
                finally:
                    if tmp:
                        shutil.rmtree(str(tmp), ignore_errors=True)
                    if src is not None:
                        try:
                            src.unlink()
                        except OSError:
                            pass
            return {'message': 'the backup is being put back', 'job': rb_job_start(st, by, what='restore', work=work)}
    except (RbError, ValueError) as e:
        raise Refused(str(e))
    except subprocess.SubprocessError as e:
        raise Refused('it took too long: %s' % str(e)[:200], 504)
    raise Refused('no such thing to do')


@route('GET', '/api/cert', admin=True)
def api_cert(c):
    return {'cert': cert_facts(), 'host': host_name()}


@route('POST', '/api/cert', admin=True)
def api_cert_do(c):
    do = c.body.get('do')
    if do == 'put':
        cert_put(c.body.get('cert'), c.body.get('key'), c.body.get('chain') or '')
        words = 'a certificate given for the pages'
    elif do == 'self':
        names = c.body.get('names') or []
        if isinstance(names, str):
            names = re.split(r'[\s,]+', names)
        cert_self(names, int(c.body.get('days') or 825))
        words = 'a new self-signed certificate for %s' % ', '.join(names)
    else:
        raise Refused('put or self')
    c.daemon.store.add_event('settings', '%s put in %s' % (c.name, words), 'warn', who=c.name)
    return {'cert': cert_facts()}


@route('GET', '/api/upgrade', admin=True)
def api_upgrade(c):
    return c.daemon.upgrades.view_otp()


@route('POST', '/api/upgrade', admin=True)
def api_upgrade_do(c):
    up = c.daemon.upgrades
    b = c.body
    act = str(b.get('action') or '')
    if act:
        # otp's Upgrades pane: what it asks, answered with the whole pane again.
        msg = ''
        if act == 'online_look':
            got = up.look(c.name)
            msg = got.get('error') or ('looked: the newest there is %s' % (got.get('newest') or {}).get('version', '–'))
        elif act in ('online_get', 'downgrade_get'):
            older = act == 'downgrade_get'
            path, info = up.fetch(str(b.get('version') or ''), c.name, older=older)
            up.hold(path, info, c.name)
            msg = 'ai %s fetched and checked' % info.get('version')
            if b.get('start'):
                up.install(path, c.name, older=older)
                msg = 'ai %s is being put in' % info.get('version')
        elif act == 'start':
            h = up.held()
            if not h:
                raise Refused('no package is waiting: send one, or fetch one from the web')
            up.install(Path(h['path']), c.name, older=bool(h.get('downgrade')))
            msg = 'ai %s is being put in' % h.get('version')
        elif act == 'forget':
            up.forget(c.name)
            msg = 'the package is thrown away'
        elif act == 'cancel':
            raise Refused('once install.sh runs it is not stopped half way: it finishes, or puts back what it '
                          'changed by itself')
        elif act == 'hide':
            c.daemon.store.set_meta('upgrade:hidden', str(up.status().get('at')))
        elif act == 'downgrade_list':
            return {'downgrade': up.downgrade_list()}
        elif act == 'downgrade_changelog':
            return {'changelog': changelog_between(str(b.get('version') or ''), __version__)}
        else:
            raise Refused('no such thing to do with the upgrades')
        out = up.view_otp()
        out['message'] = msg
        return out
    do = b.get('do')
    if do == 'look':
        return {'online': up.look(c.name)}
    if do in ('fetch', 'install', 'downgrade'):
        version = str(c.body.get('version') or '')
        path, info = up.fetch(version, c.name, older=do == 'downgrade')
        if do in ('install', 'downgrade'):
            up.install(path, c.name, older=do == 'downgrade')
        return {'info': info}
    if do == 'hide':
        c.daemon.store.set_meta('upgrade:hidden', str(up.status().get('at')))
        return {}
    raise Refused('look, fetch, install, downgrade or hide')


@route('GET', '/api/software', admin=True)
def api_software(c):
    return {'nodes': [{'name': node_name(), 'me': True, 'alive': True, 'software': software_info(c.daemon.store)}]}


@route('GET', '/api/console-login', admin=True)
def api_console_login(c):
    return {'on': console_at_login(), 'there': CONSOLE_PROFILE.exists()}


@route('POST', '/api/console-login', admin=True)
def api_console_login_do(c):
    said = console_at_login_set(bool(c.body.get('on')))
    c.daemon.store.add_event('settings', '%s switched %s the ai console at root\'s login' % (
        c.name, 'on' if c.body.get('on') else 'off'), 'warn', who=c.name)
    return {'on': console_at_login(), 'message': said}


@route('GET', '/api/linux', admin=True)
def api_linux(c):
    return {'accounts': linux_accounts()}


# ---------------------------------------------------------------------------
# The server's panes, as otp draws them (system.js): one node, this server
# ---------------------------------------------------------------------------
# The pages for the firewall, the network, the clock, root's SSH keys, the
# system's updates and restarting are otp's own, and ask for what otp's
# daemon answers - its nodes, its jobs, its plans - shaped exactly so. Here
# there is one node: this server. What root does is in ai_os.py, taken from
# otp's root helper; the daemon is root and calls it straight.
AIOS = [None]


def aios():
    if AIOS[0] is None:
        import importlib.util
        for p in (LIB_DIR / 'ai_os.py', HERE / 'deploy' / 'ai_os.py'):
            if p.is_file():
                spec = importlib.util.spec_from_file_location('ai_os', str(p))
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)
                AIOS[0] = m
                break
        else:
            raise Refused('ai_os.py is not installed (%s)' % LIB_DIR, 500)
    return AIOS[0]


def os_call(fn, *args, **kw):
    """A function of ai_os, its Refused said as ours."""
    try:
        return fn(*args, **kw)
    except Exception as e:                              # noqa: BLE001
        if e.__class__.__name__ == 'Refused' or isinstance(e, ValueError):
            raise Refused(str(e))
        raise


def node_address():
    rc, so, _se = run(['ip', '-4', 'route', 'get', '192.0.2.1'], timeout=5)
    m = re.search(r'\bsrc (\S+)', so or '')
    return m.group(1) if m else '127.0.0.1'


def node_name():
    return host_name().split('.')[0]


def node_of(daemon, **extra):
    n = {'name': node_name(), 'me': True, 'alive': True, 'address': node_address(),
         'version': __version__, 'started': daemon.started}
    n.update(extra)
    return n


# ---- changes on trial: kept, or taken back ----------------------------------------------------
def trial_undo(daemon, kind, undo):
    if kind == 'net':
        net_restore(undo)
    elif kind == 'fw':
        daemon.store.set_meta_json('fw:conf', undo.get('conf') or {'on': False, 'off': [], 'rules': []})
        fw_put(daemon, undo.get('conf') or {}, record=False)
        if undo.get('access') is not None:
            access_apply(undo['access'])
            daemon.store.set_meta_json('fw:access', undo['access'])
    elif kind == 'access':
        access_apply(undo)


# ---- the network ---------------------------------------------------------------------------------
NM_KEYS = ['ipv4.method', 'ipv4.addresses', 'ipv4.gateway', 'ipv4.dns', 'ipv4.dns-search',
           'ipv4.ignore-auto-dns', 'ipv6.method', 'ipv6.addresses', 'ipv6.gateway', 'ipv6.dns']
NET_CACHE = {'at': 0.0, 'data': None}


def net_now(fresh=False):
    if NO_SYSTEM:
        return {'at': time.time(), 'data': {'nm': False, 'devices': [], 'con': '', 'dev': '', 'conf': {},
                                            'live': {'addrs4': [], 'addrs6': [], 'gw4': '', 'gw6': '',
                                                     'dns': []}, 'hostname': host_name()}}
    if fresh or not NET_CACHE['data'] or time.time() - NET_CACHE['at'] > 15:
        try:
            NET_CACHE['data'] = os_call(aios().net_read)
        except Refused as e:
            NET_CACHE['data'] = {'nm': False, 'said': str(e)}
        NET_CACHE['at'] = time.time()
    return {'at': NET_CACHE['at'], 'data': NET_CACHE['data']}


def net_view(daemon, fresh=False):
    job = daemon.store.meta_json('net:job', {}) or {}
    if job and job.get('state') in ('done', 'failed'):
        keep = 6 * 3600 if job.get('state') == 'done' else 86400
        if daemon.store.get_meta('net:seen') == str(job.get('id')) or \
                time.time() - float(job.get('moved') or job.get('at') or 0) > keep:
            job = {}
    return {'nodes': [node_of(daemon, now=net_now(fresh), job=job)], 'cluster': False,
            'vip': None, 'now': time.time(), 'trials': daemon.trials.view()}


def nm_fields(con):
    rc, so, se = run(['nmcli', '-t', '-g', ','.join(NM_KEYS), 'connection', 'show', con], timeout=15)
    if rc != 0:
        raise Refused('nmcli: %s' % (se or so).strip()[:200])
    vals = so.rstrip('\n').split('\n')
    return {k: v.replace('\\:', ':').strip() for k, v in zip(NM_KEYS, vals + [''] * len(NM_KEYS))}


def nm_args(con, props):
    args = ['nmcli', 'connection', 'modify', con]
    for k, v in props.items():
        args += [k, '' if v in ('--', None) else v]
    return args


def _addrs(text, version, what):
    out = []
    for a in re.split(r'[\s,;]+', str(text or '').strip()):
        if not a:
            continue
        ip = plain_ip(a, 'address' if what == 'dns' else 'interface')
        if ip.version != version:
            raise Refused('%s is not an IPv%d address' % (a, version))
        if what == 'addr' and '/' not in a:
            raise Refused('%s: an address with its prefix, as %s' % (
                a, '192.0.2.10/24' if version == 4 else '2001:db8::10/64'))
        out.append(str(ip))
    return out


def net_check(daemon, want):
    """The change asked for, checked: {con, props, hostname, plan: [steps]}."""
    if not isinstance(want, dict):
        raise Refused('what is wanted is an object')
    now = net_now()['data'] or {}
    if not now.get('nm'):
        raise Refused('NetworkManager (nmcli) is not on this server: set its network by hand')
    cons = [d['con'] for d in now.get('devices') or [] if d.get('con')]
    con = str(want.get('con') or now.get('con') or '')
    if con not in cons:
        raise Refused('there is no connection %r here' % con)
    v4 = want.get('ipv4') or {}
    addr = _addrs(v4.get('addr'), 4, 'addr')
    if len(addr) != 1:
        raise Refused('one IPv4 address with its prefix, as 192.0.2.10/24')
    gw = _addrs(v4.get('gw'), 4, 'dns')
    dns = _addrs(v4.get('dns'), 4, 'dns')
    search = [s for s in re.split(r'[\s,;]+', str(v4.get('search') or '')) if s]
    for s in search:
        if not HOST_RE.match(s):
            raise Refused('%s is not a domain' % s[:60])
    props = {'ipv4.method': 'manual', 'ipv4.addresses': addr[0], 'ipv4.gateway': gw[0] if gw else '',
             'ipv4.dns': ','.join(dns), 'ipv4.dns-search': ','.join(search),
             'ipv4.ignore-auto-dns': 'yes'}
    v6 = want.get('ipv6') or {}
    plan = ['%s: IPv4 %s%s, DNS %s%s' % (con, addr[0], ' via %s' % gw[0] if gw else ' (no gateway)',
                                         ', '.join(dns) or 'none', ', search %s' % ', '.join(search) if search else '')]
    if v6.get('on'):
        dns6 = _addrs(v6.get('dns'), 6, 'dns')
        if v6.get('mode') == 'auto':
            props.update({'ipv6.method': 'auto', 'ipv6.addresses': '', 'ipv6.gateway': ''})
            plan.append('IPv6: automatic (SLAAC / DHCPv6)')
        else:
            a6 = _addrs(v6.get('addr'), 6, 'addr')
            if len(a6) != 1:
                raise Refused('one IPv6 address with its prefix, as 2001:db8::10/64')
            g6 = _addrs(v6.get('gw'), 6, 'dns')
            props.update({'ipv6.method': 'manual', 'ipv6.addresses': a6[0],
                          'ipv6.gateway': g6[0] if g6 else ''})
            plan.append('IPv6: %s%s' % (a6[0], ' via %s' % g6[0] if g6 else ''))
        props['ipv6.dns'] = ','.join(dns6)
    else:
        props.update({'ipv6.method': 'disabled', 'ipv6.addresses': '', 'ipv6.gateway': '', 'ipv6.dns': ''})
        plan.append('IPv6: off')
    host = str(want.get('hostname') or '').strip()
    if host and not HOST_RE.match(host):
        raise Refused('%s is not a host name' % host[:60])
    if host and host != now.get('hostname'):
        plan.append('the host name: %s' % host)
    plan.append('NetworkManager brings %s up again with it' % con)
    plan.append('kept with Keep it within %d s - from the old address or the new - or the old network '
                'comes back by itself' % int(CONFIG.get('revert_s') or 120))
    return {'con': con, 'props': props, 'hostname': host if host != now.get('hostname') else '', 'plan': plan}


def net_job(daemon, got, by):
    if NO_SYSTEM:
        raise Refused('this is a test machine: nothing is changed')
    job = daemon.store.meta_json('net:job', {}) or {}
    if job.get('state') == 'running':
        raise Refused('a change of the network is going on already')
    job = {'id': secrets.token_hex(6), 'state': 'running', 'pct': 5, 'steps': [], 'at': time.time(),
           'moved': time.time(), 'by': by}
    daemon.store.set_meta_json('net:job', job)

    def step(words, ok=True, pct=None):
        job['steps'].append({'ok': ok, 'what': words, 'at': time.time()})
        job['moved'] = time.time()
        if pct:
            job['pct'] = pct
        daemon.store.set_meta_json('net:job', job)

    def go():
        try:
            before = nm_fields(got['con'])
            rc, so, _se = run(['hostnamectl', '--static'], timeout=5)
            undo = {'con': got['con'], 'props': {k: before[k] for k in NM_KEYS},
                    'hostname': so.strip() if rc == 0 else ''}
            step('what is there now kept, to go back to', pct=15)
            run(nm_args(got['con'], got['props']), timeout=30, check=True)
            step('NetworkManager: %s set' % got['con'], pct=40)
            if got['hostname']:
                run(['hostnamectl', 'set-hostname', got['hostname']], timeout=15, check=True)
                step('the host name: %s' % got['hostname'], pct=50)
            daemon.trials.start('net', 'the network: %s' % got['plan'][0], undo, by)
            time.sleep(1.0)
            rc, so, se = run(['nmcli', 'connection', 'up', got['con']], timeout=90)
            if rc != 0:
                raise Refused('nmcli connection up: %s' % (se or so).strip()[-200:])
            step('%s is up with it - now keep it' % got['con'], pct=100)
            job['state'] = 'done'
            NET_CACHE['at'] = 0
        except Exception as e:                          # noqa: BLE001
            step(str(e)[:300], ok=False, pct=100)
            job['state'] = 'failed'
        daemon.store.set_meta_json('net:job', job)
        daemon.store.add_event('settings', '%s changed the network: %s' % (by, job['state']),
                               'warn' if job['state'] == 'done' else 'bad', who=by)
    threading.Thread(target=go, name='ai-net', daemon=True).start()
    return job


def net_restore(undo):
    run(nm_args(undo['con'], undo['props']), timeout=30, check=True)
    if undo.get('hostname'):
        run(['hostnamectl', 'set-hostname', undo['hostname']], timeout=15)
    run(['nmcli', 'connection', 'up', undo['con']], timeout=90)
    NET_CACHE['at'] = 0


# ---- the firewall --------------------------------------------------------------------------------
# What the pages manage is ai's own chain, AI-IN, jumped to first from INPUT:
# the rules of your own in their order, then what ai's functions need - and
# what AI-IN does not let in goes on to the rest of INPUT, as it was. Where
# firewalld runs, the same rules are rich rules of its default zone.
FW_CHAIN = 'AI-IN'
FW_PROTOS = ('tcp', 'udp', 'icmp', 'vrrp', 'any')
FW_FILES = {4: ['/etc/sysconfig/iptables', '/etc/iptables/rules.v4'],
            6: ['/etc/sysconfig/ip6tables', '/etc/iptables/rules.v6']}
FW_TOOLS = {4: ('iptables', 'iptables-restore', 'iptables-save'),
            6: ('ip6tables', 'ip6tables-restore', 'ip6tables-save')}
FW_AUTO_OPTIONAL = ('ssh', 'icmp', 'dhcpv6', 'web', 'ntp')
ACCESS_WORDS = {'pages': 'The pages'}


def fw_backend():
    if NO_SYSTEM:
        return 'test'
    if which('firewall-cmd'):
        rc, so, _se = run(['firewall-cmd', '--state'], timeout=10)
        if rc == 0 and 'running' in so:
            return 'firewalld'
    if which('ufw'):
        rc, so, _se = run(['ufw', 'status'], timeout=10)
        if rc == 0 and 'Status: active' in so:
            return 'ufw'
    if which('iptables'):
        return 'iptables'
    return ''


def _fam(addr):
    try:
        return ipaddress.ip_network(str(addr), strict=False).version
    except ValueError:
        return 4


def fw_rule_checked(x):
    if not isinstance(x, dict):
        raise Refused('a rule is an object')
    proto = str(x.get('proto') or 'tcp')
    if proto not in FW_PROTOS:
        raise Refused('the protocol is TCP, UDP, ICMP, VRRP or any')
    port = re.sub(r'\s+', '', str(x.get('port') or ''))
    if port:
        if proto not in ('tcp', 'udp'):
            raise Refused('a port only with TCP or UDP')
        bits = port.split(',')
        if len(bits) > 15:
            raise Refused('fifteen ports at most in one rule')
        for b in bits:
            m = re.match(r'^(\d{1,5})(?:[-:](\d{1,5}))?\Z', b)
            if not m or not 0 < int(m.group(1)) < 65536 or \
                    (m.group(2) and not int(m.group(1)) < int(m.group(2)) < 65536):
                raise Refused('%s is not a port, a range (8000-8100) or ports by commas' % b)
        port = ','.join(b.replace(':', '-') for b in bits)
    src = str(x.get('source') or '').strip()
    fam = int(x.get('family') or 0)
    if src:
        net = plain_ip(src, 'network')
        src = str(net)
        if fam and fam != net.version:
            raise Refused('%s is not an IPv%d network' % (src, fam))
        fam = net.version
    if fam not in (0, 4, 6):
        raise Refused('IPv4, IPv6 or both')
    action = str(x.get('action') or 'accept')
    if action not in ('accept', 'drop', 'reject'):
        raise Refused('accept, drop or reject')
    return {'family': fam, 'proto': proto, 'port': port, 'source': src, 'action': action,
            'scope': 'all', 'note': clean_line(x.get('note'), 80), 'disabled': bool(x.get('disabled'))}


def fw_conf(store):
    c = store.meta_json('fw:conf', None) or {}
    return {'on': bool(c.get('on')), 'set': bool(c), 'off': c.get('off') or [], 'rules': c.get('rules') or [],
            'by': c.get('by'), 'at': c.get('at')}


def access_conf(store):
    a = store.meta_json('fw:access', None)
    if a:
        return a
    now = access_read()
    return {'pages': {'any': bool(now.get('all')), 'from': list(now.get('nets') or [])}, 'from_nginx': True}


def fw_auto(store):
    out = [{'key': 'ssh', 'title': 'SSH', 'why': 'to manage the machine - turned off, '
            'take care to keep a rule of your own for it',
            'rules': [{'family': f, 'proto': 'tcp', 'port': '22', 'source': ''} for f in (4, 6)]},
           {'key': 'icmp', 'title': 'ICMP / ICMPv6', 'why': 'ping, and IPv6 cannot work without '
            'ICMPv6 (neighbour discovery)',
            'rules': [{'family': f, 'proto': 'icmp', 'port': '', 'source': ''} for f in (4, 6)]},
           {'key': 'dhcpv6', 'title': 'DHCPv6 client', 'why': 'answers of a DHCPv6 server, for '
            'an address given that way', 'rules': [{'family': 6, 'proto': 'udp', 'port': '546',
                                                     'source': 'fe80::/10'}]}]
    a = access_conf(store).get('pages') or {}
    web = []
    srcs = [''] if a.get('any') or not a.get('from') else list(a.get('from'))
    for s in srcs:
        for f in ((4, 6) if not s else (_fam(s),)):
            web.append({'family': f, 'proto': 'tcp', 'port': '80,443', 'source': s})
    out.append({'key': 'web', 'title': 'HTTP / HTTPS', 'why': 'these pages, the terminals and the files; '
                'who may reach them is under "Who may reach the pages"', 'rules': web})
    nc = store.meta_json('ntp:conf', {}) or {}
    if nc.get('manage') and nc.get('allow'):
        out.append({'key': 'ntp', 'title': 'NTP (time served)', 'why': 'this server serves the '
                    'time to the networks set under Settings → Time',
                    'rules': [{'family': _fam(x), 'proto': 'udp', 'port': '123', 'source': x}
                              for x in nc['allow']]})
    return out


def fw_lines(c, auto, fam):
    ch = FW_CHAIN
    out = ['-A %s -i lo -m comment --comment "ai: loopback" -j ACCEPT' % ch,
           '-A %s -m conntrack --ctstate ESTABLISHED,RELATED -m comment --comment "ai: answers" -j ACCEPT' % ch]
    if fam == 6:
        out += ['-A %s -p ipv6-icmp -m icmp6 --icmpv6-type %d -m comment --comment "ai: neighbour discovery" '
                '-j ACCEPT' % (ch, t) for t in (133, 134, 135, 136)]

    def one(r, note, target):
        if r.get('family') and int(r['family']) != fam:
            return None
        a = ['-A', ch]
        if r.get('source'):
            a += ['-s', r['source']]
        p = r.get('proto') or 'any'
        if p == 'icmp':
            a += ['-p', 'icmp' if fam == 4 else 'ipv6-icmp']
        elif p == 'vrrp':
            a += ['-p', '112']
        elif p != 'any':
            a += ['-p', p]
            if r.get('port'):
                ports = r['port'].replace('-', ':')
                a += ['-m', 'multiport', '--dports', ports] if ',' in ports else ['--dport', ports]
        a += ['-m', 'comment', '--comment', '"ai: %s"' % re.sub(r'["\\]', '', note)[:60]]
        a += ['-j', target]
        return ' '.join(a)
    for r in c.get('rules') or []:
        if not r.get('disabled'):
            x = one(r, r.get('note') or 'yours', {'accept': 'ACCEPT', 'drop': 'DROP', 'reject': 'REJECT'}[r['action']])
            if x:
                out.append(x)
    for item in auto:
        if item['key'] in (c.get('off') or []):
            continue
        for r in item['rules']:
            x = one(r, item['title'], 'ACCEPT')
            if x:
                out.append(x)
    return out


def fw_rich(c, auto):
    out = []

    def rich(r, action):
        fams = [int(r['family'])] if r.get('family') else ([4, 6] if r.get('proto') == 'icmp' else [0])
        res = []
        for fam in fams:
            ports = (r.get('port') or '').split(',') if r.get('port') else ['']
            for port in ports:
                bits = ['rule']
                if fam:
                    bits.append('family="ipv%d"' % fam)
                if r.get('source'):
                    bits.append('source address="%s"' % r['source'])
                p = r.get('proto') or 'any'
                if p == 'icmp':
                    bits.append('protocol value="%s"' % ('icmp' if fam != 6 else 'ipv6-icmp'))
                elif p == 'vrrp':
                    bits.append('protocol value="vrrp"')
                elif p in ('tcp', 'udp'):
                    bits.append('port port="%s" protocol="%s"' % (port, p) if port else 'protocol value="%s"' % p)
                bits.append(action)
                res.append(' '.join(bits))
        return res
    for r in c.get('rules') or []:
        if not r.get('disabled'):
            out += rich(r, r['action'])
    for item in auto:
        if item['key'] not in (c.get('off') or []):
            for r in item['rules']:
                out += rich(r, 'accept')
    return list(dict.fromkeys(out))


def fw_put(daemon, c, record=True):
    """The rules put in, as the conf says: (backend, said)."""
    store = daemon.store
    b = fw_backend()
    auto = fw_auto(store)
    said = []
    if b == 'test':
        said.append('a test machine: nothing changed')
    elif b == 'iptables':
        for fam in (4, 6):
            tool, restore, save = FW_TOOLS[fam]
            if not which(tool):
                continue
            if c.get('on'):
                snippet = '*filter\n:%s - [0:0]\n%s\nCOMMIT\n' % (FW_CHAIN, '\n'.join(fw_lines(c, auto, fam)))
                rc, so, se = run([restore, '--noflush'], input=snippet, timeout=30)
                if rc != 0:
                    raise Refused('%s does not take the rules: %s' % (restore, (se or so).strip()[-300:]))
                if run([tool, '-C', 'INPUT', '-j', FW_CHAIN], timeout=10)[0] != 0:
                    run([tool, '-I', 'INPUT', '1', '-j', FW_CHAIN], timeout=10)
                said.append('IPv%d: %d rule(s) in %s' % (fam, len(fw_lines(c, auto, fam)), FW_CHAIN))
            else:
                while run([tool, '-D', 'INPUT', '-j', FW_CHAIN], timeout=10)[0] == 0:
                    pass
                run([tool, '-F', FW_CHAIN], timeout=10)
                run([tool, '-X', FW_CHAIN], timeout=10)
            for path in FW_FILES[fam]:
                if os.path.exists(path):
                    rc, so, _se = run([save], timeout=30)
                    if rc == 0 and so.strip():
                        write_atomic(path, so, mode=0o600)
                        said.append('%s: kept over a reboot' % path)
                    break
            else:
                if c.get('on'):
                    said.append('IPv%d: not kept over a reboot (install iptables-services or iptables-persistent)' % fam)
    elif b == 'firewalld':
        had = store.meta_json('fw:rich', []) or []
        want = fw_rich(c, auto) if c.get('on') else []
        for rule in had:
            if rule not in want:
                for perm in ([], ['--permanent']):
                    run(['firewall-cmd'] + perm + ['--remove-rich-rule', rule], timeout=30)
        for rule in want:
            if rule not in had:
                for perm in (['--permanent'], []):
                    rc, so, se = run(['firewall-cmd'] + perm + ['--add-rich-rule', rule], timeout=30)
                    if rc != 0:
                        raise Refused('firewalld does not take %s: %s' % (rule, (se or so).strip()[:200]))
        store.set_meta_json('fw:rich', want)
        said.append('firewalld: %d rich rule(s) of ai in the default zone' % len(want))
    elif b == 'ufw':
        if c.get('on'):
            raise Refused('ufw looks after this server\'s firewall: change it with ufw, or switch it off '
                          '(ufw disable) to manage it here')
    elif c.get('on'):
        raise Refused('there is no iptables on this machine')
    store.set_meta_json('fw:state', {'state': 'done', 'said': said, 'at': time.time()})
    return b, said


def fw_read(fresh=False):
    b = fw_backend()
    out = {'backend': b, 'now': {}, 'full': {}, 'full_at': time.time()}
    if b == 'iptables':
        for fam in (4, 6):
            rc, so, _se = run([FW_TOOLS[fam][2], '-t', 'filter'], timeout=20)
            lines = []
            for line in so.splitlines() if rc == 0 else []:
                line = re.sub(r'^\[\d+:\d+\]\s+', '', line.strip())
                if not line or line.startswith('#') or line in ('*filter', 'COMMIT'):
                    continue
                lines.append(re.sub(r' \[\d+:\d+\]$', '', line))
            out['full'][fam] = lines[:1500]
            out['now'][fam] = [x for x in lines if x.startswith(':INPUT ') or
                               (x.startswith('-A INPUT') and x != '-A INPUT -j %s' % FW_CHAIN)][:200]
    elif b in ('firewalld', 'ufw'):
        cmd = ['firewall-cmd', '--list-all'] if b == 'firewalld' else ['ufw', 'status', 'verbose']
        rc, so, _se = run(cmd, timeout=20)
        out['full'] = {4: [x.rstrip() for x in so.splitlines() if x.strip()][:400], 6: []}
    return out


def fw_view(daemon, fresh=False):
    store = daemon.store
    st = store.meta_json('fw:state', {}) or {}
    n = node_of(daemon, fw=fw_read(fresh), access=access_read(), state=st.get('state') or '',
                said=st.get('said') or [], current=True, waiting=False, progress=None, auto=fw_auto(store))
    return {'node': node_name(), 'cluster': False, 'nodes': [n], 'conf': fw_conf(store),
            'access': access_conf(store), 'access_words': ACCESS_WORDS, 'inner': {n['name']: []},
            'optional': list(FW_AUTO_OPTIONAL), 'may': True, 'trials': daemon.trials.view()}


def fw_save(daemon, b, who, ip):
    store = daemon.store
    raw = b.get('rules') or []
    if not isinstance(raw, list) or len(raw) > 200:
        raise Refused('two hundred rules at most')
    rules = []
    for x in raw:
        r = fw_rule_checked(x)
        r['id'] = re.sub(r'[^0-9a-z]', '', str((x or {}).get('id') or ''))[:16] or secrets.token_hex(4)
        if r['id'].startswith('n'):
            r['id'] = secrets.token_hex(4)
        rules.append(r)
    off = [k for k in (b.get('off') or []) if k in FW_AUTO_OPTIONAL]
    was_conf = store.meta_json('fw:conf', None) or {'on': False, 'off': [], 'rules': []}
    was_access = store.meta_json('fw:access', None)
    said = []
    new_access = None
    if isinstance(b.get('access'), dict):
        pg = (b['access'].get('pages') or {})
        nets = [str(plain_ip(n, 'network')) for n in (pg.get('from') or [])]
        if not pg.get('any') and not nets:
            raise Refused('who may reach the pages: everybody, or at least one network')
        if not pg.get('any'):
            try:
                me_ip = ipaddress.ip_address(ip)
                inside = me_ip.is_loopback or any(me_ip in ipaddress.ip_network(x, strict=False) for x in nets)
            except ValueError:
                inside = True
            if not inside and not b.get('even_if_me'):
                raise Refused('your own address (%s) is not among the networks that may reach the pages: you '
                              'would be shut out. Add it, or let everybody in' % ip, 409)
        new_access = {'pages': {'any': bool(pg.get('any')), 'from': nets}}
        access_apply({'all': new_access['pages']['any'], 'nets': nets})
        store.set_meta_json('fw:access', new_access)
        said.append('who may reach the pages: %s' % ('everybody' if pg.get('any') else ', '.join(nets)))
    c = {'on': bool(b.get('on')), 'off': off, 'rules': rules, 'by': who, 'at': time.time()}
    if c['on'] != bool(was_conf.get('on')):
        said.append('ai\'s firewall rules %s' % ('on' if c['on'] else 'off'))
    if rules != (was_conf.get('rules') or []):
        said.append('%d rule(s) of your own' % len(rules))
    if sorted(off) != sorted(was_conf.get('off') or []):
        said.append('turned off: %s' % (', '.join(off) or 'nothing'))
    store.set_meta_json('fw:conf', c)
    try:
        fw_put(daemon, c)
    except Refused:
        store.set_meta_json('fw:conf', was_conf)
        raise
    daemon.trials.start('fw', 'the firewall and access: %s' % (' · '.join(said) or 'as it was'),
                        {'conf': was_conf, 'access': {'all': (was_access or access_conf(store)).get('pages', {}).get('any', True),
                                                      'nets': (was_access or access_conf(store)).get('pages', {}).get('from', [])}
                         if new_access else None}, who)
    if said:
        store.add_event('settings', '%s changed the firewall and access: %s' % (who, ' · '.join(said)), 'warn', who=who)
    return {'message': 'saved and put in - press Keep it within %d s, or it goes back by itself'
                       % int(CONFIG.get('revert_s') or 120)}


# ---- restart and power off ------------------------------------------------------------------------
def power_plan(store):
    return store.meta_json('power:plan', {}) or {}


def power_view(daemon):
    store = daemon.store
    plan = power_plan(store)
    row = store.meta_json('power:row', {}) or {}
    seen = store.get_meta('power:seen') == str(plan.get('id') or '')
    live = plan and not seen and time.time() - float(plan.get('at') or 0) < 1800
    return {'plan': plan if live else {}, 'nodes': [node_of(daemon, row=row if row.get('id') == plan.get('id') else {})],
            'now': time.time(), 'cluster': False, 'busy': bool(live and row.get('state') == 'going')}


def power_ask(daemon, how, by):
    if how not in ('reboot', 'poweroff'):
        raise Refused('reboot or poweroff')
    plan = {'id': secrets.token_hex(6), 'how': how, 'targets': [node_name()], 'order': 'one',
            'at': time.time(), 'by': by}
    daemon.store.set_meta_json('power:plan', plan)
    daemon.store.set_meta_json('power:row', {'id': plan['id'], 'state': 'going', 'down_at': time.time() + 3})
    power(how, by, daemon.store)
    return plan


def power_back(daemon):
    """Started again after a restart asked from the pages: said so."""
    store = daemon.store
    plan, row = power_plan(store), store.meta_json('power:row', {}) or {}
    if plan.get('how') == 'reboot' and row.get('id') == plan.get('id') and row.get('state') == 'going' and \
            daemon.started > float(row.get('down_at') or 0):
        row['state'] = 'back'
        store.set_meta_json('power:row', row)


# ---- the clock ----------------------------------------------------------------------------------------
NTP_DEFAULT = {'manage': False, 'servers': [], 'peers': False, 'allow': [], 'makestep': [1, 3],
               'minsources': 1, 'timezone': ''}
NTP_CACHE = {'at': 0.0, 'now': None, 'zones': None}


def ntp_now(fresh=False):
    if fresh or not NTP_CACHE['now'] or time.time() - NTP_CACHE['at'] > 20:
        try:
            data = os_call(aios().ntp_read) if not NO_SYSTEM else {'time': time.time(), 'chrony': False}
            data['timezone'] = data.get('timezone') or time.strftime('%Z')
        except Refused as e:
            data = {'time': time.time(), 'said': str(e)}
        NTP_CACHE['now'] = {'at': time.time(), 'data': data}
        NTP_CACHE['at'] = time.time()
    return NTP_CACHE['now']


def ntp_view(daemon):
    if NTP_CACHE['zones'] is None:
        NTP_CACHE['zones'] = [] if NO_SYSTEM else aios().zones()
    conf = dict(NTP_DEFAULT, **(daemon.store.meta_json('ntp:conf', {}) or {}))
    return {'nodes': [node_of(daemon, now=ntp_now(), applied=daemon.store.meta_json('ntp:applied', {}) or {})],
            'conf': conf, 'zones': NTP_CACHE['zones'], 'cluster': False, 'hash': '', 'now': time.time()}


def ntp_save(daemon, c, by):
    m = aios()
    try:
        step = [float(c.get('step_s') or 1), int(c.get('step_n') if c.get('step_n') not in (None, '') else 3)]
    except (TypeError, ValueError):
        raise Refused('the step is a number of seconds and a number of updates')
    want = {'manage': bool(c.get('manage')), 'servers': c.get('servers') or [], 'peers': [],
            'allow': c.get('allow') or [], 'makestep': step, 'minsources': c.get('minsources') or 1,
            'timezone': str(c.get('timezone') or '')}
    n = os_call(m.ntp_checked, want)
    keep = {'manage': n['manage'], 'servers': n['servers'], 'peers': False, 'allow': n['allow'],
            'makestep': n['makestep'], 'minsources': n['minsources'], 'timezone': n['timezone']}
    daemon.store.set_meta_json('ntp:conf', keep)
    try:
        got = {'said': ['a test machine: nothing changed']} if NO_SYSTEM else os_call(m.ntp_apply, n)
        daemon.store.set_meta_json('ntp:applied', {'at': time.time(), 'ok': True, 'said': '; '.join(got.get('said') or [])})
    except Refused as e:
        daemon.store.set_meta_json('ntp:applied', {'at': time.time(), 'ok': False, 'said': str(e)})
        raise
    NTP_CACHE['at'] = 0
    if keep['allow']:
        c2 = fw_conf(daemon.store)
        if c2['on']:
            fw_put(daemon, c2)
    daemon.store.add_event('settings', '%s set the time: %s%s' % (
        by, ', '.join(s['host'] for s in n['servers']) if n['manage'] else 'the machine\'s own servers',
        ', time zone %s' % n['timezone'] if n['timezone'] else ''), 'info', who=by)
    return {'message': 'saved and put in'}


# ---- root's SSH keys ---------------------------------------------------------------------------------
SK_CACHE = {'at': 0.0, 'got': None, 'error': ''}


def sk_read(fresh=False):
    if fresh or SK_CACHE['got'] is None or time.time() - SK_CACHE['at'] > 30:
        try:
            SK_CACHE['got'] = os_call(aios().sshkeys_do, {'do': 'list'}) if not NO_SYSTEM else \
                {'keys': [], 'file': '/root/.ssh/authorized_keys', 'sshd': {'there': False}}
            SK_CACHE['error'] = ''
        except Refused as e:
            SK_CACHE['error'] = str(e)
            SK_CACHE['got'] = SK_CACHE['got'] or {'keys': [], 'sshd': {}}
        SK_CACHE['at'] = time.time()
    return SK_CACHE['got']


def ssh_fp_of(public):
    m = aios().key_facts(public)
    return (m[1], m[2]) if m else ('', '')


def rootkey_view(store, keys):
    r = store.meta_json('rootkey:all', {}) or {}
    on = {node_name(): any(k.get('fp') == r.get('fp') for k in keys) if r.get('fp') else False}
    return [{'scope': 'all', 'has': bool(r.get('pub')), 'pub': r.get('pub') or '', 'fp': r.get('fp') or '',
             'kind': r.get('kind') or '', 'how': r.get('how') or '', 'by': r.get('by') or '', 'at': r.get('at'),
             'on': on}]


def sshkeys_view(daemon, fresh=False):
    got = sk_read(fresh)
    n = node_of(daemon, keys=got.get('keys') or [], sshd=got.get('sshd') or {}, file=got.get('file') or '',
                at=SK_CACHE['at'], error=SK_CACHE['error'], pending=0)
    return {'nodes': [n], 'keygen': bool(which('ssh-keygen')), 'cluster': False,
            'kept': rootkey_view(daemon.store, n['keys'])}


def sshkey_pair(kind, comment):
    if kind not in ('ed25519', 'rsa4096'):
        raise Refused('ed25519 or rsa4096')
    if not which('ssh-keygen'):
        raise Refused('ssh-keygen is not on this server (dnf install openssh-clients)')
    comment = re.sub(r'[^A-Za-z0-9@._ -]', '', str(comment or ''))[:80].strip() or 'root'
    with tempfile.TemporaryDirectory(prefix='.ai-key-') as work:
        p = os.path.join(work, 'k')
        args = ['-t', 'ed25519'] if kind == 'ed25519' else ['-t', 'rsa', '-b', '4096']
        run(['ssh-keygen', '-q'] + args + ['-a', '100', '-N', '', '-C', comment, '-f', p], timeout=120, check=True)
        return read_text(p), read_text(p + '.pub').strip()


def ssh_public_of(private, passphrase=''):
    with tempfile.TemporaryDirectory(prefix='.ai-key-') as work:
        p = os.path.join(work, 'k')
        with open(p, 'w') as f:
            f.write(str(private).strip() + '\n')
        os.chmod(p, 0o600)
        rc, so, se = run(['ssh-keygen', '-y', '-P', str(passphrase or ''), '-f', p], timeout=30)
        if rc != 0:
            raise Refused('ssh-keygen does not read that private key%s' % (
                ' - is the passphrase right?' if 'passphrase' in (se or '').lower() or 'incorrect' in (se or '').lower() else ''))
        return so.strip()


def sshkeys_do(daemon, b, who):
    m = aios()
    act = str(b.get('action') or '')
    if act == 'refresh':
        sk_read(True)
        return {'message': 'read again'}
    if act == 'add':
        text = str(b.get('line') or '').strip()
        was_private = 'PRIVATE KEY-----' in text
        line = ssh_public_of(text, b.get('passphrase') or '') if was_private else \
            (text.splitlines()[0].strip() if text else '')
        os_call(m.sshkeys_do, {'do': 'add', 'line': line})
        sk_read(True)
        daemon.store.add_event('settings', '%s added an SSH key for root' % who, 'warn', who=who)
        return {'message': 'the key is on%s' % (' - the private half was not kept' if was_private else '')}
    if act == 'drop':
        os_call(m.sshkeys_do, {'do': 'drop', 'fp': str(b.get('fp') or ''), 'last_ok': bool(b.get('last_ok'))})
        sk_read(True)
        daemon.store.add_event('settings', '%s took the SSH key %s of root away' % (who, b.get('fp')), 'warn', who=who)
        return {'message': 'the key is taken away'}
    if act in ('rk_make', 'rk_given', 'rk_again'):
        if act == 'rk_make':
            private, public = sshkey_pair(str(b.get('kind') or 'ed25519'),
                                          'root@%s %s' % (node_name(), time.strftime('%Y-%m-%d')))
            how = 'made'
        elif act == 'rk_given':
            text = str(b.get('key') or '').strip()
            private = ''
            if 'PRIVATE KEY-----' in text:
                public = ssh_public_of(text, b.get('passphrase') or '')
            else:
                public = text.splitlines()[0].strip() if text else ''
            how = 'given'
        else:
            r = daemon.store.meta_json('rootkey:all', {}) or {}
            if not r.get('pub'):
                raise Refused('there is no key made or given for that')
            public, private, how = r['pub'], '', r.get('how') or 'made'
        os_call(m.sshkeys_do, {'do': 'add', 'line': public})
        fp, kind = ssh_fp_of(public)
        if act != 'rk_again':
            daemon.store.set_meta_json('rootkey:all', {'scope': 'all', 'pub': public, 'fp': fp, 'kind': kind,
                                                       'how': how, 'by': who, 'at': time.time()})
        sk_read(True)
        daemon.store.add_event('settings', '%s %s an SSH key for root (%s)%s' % (
            who, {'rk_make': 'made', 'rk_given': 'put on', 'rk_again': 'put on again'}[act], fp,
            ' - its private half handed to the page once, kept nowhere' if act == 'rk_make' else ''), 'warn', who=who)
        out = {'pub': public, 'fp': fp, 'nodes': [node_name()], 'message': 'the key is on'}
        if act == 'rk_make':
            out.update(private=private, file='ai-root-%s-%s' % (node_name(), time.strftime('%Y%m%d')),
                       message='made - keep the private half now, it is not shown again')
        return out
    raise Refused('no such thing to do')


# ---- the system's updates --------------------------------------------------------------------------
def osup_state():
    try:
        return json.loads(read_text(STATE_DIR / 'osup.json') or '{}')
    except ValueError:
        return {}


def osup_view(daemon):
    store = daemon.store
    plan = store.meta_json('osup:plan', {}) or {}
    st = osup_state()
    check = store.meta_json('osup:check', {}) or {}
    row = store.meta_json('osup:row', {}) or {}
    if st.get('kind') == 'check':
        check = {'state': 'running' if st.get('state') == 'running' else 'done', 'id': st.get('id'),
                 'checked': st.get('at') if st.get('state') != 'running' else check.get('checked'),
                 'count': st.get('count', 0), 'security': st.get('security'),
                 'reboot_now': st.get('reboot_now'), 'reboot_after': st.get('reboot_after'),
                 'reboot_why': st.get('reboot_why') or [], 'pm': st.get('pm'),
                 'packages': st.get('packages') or [], 'lines': st.get('lines') or [],
                 'began': st.get('began'), 'error': st.get('said') or ''}
        if check['state'] == 'done':
            store.set_meta_json('osup:check', check)
    elif st.get('kind') == 'upgrade' and st.get('id') == plan.get('id'):
        row = {'state': {'running': 'updating'}.get(st.get('state'), st.get('state')), 'plan': plan.get('id'),
               'pct': st.get('pct'), 'phase': st.get('phase'), 'said': st.get('said') or '',
               'at': st.get('at'), 'lines': st.get('lines') or [], 'began': st.get('began'),
               'reboot': bool(st.get('reboot')), 'rebooted': row.get('rebooted', False)}
        if row['state'] in ('done', 'failed') and plan.get('state') == 'running':
            plan['state'] = row['state']
            store.set_meta_json('osup:plan', plan)
            store.add_event('system', 'the update of the system ended: %s' % row['state'],
                            'info' if row['state'] == 'done' else 'bad', who=plan.get('by'))
            if row['state'] == 'done':
                store.set_meta_json('osup:check', dict(check, count=0, packages=[], reboot_now=row['reboot']))
                check = store.meta_json('osup:check', {})
        store.set_meta_json('osup:row', row)
    if plan.get('state') == 'running' and time.time() - float(row.get('at') or plan.get('at') or 0) > 3600:
        plan['state'] = 'failed'
        store.set_meta_json('osup:plan', plan)
    cl = store.meta_json('osup:cleared', {}) or {}
    for name, part in (('check', check), ('row', row)):
        c = cl.get(name) or {}
        lines = part.get('lines') or []
        if lines and c and c.get('mark') == osup_mark(part):
            at = max((i for i, ln in enumerate(lines) if ln == c.get('last')), default=None)
            part = dict(part, lines=lines[at + 1:] if at is not None else lines)
            if name == 'check':
                check = part
            else:
                row = part
    seen = store.get_meta('osup:seen')
    hidden = bool(plan) and seen == plan.get('id') and plan.get('state') != 'running'
    started = daemon.started
    reboot = (bool(row.get('reboot')) and float(row.get('at') or 0) > 0 and not row.get('rebooted')) or \
        bool(check.get('reboot_now') and check.get('state') == 'done')
    pw = power_view(daemon)
    return {'plan': {} if hidden else plan, 'now': time.time(), 'cluster': False, 'helper': True,
            'power': pw['plan'] if pw['busy'] else {},
            'nodes': [node_of(daemon, row=row if row.get('plan') == plan.get('id') else {}, check=check,
                              reboot=reboot, started=started)]}


def osup_mark(part):
    """Which run a part's lines are of: the same mark, the same run."""
    return '%s|%s' % (part.get('plan') or part.get('id') or '', part.get('began') or '')


def osup_do(daemon, b, who):
    m = aios()
    store = daemon.store
    act = str(b.get('action') or '')
    if NO_SYSTEM and act in ('check', 'start', 'reboot'):
        raise Refused('this is a test machine: nothing is changed')
    if act == 'check':
        os_call(m.osup_launch, secrets.token_hex(6), 'check')
        return {'message': 'looking for updates on %s' % node_name()}
    if act == 'start':
        plan = store.meta_json('osup:plan', {}) or {}
        if plan.get('state') == 'running':
            raise Refused('an update is going on already')
        plan = {'id': secrets.token_hex(6), 'order': [node_name()], 'reboot': 'auto' if b.get('reboot') == 'auto' else 'ask',
                'by': who, 'at': time.time(), 'state': 'running', 'from': node_name()}
        store.set_meta_json('osup:plan', plan)
        store.set_meta_json('osup:row', {'plan': plan['id'], 'state': 'waiting', 'at': time.time()})
        os_call(m.osup_launch, plan['id'], 'upgrade')
        store.add_event('system', '%s started the update of the system%s' % (
            who, ', restarted by itself when it needs it' if plan['reboot'] == 'auto' else ''), 'warn', who=who)
        return {'message': 'the update starts', 'plan': plan}
    if act == 'cancel':
        plan = store.meta_json('osup:plan', {}) or {}
        if plan.get('state') == 'running':
            plan['state'] = 'cancelled'
            store.set_meta_json('osup:plan', plan)
        return {'message': 'stopped - what dnf or apt is doing now finishes'}
    if act == 'clear':
        v = osup_view(daemon)
        n = v['nodes'][0]
        cl = {}
        for k in ('row', 'check'):
            part = n.get(k) or {}
            if part.get('lines'):
                cl[k] = {'mark': osup_mark(part), 'last': part['lines'][-1]}
        store.set_meta_json('osup:cleared', cl)
        return osup_view(daemon)
    if act == 'hide':
        plan = store.meta_json('osup:plan', {}) or {}
        if plan.get('state') == 'running':
            raise Refused('it is still going on')
        if plan.get('id'):
            store.set_meta('osup:seen', str(plan['id']))
        return osup_view(daemon)
    if act == 'reboot':
        row = store.meta_json('osup:row', {}) or {}
        row['rebooted'] = True
        store.set_meta_json('osup:row', row)
        power_ask(daemon, 'reboot', who)
        return {'message': 'restarting %s' % node_name()}
    raise Refused('no such thing to do')


def osup_tick(daemon):
    """A restart the update asked for by itself (Restart by itself when needed)."""
    plan = daemon.store.meta_json('osup:plan', {}) or {}
    row = daemon.store.meta_json('osup:row', {}) or {}
    if plan.get('reboot') == 'auto' and plan.get('state') == 'done' and row.get('reboot') and \
            not row.get('rebooted') and row.get('plan') == plan.get('id'):
        row['rebooted'] = True
        daemon.store.set_meta_json('osup:row', row)
        power_ask(daemon, 'reboot', 'the update of the system')


# ---- the routes of these panes ---------------------------------------------------------------------------
@route('GET', '/api/net', admin=True)
def api_net(c):
    return net_view(c.daemon)


@route('POST', '/api/net', admin=True)
def api_net_do(c):
    act = c.body.get('action')
    if act == 'read':
        return net_view(c.daemon, fresh=True)
    if act == 'plan':
        got = net_check(c.daemon, c.body.get('want') or {})
        return {'plan': got['plan'], 'want': c.body.get('want')}
    if act == 'apply':
        got = net_check(c.daemon, c.body.get('want') or {})
        job = net_job(c.daemon, got, c.name)
        return {'message': 'asked: %s does it now' % node_name(), 'id': job['id']}
    if act == 'hide':
        job = c.daemon.store.meta_json('net:job', {}) or {}
        if job.get('state') not in ('done', 'failed'):
            raise Refused('the change is not over yet', 409)
        c.daemon.store.set_meta('net:seen', str(job.get('id')))
        return net_view(c.daemon)
    raise Refused('no such thing to do')


@route('POST', '/api/trial', admin=True)
def api_trial(c):
    kind = str(c.body.get('kind') or '')
    act = str(c.body.get('action') or c.body.get('do') or '')
    if act == 'keep':
        c.daemon.trials.keep(kind, c.name)
        return {'message': 'kept'}
    if act == 'back':
        c.daemon.trials.back(kind, c.name)
        return {'message': 'the old is back'}
    raise Refused('keep or back')


@route('GET', '/api/firewall', admin=True)
def api_fw(c):
    return fw_view(c.daemon, fresh=bool(c.arg('fresh')))


@route('POST', '/api/firewall', admin=True)
def api_fw_do(c):
    act = str(c.body.get('action') or '')
    if act == 'rule_check':
        return {'rule': fw_rule_checked(c.body.get('rule') if isinstance(c.body.get('rule'), dict) else {})}
    if act == 'save':
        return fw_save(c.daemon, c.body, c.name, c.ip)
    raise Refused('no such thing to do')


@route('GET', '/api/power', admin=True)
def api_power(c):
    return power_view(c.daemon)


@route('POST', '/api/power', admin=True)
def api_power_do(c):
    if c.body.get('action') == 'hide':
        plan = power_plan(c.daemon.store)
        if plan.get('id'):
            c.daemon.store.set_meta('power:seen', str(plan['id']))
        return power_view(c.daemon)
    how = str(c.body.get('how') or '')
    if how in ('restart-ai', 'restart-web'):
        return {'message': power(how, c.name, c.daemon.store)}
    plan = power_ask(c.daemon, how, c.name)
    return {'message': 'asked', 'plan': plan}


@route('GET', '/api/ntp', admin=True)
def api_ntp(c):
    return ntp_view(c.daemon)


@route('POST', '/api/ntp', admin=True)
def api_ntp_do(c):
    act = c.body.get('action')
    if act == 'save':
        return ntp_save(c.daemon, c.body.get('conf') or {}, c.name)
    if act == 'read':
        ntp_now(True)
        return {'message': 'read again'}
    if act == 'sync':
        if not NO_SYSTEM:
            os_call(aios().ntp_sync)
        ntp_now(True)
        c.daemon.store.add_event('settings', '%s stepped the clock to the time servers' % c.name, 'warn', who=c.name)
        return {'message': 'stepped to the time servers'}
    raise Refused('no such thing to do')


@route('GET', '/api/sshkeys', admin=True)
def api_sshkeys(c):
    return sshkeys_view(c.daemon)


@route('POST', '/api/sshkeys', admin=True)
def api_sshkeys_do(c):
    return sshkeys_do(c.daemon, c.body, c.name)


@route('GET', '/api/osup', admin=True)
def api_osup(c):
    return osup_view(c.daemon)


@route('POST', '/api/osup', admin=True)
def api_osup_do(c):
    return osup_do(c.daemon, c.body, c.name)


# ---------------------------------------------------------------------------
# The HTTP side: the API (for the PHP pages), the terminals and the files
# (straight from nginx, by the session cookie)
# ---------------------------------------------------------------------------
COOKIE = 'ai_session'


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'ai'
    sys_version = ''
    daemon = None

    def log_message(self, fmt, *args):
        log('http %s' % (fmt % args), 'debug')

    # -- answering --------------------------------------------------------------
    def answer(self, status, data, extra=None):
        body = json.dumps(data, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def fail(self, status, words):
        self.answer(status, {'ok': False, 'error': words})

    def body_json(self, most=8 * 1024 * 1024):
        n = int(self.headers.get('Content-Length') or 0)
        if n > most:
            raise Refused('that is too much to send here', 413)
        raw = self.rfile.read(n) if n else b''
        if not raw:
            return {}
        try:
            got = json.loads(raw.decode('utf-8'))
        except ValueError:
            raise Refused('the body is not JSON')
        if not isinstance(got, dict):
            raise Refused('the body is not an object')
        return got

    def do_GET(self):
        self.dispatch('GET')

    def do_POST(self):
        self.dispatch('POST')

    def dispatch(self, method):
        u = urllib.parse.urlsplit(self.path)
        try:
            if u.path.startswith('/api/'):
                return self.api(method, u)
            if u.path == '/ws/term':
                return self.ws_term(u)
            if u.path.startswith('/files/'):
                return self.files(method, u)
            self.fail(404, 'no such thing here')
        except Refused as e:
            try:
                self.fail(e.status, str(e))
            except OSError:
                pass
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:                          # noqa: BLE001
            log('%s %s broke: %s\n%s' % (method, u.path, e, traceback.format_exc()), 'error')
            try:
                self.fail(500, 'it broke here: %s' % e)
            except OSError:
                pass

    # -- the API, for PHP ---------------------------------------------------------
    def api(self, method, u):
        d = self.daemon
        if not hmac.compare_digest(str(self.headers.get('X-Ai-Token') or ''), d.token):
            return self.fail(403, 'not the pages\' token')
        hit = ROUTES.get((method, u.path))
        if not hit:
            return self.fail(404, 'unknown endpoint')
        fn, admin, anon = hit
        ip = re.sub(r'[^0-9A-Fa-f:.]', '', str(self.headers.get('X-Ai-Client') or ''))[:64] or '127.0.0.1'
        token = str(self.headers.get('X-Ai-Session') or '')
        who = None if anon else d.auth.who(token)
        if not anon and not who:
            return self.fail(401, 'not signed in')
        body = self.body_json() if method == 'POST' else {}
        c = Ctx(d, who, body, urllib.parse.parse_qs(u.query), ip, token)
        if who and who.get('_mfa') and u.path not in MFA_ALLOWED:
            return self.fail(403, 'give the second step of signing in first')
        if who and who['must_change'] and u.path not in ('/api/auth/password', '/api/auth/whoami',
                                                         '/api/auth/logout', '/api/status', '/api/auth/prefs'):
            return self.fail(403, 'change your password first')
        if admin:
            need_admin(c)
        out = fn(c)
        if isinstance(out, tuple):
            status, out = out
        else:
            status = 200
        out = dict(out or {})
        out.setdefault('ok', True)
        self.answer(status, out)

    # -- straight from nginx: by the cookie -----------------------------------------------
    def cookie_who(self):
        raw = str(self.headers.get('Cookie') or '')
        token = ''
        for part in raw.split(';'):
            k, _s, v = part.strip().partition('=')
            if k == COOKIE:
                token = v.strip()
        who = self.daemon.auth.who(token)
        if not who:
            raise Refused('not signed in', 401)
        if who.get('_mfa'):
            raise Refused('give the second step of signing in first', 403)
        if who['must_change']:
            raise Refused('change your password first', 403)
        return who

    def same_site(self, post):
        """Only this page may ask: a WebSocket from its own origin, a POST with a
        header of ours that no form on another site can send."""
        host = str(self.headers.get('X-Forwarded-Host') or self.headers.get('Host') or '')
        origin = str(self.headers.get('Origin') or '')
        if origin and origin != 'null':
            o = urllib.parse.urlsplit(origin)
            if o.netloc.lower() != host.lower():
                raise Refused('that request did not come from this page', 403)
        site = str(self.headers.get('Sec-Fetch-Site') or '')
        if site and site not in ('same-origin', 'none'):
            raise Refused('that request did not come from this page', 403)
        if post and self.headers.get('X-Ai-Req') != '1':
            raise Refused('that request did not come from this page', 403)

    def ip(self):
        return re.sub(r'[^0-9A-Fa-f:.]', '', str(self.headers.get('X-Real-IP') or self.client_address[0]))[:64]

    def ws_term(self, u):
        self.same_site(False)
        who = self.cookie_who()
        q = urllib.parse.parse_qs(u.query)
        tm = self.daemon.terms
        r = tm.row((q.get('id') or [''])[0])
        tm.may(who, r)
        if self.headers.get('Upgrade', '').lower() != 'websocket' or not self.headers.get('Sec-WebSocket-Key'):
            raise Refused('a WebSocket, please', 400)
        if r['id'] not in tm.live(True):
            raise Refused('that terminal has ended', 410)
        key = self.headers['Sec-WebSocket-Key'].strip()
        self.send_response(101, 'Switching Protocols')
        self.send_header('Upgrade', 'websocket')
        self.send_header('Connection', 'Upgrade')
        self.send_header('Sec-WebSocket-Accept', WebSocket.accept_key(key))
        self.end_headers()
        self.wfile.flush()
        self.close_connection = True
        try:
            cols = max(10, min(1000, int((q.get('c') or ['120'])[0])))
            rows = max(3, min(500, int((q.get('r') or ['40'])[0])))
        except ValueError:
            cols, rows = 120, 40
        self.connection.settimeout(None)
        ws = WebSocket(self.connection)
        log('%s looks at the terminal %s from %s' % (who['name'], r['id'], self.ip()), 'debug')
        term_bridge(self.daemon, ws, who, r, cols, rows, readonly=(q.get('ro') or [''])[0] == '1')

    def files(self, method, u):
        post = method == 'POST'
        self.same_site(post)
        who = self.cookie_who()
        q = urllib.parse.parse_qs(u.query)

        def arg(n, default=''):
            v = q.get(n)
            return v[0] if v else default
        d = self.daemon
        if u.path == '/files/list' and not post:
            path = arg('path') or self.home_of(who)
            root = arg('root')
            if root:
                # The files of one chat (1.0.5): its own folder and what is in
                # it, never above - whatever the account may see elsewhere.
                root = os.path.realpath(root)
                real = os.path.realpath(path)
                if real != root and not real.startswith(root.rstrip('/') + '/'):
                    raise Refused('that is outside the folder of this chat (%s)' % root, 403)
            got = files_list(who, path, arg('hidden', '1') == '1')
            if root:
                got['root'] = root
                if os.path.realpath(got.get('path') or path) == root:
                    got['up'] = None
                got['roots'] = [root]
            return self.answer(200, dict(got, ok=True))
        if u.path == '/files/get' and not post:
            return self.send_path(who, arg('path'), arg('inline') == '1')
        if u.path == '/files/op' and post:
            out = files_op(who, self.body_json())
            return self.answer(200, dict(out, ok=True))
        if u.path == '/files/put' and post:
            length = int(self.headers.get('Content-Length') or -1)
            path, size = take_upload(self.rfile, length, arg('dir'), arg('name'), who, arg('overwrite') == '1')
            d.store.add_event('files', '%s sent %s (%s)' % (who['name'], path, human_bytes(size)), 'info',
                              who=who['name'])
            return self.answer(200, {'ok': True, 'path': path, 'size': size})
        if u.path == '/files/chat' and post:
            tm = d.terms
            r = tm.row(arg('term'))
            tm.may(who, r)
            folder = chat_folder(d, who, r)
            name = time.strftime('%Y%m%d-%H%M%S-') + safe_name(arg('name') or 'pasted')
            pw = linux_user(r['run_as'])
            length = int(self.headers.get('Content-Length') or -1)
            path, size = take_upload(self.rfile, length, folder, name, who, False, uid=pw.pw_uid, gid=pw.pw_gid)
            mime = mimetypes.guess_type(path)[0] or ''
            if arg('paste', '1') == '1':
                text = path if ' ' not in path else shlex.quote(path)
                tm.send(r, (text if mime.startswith('image/') else '@' + text) + ' ')
            d.store.add_event('files', '%s gave Claude %s (%s)' % (who['name'], path, human_bytes(size)), 'info',
                              who=who['name'])
            return self.answer(200, {'ok': True, 'path': path, 'size': size, 'image': mime.startswith('image/')})
        if u.path == '/files/package' and post:
            if who['role'] != 'admin':
                raise Refused('only an administrator puts in a new version', 403)
            UPGRADE_DIR.mkdir(parents=True, exist_ok=True)
            length = int(self.headers.get('Content-Length') or -1)
            if length > UPGRADE_MOST:
                raise Refused('no version of ai is that big', 413)
            name = safe_name(arg('name') or 'package.tar.gz')
            if not re.match(r'^ai-\d+\.\d+\.\d+\.tar\.gz\Z', name):
                raise Refused('a package is called ai-X.Y.Z.tar.gz')
            tmp = UPGRADE_DIR / name
            data = self.rfile.read(length) if length > 0 else b''
            write_atomic(tmp, data, mode=0o600)
            try:
                info = d.upgrades.take(tmp, who['name'], older=bool(CONFIG.get('upgrade_downgrade', True)))
            except Refused:
                tmp.unlink()
                raise
            if arg('install') == '1':
                d.upgrades.install(tmp, who['name'])
                return self.answer(200, {'ok': True, 'info': info})
            d.upgrades.hold(tmp, info, who['name'])
            out = d.upgrades.view_otp()
            out.update(ok=True, info=info, message='ai %s checked: signed by %s%s' % (
                info.get('version'), info.get('signed_by'), ' - older than this one' if info.get('older') else ''))
            return self.answer(200, out)
        raise Refused('no such thing here', 404)

    def home_of(self, who):
        try:
            return linux_user(run_as_of(who)).pw_dir
        except Refused:
            return '/'

    def send_path(self, who, path, inline):
        real = path_allowed(who, path or '/')
        if os.path.isdir(real):
            return self.send_zip(who, real)
        if not os.path.isfile(real):
            raise Refused('no such file', 404)
        size = os.path.getsize(real)
        mime = mimetypes.guess_type(real)[0] or 'application/octet-stream'
        name = os.path.basename(real)
        if inline and not SAFE_INLINE.match(mime):
            if size < TEXT_MOST:
                mime = 'text/plain'
            else:
                inline = False
        self.send_response(200)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Disposition', '%s; filename*=UTF-8\'\'%s' % (
            'inline' if inline else 'attachment', urllib.parse.quote(name)))
        self.send_header('Content-Security-Policy', "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; sandbox")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        with open(real, 'rb') as f:
            shutil.copyfileobj(f, self.wfile, 1 << 20)

    def send_zip(self, who, real):
        name = (os.path.basename(real.rstrip('/')) or 'root') + '.zip'
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Disposition', 'attachment; filename*=UTF-8\'\'%s' % urllib.parse.quote(name))
        self.send_header('Transfer-Encoding', 'chunked')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.close_connection = True
        out = self.wfile

        class Chunks(io.RawIOBase):
            def writable(self):
                return True

            def write(self, b):
                if b:
                    out.write(b'%x\r\n' % len(b) + bytes(b) + b'\r\n')
                return len(b)
        stream = Chunks()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            base = os.path.dirname(real.rstrip('/'))
            for top, dirs, files in os.walk(real):
                dirs[:] = [x for x in dirs if not os.path.islink(os.path.join(top, x))]
                for fn in files:
                    full = os.path.join(top, fn)
                    if os.path.islink(full) or not os.path.isfile(full):
                        continue
                    try:
                        z.write(full, os.path.relpath(full, base))
                    except OSError:
                        continue
        out.write(b'0\r\n\r\n')


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128


# ---------------------------------------------------------------------------
# The daemon
# ---------------------------------------------------------------------------
class Daemon:
    def __init__(self):
        # A database server not answering yet (started after this, or away):
        # waited for, said in the log, not a crash in a loop (otp's).
        while True:
            try:
                self.store = Store(DB_FILE)
                break
            except DbError as e:
                LOG_TO_STDERR[0] = True
                log_sparing('db-start', 'the database does not open yet - trying again every 5 s: %s' % e, 'error', 300)
                time.sleep(5)
        config_rebuild(self.store)
        self.auth = Auth(self.store)
        self.terms = Terms(self.store)
        self.trials = Trials(self)
        self.upgrades = Upgrades(self)
        self.token = ''
        self.started = time.time()
        self.osup_checking = False
        self.stop = threading.Event()
        self.notifying = threading.Lock()

    def write_token(self):
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        try:
            gid = grp.getgrnam(WEB_GROUP).gr_gid
        except KeyError:
            gid = None
        if gid is not None:
            try:
                os.chown(str(RUN_DIR), 0, gid)
                os.chmod(str(RUN_DIR), 0o750)
            except OSError:
                pass
        write_atomic(TOKEN_FILE, self.token + '\n', mode=0o640, gid=gid)
        write_atomic(RUN_DIR / 'api-port', '%d\n' % int(CONFIG.get('api_port') or 9871), mode=0o644, gid=gid)

    def first_account(self):
        if self.store.users():
            return
        pw = new_password()
        self.auth.add_user('admin', pw, 'admin', '', must_change=True, by='the first start')
        write_atomic(STATE_DIR / 'first-login.txt', 'name: admin\npassword: %s\n' % pw, mode=0o600)
        log('there was no account: admin was made, its password is in %s' % (STATE_DIR / 'first-login.txt'), 'warn')

    def mail_going(self):
        """The outgoing mail, every few seconds: what waits tried again."""
        try:
            texts_from_before(self.store)
        except Exception as e:                          # noqa: BLE001
            log('the message texts of 1.0.5 could not be carried over: %s' % e, 'warn')
        while not self.stop.wait(5):
            try:
                mailq_tick(self.store)
            except Exception as e:                      # noqa: BLE001
                log_sparing('mailq', 'the outgoing mail: %s' % str(e).split('\n')[0][:200], 'warn')

    def housekeeping(self):
        n = 0
        while not self.stop.wait(15):
            n += 1
            try:
                self.trials.tick()
                osup_tick(self)
                if n % 4 == 0:
                    config_rebuild(self.store)          # a setting changed on the command line
                    self.auth.tidy()
                    self.terms.sync()
                if n % 40 == 1:
                    keep = float(CONFIG.get('retain_events_days') or 180) * 86400
                    self.store.x('DELETE FROM events WHERE at < ?', (time.time() - keep,))
                    pass
                    if (STATE_DIR / 'first-login.txt').exists():
                        u = self.store.user('admin')
                        if not u or not u['must_change']:
                            (STATE_DIR / 'first-login.txt').unlink()
                if n % 20 == 2:
                    self.upgrades.tick()
                if n % 20 == 5:
                    db_nightly(self.store)
                if n % 4 == 1:
                    rb_tick(self)
                if n % 4 == 3 and not self.notifying.locked():
                    threading.Thread(target=self.notify_once, daemon=True).start()
            except Exception as e:                      # noqa: BLE001
                log_sparing('house', 'housekeeping: %s\n%s' % (e, traceback.format_exc()))

    def notify_once(self):
        with self.notifying:
            try:
                notify_tick(self.store)
            except Exception as e:                      # noqa: BLE001
                log_sparing('notify', 'the notices: %s' % e)

    def run(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_TO_FILE[0] = True
        LOG_TO_STDERR[0] = True
        IS_DAEMON[0] = True
        STORE_NOW['store'] = self.store
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(str(STATE_DIR), 0o711)
        port = int(CONFIG.get('api_port') or 9871)
        Handler.daemon = self
        # Bound first: a second daemon that cannot have the port must not
        # write a token of its own over the running one's.
        srv = Server(('127.0.0.1', port), Handler)
        self.write_token()
        versions_ran_note(self.store)
        self.first_account()
        log('ai %s started: the API on 127.0.0.1:%d, the database %s' % (__version__, port, self.store.db.where()))
        self.store.add_event('starting and stopping', 'ai %s started on %s' % (__version__, host_name()), 'info')
        try:
            tls_reapply_if_needed(self.store)
        except Exception as e:                          # noqa: BLE001
            log('the TLS of the pages: %s' % e, 'warn')
        try:
            power_back(self)
        except Exception as e:                          # noqa: BLE001
            log('after a restart: %s' % e, 'warn')
        threading.Thread(target=self.housekeeping, name='ai-house', daemon=True).start()
        threading.Thread(target=self.mail_going, name='ai-mailq', daemon=True).start()

        def bye(sig, _frame):
            log('stopping (signal %d); the terminals go on running' % sig)
            self.stop.set()
            threading.Thread(target=srv.shutdown, daemon=True).start()
        signal.signal(signal.SIGTERM, bye)
        signal.signal(signal.SIGINT, bye)
        signal.signal(signal.SIGHUP, lambda s, f: config_rebuild(self.store))
        srv.serve_forever(poll_interval=0.5)
        self.store.add_event('starting and stopping', 'ai %s stopped' % __version__, 'info')


# ---------------------------------------------------------------------------
# Colour - as isemon does it
# ---------------------------------------------------------------------------
# colorama when it is installed, and the same escape sequences written by hand
# when it is not. A nicety, never a dependency: a server being put right at two
# in the morning is not the one to find that ai will not start because a
# colour library is missing. colorama adds a Windows console, a
# terminal reset however the program ends, and nothing else on Linux.
try:
    import colorama
    from colorama import Fore as _Fore, Style as _Style
    HAVE_COLORAMA = True
except Exception:                       # not installed, or installed broken
    colorama = None
    HAVE_COLORAMA = False

    class _Fore(object):
        RED = '\033[31m'; GREEN = '\033[32m'; YELLOW = '\033[33m'
        BLUE = '\033[34m'; MAGENTA = '\033[35m'; CYAN = '\033[36m'
        WHITE = '\033[37m'; RESET = '\033[39m'

    class _Style(object):
        BRIGHT = '\033[1m'; DIM = '\033[2m'; NORMAL = '\033[22m'
        RESET_ALL = '\033[0m'

_COLORAMA_READY = False


def write_private(path, text):
    """A file only root reads, so from its first byte (1.0.94)."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(text)


def start_colour():
    global _COLORAMA_READY
    if _COLORAMA_READY or not HAVE_COLORAMA:
        return
    _COLORAMA_READY = True
    try:
        if hasattr(colorama, 'just_fix_windows_console'):
            colorama.just_fix_windows_console()
        else:
            colorama.init()
    except Exception:
        pass


ANSI = re.compile(r'\033\[[0-9;]*m')
TERM_CTL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]')


def term_safe(text):
    """What came from outside, safe on a terminal (1.0.139): a User-Name or a
    reason from a packet carried escapes that cleared the screen, set the
    title or wrote the clipboard. Colours are kept; any other control
    character is shown as \\xNN."""
    t = str(text)
    out, at = [], 0
    for m in ANSI.finditer(t):
        out.append(TERM_CTL.sub(lambda c: '\\x%02x' % ord(c.group(0)), t[at:m.start()]))
        out.append(m.group(0))
        at = m.end()
    out.append(TERM_CTL.sub(lambda c: '\\x%02x' % ord(c.group(0)), t[at:]))
    return ''.join(out)


def plain_len(text):
    """How wide something looks, the colour taken out."""
    return len(ANSI.sub('', str(text)))


def plain_pad(text, width):
    return str(text) + ' ' * max(0, width - plain_len(text))


class Palette(object):
    """Every colour the command line uses, in one place."""

    def __init__(self, on):
        self.on = bool(on)
        if self.on:
            start_colour()

        def code(*parts):
            return ''.join(parts) if self.on else ''

        self.c_ok = code(_Fore.GREEN)
        self.c_warn = code(_Fore.YELLOW)
        self.c_bad = code(_Style.BRIGHT, _Fore.RED)
        self.c_info = code(_Fore.CYAN)
        self.c_head = code(_Style.BRIGHT, _Fore.CYAN)
        self.c_key = code(_Fore.WHITE)
        self.c_addr = code(_Fore.MAGENTA)
        self.c_hi = code(_Style.BRIGHT)
        self.c_dim = code(_Style.DIM)
        self.off = code(_Style.RESET_ALL)
        try:
            self.width = max(60, min(120, shutil.get_terminal_size((100, 24)).columns))
        except Exception:
            self.width = 100

    def paint(self, text, colour):
        if not self.on or not colour:
            return str(text)
        return '%s%s%s' % (colour, text, self.off)

    def good(self, t):
        return self.paint(t, self.c_ok)

    def bad(self, t):
        return self.paint(t, self.c_bad)

    def warn(self, t):
        return self.paint(t, self.c_warn)

    def info(self, t):
        return self.paint(t, self.c_info)

    def dim(self, t):
        return self.paint(t, self.c_dim)

    soft = dim

    def head(self, t):
        return self.paint(t, self.c_head)

    def bold(self, t):
        return self.paint(t, self.c_hi)

    hi = bold

    def addr(self, t):
        return self.paint(t, self.c_addr)

    def ok_line(self, t):
        return (self.good('✔ ') if self.on else '[ ok ] ') + str(t)

    def warn_line(self, t):
        return (self.warn('! ') if self.on else '[warn] ') + str(t)

    def bad_line(self, t):
        return (self.bad('✘ ') if self.on else '[fail] ') + str(t)


def colour_wanted(no_color=False, stream=None):
    """What the person asked for, then NO_COLOR, then FORCE_COLOR, then the
    terminal itself - in that order, as isemon decides it."""
    if no_color or os.environ.get('NO_COLOR') is not None:
        return False
    if os.environ.get('FORCE_COLOR') or os.environ.get('CLICOLOR_FORCE'):
        return True
    if str(os.environ.get('TERM') or '').lower() in ('dumb', '') \
            and not os.environ.get('TERM_PROGRAM'):
        return False
    try:
        return bool((stream or sys.stdout).isatty())
    except Exception:
        return False


# ---- colour in every output (1.0.132) ---------------------------------------------
# With colour on, every table and every line the command line prints is
# coloured the same way - tables by their cells, other lines as they read:
# "key: value", addresses, times, and the words that say how a thing is.
# Whatever already carries its own colour is left as it is.
TABLE_PAL = None
TONE_GOOD = {'on', 'yes', 'active', 'ok', 'accept', 'accepted', 'running', 'answering',
             'in place', 'in service', 'done', 'synchronised', 'healthy', 'up', 'enabled',
             'signed in', 'good', 'valid', 'sent', 'taken', 'checked'}
TONE_BAD = {'off', 'no', 'reject', 'rejected', 'failed', 'fail', 'error', 'gone', 'down',
            'locked', 'locked out', 'expired', 'not answering', 'inactive', 'dead', 'disabled',
            'refused', 'missing', 'broken', 'lost', 'crit'}
TONE_WARN = {'pending', 'waiting', 'maintenance', 'in maintenance', 'paused', 'warn',
             'warning', 'not set up', 'unknown', 'stale', 'not yet'}
TONE_DIM = {'never', '-', '–', '(none)', 'none', 'as they come', 'not set', ''}
RE_ADDR = re.compile(r'(?<![\w.:])(\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?(?::\d{1,5})?)(?![\w.])')
RE_TIME = re.compile(r'\b(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})([ T]\d{2}:\d{2}(?::\d{2})?)?\b')


def tone_cell(text, pal):
    """One value coloured by what it says."""
    t = str(text)
    if not pal or not pal.on or ANSI.search(t):
        return t
    low = t.strip().lower()
    if low in TONE_GOOD:
        return pal.good(t)
    if low in TONE_BAD:
        return pal.bad(t)
    if low in TONE_WARN:
        return pal.warn(t)
    if low in TONE_DIM:
        return pal.dim(t)
    if RE_TIME.fullmatch(t.strip()):
        return pal.dim(t)
    return tone_words(t, pal)


def tone_words(t, pal):
    """Addresses and times inside a text."""
    t = RE_ADDR.sub(lambda m: pal.addr(m.group(1)), t)
    return RE_TIME.sub(lambda m: pal.dim(m.group(0)), t)


def _cut(text, width):
    """`text` no wider than `width` on the screen, its colour kept or - when it
    has to be cut - taken off."""
    if plain_len(text) <= width:
        return text
    return ANSI.sub('', text)[:width]


def table(rows, heads, widths=None):
    if not rows:
        return '  (none)'
    pal = TABLE_PAL
    cells = [[tone_cell(term_safe(c), pal) for c in r] for r in rows]
    cols = list(zip(*([heads] + [[str(c) for c in r] for r in cells])))
    w = widths or [min(48, max(plain_len(x) for x in col)) for col in cols]
    head = '  ' + '  '.join(h.upper().ljust(w[i]) for i, h in enumerate(heads))
    out = [pal.head(head) if pal and pal.on else head]
    for r in cells:
        out.append('  ' + '  '.join(plain_pad(_cut(str(c), w[i]), w[i])
                                    for i, c in enumerate(r)))
    return '\n'.join(out)


class ColourOut(object):
    """stdout, every line coloured on its way out unless it is already."""
    LINE_KV = re.compile(r'^(\s*)([A-Za-z][\w .()/\'-]{0,40}?)(:\s+|\s{2,})(\S.*)$')

    def __init__(self, stream, pal):
        self.s, self.pal, self.buf = stream, pal, ''

    def _line(self, ln):
        p = self.pal
        ln = term_safe(ln)
        if not p.on or not ln.strip() or ANSI.search(ln):
            return ln
        m = self.LINE_KV.match(ln)
        if m and not ln.lstrip().startswith(('$', '#')):
            return '%s%s%s%s' % (m.group(1), p.info(m.group(2)), m.group(3),
                                 tone_cell(m.group(4), p))
        return tone_words(ln, p)

    def write(self, text):
        self.buf += str(text)
        if '\n' in self.buf:
            done, self.buf = self.buf.rsplit('\n', 1)
            self.s.write('\n'.join(self._line(x) for x in done.split('\n')) + '\n')
        return len(text)

    def flush(self):
        if self.buf:
            self.s.write(self.buf)
            self.buf = ''
        self.s.flush()

    def __getattr__(self, name):
        return getattr(self.s, name)


def ask_password(prompt='password', twice=True, env='AI_PASSWORD'):
    said = os.environ.get(env) if env else None
    if said:
        return said
    first = getpass.getpass('%s: ' % prompt)
    if twice:
        again = getpass.getpass('and again: ')
        if first != again:
            raise SystemExit('those two are not the same')
    return first


class HelpfulParser(argparse.ArgumentParser):
    """An ArgumentParser whose help is isemon's: two columns, in colour.
    Anything going wrong in the drawing falls back to argparse's own."""
    palette = None

    def format_help(self):
        try:
            return help_text(self, self.palette or Palette(False))
        except Exception:
            return super(HelpfulParser, self).format_help()

    def error(self, message):
        pal = self.palette or Palette(False)
        sys.stderr.write('%s\n' % pal.bad_line(message))
        sys.stderr.write(pal.dim('try:  ai --help') + '\n')
        raise SystemExit(2)


def help_option_words(action):
    names = ', '.join(action.option_strings)
    if action.nargs == 0:
        return names, ''
    if action.metavar:
        meta = ' '.join(action.metavar) if isinstance(action.metavar, tuple) else action.metavar
    elif action.choices:
        meta = '{%s}' % ','.join(str(c) for c in action.choices)
    else:
        meta = action.dest.upper()
    if action.nargs in ('+', '*'):
        meta += ' ...'
    return names, meta


def help_text(parser, pal):
    """The whole of --help, in the width of this terminal."""
    import textwrap
    width = pal.width
    out = ['%s %s' % (pal.head('ai'), pal.bold(__version__)),
           pal.dim('Claude Code on this server, from a web browser - and the server looked after '
                   'from the same pages - in one Python file'),
           '',
           '%s ai %s' % (pal.paint('usage:', pal.c_key), pal.dim('[--json] [--no-color] '
                                                                 '[what to do]')),
           pal.dim('       with nothing at all it says what it is doing')]
    every = [a for g in parser._action_groups for a in g._group_actions]
    left = min(34, max([len(' '.join(x for x in help_option_words(a) if x))
                        for a in every] or [20]) + 2)
    for group in parser._action_groups:
        actions = [a for a in group._group_actions if a.help != argparse.SUPPRESS]
        if not actions:
            continue
        out.append('')
        out.append(pal.head((group.title or '').upper()))
        if group.description:
            for line in textwrap.wrap(group.description, width - 2):
                out.append('  ' + pal.dim(line))
        for action in actions:
            names, meta = help_option_words(action)
            painted = pal.good(names) + (' ' + pal.warn(meta) if meta else '')
            says = action.help or ''
            if (action.default not in (None, False, '', argparse.SUPPRESS)
                    and action.nargs != 0 and action.default != []
                    and '[%s]' % action.default not in says):
                says += ' [%s]' % action.default
            lines = textwrap.wrap(says, max(24, width - left - 4)) or ['']
            if plain_len(painted) > left:
                out.append('  ' + painted)
                lines_at = 0
            else:
                out.append('  %s  %s' % (plain_pad(painted, left), lines[0]))
                lines_at = 1
            for more in lines[lines_at:]:
                out.append('  %s  %s' % (' ' * left, more))
    out.append('')
    out.append(pal.head('THINGS PEOPLE ACTUALLY TYPE'))
    wide = min(36, max(len(c.split('\n')[0]) for c, _ in HELP_EXAMPLES) + 2)
    for command, says in HELP_EXAMPLES:
        first, *rest = command.split('\n')
        if len(first) + 2 > wide:
            out.append('  ' + pal.info(first) + ('' if rest or not says else ''))
            for r in rest:
                out.append('  ' + pal.info(r))
            if says:
                out.append('  %s  %s' % (' ' * wide, pal.dim(says)))
        else:
            out.append('  %s%s' % (plain_pad(pal.info(first), wide), pal.dim(says)))
            for r in rest:
                out.append('  ' + pal.info(r))
    out.append('')
    for note in ('the pages are at https://<this machine>/ · the configuration is %s' % CONFIG_FILE,
                 'typed with nothing at all it is --status; systemd runs the daemon as '
                 '--daemon',
                 'colour is off when this is piped, and with --no-color or NO_COLOR=1'
                 + ('' if HAVE_COLORAMA else ' (colorama is not installed; colour is '
                                             'written by hand)')):
        for line in textwrap.wrap(note, width - 4):
            out.append('  ' + pal.dim(line))
    out.append('')
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# The console: ai run by its menus, on the server's own screen
# ---------------------------------------------------------------------------
# `ai --console` - and, with `ai --console-at-login on`, what root sees first
# after signing in at the console or over SSH. Taken from otp's console
# (otp 1.0.161) whole: the same screen, the same windows, forms, lists and
# live views; only the menus are ai's. Everything is done by the same
# `ai ...` commands the command line has, each run as it would be typed, so
# nothing here can do more than they do. q leaves it for the ordinary shell;
# ! opens a shell and comes back when it is closed. Coloured with colorama
# when present.
import textwrap  # noqa: E402


class ConsoleBack(Exception):
    """Back to the menu."""


class Console(object):
    def __init__(self, pal):
        self.pal = pal
        self.me = os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0].endswith('.py')
                                  else __file__)
        try:
            __import__('readline')     # arrows and history in input()
        except ImportError:
            pass

    # ---- small things ---------------------------------------------------------------
    def cmd(self, *args, show=True):
        """`ai ARGS`, its output on the screen; its exit code."""
        argv = ai_argv() + [str(a) for a in args]
        if not self.pal.on:
            argv.append('--no-color')
        if show:
            print(self.pal.dim('$ ai ' + ' '.join(self._quote(a) for a in args)))
        try:
            return subprocess.call(argv)
        except KeyboardInterrupt:
            print()
            return 130

    def out(self, *args):
        """`ai ARGS --json`, read."""
        try:
            got = subprocess.run(ai_argv() + [str(a) for a in args] + ['--json'],
                                 capture_output=True, text=True, timeout=60)
            return json.loads(got.stdout or 'null')
        except Exception:                               # noqa: BLE001
            return None

    @staticmethod
    def _quote(a):
        a = str(a)
        return a if re.match(r'^[A-Za-z0-9_@%+=:,./-]+\Z', a) else "'%s'" % a.replace("'", "'\\''")

    # ---- keys on the ordinary terminal: Esc goes back everywhere (1.0.132) ---------
    def _raw(self):
        """The terminal's settings, to be put back; None without a terminal."""
        try:
            import termios
            return termios.tcgetattr(sys.stdin.fileno())
        except Exception:                               # noqa: BLE001
            return None

    def _restore(self, was):
        if was is None:
            return
        import termios
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, was)

    def key(self, wait=None):
        """One key, without Enter: 'esc', 'enter', 'bs', 'up'..., a character -
        or None when `wait` seconds went by without one."""
        import select
        import tty
        fd = sys.stdin.fileno()
        was = self._raw()
        try:
            if was is not None:
                # TCSANOW: what was typed ahead is kept, not thrown away.
                import termios
                tty.setcbreak(fd, termios.TCSANOW)
            r, _w, _x = select.select([fd], [], [], wait)
            if not r:
                return None
            ch = os.read(fd, 1)
            if ch == b'\x1b':
                # Alone, Esc; followed at once by more, a key's sequence.
                r, _w, _x = select.select([fd], [], [], 0.05)
                if not r:
                    return 'esc'
                rest = os.read(fd, 8)
                full = {b'[5~': 'pgup', b'[6~': 'pgdn', b'[1~': 'home', b'[4~': 'end',
                        b'[7~': 'home', b'[8~': 'end', b'[H': 'home', b'[F': 'end',
                        b'OH': 'home', b'OF': 'end'}.get(rest)
                if full:
                    return full
                return {b'[A': 'up', b'[B': 'down', b'[C': 'right', b'[D': 'left', b'OA': 'up',
                        b'OB': 'down', b'OC': 'right', b'OD': 'left'}.get(rest[:2], 'seq')
            if ch in (b'\r', b'\n'):
                return 'enter'
            if ch in (b'\x7f', b'\x08'):
                return 'bs'
            if ch == b'\x03':
                return 'ctrl-c'
            if ch == b'\x04':
                return 'ctrl-d'
            if ch == b'\x15':
                return 'ctrl-u'
            try:
                return ch.decode('utf-8')
            except UnicodeDecodeError:
                more = ch
                while len(more) < 4:
                    more += os.read(fd, 1)
                    try:
                        return more.decode('utf-8')
                    except UnicodeDecodeError:
                        continue
                return ''
        finally:
            self._restore(was)

    def ask(self, words, default='', secret=False):
        """A line typed; Esc (or Ctrl+C) goes back to the menu. A secret shows
        a star for each character, never the characters."""
        p = self.pal
        hint = (' [%s]' % default) if default else ''
        prompt = '  %s%s: ' % (p.info(words), p.dim(hint))
        if self._raw() is None:
            try:
                got = input(prompt)
            except EOFError:
                raise ConsoleBack()
            return got.strip() or default
        sys.stdout.write(prompt)
        sys.stdout.flush()
        got = ''
        while True:
            k = self.key()
            if k in ('esc', 'ctrl-c', 'ctrl-d'):
                sys.stdout.write(p.dim('  (back)') + '\n')
                sys.stdout.flush()
                raise ConsoleBack()
            if k == 'enter':
                sys.stdout.write('\n')
                sys.stdout.flush()
                return got.strip() or default
            if k == 'bs':
                if got:
                    got = got[:-1]
                    sys.stdout.write('\b \b')
            elif k == 'ctrl-u':
                sys.stdout.write('\b \b' * len(got))
                got = ''
            elif k and len(k) == 1 and k.isprintable():
                got += k
                sys.stdout.write('*' if secret else k)
            sys.stdout.flush()

    def yes(self, words):
        return self.ask(words + ' (y/N)').lower() in ('y', 'yes', 'a', 'ano')

    def pause(self):
        sys.stdout.write(self.pal.dim('\n  Enter or Esc - back to the menu '))
        sys.stdout.flush()
        if self._raw() is None:
            try:
                input()
            except EOFError:
                pass
            return
        while self.key() not in ('enter', 'esc', 'ctrl-c', 'ctrl-d', 'q'):
            pass
        sys.stdout.write('\n')

    def stopped(self, wait):
        """In a live view: True when Esc, q or Ctrl+C was pressed within
        `wait` seconds."""
        if self._raw() is None:
            time.sleep(wait)
            return False
        return self.key(wait) in ('esc', 'q', 'ctrl-c', 'ctrl-d')

    def clear_screen(self):
        if sys.stdout.isatty():
            sys.stdout.write('\033[H\033[2J')
            sys.stdout.flush()

    # ---- the menus: a text screen, arrows and Enter (1.0.131) ----------------------
    # curses: only what changed is written, so nothing blinks; a window made
    # bigger or smaller (PuTTY's too) is drawn again to its new size. Leaving it
    # for a command's output and coming back is the one full redraw.
    HELP = ' Up/Down move   Enter choose   Esc back   ! shell   q leave '

    def status_thread(self):
        """The line at the top, asked for again every 20 s off the screen's
        thread - the menu never waits for it."""
        def look():
            while not self.closing:
                # Nothing asked while nobody sees the bar (1.0.136): in a live
                # view, a page or a shell - asked again on the way back.
                if self.plain and not self.st_now:
                    time.sleep(0.5)
                    continue
                self.st_now = False
                st = self.out('--status') or {}
                active = '?'
                if shutil.which('systemctl'):
                    try:
                        active = subprocess.run(['systemctl', 'is-active', 'ai'],
                                                capture_output=True, text=True,
                                                timeout=10).stdout.strip() or '?'
                    except Exception:                   # noqa: BLE001
                        pass
                self.st = dict(st, _active=active)
                self.st_gen += 1
                for _ in range(60):
                    if self.closing or self.st_now:
                        break
                    time.sleep(0.5)
        threading.Thread(target=look, name='ai-console-status', daemon=True).start()

    def _put(self, y, x, text, attr=0):
        try:
            h, w = self.scr.getmaxyx()
            if y < 0 or y >= h or x >= w:
                return
            self.scr.addnstr(y, x, str(text), max(0, w - x - (1 if y == h - 1 else 0)), attr)
        except Exception:                               # noqa: BLE001 - the edge
            pass

    def _colours(self):
        c = self.curses
        self.A = {'head': c.A_REVERSE, 'sel': c.A_REVERSE | c.A_BOLD, 'ok': c.A_BOLD,
                  'warn': c.A_BOLD, 'bad': c.A_BOLD, 'dim': c.A_DIM, 'key': c.A_BOLD,
                  'title': c.A_BOLD}
        if not c.has_colors():
            return
        try:
            c.start_color()
            try:
                c.use_default_colors()
                bg = -1
            except Exception:                           # noqa: BLE001
                bg = c.COLOR_BLACK
            c.init_pair(1, c.COLOR_BLACK, c.COLOR_CYAN)
            c.init_pair(2, c.COLOR_BLACK, c.COLOR_GREEN)
            c.init_pair(3, c.COLOR_GREEN, bg)
            c.init_pair(4, c.COLOR_YELLOW, bg)
            c.init_pair(5, c.COLOR_RED, bg)
            c.init_pair(6, c.COLOR_CYAN, bg)
            self.A.update(head=c.color_pair(1), sel=c.color_pair(2) | c.A_BOLD,
                          ok=c.color_pair(3) | c.A_BOLD, warn=c.color_pair(4) | c.A_BOLD,
                          bad=c.color_pair(5) | c.A_BOLD, key=c.color_pair(6) | c.A_BOLD)
        except Exception:                               # noqa: BLE001
            pass

    def draw(self, title, items, sel, top, path):
        scr, A = self.scr, self.A
        scr.erase()
        h, w = scr.getmaxyx()
        st = self.st or {}
        # The bar at the top: what this is, and how it is.
        self._put(0, 0, ' ' * w, A['head'])
        left = ' ai %s  %s ' % (__version__, socket.gethostname())
        self._put(0, 0, left, A['head'] | self.curses.A_BOLD)
        active = st.get('_active') or '...'
        svc = ' service %s ' % active
        self._put(0, len(left) + 1, svc, A['sel'] if active == 'active' else
                  (A['head'] if active == '...' else self.curses.A_REVERSE | A['bad']))
        bits = []
        if st.get('terms') is not None:
            bits.append('%s terminal(s) running' % st.get('terms'))
        if st.get('signed_in') is not None:
            bits.append('%s signed in' % st.get('signed_in'))
        if st.get('newer'):
            bits.append('%s is out' % st['newer'])
        y = 1
        right = ' ' + ' | '.join(bits) + ' '
        if len(left) + len(svc) + len(right) + 2 < w:
            self._put(0, w - len(right), right, A['head'])
        elif bits:
            self._put(1, 1, ' | '.join(bits), A['key'])
            y = 2
        for t in st.get('trials') or []:
            left = max(0, int(float(t.get('until') or 0) - time.time()))
            self._put(y, 1, '%s waits to be kept: %d:%02d left (Firewall and access > Keep it)' % (
                {'net': 'the new network', 'fw': 'the change of the firewall',
                 'access': 'who may reach the pages'}.get(t.get('kind'), t.get('kind')),
                left // 60, left % 60), A['warn'])
            y += 1
        if st and st.get('daemon_alive') is False:
            self._put(y, 1, 'the daemon is not answering', A['bad'])
            y += 1
        for one in (st.get('problems') or [])[:max(0, min(4, h - 12))]:
            self._put(y, 1, '! ' + str(one), A['warn'])
            y += 1
        y += 1
        self._put(y, 2, path, A['dim'])
        self._put(y, 2 + len(path), title, A['title'])
        y += 2
        # The items, a window of them when the screen is short.
        room = max(1, h - y - 2)
        if sel < top:
            top = sel
        if sel >= top + room:
            top = sel - room + 1
        width = max(20, min(w - 6, max(len(it[1]) for it in items) + 10))
        for n, it in enumerate(items[top:top + room]):
            i = top + n
            line = ' %3s  %s' % (it[0], it[1])
            line = line + ' ' * max(0, width - len(line))
            if i == sel:
                self._put(y + n, 2, line, A['sel'])
            else:
                self._put(y + n, 2, ' %3s' % it[0], A['key'])
                self._put(y + n, 8, it[1])
        if top > 0:
            self._put(y - 1, 4, '^ more', A['dim'])
        if top + room < len(items):
            self._put(y + room, 4, 'v more', A['dim'])
        self._put(h - 1, 0, ' ' * (w - 1), A['head'])
        self._put(h - 1, 0, self.HELP[:w - 1], A['head'])
        scr.noutrefresh()
        return top

    def menu(self, title, items, path=''):
        """items: [(key, words, function[, 'plain'])]; returns 'back' or 'quit'."""
        c = self.curses
        sel, top, typed, typed_at, seen = 0, 0, '', 0.0, -1
        while True:
            if self.plain:
                # Back from a command's screen: drawn whole, once.
                c.reset_prog_mode()
                self.scr.clear()
                self.plain = False
                self.st_now = True
            top = self.draw(title, items, sel, top, path)
            self.curses.doupdate()
            self.backdrop = (lambda _s=sel, _t=top: self.draw(title, items, _s, _t, path))
            seen = self.st_gen
            self.scr.timeout(500)
            while True:
                k = self.scr.getch()
                if k != -1 or self.st_gen != seen:
                    break
                # The window's size looked at too (PuTTY and others whose
                # change is not always told): drawn again to the new one.
                try:
                    size = os.get_terminal_size(sys.__stdout__.fileno())
                    if (size.lines, size.columns) != self.scr.getmaxyx():
                        c.resizeterm(size.lines, size.columns)
                        k = c.KEY_RESIZE
                        break
                except (OSError, ValueError, c.error):
                    pass
            if k == -1:
                continue
            if k == 27:
                # An arrow some terminals send as ESC [ B rather than as the
                # key the terminal description names: read whole here.
                self.scr.nodelay(True)
                k2 = self.scr.getch()
                if k2 in (ord('['), ord('O')):
                    k3 = self.scr.getch()
                    k = {ord('A'): c.KEY_UP, ord('B'): c.KEY_DOWN, ord('C'): c.KEY_RIGHT,
                         ord('D'): c.KEY_LEFT, ord('H'): c.KEY_HOME,
                         ord('F'): c.KEY_END}.get(k3, -1)
                    if k3 in (ord('5'), ord('6')):            # PgUp / PgDn: ESC [ 5 ~
                        self.scr.getch()
                        k = c.KEY_PPAGE if k3 == ord('5') else c.KEY_NPAGE
                    if k == -1:
                        continue
                elif k2 != -1:
                    c.ungetch(k2)
                self.scr.nodelay(False)
            if k == c.KEY_RESIZE:
                try:
                    c.update_lines_cols()
                except Exception:                       # noqa: BLE001
                    pass
                self.scr.clear()
                continue
            if k in (c.KEY_UP, ord('k')):
                sel = (sel - 1) % len(items)
            elif k in (c.KEY_DOWN, ord('j'), 9):
                sel = (sel + 1) % len(items)
            elif k in (c.KEY_HOME, c.KEY_PPAGE):
                sel = 0
            elif k in (c.KEY_END, c.KEY_NPAGE):
                sel = len(items) - 1
            elif k in (27, c.KEY_LEFT, c.KEY_BACKSPACE, 127, 8):
                if path:
                    return 'back'
            elif k in (ord('q'), ord('Q')):
                return 'quit'
            elif k == ord('!'):
                self.go_plain(self.shell)
            elif ord('0') <= k <= ord('9'):
                now = time.time()
                typed = (typed if now - typed_at < 1.0 else '') + chr(k)
                typed_at = now
                hit = [i for i, it in enumerate(items) if it[0] == typed]
                if hit:
                    sel = hit[0]
                    # One that no longer number can grow into: chosen at once.
                    if not any(it[0].startswith(typed) and it[0] != typed for it in items):
                        k = 10
                        typed = ''
            if k in (10, 13, c.KEY_ENTER, c.KEY_RIGHT):
                it = items[sel]
                # Run on the text screen - its questions are windows there
                # (1.0.135); only a view of its own ('plain') leaves it.
                if len(it) > 3 and it[3] == 'plain':
                    r = self.go_plain(it[2])
                else:
                    try:
                        r = it[2]()
                    except ConsoleBack:
                        r = None
                if r == 'quit':
                    return 'quit'

    def go_plain(self, fn):
        """`fn` on the ordinary terminal - a command's output, a question, the
        live log - and back to the screen after it."""
        c = self.curses
        c.def_prog_mode()
        c.endwin()
        self.plain = True
        # A clean screen for it - not what the last command left there.
        if sys.stdout.isatty():
            sys.stdout.write('\033[H\033[2J\033[3J')
            sys.stdout.flush()
        try:
            return fn()
        except ConsoleBack:
            return None
        except KeyboardInterrupt:
            print()
            return None

    def run(self):
        main = [
            ('1', 'Status and checks', self.m_status),
            ('2', 'Live log', self.m_live_log),
            ('3', 'Terminals (Claude Code, shells)', self.m_terms),
            ('4', 'Accounts of the pages', self.m_accounts),
            ('5', 'Settings', self.m_settings),
            ('6', 'Firewall and access', self.m_fw),
            ('7', 'The server: network, time, updates, SSH keys, certificate, power', self.m_server),
            ('8', 'Upgrades', self.m_upgrades),
            ('9', 'The service', self.m_service),
            ('0', 'Data: copies of the database, backups, mail', self.m_data),
        ]
        os.environ.setdefault('ESCDELAY', '25')     # Esc at once, not after a second
        # Lines and blocks drawn as UTF-8 characters, as PuTTY in UTF-8 shows
        # them - not the line-drawing set, which it draws as letters.
        os.environ.setdefault('NCURSES_NO_UTF8_ACS', '1')
        try:
            import locale
            locale.setlocale(locale.LC_ALL, '')
        except Exception:                               # noqa: BLE001
            pass
        import curses
        self.curses = curses
        self.st, self.st_gen, self.st_now, self.closing, self.plain = {}, 0, False, False, False

        def body(scr):
            self.scr = scr
            try:
                curses.curs_set(0)
            except Exception:                           # noqa: BLE001
                pass
            scr.keypad(True)
            self._colours()
            self.status_thread()
            # It opens on the live log, every line (as otp's); Esc: the menu.
            if os.environ.get('AI_CONSOLE_START', 'log') == 'log':
                self.go_plain(lambda: self.live_log(''))
            self.menu('Main menu', main)
        try:
            curses.wrapper(body)
        finally:
            self.closing = True
        print(self.pal.dim('  The ai console is closed - `ai --console` opens it again.'))
        return 0

    def shell(self):
        sh = os.environ.get('SHELL') or '/bin/bash'
        print(self.pal.dim('  A shell - exit (or Ctrl+D) comes back to the ai console.'))
        try:
            subprocess.call([sh], env=dict(os.environ, AI_CONSOLE='1'))
        except KeyboardInterrupt:
            pass

    def sub(self, title, items):
        r = self.menu(title, items, path='Main menu > ')
        return 'quit' if r == 'quit' else None

    # ---- long output: a screen of its own, scrolled (1.0.134) -------------------
    # As the fullscreen pickers of video_tools: the terminal is not scrolled, a
    # window (top) into the lines is; each frame is one write (home, each line
    # cleared to its end, the rest cleared) so nothing blinks, and the scroll
    # bar is drawn after it into the last column. Arrows, PgUp/PgDn, Home/End,
    # Space; Esc, q or Enter back. A window made bigger or smaller is drawn
    # again to its size.
    def capture(self, argv, env=None):
        """What a command writes, its colour kept: (text, exit code)."""
        e = dict(os.environ, **(env or {}))
        if self.pal.on:
            e.update(FORCE_COLOR='1', SYSTEMD_COLORS='1')
        e['COLUMNS'] = str(max(60, self._cols() - 2))
        try:
            got = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=e, timeout=1800)
            # Made safe here whatever the colour (1.0.146): with colour off the
            # command wrote what a packet carried as it came, and page() put it
            # on root's terminal - the title, the clipboard, the screen.
            return term_safe(got.stdout.decode('utf-8', 'replace')), got.returncode
        except subprocess.TimeoutExpired:
            return 'it took more than 30 minutes and was stopped', 124
        except OSError as ex:
            return str(ex), 127

    @staticmethod
    def _cols():
        try:
            return os.get_terminal_size(sys.__stdout__.fileno()).columns
        except (OSError, ValueError):
            return 100

    @staticmethod
    def _fit(line, width):
        """`line` cut to `width` columns on the screen, its colours kept."""
        out, seen = [], 0
        for part in re.split(r'(\x1b\[[0-9;?]*[A-Za-z])', line):
            if not part:
                continue
            if part.startswith('\x1b['):
                out.append(part)
                continue
            if seen + len(part) > width:
                out.append(part[:max(0, width - seen)])
                out.append('\x1b[0m')
                return ''.join(out)
            out.append(part)
            seen += len(part)
        return ''.join(out) + ('\x1b[0m' if '\x1b[' in line else '')

    def page(self, title, text):
        p = self.pal
        lines = [ln.expandtabs(8).replace('\r', '') for ln in text.rstrip('\n').split('\n')] or ['']
        tty = self._raw() is not None and sys.stdout.isatty()
        if not tty:
            print(text)
            return
        out = sys.stdout
        out.write('\x1b[?1049h\x1b[?25l')
        top, size = 0, None
        try:
            while True:
                try:
                    sz = os.get_terminal_size(sys.__stdout__.fileno())
                    cols, rows = max(40, sz.columns), max(8, sz.lines)
                except OSError:
                    cols, rows = 100, 30
                avail = max(3, rows - 2)
                top = max(0, min(top, max(0, len(lines) - avail)))
                end = min(len(lines), top + avail)
                head = ' %s ' % title
                where = ' %d-%d of %d ' % (top + 1, end, len(lines)) if len(lines) > avail \
                    else ' %d lines ' % len(lines)
                bar = (head + ' ' * max(0, cols - len(head) - len(where)) + where)[:cols]
                foot = (' Up/Down PgUp/PgDn Home/End scroll   Esc, q or Enter back ')[:cols - 1]
                body = [self._fit(ln, cols - 2) for ln in lines[top:end]]
                body += [''] * (avail - len(body))
                frame = ['\x1b[7m' + bar + '\x1b[0m' if p.on else bar] + body + \
                    ['\x1b[7m' + foot + ' ' * max(0, cols - 1 - len(foot)) + '\x1b[0m'
                     if p.on else foot]
                out.write('\x1b[H' + '\n'.join(ln + '\x1b[K' for ln in frame) + '\x1b[J')
                self._scrollbar(2, avail, len(lines), avail, top, cols)
                out.flush()
                size = (cols, rows)
                while True:
                    k = self.key(0.3)
                    if k is not None:
                        break
                    try:
                        sz = os.get_terminal_size(sys.__stdout__.fileno())
                        if (max(40, sz.columns), max(8, sz.lines)) != size:
                            break
                    except OSError:
                        pass
                if k in ('esc', 'q', 'enter', 'ctrl-c', 'ctrl-d'):
                    return
                if k in ('up', 'k'):
                    top -= 1
                elif k in ('down', 'j'):
                    top += 1
                elif k in ('pgup', 'b'):
                    top -= avail - 1
                elif k in ('pgdn', ' ', 'f'):
                    top += avail - 1
                elif k in ('home', 'g'):
                    top = 0
                elif k in ('end', 'G'):
                    top = len(lines)
        finally:
            out.write('\x1b[?25h\x1b[?1049l')
            out.flush()

    def _scrollbar(self, base_row, nrows, total, visible, top, cols):
        if total <= visible or nrows <= 0:
            return
        thumb = max(1, min(nrows, round(nrows * visible / total)))
        span = nrows - thumb
        denom = max(1, total - visible)
        tstart = max(0, min(span, round(span * (top / denom))))
        on = self.pal.on
        parts = ['\x1b[?7l']
        for r in range(nrows):
            hit = tstart <= r < tstart + thumb
            g = '\u2588' if hit else '\u2502'
            if on:
                g = ('\x1b[36m' if hit else '\x1b[2m') + g + '\x1b[0m'
            parts.append('\x1b[%d;%dH%s' % (base_row + r, cols, g))
        parts.append('\x1b[?7h')
        sys.stdout.write(''.join(parts))

    def show(self, *args):
        """`ai ARGS`, its output on a screen of its own."""
        # A question left empty is nothing asked for: back to the menu.
        if any(a is None or str(a).strip() == '' for a in args):
            return
        self.clear_screen()
        print(self.pal.dim('  working… $ ai ' + ' '.join(self._quote(a) for a in args)))
        argv = ai_argv() + [str(a) for a in args]
        text, rc = self.capture(argv)
        if rc not in (0, None):
            text += '\n' + self.pal.dim('(it ended with %d)' % rc)
        self.page('$ ai ' + ' '.join(self._quote(a) for a in args), text)

    def show_live(self, *args):
        """`ai ARGS` straight on the terminal - one that asks something."""
        if any(a is None or str(a).strip() == '' for a in args):
            return
        self.clear_screen()
        self.cmd(*args)
        self.pause()

    # ---- 1 status ---------------------------------------------------------------
    def m_status(self):
        def events():
            got = self.form('Events', [
                {'key': 'n', 'label': 'how many', 'kind': 'number', 'value': '40',
                 'range': (1, 5000), 'need': True},
                {'key': 'q', 'label': 'only with the words', 'help':
                 'Empty: every event. Or a name, a kind (sign-in, terminals, settings) or a word.'}])
            if got:
                self.act('--events', '--limit', got['n'], *(['--search', got['q']]
                                                             if got['q'] else []))
        return self.sub('Status and checks', [
            ('1', 'Status', lambda: self.act('--status')),
            ('2', 'Checks (tmux, Claude Code, nginx, PHP, the certificate, the firewall…)',
             lambda: self.act('--check')),
            ('3', 'Events', events),
            ('4', 'Who is signed in to the pages', lambda: self.act('--sign-ins')),
        ])

    # ---- 2 live log -------------------------------------------------------------
    LOG_TONES = {'error': 'bad', 'crit': 'bad', 'warn': 'warn', 'info': '', 'debug': 'dim'}

    def m_live_log(self):
        self.live(lambda: self.live_log(''))

    # ---- live views: scrolled, and what is typed is a grep (1.0.135) ------------
    # The log and the journal come into one screen of
    # their own: the newest at the bottom, followed while the view is at the
    # end. Up/PgUp/Home scroll back (the view then stays where it is and counts
    # what came meanwhile), End follows again; a bar on the right shows where
    # the window is. Whatever is typed filters the lines as `grep -i` does (a
    # regular expression, or the words as they are when it is not one), the
    # hits marked; Backspace takes a character back, Ctrl+U all of them. Esc
    # clears the filter first, then goes back to the menu.
    LIVE_KEEP = 20000

    def live_log(self, what=''):
        path = LOG_FILE
        st = {'f': None, 'ino': None}

        def opened():
            # Not through a link, nor stuck on a FIFO (as otp's).
            fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                import stat as _st
                if not _st.S_ISREG(os.fstat(fd).st_mode):
                    raise OSError('not a plain file')
            except OSError:
                os.close(fd)
                raise
            return os.fdopen(fd, 'r', encoding='utf-8', errors='replace')

        def first():
            try:
                f = opened()
            except OSError as e:
                return [self.pal.bad_line('%s cannot be read: %s' % (path, e))]
            st['f'] = f
            st['ino'] = os.fstat(f.fileno()).st_ino
            # Read from near the end only: a log can be gigabytes.
            f.seek(0, 2)
            start = max(0, f.tell() - 2 * 1024 * 1024)
            f.seek(start)
            got = f.read().splitlines()
            # The first line only when reading began inside it (1.0.146): a short
            # log lost its first whole line.
            if start and len(got) > 1:
                got = got[1:]
            return got[-self.LIVE_KEEP:]

        def more():
            f = st['f']
            if f is None:
                return []
            out = []
            while len(out) < 5000:
                ln = f.readline()
                if not ln:
                    break
                out.append(ln.rstrip('\n'))
            if not out:
                try:
                    if os.stat(str(path)).st_ino != st['ino']:      # rotated
                        f.close()
                        st['f'] = opened()
                        st['ino'] = os.fstat(st['f'].fileno()).st_ino
                except OSError:
                    pass
            return out
        try:
            self.live_view('Live log  %s' % path, first, more, self._log_text, what)
        finally:
            if st['f']:
                st['f'].close()

    def journal(self):
        """journalctl -u ai -f, in the live view."""
        try:
            pr = subprocess.Popen(['journalctl', '-u', 'ai', '-f', '-n', '400', '--no-pager'],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                  errors='replace')
        except OSError as e:
            self.page('journalctl', self.pal.bad_line(str(e)))
            return
        q = collections.deque()

        def pump():
            for ln in pr.stdout:
                q.append(ln.rstrip('\n'))
        threading.Thread(target=pump, daemon=True).start()

        def more():
            out = []
            while q:
                out.append(q.popleft())
            return out

        def paint(ln):
            return self._log_text(ln) if re.match(
                r'^\S+ \S+ (info|warn|error|debug|crit) ', ln) else tone_words(ln, self.pal)
        try:
            self.live_view('journalctl -u ai -f', lambda: [], more, paint, '')
        finally:
            pr.terminate()
            try:
                pr.wait(3)
            except Exception:                           # noqa: BLE001
                pr.kill()

    @staticmethod
    def _grep(find):
        """What is typed as `grep -i` takes it: a test of one line."""
        if not find:
            return lambda s: True
        try:
            rx = re.compile(find, re.I)
            return lambda s: rx.search(s) is not None
        except (re.error, OverflowError, RecursionError):   # a{9999999999} too (1.0.139)
            low = find.lower()
            return lambda s: low in s.lower()

    def _mark(self, coloured, find):
        """The hits of `find` shown reversed - in the text between the colours."""
        if not find or not self.pal.on:
            return coloured
        try:
            rx = re.compile(find, re.I)
        except (re.error, OverflowError, RecursionError):
            rx = re.compile(re.escape(find), re.I)
        out = []
        for part in re.split(r'(\x1b\[[0-9;?]*[A-Za-z])', coloured):
            if part.startswith('\x1b['):
                out.append(part)
            elif part:
                out.append(rx.sub(lambda m: '\x1b[7m' + m.group(0) + '\x1b[27m'
                                  if m.group(0) else '', part))
        return ''.join(out)

    @staticmethod
    def _slice(line, start, width):
        """Columns start..start+width of `line` on the screen, its colours kept."""
        out, seen = [], 0
        end = start + width
        for part in re.split(r'(\x1b\[[0-9;?]*[A-Za-z])', line):
            if not part:
                continue
            if part.startswith('\x1b['):
                out.append(part)
                continue
            a, b = seen, seen + len(part)
            if b > start and a < end:
                out.append(part[max(0, start - a):max(0, end - a)])
            seen = b
        return ''.join(out) + ('\x1b[0m' if '\x1b[' in line else '')

    def live_view(self, title, first, more, paint, find=''):
        """The live screen: `first()` the lines there are, `more()` those come
        since (asked a few times a second), `paint(line)` its colours."""
        p = self.pal
        if self._raw() is None or not sys.stdout.isatty():
            for ln in first() + more():
                print(ln)
            return
        import termios
        import tty
        fd = sys.stdin.fileno()
        was = termios.tcgetattr(fd)
        out = sys.stdout
        lines = []                       # (plain, coloured)

        def add(raw):
            for ln in raw:
                ln = term_safe(ln.expandtabs(8).replace('\r', ''))
                col = (paint(ln) if paint else ln) if p.on else self._plain_text(ln)
                lines.append((self._plain_text(col), col))
        add(first())
        test = self._grep(find)
        hits = [i for i, x in enumerate(lines) if test(x[0])]
        top, follow, xoff, new, dirty, size = 0, True, 0, 0, True, None
        tty.setcbreak(fd, termios.TCSANOW)
        out.write('\x1b[?1049h\x1b[?25l')
        try:
            while True:
                came = more()
                if came:
                    n0 = len(lines)
                    add(came)
                    got = [i for i in range(n0, len(lines)) if test(lines[i][0])]
                    hits += got
                    if not follow:
                        new += len(got)
                    if len(lines) > self.LIVE_KEEP * 1.25:
                        cut = len(lines) - self.LIVE_KEEP
                        gone = sum(1 for i in hits if i < cut)
                        del lines[:cut]
                        hits = [i - cut for i in hits if i >= cut]
                        top = max(0, top - gone)
                    dirty = dirty or bool(got)
                try:
                    sz = os.get_terminal_size(sys.__stdout__.fileno())
                    cols, rows = max(40, sz.columns), max(8, sz.lines)
                except OSError:
                    cols, rows = 100, 30
                if (cols, rows) != size:
                    size, dirty = (cols, rows), True
                avail = max(3, rows - 2)
                last = max(0, len(hits) - avail)
                if follow:
                    top = last
                top = max(0, min(top, last))
                if dirty:
                    end = min(len(hits), top + avail)
                    where = (' %d-%d of %d ' % (top + 1, end, len(hits))) if hits else ' 0 '
                    state = ' following ' if follow else (' PAUSED%s ' % (
                        ', %d new below' % new if new else ''))
                    head = ' %s ' % title
                    gp = '  grep -i: %s_ ' % find if find else '  type to grep '
                    right = state + where
                    bar = (head + gp)[:max(0, cols - len(right))]
                    bar = bar + ' ' * max(0, cols - len(bar) - len(right)) + right
                    foot = (' type: grep (any case)  Bksp  Ctrl+U clear   Up/Down PgUp/PgDn '
                            'Home  End: follow   Left/Right  Esc back ')[:cols - 1]
                    body = [self._slice(self._mark(lines[i][1], find), xoff, cols - 2)
                            for i in hits[top:end]]
                    if not hits:
                        body = ['', '   ' + (p.dim('nothing with "%s" yet' % find) if find
                                             else p.dim('nothing yet'))]
                    body += [''] * (avail - len(body))
                    inv = (lambda t: '\x1b[7m' + t + '\x1b[0m') if p.on else (lambda t: t)
                    tone = '\x1b[33m' if (not follow and p.on) else ''
                    frame = [tone + inv(bar[:cols])] + body[:avail] + \
                        [inv(foot + ' ' * max(0, cols - 1 - len(foot)))]
                    out.write('\x1b[H' + '\n'.join(ln + '\x1b[K' for ln in frame) + '\x1b[J')
                    self._scrollbar(2, avail, len(hits), avail, top, cols)
                    out.flush()
                    dirty = False
                k = self.key(0.25)
                if k is None:
                    continue
                dirty = True
                if k in ('esc', 'ctrl-c', 'ctrl-d'):
                    if find and k == 'esc':
                        find = ''
                    else:
                        return
                elif k == 'up':
                    follow, top = False, top - 1
                elif k == 'down':
                    top += 1
                    follow = top >= last
                elif k == 'pgup':
                    follow, top = False, top - (avail - 1)
                elif k == 'pgdn':
                    top += avail - 1
                    follow = top >= last
                elif k == 'home':
                    follow, top = False, 0
                elif k in ('end', 'enter'):
                    follow, new = True, 0
                elif k == 'left':
                    xoff = max(0, xoff - 20)
                    continue
                elif k == 'right':
                    xoff += 20
                    continue
                elif k == 'bs':
                    find = find[:-1]
                elif k == 'ctrl-u':
                    find = ''
                elif k and len(k) == 1 and k.isprintable():
                    find += k
                else:
                    continue
                if k in ('bs', 'ctrl-u', 'esc') or (k and len(k) == 1 and k.isprintable()):
                    test = self._grep(find)
                    hits = [i for i, x in enumerate(lines) if test(x[0])]
                    follow, new = True, 0
                if follow:
                    new = 0
        finally:
            out.write('\x1b[?25h\x1b[?1049l')
            out.flush()
            termios.tcsetattr(fd, termios.TCSADRAIN, was)

    def _log_text(self, ln):
        """One line of the log, coloured (colorama when it is there): the time
        dim, the level by how bad, what it is about in cyan, addresses in
        magenta, accept and reject in green and red, a whole warning in yellow
        and a whole error in red."""
        p = self.pal
        ln = ln.rstrip('\n')
        m = re.match(r'^(\S+ \S+) (\w+)(\s+)(.*)$', ln)
        if not m or not p.on:
            return ln
        lvl, rest = m.group(2), m.group(4)
        tone = self.LOG_TONES.get(lvl, '')
        paint = {'bad': p.bad, 'warn': p.warn, 'dim': p.dim}.get(tone)
        what = re.match(r'^([a-z][a-z -]{1,30}): (.*)$', rest)
        head, body = (what.group(1) + ':', what.group(2)) if what else ('', rest)

        def words(t):
            t = re.sub(r'(\[?[0-9a-fA-F:]*\d{1,3}(?:\.\d{1,3}){3}\]?(?::\d+)?|\b[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7}\b)',
                       lambda x: p.addr(x.group(1)) + (p.c_warn if tone == 'warn' else
                                                       p.c_bad if tone == 'bad' else ''), t)
            t = re.sub(r'\b(accept(?:ed)?|signed in|in place|done|ok)\b',
                       lambda x: p.good(x.group(1)) + (p.c_warn if tone == 'warn' else ''), t)
            t = re.sub(r'\b(reject(?:ed)?|refused|failed|wrong|locked out|not answering)\b',
                       lambda x: p.bad(x.group(1)) + (p.c_warn if tone == 'warn' else ''), t)
            return t
        body = words(body)
        if paint is not None and tone != 'dim':
            body = paint(body)
        elif tone == 'dim':
            body = p.dim(body)
        lv = (paint or p.info)(lvl.ljust(5))
        return '%s %s %s%s' % (p.dim(m.group(1)), lv, p.info(head) + (' ' if head else ''), body)

    def _log_line(self, ln):
        print(self._log_text(ln))

    # ---- 5 accounts -------------------------------------------------------------
    ROLES = [('admin', 'admin - everything: any terminal, the server'),
             ('user', 'user - terminals of their own, files in their folders')]

    def _pw_fields(self):
        return [{'key': 'pw', 'label': 'password', 'kind': 'secret', 'need': True,
                 'help': 'At least 10 characters; only stars are shown.',
                 'check': lambda v, _: None if len(v) >= 10 else 'at least 10 characters'},
                {'key': 'again', 'label': 'again', 'kind': 'secret', 'need': True,
                 'check': lambda v, vals: None if v == vals.get('pw')
                 else 'the two passwords are not the same'}]

    def m_accounts(self):
        def load():
            return self._rows(self.out('--users') or {}, 'users')

        cols = [('account', lambda u: u.get('name'), 24, None),
                ('role', lambda u: u.get('role'), 7, None),
                ('state', lambda u: 'off' if u.get('disabled') else 'on', 5,
                 lambda u: 'dim' if u.get('disabled') else 'ok'),
                ('runs as', lambda u: u.get('run_as') or '-', 12, None),
                ('last in', lambda u: self._when(u.get('last_login')), 16, None),
                ('note', lambda u: u.get('note') or '', 40, lambda u: 'dim')]
        return self.sub('Accounts of the pages', [
            ('1', 'Browse them (Enter: what to do with one)',
             lambda: self.pick('Accounts of the pages', load, cols, self.account_do)),
            ('2', 'Make one', self.account_new),
            ('3', 'Who is signed in now', lambda: self.act('--sign-ins')),
            ('4', 'The second step of signing in, for everybody', self.mfa_switch),
            ('5', 'Who is locked out', lambda: self.act('--lockouts')),
            ('6', 'Clear every lockout', lambda: self.act('--unlock', 'all')),
        ])

    def mfa_switch(self):
        got = self.out('--admin-2fa', 'status') or {}
        on = bool(got.get('admin_2fa')) if isinstance(got, dict) else False
        if on:
            if self.confirm('Switch the second step off', 'A password alone signs in again.', 'Switch it off'):
                self.act('--admin-2fa', 'off')
        elif self.confirm('Switch the second step on', 'After the password every account gives a code too (an '
                          'app, e-mail or SMS - set up at its next sign-in). Every sign-in ends now.', 'Switch it on'):
            self.act('--admin-2fa', 'on')

    def account_do(self, u):
        name = u['name']
        opts = [('pw', 'Set its password'), ('role', 'Change its role (now %s)' % u.get('role')),
                ('runas', 'The Linux account its terminals run as (now %s)' % u.get('run_as')),
                ('on', 'Switch it on again') if u.get('disabled') else ('off', 'Switch it off'),
                ('out', 'End its sign-ins'), ('mfa', 'Reset its second step (it sets one up again)'),
                ('show', 'Show it all'), ('delete', 'Delete it')]
        what = self.choose(name, opts, '%s, runs as %s, %s' % (u.get('role'), u.get('run_as'),
                                                               'off' if u.get('disabled') else 'on'))
        if what == 'pw':
            got = self.form('A new password for %s' % name, self._pw_fields())
            if got:
                self.act('--passwd', name, env={'AI_PASSWORD': got['pw']})
        elif what == 'role':
            r = self.choose('The role of %s' % name, self.ROLES,
                            cur=[x[0] for x in self.ROLES].index(u.get('role'))
                            if u.get('role') in [x[0] for x in self.ROLES] else 0)
            if r and r != u.get('role'):
                self.act('--set-role', name, '--role', r)
        elif what == 'runas':
            got = self.ask_one('The terminals of %s run as' % name, 'Linux account', u.get('run_as_own') or '',
                               help_='Empty: the default (Settings - Claude Code). The account must be there.',
                               need=False)
            if got is not None:
                self.act('--set-run-as', name, got or '-')
        elif what == 'off':
            if self.confirm('Switch off', '%s can no longer sign in to the pages; its terminals go on '
                            'running.' % name, 'Switch it off'):
                self.act('--disable-user', name)
        elif what == 'on':
            self.act('--enable-user', name)
        elif what == 'out':
            self.act('--end-sign-ins', name)
        elif what == 'mfa':
            if self.confirm('Reset the second step', 'The app or address of %s is forgotten and its sign-ins '
                            'end: at the next sign-in it sets a second step up again.' % name, 'Reset it'):
                self.act('--reset-2fa', name)
        elif what == 'show':
            self.details(name, u, skip=('prefs',))
        elif what == 'delete':
            if self.confirm('Delete', 'The account %s is deleted. This cannot be undone. Its terminals '
                            'go on running.' % name, 'Delete it', danger=True):
                self.act('--del-user', name)

    def account_new(self):
        got = self.form('Make an account', [
            {'key': 'name', 'label': 'name', 'need': True,
             'help': 'What it signs in with: letters, digits, . _ - @',
             'check': lambda v, _: None if re.match(r'^[A-Za-z0-9][A-Za-z0-9._@-]{0,63}$', v)
             else 'letters, digits and . _ - @ only'},
            {'key': 'role', 'label': 'role', 'kind': 'choice', 'value': 'user',
             'options': self.ROLES,
             'help': 'admin may do everything; user has terminals of its own, as its Linux account.'},
            {'key': 'run_as', 'label': 'runs as', 'help':
             'The Linux account its terminals run as. Empty: the default (Settings - Claude Code).'}]
            + self._pw_fields())
        if got:
            self.act('--add-user', got['name'], '--role', got['role'],
                     *(['--run-as', got['run_as']] if got.get('run_as') else []),
                     env={'AI_PASSWORD': got['pw']})

    # ---- 6 settings -------------------------------------------------------------
    def m_settings(self):
        def by_key():
            keys = sorted(SCHEMA_KEYS)
            key = self.ask_one('Change one by its key', 'the key', help_=(
                'Its key, as `ai --settings` shows it - e.g. claude_args, upgrade_auto. '
                'Then the same window as in Browse opens.'),
                check=lambda v, _: None if v in keys else 'there is no setting %s' % v)
            if not key:
                return
            row = next((r[1] for r in self._settings_rows() if r[0] == 'set'
                        and r[1]['key'] == key), None)
            if not row:
                self.note('Change one', 'there is no setting %s' % key, 'bad')
                return
            done = self._edit_one(row)
            if done:
                self.note('Change one', done[0], 'bad' if done[1] else 'ok')
        return self.sub('Settings', [
            ('1', 'Browse and change (arrows, Enter)', self.settings_tui),
            ('2', 'Change one by its key', by_key),
            ('3', 'All of them as text', lambda: self.act('--settings')),
        ])

    # ---- settings on the text screen: arrows, Enter, a window to change one (1.0.134)
    PANE_TITLES = [('claude', 'Claude Code'), ('access', 'Signing in'), ('upgrade', 'Upgrades'),
                   ('general', 'About')]

    def _settings_rows(self):
        got = self.out('--settings') or []
        rows = got.get('settings') if isinstance(got, dict) else got
        by = {r['key']: r for r in rows or [] if isinstance(r, dict) and r.get('key')}
        out, seen = [], set()
        for pane, words in self.PANE_TITLES:
            keys = [k for k, r in by.items() if r.get('pane') == pane]
            if not keys:
                continue
            out.append(('head', words))
            for k in keys:
                out.append(('set', by[k]))
                seen.add(k)
        rest = [k for k in by if k not in seen]
        if rest:
            out.append(('head', 'Everything else'))
            out += [('set', by[k]) for k in rest]
        return out

    @staticmethod
    def _shown(v):
        if v is True:
            return 'on'
        if v is False:
            return 'off'
        return '' if v is None else str(v)

    def _kind(self, key):
        s = SCHEMA_KEYS.get(key)
        kind, extra = (s[2], s[5]) if s else ('str', {})
        if kind == 'bool':
            return 'switch', ['1', '0']
        if kind == 'choice':
            return 'choice', [c[0] for c in extra.get('choices') or []]
        if kind == 'int':
            return 'number', [extra.get('min', 0), extra.get('max', 10 ** 9)]
        return 'text', None

    def settings_tui(self):
        c, A = self.curses, self.A
        rows = self._settings_rows()
        if not rows:
            return None
        sel = next(i for i, r in enumerate(rows) if r[0] == 'set')
        top, said, said_bad, find = 0, '', False, ''
        while True:
            if self.plain:
                c.reset_prog_mode()
                self.scr.clear()
                self.plain = False

            def paint():
                nonlocal top
                h, w = self.scr.getmaxyx()
                self.scr.erase()
                self._put(0, 0, ' ' * w, A['head'])
                self._put(0, 0, ' ai %s  Settings' % __version__, A['head'] | c.A_BOLD)
                if find:
                    self._put(0, max(0, w - len(find) - 12), ' find: %s ' % find, A['head'])
                avail = max(3, h - 3)
                if sel < top:
                    top = sel
                if sel >= top + avail:
                    top = sel - avail + 1
                top = max(0, min(top, max(0, len(rows) - avail)))
                if top > 0 and rows[top - 1][0] == 'head' and sel - top < avail - 1:
                    top -= 1                    # the group's heading with its first setting
                namew = max(20, min(44, w // 3))
                valw = max(10, min(40, w - namew - 30))
                for n, r in enumerate(rows[top:top + avail]):
                    y = 1 + n
                    if r[0] == 'head':
                        self._put(y, 1, r[1].upper(), A['key'])
                        continue
                    st = r[1]
                    val = self._shown(st.get('value'))
                    line = '  %-*s %-*s %s' % (namew, (st.get('label') or st['key'])[:namew], valw,
                                              val[:valw], st.get('key'))
                    if top + n == sel:
                        self._put(y, 0, line + ' ' * max(0, w - 2 - len(line)), A['sel'])
                    else:
                        self._put(y, 0, '  ' + (st.get('label') or st['key'])[:namew])
                        tone = A['dim'] if st.get('source') == 'default' else A['ok']
                        self._put(y, 3 + namew, val[:valw], tone)
                        self._put(y, 4 + namew + valw, st.get('key'), A['dim'])
                # The bar on the right.
                total = len(rows)
                if total > avail:
                    thumb = max(1, min(avail, round(avail * avail / total)))
                    tstart = max(0, min(avail - thumb, round((avail - thumb) * top
                                                              / max(1, total - avail))))
                    utf = 'utf' in (sys.stdout.encoding or '').lower()
                    for r in range(avail):
                        hit = tstart <= r < tstart + thumb
                        self._put(1 + r, w - 1, ('\u2588' if hit else '\u2502') if utf
                                  else ('#' if hit else '|'), A['key'] if hit else A['dim'])
                if said:
                    self._put(h - 2, 1, said[:w - 2], A['bad'] if said_bad else A['ok'])
                help_ = ' Up/Down PgUp/PgDn Home/End move   Enter change   / find   Esc back '
                self._put(h - 1, 0, ' ' * (w - 1), A['head'])
                self._put(h - 1, 0, help_[:w - 1], A['head'])
                self.scr.noutrefresh()
                return h, avail
            self.backdrop = paint
            h, avail = paint()
            c.doupdate()
            self.scr.timeout(500)
            k = self._getkey()
            if k is None:
                continue
            said = ''
            sets = [i for i, r in enumerate(rows) if r[0] == 'set']
            if k == 'esc':
                if find:
                    find = ''
                    continue
                return None
            if k == 'q':
                return 'quit'
            if k in ('up', 'down', 'pgup', 'pgdn', 'home', 'end'):
                pos = sets.index(sel) if sel in sets else 0
                pos = {'up': pos - 1, 'down': pos + 1, 'pgup': pos - (avail - 2),
                       'pgdn': pos + (avail - 2), 'home': 0, 'end': len(sets) - 1}[k]
                sel = sets[max(0, min(len(sets) - 1, pos))]
            elif k == '/':
                find = self._line_in(h - 2, 'Find (a word of its name or key): ', '') or ''
                if find:
                    hit = [i for i in sets if find.lower() in (
                        str(rows[i][1].get('label')) + ' ' + rows[i][1]['key']).lower()]
                    if hit:
                        sel = hit[0]
                    else:
                        said, said_bad = 'nothing with "%s"' % find, True
            elif k == 'n' and find:
                hit = [i for i in sets if i > sel and find.lower() in (
                    str(rows[i][1].get('label')) + ' ' + rows[i][1]['key']).lower()]
                if hit:
                    sel = hit[0]
            elif k == 'enter':
                done = self._edit_one(rows[sel][1])
                if done:
                    said, said_bad = done
                    if not said_bad:
                        cur = rows[sel][1]['key']
                        rows = self._settings_rows()
                        sel = next((i for i, r in enumerate(rows)
                                    if r[0] == 'set' and r[1]['key'] == cur), sel)

    def _getkey(self, win=None):
        """A key on the text screen, by name: 'up', 'enter', 'esc', or the character."""
        c = self.curses
        src = win or self.scr
        k = src.getch()
        if k == -1:
            # The window's size looked at, as the menus do.
            try:
                size = os.get_terminal_size(sys.__stdout__.fileno())
                if (size.lines, size.columns) != self.scr.getmaxyx():
                    c.resizeterm(size.lines, size.columns)
                    self.scr.clear()
                    return 'resize'
            except (OSError, ValueError, c.error):
                pass
            return None
        if k == 27:
            src.nodelay(True)
            k2 = src.getch()
            if k2 in (ord('['), ord('O')):
                seq = ''
                while True:
                    k3 = src.getch()
                    if k3 == -1:
                        break
                    seq += chr(k3)
                    if chr(k3).isalpha() or chr(k3) == '~':
                        break
                src.nodelay(False)
                return {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left', 'H': 'home',
                        'F': 'end', '5~': 'pgup', '6~': 'pgdn', '1~': 'home', '4~': 'end',
                        '7~': 'home', '8~': 'end', '3~': 'del'}.get(seq, None)
            if k2 != -1:
                c.ungetch(k2)
            src.nodelay(False)
            return 'esc'
        named = {c.KEY_UP: 'up', c.KEY_DOWN: 'down', c.KEY_LEFT: 'left', c.KEY_RIGHT: 'right',
                 c.KEY_PPAGE: 'pgup', c.KEY_NPAGE: 'pgdn', c.KEY_HOME: 'home', c.KEY_END: 'end',
                 c.KEY_ENTER: 'enter', 10: 'enter', 13: 'enter', c.KEY_BACKSPACE: 'bs',
                 127: 'bs', 8: 'bs', c.KEY_DC: 'del', c.KEY_RESIZE: 'resize', 21: 'ctrl-u',
                 9: 'tab'}
        if k in named:
            if k == c.KEY_RESIZE:
                try:
                    c.update_lines_cols()
                except Exception:                       # noqa: BLE001
                    pass
            return named[k]
        if 0xc0 <= k < 0xf8:
            # getch() gives UTF-8 a byte at a time (1.0.139): "ž" came as two
            # Latin-1 letters, and a password typed here was not the one meant.
            raw = bytearray([k])
            src.nodelay(True)
            try:
                for _ in range(1 if k < 0xe0 else 2 if k < 0xf0 else 3):
                    k2 = src.getch()
                    if not 0x80 <= k2 < 0xc0:
                        break
                    raw.append(k2)
            finally:
                src.nodelay(False)
            try:
                return raw.decode('utf-8')
            except UnicodeDecodeError:
                return None
        if 32 <= k < 0x110000:
            try:
                return chr(k)
            except ValueError:
                return None
        return None

    def _line_in(self, y, prompt, text, secret=False, win=None, x=1, width=None):
        """A line typed on the text screen: Enter gives it, Esc gives None."""
        c = self.curses
        scr = win or self.scr
        pos = len(text)
        try:
            c.curs_set(1)
        except Exception:                               # noqa: BLE001
            pass
        try:
            while True:
                h, w = scr.getmaxyx()
                room = (width or (w - x - len(prompt) - 2))
                shown = ('*' * len(text)) if secret else text
                start = max(0, pos - room + 1)
                try:
                    scr.addstr(y, x, prompt, self.A['key'])
                    scr.addstr(y, x + len(prompt), shown[start:start + room].ljust(room),
                               self.curses.A_UNDERLINE)
                    scr.move(y, x + len(prompt) + pos - start)
                except c.error:
                    pass
                scr.refresh()
                scr.timeout(500)
                k = self._getkey(scr)
                if k == 'enter':
                    return text
                if k == 'esc':
                    return None
                if k == 'bs' and pos > 0:
                    text = text[:pos - 1] + text[pos:]
                    pos -= 1
                elif k == 'del':
                    text = text[:pos] + text[pos + 1:]
                elif k == 'left':
                    pos = max(0, pos - 1)
                elif k == 'right':
                    pos = min(len(text), pos + 1)
                elif k == 'home':
                    pos = 0
                elif k == 'end':
                    pos = len(text)
                elif k == 'ctrl-u':
                    text, pos = '', 0
                elif k and len(k) == 1 and k.isprintable():
                    text = text[:pos] + k + text[pos:]
                    pos += 1
        finally:
            try:
                c.curs_set(0)
            except Exception:                           # noqa: BLE001
                pass

    def _box(self, win, h, w):
        """A frame round a window, in UTF-8 lines where the terminal takes them."""
        c, A = self.curses, self.A
        if 'utf' in (sys.stdout.encoding or '').lower():
            hz, vt, tl, tr, bl, br = '\u2500', '\u2502', '\u250c', '\u2510', '\u2514', '\u2518'
        else:
            hz, vt, tl, tr, bl, br = '-', '|', '+', '+', '+', '+'
        for y, line in ((0, tl + hz * (w - 2) + tr), (h - 1, bl + hz * (w - 2) + br)):
            try:
                win.addstr(y, 0, line, A['key'])
            except c.error:
                pass                                    # the bottom-right corner
        for y in range(1, h - 1):
            for x in (0, w - 1):
                try:
                    win.addstr(y, x, vt, A['key'])
                except c.error:
                    pass

    def _edit_one(self, st):
        """The window to change one setting: what it is, what it may be, the
        value checked as the daemon checks it before it is saved. Returns
        (words, bad) or None when nothing was done."""
        c, A = self.curses, self.A
        key = st['key']
        kind, shape = self._kind(key)
        secret = bool(st.get('secret'))
        cur = self._shown(st.get('value'))
        if kind == 'switch':
            cur = '1' if st.get('value') in (True, 1, '1', 'on') else '0'
        text = '' if secret else cur
        choice = shape.index(cur) if kind in ('switch', 'choice') and cur in (shape or []) else 0
        err = ''
        helptext = re.sub(r'<[^>]+>', '', html.unescape(str(st.get('help') or '')))
        while True:
            self._under()
            h, w = self.scr.getmaxyx()
            ww = max(40, min(96, w - 4))
            body = []
            for para in helptext.split('\n'):
                body += textwrap.wrap(para, ww - 4) or ['']
            facts = ['now: %s%s' % ('(hidden)' if secret else (self._shown(st.get('value')) or '(empty)'),
                                    '' if st.get('source') == 'default' else
                                    '   - %s' % (st.get('source_says') or st.get('source'))),
                     'as it comes: %s' % (self._shown(st.get('default')) or '(empty)')]
            if kind == 'number':
                facts.append('a whole number from %s to %s' % (shape[0], shape[1]))
            elif kind == 'choice':
                facts.append('one of: ' + ', '.join(shape))
            if st.get('file_only'):
                facts.append('kept in config.json on this machine - it takes effect after a restart')
            if st.get('node_key'):
                facts.append('this node\'s own (each node of a cluster has its own)')
            # The help cut to what the screen has room for - the rest always fits.
            fixed = len(facts) + 9 + (len(shape) - 1 if kind == 'choice' else 0)
            body = body[:max(1, h - 2 - fixed)]
            wh = min(h - 2, len(body) + fixed)
            win = c.newwin(wh, ww, max(0, (h - wh) // 2), max(0, (w - ww) // 2))
            win.keypad(True)
            win.erase()
            self._box(win, wh, ww)
            title = ' %s ' % (st.get('label') or key)
            try:
                win.addnstr(0, 2, title, ww - 4, A['title'])
                win.addnstr(1, 2, key, ww - 4, A['dim'])
                y = 2
                for ln in body:
                    win.addnstr(y, 2, ln, ww - 4)
                    y += 1
                y += 1
                for f in facts:
                    win.addnstr(y, 2, f, ww - 4, A['dim'])
                    y += 1
                y += 1
                if err:
                    win.addnstr(wh - 2, 2, err[:ww - 4], ww - 4, A['bad'])
                else:
                    win.addnstr(wh - 2, 2, ('Left/Right choose' if kind in ('switch', 'choice')
                                            else 'type the new value') +
                                '   Enter save   Esc cancel', ww - 4, A['dim'])
            except c.error:
                pass
            if kind in ('switch', 'choice'):
                words = {'1': 'on', '0': 'off'} if kind == 'switch' else {}
                x = 2
                for i, opt in enumerate(shape):
                    lab = ' %s ' % (words.get(opt) or dict((SCHEMA_KEYS[key][5].get('choices') or [])
                                                           if key in SCHEMA_KEYS else []).get(opt) or opt)
                    if kind == 'choice':
                        # One under the other: their words can be long.
                        lab = (' > ' if i == choice else '   ') + lab.strip() + ' '
                        try:
                            win.addnstr(y, 2, lab, ww - 4, A['sel'] if i == choice else 0)
                        except c.error:
                            pass
                        y += 1
                        continue
                    try:
                        win.addnstr(y, x, lab, max(0, ww - x - 2), A['sel'] if i == choice else 0)
                    except c.error:
                        pass
                    x += len(lab) + 1
                win.noutrefresh()
                c.doupdate()
                win.timeout(500)
                k = self._getkey(win)
                if k == 'esc':
                    return None
                if k in ('left', 'up'):
                    choice = (choice - 1) % len(shape)
                elif k in ('right', 'down', 'tab', ' '):
                    choice = (choice + 1) % len(shape)
                elif k == 'enter':
                    value = shape[choice]
                else:
                    continue
                if k != 'enter':
                    continue
            else:
                win.noutrefresh()
                c.doupdate()
                got = self._line_in(y, 'value: ', text, secret=secret, win=win, x=2,
                                    width=ww - 14)
                if got is None:
                    return None
                text = got
                if secret and not got:
                    return ('nothing typed - %s stays as it was' % key, False)
                value = got
            # Checked here as the daemon checks it, then saved by `ai --set`.
            try:
                setting_value(key, value if kind != 'switch' else value == '1')
            except (Refused, ValueError, TypeError) as e:
                err = str(e)
                continue
            # A secret goes by the environment, not the command line (as otp's).
            env = {'AI_VALUE_' + key.upper(): value} if secret else None
            out, rc = self.capture(ai_argv() + ['--set', '%s=%s' % (
                key, '@env' if secret else value), '--no-color'], env=env)
            if rc != 0:
                err = (out.strip().splitlines() or ['it was not saved'])[-1]
                continue
            return ('%s = %s - saved%s' % (key, '(hidden)' if secret else value,
                                           '; the running service takes it within a minute'
                                           if not st.get('file_only') else
                                           '; restart the service for it'), False)

    # ---- windows on the text screen for every menu: arrows and Enter (1.0.135) ----
    # Nothing is typed at a bare prompt any more: a question is a window (a
    # form) whose fields are moved between by the arrows, a choice is picked
    # by the arrows, a list (terminals, accounts…) is scrolled and
    # Enter on one offers what can be done with it. What is typed is checked
    # before anything is run; Esc closes the window and goes back. The screen
    # under a window is drawn again by `self.backdrop` - so a window made
    # bigger or smaller (PuTTY's too) is drawn right.
    def _fresh(self):
        """Back from a command's own screen: the text screen drawn whole again."""
        if self.plain:
            self.curses.reset_prog_mode()
            self.scr.clear()
            self.plain = False
            self.st_now = True

    def _under(self):
        """The screen under a window, written but not yet shown."""
        self._fresh()
        fn = getattr(self, 'backdrop', None)
        if fn:
            try:
                fn()
                return
            except Exception:                           # noqa: BLE001
                pass
        self.scr.noutrefresh()

    def _window(self, want_h, want_w):
        """A framed window in the middle of the screen; (win, h, w)."""
        c = self.curses
        h, w = self.scr.getmaxyx()
        ww = max(20, min(want_w, w - 2))
        wh = max(5, min(want_h, h - 2))
        win = c.newwin(wh, ww, max(0, (h - wh) // 2), max(0, (w - ww) // 2))
        win.keypad(True)
        win.erase()
        self._box(win, wh, ww)
        return win, wh, ww

    def _wput(self, win, y, x, text, attr=0, width=None):
        try:
            wh, ww = win.getmaxyx()
            if 0 < y < wh - 1 and x < ww - 1:
                win.addnstr(y, x, str(text), max(0, (width or ww) - (x if width is None else 0)
                                                 - (1 if width is None else 0)), attr)
        except self.curses.error:
            pass

    def _wkey(self, win, wait=500):
        win.timeout(wait)
        return self._getkey(win)

    def _wrap(self, text, width):
        out = []
        for para in str(text or '').split('\n'):
            out += textwrap.wrap(para, max(10, width)) or ['']
        return out

    @staticmethod
    def _plain_text(text):
        return re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', str(text or ''))

    def note(self, title, text, tone=''):
        """Words in a window; any of Enter, Esc, q or Space closes it."""
        A = self.A
        while True:
            self._under()
            h, w = self.scr.getmaxyx()
            ww = max(30, min(100, w - 4))
            lines = self._wrap(text, ww - 4)[:max(1, h - 6)]
            win, wh, ww = self._window(len(lines) + 4, max(len(title) + 8, min(
                ww, max(len(x) for x in lines + ['']) + 6, ww)))
            self._wput(win, 0, 2, ' %s ' % title, A['title'])
            try:
                win.addnstr(0, 2, ' %s ' % title, ww - 4, A['title'])
            except self.curses.error:
                pass
            for i, ln in enumerate(lines):
                self._wput(win, 1 + i, 2, ln, A.get(tone, 0) if tone else 0)
            self._wput(win, wh - 2, 2, 'Enter or Esc - back', A['dim'])
            win.noutrefresh()
            self.curses.doupdate()
            k = self._wkey(win)
            if k in ('enter', 'esc', 'q', ' '):
                return

    def working(self, words):
        """A window that says something is being done (the screen waits for it)."""
        self._under()
        win, wh, ww = self._window(3, min(100, len(words) + 6))
        self._wput(win, 1, 2, words, self.A['dim'])
        win.noutrefresh()
        self.curses.doupdate()

    def confirm(self, title, words, yes='Yes', no='No', danger=False):
        """Yes or no, chosen by the arrows (or y / n); No unless chosen."""
        A = self.A
        pick = 1
        while True:
            self._under()
            h, w = self.scr.getmaxyx()
            ww = max(40, min(80, w - 4))
            lines = self._wrap(words, ww - 4)[:max(1, h - 8)]
            win, wh, ww = self._window(len(lines) + 5, ww)
            try:
                win.addnstr(0, 2, ' %s ' % title, ww - 4, A['bad'] if danger else A['title'])
            except self.curses.error:
                pass
            for i, ln in enumerate(lines):
                self._wput(win, 1 + i, 2, ln)
            x = 2
            y = wh - 2
            for i, lab in enumerate((yes, no)):
                lab = '  %s  ' % lab
                self._wput(win, y, x, lab, (A['bad'] if danger and i == 0 else A['sel'])
                           if i == pick else A['key'])
                x += len(lab) + 2
            self._wput(win, y, x + 2, 'Left/Right  Enter  Esc', A['dim'])
            win.noutrefresh()
            self.curses.doupdate()
            k = self._wkey(win)
            if k in ('esc', 'n', 'N'):
                return False
            if k in ('y', 'Y'):
                return True
            if k in ('left', 'right', 'tab', 'up', 'down'):
                pick = 1 - pick
            elif k == 'enter':
                return pick == 0

    def choose(self, title, options, words='', cur=0):
        """One of `options` ([(value, words)]), picked by the arrows; Esc None."""
        A = self.A
        if not options:
            return None
        sel = max(0, min(cur or 0, len(options) - 1))
        top = 0
        while True:
            self._under()
            h, w = self.scr.getmaxyx()
            ww = min(90, w - 4, max(36, max(len(o[1]) for o in options) + 12,
                                    len(title) + 8, len(words) + 6 if words else 0))
            head = self._wrap(words, ww - 4) if words else []
            room = max(1, min(len(options), h - 6 - len(head)))
            win, wh, ww = self._window(room + len(head) + (4 if head else 3), ww)
            try:
                win.addnstr(0, 2, ' %s ' % title, ww - 4, A['title'])
            except self.curses.error:
                pass
            y = 1
            for ln in head:
                self._wput(win, y, 2, ln, A['dim'])
                y += 1
            if head:
                y += 1
            if sel < top:
                top = sel
            if sel >= top + room:
                top = sel - room + 1
            for n, (val, lab) in enumerate(options[top:top + room]):
                i = top + n
                line = ' %2d  %s' % (i + 1, lab)
                if i == sel:
                    self._wput(win, y + n, 2, line.ljust(ww - 5), A['sel'])
                else:
                    self._wput(win, y + n, 2, ' %2d' % (i + 1), A['key'])
                    self._wput(win, y + n, 7, lab)
            if len(options) > room:
                self._wbar(win, y, room, len(options), top, ww - 2)
            win.noutrefresh()
            self.curses.doupdate()
            k = self._wkey(win)
            if k in ('esc', 'left'):
                return None
            if k == 'q':
                return None
            if k == 'up':
                sel = (sel - 1) % len(options)
            elif k in ('down', 'tab'):
                sel = (sel + 1) % len(options)
            elif k in ('home', 'pgup'):
                sel = 0
            elif k in ('end', 'pgdn'):
                sel = len(options) - 1
            elif k and k.isdigit():
                n = int(k) - 1
                if 0 <= n < len(options):
                    sel = n
                    return options[sel][0]
            elif k in ('enter', 'right'):
                return options[sel][0]

    def _wbar(self, win, y0, rows, total, top, x):
        """The scroll bar on the right of a list in a window."""
        A = self.A
        if total <= rows:
            return
        thumb = max(1, min(rows, round(rows * rows / total)))
        tstart = max(0, min(rows - thumb, round((rows - thumb) * top / max(1, total - rows))))
        utf = 'utf' in (sys.stdout.encoding or '').lower()
        for r in range(rows):
            hit = tstart <= r < tstart + thumb
            try:
                win.addstr(y0 + r, x, ('█' if hit else '│') if utf else
                           ('#' if hit else '|'), A['key'] if hit else A['dim'])
            except self.curses.error:
                pass

    def form(self, title, fields, words='', check=None, ok='OK'):
        """Questions in one window. fields: [{'key', 'label', 'kind': 'text' |
        'secret' | 'choice' | 'number', 'value', 'options': [(value, words)],
        'need': True, 'range': (a, b), 'help', 'check': fn(value, values) ->
        an error or None, 'when': fn(values) -> shown or not}]. Up/Down (Tab)
        move between them, a choice is changed by Left/Right, Enter checks
        them all and gives {key: value}; Esc gives None. A secret shows a star
        for each character, never the characters."""
        c, A = self.curses, self.A
        vals, pos = {}, {}
        for f in fields:
            f.setdefault('kind', 'text')
            if f['kind'] == 'choice':
                opts = [o[0] for o in f['options']]
                vals[f['key']] = f.get('value') if f.get('value') in opts else opts[0]
            else:
                vals[f['key']] = str(f.get('value') if f.get('value') is not None else '')
            pos[f['key']] = len(vals[f['key']]) if f['kind'] != 'choice' else 0
        at, err, err_at = 0, '', None
        try:
            c.curs_set(1)
        except Exception:                               # noqa: BLE001
            pass
        try:
            while True:
                shown = [f for f in fields if not f.get('when') or f['when'](vals)]
                at = max(0, min(at, len(shown) - 1))
                f = shown[at]
                self._under()
                h, w = self.scr.getmaxyx()
                ww = max(50, min(100, w - 4))
                head = self._wrap(words, ww - 4) if words else []
                labw = min(30, max(len(x.get('label') or x['key']) for x in shown) + 1)
                fieldw = max(8, ww - labw - 7)
                helps = self._wrap(f.get('help') or '', ww - 4) if f.get('help') else []
                helps = helps[:4]
                wh = len(head) + (1 if head else 0) + len(shown) + 2 + 4 + 1
                win, wh, ww = self._window(wh, ww)
                try:
                    win.addnstr(0, 2, ' %s ' % title, ww - 4, A['title'])
                except c.error:
                    pass
                y = 1
                for ln in head:
                    self._wput(win, y, 2, ln, A['dim'])
                    y += 1
                if head:
                    y += 1
                cursor = None
                for i, x in enumerate(shown):
                    lab = (x.get('label') or x['key'])[:labw - 1]
                    here = i == at
                    self._wput(win, y, 2, lab.rjust(labw), A['key'] if here else 0)
                    vx = 3 + labw + 1
                    v = vals[x['key']]
                    if x['kind'] == 'choice':
                        words_ = dict(x['options']).get(v, v)
                        txt = ('< %s >' % words_) if here else ('  %s' % words_)
                        self._wput(win, y, vx, txt[:fieldw], A['sel'] if here else A['ok'])
                    else:
                        t = ('*' * len(v)) if x['kind'] == 'secret' else v
                        p = pos[x['key']] if here else len(t)
                        start = max(0, p - fieldw + 1)
                        self._wput(win, y, vx, t[start:start + fieldw].ljust(fieldw),
                                   c.A_UNDERLINE | (A['key'] if here else 0))
                        if here:
                            cursor = (y, vx + p - start)
                    if err and err_at == x['key']:
                        self._wput(win, y, ww - 3, '!', A['bad'])
                    y += 1
                y += 1
                for ln in helps:
                    self._wput(win, y, 2, ln, A['dim'])
                    y += 1
                if err:
                    self._wput(win, wh - 2, 2, err[:ww - 4], A['bad'])
                else:
                    self._wput(win, wh - 2, 2, ('Up/Down field   ' + ('Left/Right choose   '
                               if any(x['kind'] == 'choice' for x in shown) else '') +
                               'Enter %s   Esc cancel' % ok)[:ww - 4], A['dim'])
                if cursor:
                    try:
                        c.curs_set(1)
                        win.move(*cursor)
                    except c.error:
                        pass
                else:
                    try:
                        c.curs_set(0)
                    except Exception:                   # noqa: BLE001
                        pass
                win.noutrefresh()
                c.doupdate()
                k = self._wkey(win)
                if k is None or k == 'resize':
                    continue
                key, kind = f['key'], f['kind']
                if k == 'esc':
                    return None
                if k in ('up',) or (k == 'tab' and False):
                    at = (at - 1) % len(shown)
                elif k in ('down', 'tab'):
                    at = (at + 1) % len(shown)
                elif k == 'enter':
                    err, err_at = '', None
                    for i, x in enumerate(shown):
                        v = vals[x['key']]
                        if x['kind'] != 'choice':
                            v = v.strip() if x['kind'] != 'secret' else v
                            vals[x['key']] = v
                        bad = None
                        if x.get('need') and v == '':
                            bad = '%s - it is needed' % (x.get('label') or x['key'])
                        elif x['kind'] == 'number' and v != '':
                            try:
                                n = int(v)
                                lo, hi = x.get('range') or (None, None)
                                if (lo is not None and n < lo) or (hi is not None and n > hi):
                                    bad = '%s - a whole number from %s to %s' % (
                                        x.get('label') or x['key'], lo, hi)
                            except ValueError:
                                bad = '%s - a whole number' % (x.get('label') or x['key'])
                        if not bad and x.get('check') and v != '':
                            try:
                                bad = x['check'](v, vals)
                            except Exception as e:              # noqa: BLE001
                                bad = str(e)
                        if bad:
                            err, err_at, at = bad, x['key'], i
                            break
                    if err:
                        continue
                    got = {x['key']: vals[x['key']] for x in shown}
                    if check:
                        bad = check(got)
                        if bad:
                            err, err_at = (bad if isinstance(bad, tuple) else (bad, None))
                            if err_at:
                                at = next((i for i, x in enumerate(shown) if x['key'] == err_at),
                                          at)
                            continue
                    return got
                elif kind == 'choice':
                    opts = [o[0] for o in f['options']]
                    i = opts.index(vals[key]) if vals[key] in opts else 0
                    if k in ('left',):
                        vals[key] = opts[(i - 1) % len(opts)]
                    elif k in ('right', ' '):
                        vals[key] = opts[(i + 1) % len(opts)]
                    err = ''
                else:
                    t, p = vals[key], pos[key]
                    if k == 'bs' and p > 0:
                        t, p = t[:p - 1] + t[p:], p - 1
                    elif k == 'del':
                        t = t[:p] + t[p + 1:]
                    elif k == 'left':
                        p = max(0, p - 1)
                    elif k == 'right':
                        p = min(len(t), p + 1)
                    elif k == 'home':
                        p = 0
                    elif k == 'end':
                        p = len(t)
                    elif k == 'ctrl-u':
                        t, p = '', 0
                    elif k and len(k) == 1 and k.isprintable():
                        if kind == 'number' and not (k.isdigit() or (k == '-' and p == 0)):
                            continue
                        t, p = t[:p] + k + t[p:], p + 1
                    else:
                        continue
                    vals[key], pos[key] = t, p
                    if err_at == key:
                        err, err_at = '', None
        finally:
            try:
                c.curs_set(0)
            except Exception:                           # noqa: BLE001
                pass

    def ask_one(self, title, label, value='', help_='', need=True, secret=False, check=None):
        """One question in a window; its answer, or None (Esc)."""
        got = self.form(title, [{'key': 'v', 'label': label, 'value': value, 'help': help_,
                                 'need': need, 'kind': 'secret' if secret else 'text',
                                 'check': check}])
        return None if got is None else got['v']

    def pick(self, title, load, cols, act=None, empty='nothing here', words=''):
        """A list to scroll with the arrows: `load()` gives its rows (asked
        again after something was done to one), `cols` [(heading, fn(row),
        width, tone fn(row) or None)]. Enter calls `act(row)`; / finds. Esc
        back, q leaves the console."""
        c, A = self.curses, self.A
        rows = load() or []
        sel, top, find, said, said_bad = 0, 0, '', '', False
        while True:
            self._fresh()
            h, w = self.scr.getmaxyx()
            seen = [r for r in rows if not find or find.lower() in ' '.join(
                str(fn(r)) for _h, fn, _w, _t in cols).lower()]
            sel = max(0, min(sel, len(seen) - 1))
            avail = max(3, h - 5 - (1 if words else 0))
            if sel < top:
                top = sel
            if sel >= top + avail:
                top = sel - avail + 1
            top = max(0, min(top, max(0, len(seen) - avail)))
            # Widths: as given; the last one takes what is left.
            ws = [cw for _h, _f, cw, _t in cols]
            fixed = sum(x + 2 for x in ws[:-1])
            ws[-1] = max(8, min(ws[-1] or 200, w - 4 - fixed))

            def paint(_title=title, _seen=seen, _top=top, _sel=sel, _ws=ws, _avail=avail):
                self.scr.erase()
                self._put(0, 0, ' ' * w, A['head'])
                self._put(0, 0, ' ai %s  %s ' % (__version__, _title), A['head'] | c.A_BOLD)
                right = ' %d%s ' % (len(_seen), (' of %d, with "%s"' % (len(rows), find))
                                    if find else '')
                self._put(0, max(0, w - len(right) - 1), right, A['head'])
                y = 1
                if words:
                    self._put(y, 1, words[:w - 2], A['dim'])
                    y += 1
                x = 2
                for (hd, _f, _w, _t), cw in zip(cols, _ws):
                    self._put(y + 1, x, hd[:cw], A['key'])
                    x += cw + 2
                y += 2
                if not _seen:
                    self._put(y + 1, 4, empty if not find else 'nothing with "%s"' % find,
                              A['dim'])
                for n, r in enumerate(_seen[_top:_top + _avail]):
                    i = _top + n
                    x = 2
                    if i == _sel:
                        self._put(y + n, 1, ' ' * (w - 3), A['sel'])
                    for (hd, fn, _w, tone), cw in zip(cols, _ws):
                        try:
                            v = str(fn(r))
                        except Exception:               # noqa: BLE001
                            v = '?'
                        attr = A['sel'] if i == _sel else (A.get(tone(r) or '', 0) if tone else 0)
                        self._put(y + n, x, v[:cw], attr)
                        x += cw + 2
                if len(_seen) > _avail:
                    thumb = max(1, min(_avail, round(_avail * _avail / len(_seen))))
                    ts = max(0, min(_avail - thumb, round((_avail - thumb) * _top
                                                          / max(1, len(_seen) - _avail))))
                    utf = 'utf' in (sys.stdout.encoding or '').lower()
                    for r_ in range(_avail):
                        hit = ts <= r_ < ts + thumb
                        self._put(y + r_, w - 1, ('█' if hit else '│') if utf
                                  else ('#' if hit else '|'), A['key'] if hit else A['dim'])
                if said:
                    self._put(h - 2, 1, said[:w - 2], A['bad'] if said_bad else A['ok'])
                help_ = ' Up/Down PgUp/PgDn Home/End move   Enter %s   / find   Esc back ' % (
                    'what to do with it' if act else 'look')
                self._put(h - 1, 0, ' ' * (w - 1), A['head'])
                self._put(h - 1, 0, help_[:w - 1], A['head'])
                self.scr.noutrefresh()
            self.backdrop = paint
            paint()
            c.doupdate()
            self.scr.timeout(500)
            k = self._getkey()
            if k is None:
                continue
            said = ''
            if k == 'esc':
                if find:
                    find = ''
                    continue
                return None
            if k == 'q':
                return 'quit'
            if k in ('up', 'down', 'pgup', 'pgdn', 'home', 'end'):
                sel = {'up': sel - 1, 'down': sel + 1, 'pgup': sel - (avail - 1),
                       'pgdn': sel + (avail - 1), 'home': 0, 'end': len(seen) - 1}[k]
            elif k == '/':
                got = self.ask_one('Find', 'with the words', find, need=False,
                                   help_='Only the rows with these words in them stay; '
                                         'Esc in the list shows them all again.')
                if got is not None:
                    find, sel, top = got, 0, 0
            elif k in ('enter', 'right') and seen and act:
                r = act(seen[sel])
                if r == 'quit':
                    return 'quit'
                if isinstance(r, tuple):
                    said, said_bad = r
                rows = load() or []

    def act(self, *args, env=None, title=None, quiet_ok=None):
        """`ai ARGS` run: a short answer in a window, a long one on a screen
        of its own to scroll. Returns the exit code."""
        argv = ai_argv() + [str(a) for a in args]
        shown = '$ ai ' + ' '.join(self._quote(a) for a in args)
        return self.act_argv(argv, title or shown, env=env, quiet_ok=quiet_ok)

    def act_argv(self, argv, title, env=None, quiet_ok=None):
        self.working('working…  ' + title)
        text, rc = self.capture(argv, env=env)
        plain = self._plain_text(text).rstrip()
        if rc == 0 and not plain and quiet_ok:
            plain = text = quiet_ok
        h, w = self.scr.getmaxyx()
        lines = self._wrap(plain, max(30, min(100, w - 4)) - 4)
        if len(lines) <= max(3, min(14, h - 8)):
            self.note(title if rc == 0 else '%s - it ended with %d' % (title, rc),
                      plain or '(it said nothing)', '' if rc == 0 else 'bad')
        else:
            if rc not in (0, None):
                text += '\n' + self.pal.dim('(it ended with %d)' % rc)
            self.go_plain(lambda: self.page(title, text))
        return rc

    def live(self, fn):
        """A view of its own on the terminal (a live log, a progress)."""
        self.go_plain(fn)

    # ---- small parts the lists use ------------------------------------------------
    @staticmethod
    def _when(ts):
        if not ts:
            return '-'
        try:
            return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(ts)))
        except (TypeError, ValueError):
            return str(ts)

    @staticmethod
    def _rows(got, *keys):
        if isinstance(got, dict):
            for k in keys:
                if isinstance(got.get(k), list):
                    return got[k]
            return []
        return got if isinstance(got, list) else []

    def details(self, title, row, skip=()):
        """One row's fields as words, in a window or on its own screen."""
        lines = []
        for k, v in row.items():
            if k in skip or v in (None, '', [], {}):
                continue
            if isinstance(v, (list, dict)):
                v = json.dumps(v, default=str, ensure_ascii=False)
            elif k in ('created', 'last_used', 'last_seen', 'last_in', 'activated', 'at',
                       'pending_at', 'locked_until') and isinstance(v, (int, float)):
                v = self._when(v)
            lines.append('%-16s %s' % (k, v))
        h, w = self.scr.getmaxyx()
        if len(lines) <= h - 8:
            self.note(title, '\n'.join(lines))
        else:
            self.go_plain(lambda: self.page(title, '\n'.join(lines)))

    # ---- 9 backups --------------------------------------------------------------
    # ---- 10 upgrades ------------------------------------------------------------
    def m_upgrades(self):
        def online():
            self.working('working…  looking for a new version')
            row = self.out('--upgrade-check') or {}
            if row.get('error'):
                self.note('Upgrade from the web', '%s:\n%s' % (row.get('url'), row['error']), 'bad')
                return
            here = ver_tuple(__version__)
            newer = [p for p in row.get('packages') or [] if ver_tuple(p.get('version')) > here]
            if not newer:
                self.note('Upgrade from the web', 'Nothing newer than %s at %s.' % (
                    __version__, row.get('url')), 'ok')
                return
            ver = self.choose('Upgrade from the web', [
                (p['version'], 'ai %s%s' % (p['version'], '   (the newest)' if i == 0 else ''))
                for i, p in enumerate(newer)], 'This server runs %s. Found at %s:' % (
                    __version__, row.get('url')))
            if not ver:
                return
            if not self.confirm('Upgrade to %s' % ver, 'It is fetched, its signature checked, and put in. '
                                'The terminals go on running; the pages are back after a few seconds.',
                                'Upgrade'):
                return
            self.live(lambda: self.show_live('--upgrade-online', ver, '--yes'))

        def install():
            path = self.ask_one('Upgrade from a package', 'the package', '/root/',
                                help_='ai-X.Y.Z.tar.gz, as released - its signature is checked first.',
                                check=lambda v, _: None if os.path.isfile(v) and v.endswith('.tar.gz')
                                else 'not an ai-X.Y.Z.tar.gz')
            if not path:
                return
            if not self.confirm('Upgrade', 'ai is upgraded with %s once its signature is checked.' % path,
                                'Upgrade'):
                return

            def run_signed():
                self.clear_screen()
                subprocess.call([sys.executable, '-I', upgrader(), '--run', path])
                self.pause()
            self.live(run_signed)
        def back():
            ver = self.ask_one('Go back to', 'version', '', help_='One that --downgrade-check says may be gone '
                               'back to. A copy of the database is made first.')
            if ver and self.confirm('Go back', 'ai %s is fetched, checked and put in instead of %s.' % (
                    ver, __version__), 'Go back', danger=True):
                self.live(lambda: self.show_live('--downgrade', ver, '--yes'))
        return self.sub('Upgrades', [
            ('1', 'How it stands', lambda: self.act('--upgrade-status')),
            ('2', 'Look for a new version on the web now', lambda: self.act('--upgrade-check')),
            ('3', 'Upgrade from the web', online),
            ('4', 'Upgrade from a package file', install),
            ('5', 'Older versions, and whether each may be gone back to', lambda: self.act('--downgrade-check')),
            ('6', 'Go back to an older version', back),
        ])

    # ---- 0 data: the database, backups, mail ------------------------------------
    def m_data(self):
        def restore():
            f = self.ask_one('Put a copy back', 'file', str(BACKUP_DIR) + '/',
                             help_='A copy made here (ai --db-copies) or brought from elsewhere. Everything is replaced.')
            if f and self.confirm('Put the copy back', 'Every account, setting and event is replaced by what is in '
                                  '%s. A copy of now is made first.' % f, 'Put it back', danger=True):
                self.act('--db-restore', f, '--yes')

        def export():
            f = self.ask_one('Export the configuration', 'file', '/root/ai-config-%s.json' % time.strftime('%Y%m%d'))
            if f:
                self.act('--export-config', f)

        def mail():
            to = self.ask_one('A test mail', 'to', '', help_='An address the mail goes to - every step is shown.')
            if to:
                self.act('--mail-test', to)
        return self.sub('Data: copies of the database, backups, mail', [
            ('1', 'The copies of the database', lambda: self.act('--db-copies')),
            ('2', 'Make a copy now', lambda: self.act('--db-copy')),
            ('3', 'Put a copy back', restore),
            ('4', 'Backups to other machines: how they stand', lambda: self.act('--backups')),
            ('5', 'Back up now, to every destination', lambda: self.act('--backup-now')),
            ('6', 'Export the whole configuration into a file', export),
            ('7', 'Send a test mail', mail),
            ('8', 'Tidy up what has been kept long enough', lambda: self.act('--tidy')),
        ])

    # ---- 11 the service ---------------------------------------------------------
    def m_service(self):
        def restart():
            if self.confirm('Restart the service', 'The pages do not answer for a few seconds; the '
                            'terminals go on running.', 'Restart'):
                self.act_argv(['systemctl', 'restart', 'ai'], '$ systemctl restart ai',
                              quiet_ok='restarted')
                self.st_now = True

        def at_login():
            on = console_at_login()
            r = self.choose('The console at login', [
                ('on', 'On - root sees this console first when signing in'),
                ('off', 'Off - root gets the ordinary shell')],
                'It is %s now.' % ('ON' if on else 'off'), cur=0 if on else 1)
            if r and (r == 'on') != on:
                try:
                    self.note('The console at login', console_at_login_set(r == 'on'), 'ok')
                except SystemExit as e:
                    self.note('The console at login', str(e), 'bad')
        php = ' '.join(['php-fpm'] + ['php%s-fpm' % p.name[7:] for p in Path('/usr/sbin').glob('php-fpm?*')])
        return self.sub('The service', [
            ('1', 'Its state', lambda: self.act_argv(
                ['systemctl', 'status', 'ai', '--no-pager', '-n', '60', '-l'],
                '$ systemctl status ai')),
            ('2', 'Restart it', restart),
            ('3', 'The pages (nginx, PHP)', lambda: self.act_argv(
                ['systemctl', 'status', 'nginx'] + php.split() + ['--no-pager', '-n', '5'],
                '$ systemctl status nginx php-fpm')),
            ('4', 'Its journal, live', self.journal, 'plain'),
            ('5', 'The console at login: on or off', at_login),
        ])

    # ---- 3 terminals ------------------------------------------------------------------
    def m_terms(self):
        def load():
            return [t for t in self._rows(self.out('--sessions') or {}, 'terms')
                    if self.show_ended or t.get('state') != 'ended']

        def toggle():
            self.show_ended = not self.show_ended
            self.note('Terminals', 'The ended ones are %s.' % ('listed too' if self.show_ended else 'left out'))
        self.show_ended = getattr(self, 'show_ended', False)
        cols = [('id', lambda t: t.get('id'), 8, None),
                ('state', lambda t: t.get('state'), 8,
                 lambda t: {'running': 'ok', 'exited': 'warn', 'ended': 'dim'}.get(t.get('state'))),
                ('as', lambda t: t.get('run_as'), 10, None),
                ('who', lambda t: t.get('owner') or '-', 12, None),
                ('name', lambda t: t.get('title'), 28, None),
                ('folder', lambda t: t.get('path') or t.get('cwd'), 60, lambda t: 'dim')]
        return self.sub('Terminals', [
            ('1', 'Browse them (Enter: open one here, end it…)',
             lambda: self.pick('Terminals', load, cols, self.term_do,
                               empty='no terminal - make one with New Claude Code')),
            ('2', 'New Claude Code', lambda: self.term_new('claude')),
            ('3', 'New shell', lambda: self.term_new('shell')),
            ('4', 'Ended ones in the list too: on or off', toggle),
        ])

    def term_do(self, t):
        tid = t['id']
        opts = [] if t.get('state') == 'ended' else [('attach', 'Open it here (Ctrl+b d leaves it running)')]
        if t.get('state') == 'exited':
            opts.append(('restart', 'Start it again'))
        if t.get('state') == 'ended':
            opts += [('again', 'Start it again, the same way'), ('screen', 'Its last screen')]
        else:
            opts.append(('end', 'End it'))
        opts.append(('show', 'Show it all'))
        what = self.choose(t.get('title') or tid, opts, '%s · %s · %s' % (t.get('state'), t.get('run_as'),
                                                                          t.get('path') or t.get('cwd')))
        if what == 'attach':
            def go():
                self.clear_screen()
                subprocess.call(ai_argv() + ['--attach', tid])
            self.live(go)
        elif what == 'restart':
            self.act('--restart-term', tid)
        elif what == 'again':
            self.act('--again', tid)
        elif what == 'screen':
            self.show('--screen', tid)
        elif what == 'end':
            if self.confirm('End it', 'What runs in "%s" ends now.' % (t.get('title') or tid), 'End it',
                            danger=True):
                self.act('--end', tid)
        elif what == 'show':
            self.details(t.get('title') or tid, t)

    def term_new(self, kind):
        fields = [{'key': 'dir', 'label': 'working directory', 'value': os.getcwd() if os.getcwd() != '/'
                   else os.path.expanduser('~'), 'need': True, 'help': 'Where it starts - a full path.',
                   'check': lambda v, _: None if os.path.isdir(v) else 'there is no folder %s' % v},
                  {'key': 'run_as', 'label': 'runs as', 'value': 'root',
                   'help': 'The Linux account it runs as.'}]
        if kind == 'claude':
            fields += [{'key': 'how', 'label': 'start with', 'kind': 'choice', 'value': 'new',
                        'options': [('new', 'a new conversation'), ('continue', 'the last conversation of the folder'),
                                    ('pick', 'one of its conversations, chosen')]},
                       {'key': 'model', 'label': 'model', 'help': 'Empty: as Claude Code chooses; opus, sonnet…'}]
        got = self.form('New Claude Code' if kind == 'claude' else 'New shell', fields)
        if not got:
            return
        args = ['--new', got['dir'], '--run-as', got['run_as'] or 'root']
        if kind == 'shell':
            args.append('--shell')
        else:
            if got.get('how') in ('continue', 'pick'):
                args.append('--' + got['how'])
            if got.get('model'):
                args += ['--model', got['model']]
        out, rc = self.capture(ai_argv() + args + ['--json'])
        try:
            tid = json.loads(out).get('id')
        except (ValueError, AttributeError):
            tid = None
        if rc != 0 or not tid:
            self.note('New terminal', self._plain_text(out).strip() or 'it did not start', 'bad')
            return
        if self.confirm('Started', 'The terminal %s runs - on the pages too. Open it here now?' % tid,
                        'Open it', 'Not now'):
            def go():
                self.clear_screen()
                subprocess.call(ai_argv() + ['--attach', tid])
            self.live(go)

    # ---- 6 the firewall and who may reach the pages -------------------------------------
    def m_fw(self):
        def port():
            got = self.form('Let a port in', [
                {'key': 'port', 'label': 'port', 'need': True, 'help': '443, 8000-8100 or 80,443; with '
                 '/udp for UDP (53/udp).',
                 'check': lambda v, _: None if re.match(r'^\d{1,5}([-,]\d{1,5})*(/(tcp|udp))?$', v)
                 else 'a port, a range or ports by commas, /tcp or /udp'},
                {'key': 'from', 'label': 'from', 'help': 'An address or a network. Empty: from anywhere.'},
                {'key': 'note', 'label': 'note', 'help': 'Shown on the pages and as the rule\'s comment.'}])
            if got:
                self.act('--fw-open', got['port'], *(['--from', got['from']] if got.get('from') else []),
                         *(['--note', got['note']] if got.get('note') else []))

        def drop():
            n = self.ask_one('Take a rule of your own away', 'its number', help_=(
                'The number `ai --fw status` shows by it.'),
                check=lambda v, _: None if v.isdigit() else 'a number')
            if n:
                self.act('--fw-del', n)

        def pages():
            got = self.ask_one('Who may reach the pages', 'networks', help_=(
                'Comma between: 192.168.0.0/16,10.0.0.0/8 - or all for everybody. This machine always may. '
                'It goes back by itself unless kept.'), need=True)
            if got:
                self.act('--pages-from', got)

        def onoff():
            r = self.choose('ai\'s firewall rules', [
                ('on', 'On - the chain AI-IN first in INPUT (iptables), or rich rules (firewalld)'),
                ('off', 'Off - ai\'s rules taken away; the rest of the firewall stays as it is')])
            if r:
                self.act('--fw', r)
        return self.sub('Firewall and access', [
            ('1', 'How it stands', lambda: self.act('--fw', 'status')),
            ('2', 'Open HTTP and HTTPS (the pages) in the firewall', lambda: self.act('--open-web')),
            ('3', 'Let a port in', port),
            ('4', 'Take a rule of your own away', drop),
            ('5', 'ai\'s firewall rules on or off', onoff),
            ('6', 'Who may reach the pages', pages),
            ('7', 'Keep the change waiting to be kept', lambda: self.act('--change-keep', 'all')),
            ('8', 'Put the old back now', lambda: self.act('--change-back', 'all')),
        ])

    # ---- 7 the server ---------------------------------------------------------------------
    def m_server(self):
        def keyadd():
            got = self.ask_one('Add a public key for root', 'the key', help_=(
                'One line of a .pub file: ssh-ed25519 AAAA… you@laptop'), need=True)
            if got:
                self.act('--sshkey-add', got)

        def power(how):
            if self.confirm('Restart the server' if how == 'reboot' else 'Switch the server off',
                            'Every terminal ends with it.' + ('' if how == 'reboot' else
                                                             ' It stays off until somebody switches it on.'),
                            'Restart' if how == 'reboot' else 'Switch it off', danger=True):
                self.act('--' + how, '--yes')
        return self.sub('The server', [
            ('1', 'The network', lambda: self.act('--net')),
            ('2', 'The time (chrony)', lambda: self.act('--ntp')),
            ('3', 'Look for system updates', lambda: self.act('--osup', 'check')),
            ('4', 'Update the system now, followed live', lambda: self.show_live('--osup', 'upgrade'), 'plain'),
            ('5', 'SSH keys of root', lambda: self.act('--sshkeys')),
            ('6', 'Add a public key for root', keyadd),
            ('7', 'The certificate of the pages', lambda: self.act('--cert')),
            ('8', 'Restart the server', lambda: power('reboot')),
            ('9', 'Switch the server off', lambda: power('poweroff')),
        ])



# In /etc itself, where only root writes (as otp's).
CONSOLE_FLAG = Path(os.environ.get('AI_CONSOLE_FLAG', '/etc/ai-console-login'))
CONSOLE_PROFILE = Path('/etc/profile.d/zz-ai-console.sh')


def console_at_login():
    try:
        fd = os.open(str(CONSOLE_FLAG), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return False
        return os.read(fd, 8).decode('ascii', 'replace').strip() == 'on'
    finally:
        os.close(fd)


def console_at_login_set(on):
    if os.geteuid() != 0:
        raise SystemExit('ai: only root sets that')
    # Written beside it and put in its place: a link or a pipe found there is
    # replaced, never followed.
    tmp = '%s.%d.tmp' % (CONSOLE_FLAG, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        os.write(fd, b'on\n' if on else b'off\n')
        os.fchmod(fd, 0o644)
    finally:
        os.close(fd)
    os.rename(tmp, str(CONSOLE_FLAG))
    return ('the ai console opens when root signs in at the console or over SSH (q leaves '
            'it for the shell)' if on else 'root signs in to the ordinary shell; '
            '`ai --console` opens the console')


def console_main(pal):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit('ai: the console needs a terminal')
    return Console(pal).run()


def ai_argv():
    """How this program runs itself again (the console's commands)."""
    me = str(LIB_DIR / 'ai.py') if (LIB_DIR / 'ai.py').is_file() else os.path.abspath(__file__)
    return [sys.executable, me]


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------
# Everything the pages can do that a server needs at two in the morning, as
# otp's command line does it: in colour on a terminal (colorama when it is
# there), plain anywhere else, `--json` for a script and for the console.
# It talks to the database and the machine directly, never through the API -
# the moment the command line is most needed is the moment nobody can sign in.
HELP_EXAMPLES = [
    ('ai', 'what it is doing (the same as --status)'),
    ('ai --console', 'everything by its menus, on this screen'),
    ('ai --check', 'every part of it: tmux, Claude Code, nginx, PHP, the certificate, the firewall'),
    ('ai --open-web', 'HTTP and HTTPS let in by the firewall (firewalld, ufw or iptables)'),
    ('ai --fw-open 8080 --from 10.0.0.0/8', 'a port of your own let in'),
    ('ai --pages-from 192.168.0.0/16,10.0.0.0/8', 'who may reach the pages (all = everybody)'),
    ('ai --sessions', 'the terminals, running and ended'),
    ('ai --attach 1a2b3c4d', 'one of them, here; Ctrl+b d leaves it running'),
    ('ai --new /srv/project --continue', 'Claude Code in a folder, its last conversation'),
    ('ai --add-user jan --role user --run-as jan', 'the password asked for (or AI_PASSWORD)'),
    ('ai --set upgrade_auto=1', 'a setting changed'),
    ('ai --upgrade-online', 'the newest version: fetched, checked, put in'),
]


def build_parser():
    p = HelpfulParser(prog='ai', add_help=False, allow_abbrev=False,
                      usage='ai [--json] [--no-color] [what to do]',
                      description='Claude Code on this server, from a web browser')
    g = p.add_argument_group('EVERYWHERE')
    g.add_argument('-h', '--help', action='store_true', help='this, and stop')
    g.add_argument('--version', action='store_true', help='which version this is, and stop')
    g.add_argument('--no-color', '--no-colour', action='store_true', dest='no_color',
                   help='plain text, no colour')
    g.add_argument('--json', action='store_true', help='answer as JSON where it makes sense')
    g.add_argument('--yes', action='store_true', help='never ask')
    g.add_argument('--daemon', action='store_true', help='run the daemon in the foreground (what systemd starts)')
    g.add_argument('--console', action='store_true', help='ai by its menus, on this screen (q leaves it)')
    g.add_argument('--console-at-login', choices=('on', 'off', 'status'), metavar='on|off|status',
                   help='the console when root signs in, or the ordinary shell')
    g = p.add_argument_group('LOOKING', 'Reading what it knows. None of these change anything.')
    g.add_argument('--status', action='store_true', help='what it is doing, in one screen')
    g.add_argument('--check', action='store_true', help='a health check, every part of it')
    g.add_argument('--events', action='store_true', help='what happened: sign-ins, terminals, changes')
    g.add_argument('--log', action='store_true', help='its own log, the last lines')
    g.add_argument('--sign-ins', action='store_true', help='who is signed in to the pages now')
    g.add_argument('--limit', type=int, default=40, metavar='N', help='how many rows [40]')
    g.add_argument('--search', metavar='TEXT', default='', help='only rows holding this')
    g = p.add_argument_group('TERMINALS', 'Claude Code and shells in tmux: they go on when nobody looks.')
    g.add_argument('--sessions', action='store_true', help='the terminals, running and ended')
    g.add_argument('--attach', metavar='ID', help='one terminal, here (Ctrl+b d leaves it running)')
    g.add_argument('--screen', metavar='ID', help='what one shows now (or its last screen)')
    g.add_argument('--new', metavar='DIR', help='a new terminal in DIR: Claude Code, or --shell')
    g.add_argument('--shell', action='store_true', help='with --new: a shell, not Claude Code')
    g.add_argument('--continue', action='store_true', dest='cont',
                   help='with --new: the last conversation of the folder')
    g.add_argument('--pick', action='store_true', help='with --new: choose one of its conversations')
    g.add_argument('--model', default='', help='with --new: the model (opus, sonnet…)')
    g.add_argument('--title', default='', help='with --new: its name')
    g.add_argument('--end', metavar='ID', help='end a terminal')
    g.add_argument('--restart-term', metavar='ID', help='start what ran in a terminal again')
    g.add_argument('--again', metavar='ID', help='an ended terminal started afresh, the same way')
    g = p.add_argument_group('ACCOUNTS', 'Who may sign in to the pages.')
    g.add_argument('--users', action='store_true', help='the accounts')
    g.add_argument('--add-user', metavar='NAME', help='an account (--role, --run-as; the password asked)')
    g.add_argument('--role', default='user', choices=ROLES, help='with --add-user, --set-role [user]')
    g.add_argument('--run-as', default='', metavar='ACCOUNT', help='the Linux account its terminals run as')
    g.add_argument('--password', default='', help='its password (otherwise asked, or AI_PASSWORD)')
    g.add_argument('--make-password', action='store_true', help='make a password, print it, to be changed')
    g.add_argument('--passwd', metavar='NAME', help='a new password for an account')
    g.add_argument('--del-user', '--drop-user', metavar='NAME', dest='del_user', help='an account taken away')
    g.add_argument('--disable-user', metavar='NAME', help='may no longer sign in (its terminals go on)')
    g.add_argument('--enable-user', metavar='NAME', help='may sign in again')
    g.add_argument('--set-role', metavar='NAME', help='its role, from --role')
    g.add_argument('--set-run-as', nargs=2, metavar=('NAME', 'ACCOUNT'),
                   help='the Linux account its terminals run as (- for the default)')
    g.add_argument('--end-sign-ins', metavar='NAME', help='every sign-in of an account ended')
    g.add_argument('--admin-2fa', choices=('status', 'on', 'off'), metavar='status|on|off',
                   help='the second step of signing in, for everybody: how it stands, on or off')
    g.add_argument('--reset-2fa', metavar='NAME', help='the second step of an account taken away (set up again)')
    g.add_argument('--lockouts', action='store_true', help='who is locked out, or counted, after wrong passwords')
    g.add_argument('--unlock', metavar='WHO|all', help='a lockout cleared: an address, a name, or all')
    g = p.add_argument_group('THE DATABASE AND THE CONFIGURATION')
    g.add_argument('--db-copy', '--backup', action='store_true', dest='db_copy',
                   help='a copy of the database now (any engine takes it back), its key beside it')
    g.add_argument('--dump', action='store_true', help='with --db-copy: a dump by the engine\'s own program too')
    g.add_argument('--db-copies', action='store_true', help='the copies and the dumps kept (/var/lib/ai/backups, /var/lib/ai/dumps)')
    g.add_argument('--db-restore', '--restore', metavar='FILE', dest='db_restore',
                   help='a copy put back (everything replaced; --yes)')
    g.add_argument('--tidy', action='store_true', help='delete what has been kept long enough (events, sign-ins, copies)')
    g.add_argument('--export-config', metavar='FILE', help='the whole configuration into a file (- for stdout)')
    g.add_argument('--with-secrets', action='store_true', help='with --export-config: the secrets too, locked')
    g.add_argument('--import-config', metavar='FILE', help='a configuration taken in (--replace: exactly the file; --yes)')
    g.add_argument('--replace', action='store_true', help='with --import-config: what is not in the file goes')
    g.add_argument('--backup-now', '--rbackup-now', action='store_true', dest='backup_now',
                   help='a backup made and sent to every destination switched on')
    g.add_argument('--backups', '--rbackup-status', action='store_true', dest='backups',
                   help='the destinations of the backups and what was sent')
    g.add_argument('--backup-file', metavar='FILE', help='a backup made into a file here (locked with its password)')
    g.add_argument('--restore-bundle', metavar='FILE', help='a backup put back (AI_BACKUP_PASSWORD; --yes)')
    g.add_argument('--passphrase-file', metavar='FILE', help='with --restore-bundle: the password of the backups, one line')
    g = p.add_argument_group('MAIL')
    g.add_argument('--mail-test', metavar='ADDRESS', help='a test mail sent, every step shown')
    g = p.add_argument_group('SETTINGS')
    g.add_argument('--settings', action='store_true', help='every setting and its value')
    g.add_argument('--set', action='append', metavar='KEY=VALUE', default=[],
                   help='a setting changed (VALUE @env: from AI_VALUE_KEY)')
    g.add_argument('--setting', nargs=2, metavar=('KEY', 'VALUE'), help=argparse.SUPPRESS)
    g = p.add_argument_group('FIREWALL AND ACCESS', 'A change goes back by itself unless kept (--change-keep).')
    g.add_argument('--fw', choices=('status', 'on', 'off'), metavar='status|on|off',
                   help='ai\'s firewall rules: how they stand, or on or off')
    g.add_argument('--open-web', action='store_true',
                   help='HTTP and HTTPS let in: firewalld\'s services, ufw, or ai\'s rules (iptables)')
    g.add_argument('--fw-open', metavar='PORT[/udp]', help='a rule of your own: a port (443, 8000-8100, 80,443)')
    g.add_argument('--from', default='', dest='source', metavar='CIDR', help='with --fw-open: only from there')
    g.add_argument('--note', default='', help='with --fw-open: what it is for')
    g.add_argument('--fw-del', type=int, metavar='N', help='a rule of your own taken away (its number)')
    g.add_argument('--pages-from', metavar='CIDR,..|all', help='who may reach the pages')
    g.add_argument('--change-keep', choices=('net', 'fw', 'access', 'all'), help='keep a change on trial')
    g.add_argument('--change-back', choices=('net', 'fw', 'access', 'all'), help='put the old back now')
    g = p.add_argument_group('THE SERVER')
    g.add_argument('--net', action='store_true', help='its network, as NetworkManager has it')
    g.add_argument('--ntp', action='store_true', help='its clock: chrony, the time servers, the zone')
    g.add_argument('--osup', choices=('status', 'check', 'upgrade'), metavar='status|check|upgrade',
                   help='the system\'s updates: what waits, looked for, or put in (followed here)')
    g.add_argument('--sshkeys', action='store_true', help='the keys that may sign in as root')
    g.add_argument('--sshkey-add', metavar='LINE', help='a public key for root (ssh-ed25519 AAAA…)')
    g.add_argument('--cert', '--web-status', action='store_true', dest='cert',
                   help='the certificate of the pages and how TLS is spoken')
    g.add_argument('--tls-import', nargs='+', metavar='FILE', help='a certificate in: PEM files (certificate, key, '
                   'chain, root - in any order, or all in one) or a .pfx / .p12; its password in AI_TLS_PASSWORD')
    g.add_argument('--tls-preset', choices=['standard', 'intermediate', 'modern'],
                   help='the protocols and ciphers: standard (TLS 1.2+1.3, ECDHE), intermediate (Mozilla, with DHE), '
                   'modern (TLS 1.3 only)')
    g.add_argument('--tls-dh', choices=sorted(DH_WORDS), help='the DH parameters')
    g.add_argument('--tls-hsts', type=int, metavar='SECONDS', help='Strict-Transport-Security (0 = none)')
    g.add_argument('--reboot', action='store_true', help='restart the server (asks, or --yes)')
    g.add_argument('--poweroff', action='store_true', help='switch the server off (asks, or --yes)')
    g = p.add_argument_group('UPGRADES')
    g.add_argument('--upgrade-check', action='store_true', help='whether a newer version is out')
    g.add_argument('--downgrade', metavar='VERSION', help='back to an older version at upgrade_url - only a safe one')
    g.add_argument('--upgrade-online', nargs='?', const='newest', metavar='VERSION',
                   help='fetch the newest (or VERSION) from upgrade_url and put it in')
    g.add_argument('--upgrade-status', action='store_true', help='the last upgrade, and what it said')
    g.add_argument('--upgrade-follow', action='store_true', help='follow an upgrade going on until it ends')
    g.add_argument('--downgrade-check', action='store_true', help='the versions at upgrade_url older than this one, '
                   'and whether each may be gone back to')
    return p


class CliDaemon(object):
    """What the parts shared with the daemon need of it, on the command line:
    a change on trial is taken back by the running daemon if not kept."""

    def __init__(self, store):
        self.store = store
        self.trials = Trials(self)
        self.upgrades = Upgrades(self)
        self.started = time.time()
        self.osup_checking = False


def rbWhere_cli(t):
    if t.get('kind') == 'folder':
        return t.get('path') or ''
    if t.get('kind') == 'smb':
        return '\\\\%s\\%s\\%s' % (t.get('host'), t.get('share') or '', t.get('path') or '')
    return '%s%s:%s/%s' % ((t['user'] + '@') if t.get('user') else '', t.get('host'), t.get('port'),
                           str(t.get('path') or '').lstrip('/'))


def cli_store():
    if os.geteuid() != 0 and not DB_FILE.exists():
        raise SystemExit('ai: %s is not there - run as root' % DB_FILE)
    try:
        st = Store(DB_FILE)
    except DbError as e:
        raise SystemExit('ai: the database does not open: %s' % e)
    config_rebuild(st)
    STORE_NOW['store'] = st
    return st


def ago(ts):
    if not ts:
        return '-'
    s = int(time.time() - float(ts))
    for unit, n in (('d', 86400), ('h', 3600), ('min', 60)):
        if s >= n:
            return '%d %s ago' % (s // n, unit)
    return '%d s ago' % s


def when(ts):
    return time.strftime('%d-%m-%Y %H:%M', time.localtime(float(ts))) if ts else '-'


def daemon_alive():
    try:
        token = TOKEN_FILE.read_text().strip()
        req = urllib.request.Request('http://127.0.0.1:%d/api/health' % int(CONFIG.get('api_port') or 9871),
                                     headers={'X-Ai-Token': token})
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except Exception:                                   # noqa: BLE001
        return False


def status_row(d):
    st = d.store
    tm = Terms(st)
    terms = tm.list({'name': 'cli', 'role': 'admin'})
    online = st.meta_json('upgrade:online', {}) or {}
    newest = online.get('newest') or {}
    problems = []
    if not which('tmux'):
        problems.append('tmux is not installed: no terminal can start')
    cert = cert_facts()
    if cert.get('until_ts') and cert['until_ts'] - time.time() < 14 * 86400:
        problems.append('the certificate of the pages runs out %s' % cert.get('until'))
    alive = daemon_alive()
    if not alive:
        problems.append('the daemon is not answering (systemctl status ai)')
    return {'version': __version__, 'host': host_name(), 'daemon_alive': alive,
            'terms': len([t for t in terms if t['state'] != 'ended']),
            'signed_in': len(st.q('SELECT id FROM sessions')), 'accounts': len(st.users()),
            'newer': newest.get('version') if newest and ver_tuple(newest.get('version')) > ver_tuple(__version__) else '',
            'trials': d.trials.view(), 'problems': problems, 'term_list': terms,
            'upgrade_url': CONFIG.get('upgrade_url'), 'looked': online.get('at')}


def say_json(obj):
    print(json.dumps(obj, indent=2, default=str, ensure_ascii=False))


def cli_status(d, pal, as_json):
    s = status_row(d)
    if as_json:
        say_json(s)
        return 0
    print('%s %s on %s - the daemon is %s' % (pal.head('ai'), pal.bold(__version__), pal.bold(s['host']),
                                              pal.good('answering') if s['daemon_alive'] else pal.bad('NOT answering')))
    print('  database     %s' % DB_FILE)
    print('  accounts     %d, %d signed in now' % (s['accounts'], s['signed_in']))
    print('  terminals    %d running' % s['terms'])
    live = [t for t in s['term_list'] if t['state'] != 'ended']
    if live:
        print(table([[t['id'], t['state'], t['run_as'], t['owner'] or '-', t['title'], t['path']] for t in live],
                    ['id', 'state', 'as', 'who', 'name', 'folder']))
    if s['newer']:
        print(pal.warn_line('ai %s is out - ai --upgrade-online' % s['newer']))
    for t in s['trials']:
        print(pal.warn_line('%s waits to be kept: %d s left (ai --change-keep %s)' % (t['words'], t['left'], t['kind'])))
    for pr in s['problems']:
        print(pal.bad_line(pr))
    return 0 if s['daemon_alive'] else 1


def cli_check(d, pal, as_json):
    out = []

    def one(what, ok, said, warn=False):
        out.append({'what': what, 'ok': bool(ok), 'warn': bool(warn and not ok), 'said': said})
    one('tmux', which('tmux'), first_line([tmux_bin(), '-V']) or 'not installed')
    one('python', sys.version_info >= (3, 9), sys.version.split()[0])
    alive = daemon_alive()
    one('the daemon', alive, 'answering on 127.0.0.1:%s' % CONFIG.get('api_port') if alive
        else 'not answering - systemctl status ai')
    try:
        g = grp.getgrnam(WEB_GROUP)
        st = os.stat(str(TOKEN_FILE))
        one('the pages\' token', st.st_gid == g.gr_gid and st.st_mode & 0o040, '%s, group %s' % (TOKEN_FILE, WEB_GROUP))
    except (KeyError, OSError) as e:
        one('the pages\' token', False, str(e))
    rc, so, se = run(['nginx', '-t'], timeout=20)
    one('nginx', rc == 0, ((se or so).strip().splitlines() or ['?'])[-1])
    php = [p for p in Path('/run/php-fpm').glob('ai.sock')] + [p for p in Path('/run/php').glob('ai.sock')]
    one('php-fpm', bool(php), str(php[0]) if php else 'the socket ai.sock is not there - is php-fpm running?')
    c = cert_facts()
    days = int((c['until_ts'] - time.time()) // 86400) if c.get('until_ts') else None
    one('the certificate', c.get('there') and (days is None or days > 14),
        '%s days left%s' % (days, ', self-signed' if c.get('self_signed') else '') if c.get('there') else 'not there',
        warn=c.get('there'))
    b = fw_backend()
    if b == 'firewalld':
        rc, so, _se = run(['firewall-cmd', '--list-services'], timeout=10)
        rc2, so2, _se2 = run(['firewall-cmd', '--list-ports'], timeout=10)
        web = 'https' in so.split() or '443/tcp' in so2.split() or bool(fw_conf(d.store)['on'])
        one('the firewall', web, 'firewalld: %s' % ('HTTPS is let in' if web else
                                                   'HTTPS is NOT let in - ai --open-web'))
    elif b == 'ufw':
        rc, so, _se = run(['ufw', 'status'], timeout=10)
        web = re.search(r'^(443|443/tcp|Nginx Full|80,443/tcp)\b.*ALLOW', so, re.M) is not None
        one('the firewall', web, 'ufw: %s' % ('HTTPS is let in' if web else 'HTTPS is NOT let in - ai --open-web'))
    else:
        c2 = fw_conf(d.store)
        one('the firewall', True, '%s%s' % (b or 'none', ', ai\'s rules on' if c2['on'] else ''))
    if which('getenforce'):
        rc, so, _se = run(['getenforce'], timeout=5)
        if so.strip() not in ('Disabled', ''):
            rc, so2, _se = run(['getsebool', 'httpd_can_network_connect'], timeout=5)
            one('SELinux', 'on' in so2, so2.strip() or '?')
    for name in sorted({run_as_of(u) for u in d.store.users()} | {'root'}):
        try:
            f = claude_facts(linux_user(name), fresh=True)
            one('Claude Code for %s' % name, bool(f.get('version')),
                (f.get('version') or 'not installed - Settings - Claude Code, or: curl -fsSL '
                 'https://claude.ai/install.sh | bash') + (', signed in' if f.get('signed_in') else ''),
                warn=True)
        except Refused as e:
            one('Claude Code for %s' % name, False, str(e))
    du = shutil.disk_usage(str(STATE_DIR) if STATE_DIR.exists() else '/')
    one('the disk', du.free > 1 << 30, '%s free' % human_bytes(du.free))
    if as_json:
        say_json({'checks': out, 'ok': all(x['ok'] or x['warn'] for x in out)})
    else:
        for x in out:
            line = '%-22s %s' % (x['what'], x['said'])
            print(pal.ok_line(line) if x['ok'] else (pal.warn_line(line) if x['warn'] else pal.bad_line(line)))
    return 0 if all(x['ok'] or x['warn'] for x in out) else 1


def cli_fw_status(d, pal, as_json):
    v = fw_view(d)
    n = v['nodes'][0]
    if as_json:
        say_json(v)
        return 0
    c, a = v['conf'], v['access'].get('pages') or {}
    print('%s  %s' % (pal.head('the firewall'), n['fw'].get('backend') or 'none'))
    print('  ai\'s rules     %s' % ('on' if c['on'] else 'off'))
    print('  the pages      from %s' % ('everybody' if a.get('any') else ', '.join(a.get('from') or [])))
    if c['rules']:
        print(pal.head('\nrules of your own'))
        print(table([[i + 1, r['action'], 'IPv%s' % r['family'] if r['family'] else 'both',
                      r['proto'] + ((' ' + r['port']) if r['port'] else ''), r['source'] or 'anywhere',
                      'off' if r.get('disabled') else 'on', r.get('note') or ''] for i, r in enumerate(c['rules'])],
                    ['#', 'action', 'ip', 'what', 'from', 'state', 'note']))
    print(pal.head('\nwhat ai lets in by itself'))
    print(table([[x['key'], 'off' if x['key'] in c['off'] else 'on', x['title'],
                  ', '.join('%s %s%s' % (r['proto'], r['port'], ' from ' + r['source'] if r['source'] else '')
                            for r in x['rules'])] for x in n['auto']], ['key', 'state', 'what', 'rules']))
    for t in v['trials']:
        print(pal.warn_line('%s waits to be kept: %d s left (ai --change-keep %s)' % (t['words'], t['left'], t['kind'])))
    return 0


def cli_fw_save(d, pal, conf=None, access=None):
    c = fw_conf(d.store) if conf is None else conf
    body = {'on': c['on'], 'off': c['off'], 'rules': c['rules']}
    if access is not None:
        body['access'] = access
        body['even_if_me'] = True
    got = fw_save(d, body, 'the command line', '127.0.0.1')
    print(pal.ok_line(got['message']))
    print(pal.dim('  ai --change-keep fw keeps it; ai --change-back fw puts the old back'))
    return 0


def cli_open_web(d, pal):
    """HTTP and HTTPS let in, by whatever looks after this machine's firewall."""
    b = fw_backend()
    c = fw_conf(d.store)
    if c['on']:
        if 'web' in c['off']:
            c['off'] = [k for k in c['off'] if k != 'web']
        fw_put(d, c)
        d.store.set_meta_json('fw:conf', dict(c, at=time.time(), by='the command line'))
        print(pal.ok_line('ai\'s rules let 80 and 443 in (%s)' % b))
    if b == 'firewalld':
        for svc in ('http', 'https'):
            run(['firewall-cmd', '--permanent', '--add-service=' + svc], timeout=30, check=True)
        run(['firewall-cmd', '--reload'], timeout=60, check=True)
        print(pal.ok_line('firewalld: the services http and https are let in, now and after a restart'))
    elif b == 'ufw':
        for port in ('80/tcp', '443/tcp'):
            run(['ufw', 'allow', port], timeout=30, check=True)
        print(pal.ok_line('ufw: 80/tcp and 443/tcp allowed'))
    elif b == 'iptables' and not c['on']:
        done = []
        for fam in (4, 6):
            tool = FW_TOOLS[fam][0]
            if not which(tool):
                continue
            rule = ['INPUT', '-p', 'tcp', '-m', 'multiport', '--dports', '80,443', '-m', 'comment',
                    '--comment', 'ai: the pages', '-j', 'ACCEPT']
            if run([tool, '-C'] + rule, timeout=10)[0] != 0:
                run([tool, '-I'] + rule[:1] + ['1'] + rule[1:], timeout=10, check=True)
            for path in FW_FILES[fam]:
                if os.path.exists(path):
                    rc, so, _se = run([FW_TOOLS[fam][2]], timeout=30)
                    if rc == 0 and so.strip():
                        write_atomic(path, so, mode=0o600)
                    break
            done.append('IPv%d' % fam)
        print(pal.ok_line('iptables: 80 and 443 let in first in INPUT (%s)' % ', '.join(done)))
    elif b == 'test':
        print(pal.ok_line('a test machine: nothing changed'))
    elif not c['on']:
        print(pal.ok_line('there is no firewall running here - 80 and 443 are open already'))
    return 0


def cli_trial(d, pal, kind, keep):
    kinds = [kind] if kind != 'all' else [t['kind'] for t in d.trials.view()]
    if not kinds:
        print(pal.ok_line('nothing waits to be kept'))
        return 0
    for k in kinds:
        ok = d.trials.keep(k, 'the command line') if keep else d.trials.back(k, 'the command line')
        print((pal.ok_line if ok else pal.warn_line)('%s: %s' % (k, ('kept' if keep else 'the old is back')
                                                              if ok else 'nothing waited')))
    return 0


def cli_terms_new(d, a, pal):
    u = {'name': 'cli', 'role': 'admin', 'run_as': a.run_as or '', 'roots': '[]'}
    opts = {}
    if a.cont:
        opts['continue'] = True
    if a.pick:
        opts['pick'] = True
    if a.model:
        opts['model'] = a.model
    tid = Terms(d.store).new(u, 'shell' if a.shell else 'claude', a.new, a.title, opts,
                             run_as=a.run_as or str(CONFIG.get('default_run_as') or 'root'))
    if a.json:
        say_json({'id': tid})
    else:
        print(pal.ok_line('started %s - ai --attach %s (and on the pages)' % (tid, tid)))
    return 0


def cli_osup(d, a, pal):
    if a.osup == 'check' or a.osup == 'upgrade':
        if a.osup == 'upgrade' and not a.yes and sys.stdin.isatty() and \
                input('update every package of the system now? [y/N] ').strip().lower() not in ('y', 'yes', 'a', 'ano'):
            return 1
        r = osup_do(d, {'action': 'check' if a.osup == 'check' else 'start', 'reboot': 'ask'}, 'the command line')
        print(pal.ok_line(r['message']))
        seen = 0
        while True:
            time.sleep(1.0)
            st = osup_state()
            lines = st.get('lines') or []
            for ln in lines[seen:]:
                print('  ' + term_safe(ln))
            seen = len(lines)
            if st.get('state') in ('done', 'failed'):
                break
        v = osup_view(d)
        ck = v['nodes'][0]['check']
        if a.osup == 'check':
            print(pal.ok_line('%s update(s) waiting%s' % (ck.get('count', 0), ', a restart is wanted now'
                                                          if ck.get('reboot_now') else '')))
        else:
            print((pal.ok_line if st.get('state') == 'done' else pal.bad_line)('the update: %s' % st.get('state')))
            if st.get('reboot'):
                print(pal.warn_line('a restart is needed - ai --reboot'))
        return 0 if st.get('state') == 'done' else 1
    v = osup_view(d)
    ck = v['nodes'][0]['check']
    if a.json:
        say_json(v)
        return 0
    print('%s  %s' % (pal.head('the system\'s updates'), ck.get('pm') or pkg_manager()))
    print('  waiting        %s' % (ck.get('count', 0) if ck.get('checked') else 'not looked yet - ai --osup check'))
    print('  looked         %s' % when(ck.get('checked')))
    print('  a restart      %s' % ('wanted now' if ck.get('reboot_now') else 'not wanted'))
    for pk in (ck.get('packages') or [])[:a.limit]:
        print('    ' + pk)
    return 0


def cli_main(argv):
    said = list(argv)
    parser = build_parser()
    pal = Palette(colour_wanted('--no-color' in said or '--no-colour' in said) and '--json' not in said)
    parser.palette = pal
    global TABLE_PAL
    TABLE_PAL = pal
    a = parser.parse_args(argv)
    if (pal.on or sys.stdout.isatty()) and not a.console and not a.json and not a.daemon and \
            not a.attach and not isinstance(sys.stdout, ColourOut):
        sys.stdout = ColourOut(sys.stdout, pal)
    if a.help:
        sys.stdout.write(parser.format_help())
        return 0
    if a.version:
        print('%s %s%s' % (pal.head('ai'), pal.bold(__version__), '' if HAVE_COLORAMA
                           else pal.dim('  (colorama is not installed; colour is written by hand)')))
        return 0
    if a.daemon:
        Daemon().run()
        return 0
    if a.console_at_login:
        if a.console_at_login != 'status':
            print(pal.ok_line(console_at_login_set(a.console_at_login == 'on')))
        else:
            print(pal.ok_line('the console at login is %s' % ('ON' if console_at_login() else 'off')))
        if not CONSOLE_PROFILE.exists():
            print(pal.warn_line('%s is not there - install.sh puts it in' % CONSOLE_PROFILE))
        return 0
    if a.console:
        return console_main(pal)
    st = cli_store()
    d = CliDaemon(st)
    auth = Auth(st)
    tm = Terms(st)
    admin = {'name': 'cli', 'role': 'admin'}
    try:
        # ---- terminals ------------------------------------------------------------
        if a.sessions:
            terms = tm.list(admin)
            if a.json:
                say_json({'terms': terms})
            else:
                print(table([[t['id'], t['state'], t['run_as'], t['owner'] or '-', t['title'], t['path'],
                              ago(t['activity'])] for t in terms],
                            ['id', 'state', 'as', 'who', 'name', 'folder', 'last']))
            return 0
        if a.attach:
            r = tm.row(a.attach)
            pw = linux_user(r['run_as'])
            if r['id'] not in tm.live(True):
                raise Refused('that terminal has ended (ai --again %s starts it afresh)' % r['id'])
            sock = str(TMUX_DIR / pw.pw_name / 'sock')
            cmd = [tmux_bin(), '-u', '-S', sock, 'attach-session', '-t', 'ai-' + r['id']]
            if os.geteuid() == 0 and pw.pw_uid != 0:
                cmd = ['runuser', '-u', pw.pw_name, '--'] + cmd
            os.execvp(cmd[0], cmd)
        if a.screen:
            r = tm.row(a.screen)
            print(tm.capture(r, 200) if r['id'] in tm.live(True) else (r.get('last_screen') or '(nothing kept)'))
            return 0
        if a.new:
            return cli_terms_new(d, a, pal)
        if a.end or a.restart_term or a.again:
            r = tm.row(a.end or a.restart_term or a.again)
            if a.end:
                tm.kill(admin, r)
                print(pal.ok_line('%s ended' % r['id']))
            elif a.restart_term:
                tm.restart(admin, r)
                print(pal.ok_line('%s started again' % r['id']))
            else:
                print(pal.ok_line('started %s - ai --attach %s' % ((tid := tm.again(admin, r)), tid)))
            return 0
        # ---- accounts ---------------------------------------------------------------
        if a.users:
            users = [user_view(u) for u in st.users()]
            if a.json:
                say_json({'users': users})
            else:
                print(table([[u['name'], u['role'], 'off' if u['disabled'] else 'on', u['run_as'],
                              when(u['last_login']), u['note']] for u in users],
                            ['account', 'role', 'state', 'runs as', 'last in', 'note']))
            return 0
        if a.add_user or a.passwd:
            name = a.add_user or a.passwd
            pw_ = a.password or os.environ.get('AI_PASSWORD') or (new_password() if a.make_password else '')
            if not pw_:
                pw_ = ask_password('a password for %s' % name)
            if a.add_user:
                auth.add_user(name, pw_, a.role, a.run_as, must_change=a.make_password, by='the command line')
            else:
                auth.set_password(name, pw_, 'the command line', must_change=a.make_password)
                st.x('DELETE FROM sessions WHERE name=?', (name,))
            print('%s: done%s' % (name, ' - password: %s' % pw_ if a.make_password else ''))
            return 0
        if a.del_user:
            auth.drop_user(a.del_user, 'the command line')
            print(pal.ok_line('%s taken away' % a.del_user))
            return 0
        if a.disable_user or a.enable_user:
            auth.edit_user(a.disable_user or a.enable_user, 'the command line', disabled=bool(a.disable_user))
            print(pal.ok_line('%s %s' % (a.disable_user or a.enable_user, 'switched off' if a.disable_user else 'switched on')))
            return 0
        if a.set_role:
            auth.edit_user(a.set_role, 'the command line', role=a.role)
            print(pal.ok_line('%s is %s' % (a.set_role, ROLE_WORDS[a.role])))
            return 0
        if a.set_run_as:
            name, acct = a.set_run_as
            auth.edit_user(name, 'the command line', run_as='' if acct == '-' else acct)
            print(pal.ok_line('the terminals of %s run as %s' % (name, 'the default' if acct == '-' else acct)))
            return 0
        if a.admin_2fa:
            if a.admin_2fa != 'status':
                on = a.admin_2fa == 'on'
                st.set_setting('admin_2fa', on, 'the command line')
                CONFIG['admin_2fa'] = on
                if on:
                    n = st.x('DELETE FROM sessions')
                    print(pal.warn_line('%d sign-in(s) ended: each gives its second step now' % n))
                st.add_event('settings', 'the command line switched the second step of signing in %s'
                             % ('on' if on else 'off'), 'warn')
            mfa = mfa_all(st)
            have = [u['name'] for u in st.users() if u['name'].lower() in mfa]
            if a.json:
                say_json({'admin_2fa': bool(CONFIG.get('admin_2fa')), 'ways': mfa_methods(), 'set_up': have})
                return 0
            print(pal.ok_line('the second step of signing in is %s%s' % (
                'ON' if CONFIG.get('admin_2fa') else 'off',
                (' - offered: %s' % ', '.join(mfa_methods())) if CONFIG.get('admin_2fa') else '')))
            print('set up: %s' % (', '.join('%s (%s)' % (n, mfa[n.lower()]['kind']) for n in have) or 'nobody'))
            return 0
        if a.reset_2fa:
            if not st.user(a.reset_2fa):
                raise Refused('there is no account %s' % a.reset_2fa)
            had = mfa_reset(st, a.reset_2fa, 'the command line')
            st.x('DELETE FROM sessions WHERE name=?', (a.reset_2fa,))
            print(pal.ok_line('%s: %s' % (a.reset_2fa, 'reset - set up again at the next sign-in' if had
                                          else 'no second step was set up')))
            return 0
        if a.lockouts:
            rows = lockouts_view(st)
            if a.json:
                say_json({'lockouts': rows})
                return 0
            if not rows:
                print(pal.ok_line('nobody is locked out, and no wrong attempt is being counted'))
                return 0
            now = time.time()
            print(table([[r['who'], r['by'], 'LOCKED %d min' % max(1, int((r['until'] - now) // 60 + 1))
                          if r['locked'] else 'counting', '%d/%d' % (r['fails'], r['limit']),
                          when(r['first'])] for r in rows], ['who', 'by', 'state', 'wrong', 'since']))
            return 0
        if a.unlock:
            keys = None if a.unlock == 'all' else ['ip:' + a.unlock, 'name:' + a.unlock.lower()]
            n = lockouts_clear(st, keys, 'the command line')
            print(pal.ok_line('cleared: %d' % n) if n else pal.warn_line('nothing was counted for %s' % a.unlock))
            return 0
        if a.db_copy:
            print(pal.ok_line('made: %s' % make_backup(st, 'on the command line')))
            if a.dump:
                print(pal.ok_line('made: %s' % make_dump(st, 'by-hand')))
            return 0
        if a.db_copies:
            rows = [dict(r, kind='copy', folder=str(BACKUP_DIR)) for r in kept_copies()] + \
                [dict(r, folder=str(DUMP_DIR)) for r in kept_dumps(st.db.engine)]
            if a.json:
                say_json({'copies': rows})
            else:
                print(table([[r['name'], DUMP_WORDS.get(r['kind'], r['kind']), when(r['at']), human_bytes(r['bytes']),
                              'yes' if r.get('key') else 'NO'] for r in rows],
                            ['file', 'what', 'made', 'size', 'key beside']) if rows
                      else pal.warn_line('no copy yet (ai --db-copy)'))
                print(pal.dim('  in %s and %s' % (BACKUP_DIR, DUMP_DIR)))
            return 0
        if a.db_restore:
            path = a.db_restore
            if dbkey_is_bundle(path):
                raise Refused('that file is locked with its key: put it back on the pages (Settings - The database)')
            said, why = db_file_peek(path, st.db.engine, need_admin=False)
            if said is None:
                raise Refused(why)
            print('%s: %s, %s' % (os.path.basename(path), DUMP_WORDS.get(said['kind'], said['kind']),
                                  ', '.join('%s %d' % kv for kv in sorted((said.get('counts') or {}).items()))))
            if said.get('no_admin'):
                print(pal.warn_line('there is no administrator in it: make one afterwards (ai --add-user NAME --role admin)'))
            if not a.yes:
                raise Refused('everything here is replaced by it: add --yes')
            got = db_file_restore(st, path, 'the command line', key_file=_key_beside(path), from_name=path,
                                  need_admin=False)
            print(pal.ok_line('put back - what was here is in %s; %s' % (got['safety'], got['key'])))
            print(pal.dim('  the running daemon reads it at once; restart it to be sure: systemctl restart ai'))
            return 0
        if a.backups:
            page = rb_page(st)
            if a.json:
                say_json(page)
                return 0
            print(table([[t['name'], t['kind_words'], rbWhere_cli(t), 'on' if t.get('enabled') else 'off',
                          ('ok ' if (t.get('last') or {}).get('ok') else 'FAILED ') + when((t.get('last') or {}).get('at'))
                          if t.get('last') else '-'] for t in page['targets']],
                        ['destination', 'kind', 'where', 'state', 'last']) if page['targets']
                  else pal.warn_line('no destination yet (Settings → Backups)'))
            print('locked: %s · scheduled: %s' % ('yes' if page['locked'] else 'NO - set rbackup_password',
                                                  page['next'] or 'no'))
            for r in page['runs'][:10]:
                print('  %s  %s  %s' % (when(r['at']), 'ok    ' if r.get('ok') else 'FAILED',
                                        r.get('file') or r.get('error') or ''))
            return 0
        if a.backup_now:
            r = rb_run(st, 'the command line')
            for x in r['targets']:
                print((pal.ok_line if x['ok'] else pal.bad_line)('%s: %s' % (x['name'], 'sent' if x['ok'] else x.get('error'))))
            if r.get('error'):
                print(pal.bad_line(r['error']))
            return 0 if r['ok'] else 1
        if a.backup_file:
            if not rb_password():
                raise Refused('the backups have no password (ai --set rbackup_password=@env, AI_VALUE_RBACKUP_PASSWORD)')
            work = tempfile.mkdtemp(prefix='ai-bf-', dir=str(STATE_DIR))
            try:
                path, m, _md = rb_build(st, work)
                dst = a.backup_file if not os.path.isdir(a.backup_file) else os.path.join(a.backup_file, m['file'])
                shutil.move(path, dst)
                print(pal.ok_line('written: %s (%s)' % (dst, human_bytes(m['bytes']))))
            finally:
                shutil.rmtree(work, ignore_errors=True)
            return 0
        if a.restore_bundle:
            pw = os.environ.get('AI_BACKUP_PASSWORD') or (read_text(a.passphrase_file).splitlines() or [''])[0] \
                if a.passphrase_file else os.environ.get('AI_BACKUP_PASSWORD') or rb_password()
            with open(a.restore_bundle, 'rb') as f:
                locked = f.read(8).startswith(b'Salted__')
            if locked and not pw:
                pw = ask_password('the password of the backups', twice=False, env='AI_BACKUP_PASSWORD')
            work = tempfile.mkdtemp(prefix='ai-look-', dir=str(STATE_DIR))
            try:
                _top, m = rb_open(a.restore_bundle, pw if locked else '', work)
            finally:
                shutil.rmtree(work, ignore_errors=True)
            print('%s: made %s on %s by ai %s, %s account(s)' % (os.path.basename(a.restore_bundle), m.get('made_words'),
                                                                m.get('node'), m.get('ai'), m.get('accounts')))
            if not a.yes:
                raise Refused('everything here is replaced by it: add --yes')
            got = rb_restore(d, a.restore_bundle, pw if locked else '', 'the command line')
            print(pal.ok_line('put back - what was here is in %s' % got['safety']))
            print(pal.dim('  systemctl restart ai'))
            return 0
        if a.export_config:
            conf = config_export(st, a.with_secrets)
            out_ = conf
            if a.with_secrets:
                phrase = '-'.join(secrets.token_hex(3) for _ in range(4))
                out_ = dict(lock_with(phrase, conf), version=__version__, host=host_name())
            text = json.dumps(out_, indent=2, ensure_ascii=False)
            if a.export_config == '-':
                sys.stdout.write(text + '\n')
            else:
                write_atomic(a.export_config, text + '\n', mode=0o600)
                print(pal.ok_line('written: %s' % a.export_config))
            if a.with_secrets:
                print(pal.warn_line('the passphrase of the file (shown once): %s' % phrase), file=sys.stderr)
            return 0
        if a.import_config:
            try:
                conf = json.loads(read_text(a.import_config, most=64 << 20))
            except ValueError:
                raise Refused('%s is not JSON' % a.import_config)
            if isinstance(conf, dict) and conf.get('kind') == 'ai-config-locked':
                conf = open_with(ask_password('the passphrase of the file', twice=False, env='AI_PASSPHRASE'), conf)
            if not a.yes:
                raise Refused('the configuration in it is saved here%s: add --yes' % (
                    ', and what is not in it goes' if a.replace else ''))
            print(pal.ok_line(config_import(d, conf, 'the command line', a.replace, wait=True)))
            return 0
        if a.mail_test:
            to = mail_checked(a.mail_test)
            try:
                steps = mail_send(st, test_mail(to, mail_lang()), [to])
                ok = True
            except MailError as e:
                steps, ok = e.steps, False
                err = str(e)
            for s in steps:
                print((pal.ok_line if s.get('ok') else pal.bad_line)('%s%s' % (s['what'], (' - ' + s['said']) if s.get('said') else '')))
            print(pal.ok_line('sent to %s' % to) if ok else pal.bad_line('not sent: %s' % err))
            return 0 if ok else 1
        if a.end_sign_ins:
            n = st.x('DELETE FROM sessions WHERE name=?', (a.end_sign_ins,))
            print(pal.ok_line('%d sign-in(s) of %s ended' % (n, a.end_sign_ins)))
            return 0
        if a.sign_ins:
            rows = st.q('SELECT name, created, seen, ip, agent FROM sessions ORDER BY seen DESC')
            if a.json:
                say_json({'sessions': rows})
            else:
                print(table([[r['name'], r['ip'], when(r['created']), ago(r['seen']), (r['agent'] or '')[:40]]
                             for r in rows], ['who', 'from', 'since', 'last', 'browser']))
            return 0
        # ---- settings -------------------------------------------------------------------
        if a.settings:
            saved = st.settings_all()
            rows = [{'key': k, 'pane': pane, 'kind': kind, 'label': label, 'help': h, 'extra': extra,
                     'value': ('' if extra.get('secret') and CONFIG.get(k) else CONFIG.get(k)),
                     'secret': bool(extra.get('secret')), 'default': DEFAULTS.get(k),
                     'source': 'saved' if k in saved else 'default'}
                    for k, pane, kind, label, h, extra in SCHEMA]
            if a.json:
                say_json({'settings': rows})
            else:
                print(table([[r['key'], r['pane'], '(hidden)' if r['secret'] and CONFIG.get(r['key'])
                              else json.dumps(r['value']), r['source']] for r in rows],
                            ['key', 'pane', 'value', 'from']))
            return 0
        sets = list(a.set) + (['%s=%s' % tuple(a.setting)] if a.setting else [])
        if sets:
            for one in sets:
                k, sep, v = one.partition('=')
                if not sep or k not in SCHEMA_KEYS:
                    raise Refused('there is no setting %s (ai --settings)' % k)
                if v == '@env':
                    v = os.environ.get('AI_VALUE_' + k.upper(), '')
                if SCHEMA_KEYS[k][2] == 'bool':
                    v = v.lower() in ('1', 'true', 'on', 'yes', 'ano')
                nv = setting_value(k, v)
                if SCHEMA_KEYS[k][2] == 'password' and nv:
                    nv = seal_secret(nv, 'setting:' + k)
                st.set_setting(k, nv, 'the command line')
                print(pal.ok_line('%s = %s' % (k, '(hidden)' if SCHEMA_KEYS[k][5].get('secret') else json.dumps(v))))
            st.add_event('settings', 'the command line changed: %s' % ', '.join(s.split('=')[0] for s in sets), 'info')
            print(pal.dim('  the running daemon takes it within a minute'))
            return 0
        # ---- the firewall ---------------------------------------------------------------
        if a.fw:
            if a.fw == 'status':
                return cli_fw_status(d, pal, a.json)
            c = fw_conf(st)
            c['on'] = a.fw == 'on'
            return cli_fw_save(d, pal, c)
        if a.open_web:
            return cli_open_web(d, pal)
        if a.fw_open:
            port, _s, proto = a.fw_open.partition('/')
            c = fw_conf(st)
            c['rules'].append(dict(fw_rule_checked({'proto': proto or 'tcp', 'port': port, 'source': a.source,
                                                    'action': 'accept', 'note': a.note}), id=secrets.token_hex(4)))
            if not c['on']:
                print(pal.warn_line('ai\'s rules are off: the rule is kept, and in force once they are on (ai --fw on)'))
            return cli_fw_save(d, pal, c)
        if a.fw_del:
            c = fw_conf(st)
            if not 0 < a.fw_del <= len(c['rules']):
                raise Refused('there is no rule %d (ai --fw status)' % a.fw_del)
            c['rules'].pop(a.fw_del - 1)
            return cli_fw_save(d, pal, c)
        if a.pages_from:
            every = a.pages_from.strip().lower() == 'all'
            nets = [] if every else [x.strip() for x in a.pages_from.split(',') if x.strip()]
            return cli_fw_save(d, pal, access={'pages': {'any': every, 'from': nets}})
        if a.change_keep or a.change_back:
            return cli_trial(d, pal, a.change_keep or a.change_back, bool(a.change_keep))
        # ---- the server ---------------------------------------------------------------------
        if a.net:
            v = net_view(d, fresh=True)
            if a.json:
                say_json(v)
                return 0
            data = v['nodes'][0]['now']['data'] or {}
            conf, live = data.get('conf') or {}, data.get('live') or {}
            print('%s  %s' % (pal.head('the network'), 'NetworkManager' if data.get('nm') else 'by hand (no nmcli)'))
            print('  host name      %s' % data.get('hostname'))
            print('  connection     %s (%s)' % (data.get('con') or '-', data.get('dev') or '-'))
            print('  IPv4           %s' % (', '.join(conf.get('ipv4_addresses') or []) or
                                           ', '.join(x['addr'] for x in live.get('addrs4') or [])))
            print('  gateway        %s' % (conf.get('ipv4_gateway') or live.get('gw4') or '-'))
            print('  DNS            %s' % (', '.join(conf.get('ipv4_dns') or live.get('dns') or []) or '-'))
            print('  IPv6           %s' % (', '.join(x['addr'] for x in live.get('addrs6') or []) or 'off'))
            print(pal.dim('  changed on the pages: Settings - Network (it goes back by itself unless kept)'))
            return 0
        if a.ntp:
            v = ntp_view(d)
            if a.json:
                say_json(v)
                return 0
            data = v['nodes'][0]['now']['data']
            t = data.get('tracking') or {}
            print('%s  %s' % (pal.head('the time'), 'chrony' if data.get('chrony') else 'no chrony'))
            print('  time zone      %s' % (data.get('timezone') or '-'))
            print('  synchronised   %s' % (data.get('ntpsynchronized') or '-'))
            print('  follows        %s, stratum %s' % (t.get('ref') or t.get('ref_id') or '-', t.get('stratum', '-')))
            print('  off by         %s s' % t.get('offset', '-'))
            for s in data.get('sources') or []:
                print('    %s %-30s stratum %s' % (s.get('state'), s.get('name'), s.get('stratum')))
            return 0
        if a.osup:
            return cli_osup(d, a, pal)
        if a.sshkeys or a.sshkey_add:
            if a.sshkey_add:
                print(pal.ok_line(sshkeys_do(d, {'action': 'add', 'line': a.sshkey_add}, 'the command line')['message']))
            v = sshkeys_view(d, fresh=True)
            n = v['nodes'][0]
            if a.json:
                say_json(v)
                return 0
            print(table([[k.get('type'), k.get('fp'), k.get('comment') or '-'] for k in n['keys']],
                        ['kind', 'fingerprint', 'comment']))
            sd = n.get('sshd') or {}
            print('  root may sign in: %s, with a password: %s, port %s' % (
                sd.get('permit_root', '?'), sd.get('password', '?'), sd.get('port', '?')))
            return 0
        if a.tls_import or a.tls_preset or a.tls_dh or a.tls_hsts is not None:
            prof = tls_prof(st) or {'preset': 'standard', 'dh': 'none', 'hsts': 63072000}
            if a.tls_import:
                pem, pfx = '', b''
                for f in a.tls_import:
                    with open(f, 'rb') as fh:
                        raw = fh.read()
                    if b'-----BEGIN ' in raw:
                        pem += raw.decode('utf-8', 'replace') + '\n'
                    elif pfx:
                        raise Refused('one PFX / PKCS#12 file at a time')
                    else:
                        pfx = raw
                pend = unseal_secret(prof.get('pending_key'), 'web:tls-pending') if prof.get('pending_key') else ''
                try:
                    got = cert_bundle(cert=pem, pfx=pfx, password=os.environ.get('AI_TLS_PASSWORD') or '',
                                      pending_key=pend or '')
                except ValueError as e:
                    raise Refused(str(e))
                got['key'] = seal_secret(got['key'], 'web:tls')
                prof.update(got)
                prof.pop('pending_key', None)
                prof.pop('csr', None)
                print(pal.ok_line('the certificate of %s, %s' % (got['info'].get('cn') or '?',
                                                                 'its chain checked' if got.get('verify') == 'ok' else
                                                                 'no root given to check it against')))
            pol = {'preset': a.tls_preset or prof.get('preset') or 'standard', 'dh': a.tls_dh or prof.get('dh') or 'none',
                   'hsts': a.tls_hsts if a.tls_hsts is not None else prof.get('hsts'), 'prefer': prof.get('prefer'),
                   'protocols': prof.get('protocols'), 'ciphers': prof.get('ciphers')}
            try:
                prof.update(tls_policy_checked(pol))
            except ValueError as e:
                raise Refused(str(e))
            for line in tls_apply(st, prof, 'the command line'):
                print(pal.ok_line(line))
            return 0
        if a.cert:
            c = cert_facts()
            if a.json:
                say_json({'cert': c, 'tls': tls_view(tls_prof(st))})
                return 0
            prof = tls_prof(st)
            if prof:
                t = tls_resolved(prof)
                print('  %-14s %s' % ('TLS', '%s · %s · DH %s · HSTS %s' % (
                    ' '.join(t['protocols']), prof.get('preset') or 'standard', t['dh'],
                    ('%d s' % t['hsts']) if t['hsts'] else 'off')))
                if prof.get('pending_key'):
                    print(pal.warn_line('a certificate request waits for its certificate (ai --tls-import FILE)'))
            if not c.get('there'):
                print(pal.bad_line('there is no certificate at %s' % CERT_FILE))
                return 1
            for k in ('subject', 'issuer', 'from', 'until', 'sha256'):
                print('  %-14s %s' % (k, c.get(k, '-')))
            print('  %-14s %s' % ('names', ', '.join(c.get('names') or [])))
            return 0
        if a.reboot or a.poweroff:
            how = 'reboot' if a.reboot else 'poweroff'
            if not a.yes and input('%s the server now? every terminal ends [y/N] ' % (
                    'restart' if a.reboot else 'switch off')).strip().lower() not in ('y', 'yes', 'a', 'ano'):
                return 1
            power_ask(d, how, 'the command line')
            print(pal.ok_line('the server %s in 3 s' % ('restarts' if a.reboot else 'switches off')))
            return 0
        # ---- upgrades ---------------------------------------------------------------------------
        if a.downgrade_check:
            v = d.upgrades.view()
            if not (v.get('online') or {}).get('at'):
                v = (d.upgrades.look('the command line'), d.upgrades.view())[1]
            print('  here           ai %s · the oldest safe on this database: %s' % (__version__, v['floor']))
            if not v['older']:
                print(pal.ok_line('there is no older version at %s' % v.get('url')))
            for p_ in v['older']:
                print((pal.ok_line if p_['safe'] else pal.warn_line)('ai %s: %s' % (
                    p_['version'], 'may be gone back to (ai --downgrade %s)' % p_['version'] if p_['safe'] else p_['why'])))
            return 0
        if a.upgrade_follow:
            seen = 0
            while True:
                s = d.upgrades.status()
                log_ = read_text(UPGRADE_DIR / 'last.log', 400000)
                lines = log_.splitlines()
                for line in lines[seen:]:
                    print(line)
                seen = len(lines)
                if s.get('state') != 'running':
                    print((pal.ok_line if s.get('state') == 'done' else pal.warn_line)(
                        'the upgrade: %s %s' % (s.get('state') or 'nothing going on', s.get('version') or '')))
                    return 0 if s.get('state') in ('done', None, '') else 1
                time.sleep(1.5)
        if a.tidy:
            auth.tidy()
            keep = float(CONFIG.get('retain_events_days') or 180) * 86400
            n = st.x('DELETE FROM events WHERE at < ?', (time.time() - keep,))
            mailq_tick(st)
            print(pal.ok_line('tidied: %d event(s); the outgoing mail keeps %d day(s)' % (
                n, int(CONFIG.get('mail_keep_days') or 14))))
            return 0
        if a.upgrade_status:
            v = d.upgrades.view()
            if a.json:
                say_json(v)
                return 0
            s = v.get('status') or {}
            print('  here           ai %s' % __version__)
            print('  looked at      %s (%s)' % (v.get('url'), ago((v.get('online') or {}).get('at'))))
            print('  newer          %s' % (', '.join(p['version'] for p in v.get('newer') or []) or 'none'))
            print('  the last one   %s %s %s' % (s.get('version') or '-', s.get('state') or '-', when(s.get('at'))))
            if v.get('log'):
                print(pal.dim('\n' + '\n'.join(v['log'].strip().splitlines()[-20:])))
            return 0
        if a.upgrade_check or a.upgrade_online:
            row = d.upgrades.look('the command line')
            if a.json and a.upgrade_check:
                say_json(row)
                return 0
            if row.get('error'):
                raise SystemExit('ai: %s' % row['error'])
            for pk in row.get('packages') or []:
                print('  %s%s' % (pk['version'], '  <- newer' if ver_tuple(pk['version']) > ver_tuple(__version__) else ''))
            newest = row.get('newest') or {}
            if not a.upgrade_online:
                print('this is %s; the newest at %s is %s' % (__version__, row['url'], newest.get('version', '-')))
                return 0
            want = newest.get('version') if a.upgrade_online == 'newest' else a.upgrade_online
            if not want or ver_tuple(want) <= ver_tuple(__version__):
                print(pal.ok_line('nothing newer than %s to put in' % __version__))
                return 0
            if not a.yes and input('put ai %s in now? [y/N] ' % want).strip().lower() not in ('y', 'yes', 'a', 'ano'):
                return 1
            path, info = d.upgrades.fetch(want, 'the command line')
            print(pal.ok_line('ai %s, signed by %s - checked; putting it in' % (info['version'], info.get('signed_by'))))
            os.execvp(sys.executable, [sys.executable, '-I', upgrader(), '--run', str(path)])
        if a.downgrade:
            floor = downgrade_floor(st)
            if not a.yes and input('go back from ai %s to %s (the oldest safe here: %s)? [y/N] ' % (
                    __version__, a.downgrade, floor)).strip().lower() not in ('y', 'yes', 'a', 'ano'):
                return 1
            path, info = d.upgrades.fetch(a.downgrade, 'the command line', older=True)
            make_backup(st, 'before going back to %s, on the command line' % info['version'])
            print(pal.ok_line('ai %s, signed by %s - checked; going back to it' % (info['version'], info.get('signed_by'))))
            os.execvp(sys.executable, [sys.executable, '-I', upgrader(), '--run', str(path), '--floor', floor])
        # ---- looking ------------------------------------------------------------------------------
        if a.events:
            where, args = '', []
            if a.search:
                where = ' WHERE text LIKE ? OR who LIKE ? OR kind LIKE ?'
                args = ['%' + a.search + '%'] * 3
            rows = st.q('SELECT * FROM events%s ORDER BY id DESC LIMIT ?' % where, args + [a.limit])
            if a.json:
                say_json({'events': rows})
            else:
                for e in reversed(rows):
                    tone = {'warn': pal.warn, 'bad': pal.bad}.get(e['level'], lambda x: x)
                    print('%s %s %s' % (pal.dim(when(e['at'])), pal.info(('%-12s' % e['kind'])), tone(term_safe(e['text']))))
            return 0
        if a.log:
            text = read_text(LOG_FILE, most=1 << 22)
            for ln in text.splitlines()[-a.limit:]:
                print(term_safe(ln))
            return 0
        if a.check:
            return cli_check(d, pal, a.json)
        return cli_status(d, pal, a.json)
    except Refused as e:
        print(pal.bad_line(str(e)), file=sys.stderr)
        return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    config_rebuild()
    try:
        return cli_main(argv)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
