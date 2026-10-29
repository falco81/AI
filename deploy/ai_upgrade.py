#!/usr/bin/python3 -I
"""ai_upgrade.py - a new version of ai, checked and put in by root.

A package is trusted for nothing it says about itself:

  * it must be signed: MANIFEST lists the SHA-256 of every file, and
    MANIFEST.sig is the Ed25519 signature of MANIFEST by one of the keys in
    /usr/local/lib/ai/release-keys/ - which only root can write, and which
    only a package installed by root (install.sh) puts there;
  * every file in it is listed in MANIFEST with the right hash, nothing more,
    no links, no device, no path outside its one folder;
  * it is not older than the version installed (the same one again is a
    retry and is allowed; going back is done by hand, with that version's
    install.sh --upgrade).

Then its own install.sh --upgrade --yes is run, exactly as somebody would on
the command line. It runs in a systemd unit of its own (ai-upgrade-*), not
in ai.service, which install.sh restarts; the terminals (tmux) go on.

  ai_upgrade.py --inspect FILE      check a package and say what it is (JSON)
  ai_upgrade.py --run FILE          check and put in a package, said here
  ai_upgrade.py --job FILE --by WHO the same for the pages: what it says goes
                                    to /var/lib/ai/upgrade/last.log and
                                    status.json
"""
import hashlib
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time

STATE_DIR = os.environ.get('AI_STATE', '/var/lib/ai')
UPGRADE_DIR = os.path.join(STATE_DIR, 'upgrade')
LIB_DIR = os.environ.get('AI_LIB', '/usr/local/lib/ai')
KEYS_DIR = os.environ.get('AI_RELEASE_KEYS', os.path.join(LIB_DIR, 'release-keys'))
MOST_PACKED = 64 * 1024 * 1024
MOST_UNPACKED = 256 * 1024 * 1024
MOST_FILES = 5000
INSTALL_LIMIT_S = 20 * 60
TOP = re.compile(r'^ai-([0-9]+(?:\.[0-9]+){2,3})\Z')


class Refused(Exception):
    pass


def version_tuple(v):
    return tuple(int(x) for x in str(v).split('.'))


def installed_version():
    try:
        with open(os.path.join(LIB_DIR, 'ai.py'), encoding='utf-8') as f:
            for line in f:
                m = re.match(r"^__version__ = '([0-9.]+)'", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ''


def trusted_keys():
    try:
        names = sorted(n for n in os.listdir(KEYS_DIR) if n.endswith('.pub'))
    except OSError:
        names = []
    return [os.path.join(KEYS_DIR, n) for n in names]


def signed_by(manifest, signature):
    """The name of the trusted key that signed MANIFEST, or None."""
    for key in trusted_keys():
        try:
            r = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', key,
                                '-rawin', '-in', manifest, '-sigfile', signature],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise Refused('openssl is needed to check the signature, and it did not run')
        if r.returncode == 0:
            return os.path.basename(key)[:-4]
    return None


