/* app.js - the pages of ai: the terminals, the files, the conversations, the
   server's settings. Drawn with core.js, otp's own helpers, so that it looks
   and behaves as otp's administration pages do; every answer comes from the
   daemon, which decides what this sign-in may see and do. */
'use strict';

ADMIN = !!(ME && ME.role === 'admin');
var PANE = 'claude';
var RAIL = {pinned: false, open: null, shut: null};
var SETTINGS = null;
var DIRTY = {};
var PENDING = {};
var LIVE = {on: true, timer: null};
var TL = {terms: [], open: '', side: true, full: false};

function roleWords(role) { return role === 'admin' ? 'administrator' : 'user'; }
function hideForRole() {
  document.querySelectorAll('.admin-only').forEach(function (n) { if (!ADMIN) n.hidden = true; });
}
function prefs() { return (ME && ME.prefs) || {}; }
function savePrefs(change) {
  return api('prefs', {prefs: change}).then(function (d) { ME.prefs = d.prefs; return d.prefs; });
}
function pathJoin(a, b) { return (a.replace(/\/+$/, '') || '') + '/' + b; }
function baseName(p) { p = String(p || '').replace(/\/+$/, ''); return p.slice(p.lastIndexOf('/') + 1) || '/'; }
function tagEl(words, kind) { return el('span', 'tag ' + (kind || 'dim'), words); }

/* ---- tabs and the address --------------------------------------------------- */
var TABS = ['terms', 'files', 'history', 'overview', 'events', 'settings'];
window.optShowTab = function (name, sub) {
  if (TABS.indexOf(name) < 0) name = 'terms';
  var btn = document.querySelector('.tabs button[data-tab="' + name + '"]');
  if (btn && btn.hidden) name = 'terms';
  TAB = name;
  document.querySelectorAll('.tabs button[data-tab]').forEach(function (b) {
    b.setAttribute('aria-selected', b.getAttribute('data-tab') === name ? 'true' : 'false');
  });
  TABS.forEach(function (one) { $('tab-' + one).hidden = one !== name; });
  document.body.classList.toggle('term-wide', name === 'terms');
  holdTheTallOnes();
  onTab(name, sub);
  writeHash();
};
document.querySelectorAll('.tabs button[data-tab]').forEach(function (b) {
  b.onclick = function () { showTab(b.getAttribute('data-tab')); };
});
function writeHash() {
  var want = '#' + TAB;
  if (TAB === 'settings') want += '/' + PANE;
  if (TAB === 'terms' && TL.open) want += '/' + TL.open;
  if (TAB === 'files' && FL.path) want += '/' + encodeURIComponent(FL.path);
  if (location.hash !== want) try { history.replaceState(null, '', want); } catch (e) { }
}
function onTab(name, sub) {
  explainWhatWasDrawn(document);
  if (ME && ME.must_change) return;           /* a password of its own first */
  if (name === 'terms') { loadTerms(sub); if (TL.open) setTimeout(termFit, 30); }
  if (name === 'files') loadFiles(sub || FL.path || '');
  if (name === 'history') loadHistory();
  if (name === 'overview') loadOverview();
  if (name === 'events') loadEvents();
  if (name === 'settings') { loadSettings(); showPane(sub || PANE); }
}

/* ---- the header, the live updates ------------------------------------------- */
function paintHeader(s) {
  STATUS = s;
  var pill = $('state-pill');
  var kind = s.problems && s.problems.length ? 'warn' : 'ok';
  if (s.upgrade_state === 'running') kind = 'warn';
  pill.className = 'pill ' + kind;
  pill.lastChild.textContent = s.upgrade_state === 'running' ? 'being upgraded'
    : (kind === 'warn' ? 'running, with trouble' : 'running');
  explain(pill, 'ai ' + s.version + ' on ' + s.host + '. ' + (s.terms_running || 0) + ' terminal(s) running.'
    + (s.newer ? ' A newer version is out: ' + s.newer + ' (Settings - Upgrades).' : ''));
  var pr = $('problems');
  clear(pr);
  (s.problems || []).forEach(function (p, i) {
    if (i) pr.appendChild(el('br'));
    pr.appendChild(document.createTextNode(p));
  });
  if (s.newer && ADMIN) {
    if (pr.childNodes.length) pr.appendChild(el('br'));
    var a = el('a', '', 'ai ' + s.newer + ' is out - Settings - Upgrades');
    a.href = '#settings/upgrade';
    a.onclick = function (e) { e.preventDefault(); showTab('settings', 'upgrade'); };
    pr.appendChild(a);
  }
  pr.hidden = !pr.childNodes.length;
  drawTrials(s);
  $('updated-at').textContent = clockWords(new Date());
  $('tabn-terms').textContent = s.terms_running ? num(s.terms_running) : '';
  $('offline').hidden = true;
}

var TRIALS = {list: [], skew: 0, timer: null};
var TRIAL_WORDS = {
  net: ['The new network waits to be kept', 'Not kept, the server goes back to its old network by itself. Keep it once the pages answer at the new address.'],
  fw: ['The new firewall waits to be kept', 'Not kept, the rules as they were before come back by themselves. Keep it once SSH and these pages still answer.'],
  access: ['Who may reach the pages waits to be kept', 'Not kept, the list as it was before comes back by itself. Keep it once the pages still answer from where you are.']
};
function drawTrials(s) {
  TRIALS.list = (s && s.trials) || [];
  TRIALS.skew = s && s.now ? s.now - Date.now() / 1000 : 0;
  var host = $('trials');
  clear(host);
  if (!TRIALS.list.length) {
    host.hidden = true;
    if (TRIALS.timer) { clearInterval(TRIALS.timer); TRIALS.timer = null; }
    return;
  }
  host.hidden = false;
  TRIALS.list.forEach(function (t) {
    var w = TRIAL_WORDS[t.kind] || [t.words, ''];
    var row = el('div', 'trial');
    var words = el('div', 'trial-words');
    words.appendChild(el('b', '', w[0]));
    words.appendChild(document.createTextNode(' - '));
    var left = el('span', 'trial-left mono');
    left.dataset.until = t.until;
    words.appendChild(left);
    words.appendChild(el('div', 'small', w[1]));
    words.appendChild(noI18n(el('div', 'small muted', t.words)));
    row.appendChild(words);
    var tools = el('div', 'trial-tools');
    var keep = cmdButton('Keep it', 'check', 'small primary');
    keep.onclick = function () { trialDo(t, 'keep', keep); };
    var back = cmdButton('Put the old back now', 'undo', 'small danger');
    back.onclick = function () {
      confirmThen('Put the old back now?', 'What was there before the change comes back at once.', 'Put it back',
                  function () { trialDo(t, 'back', back); });
    };
    tools.appendChild(keep);
    tools.appendChild(back);
    row.appendChild(tools);
    host.appendChild(row);
  });
  trialCount();
  if (!TRIALS.timer) TRIALS.timer = setInterval(trialCount, 1000);
}
function trialCount() {
  var now = Date.now() / 1000 + TRIALS.skew;
  document.querySelectorAll('#trials .trial-left').forEach(function (x) {
    var left = parseFloat(x.dataset.until) - now;
    x.textContent = left > 0 ? Math.floor(left / 60) + ':' + ('0' + Math.floor(left % 60)).slice(-2) + ' left' : 'going back now';
  });
}
function trialDo(t, action, button) {
  busy(button, true);
  api('trial', {kind: t.kind, do: action}).then(function () {
    toast(action === 'keep' ? 'kept' : 'put back', 'good');
    tick();
  }).catch(oops).then(function () { busy(button, false); });
}

function tick() {
  return api('status').then(paintHeader).catch(function (e) {
    if (e && e.unreachable) {
      var off = $('offline');
      off.textContent = 'The server is not answering just now (' + e.message + ') - asking again.';
      off.hidden = false;
    }
  });
}
function liveLoop() {
  clearInterval(LIVE.timer);
  LIVE.timer = setInterval(function () {
    if (!LIVE.on || document.hidden) return;
    tick();
    if (ME && ME.must_change) return;
    if (TAB === 'terms') loadTerms(null, true);
    if (TAB === 'settings' && PANE === 'upgrade') loadUpgrade(true);
  }, 5000);
}
$('updated').onclick = function () {
  LIVE.on = !LIVE.on;
  $('updated').classList.toggle('paused', !LIVE.on);
  $('updated').querySelector('b').textContent = LIVE.on ? 'live' : 'paused';
};
$('signout').onclick = function () {
  api('logout', {}).then(function () { location.href = '/'; }).catch(function () { location.href = '/'; });
};

/* ---- the account signed in -------------------------------------------------- */
function passwordForm(body, must) {
  var o = secretBox('', ''), n1 = secretBox('', ''), n2 = secretBox('', '');
  var g = el('div', 'formgrid');
  g.appendChild(formField(must ? 'The one you were given' : 'The present one', o));
  g.appendChild(formField('A new one (at least 10 characters)', n1));
  g.appendChild(formField('The new one again', n2));
  body.appendChild(g);
  return function (button) {
    if (n1.value !== n2.value) { toast('the two new ones are not the same', 'bad'); return; }
    busy(button, true);
    api('password', {old: o.value, new: n1.value}).then(function () {
      toast('the password is changed', 'good');
      ME.must_change = false;
      closeModal();
      if (must) location.reload();
    }).catch(oops).then(function () { busy(button, false); });
  };
}
function mustChange() {
  modal('First choose a password of your own', function (body) {
    body.appendChild(el('p', 'note', 'This account was given its password by somebody else. Before anything else, choose one that only you know.'));
    var go = passwordForm(body, true);
    MODAL_CLOSE = function () { if (ME.must_change) setTimeout(mustChange, 0); };
    body._go = go;
  }, [{words: 'Sign out', go: function () { $('signout').onclick(); }},
      {words: 'Change the password', cls: 'primary', icon: 'lock', go: function (b) { $('modal-body')._go(b); }}]);
}
$('me-btn').onclick = function () {
  modal('You: ' + ME.name, function (body) {
    body.appendChild(kvTable([
      ['Role', roleWords(ME.role)],
      ['Terminals run as', noI18n(el('span', 'mono', ME.run_as))],
      ['Files in', noI18n(el('span', 'mono', ME.role === 'admin' ? 'everywhere' : ((ME.roots || []).join(', ') || 'the home of ' + ME.run_as)))],
      ['Last sign-in', stamp(ME.last_login) + (ME.last_ip ? ' · ' + ME.last_ip : '')]
    ]));
    var lang = selectBox((window.AI_LANGS || []).map(function (l) { return [l.code, l.name]; }), window.AI_LANG);
    lang.onchange = function () {
      savePrefs({lang: lang.value}).then(function () {
        document.cookie = 'ai_lang=' + lang.value + '; path=/; max-age=31536000; samesite=strict'
          + (location.protocol === 'https:' ? '; secure' : '');
        location.reload();
      }).catch(oops);
    };
    var font = el('input');
    font.type = 'number'; font.min = 8; font.max = 32; font.value = termFont();
    font.onchange = function () { termSetFont(parseInt(font.value, 10) || 14); savePrefs({font: parseInt(font.value, 10) || 14}).catch(oops); };
    var g = el('div', 'formgrid');
    g.style.marginTop = '14px';
    g.appendChild(formField('Language of the pages', lang));
    g.appendChild(formField('Size of the terminal\'s letters', font));
    body.appendChild(g);
    body.appendChild(el('h3', '', 'A new password'));
    body._go = passwordForm(body, false);
  }, [{words: 'Close', close: true},
      {words: 'Change the password', cls: 'primary', icon: 'lock', go: function (b) { $('modal-body')._go(b); }}]);
};

/* ==========================================================================
   The terminals
   ========================================================================== */
function termStateTag(t) {
  if (t.state === 'running') return tagEl(t.viewers ? 'open' : 'running', t.viewers ? 'info' : 'ok');
  if (t.state === 'exited') return tagEl('exited' + (t.exit_status !== null && t.exit_status !== undefined ? ' (' + t.exit_status + ')' : ''), 'warn');
  return tagEl('ended', 'dim');
}
function kindWords(k) { return k === 'claude' ? 'Claude Code' : (k === 'shell' ? 'shell' : 'command'); }

function loadTerms(openId, quiet) {
  return api('terms').then(function (d) {
    TL.terms = d.terms;
    drawTermList();
    if (openId && openId !== TL.open) {
      var t = d.terms.filter(function (x) { return x.id === openId; })[0];
      if (t) openTerm(t.id);
    } else if (TL.open) {
      var cur = d.terms.filter(function (x) { return x.id === TL.open; })[0];
      if (cur) paintTermBar(cur);
    }
    if (!TL.open) drawTermEmpty();
  }).catch(function (e) { if (!quiet) oops(e); });
}

function drawTermList() {
  var host = $('tl-list');
  var q = $('tl-q').value.trim().toLowerCase();
  var all = $('tl-show').value === 'all';
  clear(host);
  var list = TL.terms.filter(function (t) {
    if (!all && t.state === 'ended') return false;
    if (!q) return true;
    return (t.title + ' ' + t.path + ' ' + t.owner + ' ' + t.run_as + ' ' + t.id).toLowerCase().indexOf(q) >= 0;
  });
  if (!list.length) {
    host.appendChild(el('p', 'muted small', TL.terms.length ? 'Nothing matches.' : 'No terminal yet. Press New.'));
  }
  list.forEach(function (t) {
    var row = el('button', 'tl-item' + (t.id === TL.open ? ' on' : '') + (t.state === 'ended' ? ' ended' : ''));
    row.type = 'button';
    var top = el('div', 'tl-top');
    var ic = el('span', 'tl-icon');
    ic.innerHTML = iconMarkup(t.kind === 'claude' ? 'terminal' : (t.kind === 'shell' ? 'log' : 'play'), 16);
    top.appendChild(ic);
    top.appendChild(noI18n(el('span', 'tl-title', t.title)));
    top.appendChild(termStateTag(t));
    row.appendChild(top);
    row.appendChild(noI18n(el('div', 'tl-path mono', t.path || t.cwd)));
    var meta = el('div', 'tl-meta muted');
    meta.appendChild(document.createTextNode(kindWords(t.kind) + ' · ' + t.run_as
      + (ADMIN && t.owner && t.owner !== ME.name ? ' · ' + t.owner : '') + ' · ' + ago(t.activity)));
    row.appendChild(meta);
    row.onclick = function () {
      if (t.state === 'ended') { endedPeek(t); return; }
      openTerm(t.id);
    };
    host.appendChild(row);
  });
  explainWhatWasDrawn(host);
}
$('tl-q').addEventListener('input', debounce(drawTermList, 120));
$('tl-show').onchange = drawTermList;
$('tl-new').onclick = function () { newTermAsk('claude'); };
$('te-claude').onclick = function () { newTermAsk('claude'); };
$('te-shell').onclick = function () { newTermAsk('shell'); };
$('te-hist').onclick = function () { showTab('history'); };

function drawTermEmpty() {
  $('term-empty').hidden = false;
  $('term-open').hidden = true;
  var host = $('te-recent');
  clear(host);
  var recent = (prefs().recent || []).slice(0, 8);
  if (recent.length) {
    host.appendChild(el('h3', '', 'Claude Code in a folder used lately'));
    var row = el('div', 'btnrow');
    recent.forEach(function (p) {
      var b = cmdButton(baseName(p), 'terminal', 'small');
      noI18n(b.querySelector('span'));
      explain(b, 'A new Claude Code terminal in ' + p);
      b.onclick = function () { startTerm({kind: 'claude', cwd: p}); };
      row.appendChild(b);
    });
    host.appendChild(row);
  }
  var live = TL.terms.filter(function (t) { return t.state !== 'ended'; });
  if (live.length) {
    host.appendChild(el('h3', '', 'Running'));
    var r2 = el('div', 'btnrow');
    live.slice(0, 10).forEach(function (t) {
      var b = cmdButton(t.title, 'play', 'small');
      noI18n(b.querySelector('span'));
      b.onclick = function () { openTerm(t.id); };
      r2.appendChild(b);
    });
    host.appendChild(r2);
  }
}

function endedPeek(t) {
  modal('It has ended: ' + t.title, function (body) {
    body.appendChild(kvTable([['Folder', noI18n(el('span', 'mono', t.cwd))], ['Ran as', t.run_as],
                              ['Started', stamp(t.created)], ['Ended', stamp(t.ended)]]));
    var pre = el('pre', 'lines tall');
    pre.textContent = '…';
    body.appendChild(pre);
    api('term&id=' + encodeURIComponent(t.id) + '&lines=200').then(function (d) {
      pre.textContent = d.term.screen || '(nothing was kept of its screen)';
      pre.scrollTop = pre.scrollHeight;
    }).catch(function (e) { pre.textContent = String(e.message || e); });
  }, [{words: 'Take it off the list', cls: 'danger', icon: 'trash', go: function () {
        api('terms', {do: 'forget', id: t.id}).then(function () { closeModal(); loadTerms(); }).catch(oops);
      }},
      {spacer: true},
      {words: 'Close', close: true},
      {words: 'Start it again', cls: 'primary', icon: 'play', go: function (b) {
        busy(b, true);
        api('terms', {do: 'again', id: t.id}).then(function (d) { closeModal(); loadTerms(d.id); })
          .catch(oops).then(function () { busy(b, false); });
      }}], 'wide');
}

/* ---- a new one ---------------------------------------------------------------- */
var MODELS = [['', 'as Claude Code chooses'], ['opus', 'Opus'], ['sonnet', 'Sonnet'], ['haiku', 'Haiku'],
              ['fable', 'Fable'], ['opusplan', 'Opus to plan, Sonnet to do']];
var MODES = [['', 'ask before changes (default)'], ['acceptEdits', 'accept edits by itself'],
             ['plan', 'plan only'], ['bypassPermissions', 'never ask (bypass permissions)']];

function newTermAsk(kind, cwd) {
  var st = {kind: kind || 'claude'};
  modal('A new terminal', function (body) {
    var seg = el('div', 'seg');
    [['claude', 'Claude Code'], ['shell', 'A shell']].forEach(function (k) {
      var b = el('button', st.kind === k[0] ? 'on' : '', k[1]);
      b.type = 'button';
      b.onclick = function () {
        st.kind = k[0];
        seg.querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', x === b); });
        claudeBox.hidden = st.kind !== 'claude';
      };
      seg.appendChild(b);
    });
    body.appendChild(seg);
    var g = el('div', 'formgrid');
    g.style.marginTop = '14px';
    var dir = textBox(cwd || prefs().last_cwd || (STATUS && STATUS.who && STATUS.who.default_cwd) || '', 'the home folder', 'mono');
    var dirWrap = el('div', 'btnrow');
    dir.style.flex = '1';
    dirWrap.appendChild(dir);
    var browse = cmdButton('Choose…', 'archive', 'small');
    browse.onclick = function () { pickFolder(dir.value, function (p) { dir.value = p; }); };
    dirWrap.appendChild(browse);
    var f = formField('The working directory', dirWrap, 'Where it starts. It is made if it is not there yet and the box below says so.');
    f.classList.add('span-2');
    g.appendChild(f);
    var mk = switchBox(false);
    g.appendChild(formField('Make it if it is not there', mk));
    var title = textBox('', 'from the folder');
    g.appendChild(formField('Its name', title));
    var asSel = null;
    if (ADMIN) {
      asSel = selectBox([[ME.run_as, ME.run_as + ' (yours)']], ME.run_as);
      api('linux').then(function (d) {
        d.accounts.forEach(function (a) {
          if (a.name === ME.run_as) return;
          var o = noI18n(el('option', '', a.name));
          o.value = a.name;
          asSel.appendChild(o);
        });
      }).catch(function () { });
      g.appendChild(formField('Runs as (Linux account)', asSel, 'Whose files it may change, whose Claude Code sign-in it uses.'));
    }
    body.appendChild(g);
    var chips = el('div', 'btnrow chips');
    var favs = (prefs().favs || []).concat(prefs().recent || []).filter(function (p, i, a) { return a.indexOf(p) === i; }).slice(0, 12);
    favs.forEach(function (p) {
      var b = el('button', 'chip', baseName(p));
      b.type = 'button';
      noI18n(b);
      b.title = p;
      b.onclick = function () { dir.value = p; };
      chips.appendChild(b);
    });
    if (favs.length) body.appendChild(chips);
    var claudeBox = el('div', 'set-sec');
    claudeBox.appendChild(el('h3', 'set-sec-head', 'Claude Code'));
    var g2 = el('div', 'formgrid');
    var start = selectBox([['new', 'a new conversation'], ['continue', 'the last conversation of this folder (--continue)'],
                           ['pick', 'choose one of its conversations (--resume)']], 'new');
    g2.appendChild(formField('Start with', start));
    var model = selectBox(MODELS, prefs().model || '');
    g2.appendChild(formField('Model', model));
    var mode = selectBox(MODES, prefs().mode || '');
    g2.appendChild(formField('Permissions', mode, 'Never ask is refused by Claude Code when it runs as root.'));
    var args = textBox(prefs().args || '', '--verbose, --add-dir ../other…', 'mono');
    g2.appendChild(formField('More words for its command line', args));
    claudeBox.appendChild(g2);
    claudeBox.hidden = st.kind !== 'claude';
    body.appendChild(claudeBox);
    body._get = function () {
      var opts = {};
      if (start.value === 'continue') opts.continue = true;
      if (start.value === 'pick') opts.pick = true;
      if (model.value) opts.model = model.value;
      if (mode.value) opts.mode = mode.value;
      if (args.value.trim()) opts.args = args.value.trim();
      if (mk._get()) opts.mkdir = true;
      return {kind: st.kind, cwd: dir.value.trim(), title: title.value.trim(), opts: opts,
              run_as: asSel ? asSel.value : '', keep: {model: model.value, mode: mode.value, args: args.value.trim()}};
    };
  }, [{words: 'Close', close: true},
      {words: 'Start it', cls: 'primary', icon: 'play', go: function (b) {
        var want = $('modal-body')._get();
        busy(b, true);
        startTerm(want).then(function (ok) { if (ok) closeModal(); }).then(function () { busy(b, false); });
      }}], 'wide');
}

function startTerm(want) {
  var size = TERM.t ? {cols: TERM.t.cols, rows: TERM.t.rows} : {cols: 160, rows: 48};
  return api('terms', {do: 'new', kind: want.kind, cwd: want.cwd, title: want.title || '', opts: want.opts || {},
                       run_as: want.run_as || '', cols: size.cols, rows: size.rows}).then(function (d) {
    var p = {};
    if (want.cwd) {
      var rec = [want.cwd].concat((prefs().recent || []).filter(function (x) { return x !== want.cwd; })).slice(0, 12);
      p.recent = rec;
      p.last_cwd = want.cwd;
    }
    if (want.keep) { p.model = want.keep.model; p.mode = want.keep.mode; p.args = want.keep.args; }
    savePrefs(p).catch(function () { });
    if (TAB !== 'terms') showTab('terms');
    return loadTerms(d.id).then(function () { return true; });
  }).catch(function (e) { oops(e); return false; });
}

