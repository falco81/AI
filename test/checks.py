#!/usr/bin/env python3
"""The parts of ai that can be checked without a server: run as
python3 test/checks.py - from the unpacked folder."""
import importlib.util
import json
import os
import sys
import time
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = tempfile.mkdtemp(prefix='ai-checks-')
os.environ.update(AI_STATE=WORK, AI_RUN=WORK + '/run', AI_LOGDIR=WORK + '/log', AI_CONFIG=WORK + '/none.json',
                  AI_NO_SYSTEM='1', AI_LIB=os.path.join(HERE, 'deploy'))
spec = importlib.util.spec_from_file_location('ai', os.path.join(HERE, 'ai.py'))
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)
FAILS = []


def check(what, ok):
    print('%s %s' % ('ok  ' if ok else 'FAIL', what))
    if not ok:
        FAILS.append(what)


h = ai.hash_password('a long password')
check('a password is checked by its hash', ai.check_password('a long password', h)
      and not ai.check_password('another one', h))
check('the WebSocket accept key (RFC 6455)',
      ai.WebSocket.accept_key('dGhlIHNhbXBsZSBub25jZQ==') == 's3pPLMBiTxaQ9kYGzzhZRbK+xOo=')
check('NAME=value lines', ai.env_lines('# x\nA=1\nexport B="two words"\n bad line\n') == {'A': '1', 'B': 'two words'})
r = ai.fw_rule_checked({'proto': 'tcp', 'port': '80, 443', 'source': '10.1.2.3/8'})
check('a firewall rule taken apart', r['port'] == '80,443' and r['source'] == '10.0.0.0/8' and r['family'] == 4)
try:
    ai.fw_rule_checked({'proto': 'icmp', 'port': '22'})
    check('a port with ICMP refused', False)
except ai.Refused:
    check('a port with ICMP refused', True)
lines = ai.fw_lines({'rules': [r], 'off': ['icmp', 'dhcpv6']}, [{'key': 'ssh', 'title': 'SSH', 'rules': [
    {'family': 4, 'proto': 'tcp', 'port': '22', 'source': ''}]}], 4)
check('the chain AI-IN: loopback, answers, yours, then ai\'s',
      lines[0].startswith('-A AI-IN -i lo') and '--dports 80,443' in lines[2] and '--dport 22' in lines[3])
t = ai.Terms(None)
s = t.claude_script({'resume': '1234', 'model': 'opus', 'mode': 'plan', 'args': '--verbose'})
check('Claude Code started with what was chosen',
      "exec claude --resume 1234 --model opus --permission-mode plan --verbose" in s)
p = os.path.join(WORK, 'c.jsonl')
with open(p, 'w') as f:
    f.write(json.dumps({'type': 'user', 'cwd': '/srv/x', 'message': {'content': 'make it faster'}}) + '\n')
    f.write(json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'ok'}]}}) + '\n')
c = ai.conversation_facts(p)
check('a conversation read for the list', c['cwd'] == '/srv/x' and c['first'] == 'make it faster' and c['messages'] == 2)
st = ai.Store(os.path.join(WORK, 'ai.db'))
a = ai.Auth(st)
a.add_user('alice', 'a good long password', 'admin', '')
tok = a.login('alice', 'a good long password', '127.0.0.1')
check('signing in, and the session found again', a.who(tok)['name'] == 'alice')
try:
    a.login('alice', 'wrong', '127.0.0.1')
    check('a wrong password refused', False)
except ai.Refused:
    check('a wrong password refused', True)
check('the newest of the packages', [x['version'] for x in sorted(
    [{'version': v} for v in ('1.0.9', '1.0.10', '1.0.2')], key=lambda x: ai.ver_tuple(x['version']),
    reverse=True)] == ['1.0.10', '1.0.9', '1.0.2'])
pal = ai.Palette(False)
check('plain output says ok and fail in words', pal.ok_line('x') == '[ ok ] x' and pal.bad_line('y') == '[fail] y')
p2 = ai.build_parser()
a2 = p2.parse_args(['--fw-open', '8080/udp', '--from', '10.0.0.0/8'])
check('the command line takes the firewall\'s words', a2.fw_open == '8080/udp' and a2.source == '10.0.0.0/8')
# ---- 1.0.4: what came from otp ------------------------------------------------------------
check('TOTP of RFC 6238 (SHA-1, 59 s)', ai.totp(ai.base64.b32encode(b'12345678901234567890').decode(), 59, 8)
      == '94287082')
sec = ai.b32_new()
check('a code of now is found, and its step', ai.totp_match(sec, ai.totp(sec)) == ai.totp_step())
check('a wrong code is not', ai.totp_match(sec, '000000' if ai.totp(sec) != '000000' else '111111') is None)
q = ai.QrCode('otpauth://totp/x?secret=ABC', 'M')
check('a QR code drawn', q.size >= 21 and ai.qr_data_uri('hello').startswith('data:image/svg+xml;base64,'))
sealed = ai.seal_secret('the secret', 'setting:x')
check('a secret sealed opens only where it was sealed for', ai.unseal_secret(sealed, 'setting:x') == 'the secret'
      and ai.unseal_secret(sealed, 'setting:y') is None and sealed.startswith('sealed:2:'))
block = 'server {\n    listen 443 ssl;\n    server_name x;\n    ssl_protocols TLSv1.2;\n    location / { ssl_protocols x; }\n}'
b2 = ai.set_directive(block, 'ssl_protocols', 'TLSv1.3')
check('a line of nginx set in its server, not in a location', 'ssl_protocols             TLSv1.3;' in b2
      and 'ssl_protocols x;' in b2 and b2.count('TLSv1.2') == 0)
check('the server on 443 found', ai.nginx_tls_block('server {\n listen 80;\n}\n' + block)[1].startswith('server {\n    listen 443'))
f = ai.text_message('sms_code')['fields'][0]
try:
    ai.text_check(f, '{site}: {code} {other}')
    bad = False
except ValueError:
    bad = True
check('a text with a word it may not have refused', bad)
check('a text of a mail kept to what mail programs show', ai.text_rich_clean('<b>a</b><script>x</script><i>b</i>')
      == '<b>a</b><i>b</i>')
