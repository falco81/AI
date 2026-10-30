/* usage.js - what the chats with Claude Code used (1.0.13), on the Overview.
   Read from Claude Code's own transcripts by the daemon (/api/usage): every
   chat of the Linux accounts this person may see, with its tokens and what
   they would cost at Anthropic's list prices - and the same by day, hour,
   model, account and folder. A chat is opened in its terminal when that still
   runs, or picked up again (--resume) when it does not. */
'use strict';

var US = {days: 30, data: null, q: '', sort: 'last', show: 'cost'};
try { US.days = Number(localStorage.getItem('ai-usage-days')) || 30; } catch (e) { }

function money(v) {
  if (!v) return '$0';
  if (v < 0.01) return '<$0.01';
  return '$' + (v >= 100 ? Math.round(v).toLocaleString('en-US') : v.toFixed(2));
}
function tok(n) {
  n = Number(n) || 0;
  if (n >= 1e9) return (n / 1e9).toFixed(1) + ' G';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + ' M';
  if (n >= 1e4) return Math.round(n / 1e3) + ' k';
  return num(n);
}
function usSeg(items, value, on) {
  var seg = el('div', 'seg');
  items.forEach(function (it) {
    var b = el('button', it[0] === value ? 'on' : '', it[1]);
    b.type = 'button';
    b.onclick = function () {
      seg.querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', x === b); });
      on(it[0]);
    };
    seg.appendChild(b);
  });
  return seg;
}

