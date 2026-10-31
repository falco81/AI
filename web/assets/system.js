/* system.js - the server's own panes, taken whole from otp's administration
   pages (admin.js 1.0.161): Firewall and access, Network, Restart and power
   off, Time, SSH keys of root and System updates - the same cards, the same
   buttons, the same words. Here there is one node, this server; what was a
   cluster's is simply never drawn. */
'use strict';
var TOKADMIN = ADMIN;

/* ---- helpers of otp's, used by the panes below ------------------------------- */
function msect(title, lede, wide) {
  var box = el('section', 'msect' + (wide ? ' wide' : ''));
  box.appendChild(el('h4', '', title));
  if (lede) box.appendChild(el('p', 'msect-lede', lede));
  var body = el('div', 'msect-body');
  box.appendChild(body);
  box._body = body;
  return box;
}
function askThen(title, words, buttonWords, danger) {
  return new Promise(function (done) {
    var said = false;
    var end = function (v) { if (!said) { said = true; done(v); } };
    confirmThen(title, words, buttonWords, function () { end(true); }, danger);
    var gen = MODAL_GEN;
    var watch = setInterval(function () {
      if (said) { clearInterval(watch); return; }
      if ($('modal').hidden || MODAL_GEN > gen + 1) { clearInterval(watch); setTimeout(function () { end(false); }, 50); }
    }, 300);
  });
}
function paneLive(name) {
  return TAB === 'settings' && PANE === name && $('pane-' + name) && !$('pane-' + name).hidden;
}
function upBar(pc, kind, words, wide) {
  var box = el('div', 'going up-bar' + (wide ? ' wide' : '') + (kind ? ' ' + kind : ''));
  var bar = el('div', 'bar');
  var fill = el('span', '');
  fill.style.width = Math.max(0, Math.min(100, pc)) + '%';
  bar.appendChild(fill);
  box.appendChild(bar);
  if (words) box.appendChild(wide ? el('div', 'says', words) : noI18n(el('div', 'says', words)));
  return box;
}
function certProgress(p, target) {
  var box = el('div', 'cert-prog');
  var total = Number(p.total) || 6, step = Math.max(1, Number(p.step) || 1);
  var gone = Math.max(0, (Number(p.now) || 0) - (Number(p.at) || 0));
  var part = p.expect_s ? Math.min(0.95, gone / Number(p.expect_s)) : 0.5;
  var pct = Math.min(99, Math.round(((step - 1) + part) / total * 100));
  var head = el('div', 'cert-prog-h');
  head.appendChild(el('span', '', p.words || 'working'));
  head.appendChild(noI18n(el('b', '', pct + ' %')));
  box.appendChild(head);
  var bar = el('div', 'cert-prog-bar');
  var fill = el('span', '');
  fill.style.width = pct + '%';
  bar.appendChild(fill);
  box.appendChild(bar);
  var mm = function (sec) { sec = Math.round(sec); return Math.floor(sec / 60) + ':' + ('0' + (sec % 60)).slice(-2); };
  box.appendChild(el('div', 'cert-prog-s', p.expect_s
    ? 'on ' + target + ' - ' + mm(gone) + ' so far, usually about ' + Math.round(p.expect_s / 60 || 1) + ' min'
    : 'on ' + target + ' - step ' + step + ' of ' + total));
  return box;
}
function tlsRow(words, says, control) {
  var row = el('div', 'arow');
  var t = el('div', 'arow-t');
  t.appendChild(el('div', 'arow-k', words));
  t.appendChild(el('div', 'arow-s', says));
  row.appendChild(t);
  var c = el('div', 'arow-c');
  c.appendChild(control);
  row.appendChild(c);
  return row;
}
function txT(s) {
  var got = typeof i18nText === 'function' ? i18nText(String(s)) : null;
  return got == null ? String(s) : got;      /* untranslated, or English: as it is */
}
function rbCopyme(text, said) {
  var code = noI18n(el('code', 'copyme', text));
  explain(code, 'Click to copy.');
  code.onclick = function () { copyText(text, code, said || 'Copied'); };
  return code;
}
function rbPanel(note) {
  var box = el('div', 'subpanel rb-panel');
  var p = el('p', 'note');
  p.innerHTML = note;
  box.appendChild(p);
  var row = el('div', 'btnrow');
  box.appendChild(row);
  var below = el('div', 'rb-below');
  box.appendChild(below);
  return {box: box, row: row, below: below};
}
/* ---- Firewall and access (1.0.52) ---------------------------------------------------
   Who may reach which pages (nginx, page by page) and the machine's firewall:
   ai's own chain AI-IN, the rules of your own first, then what ai's
   functions need. Every node puts it in through its root helper. */
var FW = {last: null, timer: null, node: null, fam: '4', draft: null, dirty: false};
/* Changes wait for the save bar (1.0.54), as everywhere else in Settings:
   what is shown is the draft, the nodes' state comes live. */
function fwFromServer(d) {
  return JSON.parse(JSON.stringify({on: !!d.conf.on, off: d.conf.off || [], rules: d.conf.rules || [],
                                    access: d.access, access_changed: false}));
}
function fwDirty() {
  fwMarkBar();
  if (FW.last) drawFw(FW.last);
}
function fwPending() {
  pendingSet('fw', {save: fwSave, reset: function () { FW.dirty = false; FW.draft = null; loadFw(); }});
}
function fwMarkBar() {
  if (!FW.dirty) FW.dirty = true;
  FW.ver = (FW.ver || 0) + 1;
  fwPending();
}
function fwSave() {
  if (!FW.draft) return Promise.resolve(true);
  var dr = FW.draft, was = FW.last ? !!FW.last.conf.on : false, ver = FW.ver;
  var go = function () {
    var body = {action: 'save', on: dr.on, off: dr.off, rules: dr.rules};
    if (dr.access_changed) body.access = dr.access;
    return api('firewall', body).then(function (x) {
      toast(x.message, 'good');
      /* Changed while it was being saved: kept, still to be saved (1.0.57). */
      if (FW.ver !== ver) return false;
      FW.dirty = false; FW.draft = null;
      loadFw();
      return true;
    });
  };
  var ask = Promise.resolve(true);
  if (dr.on && !was) {
    ask = askThen('Let ai look after the firewall',
      'ai puts a chain of its own, AI-IN, first in INPUT on every node, for IPv4 and IPv6, and keeps it in /etc/sysconfig/iptables and ip6tables. Your own rules stay as they are; AI-IN only lets in - what it does not let in goes on to them. SSH stays open (a rule of ai\'s, which you can turn off).',
      'Turn it on', false);
  } else if (!dr.on && was) {
    ask = askThen('Take ai\'s rules away', 'The chain AI-IN and its jump go, on every node; the rest of the firewall stays exactly as it is. ' +
      'Whatever only AI-IN let in (SSH, the pages) is then up to your own rules.', 'Take them away');
  }
  return ask.then(function (yes) { return yes ? go() : false; });
}
function loadFw() {
  if (!TOKADMIN) {
    /* The map of the network is not for every reader (1.0.57); said here once,
       not refused every five seconds (1.0.146). */
    var lede = $('fw-lede');
    if (lede) lede.textContent = 'The firewall and who may reach the pages are shown to administrators only.';
    return;
  }
  apiLatest('fw', 'firewall').then(drawFw).catch(oops);     /* the newest only (1.0.61) */
  clearInterval(FW.timer);
  FW.timer = setInterval(function () {
    if (!paneLive('fw')) { clearInterval(FW.timer); return; }
    if (document.hidden) return;
    if ($('modal') && !$('modal').hidden) return;
    apiLatest('fw', 'firewall').then(function (d) { liveRun(function () { drawFw(d); }); }).catch(function () {});
  }, 5000);
}
function fwFam(f) {
  f = Number(f) || 0;
  return noI18n(el('span', 'fam fam' + (f || 'x'), f ? 'IPv' + f : 'IPv4 + IPv6'));
}
function fwWhat(r) {
  var proto = r.proto === 'any' ? 'everything' : (r.proto === 'icmp' && Number(r.family) === 6 ? 'ICMPv6' : r.proto.toUpperCase());
  return proto + (r.port ? ' ' + r.port : '');
}
function fwAction(a) {
  return el('span', 'fwact fwact-' + a, {accept: 'ACCEPT', drop: 'DROP', reject: 'REJECT'}[a] || a);
}
function fwRuleLine(r) {
  var line = el('div', 'fw-rl');
  line.appendChild(fwFam(r.family));
  line.appendChild(noI18n(el('code', 'fw-what', fwWhat(r))));
  line.appendChild(el('span', 'fw-from', r.source ? 'from ' : 'from anywhere'));
  if (r.source) line.lastChild.appendChild(noI18n(el('code', '', r.source)));
  return line;
}

function drawFw(d) {
  FW.last = d;
  if (!FW.dirty || !FW.draft) FW.draft = fwFromServer(d);
  var dr = FW.draft;
  if (FW.dirty) fwPending();
  /* What is drawn is the draft; the auto rules follow what is turned off in it. */
  d = Object.assign({}, d, {conf: Object.assign({}, d.conf, {on: dr.on, off: dr.off, rules: dr.rules}), access: dr.access});
  d.nodes = d.nodes.map(function (n) {
    return Object.assign({}, n, {auto: (n.auto || []).map(function (a) {
      return Object.assign({}, a, {on: a.fixed || dr.off.indexOf(a.key) < 0});
    })});
  });
  if (!FW.node || !d.nodes.some(function (n) { return n.name === FW.node; })) {
    FW.node = (d.nodes.filter(function (n) { return n.me; })[0] || d.nodes[0] || {}).name;
  }
  drawFwAccess(d);
  /* The switch: ai looks after its rules, or leaves the firewall alone. */
  liveFill($('fw-master'), function (master) {
  var sw = switchBox(d.conf.on);
  sw.classList.add('big');
  sw._input.disabled = !d.may;
  sw._input.onchange = function () { FW.draft.on = !!sw._get(); fwDirty(); };
  var lab = el('label', 'fw-master');
  lab.appendChild(sw);
  lab.appendChild(el('span', '', d.conf.on ? 'ai looks after its rules' : 'ai leaves the firewall alone'));
  master.appendChild(lab);
  });
  $('fw-lede').textContent = d.conf.on
    ? 'In INPUT first: the chain AI-IN - your own rules in their order, then what ai\'s functions need. What it does not let in goes on to the rules that were there before.'
    : 'Off: nothing is changed in the firewall. Turned on, what ai\'s functions need is let in by itself, and the rules of your own with it.';
  /* The nodes, each with what its root says. */
  var nodes = $('fw-nodes');
  liveFill(nodes, function (nodes) {
  d.nodes.forEach(function (n) {
    var b = el('button', 'fw-node' + (n.name === FW.node ? ' on' : ''));
    b.type = 'button';
    var top = el('div', 'fw-node-top');
    top.appendChild(noI18n(el('b', '', n.name)));
    if (n.me) top.appendChild(el('span', 'tag dim', 'this one'));
    b.appendChild(top);
    var be = (n.fw || {}).backend;
    var st = el('div', 'fw-node-s');
    var tone, words;
    if (!n.alive) { tone = 'crit'; words = 'not answering'; }
    else if (be === 'firewalld' && n.current) { tone = 'ok'; words = d.conf.on ? 'in place (firewalld)' : 'nothing of ai\'s'; }
    else if (n.progress) { tone = 'warn'; words = 'putting it in…'; }
    else if (n.state === 'failed' && !n.current) { tone = 'crit'; words = 'failed - see below'; }
    else if (n.waiting || !n.current) { tone = 'warn'; words = 'waiting for root'; }
    else { tone = 'ok'; words = d.conf.on ? 'in place' : 'nothing of ai\'s'; }
    st.appendChild(el('span', 'dot ' + tone));
    st.appendChild(el('span', '', words));
    b.appendChild(st);
    if (n.address) b.appendChild(noI18n(el('div', 'fw-node-a', n.address)));
    b.onclick = function () { FW.node = n.name; drawFw(FW.last); };
    nodes.appendChild(b);
  });
  });
  nodes.hidden = d.nodes.length < 2;
  drawFwBody(d);
  explainWhatWasDrawn($('pane-fw'));
}

function drawFwAccess(d) {
  var host = $('fw-access');
  liveFill(host, function (host) {
  var st = {};
  var rows = el('div', 'fw-acc');
  var me = d.nodes.filter(function (n) { return n.name === FW.node; })[0] || d.nodes[0] || {};
  var inner = (d.inner || {})[me.name] || [];
  [['pages', 'The pages', 'https://…/ - the terminals, the files and these settings', 'gear']].forEach(function (p) {
    var acc = FW.draft.access;
    if (!acc[p[0]]) acc[p[0]] = {any: true, from: []};
    st[p[0]] = acc[p[0]];
    st[p[0]].any = !!st[p[0]].any;
    st[p[0]].from = (st[p[0]].from || []).slice();
    var row = el('div', 'fw-acc-row');
    var t = el('div', 'fw-acc-t');
    t.appendChild(el('b', '', p[1]));
    t.appendChild(el('div', 'arow-s', p[2]));
    row.appendChild(t);
    var c = el('div', 'fw-acc-c');
    var seg = el('div', 'seg');
    var box = el('textarea', 'mono fw-nets');
    box.rows = 2; box.spellcheck = false;
    box.placeholder = '10.0.0.0/8, 192.168.10.0/24, 2001:db8::/32';
    box.value = st[p[0]].from.join(', ');
    box.disabled = !d.may;
    box.oninput = function () {
      st[p[0]].from = box.value.split(/[\s,;]+/).filter(Boolean);
      FW.draft.access_changed = true; FW.dirty = true; fwMarkBar();
    };
    [[true, 'Everybody'], [false, 'Only from']].forEach(function (o) {
      var b = el('button', '', o[1]);
      b.type = 'button';
      b.disabled = !d.may;
      b.onclick = function () {
        st[p[0]].any = o[0];
        Array.prototype.forEach.call(seg.children, function (x) { x.classList.toggle('on', x === b); });
        box.hidden = o[0];
        FW.draft.access_changed = true; FW.dirty = true; fwMarkBar();
      };
      if (st[p[0]].any === o[0]) b.classList.add('on');
      seg.appendChild(b);
    });
    box.hidden = st[p[0]].any;
    c.appendChild(seg);
    c.appendChild(box);
    row.appendChild(c);
    rows.appendChild(row);
  });
  host.appendChild(rows);
  var foot = el('div', 'fw-acc-foot');
  var always = el('div', 'fw-always');
  always.appendChild(el('span', 'arow-s', 'Always let in:'));
  ['127.0.0.1', '::1'].concat(inner.filter(function (a) { return a !== '127.0.0.1' && a !== '::1'; })).forEach(function (a) { always.appendChild(noI18n(el('code', 'cchip', a))); });
  foot.appendChild(always);
  if (d.access.from_nginx && !FW.draft.access_changed) foot.appendChild(el('span', 'tag dim', 'as install.sh wrote it - not set here yet'));
  host.appendChild(foot);
  });
}