check('a code kept out of the list of the outgoing mail', ai.mailq_subject_kept('Kód 123456', 'code') == 'Kód ••••••')
check('the outgoing mail searched by field', ai.mailq_match({'to': 'a@b.cz', 'state': 'waiting', 'kind': 'code',
                                                            'name': '', 'by': '', 'said': 'greylisted', 'subject': '',
                                                            'tries': 3}, 'to:*@b.cz state:waiting tries:>2 -kind:test'))
check('a layout of the columns reduced to what it may hold', ai.clean_cols({'t': {'w': {'a': 9999999, 'b': 'x'},
                                                                                   'o': ['a', 3], 'zz': 1}})
      == {'t': {'w': {'a': 3000}, 'o': ['a', '3'], 't': 0}})
lk = ai.lock_with('phrase one', {'a': 1})
check('a file locked with a passphrase opens with it alone', ai.open_with('phrase one', lk) == {'a': 1})
try:
    ai.open_with('another', lk)
    check('... and not with another', False)
except ai.Refused:
    check('... and not with another', True)
check('a TLS policy checked', ai.tls_policy_checked({'preset': 'modern', 'dh': 'none', 'hsts': 0})
      == {'preset': 'modern', 'dh': 'none', 'prefer': False, 'hsts': 0})
check('a mail address and a phone number checked', ai.mail_checked('a@b.cz') == 'a@b.cz'
      and ai.phone_checked('+420 603 123 456') == '+420603123456')
check('the oldest version safe to go back to', ai.ver_tuple(ai.DOWNGRADE_FLOOR) <= ai.ver_tuple(ai.__version__))

# ---- 1.0.9: Claude Code's options, the folder of the chats ------------------------------
got = ai.cc_option_args({'effort': 'high', 'allowed_tools': 'Bash(git *)\nEdit', 'worktree': True, 'debug': 'hooks',
                         'verbose': True, 'plugin_dirs': ['/a', '/b'], 'name': 'x y'})
check('the options of Claude Code on its command line', got == ['--name', 'x y', '--effort', 'high', '--allowedTools',
                                                                'Bash(git *)', 'Edit', '--plugin-dir', '/a', '--plugin-dir',
                                                                '/b', '--worktree', '--verbose', '--debug=hooks'])
try:
    ai.cc_option_args({'effort': 'enormous'})
    bad = False
except ai.Refused:
    bad = True
check('an effort Claude Code does not know refused', bad)
script = ai.Terms(None).claude_script({'prompt': 'start -w here', 'worktree': True})
check('the first message after every option', script.endswith("--worktree -- 'start -w here'"))
check('a folder under the folder of the chats', ai.path_under('/srv/chats/a/b', '/srv/chats') and not ai.path_under('/srv/chatsX', '/srv/chats'))
check('a name of an agent or a command kept to what it may be', bool(ai.CC_NAME_RE.match('front/component'))
      and not ai.CC_NAME_RE.match('../x') and not ai.CC_NAME_RE.match('/etc'))
check('the head of an agent read', ai.cc_front('---\nname: r\ndescription: Reviews\n---\nbody') == {'name': 'r', 'description': 'Reviews'})

check('a million tokens of Opus 5.5 written at its list price', abs(ai.usage_cost('claude-opus-5-5', 0, 10**6, 0, 0) - 20.0) < 1e-9)
check('the longest name of a model wins its price', abs(ai.usage_cost('claude-sonnet-5-5', 10**6, 0, 0, 0) - 2.0) < 1e-9
      and abs(ai.usage_cost('claude-sonnet-4-6', 10**6, 0, 0, 0) - 3.0) < 1e-9)
check('a model of no known price said so', ai.usage_cost('gpt-9', 1, 1, 1, 1) is None)
_tr = os.path.join(tempfile.mkdtemp(), 'x.jsonl')
with open(_tr, 'w') as _f:
    for _ in range(2):      # one answer written twice, once per block
        _f.write(json.dumps({'timestamp': '2026-10-30T08:00:00Z', 'cwd': '/srv/x', 'message': {'id': 'm1', 'model': 'claude-opus-5-5',
                             'usage': {'input_tokens': 3, 'output_tokens': 5, 'cache_read_input_tokens': 7}}}) + '\n')
check('an answer of a transcript counted once', ai.usage_file_rows(_tr, os.stat(_tr)) == [
    ('2026-10-30', 'claude-opus-5-5', '/srv/x', 3, 5, 0, 7, '2026-10-30T08:00:00Z')])

ai.CONFIG['claude_classic'] = True
check('Claude Code drawn into tmux\'s history', ai.Terms(None).claude_script({}).startswith('export CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1; '))
ai.CONFIG['claude_classic'] = False
check('...or in its own full-screen look', 'CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN' not in ai.Terms(None).claude_script({}))
ai.CONFIG['claude_classic'] = True

