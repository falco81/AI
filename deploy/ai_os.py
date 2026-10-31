#!/usr/bin/python3 -I
"""ai_os.py - the machine's own parts of ai, done as root: the clock (chrony),
root's SSH keys and the updates of the system.

Taken from otp's root helper (otp_web.py 1.0.159), function for function:
the same checks, the same files, the same words. ai runs as root, so the
daemon imports this and calls it; only the update of the system runs apart,
in a systemd unit of its own, so that it outlives the daemon (an update of
Python under it included):

  ai_os.py --os-job ID check|upgrade   the system's updates (started by ai)
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import ipaddress

STATE_DIR = os.environ.get('AI_STATE', '/var/lib/ai')
NO_SERVICES = bool(os.environ.get('AI_NO_SYSTEM'))
NAME_RE = re.compile(r'^(?=.{1,253}\Z)([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)'
                     r'(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\Z')
ADDR_RE = re.compile(r'^[0-9A-Fa-f:.]+(/[0-9]{1,3})?\Z')


class Refused(Exception):
    pass


def plain(text, how):
    text = str(text or '').strip()
    if not ADDR_RE.match(text):
        raise ValueError('not a plain address')
    got = {'address': ipaddress.ip_address, 'network': lambda t: ipaddress.ip_network(t, strict=False),
           'interface': ipaddress.ip_interface}[how](text)
    if '%' in str(got):
        raise ValueError('a scope id is not taken')
    return got


def run(cmd, what, ok=(0,)):
    try:
        got = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        raise Refused('%s is not on this machine' % cmd[0])
    if got.returncode not in ok:
        raise Refused('%s: %s' % (what, (got.stderr or got.stdout).strip()[-300:]))
    return got.stdout


def write_root(path, text, mode):
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.ai-', dir=folder)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_here(name, text):
    write_root(os.path.join(STATE_DIR, name), text, 0o600)


# ---- the clock: chrony ------------------------------------------------------------------
CHRONYC = os.environ.get('AI_CHRONYC', 'chronyc')
TIMEDATECTL = os.environ.get('AI_TIMEDATECTL', 'timedatectl')
# Debian and Ubuntu read /etc/chrony/chrony.conf (1.0.146): the other was
# written there and never read, and "applied" said so.
CHRONY_CONF = os.environ.get('AI_CHRONY_CONF') or next(
    (p for p in ('/etc/chrony.conf', '/etc/chrony/chrony.conf') if os.path.isfile(p)),
    '/etc/chrony.conf')
NTP_BEGIN = '# ---- ai: the time servers, set on its pages (Settings - Time) ----'
NTP_END = '# ---- ai: end ----'
NTP_KEYS = ('server', 'pool', 'peer', 'makestep', 'allow', 'minsources', 'maxdistance', 'sourcedir')
TZ_RE = re.compile(r'^[A-Za-z0-9_+-]{1,40}(/[A-Za-z0-9_+-]{1,40}){0,3}\Z')


def ntp_read():
    out = {'chrony': bool(shutil.which(CHRONYC)), 'tracking': {}, 'sources': [], 'stats': {}}
    try:
        t = run([TIMEDATECTL, 'show'], 'timedatectl', ok=(0, 1))
        for line in t.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                if k in ('Timezone', 'NTP', 'NTPSynchronized', 'LocalRTC', 'CanNTP'):
                    out[k.lower()] = v
    except (Refused, OSError):
        pass
    out['time'] = time.time()
    if not out['chrony']:
        return out
    try:
        f = run([CHRONYC, '-c', 'tracking'], 'chronyc tracking').strip().split(',')
        if len(f) >= 14:
            out['tracking'] = {'ref_id': f[0], 'ref': f[1], 'stratum': int(f[2] or 0),
                               'ref_time': float(f[3] or 0), 'offset': float(f[4] or 0),
                               'last_offset': float(f[5] or 0), 'rms': float(f[6] or 0),
                               'freq': float(f[7] or 0), 'skew': float(f[9] or 0),
                               'root_delay': float(f[10] or 0), 'root_disp': float(f[11] or 0),
                               'interval': float(f[12] or 0), 'leap': f[13]}
    except (Refused, ValueError, OSError) as e:
        out['said'] = str(e)[:200]
    try:
        for line in run([CHRONYC, '-c', 'sources'], 'chronyc sources').splitlines():
            f = line.split(',')
            if len(f) < 10:
                continue
            try:
                out['sources'].append({'mode': f[0], 'state': f[1], 'name': f[2][:120],
                                       'stratum': int(f[3] or 0), 'poll': int(f[4] or 0),
                                       'reach': int(f[5] or 0, 8) if f[5] else 0,
                                       'last_rx': int(f[6]) if f[6].lstrip('-').isdigit() else None,
                                       'offset': float(f[7] or 0), 'measured': float(f[8] or 0),
                                       'error': float(f[9] or 0)})
            except ValueError:
                continue
    except (Refused, OSError):
        pass
    try:
        with open(CHRONY_CONF) as f:
            text = f.read()
        out['managed'] = NTP_BEGIN in text
        out['own'] = [l.strip() for l in text.splitlines()
                      if l.strip().split(' ')[0] in ('server', 'pool', 'peer')][:20]
    except OSError:
        out['managed'] = False
    return out


def ntp_checked(r):
    out = {'manage': bool(r.get('manage')), 'servers': [], 'allow': [],
           'makestep': [1.0, 3], 'minsources': 1, 'timezone': '', 'peers': []}
    for x in (r.get('servers') or [])[:12]:
        if not isinstance(x, dict):
            raise Refused('a server is an object')
        host = str(x.get('host') or '').strip().lower().rstrip('.')
        try:
            host = str(plain(host, 'address'))
        except ValueError:
            if not NAME_RE.match(host):
                raise Refused('%r is not a host name or an address' % host[:80])
        out['servers'].append({'host': host, 'pool': bool(x.get('pool')),
                               'iburst': bool(x.get('iburst', True)),
                               'prefer': bool(x.get('prefer')), 'nts': bool(x.get('nts'))})
    for p in (r.get('peers') or [])[:2]:
        try:
            out['peers'].append(str(plain(p, 'address')))
        except ValueError:
            raise Refused('%r is not the other node\'s address' % str(p)[:60])
    for a in (r.get('allow') or [])[:20]:
        try:
            out['allow'].append(str(plain(a, 'network')))
        except ValueError:
            raise Refused('%r is not a network (192.0.2.0/24)' % str(a)[:60])
    try:
        th = float((r.get('makestep') or [1.0, 3])[0])
        lim = int((r.get('makestep') or [1.0, 3])[1])
    except (TypeError, ValueError, IndexError):
        raise Refused('makestep is a threshold in seconds and a number of updates')
    if not (0.001 <= th <= 3600) or not (-1 <= lim <= 1000):
        raise Refused('makestep: 0.001 - 3600 s, and -1 (always) to 1000 updates')
    out['makestep'] = [th, lim]
    try:
        out['minsources'] = max(1, min(10, int(r.get('minsources') or 1)))
    except (TypeError, ValueError):
        out['minsources'] = 1
    tz = str(r.get('timezone') or '').strip()
    if tz and not TZ_RE.match(tz):
        raise Refused('%r is not a time zone' % tz[:60])
    out['timezone'] = tz
    if out['manage'] and not out['servers'] and not out['peers']:
        raise Refused('at least one time server')
    return out


def ntp_conf_text(text, n):
    """chrony.conf with ai's block (or without it, put back as it was)."""
    lines = text.splitlines()
    out, inside = [], False
    for l in lines:
        if l.strip() == NTP_BEGIN:
            inside = True
            continue
        if l.strip() == NTP_END:
            inside = False
            continue
        if inside:
            continue
        if l.startswith('#ai# '):
            l = l[5:]                       # the file's own line, put back first
        out.append(l)
    if not n['manage']:
        return '\n'.join(out).rstrip('\n') + '\n'
    kept = []
    for l in out:
        if l.strip().split(' ')[0] in NTP_KEYS:
            kept.append('#ai# ' + l)
        else:
            kept.append(l)
    block = [NTP_BEGIN]
    for x in n['servers']:
        opts = [o for o, on in (('iburst', x['iburst']), ('prefer', x['prefer']),
                                ('nts', x['nts'])) if on]
        block.append('%s %s %s' % ('pool' if x['pool'] else 'server', x['host'], ' '.join(opts)))
    for p in n['peers']:
        # The other node of the cluster: one more source, and allowed to ask.
        block.append('server %s iburst' % p)
        block.append('allow %s' % p)
    for a in n['allow']:
        block.append('allow %s' % a)
    block.append('makestep %s %d' % (('%g' % n['makestep'][0]), n['makestep'][1]))
    if n['minsources'] > 1:
        block.append('minsources %d' % n['minsources'])
    block.append(NTP_END)
    return '\n'.join([l.rstrip() for l in kept]).rstrip('\n') + '\n\n' + '\n'.join(block) + '\n'