function drawFwBody(d) {
  var body = $('fw-body');
  liveFill(body, function (body) {
  var n = d.nodes.filter(function (x) { return x.name === FW.node; })[0] || {};
  var fw = n.fw || {};
  if (fw.backend === 'firewalld') {
    body.appendChild(el('p', 'note', 'firewalld looks after the firewall of ' + n.name + ': ai puts its rules in as rich rules of the default zone, and takes them away again; whatever else the zone allows stays as it is.'));
  } else if (fw.backend === 'ufw') {
    body.appendChild(el('p', 'note warn', 'ufw looks after the firewall of ' + n.name + ': ai leaves it to it. Change it with ufw, or switch it off (ufw disable) to manage it here.'));
  } else if (fw.backend === '' && n.state) {
    body.appendChild(el('p', 'note warn', 'There is no iptables on ' + n.name + '.'));
  }
  if (n.progress) body.appendChild(certProgress(n.progress, n.name));
  if (n.state === 'failed' && (n.said || []).length) {
    var bad = el('div', 'note bad');
    bad.appendChild(el('b', '', 'Root on ' + n.name + ' did not put it in: '));
    bad.appendChild(noI18n(el('span', '', n.said[n.said.length - 1])));
    if (d.may) {
      var again = cmdButton('Try again', 'refresh', 'small');
      again.onclick = function () { api('web', {action: 'retry', node: n.name}).then(function (x) { toast(x.message, 'good'); }).catch(oops); };
      bad.appendChild(again);
    }
    body.appendChild(bad);
  }
  /* How a packet goes: one line, so the order is plain. */
  var flow = el('div', 'fw-flow' + (d.conf.on ? '' : ' off'));
  [['INPUT', ''], ['your rules', 'mine'], ['what ai needs', 'auto'], ['the rest of INPUT', 'rest']].forEach(function (s, i) {
    if (i) flow.appendChild(el('span', 'fw-arrow', '→'));
    flow.appendChild(el('span', 'fw-step ' + s[1], s[0]));
  });
  body.appendChild(flow);

  /* Your own rules. */
  var h1 = el('div', 'fw-h');
  h1.appendChild(el('h3', '', 'Rules of your own'));
  if (d.may) {
    var add = cmdButton('Add a rule', 'add', 'small primary');
    add.onclick = function () { fwRuleEdit(d, null); };
    h1.appendChild(add);
  }
  body.appendChild(h1);
  body.appendChild(el('p', 'note', 'Looked at in this order, first: a DROP or REJECT here wins over what ai lets in below.'));
  var mine = (d.conf.rules || []);
  body.appendChild(listTable(['', 'Action', 'IP', 'What', 'From', 'Node', 'Note', ''], mine, function (r, i) {
    var tr = el('tr', r.disabled ? 'dim' : '');
    tr.appendChild(el('td', 'num muted', String(i + 1)));
    var a = el('td'); a.appendChild(fwAction(r.action)); tr.appendChild(a);
    var f = el('td'); f.appendChild(fwFam(r.family)); tr.appendChild(f);
    tr.appendChild(noI18n(el('td', 'mono', fwWhat(r))));
    tr.appendChild(r.source ? noI18n(el('td', 'mono', r.source)) : el('td', 'muted', 'anywhere'));
    var sc = el('td'); sc.appendChild(r.scope === 'all' ? el('span', 'tag dim', 'all nodes') : noI18n(el('span', 'tag', r.scope))); tr.appendChild(sc);
    tr.appendChild(noI18n(el('td', 'muted', r.note || '')));
    var tools = el('td', 'acts');
    if (d.may) {
      var up = iconButton('up', 'Earlier'); up.disabled = i === 0;
      up.onclick = function () { fwMove(i, -1); };
      var dn = iconButton('down', 'Later'); dn.disabled = i === mine.length - 1;
      dn.onclick = function () { fwMove(i, 1); };
      var ed = iconButton('edit', 'Change it'); ed.onclick = function () { fwRuleEdit(d, r); };
      var rm = iconButton('trash', 'Take it away');
      rm.onclick = function () { FW.draft.rules.splice(i, 1); fwDirty(); };
      [up, dn, ed, rm].forEach(function (b) { tools.appendChild(b); });
    }
    tr.appendChild(tools);
    return tr;
  }, 'plain fw-table|None yet - ai\'s own rules below are enough for what it does'));

  /* What ai lets in by itself, on this node. */
  var h2 = el('div', 'fw-h');
  h2.appendChild(el('h3', '', 'What ai lets in by itself'));
  h2.appendChild(noI18n(el('span', 'tag dim', n.name || '')));
  body.appendChild(h2);
  body.appendChild(el('p', 'note', 'Worked out from what is set up, and changed with it. What keeps the pages reachable from this machine cannot be turned off.'));
  var grid = el('div', 'fw-auto');
  (n.auto || []).forEach(function (item) {
    var card = el('div', 'fw-auto-card' + (item.on ? '' : ' off'));
    var top = el('div', 'fw-auto-top');
    var t = el('div', '');
    t.appendChild(el('b', '', item.title));
    t.appendChild(el('div', 'arow-s', item.why));
    top.appendChild(t);
    if (item.fixed) {
      top.appendChild(el('span', 'tag ok', 'always'));
    } else {
      var sw = switchBox(item.on);
      sw._input.disabled = !d.may;
      sw._input.onchange = function () {
        var off = FW.draft.off.filter(function (k) { return k !== item.key; });
        if (!sw._get()) off.push(item.key);
        FW.draft.off = off;
        fwDirty();
      };
      top.appendChild(sw);
    }
    card.appendChild(top);
    var list = el('div', 'fw-auto-rules');
    if (!item.rules.length) list.appendChild(el('span', 'muted', item.key === 'radius' ? 'no RADIUS client yet' : 'nothing'));
    item.rules.slice(0, 12).forEach(function (r) { list.appendChild(fwRuleLine(r)); });
    if (item.rules.length > 12) list.appendChild(el('span', 'muted', '… and ' + (item.rules.length - 12) + ' more'));
    card.appendChild(list);
    grid.appendChild(card);
  });
  body.appendChild(grid);

  /* Everything else: read only. */
  var other = el('details', 'fw-other');
  other.appendChild(el('summary', '', 'The whole firewall on ' + (n.name || 'this node') + ' (read only)'));
  var seg = el('div', 'seg');
  var pre = noI18n(el('pre', 'fw-pre'));
  /* All of it (1.0.67): every chain of the filter table as iptables-save
     shows it, AI-IN's lines marked - root reads it after every change,
     and again when asked. Where it has not been read yet, INPUT alone. */
  var full = fw.full || null, now = fw.now || {};
  var paint = function () {
    var lines = full ? (full[FW.fam] || []) : (now[FW.fam] || []);
    clear(pre);
    if (!lines.length) pre.textContent = '(nothing - or not known yet)';
    lines.forEach(function (line, i) {
      var ours = /AI-IN/.test(line);
      var sp = el('span', ours ? 'fw-line fw-ours' : 'fw-line', line);
      pre.appendChild(sp);
      if (i < lines.length - 1) pre.appendChild(document.createTextNode('\n'));
    });
    Array.prototype.forEach.call(seg.children, function (x) { x.classList.toggle('on', x.dataset.f === FW.fam); });
  };
  [['4', 'IPv4 (iptables)'], ['6', 'IPv6 (ip6tables)']].forEach(function (o) {
    var b = el('button', '', o[1]); b.type = 'button'; b.dataset.f = o[0];
    b.onclick = function () { FW.fam = o[0]; paint(); };
    seg.appendChild(b);
  });
  other.appendChild(seg);
  other.appendChild(pre);
  var foot = el('p', 'note');
  foot.appendChild(document.createTextNode(full
    ? 'The filter table as iptables-save shows it, read ' + (fw.full_at ? ago(fw.full_at) : '?') + '. The marked lines are ai\'s (the chain AI-IN and the jump to it); the rest are yours, and ai never changes them. '
    : 'INPUT as iptables-save shows it, without AI-IN. These lines are yours: ai never changes them. '));
  /* The other node's too (1.0.71): asked through the database, root there
     reads it and it comes back in a few seconds. */
  if (n.me || n.alive) {
    var again = el('a', 'fgo', 'Read it again');
    again.onclick = function () {
      again.textContent = 'reading…';
      api('firewall&fresh=' + encodeURIComponent(n.me ? '1' : n.name), undefined, 30).then(function (d) {
        FW.otherOpen = true; drawFw(d);
      }).catch(oops);
    };
    foot.appendChild(again);
  }
  other.appendChild(foot);
  paint();
  if (FW.otherOpen) other.open = true;
  other.ontoggle = function () { FW.otherOpen = other.open; };
  body.appendChild(other);
  });
}

function fwMove(i, dir) {
  var list = FW.draft.rules, j = i + dir;
  if (j < 0 || j >= list.length) return;
  var t = list[i]; list[i] = list[j]; list[j] = t;
  fwDirty();
}
function fwRuleEdit(d, r) {
  var st = Object.assign({family: 0, proto: 'tcp', port: '', source: '', action: 'accept', scope: 'all', note: '', disabled: false}, r || {});
  modal(r ? 'Change the rule' : 'A rule of your own', function (body) {
    var rows = el('div', 'tls-rows');
    var segOf = function (opts, key, after) {
      var seg = el('div', 'seg');
      opts.forEach(function (o) {
        var b = el('button', '', o[1]); b.type = 'button';
        b.onclick = function () { st[key] = o[0]; Array.prototype.forEach.call(seg.children, function (x) { x.classList.toggle('on', x === b); }); if (after) after(); };
        if (String(st[key]) === String(o[0])) b.classList.add('on');
        seg.appendChild(b);
      });
      return seg;
    };
    rows.appendChild(tlsRow('Action', 'ACCEPT lets it in; DROP says nothing; REJECT answers that it is closed.',
      segOf([['accept', 'Accept'], ['drop', 'Drop'], ['reject', 'Reject']], 'action')));
    rows.appendChild(tlsRow('IP version', 'Taken from the address when one is given.',
      segOf([[0, 'Both'], [4, 'IPv4'], [6, 'IPv6']], 'family')));
    var port = textBox('', '', 'mono'); port.value = st.port; port.placeholder = '443 · 8000-8100 · 80,443';
    port.oninput = function () { st.port = port.value.trim(); };
    var portRow = tlsRow('Port', 'One, a range, or several by commas. Empty: every port.', port);
    var paintPort = function () { portRow.classList.toggle('dim', ['tcp', 'udp'].indexOf(st.proto) < 0); port.disabled = ['tcp', 'udp'].indexOf(st.proto) < 0; if (port.disabled) { port.value = ''; st.port = ''; } };
    rows.appendChild(tlsRow('Protocol', '', segOf([['tcp', 'TCP'], ['udp', 'UDP'], ['icmp', 'ICMP'], ['vrrp', 'VRRP'], ['any', 'Any']], 'proto', paintPort)));
    rows.appendChild(portRow);
    var src = textBox('', '', 'mono'); src.value = st.source; src.placeholder = '192.0.2.0/24 · 2001:db8::/32 · empty = anywhere';
    src.oninput = function () { st.source = src.value.trim(); };
    rows.appendChild(tlsRow('From', 'An address or a network.', src));
    var scope = selectBox([['all', 'All nodes']].concat(d.nodes.map(function (n) { return [n.name, n.name + (n.me ? ' (this one)' : '')]; })), st.scope);
    scope.onchange = function () { st.scope = scope.value; };
    rows.appendChild(tlsRow('On', 'Every node, or only one.', scope));
    var note = textBox('', ''); note.value = st.note; note.placeholder = 'Zabbix agent'; note.maxLength = 80;
    note.oninput = function () { st.note = note.value; };
    rows.appendChild(tlsRow('Note', 'Shown here and as the comment of the rule in iptables.', note));
    var dis = switchBox(!st.disabled);
    dis._input.onchange = function () { st.disabled = !dis._get(); };
    rows.appendChild(tlsRow('In force', 'Off keeps it here without putting it in.', dis));
    body.appendChild(rows);
    paintPort();
  }, [{words: 'Cancel', close: true},
      {words: r ? 'Change it' : 'Add it', cls: 'primary', icon: 'check', go: function (b) {
        /* Checked by the daemon now, kept in the draft until Save (1.0.54). */
        busy(b, true);
        api('firewall', {action: 'rule_check', rule: st}).then(function (x) {
          var got = Object.assign({}, x.rule, {id: r ? r.id : 'n' + Date.now().toString(36)});
          var list = FW.draft.rules;
          var i = r ? list.findIndex(function (y) { return y.id === r.id; }) : -1;
          if (i >= 0) list[i] = got; else list.push(got);
          closeModal(); fwDirty();
        }).catch(oops).then(function () { busy(b, false); });
      }}], 'medium');
}

/* ---- Settings → Network (1.0.119) ---------------------------------------------
   Each node's network as it says it is, a form for the new one, and the change
   followed step by step - through whichever node answers the page. */