/* ---- a folder, chosen ------------------------------------------------------------- */
function pickFolder(start, then) {
  var st = {path: start || ''};
  modal('Choose a folder', function (body) {
    var bar = el('div', 'btnrow');
    var up = cmdButton('Up', 'up', 'small');
    var path = textBox('', '', 'mono');
    path.style.flex = '1';
    var mk = cmdButton('New folder', 'add', 'small');
    bar.appendChild(up);
    bar.appendChild(path);
    bar.appendChild(mk);
    body.appendChild(bar);
    var list = el('div', 'pick-list');
    body.appendChild(list);
    var go = function (p) {
      filesApi('list', 'hidden=0&path=' + encodeURIComponent(p || '')).then(function (d) {
        st.path = d.path;
        path.value = d.path;
        up.disabled = !d.up;
        up.onclick = function () { go(d.up); };
        clear(list);
        var dirs = d.entries.filter(function (e) { return e.kind === 'dir'; });
        if (!dirs.length) list.appendChild(el('p', 'muted small', 'No folders in it.'));
        dirs.forEach(function (e) {
          var b = el('button', 'pick-row');
          b.type = 'button';
          b.innerHTML = iconMarkup('archive', 15);
          b.appendChild(noI18n(el('span', '', e.name)));
          b.onclick = function () { go(pathJoin(d.path, e.name)); };
          list.appendChild(b);
        });
      }).catch(oops);
    };
    path.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); go(path.value); } });
    mk.onclick = function () {
      var name = prompt('The name of the new folder');
      if (!name) return;
      filesApi('op', '', {op: 'mkdir', path: st.path, name: name}).then(function (d) { go(d.path); }).catch(oops);
    };
    go(st.path);
  }, [{words: 'Close', close: true},
      {words: 'Choose this one', cls: 'primary', icon: 'check', go: function () { closeModal(); then(st.path); }}]);
}

/* ---- the one open ---------------------------------------------------------------- */
function openTerm(id) {
  var t = TL.terms.filter(function (x) { return x.id === id; })[0];
  if (!t) return;
  TL.open = id;
  $('term-empty').hidden = true;
  $('term-open').hidden = false;
  $('term-gone').hidden = true;
  paintTermBar(t);
  drawTermList();
  drawKeys();
  writeHash();
  termOpen(id, $('term-host'), function (state, words) {
    var p = $('tb-state');
    p.className = 'pill small ' + (state === 'live' ? 'ok' : (state === 'ended' ? 'unknown' : 'warn'));
    p.lastChild.textContent = words;
    if (state === 'ended') termEnded(id);
  });
  if (window.innerWidth < 900) sideShow(false);
}
function paintTermBar(t) {
  $('tb-title').textContent = t.title;
  $('tb-path').textContent = (t.path || t.cwd) + ' · ' + t.run_as;
  document.title = t.title + ' · ' + ((STATUS && STATUS.site) || 'ai');
  if (t.state === 'exited' && !$('term-gone')._shown) termExited(t);
  if (t.state === 'running') { $('term-gone').hidden = true; $('term-gone')._shown = false; }
}
function termExited(t) {
  var box = $('term-gone');
  box._shown = true;
  clear(box);
  box.appendChild(el('div', '', 'What ran in it has ended' + (t.exit_status !== null && t.exit_status !== undefined ? ' (exit ' + t.exit_status + ')' : '') + '. Its last screen is above.'));
  var row = el('div', 'btnrow');
  var again = cmdButton('Start it again', 'play', 'small primary');
  again.onclick = function () { api('terms', {do: 'restart', id: t.id}).then(function () { box.hidden = true; box._shown = false; termOpen(t.id, $('term-host'), TERM.onState); }).catch(oops); };
  var end = cmdButton('Close it', 'close', 'small');
  end.onclick = function () { api('terms', {do: 'kill', id: t.id}).then(function () { closeTermView(); loadTerms(); }).catch(oops); };
  row.appendChild(again);
  row.appendChild(end);
  box.appendChild(row);
  box.hidden = false;
}
function termEnded(id) {
  var box = $('term-gone');
  clear(box);
  box.appendChild(el('div', '', 'This terminal has ended.'));
  var row = el('div', 'btnrow');
  var b = cmdButton('Back to the list', 'list', 'small');
  b.onclick = function () { closeTermView(); loadTerms(); };
  row.appendChild(b);
  box.appendChild(row);
  box.hidden = false;
}
function closeTermView() {
  termClose();
  TL.open = '';
  document.title = (STATUS && STATUS.site ? STATUS.site + ' · ' : '') + 'ai';
  drawTermEmpty();
  drawTermList();
  writeHash();
}
function sideShow(on) {
  TL.side = on;
  $('term-layout').classList.toggle('no-side', !on);
  setTimeout(termFit, 50);
}
$('tb-side').onclick = function () { sideShow(!TL.side); };
$('tb-font-').onclick = function () { termSetFont((TERM.t ? TERM.t.options.fontSize : 14) - 1); };
$('tb-font+').onclick = function () { termSetFont((TERM.t ? TERM.t.options.fontSize : 14) + 1); };
$('tb-full').onclick = function () {
  TL.full = !TL.full;
  document.body.classList.toggle('term-full', TL.full);
  setTimeout(termFit, 50);
};
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && TL.full) {
    var now = Date.now();
    if (TL.escAt && now - TL.escAt < 400) { TL.full = false; document.body.classList.remove('term-full'); setTimeout(termFit, 50); }
    TL.escAt = now;
  }
});
$('tb-attach').onclick = function () {
  var i = el('input');
  i.type = 'file';
  i.multiple = true;
  i.onchange = function () { termGiveFiles(i.files); };
  i.click();
};
$('tb-files').onclick = function () {
  var t = TL.terms.filter(function (x) { return x.id === TL.open; })[0];
  if (t) { showTab('files'); loadFiles(t.path || t.cwd); }
};
$('tb-compose').onclick = function () {
  var c = $('term-compose');
  c.hidden = !c.hidden;
  if (!c.hidden) $('tc-text').focus();
  setTimeout(termFit, 50);
};
$('tc-close').onclick = function () { $('term-compose').hidden = true; setTimeout(termFit, 50); };
$('tc-send').onclick = function () { termType($('tc-text').value, true); $('tc-text').value = ''; };
$('tc-put').onclick = function () { termType($('tc-text').value, false); $('tc-text').value = ''; };
$('tc-text').addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $('tc-send').onclick(); }
});
$('tc-text').addEventListener('paste', function (e) {
  var cd = e.clipboardData;
  if (cd && cd.files && cd.files.length) { e.preventDefault(); termGiveFiles(cd.files); }
});
$('tb-more').onclick = function () {
  var t = TL.terms.filter(function (x) { return x.id === TL.open; })[0];
  if (!t) return;
  modal(t.title, function (body) {
    body.appendChild(kvTable([
      ['Kind', kindWords(t.kind)], ['Folder', noI18n(el('span', 'mono', t.cwd))],
      ['Now in', noI18n(el('span', 'mono', t.path))], ['Runs as', t.run_as], ['Started by', t.owner || '–'],
      ['Started', stamp(t.created)], ['Windows looking at it', String(t.viewers)],
      ['Running now', noI18n(el('span', 'mono', t.command || '–'))],
      ['On the server', noI18n(el('span', 'mono', 'ai --attach ' + t.id))]
    ]));
    var name = textBox(t.title, '');
    var g = el('div', 'formgrid');
    g.style.marginTop = '12px';
    var w = el('div', 'btnrow');
    name.style.flex = '1';
    w.appendChild(name);
    var save = cmdButton('Rename', 'save', 'small');
    save.onclick = function () {
      api('terms', {do: 'rename', id: t.id, title: name.value}).then(function () { closeModal(); loadTerms(); }).catch(oops);
    };
    w.appendChild(save);
    g.appendChild(formField('Its name', w));
    body.appendChild(g);
  }, [{words: 'End it', cls: 'danger', icon: 'power', go: function () {
        api('terms', {do: 'kill', id: t.id}).then(function () { closeModal(); closeTermView(); loadTerms(); }).catch(oops);
      }},
      {words: 'Start it again', icon: 'refresh', go: function () {
        api('terms', {do: 'restart', id: t.id}).then(function () { closeModal(); termOpen(t.id, $('term-host'), TERM.onState); }).catch(oops);
      }},
      {words: 'In a window of its own', icon: 'unfold', go: function () {
        window.open(location.pathname + '#terms/' + t.id, '_blank');
        closeModal();
      }},
      {spacer: true},
      {words: 'Close', close: true}], 'wide');
};

/* The keys a phone, or a browser that keeps them, does not give - and Ctrl
   and Alt held for the next key, pressed here or typed. */
var KEYS = [
  ['Esc', '\x1b', 'Escape: stops Claude in the middle of what it is doing, closes a menu.'],
  ['Esc Esc', '\x1b\x1b', 'Twice Escape: Claude Code goes back to an earlier message (rewind).'],
  ['Tab', '\t', 'Tab: completes a path or a command.'],
  ['⇧Tab', '\x1b[Z', 'Shift+Tab: switches Claude Code\'s mode - asking, accepting edits, planning.'],
  ['↑', '\x1b[A', 'Up'], ['↓', '\x1b[B', 'Down'], ['←', '\x1b[D', 'Left'], ['→', '\x1b[C', 'Right'],
  ['Home', '\x1b[H', 'Home'], ['End', '\x1b[F', 'End'], ['PgUp', '\x1b[5~', 'Page Up'], ['PgDn', '\x1b[6~', 'Page Down'],
  ['Ins', '\x1b[2~', 'Insert'], ['Del', '\x1b[3~', 'Delete'],
  ['Enter', '\r', 'Enter'],
  ['⇧⏎', '\x1b\r', 'A new line in what you are writing, without sending it - Shift+Enter, Alt+Enter and Ctrl+Enter on the keyboard do the same.'],
  ['Ctrl+C', '\x03', 'Ctrl+C: stops what runs; twice, Claude Code ends.'],
  ['Ctrl+D', '\x04', 'Ctrl+D: the end of input; ends a shell.'],
  ['Ctrl+R', '\x12', 'Ctrl+R: searches back through what was typed.'],
  ['Ctrl+O', '\x0f', 'Ctrl+O: Claude Code shows everything it did, in detail.'],
  ['Ctrl+T', '\x14', 'Ctrl+T: Claude Code\'s list of tasks.'],
  ['Ctrl+L', '\x0c', 'Ctrl+L: clears the screen.'],
  ['Ctrl+Z', '\x1a', 'Ctrl+Z: puts what runs in the background (fg brings it back).'],
  ['History', '\x02[', 'Scrolls back through the terminal (tmux): arrows and Page Up/Down, q to come back. The mouse wheel does the same.']
];
var FKEYS = ['\x1bOP', '\x1bOQ', '\x1bOR', '\x1bOS', '\x1b[15~', '\x1b[17~', '\x1b[18~', '\x1b[19~', '\x1b[20~', '\x1b[21~', '\x1b[23~', '\x1b[24~'];
function drawKeys() {
  var host = $('term-keys');
  if (host._drawn) return;
  host._drawn = true;
  var mod = function (name, words, says) {
    var b = el('button', 'btn small key mod', words);
    b.type = 'button';
    noI18n(b);
    explain(b, says);
    b.onmousedown = function (e) { e.preventDefault(); };
    b.onclick = function () { TERM.mods[name] = !TERM.mods[name]; paintMods(); if (TERM.t) TERM.t.focus(); };
    b._mod = name;
    host.appendChild(b);
  };
  mod('ctrl', 'Ctrl', 'Ctrl held for the next key - pressed here or typed: Ctrl, then C is Ctrl+C. For a phone, which has no Ctrl.');
  mod('alt', 'Alt', 'Alt held for the next key - pressed here or typed: Alt, then B is Alt+B (a word back).');
  KEYS.forEach(function (k) {
    var b = el('button', 'btn small key', k[0]);
    b.type = 'button';
    noI18n(b);
    explain(b, k[2]);
    b.onmousedown = function (e) { e.preventDefault(); };
    b.onclick = function () { termKeys(k[1]); };
    host.appendChild(b);
  });
  var f = el('select', 'key-f');
  var o0 = el('option', '', 'F1-F12');
  o0.value = '';
  f.appendChild(o0);
  FKEYS.forEach(function (seq, i) { var o = noI18n(el('option', '', 'F' + (i + 1))); o.value = seq; f.appendChild(o); });
  explain(f, 'A function key, F1 to F12.');
  f.onchange = function () { if (f.value) termKeys(f.value); f.value = ''; };
  host.appendChild(f);
  var lock = el('button', 'btn small key lockkeys', 'All keys');
  lock.type = 'button';
  explain(lock, 'The terminal over the whole screen, and every key of the keyboard given to it - Ctrl+W, Ctrl+T, Ctrl+N, Ctrl+Tab, Esc and F11 too, which the browser keeps for itself otherwise (Chrome and Edge). Hold Esc to come back.');
  lock.onclick = function () {
    termLockKeys(!TERM.locked).then(function (on) {
      paintMods();
      toast(on ? 'every key goes to the terminal now - hold Esc to come back' : 'the browser has its keys back', 'good');
    }).catch(function (e) { paintMods(); toast(String(e.message || e), 'bad'); });
  };
  host.appendChild(lock);
  TERM.onMods = paintMods;
  function paintMods() {
    Array.prototype.forEach.call(host.querySelectorAll('.mod'), function (b) { b.classList.toggle('on', !!TERM.mods[b._mod]); });
    lock.classList.toggle('on', !!TERM.locked);
    /* Locked, the terminal is the whole screen. */
    if (TERM.locked !== TL.lockedWas) {
      TL.lockedWas = TERM.locked;
      TL.full = !!TERM.locked;
      document.body.classList.toggle('term-full', TL.full);
      setTimeout(termFit, 80);
    }
  }
}

/* Claude Code's own commands, put into the terminal. */
var COMMANDS = [
  ['/help', 'what Claude Code can do, and its keys'], ['/clear', 'a new conversation, the old one kept'],
  ['/compact', 'the conversation shortened into a summary, to go on with less'],
  ['/resume', 'go back to an earlier conversation of this folder'], ['/model', 'choose the model'],
  ['/context', 'how full the context is'], ['/cost', 'what this conversation has cost'], ['/usage', 'how much of the plan is used'],
  ['/status', 'version, account, model, connections'], ['/config', 'Claude Code\'s settings'],
  ['/permissions', 'what it may do without asking'], ['/memory', 'CLAUDE.md, its memory files'],
  ['/init', 'a CLAUDE.md written for this project'], ['/review', 'a review of a pull request'],
  ['/security-review', 'a security review of the changes'], ['/agents', 'its subagents'],
  ['/mcp', 'the MCP servers'], ['/hooks', 'the hooks'], ['/plugin', 'plugins'], ['/add-dir', 'another folder it may work in'],
  ['/export', 'the conversation into a file or the clipboard'], ['/rewind', 'back to an earlier point of the conversation'],
  ['/todos', 'its list of tasks'], ['/bashes', 'the shells it runs in the background'], ['/vim', 'vim keys in its input'],
  ['/output-style', 'how it writes'], ['/statusline', 'its status line'], ['/terminal-setup', 'Shift+Enter for new lines'],
  ['/doctor', 'checks its installation'], ['/login', 'sign in to a Claude account'], ['/logout', 'sign out'],
  ['/release-notes', 'what is new in it'], ['/bug', 'tell Anthropic about a problem'], ['/exit', 'end Claude Code']
];
$('tb-cmds').onclick = function () {
  modal('Claude Code\'s commands', function (body) {
    body.appendChild(el('p', 'note', 'Pressed, a command is typed into the terminal and sent. Anything you have written there yet goes with it. Typing / in the terminal shows the same list - and the commands of your own (.claude/commands).'));
    var only = switchBox(false);
    var fw = formField('Only type it, do not send it', only);
    body.appendChild(fw);
    var q = textBox('', 'find…');
    body.appendChild(q);
    var list = el('div', 'cmd-list');
    body.appendChild(list);
    var draw = function () {
      clear(list);
      var want = q.value.trim().toLowerCase();
      COMMANDS.forEach(function (c) {
        if (want && (c[0] + ' ' + c[1]).toLowerCase().indexOf(want) < 0) return;
        var b = el('button', 'cmd-row');
        b.type = 'button';
        b.appendChild(noI18n(el('span', 'mono', c[0])));
        b.appendChild(el('span', 'muted', c[1]));
        b.onclick = function () {
          closeModal();
          termKeys(c[0]);
          if (!only._get()) setTimeout(function () { termKeys('\r'); }, 150);
        };
        list.appendChild(b);
      });
    };
    q.addEventListener('input', draw);
    draw();
  }, [{words: 'Close', close: true}], 'wide');
};

/* ==========================================================================
   The files
   ========================================================================== */
var FL = {path: '', data: null};
function loadFiles(path) {
  var hidden = $('fl-hidden').checked ? '1' : '0';
  return filesApi('list', 'hidden=' + hidden + '&path=' + encodeURIComponent(path || '')).then(function (d) {
    FL.path = d.path;
    FL.data = d;
    $('fl-path').value = d.path;
    $('fl-up').disabled = !d.up;
    drawRoots(d);
    drawFiles(d);
    writeHash();
  }).catch(oops);
}
function drawRoots(d) {
  var s = $('fl-roots');
  clear(s);
  var o0 = el('option', '', 'go to…');
  o0.value = '';
  s.appendChild(o0);
  var seen = {};
  var add = function (p, words) {
    if (seen[p]) return;
    seen[p] = 1;
    var o = el('option', '', words || p);
    o.value = p;
    noI18n(o);
    s.appendChild(o);
  };
  (d.roots || []).forEach(function (r) { add(r); });
  (prefs().favs || []).forEach(function (p) { add(p, '★ ' + p); });
  (prefs().recent || []).forEach(function (p) { add(p); });
  TL.terms.forEach(function (t) { if (t.state !== 'ended') add(t.path || t.cwd); });
  var fav = (prefs().favs || []).indexOf(d.path) >= 0;
  $('fl-fav').classList.toggle('primary', fav);
}
$('fl-roots').onchange = function () { if ($('fl-roots').value) loadFiles($('fl-roots').value); };
$('fl-up').onclick = function () { if (FL.data && FL.data.up) loadFiles(FL.data.up); };
$('fl-path').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); loadFiles($('fl-path').value.trim()); } });
$('fl-hidden').onchange = function () { loadFiles(FL.path); };
$('fl-fav').onclick = function () {
  var favs = (prefs().favs || []).slice();
  var at = favs.indexOf(FL.path);
  if (at >= 0) favs.splice(at, 1); else favs.unshift(FL.path);
  savePrefs({favs: favs.slice(0, 30)}).then(function () {
    toast(at >= 0 ? 'no longer kept' : 'kept in the list', 'good');
    drawRoots(FL.data);
  }).catch(oops);
};
$('fl-term').onclick = function () { newTermAsk('claude', FL.path); };
$('fl-mkdir').onclick = function () {
  var name = prompt('The name of the new folder');
  if (!name) return;
  filesApi('op', '', {op: 'mkdir', path: FL.path, name: name}).then(function () { loadFiles(FL.path); }).catch(oops);
};
$('fl-newfile').onclick = function () {
  var name = prompt('The name of the new file');
  if (!name) return;
  editText(pathJoin(FL.path, name), '', 0, true);
};
$('fl-send').onclick = function () { $('fl-input').click(); };
$('fl-input').onchange = function () { sendFiles($('fl-input').files); $('fl-input').value = ''; };

