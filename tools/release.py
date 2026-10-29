#!/usr/bin/env python3
"""tools/release.py - a release of ai: signed, packed, put into release/.

    python3 tools/release.py              the version in ai.py
    python3 tools/release.py --check      only check that it would go

What it does, from the folder this is in (the repository, which is the
unpacked package itself, as otp's is):

  1. MANIFEST - the SHA-256 of every file of the package - and MANIFEST.sig,
     its Ed25519 signature by the release key (openssl pkeyutl);
  2. the signature checked against a public key in deploy/release-keys/, the
     one install.sh puts on every server, so that a server takes it;
  3. release/ai-X.Y.Z.tar.gz, with every file under ai-X.Y.Z/, checked again
     the way a server checks it (deploy/ai_upgrade.py --inspect);
  4. release/ kept to the ten newest packages - what upgrade_url offers.

The private key is never in the repository. It is read from AI_RELEASE_KEY
(the PEM itself, for a CI or a cloud environment's secret), AI_RELEASE_KEY_FILE,
or ~/.ai-release/ai-release-1.key.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEEP = 10
LEAVE_OUT = {'.git', 'release', '__pycache__', '.ai-uploads', 'MANIFEST', 'MANIFEST.sig', '.github'}


def version():
    with open(os.path.join(ROOT, 'ai.py'), encoding='utf-8') as f:
        m = re.search(r"^__version__ = '([0-9.]+)'", f.read(), re.M)
    if not m:
        raise SystemExit('no __version__ in ai.py')
    return m.group(1)


def files():
    out = []
    for top, dirs, names in os.walk(ROOT):
        rel_top = os.path.relpath(top, ROOT)
        dirs[:] = sorted(d for d in dirs if d not in LEAVE_OUT and not d.startswith('.'))
        for n in sorted(names):
            rel = n if rel_top == '.' else os.path.join(rel_top, n).replace(os.sep, '/')
            if rel in LEAVE_OUT or n.endswith(('.pyc', '.swp', '~')) or n.startswith('.') and n != '.user.ini':
                continue
            out.append(rel)
    return sorted(out)


def key_file(work):
    pem = os.environ.get('AI_RELEASE_KEY', '').strip()
    if pem:
        p = os.path.join(work, 'release.key')
        with open(p, 'w') as f:
            f.write(pem.replace('\\n', '\n') + '\n')
        os.chmod(p, 0o600)
        return p
    for p in (os.environ.get('AI_RELEASE_KEY_FILE', ''), os.path.expanduser('~/.ai-release/ai-release-1.key')):
        if p and os.path.isfile(p):
            return p
    raise SystemExit('no release key: AI_RELEASE_KEY, AI_RELEASE_KEY_FILE or ~/.ai-release/ai-release-1.key')


def sign(key, manifest, sig):
    got = subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', key, '-rawin', '-in', manifest,
                          '-out', sig], capture_output=True, text=True)
    if got.returncode != 0:
        raise SystemExit('openssl could not sign: %s' % got.stderr.strip())


def verified(manifest, sig):
    keys = os.path.join(ROOT, 'deploy', 'release-keys')
    for n in sorted(os.listdir(keys)):
        if n.endswith('.pub'):
            got = subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', os.path.join(keys, n),
                                  '-rawin', '-in', manifest, '-sigfile', sig], capture_output=True)
            if got.returncode == 0:
                return n
    return ''


def main(argv):
    check = '--check' in argv
    v = version()
    names = files()
    for need in ('ai.py', 'install.sh', 'deploy/ai_upgrade.py', 'deploy/ai_os.py', 'CHANGELOG.md'):
        if need not in names:
            raise SystemExit('%s is missing' % need)
    with open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8') as f:
        if not re.search(r'^## %s\b' % re.escape(v), f.read(), re.M):
            raise SystemExit('CHANGELOG.md says nothing of %s' % v)
    lines = []
    for rel in names:
        h = hashlib.sha256()
        with open(os.path.join(ROOT, rel), 'rb') as f:
            for lump in iter(lambda: f.read(1 << 20), b''):
                h.update(lump)
        lines.append('%s  %s' % (h.hexdigest(), rel))
    if check:
        print('ai %s: %d files - fine' % (v, len(names)))
        return 0
    manifest = os.path.join(ROOT, 'MANIFEST')
    sig = os.path.join(ROOT, 'MANIFEST.sig')
    with open(manifest, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    with tempfile.TemporaryDirectory(prefix='ai-release-') as work:
        sign(key_file(work), manifest, sig)
    who = verified(manifest, sig)
    if not who:
        raise SystemExit('the signature is not by any key in deploy/release-keys/ - a server would refuse it')
    rel_dir = os.path.join(ROOT, 'release')
    os.makedirs(rel_dir, exist_ok=True)
    top = 'ai-%s' % v
    out = os.path.join(rel_dir, top + '.tar.gz')
    with tarfile.open(out, 'w:gz', format=tarfile.PAX_FORMAT) as tar:
        def add_dir(name):
            ti = tarfile.TarInfo(name)
            ti.type, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = tarfile.DIRTYPE, 0o755, 0, 0, 'root', 'root'
            tar.addfile(ti)
        add_dir(top)
        seen = set()
        for rel in names + ['MANIFEST', 'MANIFEST.sig']:
            parts = rel.split('/')
            for i in range(1, len(parts)):
                d = '/'.join(parts[:i])
                if d not in seen:
                    seen.add(d)
                    add_dir(top + '/' + d)
            full = os.path.join(ROOT, rel)
            ti = tar.gettarinfo(full, arcname=top + '/' + rel)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = 'root'
            ti.mode = 0o755 if os.access(full, os.X_OK) else 0o644
            with open(full, 'rb') as f:
                tar.addfile(ti, f)
    got = subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'deploy', 'ai_upgrade.py'), '--inspect', out],
                         capture_output=True, text=True, env=dict(os.environ, AI_RELEASE_KEYS=os.path.join(
                             ROOT, 'deploy', 'release-keys'), AI_LIB='/nonexistent'))
    info = json.loads(got.stdout.strip().splitlines()[-1])
    if not info.get('ok'):
        raise SystemExit('the package does not pass the check a server makes: %s' % info.get('said'))
    pk = sorted((n for n in os.listdir(rel_dir) if re.match(r'^ai-\d+\.\d+\.\d+\.tar\.gz$', n)),
                key=lambda n: tuple(int(x) for x in n[3:-7].split('.')))
    for old in pk[:-KEEP]:
        os.unlink(os.path.join(rel_dir, old))
        print('taken away: release/%s' % old)
    print('release/%s - %d files, signed by %s, %d bytes' % (os.path.basename(out), info['files'], who,
                                                            os.path.getsize(out)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