var NET = {d: null, node: '', poll: null, fails: 0, failSince: 0, watch: '', redirect: null};
function loadNet() {
  api('net').then(function (d) {
    NET.d = d; NET.fails = 0;
    if (!NET.node || !d.nodes.some(function (n) { return n.name === NET.node; })) NET.node = (d.nodes[0] || {}).name;
    drawNet();
    netPollFor();
  }).catch(oops);
}
function netJobActive(j) { return j && ['asked', 'running', 'rebooting'].indexOf(j.state) >= 0; }
function netPollFor() {
  var busy = NET.d && NET.d.nodes.some(function (n) { return netJobActive(n.job); });
  if ((busy || NET.watch) && !NET.poll) NET.poll = setInterval(netPoll, 2000);
  if (!busy && !NET.watch && NET.poll) { clearInterval(NET.poll); NET.poll = null; }
}
function netPoll() {
  if (TAB !== 'settings' || PANE !== 'network') { clearInterval(NET.poll); NET.poll = null; return; }
  api('net').then(function (d) {
    NET.d = d; NET.fails = 0; NET.failSince = 0;
    var n = d.nodes.filter(function (x) { return x.name === NET.watch; })[0];
    if (NET.watch && n && n.job && ['done', 'failed'].indexOf(n.job.state) >= 0) {
      toast(n.job.state === 'done' ? 'the network of ' + n.name + ' is changed' : 'the network of ' + n.name + ' was not changed', n.job.state === 'done' ? 'good' : 'bad');
      NET.watch = '';
    }
    drawNet(true);
    netPollFor();
  }).catch(function () {
    /* The page's own node restarting: it does not answer for a while. */
    NET.fails += 1;
    if (!NET.failSince) NET.failSince = Date.now();
    drawNetAway();
  });
}
function netNodeOf(name) { return ((NET.d && NET.d.nodes) || []).filter(function (n) { return n.name === name; })[0]; }
function drawNet(live) {
  var real = $('net-host');
  if (!real || !NET.d) return;
  liveFill(real, function (host) {
  var d = NET.d;
  if (d.cluster) {
    var seg = el('div', 'seg net-nodes');
    d.nodes.forEach(function (n) {
      var b = el('button', n.name === NET.node ? 'on' : '');
      b.type = 'button';
      b.appendChild(el('span', 'dot ' + (n.alive ? 'ok' : 'bad')));
      b.appendChild(noI18n(el('span', '', ' ' + n.name)));
      if (n.me) b.appendChild(el('span', 'tag info', 'this page'));
      b.onclick = function () { NET.node = n.name; drawNet(); };
      seg.appendChild(b);
    });
    host.appendChild(seg);
  }
  var n = netNodeOf(NET.node);
  if (!n) return;
  if (n.job && n.job.state && (netJobActive(n.job) || NET.watch === n.name || Date.now() / 1000 - (n.job.moved || 0) < 900))
    host.appendChild(netProgressCard(n));
  host.appendChild(netNowCard(n));
  if (!netJobActive(n.job)) host.appendChild(netFormCard(n));
  }, live, function () { explainWhatWasDrawn(real); });
}
function netFacts(rows) {
  var dl = el('div', 'net-facts');
  rows.forEach(function (r) {
    if (r[1] === undefined) return;
    var one = el('div', 'net-fact');
    one.appendChild(el('span', 'k', r[0]));
    var v = el('span', 'v' + (r[2] ? ' mono' : ''));
    if (r[1] instanceof Node) v.appendChild(r[1]); else v.textContent = r[1] === '' || r[1] === null ? '–' : String(r[1]);
    if (r[2]) noI18n(v);
    one.appendChild(v);
    dl.appendChild(one);
  });
  return dl;
}
function netNowCard(n) {
  var card = el('div', 'card full');
  var h = el('h2', '', 'As it is now');
  var right = el('span', 'right');
  var re = cmdButton('Read it again', 'refresh', 'small');
  re.onclick = function () {
    busy(re, true);
    api('net', {action: 'read', node: n.name}).then(function (d) { NET.d = d; setTimeout(loadNet, n.me ? 0 : 6000); toast(n.me ? 'read' : n.name + ' says it again within a few seconds', 'good'); })
      .catch(oops).then(function () { busy(re, false); });
  };
  right.appendChild(re);
  h.appendChild(right);
  card.appendChild(h);
  var now = n.now || {};
  var data = now.data || {};
  if (!data.devices && !data.live) {
    card.appendChild(el('p', 'note', n.alive ? n.name + ' has not said what its network is yet - Read it again.' : n.name + ' is not answering.'));
    return card;
  }
  var conf = data.conf || {};
  var live = data.live || {};
  var v6 = (live.addrs6 || []).map(function (a) { return a.addr; });
  card.appendChild(netFacts([
    ['Host name', data.hostname || '', true],
    ['Connection', (data.con || '–') + (data.dev ? ' (' + data.dev + ')' : ''), true],
    ['IPv4 address', (conf.ipv4_addresses || []).join(', ') || (live.addrs4 || []).map(function (a) { return a.addr; }).join(', '), true],
    ['Gateway', conf.ipv4_gateway || live.gw4 || '', true],
    ['DNS servers', ((conf.ipv4_dns || []).concat(conf.ipv6_dns || [])).join(', ') || (live.dns || []).join(', '), true],
    ['Search domains', (conf.ipv4_search || []).join(', '), true],
    ['IPv6', conf.ipv6_method === 'disabled' || conf.ipv6_method === 'ignore' || !conf.ipv6_method ? 'off' : (conf.ipv6_method === 'manual' ? 'on, set by hand' : 'on, automatic')],
    ['IPv6 addresses', v6.join(', '), true],
    ['Read', now.at ? ago(now.at) : '']
  ]));
  if (!data.nm) card.appendChild(el('p', 'note warn', 'NetworkManager (nmcli) is not on ' + n.name + ': its network can only be set by hand there.'));
  return card;
}
function netFormCard(n) {
  var card = el('div', 'card full');
  card.appendChild(el('h2', '', 'New settings for ' + n.name));
  var data = (n.now || {}).data || {};
  var conf = data.conf || {};
  var live = data.live || {};
  if (!data.nm) { card.appendChild(el('p', 'note', 'Nothing can be set from here without NetworkManager.')); return card; }
  var on6was = !(conf.ipv6_method === 'disabled' || conf.ipv6_method === 'ignore' || !conf.ipv6_method);
  var host = textBox(data.hostname || '', 'ai.example.cz', 'mono');
  var a4Was = (conf.ipv4_addresses || [])[0] || ((live.addrs4 || [])[0] || {}).addr || '';
  var a4 = textBox(a4Was, '192.0.2.10/24', 'mono');
  var gw = textBox(conf.ipv4_gateway || live.gw4 || '', '192.0.2.1', 'mono');
  var dns = textBox((conf.ipv4_dns || live.dns || []).filter(function (x) { return x.indexOf(':') < 0; }).join(', '), '192.0.2.53, 192.0.2.54', 'mono');
  var search = textBox((conf.ipv4_search || []).join(', '), 'example.cz', 'mono');
  var s6 = switchBox(on6was);
  var mode6 = selectBox([['manual', 'set by hand'], ['auto', 'automatic (SLAAC / DHCPv6)']], conf.ipv6_method === 'auto' ? 'auto' : 'manual');
  var a6 = textBox((conf.ipv6_addresses || [])[0] || '', '2001:db8::10/64', 'mono');
  var gw6 = textBox(conf.ipv6_gateway || '', '2001:db8::1', 'mono');
  var dns6 = textBox((conf.ipv6_dns || []).join(', '), '2001:db8::53', 'mono');
  var cons = (data.devices || []).filter(function (x) { return x.con; });
  var con = selectBox(cons.map(function (x) { return [x.con, x.con + ' (' + x.dev + ')']; }), data.con);
  var g1 = el('div', 'formgrid');
  g1.appendChild(formField('Host name (FQDN)', host, 'The machine\'s whole name. The node keeps its name in ai (' + n.name + ') whatever the machine is called.'));
  if (cons.length > 1) g1.appendChild(formField('Connection', con));
  card.appendChild(g1);
  var s1 = msect('IPv4', '');
  var g2 = el('div', 'formgrid');
  g2.appendChild(formField('Address with its prefix', a4, 'e.g. 192.0.2.10/24 - /24 is the mask 255.255.255.0.'));
  g2.appendChild(formField('Gateway', gw));
  g2.appendChild(formField('DNS servers', dns, 'Separated by commas.'));
  g2.appendChild(formField('Search domains', search));
  s1._body.appendChild(g2);
  card.appendChild(s1);
  var s2 = msect('IPv6 (dual stack)', 'Switched on, the server takes IPv6 beside IPv4: nginx answers on both, the firewall is set for both.');
  var r6 = el('div', 'formgrid');
  r6.appendChild(formField('IPv6', s6));
  var g6 = el('div', 'formgrid');
  g6.appendChild(formField('How', mode6));
  g6.appendChild(formField('Address with its prefix', a6, 'e.g. 2001:db8::10/64'));
  g6.appendChild(formField('Gateway', gw6));
  g6.appendChild(formField('DNS servers', dns6));
  s2._body.appendChild(r6);
  s2._body.appendChild(g6);
  card.appendChild(s2);
  var paint6 = function () {
    g6.hidden = !s6._get();
    var manual = mode6.value === 'manual';
    a6.closest('.set-item').hidden = !manual;
    gw6.closest('.set-item').hidden = !manual;
  };
  s6._input.addEventListener('change', paint6);
  mode6.addEventListener('change', paint6);
  /* Shown only when the new address is outside the web address's network
     (1.0.120): the node could not hold it there - on purpose only while a
     whole cluster moves to another network, one node at a time. */
  var elsewhere = null;
  var vnet = null;
  if (NET.d.cluster && NET.d.vip && NET.d.vip.on) {
    elsewhere = el('div', 'note warn net-elsewhere');
    var lab = el('label', 'check small');
    var cb = el('input'); cb.type = 'checkbox';
    lab.appendChild(cb);
    lab.appendChild(el('span', '', 'The web address (' + NET.d.vip.address + ') is meant to be in another network than the new address'));
    elsewhere.appendChild(el('div', 'small', 'The new address is not in the network of the web address: keepalived could not put the web address on this node. Tick it only while the whole cluster moves to another network - this node now, the other next, the web address last (High availability).'));
    elsewhere.appendChild(lab);
    elsewhere._get = function () { return cb.checked && !elsewhere.hidden; };
    elsewhere.hidden = true;
    card.appendChild(elsewhere);
    vnet = NET.d.vip.address;
    var paintVip = function () {
      elsewhere.hidden = !ipOutside(a4.value.trim(), vnet);
    };
    a4.addEventListener('input', paintVip);
    setTimeout(paintVip, 0);
  }
  var want = function () {
    return {con: con.value || data.con, hostname: host.value.trim(),
            ipv4: {addr: a4.value.trim(), gw: gw.value.trim(), dns: dns.value, search: search.value},
            ipv6: {on: !!s6._get(), mode: mode6.value, addr: a6.value.trim(), gw: gw6.value.trim(), dns: dns6.value},
            vip_elsewhere: elsewhere ? elsewhere._get() : false};
  };
  var planBox = el('div', 'net-plan');
  var row = el('div', 'btnrow');
  row.style.marginTop = '14px';
  var check = cmdButton('Check it', 'check', '');
  var go = cmdButton('Change it', 'net', 'primary');
  check.onclick = function () {
    busy(check, true);
    api('net', {action: 'plan', node: n.name, want: want()}).then(function (d) {
      clear(planBox);
      planBox.appendChild(el('h4', '', 'What happens'));
      var ol = el('ol', 'net-steps');
      d.plan.forEach(function (p) { ol.appendChild(el('li', '', p)); });
      planBox.appendChild(ol);
    }).catch(function (e) { clear(planBox); planBox.appendChild(el('p', 'note bad', String(e.message || e))); })
      .then(function () { busy(check, false); });
  };
  go.onclick = function () {
    var w = want();
    api('net', {action: 'plan', node: n.name, want: w}).then(function (d) {
      var words = '<ol class="net-steps">' + d.plan.map(function (p) { return '<li>' + htmlText(p) + '</li>'; }).join('') + '</ol>'
        + (n.me && !NET.d.cluster ? '<p class="note">' + htmlText('Not kept within the time set under Signing in, the old network comes back by itself: open the pages at the new address and press Keep it.') + '</p>' : '');
      confirmThen('Change the network of ' + n.name + '?', words, 'Change it', function () {
        api('net', {action: 'apply', node: n.name, want: w}).then(function (r) {
          toast(r.message, 'good');
          NET.watch = n.name;
          NET.target = {node: n.name, old: (a4Was || '').split('/')[0],   /* what the box was filled with (1.0.146) - its defaultValue was always '' */ ip: w.ipv4.addr.split('/')[0], host: w.hostname, oldHost: data.hostname || '', me: n.me};
          loadNet();
        }).catch(oops);
      });
    }).catch(oops);
  };
  row.appendChild(check);
  row.appendChild(go);
  card.appendChild(row);
  card.appendChild(planBox);
  setTimeout(paint6, 0);
  return card;
}
/* Is the address (with its prefix) outside the network of the web address?
   IPv4 only - the web address and the nodes speak VRRP over IPv4. */
function ipOutside(addr, vip) {
  var p = function (t) {
    var m = /^(\d+)\.(\d+)\.(\d+)\.(\d+)(?:\/(\d+))?$/.exec(String(t || '').trim());
    if (!m) return null;
    return {n: ((+m[1] << 24) >>> 0) + (+m[2] << 16) + (+m[3] << 8) + (+m[4]), len: m[5] === undefined ? 32 : +m[5]};
  };
  var a = p(addr), v = p(vip);
  if (!a || !v) return false;
  var mask = v.len === 0 ? 0 : (0xffffffff << (32 - v.len)) >>> 0;
  return ((a.n & mask) >>> 0) !== ((v.n & mask) >>> 0);
}
function netProgressCard(n) {
  var j = n.job;
  var card = el('div', 'card full net-job ' + (j.state || ''));
  card.appendChild(el('h2', '', j.state === 'done' ? 'The network of ' + n.name + ' is changed'
    : (j.state === 'failed' ? 'The network of ' + n.name + ' was not changed' : 'Changing the network of ' + n.name)));
  var bar = el('div', 'going wide');
  bar.innerHTML = '<div class="bar"><span></span></div>';
  bar.querySelector('span').style.width = Math.max(3, Math.min(100, j.pct || 0)) + '%';
  card.appendChild(bar);
  if (j.state === 'rebooting') {
    var since = Math.max(0, NET.d.now - (j.down_at || j.moved || NET.d.now));
    var p = el('p', 'note', 'Restarting: ' + span(since) + ' so far - a restart takes a minute or two.');
    card.appendChild(p);
  }
  var ol = el('ol', 'net-steps done');
  (j.steps || []).forEach(function (s) {
    var li = el('li', s.ok ? 'good' : 'bad');
    li.appendChild(el('span', 'mark', s.ok ? '✓' : '✗'));
    li.appendChild(el('span', '', s.what));
    li.appendChild(el('span', 'muted small', ' ' + clockWords(new Date(s.at * 1000))));
    ol.appendChild(li);
  });
  card.appendChild(ol);
  if (j.state === 'done' || j.state === 'failed') {
    var row = el('div', 'actions');
    var hide = hideButton(function () {
      return api('net', {action: 'hide', node: n.name}).then(function (d) { NET.d = d; drawNet(); });
    });
    row.appendChild(hide);
    row.appendChild(el('span', 'muted small', j.state === 'done'
      ? 'Hidden by itself 6 hours after it was done.' : 'Hidden by itself after a day.'));
    card.appendChild(row);
  }
  return card;
}
/* "Hide this" on what is over and only says how it went (1.0.123): a
   change of network, a restart, an upgrade, a job on the database, a test
   mail. `go` hides it - a promise when the server is told. */
function hideButton(go) {
  var b = cmdButton('Hide this', 'close', 'small');
  b.classList.add('hide-this');
  b.onclick = function (e) {
    if (e) e.stopPropagation();
    busy(b, true);
    Promise.resolve(go()).catch(oops).then(function () { busy(b, false); });
  };
  return b;
}
function hideBar(go, words) {
  var row = el('div', 'actions hide-row');
  row.appendChild(hideButton(go));
  if (words) row.appendChild(el('span', 'muted small', words));
  return row;
}
function drawNetAway() {
  /* The page's node does not answer: it is the one restarting. Counted down,
     and taken to its new address when it changed. */
  var host = $('net-host');
  if (!host) return;
  var t = NET.target || {};
  var away = Math.round((Date.now() - NET.failSince) / 1000);
  var box = $('net-away');
  if (!box) {
    box = el('div', 'card full net-job');
    box.id = 'net-away';
    host.insertBefore(box, host.firstChild);
  }
  clear(box);
  box.appendChild(el('h2', '', 'This page\'s server is restarting'));
  var bar = el('div', 'going wide');
  bar.innerHTML = '<div class="bar"><span></span></div>';
  bar.querySelector('span').style.width = Math.min(100, Math.round(away / 150 * 100)) + '%';
  box.appendChild(bar);
  box.appendChild(el('p', 'note', 'Not answering for ' + span(away) + '. The page asks again every two seconds.'));
  var newHost = '';
  if (t.me && t.ip && t.old && t.ip !== t.old && location.hostname === t.old) newHost = t.ip;
  if (t.me && t.host && t.oldHost && t.host !== t.oldHost && location.hostname.toLowerCase() === t.oldHost.toLowerCase()) newHost = t.host;
  if (newHost) {
    var url = location.protocol + '//' + (newHost.indexOf(':') >= 0 ? '[' + newHost + ']' : newHost) + (location.port ? ':' + location.port : '') + '/admin/#settings/network';
    var p = el('p', 'note');
    p.appendChild(document.createTextNode('It comes back at its new address: '));
    var a = noI18n(el('a', 'mono', url)); a.href = url;
    p.appendChild(a);
    box.appendChild(p);
    if (away > 150 && !NET.redirect) { NET.redirect = setTimeout(function () { location.href = url; }, 500); }
  }
}

/* ---- Settings → Restart and power off (1.0.119) ------------------------------- */
var PW = {d: null, poll: null, failSince: 0, mine: false, reload: false};
function loadPower() {
  api('power').then(function (d) { PW.d = d; PW.failSince = 0; drawPower(); pwPollFor(); }).catch(oops);
}
function pwPollFor() {
  var live = PW.d && PW.d.plan && PW.d.plan.id && !pwAllDone(PW.d);
  if (live && !PW.poll) PW.poll = setInterval(pwPoll, 2000);
  if (!live && PW.poll) { clearInterval(PW.poll); PW.poll = null; }
}
function pwPoll() {
  if (TAB !== 'settings' || PANE !== 'power') { clearInterval(PW.poll); PW.poll = null; return; }
  api('power').then(function (d) {
    var wasAway = !!PW.failSince;
    PW.d = d; PW.failSince = 0;
    drawPower(true);
    if (pwAllDone(d)) {
      clearInterval(PW.poll); PW.poll = null;
      toast(d.plan.how === 'reboot' ? 'every node is up again' : 'switched off', 'good');
      if (wasAway || PW.reload) setTimeout(function () { location.reload(); }, 2500);
    }
  }).catch(function () { if (!PW.failSince) PW.failSince = Date.now(); drawPowerAway(); });
}
function pwStateOf(d, n) {
  var r = n.row || {};
  var plan = d.plan || {};
  if (!r.state) return {k: 'wait', w: plan.order === 'rolling' ? 'waits its turn' : 'asked'};
  if (r.state === 'failed') return {k: 'bad', w: 'failed: ' + (r.said || '')};
  if (r.state === 'back') return {k: 'ok', w: 'up again'};
  if (r.state === 'going') {
    if (plan.how === 'poweroff') return n.alive && (d.now - (r.down_at || 0)) < 20 ? {k: 'going', w: 'switching off'} : {k: 'ok', w: 'switched off'};
    if (n.alive && (n.started || 0) > (r.down_at || 0)) return {k: 'going', w: 'starting'};
    if (n.alive && d.now < (r.down_at || 0) + 15) return {k: 'going', w: 'going down'};
    return {k: 'going', w: 'restarting'};
  }
  return {k: 'wait', w: r.state};
}
function pwAllDone(d) {
  if (!d.plan || !d.plan.id) return true;
  return d.nodes.filter(function (n) { return (d.plan.targets || []).indexOf(n.name) >= 0; })
    .every(function (n) { var s = pwStateOf(d, n); return s.k === 'ok' || s.k === 'bad'; });
}
function drawPower(live) {
  var real = $('pw-host');
  if (!real || !PW.d) return;
  liveFill(real, function (host) {
  var d = PW.d;
  if (d.plan && d.plan.id) host.appendChild(pwProgress(d));
  var grid = el('div', 'pw-grid');
  d.nodes.forEach(function (n) {
    var c = el('div', 'card pw-node');
    var h = el('div', 'pw-head');
    h.appendChild(el('span', 'dot ' + (n.alive ? 'ok' : 'bad')));
    h.appendChild(noI18n(el('b', '', n.name)));
    if (n.me) h.appendChild(el('span', 'tag info', 'this page'));
    c.appendChild(h);
    c.appendChild(netFacts([
      ['State', n.alive ? 'answering' : 'not answering'],
      ['Address', n.address || '', true],
      ['Running for', n.started ? span(d.now - n.started) : ''],
      ['Version', n.version || '', true]
    ]));
    var row = el('div', 'btnrow');
    var rb = cmdButton('Restart', 'refresh', '');
    var off = cmdButton('Power off', 'power', 'danger');
    rb.disabled = off.disabled = !!d.busy || !n.alive;
    rb.onclick = function () { pwAsk('reboot', [n.name], 'one', n); };
    off.onclick = function () { pwAsk('poweroff', [n.name], 'one', n); };
    row.appendChild(rb); row.appendChild(off);
    c.appendChild(row);
    grid.appendChild(c);
  });
  host.appendChild(grid);
  if (d.cluster) {
    var both = el('div', 'card full');
    both.appendChild(el('h2', '', 'Both nodes'));
    var all = d.nodes.map(function (n) { return n.name; });
    var row2 = el('div', 'btnrow');
    var r1 = cmdButton('Restart one after the other', 'refresh', 'primary');
    explain(r1, 'The other node first, then this one - each in maintenance while it restarts, so the web address and the service never stop.');
    var r2 = cmdButton('Restart both at once', 'refresh', '');
    var r3 = cmdButton('Power off both', 'power', 'danger');
    [r1, r2, r3].forEach(function (b) { b.disabled = !!d.busy; });
    r1.onclick = function () { pwAsk('reboot', all, 'rolling'); };
    r2.onclick = function () { pwAsk('reboot', all, 'together'); };
    r3.onclick = function () { pwAsk('poweroff', all, 'together'); };
    row2.appendChild(r1); row2.appendChild(r2); row2.appendChild(r3);
    both.appendChild(row2);
    host.appendChild(both);
  }
  }, live, function () { explainWhatWasDrawn(real); });
}
function pwAsk(how, targets, order, n) {
  var d = PW.d;
  var who = targets.join(', ');
  var words;
  if (how === 'poweroff') words = targets.length > 1 ? 'Both nodes are switched off. Nothing answers - RADIUS, the pages - until somebody switches them on again at the machines.'
    : (d.cluster ? n.name + ' is switched off; the web address moves to the other node, which goes on answering alone. It has to be switched on again at the machine.' : 'The server is switched off. Nothing answers - and every terminal ends - until somebody switches it on again at the machine.');
  else if (order === 'rolling') words = 'One after the other: each goes into maintenance, the web address moves to the other node, it restarts and comes back into service - then the next. RADIUS and the pages go on answering all the time.';
  else if (targets.length > 1) words = 'Both restart at the same moment: for a minute or two nothing answers - RADIUS, the pages, the web address.';
  else words = d.cluster ? n.name + ' goes into maintenance, the web address moves to the other node, and it restarts; back up, it comes back into service by itself.' : 'The server restarts: for a minute or two nothing answers, and every terminal ends.';
  confirmThen((how === 'reboot' ? 'Restart ' : 'Power off ') + who + '?', htmlText(words), how === 'reboot' ? 'Restart' : 'Power off', function () {
    api('power', {how: how, targets: targets, order: order}).then(function (r) {
      toast(r.message, 'good');
      PW.reload = targets.indexOf(((d.nodes.filter(function (x) { return x.me; })[0]) || {}).name) >= 0;
      loadPower();
    }).catch(oops);
  }, how === 'poweroff');
}
function pwProgress(d) {
  var plan = d.plan;
  var card = el('div', 'card full net-job');
  var done = pwAllDone(d);
  card.appendChild(el('h2', '', (plan.how === 'reboot' ? 'Restart' : 'Power-off') + (done ? ' - done' : ' under way')));
  var ol = el('ol', 'net-steps done');
  d.nodes.filter(function (n) { return (plan.targets || []).indexOf(n.name) >= 0; })
    .sort(function (a, b) { return plan.targets.indexOf(a.name) - plan.targets.indexOf(b.name); })
    .forEach(function (n) {
      var st = pwStateOf(d, n);
      var li = el('li', st.k === 'ok' ? 'good' : (st.k === 'bad' ? 'bad' : ''));
      li.appendChild(el('span', 'mark', st.k === 'ok' ? '✓' : (st.k === 'bad' ? '✗' : '…')));
      li.appendChild(noI18n(el('b', '', n.name + ' ')));
      li.appendChild(el('span', '', st.w));
      var r = n.row || {};
      if (st.k === 'going' && r.down_at) {
        var t = Math.max(0, d.now - r.down_at);
        var bar = el('div', 'going wide');
        bar.innerHTML = '<div class="bar"><span></span></div>';
        bar.querySelector('span').style.width = Math.min(100, Math.round(t / 120 * 100)) + '%';
        li.appendChild(el('span', 'muted small', ' ' + span(t)));
        li.appendChild(bar);
      }
      ol.appendChild(li);
    });
  card.appendChild(ol);
  if (done) card.appendChild(hideBar(function () {
    return api('power', {action: 'hide'}).then(function (x) { PW.d = x; drawPower(); });
  }, 'Hidden by itself half an hour after it began.'));
  return card;
}
function drawPowerAway() {
  var host = $('pw-host');
  if (!host) return;
  var box = $('pw-away');
  if (!box) { box = el('div', 'card full net-job'); box.id = 'pw-away'; host.insertBefore(box, host.firstChild); }
  clear(box);
  var away = Math.round((Date.now() - PW.failSince) / 1000);
  box.appendChild(el('h2', '', 'This page\'s server is restarting'));
  var bar = el('div', 'going wide');
  bar.innerHTML = '<div class="bar"><span></span></div>';
  bar.querySelector('span').style.width = Math.min(100, Math.round(away / 120 * 100)) + '%';
  box.appendChild(bar);
  box.appendChild(el('p', 'note', 'Not answering for ' + span(away) + ' - asked again every two seconds; the page comes back by itself.'));
}