check('a PNG of the site\'s own known by its first bytes', ai.logo_kind(b'\x89PNG\r\n\x1a\n....') == 'image/png')
check('something not a picture not taken for one', not ai.logo_kind(b'hello'))
try:
    ai.logo_check(b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    check('an SVG with a script turned away', False)
except ai.Refused:
    check('an SVG with a script turned away', True)
check('every picture of the sign-in drawn', set(ai.ART_NAMES) == {'browser', 'terminal', 'chat', 'tmux', 'devices',
      'spark', 'tablet', 'diff', 'folders', 'agents', 'usage', 'keys', 'none', 'custom'})

_inst = open(os.path.join(HERE, 'install.sh')).read()
check('install.sh puts in every PHP file of the pages', '/web/*.php' in _inst)

check('big numbers short on the command line', ai.big_num(1234) == '1.2k' and ai.big_num(5) == '5'
      and ai.big_num(2500000) == '2.5M')
check('a permission mode checked', ai.cli_mode('acceptEdits') == 'acceptEdits' and ai.cli_mode('default') == '')
_pa = ai.build_parser().parse_args(['--edit', 'abcd1234', '--effort', 'high', '--mode', 'plan', '--cwd', '/srv'])
check('--edit takes its choices', (_pa.edit, _pa.effort, _pa.mode, _pa.cwd) == ('abcd1234', 'high', 'plan', '/srv'))
check('--signin-art alone asks which one', ai.build_parser().parse_args(['--signin-art']).signin_art == '')
check('every picture has its words in the console', all(n in ai.ART_WORDS_TEXT for n in ai.ART_NAMES))

check('every form of the certificate known', set(ai.TLS_EXPORTS) == {'pem', 'crt', 'der', 'p7b', 'pem_key', 'key', 'pfx'})
try:
    ai.tls_export({'cert': 'x'}, 'pfx', '')
    check('a .pfx without a password turned away', False)
except ai.Refused:
    check('a .pfx without a password turned away', True)
try:
    ai.tls_export({}, 'zip')
    check('an unknown form turned away', False)
except ai.Refused:
    check('an unknown form turned away', True)

# ACME (1.0.39)
check('every key Let\'s Encrypt takes can be asked for', set(c[0] for c in ai.SCHEMA_KEYS['acme_key'][5]['choices'])
      == set(ai.ACME_CERT_KEYS) == {'dual', 'dual-strong', 'ec', 'ec384', 'rsa2048', 'rsa3072', 'rsa4096'})
check('the account\'s key any Let\'s Encrypt takes', set(c[0] for c in ai.SCHEMA_KEYS['acme_account_key'][5]['choices'])
      == set(ai.KEY_WORDS))
check('both is what is ordered unless said', ai.DEFAULTS['acme_key'] == 'dual')
check('the second certificate goes with its own first one only',
      ai.tls_alt({'cert': 'A', 'alt': {'cert': 'x', 'key': 'k', 'for': ai.tls_alt_for('A')}}) is not None and
      ai.tls_alt({'cert': 'B', 'alt': {'cert': 'x', 'key': 'k', 'for': ai.tls_alt_for('A')}}) is None)
check('the page never sees the second key', 'key' not in (ai.tls_view({'cert': 'A', 'alt': {'cert': 'x', 'key': 'k', 'for': ai.tls_alt_for('A'), 'info': {}}}) or {}).get('alt', {}))
check('an ECDSA P-384 key made', 'BEGIN PRIVATE KEY' in ai.new_key('ec384'))
check('base64url without padding', ai._b64u(b'\xfb\xff') == '-_8')
_was = dict(ai.CONFIG)
ai.CONFIG.update(acme_dns='desec', acme_desec_domain='x.dedyn.io', acme_dns_alias='')
check('a TXT record of another domain goes to deSEC by a CNAME',
      ai.acme_dns_where('ai.example.cz') == ('_acme-challenge.ai.x.dedyn.io', '_acme-challenge.ai.x.dedyn.io'))
check('a name at deSEC itself needs no CNAME', ai.acme_dns_where('ai.x.dedyn.io') == ('_acme-challenge.ai.x.dedyn.io', None))
ai.CONFIG.clear(); ai.CONFIG.update(_was)
check('an ACME account gone is known by its error', ai._acme_account_gone('urn:ietf:params:acme:error:accountDoesNotExist', ''))

# maintenance (1.0.46)
class _MSt:
    def __init__(s): s.m = {}; s.ev = []
    def meta_json(s, k, d=None): import json as _j; return _j.loads(s.m[k]) if k in s.m else d
    def set_meta(s, k, v): s.m[k] = v
    def add_event(s, *a, **k): s.ev.append(a[1])
_ms = _MSt()
check('in service unless said', ai.maintenance_row(_ms) == {'on': False})
ai.maintenance_set(_ms, True, 'upgrade to 9.9.9', ai.MAINT_BY_UPGRADE)
_was_dir = ai.UPGRADE_DIR
ai.UPGRADE_DIR = ai.Path(tempfile.mkdtemp())
(ai.UPGRADE_DIR / 'status.json').write_text('{"state": "running", "at": %f}' % __import__('time').time())
ai.maintenance_settle(_ms)
check('kept out of service while the upgrade runs', ai.maintenance_row(_ms).get('on') is True)
(ai.UPGRADE_DIR / 'status.json').write_text('{"state": "done"}')
ai.maintenance_settle(_ms)
check('back in service once the upgrade is over', ai.maintenance_row(_ms).get('on') is False)
ai.maintenance_set(_ms, True, 'by hand', 'admin')
ai.maintenance_settle(_ms)
check('one taken out by hand stays out', ai.maintenance_row(_ms).get('on') is True)
ai.UPGRADE_DIR = _was_dir

# the proxy (1.0.47)
_pw = dict(ai.CONFIG)
ai.CONFIG.update(proxy=True, proxy_url='http://px.example.cz:3128', proxy_user='', proxy_no='localhost, .example.cz, 10.0.0.0/8',
                 proxy_os=False, proxy_acme=False, proxy_terms=False)
check('Try it asks the proxy itself', ai.proxy_full() == 'http://px.example.cz:3128')
check('every use off at first', all(ai.DEFAULTS[k] is False for k in ai.PROXY_USES.values())
      and ai.DEFAULTS['proxy'] is False)
check('no use through it unless switched on', all(ai.proxy_full(u) == '' for u in ai.PROXY_USES)
      and ai.proxy_env('terms') == {})
ai.CONFIG.update(proxy_acme=True, proxy_terms=True)
check('a use switched on goes through it', ai.proxy_full('acme') == 'http://px.example.cz:3128'
      and ai.proxy_full('upgrade') == '' and ai.proxy_full('os') == '')
check('the terminals get it in their environment', ai.proxy_env('terms').get('HTTPS_PROXY') == 'http://px.example.cz:3128'
      and '.example.cz' in ai.proxy_env('terms')['NO_PROXY'])
check('a name under a domain of the list straight', ai.proxy_skips('a.example.cz') and not ai.proxy_skips('github.com'))
check('an address in a net of the list straight', ai.proxy_skips('10.1.2.3') and not ai.proxy_skips('192.0.2.1'))
ai.CONFIG.clear(); ai.CONFIG.update(_pw)
check('no proxy unless switched on', ai.proxy_full() == '' and ai.proxy_full('acme') == '')
_src = open(os.path.join(HERE, 'ai.py')).read()
import re as _re
check('every way out over HTTP names its use', 'urllib.request.urlopen(' not in _src.replace(
      "urllib.request.urlopen(req, timeout=3)", '') and
      all(u in _src for u in ("purpose='upgrade'", "purpose='acme'", "purpose='acme_dns'", "purpose='sms'",
                              "purpose='sms_tel'", "proxy_use='claude_install'")))

_ins = open(os.path.join(HERE, 'install.sh')).read()
check('only errors on the console, a printk set by hand kept', 'kernel.printk = 4 4 1 7' in _ins and
      '\nconsole_quiet\n' in _ins and 'set by hand' in _ins and 'chmod +x /etc/rc.d' not in _ins
      and '/etc/sysctl.d/80-ai-console.conf; do' in _ins)

check('every password is drawn masked, its last two shown', all(ai.secret_key(k) for k, _p, kind, *_r in ai.SCHEMA
      if kind == 'password') and ai.secret_shown('TajneHeslo42') == '••••••••••42' and ai.is_masked(ai.secret_shown('ab12345')))

_js = open(os.path.join(HERE, 'web', 'assets', 'app.js')).read()
check('the move to another database is one wizard and one job', 'def db_migrate(' in _src and
      "act == 'migrate'" in _src and "act == 'migrate_check'" in _src and 'function migOpen' in _js and
      "id=\"db-migrate\"" in open(os.path.join(HERE, 'web', 'index.php')).read() and
      'db-engine-move' not in open(os.path.join(HERE, 'web', 'index.php')).read())
check('nothing written into config.json before the switch', _src.index("if switch:\n            progress(7, 7")
      < _src.index("write_file_settings({k: c.get(k) for k in DB_KEYS})", _src.index('def db_migrate(')))

check('the database settings stay on the page beside the wizard', 'DB_WIZARD_KEYS' not in _js and
      "s.key === 'db_engine'" in _js and 'another engine is reached by Move to another database' in _src)

# acme push (1.0.58): the vectors of the protocol's document, in plain Python and with cryptography
import re as _re2, collections as _co, base64
_names = _co.Counter(a or b for a, b in _re2.findall(r'^(?:def|class)\s+([A-Za-z_]\w*)|^([A-Za-z_]\w*)\s*=', _src, _re2.M))
check('no name defined twice in ai.py (a new part never replaces an old one)', not [k for k, v in _names.items() if v > 1])
_was_crypto = ai.PUSH_CRYPTO
for _mode in ('python', _was_crypto):
    ai.PUSH_CRYPTO = _mode
    _app = bytes(range(32, 64)); _eph = bytes(range(64, 96)); _gn = bytes(range(96, 108))
    _apub = ai.push_x25519(_app, (9).to_bytes(32, 'little'))
    _sealed = ai.push_seal_key('KEY\n', _apub, '00112233445566778899aabbccddeeff', 'ab' * 32, eph=_eph, nonce=_gn)
    _pub = base64.b64decode('A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=')
    _can = ai.push_canonical('inventory', '00112233445566778899aabbccddeeff', '56475aa75463474c', 1793534400,
                             'n0nce-0123456789ab', b'{"slots": ["auto"]}')
    _sig = base64.b64decode('7nqJW4/NR3Et6pZx3B8qS3rvQGaQR0UTlNdptpRs4lxaZtc3Cf2zBRkOWPB0tV/rmQNfwbcl2/FKJ3Pu2h/bDg==')
    check('acme push vectors (%s)' % _mode,
          base64.b64encode(_apub).decode() == 'NYBy1jZYgNGu6jKa35EhODhR7SGijjt16WXQ0s0WYlQ=' and
          _sealed['ct'] == '2UbSrj9NwnCBu3qZW4U7MzxzlGw=' and ai.push_key_id(_pub) == '56475aa75463474c' and
          ai.push_ed25519_verify(_pub, _can, _sig) and not ai.push_ed25519_verify(_pub, _can + b'x', _sig) and
          ai.push_open_key(_sealed, _app, '00112233445566778899aabbccddeeff', 'ab' * 32) == 'KEY\n' and
          ai.push_open_key(_sealed, _app, '00112233445566778899aabbccddeeff', 'cd' * 32) is None and
          ai.push_proof('ABCD-EFGH-JKMN-PQRS', 'pair', '00112233445566778899aabbccddeeff', '56475aa75463474c',
                        'n0nce-0123456789ab') == 'e8e1978c03896460ce7f6e1697d5a5220c8f3a1cd8a01d2fc2e838dbd9318b39')
ai.PUSH_CRYPTO = _was_crypto
check('acme push is off until switched on', "'on': bool(got.get('on'))" in _src and
      "acme-push-(hello|pair|inventory|install)" in open(os.path.join(HERE, 'web', 'index.php')).read())

ai.CONFIG.update(upgrade_auto=True)
check('ai --get shows a value as --set takes it', ai.cli_get_value('upgrade_auto') == 'true' and
      ai.cli_get_value('acme_days') == str(ai.CONFIG.get('acme_days')))

check('Claude Code upkeep is not kept to the folders of the chats', "upkeep=True)" in _src and
      "keep['upkeep'] = True" in _src and "if root and not upkeep and not path_under(cwd, root)" in _src)

check('a passkey\'s COSE key becomes PEM', ai.passkey_pem({1: 2, 3: -7, -1: 1, -2: b'\x01' * 32, -3: b'\x02' * 32})[1]
      .startswith('-----BEGIN PUBLIC KEY-----') and ai._pk_cbor(bytes.fromhex('a2616101616283020304'))[0] == {'a': 1, 'b': [2, 3, 4]})

check('passkeys are off until switched on', ai.DEFAULTS['passkeys'] is False and "CONFIG.get('passkeys', True)" not in _src)

_l = ai.server_load()
check('the load of the server is read from /proc', isinstance(_l.get('mem_total'), int) and _l.get('cores') >= 1)

import tempfile as _tf
_fs = _tf.mkdtemp()
def _w(rel, txt):
    f = os.path.join(_fs, rel); os.makedirs(os.path.dirname(f), exist_ok=True); open(f, 'w').write(txt)
_w('class/hwmon/hwmon0/name', 'coretemp\n'); _w('class/hwmon/hwmon0/temp1_input', '52000\n')
_w('class/hwmon/hwmon0/temp1_label', 'Package id 0\n'); _w('class/hwmon/hwmon0/temp2_input', '49000\n')
_w('class/hwmon/hwmon0/temp2_label', 'Core 0\n'); _w('class/hwmon/hwmon0/temp3_input', '55000\n')
_w('class/hwmon/hwmon0/temp3_label', 'Core 1\n')
_was_sys, ai.LOAD_SYS = ai.LOAD_SYS, _fs
_t = ai.load_temps()
check('temperatures are read per core and of the whole processor',
      _t.get('cpu') == [['Package id 0', 52.0]] and {str(k): v for k, v in _t.get('cores', {}).items()} == {'0': 49.0, '1': 55.0})
ai.LOAD_SYS = _was_sys
import shutil as _sh; _sh.rmtree(_fs, ignore_errors=True)
_d = ai.load_detail()
check('the load panels have each core, the filesystems and the cards',
      len(_d.get('cores', [])) == os.cpu_count() and _d.get('filesystems') and all(c.get('busy') is not None for c in _d['cores']))

check('the load in the header is off until an account picks a look', "HLOAD.look = prefs().hload || 'off'" in open(os.path.join(HERE, 'web', 'assets', 'app.js')).read())

ai.server_load(); time.sleep(1.1); ai._load_keep(ai.server_load())
_h = ai.load_history()
check('the last two minutes of the load are kept for a page loaded again', bool(_h) and set(_h[-1]) >= {'at', 'cpu', 'mem', 'disk', 'net'})

# the perf meter's fixes of 1.0.79 (found in plexmon 2.7.1-2.7.3)
import tempfile as _tf2, shutil as _sh2
_fs2 = _tf2.mkdtemp()
def _w2(rel, txt):
    f = os.path.join(_fs2, rel); os.makedirs(os.path.dirname(f), exist_ok=True); open(f, 'w').write(txt)
# coretemp of package 0 with Core 0 and Core 1; 4 logical processors, two threads on each core
_w2('devices/platform/coretemp.0/x', ''); _w2('class/hwmon/hwmon1/name', 'coretemp\n')
os.symlink(os.path.join(_fs2, 'devices/platform/coretemp.0'), os.path.join(_fs2, 'class/hwmon/hwmon1/device'))
for _n, _lab, _t in ((2, 'Core 0', 50000), (3, 'Core 1', 60000)):
    _w2('class/hwmon/hwmon1/temp%d_label' % _n, _lab + '\n'); _w2('class/hwmon/hwmon1/temp%d_input' % _n, '%d\n' % _t)
for _c in range(os.cpu_count() or 1):
    _w2('devices/system/cpu/cpu%d/topology/core_id' % _c, '%d\n' % (_c % 2))
    _w2('devices/system/cpu/cpu%d/topology/physical_package_id' % _c, '0\n')
_was_sys2, ai.LOAD_SYS = ai.LOAD_SYS, _fs2

ai.LOAD_DETAIL.update(at=0.0, raw=None, out=None)
_cs = ai.load_detail()['cores']
check('every logical processor has its core\'s temperature (hyperthreading)',
      all(c['temp'] == (50.0 if c['n'] % 2 == 0 else 60.0) for c in _cs) and len(_cs) == (os.cpu_count() or 1))
ai.LOAD_SYS = _was_sys2; ai.LOAD_DETAIL.update(at=0.0, raw=None, out=None)
_sh2.rmtree(_fs2, ignore_errors=True)
check('free space is asked only of the kernel\'s own filesystems', 'nfs' not in ai.LOAD_FS_KINDS and
      'fuseblk' not in ai.LOAD_FS_KINDS and 'vfat' not in ai.LOAD_FS_KINDS and 'ext4' in ai.LOAD_FS_KINDS)
_appjs = open(os.path.join(HERE, 'web', 'assets', 'app.js')).read()
_indexphp = open(os.path.join(HERE, 'web', 'index.php')).read()
check('bars of the load: nothing at 0 %, the real share of a process', 'Math.max(2, Math.min(100, x[3]))' not in _appjs
      and 'hlBar(100 * v / top' not in _appjs and 'function hlWidth(pct)' in _appjs)

_src2 = open(os.path.join(HERE, 'ai.py')).read()
check('the performance meter can be switched off for the whole server', ai.DEFAULTS.get('perf_meter') is True and
      "if not CONFIG.get('perf_meter', True):" in _src2 and "($initial['perf_meter'] ?? true)" in
      open(os.path.join(HERE, 'web', 'index.php')).read())
check('a page with the meter off has no timer and asks nothing', "if (HLOAD.gone || (prefs().hload || 'off') === 'off') { hloadStop(); return; }"
      in open(os.path.join(HERE, 'web', 'assets', 'app.js')).read())

check('the load is read once every 5 s for every page, and the watching ends by itself', ai.LOAD_STEP_S == 5.0
      and ai.LOAD_WATCH_S == 45.0 and 'load_watch(c.daemon.store)' in _src2 and "'load:' + node_name()" in _src2)
check('the graphs slide by one animation of their SVG group, not redrawn on a timer', 'hl-slide' in _appjs and
      'setInterval(hloadTick, HLOAD_STEP * 1000)' in open(os.path.join(HERE, 'web', 'assets', 'app.js')).read())

check('a page coming back gets the last state at once, from the database', 'def load_saved(store):' in _src2
      and "out['stale'] = True" in _src2 and "'last': LOAD_LAST['out']" in _src2)

class _NStore:
    def __init__(s): s.m = {}; s.ev = []
    def get_meta(s, k, d=None): return s.m.get(k, d)
    def set_meta(s, k, v): s.m[k] = v
    def meta_json(s, k, d=None): import json as _j; return _j.loads(s.m[k]) if k in s.m else d
    def set_meta_json(s, k, v): import json as _j; s.m[k] = _j.dumps(v)
    def add_event(s, *a, **k): s.ev.append(a[1])
_ns, _was_vn = _NStore(), ai.VERSION_NOTICES
ai.VERSION_NOTICES = [{'since': ai.__version__, 'id': 'v-step', 'level': 'crit', 'title': 'a step', 'cli': 'ai --x'},
                      {'since': '0.0.1', 'id': 'v-old', 'level': 'warn', 'title': 'an old one'}]
ai.notices_version_sync(_ns)                     # a fresh install: none of them
_fresh = ai.notices_kept(_ns)
_ns.set_meta('notices:version', '1.0.1')
ai.notices_version_sync(_ns); ai.notices_version_sync(_ns)
_after = [n['id'] for n in ai.notices_kept(_ns)]
ai.notice_done(_ns, 'v-step', 'test')
check('a version adds what it needs done once, after an upgrade only, until said done',
      _fresh == [] and _after == ['v-step'] and ai.notices_kept(_ns) == [])
ai.VERSION_NOTICES = _was_vn

_cs = _NStore()
ai.notice_add(_cs, {'id': 'still', 'level': 'crit', 'title': 'still to do'})
for _i, _t in enumerate(('a', 'b', 'c')):
    _cs.set_meta_json('notices:done', [{'id': _t + str(_j), 'title': _t, 'how': 'done', 'at': 1000 + _j}
                                       for _j in range(_i + 1)] + (_cs.meta_json('notices:done', []) or []))
_shown = [[x['id'], x['at']] for x in ai.notices_done_list(_cs)][:2]
_gone = ai.notices_done_clear(_cs, _shown, 'test')
_left = len(_cs.meta_json('notices:done', []))
check('Clear empties exactly the rows the page shows, never what still waits', _gone == 2 and _left == 4
      and [n['id'] for n in ai.notices_kept(_cs)] == ['still'])
check('Clear without a list (the command line) empties all of it', ai.notices_done_clear(_cs, None) == 4
      and _cs.meta_json('notices:done', []) == [] and len(ai.notices_kept(_cs)) == 1)
check('the page has Clear only in the heading of Done lately, sending clear_done',
      "do: 'clear_done', items: done.map" in _appjs and "'nt-done-head'" in _appjs)

# ---- SELinux and the system's trusted roots (1.0.91): fake tools, fake folders ------------------
import subprocess as _sp
_SE = os.path.join(WORK, 'se'); _SB = os.path.join(_SE, 'bin'); os.makedirs(_SB)
def _tool(name, body):
    with open(os.path.join(_SB, name), 'w') as f:
        f.write('#!/bin/sh\n' + body.replace('@', _SE) + '\n')
    os.chmod(os.path.join(_SB, name), 0o755)
_tool('getenforce', 'cat @/mode')
_tool('setenforce', '[ "$1" = 1 ] && echo Enforcing > @/mode || echo Permissive > @/mode')
_tool('semodule', 'case "$1" in -l) cat @/modules 2>/dev/null; echo base;; -i) echo ai_server >> @/modules;; esac')
_tool('getsebool', 'grep -q "^$1$" @/bools 2>/dev/null && echo "$1 --> on" || echo "$1 --> off"')
_tool('setsebool', 'echo "$2" >> @/bools')
_tool('semanage', '[ "$2" = "-l" ] && { echo "http_port_t tcp 80, 443"; cat @/ports 2>/dev/null; exit 0; }; echo "$4 tcp $7" >> @/ports')
_tool('ausearch', 'cat @/avc 2>/dev/null; exit 0')
_tool('audit2why', 'cat; exit 0')
_tool('restorecon', 'echo \'{"' + str(ai.RUN_DIR) + '": "httpd_var_run_t", "' + str(ai.TOKEN_FILE) + '": "httpd_var_run_t", "/var/www/ai": "httpd_sys_content_t"}\' > @/labels')
_tool('update-ca-trust', 'cat @/anchors/*.pem > @/bundle.pem 2>/dev/null; echo x >> @/runs')
def _put(n, s):
    with open(os.path.join(_SE, n), 'w') as f:
        f.write(s)
_put('mode', 'Permissive\n'); _put('config', 'SELINUX=permissive\nSELINUXTYPE=targeted\n'); _put('cmdline', 'ro quiet\n')
_put('labels', json.dumps({str(ai.RUN_DIR): 'var_run_t', str(ai.TOKEN_FILE): 'var_run_t', '/var/www/ai': 'httpd_sys_content_t'}))
_put('avc', 'type=AVC msg=audit(1000.1:7): avc:  denied  { read } for  pid=9 comm="php-fpm" name="api-token" '
            'scontext=system_u:system_r:httpd_t:s0 tcontext=system_u:object_r:var_run_t:s0 tclass=file permissive=1\n')
_was_path = os.environ['PATH']
os.environ.update(PATH=_SB + ':' + _was_path, AI_SELINUX_LABELS=os.path.join(_SE, 'labels'), AI_SELINUX_AUDITD='active')
ai.SE_CONFIG, ai.SE_CMDLINE, ai.SE_RELABEL = (os.path.join(_SE, x) for x in ('config', 'cmdline', 'autorelabel'))
import shutil as _sh
ai.SE_CIL = os.path.join(_SE, 'ai_server.cil')
_sh.copyfile(os.path.join(HERE, 'deploy', 'ai_server.cil'), ai.SE_CIL)
_r = ai.selinux_want()
_c0 = ai.se_check(_r)
check('SELinux: permissive, nothing of ai\'s in - not ready, and why',
      _c0['mode'] == 'Permissive' and _c0['module'] is False and not _c0['ready'] and
      any('not installed' in x for x in _c0['problems']) and _c0['denials']['total'] == 1)
try:
    ai.se_do(dict(_r, do='enforce'))
    check('SELinux: enforcing refused while something is missing', False)
except ai.Refused as _e:
    check('SELinux: enforcing refused while something is missing - what is missing put in, never enforced at once',
          'is put in now' in str(_e) and open(os.path.join(_SE, 'mode')).read().strip() == 'Permissive'
          and ai.se_applied_at() > 0)
_put('modules', ''); _put('bools', ''); os.unlink(os.path.join(WORK, ai.SE_APPLIED))
_c1 = ai.se_do(dict(_r, do='prepare'))
check('SELinux: "put in what ai needs" - module, boolean, labels; old refusals no longer count',
      _c1['module'] is True and all(b['on'] for b in _c1['booleans']) and all(x['ok'] for x in _c1['labels'])
      and _c1['denials']['total'] == 0 and _c1['ready'])
_c2 = ai.se_do(dict(_r, do='enforce'))
check('SELinux: enforcing, now and in the configuration',
      _c2['mode'] == 'Enforcing' and 'SELINUX=enforcing' in open(ai.SE_CONFIG).read())
_c3 = ai.se_do(dict(_r, do='permissive'))
check('SELinux: back to permissive, the rest of the configuration as it was',
      _c3['mode'] == 'Permissive' and open(ai.SE_CONFIG).read() == 'SELINUX=permissive\nSELINUXTYPE=targeted\n')
_put('mode', 'Disabled\n')
_c4 = ai.se_do(dict(_r, do='prepare'))
check('SELinux: disabled made ready - permissive at the next start, every file labelled then',
      os.path.exists(ai.SE_RELABEL) and any('restart the machine' in x for x in _c4['said']))
try:
    ai.se_want_checked({'booleans': [{'name': 'allow_execmem'}]})
    check('SELinux: a boolean ai does not set is refused', False)
except ai.Refused:
    check('SELinux: a boolean ai does not set is refused', True)
_snot = _NStore()
_snot.set_meta_json('selinux:now', {'data': {'mode': 'Enforcing', 'problems': ['x is labelled y']}})
check('SELinux: enforcing with something missing is a notice for "To be done by hand"',
      (ai.selinux_notice(_snot) or {}).get('id') == 'selinux-needs' and "'selinux-needs'" in _appjs)

_A = os.path.join(_SE, 'anchors'); os.makedirs(_A, 0o755)
os.chmod(_A, 0o755)
os.environ.update(AI_OSROOTS_FLAVOUR='rhel', AI_OSROOTS_DIR=_A, AI_OSROOTS_BUNDLE=os.path.join(_SE, 'bundle.pem'),
                  AI_OSROOTS_EXTRACT=os.path.join(_SB, 'update-ca-trust'), AI_OSROOTS_PKG='echo ca-certificates-test')
def _ca(name, ext, days=365, sign=None):
    key, crt = os.path.join(_SE, name + '.key'), os.path.join(_SE, name + '.pem')
    if sign:
        _sp.run(['openssl', 'req', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', crt + '.csr', '-subj', '/CN=' + name],
                capture_output=True, check=True)
        with open(crt + '.ext', 'w') as f:
            f.write(ext.replace(',', '\n', 1) if False else 'basicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign\n')
        _sp.run(['openssl', 'x509', '-req', '-in', crt + '.csr', '-CA', sign + '.pem', '-CAkey', sign + '.key', '-CAcreateserial',
                 '-out', crt, '-days', str(days), '-extfile', crt + '.ext'], capture_output=True, check=True, cwd=_SE)
    else:
        _sp.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', crt, '-days', str(days),
                 '-subj', '/CN=' + name, '-addext', ext], capture_output=True, check=True)
    return open(crt).read()
