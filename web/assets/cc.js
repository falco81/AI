/* cc.js - the Claude Code tab (1.0.9): everything Claude Code reads besides
   its command line, for one Linux account and one project folder - its
   settings, permissions and hooks, its memory (CLAUDE.md), MCP servers,
   agents, commands, skills, output styles, plugins, the sessions it runs in
   the background and what the conversations used. The daemon reads and
   writes the files as that account, and runs Claude Code's own commands
   (claude mcp, claude plugin, claude agents) as it. */
'use strict';

var CC = {as: '', project: '', pane: 'overview', ov: null, rail: {pinned: false}};
var CC_PANES = [
  ['overview', 'sparkle', 'Overview', 'The version, the sign-in, what is set up - and the doctor.'],
  ['settings', 'gear', 'Settings', 'settings.json: the model, the permission mode, the environment and the rest, for you, the project or only you in the project.'],
  ['permissions', 'shield', 'Permissions', 'What Claude Code may do without asking, what it asks first, and what it never does.'],
  ['hooks', 'bolt', 'Hooks', 'Commands run by Claude Code itself before or after a tool, when a prompt is sent, when it stops.'],
  ['memory', 'book', 'Memory', 'CLAUDE.md - what Claude Code reads at the start of every conversation.'],
  ['mcp', 'plug', 'MCP servers', 'The tools and data Claude Code reaches through the Model Context Protocol.'],
  ['agent', 'bot', 'Agents', 'Subagents: a prompt, a model and tools of their own, called by name.'],
  ['command', 'slash', 'Commands', 'Your own /commands: a prompt kept in a file, with arguments.'],
  ['skill', 'puzzle', 'Skills', 'Folders of instructions Claude Code loads when they fit the task.'],
  ['style', 'edit', 'Output styles', 'How Claude Code writes its answers.'],
  ['plugins', 'archive', 'Plugins', 'Plugins and their marketplaces: installed, enabled, updated.'],
  ['background', 'play', 'Background sessions', 'Sessions Claude Code runs on its own (claude --bg): opened, stopped, removed.'],
  ['usage', 'chart', 'Usage', 'The tokens the conversations used, by day, model and folder.'],
  ['keys', 'key', 'Keyboard', 'keybindings.json: Claude Code\'s own keys.']
];
var CC_MODES = [['', 'as Claude Code decides (default)'], ['default', 'ask before changes'], ['acceptEdits', 'accept edits by itself'],
                ['plan', 'plan only'], ['auto', 'auto (a classifier decides)'], ['manual', 'manual (ask for everything)'],
                ['dontAsk', 'do not ask (deny what is not allowed)'], ['bypassPermissions', 'never ask (bypass permissions)']];
var CC_TOOLS = ['Bash', 'Read', 'Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Glob', 'Grep', 'WebFetch', 'WebSearch',
                'Task', 'TodoWrite', 'Skill', 'SlashCommand', 'KillShell', 'BashOutput'];