def inspect(path, extract_to=None):
    """Everything about a package that can be said without trusting it - and
    with extract_to, the package unpacked there once it has passed."""
    try:
        size = os.path.getsize(path)
    except OSError as e:
        raise Refused('the package cannot be read: %s' % e)
    if size > MOST_PACKED:
        raise Refused('the package is bigger than 64 MB, which no version of ai is')
    try:
        tar = tarfile.open(path, 'r:gz')
    except (tarfile.TarError, OSError, EOFError) as e:
        raise Refused('that is not a .tar.gz: %s' % e)
    with tar:
        # Read one header at a time and stopped at the limit (1.0.44):
        # getmembers() read every header first, millions of them if the
        # package said so, before anything was counted.
        members = []
        try:
            while True:
                one = tar.next()
                if one is None:
                    break
                members.append(one)
                if len(members) > MOST_FILES:
                    break
        except (tarfile.TarError, OSError, EOFError) as e:
            raise Refused('the package is damaged: %s' % e)
        if not members or len(members) > MOST_FILES:
            raise Refused('the package holds no files, or far too many')
        top = members[0].name.split('/')[0]
        m = TOP.match(top)
        if not m:
            raise Refused('the package is not an ai release: its folder is "%s", not ai-X.Y.Z'
                          % top[:80])
        version = m.group(1)
        files, total = {}, 0
        for one in members:
            name = one.name
            parts = name.split('/')
            if name.startswith('/') or '..' in parts or parts[0] != top or '\\' in name:
                raise Refused('the package has a path outside its folder: %s' % name[:120])
            if one.isdir():
                continue
            if not one.isreg():
                raise Refused('the package holds something that is not a plain file: %s'
                              % name[:120])
            total += one.size
            if total > MOST_UNPACKED:
                raise Refused('the package unpacks to more than 256 MB')
            rel = '/'.join(parts[1:])
            if rel in files:
                raise Refused('the package holds %s twice' % rel)
            files[rel] = one
        for need in ('MANIFEST', 'MANIFEST.sig', 'ai.py', 'install.sh'):
            if need not in files:
                raise Refused('the package has no %s%s' % (need, ' - it is not signed'
                                                             if need.startswith('MANIFEST')
                                                             else ''))
        work = tempfile.mkdtemp(prefix='ai-inspect-')
        try:
            man = os.path.join(work, 'MANIFEST')
            sig = os.path.join(work, 'MANIFEST.sig')
            for rel, dest in (('MANIFEST', man), ('MANIFEST.sig', sig)):
                if files[rel].size > 4 * 1024 * 1024:
                    raise Refused('%s is far too big' % rel)
                with tar.extractfile(files[rel]) as src, open(dest, 'wb') as out:
                    out.write(src.read())
            if not trusted_keys():
                raise Refused('no release key is installed on this machine (%s): install once on '
                              'the command line with install.sh --upgrade' % KEYS_DIR)
            who = signed_by(man, sig)
            if not who:
                raise Refused('the signature is not by any release key this machine trusts - '
                              'a package that was changed, or signed by an unknown key. Put it '
                              'in on the command line (install.sh --upgrade) if you trust it.')
            listed = {}
            with open(man, encoding='utf-8') as f:
                for line in f:
                    line = line.rstrip('\n')
                    if not line.strip():
                        continue
                    mm = re.match(r'^([0-9a-f]{64})  (.+)\Z', line)
                    if not mm:
                        raise Refused('MANIFEST has a line that does not read')
                    listed[mm.group(2)] = mm.group(1)
            have = set(files) - {'MANIFEST', 'MANIFEST.sig'}
            if set(listed) != have:
                extra = sorted(have - set(listed))[:3]
                missing = sorted(set(listed) - have)[:3]
                raise Refused('the files are not the ones signed%s%s' % (
                    (' - not signed: ' + ', '.join(extra)) if extra else '',
                    (' - missing: ' + ', '.join(missing)) if missing else ''))
            changelog = ''
            ai_version = ''
            for rel in sorted(have):
                h = hashlib.sha256()
                keep = rel in ('CHANGELOG.md', 'ai.py')
                body = []
                with tar.extractfile(files[rel]) as src:
                    while True:
                        lump = src.read(1 << 20)
                        if not lump:
                            break
                        h.update(lump)
                        if keep:
                            body.append(lump)
                if h.hexdigest() != listed[rel]:
                    raise Refused('%s is not the file that was signed' % rel)
                if rel == 'ai.py':
                    mm = re.search(rb"^__version__ = '([0-9.]+)'", b''.join(body), re.M)
                    ai_version = mm.group(1).decode() if mm else ''
                if rel == 'CHANGELOG.md':
                    text = b''.join(body).decode('utf-8', 'replace')
                    mm = re.search(r'^## %s\b.*?(?=^## |\Z)' % re.escape(version), text,
                                   re.M | re.S)
                    changelog = mm.group(0).strip()[:20000] if mm else ''
            if ai_version != version:
                raise Refused('the folder says %s and ai.py says %s' % (version, ai_version))
            if extract_to:
                for one in members:
                    target = os.path.join(extract_to, one.name)
                    if one.isdir():
                        os.makedirs(target, mode=0o755, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(target), mode=0o755, exist_ok=True)
                    with tar.extractfile(one) as src, \
                            open(target, 'xb') as out:
                        shutil.copyfileobj(src, out)
                    os.chmod(target, 0o755 if one.mode & 0o111 else 0o644)
        finally:
            shutil.rmtree(work, ignore_errors=True)
    have_v = installed_version()
    return {'version': version, 'top': top, 'files': len(have), 'signed_by': who,
            'bytes': size, 'changelog': changelog, 'installed': have_v,
            'newer': not have_v or version_tuple(version) > version_tuple(have_v),
            'older': bool(have_v) and version_tuple(version) < version_tuple(have_v)}


def write_here(name, text):
    os.makedirs(UPGRADE_DIR, mode=0o700, exist_ok=True)
    path = os.path.join(UPGRADE_DIR, name)
    fd, tmp = tempfile.mkstemp(prefix='.' + name + '.', dir=UPGRADE_DIR)
    with os.fdopen(fd, 'w') as f:
        f.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def status(**fields):
    fields['at'] = time.time()
    write_here('status.json', json.dumps(fields))