_root = _ca('Test Root', 'basicConstraints=critical,CA:TRUE')
_int = _ca('Test Issuing', '', sign=os.path.join(_SE, 'Test Root'))
_leaf = _ca('www.test', 'basicConstraints=CA:FALSE')
_os = _NStore()
_got = ai.osr_check(_os, _leaf + _int)
check('trusted roots: a server\'s own certificate is not taken, an intermediate without its root is said',
      _got[0]['refused'] and not _got[1]['refused'] and any('without its root' in w for w in _got[1]['warn']))
try:
    ai.osr_check(_os, _root + '-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----\n')
    check('trusted roots: a private key refuses the whole text', False)
except ai.Refused:
    check('trusted roots: a private key refuses the whole text', True)
_add = ai.osr_add(_os, _root + _int, 'test')
_row = ai.osr_run(_os, ai.osr_want(_os))
_files = sorted(os.listdir(_A))
check('trusted roots: both written as ai-<sha16>.pem, the tool run once, in the system\'s list',
      len(_add['added']) == 2 and len(_files) == 2 and all(ai.OSR_NAME_RE.match(x) for x in _files)
      and open(os.path.join(_SE, 'runs')).read().count('x') == 1 and _row['ok']
      and all(x.get('in_bundle') for x in _row['state']['ours']))