function loadUsage() {
  var host = $('ov-usage');
  if (!host) return;
  if (!US.data) { clear(host); host.appendChild(el('p', 'note', 'counting the chats…')); }
  api('usage&days=' + US.days).then(function (d) {
    US.data = d;
    drawUsage();
  }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
}

function drawUsage() {
  var host = $('ov-usage'), d = US.data;
  if (!host || !d) return;
  clear(host);
  var t = d.total;
  var head = el('div', 'us-head');
  var h = el('h2', '', 'Claude Code: what the chats used');
  head.appendChild(h);
  var tools = el('div', 'us-tools');
  tools.appendChild(usSeg([['7', '7 days'], ['30', '30 days'], ['90', '90 days'], ['365', 'a year']], String(US.days), function (v) {
    US.days = Number(v);
    try { localStorage.setItem('ai-usage-days', v); } catch (e) { }
    loadUsage();
  }));
  tools.appendChild(usSeg([['cost', 'cost'], ['tokens', 'tokens']], US.show, function (v) { US.show = v; drawUsage(); }));
  var again = cmdButton('Count again', 'refresh', 'small');
  again.onclick = loadUsage;
  tools.appendChild(again);
  head.appendChild(tools);
  host.appendChild(head);
  host.appendChild(noI18n(el('p', 'muted small us-note', txT('From Claude Code\'s own transcripts of these Linux accounts:') + ' '
    + (d.accounts.length ? d.accounts.join(', ') : '–') + '. '
    + txT('The cost is an estimate at Anthropic\'s list prices per token, to compare by - a Claude subscription is not billed by the token.')
    + (d.unpriced.length ? ' ' + txT('No price known for:') + ' ' + d.unpriced.join(', ') + '.' : ''))));

  var tiles = el('div', 'us-tiles');
  var spent = t.input + t.output + t.cache_write + t.cache_read;
  [['Estimated cost', money(t.cost), 'dollar'],
   ['Chats', num(t.chats), 'terminal'],
   ['Per chat', t.chats ? money(t.cost / t.chats) : '–', 'chart'],
   ['Answers', num(t.messages), 'list'],
   ['Written by Claude', tok(t.output), 'edit'],
   ['Sent', tok(t.input + t.cache_write), 'upload'],
   ['Read from the cache', tok(t.cache_read), 'refresh'],
   ['Cache share', spent ? Math.round(100 * t.cache_read / spent) + ' %' : '–', 'eye']].forEach(function (x) {
    var tl = el('div', 'us-tile');
    var top = el('div', 'us-tile-l');
    top.innerHTML = iconMarkup(x[2], 14);
    top.appendChild(el('span', '', x[0]));
    tl.appendChild(top);
    tl.appendChild(noI18n(el('b', '', x[1])));
    tiles.appendChild(tl);
  });
  host.appendChild(tiles);

  var val = function (x) { return US.show === 'cost' ? x.cost : x.output + x.input + x.cache_write; };
  var say = function (x) { return US.show === 'cost' ? money(x.cost) : tok(x.output + x.input + x.cache_write) + ' ' + txT('tokens'); };
  var bars = function (title, rows, label) {
    var box = el('div', 'us-box');
    box.appendChild(el('h3', '', title));
    if (!rows.length) { box.appendChild(el('p', 'muted small', 'Nothing in these days.')); return box; }
    var most = Math.max.apply(null, rows.map(val).concat([1e-9]));
    var chart = el('div', 'cc-bars us-bars');
    rows.forEach(function (x) {
      var col = el('div', 'cc-bar');
      var fill = el('i');
      fill.style.height = Math.max(2, Math.round(100 * val(x) / most)) + '%';
      col.appendChild(fill);
      explain(col, '<b>' + htmlText(label(x)) + '</b><br>' + say(x) + ' · ' + num(x.messages) + ' ' + txT('answers'));
      col.appendChild(noI18n(el('span', '', label(x))));
      chart.appendChild(col);
    });
    box.appendChild(chart);
    return box;
  };
  var row = el('div', 'us-two');
  row.appendChild(bars('By day', d.by_day, function (x) { return x.key.slice(5); }));
  var hours = [];
  for (var hh = 0; hh < 24; hh++) {
    var k = (hh < 10 ? '0' : '') + hh;
    hours.push(d.by_hour.filter(function (x) { return x.key === k; })[0] || {key: k, cost: 0, output: 0, input: 0, cache_write: 0, cache_read: 0, messages: 0});
  }
  row.appendChild(bars('By hour of the day', hours, function (x) { return x.key; }));
  host.appendChild(row);

  var table = function (title, rows, label, withChats) {
    var box = el('div', 'us-box');
    box.appendChild(el('h3', '', title));
    var total = rows.reduce(function (a, x) { return a + val(x); }, 0) || 1;
    box.appendChild(listTable([label, withChats ? {words: 'Chats', cls: 'num'} : null, {words: 'Answers', cls: 'num'},
      {words: 'Written', cls: 'num'}, {words: 'Cache read', cls: 'num'}, {words: 'Cost', cls: 'num'}, ''].filter(Boolean), rows, function (x) {
      var tr = el('tr');
      tr.appendChild(noI18n(el('td', 'mono small us-key', x.key)));
      if (withChats) tr.appendChild(el('td', 'num', num(x.chats)));
      tr.appendChild(el('td', 'num', num(x.messages)));
      tr.appendChild(el('td', 'num', tok(x.output)));
      tr.appendChild(el('td', 'num muted', tok(x.cache_read)));
      tr.appendChild(noI18n(el('td', 'num', money(x.cost))));
      var share = el('td', 'us-share');
      var bar = el('i');
      bar.style.width = Math.round(100 * val(x) / total) + '%';
      share.appendChild(bar);
      tr.appendChild(share);
      return tr;
    }, 'plain|Nothing in these days'));
    return box;
  };
  var three = el('div', 'us-two');
  three.appendChild(table('By model', d.by_model, 'Model', true));
  if (d.by_account.length > 1) three.appendChild(table('By account', d.by_account, 'Account', true));
  else three.appendChild(table('By folder', d.by_project.slice(0, 12), 'Folder', true));
  host.appendChild(three);
  if (d.by_account.length > 1) host.appendChild(table('By folder', d.by_project.slice(0, 20), 'Folder', true));

  /* Every chat. */
  var chats = el('div', 'us-box');
  var ch = el('div', 'us-chats-head');
  ch.appendChild(el('h3', '', 'The chats'));
  var q = el('input');
  q.type = 'search';
  q.placeholder = txT('find a chat - words, folder, model…');
  q.value = US.q;
  ch.appendChild(q);
  var sort = selectBox([['last', 'newest first'], ['cost', 'the dearest first'], ['messages', 'the longest first'], ['output', 'the most written first']], US.sort);
  ch.appendChild(sort);
  chats.appendChild(ch);
  var list = el('div');
  chats.appendChild(list);
  var drawList = function () {
    var want = US.q.toLowerCase();
    var rows = d.chats.filter(function (c) {
      return !want || (c.title + ' ' + c.cwd + ' ' + c.account + ' ' + c.models.join(' ') + ' ' + c.id).toLowerCase().indexOf(want) >= 0;
    });
    rows.sort(function (a, b) {
      if (US.sort === 'last') return a.last < b.last ? 1 : -1;
      return (b[US.sort] || 0) - (a[US.sort] || 0);
    });
    clear(list);
    list.appendChild(listTable(['Chat', 'Folder', 'Model', {words: 'Answers', cls: 'num'}, {words: 'Written', cls: 'num'},
      {words: 'Sent', cls: 'num'}, {words: 'Cache read', cls: 'num'}, {words: 'Cost', cls: 'num'}, 'Last'], rows.slice(0, 300), function (c) {
      var tr = el('tr', 'clickable');
      var td = el('td', 'us-chat');
      var name = noI18n(el('div', 'us-title', c.title || c.id));
      td.appendChild(name);
      var sub = el('div', 'muted small');
      sub.appendChild(noI18n(el('span', 'mono', c.account)));
      if (c.term) {
        var live = (TL.terms || []).some(function (x) { return x.id === c.term.id && x.state !== 'ended'; });
        sub.appendChild(el('span', 'pill small ' + (live ? 'good' : ''), live ? 'running' : 'its terminal ended'));
      }
      td.appendChild(sub);
      tr.appendChild(td);
      tr.appendChild(noI18n(el('td', 'mono small muted us-key', c.cwd)));
      tr.appendChild(noI18n(el('td', 'small', c.models.map(function (m) { return m.replace(/^claude-/, ''); }).join(', '))));
      tr.appendChild(el('td', 'num', num(c.messages)));
      tr.appendChild(el('td', 'num', tok(c.output)));
      tr.appendChild(el('td', 'num', tok(c.input + c.cache_write)));
      tr.appendChild(el('td', 'num muted', tok(c.cache_read)));
      tr.appendChild(noI18n(el('td', 'num us-cost', money(c.cost))));
      tr.appendChild(el('td', 'muted small', ago(Date.parse(c.last) / 1000)));
      tr.onclick = function () { usageOpen(c); };
      tr.addEventListener('contextmenu', function (e) { e.preventDefault(); usageMenu(c, e.clientX, e.clientY, tr); });
      longPress(tr, function (x, y) { usageMenu(c, x, y, tr); });
      return tr;
    }, 'plain|No chat in these days'));
    if (rows.length > 300 || d.more) list.appendChild(el('p', 'muted small', 'Only the first 300 shown - find a chat to narrow it.'));
  };
  q.addEventListener('input', debounce(function () { US.q = q.value.trim(); drawList(); }, 150));
  sort.onchange = function () { US.sort = sort.value; drawList(); };
  drawList();
  host.appendChild(chats);
  if (typeof explainWhatWasDrawn === 'function') explainWhatWasDrawn(host);
}

/* A chat clicked: its terminal when it still runs, else picked up again. */
function usageOpen(c) {
  var live = c.term && (TL.terms || []).some(function (x) { return x.id === c.term.id && x.state !== 'ended'; });
  if (live) { showTab('terms'); openTerm(c.term.id); return; }
  usageMenu(c, null, null, null);
}
function usageMenu(c, x, y, row) {
  var live = c.term && (TL.terms || []).some(function (t) { return t.id === c.term.id && t.state !== 'ended'; });
  var head = c.title || c.id;
  var items = [{head: head.length > 70 ? head.slice(0, 69) + '…' : head},
    live ? {icon: 'terminal', words: 'Open its terminal', go: function () { showTab('terms'); openTerm(c.term.id); }} : null,
    {icon: 'history', words: 'Pick it up again (--resume)', go: function () {
      resumeIt({id: c.id, cwd: c.cwd, run_as: c.account, summary: c.title}, null);
    }},
    {icon: 'copy', words: 'Copy its ID', go: function () { copyText2(c.id); }},
    {icon: 'copy', words: 'Copy the command to pick it up', go: function () {
      copyText2('cd ' + JSON.stringify(c.cwd) + ' && claude --resume ' + c.id);
    }},
    {icon: 'folder', words: 'Its folder in Files', go: function () { showTab('files'); loadFiles(c.cwd); }}];
  if (x === null) {
    var r = document.querySelector('#ov-usage .us-chats-head').getBoundingClientRect();
    x = r.left + 40; y = r.bottom + 8;
  }
  ctxMenu(x, y, items, row);
}