def put_in(package, by='the command line', log_to=print):
    """Check the package and run its install.sh --upgrade: (rc, info)."""
    if os.geteuid() != 0:
        raise Refused('putting a version in takes root')
    work = tempfile.mkdtemp(prefix='ai-upgrade-', dir='/var/tmp')
    os.chmod(work, 0o700)
    try:
        copy = os.path.join(work, 'package.tar.gz')
        shutil.copyfile(package, copy)
        unpacked = os.path.join(work, 'x')
        os.makedirs(unpacked, mode=0o700)
        info = inspect(copy, extract_to=unpacked)
        if info['older']:
            raise Refused('%s is older than %s, which is installed: going back is done by hand, '
                          'with that version\'s install.sh --upgrade' % (info['version'], info['installed']))
        log_to('ai %s, signed by %s, %d files - checked' % (info['version'], info['signed_by'], info['files']))
        src = os.path.join(unpacked, info['top'])
        env = {'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
               'LANG': 'C.UTF-8', 'AI_UPGRADE_FROM_PAGES': '1', 'TERM': 'dumb',
               'AI_UPGRADE_BY': str(by)[:100]}
        log_to('running %s/install.sh --upgrade --yes' % info['top'])
        p = subprocess.Popen(['bash', os.path.join(src, 'install.sh'), '--upgrade', '--yes'],
                             cwd=src, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             start_new_session=True)
        late = []

        def too_long():
            late.append(time.time())
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except OSError:
                pass
        dog = threading.Timer(INSTALL_LIMIT_S, too_long)
        dog.daemon = True
        dog.start()
        try:
            fd = p.stdout.fileno()
            buf = b''
            while True:
                if late and time.time() - late[0] > 35:
                    break
                r, _w, _x = select.select([fd], [], [], 1.0)
                if not r:
                    if p.poll() is not None:
                        break
                    continue
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                buf += chunk
                while b'\n' in buf:
                    raw, buf = buf.split(b'\n', 1)
                    log_to(re.sub(r'\x1b\[[0-9;]*m', '', raw.decode('utf-8', 'replace')))
            if buf:
                log_to(re.sub(r'\x1b\[[0-9;]*m', '', buf.decode('utf-8', 'replace')))
            rc = p.wait()
        finally:
            dog.cancel()
        if late:
            raise Refused('install.sh did not finish in %d min and was stopped' % (INSTALL_LIMIT_S // 60))
        log_to('install.sh ended with %d' % rc)
        return rc, info
    finally:
        shutil.rmtree(work, ignore_errors=True)


def job(package, by):
    lines = []
    last = [0.0]

    def log_to(text):
        lines.append(text)
        if time.time() - last[0] > 1.5:
            last[0] = time.time()
            try:
                write_here('last.log', '\n'.join(lines[-4000:]) + '\n')
            except OSError:
                pass
    try:
        status(state='running', by=by, file=os.path.basename(package))
        rc, info = put_in(package, by, log_to)
        status(state='done' if rc == 0 else 'failed', rc=rc, version=info['version'], by=by,
               tail=lines[-40:])
    except Refused as e:
        log_to('refused: %s' % e)
        status(state='failed', rc=-1, said=str(e), by=by, tail=lines[-40:])
    except Exception as e:                       # noqa: BLE001 - said, never lost
        log_to('broke: %s' % e)
        status(state='failed', rc=-2, said='the upgrade broke: %s' % e, by=by, tail=lines[-40:])
    finally:
        write_here('last.log', '\n'.join(lines[-4000:]) + '\n')
        try:
            if os.path.dirname(os.path.abspath(package)) == UPGRADE_DIR:
                os.unlink(package)
        except OSError:
            pass
    return 0


def main(argv):
    if len(argv) >= 2 and argv[0] == '--inspect':
        try:
            print(json.dumps(dict(inspect(argv[1]), ok=True)))
        except Refused as e:
            print(json.dumps({'ok': False, 'said': str(e)}))
        return 0
    if len(argv) >= 2 and argv[0] == '--run':
        try:
            rc, _info = put_in(os.path.abspath(argv[1]))
        except Refused as e:
            print('refused: %s' % e)
            return 1
        return rc
    if len(argv) >= 2 and argv[0] == '--job':
        by = argv[3] if len(argv) >= 4 and argv[2] == '--by' else 'the pages'
        return job(os.path.abspath(argv[1]), by)
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