with open(os.path.join(_A, 'company.pem'), 'w') as f:
    f.write(_leaf)
ai.osr_run(_os, ai.osr_want(_os))
check('trusted roots: nothing changed, the tool not run again; another\'s file shown, never touched',
      open(os.path.join(_SE, 'runs')).read().count('x') == 1 and os.path.exists(os.path.join(_A, 'company.pem'))
      and [o['file'] for o in ai.osr_view(_os)['nodes'][0]['others']] == ['company.pem'])
_fp_root = [c['fp'] for c in ai.osr_want(_os)['certs'] if c['kind'] == 'root'][0]
ai.osr_remove(_os, _fp_root[:12], 'test')
_row = ai.osr_run(_os, ai.osr_want(_os))
_v = ai.osr_view(_os)
check('trusted roots: one taken away - its file gone, the tool run, the view applied',
      len([x for x in os.listdir(_A) if x.startswith('ai-')]) == 1 and _v['nodes'][0]['status'] == 'applied'
      and open(os.path.join(_SE, 'runs')).read().count('x') == 2 and len(_v['certs']) == 1)
os.chmod(_A, 0o777)
_row = ai.osr_run(_os, {'certs': [{'pem': _root, 'fp': _fp_root}], 'hash': 'h', 'v': 1})
check('trusted roots: a folder others may write is never written into',
      not _row['ok'] and 'root\'s alone' in _row['error'])