/* ---- Settings → Time (1.0.120) -------------------------------------------------
   Each node's clock as chrony sees it, its sources, and the time servers for the
   whole cluster. */
var NTP = {d: null, poll: null, draft: null, node: ''};
function loadNtp() {
  api('ntp').then(function (d) {
    NTP.d = d;
    if (!NTP.node) NTP.node = (d.nodes[0] || {}).name;
    drawNtp();
    if (!NTP.poll) NTP.poll = setInterval(function () {
      if (TAB !== 'settings' || PANE !== 'time') { clearInterval(NTP.poll); NTP.poll = null; return; }
      api('ntp').then(function (x) { NTP.d = x; drawNtp(true); }).catch(function () {});
    }, 10000);
  }).catch(oops);
}
function ntpMs(s) {
  if (s === undefined || s === null || isNaN(s)) return '–';
  var ms = s * 1000;
  var a = Math.abs(ms);
  return (ms >= 0 ? '+' : '−') + (a >= 1000 ? (a / 1000).toFixed(2) + ' s' : (a >= 10 ? a.toFixed(1) : a.toFixed(3)) + ' ms');
}
function ntpHealth(n) {
  var d = (n.now || {}).data || {};
  var t = d.tracking || {};
  if (!d.time) return {k: 'bad', w: n.alive ? 'not read yet' : 'not answering'};
  if (!d.chrony) return {k: d.ntpsynchronized === 'yes' ? 'ok' : 'bad', w: d.ntpsynchronized === 'yes' ? 'synchronised (not chrony)' : 'chrony is not installed'};
  if (t.leap === 'Not synchronised' || !t.stratum) return {k: 'bad', w: 'not synchronised'};
  var off = Math.abs(t.offset || 0);
  if (off > 1) return {k: 'bad', w: 'synchronised, but off'};
  if (off > 0.1) return {k: 'warn', w: 'synchronised'};
  return {k: 'ok', w: 'synchronised'};
}
function drawNtp(quiet) {
  var real = $('ntp-host');
  if (!real || !NTP.d) return;
  /* What the server has, until something is changed here. */
  /* Refreshed in place, never replaced (1.0.14): the pane is drawn again every
     10 s, and a choice made in a field drawn before that - a time zone looked
     for in a list of 400 - went into the draft thrown away, so the save put
     in the old one and nothing changed. */
  if (!NTP.draft) NTP.draft = JSON.parse(JSON.stringify(NTP.d.conf));
  else if (!PENDING.ntp) {
    var fresh = JSON.parse(JSON.stringify(NTP.d.conf));
    Object.keys(NTP.draft).forEach(function (k) { if (!(k in fresh)) delete NTP.draft[k]; });
    Object.keys(fresh).forEach(function (k) { NTP.draft[k] = fresh[k]; });
  }
  liveFill(real, function (host) {
  var d = NTP.d;
  var grid = el('div', 'pw-grid');
  d.nodes.forEach(function (n) {
    var nd = (n.now || {}).data || {};
    var t = nd.tracking || {};
    var h = ntpHealth(n);
    var c = el('div', 'card ntp-node');
    var head = el('div', 'pw-head');
    head.appendChild(el('span', 'dot ' + (h.k === 'ok' ? 'ok' : (h.k === 'warn' ? 'warn' : 'bad'))));
    head.appendChild(noI18n(el('b', '', n.name)));
    if (n.me) head.appendChild(el('span', 'tag info', 'this page'));
    head.appendChild(el('span', 'tag ' + (h.k === 'ok' ? 'ok' : (h.k === 'warn' ? 'warn' : 'crit')), h.w));
    c.appendChild(head);
    var big = el('div', 'ntp-big');
    big.appendChild(noI18n(el('span', 'ntp-off', ntpMs(t.offset))));
    big.appendChild(el('span', 'muted small', ' off the time servers'));
    c.appendChild(big);
    var clock = '';
    if (nd.time) {
      var dt = new Date((nd.time + (d.now - (n.now.at || d.now))) * 1000);
      clock = dt.toLocaleString(numLang());
    }
    c.appendChild(netFacts([
      ['Follows', t.ref || t.ref_id || '', true],
      ['Stratum', t.stratum !== undefined ? String(t.stratum) : '', true],
      ['Last correction', ntpMs(t.last_offset), true],
      ['Frequency', t.freq !== undefined ? t.freq.toFixed(3) + ' ppm' : '', true],
      ['Root delay / dispersion', t.root_delay !== undefined ? ntpMs(t.root_delay).replace('+', '') + ' / ' + ntpMs(t.root_disp).replace('+', '') : '', true],
      ['Leap status', t.leap || ''],
      ['Time zone', nd.timezone || '', true],
      ['Its time', clock],
      ['Read', n.now && n.now.at ? ago(n.now.at) : '']
    ]));
    var ap = n.applied || {};
    if (ap.at) {
      var st = el('p', 'small ' + (ap.ok ? 'muted' : 'bad'));
      st.textContent = (ap.ok ? 'Time servers set ' : 'Time servers NOT set ') + ago(ap.at) + (ap.said ? ': ' + ap.said : '');
      c.appendChild(st);
    }
    var row = el('div', 'btnrow');
    var re = cmdButton('Read it again', 'refresh', 'small');
    re.onclick = function () { api('ntp', {action: 'read', node: n.name}).then(function (r) { toast(r.message, 'good'); setTimeout(loadNtp, 4000); }).catch(oops); };
    var sy = cmdButton('Step it now', 'clock', 'small');
    explain(sy, 'The clock set to the time servers at once (chronyc makestep), not slewed slowly - for a clock that is far off.');
    sy.onclick = function () {
      confirmThen('Step the clock of ' + n.name + ' now?', htmlText('The clock jumps to the time servers\' time at once. Codes and logs written in that moment may look out of order.'), 'Step it', function () {
        api('ntp', {action: 'sync', node: n.name}).then(function (r) { toast(r.message, 'good'); setTimeout(loadNtp, 6000); }).catch(oops);
      }, false);
    };
    row.appendChild(re); row.appendChild(sy);
    c.appendChild(row);
    grid.appendChild(c);
  });
  host.appendChild(grid);
  if (d.cluster && d.nodes.length > 1) {
    var a = ((d.nodes[0].now || {}).data || {}).tracking || {};
    var b = ((d.nodes[1].now || {}).data || {}).tracking || {};
    if (a.offset !== undefined && b.offset !== undefined) {
      var diff = Math.abs(a.offset - b.offset);
      host.appendChild(el('p', 'note ' + (diff > 1 ? 'bad' : (diff > 0.1 ? 'warn' : 'good')), 'Between the two nodes: ' + ntpMs(diff).replace('+', '') + (diff > 1 ? ' - codes right on one node may be refused on the other' : '')));
    }
  }
  /* Sources, per node. */
  var sc = el('div', 'card full');
  var sh = el('h2', '', 'Where the time comes from');
  sc.appendChild(sh);
  if (d.cluster) {
    var seg = el('div', 'seg');
    d.nodes.forEach(function (n) {
      var bt = el('button', n.name === NTP.node ? 'on' : '', n.name);
      bt.type = 'button';
      noI18n(bt);
      bt.onclick = function () { NTP.node = n.name; drawNtp(false); };
      seg.appendChild(bt);
    });
    sc.appendChild(seg);
  }
  var sn = d.nodes.filter(function (x) { return x.name === NTP.node; })[0] || d.nodes[0];
  var srcs = (((sn || {}).now || {}).data || {}).sources || [];
  var STATES = {'*': ['ok', 'followed'], '+': ['ok', 'combined'], '-': ['', 'not combined'], '?': ['crit', 'unreachable'],
                'x': ['crit', 'false ticker'], '~': ['warn', 'too variable']};
  if (!srcs.length) sc.appendChild(el('p', 'note', 'No source - chrony has none, or is not installed.'));
  else sc.appendChild(listTable(['State', 'Source', 'Stratum', 'Asked every', 'Reached', 'Last heard', 'Offset'], srcs, function (s) {
    var tr = el('tr');
    var stt = STATES[s.state] || ['', s.state];
    var td = el('td');
    td.appendChild(el('span', 'tag ' + stt[0], stt[1]));
    if (s.mode === '=') td.appendChild(el('span', 'muted small', ' peer'));
    tr.appendChild(td);
    tr.appendChild(noI18n(el('td', 'mono', s.name)));
    tr.appendChild(el('td', 'num', String(s.stratum)));
    tr.appendChild(el('td', 'num', span(Math.pow(2, s.poll || 0))));
    var r = el('td');
    var bits = el('span', 'reach');
    for (var i = 7; i >= 0; i--) bits.appendChild(el('i', (s.reach >> i) & 1 ? 'on' : ''));
    bits.title = (s.reach || 0).toString(2).padStart(8, '0') + ' - the last 8 tries';
    r.appendChild(bits);
    tr.appendChild(r);
    tr.appendChild(el('td', 'muted', s.last_rx === null || s.last_rx === undefined ? '–' : span(s.last_rx) + ' ago'));
    tr.appendChild(noI18n(el('td', 'num mono', ntpMs(s.offset) + ' ± ' + ntpMs(s.error).replace('+', ''))));
    return tr;
  }, 'plain'));
  var own = (((sn || {}).now || {}).data || {}).own || [];
  if (own.length && !(((sn || {}).now || {}).data || {}).managed) {
    sc.appendChild(el('p', 'muted small', 'Its own /etc/chrony.conf: '));
    sc.appendChild(noI18n(el('pre', 'mono small', own.join('\n'))));
  }
  host.appendChild(sc);
  host.appendChild(ntpForm());
  }, !!quiet, function () { explainWhatWasDrawn(real); });
}
function ntpForm() {
  var d = NTP.d;
  var dr = NTP.draft;
  var card = el('div', 'card full');
  card.id = 'ntp-form';
  /* Anything changed here waits for the save bar at the bottom. */
  ['input', 'change'].forEach(function (ev) { card.addEventListener(ev, function () { ntpDirty(); }); });
  card.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('button')) ntpDirty(); });
  card.appendChild(el('h2', '', 'The time servers'));
  var on = switchBox(dr.manage);
  var g0 = el('div', 'formgrid');
  g0.appendChild(formField('ai sets the time servers', on, 'Off: each machine keeps its own /etc/chrony.conf (AlmaLinux\'s pool, or what you set by hand) - shown and checked here, not changed. On: the servers below, the same on every node; the file\'s own server and pool lines are commented out, and put back when switched off again.'));
  card.appendChild(g0);
  var body = el('div');
  card.appendChild(body);
  var draw = function () {
    clear(body);
    body.hidden = !dr.manage;
    var list = el('div', 'ntp-servers');
    (dr.servers || []).forEach(function (s, i) {
      var row = el('div', 'ntp-srv');
      var hostIn = textBox(s.host, 'ntp.example.cz', 'mono');
      hostIn.oninput = function () { s.host = hostIn.value.trim(); };
      var kind = selectBox([['server', 'one server'], ['pool', 'a pool (several addresses)']], s.pool ? 'pool' : 'server');
      kind.onchange = function () { s.pool = kind.value === 'pool'; };
      row.appendChild(hostIn); row.appendChild(kind);
      [['iburst', 'iburst', 'Four quick questions at the start: synchronised in seconds, not minutes.'],
       ['prefer', 'preferred', 'Followed before the others when it is good.'],
       ['nts', 'NTS', 'Network Time Security: the server proves who it is (time.cloudflare.com, ptbtime1.ptb.de, nts.netnod.se…). Needs TCP 4460 out.']].forEach(function (o) {
        var l = el('label', 'check small');
        var cb = el('input'); cb.type = 'checkbox'; cb.checked = !!s[o[0]];
        cb.onchange = function () { s[o[0]] = cb.checked; };
        l.appendChild(cb); l.appendChild(el('span', '', o[1]));
        explain(l, o[2]);
        row.appendChild(l);
      });
      var x = iconButton('trash', 'Take it away');
      x.onclick = function () { dr.servers.splice(i, 1); draw(); };
      row.appendChild(x);
      list.appendChild(row);
    });
    body.appendChild(list);
    var adds = el('div', 'btnrow');
    var add = cmdButton('Add a server', 'add', 'small');
    add.onclick = function () { dr.servers.push({host: '', pool: false, iburst: true, prefer: false, nts: false}); draw(); };
    adds.appendChild(add);
    [['cz.pool.ntp.org', true, false], ['pool.ntp.org', true, false], ['time.cloudflare.com', false, true], ['tik.cesnet.cz', false, false], ['tak.cesnet.cz', false, false]].forEach(function (p) {
      var b = cmdButton('+ ' + p[0], '', 'small');
      noI18n(b);
      b.onclick = function () {
        if (dr.servers.some(function (s) { return s.host === p[0]; })) return;
        dr.servers.push({host: p[0], pool: p[1], iburst: true, prefer: false, nts: p[2]}); draw();
      };
      adds.appendChild(b);
    });
    body.appendChild(adds);
    var g = el('div', 'formgrid');
    g.style.marginTop = '14px';
    if (d.cluster) {
      var peers = switchBox(dr.peers);
      peers._input.onchange = function () { dr.peers = !!peers._get(); };
      g.appendChild(formField('The nodes take each other too', peers, 'Each node is one more source for the other: if the servers above are out of reach, the two nodes at least keep one time - which is what codes need.'));
    }
    var stepS = textBox(String((dr.makestep || [1, 3])[0]), '1', 'mono');
    stepS.oninput = function () { dr.makestep = [stepS.value, (dr.makestep || [1, 3])[1]]; };
    var stepN = textBox(String((dr.makestep || [1, 3])[1]), '3', 'mono');
    stepN.oninput = function () { dr.makestep = [(dr.makestep || [1, 3])[0], stepN.value]; };
    g.appendChild(formField('Step when off by more than (s)', stepS, 'Further off than this, the clock jumps to the right time instead of being slowed or sped up gently.'));
    g.appendChild(formField('…in the first updates', stepN, 'How many updates after chronyd starts may step it: 3 is after a boot; -1 any time.'));
    var mins = textBox(String(dr.minsources || 1), '1', 'mono');
    mins.oninput = function () { dr.minsources = mins.value; };
    g.appendChild(formField('Sources that have to agree', mins, 'The clock is set only when at least this many sources agree. 1 with one server; 2 or 3 with several.'));
    var allow = textBox((dr.allow || []).join(', '), '192.0.2.0/24', 'mono');
    /* A list, as it came (1.0.146): kept as the typed text, the next drawing
       of the pane broke on .join and it stopped refreshing. */
    allow.oninput = function () { dr.allow = allow.value.split(/[\s,;]+/).filter(Boolean); };
    g.appendChild(formField('Serve the time to', allow, 'Networks that may ask this server for the time (UDP 123). Empty: nobody. The firewall opens it by itself.'));
    body.appendChild(g);
  };
  on._input.onchange = function () { dr.manage = !!on._get(); draw(); };
  draw();
  var zones = d.zones || [];
  var tz = selectBox([['', '- as each machine has it -']].concat(zones.map(function (z) { return [z, z]; })), dr.timezone || '');
  tz.onchange = function () { dr.timezone = tz.value; };
  var g2 = el('div', 'formgrid');
  g2.style.marginTop = '14px';
  g2.appendChild(formField('Time zone', tz, 'Of the machines: the logs and the times on these pages. Codes do not depend on it.'));
  card.appendChild(g2);
  card.appendChild(el('p', 'muted small', 'Saved with the bar at the bottom; each node then puts them in by itself within seconds.'));
  return card;
}
function ntpDirty() {
  pendingSet('ntp', {pane: 'time', save: ntpSave, reset: function () {
    delete PENDING.ntp; drawNtp(false);
  }});
}
function ntpSave() {
  var dr = NTP.draft;
  if (!dr) return Promise.resolve(true);
  var c = {manage: dr.manage, servers: (dr.servers || []).filter(function (s) { return s.host; }), peers: dr.peers,
           allow: dr.allow, step_s: (dr.makestep || [1, 3])[0], step_n: (dr.makestep || [1, 3])[1],
           minsources: dr.minsources, timezone: dr.timezone};
  return api('ntp', {action: 'save', conf: c}).then(function (r) {
    toast(r.message, 'good'); setTimeout(loadNtp, 5000); return true;
  });
}