function fileIcon(e) {
  if (e.kind === 'dir') return 'archive';
  if (/\.(png|jpe?g|gif|webp|svg|bmp)$/i.test(e.name)) return 'eye';
  if (/\.(zip|gz|tgz|xz|bz2|7z|rar|tar)$/i.test(e.name)) return 'archive';
  return 'log';
}
function drawFiles(d) {
  var host = $('fl-table');
  clear(host);
  $('fl-said').textContent = d.entries.length + ' item(s)' + (d.more ? ' (only the first 10 000)' : '');
  host.appendChild(listTable(['Name', {words: 'Size', cls: 'num'}, 'Changed', 'Owner', 'Rights', ''], d.entries, function (e) {
    var tr = el('tr', 'clickable');
    var td = el('td', 'fl-name');
    var ic = el('span', 'fl-icon' + (e.kind === 'dir' ? ' dir' : ''));
    ic.innerHTML = iconMarkup(fileIcon(e), 15);
    td.appendChild(ic);
    td.appendChild(noI18n(el('span', '', e.name + (e.kind === 'dir' ? '/' : '') + (e.link ? ' →' : ''))));
    tr.appendChild(td);
    tr.appendChild(el('td', 'num muted', e.kind === 'dir' ? '' : bytes(e.size)));
    tr.appendChild(stampCell(e.mtime, 'muted'));
    tr.appendChild(noI18n(el('td', 'muted', e.owner)));
    tr.appendChild(noI18n(el('td', 'mono muted small', e.mode)));
    var tools = el('td', 'tools');
    var full = pathJoin(d.path, e.name);
    var dl = iconButton('download', e.kind === 'dir' ? 'Download it as a .zip' : 'Download it');
    dl.onclick = function (ev) { ev.stopPropagation(); download(full); };
    var rn = iconButton('edit', 'Rename it');
    rn.onclick = function (ev) {
      ev.stopPropagation();
      var name = prompt('A new name for ' + e.name, e.name);
      if (!name || name === e.name) return;
      filesApi('op', '', {op: 'rename', path: full, name: name}).then(function () { loadFiles(d.path); }).catch(oops);
    };
    var rm = iconButton('trash', 'Take it away');
    rm.onclick = function (ev) {
      ev.stopPropagation();
      confirmThen('Take ' + e.name + ' away?', (e.kind === 'dir' ? 'The folder <b>' + htmlText(e.name) + '</b> and everything in it are' : '<b>' + htmlText(e.name) + '</b> is') + ' deleted from the server. There is no bin.', 'Delete it', function () {
        filesApi('op', '', {op: 'delete', path: full}).then(function () { loadFiles(d.path); }).catch(oops);
      });
    };
    tools.appendChild(dl);
    tools.appendChild(rn);
    tools.appendChild(rm);
    tr.appendChild(tools);
    tr.onclick = function () {
      if (e.kind === 'dir') loadFiles(full);
      else openFile(full, e);
    };
    return tr;
  }, 'plain|An empty folder'));
  explainWhatWasDrawn(host);
}
function download(path) {
  var a = el('a');
  a.href = '/files/get?path=' + encodeURIComponent(path);
  a.download = '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}
function openFile(path, e) {
  if (/\.(png|jpe?g|gif|webp|bmp|avif)$/i.test(e.name)) {
    modal(e.name, function (body) {
      var img = el('img', 'fl-img');
      img.src = '/files/get?inline=1&path=' + encodeURIComponent(path);
      body.appendChild(img);
    }, [{words: 'Download it', icon: 'download', go: function () { download(path); }}, {words: 'Close', close: true}], 'wide');
    return;
  }
  if (/\.pdf$/i.test(e.name)) { window.open('/files/get?inline=1&path=' + encodeURIComponent(path), '_blank'); return; }
  if (e.size > 2 * 1024 * 1024) { download(path); return; }
  filesApi('op', '', {op: 'read', path: path}).then(function (d) { editText(path, d.text, d.mtime, false); })
    .catch(function (err) {
      if (/not text|too big/.test(String(err.message))) download(path); else oops(err);
    });
}
function editText(path, text, mtime, isNew) {
  modal(baseName(path), function (body) {
    body.appendChild(noI18n(el('div', 'mono small muted', path)));
    var ta = el('textarea', 'mono fl-edit');
    ta.value = text;
    ta.spellcheck = false;
    body.appendChild(ta);
    body._get = function () { return ta.value; };
    ta.addEventListener('keydown', function (e) {
      if (e.key === 's' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $('modal-foot').querySelector('.btn.primary').click(); }
    });
  }, [{words: 'Download it', icon: 'download', go: function () { download(path); }},
      {spacer: true},
      {words: 'Close', close: true},
      {words: 'Save it', cls: 'primary', icon: 'save', go: function (b) {
        busy(b, true);
        filesApi('op', '', {op: 'write', path: path, text: $('modal-body')._get(), mtime: isNew ? null : mtime})
          .then(function (d) { mtime = d.mtime; isNew = false; toast('saved', 'good'); loadFiles(FL.path); })
          .catch(oops).then(function () { busy(b, false); });
      }}], 'wide');
}
function sendFiles(files) {
  var list = Array.prototype.slice.call(files || []);
  if (!list.length) return;
  var host = $('fl-progress');
  var to = FL.path;
  var next = function () {
    var f = list.shift();
    if (!f) { loadFiles(to); return; }
    var row = el('div', 'fl-prog');
    var name = f.name || ('pasted.' + ((f.type || '').split('/')[1] || 'bin'));
    row.appendChild(noI18n(el('span', 'mono', name)));
    var bar = el('div', 'up-bar');
    var fill = el('i');
    bar.appendChild(fill);
    row.appendChild(bar);
    var pc = el('span', 'muted small', '0 %');
    row.appendChild(pc);
    host.appendChild(row);
    sendFile('/files/put?dir=' + encodeURIComponent(to) + '&name=' + encodeURIComponent(name), f, function (a, b) {
      fill.style.width = Math.round(a * 100 / b) + '%';
      pc.textContent = Math.round(a * 100 / b) + ' %';
    }).then(function (d) {
      pc.textContent = 'there: ' + baseName(d.path);
      setTimeout(function () { row.remove(); }, 2500);
      next();
    }).catch(function (e) { pc.textContent = String(e.message || e); pc.className = 'bad small'; next(); });
  };
  next();
}
(function filesDrop() {
  var host = $('fl-host'), drop = $('fl-drop'), depth = 0;
  var has = function (e) { return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0; };
  host.addEventListener('dragenter', function (e) { if (!has(e)) return; e.preventDefault(); depth++; drop.hidden = false; });
  host.addEventListener('dragover', function (e) { if (!has(e)) return; e.preventDefault(); });
  host.addEventListener('dragleave', function (e) { if (!has(e)) return; depth = Math.max(0, depth - 1); if (!depth) drop.hidden = true; });
  host.addEventListener('drop', function (e) { if (!has(e)) return; e.preventDefault(); depth = 0; drop.hidden = true; sendFiles(e.dataTransfer.files); });
  document.addEventListener('paste', function (e) {
    if (TAB !== 'files' || !$('modal').hidden) return;
    var t = e.target;
    if (t && /^(INPUT|TEXTAREA)$/.test(t.tagName)) return;
    var cd = e.clipboardData;
    if (!cd) return;
    var files = [];
    Array.prototype.forEach.call(cd.items || [], function (it) { if (it.kind === 'file') { var f = it.getAsFile(); if (f) files.push(f); } });
    if (files.length) { e.preventDefault(); sendFiles(files); return; }
    var text = cd.getData('text/plain');
    if (text) {
      e.preventDefault();
      var name = prompt('The pasted text as a file called', 'pasted-' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.txt');
      if (name) sendFiles([new File([text], name, {type: 'text/plain'})]);
    }
  });
}());

/* ==========================================================================
   The conversations
   ========================================================================== */
var HI = {items: [], asSet: false};
function loadHistory() {
  var as = $('hi-as').value || '';
  $('hi-said').textContent = 'reading…';
  api('history' + (as ? '&run_as=' + encodeURIComponent(as) : '')).then(function (d) {
    HI.items = d.items;
    HI.run_as = d.run_as;
    if (ADMIN && !HI.asSet) {
      HI.asSet = true;
      api('linux').then(function (l) {
        var s = $('hi-as');
        clear(s);
        l.accounts.forEach(function (a) {
          var o = noI18n(el('option', '', a.name));
          o.value = a.name;
          s.appendChild(o);
        });
        s.value = d.run_as;
      }).catch(function () { });
    }
    var cwds = {};
    d.items.forEach(function (it) { if (it.cwd) cwds[it.cwd] = (cwds[it.cwd] || 0) + 1; });
    var sel = $('hi-cwd'), was = sel.value;
    clear(sel);
    var o0 = el('option', '', 'every folder');
    o0.value = '';
    sel.appendChild(o0);
    Object.keys(cwds).sort().forEach(function (c) {
      var o = el('option', '', c + ' (' + cwds[c] + ')');
      o.value = c;
      noI18n(o);
      sel.appendChild(o);
    });
    sel.value = cwds[was] ? was : '';
    drawHistory();
  }).catch(function (e) { $('hi-said').textContent = ''; oops(e); });
}
function drawHistory() {
  var q = $('hi-q').value.trim().toLowerCase(), cwd = $('hi-cwd').value;
  var rows = HI.items.filter(function (it) {
    if (cwd && it.cwd !== cwd) return false;
    return !q || (it.first + ' ' + it.summary + ' ' + it.cwd + ' ' + it.branch + ' ' + it.id).toLowerCase().indexOf(q) >= 0;
  });
  $('hi-said').textContent = rows.length + ' of ' + HI.items.length;
  var host = $('hi-table');
  clear(host);
  host.appendChild(listTable(['When', 'Folder', 'What it was about', {words: 'Messages', cls: 'num'}, ''], rows, function (it) {
    var tr = el('tr', 'clickable');
    tr.appendChild(stampCell(it.mtime));
    var f = noI18n(el('td', 'mono small', it.cwd || '?'));
    if (it.branch) f.appendChild(el('span', 'tag dim', it.branch));
    tr.appendChild(f);
    var w = el('td', 'hi-words');
    if (it.summary) w.appendChild(noI18n(el('b', '', it.summary)));
    if (it.first) w.appendChild(noI18n(el('div', 'muted small', it.first)));
    tr.appendChild(w);
    tr.appendChild(el('td', 'num muted', (it.messages || 0) + (it.messages_more ? '+' : '')));
    var tools = el('td', 'tools');
    var go = cmdButton('Pick it up', 'play', 'small primary');
    go.onclick = function (e) { e.stopPropagation(); resumeIt(it, go); };
    tools.appendChild(go);
    tr.appendChild(tools);
    tr.onclick = function () { resumeIt(it, go); };
    return tr;
  }, 'plain|No conversation of Claude Code here yet'));
}
function resumeIt(it, button) {
  busy(button, true);
  var size = TERM.t ? {cols: TERM.t.cols, rows: TERM.t.rows} : {cols: 160, rows: 48};
  api('history', {id: it.id, cwd: it.cwd, run_as: it.run_as, first: it.summary || it.first,
                  model: prefs().model || '', mode: prefs().mode || '', cols: size.cols, rows: size.rows})
    .then(function (d) { showTab('terms'); return loadTerms(d.id); })
    .catch(oops).then(function () { busy(button, false); });
}
$('hi-q').addEventListener('input', debounce(drawHistory, 150));
$('hi-cwd').onchange = drawHistory;
$('hi-as').onchange = loadHistory;

/* ==========================================================================
   The overview
   ========================================================================== */
function setCard(id, value, sub, tone) {
  $('m-' + id).textContent = value;
  $('m-' + id + '-sub').textContent = sub || ' ';
  if (tone) $('card-' + id).className = 'card metric ' + tone;
}
function loadOverview() {
  api('overview').then(function (d) {
    var running = d.terms.filter(function (t) { return t.state !== 'ended'; });
    setCard('terms', num(running.length), running.filter(function (t) { return t.kind === 'claude'; }).length + ' Claude Code · ' + running.filter(function (t) { return t.viewers; }).length + ' open now', 'info');
    if (!d.machine) return;
    var m = d.machine;
    setCard('load', m.load[0].toFixed(2), m.cpus + ' processor(s) · ' + m.load[1].toFixed(2) + ' · ' + m.load[2].toFixed(2), m.load[0] > m.cpus ? 'warn' : 'ok');
    var used = m.mem_total ? 1 - m.mem_avail / m.mem_total : 0;
    setCard('mem', Math.round(used * 100) + ' %', bytes(m.mem_total - m.mem_avail) + ' of ' + bytes(m.mem_total), used > 0.9 ? 'crit' : (used > 0.75 ? 'warn' : 'ok'));
    var root = m.disks[0] || {total: 0, used: 0, free: 0};
    var du = root.total ? root.used / root.total : 0;
    setCard('disk', Math.round(du * 100) + ' %', bytes(root.free) + ' free on ' + root.path, du > 0.92 ? 'crit' : (du > 0.8 ? 'warn' : 'ok'));
    setCard('server', m.host, 'up ' + span(m.uptime) + ' · ' + m.os, 'ok');
    setCard('ver', d.version, d.newer ? d.newer + ' is out' : 'the newest known', d.newer ? 'warn' : 'info');
    var ou = d.osup;
    setCard('osup', ou && ou.checked ? num(ou.count || 0) : '?', ou && ou.checked ? (ou.reboot_now ? 'a restart is wanted · ' : '') + 'looked ' + ago(ou.checked) : 'not looked at yet', ou && ou.count ? 'warn' : 'info');
    var c = d.cert || {};
    var days = c.until_ts ? Math.floor((c.until_ts - Date.now() / 1000) / 86400) : null;
    setCard('cert', days === null ? '–' : days + ' days', c.self_signed ? 'self-signed' : (c.issuer || ''), days !== null && days < 14 ? 'crit' : (days !== null && days < 30 ? 'warn' : 'ok'));
    var mh = $('ov-machine');
    clear(mh);
    mh.appendChild(kvTable([
      ['System', m.os + ' · ' + m.kernel + ' · ' + m.arch],
      ['Addresses', noI18n(el('span', 'mono', m.addrs.map(function (a) { return a.addr + ' (' + a.dev + ')'; }).join(', ')))],
      ['Disks', m.disks.map(function (x) { return x.path + ' ' + bytes(x.free) + ' free of ' + bytes(x.total); }).join(' · ')],
      ['Swap', bytes(m.swap_total - m.swap_free) + ' of ' + bytes(m.swap_total)],
      ['Software', noI18n(el('span', 'small', Object.keys(m.software).filter(function (k) { return m.software[k]; }).map(function (k) { return k + ' ' + m.software[k]; }).join(' · ')))]
    ]));
    var sh = $('ov-signed');
    clear(sh);
    sh.appendChild(listTable(['Who', 'From', 'Last'], d.signed_in, function (s) {
      var tr = el('tr');
      tr.appendChild(noI18n(el('td', '', s.name)));
      tr.appendChild(noI18n(el('td', 'mono', s.ip)));
      tr.appendChild(el('td', 'muted', ago(s.seen)));
      return tr;
    }));
    var eh = $('ov-events');
    clear(eh);
    eh.appendChild(eventTable(d.events));
  }).catch(oops);
}
function eventTable(rows) {
  return listTable(['When', 'What', 'Who', ''], rows, function (e) {
    var tr = el('tr');
    tr.appendChild(stampCell(e.at));
    tr.appendChild(noI18n(el('td', '', e.text)));
    tr.appendChild(noI18n(el('td', 'muted', e.who || '')));
    tr.appendChild(el('td', '', '')).appendChild(tagEl(e.kind, e.level === 'bad' ? 'crit' : (e.level === 'warn' ? 'warn' : 'dim')));
    return tr;
  }, 'plain|Nothing yet');
}

/* ==========================================================================
   The events
   ========================================================================== */
var EV = {page: 0};
function loadEvents(page) {
  EV.page = page || 0;
  var per = parseInt($('ev-per').value, 10) || 100;
  var q = 'events&page=' + (EV.page + 1) + '&per=' + per + '&q=' + encodeURIComponent($('ev-q').value.trim())
    + '&kind=' + encodeURIComponent($('ev-kind').value);
  api(q).then(function (d) {
    var sel = $('ev-kind'), was = sel.value;
    if (sel.options.length <= 1 || sel._n !== d.kinds.length) {
      sel._n = d.kinds.length;
      clear(sel);
      var o0 = el('option', '', 'every kind');
      o0.value = '';
      sel.appendChild(o0);
      d.kinds.forEach(function (k) { var o = el('option', '', k); o.value = k; sel.appendChild(o); });
      sel.value = was;
    }
    $('ev-said').textContent = num(d.total) + ' event(s)';
    var host = $('ev-table');
    clear(host);
    host.appendChild(eventTable(d.events));
    pager('ev-pager', EV.page, per, d.total, loadEvents);
  }).catch(oops);
}
$('ev-q').addEventListener('input', debounce(function () { loadEvents(0); }, 300));
$('ev-kind').onchange = function () { loadEvents(0); };
$('ev-per').onchange = function () { loadEvents(0); };

/* ==========================================================================
   Settings
   ========================================================================== */
function showPane(name) {
  if (!$('pane-' + name)) name = 'claude';
  PANE = name;
  document.querySelectorAll('#ctl-nav button[data-pane]').forEach(function (b) {
    b.classList.toggle('on', b.dataset.pane === name);
  });
  document.querySelectorAll('.ctl-pane').forEach(function (p) { p.hidden = p.id !== 'pane-' + name; });
  writeHash();
  if (name === 'claude') loadClaude();
  if (name === 'people') { loadUsers(); loadLockouts(); }
  if (name === 'mail') loadMail();
  if (name === 'db') loadDb();
  if (name === 'backup') loadRbackup();
  if (name === 'web') loadWeb();
  if (name === 'fw') loadFw();
  if (name === 'network') loadNet();
  if (name === 'time') loadNtp();
  if (name === 'power') loadPower();
  if (name === 'osup') loadOsup(); else if (typeof ouPoll === 'function') ouPoll(false);
  if (name === 'sshkeys') loadSshKeys(); else if (typeof skPoll === 'function') skPoll(false);
  if (name === 'upgrade') loadUpgrade();
  if (name === 'about') { loadAbout(); loadConsoleLogin(); }
  markDirtyCount();
}
document.querySelectorAll('#ctl-nav button[data-pane]').forEach(function (b) {
  b.onclick = function () { showPane(b.dataset.pane); };
});
function pinRail(on) {
  RAIL.pinned = !!on;
  var nav = $('ctl-nav'), pin = $('ctl-pin');
  nav.classList.toggle('pinned', RAIL.pinned);
  document.querySelector('.ctl-layout').classList.toggle('nav-pinned', RAIL.pinned);
  pin.setAttribute('aria-pressed', RAIL.pinned ? 'true' : 'false');
  explain(pin, RAIL.pinned ? 'The menu is staying open. Press again to let it hide itself at the edge of the screen.'
    : 'The menu hides itself at the edge of the screen and slides out when you point at it. Press this to keep it open.');
  try { localStorage.setItem('ai-rail-pinned', RAIL.pinned ? '1' : '0'); } catch (e) { }
}
(function rail() {
  var nav = $('ctl-nav'), pin = $('ctl-pin');
  pin.innerHTML = iconMarkup('pin', 17);
  pin.onclick = function (e) { e.stopPropagation(); pinRail(!RAIL.pinned); };
  nav.addEventListener('mouseenter', function () {
    clearTimeout(RAIL.shut);
    RAIL.open = setTimeout(function () { nav.classList.add('open'); }, 60);
  });
  nav.addEventListener('mouseleave', function () {
    clearTimeout(RAIL.open);
    RAIL.shut = setTimeout(function () {
      if (document.activeElement && document.activeElement.id === 'ctl-find' && $('ctl-find').value) return;
      nav.classList.remove('open');
    }, 260);
  });
  var was = '1';
  try { was = localStorage.getItem('ai-rail-pinned') || '1'; } catch (e) { }
  pinRail(was === '1');
}());
$('ctl-find').addEventListener('input', function () {
  var want = $('ctl-find').value.trim().toLowerCase();
  var box = $('ctl-found');
  clear(box);
  if (!want || !SETTINGS) { box.hidden = true; return; }
  var tr = function (x) { try { return (typeof i18nText === 'function' && x) ? (i18nText(x) || '') : ''; } catch (e) { return ''; } };
  var hits = SETTINGS.settings.filter(function (s) {
    return (s.label + ' ' + s.key + ' ' + s.help + ' ' + tr(s.label) + ' ' + tr(s.help)).toLowerCase().indexOf(want) >= 0;
  }).slice(0, 12);
  if (!hits.length) box.appendChild(el('div', 'ctl-none', 'Nothing by that name'));
  var paneOf = {claude: 'claude', access: 'access', upgrade: 'upgrade', general: 'about'};
  hits.forEach(function (s) {
    var b = el('button', 'ctl-hit');
    b.type = 'button';
    b.appendChild(el('span', 'ctl-hit-t', s.label));
    b.onclick = function () {
      showPane(paneOf[s.pane] || 'about');
      $('ctl-find').value = '';
      box.hidden = true;
      var item = document.querySelector('.set-item[data-key="' + s.key + '"]');
      if (item) { item.scrollIntoView({block: 'center'}); item.classList.add('found'); }
    };
    box.appendChild(b);
  });
  box.hidden = !hits.length;
});

/* ---- the settings that are only values ---------------------------------------- */
var SECT = {claude: 'sect-claude', access: 'sect-access', upgrade: 'sect-upgrade', general: 'sect-general', mail: 'sect-mail', db: 'sect-db', backup: 'sect-backup'};
function loadSettings() {
  return api('settings').then(function (d) {
    SETTINGS = d;
    DIRTY = {};
    Object.keys(SECT).forEach(function (pane) {
      var host = $(SECT[pane]);
      clear(host);
      var g = el('div', 'set-grid cols-2');
      d.settings.filter(function (s) { return s.pane === pane; }).forEach(function (s) { g.appendChild(settingItem(s)); });
      host.appendChild(g);
    });
    applyWhen();
    if (typeof rbPassTools === 'function') rbPassTools();
    markDirtyCount();
    explainWhatWasDrawn(document.querySelector('#tab-settings'));
  }).catch(oops);
}
function settingItem(s) {
  var item = el('div', 'set-item' + (s.kind === 'bool' ? ' set-bool' : '') + (s.kind === 'text' ? ' tall span-2' : ''));
  item.dataset.key = s.key;
  var label = el('label', '', s.label);
  item.appendChild(label);
  var input;
  if (s.kind === 'bool') {
    input = switchBox(!!s.value);
    input._input.onchange = function () { mark(); };
  } else if (s.kind === 'choice') {
    input = selectBox(s.extra.choices, s.value);
    input.onchange = function () { mark(); };
  } else if (s.kind === 'text') {
    input = el('textarea', 'mono');
    input.rows = 5;
    input.value = s.value || '';
    input.spellcheck = false;
    input.oninput = function () { mark(); };
  } else if (s.kind === 'password') {
    input = secretBox('', s.set ? 'saved - empty keeps it' : 'not set');
    input.oninput = function () { mark(); };
  } else {
    input = textBox(s.value === null || s.value === undefined ? '' : s.value, '', s.kind === 'int' ? '' : 'mono');
    if (s.kind === 'int') { input.type = 'number'; if (s.extra.min !== undefined) input.min = s.extra.min; if (s.extra.max !== undefined) input.max = s.extra.max; }
    input.oninput = function () { mark(); };
  }
  if (input.id === '') input.id = 'set-' + s.key;
  item.appendChild(input);
  /* Name, control, then the rest in a row of its own (otp's set-tail), so
     what is added under a setting never lies over its words. */
  var tail = el('div', 'set-tail');
  if (s.help) tail.appendChild(el('div', 'says', s.help));
  if (s.saved && s.kind !== 'password') {
    var back = el('button', 'link small', 'back to the default');
    back.type = 'button';
    explain(back, 'The built-in value: ' + (s.default === '' ? '(empty)' : String(s.default)));
    back.onclick = function () { DIRTY[s.key] = null; item.classList.add('dirty'); markDirtyCount(); };
    tail.appendChild(back);
  }
  item.appendChild(tail);
  function value() {
    if (s.kind === 'bool') return !!input._get();
    if (s.kind === 'int') return parseInt(input.value, 10);
    return input.value;
  }
  function mark() {
    var v = value();
    if (String(v) === String(s.value === null ? '' : s.value)) delete DIRTY[s.key]; else DIRTY[s.key] = v;
    item.classList.toggle('dirty', s.key in DIRTY);
    markDirtyCount();
    applyWhen();
  }
  item._value = value;
  if (s.extra && s.extra.when) item.dataset.when = JSON.stringify(s.extra.when);
  return item;
}
/* What only one choice uses is there only while that choice is made (otp's
   ONLY_WHEN): not a page of boxes that do nothing. */
function applyWhen() {
  document.querySelectorAll('.set-item[data-when]').forEach(function (item) {
    var w = JSON.parse(item.dataset.when);
    var master = document.querySelector('.set-item[data-key="' + w[0] + '"]');
    var v = master && master._value ? master._value() : null;
    item.hidden = !!master && w[1].map(String).indexOf(String(v)) < 0;
  });
}
var SAVE_PANES = ['fw', 'time'];
function pendingSet(key, p) { p.pane = p.pane || PANE; PENDING[key] = p; markDirtyCount(); }
function markDirtyCount() {
  var n = Object.keys(DIRTY).length + Object.keys(PENDING).length;
  var bar = $('save-bar');
  var here = TAB === 'settings' && (SAVE_PANES.indexOf(PANE) >= 0 || !!SECT[PANE === 'about' ? 'general' : PANE]
    || Object.keys(PENDING).some(function (k) { return PENDING[k].pane === PANE; }));
  bar.style.display = here || n ? '' : 'none';
  bar.classList.toggle('dirty', n > 0);
  $('set-said').textContent = n ? n + ' change(s) not saved yet' : '';
}
$('set-save').onclick = function () {
  var keys = Object.keys(PENDING);
  if (!Object.keys(DIRTY).length && !keys.length) { toast('nothing has changed'); return; }
  busy($('set-save'), true);
  var chain = Promise.resolve(true);
  if (Object.keys(DIRTY).length) {
    chain = api('settings', {values: DIRTY}).then(function () {
      toast('saved', 'good');
      return loadSettings().then(function () { return true; });
    }).catch(function (e) { oops(e); return false; });
  }
  keys.forEach(function (k) {
    chain = chain.then(function (ok) {
      if (!ok || !PENDING[k]) return ok;
      return Promise.resolve(PENDING[k].save()).then(function (r) {
        if (r === false) return false;
        delete PENDING[k];
        return true;
      }).catch(function (e) { oops(e); return false; });
    });
  });
  chain.then(function () { markDirtyCount(); busy($('set-save'), false); });
};
$('set-reset').onclick = function () {
  Object.keys(PENDING).forEach(function (k) { try { PENDING[k].reset(); } catch (e) { /* drawn again anyway */ } });
  PENDING = {};
  loadSettings();
};

/* ---- Claude Code --------------------------------------------------------------- */
function loadClaude(fresh) {
  api('claude' + (fresh ? '&fresh=1' : '')).then(function (d) {
    var host = $('cc-table');
    clear(host);
    host.appendChild(listTable(['Linux account', 'Claude Code', 'Signed in', 'Node.js', ''], d.accounts, function (a) {
      var tr = el('tr');
      tr.appendChild(noI18n(el('td', 'mono', a.account)));
      var v = el('td');
      if (a.error) v.appendChild(el('span', 'bad', a.error));
      else if (a.version) {
        v.appendChild(noI18n(el('span', '', a.version)));
        v.appendChild(noI18n(el('div', 'mono small muted', a.path)));
      } else v.appendChild(tagEl('not installed', 'warn'));
      tr.appendChild(v);
      var s = el('td');
      s.appendChild(a.signed_in ? tagEl('yes', 'ok') : (a.api_key ? tagEl('API key', 'info') : tagEl('not yet', 'warn')));
      if (a.email) s.appendChild(noI18n(el('div', 'small muted', a.email + (a.org ? ' · ' + a.org : ''))));
      tr.appendChild(s);
      tr.appendChild(noI18n(el('td', 'muted', a.node || '–')));
      var tools = el('td', 'tools');
      var add = function (words, icon, what, says, cls) {
        var b = cmdButton(words, icon, 'small' + (cls ? ' ' + cls : ''));
        explain(b, says);
        b.onclick = function () {
          busy(b, true);
          api('claude', {do: what, run_as: a.account}).then(function (r) { return startedHere(r.id); })
            .catch(oops).then(function () { busy(b, false); });
        };
        tools.appendChild(b);
      };
      if (ADMIN) {
        if (!a.version) {
          add('Install it', 'download', 'install', 'Anthropic\'s own installer, in a terminal you watch: ' + d.native, 'primary');
          if (a.npm) add('With npm', 'download', 'npm', d.npm);
        } else {
          add('Update it', 'download', 'update', 'claude update, in a terminal you watch.');
          add('Check it', 'search', 'doctor', 'claude doctor: what is wrong with the installation, if anything.');
        }
      }
      if (a.version) add('Sign in', 'lock', 'login', 'Claude Code in a terminal of its own: it asks how to sign in the first time; or type /login.');
      tr.appendChild(tools);
      return tr;
    }));
  }).catch(oops);
}
function startedHere(id) {
  showTab('terms');
  return loadTerms(id);
}
$('cc-look').onclick = function () { loadClaude(true); };

/* ---- the accounts ------------------------------------------------------------- */
var US = null;
function loadUsers() {
  api('users').then(function (d) {
    US = d;
    var host = $('us-table');
    clear(host);
    host.appendChild(listTable(['Name', 'Role', 'Terminals run as', 'Files in', 'Second step', 'Last sign-in', ''], d.users, function (u) {
      var tr = el('tr', 'clickable' + (u.disabled ? ' dim' : ''));
      var n = noI18n(el('td', '', u.name));
      if (u.disabled) n.appendChild(tagEl('off', 'crit'));
      if (u.must_change) n.appendChild(tagEl('to choose a password', 'warn'));
      tr.appendChild(n);
      tr.appendChild(el('td', '', roleWords(u.role)));
      tr.appendChild(noI18n(el('td', 'mono', u.run_as + (u.run_as_own ? '' : ' *'))));
      tr.appendChild(noI18n(el('td', 'mono small', u.role === 'admin' ? 'everywhere' : (u.roots.join(', ') || '~' + u.run_as))));
      var mf = el('td', 'small');
      if (u.mfa) {
        mf.appendChild(tagEl(u.mfa.kind === 'app' ? 'app' : 'e-mail', 'ok'));
        if (u.mfa.dest) mf.appendChild(noI18n(el('span', 'muted mono', ' ' + u.mfa.dest)));
      } else mf.appendChild(el('span', d.mfa_on ? 'warn' : 'muted', d.mfa_on ? 'at the next sign-in' : '–'));
      tr.appendChild(mf);
      tr.appendChild(el('td', 'muted', u.last_login ? ago(u.last_login) + (u.last_ip ? ' · ' + u.last_ip : '') : 'never'));
      tr.appendChild(el('td', 'tools'));
      tr.onclick = function () { editUser(u); };
      return tr;
    }));
    host.appendChild(el('p', 'muted small', '* the default (Settings - Claude Code), ' + d.default_run_as + ' now'));
    var sh = $('us-sessions');
    clear(sh);
    sh.appendChild(listTable(['Who', 'Since', 'Last', 'From', 'Browser', ''], d.sessions, function (s) {
      var tr = el('tr');
      var who = noI18n(el('td', '', s.name));
      if (s.mfa_pending) who.appendChild(tagEl('second step not given yet', 'warn'));
      tr.appendChild(who);
      tr.appendChild(stampCell(s.created));
      tr.appendChild(el('td', 'muted', ago(s.seen)));
      tr.appendChild(noI18n(el('td', 'mono', s.ip)));
      tr.appendChild(noI18n(el('td', 'small muted', (s.agent || '').slice(0, 60))));
      var tools = el('td', 'tools');
      if (s.id !== d.me_sid) {
        var b = iconButton('out', 'End this sign-in');
        b.onclick = function () { api('users', {do: 'end', sid: s.id, name: s.name}).then(loadUsers).catch(oops); };
        tools.appendChild(b);
      } else tools.appendChild(tagEl('you', 'info'));
      tr.appendChild(tools);
      return tr;
    }));
  }).catch(oops);
}
function userForm(body, u) {
  var g = el('div', 'formgrid');
  var f = {};
  if (!u) {
    f.name = textBox('', 'jan.novak');
    g.appendChild(formField('Name', f.name));
  }
  f.role = selectBox([['user', 'user - terminals of their own, files in their folders'], ['admin', 'administrator - everything']], u ? u.role : 'user');
  g.appendChild(formField('Role', f.role));
  var names = [['', 'the default (' + (US ? US.default_run_as : 'root') + ')']].concat((US ? US.linux : []).map(function (a) { return [a.name, a.name + ' (' + a.home + ')']; }));
  f.run_as = selectBox(names, u ? u.run_as_own : '');
  Array.prototype.forEach.call(f.run_as.options, function (o, i) { if (i) noI18n(o); });
  g.appendChild(formField('Terminals run as (Linux account)', f.run_as, 'Whoever signs in here is this account on the server: its files, its rights, its Claude Code sign-in.'));
  f.roots = el('textarea', 'mono');
  f.roots.rows = 2;
  f.roots.value = u ? u.roots.join('\n') : '';
  f.roots.placeholder = '/srv/project';
  g.appendChild(formField('Folders for files (a user)', f.roots, 'One a line. Empty: the home folder of the Linux account. An administrator may use every folder.'));
  f.note = textBox(u ? u.note : '', '');
  g.appendChild(formField('A note', f.note));
  if (!u) {
    f.pw = secretBox('', 'made and shown, if empty');
    g.appendChild(formField('Password', f.pw));
    f.mklin = switchBox(false);
    g.appendChild(formField('Make a new Linux account by this name', f.mklin));
    f.newlin = textBox('', 'jan');
    g.appendChild(formField('Its name (small letters)', f.newlin));
    f.sudo = switchBox(false);
    g.appendChild(formField('It may use sudo (wheel / sudo group)', f.sudo));
  } else {
    f.off = switchBox(u.disabled);
    g.appendChild(formField('Switched off - may not sign in', f.off));
  }
  body.appendChild(g);
  return f;
}
$('us-add').onclick = function () {
  modal('A new account', function (body) { body._f = userForm(body, null); }, [
    {words: 'Close', close: true},
    {words: 'Make it', cls: 'primary', icon: 'add', go: function (b) {
      var f = $('modal-body')._f;
      var runAs = f.mklin._get() ? f.newlin.value.trim() : f.run_as.value;
      busy(b, true);
      api('users', {do: 'add', name: f.name.value.trim(), role: f.role.value, run_as: runAs, roots: f.roots.value,
                    note: f.note.value, password: f.pw.value, make_linux: !!f.mklin._get(), sudo: !!f.sudo._get()})
        .then(function (d) {
          closeModal();
          loadUsers();
          if (d.password) showPassword(f.name.value.trim(), d.password);
        }).catch(oops).then(function () { busy(b, false); });
    }}], 'wide');
};
function showPassword(name, pw) {
  modal('The password of ' + name, function (body) {
    body.appendChild(el('p', 'note', 'Shown this once. It has to be changed at the first sign-in.'));
    var p = noI18n(el('div', 'mono big', pw));
    copyOnClick(p, pw, 'the password was copied');
    body.appendChild(p);
  }, [{words: 'Close', close: true}], true);
}
function editUser(u) {
  var reset = {words: 'Reset the second step', icon: 'key', go: function () {
    confirmThen('Reset the second step of ' + u.name + '?', 'Its app or mail address is forgotten and its sign-ins end: at the next sign-in it sets a second step up again - with only its password.', 'Reset it', function () {
      api('users', {do: 'mfa_reset', name: u.name}).then(function (r) { toast(r.message, 'good'); closeModal(); loadUsers(); }).catch(oops);
    }, true);
  }};
  modal('The account ' + u.name, function (body) { body._f = userForm(body, u); }, (u.mfa ? [reset] : []).concat([
    {words: 'Take it away', cls: 'danger', icon: 'trash', go: function () {
      api('users', {do: 'drop', name: u.name}).then(function () { closeModal(); loadUsers(); }).catch(oops);
    }},
    {words: 'A new password', icon: 'lock', go: function () {
      api('users', {do: 'password', name: u.name}).then(function (d) { closeModal(); loadUsers(); showPassword(u.name, d.password); }).catch(oops);
    }},
    {spacer: true},
    {words: 'Close', close: true},
    {words: 'Save it', cls: 'primary', icon: 'save', go: function (b) {
      var f = $('modal-body')._f;
      busy(b, true);
      api('users', {do: 'edit', name: u.name, role: f.role.value, run_as: f.run_as.value, roots: f.roots.value,
                    note: f.note.value, disabled: !!f.off._get()})
        .then(function () { closeModal(); loadUsers(); }).catch(oops).then(function () { busy(b, false); });
    }}]), 'wide');
}

/* ==========================================================================
   Certificates and TLS, as otp's (1.0.47)
   ========================================================================== */
var WEB = {last: null, timer: null};
function loadWeb() {
  apiLatest('web', 'web').then(drawWeb).catch(oops);
  clearInterval(WEB.timer);
  WEB.timer = setInterval(function () {
    if (!paneLive('web')) { clearInterval(WEB.timer); return; }
    if (document.hidden) return;
    if ($('modal') && !$('modal').hidden) return;
    apiLatest('web', 'web').then(function (d) { liveRun(function () { drawWeb(d); }); }).catch(function () {});
  }, 5000);
}
function daysLeft(ts) { return ts ? Math.floor((ts - Date.now() / 1000) / 86400) : null; }
function certTone(days) { return days === null ? 'dim' : (days < 0 ? 'crit' : (days < 21 ? 'warn' : 'ok')); }
function webTargetWords(t) { return t === 'vip' ? 'the web address' : t; }

function certCard(d, target) {
  var prof = d.tls[target];
  var node = (d.nodes || []).filter(function (n) { return n.name === target; })[0];
  var w = target === 'vip' ? null : ((node || {}).web || {});
  var info = (prof && prof.info) || (w && w.cert_now) || null;
  if (target === 'vip' && !info) {
    var holder = (d.nodes || []).filter(function (n) { return (n.web || {}).vip_cert_now; })[0];
    if (holder && prof) info = holder.web.vip_cert_now;
  }
  var card = el('section', 'cert-card');
  var head = el('header', 'cert-h');
  var title = el('div', 'cert-title');
  title.appendChild(el('span', 'cert-target', target === 'vip' ? 'The web address (VIP) of the cluster' : 'Node'));
  title.appendChild(noI18n(el('b', '', target === 'vip' ? (d.vip.fqdn || d.vip.address || '–') : target)));
  if (target === 'vip') {
    /* Said plainly what this card is (1.0.50). */
    title.appendChild(el('span', 'cert-for', d.vip.address
      ? 'the certificate answered on the VIP ' + String(d.vip.address).split('/')[0] + ', whichever node holds it'
      : 'the certificate of the VIP - the address is set on Settings → High availability'));
  }
  if (node && node.me) title.appendChild(el('span', 'tag dim', 'this one'));
  if (target !== 'vip') {
    /* The same line under every name, so the cards stand level (1.0.51). */
    title.appendChild(el('span', 'cert-for', 'the certificate answered on ' + target + '\'s own name and address' +
      (node && node.address ? ' (' + node.address + ')' : '')));
  }
  head.appendChild(title);
  var days = info ? daysLeft(info.not_after) : null;
  var badge = el('span', 'tag ' + certTone(days), days === null ? 'no certificate' :
    (days < 0 ? 'ran out' : (days < 21 ? days + ' days left' : 'valid')));
  head.appendChild(badge);
  card.appendChild(head);
  if (info) {
    var b = el('div', 'cert-body');
    b.appendChild(noI18n(el('div', 'cert-cn', info.cn || info.subject || '')));
    var bar = el('div', 'cert-life');
    var span = info.not_after && info.not_before ? (info.not_after - info.not_before) : 1;
    var used = info.not_before ? Math.max(0, Math.min(1, (Date.now() / 1000 - info.not_before) / span)) : 0;
    var fill = el('span', 'cert-life-fill ' + certTone(days));
    fill.style.width = Math.round(used * 100) + '%';
    bar.appendChild(fill);
    b.appendChild(bar);
    var facts = [['Issued by', noI18n(el('span', '', info.self_signed ? 'itself (self-signed)' : (info.issuer || '').replace(/^CN=/, '')))],
                 ['Valid until', info.not_after ? stamp(info.not_after) : '–'],
                 ['Key', info.key || '–']];
    if (info.san && info.san.length) facts.push(['Names', noI18n(el('span', '', info.san.join(', ')))]);
    if (prof) {
      facts.push(['Chain', prof.chain_info ? (prof.chain_info.length + ' between it and the root') : '–']);
      facts.push(['Root', prof.root_info && prof.root_info.length ? noI18n(el('span', '', prof.root_info[0].cn || 'given')) : 'not given']);
      if (prof.verify) facts.push(['Checked', prof.verify === 'ok' ? el('span', 'good', 'the chain leads to the root') : el('span', 'bad', prof.verify)]);
    }
    var kv = el('dl', 'cert-kv');
    facts.forEach(function (f) {
      kv.appendChild(el('dt', '', f[0]));
      var dd = el('dd');
      if (f[1] && f[1].nodeType) dd.appendChild(f[1]); else dd.textContent = f[1];
      kv.appendChild(dd);
    });
    b.appendChild(kv);
    card.appendChild(b);
  } else {
    card.appendChild(el('p', 'note', target === 'vip'
      ? 'None of its own: the web address answers with the certificate of the node it is on.'
      : 'Not known yet.'));
  }
  /* How TLS is spoken, as chips. */
  var chips = el('div', 'cert-chips');
  var preset = (prof && prof.preset) || 'standard';
  chips.appendChild(el('span', 'cchip', {standard: 'TLS 1.2 + 1.3, ECDHE', intermediate: 'Mozilla intermediate', modern: 'TLS 1.3 only', custom: 'custom'}[preset] || preset));
  if (prof && prof.dh && prof.dh !== 'none') chips.appendChild(noI18n(el('span', 'cchip', 'DH ' + prof.dh)));
  if (prof && prof.hsts) chips.appendChild(el('span', 'cchip', 'HSTS ' + Math.round(prof.hsts / 86400) + ' days'));
  if (prof && prof.pending) chips.appendChild(el('span', 'cchip warn', 'a request waits for its certificate'));
  if (!prof && target !== 'vip') chips.appendChild(el('span', 'cchip dim', 'as install.sh made it'));
  card.appendChild(chips);
  /* Is it in place on the node? */
  if (target === 'vip' && prof && d.vip && d.vip.on) {
    /* The web address's certificate is put in on every node (1.0.51). */
    (d.nodes || []).forEach(function (n) {
      var nw = n.web || {};
      if (nw.progress) { card.appendChild(certProgress(nw.progress, n.name)); return; }
      var st2 = el('div', 'cert-state');
      st2.appendChild(el('span', 'dot ' + (nw.state === 'failed' ? 'crit' : (nw.current ? 'ok' : 'warn'))));
      st2.appendChild(el('span', '', nw.state === 'failed' ? n.name + ': ' + ((nw.said || []).slice(-1)[0] || 'failed')
        : (nw.current ? 'in place on ' + n.name : 'being put in on ' + n.name + '…')));
      card.appendChild(st2);
    });
  } else if (target === 'vip' && prof && d.vip && !d.vip.on) {
    card.appendChild(el('p', 'note small', 'Put in on the nodes once the web address is turned on (Settings → High availability).'));
  }
  if (target !== 'vip' && w && w.progress) {
    card.appendChild(certProgress(w.progress, target));
  } else if (prof && target !== 'vip' && w) {
    var st = el('div', 'cert-state');
    st.appendChild(el('span', 'dot ' + (w.state === 'failed' ? 'crit' : (w.current ? 'ok' : 'warn'))));
    st.appendChild(el('span', '', w.state === 'failed' ? 'root could not put it in: ' + ((w.said || []).slice(-1)[0] || '')
      : (w.current ? 'in place on ' + target : 'being put in on ' + target + '…')));
    card.appendChild(st);
  }
  if (d.may) {
    var tools = el('div', 'cert-tools');
    var up = cmdButton('Upload', 'upload', 'small');
    up.onclick = function () { certUpload(target, prof); };
    tools.appendChild(up);
    var req = cmdButton(prof && prof.pending ? 'The waiting request' : 'Request (CSR)', 'list', 'small');
    req.onclick = function () { certRequest(target, prof); };
    tools.appendChild(req);
    var ss = cmdButton('Self-signed', 'key', 'small');
    ss.onclick = function () { certSelf(target, d); };
    tools.appendChild(ss);
    var pol = cmdButton('TLS settings', 'gear', 'small');
    pol.onclick = function () { certPolicy(target, prof, d); };
    tools.appendChild(pol);
    if (prof && prof.cert) {
      var dl = cmdButton('Download', 'download', 'small');
      dl.title = 'The certificate and its chain, as PEM - without the key';
      dl.onclick = function () {
        api('web', {action: 'tls_pem', target: target}).then(function (x) {
          saveFile((target === 'vip' ? 'web-address' : target) + '.pem', x.pem);
        }).catch(oops);
      };
      tools.appendChild(dl);
      var fg = cmdButton('Let go', 'forget', 'small danger-soft');
      fg.title = 'ai stops looking after it (nginx keeps what it has)';
      fg.onclick = function () {
        confirmThen('Stop looking after the TLS of ' + webTargetWords(target), 'nginx keeps the files it has now; ai no longer changes them.', 'Stop', function () {
          api('web', {action: 'tls_forget', target: target}).then(function (x) { toast(x.message, 'good'); loadWeb(); }).catch(oops);
        });
      };
      tools.appendChild(fg);
    }
    card.appendChild(tools);
  }
  return card;
}

/* What root is doing on a node, as a bar (1.0.50): the steps done, and in
   the long one - making DH parameters - the time gone against the time it
   usually takes (never shown as more than 95 % before it is done). */
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

/* Files read in the browser: PEM as text, a PFX as base64. */
function readCertFiles(files) {
  return Promise.all(Array.prototype.map.call(files, function (f) {
    return new Promise(function (ok, bad) {
      if (f.size > 200000) { bad(new Error(f.name + ' is far bigger than any certificate file')); return; }
      var r = new FileReader();
      r.onload = function () {
        var bytesArr = new Uint8Array(r.result);
        var head = String.fromCharCode.apply(null, bytesArr.slice(0, Math.min(bytesArr.length, 4096)));
        if (/-----BEGIN /.test(head) || /-----BEGIN /.test(new TextDecoder().decode(bytesArr))) {
          ok({name: f.name, pem: new TextDecoder().decode(bytesArr)});
        } else {
          var bin = '';
          for (var i = 0; i < bytesArr.length; i++) bin += String.fromCharCode(bytesArr[i]);
          ok({name: f.name, pfx: btoa(bin)});
        }
      };
      r.onerror = function () { bad(new Error(f.name + ' could not be read')); };
      r.readAsArrayBuffer(f);
    });
  }));
}

var CERT_PASTE_HINT = '-----BEGIN CERTIFICATE-----\n' +
  '1. the certificate of this name (the server\'s own)\n' +
  '-----END CERTIFICATE-----\n' +
  '-----BEGIN CERTIFICATE-----\n' +
  '2. the intermediate certificate(s), if there are any - one block each\n' +
  '-----END CERTIFICATE-----\n' +
  '-----BEGIN CERTIFICATE-----\n' +
  '3. the root certificate (optional)\n' +
  '-----END CERTIFICATE-----\n' +
  '-----BEGIN PRIVATE KEY-----\n' +
  '4. its private key (not needed when the request was made here)\n' +
  '-----END PRIVATE KEY-----\n\n' +
  'Any order is taken: they are sorted by themselves.';
function certUpload(target, prof) {
  var got = [];
  modal('A certificate for ' + webTargetWords(target), function (body) {
    body.appendChild(el('p', 'note', 'PEM files - the certificate, its key, the chain, the root, in any order or all in one - or one PFX / PKCS#12 file. ' +
      (prof && prof.pending ? 'A request waits here: the certificate the authority sent back is enough, its key is here.' : 'The key has to come with it.')));
    var drop = el('div', 'drop');
    var inp = el('input'); inp.type = 'file'; inp.multiple = true; inp.hidden = true;
    inp.accept = '.pem,.crt,.cer,.key,.pfx,.p12,.chain,.ca,.txt';
    var says = el('span', '', 'Drop the files here, or press to choose them');
    drop.appendChild(inp); drop.appendChild(says);
    var list = el('div', 'cert-files');
    function take(files) {
      readCertFiles(files).then(function (r) {
        got = got.concat(r);
        clear(list);
        got.forEach(function (x) { list.appendChild(noI18n(el('span', 'cchip', x.name + (x.pfx ? ' (PFX)' : ' (PEM)')))); });
        says.textContent = 'Read: ' + got.length + ' file(s). More can be added.';
      }).catch(oops);
    }
    drop.onclick = function () { inp.click(); };
    inp.onchange = function () { take(inp.files); inp.value = ''; };
    drop.addEventListener('dragover', function (e) { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', function () { drop.classList.remove('over'); });
    drop.addEventListener('drop', function (e) { e.preventDefault(); drop.classList.remove('over'); take(e.dataTransfer.files); });
    body.appendChild(drop);
    body.appendChild(list);
    var paste = el('textarea', 'mono cert-paste');
    paste.id = 'cu-paste';
    paste.rows = 16;
    /* The usual order shown in the box itself (1.0.50); any order is taken. */
    paste.placeholder = CERT_PASTE_HINT;
    paste.spellcheck = false;
    body.appendChild(formField('Or paste PEM here', paste));
    var pw = secretBox('', 'only for a PFX or a key with a passphrase', 'mono');
    pw.id = 'cu-pw';
    body.appendChild(formField('Password', pw, 'Used here to open it, and not kept.'));
    body.appendChild(el('div', 'said', '')).id = 'cu-said';
  }, [{words: 'Cancel', close: true},
      {words: 'Put it in', cls: 'primary', icon: 'save', go: function (b) {
        var pem = got.filter(function (x) { return x.pem; }).map(function (x) { return x.pem; }).join('\n') + '\n' + ($('cu-paste').value || '');
        var pfx = got.filter(function (x) { return x.pfx; });
        if (pfx.length > 1) { toast('one PFX / PKCS#12 file at a time', 'bad'); return; }
        if (!pfx.length && !/-----BEGIN /.test(pem)) { toast('choose the files first, or paste the PEM', 'bad'); return; }
        busy(b, true);
        api('web', {action: 'tls_upload', target: target, cert: pem, pfx: pfx.length ? pfx[0].pfx : '',
                    password: ($('cu-pw') || {}).value || ''}).then(function (x) {
          toast(x.message, 'good'); closeModal(); loadWeb();
        }).catch(function (e) { $('cu-said').className = 'said bad'; $('cu-said').textContent = e.message; }).then(function () { busy(b, false); });
      }}], 'medium');
}

function certNamesDefault(target, d) {
  if (target === 'vip') return d.vip.fqdn || '';
  var n = (d.nodes || []).filter(function (x) { return x.name === target; })[0];
  return n && /\./.test(n.host || '') ? n.host : '';
}
function certSubjectFields(body, target, d, withDays) {
  var g = el('div', 'formgrid');
  var cn = textBox(certNamesDefault(target, d), 'ai.example.cz', 'mono'); cn.id = 'cs-cn';
  var names = textBox('', 'claude.example.cz, 192.0.2.11', 'mono'); names.id = 'cs-names';
  var kind = selectBox([['rsa2048', 'RSA 2048'], ['rsa3072', 'RSA 3072'], ['rsa4096', 'RSA 4096'], ['ec', 'EC P-256']], 'rsa2048'); kind.id = 'cs-kind';
  g.appendChild(formField('The name (CN)', cn, 'What people type in the browser.'));
  g.appendChild(formField('Other names', names, 'More names or addresses it is good for, by commas.'));
  g.appendChild(formField('The key', kind));
  var org = textBox('', 'Krajský úřad'); org.id = 'cs-org';
  g.appendChild(formField('Organisation', org));
  if (withDays) {
    var days = selectBox([['365', '1 year'], ['825', '27 months'], ['1825', '5 years'], ['3650', '10 years']], '825'); days.id = 'cs-days';
    g.appendChild(formField('Valid for', days));
  } else {
    var unit = textBox('', 'IT'); unit.id = 'cs-unit';
    var city = textBox('', 'Olomouc'); city.id = 'cs-city';
    var country = textBox('CZ', 'CZ'); country.id = 'cs-country'; country.maxLength = 2;
    g.appendChild(formField('Unit', unit));
    g.appendChild(formField('City', city));
    g.appendChild(formField('Country', country));
  }
  body.appendChild(g);
}
function certSubjectValues() {
  var v = function (id) { return ($(id) || {}).value || ''; };
  return {cn: v('cs-cn').trim(), names: v('cs-names'), kind: v('cs-kind'), org: v('cs-org'),
          unit: v('cs-unit'), city: v('cs-city'), country: v('cs-country'), days: v('cs-days')};
}

function certRequest(target, prof) {
  if (prof && prof.pending && prof.csr) { showCsr(target, prof.csr, prof); return; }
  modal('A certificate request for ' + webTargetWords(target), function (body) {
    body.appendChild(el('p', 'note', 'A new key is made here and stays here; the request (CSR) goes to your certificate authority. Upload what it sends back - the certificate alone is enough.'));
    certSubjectFields(body, target, WEB.last || {vip: {}}, false);
  }, [{words: 'Cancel', close: true},
      {words: 'Make the request', cls: 'primary', icon: 'list', go: function (b) {
        busy(b, true);
        api('web', Object.assign({action: 'tls_csr', target: target}, certSubjectValues())).then(function (x) {
          closeModal(); loadWeb(); showCsr(target, x.csr, x.tls);
        }).catch(oops).then(function () { busy(b, false); });
      }}], 'medium');
}
function showCsr(target, csr, prof) {
  modal('The request for ' + webTargetWords(target), function (body) {
    body.appendChild(el('p', 'note', 'Give this to your certificate authority. The key waits here; once the certificate comes back, upload it.'));
    var pre = noI18n(el('pre', 'mono cert-csr', csr));
    copyOnClick(pre, csr, 'the request was copied');
    body.appendChild(pre);
  }, [{words: 'Drop the request', icon: 'trash', go: function () {
        modalOver(function () { confirmThen('Drop the request', 'Its waiting key goes too; a certificate made for it can then not be used.', 'Drop it', function () {
          api('web', {action: 'tls_csr_drop', target: target}).then(function (x) { toast(x.message, 'good'); loadWeb(); }).catch(oops);
        }, true); });
      }},
      {words: 'Download .csr', icon: 'download', go: function () { saveFile((target === 'vip' ? 'web-address' : target) + '.csr', csr); }},
      {spacer: true},
      {words: 'Upload the certificate…', cls: 'primary', icon: 'upload', go: function () { closeModal(); certUpload(target, {pending: true}); }},
      {words: 'Close', close: true}], 'medium');
}

function certSelf(target, d) {
  modal('A self-signed certificate for ' + webTargetWords(target), function (body) {
    body.appendChild(el('p', 'note warn', 'Browsers warn about a self-signed certificate until it is trusted by hand. Good for a test, or until the real one comes.'));
    certSubjectFields(body, target, d, true);
  }, [{words: 'Cancel', close: true},
      {words: 'Make it and put it in', cls: 'primary', icon: 'key', go: function (b) {
        busy(b, true);
        api('web', Object.assign({action: 'tls_selfsigned', target: target}, certSubjectValues())).then(function (x) {
          toast(x.message, 'good'); closeModal(); loadWeb();
        }).catch(oops).then(function () { busy(b, false); });
      }}], 'medium');
}

function certPolicy(target, prof, d) {
  prof = prof || {};
  var st = {preset: prof.preset || 'standard',
            protocols: (prof.protocols || ['TLSv1.2', 'TLSv1.3']).slice(),
            ciphers: prof.ciphers || (d.presets.standard || {}).ciphers || '',
            dh: prof.dh || 'none', prefer: !!prof.prefer, hsts: (prof.hsts === undefined || prof.hsts === null || prof.hsts === '') ? 63072000 : Number(prof.hsts)};
  var PRESETS = [
    ['standard', 'Standard', 'TLS 1.2 + 1.3', 'ECDHE with AES-GCM and ChaCha20. Every browser of the last ten years.', 'recommended'],
    ['intermediate', 'Mozilla intermediate', 'TLS 1.2 + 1.3', 'Adds the DHE ciphers, for old clients. Wants DH parameters.', ''],
    ['modern', 'Mozilla modern', 'TLS 1.3 only', 'The strongest; old systems and some scanners cannot connect.', ''],
    ['custom', 'Custom', 'chosen here', 'The protocols and an OpenSSL cipher list of your own.', '']];
  modal('How ' + webTargetWords(target) + ' speaks TLS', function (body) {
    /* The protocols and ciphers: one tile each. */
    body.appendChild(el('h4', 'tls-h', 'Protocols and ciphers'));
    var tiles = el('div', 'tls-tiles');
    var custom = el('div', 'tls-custom');
    var used = el('details', 'tls-used');
    function paint() {
      Array.prototype.forEach.call(tiles.children, function (t) { t.classList.toggle('on', t.dataset.k === st.preset); });
      custom.hidden = st.preset !== 'custom';
      used.hidden = st.preset === 'custom';
      var p = d.presets[st.preset];
      if (p) {
        clear(used);
        used.appendChild(el('summary', '', 'The ciphers it uses'));
        used.appendChild(noI18n(el('code', 'tls-cipherlist', p.ciphers ? p.ciphers.split(':').join('\n') : 'TLS 1.3 chooses its own: TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256, TLS_AES_128_GCM_SHA256')));
      }
      dhRow.classList.toggle('dim', st.preset === 'modern' || (st.preset === 'standard' && st.dh === 'none'));
    }
    PRESETS.forEach(function (p) {
      var t = el('button', 'tls-tile');
      t.type = 'button';
      t.dataset.k = p[0];
      var top = el('div', 'tls-tile-top');
      top.appendChild(el('b', '', p[1]));
      if (p[4]) top.appendChild(el('span', 'tag ok', p[4]));
      t.appendChild(top);
      t.appendChild(el('div', 'tls-tile-prot', p[2]));
      t.appendChild(el('div', 'tls-tile-s', p[3]));
      t.onclick = function () { st.preset = p[0]; paint(); };
      tiles.appendChild(t);
    });
    body.appendChild(tiles);
    /* Custom: the protocols as switches, the cipher list. */
    var prow = el('div', 'tls-prot');
    ['TLSv1.2', 'TLSv1.3'].forEach(function (v) {
      var b = el('button', 'tls-pill');
      b.type = 'button';
      b.textContent = v.replace('TLSv', 'TLS ');
      noI18n(b);
      var sync = function () { b.classList.toggle('on', st.protocols.indexOf(v) >= 0); };
      b.onclick = function () {
        var i = st.protocols.indexOf(v);
        if (i >= 0 && st.protocols.length > 1) st.protocols.splice(i, 1); else if (i < 0) st.protocols.push(v);
        sync();
      };
      sync();
      prow.appendChild(b);
    });
    custom.appendChild(el('div', 'tls-sub', 'Protocols'));
    custom.appendChild(prow);
    var ciphers = el('textarea', 'mono tls-ciphers');
    ciphers.rows = 4; ciphers.spellcheck = false; ciphers.value = st.ciphers;
    ciphers.oninput = function () { st.ciphers = ciphers.value; };
    custom.appendChild(el('div', 'tls-sub', 'Ciphers for TLS 1.2 (an OpenSSL list; TLS 1.3 chooses its own)'));
    custom.appendChild(ciphers);
    body.appendChild(custom);
    body.appendChild(used);
    /* The rest, row by row. */
    body.appendChild(el('h4', 'tls-h', 'More'));
    var rows = el('div', 'tls-rows');
    var dh = selectBox(Object.keys(d.dh).map(function (k) { return [k, d.dh[k]]; }), st.dh);
    dh.onchange = function () { st.dh = dh.value; paint(); };
    var dhRow = tlsRow('DH parameters', 'Only the DHE ciphers use them (Mozilla intermediate, or your own). An RFC 7919 group is ready at once; made here takes from seconds to minutes.', dh);
    rows.appendChild(dhRow);
    var prefer = switchBox(st.prefer);
    prefer._input.onchange = function () { st.prefer = !!prefer._get(); };
    rows.appendChild(tlsRow('The server chooses the cipher', 'Off is right for these lists: every cipher in them is strong, and the client knows best which is fast for it.', prefer));
    var seg = el('div', 'seg');
    [[0, 'off'], [15768000, '6 months'], [31536000, '1 year'], [63072000, '2 years']].forEach(function (o) {
      var b = el('button', '', o[1]);
      b.type = 'button';
      b.onclick = function () { st.hsts = o[0]; Array.prototype.forEach.call(seg.children, function (x) { x.classList.toggle('on', x === b); }); };
      if (st.hsts === o[0]) b.classList.add('on');
      seg.appendChild(b);
    });
    if (!seg.querySelector('.on')) seg.children[0].classList.add('on');
    rows.appendChild(tlsRow('HSTS', 'A browser that saw it comes back only over HTTPS for that long. Turn it on once HTTPS is surely staying.', seg));
    body.appendChild(rows);
    paint();
  }, [{words: 'Cancel', close: true},
      {words: 'Save', cls: 'primary', icon: 'save', go: function (b) {
        busy(b, true);
        api('web', {action: 'tls_policy', target: target, preset: st.preset, protocols: st.protocols,
                    ciphers: String(st.ciphers || '').trim(), dh: st.dh, prefer: st.prefer ? 1 : 0,
                    hsts: st.hsts}).then(function (x) {
          toast(x.message, 'good'); closeModal(); loadWeb();
        }).catch(oops).then(function () { busy(b, false); });
      }}], 'medium');
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

function drawWeb(d) {
  WEB.last = d;
  var host = $('web-certs');
  liveFill(host, function (host) {
  Object.keys(d.tls).forEach(function (t) {
    if (t === 'vip' && !d.cluster) return;
    host.appendChild(certCard(d, t));
  });
  }, undefined, function () { explainWhatWasDrawn($('pane-web')); });
}

/* ---- power: the services only (the server itself is otp's pane, system.js) ---- */
function powerDo(what) {
  api('power', {how: what}).then(function (d) { toast(d.message, 'good'); }).catch(oops);
}
$('pw-ai').onclick = function () { powerDo('restart-ai'); };
$('pw-web').onclick = function () { powerDo('restart-web'); };

/* ---- upgrades ---------------------------------------------------------------------------- */
function loadUpgrade(quiet) {
  api('upgrade').then(function (d) {
    var host = $('up-web');
    if (!quiet || host._at !== (d.online && d.online.at)) {
      host._at = d.online && d.online.at;
      clear(host);
      var o = d.online || {};
      host.appendChild(kvTable([
        ['Here', 'ai ' + d.here],
        ['Looked at', noI18n(el('span', 'mono small', d.url || '–'))],
        ['Last look', o.at ? stamp(o.at) + (o.error ? ' - ' + o.error : '') : 'never'],
        ['Newest there', o.newest ? o.newest.version : '–'],
        ['Release keys trusted', (d.keys || []).join(', ') || 'none']
      ]));
      if (d.newer.length) {
        var row = el('div', 'btnrow');
        row.style.marginTop = '12px';
        var pick = selectBox(d.newer.map(function (p) { return [p.version, 'ai ' + p.version]; }), d.newer[0].version);
        row.appendChild(pick);
        var go = cmdButton('Upgrade now', 'up', 'primary');
        go.onclick = function () {
          confirmThen('Upgrade to ' + pick.value + '?', 'It is fetched, checked and put in. The terminals go on running; these pages are back after a few seconds.', 'Upgrade', function () {
            busy(go, true);
            api('upgrade', {do: 'install', version: pick.value}, 600).then(function () { toast('the upgrade is running', 'good'); loadUpgrade(); })
              .catch(oops).then(function () { busy(go, false); });
          }, false);
        };
        row.appendChild(go);
        host.appendChild(row);
      } else if (o.at && !o.error) host.appendChild(el('p', 'note good', 'This is the newest version there.'));
    }
    var st = d.status;
    $('up-state').textContent = st ? (st.version ? 'ai ' + st.version + ' · ' : '') + ({running: 'running', done: 'done', failed: 'failed', lost: 'lost'}[st.state] || st.state || '') + ' · ' + stamp(st.at) + (st.said ? ' · ' + st.said : '') : '';
    var log = $('up-log');
    log.textContent = d.log || '–';
    log.scrollTop = log.scrollHeight;
  }).catch(function (e) { if (!quiet) oops(e); });
}
$('up-look').onclick = function () {
  busy($('up-look'), true);
  api('upgrade', {do: 'look'}, 60).then(function () { loadUpgrade(); }).catch(oops).then(function () { busy($('up-look'), false); });
};
$('up-send').onclick = function () { $('up-input').click(); };
$('up-input').onchange = function () {
  var f = $('up-input').files[0];
  $('up-input').value = '';
  if (!f) return;
  var host = $('up-sent');
  clear(host);
  host.appendChild(el('p', 'muted', 'sending ' + f.name + '…'));
  sendFile('/files/package?name=' + encodeURIComponent(f.name), f).then(function (d) {
    clear(host);
    var i = d.info;
    host.appendChild(kvTable([['Version', i.version], ['Signed by', i.signed_by], ['Files', String(i.files)], ['Here now', i.installed]]));
    if (i.changelog) { var p = el('pre', 'lines'); p.textContent = i.changelog; host.appendChild(p); }
    var go = cmdButton('Put it in', 'up', 'primary');
    go.onclick = function () {
      busy(go, true);
      sendFile('/files/package?install=1&name=' + encodeURIComponent(f.name), f).then(function () { toast('the upgrade is running', 'good'); loadUpgrade(); })
        .catch(oops).then(function () { busy(go, false); });
    };
    host.appendChild(go);
  }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
};

/* ---- about ---------------------------------------------------------------------------- */
function loadAbout() {
  api('machine').then(function (d) {
    var host = $('about-state'), m = d.machine;
    clear(host);
    host.appendChild(kvTable([
      ['ai', m.software.ai], ['Server', m.host + ' · ' + m.os],
      ['Software', noI18n(el('span', 'small', Object.keys(m.software).filter(function (k) { return m.software[k]; }).map(function (k) { return k + ' ' + m.software[k]; }).join(' · ')))],
      ['PHP of the pages', PHP_SAFETY ? PHP_SAFETY.version + (PHP_SAFETY.patched ? '' : ' - not fixed against php2shell, guarded') : '–'],
      ['Its folders', noI18n(el('span', 'mono small', d.paths.state + ' · ' + d.paths.config + ' · ' + d.paths.log))],
      ['On the command line', noI18n(el('span', 'mono', 'ai --status · ai --sessions · ai --attach ID'))]
    ]));
  }).catch(oops);
}
function loadConsoleLogin() {
  api('console-login').then(function (d) {
    var host = $('ab-console');
    clear(host);
    var sw = switchBox(d.on);
    sw._input.onchange = function () {
      api('console-login', {on: !!sw._get()}).then(function (r) { toast(r.message, 'good'); }).catch(oops);
    };
    host.appendChild(formField('It opens when root signs in', sw, d.there ? '' : '/etc/profile.d/zz-ai-console.sh is not there - install.sh --upgrade puts it in.'));
  }).catch(oops);
}
$('ab-log').onclick = function () {
  api('log').then(function (d) { var p = $('ab-logtext'); p.textContent = d.text || '(empty)'; p.scrollTop = p.scrollHeight; }).catch(oops);
};

/* ==========================================================================
   Starting
   ========================================================================== */
(function start() {
  hideForRole();
  dressButtons(document);
  explainWhatWasDrawn(document);
  if (STATUS) paintHeader(STATUS);
  phpSafety();
  var h = (location.hash || '').replace(/^#/, '').split('/');
  var tab = h[0] || 'terms', sub = h.slice(1).join('/');
  if (tab === 'files' && sub) sub = decodeURIComponent(sub);
  showTab(tab, sub || undefined);
  liveLoop();
  if (ME && ME.must_change) setTimeout(mustChange, 50);
  window.addEventListener('beforeunload', function () { termClose(); });
}());

/* ---- from otp: who is locked out (1.0.112) -------------------------------------
   Who has wrong attempts counted, how long the lockout still runs - cleared
   one by one or all at once. Fetched again every 10 s while the card is on
   the screen; the time left counts down every second in between. */
var LO = {data: null, skew: 0, fetched: 0, timer: null};
function loadLockouts() {
  if (!ADMIN || !$('lo-table')) return;
  api('lockouts').then(function (d) {
    LO.data = d;
    LO.skew = d.now - Date.now() / 1000;
    LO.fetched = Date.now();
    drawLockouts();
    if (!LO.timer) LO.timer = setInterval(loTick, 1000);
  }).catch(function (e) { if (LO.timer) { clearInterval(LO.timer); LO.timer = null; } oops(e); });
}
function loTick() {
  var c = $('lo-card');
  if (!c || !c.offsetParent || document.hidden) { clearInterval(LO.timer); LO.timer = null; return; }
  if (Date.now() - LO.fetched > 10000) { LO.fetched = Date.now(); loadLockouts(); return; }
  drawLockouts();
}
function loNow() { return Date.now() / 1000 + LO.skew; }
function loClear(body, words) {
  api('lockouts', body).then(function (r) { toast(words || r.message, 'good'); loadLockouts(); }).catch(oops);
}
function loBar(n, limit, locked) {
  var bar = el('div', 'lo-bar' + (locked ? ' full' : ''));
  var fill = el('i');
  fill.style.width = (limit ? Math.min(100, Math.round(100 * n / limit)) : 0) + '%';
  bar.appendChild(fill);
  return bar;
}
function drawLockouts() {
  var d = LO.data, host = $('lo-table');
  if (!d || !host) return;
  var now = loNow();
  var rows = [];
  (d.nodes || []).forEach(function (n) {
    (n.rows || []).forEach(function (r) {
      if (r.forgets <= now) return;
      var x = Object.assign({}, r);
      if (x.locked && x.until <= now) x.locked = false;
      rows.push(x);
    });
  });
  rows.sort(function (a, b) { return (b.locked - a.locked) || (b.last - a.last); });
  liveFill($('lo-tools'), function (tools) {
    var locked = rows.filter(function (r) { return r.locked; }).length;
    if (!rows.length) return;
    if (locked) { var lc = el('span', 'small bad', num(locked) + ' locked out'); lc.style.marginRight = '12px'; tools.appendChild(lc); }
    var all = cmdButton('Clear them all', 'broom', 'small');
    all.onclick = function () {
      confirmThen('Clear every lockout?', 'Every count of wrong attempts is forgotten - the locked out may try again at once. Events keeps a line saying who did it.', 'Clear them all', function () {
        loClear({action: 'clear_all'});
      }, false);
    };
    tools.appendChild(all);
  }, true);
  liveFill(host, function (host) {
    if (!rows.length) { host.appendChild(el('p', 'note good', 'Nobody is locked out, and no wrong attempt is being counted.')); return; }
    host.appendChild(listTable(['State', 'Who', 'Where', 'How many', 'Last', ''], rows, function (r) {
      var tr = el('tr', r.locked ? 'lo-locked' : '');
      var st = el('td');
      if (r.locked) {
        st.appendChild(el('span', 'tag crit', 'locked out'));
        st.appendChild(el('div', 'small', span(r.until - now) + ' left'));
      } else {
        st.appendChild(el('span', 'tag load', 'counting'));
        st.appendChild(el('div', 'small muted', 'forgotten in ' + span(r.forgets - now)));
      }
      tr.appendChild(st);
      var who = el('td');
      who.appendChild(noI18n(el('div', 'mono', r.who)));
      who.appendChild(el('div', 'small muted', r.by === 'address' ? 'an address' : 'a name'));
      tr.appendChild(who);
      tr.appendChild(el('td', 'small', r.what));
      var w = el('td', 'num lo-count');
      var line = el('div');
      line.appendChild(noI18n(el('b', '', num(r.fails))));
      line.appendChild(document.createTextNode(' / ' + num(r.limit)));
      w.appendChild(line);
      w.appendChild(loBar(r.fails, r.limit, r.locked));
      tr.appendChild(w);
      tr.appendChild(el('td', 'muted small', ago(r.last - LO.skew)));
      var a = el('td', 'rowtools');
      var x = cmdButton('Clear', 'broom', 'small');
      explain(x, 'Its count of wrong attempts is forgotten: it may try again at once.');
      x.onclick = function () { loClear({action: 'clear', who: r.who}, 'cleared: ' + r.who); };
      a.appendChild(x);
      tr.appendChild(a);
      return tr;
    }, 'plain'));
  }, true);
}

/* ---- from otp: mail (1.0.20) ------------------------------------------------------ */
function stepsList(steps) {
  var list = el('div', 'steps');
  (steps || []).forEach(function (s) {
    var row = el('div', 'step ' + (s.ok ? 'ok' : 'bad'));
    var mark = el('span', 'step-mark');
    mark.innerHTML = iconMarkup(s.ok ? 'check' : 'cancel', 15);
    row.appendChild(mark);
    var words = el('span', 'step-words');
    words.appendChild(el('b', '', s.what));
    if (s.said) words.appendChild(el('span', 'd', s.said));
    if (s.ms !== undefined) words.appendChild(el('span', 'd', s.ms + ' ms'));
    row.appendChild(words);
    list.appendChild(row);
  });
  return list;
}
function certTable(list, drop) {
  return listTable(['It is', 'Signed by', 'Good from', 'Good until', 'Fingerprint (SHA-256)', ''], list, function (c) {
    var tr = el('tr');
    tr.appendChild(noI18n(el('td', '', c.subject || '–')));
    var by = el('td');
    if (c.self_signed) by.appendChild(el('span', 'tag info', 'itself - a root'));
    else by.appendChild(noI18n(el('span', '', c.issuer || '–')));
    tr.appendChild(by);
    var when = function (t) { var ms = Date.parse(t || ''); return isNaN(ms) ? (t || '–') : dayWords(new Date(ms)); };
    tr.appendChild(el('td', 'muted small', when(c.from)));
    var left = c.until ? (Date.parse(c.until) - Date.now()) / 86400000 : null;
    var tone = left === null || isNaN(left) ? '' : (left < 0 ? 'bad' : (left < 60 ? 'warn' : 'good'));
    tr.appendChild(el('td', 'small ' + tone, when(c.until)));
    var fp = noI18n(el('td', 'mono small muted fp-full'));
    var hex = (c.fingerprint || '').replace(/[^0-9a-fA-F]/g, '').toLowerCase();
    var half = Math.ceil(hex.length / 4) * 2;
    [hex.slice(0, half), hex.slice(half)].forEach(function (part) {
      if (part) fp.appendChild(el('div', '', part.replace(/(..)(?=.)/g, '$1:')));
    });
    fp.title = hex.replace(/(..)(?=.)/g, '$1:');
    tr.appendChild(fp);
    var tools = el('td', 'rowtools');
    if (ADMIN && drop) {
      var x = iconButton('trash', 'Take this certificate out');
      x.onclick = function () { drop(c); };
      tools.appendChild(x);
    }
    tr.appendChild(tools);
    return tr;
  });
}
/** A certificate file read into a box: PEM as it is, a DER .cer written out as PEM. */
function readCertFile(file, box) {
  var reader = new FileReader();
  reader.onload = function () {
    var bytes = new Uint8Array(reader.result || new ArrayBuffer(0));
    var text = '';
    try { text = new TextDecoder('utf-8').decode(bytes); } catch (e) { text = ''; }
    if (text.indexOf('-----BEGIN CERTIFICATE-----') < 0 && bytes.length && bytes[0] === 0x30) {
      var bin = '';
      for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
      text = '-----BEGIN CERTIFICATE-----\n' + btoa(bin).replace(/(.{64})/g, '$1\n').replace(/\n$/, '')
        + '\n-----END CERTIFICATE-----';
    }
    var ok = text.indexOf('-----BEGIN CERTIFICATE-----') >= 0;
    box.value = ok ? text.trim() : '';
    box.dispatchEvent(new Event('input'));
    toast(ok ? 'read ' + file.name + ' - Save the changes adds it' : file.name + ' is not a certificate', ok ? 'good' : 'bad');
  };
  reader.readAsArrayBuffer(file);
}
function saveFile(name, text, type) {
  var a = el('a');
  a.href = URL.createObjectURL(new Blob([text], {type: type || 'application/json'}));
  a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}
function loadMail() {
  return api('mail').then(function (d) {
    var list = d.ca_list || [];
    $('mca-when').textContent = list.length ? num(list.length) + ' certificate(s) kept' : 'none imported';
    $('mca-drop').hidden = !list.length;
    var host = $('mca-state');
    clear(host);
    if (list.length) {
      host.appendChild(certTable(list, function (c) {
        confirmThen('Take this certificate out', '<b>' + htmlText(c.subject || 'this certificate')
          + '</b> is no longer trusted for the mail server. The others stay.', 'Take it out', function () {
            api('mail', {action: 'ca', mode: 'drop', fingerprint: c.fingerprint}).then(function (r) {
              toast(r.message, 'good'); loadMail();
            }).catch(oops);
          });
      }));
    }
    $('mail-said').textContent = {off: 'switched off', smtp: 'through a mail server', direct: 'straight to the recipients'}[d.mode] || '';
    var nt = d.notices || {};
    $('mail-notices').textContent = nt.said ? 'The last notice: ' + ago(nt.at) + ' - ' + nt.said : '';
    return d;
  }).catch(oops);
}
$('mail-test').onclick = function () {
  var b = $('mail-test');
  if (Object.keys(DIRTY || {}).some(function (k) { return /^(mail_|smtp_)/.test(k); })) {
    toast('save the mail settings first', 'bad'); return;
  }
  busy(b, true);
  api('mail', {action: 'test', to: $('mail-to').value.trim(), lang: $('mail-test-lang').value}).then(function (d) {
    var host = $('mail-steps');
    clear(host);
    host.appendChild(el('p', 'note ' + (d.sent ? 'good' : 'bad'), (d.sent ? 'Sent: ' : 'Not sent: ') + d.said
      + (d.took_ms !== undefined ? ' · ' + num(d.took_ms) + ' ms' : '')));
    if ((d.steps || []).length) host.appendChild(stepsList(d.steps));
    host.appendChild(hideBar(function () { clear(host); }));
  }).catch(oops).then(function () { busy(b, false); });
};
$('mca-pem').addEventListener('input', function () {
  var pem = $('mca-pem').value.trim();
  if (!pem) { delete PENDING.mca; markDirtyCount(); return; }
  pendingSet('mca', {save: function () {
    return api('mail', {action: 'ca', mode: 'add', ca: $('mca-pem').value.trim()}).then(function (r) {
      toast(r.message, 'good'); $('mca-pem').value = ''; loadMail(); return true;
    });
  }, reset: function () { $('mca-pem').value = ''; }});
});
$('mca-file').onclick = function () { $('mca-input').click(); };
$('mca-input').onchange = function () {
  var file = this.files && this.files[0];
  if (file) readCertFile(file, $('mca-pem'));
  this.value = '';
};
$('mca-drop').onclick = function () {
  confirmThen('Take every certificate of the mail server away',
    'The mail server’s certificate will then have to be signed by an authority this machine already trusts, or the check has to be switched off.',
    'Take them all away', function () {
      api('mail', {action: 'ca', mode: 'clear'}).then(function (r) { toast(r.message, 'good'); loadMail(); }).catch(oops);
    });
};

/* ---- PHP and php2shell, said to an administrator (as otp's) ---------------------- */
function phpSafety() {
  var box = $('phpsafety'), s = typeof PHP_SAFETY !== 'undefined' ? PHP_SAFETY : null;
  if (!box || !s || s.patched) return;
  /* A distribution that backported the fix keeps the old number; the daemon
     reads the packages' changelog, and when it says the fix is in, so be it. */
  if (STATUS && STATUS.php && STATUS.php.fixed) return;
  box.hidden = false;
  box.classList.toggle('warnish', !!s.guarded);
  box.textContent = 'PHP ' + s.version + ' running this page may have php2shell '
    + '(CVE-2026-109618, CVE-2026-109619): remote code execution by anybody who can reach the '
    + 'web server. Update it - ' + (s.needs ? s.needs + ' or later, ' : '') + 'or the package '
    + 'your distribution fixed (dnf upgrade \'php*\') - and restart php-fpm; ./install.sh '
    + '--upgrade does it. A distribution that backported the fix keeps the old number: check '
    + 'rpm -q --changelog php-fpm | grep CVE-2026-109618.';
}

/* ---- the database: its copies (as otp's Database pane) ------------------------------ */
function bytesWords(n) {
  n = Number(n) || 0;
  if (n < 1024) return n + ' B';
  if (n < 1048576) return (n / 1024).toFixed(1) + ' kB';
  if (n < 1073741824) return (n / 1048576).toFixed(1) + ' MB';
  return (n / 1073741824).toFixed(2) + ' GB';
}
function loadDb() {
  api('db').then(function (d) {
    $('db-now').textContent = bytesWords(d.size) + ' · SQLite ' + d.sqlite;
    var says = $('db-says');
    clear(says);
    says.appendChild(kvTable([
      ['The file', noI18n(el('span', 'mono', d.file))],
      ['Its key', noI18n(el('span', 'mono', d.key))],
      ['The copies', noI18n(el('span', 'mono', d.folder))],
      ['The last copy', d.last && d.last.at ? ago(d.last.at) + ' (' + d.last.why + ')' : 'none yet'],
      ['In it', num(d.counts.users) + ' account(s), ' + num(d.counts.events) + ' event(s), ' + num(d.counts.terms) + ' terminal(s), ' + num(d.counts.settings) + ' setting(s) saved']
    ]));
    var host = $('db-copies');
    clear(host);
    if (!d.copies.length) { host.appendChild(el('p', 'note', 'No copy has been made yet.')); return; }
    host.appendChild(listTable(['The copy', 'Made', 'Size', ''], d.copies, function (c) {
      var tr = el('tr');
      tr.appendChild(noI18n(el('td', 'mono', c.name)));
      tr.appendChild(stampCell(c.at));
      tr.appendChild(el('td', 'num', bytesWords(c.size)));
      var t = el('td', 'rowtools');
      var dl = iconButton('download', 'Download it');
      dl.onclick = function () { download(c.path); };
      var back = iconButton('undo', 'Put it back');
      back.onclick = function () { dbRestoreAsk(c.name); };
      var x = iconButton('trash', 'Take it away');
      x.onclick = function () {
        confirmThen('Take the copy away?', '<b>' + htmlText(c.name) + '</b> is deleted from the server.', 'Take it away', function () {
          api('db', {action: 'drop', name: c.name}).then(function (r) { toast(r.message, 'good'); loadDb(); }).catch(oops);
        }, true);
      };
      [dl, back, x].forEach(function (b) { t.appendChild(b); });
      tr.appendChild(t);
      return tr;
    }));
  }).catch(oops);
}
function dbRestoreAsk(name) {
  api('db', {action: 'inspect', name: name}).then(function (r) {
    var w = r.what;
    modal('Put ' + name + ' back', function (body) {
      body.appendChild(el('p', 'note warn', 'Everything is replaced by what is in it: every account, every setting, every event. Whoever is signed in may have to sign in again. A copy of what is here now is made first.'));
      body.appendChild(kvTable([
        ['Made by', w.about && w.about.version ? 'ai ' + w.about.version + ' on ' + w.about.host : '–'],
        ['Made', w.about && w.about.at ? stamp(w.about.at) : '–'],
        ['Accounts', noI18n(el('span', 'mono', (w.users || []).join(', ')))],
        ['Events', num(w.events)],
        ['The key of its secrets', w.has_key ? (w.same_key ? 'in it - the same as here' : 'in it - it replaces the one here') : 'not in it: secrets sealed elsewhere cannot be opened']
      ]));
    }, [{words: 'Close', close: true},
        {words: 'Put it back', cls: 'danger', icon: 'undo', go: function (b) {
          busy(b, true);
          api('db', {action: 'restore', name: name}).then(function (x) {
            closeModal(); toast(x.message, 'good'); setTimeout(function () { location.reload(); }, 1500);
          }).catch(oops).then(function () { busy(b, false); });
        }}], 'medium');
  }).catch(oops);
}
$('db-make').onclick = function () {
  busy($('db-make'), true);
  api('db', {action: 'copy'}).then(function (r) { toast(r.message, 'good'); loadDb(); }).catch(oops).then(function () { busy($('db-make'), false); });
};
(function () {
  var box = $('dbu-drop');
  function send(f) {
    if (!f) return;
    var name = 'upload-' + Date.now() + '.tar.gz';
    $('dbu-says').textContent = 'Sending ' + f.name + '…';
    sendFile('/files/put?dir=' + encodeURIComponent('/var/lib/ai/copies') + '&name=' + encodeURIComponent(name), f, function () {}).then(function () {
      $('dbu-says').textContent = 'Drop a copy here, or press to choose one';
      dbRestoreAsk(name);
    }).catch(function (e) { $('dbu-says').textContent = 'Drop a copy here, or press to choose one'; oops(e); });
  }
  box.onclick = function () { $('dbu-file').click(); };
  $('dbu-file').onchange = function () { send(this.files && this.files[0]); this.value = ''; };
  ['dragenter', 'dragover'].forEach(function (n) { box.addEventListener(n, function (e) { e.preventDefault(); box.classList.add('over'); }); });
  ['dragleave', 'drop'].forEach(function (n) {
    box.addEventListener(n, function (e) {
      e.preventDefault(); box.classList.remove('over');
      if (n === 'drop' && e.dataTransfer && e.dataTransfer.files) send(e.dataTransfer.files[0]);
    });
  });
}());

/* ---- export and import (as otp's) -------------------------------------------------------- */
$('ex-plain').onclick = function () {
  api('export').then(function (d) { saveFile('ai-config-' + Date.now() + '.json', JSON.stringify(d.config, null, 2)); }).catch(oops);
};
$('ex-whole').onclick = function () {
  confirmThen('Export with the secrets', 'The password hashes of the accounts, their authenticator keys, the mail server\'s password and the private key of the certificate go into the file - locked with a passphrase made now and shown once. The file opens only with it.',
    'Export them', function () {
      api('export&secrets=1').then(function (d) {
        saveFile('ai-config-complete-locked-' + Date.now() + '.json', JSON.stringify(d.bundle, null, 2));
        modal('The passphrase of the file', function (body) {
          body.appendChild(el('p', 'note', 'The file opens only with this passphrase - it is not shown again and not kept here. Write it down apart from the file.'));
          body.appendChild(el('p', '', '')).appendChild(copyOnClick(noI18n(el('span', 'keytext', d.passphrase)), d.passphrase, 'the passphrase was copied'));
        }, [{words: 'Close', close: true}], 'small');
      }).catch(oops);
    });
};
$('ex-load').onclick = function () { $('ex-file').click(); };
$('ex-file').onchange = function () {
  var f = this.files && this.files[0];
  this.value = '';
  if (!f) return;
  f.text().then(function (t) {
    var conf;
    try { conf = JSON.parse(t); } catch (e) { toast('the file is not JSON - is it the right file?', 'bad'); return; }
    if (!conf || typeof conf !== 'object' || Array.isArray(conf)) { toast('the file is not JSON - is it the right file?', 'bad'); return; }
    if (conf && conf.config && typeof conf.config === 'object') conf = conf.config;
    var locked = conf && conf.kind === 'ai-config-locked';
    var phrase = null;
    modal('Import ' + f.name, function (body) {
      if (locked) {
        body.appendChild(el('p', 'note', 'Exported with the secrets, it is locked: the passphrase shown when it was exported opens it.'));
        phrase = textBox('', 'the passphrase', 'mono');
        phrase.type = 'password';
        noI18n(phrase);
        body.appendChild(formField('Passphrase', phrase));
      }
      body.appendChild(el('p', 'note', 'Accounts of the same name are replaced; the settings, the certificate, who may reach the pages, the firewall and the mail server\'s authorities in it are saved - the firewall as a change on trial, to be kept. Your own account is left as it is.'));
      body.appendChild(el('p', 'note', 'Add to what is here: anything not in the file stays. Exactly the file: accounts not in it are taken away, and settings not in it go back to their defaults.'));
    }, [{words: 'Close', close: true},
        {words: 'Exactly the file', cls: 'danger', icon: 'upload', close: true, go: function () {
          api('import', {config: conf, replace: true, passphrase: phrase ? phrase.value : ''}).then(function (d) { toast(d.message, 'good'); loadSettings(); }).catch(oops);
        }},
        {words: 'Add to what is here', cls: 'primary', icon: 'upload', close: true, go: function () {
          api('import', {config: conf, passphrase: phrase ? phrase.value : ''}).then(function (d) { toast(d.message, 'good'); loadSettings(); }).catch(oops);
        }}], 'medium');
  }).catch(oops);
};


/* ==== Backups to another machine (1.0.109) ===================================
   Destinations (a folder, FTP, FTPS, SFTP, SCP, SMB) with their sign-in -
   passwords, ssh keys made here or brought, the server's host key or its
   certificate checked, a client certificate for FTPS - a backup sent now or on
   a schedule, the history, the backups at each destination, and putting one
   back. Only a full administrator sees any of it. */
var RB = null;
var RB_POLL = null;
var RB_KIND_ICON = {folder: 'db', ftp: 'upload', ftps: 'lock', sftp: 'terminal', scp: 'terminal', smb: 'net'};
var RB_KIND_SAYS = {
  folder: 'A folder on this machine - an NFS or other share mounted here.',
  ftp: 'Plain FTP: the password and the file go over unencrypted - only inside a network you trust (the file itself is locked).',
  ftps: 'FTP over TLS - explicit (port 21) or implicit (990); the server’s certificate checked, a client certificate if it wants one.',
  sftp: 'SSH file transfer: a key made here or your own, or a password; the server’s host key checked.',
  scp: 'scp over SSH, and ssh to list and take away old ones - needs a shell on the server.',
  smb: 'A Windows or Samba share: the account, its domain, SMB3 encryption.'
};
function rbWhen(ts) {
  if (!ts) return '';
  var n = Number(ts);
  return isNaN(n) ? String(ts) : 'until ' + new Date(n * 1000).toLocaleDateString(numLang());
}
function rbBytes(n) {
  n = Number(n || 0);
  if (n < 1024) return num(n) + ' B';
  var u = ['kB', 'MB', 'GB', 'TB'], i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < u.length - 1);
  return n.toFixed(n < 10 ? 1 : 0) + ' ' + u[i];
}
function rbWhere(t) {
  if (t.kind === 'folder') return t.path || '';
  if (t.kind === 'smb') return '\\\\' + t.host + (t.port && t.port !== 445 ? ':' + t.port : '') + '\\' + (t.share || '') + (t.path ? '\\' + String(t.path).replace(/\//g, '\\') : '');
  return (t.user ? t.user + '@' : '') + t.host + (t.port ? ':' + t.port : '') + '/' + String(t.path || '').replace(/^\//, '');
}
function loadRbackup() {
  var top = $('rb-top');
  if (!top) return;
  if (!ME || ME.role !== 'admin') {
    clear(top);
    top.appendChild(el('p', 'note', 'Only an administrator sees and changes the backups: they hold every secret.'));
    return;
  }
  api('rbackup').then(function (d) {
    RB = d;
    drawRbTop();
    drawRbTargets();
    drawRbRuns();
    rbPassTools();
    if (d.job && d.job.running) rbWatch();
  }).catch(oops);
}
function rbPassTools() {
  /* "Make one" beside the password of the backups: a long random one, shown
     once to be put into the password vault. */
  var item = document.querySelector('.set-item[data-key="rbackup_password"]');
  if (!item || item.querySelector('.rb-gen')) return;
  var b = cmdButton('Make a strong one', 'key', 'small rb-gen');
  b.style.alignSelf = 'flex-start';
  b.onclick = function () {
    var a = new Uint8Array(24);
    crypto.getRandomValues(a);
    var abc = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789';
    var pw = '';
    for (var i = 0; i < a.length; i++) { pw += abc.charAt(a[i] % abc.length); if (i % 6 === 5 && i < a.length - 1) pw += '-'; }
    var box = item.querySelector('input');
    if (box) {
      if (box._set) box._set(pw); else box.value = pw;
      box.dispatchEvent(new Event('input', {bubbles: true}));
      box.dispatchEvent(new Event('change', {bubbles: true}));
    }
    modal('The password of the backups', function (body) {
      body.appendChild(el('p', 'note', 'Put it into your password vault now - this is the only time it is shown whole. Without it no backup can be opened, by anybody. Then press Save the changes.'));
      var p = noI18n(el('div', 'rb-pass mono', pw));
      body.appendChild(p);
      var c = cmdButton('Copy', 'copy', 'small');
      c.onclick = function () { copyText(pw, c, 'Copied'); };
      body.appendChild(c);
    }, [{words: 'Close', close: true}], true);
  };
  var says = item.querySelector('.says');
  if (says) says.parentNode.insertBefore(b, says); else item.appendChild(b);
}
function drawRbTop() {
  var host = $('rb-top');
  clear(host);
  var d = RB;
  var card = el('div', 'card full rb-hero');
  var last = (d.runs || [])[0];
  var mine = (d.runs || []).filter(function (r) { return r.node === d.node; })[0];
  var on = (d.targets || []).filter(function (t) { return t.enabled; });
  var state = !on.length ? 'warn' : (!mine ? 'warn' : (mine.ok ? 'good' : 'bad'));
  card.classList.add(state);
  var head = el('div', 'rb-hero-head');
  var ic = el('span', 'rb-hero-ic');
  ic.innerHTML = iconMarkup(state === 'good' ? 'check' : (state === 'bad' ? 'flag' : 'info'), 22);
  head.appendChild(ic);
  var words = el('div', 'rb-hero-words');
  var title = !on.length ? 'No destination yet - backups go nowhere'
    : (!mine ? 'No backup of this node has been sent yet'
      : (mine.ok ? 'The last backup of ' + d.node + ' went to every destination'
        : 'The last backup of ' + d.node + ' did not reach every destination'));
  words.appendChild(el('b', '', title));
  var facts = el('div', 'rb-hero-facts');
  var fact = function (k, v, cls) {
    var f = el('span', 'rb-fact ' + (cls || ''));
    f.appendChild(el('span', 'k', k));
    f.appendChild(el('span', 'v', v));
    facts.appendChild(f);
  };
  if (mine) fact('Last', ago(mine.at) + ' · ' + rbBytes(mine.bytes));
  fact('Next', d.next ? new Date(d.next).toLocaleString(numLang(), {weekday: 'short', day: 'numeric', month: 'numeric', hour: '2-digit', minute: '2-digit'}) : 'by hand only', d.next ? '' : 'warn');
  fact('Locked', d.locked ? 'with the password (AES-256)' : 'NOT locked - set the password', d.locked ? 'good' : 'bad');
  fact('Destinations', num(on.length) + ' of ' + num((d.targets || []).length) + ' switched on');
  words.appendChild(facts);
  if (mine && !mine.ok) {
    var bad = (mine.targets || []).filter(function (x) { return !x.ok; });
    var why = el('div', 'rb-hero-why small bad');
    why.textContent = mine.error || bad.map(function (x) { return x.name + ': ' + (x.error || 'failed'); }).join(' · ');
    words.appendChild(why);
  }
  head.appendChild(words);
  var acts = el('div', 'rb-hero-acts');
  var now = cmdButton('Back up now', 'upload', 'primary');
  now.id = 'rb-now';
  now.disabled = !on.length || (d.job && d.job.running);
  explain(now, 'A backup made now and sent to every destination switched on - the same as the scheduled one.');
  now.onclick = function () {
    busy(now, true);
    api('rbackup', {action: 'run'}).then(function (x) { toast(x.message, 'good'); RB.job = x.job; rbWatch(); })
      .catch(function (e) { busy(now, false); oops(e); });
  };
  acts.appendChild(now);
  var dl = cmdButton('Download one here', 'download', '');
  explain(dl, 'A backup made now, saved on the computer you are sitting at - locked with the password as the others.');
  dl.onclick = function () {
    if (!d.locked) {
      confirmThen('Download a backup that is not locked?', 'No password of the backups is set: the file will hold <b>every secret of this server</b> readable. Set the password first unless you know where the file goes.', 'Download it', function () { rbDownload({}); }, false);
      return;
    }
    toast('the backup is being made - the download starts when it is ready', 'good');
    rbDownload({});
  };
  acts.appendChild(dl);
  var back = cmdButton('Put one back…', 'undo', '');
  back.onclick = rbPutBackFile;
  acts.appendChild(back);
  var guide = cmdButton('How to put it back', 'book', '');
  explain(guide, 'RESTORE.md - the exact steps to bring everything back from a backup, filled in with this installation, as every backup carries it. To read now, and to keep apart from the backups.');
  guide.onclick = rbGuide;
  acts.appendChild(guide);
  head.appendChild(acts);
  card.appendChild(head);
  var going = el('div', 'going wide');
  going.id = 'rb-going';
  going.hidden = !(d.job && d.job.running);
  going.innerHTML = '<div class="bar"><span id="rb-going-fill"></span></div><div class="says" id="rb-going-says"></div>';
  card.appendChild(going);
  if (!d.tools.openssl) card.appendChild(el('p', 'note bad', 'openssl is not on this machine: backups cannot be locked (dnf install openssl).'));
  host.appendChild(card);
}
/* RESTORE.md on the pages (1.0.110): read here, downloaded as the file. */
function rbGuide() {
  api('rbackup', {action: 'restore_md'}).then(function (d) {
    modal('How to put a backup back', function (body) {
      var lede = el('p', 'note');
      lede.innerHTML = 'The <code>RESTORE.md</code> every backup carries, as one made now would have it. Keep a copy apart from the backups - with the password of the backups in a vault.';
      body.appendChild(lede);
      var doc = noI18n(el('div', 'md-doc'));
      doc.appendChild(mdRender(d.md));
      body.appendChild(doc);
    }, [{words: 'Close', close: true},
        {words: 'Download RESTORE.md', cls: 'primary', icon: 'download', go: function () {
          var a = el('a');
          a.href = URL.createObjectURL(new Blob([d.md], {type: 'text/markdown;charset=utf-8'}));
          a.download = d.name || 'RESTORE.md';
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
        }}], 'large');
  }).catch(oops);
}
/* Markdown as the guides are written: headings, paragraphs, lists, tables,
   fenced code (with a copy button), `code`, **bold**, *italic*. Built from
   elements - nothing in the text becomes HTML. */
function mdInline(text) {
  var frag = document.createDocumentFragment();
  var re = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*\s][^*]*\*)/g, last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
    var t = m[0];
    if (t.charAt(0) === '`') frag.appendChild(el('code', '', t.slice(1, -1)));
    else if (t.slice(0, 2) === '**') frag.appendChild(el('b', '', t.slice(2, -2)));
    else frag.appendChild(el('i', '', t.slice(1, -1)));
    last = re.lastIndex;
  }
  if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
  return frag;
}
function mdRender(md) {
  var out = document.createDocumentFragment();
  var lines = String(md || '').split('\n'), i = 0;
  var para = [];
  var flush = function () {
    if (!para.length) return;
    var p = el('p');
    p.appendChild(mdInline(para.join(' ')));
    out.appendChild(p);
    para = [];
  };
  while (i < lines.length) {
    var ln = lines[i];
    if (/^```/.test(ln)) {
      flush();
      var code = [];
      i += 1;
      while (i < lines.length && !/^```/.test(lines[i])) { code.push(lines[i]); i += 1; }
      i += 1;
      var wrap = el('div', 'md-code');
      var pre = el('pre', '', code.join('\n'));
      wrap.appendChild(pre);
      var cp = iconButton('copy', 'Copy');
      (function (txt, b) {
        b.onclick = function () {
          (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(function () { toast('copied', 'good'); }).catch(function () { toast('select it and copy it by hand'); });
        };
      })(code.join('\n'), cp);
      wrap.appendChild(cp);
      out.appendChild(wrap);
      continue;
    }
    var h = /^(#{1,4})\s+(.*)$/.exec(ln);
    if (h) { flush(); var hn = el('h' + Math.min(6, h[1].length + 2)); hn.appendChild(mdInline(h[2])); out.appendChild(hn); i += 1; continue; }
    if (/^\|/.test(ln)) {
      flush();
      var rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) { rows.push(lines[i]); i += 1; }
      var tbl = el('table', 'md-table');
      var tb = el('tbody');
      rows.forEach(function (r, n) {
        if (/^\|[\s|:-]+\|$/.test(r)) return;
        var cells = r.replace(/^\|/, '').replace(/\|$/, '').split('|');
        if (n === 0 && cells.every(function (c) { return !c.trim(); })) return;
        var tr = el('tr');
        cells.forEach(function (c) { var td = el(n === 0 && rows.length > 1 && /^\|[\s|:-]+\|$/.test(rows[1]) ? 'th' : 'td'); td.appendChild(mdInline(c.trim())); tr.appendChild(td); });
        tb.appendChild(tr);
      });
      tbl.appendChild(tb);
      out.appendChild(tbl);
      continue;
    }
    if (/^\s*[-*] /.test(ln)) {
      flush();
      var ul = el('ul');
      var li = null;
      while (i < lines.length && (/^\s*[-*] /.test(lines[i]) || (li && /^\s{2,}\S/.test(lines[i])))) {
        if (/^\s*[-*] /.test(lines[i])) { li = el('li'); li._t = lines[i].replace(/^\s*[-*] /, ''); ul.appendChild(li); }
        else li._t += ' ' + lines[i].trim();
        i += 1;
      }
      Array.prototype.forEach.call(ul.children, function (x) { x.appendChild(mdInline(x._t)); });
      out.appendChild(ul);
      continue;
    }
    if (/^---+\s*$/.test(ln)) { flush(); out.appendChild(el('hr')); i += 1; continue; }
    if (!ln.trim()) { flush(); i += 1; continue; }
    para.push(ln.trim());
    i += 1;
  }
  flush();
  return out;
}
function rbWatch() {
  if (RB_POLL) return;
  var step = function () {
    api('rbackup', {action: 'job'}).then(function (x) {
      var j = x.job || {};
      var g = $('rb-going');
      if (g) {
        g.hidden = !j.running;
        var f = $('rb-going-fill');
        if (f) f.style.width = (j.whole ? Math.round(100 * j.done / j.whole) : 5) + '%';
        var sy = $('rb-going-says');
        if (sy) sy.textContent = j.says || '';
      }
      if (j.running) { RB_POLL = setTimeout(step, TAB === 'settings' && PANE === 'backup' ? 1000 : 5000); return; }
      RB_POLL = null;
      if (j.error) toast('the backup: ' + j.error, 'bad');
      else if (j.result) toast(j.result.ok ? 'the backup went to every destination' : 'the backup did not reach every destination', j.result.ok ? 'good' : 'bad');
      if (TAB === 'settings' && PANE === 'backup') loadRbackup();
    }).catch(function () { RB_POLL = null; });
  };
  step();
}
function drawRbTargets() {
  var host = $('rb-targets');
  clear(host);
  var add = cmdButton('Add a destination', 'add', 'primary small');
  add.onclick = rbPickKind;
  var ah = $('rb-add-host');
  clear(ah);
  ah.appendChild(add);
  var ts = RB.targets || [];
  if (!ts.length) {
    var empty = el('div', 'rb-empty');
    empty.appendChild(el('p', '', 'No destination yet. A backup kept only on this machine is lost with it: add a place on another machine.'));
    host.appendChild(empty);
    return;
  }
  var grid = el('div', 'rb-grid');
  ts.forEach(function (t) {
    var c = el('div', 'rb-card' + (t.enabled ? '' : ' off'));
    var top = el('div', 'rb-card-top');
    var ic = el('span', 'rb-kind k-' + t.kind);
    ic.innerHTML = iconMarkup(RB_KIND_ICON[t.kind] || 'db', 18);
    top.appendChild(ic);
    var nm = el('div', 'rb-card-name');
    nm.appendChild(noI18n(el('b', '', t.name)));
    nm.appendChild(el('span', 'rb-kind-words', t.kind_words));
    top.appendChild(nm);
    var sw = switchBox(t.enabled);
    explain(sw, t.enabled ? 'Backups go here. Switch off to stop sending, keeping everything set.' : 'Switched off: nothing is sent here.');
    sw._input.onchange = function () {
      api('rbackup', {action: 'save', id: t.id, target: {kind: t.kind, enabled: sw._get(), name: t.name, host: t.host, port: t.port, path: t.path, user: t.user, share: t.share, domain: t.domain, smb_encrypt: t.smb_encrypt, implicit: t.implicit, tls_check: t.tls_check, passive: t.passive}})
        .then(function () { loadRbackup(); }).catch(function (e) { oops(e); loadRbackup(); });
    };
    top.appendChild(sw);
    c.appendChild(top);
    c.appendChild(noI18n(el('div', 'rb-where mono', rbWhere(t))));
    var chips = el('div', 'rb-chips');
    var chip = function (w, cls, tip) { var x = el('span', 'tag ' + (cls || 'dim'), w); if (tip) x.title = tip; chips.appendChild(x); };
    if (t.has_password) chip('password', 'dim');
    if (t.has_key) chip('ssh key', 'violet');
    if (t.ssh_cert) chip('ssh certificate', 'violet');
    if (t.kind === 'sftp' || t.kind === 'scp') chip(t.hostkey ? 'host key trusted' : 'host key not trusted yet', t.hostkey ? 'ok' : 'warn', (t.hostkey_fp || []).join('\n'));
    if (t.kind === 'ftps') chip({system: 'certificate: system authorities', ca: 'certificate: own authority', pin: 'certificate pinned', none: 'certificate NOT checked'}[t.tls_check] || '', t.tls_check === 'none' ? 'warn' : 'ok');
    if (t.has_client_key) chip('client certificate', 'violet');
    if (t.kind === 'smb' && t.smb_encrypt) chip('SMB3 encrypted', 'ok');
    if (t.kind === 'ftp') chip('not encrypted on the way', 'warn');
    c.appendChild(chips);
    var last = t.last;
    var ls = el('div', 'rb-last ' + (last ? (last.ok ? 'good' : 'bad') : 'muted'));
    ls.textContent = last ? (last.ok ? '✓ last sent ' + ago(last.at) + ' · ' + rbBytes(last.bytes) : '✗ ' + ago(last.at) + ': ' + (last.error || 'failed')) : 'nothing sent here yet';
    c.appendChild(ls);
    var acts = el('div', 'rb-acts');
    var tr = cmdButton('Try it', 'play', 'small');
    tr.onclick = function () { rbTry(t, null, tr); };
    acts.appendChild(tr);
    var ed = cmdButton('Edit', 'edit', 'small');
    ed.onclick = function () { rbEdit(t); };
    acts.appendChild(ed);
    var ls2 = cmdButton('Backups there', 'list', 'small');
    ls2.onclick = function () { rbListThere(t); };
    acts.appendChild(ls2);
    var del = iconButton('trash', 'Take this destination away');
    del.onclick = function () {
      confirmThen('Take the destination ' + htmlText(t.name) + ' away?', 'Nothing is deleted on the server; backups simply stop going there, and its keys and certificates set here are forgotten.', 'Take it away', function () {
        api('rbackup', {action: 'delete', id: t.id}).then(function (x) { toast(x.message, 'good'); loadRbackup(); }).catch(oops);
      });
    };
    acts.appendChild(del);
    c.appendChild(acts);
    grid.appendChild(c);
  });
  host.appendChild(grid);
}
function drawRbRuns() {
  var host = $('rb-runs');
  clear(host);
  var runs = RB.runs || [];
  /* The list can be emptied, or a line taken off (1.0.110) - the backups
     themselves stay where they went. */
  var tools = $('rb-runs-tools');
  if (tools) {
    clear(tools);
    if (runs.length) {
      var wipe = cmdButton('Clear the list', 'trash', 'small');
      wipe.onclick = function () {
        confirmThen('Clear the list of backups sent?', 'Every line goes from this list (for both nodes). <b>The backups themselves stay where they went</b> - delete them under <i>Backups there</i> on a destination. Events keeps a line saying who cleared it.', 'Clear the list', function () {
          api('rbackup', {action: 'runs_forget', all: 1}).then(function (d) { toast(d.message, 'good'); RB.runs = d.runs || []; drawRbRuns(); }).catch(oops);
        }, true);
      };
      tools.appendChild(wipe);
    }
  }
  if (!runs.length) { host.appendChild(el('p', 'note', 'No backup sent yet.')); return; }
  host.appendChild(listTable(['When', 'Node', 'File', 'Size', 'Where it went', 'Who', ''], runs, function (r) {
    var tr = el('tr');
    tr.appendChild(el('td', 'muted', new Date(r.at * 1000).toLocaleString(numLang())));
    tr.appendChild(noI18n(el('td', '', r.node || '')));
    var f = el('td', 'mono small');
    f.appendChild(noI18n(el('span', '', r.file || '–')));
    if (r.file && !r.encrypted) { f.appendChild(document.createTextNode(' ')); f.appendChild(el('span', 'tag bad', 'not locked')); }
    tr.appendChild(f);
    tr.appendChild(el('td', 'num', r.bytes ? rbBytes(r.bytes) : '–'));
    var w = el('td');
    if (r.error) w.appendChild(el('span', 'small bad', r.error));
    (r.targets || []).forEach(function (x) {
      var s = el('span', 'tag namepill ' + (x.ok ? 'ok' : 'crit'), (x.ok ? '✓ ' : '✗ ') + x.name);
      s.title = x.ok ? (x.secs + ' s' + ((x.taken_away || []).length ? ' · taken away: ' + x.taken_away.join(', ') : '')) : (x.error || '');
      noI18n(s);
      w.appendChild(s);
      w.appendChild(document.createTextNode(' '));
    });
    tr.appendChild(w);
    tr.appendChild(noI18n(el('td', 'muted small', r.by || '')));
    var a = el('td', 'rowtools');
    var del = iconButton('trash', 'Take it off the list');
    del.onclick = function () {
      api('rbackup', {action: 'runs_forget', at: r.at, file: r.file || ''}).then(function (d) { toast(d.message, 'good'); RB.runs = d.runs || []; drawRbRuns(); }).catch(oops);
    };
    a.appendChild(del);
    tr.appendChild(a);
    return tr;
  }, 'plain'));
}
function rbPickKind() {
  modal('Where should the backups go?', function (body) {
    var g = el('div', 'rb-kinds');
    (RB.kinds || []).forEach(function (k) {
      var b = el('button', 'rb-kind-tile');
      b.type = 'button';
      var ic = el('span', 'rb-kind k-' + k.kind);
      ic.innerHTML = iconMarkup(RB_KIND_ICON[k.kind] || 'db', 20);
      b.appendChild(ic);
      b.appendChild(el('b', '', k.words));
      b.appendChild(el('span', 'small muted', RB_KIND_SAYS[k.kind] || ''));
      var need = {sftp: ['ssh', 'sftp'], scp: ['ssh', 'scp'], smb: ['smbclient']}[k.kind] || [];
      var missing = need.filter(function (x) { return !RB.tools[x]; });
      if (missing.length) {
        b.appendChild(el('span', 'small bad', 'missing here: ' + missing.join(', ') + (k.kind === 'smb' ? ' (dnf install samba-client)' : ' (dnf install openssh-clients)')));
      }
      b.onclick = function () { closeModal(); setTimeout(function () { rbEdit({kind: k.kind, enabled: 1, port: k.port}); }, 30); };
      g.appendChild(b);
    });
    body.appendChild(g);
  }, [{words: 'Close', close: true}], 'medium');
}
/* The editor of one destination. A new one is saved before a key or a
   certificate is made for it - they are kept with it. */
function rbEdit(t) {
  t = t || {};
  var isNew = !t.id;
  var cur = {id: t.id};
  modal(isNew ? 'A new destination: ' + (t.kind_words || (RB.kinds.filter(function (k) { return k.kind === t.kind; })[0] || {}).words || t.kind) : t.name, function (body) {
    body.classList.add('rb-ed');
    var f = {};
    var sec = function (title, says) {
      var s = el('div', 'rb-sec');
      s.appendChild(el('h4', '', title));
      if (says) s.appendChild(el('p', 'small muted', says));
      var g = el('div', 'formgrid');
      s.appendChild(g);
      body.appendChild(s);
      return g;
    };
    var g0 = sec('What it is called', '');
    f.name = textBox(t.name || '', 'NAS in the server room');
    g0.appendChild(formField('Name', f.name));
    f.enabled = switchBox(t.enabled === undefined ? 1 : t.enabled);
    g0.appendChild(formField('Backups go here', f.enabled));
    var g1 = sec('Where', t.kind === 'folder' ? 'A whole path on this machine.' : '');
    if (t.kind === 'folder') {
      f.path = textBox(t.path || '', '/mnt/backup/ai', 'mono');
      var fp = formField('The folder', f.path);
      fp.classList.add('wide');
      g1.appendChild(fp);
    } else {
      f.host = textBox(t.host || '', 'backup.example.cz', 'mono');
      g1.appendChild(formField('The server', f.host));
      f.port = textBox(t.port || '', String({ftp: 21, ftps: t.implicit ? 990 : 21, sftp: 22, scp: 22, smb: 445}[t.kind] || ''), 'mono');
      g1.appendChild(formField('Port', f.port));
      if (t.kind === 'smb') {
        f.share = textBox(t.share || '', 'backup', 'mono');
        g1.appendChild(formField('The share', f.share));
        f.path = textBox(t.path || '', 'ai\\nightly', 'mono');
        g1.appendChild(formField('The folder in it', f.path, 'Made if it is not there.'));
      } else {
        f.path = textBox(t.path || '', t.kind === 'ftp' || t.kind === 'ftps' ? 'ai/backups' : '/home/backup/ai', 'mono');
        g1.appendChild(formField('The folder there', f.path, 'Made if it is not there. Without / at the start: under the account’s home.'));
      }
    }
    if (t.kind !== 'folder') {
      var g2 = sec('Signing in', t.kind === 'sftp' || t.kind === 'scp' ? 'A key (below) or a password - or both.' : '');
      f.user = textBox(t.user || '', t.kind === 'smb' ? 'backup' : 'ai-backup', 'mono');
      g2.appendChild(formField('Account', f.user));
      f.password = maskBox(t.password || '', t.has_password ? '' : '(none)', 'mono');
      g2.appendChild(formField('Password', f.password, t.has_password ? 'Kept, sealed. Type a new one to change it.' : ''));
      if (t.kind === 'smb') {
        f.domain = textBox(t.domain || '', 'CORP', 'mono');
        g2.appendChild(formField('Domain (workgroup)', f.domain));
        f.smb_encrypt = switchBox(t.smb_encrypt === undefined ? 1 : t.smb_encrypt);
        g2.appendChild(formField('SMB3 encryption required', f.smb_encrypt, 'Everything on the wire encrypted; a server that cannot is refused.'));
      }
      if (t.kind === 'ftp' || t.kind === 'ftps') {
        f.passive = switchBox(t.passive === undefined ? 1 : t.passive);
        g2.appendChild(formField('Passive mode', f.passive, 'The usual one, through firewalls and NAT.'));
      }
    }
    if (t.kind === 'ftps') rbFtpsBlock(body, t, f, cur);
    if (t.kind === 'sftp' || t.kind === 'scp') rbSshBlock(body, t, f, cur);
    var out = el('div', 'rb-try-out');
    out.id = 'rb-try-out';
    body.appendChild(out);
    rbEdit.form = f;
  }, [
    {words: 'Close', close: true},
    {words: 'Try it', icon: 'play', go: function (b) { rbTry(cur.id ? rbTarget(cur.id) || t : t, rbFormData(t.kind), b, true); }},
    {words: 'Save', cls: 'primary', icon: 'save', go: function (b) {
      busy(b, true);
      rbSaveForm(t.kind, cur).then(function () { busy(b, false); toast('saved', 'good'); closeModal(); loadRbackup(); })
        .catch(function (e) { busy(b, false); oops(e); });
    }}], 'large');
}
function rbTarget(id) { return (RB.targets || []).filter(function (x) { return x.id === id; })[0]; }
function rbFormData(kind) {
  var f = rbEdit.form || {};
  var v = function (k) { return f[k] ? (f[k]._get ? f[k]._get() : f[k].value) : undefined; };
  var d = {kind: kind};
  ['name', 'enabled', 'host', 'port', 'path', 'user', 'password', 'share', 'domain', 'smb_encrypt', 'passive', 'implicit', 'tls_check', 'ca', 'pin', 'ssh_cert'].forEach(function (k) {
    var x = v(k);
    if (x !== undefined) d[k] = typeof x === 'string' ? x.trim() : x;
  });
  if (f.password) d.password = f.password.value;
  return d;
}
function rbSaveForm(kind, cur) {
  return api('rbackup', {action: 'save', id: cur.id || '', target: rbFormData(kind)}).then(function (x) {
    cur.id = x.target.id;
    var i = (RB.targets || []).map(function (t) { return t.id; }).indexOf(x.target.id);
    if (i >= 0) RB.targets[i] = x.target; else RB.targets.push(x.target);
    return x.target;
  });
}
function rbNeedSaved(kind, cur) {
  return cur.id ? Promise.resolve(rbTarget(cur.id)) : rbSaveForm(kind, cur);
}
function rbKeyBox(text) {
  var w = el('div', 'rb-keybox');
  var pre = noI18n(el('pre', 'mono', text));
  w.appendChild(pre);
  var c = cmdButton('Copy', 'copy', 'small');
  c.onclick = function () { copyText(text, c, 'Copied'); };
  w.appendChild(c);
  return w;
}
/* The key and the certificates, as isemon has them (1.0.109): one box each,
   a line saying what it is, the same row of buttons always there (Make,
   Use my own, Download, Forget - the last two greyed until there is one),
   Try it at the end of the row, and below it the half to copy - a click on
   it copies it. */
function rbConfirm(title, words, yes, go, danger) {
  /* Over the editor, which stays as it is underneath. */
  modalOver(function () { confirmThen(title, words, yes, go, danger); });
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
function rbTryButton(t, cur) {
  var b = cmdButton('Try reaching it', 'pulse', 'primary');
  explain(b, 'Sign in, write a small file, find it in the list and take it away again - with what is typed above, saved or not.');
  b.onclick = function () { rbTry(cur.id ? (rbTarget(cur.id) || t) : t, rbFormData(t.kind), b, true); };
  return b;
}
function rbSshBlock(body, t, f, cur) {
  var s = el('div', 'rb-sec');
  s.appendChild(el('h4', '', 'The SSH key'));
  var P = rbPanel('A key is better than a password: made here, it never leaves this machine except when you download it, and the server holds only its <b>public</b> half - in <code>~/.ssh/authorized_keys</code> of the account.');
  if (!RB.tools['ssh-keygen']) {
    var miss = el('p', 'note');
    miss.style.color = 'var(--warn)';
    miss.textContent = 'ssh-keygen is not on this machine, so a key cannot be made or read here: dnf install openssh-clients. A password still works.';
    P.box.insertBefore(miss, P.row);
  }
  var mk = cmdButton('Make a key', 'key', '');
  explain(mk, 'Make a fresh ed25519 pair here. The private half stays on this machine, sealed; the public half is shown below for you to put on the server. Any key already kept is replaced.');
  var own = cmdButton('Use my own', 'upload', '');
  explain(own, 'Use a private key you already have. Paste it whole, with its BEGIN and END lines; its public half is worked out here.');
  var dl = cmdButton('Download it', 'download', '');
  explain(dl, 'The private half as a file, for keeping somewhere safe. That it was downloaded, and by whom, is written into Events.');
  var fg = cmdButton('Forget it', 'forget', 'danger');
  explain(fg, 'Delete the private key from this machine. Unless the server takes a password instead, nothing here reaches it until a new key is made and put on it.');
  [mk, own, dl, fg].forEach(function (b) { P.row.appendChild(b); });
  P.row.appendChild(el('span', 'spacer'));
  P.row.appendChild(rbTryButton(t, cur));
  var state = {pub: t.pub, has: !!t.has_key};
  var paint = function () {
    clear(P.below);
    dl.disabled = !state.has;
    fg.disabled = !state.has;
    mk.disabled = own.disabled = !RB.tools['ssh-keygen'];
    if (!state.has || !state.pub) {
      P.below.appendChild(el('p', 'btnhelp', 'No key yet — make one, or let it sign in with a password.'));
      return;
    }
    P.below.appendChild(el('p', 'btnhelp', 'The public half. Click it to copy.'));
    P.below.appendChild(rbCopyme(state.pub, 'the public key is on the clipboard'));
    var u = (f.user && f.user.value) || 'the account';
    P.below.appendChild(el('p', 'btnhelp', 'On the server, as ' + u + ':'));
    P.below.appendChild(rbCopyme("mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '" + state.pub + "' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"));
  };
  mk.onclick = function () {
    rbConfirm('Make a key for ' + ((f.name && f.name.value) || t.name || 'this destination'),
      'A fresh ed25519 pair is made here. The private half stays on this machine and the public half is shown for you to put on the server.' + (state.has ? '<br><br><b>The key kept now is replaced</b>, so until the new public half is on the server, backups cannot sign in there.' : ''),
      'Make one', function () {
        rbNeedSaved(t.kind, cur).then(function () { return api('rbackup', {action: 'keygen', id: cur.id}); })
          .then(function (x) { state.pub = x.pub; state.has = true; paint(); toast('a new key was made — put the public half on the server', 'good'); })
          .catch(oops);
      }, false);
  };
  own.onclick = function () {
    modalOver(function () {
      modal('Use my own key', function (body2) {
        var p = el('p', 'note');
        p.innerHTML = 'An OpenSSH private key, whole, including its <code>BEGIN</code> and <code>END</code> lines. It is kept in this machine’s database, sealed, and never shown back. Its public half is worked out here, so you do not have to hand that over as well.';
        body2.appendChild(p);
        var area = el('textarea', 'mono');
        area.rows = 11;
        area.id = 'rb-paste-area';
        area.spellcheck = false;
        area.placeholder = '-----BEGIN OPENSSH PRIVATE KEY-----';
        body2.appendChild(area);
        var pp = maskBox('', '', 'mono');
        pp.id = 'rb-paste-pp';
        body2.appendChild(formField('Its passphrase, if it has one', pp));
        setTimeout(function () { area.focus(); }, 60);
      }, [{words: 'Cancel', close: true},
          {words: 'Keep this key', cls: 'primary', close: true, go: function () {
            var key = $('rb-paste-area').value, pass = $('rb-paste-pp').value;
            rbNeedSaved(t.kind, cur).then(function () { return api('rbackup', {action: 'key_paste', id: cur.id, key: key, passphrase: pass}); })
              .then(function (x) { state.pub = x.pub; state.has = true; paint(); toast('the key was stored', 'good'); })
              .catch(oops);
          }}]);
    });
  };
  dl.onclick = function () {
    rbConfirm('Download the private key', 'The private half leaves this machine as a file. Anybody holding it can sign in to the server as <code>' + htmlText((f.user && f.user.value) || 'that account') + '</code>. That it was downloaded, and by whom, is written into Events.', 'Download it', function () {
      api('rbackup', {action: 'key_download', id: cur.id}).then(function (x) {
        var a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([x.pem], {type: 'application/octet-stream'}));
        a.download = x.file;
        document.body.appendChild(a); a.click(); a.remove();
      }).catch(oops);
    }, false);
  };
  fg.onclick = function () {
    rbConfirm('Forget the key', 'The private key is deleted from this machine. Unless the server takes a password instead, backups will not reach it until a new key is made and put on it.', 'Forget it', function () {
      api('rbackup', {action: 'key_forget', id: cur.id}).then(function () { state.has = false; state.pub = ''; paint(); toast('the key is gone'); }).catch(oops);
    });
  };
  paint();
  s.appendChild(P.box);
  f.ssh_cert = el('textarea', 'mono rb-area small');
  f.ssh_cert.value = t.ssh_cert || '';
  f.ssh_cert.placeholder = 'ssh-ed25519-cert-v01@openssh.com AAAA…';
  var cf = formField('SSH certificate of the key (only if the server wants one)', f.ssh_cert);
  cf.style.marginTop = '12px';
  s.appendChild(cf);
  body.appendChild(s);
  var h = el('div', 'rb-sec');
  h.appendChild(el('h4', '', 'The server’s host key'));
  var H = rbPanel('The key the server proves itself with. Trusted once, after comparing its fingerprint with the server’s own (<code>ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub</code> on it); a server answering with any other is refused - somebody in between, or the server reinstalled.');
  var hf = cmdButton('Forget it', 'forget', 'danger');
  H.row.appendChild(hf);
  H.row.appendChild(el('span', 'spacer'));
  H.row.appendChild(rbTryButton(t, cur));
  var paintHost = function (fps) {
    clear(H.below);
    hf.disabled = !(fps && fps.length);
    if (fps && fps.length) {
      H.below.appendChild(el('p', 'btnhelp ro', 'Trusted. Click to copy.'));
      fps.forEach(function (x) { H.below.appendChild(rbCopyme(x)); });
    } else {
      H.below.appendChild(el('p', 'btnhelp', 'Not trusted yet — Try reaching it shows the fingerprint to trust.'));
    }
  };
  hf.onclick = function () {
    rbConfirm('Forget the host key', 'Backups stop going there until it is trusted again.', 'Forget it', function () {
      api('rbackup', {action: 'hostkey_forget', id: cur.id}).then(function () { paintHost([]); }).catch(oops);
    });
  };
  paintHost(t.hostkey_fp);
  rbSshBlock.paintHost = paintHost;
  h.appendChild(H.box);
  body.appendChild(h);
}
function rbFtpsBlock(body, t, f, cur) {
  var s = el('div', 'rb-sec');
  s.appendChild(el('h4', '', 'TLS'));
  var g = el('div', 'formgrid');
  f.implicit = selectBox([['0', 'explicit - AUTH TLS on port 21'], ['1', 'implicit - TLS from the start, port 990']], t.implicit ? '1' : '0');
  f.implicit._get = function () { return f.implicit.value === '1' ? 1 : 0; };
  f.implicit.onchange = function () { if (f.port && (!f.port.value || f.port.value === '21' || f.port.value === '990')) f.port.value = f.implicit.value === '1' ? '990' : '21'; };
  g.appendChild(formField('TLS', f.implicit));
  f.tls_check = selectBox([['system', 'against the authorities this machine trusts'], ['ca', 'against an authority of my own'], ['pin', 'pinned: exactly this certificate'], ['none', 'not checked (not safe)']], t.tls_check || 'system');
  g.appendChild(formField('The server’s certificate is checked', f.tls_check));
  s.appendChild(g);
  f.ca = el('textarea', 'mono rb-area small');
  f.ca.value = t.ca || '';
  f.ca.placeholder = '-----BEGIN CERTIFICATE-----';
  var caf = formField('The authority (PEM)', f.ca, t.ca_info ? 'Now: ' + (t.ca_info.subject || '') + ' · ' + rbWhen(t.ca_info.not_after) : 'The certificate of the authority that signed the server’s.');
  s.appendChild(caf);
  f.pin = textBox(t.pin || '', '64 hex digits - Try reaching it shows the server’s', 'mono');
  var pinf = formField('Pinned SHA-256 fingerprint', f.pin);
  s.appendChild(pinf);
  var show = function () { caf.hidden = f.tls_check.value !== 'ca'; pinf.hidden = f.tls_check.value !== 'pin'; };
  f.tls_check.onchange = show;
  show();
  rbFtpsBlock.pin = f.pin;
  rbFtpsBlock.check = f.tls_check;
  body.appendChild(s);
  var cc = el('div', 'rb-sec');
  cc.appendChild(el('h4', '', 'Client certificate'));
  var P = rbPanel('Only for a server that asks for one. Made here, its key never leaves this machine except when you download it; the server gets the <b>certificate</b> - give it to its administrator.');
  var mk = cmdButton('Make one', 'key', '');
  explain(mk, 'A key and a certificate for it, made here (EC P-256, five years). Any one kept is replaced.');
  var own = cmdButton('Use my own', 'upload', '');
  explain(own, 'A certificate and its key you have: PEM (both, in any order) or a PFX / PKCS#12 file with its password.');
  var dl = cmdButton('Download it', 'download', '');
  explain(dl, 'The certificate as a file (not its key), for the server’s administrator.');
  var fg = cmdButton('Forget it', 'forget', 'danger');
  [mk, own, dl, fg].forEach(function (b) { P.row.appendChild(b); });
  P.row.appendChild(el('span', 'spacer'));
  P.row.appendChild(rbTryButton(t, cur));
  var state = {cert: t.client_cert, info: t.client_cert_info};
  var paint = function () {
    clear(P.below);
    dl.disabled = fg.disabled = !state.cert;
    if (!state.cert) {
      P.below.appendChild(el('p', 'btnhelp', 'No client certificate — most servers want none.'));
      return;
    }
    if (state.info) P.below.appendChild(noI18n(el('p', 'btnhelp ro', (state.info.subject || '') + ' · ' + rbWhen(state.info.not_after))));
    P.below.appendChild(el('p', 'btnhelp', 'The certificate. Click it to copy.'));
    P.below.appendChild(rbCopyme(state.cert, 'the certificate is on the clipboard'));
  };
  mk.onclick = function () {
    rbConfirm('Make a client certificate', 'A key and a certificate for it are made here; the key stays on this machine.' + (state.cert ? '<br><br><b>The one kept now is replaced</b>: the server has to be given the new certificate.' : ''), 'Make one', function () {
      rbNeedSaved(t.kind, cur).then(function () { return api('rbackup', {action: 'cert_make', id: cur.id, cn: 'ai-backup-' + (RB.node || '')}); })
        .then(function (x) { state.cert = x.cert; state.info = x.info; paint(); toast('made — give the certificate to the server', 'good'); }).catch(oops);
    }, false);
  };
  own.onclick = function () {
    modalOver(function () {
      modal('Use my own client certificate', function (body2) {
        var p = el('p', 'note');
        p.innerHTML = 'The certificate and its private key, as PEM - pasted, in any order - or a <code>.pfx</code> / <code>.p12</code> file. The key is kept sealed and never shown back.';
        body2.appendChild(p);
        var area = el('textarea', 'mono');
        area.rows = 11;
        area.id = 'rb-cert-area';
        area.spellcheck = false;
        area.placeholder = '-----BEGIN CERTIFICATE-----\n…\n-----BEGIN PRIVATE KEY-----';
        body2.appendChild(area);
        var file = el('input');
        file.type = 'file';
        file.accept = '.pem,.crt,.key,.pfx,.p12';
        file.onchange = function () {
          var fl = file.files[0];
          if (!fl) return;
          if (/\.(pfx|p12)$/i.test(fl.name)) fl.arrayBuffer().then(function (buf) {
            var b = new Uint8Array(buf), s2 = '';
            for (var i = 0; i < b.length; i++) s2 += String.fromCharCode(b[i]);
            area.value = btoa(s2);
          });
          else fl.text().then(function (x) { area.value = (area.value ? area.value + '\n' : '') + x; });
        };
        body2.appendChild(formField('Or a file', file));
        var pw = maskBox('', '', 'mono');
        pw.id = 'rb-cert-pw';
        body2.appendChild(formField('The password of the key or of the PFX, if it has one', pw));
      }, [{words: 'Cancel', close: true},
          {words: 'Keep this certificate', cls: 'primary', close: true, go: function () {
            var text = $('rb-cert-area').value, pass = $('rb-cert-pw').value;
            rbNeedSaved(t.kind, cur).then(function () { return api('rbackup', {action: 'cert_given', id: cur.id, text: text, password: pass}); })
              .then(function (x) { state.cert = x.cert; state.info = x.info; paint(); toast('the certificate was stored', 'good'); }).catch(oops);
          }}]);
    });
  };
  dl.onclick = function () {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([state.cert], {type: 'application/x-pem-file'}));
    a.download = 'ai-backup-client.crt';
    document.body.appendChild(a); a.click(); a.remove();
  };
  fg.onclick = function () {
    rbConfirm('Forget the client certificate', 'Its key is deleted from this machine. A server that asks for one will refuse backups until another is made and given to it.', 'Forget it', function () {
      api('rbackup', {action: 'cert_forget', id: cur.id}).then(function () { state.cert = ''; state.info = null; paint(); }).catch(oops);
    });
  };
  paint();
  cc.appendChild(P.box);
  body.appendChild(cc);
}
function rbTry(t, data, button, inEditor) {
  if (button) busy(button, true);
  var ask = {action: 'try', id: t.id || ''};
  if (data) ask.target = data;
  api('rbackup', ask).then(function (x) {
    if (button) busy(button, false);
    var show = function (host) {
      clear(host);
      if (x.hostkey_needed) {
        host.appendChild(el('p', 'note warn', 'The server shows this host key. Compare it with the server’s own fingerprint before you trust it:'));
        (x.fingerprints || []).forEach(function (fp) { host.appendChild(noI18n(el('div', 'mono small', fp))); });
        var tb = cmdButton('Trust it', 'check', 'small primary');
        tb.onclick = function () {
          var save = (inEditor && rbEdit.form) ? rbSaveForm(t.kind, {id: t.id}) : Promise.resolve(t);
          save.then(function (saved) {
            return api('rbackup', {action: 'hostkey_trust', id: saved.id, hostkey: x.hostkey}).then(function (y) {
              toast('trusted', 'good');
              if (rbSshBlock.paintHost) rbSshBlock.paintHost(y.fingerprints);
              t.id = saved.id;
              rbTry(saved, inEditor ? rbFormData(t.kind) : null, button, inEditor);
            });
          }).catch(oops);
        };
        host.appendChild(tb);
        return;
      }
      var box = el('div', 'note ' + (x.ok ? 'good' : 'bad'));
      box.appendChild(el('b', '', x.ok ? 'It works (' + x.secs + ' s)' : 'It does not work'));
      var ul = el('ul', 'rb-steps');
      (x.steps || []).forEach(function (s) { ul.appendChild(el('li', '', '✓ ' + s)); });
      if (x.error) ul.appendChild(el('li', 'bad', '✗ ' + x.error));
      box.appendChild(ul);
      var sc = x.server_cert;
      if (sc && sc.fingerprint) {
        var p = el('div', 'small');
        p.appendChild(el('span', '', 'The server’s certificate: '));
        p.appendChild(noI18n(el('span', 'mono', ((sc.cert || {}).subject || '') + ' · SHA-256 ' + sc.fingerprint)));
        box.appendChild(p);
        if (inEditor && rbFtpsBlock.pin) {
          var pin = cmdButton('Pin this certificate', 'pin', 'small');
          pin.onclick = function () { rbFtpsBlock.check.value = 'pin'; rbFtpsBlock.check.onchange(); rbFtpsBlock.pin.value = sc.fingerprint; toast('pinned - Save to keep it', 'good'); };
          box.appendChild(pin);
        }
      }
      host.appendChild(box);
      if (inEditor) host.appendChild(hideBar(function () { clear(host); }));
    };
    var host = inEditor ? $('rb-try-out') : null;
    if (host) show(host);
    else modal('Trying ' + (t.name || ''), function (body) { var h = el('div'); body.appendChild(h); show(h); }, [{words: 'Close', close: true}], 'medium');
    if (!inEditor) loadRbackup();
  }).catch(function (e) { if (button) busy(button, false); oops(e); });
}
function rbListThere(t) {
  modal('Backups at ' + t.name, function (body) {
    var host = el('div');
    host.appendChild(el('p', 'center muted', 'Asking…'));
    body.appendChild(host);
    api('rbackup', {action: 'list', id: t.id}).then(function (x) {
      clear(host);
      var files = x.files || [];
      if (!files.length) { host.appendChild(el('p', 'note', 'No backup of ai there.')); return; }
      host.appendChild(listTable(['Made', 'Node', 'Size', '', ''], files, function (fl) {
        var tr = el('tr');
        var w = el('td');
        w.appendChild(el('div', '', new Date(fl.when * 1000).toLocaleString(numLang())));
        w.appendChild(noI18n(el('div', 'mono small muted', fl.name)));
        tr.appendChild(w);
        var n = el('td');
        n.appendChild(noI18n(el('span', '', fl.node)));
        if (fl.mine) { n.appendChild(document.createTextNode(' ')); n.appendChild(el('span', 'tag info', 'this server')); }
        tr.appendChild(n);
        var sz = el('td', 'num');
        sz.textContent = rbBytes(fl.bytes);
        if (!fl.encrypted) { sz.appendChild(document.createTextNode(' ')); sz.appendChild(el('span', 'tag bad', 'not locked')); }
        tr.appendChild(sz);
        var a = el('td', 'rowtools');
        var dl = iconButton('download', 'Download it');
        dl.onclick = function () { rbDownload({id: t.id, name: fl.name}); };
        a.appendChild(dl);
        var pb = iconButton('undo', 'Put this back…');
        pb.onclick = function () { rbPutBackConfirm({id: t.id, name: fl.name, encrypted: fl.encrypted, when: fl.when, node: fl.node}); };
        a.appendChild(pb);
        var del = iconButton('trash', 'Delete it there');
        del.onclick = function () {
          confirmThen('Delete ' + htmlText(fl.name) + '?', 'It is deleted at ' + htmlText(t.name) + ', with its checksum and its RESTORE.md.', 'Delete it', function () {
            api('rbackup', {action: 'delete_file', id: t.id, name: fl.name}).then(function () { toast('deleted', 'good'); rbListThere(t); }).catch(oops);
          });
        };
        a.appendChild(del);
        tr.appendChild(a);
        return tr;
      }, 'plain'));
    }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
  }, [{words: 'Close', close: true}], 'large');
}
function rbPutBackConfirm(what) {
  modal('Put this backup back?', function (body) {
    var facts = [];
    if (what.when) facts.push(['Made', new Date(what.when * 1000).toLocaleString(numLang())]);
    if (what.node) facts.push(['On', what.node]);
    if (what.manifest) {
      var m = what.manifest;
      facts = [['Made', m.made_words], ['On', m.node + ' (' + (m.host || '') + ')'], ['ai', m.ai], ['Accounts', String(m.accounts)]];
    }
    if (facts.length) body.appendChild(peekFacts(facts));
    body.appendChild(el('p', 'note warn', 'Everything in the database is replaced with what the backup holds - accounts, settings, the certificate, events, and who is signed in: you sign in again afterwards, with an account the backup has. A copy of what is here now is made first (Settings → Database). The terminals go on running.'));
    var pw = maskBox('', what.encrypted === false ? '(not locked)' : 'the password of the backups - empty: the one set here', 'mono');
    body.appendChild(formField('Its password', pw, 'Only when it was locked with another password than the one set here now.'));
    rbPutBackConfirm.pw = pw;
  }, [{words: 'No, leave it', close: true},
      {words: 'Put it back', cls: 'danger', icon: 'undo', close: true, go: function () {
        var ask = {action: 'restore', password: rbPutBackConfirm.pw.value};
        if (what.upload) ask.upload = what.upload; else { ask.id = what.id; ask.name = what.name; }
        api('rbackup', ask).then(function (x) {
          toast(x.message, 'good');
          rbRestoreWatch();
        }).catch(oops);
      }}], 'medium');
}
function rbRestoreWatch(title) {
  modal(title || 'Putting the backup back', function (body) {
    var bar = el('div', 'going wide');
    bar.innerHTML = '<div class="bar"><span id="rbr-fill"></span></div><div class="says" id="rbr-says"></div>';
    body.appendChild(bar);
  }, [{words: 'Close', close: true}], 'medium');
  var step = function () {
    api('rbackup', {action: 'job'}).then(function (d) {
      var j = d.job || {};
      if ($('rbr-fill')) $('rbr-fill').style.width = (j.whole ? Math.round(100 * j.done / j.whole) : 5) + '%';
      if ($('rbr-says')) $('rbr-says').textContent = (j.what || '') + (j.says ? ' — ' + j.says : '');
      if (j.running) { setTimeout(step, 1000); return; }
      if (!j.what && !j.result && !j.error) { setTimeout(step, 1000); return; }
      if (j.error) { if ($('rbr-says')) $('rbr-says').textContent = j.error; toast('putting it back failed: ' + j.error, 'bad'); return; }
      var r = j.result || {};
      if ($('rbr-says')) {
        var said = $('rbr-says');
        clear(said);
        said.appendChild(el('div', '', 'Put back.'));
        (r.said || []).concat(r.key ? [r.key] : []).forEach(function (x) { said.appendChild(el('div', 'small', x)); });
        if (r.safety) said.appendChild(el('div', 'small muted', 'What was here is kept as ' + r.safety));
      }
      toast(title ? 'the database is back' : 'the backup is back', 'good');
      if (title) setTimeout(function () { location.reload(); }, 4000);
    }).catch(function (e) {
      /* Who was signed in is what the backup says now: the sign-in page. */
      if (/signed in|401/i.test(String(e && e.message || e))) {
        if ($('rbr-says')) $('rbr-says').textContent = 'Put back. Sign in again - with an account the backup has.';
        setTimeout(function () { location.reload(); }, 3500);
        return;
      }
      setTimeout(step, 2000);
    });
  };
  setTimeout(step, 500);
}
function rbPutBackFile() {
  var file = el('input');
  file.type = 'file';
  file.accept = '.enc,.gz';
  file.onchange = function () {
    var fl = file.files[0];
    if (!fl) return;
    toast('sending ' + fl.name + '…', 'good');
    var up = '';
    var a = new Uint8Array(8);
    crypto.getRandomValues(a);
    for (var i = 0; i < a.length; i++) up += ('0' + a[i].toString(16)).slice(-2);
    sendFile('/files/put?dir=' + encodeURIComponent(RB.uploads) + '&name=' + up, fl, function () {}).then(function () {
      return api('rbackup', {action: 'peek', upload: up});
    }).then(function (d) {
      if (d.said) toast(d.said, 'bad');
      rbPutBackConfirm({upload: d.upload, encrypted: d.locked, manifest: d.manifest});
    }).catch(oops);
  };
  file.click();
}

/* A button busy with something slow, the seconds counted beside its words
   (1.0.109). Returns the function that ends it. */
function busyCount(button) {
  busy(button, true);
  var began = Date.now();
  var tag = el('span', 'busy-secs', '');
  button.appendChild(tag);
  var tick = setInterval(function () { tag.textContent = ' · ' + Math.round((Date.now() - began) / 1000) + ' s'; }, 500);
  return function () { clearInterval(tick); tag.remove(); busy(button, false); };
}


/* A backup to the machine somebody is sitting at: made (or fetched) by the
   daemon where /files/get hands it to this administrator. */
function rbDownload(ask) {
  api('rbackup', Object.assign({action: 'download'}, ask)).then(function (d) { download(d.path); }).catch(oops);
}
