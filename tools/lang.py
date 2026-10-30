#!/usr/bin/env python3
"""web/lang/cs.json, made from the Czech of otp's pages and ai's own words.

    python3 tools/lang.py OTP-cs.json

The panes and helpers taken from otp (core.js, system.js) say what otp's
pages say, so their Czech is otp's own (web/lang/cs.json of otp), with otp
written as ai. Only what the pages of ai really say is taken over. ai's own
words are in tools/cs_texts.py.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cs_texts  # noqa: E402


def as_ai(t):
    t = t.replace('OTP-IN', 'AI-IN')
    return re.sub(r'\botp\b', 'ai', t)


def haystack():
    out = []
    for rel in ('web/index.php', 'web/assets/core.js', 'web/assets/app.js', 'web/assets/term.js',
                'web/assets/system.js', 'web/assets/cols.js', 'web/assets/cc.js', 'web/assets/usage.js', 'ai.py'):
        with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
            out.append(f.read().replace("\\'", "'"))
    return ' '.join(' '.join(x.split()) for x in out)


def main(argv):
    otp = json.load(open(argv[0], encoding='utf-8')) if argv else {}
    hay = haystack()
    strings, patterns, rich = {}, {}, {}
    for e in (otp.get('strings') or {}).values():
        s, t = as_ai(e['source']), as_ai(e['text'])
        if t and ' '.join(s.split()) in hay:
            strings[s] = t
    for e in (otp.get('patterns') or {}).values():
        s, t = as_ai(e['source']), as_ai(e['text'])
        bits = [b.strip() for b in re.split(r'\{\d+\}', s) if len(b.strip()) > 2]
        if t and bits and all(b in hay for b in bits):
            patterns[s] = t
    for e in (otp.get('rich') or {}).values():
        s, t = as_ai(e['source']), as_ai(e['text'])
        bits = [b.strip() for b in re.split(r'<[^>]+>|\{\d+\}', s) if len(b.strip()) > 3]
        if t and bits and all(' '.join(b.split()) in hay for b in bits):
            rich[s] = t
    strings.update(cs_texts.STRINGS)
    patterns.update(cs_texts.PATTERNS)
    rich.update(cs_texts.RICH)
    out = {'_meta': {'code': 'cs', 'name': 'Čeština', 'english': 'Czech',
                     'about': 'Texty stránek ai v češtině. Měňte jen "text", nikdy "source". '
                              'Vzniká z tools/cs_texts.py a z češtiny stránek otp (tools/lang.py).'},
           'strings': {}, 'patterns': {}, 'rich': {}}
    for part, src, key in (('strings', strings, 's'), ('patterns', patterns, 'p'), ('rich', rich, 'r')):
        for i, s in enumerate(sorted(src, key=str.lower)):
            out[part]['%s%04d' % (key, i + 1)] = {'source': s, 'text': src[s]}
    with open(os.path.join(ROOT, 'web', 'lang', 'cs.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('cs.json: %d strings, %d patterns, %d rich' % (len(strings), len(patterns), len(rich)))


if __name__ == '__main__':
    main(sys.argv[1:])