/* ---- Settings → SSH keys of root (1.0.158) -------------------------------------
   Each node's /root/.ssh/authorized_keys as its root helper reads it; the keys
   put side by side, a column a node. Above them root's key kept here, drawn as
   isemon draws a router's (1.0.159), made here - one for every node, or one for
   a node of its own. The key is then in the list below, a key of one's own
   added there too (1.0.161). */
var SK = {d: null, poll: null, asked: 0, scope: 'all'};
function loadSshKeys() {
  api('sshkeys').then(function (d) {
    SK.d = d; drawSshKeys();
    /* Read afresh on every node when the pane is opened. */
    if (Date.now() - SK.asked > 20000) {
      SK.asked = Date.now();
      api('sshkeys', {action: 'refresh', nodes: skNodes(true)}).then(function () { skPoll(true); }).catch(function () {});
    }
    skPoll(skPending());
  }).catch(oops);
}
function skNodes(aliveOnly) {
  return ((SK.d && SK.d.nodes) || []).filter(function (n) { return !aliveOnly || n.alive; }).map(function (n) { return n.name; });
}
function skPending() { return ((SK.d && SK.d.nodes) || []).some(function (n) { return n.pending; }); }
function skPoll(on) {
  if (on && !SK.poll) {
    SK.poll = setInterval(function () {
      if (TAB !== 'settings' || PANE !== 'sshkeys') { skPoll(false); return; }
      api('sshkeys').then(function (d) { SK.d = d; drawSshKeys(true); if (!skPending()) skPoll(false); }).catch(function () {});
    }, 2000);
  }
  if (!on && SK.poll) { clearInterval(SK.poll); SK.poll = null; }
}
function skKind(k) {
  var t = String(k.type || '?').toUpperCase();
  return t + (k.bits && t !== 'ED25519' ? ' ' + k.bits : '');
}
function drawSshKeys(live) {
  var real = $('sk-host');
  if (!real || !SK.d) return;
  liveLetGo(real);
  liveFill(real, function (host) {
    var d = SK.d, nodes = d.nodes || [];
    /* What sshd makes of root: keys are no use where it does not let root in. */
    nodes.forEach(function (n) {
      var sd = n.sshd || {};
      if (n.error) host.appendChild(el('p', 'note bad', n.name + ': ' + n.error));
      if (sd.there && sd.permit_root === 'no')
        host.appendChild(el('p', 'note warn', n.name + ': sshd does not let root sign in at all (PermitRootLogin no) - the keys below are not used there until it does.'));
      if (sd.there && sd.pubkey === 'no')
        host.appendChild(el('p', 'note warn', n.name + ': sshd takes no keys (PubkeyAuthentication no).'));
    });
    var kept = {};
    (d.kept || []).forEach(function (r) { if (r.fp) kept[r.fp] = r; });
    host.appendChild(skKeptCard(d));
    var card = el('div', 'card full');
    var h = el('h2', '', 'Keys that may sign in as root');
    var tools = el('span', 'right');
    var add = cmdButton('Add a key', 'upload', 'small');
    explain(add, 'A key you have already - its public line or .pub file, or the private key, of which only the public half is used - put onto the nodes you choose.');
    var again = iconButton('refresh', 'Read the keys again on every node');
    tools.appendChild(add); tools.appendChild(again);
    h.appendChild(tools);
    card.appendChild(h);
    add.onclick = skAdd;
    again.onclick = function () {
      api('sshkeys', {action: 'refresh', nodes: skNodes(true)}).then(function () { skPoll(true); toast('asked again'); }).catch(oops);
    };
    /* One row a key, by its fingerprint, a column a node. */
    var byFp = {}, order = [];
    nodes.forEach(function (n) {
      (n.keys || []).forEach(function (k) {
        var id = k.fp || ('?' + k.comment);
        if (!byFp[id]) { byFp[id] = {k: k, on: {}}; order.push(id); }
        byFp[id].on[n.name] = true;
      });
    });
    if (!order.length) {
      card.appendChild(el('p', 'note', nodes.some(function (n) { return n.at; })
        ? 'No key lets root in over SSH on ' + nodes.map(function (n) { return n.name; }).join(' or ') + '.'
        : 'Reading the keys of each node…'));
    } else {
      var heads = ['Key', 'Fingerprint', 'Comment'].concat(nodes.length > 1 ? nodes.map(function (n) { return n.name; }) : []).concat(['']);
      card.appendChild(listTable(heads, order, function (id) {
        var row = byFp[id], k = row.k;
        var tr = el('tr');
        var t = el('td');
        t.appendChild(el('span', 'tag ' + (String(k.type).toUpperCase() === 'ED25519' ? 'good' : 'info'), skKind(k)));
        if (k.options) t.appendChild(el('span', 'tag warn', 'with options'));
        if (kept[k.fp]) t.appendChild(el('span', 'tag info', 'made here'));
        tr.appendChild(t);
        tr.appendChild(noI18n(el('td', 'mono small', k.fp || '–')));
        tr.appendChild(noI18n(el('td', 'small', k.comment || '–')));
        if (nodes.length > 1) nodes.forEach(function (n) {
          var c = el('td');
          c.appendChild(el('span', 'tag ' + (row.on[n.name] ? 'good' : 'dim'), row.on[n.name] ? 'yes' : '–'));
          tr.appendChild(c);
        });
        var act = el('td', 'right sk-act');
        /* Each key exported by itself, as its .pub file (1.0.160). */
        var ex = iconButton('download', 'Export this key - its public half, as a .pub file');
        ex.disabled = !k.text;
        ex.onclick = function () { skExport(k); };
        act.appendChild(ex);
        var rm = iconButton('trash', 'Take this key away');
        rm.onclick = function () { skDrop(row); };
        act.appendChild(rm);
        tr.appendChild(act);
        return tr;
      }, 'plain'));
    }
    var pend = nodes.filter(function (n) { return n.pending; }).map(function (n) { return n.name; });
    if (pend.length) card.appendChild(el('p', 'muted small', 'Being written on ' + pend.join(', ') + '…'));
    host.appendChild(card);
    /* Each node's own facts. */
    var grid = el('div', 'pw-grid');
    nodes.forEach(function (n) {
      var c = el('div', 'card pw-node');
      var hd = el('div', 'pw-head');
      hd.appendChild(el('span', 'dot ' + (n.alive ? 'ok' : 'bad')));
      hd.appendChild(noI18n(el('b', '', n.name)));
      if (n.me) hd.appendChild(el('span', 'tag info', 'this page'));
      c.appendChild(hd);
      var sd = n.sshd || {};
      c.appendChild(netFacts([
        ['Keys', String((n.keys || []).length)],
        ['Root may sign in', sd.there ? (sd.permit_root || '?') : 'sshd is not here'],
        ['With a password', sd.there ? (sd.password || '?') : ''],
        ['SSH port', sd.port || '', true],
        ['The file', n.file || '/root/.ssh/authorized_keys', true],
        ['Read', n.at ? ago(n.at) : 'not yet']
      ]));
      grid.appendChild(c);
    });
    host.appendChild(grid);
  }, live);
}
function skNodePicker(body) {
  var nodes = (SK.d && SK.d.nodes) || [];
  var box = el('div', 'sk-nodes');
  var boxes = [];
  if (nodes.length > 1) {
    box.appendChild(el('div', 'k small muted', 'Onto the nodes'));
    nodes.forEach(function (n) {
      var lab = el('label', 'chk');
      var c = el('input'); c.type = 'checkbox'; c.checked = n.alive; c.disabled = !n.alive; c.value = n.name;
      lab.appendChild(c); lab.appendChild(noI18n(el('span', '', ' ' + n.name + (n.alive ? '' : ' (not answering)'))));
      box.appendChild(lab);
      boxes.push(c);
    });
    body.appendChild(box);
  }
  return function () {
    if (!boxes.length) return [nodes.length ? nodes[0].name : ''];
    return boxes.filter(function (c) { return c.checked; }).map(function (c) { return c.value; });
  };
}
function skScopeWords(sc) { return sc === 'all' ? 'every node' : sc; }
/* Root's key, made or given here: isemon's key panel - the same words, the
   buttons in a row, the public half below to copy. Unlike isemon's it is kept
   nowhere: ai never signs in as root, so a key made here is handed over
   once, and one given leaves only its public half. In a cluster, the same
   key on every node or a node's own. Taking a key away is in the list. */
function skKeptCard(d) {
  var card = el('div', 'card full');
  card.appendChild(el('h2', '', 'A key for root'));
  var scopes = (d.kept || []);
  if (!scopes.some(function (r) { return r.scope === SK.scope; })) SK.scope = 'all';
  if (scopes.length > 1) {
    var segb = el('div', 'seg');
    scopes.forEach(function (r) {
      var b = el('button', r.scope === SK.scope ? 'on' : '', r.scope === 'all' ? 'The same key on every node' : 'Only on');
      if (r.scope !== 'all') b.appendChild(noI18n(el('b', '', ' ' + r.scope)));
      b.type = 'button';
      b.onclick = function () { SK.scope = r.scope; drawSshKeys(); };
      segb.appendChild(b);
    });
    var ff = formField('The key for', segb);
    ff.style.marginBottom = '12px';
    card.appendChild(ff);
  }
  var cur = scopes.filter(function (r) { return r.scope === SK.scope; })[0] || {scope: 'all', on: {}};
  var nodes = Object.keys(cur.on || {});
  var where = cur.scope === 'all' ? (nodes.length > 1 ? 'both nodes - the same key' : 'this server') : '<b>' + htmlText(cur.scope) + '</b> only';
  var P = rbPanel('Its <b>public</b> half goes into <code>/root/.ssh/authorized_keys</code> of ' + where + '. The <b>private</b> half is never kept here: it is shown to you once, to download or copy. The key is then in the list below - exported or taken away there; a key of your own is added there too.');
  if (!d.keygen) {
    var miss = el('p', 'note');
    miss.style.color = 'var(--warn)';
    miss.textContent = 'ssh-keygen is not on this machine, so a key cannot be made or read here: dnf install openssh-clients.';
    P.box.insertBefore(miss, P.row);
  }
  var mk = cmdButton('Make a key', 'key', '');
  explain(mk, 'Make a fresh pair here - Ed25519, or RSA 4096 where something old needs RSA. Its private half is shown to you once; its public half goes into root\'s authorized_keys of ' + (cur.scope === 'all' ? 'every node' : cur.scope) + '.');
  P.row.appendChild(mk);
  mk.disabled = !d.keygen;
  var words = cur.scope === 'all' ? 'every node' : cur.scope;
  mk.onclick = function () {
    var kind = 'ed25519';
    modal('Make a key for ' + words, function (body) {
      var p = el('p', 'note');
      p.innerHTML = 'A fresh pair is made here. Its <b>private</b> half is shown to you once, to download or copy, and kept nowhere; its <b>public</b> half goes into root\'s authorized_keys of ' + htmlText(nodes.join(', ')) + '. A key there before stays until it is taken away in the list below.';
      body.appendChild(p);
      var sg = el('div', 'seg');
      [['ed25519', 'Ed25519 (the strongest, and short)'], ['rsa4096', 'RSA 4096 (where something old needs RSA)']].forEach(function (o) {
        var b = el('button', o[0] === kind ? 'on' : '', o[1]);
        b.type = 'button';
        b.onclick = function () { kind = o[0]; Array.prototype.forEach.call(sg.children, function (x) { x.classList.remove('on'); }); b.classList.add('on'); };
        sg.appendChild(b);
      });
      body.appendChild(formField('The kind', sg));
    }, [{words: 'Cancel', close: true}, {words: 'Make one', cls: 'primary', icon: 'key', go: function (b) {
      busy(b, true);
      api('sshkeys', {action: 'rk_make', scope: cur.scope, kind: kind}).then(function (x) {
        skShowMade(x);
        return api('sshkeys');
      }).then(function (d2) { SK.d = d2; drawSshKeys(); skPoll(true); })
        .catch(function (e) { busy(b, false); oops(e); });
    }}], 'medium');
  };
  card.appendChild(P.box);
  return card;
}
function skShowMade(x) {
  modal('Keep the private key now', function (body) {
    var w = el('p', 'note warn');
    w.textContent = 'This is the only time it is shown. Whoever holds it signs in to ' + x.nodes.join(', ') + ' as root.';
    body.appendChild(w);
    var area = noI18n(el('textarea', 'mono'));
    area.rows = 9; area.readOnly = true; area.value = x.private; area.spellcheck = false;
    body.appendChild(area);
    var row = el('div', 'btnrow');
    var dl = cmdButton('Download the key', 'download', 'primary');
    dl.onclick = function () { skSave(x.private, x.file); };
    var cp = cmdButton('Copy it', 'copy', '');
    cp.onclick = function () { copyText(x.private, cp, 'the private key is on the clipboard'); };
    row.appendChild(dl); row.appendChild(cp);
    row.style.margin = '12px 0 16px';
    body.appendChild(row);
    body.appendChild(el('p', 'btnhelp', 'Its public half, put onto the nodes - click it to copy:'));
    body.appendChild(rbCopyme(x.pub, 'the public key is on the clipboard'));
    body.appendChild(noI18n(el('p', 'muted small mono', x.fp)));
    body.appendChild(el('p', 'btnhelp', 'Then, on your machine: ssh -i ' + x.file + ' root@…'));
  }, [{words: 'I have kept it', cls: 'primary', close: true}], 'medium');
}
function skKept(action, extra, b) {
  if (b) busy(b, true);
  var q = {action: action, scope: SK.scope};
  Object.keys(extra || {}).forEach(function (k) { q[k] = extra[k]; });
  api('sshkeys', q).then(function (x) {
    toast(x.message, 'good');
    return api('sshkeys');
  }).then(function (d) { SK.d = d; drawSshKeys(); skPoll(true); })
    .catch(function (e) { if (b) busy(b, false); oops(e); });
}
function skSave(text, file) {
  var a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {type: 'application/octet-stream'}));
  a.download = file;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
}
/* One key's public half as a .pub file, named by its comment. */
function skExport(k) {
  var name = String(k.comment || k.type || 'key').replace(/[^A-Za-z0-9@._-]+/g, '_').replace(/^[._]+/, '').slice(0, 60) || 'key';
  skSave(k.text + '\n', name + '.pub');
  toast('the key is exported as ' + name + '.pub', 'good');
}
function skAdd() {
  var area, pick, pp, ppf;
  modal('Add a key for root', function (body) {
    var p = el('p', 'note');
    p.innerHTML = 'One line of a <code>.pub</code> file: <code>ssh-ed25519 AAAA… you@laptop</code>. Ed25519, ECDSA or RSA of 3072 bits and more; options before the key are not taken here. A private key is taken too: its public half is worked out here and the private half is not kept.';
    body.appendChild(p);
    area = noI18n(el('textarea', 'mono'));
    area.rows = 4; area.spellcheck = false; area.placeholder = 'ssh-ed25519 AAAA… you@laptop';
    body.appendChild(area);
    var fr = el('div', 'btnrow');
    fr.style.margin = '8px 0 4px';
    var pickB = cmdButton('Read a file…', 'upload', 'small');
    var input = el('input'); input.type = 'file'; input.hidden = true;
    pickB.onclick = function () { input.click(); };
    input.onchange = function () {
      var f = input.files && input.files[0];
      if (!f) return;
      if (f.size > 65536) { toast('that file is far bigger than a key', 'warn'); return; }
      f.text().then(function (t) { t = t.trim(); area.value = t.indexOf('PRIVATE KEY') >= 0 ? t : t.split(/\r?\n/)[0]; skAddPp(); });
    };
    fr.appendChild(pickB); fr.appendChild(input);
    body.appendChild(fr);
    pp = maskBox('', '', 'mono');
    ppf = formField('Its passphrase, if the private key has one', pp);
    var skAddPp = function () { ppf.hidden = area.value.indexOf('PRIVATE KEY') < 0; };
    area.oninput = skAddPp;
    skAddPp();
    body.appendChild(ppf);
    pick = skNodePicker(body);
    setTimeout(function () { area.focus(); }, 60);
  }, [{words: 'Cancel', close: true}, {words: 'Add it', cls: 'primary', icon: 'add', close: true, go: function () {
    var nodes = pick();
    api('sshkeys', {action: 'add', line: area.value.trim(), passphrase: pp.value, nodes: nodes}).then(function (x) { toast(x.message, 'good'); skPoll(true); }).catch(oops);
  }}], 'medium');
}
function skDrop(row) {
  var nodes = Object.keys(row.on);
  var last = ((SK.d && SK.d.nodes) || []).filter(function (n) { return row.on[n.name] && (n.keys || []).length <= 1; }).map(function (n) { return n.name; });
  confirmThen('Take the key away', 'Root no longer signs in with <code>' + htmlText(row.k.fp || '') + '</code>' + (row.k.comment ? ' (' + htmlText(row.k.comment) + ')' : '') + ' on ' + htmlText(nodes.join(', ')) + '.'
    + (last.length ? '<br><br><b>It is the last key root signs in with on ' + htmlText(last.join(', ')) + '.</b> Unless root may sign in with a password, nobody reaches it over SSH as root after this.' : ''),
    'Take it away', function () {
      api('sshkeys', {action: 'drop', fp: row.k.fp, nodes: nodes, last_ok: !!last.length}).then(function (x) { toast(x.message, 'good'); skPoll(true); }).catch(oops);
    }, true);
}