def ntp_apply(n):
    said = []
    if not shutil.which(CHRONYC) and not NO_SERVICES:
        if shutil.which('dnf'):
            run(['dnf', '-y', 'install', 'chrony'], 'dnf install chrony')
            said.append('chrony installed')
        else:
            raise Refused('chrony is not on this machine')
    try:
        with open(CHRONY_CONF) as f:
            had = f.read()
    except FileNotFoundError:
        had = 'driftfile /var/lib/chrony/drift\nrtcsync\nlogdir /var/log/chrony\n'
    new = ntp_conf_text(had, n)
    if new != had:
        if NTP_BEGIN not in had:
            try:
                write_root(CHRONY_CONF + '.ai-before', had, 0o644)
            except OSError:
                pass
        write_root(CHRONY_CONF, new, 0o644)
        said.append('%s: %s' % (CHRONY_CONF, ', '.join(x['host'] for x in n['servers'])
                                if n['manage'] else 'its own servers again'))
        if not NO_SERVICES and not os.environ.get('AI_NTP_NO_SERVICE'):
            run(['systemctl', 'enable', '--now', 'chronyd'], 'systemctl enable chronyd')
            run(['systemctl', 'restart', 'chronyd'], 'systemctl restart chronyd')
            said.append('chronyd restarted')
    if n['timezone']:
        try:
            cur = run([TIMEDATECTL, 'show', '-p', 'Timezone', '--value'], 'timedatectl').strip()
        except Refused:
            cur = ''
        if cur != n['timezone']:
            run([TIMEDATECTL, 'set-timezone', n['timezone']], 'timedatectl set-timezone')
            said.append('time zone: %s' % n['timezone'])
    if not NO_SERVICES and shutil.which(TIMEDATECTL) and not os.environ.get('AI_NTP_NO_SERVICE'):
        run([TIMEDATECTL, 'set-ntp', 'true'], 'timedatectl set-ntp', ok=(0, 1))
    return {'said': said}




