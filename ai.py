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
import fcntl
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
import shlex
import shutil
import signal
import socket
import sqlite3
import ssl
import stat
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

__version__ = '1.0.2'

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
    'term_lang': 'C.UTF-8',
    'default_run_as': 'root',
    'default_cwd': '',
    'chat_upload_dir': '.ai-uploads',
    'upload_most_mb': 4096,
    'events_keep_days': 180,
    'ended_keep_days': 14,
    'revert_s': 120,
    'debug': False,
}

# The settings the pages show, pane by pane. Everything else in DEFAULTS is
# set in /etc/ai/config.json or by its own page (the firewall, the network...).
SCHEMA = [
    # key, pane, kind, label, help, extra
    ('site_name', 'general', 'str', 'Name of this installation',
     'What the pages call this server, beside its host name. Empty: the host name alone.', {}),
    ('ui_lang', 'general', 'choice', 'Language of the pages',
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
    ('term_lang', 'claude', 'str', 'Language and characters of the terminals',
     'LANG of every terminal. A UTF-8 one is needed for Claude Code to draw itself.', {}),
    ('default_run_as', 'claude', 'str', 'Runs as, unless the account says otherwise',
     'The Linux account a terminal runs as for an account that has none of its own.', {}),
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
    ('session_idle_h', 'access', 'int', 'Signed out after (hours without a click)',
     'A sign-in nobody used for this long ends by itself. The terminals go on running.',
     {'min': 1, 'max': 720}),
    ('session_max_h', 'access', 'int', 'Signed out after at most (hours)',
     'However much it is used, a sign-in ends after this long.', {'min': 1, 'max': 8760}),
    ('login_max_fails', 'access', 'int', 'Wrong passwords before a pause',
     'From one address or for one name; then nobody signs in from there for the pause below.',
     {'min': 3, 'max': 100}),
    ('login_lock_min', 'access', 'int', 'The pause (minutes)', '', {'min': 1, 'max': 1440}),
    ('password_min', 'access', 'int', 'Shortest password', '', {'min': 8, 'max': 128}),
    ('revert_s', 'access', 'int', 'Changes that could cut you off go back after (seconds)',
     'A change of the network, the firewall or who may reach the pages is taken back by itself '
     'unless it is kept within this time - pressed Keep it, from the old address or the new.',
     {'min': 30, 'max': 3600}),
    ('events_keep_days', 'access', 'int', 'Events kept (days)', '', {'min': 7, 'max': 3650}),
    ('upgrade_url', 'upgrade', 'str', 'Where new versions are looked for',
     'A GitHub folder (https://github.com/OWNER/REPO/tree/BRANCH/FOLDER), a web page or a '
     'folder listing with ai-X.Y.Z.tar.gz links, or one package\'s address. HTTPS only.', {}),
    ('upgrade_check', 'upgrade', 'bool', 'Look once a day',
     'Whether there is a newer version - it is only said, unless the next switch is on too.', {}),
    ('upgrade_auto', 'upgrade', 'bool', 'Put a newer version in by itself',
     'Once a day, at the hour below: a newer signed version found there is fetched, checked and '
     'put in. The terminals go on running; the pages reconnect after a few seconds.', {}),
    ('upgrade_auto_hour', 'upgrade', 'int', 'At what hour', 'Local time of this server, 0-23.',
     {'min': 0, 'max': 23}),
    ('debug', 'general', 'bool', 'Debug log', 'Writes far more into /var/log/ai/ai.log.', {}),
]
SCHEMA_KEYS = {s[0]: s for s in SCHEMA}

CONFIG = dict(DEFAULTS)


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
                if k in DEFAULTS:
                    c[k] = v
        except sqlite3.Error:
            pass
    CONFIG.clear()
    CONFIG.update(c)
    return c


# ---------------------------------------------------------------------------
# The log this daemon writes about itself
# ---------------------------------------------------------------------------
LOG_LOCK = threading.Lock()
LOG_TO_FILE = [False]
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
# The database
# ---------------------------------------------------------------------------
SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS users (
    name TEXT PRIMARY KEY, pw TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
    run_as TEXT NOT NULL DEFAULT '', roots TEXT NOT NULL DEFAULT '[]',
    disabled INTEGER NOT NULL DEFAULT 0, must_change INTEGER NOT NULL DEFAULT 0,
    prefs TEXT NOT NULL DEFAULT '{}', note TEXT NOT NULL DEFAULT '',
    created REAL, last_login REAL, last_ip TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created REAL, seen REAL, ip TEXT, agent TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, kind TEXT, level TEXT, who TEXT, text TEXT
);
CREATE INDEX IF NOT EXISTS events_at ON events(at);
CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT, at REAL, by TEXT);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS terms (
    id TEXT PRIMARY KEY, owner TEXT, run_as TEXT, title TEXT, kind TEXT, cwd TEXT,
    opts TEXT NOT NULL DEFAULT '{}', created REAL, ended REAL, last_screen TEXT,
    exit_status INTEGER
);
CREATE TABLE IF NOT EXISTS fails (k TEXT PRIMARY KEY, n INTEGER, first REAL, until REAL);
'''


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=30,
                                  isolation_level=None)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=NORMAL')
            self.db.executescript(SCHEMA_SQL)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.q(sql, args)
        return rows[0] if rows else None

    def x(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            return cur.rowcount

    # -- meta and settings --------------------------------------------------
    def get_meta(self, k, default=None):
        r = self.one('SELECT v FROM meta WHERE k=?', (k,))
        return r['v'] if r else default

    def set_meta(self, k, v):
        self.x('INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v', (k, v))

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
        self.x('INSERT INTO settings(k,v,at,by) VALUES(?,?,?,?) ON CONFLICT(k) DO UPDATE SET '
               'v=excluded.v, at=excluded.at, by=excluded.by', (k, json.dumps(v), time.time(), by))

    def drop_setting(self, k):
        self.x('DELETE FROM settings WHERE k=?', (k,))

    # -- events -------------------------------------------------------------
    def add_event(self, kind, text, level='info', who=''):
        self.x('INSERT INTO events(at,kind,level,who,text) VALUES(?,?,?,?,?)',
               (time.time(), kind, level, who or '', str(text)[:2000]))
        log('%s: %s' % (kind, text), 'info' if level in ('info', 'good') else 'warn')

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
            if r and r['until'] and r['until'] > now:
                return int(r['until'] - now)
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
            self.store.x('INSERT INTO fails(k,n,first,until) VALUES(?,?,?,?) ON CONFLICT(k) DO '
                         'UPDATE SET n=excluded.n, first=excluded.first, until=excluded.until',
                         (k, n, first, until))

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
        token = secrets.token_urlsafe(32)
        self.store.x('INSERT INTO sessions(id,name,created,seen,ip,agent) VALUES(?,?,?,?,?,?)',
                     (self.sid(token), name, time.time(), time.time(), ip, clean_line(agent, 200)))
        self.store.x('UPDATE users SET last_login=?, last_ip=? WHERE name=?', (time.time(), ip, name))
        self.store.add_event('sign-in', '%s signed in from %s' % (name, ip), 'info', who=name)
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
        return u

    def logout(self, token):
        self.store.x('DELETE FROM sessions WHERE id=?', (self.sid(token),))

    def tidy(self):
        now = time.time()
        idle = float(CONFIG.get('session_idle_h') or 12) * 3600
        most = float(CONFIG.get('session_max_h') or 168) * 3600
        self.store.x('DELETE FROM sessions WHERE seen < ? OR created < ?', (now - idle, now - most))
        self.store.x('DELETE FROM fails WHERE (until = 0 OR until < ?) AND first < ?',
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

    def list(self, u, ended=True):
        live = self.live()
        self.sync(live)
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
        try:
            args += shlex.split(str(CONFIG.get('claude_args') or ''))
            args += shlex.split(str(opts.get('args') or ''))
        except ValueError as e:
            raise Refused('the words to start Claude Code with: %s' % e)
        q = ' '.join(shlex.quote(a) for a in args)
        exe = shlex.quote(cmd)
        return ('if ! command -v %s >/dev/null 2>&1; then '
                'printf "\\n  Claude Code (%s) is not installed for %%s on this server.\\n'
                '  Install it from Settings - Claude Code, or here:\\n'
                '    curl -fsSL https://claude.ai/install.sh | bash\\n\\n" "$(id -un)"; '
                'exec "${SHELL:-/bin/bash}" -l; fi; exec %s %s' % (exe, cmd.replace('"', ''), exe, q))

    def new(self, u, kind='claude', cwd='', title='', opts=None, cols=160, rows=48, run_as=None):
        opts = dict(opts or {})
        if kind not in ('claude', 'shell', 'command'):
            raise Refused('a terminal is claude, shell or command')
        if kind == 'command' and u['role'] != 'admin':
            raise Refused('only an administrator starts a command', 403)
        who_as = run_as if (run_as and u['role'] == 'admin') else run_as_of(u)
        pw = linux_user(who_as)
        cwd = str(cwd or CONFIG.get('default_cwd') or pw.pw_dir).strip()
        if cwd.startswith('~'):
            cwd = pw.pw_dir + cwd[1:]
        if not cwd.startswith('/'):
            cwd = os.path.join(pw.pw_dir, cwd)
        cwd = os.path.normpath(cwd)
        path_allowed(u, cwd)
        if not os.path.isdir(cwd):
            if opts.get('mkdir'):
                os.makedirs(cwd, exist_ok=True)
                if os.geteuid() == 0:
                    os.chown(cwd, pw.pw_uid, pw.pw_gid)
            else:
                raise Refused('%s is not a folder on this server' % cwd)
        tid = secrets.token_hex(4)
        name = 'ai-' + tid
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
        args = ['capture-pane', '-p', '-J', '-t', 'ai-' + r['id'], '-S', str(-int(lines))]
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
        pw = self.pw_of(r)
        rc, so, se = self.tmux(pw, ['respawn-pane', '-k', '-t', 'ai-' + r['id']])
        if rc != 0:
            raise Refused('tmux: %s' % (se or so).strip()[:200], 500)
        self.cache['at'] = 0
        self.store.add_event('terminals', '%s started the terminal "%s" again' % (u['name'], r['title']),
                             'info', who=u['name'])

    def again(self, u, r):
        """An ended terminal started afresh - the same kind, folder and choices."""
        try:
            opts = json.loads(r['opts'] or '{}')
        except ValueError:
            opts = {}
        if r['kind'] == 'claude' and not opts.get('resume'):
            opts['continue'] = True
        return self.new(u, r['kind'] or 'shell', r['cwd'], r['title'], opts,
                        run_as=r['run_as'] if u['role'] == 'admin' else None)

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

    def pump():
        try:
            while not done.is_set():
                try:
                    ready, _w, _x = select.select([master], [], [], 1.0)
                except (OSError, ValueError):
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


def files_op(u, body):
    op = str(body.get('op') or '')
    path = str(body.get('path') or '')
    if not path.startswith('/'):
        raise Refused('a full path, please')
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
    raise Refused('mkdir, rename, delete, read or write')


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
        st = self.status()
        hidden = self.store.get_meta('upgrade:hidden') == str(st.get('at'))
        return {'here': __version__, 'online': online, 'newer': newer, 'url': CONFIG.get('upgrade_url'),
                'check': bool(CONFIG.get('upgrade_check')), 'auto': bool(CONFIG.get('upgrade_auto')),
                'status': None if hidden else st, 'log': '' if hidden else read_text(UPGRADE_DIR / 'last.log', 400000),
                'keys': sorted(p.name for p in (LIB_DIR / 'release-keys').glob('*.pub'))
                if (LIB_DIR / 'release-keys').is_dir() else []}

    def fetch(self, version, by):
        pk = [p for p in online_list(CONFIG.get('upgrade_url')) if p['version'] == str(version)]
        if not pk:
            raise Refused('ai %s is not at %s' % (version, CONFIG.get('upgrade_url')))
        if ver_tuple(pk[0]['version']) <= ver_tuple(__version__):
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

    def take(self, path, by):
        info = upgrade_inspect(path)
        if info.get('older'):
            path = Path(path)
            raise Refused('%s is older than %s, which runs here: going back is done on the command line '
                          '(install.sh --upgrade of that version)' % (info['version'], __version__))
        return info

    def install(self, path, by):
        with self.lock:
            st = self.status()
            if st.get('state') == 'running':
                raise Refused('an upgrade is running already')
            if self.busy:
                raise Refused('an upgrade is being started already')
            self.busy = True
        try:
            info = self.take(path, by)
            write_atomic(UPGRADE_DIR / 'status.json', json.dumps({'state': 'running', 'version': info['version'],
                                                                  'by': by, 'at': time.time()}), mode=0o600)
            write_atomic(UPGRADE_DIR / 'last.log', '', mode=0o600)
            cmd = [sys.executable if os.path.exists(sys.executable) else '/usr/bin/python3', '-I', upgrader(),
                   '--job', str(path), '--by', by or 'the pages']
            self.store.add_event('upgrades', '%s is putting ai %s in (signed by %s)' % (
                by, info['version'], info.get('signed_by')), 'warn', who=by)
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
    u = c.daemon.store.user(str(c.body.get('name') or '').strip())
    return {'token': token, 'who': user_view(u)}


@route('POST', '/api/auth/logout')
def api_logout(c):
    c.daemon.auth.logout(c.token)
    return {}


@route('GET', '/api/auth/whoami')
def api_whoami(c):
    return {'who': user_view(c.who)}


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
        if k in ('lang', 'font', 'theme', 'favs', 'recent', 'files_hidden', 'rail', 'keys', 'paste'):
            if v is None:
                prefs.pop(k, None)
            else:
                prefs[k] = v
    text = json.dumps(prefs)
    if len(text) > 64000:
        raise Refused('too much to keep')
    c.daemon.store.x('UPDATE users SET prefs=? WHERE name=?', (text, c.name))
    return {'prefs': prefs}


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
    lines = max(5, min(2000, int(c.arg('lines', '40') or 40)))
    v['screen'] = tm.capture(r, lines) if v['state'] != 'ended' else (r.get('last_screen') or '')
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
        tm.restart(c.who, r)
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
    if kind == 'str':
        v = v.strip()
        if '\n' in v or len(v) > 2000:
            raise Refused('%s: one line' % s[3])
    if len(v) > 64000:
        raise Refused('%s: too long' % s[3])
    if k == 'upgrade_url' and v and not v.startswith('https://'):
        raise Refused('the address of new versions is https://')
    if k == 'default_run_as' and v:
        linux_user(v)
    return v


@route('GET', '/api/settings')
def api_settings(c):
    saved = c.daemon.store.settings_all()
    admin = c.who['role'] == 'admin'
    out = []
    for k, pane, kind, label, help_, extra in SCHEMA:
        v = CONFIG.get(k)
        if extra.get('secret') and not admin:
            v = '' if not v else '(set)'
        out.append({'key': k, 'pane': pane, 'kind': kind, 'label': label, 'help': help_, 'extra': extra,
                    'value': v, 'default': DEFAULTS.get(k), 'saved': k in saved})
    return {'settings': out}


@route('POST', '/api/settings', admin=True)
def api_settings_do(c):
    values = c.body.get('values') or {}
    if not isinstance(values, dict):
        raise Refused('values is an object')
    said = []
    for k, v in values.items():
        if k not in SCHEMA_KEYS:
            raise Refused('there is no setting %s' % k)
        if v is None:
            c.daemon.store.drop_setting(k)
            said.append('%s back to its default' % k)
            continue
        nv = setting_value(k, v)
        c.daemon.store.set_setting(k, nv, c.name)
        said.append('%s = %s' % (k, '(hidden)' if SCHEMA_KEYS[k][5].get('secret') else json.dumps(nv)[:80]))
    config_rebuild(c.daemon.store)
    CLAUDE_CACHE.clear()
    if said:
        c.daemon.store.add_event('settings', '%s changed: %s' % (c.name, '; '.join(said)), 'info', who=c.name)
    return {}


@route('GET', '/api/users', admin=True)
def api_users(c):
    d = c.daemon
    return {'users': [user_view(u) for u in d.store.users()],
            'sessions': d.store.q('SELECT id, name, created, seen, ip, agent FROM sessions ORDER BY seen DESC'),
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
    elif do == 'linux':
        linux_add(str(b.get('run_as') or ''), bool(b.get('sudo')))
        c.daemon.store.add_event('accounts', '%s made the Linux account %s' % (c.name, b.get('run_as')), 'warn',
                                 who=c.name)
    else:
        raise Refused('add, edit, drop, password, end or linux')
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
    return c.daemon.upgrades.view()


@route('POST', '/api/upgrade', admin=True)
def api_upgrade_do(c):
    up = c.daemon.upgrades
    do = c.body.get('do')
    if do == 'look':
        return {'online': up.look(c.name)}
    if do in ('fetch', 'install'):
        version = str(c.body.get('version') or '')
        path, info = up.fetch(version, c.name)
        if do == 'install':
            up.install(path, c.name)
        return {'info': info}
    if do == 'hide':
        c.daemon.store.set_meta('upgrade:hidden', str(up.status().get('at')))
        return {}
    raise Refused('look, fetch, install or hide')


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
            return self.answer(200, dict(files_list(who, arg('path') or self.home_of(who), arg('hidden', '1') == '1'),
                                         ok=True))
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
                info = d.upgrades.take(tmp, who['name'])
            except Refused:
                tmp.unlink()
                raise
            if arg('install') == '1':
                d.upgrades.install(tmp, who['name'])
            return self.answer(200, {'ok': True, 'info': info})
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
        self.store = Store(DB_FILE)
        config_rebuild(self.store)
        self.auth = Auth(self.store)
        self.terms = Terms(self.store)
        self.trials = Trials(self)
        self.upgrades = Upgrades(self)
        self.token = ''
        self.started = time.time()
        self.osup_checking = False
        self.stop = threading.Event()

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
                    keep = float(CONFIG.get('events_keep_days') or 180) * 86400
                    self.store.x('DELETE FROM events WHERE at < ?', (time.time() - keep,))
                    pass
                    if (STATE_DIR / 'first-login.txt').exists():
                        u = self.store.user('admin')
                        if not u or not u['must_change']:
                            (STATE_DIR / 'first-login.txt').unlink()
                if n % 20 == 2:
                    self.upgrades.tick()
            except Exception as e:                      # noqa: BLE001
                log_sparing('house', 'housekeeping: %s\n%s' % (e, traceback.format_exc()))

    def run(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_TO_FILE[0] = True
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(str(STATE_DIR), 0o711)
        self.write_token()
        self.first_account()
        port = int(CONFIG.get('api_port') or 9871)
        Handler.daemon = self
        srv = Server(('127.0.0.1', port), Handler)
        log('ai %s started: the API on 127.0.0.1:%d, the database %s' % (__version__, port, DB_FILE))
        self.store.add_event('starting and stopping', 'ai %s started on %s' % (__version__, host_name()), 'info')
        try:
            power_back(self)
        except Exception as e:                          # noqa: BLE001
            log('after a restart: %s' % e, 'warn')
        threading.Thread(target=self.housekeeping, name='ai-house', daemon=True).start()

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
# The command line
# ---------------------------------------------------------------------------
def cli_store():
    if not DB_FILE.exists() and os.geteuid() != 0:
        raise SystemExit('ai: %s is not there - run as root' % DB_FILE)
    st = Store(DB_FILE)
    config_rebuild(st)
    return st


def ago(ts):
    if not ts:
        return '-'
    s = int(time.time() - float(ts))
    for unit, n in (('d', 86400), ('h', 3600), ('min', 60)):
        if s >= n:
            return '%d %s ago' % (s // n, unit)
    return '%d s ago' % s


def cli_status(st):
    tm = Terms(st)
    admin = {'name': 'cli', 'role': 'admin'}
    terms = tm.list(admin)
    up = '?'
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/api/health' % int(CONFIG.get('api_port')), timeout=3):
            up = 'answering'
    except urllib.error.HTTPError:
        up = 'answering'
    except Exception:                                   # noqa: BLE001
        up = 'NOT answering'
    print('ai %s on %s - the daemon is %s' % (__version__, host_name(), up))
    print('  database   %s' % DB_FILE)
    print('  accounts   %s' % ', '.join('%s (%s%s)' % (u['name'], u['role'], ', off' if u['disabled'] else '')
                                        for u in st.users()))
    live = [t for t in terms if t['state'] != 'ended']
    print('  terminals  %d running' % len(live))
    for t in live:
        print('    %s  %-8s %-10s %-7s %s  (%s)' % (t['id'], t['run_as'], t['owner'] or '-', t['state'],
                                                    t['title'], t['path']))
    online = st.meta_json('upgrade:online', {}) or {}
    if online.get('newest'):
        print('  newest     %s at %s (%s)' % (online['newest']['version'], online.get('url'), ago(online.get('at'))))
    return 0


def cli_main(argv):
    p = argparse.ArgumentParser(prog='ai', description='Claude Code on this server, from the web pages.')
    p.add_argument('--daemon', action='store_true', help='run the daemon (systemd does)')
    p.add_argument('--status', action='store_true', help='what it is doing')
    p.add_argument('--version', action='store_true')
    p.add_argument('--sessions', action='store_true', help='the terminals, running and ended')
    p.add_argument('--attach', metavar='ID', help='one terminal, here (Ctrl+b d leaves it running)')
    p.add_argument('--new', metavar='DIR', help='a new Claude Code terminal in DIR (as --run-as)')
    p.add_argument('--users', action='store_true', help='the accounts of the pages')
    p.add_argument('--add-user', metavar='NAME', help='an account (--role, --run-as, --password)')
    p.add_argument('--role', default='user', choices=ROLES)
    p.add_argument('--run-as', default='', help='the Linux account its terminals run as')
    p.add_argument('--password', default='', help='its password (otherwise asked, or made with --make-password)')
    p.add_argument('--make-password', action='store_true', help='make a password and print it')
    p.add_argument('--passwd', metavar='NAME', help='a new password for an account')
    p.add_argument('--drop-user', metavar='NAME')
    p.add_argument('--events', action='store_true', help='the last events')
    p.add_argument('--upgrade-check', action='store_true', help='whether a newer version is out')
    p.add_argument('--upgrade-online', nargs='?', const='newest', metavar='VERSION',
                   help='fetch the newest (or VERSION) from upgrade_url and put it in')
    p.add_argument('--setting', nargs=2, metavar=('KEY', 'VALUE'), help='change a setting')
    p.add_argument('--settings', action='store_true', help='every setting and its value')
    p.add_argument('--yes', action='store_true')
    a = p.parse_args(argv)
    if a.version:
        print('ai %s' % __version__)
        return 0
    if a.daemon:
        Daemon().run()
        return 0
    st = cli_store()
    if a.sessions:
        for t in Terms(st).list({'name': 'cli', 'role': 'admin'}):
            print('%s  %-8s %-10s %-8s %-40s %s' % (t['id'], t['run_as'], t['owner'] or '-', t['state'],
                                                     t['title'][:40], t['path']))
        return 0
    if a.attach:
        r = Terms(st).row(a.attach)
        pw = linux_user(r['run_as'])
        sock = str(TMUX_DIR / pw.pw_name / 'sock')
        cmd = [tmux_bin(), '-u', '-S', sock, 'attach-session', '-t', 'ai-' + r['id']]
        if os.geteuid() == 0 and pw.pw_uid != 0:
            cmd = ['runuser', '-u', pw.pw_name, '--'] + cmd
        os.execvp(cmd[0], cmd)
    if a.new:
        u = {'name': 'cli', 'role': 'admin', 'run_as': a.run_as or '', 'roots': '[]'}
        tid = Terms(st).new(u, 'claude', a.new, '', {}, run_as=a.run_as or run_as_of(u))
        print('started %s - ai --attach %s' % (tid, tid))
        return 0
    if a.users:
        for u in st.users():
            v = user_view(u)
            print('%-20s %-6s runs as %-10s %s%s' % (v['name'], v['role'], v['run_as'],
                                                    'off ' if v['disabled'] else '', ago(v['last_login'])))
        return 0
    auth = Auth(st)
    if a.add_user or a.passwd:
        name = a.add_user or a.passwd
        pw_ = a.password or (new_password() if a.make_password else '')
        if not pw_:
            pw_ = getpass.getpass('a password for %s: ' % name)
            if getpass.getpass('and again: ') != pw_:
                raise SystemExit('ai: the two were not the same')
        try:
            if a.add_user:
                auth.add_user(name, pw_, a.role, a.run_as, must_change=a.make_password, by='the command line')
            else:
                auth.set_password(name, pw_, 'the command line', must_change=a.make_password)
                st.x('DELETE FROM sessions WHERE name=?', (name,))
        except Refused as e:
            raise SystemExit('ai: %s' % e)
        print('%s: done%s' % (name, ' - password: %s' % pw_ if a.make_password else ''))
        return 0
    if a.drop_user:
        try:
            auth.drop_user(a.drop_user, 'the command line')
        except Refused as e:
            raise SystemExit('ai: %s' % e)
        return 0
    if a.events:
        for e in reversed(st.q('SELECT * FROM events ORDER BY id DESC LIMIT 40')):
            print('%s %-6s %-12s %s' % (time.strftime('%d-%m-%Y %H:%M', time.localtime(e['at'])), e['level'],
                                        e['kind'], e['text']))
        return 0
    if a.settings:
        for k, pane, kind, label, _h, extra in SCHEMA:
            v = CONFIG.get(k)
            print('%-20s %-8s %s' % (k, pane, '(hidden)' if extra.get('secret') and v else json.dumps(v)))
        return 0
    if a.setting:
        k, v = a.setting
        if k not in SCHEMA_KEYS:
            raise SystemExit('ai: there is no setting %s (ai --settings)' % k)
        try:
            st.set_setting(k, setting_value(k, v if SCHEMA_KEYS[k][2] != 'bool' else v in ('1', 'true', 'on', 'yes')),
                           'the command line')
        except Refused as e:
            raise SystemExit('ai: %s' % e)
        print('%s = %s (the daemon takes it within a minute, or: systemctl reload ai)' % (k, v))
        return 0
    if a.upgrade_check or a.upgrade_online:
        class D:
            pass
        d = D()
        d.store = st
        up = Upgrades(d)
        row = up.look('the command line')
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
            print('nothing newer than %s to put in' % __version__)
            return 0
        if not a.yes and input('put ai %s in now? [y/N] ' % want).strip().lower() not in ('y', 'yes'):
            return 1
        path, info = up.fetch(want, 'the command line')
        print('ai %s, signed by %s - checked; putting it in' % (info['version'], info.get('signed_by')))
        os.execvp(sys.executable, [sys.executable, '-I', upgrader(), '--run', str(path)])
    return cli_status(st)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    config_rebuild()
    try:
        return cli_main(argv)
    except Refused as e:
        print('ai: %s' % e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