/* ---- Settings → System updates (1.0.158) ----------------------------------------
   What each node has waiting, the update one node at a time - out of service,
   dnf or apt, back in service - with its output as it comes, and the restart
   it needs offered at the end. */
var OU = {d: null, poll: null, node: '', hide: false, reboot: '', asked: 0};
try { OU.hide = localStorage.getItem('ai-ou-hide') === '1'; } catch (e) { /* only a convenience */ }
var OU_STATE = {waiting: ['waits its turn', 'dim'], draining: ['out of service', 'warn'],
                updating: ['updating', 'info'], rebooting: ['restarting', 'warn'],
                done: ['done', 'good'], failed: ['failed', 'bad'], skipped: ['left out', 'dim']};
function loadOsup() {
  api('osup').then(function (d) { OU.d = d; drawOsup(); ouPoll(ouLive(d)); }).catch(oops);
}
function ouLive(d) {
  d = d || OU.d || {};
  /* Just asked: the node has not begun yet, followed until it says (1.0.159). */
  if (Date.now() - OU.asked < 30000) return true;
  return (d.plan && d.plan.state === 'running') || (d.nodes || []).some(function (n) { return (n.check || {}).state === 'running'; }) || !!(d.power && d.power.id);
}
function ouPoll(on) {
  if (on && !OU.poll) {
    OU.poll = setInterval(function () {
      if (TAB !== 'settings' || PANE !== 'osup') { ouPoll(false); return; }
      api('osup').then(function (d) { OU.d = d; OU.away = 0; drawOsup(true); if (!ouLive(d)) ouPoll(false); })
        .catch(function () { OU.away = OU.away || Date.now(); drawOsup(true); });
    }, 2500);
  }
  if (!on && OU.poll) { clearInterval(OU.poll); OU.poll = null; }
}
/* Something asked of the nodes: followed from now on. */
function ouAsked() { OU.asked = Date.now(); ouPoll(true); }
/* A button clicked keeps the focus, and a live redraw leaves alone what has
   it - the window that was clicked in stayed as it was (1.0.159). */
function liveLetGo(host) {
  if (!host || host._letGo) return;
  host._letGo = true;
  host.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('button') : null;
    if (b && host.contains(b)) setTimeout(function () { if (document.activeElement === b) b.blur(); }, 0);
  });
}
function ouPercent(r) {
  var st = (r || {}).state;
  if (st === 'done' || st === 'failed') return 100;
  if (st === 'draining') return Math.min(8, 3 + Math.round((Date.now() / 1000 - Number(r.drain_at || r.at || 0)) / 3));
  if (st === 'updating') return Math.max(8, Math.min(95, Number(r.pct || 0)));
  if (st === 'rebooting') return 96;
  return 0;
}
function drawOsup(live) {
  var real = $('ou-host');
  if (!real || !OU.d) return;
  liveLetGo(real);
  liveFill(real, function (host) {
    var d = OU.d, plan = d.plan || {}, nodes = d.nodes || [];
    var running = plan.state === 'running';
    if (OU.away) host.appendChild(el('p', 'note warn', 'This page\'s server is not answering for ' + span(Math.round((Date.now() - OU.away) / 1000)) + ' - restarting, or the web address moving; asked again every few seconds.'));
    /* A restart the update left to do. */
    var need = nodes.filter(function (n) { return n.reboot; });
    if (need.length && !(d.power && d.power.id)) {
      var rb = el('div', 'card full notice warn ou-reboot');
      rb.appendChild(el('h2', '', need.length > 1 ? 'The nodes need a restart' : need[0].name + ' needs a restart'));
      rb.appendChild(el('p', 'note', 'A new kernel or libraries are in that only a restart brings into use. ' + (d.cluster ? 'Restarted one after the other, each in maintenance while it is, the service never stops.' : 'For a minute or two the pages do not answer, and every terminal ends with it.')));
      var go = cmdButton(need.length > 1 ? 'Restart them, one at a time' : 'Restart ' + need[0].name, 'refresh', 'primary');
      go.onclick = function () {
        confirmThen('Restart after the update', 'Restarted now: ' + htmlText(need.map(function (n) { return n.name; }).join(', ')) + (need.length > 1 ? ', one after the other.' : '.'), 'Restart', function () {
          api('osup', {action: 'reboot', nodes: need.map(function (n) { return n.name; })}).then(function (x) { toast(x.message, 'good'); ouAsked(); }).catch(oops);
        }, false);
      };
      rb.appendChild(go);
      host.appendChild(rb);
    }
    if (d.power && d.power.id) host.appendChild(el('p', 'note', 'Restarting: ' + (d.power.targets || []).join(', ') + ' - followed on Restart and power off.'));
    /* What each node has waiting. */
    var grid = el('div', 'pw-grid');
    nodes.forEach(function (n) {
      var c = el('div', 'card pw-node');
      var hd = el('div', 'pw-head');
      hd.appendChild(el('span', 'dot ' + (n.alive ? 'ok' : 'bad')));
      hd.appendChild(noI18n(el('b', '', n.name)));
      if (n.me) hd.appendChild(el('span', 'tag info', 'this page'));
      var ck = n.check || {};
      if (ck.state === 'running') hd.appendChild(el('span', 'tag info', 'looking…'));
      else if (ck.checked && ck.state === 'done') hd.appendChild(el('span', 'tag ' + (ck.count ? 'warn' : 'good'), ck.count ? num(ck.count) + ' waiting' : 'up to date'));
      c.appendChild(hd);
      /* The restart on a line of its own under the name (1.0.35): beside the
         others it ran out of the card. */
      var rs = n.reboot ? el('span', 'tag warn', 'restart needed')
        : (ck.reboot_after && ck.count ? el('span', 'tag info', 'restart after the update') : null);
      if (rs) { var hd2 = el('div', 'pw-head pw-head2'); hd2.appendChild(rs); c.appendChild(hd2); }
      c.appendChild(netFacts([
        ['Updates waiting', ck.checked ? num(ck.count || 0) : 'not looked yet'],
        ['Of them security', ck.security !== undefined && ck.security !== null ? num(ck.security) : ''],
        ['A restart', !ck.checked ? '' : (ck.reboot_now ? 'needed now, before any update'
          : (ck.reboot_after && ck.count ? 'needed after the update - ' + (ck.reboot_why || []).join(', ') : 'not needed by these updates'))],
        ['Looked', ck.checked ? ago(ck.checked) : ''],
        ['Updated by', ck.pm || '', true]
      ]));
      if (ck.error) c.appendChild(el('p', 'note bad', ck.error));
      if ((ck.packages || []).length) {
        var more = el('details', 'fold');
        more.appendChild(el('summary', '', 'what is waiting'));
        more.appendChild(noI18n(el('pre', 'lines', ck.packages.slice(0, 300).join('\n') + (ck.packages.length > 300 ? '\n…' : ''))));
        OU.pkOpen = OU.pkOpen || {};
        if (OU.pkOpen[n.name]) more.open = true;
        more.ontoggle = function () { OU.pkOpen[n.name] = more.open; };
        c.appendChild(more);
      }
      var row = el('div', 'btnrow');
      var look = cmdButton('Look for updates', 'search', '');
      look.disabled = !n.alive || ck.state === 'running' || running;
      look.onclick = function () { busy(look, true); api('osup', {action: 'check', nodes: [n.name]}).then(function (x) { toast(x.message); OU.node = n.name; ouAsked(); }).catch(function (e) { busy(look, false); oops(e); }); };
      row.appendChild(look);
      c.appendChild(row);
      grid.appendChild(c);
    });
    host.appendChild(grid);
    /* The update itself. */
    if (!running) {
      var uc = el('div', 'card full');
      uc.appendChild(el('h2', '', d.cluster ? 'Update the nodes' : 'Update this server'));
      uc.appendChild(el('p', 'note', d.cluster
        ? 'The other node first, then this one - each out of service while it is updated, the web address on the other, RADIUS answered there; back in service before the next one starts.'
        : 'dnf (or apt) updates every package. The terminals go on running meanwhile; a restart it needs is offered at the end.'));
      var segb = el('div', 'seg');
      [['ask', 'Ask me when a restart is needed'], ['auto', 'Restart by itself when needed' + (d.cluster ? ', one at a time' : '')]].forEach(function (o) {
        /* The choice of the last update until another is clicked (1.0.36):
           a page loaded again showed "Ask me" whatever was chosen. */
        var chosen = OU.reboot || (d.reboot_choice === 'auto' ? 'auto' : 'ask');
        var b = el('button', chosen === o[0] ? 'on' : '', o[1]);
        b.type = 'button';
        b.onclick = function () { OU.reboot = o[0]; drawOsup(); };
        segb.appendChild(b);
      });
      var after = nodes.filter(function (n) { var k = n.check || {}; return k.reboot_after && k.count; });
      if (after.length) {
        var an = el('p', 'note warn', (after.length === nodes.length && nodes.length > 1 ? 'Both nodes need' : after.map(function (n) { return n.name; }).join(', ') + (after.length > 1 ? ' need' : ' needs'))
          + ' a restart after this update: ' + after.map(function (n) { return (n.check.reboot_why || []).join(', '); }).filter(function (x, i, a) { return x && a.indexOf(x) === i; }).join('; ') + '.');
        uc.appendChild(an);
      }
      /* Only the security updates, as otp's (1.0.37). */
      var seg2 = el('div', 'seg');
      [['all', 'Every update'], ['security', 'Only the security updates']].forEach(function (o) {
        var b = el('button', (OU.what || 'all') === o[0] ? 'on' : '', o[1]);
        b.type = 'button';
        b.onclick = function () { OU.what = o[0]; drawOsup(); };
        seg2.appendChild(b);
      });
      uc.appendChild(formField('Which', seg2));
      uc.appendChild(formField('After the update', segb));
      var row2 = el('div', 'btnrow');
      var start = cmdButton(d.cluster ? 'Update them, one at a time' : 'Update it now', 'download', 'primary');
      start.disabled = !d.helper || nodes.some(function (n) { return !n.alive; }) || !!(d.power && d.power.id);
      start.onclick = function () {
        confirmThen(d.cluster ? 'Update the nodes' : 'Update this server', 'Every package of the system is updated' + (d.cluster ? ', on ' + htmlText(nodes.map(function (n) { return n.name; }).join(' and then ')) + ', each out of service while it is.' : '.')
          + ((OU.reboot || d.reboot_choice) === 'auto' ? '<br><br>A node that needs it is <b>restarted by itself</b>.' : '<br><br>A restart it needs is offered when it is done.'),
          'Update', function () {
            api('osup', {action: 'start', reboot: OU.reboot || (d.reboot_choice === 'auto' ? 'auto' : 'ask'), security: OU.what === 'security'}).then(function (x) { toast(x.message, 'good'); OU.node = ''; ouAsked(); loadOsup(); }).catch(oops);
          }, false);
      };
      var lookAll = cmdButton(d.cluster ? 'Look on every node' : 'Look again', 'search', '');
      lookAll.onclick = function () { busy(lookAll, true); api('osup', {action: 'check'}).then(function (x) { toast(x.message); ouAsked(); }).catch(function (e) { busy(lookAll, false); oops(e); }); };
      row2.appendChild(start); row2.appendChild(lookAll);
      uc.appendChild(row2);
      if (!d.helper) uc.appendChild(el('p', 'note bad', 'The root helper of this node is not installed (install.sh --upgrade puts it in).'));
      host.appendChild(uc);
    }
    /* How far it is. */
    if (plan.id) {
      var pc = el('div', 'card full');
      var ph = el('h2', '', 'The update');
      if (running) {
        var stop = cmdButton('Stop it', 'cancel', 'small danger');
        explain(stop, 'The nodes not begun stay as they are; a node being updated finishes.');
        stop.onclick = function () { confirmThen('Stop the update', 'The nodes not yet begun stay as they are; one being updated finishes.', 'Stop it', function () { api('osup', {action: 'cancel'}).then(function (x) { toast(x.message); loadOsup(); }).catch(oops); }, true); };
        var tl = el('span', 'right'); tl.appendChild(stop); ph.appendChild(tl);
      }
      pc.appendChild(ph);
      pc.appendChild(el('p', 'note', 'Started by ' + (plan.by || '?') + ' · ' + ago(plan.at) + ' · ' + ({running: 'going on', done: 'done', failed: 'failed', cancelled: 'stopped'})[plan.state || 'running']
        + (plan.reboot === 'auto' ? ' · restarted where needed' : '')));
      var steps = (plan.order || []).map(function (nm) {
        var n = nodes.filter(function (x) { return x.name === nm; })[0] || {name: nm};
        return {name: nm, row: n.row || {}};
      });
      var all = steps.length ? Math.round(steps.reduce(function (m, s) { return m + ouPercent(s.row); }, 0) / steps.length) : 0;
      pc.appendChild(upBar(all, plan.state === 'failed' ? 'bad' : (plan.state === 'done' ? 'good' : ''),
        num(all) + ' % · ' + steps.filter(function (s) { return s.row.state === 'done'; }).length + ' of ' + steps.length + ' node(s) done', true));
      var t = listTable(['Node', 'Step', 'How far', 'What happened', 'When'], steps, function (s) {
        var tr = el('tr');
        tr.appendChild(noI18n(el('td', 'mono', s.name)));
        var w = OU_STATE[s.row.state] || OU_STATE.waiting;
        var c = el('td'); c.appendChild(el('span', 'tag ' + w[1], w[0])); tr.appendChild(c);
        var b2 = el('td', 'up-how');
        var p2 = ouPercent(s.row);
        b2.appendChild(upBar(p2, s.row.state === 'failed' ? 'bad' : (s.row.state === 'done' ? 'good' : ''), num(p2) + ' %' + (s.row.state === 'updating' && s.row.phase ? ' · ' + txT(s.row.phase) : '')));
        tr.appendChild(b2);
        tr.appendChild(el('td', 'small', s.row.said || ''));
        tr.appendChild(el('td', 'muted', s.row.at ? ago(s.row.at) : '–'));
        return tr;
      }, 'plain');
      (t.querySelector('table') || t).classList.add('up-plan-table');
      pc.appendChild(t);
      if (!running) pc.appendChild(hideBar(function () { return api('osup', {action: 'hide'}).then(function (x) { OU.d = x; drawOsup(); }); }));
      host.appendChild(pc);
    }
    /* What the package manager says, a node at a time. */
    var have = nodes.filter(function (n) { return ((n.row || {}).lines || []).length || ((n.check || {}).lines || []).length; });
    if (have.length) {
      if (!OU.node || !have.some(function (n) { return n.name === OU.node; })) {
        var busyOne = have.filter(function (n) { return (n.row || {}).state === 'updating' || (n.check || {}).state === 'running'; })[0];
        OU.node = (busyOne || have[0]).name;
      }
      var lc = el('div', 'card full');
      var lh = el('h2', '', 'What it says');
      var lt = el('span', 'right');
      var hb = cmdButton(OU.hide ? 'Show it' : 'Hide it', OU.hide ? 'unfold' : 'fold', 'small');
      hb.onclick = function () { OU.hide = !OU.hide; try { localStorage.setItem('ai-ou-hide', OU.hide ? '1' : '0'); } catch (e) { /* only a convenience */ } drawOsup(); };
      var cb = cmdButton('Clear the window', 'broom', 'small');
      explain(cb, 'Empty the window of every node - for every page, and after a reload too; what comes after is shown.');
      lt.appendChild(hb); lt.appendChild(cb);
      lh.appendChild(lt);
      lc.appendChild(lh);
      if (have.length > 1) {
        var sg = el('div', 'seg');
        sg.style.marginBottom = '10px';
        have.forEach(function (n) {
          var b3 = noI18n(el('button', OU.node === n.name ? 'on' : '', n.name));
          b3.type = 'button';
          b3.onclick = function () { OU.node = n.name; OU.picked = Date.now(); drawOsup(); };
          sg.appendChild(b3);
        });
        lc.appendChild(sg);
      }
      var one = have.filter(function (n) { return n.name === OU.node; })[0];
      var lines = (one.row || {}).lines && (one.row || {}).lines.length ? one.row.lines : ((one.check || {}).lines || []);
      var from = 0;
      cb.onclick = function () {
        busy(cb, true);
        api('osup', {action: 'clear'}).then(function (x) { OU.d = x; drawOsup(); toast('the window is empty'); })
          .catch(function (e) { busy(cb, false); oops(e); });
      };
      if (!OU.hide) {
        var pre = noI18n(el('pre', 'lines ou-log', lines.slice(from).join('\n') || '–'));
        lc.appendChild(pre);
        setTimeout(function () { pre.scrollTop = pre.scrollHeight; }, 0);
      } else {
        lc.appendChild(el('p', 'muted small', 'Hidden - ' + num(lines.length) + ' line(s).'));
      }
      host.appendChild(lc);
    }
  }, live);
}