def ntp_sync():
    said = run([CHRONYC, 'makestep'], 'chronyc makestep').strip()
    run([CHRONYC, 'burst', '4/4'], 'chronyc burst', ok=(0, 1))
    return {'said': [said or 'stepped']}


def zones():
    try:
        return run([TIMEDATECTL, 'list-timezones'], 'timedatectl').split()[:700]
    except Refused:
        return []


# ---- the network, as NetworkManager has it -------------------------------------------
def nm_fields(con, fields):
    out = run(['nmcli', '-t', '-g', ','.join(fields), 'connection', 'show', con],
              'nmcli connection show')
    vals = out.rstrip('\n').split('\n')
    got = {}
    for k, v in zip(fields, vals + [''] * (len(fields) - len(vals))):
        got[k] = v.replace('\\:', ':').strip()
    return got


def nm_list(text):
    return [x.strip() for x in re.split(r'[,\s]+', text or '') if x.strip() and x.strip() != '--']


def net_read():
    out = {'nm': bool(shutil.which('nmcli')), 'devices': [], 'con': '', 'dev': '', 'conf': {},
           'live': {'addrs4': [], 'addrs6': [], 'gw4': '', 'gw6': '', 'dns': []}}
    try:
        with open('/proc/sys/net/ipv6/conf/all/disable_ipv6') as f:
            out['ipv6_kernel'] = f.read().strip() == '0'
    except OSError:
        out['ipv6_kernel'] = False
    try:
        for line in run(['ip', '-o', 'addr', 'show'], 'ip addr').splitlines():
            f = line.split()
            if len(f) < 4 or f[1] == 'lo':
                continue
            try:
                ifc = ipaddress.ip_interface(f[3])
            except ValueError:
                continue
            if ifc.ip.is_loopback or ifc.ip.is_link_local:
                continue
            (out['live']['addrs4'] if ifc.version == 4 else out['live']['addrs6']).append(
                {'addr': str(ifc), 'dev': f[1].split('@')[0]})
        for fam, key in (('-4', 'gw4'), ('-6', 'gw6')):
            r = run(['ip', fam, 'route', 'show', 'default'], 'ip route', ok=(0, 1, 2))
            m = re.search(r'default via (\S+) dev (\S+)', r)
            if m:
                out['live'][key] = m.group(1)
                if key == 'gw4':
                    out['dev'] = m.group(2)
    except Refused:
        pass
    try:
        with open('/etc/resolv.conf') as f:
            out['live']['dns'] = [l.split()[1] for l in f if l.startswith('nameserver ')
                                  and len(l.split()) > 1][:6]
    except OSError:
        pass
    try:
        out['hostname'] = run(['hostnamectl', '--static'], 'hostnamectl').strip() or \
            os.uname().nodename
    except (Refused, OSError):
        out['hostname'] = os.uname().nodename
    if not out['nm']:
        return out
    try:
        for line in run(['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device'],
                        'nmcli device').splitlines():
            f = line.replace('\\:', '\x00').split(':')
            f = [x.replace('\x00', ':') for x in f]
            if len(f) >= 4 and f[1] in ('ethernet', 'bond', 'vlan', 'bridge', 'team', 'wifi'):
                out['devices'].append({'dev': f[0], 'type': f[1], 'state': f[2], 'con': f[3]})
    except Refused as e:
        out['nm_said'] = str(e)
    dev = out['dev'] or next((d['dev'] for d in out['devices'] if d['con']), '')
    con = next((d['con'] for d in out['devices'] if d['dev'] == dev and d['con']), '')
    out['dev'], out['con'] = dev, con
    if con:
        try:
            g = nm_fields(con, ['ipv4.method', 'ipv4.addresses', 'ipv4.gateway', 'ipv4.dns',
                                'ipv4.dns-search', 'ipv6.method', 'ipv6.addresses',
                                'ipv6.gateway', 'ipv6.dns'])
            out['conf'] = {'ipv4_method': g['ipv4.method'],
                           'ipv4_addresses': nm_list(g['ipv4.addresses']),
                           'ipv4_gateway': g['ipv4.gateway'] if g['ipv4.gateway'] != '--' else '',
                           'ipv4_dns': nm_list(g['ipv4.dns']),
                           'ipv4_search': nm_list(g['ipv4.dns-search']),
                           'ipv6_method': g['ipv6.method'],
                           'ipv6_addresses': nm_list(g['ipv6.addresses']),
                           'ipv6_gateway': g['ipv6.gateway'] if g['ipv6.gateway'] != '--' else '',
                           'ipv6_dns': nm_list(g['ipv6.dns'])}
        except Refused as e:
            out['nm_said'] = str(e)
    return out



