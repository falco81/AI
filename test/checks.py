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
print('\n%d failed' % len(FAILS) if FAILS else '\nall fine')
sys.exit(1 if FAILS else 0)