/* ---- Settings → Automatic certificates (1.0.39, as otp's 1.0.169-1.0.187) --------
   The card of the certificate: who orders it, what it has now, the last try;
   port 80 tried as the CA will try it; In your DNS with Check DNS. */
function nodeGrid() { return el('div', 'pw-grid node-grid'); }
function nodeCard(n, dot, tag, tagCls) {
  var c = el('div', 'card ntp-node');
  var head = el('div', 'pw-head');
  head.appendChild(el('span', 'dot ' + dot));
  head.appendChild(noI18n(el('b', '', n.node || n.name)));
  if (n.me) head.appendChild(el('span', 'tag info', 'this page'));
  if (tag) head.appendChild(el('span', 'tag ' + (tagCls || 'dim'), tag));
  c.appendChild(head);
  return c;
}
function nodeBig(c, value, words) {
  var big = el('div', 'ntp-big');
  big.appendChild(noI18n(el('span', 'ntp-off', value)));
  if (words) big.appendChild(el('span', 'muted small', ' ' + words));
  c.appendChild(big);
}
function nodeSaid(got, words) {
  var p = el('div', 'node-said ' + (got.ok ? 'ok' : 'bad'));
  p.appendChild(el('span', 'dot ' + (got.ok ? 'ok' : 'bad')));
  var t = el('div');
  t.appendChild(el('b', '', got.error ? 'It did not go' : words));
  if (got.error) t.appendChild(noI18n(el('div', 'small muted', got.error)));
  t.appendChild(el('div', 'small muted', ago(got.at)));
  p.appendChild(t);
  return p;
}
var AC = {d: null, probe: {}, poll: null};
function loadAcme() {
  api('acme').then(function (d) { AC.d = d; drawAcme(); acPoll(d.work && d.work.busy); }).catch(oops);
}
function acPoll(on) {
  if (on && !AC.poll) AC.poll = setInterval(function () {
    if (TAB !== 'settings' || PANE !== 'acme') { acPoll(false); return; }
    api('acme').then(function (d) { AC.d = d; drawAcme(); if (!(d.work && d.work.busy)) acPoll(false); }).catch(function () {});
  }, 2000);
  if (!on && AC.poll) { clearInterval(AC.poll); AC.poll = null; }
}
function drawAcme() {
  var real = $('ac-host');
  if (!real || !AC.d) return;
  liveLetGo(real);
  liveFill(real, function (host) {
    var d = AC.d;
    if (!d.on) host.appendChild(el('p', 'note', 'Off - switch it on below, say which certificates and the CA, and save.'));
    if (d.work && d.work.busy) {
      var g = el('div', 'going wide');
      g.innerHTML = '<div class="bar"><span style="width:60%"></span></div>';
      /* Which certificate, and what is being waited for now (1.0.176). */
      var w = el('div', 'says');
      if (d.work.target) {
        w.appendChild(el('b', '', d.work.target === 'vip' ? 'the VIP address' : d.work.target));
        w.appendChild(document.createTextNode(': '));
      }
      w.appendChild(el('span', '', d.work.says || 'ordering…'));
      g.appendChild(w);
      host.appendChild(g);
    }
    /* By hand (DNS-01): the record to put in, and the order waiting for it. */
    if (d.manual) {
      var mc = el('div', 'card full ac-manual');
      mc.appendChild(el('h2', '', 'Put this TXT record in DNS'));
      mc.appendChild(el('p', 'note warn', 'The order waits for it - up to an hour. Put it in, wait until DNS carries it, then say so. Take it away again once the certificate has come.'));
      mc.appendChild(netFacts([['Name', d.manual.rr, true], ['Type', 'TXT', true], ['Value', d.manual.txt, true], ['TTL', '60', true]]));
      var mr = el('div', 'btnrow');
      var cp = cmdButton('Copy the value', 'copy', 'small');
      cp.onclick = function () { copyText(d.manual.txt); };
      var dn = cmdButton('It is in DNS', 'check', 'small primary');
      dn.disabled = !!d.manual.done;
      dn.onclick = function () { api('acme', {action: 'manual_done'}).then(function (x) { AC.d = x; drawAcme(); acPoll(true); }).catch(oops); };
      var gv = cmdButton('Give the order up', 'close', 'small');
      gv.onclick = function () { api('acme', {action: 'manual_drop'}).then(function (x) { AC.d = x; drawAcme(); }).catch(oops); };
      mr.appendChild(cp); mr.appendChild(dn); mr.appendChild(gv);
      mc.appendChild(mr);
      host.appendChild(mc);
    }
    var grid = nodeGrid();
    (d.targets || []).forEach(function (t) {
      var st = t.state || {};
      var left = t.not_after ? Math.floor((t.not_after - Date.now() / 1000) / 86400) : null;
      var acme = t.how === 'ACME';
      var dot = !acme ? 'dim' : (st.ok === false ? 'warn' : (left !== null && left < 14 ? 'warn' : 'ok'));
      var c = nodeCard({node: t.target === 'vip' ? 'the VIP address' : t.target, me: t.target === d.node}, dot,
        acme ? (st.ok === false ? 'the last try failed' : 'from the CA') : (t.how ? 'not from the CA' : 'no certificate'),
        acme ? (st.ok === false ? 'warn' : 'ok') : 'dim');
      /* Who looks after it (1.0.170): ACME, or the certificate put in on
         Certificates and TLS is kept as it is. */
      var care = el('span', 'tag ' + (t.care && t.wanted ? 'info' : 'dim'),
        !t.wanted ? 'not asked for' : (t.care ? 'ACME renews it' : 'its own certificate is kept'));
      explain(care, !t.wanted ? 'For (Settings below) does not take this one in.'
        : (t.care ? 'Renewed by ACME before it runs out. A certificate put in by hand on Certificates and TLS takes it out of ACME’s care.'
          : 'The certificate put in on Certificates and TLS (uploaded, from a request, self-signed) stays: ACME does not replace it. Look after it, or Order it now, gives it to ACME.'));
      c.querySelector('.pw-head') ? c.querySelector('.pw-head').appendChild(care) : c.appendChild(care);
      nodeBig(c, left !== null ? num(left) : '–', left !== null ? 'days left' : '');
      c.appendChild(netFacts([
        ['For', t.name || '', true], ['Issued by', t.issuer || '', true], ['Keys', t.keys || '', true],
        ['Good until', t.not_after ? new Date(t.not_after * 1000).toLocaleDateString(numLang()) : ''],
        ['Last ordered', st.ordered_at ? ago(st.ordered_at) : 'never'],
        ['Ordered by', t.target === 'vip' ? 'the first node by name' : t.target]
      ]));
      if (st.ok === false && st.said) c.appendChild(nodeSaid({ok: false, error: st.said, at: st.failed_at}, ''));
      /* What the last order did, step by step (1.0.175). */
      if ((st.steps || []).length) {
        var det = el('details', 'acme-steps-done');
        det.appendChild(el('summary', 'small muted', 'What the last order did'));
        var t0 = st.steps[0][0];
        st.steps.forEach(function (x) {
          var r = el('div', 'si-row small');
          r.appendChild(noI18n(el('span', 'muted mono', '+' + Math.round(x[0] - t0) + ' s')));
          r.appendChild(el('span', '', x[1]));
          det.appendChild(r);
        });
        c.appendChild(det);
      }
      var pr = AC.probe[t.target];
      if (pr) c.appendChild(nodeSaid({ok: pr.ok, at: pr.at, error: pr.ok ? '' : pr.said}, 'Port 80 answers as the CA will ask it'));
      var row = el('div', 'btnrow');
      var probe = cmdButton('Try port 80', 'play', 'small');
      probe.hidden = d.challenge === 'dns-01';
      explain(probe, t.name ? 'http://' + t.name + '/.well-known/acme-challenge/ asked from this node, as the CA will ask it - whether it reaches ai. A firewall in front of the servers may still stop the CA from outside.'
        : 'The name of this certificate is not known yet: give it in Settings below (This node’s DNS name, on that node) - or wait until that node says its own full name.');
      probe.disabled = !t.name;
      probe.onclick = function () {
        busy(probe, true);
        api('acme', {action: 'probe', target: t.target}).then(function (x) {
          busy(probe, false); x.at = Date.now() / 1000; AC.probe[t.target] = x; drawAcme();
        }).catch(function (e) { busy(probe, false); oops(e); });
      };
      var order = cmdButton('Order it now', 'download', 'small primary');
      order.disabled = !d.on || !t.name || (d.work && d.work.busy);
      explain(order, !d.on ? 'Switch it on below first.' : (!t.name ? 'Give its name first (Its name…).'
        : 'Ordered from the CA now - from this node for any of them: the CA’s question and the certificate are kept in the database, and ' + (t.target === 'vip' ? 'every node' : t.target) + ' puts it in. ACME renews it from then on.'));
      order.onclick = function () {
        var go = function () {
          busy(order, true);
          api('acme', {action: 'order', target: t.target}).then(function (x) { busy(order, false); toast(x.message, 'good'); AC.d = x; drawAcme(); acPoll(true); })
            .catch(function (e) { busy(order, false); oops(e); });
        };
        if (t.how && !acme) {
          confirmThen('Replace the certificate of ' + (t.target === 'vip' ? 'the VIP address' : t.target) + '?',
            'It has one put in on Certificates and TLS (' + t.how + (t.issuer ? ', ' + t.issuer.replace(/^CN=/, '').split(',')[0] : '') + '). The one from the CA takes its place once it comes, and ACME renews it from then on. Its TLS settings stay as they are.',
            'Order it', go, false);
        } else go();
      };
      var cb = cmdButton(t.care ? 'Leave it alone' : 'Look after it', t.care ? 'cancel' : 'refresh', 'small');
      cb.disabled = !t.wanted;
      explain(cb, t.care ? 'ACME stops renewing this one; the certificate it has stays.'
        : 'ACME renews this one from now on - at the next look (within the hour) if it is not from the CA yet.');
      cb.onclick = function () {
        busy(cb, true);
        api('acme', {action: 'care', target: t.target, on: !t.care}).then(function (x) { AC.d = x; drawAcme(); })
          .catch(function (e) { busy(cb, false); oops(e); });
      };
      /* Every certificate's name from here (1.0.170) - the other node's and
         the VIP address's too. */
      var nm = cmdButton('Its name…', 'edit', 'small');
      explain(nm, t.target === 'vip' ? 'The DNS name of the VIP address - the one people type. It is the VIP address’s own (Settings → High availability) and its certificate is for it.'
        : 'The DNS name the certificate of ' + t.target + ' is for. Empty: the full host name of ' + t.target + '.');
      nm.onclick = function () { acmeNameAsk(t); };
      row.appendChild(probe); row.appendChild(order); row.appendChild(cb); row.appendChild(nm);
      if (t.before && !t.before.ran_out) row.appendChild(acmePutBackButton(t.target, t.before, function (x) { AC.d = x; drawAcme(); }));
      c.appendChild(row);
      grid.appendChild(c);
    });
    host.appendChild(grid);
    if (d.on && d.dns_guide) host.appendChild(acmeDnsGuide(d));
    setTimeout(function () { acmeNamesInSettings(d); }, 0);
    if (d.account && d.account.kid) {
      var a = el('p', 'muted small', 'The account at the CA: ');
      a.appendChild(noI18n(el('span', 'mono', d.account.kid)));
      if (d.account.key) a.appendChild(noI18n(el('span', '', ' · ' + d.account.key)));
      host.appendChild(a);
    }
  });
}

/* The certificate from before ACME (1.0.172): kept when ACME replaced it,
   put back with its key as it was; ACME then leaves it alone. */
function acmePutBackButton(target, before, then) {
  var b = cmdButton('Back to the one before…', 'undo', 'small');
  var words = (before.issuer || '').replace(/^CN=/, '').split(',')[0];
  explain(b, 'The certificate it had before ACME replaced it' + (words ? ' - from ' + words : '') + (before.not_after ? ', good until ' + new Date(before.not_after * 1000).toLocaleDateString(numLang()) : '') + '. Put back as it was; ACME no longer renews this one. The TLS settings stay.');
  b.onclick = function () {
    confirmThen('Put the certificate from before ACME back?', 'The one from the CA is taken out and the one it had before - ' + (words || before.how || '') + ' - put back, on every node that serves it. ACME no longer renews this one (Look after it gives it back).', 'Put it back', function () {
      busy(b, true);
      api('acme', {action: 'put_back', target: target}).then(function (x) { toast(x.message, 'good'); then(x); })
        .catch(function (e) { busy(b, false); oops(e); });
    }, false);
  };
  return b;
}

/* The names of the certificates beside their box (1.0.170): what each node's
   certificate is for now when its box is empty, and the VIP address's name -
   it is the VIP address's own (High availability), changed from here too. */