# ---- root's SSH keys ------------------------------------------------------------------------
ROOT_AUTH = os.environ.get('AI_ROOT_AUTHKEYS', '/root/.ssh/authorized_keys')
KEY_TYPES = ('ssh-ed25519', 'ecdsa-sha2-nistp256', 'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521',
             'ssh-rsa', 'sk-ssh-ed25519@openssh.com', 'sk-ecdsa-sha2-nistp256@openssh.com')
KEY_LINE_RE = re.compile(r'^(?P<type>[a-z0-9@.-]+) (?P<blob>[A-Za-z0-9+/]{40,16000}={0,3})'
                         r'(?: (?P<comment>[^\x00-\x1f\x7f]{0,200}))?\Z')


def key_facts(line):
    """(bits, SHA256:..., type) of one public key line, read by ssh-keygen."""
    got = subprocess.run(['ssh-keygen', '-l', '-E', 'sha256', '-f', '-'], input=line + '\n',
                         capture_output=True, text=True, timeout=20)
    m = re.match(r'^(\d+) (SHA256:[A-Za-z0-9+/=]+) .*\((\w+)\)\s*$', got.stdout.strip())
    if got.returncode != 0 or not m:
        return None
    return int(m.group(1)), m.group(2), m.group(3)


def auth_lines():
    """The lines of root's authorized_keys - none where it is not there. Never
    through a link."""
    try:
        fd = os.open(ROOT_AUTH, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return []
    except OSError as e:
        raise Refused('%s cannot be read: %s' % (ROOT_AUTH, e))
    with os.fdopen(fd, 'r', encoding='utf-8', errors='replace') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise Refused('%s is not a plain file' % ROOT_AUTH)
        return f.read(1 << 20).split('\n')


def auth_keys(lines):
    out = []
    for i, ln in enumerate(lines):
        t = ln.strip()
        if not t or t.startswith('#'):
            continue
        facts = key_facts(t)
        m = KEY_LINE_RE.match(t)
        out.append({'line': i, 'fp': facts[1] if facts else '', 'bits': facts[0] if facts else 0,
                    'type': facts[2] if facts else '?',
                    'comment': (m.group('comment') or '') if m else '',
                    'options': not bool(m), 'readable': bool(facts),
                    # The line itself, for the page's export: public halves only.
                    'text': t[:16500]})
    return out


def auth_write(lines):
    """root's authorized_keys written whole: its folder made 0700 if it is not
    there, refused if it is a link; a new file of root's, 0600, renamed in."""
    folder = os.path.dirname(ROOT_AUTH)
    try:
        st = os.lstat(folder)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
            raise Refused('%s is not a plain folder' % folder)
    except FileNotFoundError:
        os.makedirs(folder, mode=0o700)
    try:
        if stat.S_ISLNK(os.lstat(ROOT_AUTH).st_mode):
            raise Refused('%s is a link - put the file itself there' % ROOT_AUTH)
    except FileNotFoundError:
        pass
    text = '\n'.join(lines).rstrip('\n') + '\n'
    fd, tmp = tempfile.mkstemp(prefix='.authorized_keys.', dir=folder)
    try:
        os.fchmod(fd, 0o600)
        if os.geteuid() == 0:
            os.fchown(fd, 0, 0)
        with os.fdopen(fd, 'w') as f:
            fd = None
            f.write(text)
        os.replace(tmp, ROOT_AUTH)
    except BaseException:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    if shutil.which('restorecon') and not NO_SERVICES:
        subprocess.run(['restorecon', '-R', folder], capture_output=True)


def sshd_says():
    """What sshd makes of root and of keys: a key is no use where it does not
    let root in with one."""
    if not shutil.which('sshd'):
        return {'there': False}
    got = subprocess.run(['sshd', '-T'], capture_output=True, text=True, timeout=20)
    said = {}
    for ln in got.stdout.splitlines():
        k, _, v = ln.partition(' ')
        if k in ('permitrootlogin', 'pubkeyauthentication', 'passwordauthentication', 'port'):
            said[k] = v.strip()
    return {'there': True, 'permit_root': said.get('permitrootlogin', ''),
            'pubkey': said.get('pubkeyauthentication', ''),
            'password': said.get('passwordauthentication', ''), 'port': said.get('port', '')}


def sshkeys_do(r):
    do = r.get('do')
    lines = auth_lines()
    if do == 'add':
        line = str(r.get('line') or '').strip()
        m = KEY_LINE_RE.match(line)
        if not m or m.group('type') not in KEY_TYPES:
            raise Refused('that is not one public key line (ssh-ed25519 AAAA... comment) - '
                          'options before the key are not taken here')
        facts = key_facts(line)
        if not facts:
            raise Refused('ssh-keygen does not read that key')
        bits, fp, kind = facts
        if kind == 'RSA' and bits < 3072:
            raise Refused('an RSA key of %d bits is too weak: 3072 at least, or ed25519' % bits)
        if kind == 'DSA':
            raise Refused('DSA keys are not taken')
        # There already is no fault: a key of root's the app was handed, or
        # one put on again (1.0.159).
        if not any(k['fp'] == fp for k in auth_keys(lines)):
            lines = [ln for ln in lines if ln.strip()] + [line]
            auth_write(lines)
    elif do == 'drop':
        fp = str(r.get('fp') or '')
        keys = auth_keys(lines)
        hit = [k for k in keys if k['fp'] and k['fp'] == fp]
        if not hit:
            raise Refused('no key %s is there' % fp)
        if len(keys) == len(hit) and not r.get('last_ok'):
            raise Refused('that is the last key root signs in with here - said again to take it '
                          'away anyway')
        gone = {k['line'] for k in hit}
        auth_write([ln for i, ln in enumerate(lines) if i not in gone])
    elif do != 'list':
        raise Refused('list, add or drop')
    lines = auth_lines()
    return {'keys': [dict((k, v) for k, v in x.items() if k != 'line') for x in auth_keys(lines)],
            'file': ROOT_AUTH, 'sshd': sshd_says()}



# ---- the updates of the system ----------------------------------------------------------------
OSUP_FILE = 'osup.json'
OSUP_LOCK = os.environ.get('AI_OSUP_LOCK', '/run/ai-osup.lock')
OSUP_PM = os.environ.get('AI_OSUP_PM', '')          # tests: a fake package manager


def osup_pm():
    if OSUP_PM:
        return 'fake'
    if shutil.which('dnf'):
        return 'dnf'
    if shutil.which('apt-get'):
        return 'apt'
    return ''


# The proxy dnf and apt go through (1.0.47, as otp's): handed over by the
# daemon before the job starts, kept here for it, readable by root only,
# never on a command line.
OSUP_PROXY = os.environ.get('AI_OSUP_PROXY', '/run/ai-osup-proxy.json')


def osup_proxy_keep(url='', no=''):
    url = str(url or '').strip()
    if url and not re.match(r'^https?://[^\s]+\Z', url):
        raise Refused('the proxy is not an http:// address')
    no = ','.join(w for w in re.split(r'[\s,;]+', re.sub(r'[^A-Za-z0-9.*:/\[\],;\s_-]', '', str(no or ''))) if w)
    if not url:
        try:
            os.unlink(OSUP_PROXY)
        except OSError:
            pass
        return
    fd = os.open(OSUP_PROXY + '.new', os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(json.dumps({'url': url, 'no': no}))
    os.replace(OSUP_PROXY + '.new', OSUP_PROXY)


def osup_proxy_env(env):
    try:
        with open(OSUP_PROXY) as f:
            got = json.loads(f.read() or '{}')
    except (OSError, ValueError):
        got = {}
    if got.get('url'):
        for k in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY'):
            env[k] = got['url']
        if got.get('no'):
            env['no_proxy'] = env['NO_PROXY'] = got['no']
    return env


def osup_running():
    import fcntl
    try:
        fd = os.open(OSUP_LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)


def osup_launch(ident, kind, security=False):
    if osup_running():
        raise Refused('an update or a look for updates is going on already')
    if not osup_pm():
        raise Refused('neither dnf nor apt-get is on this machine')
    me = os.path.abspath(__file__)
    argv = [sys.executable, '-I', me, '--os-job', ident, kind] + (['security'] if security else [])
    if (shutil.which('systemd-run') and not NO_SERVICES and os.path.isdir('/run/systemd/system')):
        got = subprocess.run(['systemd-run', '--unit', 'ai-os-%s-%s' % (kind, ident[:12]),
                              '--collect', '--quiet', '--property', 'TimeoutStopSec=30min'] + argv,
                             capture_output=True, text=True, timeout=30)
        if got.returncode != 0:
            raise Refused('systemd-run: %s' % (got.stderr or got.stdout).strip()[-200:])
        return
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)


# The packages a restart is needed for once they are updated, as dnf
# needs-restarting -r and Debian's reboot-required name them (1.0.159).
REBOOT_PKGS = {'kernel', 'kernel-core', 'kernel-rt', 'kernel-rt-core', 'kernel-modules',
               'kernel-uek', 'glibc', 'linux-firmware', 'systemd', 'dbus', 'dbus-broker',
               'dbus-daemon', 'microcode_ctl', 'zlib', 'zlib-ng-compat', 'libc6', 'linux-base',
               'intel-microcode', 'amd64-microcode'}


def reboot_for(packages):
    """Which of the packages waiting want a restart once updated."""
    out = []
    for p in packages:
        name = str(p).split()[0] if str(p).split() else ''
        if re.search(r'\.(x86_64|aarch64|noarch|i686|ppc64le|s390x)$', name):
            name = name.rsplit('.', 1)[0]
        if name in REBOOT_PKGS or name.startswith(('linux-image', 'kernel-core-', 'linux-modules')):
            out.append(name)
    return sorted(set(out))


def reboot_now(pm, env, say=None):
    """Whether this machine waits for a restart already."""
    if pm == 'fake':
        return subprocess.run([OSUP_PM, 'needs-restart'], stdout=subprocess.DEVNULL).returncode == 1
    if pm == 'dnf':
        nr = subprocess.run(['dnf', 'needs-restarting', '-r'], capture_output=True,
                            text=True, env=env, timeout=300)
        if nr.returncode == 1 and say:
            say(nr.stdout.strip().splitlines()[0] if nr.stdout.strip() else 'a restart is needed')
        return nr.returncode == 1
    return os.path.exists('/var/run/reboot-required')


def osup_job(ident, kind, security=False):
    """The work itself, as root, in a process of its own."""
    import fcntl
    fd = os.open(OSUP_LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 1
    state = {'id': ident, 'kind': kind, 'state': 'running', 'pct': 1, 'lines': [],
             'began': time.time(), 'at': time.time(), 'packages': [], 'reboot': False,
             'pm': osup_pm(), 'phase': 'starting'}
    last = [0.0]

    def put(force=False):
        state['at'] = time.time()
        if force or time.time() - last[0] > 0.8:
            last[0] = time.time()
            state['lines'] = state['lines'][-400:]
            write_here(OSUP_FILE, json.dumps(state))

    def say(line):
        line = line.rstrip()
        if line:
            state['lines'].append(line[:300])
        put()

    env = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'DEBIAN_FRONTEND': 'noninteractive', 'HOME': '/root'}
    osup_proxy_env(env)

    def stream(cmd, on_line=None, ok=(0,)):
        say('$ ' + ' '.join(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                             stdin=subprocess.DEVNULL, text=True, bufsize=1)
        for ln in p.stdout:
            say(ln)
            if on_line:
                on_line(ln)
        rc = p.wait()
        if rc not in ok:
            raise Refused('%s ended with %d' % (cmd[0], rc))
        return rc

    pm = state['pm']
    try:
        put(True)
        if kind == 'check':
            state['phase'] = 'asking for what is new'
            pk = []
            if pm == 'fake':
                stream([OSUP_PM, 'check'], lambda ln: pk.append(ln.strip())
                       if ln.strip() and not ln.startswith('#') else None)
            elif pm == 'dnf':
                rc_out = []
                stream(['dnf', '-q', '--refresh', 'check-update'], rc_out.append, ok=(0, 100))
                for ln in rc_out:
                    parts = ln.split()
                    if len(parts) >= 3 and '.' in parts[0] and not ln.startswith(' '):
                        pk.append('%s %s' % (parts[0], parts[1]))
                state['security'] = 0
                sec = subprocess.run(['dnf', '-q', 'updateinfo', 'list', '--security'],
                                     capture_output=True, text=True, env=env, timeout=300)
                state['security'] = len([x for x in sec.stdout.splitlines() if x.strip()])
            else:
                stream(['apt-get', 'update'])
                got = subprocess.run(['apt', 'list', '--upgradable'], capture_output=True,
                                     text=True, env=env, timeout=300)
                for ln in got.stdout.splitlines():
                    if '/' in ln and '[upgradable' in ln:
                        name = ln.split('/', 1)[0]
                        ver = ln.split()[1] if len(ln.split()) > 1 else ''
                        pk.append('%s %s' % (name, ver))
            state['packages'] = pk[:1000]
            state['count'] = len(pk)
            # Whether the update will need a restart, told before it is made.
            state['phase'] = 'whether a restart is needed'
            state['reboot_why'] = reboot_for(pk)
            state['reboot_after'] = bool(state['reboot_why'])
            try:
                state['reboot_now'] = reboot_now(pm, env)
            except (OSError, subprocess.SubprocessError):
                state['reboot_now'] = False
            if state['reboot_now']:
                say('a restart is needed already, before any update')
            if state['reboot_why']:
                say('a restart will be needed after the update: %s' % ', '.join(state['reboot_why']))
            state['pct'] = 100
        else:
            seen = {'total': 0, 'done': 0}

            def count(ln):
                m = re.search(r'\b(\d+)/(\d+)\s*$', ln)
                if pm in ('dnf', 'fake') and m and re.search(
                        r'(Upgrading|Installing|Cleanup|Verifying|Running scriptlet|Erasing|'
                        r'Reinstalling|Downgrading|Obsoleting)\s*:', ln):
                    total = int(m.group(2)) * 2          # each one upgraded and then verified
                    seen['total'] = max(seen['total'], total)
                    seen['done'] = min(seen['total'], seen['done'] + 1)
                    state['phase'] = 'putting the packages in'
                if pm == 'dnf' and ln.startswith('Downloading Packages'):
                    state['phase'] = 'downloading'
                    state['pct'] = max(state['pct'], 8)
                if pm == 'apt':
                    m2 = re.match(r'^(\d+) upgraded, (\d+) newly installed', ln)
                    if m2:
                        seen['total'] = (int(m2.group(1)) + int(m2.group(2))) * 2
                    if ln.startswith(('Unpacking ', 'Setting up ')):
                        seen['done'] += 1
                        state['phase'] = 'putting the packages in'
                    if ln.startswith('Get:'):
                        state['phase'] = 'downloading'
                        state['pct'] = max(state['pct'], 8)
                if seen['total']:
                    state['pct'] = max(state['pct'], min(97, 10 + int(87 * seen['done'] /
                                                                      seen['total'])))
            state['phase'] = 'asking for what is new'
            # Only the security updates where asked (1.0.37, as otp's 1.0.164):
            # dnf's own --security, unattended-upgrade on apt (it takes the
            # security sources only, as Debian and Ubuntu set it up).
            state['security_only'] = bool(security)
            if pm == 'fake':
                stream([OSUP_PM, 'upgrade'] + (['security'] if security else []), count)
            elif pm == 'dnf':
                stream(['dnf', '-y', '--refresh', 'upgrade'] + (['--security'] if security else []), count)
            elif security:
                if not shutil.which('unattended-upgrade'):
                    raise Refused('only the security updates: unattended-upgrade is not on this '
                                  'machine (apt install unattended-upgrades)')
                stream(['apt-get', 'update'])
                state['pct'] = max(state['pct'], 5)
                stream(['unattended-upgrade', '-v'], count)
            else:
                stream(['apt-get', 'update'])
                state['pct'] = max(state['pct'], 5)
                stream(['apt-get', '-y', '-o', 'Dpkg::Options::=--force-confdef', '-o',
                        'Dpkg::Options::=--force-confold', 'upgrade'], count)
            state['phase'] = 'whether a restart is needed'
            state['reboot'] = reboot_now(pm, env, say)
            state['pct'] = 100
        state['state'] = 'done'
        state['phase'] = 'done'
    except Refused as e:
        state.update(state='failed', said=str(e)[:300])
    except Exception as e:                              # noqa: BLE001
        state.update(state='failed', said='it broke: %s' % str(e)[:300])
    finally:
        put(True)
        os.close(fd)
    return 0




def main(argv):
    if len(argv) >= 3 and argv[0] == '--os-job':
        return osup_job(re.sub(r'[^A-Za-z0-9]', '', argv[1])[:40], argv[2] if argv[2] in ('check', 'upgrade') else 'check',
                        argv[3:4] == ['security'])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
