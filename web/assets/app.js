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
  if (name === 'people') loadUsers();
  if (name === 'web') loadCert();
  if (name === 'fw') loadFw();
  if (name === 'network') loadNet();
  if (name === 'time') loadNtp();
  if (name === 'power') loadPower();
  if (name === 'osup') loadOsup(); else if (typeof ouPoll === 'function') ouPoll(false);
  if (name === 'sshkeys') loadSshKeys(); else if (typeof skPoll === 'function') skPoll(false);
  if (name === 'upgrade') loadUpgrade();
  if (name === 'about') loadAbout();
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
var SECT = {claude: 'sect-claude', access: 'sect-access', upgrade: 'sect-upgrade', general: 'sect-general'};
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
  } else {
    input = textBox(s.value === null || s.value === undefined ? '' : s.value, '', s.kind === 'int' ? '' : 'mono');
    if (s.kind === 'int') { input.type = 'number'; if (s.extra.min !== undefined) input.min = s.extra.min; if (s.extra.max !== undefined) input.max = s.extra.max; }
    input.oninput = function () { mark(); };
  }
  if (input.id === '') input.id = 'set-' + s.key;
  item.appendChild(input);
  if (s.help) item.appendChild(el('div', 'says', s.help));
  if (s.saved) {
    var back = el('button', 'link small', 'back to the default');
    back.type = 'button';
    explain(back, 'The built-in value: ' + (s.default === '' ? '(empty)' : String(s.default)));
    back.onclick = function () { DIRTY[s.key] = null; item.classList.add('dirty'); markDirtyCount(); };
    item.appendChild(back);
  }
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
  }
  return item;
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
    host.appendChild(listTable(['Name', 'Role', 'Terminals run as', 'Files in', 'Last sign-in', ''], d.users, function (u) {
      var tr = el('tr', 'clickable' + (u.disabled ? ' dim' : ''));
      var n = noI18n(el('td', '', u.name));
      if (u.disabled) n.appendChild(tagEl('off', 'crit'));
      if (u.must_change) n.appendChild(tagEl('to choose a password', 'warn'));
      tr.appendChild(n);
      tr.appendChild(el('td', '', roleWords(u.role)));
      tr.appendChild(noI18n(el('td', 'mono', u.run_as + (u.run_as_own ? '' : ' *'))));
      tr.appendChild(noI18n(el('td', 'mono small', u.role === 'admin' ? 'everywhere' : (u.roots.join(', ') || '~' + u.run_as))));
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
      tr.appendChild(noI18n(el('td', '', s.name)));
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
  modal('The account ' + u.name, function (body) { body._f = userForm(body, u); }, [
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
    }}], 'wide');
}

/* ---- the certificate ------------------------------------------------------------- */
function loadCert() {
  api('cert').then(function (d) {
    var c = d.cert, host = $('ce-now');
    clear(host);
    if (!c.there) { host.appendChild(el('p', 'muted', 'There is no certificate at the place nginx reads it from.')); return; }
    var days = c.until_ts ? Math.floor((c.until_ts - Date.now() / 1000) / 86400) : null;
    host.appendChild(kvTable([
      ['For', noI18n(el('span', 'mono', c.subject || ''))],
      ['Names', noI18n(el('span', 'mono', (c.names || []).join(', ')))],
      ['By', noI18n(el('span', '', (c.issuer || '') + (c.self_signed ? ' (itself)' : '')))],
      ['Valid', (c.from || '') + ' - ' + (c.until || '') + (days !== null ? ' (' + days + ' days left)' : '')],
      ['SHA-256', noI18n(el('span', 'mono small', c.sha256 || ''))],
      ['File', noI18n(el('span', 'mono', c.file))]
    ]));
    if (!$('ce-names').value) $('ce-names').value = (c.names && c.names.length ? c.names : [d.host]).join(', ');
  }).catch(oops);
}
$('ce-put').onclick = function () {
  busy($('ce-put'), true);
  api('cert', {do: 'put', cert: $('ce-cert').value, key: $('ce-key').value}).then(function () {
    toast('the certificate is in', 'good');
    $('ce-key').value = '';
    loadCert();
  }).catch(oops).then(function () { busy($('ce-put'), false); });
};
$('ce-self').onclick = function () {
  confirmThen('A new self-signed certificate?', 'The browsers warn about it again until it is trusted.', 'Make it', function () {
    api('cert', {do: 'self', names: $('ce-names').value, days: parseInt($('ce-days').value, 10) || 825})
      .then(function () { toast('a new certificate is in', 'good'); loadCert(); }).catch(oops);
  }, false);
};
$('ce-file').onclick = function () { $('ce-input').click(); };
$('ce-input').onchange = function () {
  Array.prototype.forEach.call($('ce-input').files, function (f) {
    f.text().then(function (t) {
      if (/PRIVATE KEY/.test(t)) $('ce-key').value = t;
      if (/CERTIFICATE/.test(t)) $('ce-cert').value = ($('ce-cert').value ? $('ce-cert').value + '\n' : '') + t;
    });
  });
};

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
  var h = (location.hash || '').replace(/^#/, '').split('/');
  var tab = h[0] || 'terms', sub = h.slice(1).join('/');
  if (tab === 'files' && sub) sub = decodeURIComponent(sub);
  showTab(tab, sub || undefined);
  liveLoop();
  if (ME && ME.must_change) setTimeout(mustChange, 50);
  window.addEventListener('beforeunload', function () { termClose(); });
}());
