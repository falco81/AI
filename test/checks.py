#!/usr/bin/env python3
"""The parts of ai that can be checked without a server: run as
python3 test/checks.py - from the unpacked folder."""
import importlib.util
import json
import os
import sys
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

print('\n%d failed' % len(FAILS) if FAILS else '\nall fine')
sys.exit(1 if FAILS else 0)