function ccQ(what, extra) {
  return 'cc&what=' + what + '&as=' + encodeURIComponent(CC.as) + '&project=' + encodeURIComponent(CC.project) + (extra || '');
}
function ccPost(body) {
  return api('cc', Object.assign({as: CC.as, project: CC.project}, body));
}
function ccScopes(kindHasLocal) {
  var s = [['user', 'Mine (all my folders)']];
  if (CC.project) {
    s.push(['project', 'This project (shared, in the repository)']);
    if (kindHasLocal) s.push(['local', 'Mine in this project (not shared)']);
  }
  return s;
}
function ccSeg(items, value, on) {
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
function ccLines(v) { return String(v || '').split('\n').map(function (x) { return x.trim(); }).filter(Boolean); }

/* ---- the frame: who, which project, which pane ---------------------------------- */
function loadCC(sub) {
  if (!CC.as) CC.as = (ME && ME.run_as) || 'root';
  var nav = $('cc-nav');
  if (!nav._made) {
    nav._made = true;
    CC_PANES.forEach(function (p) {
      if (p[0] === 'agent') nav.appendChild(el('div', 'ctl-group', 'Extending it'));
      if (p[0] === 'plugins') nav.appendChild(el('div', 'ctl-group', 'Running it'));
      if (p[0] === 'settings') nav.appendChild(el('div', 'ctl-group', 'Setting it up'));
      var b = el('button', '', p[2]);
      b.type = 'button';
      b.dataset.ccpane = p[0];
      b.dataset.pane = 'cc:' + p[0];
      b.dataset.icon = p[1];
      b.title = p[3];
      b.onclick = function () { ccShow(p[0]); };
      nav.appendChild(b);
    });
    dressButtons(nav);
    ccRail();
    ccHead();
  }
  ccShow(sub || CC.pane);
}
function ccRail() {
  var nav = $('cc-nav'), pin = $('cc-pin'), lay = nav.parentNode;
  pin.innerHTML = iconMarkup('pin', 17);
  var set = function (on) {
    CC.rail.pinned = !!on;
    nav.classList.toggle('pinned', CC.rail.pinned);
    lay.classList.toggle('nav-pinned', CC.rail.pinned);
    pin.setAttribute('aria-pressed', CC.rail.pinned ? 'true' : 'false');
    explain(pin, CC.rail.pinned ? 'The menu is staying open. Press again to let it hide itself at the edge of the screen.'
      : 'The menu hides itself at the edge of the screen and slides out when you point at it. Press this to keep it open.');
    try { localStorage.setItem('ai-cc-rail-pinned', CC.rail.pinned ? '1' : '0'); } catch (e) { }
  };
  pin.onclick = function (e) { e.stopPropagation(); set(!CC.rail.pinned); };
  nav.addEventListener('mouseenter', function () { clearTimeout(CC.rail.shut); CC.rail.open = setTimeout(function () { nav.classList.add('open'); }, 60); });
  nav.addEventListener('mouseleave', function () { clearTimeout(CC.rail.open); CC.rail.shut = setTimeout(function () { nav.classList.remove('open'); }, 260); });
  var was = '0';
  try { was = localStorage.getItem('ai-cc-rail-pinned') || '0'; } catch (e) { }
  set(was === '1');
}
function ccHead() {
  var host = $('cc-head');
  clear(host);
  var row = el('div', 'cc-headrow');
  if (ADMIN) {
    var who = selectBox([[CC.as, CC.as]], CC.as);
    noI18n(who);
    api('linux').then(function (d) {
      clear(who);
      d.accounts.forEach(function (a) { var o = noI18n(el('option', '', a.name)); o.value = a.name; who.appendChild(o); });
      who.value = CC.as;
    }).catch(function () { });
    who.onchange = function () { CC.as = who.value; CC.ov = null; ccShow(CC.pane); };
    row.appendChild(formField('The Linux account', who, 'Whose Claude Code: its home holds its settings, memory and the rest.'));
  }
  var proj = el('div', 'btnrow cc-proj');
  var path = noI18n(el('span', 'mono cc-path', CC.project || txT('no project chosen - only what is yours everywhere')));
  proj.appendChild(path);
  var choose = cmdButton(CC.project ? 'Another project…' : 'Choose a project…', 'folder', 'small');
  choose.onclick = function () {
    pickFolder(CC.project || (STATUS && STATUS.chat_root) || '', function (p) { CC.project = p; CC.ov = null; ccHead(); ccShow(CC.pane); });
  };
  proj.appendChild(choose);
  if (CC.project) {
    var off = cmdButton('Without a project', 'close', 'small');
    off.onclick = function () { CC.project = ''; CC.ov = null; ccHead(); ccShow(CC.pane); };
    proj.appendChild(off);
    var open = cmdButton('A new Claude Code here', 'terminal', 'small primary');
    open.onclick = function () { newTermAsk('claude', CC.project); };
    proj.appendChild(open);
  }
  row.appendChild(formField('The project folder', proj, 'Its .claude folder, CLAUDE.md and .mcp.json - shared with everybody working in it.'));
  host.appendChild(row);
}
function ccShow(name) {
  if (!CC_PANES.some(function (p) { return p[0] === name; })) name = 'overview';
  CC.pane = name;
  document.querySelectorAll('#cc-nav button[data-ccpane]').forEach(function (b) { b.classList.toggle('on', b.dataset.ccpane === name); });
  var host = $('cc-pane');
  clear(host);
  var p = CC_PANES.filter(function (x) { return x[0] === name; })[0];
  var head = el('div', 'ctl-head');
  head.appendChild(el('h2', 'ctl-title', p[2]));
  head.appendChild(el('p', 'ctl-lede', p[3]));
  host.appendChild(head);
  var body = el('div', 'cc-body');
  host.appendChild(body);
  ({overview: ccOverview, settings: ccSettings, permissions: ccPermissions, hooks: ccHooks, memory: ccMemory,
    mcp: ccMcp, agent: ccItems, command: ccItems, skill: ccItems, style: ccItems, plugins: ccPlugins,
    background: ccBackground, usage: ccUsage, keys: ccKeys})[name](body, name);
  if (typeof writeHash === 'function') writeHash();
}

/* ---- overview -------------------------------------------------------------------- */
function ccOverview(body) {
  body.appendChild(el('p', 'note', 'reading…'));
  api(ccQ('overview', '&auth=1')).then(function (d) {
    CC.ov = d;
    clear(body);
    var f = d.facts || {}, a = d.auth || {};
    var card = el('div', 'card full');
    card.appendChild(el('h2', '', 'Claude Code of ' + d.as));
    card.appendChild(peekFacts([
      ['Version', f.version || 'not installed'],
      ['Where', noI18n(el('span', 'mono', f.path || '–'))],
      ['Signed in', a.loggedIn ? (f.email || txT('yes')) + (a.authMethod ? ' · ' + a.authMethod : '') : (a.error ? a.error : 'no')],
      ['Its folder', noI18n(el('span', 'mono', a.configDirectory || (d.home + '/.claude')))]
    ]));
    var acts = el('div', 'btnrow');
    acts.style.marginTop = '12px';
    var login = cmdButton(a.loggedIn ? 'Sign in again' : 'Sign in', 'lock', a.loggedIn ? '' : 'primary');
    login.onclick = function () { api('claude', {do: 'login', run_as: d.as}).then(function (x) { loadTerms(x.id).then(function () { showTab('terms', x.id); }); }).catch(oops); };
    acts.appendChild(login);
    var doc = cmdButton('Ask the doctor', 'check', '');
    doc.onclick = function () {
      busy(doc, true);
      ccPost({action: 'doctor'}).then(function (x) {
        modal('claude doctor', function (b) { b.appendChild(noI18n(el('pre', 'lines', x.text || '–'))); }, [{words: 'Close', close: true}], 'large');
      }).catch(oops).then(function () { busy(doc, false); });
    };
    acts.appendChild(doc);
    if (ADMIN) {
      var up = cmdButton('Update it', 'download', '');
      up.onclick = function () { api('claude', {do: 'update', run_as: d.as}).then(function (x) { loadTerms(x.id).then(function () { showTab('terms', x.id); }); }).catch(oops); };
      acts.appendChild(up);
    }
    card.appendChild(acts);
    body.appendChild(card);
    var grid = el('div', 'cc-grid');
    var tile = function (pane, n, words, icon) {
      var t = el('button', 'cc-tile');
      t.type = 'button';
      t.innerHTML = iconMarkup(icon, 20);
      t.appendChild(el('b', '', num(n)));
      t.appendChild(el('span', '', words));
      t.onclick = function () { ccShow(pane); };
      grid.appendChild(t);
    };
    var c = d.counts || {};
    tile('mcp', d.mcp || 0, 'MCP servers', 'plug');
    tile('agent', c.agent || 0, 'agents', 'bot');
    tile('command', c.command || 0, 'commands', 'slash');
    tile('skill', c.skill || 0, 'skills', 'puzzle');
    tile('style', c.style || 0, 'output styles', 'edit');
    body.appendChild(grid);
    var files = el('div', 'card full');
    files.appendChild(el('h2', '', 'Its files'));
    files.appendChild(listTable(['What', 'Whose', 'File', {words: 'Size', cls: 'num'}], Object.keys(d.files).map(function (k) {
      var bits = k.split(':');
      return {kind: bits[0], scope: bits[1], f: d.files[k]};
    }), function (r) {
      var tr = el('tr', 'tappable');
      tr.appendChild(el('td', '', {settings: 'Settings', memory: 'Memory (CLAUDE.md)', keybindings: 'Keyboard', mcp: 'MCP servers (.mcp.json)'}[r.kind] || r.kind));
      tr.appendChild(el('td', 'muted', {user: 'mine', project: 'the project', local: 'mine in the project'}[r.scope]));
      tr.appendChild(noI18n(el('td', 'mono small' + (r.f.there ? '' : ' muted'), r.f.path)));
      tr.appendChild(el('td', 'num', r.f.there ? bytes(r.f.size) : txT('not there')));
      tr.onclick = function () { ccShow({settings: 'settings', memory: 'memory', keybindings: 'keys', mcp: 'mcp'}[r.kind]); };
      return tr;
    }));
    body.appendChild(files);
  }).catch(function (e) { clear(body); body.appendChild(el('p', 'note bad', String(e.message || e))); });
}

/* ---- a file of Claude Code's, as text ---------------------------------------------- */
function ccText(host, kind, scope, opts) {
  opts = opts || {};
  clear(host);
  host.appendChild(el('p', 'note', 'reading…'));
  return api(ccQ('file', '&kind=' + kind + '&scope=' + scope + (opts.name ? '&name=' + encodeURIComponent(opts.name) : ''))).then(function (d) {
    clear(host);
    var where = el('p', 'muted small');
    where.appendChild(noI18n(el('span', 'mono', d.path)));
    where.appendChild(document.createTextNode(d.there ? '' : ' · ' + txT('not there yet - saving makes it')));
    host.appendChild(where);
    var ta = el('textarea', 'mono cc-text');
    ta.spellcheck = false;
    ta.value = d.text || opts.blank || '';
    ta.rows = opts.rows || 18;
    noI18n(ta);
    host.appendChild(ta);
    var row = el('div', 'btnrow');
    row.style.marginTop = '10px';
    var save = cmdButton('Save it', 'save', 'primary');
    var mtime = d.mtime;
    save.onclick = function () {
      if (opts.json && ta.value.trim()) {
        try { JSON.parse(ta.value); } catch (e) { toast(txT('that is not JSON') + ': ' + e.message, 'bad'); return; }
      }
      busy(save, true);
      ccPost({action: 'write', kind: kind, scope: scope, name: opts.name || '', text: ta.value, mtime: mtime}).then(function (x) {
        mtime = x.mtime;
        toast(x.message, 'good');
        if (opts.saved) opts.saved();
      }).catch(oops).then(function () { busy(save, false); });
    };
    row.appendChild(save);
    var again = cmdButton('Read it again', 'refresh', '');
    again.onclick = function () { ccText(host, kind, scope, opts); };
    row.appendChild(again);
    if (opts.extra) opts.extra(row, ta);
    host.appendChild(row);
    host._ta = ta;
    return d;
  }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
}

/* ---- settings.json: the usual ones as fields, the rest as JSON ------------------- */
var CC_SET_FIELDS = [
  ['model', 'The model', 'select', [['', 'as Claude Code decides']].concat(MODELS.slice(1)), 'A family (always its newest) or one version. Any other name of a model can be written in the JSON below.'],
  ['permissions.defaultMode', 'Permission mode at the start', 'select', CC_MODES, ''],
  ['effortLevel', 'Effort', 'select', [['', 'as Claude Code decides'], ['low', 'low'], ['medium', 'medium'], ['high', 'high'], ['xhigh', 'extra high'], ['max', 'max']], ''],
  ['outputStyle', 'Output style', 'text', null, 'The name of a style: Default, Explanatory, Learning or one of yours.'],
  ['language', 'The language it answers in', 'text', null, 'e.g. czech'],
  ['cleanupPeriodDays', 'Keep the transcripts (days)', 'number', null, ''],
  ['includeCoAuthoredBy', 'Co-Authored-By in commits', 'bool', null, ''],
  ['alwaysThinkingEnabled', 'Thinking always on', 'bool', null, ''],
  ['enableAllProjectMcpServers', 'Let in every server of .mcp.json', 'bool', null, ''],
  ['disableAllHooks', 'Switch every hook off', 'bool', null, ''],
  ['spinnerTipsEnabled', 'Tips while it works', 'bool', null, ''],
  ['autoUpdates', 'Updates itself', 'bool', null, ''],
  ['apiKeyHelper', 'A command that prints the API key', 'text', null, ''],
  ['statusLine.command', 'The status line: a command', 'text', null, 'Its output is shown under the prompt.'],
  ['permissions.additionalDirectories', 'More folders it may use', 'lines', null, 'One a line.'],
  ['env', 'Its environment', 'env', null, 'NAME=value, one a line: set in every session.']
];
function ccGet(o, key) { return key.split('.').reduce(function (a, k) { return a && a[k] !== undefined ? a[k] : undefined; }, o); }
function ccPut(o, key, v) {
  var ks = key.split('.'), last = ks.pop(), cur = o;
  ks.forEach(function (k) { if (typeof cur[k] !== 'object' || cur[k] === null) cur[k] = {}; cur = cur[k]; });
  if (v === undefined || v === '' || (Array.isArray(v) && !v.length) || (typeof v === 'object' && v && !Array.isArray(v) && !Object.keys(v).length)) delete cur[last];
  else cur[last] = v;
  if (ks.length && !Object.keys(cur).length) {
    var parent = ks.slice(0, -1).reduce(function (a, k) { return a[k]; }, o);
    delete parent[ks[ks.length - 1]];
  }
}
function ccSettingsScope(body, render) {
  var scope = CC.setScope || 'user';
  if (!CC.project && scope !== 'user') scope = 'user';
  var bar = el('div', 'cc-scopebar');
  bar.appendChild(ccSeg(ccScopes(true), scope, function (s) { CC.setScope = s; render(s); }));
  if (!CC.project) bar.appendChild(el('span', 'muted small', 'Choose a project above for its own settings.'));
  body.appendChild(bar);
  var host = el('div');
  body.appendChild(host);
  CC._host = host;
  render(scope);
}
function ccSettingsJson(scope, then) {
  return api(ccQ('file', '&kind=settings&scope=' + scope)).then(function (d) {
    var obj = {};
    if (d.text && d.text.trim()) {
      try { obj = JSON.parse(d.text); } catch (e) { obj = null; }
    }
    then(d, obj);
  });
}
function ccSettingsSave(scope, obj, mtime) {
  return ccPost({action: 'write', kind: 'settings', scope: scope, text: JSON.stringify(obj, null, 2) + '\n', mtime: mtime});
}
function ccSettings(body) {
  ccSettingsScope(body, function (scope) {
    var host = CC._host;
    clear(host);
    ccSettingsJson(scope, function (d, obj) {
      clear(host);
      if (obj === null) {
        host.appendChild(el('p', 'note bad', 'The file is not JSON Claude Code can read - put it right in the text below.'));
        ccText(host, 'settings', scope, {json: true, rows: 22});
        return;
      }
      host.appendChild(noI18n(el('p', 'muted small mono', d.path)));
      var card = el('div', 'card full');
      var g = el('div', 'formgrid cc-form');
      var boxes = {};
      CC_SET_FIELDS.forEach(function (f) {
        var v = ccGet(obj, f[0]), box;
        if (f[2] === 'select') {
          var opts = f[3].slice();
          if (v && !opts.some(function (o) { return o[0] === v; })) opts.push([v, v]);
          box = selectBox(opts, v || '');
        } else if (f[2] === 'bool') {
          box = selectBox([['', 'as Claude Code decides'], ['1', 'yes'], ['0', 'no']], v === true ? '1' : (v === false ? '0' : ''));
        } else if (f[2] === 'lines' || f[2] === 'env') {
          box = el('textarea', 'mono');
          box.rows = 3;
          box.value = f[2] === 'env' ? Object.keys(v || {}).map(function (k) { return k + '=' + v[k]; }).join('\n') : (v || []).join('\n');
          noI18n(box);
        } else {
          box = textBox(v === undefined ? '' : String(v), '', 'mono');
          if (f[2] === 'number') box.type = 'number';
          noI18n(box);
        }
        boxes[f[0]] = box;
        var ff = formField(f[1], box, f[4] || '');
        if (f[2] === 'lines' || f[2] === 'env') ff.classList.add('span-2');
        g.appendChild(ff);
      });
      card.appendChild(g);
      var row = el('div', 'btnrow');
      row.style.marginTop = '12px';
      var save = cmdButton('Save the settings', 'save', 'primary');
      save.onclick = function () {
        CC_SET_FIELDS.forEach(function (f) {
          var b = boxes[f[0]], v;
          if (f[2] === 'bool') v = b.value === '' ? undefined : b.value === '1';
          else if (f[2] === 'number') v = b.value.trim() === '' ? undefined : Number(b.value);
          else if (f[2] === 'lines') v = ccLines(b.value);
          else if (f[2] === 'env') {
            v = {};
            ccLines(b.value).forEach(function (l) { var i = l.indexOf('='); if (i > 0) v[l.slice(0, i).trim()] = l.slice(i + 1); });
          } else v = b.value.trim() || undefined;
          ccPut(obj, f[0], v);
        });
        if (obj.statusLine && obj.statusLine.command && !obj.statusLine.type) obj.statusLine.type = 'command';
        busy(save, true);
        ccSettingsSave(scope, obj, d.mtime).then(function (x) { toast(x.message, 'good'); ccShow('settings'); }).catch(oops).then(function () { busy(save, false); });
      };
      row.appendChild(save);
      card.appendChild(row);
      host.appendChild(card);
      var raw = el('details', 'card full cc-raw');
      raw.appendChild(el('summary', '', 'All of it as JSON'));
      var rawHost = el('div');
      raw.appendChild(rawHost);
      raw.ontoggle = function () { if (raw.open && !rawHost._done) { rawHost._done = true; ccText(rawHost, 'settings', scope, {json: true, rows: 22, saved: function () { ccShow('settings'); }}); } };
      host.appendChild(raw);
    }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
  });
}

/* ---- permissions: allow, ask, deny ------------------------------------------------- */
function ccPermissions(body) {
  ccSettingsScope(body, function (scope) {
    var host = CC._host;
    clear(host);
    ccSettingsJson(scope, function (d, obj) {
      clear(host);
      if (obj === null) { host.appendChild(el('p', 'note bad', 'The settings file is not JSON - put it right under Settings first.')); return; }
      var perm = obj.permissions || {};
      var lists = {allow: (perm.allow || []).slice(), ask: (perm.ask || []).slice(), deny: (perm.deny || []).slice()};
      var card = el('div', 'card full');
      card.appendChild(el('p', 'note', 'A rule is a tool, and what of it in brackets: Bash(npm run test:*), Read(./secrets/**), Edit(src/**), WebFetch(domain:example.com), mcp__github. Deny wins over ask, ask over allow.'));
      var add = el('div', 'btnrow cc-rule-add');
      var which = selectBox([['allow', 'allow it'], ['ask', 'ask first'], ['deny', 'never']], 'allow');
      var tool = selectBox(CC_TOOLS.map(function (t) { return [t, t]; }).concat([['mcp__', 'an MCP tool (mcp__…)']]), 'Bash');
      var spec = textBox('', 'npm run test:*', 'mono');
      spec.style.flex = '1';
      noI18n(spec);
      var put = cmdButton('Add the rule', 'add', 'primary');
      put.onclick = function () {
        var s = spec.value.trim();
        var rule = tool.value === 'mcp__' ? (s.indexOf('mcp__') === 0 ? s : 'mcp__' + s) : (s ? tool.value + '(' + s + ')' : tool.value);
        if (rule === 'mcp__') { toast('which MCP tool?', 'bad'); return; }
        if (lists[which.value].indexOf(rule) < 0) lists[which.value].push(rule);
        spec.value = '';
        draw();
      };
      [which, tool, spec, put].forEach(function (x) { add.appendChild(x); });
      card.appendChild(add);
      var tables = el('div', 'cc-rules');
      card.appendChild(tables);
      var draw = function () {
        clear(tables);
        [['deny', 'Never', 'crit'], ['ask', 'Ask first', 'warn'], ['allow', 'Allowed without asking', 'ok']].forEach(function (k) {
          var box = el('div', 'cc-rulebox');
          var h = el('h3', '');
          h.appendChild(el('span', 'tag ' + k[2], k[1]));
          h.appendChild(el('span', 'muted small', ' ' + num(lists[k[0]].length)));
          box.appendChild(h);
          if (!lists[k[0]].length) box.appendChild(el('p', 'muted small', 'none'));
          lists[k[0]].forEach(function (r, i) {
            var line = el('div', 'cc-rule');
            line.appendChild(noI18n(el('span', 'mono', r)));
            var x = iconButton('trash', 'Take the rule away');
            x.onclick = function () { lists[k[0]].splice(i, 1); draw(); };
            line.appendChild(x);
            box.appendChild(line);
          });
          tables.appendChild(box);
        });
      };
      draw();
      var row = el('div', 'btnrow');
      row.style.marginTop = '12px';
      var save = cmdButton('Save the permissions', 'save', 'primary');
      save.onclick = function () {
        ccPut(obj, 'permissions.allow', lists.allow);
        ccPut(obj, 'permissions.ask', lists.ask);
        ccPut(obj, 'permissions.deny', lists.deny);
        busy(save, true);
        ccSettingsSave(scope, obj, d.mtime).then(function (x) { toast(x.message, 'good'); ccShow('permissions'); }).catch(oops).then(function () { busy(save, false); });
      };
      row.appendChild(save);
      card.appendChild(row);
      host.appendChild(card);
    }).catch(oops);
  });
}

/* ---- hooks -------------------------------------------------------------------------- */
var CC_EVENTS = [['PreToolUse', 'before a tool is used (it may stop it)'], ['PostToolUse', 'after a tool was used'],
                 ['PostToolUseFailure', 'after a tool failed'], ['UserPromptSubmit', 'when a prompt is sent'],
                 ['PermissionRequest', 'when it asks for a permission'], ['Notification', 'when it says something to you'],
                 ['Stop', 'when it stops answering'], ['SubagentStart', 'when a subagent starts'], ['SubagentStop', 'when a subagent stops'],
                 ['PreCompact', 'before the conversation is compacted'], ['SessionStart', 'when a session starts'],
                 ['SessionEnd', 'when a session ends']];
function ccHooks(body) {
  ccSettingsScope(body, function (scope) {
    var host = CC._host;
    clear(host);
    ccSettingsJson(scope, function (d, obj) {
      clear(host);
      if (obj === null) { host.appendChild(el('p', 'note bad', 'The settings file is not JSON - put it right under Settings first.')); return; }
      var hooks = JSON.parse(JSON.stringify(obj.hooks || {}));
      var rows = [];
      Object.keys(hooks).forEach(function (ev) {
        (hooks[ev] || []).forEach(function (grp) {
          (grp.hooks || []).forEach(function (h) { rows.push({ev: ev, matcher: grp.matcher || '', cmd: h.command || h.prompt || '', type: h.type || 'command', timeout: h.timeout || ''}); });
        });
      });
      var card = el('div', 'card full');
      card.appendChild(el('p', 'note', 'Each hook is a command Claude Code runs itself, with the event as JSON on its input. A matcher picks the tools (Bash, Edit|Write, mcp__.*); empty is every one. An exit code of 2 stops the tool and tells Claude why.'));
      var add = el('div', 'formgrid');
      var ev = selectBox(CC_EVENTS.map(function (e) { return [e[0], e[0] + ' - ' + e[1]]; }), 'PreToolUse');
      var matcher = textBox('', 'Bash', 'mono');
      var cmd = textBox('', '~/.claude/hooks/check.sh', 'mono');
      var tmo = textBox('', '60', 'mono');
      tmo.type = 'number';
      [matcher, cmd, tmo].forEach(noI18n);
      add.appendChild(formField('When', ev));
      add.appendChild(formField('For the tools (a matcher)', matcher));
      var fc = formField('The command', cmd);
      fc.classList.add('span-2');
      add.appendChild(fc);
      add.appendChild(formField('Its time (s)', tmo));
      card.appendChild(add);
      var put = cmdButton('Add the hook', 'add', 'primary');
      put.style.marginTop = '8px';
      put.onclick = function () {
        if (!cmd.value.trim()) { toast('which command?', 'bad'); return; }
        rows.push({ev: ev.value, matcher: matcher.value.trim(), cmd: cmd.value.trim(), type: 'command', timeout: tmo.value.trim()});
        cmd.value = '';
        draw();
      };
      card.appendChild(put);
      var list = el('div');
      list.style.marginTop = '14px';
      card.appendChild(list);
      var draw = function () {
        clear(list);
        if (!rows.length) { list.appendChild(el('p', 'muted', 'No hook yet.')); return; }
        list.appendChild(listTable(['When', 'Tools', 'Command', {words: 'Time', cls: 'num'}, ''], rows, function (r) {
          var tr = el('tr');
          tr.appendChild(noI18n(el('td', 'mono', r.ev)));
          tr.appendChild(noI18n(el('td', 'mono small', r.matcher || '*')));
          tr.appendChild(noI18n(el('td', 'mono small', (r.type !== 'command' ? '[' + r.type + '] ' : '') + r.cmd)));
          tr.appendChild(el('td', 'num muted', r.timeout ? r.timeout + ' s' : '–'));
          var t = el('td', 'rowtools');
          var x = iconButton('trash', 'Take it away');
          x.onclick = function () { rows.splice(rows.indexOf(r), 1); draw(); };
          t.appendChild(x);
          tr.appendChild(t);
          return tr;
        }));
      };
      draw();
      var save = cmdButton('Save the hooks', 'save', 'primary');
      save.style.marginTop = '12px';
      save.onclick = function () {
        var out = {};
        rows.forEach(function (r) {
          var list2 = out[r.ev] = out[r.ev] || [];
          var grp = list2.filter(function (g) { return (g.matcher || '') === r.matcher; })[0];
          if (!grp) { grp = r.matcher ? {matcher: r.matcher, hooks: []} : {hooks: []}; list2.push(grp); }
          var h = r.type === 'command' ? {type: 'command', command: r.cmd} : {type: r.type, prompt: r.cmd};
          if (r.timeout) h.timeout = Number(r.timeout);
          grp.hooks.push(h);
        });
        ccPut(obj, 'hooks', out);
        busy(save, true);
        ccSettingsSave(scope, obj, d.mtime).then(function (x) { toast(x.message, 'good'); ccShow('hooks'); }).catch(oops).then(function () { busy(save, false); });
      };
      card.appendChild(save);
      host.appendChild(card);
    }).catch(oops);
  });
}

/* ---- memory --------------------------------------------------------------------------- */
function ccMemory(body) {
  var scope = CC.memScope || 'user';
  if (!CC.project) scope = 'user';
  var bar = el('div', 'cc-scopebar');
  var host = el('div', 'card full');
  bar.appendChild(ccSeg([['user', 'Mine (~/.claude/CLAUDE.md)']].concat(CC.project ? [['project', 'The project (CLAUDE.md)'], ['local', 'Mine in the project (CLAUDE.local.md)']] : []), scope, function (s) {
    CC.memScope = s;
    ccText(host, 'memory', s, {rows: 24, blank: s === 'user' ? '# What I want everywhere\n\n' : '# This project\n\n'});
  }));
  body.appendChild(bar);
  body.appendChild(el('p', 'note', 'Markdown. A line @path/to/file brings another file in; # at the start of a prompt in a session adds a line here.'));
  body.appendChild(host);
  ccText(host, 'memory', scope, {rows: 24, blank: scope === 'user' ? '# What I want everywhere\n\n' : '# This project\n\n'});
}

/* ---- MCP servers ------------------------------------------------------------------------ */
function ccMcp(body) {
  var list = el('div', 'card full');
  body.appendChild(list);
  var draw = function (servers) {
    clear(list);
    var h = el('h2', '');
    h.appendChild(el('span', '', 'The servers'));
    var right = el('span', 'right');
    var check = cmdButton('Check them', 'check', 'small');
    check.onclick = function () {
      busy(check, true);
      api(ccQ('mcp', '&check=1')).then(function (d) {
        modal('claude mcp list', function (b) { b.appendChild(noI18n(el('pre', 'lines', d.check || '–'))); }, [{words: 'Close', close: true}], 'large');
      }).catch(oops).then(function () { busy(check, false); });
    };
    right.appendChild(check);
    var add = cmdButton('Add a server', 'add', 'small primary');
    add.onclick = function () { ccMcpAdd(); };
    right.appendChild(add);
    h.appendChild(right);
    list.appendChild(h);
    if (!servers.length) { list.appendChild(el('p', 'muted', 'No MCP server for this account' + (CC.project ? ' and project.' : '.'))); return; }
    list.appendChild(listTable(['Name', 'Whose', 'Kind', 'What it runs', 'Secrets', ''], servers, function (s) {
      var tr = el('tr');
      tr.appendChild(noI18n(el('td', 'mono', s.name)));
      var w = el('td');
      w.appendChild(el('span', 'tag ' + ({user: 'info', project: 'violet', local: 'dim'}[s.scope]), {user: 'mine', project: 'the project', local: 'mine in the project'}[s.scope]));
      if (s.scope === 'project') w.appendChild(el('span', 'sub', s.approved ? 'let in' : (s.denied ? 'kept out' : 'waiting to be let in')));
      tr.appendChild(w);
      tr.appendChild(el('td', 'muted', s.type || (s.url ? 'http' : 'stdio')));
      tr.appendChild(noI18n(el('td', 'mono small', s.url || ((s.command || '') + ' ' + (s.args || []).join(' ')))));
      tr.appendChild(noI18n(el('td', 'mono small muted', Object.keys(s.env || {}).concat(Object.keys(s.headers || {})).join(', ') || '–')));
      var t = el('td', 'rowtools');
      if (s.scope === 'project') {
        var yes = iconButton(s.approved ? 'ban' : 'check', s.approved ? 'Keep it out of this project' : 'Let it in for this project');
        yes.onclick = function () { ccPost({action: 'mcp_approve', name: s.name, scope: 'project', yes: !s.approved}).then(function (x) { toast(x.message, 'good'); draw(x.servers); }).catch(oops); };
        t.appendChild(yes);
      }
      var x = iconButton('trash', 'Take the server away');
      x.onclick = function () {
        confirmThen('Take ' + s.name + ' away?', htmlText('claude mcp remove -s ' + s.scope + ' ' + s.name), 'Take it away', function () {
          ccPost({action: 'mcp_remove', name: s.name, scope: s.scope}).then(function (r) { toast(r.message, 'good'); draw(r.servers); }).catch(oops);
        }, true);
      };
      t.appendChild(x);
      tr.appendChild(t);
      return tr;
    }));
  };
  list.appendChild(el('p', 'note', 'reading…'));
  api(ccQ('mcp')).then(function (d) { draw(d.servers); }).catch(oops);
  CC._mcpDraw = draw;
}
function ccMcpAdd() {
  modal('An MCP server', function (body) {
    var g = el('div', 'formgrid');
    var name = textBox('', 'github', 'mono');
    var scope = selectBox(ccScopes(true).map(function (s) { return [s[0], s[1]]; }), CC.project ? 'local' : 'user');
    var kind = selectBox([['stdio', 'a command on this machine (stdio)'], ['http', 'an address (HTTP)'], ['sse', 'an address (SSE)']], 'stdio');
    var cmd = textBox('', 'npx', 'mono');
    var args = el('textarea', 'mono'); args.rows = 3; args.placeholder = '-y\n@modelcontextprotocol/server-filesystem\n/srv';
    var url = textBox('', 'https://mcp.example.com/mcp', 'mono');
    var env = el('textarea', 'mono'); env.rows = 3; env.placeholder = 'API_KEY=…';
    var headers = el('textarea', 'mono'); headers.rows = 2; headers.placeholder = 'Authorization: Bearer …';
    [name, cmd, args, url, env, headers].forEach(noI18n);
    g.appendChild(formField('Its name', name));
    g.appendChild(formField('Whose', scope));
    g.appendChild(formField('What it is', kind));
    var fCmd = formField('The command', cmd), fArgs = formField('Its arguments, one a line', args);
    var fUrl = formField('The address', url), fHead = formField('Headers, one a line', headers);
    var fEnv = formField('Its environment (NAME=value, one a line)', env);
    [fCmd, fArgs, fUrl, fHead, fEnv].forEach(function (f) { g.appendChild(f); });
    fArgs.classList.add('span-2'); fEnv.classList.add('span-2');
    var show = function () {
      var web = kind.value !== 'stdio';
      fCmd.hidden = fArgs.hidden = fEnv.hidden = web;
      fUrl.hidden = fHead.hidden = !web;
    };
    kind.onchange = show;
    show();
    body.appendChild(g);
    body.appendChild(el('p', 'btnhelp', 'Added with claude mcp add-json, as the account - Claude Code keeps it where it keeps its own.'));
    MODAL_GO = function (b) {
      var conf = {type: kind.value};
      if (kind.value === 'stdio') {
        conf.command = cmd.value.trim();
        conf.args = ccLines(args.value);
        var e = {};
        ccLines(env.value).forEach(function (l) { var i = l.indexOf('='); if (i > 0) e[l.slice(0, i).trim()] = l.slice(i + 1); });
        if (Object.keys(e).length) conf.env = e;
      } else {
        conf.url = url.value.trim();
        var h = {};
        ccLines(headers.value).forEach(function (l) { var i = l.indexOf(':'); if (i > 0) h[l.slice(0, i).trim()] = l.slice(i + 1).trim(); });
        if (Object.keys(h).length) conf.headers = h;
      }
      busy(b, true);
      ccPost({action: 'mcp_add', name: name.value.trim(), scope: scope.value, config: conf}).then(function (x) {
        toast(x.message, 'good');
        closeModal();
        if (CC._mcpDraw) CC._mcpDraw(x.servers);
      }).catch(oops).then(function () { busy(b, false); });
    };
  }, [{words: 'Close', close: true}, {words: 'Add it', cls: 'primary', icon: 'add', go: function (b) { MODAL_GO(b); }}], 'wide');
}

/* ---- agents, commands, skills, output styles ---------------------------------------- */
var CC_ITEM = {
  agent: {one: 'agent', blank: 'You are …\n', fields: [['description', 'When it is used', 'Reviews code for security problems. Use after every change.'], ['tools', 'Its tools (empty: all)', 'Read, Grep, Glob'], ['model', 'Its model', 'sonnet'], ['color', 'Its colour', 'blue']]},
  command: {one: 'command', blank: 'Look at $ARGUMENTS and …\n', fields: [['description', 'What it does', 'Writes the release notes'], ['argument-hint', 'Its arguments', '[version]'], ['allowed-tools', 'Tools it may use', 'Bash(git log:*)'], ['model', 'Its model', '']]},
  skill: {one: 'skill', blank: '# How to …\n\n1. …\n', fields: [['description', 'When to use it', 'Deploys the site. Use when asked to deploy or publish.'], ['allowed-tools', 'Tools it may use', '']]},
  style: {one: 'style', blank: 'Answer …\n', fields: [['description', 'What it is', 'Short answers, with the reasons'], ['keep-coding-instructions', 'Keep the coding instructions (true/false)', 'true']]}
};
function ccItems(body, kind) {
  var spec = CC_ITEM[kind];
  var card = el('div', 'card full');
  body.appendChild(card);
  var draw = function () {
    clear(card);
    var h = el('h2', '');
    h.appendChild(el('span', '', {agent: 'The agents', command: 'The commands', skill: 'The skills', style: 'The output styles'}[kind]));
    var right = el('span', 'right');
    var add = cmdButton({agent: 'A new agent', command: 'A new command', skill: 'A new skill', style: 'A new style'}[kind], 'add', 'small primary');
    add.onclick = function () { ccItemEdit(kind, null, draw); };
    right.appendChild(add);
    h.appendChild(right);
    card.appendChild(h);
    card.appendChild(el('p', 'note', {agent: 'Claude Code calls one by itself when its description fits, or when asked: "use the reviewer agent".',
      command: 'Typed as /name in a session; $ARGUMENTS is what follows it, $1 $2 one word each. A folder makes /folder:name.',
      skill: 'Each is a folder with SKILL.md; Claude Code reads its description and loads it when it fits the task.',
      style: 'Chosen with /output-style, or as the output style in Settings.'}[kind]));
    var list = el('div');
    card.appendChild(list);
    list.appendChild(el('p', 'note', 'reading…'));
    api(ccQ('items', '&kind=' + kind)).then(function (d) {
      clear(list);
      if (!d.items.length) { list.appendChild(el('p', 'muted', 'None yet.')); return; }
      list.appendChild(listTable(['Name', 'Whose', 'What it is', kind === 'agent' ? 'Model' : 'Size', 'Changed', ''], d.items, function (it) {
        var tr = el('tr', 'tappable');
        tr.appendChild(noI18n(el('td', 'mono', (kind === 'command' ? '/' : '') + it.name.replace('/', ':'))));
        tr.appendChild(el('td', '', it.scope === 'user' ? 'mine' : 'the project'));
        tr.appendChild(noI18n(el('td', 'small', it.description || '')));
        tr.appendChild(kind === 'agent' ? noI18n(el('td', 'mono small', it.model || '–')) : el('td', 'num muted', bytes(it.size)));
        tr.appendChild(stampCell(it.mtime));
        var t = el('td', 'rowtools');
        var x = iconButton('trash', 'Delete it');
        x.onclick = function (ev) {
          ev.stopPropagation();
          confirmThen('Delete ' + it.name + '?', htmlText(it.path), 'Delete it', function () {
            ccPost({action: 'delete', kind: kind, scope: it.scope, name: it.name}).then(function (r) { toast(r.message, 'good'); draw(); }).catch(oops);
          }, true);
        };
        t.appendChild(x);
        tr.appendChild(t);
        tr.onclick = function () { ccItemEdit(kind, it, draw); };
        tr.addEventListener('contextmenu', function (ev) {
          ev.preventDefault();
          ctxMenu(ev.clientX, ev.clientY, [{head: it.name}, {icon: 'edit', words: 'Edit it', go: function () { ccItemEdit(kind, it, draw); }},
            {icon: 'copy', words: 'Copy its path', go: function () { copyText2(it.path); }}, 'sep',
            {icon: 'trash', words: 'Delete it', danger: true, go: function () { x.click(); }}]);
        });
        return tr;
      }));
    }).catch(function (e) { clear(list); list.appendChild(el('p', 'note bad', String(e.message || e))); });
  };
  draw();
}
function ccSplitFront(text) {
  var m = /^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/.exec(text || '');
  if (!m) return {front: {}, body: text || ''};
  var front = {};
  m[1].split('\n').forEach(function (l) { var i = l.indexOf(':'); if (i > 0 && l[0] !== ' ') front[l.slice(0, i).trim()] = l.slice(i + 1).trim().replace(/^["']|["']$/g, ''); });
  return {front: front, body: m[2]};
}
function ccItemEdit(kind, it, done) {
  var spec = CC_ITEM[kind];
  modal(it ? it.name : {agent: 'A new agent', command: 'A new command', skill: 'A new skill', style: 'A new output style'}[kind], function (body) {
    var g = el('div', 'formgrid');
    var name = textBox(it ? it.name : '', kind === 'command' ? 'release-notes' : 'reviewer', 'mono');
    noI18n(name);
    if (it) name.disabled = true;
    var scope = selectBox(ccScopes(false), it ? it.scope : (CC.project ? 'project' : 'user'));
    if (it) scope.disabled = true;
    g.appendChild(formField('Its name', name, kind === 'command' ? 'Letters, digits, - and _; a folder/name for /folder:name.' : 'Letters, digits, - and _.'));
    g.appendChild(formField('Whose', scope));
    var boxes = {};
    spec.fields.forEach(function (f) {
      var b = textBox('', f[2], 'mono');
      noI18n(b);
      boxes[f[0]] = b;
      var ff = formField(f[1], b);
      if (f[0] === 'description') ff.classList.add('span-2');
      g.appendChild(ff);
    });
    body.appendChild(g);
    var ta = el('textarea', 'mono cc-text');
    ta.rows = 16;
    ta.spellcheck = false;
    noI18n(ta);
    body.appendChild(formField(kind === 'agent' ? 'Its system prompt' : (kind === 'command' ? 'The prompt' : 'What it says'), ta));
    var mtime = null;
    if (it) {
      api(ccQ('file', '&kind=' + kind + '&scope=' + it.scope + '&name=' + encodeURIComponent(it.name))).then(function (d) {
        var sp = ccSplitFront(d.text);
        Object.keys(boxes).forEach(function (k) { boxes[k].value = sp.front[k] || ''; });
        ta.value = sp.body;
        mtime = d.mtime;
      }).catch(oops);
    } else ta.value = spec.blank;
    MODAL_GO = function (b) {
      var n = name.value.trim();
      if (!n) { toast('a name first', 'bad'); return; }
      var lines = [];
      if (kind !== 'command') lines.push('name: ' + n.split('/').pop());
      Object.keys(boxes).forEach(function (k) { if (boxes[k].value.trim()) lines.push(k + ': ' + boxes[k].value.trim()); });
      var text = (lines.length ? '---\n' + lines.join('\n') + '\n---\n\n' : '') + ta.value.replace(/^\s+/, '');
      busy(b, true);
      ccPost({action: 'write', kind: kind, scope: scope.value, name: n, text: text, mtime: mtime}).then(function (x) {
        toast(x.message, 'good');
        closeModal();
        done();
      }).catch(oops).then(function () { busy(b, false); });
    };
  }, [{words: 'Close', close: true}, {words: 'Save it', cls: 'primary', icon: 'save', go: function (b) { MODAL_GO(b); }}], 'wide');
}

/* ---- plugins --------------------------------------------------------------------------- */
function ccPlugins(body) {
  var card = el('div', 'card full');
  body.appendChild(card);
  var mk = el('div', 'card full');
  body.appendChild(mk);
  var av = el('div', 'card full');
  body.appendChild(av);
  var run = function (b, what, sub, target, scope, after) {
    if (b) busy(b, true);
    ccPost({action: what, sub: sub, target: target, scope: scope}).then(function (x) { toast(x.message, 'good'); (after || load)(); })
      .catch(oops).then(function () { if (b) busy(b, false); });
  };
  var load = function () {
    clear(card); clear(mk);
    card.appendChild(el('p', 'note', 'reading…'));
    api(ccQ('plugins')).then(function (d) {
      clear(card);
      card.appendChild(el('h2', '', 'Installed'));
      var inst = Array.isArray(d.installed) ? d.installed : [];
      if (!inst.length) card.appendChild(el('p', 'muted', 'No plugin installed. Install one from a marketplace below.'));
      else card.appendChild(listTable(['Plugin', 'Version', 'Whose', 'State', ''], inst, function (p) {
        var tr = el('tr');
        var nm = p.id || p.name || '';
        tr.appendChild(noI18n(el('td', 'mono', nm)));
        tr.appendChild(noI18n(el('td', 'mono small', p.version || '')));
        tr.appendChild(el('td', 'muted', p.scope || ''));
        var on = p.enabled !== false;
        var st = el('td'); st.appendChild(el('span', 'tag ' + (on ? 'ok' : 'dim'), on ? 'on' : 'off')); tr.appendChild(st);
        var t = el('td', 'rowtools');
        var tog = cmdButton(on ? 'Switch off' : 'Switch on', 'power', 'small');
        tog.onclick = function () { run(tog, 'plugin', on ? 'disable' : 'enable', nm, p.scope); };
        var upd = cmdButton('Update', 'refresh', 'small');
        upd.onclick = function () { run(upd, 'plugin', 'update', nm); };
        var del = iconButton('trash', 'Uninstall it');
        del.onclick = function () { confirmThen('Uninstall ' + nm + '?', '', 'Uninstall', function () { run(null, 'plugin', 'uninstall', nm, p.scope); }, true); };
        [tog, upd, del].forEach(function (x) { t.appendChild(x); });
        tr.appendChild(t);
        return tr;
      }));
      mk.appendChild(el('h2', '', 'Marketplaces'));
      var row = el('div', 'btnrow');
      var src = textBox('', 'owner/repo, a URL or a folder', 'mono');
      src.style.flex = '1';
      noI18n(src);
      var addm = cmdButton('Add a marketplace', 'add', 'primary');
      addm.onclick = function () { if (src.value.trim()) run(addm, 'marketplace', 'add', src.value.trim()); };
      row.appendChild(src); row.appendChild(addm);
      mk.appendChild(row);
      var ms = Array.isArray(d.marketplaces) ? d.marketplaces : [];
      if (ms.length) mk.appendChild(listTable(['Name', 'From', ''], ms, function (m) {
        var tr = el('tr');
        tr.appendChild(noI18n(el('td', 'mono', m.name)));
        tr.appendChild(noI18n(el('td', 'mono small muted', m.repo || m.url || m.path || m.source || '')));
        var t = el('td', 'rowtools');
        var u = cmdButton('Update', 'refresh', 'small');
        u.onclick = function () { run(u, 'marketplace', 'update', m.name); };
        var x = iconButton('trash', 'Take it away');
        x.onclick = function () { confirmThen('Take the marketplace ' + m.name + ' away?', '', 'Take it away', function () { run(null, 'marketplace', 'remove', m.name); }, true); };
        t.appendChild(u); t.appendChild(x);
        tr.appendChild(t);
        return tr;
      }));
    }).catch(function (e) { clear(card); card.appendChild(el('p', 'note bad', String(e.message || e))); });
  };
  load();
  av.appendChild(el('h2', '', 'Available'));
  var show = cmdButton('Show what the marketplaces have', 'list', '');
  av.appendChild(show);
  var avList = el('div');
  av.appendChild(avList);
  show.onclick = function () {
    busy(show, true);
    api(ccQ('plugins', '&available=1')).then(function (d) {
      clear(avList);
      var all = (d.available && (d.available.available || d.available)) || [];
      if (!Array.isArray(all)) all = [];
      if (d.available_error) avList.appendChild(el('p', 'note bad', d.available_error));
      var q = textBox('', 'find a plugin…', '');
      q.style.margin = '10px 0';
      avList.appendChild(q);
      var host = el('div');
      avList.appendChild(host);
      var draw = function () {
        clear(host);
        var w = q.value.trim().toLowerCase();
        var rows = all.filter(function (p) { return !w || JSON.stringify(p).toLowerCase().indexOf(w) >= 0; }).slice(0, 200);
        host.appendChild(listTable(['Plugin', 'What it does', ''], rows, function (p) {
          var tr = el('tr');
          var id = p.id || ((p.name || '') + (p.marketplace ? '@' + p.marketplace : ''));
          tr.appendChild(noI18n(el('td', 'mono', id)));
          tr.appendChild(noI18n(el('td', 'small', p.description || '')));
          var t = el('td', 'rowtools');
          var i = cmdButton(p.installed ? 'Installed' : 'Install', 'download', 'small' + (p.installed ? '' : ' primary'));
          i.disabled = !!p.installed;
          i.onclick = function () { run(i, 'plugin', 'install', id, CC.project ? 'project' : 'user', load); };
          t.appendChild(i);
          tr.appendChild(t);
          return tr;
        }));
      };
      q.oninput = debounce(draw, 150);
      draw();
    }).catch(oops).then(function () { busy(show, false); });
  };
}

/* ---- the sessions it runs on its own ---------------------------------------------------- */
function ccBackground(body) {
  var card = el('div', 'card full');
  body.appendChild(card);
  var load = function () {
    clear(card);
    var h = el('h2', '');
    h.appendChild(el('span', '', 'Its sessions'));
    var right = el('span', 'right');
    var again = cmdButton('Look again', 'refresh', 'small');
    again.onclick = load;
    right.appendChild(again);
    var start = cmdButton('Start one in the background…', 'play', 'small primary');
    start.onclick = function () { newTermAsk('claude', CC.project || ''); };
    right.appendChild(start);
    h.appendChild(right);
    card.appendChild(h);
    card.appendChild(el('p', 'note', 'What claude agents lists: the sessions of this account that run now - in a terminal, or in the background on their own (claude --bg), and those that ended. A background one is opened in a terminal of these pages with claude attach.'));
    var list = el('div');
    card.appendChild(list);
    list.appendChild(el('p', 'note', 'reading…'));
    api(ccQ('agents')).then(function (d) {
      clear(list);
      if (!d.sessions.length) { list.appendChild(el('p', 'muted', 'No session.')); return; }
      list.appendChild(listTable(['Name', 'Folder', 'Kind', 'State', 'Started', ''], d.sessions, function (s) {
        var tr = el('tr');
        tr.appendChild(noI18n(el('td', 'mono', s.name || s.id || s.sessionId || '')));
        tr.appendChild(noI18n(el('td', 'mono small', s.cwd || '')));
        tr.appendChild(el('td', 'muted', s.kind === 'background' ? 'in the background' : (s.kind === 'interactive' ? 'in a terminal' : (s.kind || ''))));
        var st = el('td'); st.appendChild(el('span', 'tag ' + ({busy: 'load', idle: 'ok', running: 'load', done: 'dim', stopped: 'dim'}[s.status] || 'dim'), s.status || '')); tr.appendChild(st);
        tr.appendChild(s.startedAt ? stampCell(s.startedAt / 1000) : el('td', 'muted', '–'));
        var t = el('td', 'rowtools');
        var id = s.id || s.shortId || s.name || '';
        if (s.kind === 'background' && id) {
          var open = cmdButton('Open', 'terminal', 'small primary');
          open.onclick = function () { ccPost({action: 'attach', id: id}).then(function (x) { loadTerms(x.id).then(function () { showTab('terms', x.id); }); }).catch(oops); };
          var logs = cmdButton('Its output', 'list', 'small');
          logs.onclick = function () {
            api(ccQ('logs', '&id=' + encodeURIComponent(id))).then(function (x) {
              modal('claude logs ' + id, function (b) { b.appendChild(noI18n(el('pre', 'lines', x.text || '–'))); }, [{words: 'Close', close: true}], 'large');
            }).catch(oops);
          };
          var stop = cmdButton('Stop', 'cancel', 'small');
          stop.onclick = function () { ccPost({action: 'stop', id: id}).then(function (x) { toast(x.message, 'good'); load(); }).catch(oops); };
          var rm = iconButton('trash', 'Remove it (and its worktree, where that is safe)');
          rm.onclick = function () { confirmThen('Remove ' + id + '?', '', 'Remove it', function () { ccPost({action: 'rm', id: id}).then(function (x) { toast(x.message, 'good'); load(); }).catch(oops); }, true); };
          [open, logs, stop, rm].forEach(function (x) { t.appendChild(x); });
        }
        tr.appendChild(t);
        return tr;
      }));
    }).catch(function (e) { clear(list); list.appendChild(el('p', 'note bad', String(e.message || e))); });
  };
  load();
}

/* ---- usage -------------------------------------------------------------------------------- */
function ccUsage(body) {
  var days = CC.usageDays || 30;
  var bar = el('div', 'cc-scopebar');
  bar.appendChild(ccSeg([['7', '7 days'], ['30', '30 days'], ['90', '90 days'], ['365', 'a year']], String(days), function (v) { CC.usageDays = Number(v); ccShow('usage'); }));
  body.appendChild(bar);
  var host = el('div');
  body.appendChild(host);
  host.appendChild(el('p', 'note', 'counting…'));
  api(ccQ('usage', '&days=' + days)).then(function (d) {
    clear(host);
    var u = d.usage, t = u.total;
    var grid = el('div', 'cc-grid');
    [['Tokens written by Claude', t.output], ['Tokens sent', t.input], ['Written to the cache', t.cache_write], ['Read from the cache', t.cache_read],
     ['Answers', t.messages], ['Conversations', t.sessions]].forEach(function (x) {
      var tl = el('div', 'cc-tile');
      tl.appendChild(el('b', '', num(x[1])));
      tl.appendChild(el('span', '', x[0]));
      grid.appendChild(tl);
    });
    host.appendChild(grid);
    var daysCard = el('div', 'card full');
    daysCard.appendChild(el('h2', '', 'By day'));
    var most = Math.max(1, Math.max.apply(null, u.by_day.map(function (x) { return x.output; }).concat([1])));
    var chart = el('div', 'cc-bars');
    u.by_day.forEach(function (x) {
      var col = el('div', 'cc-bar');
      var fill = el('i');
      fill.style.height = Math.max(2, Math.round(100 * x.output / most)) + '%';
      col.appendChild(fill);
      col.title = x.key + ': ' + num(x.output) + ' ' + txT('tokens written') + ', ' + num(x.messages) + ' ' + txT('answers');
      col.appendChild(noI18n(el('span', '', x.key.slice(5))));
      chart.appendChild(col);
    });
    if (!u.by_day.length) daysCard.appendChild(el('p', 'muted', 'Nothing in these days.'));
    else daysCard.appendChild(chart);
    host.appendChild(daysCard);
    var two = function (title, rows, label) {
      var c = el('div', 'card full');
      c.appendChild(el('h2', '', title));
      c.appendChild(listTable([label, {words: 'Written', cls: 'num'}, {words: 'Sent', cls: 'num'}, {words: 'Cache read', cls: 'num'}, {words: 'Answers', cls: 'num'}], rows, function (x) {
        var tr = el('tr');
        tr.appendChild(noI18n(el('td', 'mono small', x.key)));
        tr.appendChild(el('td', 'num', num(x.output)));
        tr.appendChild(el('td', 'num', num(x.input + x.cache_write)));
        tr.appendChild(el('td', 'num muted', num(x.cache_read)));
        tr.appendChild(el('td', 'num', num(x.messages)));
        return tr;
      }));
      host.appendChild(c);
    };
    two('By model', u.by_model, 'Model');
    two('By folder', u.by_project, 'Folder');
  }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
}

/* ---- keyboard ---------------------------------------------------------------------------- */
function ccKeys(body) {
  var host = el('div', 'card full');
  body.appendChild(el('p', 'note', 'Claude Code\'s own keys, as /keybindings writes them: {"bindings": [{"context": "Chat", "bindings": {"ctrl+e": "chat:externalEditor"}}]}.'));
  body.appendChild(host);
  ccText(host, 'keybindings', 'user', {json: true, rows: 20, blank: '{\n  "bindings": []\n}\n'});
}