os.chmod(_A, 0o755)
_parts = ai.se_report_parts(_r)
check('SELinux report: the processes with their domains, never an empty file',
      _parts['processes.txt'].startswith('LABEL') or 'rror' in _parts['processes.txt'])
os.environ['PATH'] = _was_path
check('the relay lets selinux and osroots through, and the panes are on the page',
      "'selinux' => '/api/selinux'" in _indexphp and "'osroots' => '/api/osroots'" in _indexphp
      and 'id="se-host"' in _indexphp and 'id="osr-host"' in _indexphp)

# ---- the whole chain sent (1.0.93): completed from "CA Issuers" as browsers do --------------------
_CH = os.path.join(WORK, 'chain'); os.makedirs(_CH)
def _ossl(*a):
    _sp.run(['openssl'] + list(a), capture_output=True, check=True, cwd=_CH)
_ossl('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'r.key', '-out', 'r.pem', '-days', '99', '-subj', '/CN=Chain Root',
      '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign')
_ossl('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'i.key', '-out', 'i.csr', '-subj', '/CN=Chain Issuing CA')
with open(os.path.join(_CH, 'i.ext'), 'w') as f:
    f.write('basicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign\nauthorityInfoAccess=caIssuers;URI:http://ca.test/r.der\n')
_ossl('x509', '-req', '-in', 'i.csr', '-CA', 'r.pem', '-CAkey', 'r.key', '-CAcreateserial', '-out', 'i.pem', '-days', '99', '-extfile', 'i.ext')
_ossl('req', '-newkey', 'rsa:2048', '-nodes', '-keyout', 'l.key', '-out', 'l.csr', '-subj', '/CN=www.chain.test')
with open(os.path.join(_CH, 'l.ext'), 'w') as f:
    f.write('basicConstraints=CA:FALSE\nsubjectAltName=DNS:www.chain.test\nauthorityInfoAccess=caIssuers;URI:http://ca.test/i.p7c\n')
_ossl('x509', '-req', '-in', 'l.csr', '-CA', 'i.pem', '-CAkey', 'i.key', '-CAcreateserial', '-out', 'l.pem', '-days', '99', '-extfile', 'l.ext')
_ossl('crl2pkcs7', '-nocrl', '-certfile', 'i.pem', '-outform', 'DER', '-out', 'i.p7c')
_ossl('x509', '-in', 'r.pem', '-outform', 'DER', '-out', 'r.der')
_rd = lambda n, m='r': open(os.path.join(_CH, n), m).read()
_bundle = os.path.join(_CH, 'system.pem')
with open(_bundle, 'w') as f:
    f.write(_rd('r.pem'))
os.environ['AI_CHAIN_ROOTS'] = _bundle
_asked = []
class _Got:
    def __init__(s, data): s.data = data
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def read(s, n=-1): return s.data
_was_open = ai.url_open
def _fake_open(req, timeout=30, context=None, purpose=''):
    _asked.append(req.full_url)
    return _Got(_rd(req.full_url.rsplit('/', 1)[1], 'rb'))
ai.url_open = _fake_open
_leaf = _rd('l.pem')
_c, _s = ai.chain_complete(_leaf, [], fetch=False)
check('chain: a certificate sent alone does not reach the system\'s root - the intermediate is named',
      not _s['ok'] and _s['missing'] == 'Chain Issuing CA')
_c, _s = ai.chain_complete(_leaf, [])
check('chain: completed from "CA Issuers" (PKCS#7) as browsers do - the root itself never sent',
      _s['ok'] and _s['fetched'] == ['Chain Issuing CA'] and len(_c) == 1 and _s['root'] == 'Chain Root'
      and _asked == ['http://ca.test/i.p7c'])
_asked[:] = []
_c, _s = ai.chain_complete(_leaf, [_rd('i.pem')])
check('chain: a whole chain sent is taken as it is, nothing fetched', _s['ok'] and not _s['fetched'] and not _asked)
with open(_bundle, 'w') as f:
    f.write('')
os.environ['AI_CHAIN_ROOTS'] = '/nonexistent'
_c, _s = ai.chain_complete(_leaf, [_rd('i.pem')], roots=_rd('r.pem'))
check('chain: a root of your own given with it is a private root', _s['ok'] and _s.get('private'))
os.environ['AI_CHAIN_ROOTS'] = _bundle
_c, _s = ai.chain_complete(_leaf, [])
check('chain: a root that is not the system\'s is said as such, not as a missing intermediate',
      not _s['ok'] and _s.get('root_missing') and _s['missing'] == 'Chain Root')
with open(_bundle, 'w') as f:
    f.write(_rd('r.pem'))
_prof = {'cert': _leaf, 'chain': '', 'info': ai.cert_info(_leaf)}
_said = []
ai.chain_fix_prof(_prof, _said, fetch=True)
_n = len(_asked)
ai.chain_fix_prof(_prof, [], fetch=True)
_prof2 = dict(_prof, chain='')
ai.chain_fix_prof(_prof2, [], fetch=True)
check('chain: kept with the profile, not fetched again - unless the same certificate comes again without its chain',
      _prof['chain'].count('BEGIN CERTIFICATE') == 1 and _prof['chain_state']['ok'] and len(_asked) == _n + 1
      and _prof2['chain'].count('BEGIN CERTIFICATE') == 1 and any('completed' in x for x in _said))
ai.url_open = _was_open
del os.environ['AI_CHAIN_ROOTS']
check('chain: the card says complete or incomplete, and offers Complete the chain',
      "'Complete the chain'" in _appjs and 'certChainWords' in _appjs and "action: 'tls_chain'" in _appjs)

check('chain: the certificate in place is looked at by itself, nginx touched only when a link is missing',
      'tls_chain_tick(self)' in open(os.path.join(HERE, 'ai.py')).read() and ai.CHAIN_LOOK_EVERY == 6 * 3600)

print('\n%d failed' % len(FAILS) if FAILS else '\nall fine')
sys.exit(1 if FAILS else 0)