function acmeNamesInSettings(d) {
  var item = document.querySelector('.set-item[data-key="acme_node_name"]');
  if (!item) return;
  var now = {};
  (d.targets || []).forEach(function (t) { now[t.target] = t.name || ''; });
  var input = $('set-acme_node_name');
  if (input && now[d.node]) input.placeholder = now[d.node];
  Array.prototype.forEach.call(item.querySelectorAll('.node-other[data-node]'), function (row) {
    /* An empty one says the name it stands for, in the place of "(empty)"
       (1.0.172): the words did not fit in a narrow box. */
    var n = row.dataset.node;
    var empty = row.querySelector('.node-empty');
    if (empty && now[n]) {
      var v = noI18n(el('span', 'mono small muted', now[n]));
      v.title = 'none of its own: the name of its certificate, else its full host name';
      row.replaceChild(v, empty);
      var note = row.querySelector('span.muted:not(.mono)');
      if (note) note.textContent = 'by itself';
    }
  });
  var vip = (d.targets || []).filter(function (t) { return t.target === 'vip'; })[0];
  var box = item.querySelector('.node-others');
  var vr = item.querySelector('.node-other.vip');
  if (vr) vr.remove();
  if (!vip) return;
  if (!box) {
    box = el('div', 'node-others small');
    (item.querySelector('.set-tail') || item).appendChild(box);
  }
  vr = el('div', 'node-other vip');
  vr.appendChild(el('span', 'tag dim', 'VIP'));
  vr.appendChild(vip.name ? noI18n(el('span', 'mono small', vip.name)) : el('span', 'node-empty small', '(empty)'));
  vr.appendChild(el('span', 'muted', 'High availability'));
  if (ADMIN) {
    var eb = iconButton('edit', 'Change the name of the VIP address');
    eb.onclick = function () { acmeNameAsk({target: 'vip', name: vip.name}); };
    vr.appendChild(eb);
  }
  box.appendChild(vr);
}
function acmeNameAsk(t) {
  askInModal(t.target === 'vip' ? 'The name of the VIP address' : 'The name of ' + t.target,
    'The full DNS name its certificate is for - it goes into the certificate as its name (CN) and in its alternative names (SAN). The CA gives it only for a name that points at it (HTTP-01) or whose TXT record can be put in (DNS-01).',
    [{label: 'DNS name', placeholder: t.target === 'vip' ? 'ai.example.cz' : t.target + '.example.cz', mono: true, value: t.name || '',
      says: t.target === 'vip' ? 'Empty: the VIP address has no name.' : 'Empty: its full host name, as ' + t.target + ' says it.'}],
    'Keep it', 'save', function (v, b) {
      busy(b, true);
      api('acme', {action: 'name', target: t.target, name: v[0].trim()}).then(function (x) {
        closeModal(); AC.d = x; drawAcme(); toast('kept', 'good');
        if (t.target !== 'vip') loadSettings();
      }).catch(function (e) { busy(b, false); oops(e); });
    });
}

/* In your DNS (1.0.170): what each certificate asked for needs there - by the
   way the CA checks it - the steps of the way chosen, and a check that looks
   each record up from this node. */
var AC_DNS = {at: 0, rows: null};
var ACME_DNS_STEPS = {
  'http-01': ['Each name points at the address that reaches port 80 of its node (or of the VIP address) - from the internet, or from your own CA.',
              'Port 80 is open to it - the firewall in front of the servers, and Firewall and access here.',
              'Try port 80 on each card, then Order it now.'],
  desec: ['Sign up at desec.io (free) and confirm the mail.',
          'Add a domain there: a free one - yourname.dedyn.io - or one of your own whose DNS is at deSEC.',
          'Token management: make a token. Give it below as The deSEC API token, with The domain at deSEC, and save.',
          'In the DNS of your own domain put the CNAME records below - once; they stay for every renewal.',
          'Check DNS here, then Order it now. Renewals go by themselves.'],
  cloudflare: ['A token at Cloudflare (My Profile → API Tokens) with Zone - DNS - Edit for the zone, given below.',
               'Where the DNS of your domain is not at Cloudflare: a zone that is, as The TXT records go into, and the CNAME records below in your DNS.',
               'Order it now. Renewals go by themselves.'],
  rfc2136: ['A TSIG key the DNS server lets update the _acme-challenge records (tsig-keygen), given below with the server and the zone.',
            'With The TXT records go into: the CNAME records below in your DNS, and the key allowed in that zone.',
            'Order it now. Renewals go by themselves.'],
  acmedns: ['Register at the acme-dns server (POST /register) - it gives a user, a key and a subdomain; give them below.',
            'In your DNS put the CNAME records below - once.',
            'Check DNS here, then Order it now. Renewals go by themselves.'],
  manual: ['At every order - renewals too - the TXT record is shown here: put it in your DNS, then say It is in DNS.',
           'Better: a CNAME once in your DNS to a zone ai can write to (deSEC is free) - then nothing is by hand any more.']
};
function acmeDnsGuide(d) {
  var g = d.dns_guide;
  var key = g.challenge === 'http-01' ? 'http-01' : g.dns;
  var card = el('div', 'card full acme-dns');
  var h = el('h2', '', 'In your DNS');
  card.appendChild(h);
  card.appendChild(el('p', 'note', g.challenge === 'http-01'
    ? 'HTTP-01: the CA asks port 80 of each name - so each name points at the node, or the VIP address, and port 80 is open to the CA.'
    : (g.dns === 'manual' ? 'DNS-01 by hand: the CA reads a TXT record you put in at every order.'
      : 'DNS-01: the CA reads a TXT record ai puts in. What has to be in your DNS for it - once - is below.')));
  var ol = el('ol', 'acme-steps');
  (ACME_DNS_STEPS[key] || []).forEach(function (w) { ol.appendChild(el('li', '', w)); });
  card.appendChild(ol);
  var checked = AC_DNS.rows && Date.now() / 1000 - AC_DNS.at < 600 ? AC_DNS.rows : null;
  var rows = (g.rows || []).map(function (r, i) {
    var c = checked && checked[i] && checked[i].record === r.record ? checked[i] : {};
    return Object.assign({}, r, {ok: c.ok, said: c.said});
  });
  /* The copy buttons in columns of their own right after the text (1.0.43):
     one under the other by the table itself - measured after drawing, they
     jumped at every refresh of the page. */
  var copyCell = function (text) {
    var td = el('td', 'dns-btn');
    if (text) {
      var b = iconButton('copy', 'Copy');
      b.onclick = function () { copyText(text, b); };
      td.appendChild(b);
    }
    return td;
  };
  var t = listTable(['Certificate', 'Record', '', 'Type', 'Points at / value', '', 'In DNS now'], rows, function (r) {
    var tr = el('tr');
    tr.appendChild(r.target === 'vip' ? el('td', '', 'the VIP address') : (r.type === 'NS' ? el('td', '', 'its zone at deSEC') : noI18n(el('td', '', r.target))));
    var rec = el('td', 'small dns-txt');
    if (r.record) rec.appendChild(noI18n(el('span', 'mono', r.record)));
    else rec.appendChild(el('span', 'muted', r.why || ''));
    tr.appendChild(rec);
    tr.appendChild(copyCell(r.record));
    tr.appendChild(noI18n(el('td', 'mono small', r.type || '')));
    var val = el('td', 'small dns-txt');
    var shown = r.type === 'CNAME' || r.type === 'NS' || (r.type === 'A' && r.value);
    if (shown) {
      val.appendChild(noI18n(el('span', 'mono', r.value)));
      if (r.type === 'A') val.appendChild(el('div', 'muted', 'or the public address in front of it'));
    } else val.appendChild(el('span', 'muted', r.type === 'TXT' ? (r.value || r.why) : ''));
    tr.appendChild(val);
    tr.appendChild(copyCell(shown ? r.value : ''));
    var st = el('td', 'small');
    if (r.check) {
      if (r.ok === undefined) st.appendChild(el('span', 'muted', 'not checked yet'));
      else {
        var tag = el('span', 'tag ' + (r.ok ? 'ok' : 'warn'), r.ok ? 'there' : 'not yet');
        st.appendChild(tag);
        if (r.said && !r.ok) st.appendChild(el('div', 'muted', r.said));
      }
    } else st.appendChild(el('span', 'muted', r.type === 'TXT' && !r.value ? 'ai puts it in' : '–'));
    tr.appendChild(st);
    return tr;
  });
  card.appendChild(t);
  var row = el('div', 'btnrow');
  var chk = cmdButton('Check DNS', 'search', 'small');
  explain(chk, 'Each record looked up from this node now, through its DNS servers - as the CA will look. A record just put in may take a while to show (its TTL).');
  chk.disabled = !(g.rows || []).some(function (r) { return r.check; });
  chk.onclick = function () {
    busy(chk, true);
    api('acme', {action: 'dns_check'}).then(function (x) {
      AC_DNS = {at: Date.now() / 1000, rows: x.rows, own: x.own_resolvers};
      busy(chk, false); drawAcme();
    }).catch(function (e) { busy(chk, false); oops(e); });
  };
  row.appendChild(chk);
  if (checked && AC_DNS.own === false) {
    card.appendChild(el('p', 'note warn small', 'Checked with this machine’s DNS servers - inside your network they may see what the internet does not. Set DNS servers for ACME (below) to public ones, 1.1.1.1, 9.9.9.9, to see what the CA sees.'));
  }
  if (checked) {
    var when = el('span', 'muted small');
    when.appendChild(el('span', '', 'checked'));
    when.appendChild(document.createTextNode(' '));
    when.appendChild(el('span', '', ago(AC_DNS.at)));
    row.appendChild(when);
  }
  card.appendChild(row);
  return card;
}

/* ---- Settings → Proxy (1.0.47, otp's own) ---------------------------------------- */
var PX = {poll: null};
function drawProxy() {
  var host = $('px-host');
  if (!host) return;
  clear(host);
  var c = el('div', 'card full');
  c.appendChild(el('h2', '', 'Try it'));
  c.appendChild(el('p', 'note', 'An address asked from this node through the proxy as it is saved (whichever uses are switched on), or straight where none is set or the address is in the list. Each step is shown. Empty: where the new versions are looked for.'));
  var row = el('div', 'btnrow');
  var url = el('input');
  url.type = 'text';
  url.placeholder = 'https://github.com/';
  url.style.flex = '1';
  url.style.minWidth = '260px';
  var go = cmdButton('Try it', 'play', 'primary');
  var said = el('div', 'px-out');
  /* Tried on every node (1.0.169): each node's card fills in as it answers. */
  go.onclick = function () {
    busy(go, true);
    clear(said);
    if (PX.poll) { clearInterval(PX.poll); PX.poll = null; }
    api('proxy', {action: 'try', url: url.value.trim()}).then(function (x) {
      var nodes = x.nodes || [];
      var cards = {};
      var grid = nodeGrid();
      nodes.forEach(function (n) {
        var cd = nodeCard({node: n, me: !!(STATUS && n === STATUS.node)}, 'dim', 'being tried', 'info');
        var body = el('div', 'px-out');
        body.appendChild(pxPath(null, n));
        cd.appendChild(body);
        grid.appendChild(cd);
        cards[n] = {body: body, done: false, card: cd};
      });
      said.appendChild(grid);
      var began = Date.now();
      var look = function () {
        api('proxy', {action: 'result', id: x.id}).then(function (r) {
          var left = 0;
          nodes.forEach(function (n) {
            var got = (r.nodes || {})[n];
            if (cards[n].done) return;
            if (!got) { left++; return; }
            cards[n].done = true;
            var hd = cards[n].card.querySelector('.pw-head');
            hd.querySelector('.dot').className = 'dot ' + (got.ok ? 'ok' : 'bad');
            var tg = hd.querySelector('.tag:last-child');
            hd.replaceChild(el('span', 'tag ' + (got.ok ? 'ok' : 'crit'), got.ok ? (got.mode === 'proxy' ? 'through the proxy' : 'straight') : 'not reached'), tg);
            clear(cards[n].body);
            if (got.error) { cards[n].body.appendChild(el('p', 'note bad', got.error)); return; }
            cards[n].body.appendChild(pxPath(got));
            cards[n].body.appendChild(pxSteps(got));
          });
          if (!left || Date.now() - began > 60000) {
            clearInterval(PX.poll); PX.poll = null; busy(go, false);
            nodes.forEach(function (n) {
              if (!cards[n].done) { clear(cards[n].body); cards[n].body.appendChild(el('p', 'note warn', 'This node did not answer in a minute - is it running?')); }
            });
          }
        }).catch(function () {});
      };
      PX.poll = setInterval(look, 1000);
      setTimeout(look, 300);
    }).catch(function (e) { busy(go, false); oops(e); });
  };
  url.addEventListener('keydown', function (e) { if (e.key === 'Enter') go.click(); });
  row.appendChild(url); row.appendChild(go);
  c.appendChild(row);
  c.appendChild(said);
  host.appendChild(c);
}
/* The way it went, drawn: this node, the proxy (when it went through one),
   the address - each link green, red, or still being tried. */
function pxPath(x, nodeName) {
  var box = el('div', 'px-path' + (x ? (x.ok ? ' ok' : ' bad') : ' going'));
  var steps = (x && x.steps) || [];
  var failAt = steps.filter(function (s) { return !s.ok; })[0];
  var stop = function (icon, title, sub, cls) {
    var n = el('div', 'px-stop ' + (cls || ''));
    var ic = el('span', 'px-ic');
    ic.innerHTML = iconMarkup(icon, 22);
    n.appendChild(ic);
    n.appendChild(noI18n(el('b', 'mono', title)));
    if (sub) n.appendChild(el('span', 'muted small', sub));
    return n;
  };
  var link = function (state, words) {
    var l = el('div', 'px-link ' + state);
    l.appendChild(el('span', 'px-wire'));
    if (words) l.appendChild(el('span', 'px-lw small', words));
    return l;
  };
  if (!x) {
    box.appendChild(stop('router', nodeName || (STATUS && STATUS.node) || 'ai', 'the node', 'me'));
    box.appendChild(link('going', 'trying…'));
    box.appendChild(stop('globe', '…', '', ''));
    return box;
  }
  var reached = function (re) { return steps.some(function (s) { return s.ok && re.test(s.what); }); };
  box.appendChild(stop('router', x.node, 'the node', 'me'));
  if (x.mode === 'proxy') {
    var toProxy = reached(/^connected to the proxy/) ? 'ok' : 'bad';
    box.appendChild(link(toProxy, toProxy === 'ok' ? 'connected' : 'not reached'));
    box.appendChild(stop('wall', x.proxy, x.proxy_auth ? 'the proxy · with a password' : 'the proxy', toProxy === 'ok' ? 'good' : 'bad'));
    var through = x.ok ? 'ok' : (toProxy === 'ok' ? 'bad' : 'off');
    box.appendChild(link(through, through === 'ok' ? 'through the proxy' : (through === 'bad' ? 'stopped here' : '')));
  } else {
    var st = x.ok ? 'ok' : 'bad';
    box.appendChild(link(st, 'straight'));
  }
  box.appendChild(stop(x.tls ? 'lock' : 'globe', x.host + ':' + x.port, x.tls ? x.tls.version + ' · ' + (x.tls.issuer || '') : '', x.ok ? 'good' : 'bad'));
  var top = el('div', 'px-verdict ' + (x.ok ? 'ok' : 'bad'));
  top.appendChild(el('span', 'dot ' + (x.ok ? 'ok' : 'bad')));
  var words = x.ok
    ? (x.mode === 'proxy' ? 'Reached through the proxy' : 'Reached straight') + ' - HTTP ' + x.status + ', ' + x.ms + ' ms'
    : 'Not reached: ' + ((failAt && failAt.said) || '?');
  top.appendChild(el('b', '', words));
  if (x.mode === 'direct' && x.why_direct) top.appendChild(el('span', 'muted small', 'straight because ' + x.why_direct));
  var wrap = el('div', 'px-result');
  wrap.appendChild(top);
  wrap.appendChild(box);
  return wrap;
}
function pxSteps(x) {
  var ul = el('div', 'px-steps');
  var plan = x.mode === 'proxy'
    ? ['the proxy looked up', 'connected to the proxy'].concat(/^https/.test(x.url) ? ['a tunnel through the proxy', 'TLS'] : []).concat(['asked for'])
    : ['looked up', 'connected to'].concat(/^https/.test(x.url) ? ['TLS'] : []).concat(['asked for']);
  var done = x.steps || [];
  done.forEach(function (s) {
    var r = el('div', 'px-step ' + (s.ok ? 'ok' : 'bad'));
    r.appendChild(el('span', 'px-n', s.ok ? '✓' : '✗'));
    var t = el('div', 'px-st');
    t.appendChild(el('b', '', s.what));
    if (s.said) t.appendChild(noI18n(el('div', 'muted small mono', s.said)));
    r.appendChild(t);
    r.appendChild(el('span', 'px-ms small muted', s.ms + ' ms'));
    ul.appendChild(r);
  });
  for (var i = done.length; i < plan.length; i++) {
    var r = el('div', 'px-step off');
    r.appendChild(el('span', 'px-n', '○'));
    var t = el('div', 'px-st');
    t.appendChild(el('b', '', 'not tried - the step before stopped it'));
    r.appendChild(t);
    ul.appendChild(r);
  }
  return ul;
}
