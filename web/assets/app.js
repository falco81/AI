/* app.js - the pages of ai: the terminals, the files, the conversations, the
   server's settings. Drawn with core.js, otp's own helpers, so that it looks
   and behaves as otp's administration pages do; every answer comes from the
   daemon, which decides what this sign-in may see and do. */
'use strict';

ADMIN = !!(ME && ME.role === 'admin');
var PANE = 'claude';
var RAIL = {pinned: false, open: null, shut: null};
var SETTINGS = null, DIRTY = {}, DRAWN_NODE = '';
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
var TABS = ['terms', 'files', 'history', 'claude', 'overview', 'events', 'settings'];
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
  if (TAB === 'claude' && typeof CC !== 'undefined') want += '/' + CC.pane;
  if (TAB === 'terms' && TL.open) want += '/' + TL.open;
  if (TAB === 'files' && FL.path) want += '/' + encodeURIComponent(FL.path);
  if (TAB === 'overview' && typeof OV !== 'undefined' && OV.part === 'claude') want += '/claude';
  if (location.hash !== want) try { history.replaceState(null, '', want); } catch (e) { }
}
function onTab(name, sub) {
  explainWhatWasDrawn(document);
  if (ME && ME.must_change) return;           /* a password of its own first */
  if (name === 'terms') { loadTerms(sub); if (TL.open) setTimeout(termFit, 30); }
  if (name === 'files') loadFiles(sub || FL.path || '');
  if (name === 'history') loadHistory();
  if (name === 'claude' && typeof loadCC === 'function') loadCC(sub);
  if (name === 'overview') loadOverview(sub);
  if (name === 'events') loadEvents();
  if (name === 'settings') { loadSettings(); showPane(sub || PANE); }
}

/* ---- the header, the live updates ------------------------------------------- */
function paintHeader(s) {
  STATUS = s;
  if (s.mailq && typeof mailqBadge === 'function') mailqBadge(s.mailq);
  var pill = $('state-pill');
  var kind = s.problems && s.problems.length ? 'warn' : 'ok';
  var inMaint = !!(s.maintenance && s.maintenance.on);
  if (s.upgrade_state === 'running' || inMaint) kind = 'warn';
  pill.className = 'pill ' + kind;
  pill.lastChild.textContent = s.upgrade_state === 'running' ? 'being upgraded'
    : (inMaint ? 'in maintenance' : (kind === 'warn' ? 'running, with trouble' : 'running'));
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
function meInitials(name, display) {
  var words = String(display || name || '?').replace(/[^\p{L}\p{N}\s._-]/gu, ' ')
    .split(/[\s._@-]+/).filter(Boolean);
  var two = words.length > 1 ? words[0][0] + words[words.length - 1][0] : String(words[0] || name || '?').slice(0, 2);
  return two.toUpperCase();
}
/* Your account, as otp draws it: who, what you may do, the language and the
   letters of the terminal, the columns of the tables, your settings in a
   file, a new password. */
function showMe() {
  modal('Your account', function (body) {
    var head = el('div', 'me-head');
    var ava = noI18n(el('div', 'me-ava' + (ME.role === 'admin' ? ' admin' : ''), meInitials(ME.name)));
    ava.setAttribute('aria-hidden', 'true');
    head.appendChild(ava);
    var who = el('div', 'me-who');
    who.appendChild(noI18n(el('div', 'me-n mono', ME.name)));
    var tags = el('div', 'me-tags');
    tags.appendChild(el('span', 'tag ' + (ME.role === 'admin' ? 'violet' : 'dim'), roleWords(ME.role)));
    if (ME.mfa_kind) tags.appendChild(el('span', 'tag ok', 'second step: ' + (ME.mfa_kind === 'app' ? 'app' : 'e-mail')));
    who.appendChild(tags);
    head.appendChild(who);
    body.appendChild(head);
    var may = el('div', 'me-sec');
    may.appendChild(el('h3', '', 'What you may do'));
    may.appendChild(el('p', '', ME.role === 'admin' ? 'Anything: terminals as any Linux account, every file, the settings and the server itself.'
      : 'Terminals of your own, as the Linux account below, and the files of your folders. No setting and no account.'));
    may.appendChild(kvTable([
      ['Terminals run as', noI18n(el('span', 'mono', ME.run_as))],
      ['Files in', noI18n(el('span', 'mono', ME.role === 'admin' ? 'everywhere' : ((ME.roots || []).join(', ') || 'the home of ' + ME.run_as)))],
      ['Last sign-in', stamp(ME.last_login) + (ME.last_ip ? ' · ' + ME.last_ip : '')]
    ]));
    body.appendChild(may);
    var lsec = el('div', 'me-sec');
    lsec.appendChild(el('h3', '', 'Language and letters'));
    var lang = selectBox((window.AI_LANGS || []).map(function (l) { return [l.code, l.name]; }), window.AI_LANG);
    noI18n(lang);
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
    g.appendChild(formField('The language of these pages', lang));
    g.appendChild(formField('Size of the terminal\'s letters', font));
    lsec.appendChild(g);
    lsec.appendChild(el('p', 'small muted', 'The colours of the terminals - for every terminal you open, kept with your account:'));
    lsec.appendChild(termPalettePicker());
    var rb = selectBox([['paste', 'pastes, as in PuTTY - what is selected is copied by itself; Ctrl + right button: the menu'],
                        ['menu', 'opens the menu (copy, paste, the chat...)']], termRightMode());
    rb.onchange = function () { savePrefs({term_right: rb.value}).then(function () { toast('kept', 'good'); }).catch(oops); };
    var g2 = el('div', 'formgrid');
    g2.style.marginTop = '12px';
    var rf = formField('The right mouse button in a terminal', rb);
    rf.classList.add('span-2');
    g2.appendChild(rf);
    lsec.appendChild(g2);
    body.appendChild(lsec);

    /* The columns of the tables - exactly otp's (isemon's). */
    var cols = el('div', 'me-sec');
    cols.appendChild(el('h3', '', 'Columns of the tables'));
    var line = el('div', 'me-row');
    var say = el('div', 'me-say');
    say.innerHTML = '<b>Edit the columns</b><br>While this is on, the edge of any column’s '
      + 'heading can be dragged to size it and the heading itself to move it, and the right '
      + 'button on a heading hides a column, brings a hidden one back or adds an empty one '
      + 'for room; each change is kept the moment you let go. It is for this sign-in only: signing out or the sign-in '
      + 'running out turns it off again. Off, the tables are drawn '
      + 'as you left them and nothing can move them.';
    line.appendChild(say);
    var sw = el('label', 'sw');
    var box = el('input');
    box.type = 'checkbox';
    box.id = 'me-cols-edit';
    box.checked = COLS_EDIT;
    box.setAttribute('aria-label', 'Edit the columns');
    sw.appendChild(box);
    sw.appendChild(el('span', 'knob'));
    line.appendChild(sw);
    cols.appendChild(line);
    box.onchange = function () {
      var on = box.checked;
      box.disabled = true;
      colsSwitch(on).then(function (d) {
        box.checked = !!d.edit;
      }).catch(function (e) {
        box.checked = COLS_EDIT;
        oops(e);
      }).then(function () { box.disabled = false; });
    };
    var laid = Object.keys(COLS).length;
    cols.appendChild(el('p', '', laid ? 'You have laid out ' + num(laid) + ' table(s).'
      : 'Every table is as it comes.')).style.marginTop = '10px';
    var acts = el('div', 'me-acts');
    var back = cmdButton('Put my columns back as they come', 'undo', 'small');
    explain(back, 'Every table you have laid out goes back as it comes: the widths and the '
      + 'order of the columns, on every page. Nobody else’s change.');
    back.disabled = !laid;
    back.onclick = function () {
      back.disabled = true;
      colsReset().then(function () { closeModal(); showMe(); }).catch(function (e) {
        back.disabled = false;
        oops(e);
      });
    };
    acts.appendChild(back);
    cols.appendChild(acts);
    body.appendChild(cols);

    /* Your own settings, to a file and back. */
    var mine = el('div', 'me-sec');
    mine.appendChild(el('h3', '', 'Your settings in a file'));
    mine.appendChild(el('p', '', 'How you have set these pages up for yourself — the '
      + 'columns of the tables, the language, the letters and keys of the terminal — saved as a JSON file, and read back here '
      + 'or on another machine running ai. Never your password, your role or anything else '
      + 'about the account.'));
    var io = el('div', 'me-acts');
    var out = cmdButton('Export my settings', 'download', 'small');
    out.onclick = function () { meExport(out); };
    io.appendChild(out);
    var inn = cmdButton('Import settings…', 'upload', 'small');
    inn.onclick = function () { mePick(); };
    io.appendChild(inn);
    mine.appendChild(io);
    body.appendChild(mine);

    var ssec = el('div', 'me-sec');
    ssec.appendChild(el('h3', '', 'Where you are signed in'));
    ssec.appendChild(el('p', '', 'You may be signed in from several places at once - every one sees the same terminals, live. Signing out or closing the browser ends no terminal: Claude Code goes on working on the server.'));
    var sacts = el('div', 'me-acts');
    var every = cmdButton('Sign out everywhere', 'out', 'small');
    every.onclick = function () {
      confirmThen('Sign out everywhere?', 'Every sign-in of yours ends - here and on every other computer. The terminals go on running.', 'Sign out everywhere', function () {
        api('logout', {everywhere: true}).then(function () { location.href = '/'; }).catch(function () { location.href = '/'; });
      }, true);
    };
    sacts.appendChild(every);
    ssec.appendChild(sacts);
    body.appendChild(ssec);

    var pwsec = el('div', 'me-sec');
    pwsec.appendChild(el('h3', '', 'A new password'));
    body.appendChild(pwsec);
    body._go = passwordForm(pwsec, false);
  }, [{words: 'Close', close: true},
      {words: 'Change the password', cls: 'primary', icon: 'lock', go: function (b) { $('modal-body')._go(b); }}], 'medium');
}
$('me-btn').onclick = showMe;

/** "Edit the columns" on or off for this sign-in: the daemon holds it. */
function colsSwitch(on) {
  return api('columns', {edit: !!on}).then(function (d) {
    colsEditing(!!d.edit);
    colsCardSay();
    toast(d.edit ? 'Columns can be sized and moved now — each change is kept at once'
      : 'Columns are held as they are', 'good');
    return d;
  });
}

/** The file a person's own settings go into: one object with a mark of
    what it is, where and when it came from, and `settings` by section -
    `columns` and `prefs`; a version that does not know a section leaves it
    alone. As isemon's, with its own kind. */
var ME_FILE_KIND = 'ai-user-settings';

function meExport(button) {
  if (button) button.disabled = true;
  api('my-settings').then(function (d) {
    var file = {
      kind: ME_FILE_KIND,
      format: 1,
      from: location.host,
      version: d.version || '',
      user: d.name || (ME && ME.name) || '',
      exported: new Date().toISOString(),
      settings: d.settings || {}
    };
    var blob = new Blob([JSON.stringify(file, null, 2) + '\n'], {type: 'application/json'});
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'ai-settings-' + String(file.user || 'me').replace(/[^a-z0-9._-]/gi, '_')
      + '-' + file.exported.slice(0, 10) + '.json';
    document.body.appendChild(link);
    link.click();
    setTimeout(function () { URL.revokeObjectURL(link.href); link.remove(); }, 1500);
    var n = Object.keys((file.settings || {}).columns || {}).length;
    toast('your settings were saved to ' + link.download + ' (' + num(n)
      + ' table layout(s))', 'good');
  }).catch(oops).then(function () { if (button) button.disabled = false; });
}

function mePick() {
  var pick = el('input');
  pick.type = 'file';
  pick.accept = '.json,application/json';
  pick.hidden = true;
  pick.onchange = function () {
    var file = pick.files && pick.files[0];
    pick.remove();
    if (file) meImport(file);
  };
  document.body.appendChild(pick);
  pick.click();
}

function meImport(file) {
  if (file.size > 2 * 1024 * 1024) {
    toast('that file is far bigger than any settings file (' + bytes(file.size) + ')', 'bad');
    return;
  }
  var reader = new FileReader();
  reader.onerror = function () { toast('that file could not be read', 'bad'); };
  reader.onload = function () {
    var got;
    try { got = JSON.parse(String(reader.result || '')); } catch (e) {
      toast('that is not a settings file: it is not JSON', 'bad');
      return;
    }
    /* Our own file, or just its `settings` on their own. isemon's file is
       read as well: the columns are kept the same way in both. */
    var settings = got && (got.kind === ME_FILE_KIND || got.kind === 'otp-user-settings' || got.kind === 'isemon-user-settings')
      ? got.settings
      : (got && got.settings && typeof got.settings === 'object' ? got.settings : got);
    if (!settings || typeof settings !== 'object' || Array.isArray(settings)) {
      toast('that is not a settings file', 'bad');
      return;
    }
    var cols = settings.columns && typeof settings.columns === 'object'
      ? Object.keys(settings.columns).length : null;
    var other = Object.keys(settings).filter(function (k) {
      return k !== 'columns' && k !== 'prefs';
    });
    var at = got.exported ? Date.parse(String(got.exported)) : NaN;
    modal('Import settings', function (body) {
      body.appendChild(peekFacts([
        ['Whose', got.user ? noI18n(el('span', 'mono', String(got.user))) : '–'],
        ['From', got.from ? noI18n(el('span', 'mono', String(got.from))) : '–'],
        ['Saved', isFinite(at) ? stamp(at / 1000) : '–'],
        ['ai version', got.version ? noI18n(el('span', 'mono', String(got.version))) : '–']]));
      body.appendChild(el('p', 'note', 'This file holds:'));
      var list = el('ul', 'me-list');
      if (cols !== null) list.appendChild(el('li', '', 'the columns of ' + num(cols) + ' table(s)'));
      if (settings.prefs && typeof settings.prefs === 'object' && settings.prefs.lang) {
        list.appendChild(el('li', '', 'the language of the page'));
      }
      if (other.length) {
        list.appendChild(el('li', '', other.join(', ') + ' — not kept by this version, left alone'));
      }
      body.appendChild(list);
      body.appendChild(el('p', 'note', 'They replace yours. Your password and your account are not touched.'));
    }, [{words: 'No, leave it', close: true},
        {words: 'Import them', cls: 'primary', close: true, go: function () {
        api('my-settings', {settings: settings}).then(function (d) {
          if (settings.columns && typeof settings.columns === 'object') {
            /* What the daemon kept, not what the file said: it is the same
               less whatever a layout cannot hold. */
            return api('my-settings').then(function (now) {
              colsTake((now.settings || {}).columns || {});
              colsApplyAll();
              return d;
            });
          }
          return d;
        }).then(function (d) {
          toast('imported: the columns of ' + num((d.took || {}).columns || 0) + ' table(s)'
            + ((d.ignored || []).length ? '; left alone: ' + d.ignored.join(', ') : ''), 'good');
          var lang = settings.prefs && typeof settings.prefs === 'object'
            ? String(settings.prefs.lang || '') : '';
          if (lang && lang !== (window.AI_LANG || 'en')
              && (window.AI_LANGS || []).some(function (l) { return l.code === lang; })) {
            location.reload();
            return;
          }
          colsCardSay();
        }).catch(oops);
      }}], true);
  };
  reader.readAsText(file);
}

/** The card on the Accounts pane: how many tables are laid out, and the
    switch's words. */
function colsCardSay() {
  var laid = Object.keys(COLS).length;
  if ($('cols-count')) {
    $('cols-count').textContent = laid ? num(laid) + ' table(s) laid out by you'
      : 'every table as it comes';
  }
  var b = $('cols-edit-go');
  if (b) {
    setButtonIcon(b, COLS_EDIT ? 'check' : 'edit',
                  COLS_EDIT ? 'Stop editing the columns' : 'Edit the columns');
    b.classList.toggle('primary', COLS_EDIT);
  }
  if ($('cols-reset')) $('cols-reset').disabled = !laid;
}
$('cols-edit-go').onclick = function () { colsSwitch(!COLS_EDIT).catch(oops); };
$('cols-reset').onclick = function () {
  confirmThen('Put my columns back',
    'Every table you have laid out goes back as it comes: the widths and the order of the '
    + 'columns, on every page. Nobody else’s tables change.',
    'Put them back', function () { colsReset().then(function () { colsCardSay(); loadUsers(); }).catch(oops); });
};
$('cols-export').onclick = function () { meExport($('cols-export')); };
$('cols-import').onclick = function () { mePick(); };

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

function pins() { return (prefs().pins || []).filter(function (x) { return typeof x === 'string'; }); }
function isPinned(id) { return pins().indexOf(id) >= 0; }
function togglePin(t) {
  var p = pins().filter(function (x) { return x !== t.id && TL.terms.some(function (y) { return y.id === x; }); });
  var was = isPinned(t.id);
  if (!was) p.unshift(t.id);
  savePrefs({pins: p.slice(0, 50)}).then(function () {
    toast(was ? 'no longer pinned: ' + t.title : 'pinned: ' + t.title, 'good');
    drawTermList();
  }).catch(oops);
}
function drawTermList() {
  if (TL.renaming) return;            /* a name being written in its row: not drawn over */
  var host = $('tl-list');
  var q = $('tl-q').value.trim().toLowerCase();
  var all = $('tl-show').value === 'all';
  clear(host);
  var list = TL.terms.filter(function (t) {
    if (!all && t.state === 'ended' && !isPinned(t.id)) return false;
    if (!q) return true;
    return (t.title + ' ' + t.path + ' ' + t.owner + ' ' + t.run_as + ' ' + t.id).toLowerCase().indexOf(q) >= 0;
  });
  if (!list.length) {
    host.appendChild(el('p', 'muted small', TL.terms.length ? 'Nothing matches.' : 'No terminal yet. Press New.'));
  }
  var order = pins();
  var pinned = list.filter(function (t) { return order.indexOf(t.id) >= 0; })
    .sort(function (a, b) { return order.indexOf(a.id) - order.indexOf(b.id); });
  var rest = list.filter(function (t) { return order.indexOf(t.id) < 0; });
  var row = function (t) {
    var row = el('div', 'tl-item' + (t.id === TL.open ? ' on' : '') + (t.state === 'ended' ? ' ended' : ''));
    row.tabIndex = 0;
    row.setAttribute('role', 'button');
    row.dataset.id = t.id;
    var top = el('div', 'tl-top');
    var ic = el('span', 'tl-icon');
    ic.innerHTML = iconMarkup(t.kind === 'claude' ? 'terminal' : (t.kind === 'shell' ? 'log' : 'play'), 16);
    ic.appendChild(el('i', 'tl-dot'));
    ic.title = t.title;
    top.appendChild(ic);
    if (isPinned(t.id)) { var pi = el('span', 'tl-pin'); pi.innerHTML = iconMarkup('pin', 12); top.appendChild(pi); }
    top.appendChild(noI18n(el('span', 'tl-title', t.title)));
    top.appendChild(termStateTag(t));
    row.appendChild(top);
    row.appendChild(noI18n(el('div', 'tl-path mono', t.path || t.cwd)));
    var meta = el('div', 'tl-meta muted');
    meta.appendChild(document.createTextNode(kindWords(t.kind) + ' · ' + t.run_as
      + (ADMIN && t.owner && t.owner !== ME.name ? ' · ' + t.owner : '') + ' · ' + ago(t.activity)));
    row.appendChild(meta);
    var dots = el('button', 'tl-dots');
    dots.type = 'button';
    dots.innerHTML = iconMarkup('more', 16);
    dots.setAttribute('aria-label', 'What to do with it');
    explain(dots, 'Pin it, rename it, its files, start it again, end it… - the right mouse button on it does the same.');
    dots.onclick = function (e) {
      e.stopPropagation();
      var r = dots.getBoundingClientRect();
      termMenu(t, r.left, r.bottom + 4, row);
    };
    row.appendChild(dots);
    row.onclick = function () {
      if (row.querySelector('.tl-rename')) return;
      if (t.state === 'ended') { endedPeek(t); return; }
      openTerm(t.id);
    };
    row.onkeydown = function (e) { if (e.key === 'Enter') row.onclick(); };
    row.addEventListener('contextmenu', function (e) {
      e.preventDefault();
      termMenu(t, e.clientX, e.clientY, row);
    });
    longPress(row, function (x, y) { termMenu(t, x, y, row); });
    host.appendChild(row);
  };
  if (pinned.length) {
    var h1 = el('div', 'tl-sec');
    var hi = el('span', 'tl-pin'); hi.innerHTML = iconMarkup('pin', 11); h1.appendChild(hi);
    h1.appendChild(el('span', '', 'Pinned'));
    host.appendChild(h1);
    pinned.forEach(row);
    if (rest.length) host.appendChild(el('div', 'tl-sec', 'The others'));
  }
  rest.forEach(row);
  explainWhatWasDrawn(host);
}
/* Renamed in its row, as claude.ai renames a chat: Enter keeps it, Esc does not. */
function renameInline(t, row) {
  var title = row && row.querySelector('.tl-title');
  if (!title || (TLR && !TLR.pinned && !narrow() && !$('term-side').classList.contains('open'))) { renameAsk(t); return; }
  var box = el('input', 'tl-rename');
  box.value = t.title;
  box.maxLength = 120;
  title.replaceWith(box);
  box.focus();
  box.select();
  TL.renaming = t.id;
  var done = false;
  var finish = function (keep) {
    if (done) return;
    done = true;
    TL.renaming = '';
    var v = box.value.trim();
    if (!keep || !v || v === t.title) { drawTermList(); return; }
    api('terms', {do: 'rename', id: t.id, title: v}).then(function () { toast('renamed', 'good'); loadTerms(TL.open || undefined, true); })
      .catch(function (e) { oops(e); drawTermList(); });
  };
  box.onkeydown = function (e) {
    e.stopPropagation();
    if (e.key === 'Enter') { e.preventDefault(); finish(true); }
    if (e.key === 'Escape') { e.preventDefault(); finish(false); }
  };
  box.onclick = function (e) { e.stopPropagation(); };
  box.onblur = function () { finish(true); };
}
function renameAsk(t) {
  modal('Rename', function (body) {
    var name = textBox(t.title, '');
    name.maxLength = 120;
    body._name = name;
    body.appendChild(formField('Its name', name));
    setTimeout(function () { name.focus(); name.select(); }, 30);
    name.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); $('modal-body')._go(); } });
    body._go = function () {
      api('terms', {do: 'rename', id: t.id, title: name.value}).then(function () { closeModal(); loadTerms(TL.open || undefined, true); }).catch(oops);
    };
  }, [{words: 'Cancel', close: true}, {words: 'Rename', cls: 'primary', icon: 'save', go: function () { $('modal-body')._go(); }}]);
}
$('tl-q').addEventListener('input', debounce(drawTermList, 120));
$('tl-show').onchange = drawTermList;
$('tl-new').onclick = function () { newTermAsk('claude'); };
$('te-claude').onclick = function () { newTermAsk('claude'); };
$('te-shell').onclick = function () { newTermAsk('shell'); };
$('te-hist').onclick = function () { showTab('history'); };
/* The right button anywhere on the list of terminals (1.0.11), not only on
   a chat: what can be started from it, and how the list is shown. */
(function () {
  var side = $('term-side');
  var menu = function (x, y) {
    var all = $('tl-show').value === 'all';
    ctxMenu(x, y, [{head: txT('Terminals')},
      {icon: 'terminal', words: 'A new Claude Code…', go: function () { newTermAsk('claude'); }},
      {icon: 'terminal', words: 'A new shell…', go: function () { newTermAsk('shell'); }},
      {icon: 'history', words: 'Pick up a conversation', go: function () { showTab('history'); }},
      'sep',
      {icon: all ? 'eye' : 'list', words: all ? 'Only the running ones' : 'With the ended ones', go: function () {
        $('tl-show').value = all ? 'live' : 'all';
        drawTermList();
      }},
      {icon: 'search', words: 'Find a terminal', go: function () { side.classList.add('open'); $('tl-q').focus(); }},
      endedCount() ? {icon: 'trash', words: 'Take every ended one off the list (' + endedCount() + ')', danger: true, go: forgetEnded} : null,
      narrow() ? null : {icon: 'pin', words: TLR.pinned ? 'Let the list hide itself' : 'Keep the list open', go: function () { pinSide(!TLR.pinned); }},
      {icon: 'refresh', words: 'Read it again', go: function () { loadTerms(); }}]);
  };
  side.addEventListener('contextmenu', function (e) {
    if (e.target.closest('.tl-item, input, select')) return;
    e.preventDefault();
    menu(e.clientX, e.clientY);
  });
  longPress(side, function (x, y, target) { if (!target.closest('.tl-item, input, select')) menu(x, y); });
}());

/* ---- the start, as claude.ai starts (1.0.9): a box to write the task in,
   the folder, the model, the mode and the effort as chips under it, and the
   chats going on below. Enter starts Claude Code on it in that folder. */
var CX = {cwd: '', model: '', mode: '', effort: ''};
function cxWords(list, v) { var x = list.filter(function (o) { return o[0] === v; })[0]; return x ? x[1] : v; }
function cxChip(b, icon, words, title) {
  b.innerHTML = iconMarkup(icon, 14);
  b.appendChild(noI18n(el('span', '', words)));
  var dn = el('span', 'cx-caret', '▾');
  b.appendChild(dn);
  if (title) b.title = title;
}
function cxDraw() {
  var root = (STATUS && STATUS.chat_root) || '';
  if (!CX.cwd) CX.cwd = prefs().last_cwd || root || '';
  if (root && CX.cwd && CX.cwd !== root && CX.cwd.indexOf(root.replace(/\/+$/, '') + '/') !== 0) CX.cwd = root;
  if (!CX._init) {
    CX._init = true;
    CX.model = prefs().model || '';
    CX.mode = prefs().mode || '';
    CX.effort = (prefs().cc_opts || {}).effort || '';
  }
  cxChip($('cx-dir'), 'folder', CX.cwd ? baseName(CX.cwd) : txT('the home folder'), CX.cwd || '');
  cxChip($('cx-model'), 'sparkle', CX.model ? cxWords(MODELS, CX.model) : txT('Model'));
  cxChip($('cx-mode'), 'shield', CX.mode ? cxWords(MODES, CX.mode) : txT('ask before changes'));
  cxChip($('cx-effort'), 'bolt', CX.effort ? txT('effort') + ': ' + CX.effort : txT('effort'));
  var name = (ME && ME.name) || '';
  var h = new Date().getHours();
  $('cx-hello').textContent = txT(h < 11 ? 'Good morning' : (h < 18 ? 'Good afternoon' : 'Good evening')) + (name ? ', ' + name : '');
}
function cxStart() {
  var text = $('cx-text').value.trim();
  var opts = {};
  if (text) opts.prompt = text;
  if (CX.model) opts.model = CX.model;
  if (CX.mode) opts.mode = CX.mode;
  if (CX.effort) opts.effort = CX.effort;
  var title = text ? text.replace(/\s+/g, ' ').slice(0, 48) : '';
  busy($('cx-send'), true);
  startTerm({kind: 'claude', cwd: CX.cwd, title: title, opts: opts, keep: {model: CX.model, mode: CX.mode, args: prefs().args || ''}})
    .then(function (ok) { if (ok) $('cx-text').value = ''; }).then(function () { busy($('cx-send'), false); });
}
(function () {
  $('cx-mark').innerHTML = iconMarkup('sparkle', 30);
  $('cx-send').innerHTML = iconMarkup('up', 18);
  $('cx-send').onclick = cxStart;
  var ta = $('cx-text');
  ta.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); cxStart(); }
  });
  ta.addEventListener('input', function () { ta.style.height = 'auto'; ta.style.height = Math.min(320, ta.scrollHeight + 2) + 'px'; });
  var menu = function (b, list, key) {
    var r = b.getBoundingClientRect();
    ctxMenu(r.left, r.bottom + 4, list.map(function (o) {
      return {icon: CX[key] === o[0] ? 'check' : '', words: o[1], go: function () { CX[key] = o[0]; cxDraw(); }};
    }));
  };
  $('cx-dir').onclick = function () { pickFolder(CX.cwd, function (p) { CX.cwd = p; cxDraw(); }); };
  $('cx-model').onclick = function () { menu($('cx-model'), MODELS, 'model'); };
  $('cx-mode').onclick = function () { menu($('cx-mode'), MODES, 'mode'); };
  $('cx-effort').onclick = function () {
    menu($('cx-effort'), [['', 'as Claude Code decides'], ['low', 'low'], ['medium', 'medium'], ['high', 'high'], ['xhigh', 'extra high'], ['max', 'max']], 'effort');
  };
  $('cx-more').onclick = function () { newTermAsk('claude', CX.cwd); };
}());
function drawTermEmpty() {
  $('term-empty').hidden = false;
  $('term-open').hidden = true;
  $('term-layout').classList.add('at-start');
  cxDraw();
  setTimeout(function () { if (!$('term-empty').hidden && !('ontouchstart' in window)) $('cx-text').focus(); }, 60);
  var host = $('te-recent');
  clear(host);
  /* The folders first (1.0.21): a click there sets where the box above starts, so it belongs next to it. */
  var recent = (prefs().recent || []).slice(0, 8);
  if (recent.length) {
    host.appendChild(el('h3', 'cx-h', 'Folders used lately'));
    var row = el('div', 'cx-folders');
    recent.forEach(function (p) {
      var b = el('button', 'cx-chip');
      b.type = 'button';
      b.innerHTML = iconMarkup('folder', 14);
      b.appendChild(noI18n(el('span', '', baseName(p))));
      b.title = p;
      b.onclick = function () { CX.cwd = p; cxDraw(); $('cx-text').focus(); };
      row.appendChild(b);
    });
    host.appendChild(row);
  }
  var card = function (t) {
    var ended = t.state === 'ended';
    var c = el('button', 'cx-card' + (ended ? ' ended' : ''));
    c.type = 'button';
    var top = el('div', 'cx-card-t');
    top.innerHTML = iconMarkup(t.kind === 'claude' ? 'sparkle' : 'terminal', 14);
    top.appendChild(noI18n(el('span', '', t.title || t.id)));
    if (isPinned(t.id)) { var pi = el('span', 'cx-pin'); pi.innerHTML = iconMarkup('pin', 12); top.appendChild(pi); }
    c.appendChild(top);
    c.appendChild(noI18n(el('div', 'cx-card-p mono', t.cwd || '')));
    var foot = el('div', 'cx-card-f');
    foot.appendChild(el('span', 'tag ' + (t.state === 'running' ? 'ok' : 'dim'), t.state === 'running' ? 'running' : (t.state || '')));
    var when = ended ? (t.ended || t.created) : (t.started || t.created);
    if (when) foot.appendChild(el('span', 'muted small', ago(when)));
    c.appendChild(foot);
    /* An ended one goes on where it stopped, in its own tile (1.0.19). */
    c.onclick = ended ? function () {
      busy(c, true);
      api('terms', {do: 'again', id: t.id}).then(function (d) { loadTerms(d.id); })
        .catch(oops).then(function () { busy(c, false); });
    } : function () { openTerm(t.id); };
    if (ended) c.title = txT('Start it again where it stopped');
    c.addEventListener('contextmenu', function (e) { e.preventDefault(); termMenu(t, e.clientX, e.clientY, null); });
    longPress(c, function (x, y) { termMenu(t, x, y, null); });
    return c;
  };
  var live = TL.terms.filter(function (t) { return t.state !== 'ended'; });
  if (live.length) {
    host.appendChild(el('h3', 'cx-h', 'Going on'));
    var grid = el('div', 'cx-cards');
    live.slice(0, 12).forEach(function (t) { grid.appendChild(card(t)); });
    host.appendChild(grid);
  }
  /* The last few that ended (1.0.19) - the pinned ones first, then the
     newest; the rest under "with the ended ones" in the list. */
  var gone = TL.terms.filter(function (t) { return t.state === 'ended'; });
  if (gone.length) {
    gone.sort(function (a, b) {
      var pa = isPinned(a.id) ? 1 : 0, pb = isPinned(b.id) ? 1 : 0;
      if (pa !== pb) return pb - pa;
      return (b.ended || b.created || 0) - (a.ended || a.created || 0);
    });
    var hh = el('div', 'cx-hrow');
    hh.appendChild(el('h3', 'cx-h', 'Ended lately'));
    if (gone.length > 6) {
      var all = el('a', 'small', txT('all of them') + ' (' + gone.length + ')');
      noI18n(all);
      all.href = '#terms';
      all.onclick = function (e) {
        e.preventDefault();
        $('tl-show').value = 'all'; drawTermList();
        if (!narrow()) { if (!TLR.pinned) pinSide(true); } else sideShow(true);
      };
      hh.appendChild(all);
    }
    host.appendChild(hh);
    var g2 = el('div', 'cx-cards');
    gone.slice(0, 6).forEach(function (t) { g2.appendChild(card(t)); });
    host.appendChild(g2);
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
/* The families (always their newest), then each version by its own name
   (1.0.16) - as claude.ai offers them; --model takes either. */
var MODELS = [['', 'as Claude Code chooses'], ['opus', 'Opus - the newest'], ['sonnet', 'Sonnet - the newest'],
              ['haiku', 'Haiku - the newest'], ['fable', 'Fable - the newest'], ['opusplan', 'Opus to plan, Sonnet to do'],
              ['claude-fable-5-1', 'Fable 5.1'], ['claude-fable-5', 'Fable 5'],
              ['claude-opus-5-5', 'Opus 5.5'], ['claude-opus-5', 'Opus 5'], ['claude-opus-4-8', 'Opus 4.8'],
              ['claude-opus-4-7', 'Opus 4.7'], ['claude-opus-4-6', 'Opus 4.6'],
              ['claude-sonnet-5-5', 'Sonnet 5.5'], ['claude-sonnet-5', 'Sonnet 5'], ['claude-sonnet-4-6', 'Sonnet 4.6'],
              ['claude-haiku-5-5', 'Haiku 5.5'], ['claude-haiku-4-5', 'Haiku 4.5']];
var MODES = [['', 'ask before changes (default)'], ['acceptEdits', 'accept edits by itself'],
             ['plan', 'plan only'], ['auto', 'auto (a classifier decides)'], ['manual', 'manual (ask for everything)'],
             ['dontAsk', 'do not ask (deny what is not allowed)'], ['bypassPermissions', 'never ask (bypass permissions)']];

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
    var root = (STATUS && STATUS.chat_root) || '';
    var inRoot = function (p) { return !root || p === root || String(p || '').indexOf(root.replace(/\/+$/, '') + '/') === 0; };
    var first = cwd || prefs().last_cwd || '';
    var dir = textBox(inRoot(first) && first ? first : (root || first), root || 'the home folder', 'mono');
    var dirWrap = el('div', 'btnrow');
    dir.style.flex = '1';
    dirWrap.appendChild(dir);
    var browse = cmdButton('Choose…', 'archive', 'small');
    browse.onclick = function () { pickFolder(dir.value, function (p) { dir.value = p; }); };
    dirWrap.appendChild(browse);
    var f = formField('The working directory', dirWrap, 'Where it starts. It is made if it is not there yet and the box below says so.');
    f.classList.add('span-2');
    /* Where the folders a chat may start in are limited (1.0.14): said here,
       with the way to the setting - it was not to be found. */
    var lim = el('div', 'small muted dir-limit');
    if (root) lim.appendChild(document.createTextNode(txT('Only in') + ' ' + root + ' ' + txT('and the folders under it.') + ' '));
    else lim.appendChild(document.createTextNode(txT('Anywhere on the server.') + ' '));
    if (ADMIN) {
      var toSet = el('a', '', txT(root ? 'Change it' : 'Limit it to one folder'));
      toSet.href = '#settings/claude';
      toSet.onclick = function (e) {
        e.preventDefault(); closeModal(); showTab('settings', 'claude');
        setTimeout(function () {
          var item = document.querySelector('.set-item[data-key="chat_root"]');
          if (item) { item.scrollIntoView({block: 'center'}); item.classList.remove('found'); void item.offsetWidth; item.classList.add('found'); }
          var box = $('set-chat_root'); if (box && box.focus) box.focus();
        }, 600);
      };
      lim.appendChild(toSet);
    }
    noI18n(lim);
    f.appendChild(lim);
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
    var favs = (prefs().favs || []).concat(prefs().recent || []).filter(function (p, i, a) { return a.indexOf(p) === i && inRoot(p); }).slice(0, 12);
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
    var keep = prefs().cc_opts || {};
    var g2 = el('div', 'formgrid');
    var start = selectBox([['new', 'a new conversation'], ['continue', 'the last conversation of this folder (--continue)'],
                           ['pick', 'choose one of its conversations (--resume)'], ['bg', 'a new one in the background (--bg)']], 'new');
    g2.appendChild(formField('Start with', start));
    var nameBox = textBox('', 'shown in the prompt box and in /resume');
    g2.appendChild(formField('Its name in Claude Code (--name)', nameBox));
    var model = selectBox(MODELS.concat([['*', 'another… (written below)']]), prefs().model || '');
    var modelOwn = textBox('', 'claude-opus-5-5', 'mono');
    noI18n(modelOwn);
    modelOwn.hidden = model.value !== '*';
    model.onchange = function () { modelOwn.hidden = model.value !== '*'; };
    var mw = el('div'); mw.appendChild(model); mw.appendChild(modelOwn);
    g2.appendChild(formField('Model', mw));
    var effort = selectBox([['', 'as Claude Code decides'], ['low', 'low'], ['medium', 'medium'], ['high', 'high'], ['xhigh', 'extra high'], ['max', 'max']], keep.effort || '');
    g2.appendChild(formField('Effort (--effort)', effort));
    var mode = selectBox(MODES, prefs().mode || '');
    g2.appendChild(formField('Permissions', mode, 'Never ask is refused by Claude Code when it runs as root.'));
    var prompt1 = el('textarea');
    prompt1.rows = 3;
    prompt1.placeholder = txT('What it starts on, as though typed first - empty: nothing, it waits for you.');
    var pf = formField('The first message', prompt1);
    pf.classList.add('span-2');
    g2.appendChild(pf);
    claudeBox.appendChild(g2);
    /* Every other option of Claude Code's command line, as fields (1.0.9). */
    var more = el('details', 'cc-more');
    more.appendChild(el('summary', '', 'Every option of Claude Code'));
    var gm = el('div', 'formgrid');
    var F = {};
    var add = function (key, label, box, says, wide) {
      F[key] = box;
      var ff = formField(label, box, says || '');
      if (wide) ff.classList.add('span-2');
      gm.appendChild(ff);
    };
    var text = function (ph, mono) { var b = textBox('', ph || '', mono ? 'mono' : ''); if (mono) noI18n(b); return b; };
    var area = function (ph, rows) { var b = el('textarea', 'mono'); b.rows = rows || 2; b.placeholder = ph || ''; noI18n(b); return b; };
    var flag = function () { return switchBox(false); };
    gm.appendChild(el('h4', 'span-2 cc-h4', 'Tools and permissions'));
    add('allowed_tools', 'Allowed without asking (--allowedTools)', area('Bash(git *)\nEdit'), 'One a line, or with commas.');
    add('disallowed_tools', 'Never (--disallowedTools)', area('Bash(rm *)'), 'One a line, or with commas.');
    add('tools', 'Only these built-in tools (--tools)', text('Bash,Edit,Read', true), 'Empty: all of them; "default": the usual set.');
    add('allow_skip', 'Never asking may be switched on in it', flag(), '--allow-dangerously-skip-permissions');
    gm.appendChild(el('h4', 'span-2 cc-h4', 'What it knows'));
    var dirs = area('/srv/shared\n../other', 2);
    var dirsWrap = el('div');
    dirsWrap.appendChild(dirs);
    var dirPick = cmdButton('Add a folder…', 'folder', 'small');
    dirPick.onclick = function () { pickFolder(dir.value, function (p) { dirs.value = (dirs.value.trim() ? dirs.value.trim() + '\n' : '') + p; }); };
    dirsWrap.appendChild(dirPick);
    add('add_dirs', 'More folders it may use (--add-dir)', dirsWrap, 'One a line.');
    F.add_dirs = dirs;
    add('append_system_prompt', 'Added to its system prompt', area('Answer in Czech. Keep commits small.', 3), '--append-system-prompt', true);
    add('system_prompt', 'Its whole system prompt instead', area('', 2), '--system-prompt: Claude Code\'s own is not used then.', true);
    var agent = selectBox([['', 'none']], keep.agent || '');
    add('agent', 'The agent of the session (--agent)', agent);
    api('cc&what=items&kind=agent&as=' + encodeURIComponent(asSel ? asSel.value : '') + '&project=' + encodeURIComponent(dir.value || '')).then(function (d) {
      (d.items || []).forEach(function (it) { var o = noI18n(el('option', '', it.name + (it.scope === 'project' ? ' (project)' : ''))); o.value = it.name.split('/').pop(); agent.appendChild(o); });
    }).catch(function () { });
    add('mcp_config', 'MCP servers from files (--mcp-config)', area('.mcp.dev.json'), 'One a line: a file or JSON.');
    add('strict_mcp', 'Only those servers', flag(), '--strict-mcp-config');
    add('settings', 'More settings (--settings)', text('a file, or JSON', true));
    add('setting_sources', 'Settings read from (--setting-sources)', text('user,project,local', true));
    add('plugin_dirs', 'Plugins from folders (--plugin-dir)', area('~/my-plugin'), 'For this session only.');
    gm.appendChild(el('h4', 'span-2 cc-h4', 'The session'));
    add('fork', 'Continued as a new conversation', flag(), '--fork-session, with --continue or --resume');
    add('worktree', 'In a new git worktree (--worktree)', text('its name, or empty for one made up', true));
    add('use_worktree', 'Make a worktree', flag());
    add('session_id', 'Its session ID (--session-id)', text('a UUID', true));
    add('autocompact', 'Compacted at (--autocompact)', text('auto, or 100k … 1M', true));
    add('fallback_model', 'When the model is busy (--fallback-model)', text('sonnet,haiku', true));
    add('remote_control', 'Remote Control on, named', text('', true), '--remote-control: the session can be followed from claude.ai.');
    add('use_remote', 'Remote Control', flag());
    gm.appendChild(el('h4', 'span-2 cc-h4', 'How it runs'));
    add('verbose', 'Verbose', flag(), '--verbose');
    add('debug', 'Debug, of what (--debug)', text('hooks,mcp - empty: all', true));
    add('use_debug', 'Debug', flag());
    add('safe_mode', 'Safe mode', flag(), '--safe-mode: CLAUDE.md, hooks, plugins, MCP and the rest of yours switched off');
    add('bare', 'Bare', flag(), '--bare: no hooks, plugins, CLAUDE.md discovery, keychain');
    add('restricted', 'Restricted', flag(), '--restricted: no tools that run code');
    add('chrome', 'Claude in Chrome', selectBox([['', 'as set'], ['on', 'on (--chrome)'], ['off', 'off (--no-chrome)']], ''));
    add('ide', 'Connect to the IDE', flag(), '--ide');
    add('brief', 'Messages to you (SendUserMessage)', flag(), '--brief');
    add('no_slash', 'No skills or /commands', flag(), '--disable-slash-commands');
    add('screen_reader', 'For a screen reader', flag(), '--ax-screen-reader');
    add('exclude_dynamic', 'The machine\'s details in the first message', flag(), '--exclude-dynamic-system-prompt-sections');
    var args = textBox(prefs().args || '', '--verbose, --add-dir ../other…', 'mono');
    add('args', 'More words for its command line', args, 'Anything else claude --help lists, as typed.', true);
    var remember = switchBox(false);
    add('remember', 'Keep these as how my chats start', remember, 'Kept with your account, offered every time.', true);
    more.appendChild(gm);
    claudeBox.appendChild(more);
    /* What was kept as the start of every chat, put back into the boxes. */
    Object.keys(keep).forEach(function (k) {
      var b = F[k];
      if (!b || k === 'remember') return;
      if (b._set) b._set(!!keep[k]); else if (b.tagName === 'SELECT' || b.tagName === 'TEXTAREA' || b.tagName === 'INPUT') b.value = Array.isArray(keep[k]) ? keep[k].join('\n') : String(keep[k]);
    });
    if (keep.worktree !== undefined && F.use_worktree._set) F.use_worktree._set(true);
    claudeBox.hidden = st.kind !== 'claude';
    body.appendChild(claudeBox);
    body._get = function () {
      var opts = {};
      if (start.value === 'continue') opts.continue = true;
      if (start.value === 'pick') opts.pick = true;
      var m = model.value === '*' ? modelOwn.value.trim() : model.value;
      if (m) opts.model = m;
      if (mode.value) opts.mode = mode.value;
      if (effort.value) opts.effort = effort.value;
      if (nameBox.value.trim()) opts.name = nameBox.value.trim();
      if (prompt1.value.trim()) opts.prompt = prompt1.value.trim();
      var cc = {};
      var val = function (k) { var b = F[k]; return b._get ? !!b._get() : String(b.value || '').trim(); };
      ['allowed_tools', 'disallowed_tools', 'tools', 'append_system_prompt', 'system_prompt', 'agent', 'mcp_config', 'settings',
       'setting_sources', 'plugin_dirs', 'session_id', 'autocompact', 'fallback_model'].forEach(function (k) { if (val(k)) cc[k] = val(k); });
      ['allow_skip', 'strict_mcp', 'fork', 'verbose', 'safe_mode', 'bare', 'restricted', 'ide', 'brief', 'no_slash', 'screen_reader', 'exclude_dynamic']
        .forEach(function (k) { if (val(k)) cc[k] = true; });
      if (val('use_worktree')) cc.worktree = val('worktree') || true;
      if (val('use_debug')) cc.debug = val('debug') || true;
      if (val('use_remote')) cc.remote_control = val('remote_control') || true;
      if (F.chrome.value === 'on') cc.chrome = true;
      if (F.chrome.value === 'off') cc.no_chrome = true;
      if (val('add_dirs')) opts.add_dirs = val('add_dirs').split('\n').map(function (x) { return x.trim(); }).filter(Boolean);
      Object.assign(opts, cc);
      if (args.value.trim()) opts.args = args.value.trim();
      if (start.value === 'bg') opts.args = ((opts.args || '') + ' --bg').trim();
      if (mk._get()) opts.mkdir = true;
      var keepNow = null;
      if (remember._get()) { keepNow = Object.assign({}, cc); if (effort.value) keepNow.effort = effort.value; }
      return {kind: st.kind, cwd: dir.value.trim(), title: title.value.trim(), opts: opts,
              run_as: asSel ? asSel.value : '', keep: {model: m, mode: mode.value, args: args.value.trim()}, ccKeep: keepNow};
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
    if (want.ccKeep) p.cc_opts = want.ccKeep;
    savePrefs(p).catch(function () { });
    if (TAB !== 'terms') showTab('terms');
    return loadTerms(d.id).then(function () { return true; });
  }).catch(function (e) { oops(e); return false; });
}

/* ---- a folder, chosen (1.0.9) ------------------------------------------------------
   Its folders and files, from the folder of the chats down (Settings -
   Claude Code), never above it; folders and files made, renamed and deleted
   here - by the buttons, the right mouse button, or a finger held still on a
   tablet - and the folder shown chosen. */
function pickFolder(start, then) {
  var root = (STATUS && STATUS.chat_root) || '';
  var st = {path: start || root || '', d: null};
  var under = function (p) { return !root || p === root || String(p).indexOf(root.replace(/\/+$/, '') + '/') === 0; };
  if (root && !under(st.path)) st.path = root;
  /* Over the dialog it was asked from (1.0.14): Close goes back to that one. */
  modalOver(function () { pickFolderModal(root, st, under, then); });
}
function pickFolderModal(root, st, under, then) {
  modal(root ? 'Choose a folder in ' + baseName(root) : 'Choose a folder', function (body) {
    var bar = el('div', 'btnrow pick-bar');
    var up = cmdButton('Up', 'up', 'small');
    var path = textBox('', '', 'mono');
    path.style.flex = '1';
    noI18n(path);
    var mk = cmdButton('New folder', 'add', 'small');
    var mkf = cmdButton('New file', 'edit', 'small');
    var again = iconButton('refresh', 'Read the folder again');
    [up, path, mk, mkf, again].forEach(function (x) { bar.appendChild(x); });
    body.appendChild(bar);
    if (root) body.appendChild(el('p', 'muted small', 'Only ' + root + ' and what is under it (Settings - Claude Code - The folder of the chats).'));
    var ask = el('div', 'pick-ask');
    ask.hidden = true;
    body.appendChild(ask);
    var list = el('div', 'pick-list');
    body.appendChild(list);
    var said = el('p', 'muted small pick-said');
    body.appendChild(said);
    var op = function (what, extra) {
      return filesApi('op', '', Object.assign({op: what, root: root || undefined}, extra));
    };
    /* A name asked for in the picker itself, not in a popup over it. */
    var askName = function (words, value, go) {
      clear(ask);
      ask.hidden = false;
      ask.appendChild(el('span', 'small', words));
      var box = textBox(value || '', '', 'mono');
      noI18n(box);
      box.style.flex = '1';
      ask.appendChild(box);
      var ok = cmdButton('OK', 'check', 'small primary');
      var no = cmdButton('Cancel', 'close', 'small');
      ask.appendChild(ok);
      ask.appendChild(no);
      var done = function () { ask.hidden = true; clear(ask); };
      ok.onclick = function () {
        var v = box.value.trim();
        if (!v) { box.focus(); return; }
        go(v).then(done).catch(oops);
      };
      no.onclick = done;
      box.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); ok.click(); }
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); done(); }
      });
      setTimeout(function () { box.focus(); if (value) box.setSelectionRange(0, value.replace(/\.[^.]*$/, '').length || value.length); }, 30);
    };
    var newFolder = function (inside) {
      askName('A new folder in ' + baseName(inside) + ':', '', function (name) {
        return op('mkdir', {path: inside, name: name}).then(function (d) { toast('made: ' + d.path, 'good'); go(inside === st.path ? st.path : inside); });
      });
    };
    var newFile = function (inside) {
      askName('A new file in ' + baseName(inside) + ':', '', function (name) {
        return op('touch', {path: inside, name: name}).then(function (d) { toast('made: ' + d.path, 'good'); go(inside); });
      });
    };
    var rename = function (full, name) {
      askName('A new name for ' + name + ':', name, function (v) {
        return op('rename', {path: full, name: v}).then(function () { go(st.path); });
      });
    };
    var remove = function (full, e) {
      modalOver(function () {
        confirmThen(e.kind === 'dir' ? 'Delete the folder ' + e.name + '?' : 'Delete ' + e.name + '?',
          htmlText(full) + (e.kind === 'dir' ? '<br>' + htmlText(txT('With everything in it. It cannot be undone.')) : '<br>' + htmlText(txT('It cannot be undone.'))),
          'Delete it', function () {
            op('delete', {path: full}).then(function () { toast('deleted: ' + full, 'good'); go(st.path); }).catch(oops);
          }, true);
      });
    };
    var rowMenu = function (e, x, y) {
      var full = pathJoin(st.path, e.name);
      var dir = e.kind === 'dir';
      ctxMenu(x, y, [{head: e.name}].concat(dir ? [
        {icon: 'archive', words: 'Open it', go: function () { go(full); }},
        {icon: 'check', words: 'Choose this folder', go: function () { closeModal(); then(full); }},
        'sep',
        {icon: 'add', words: 'A new folder in it…', go: function () { newFolder(full); }},
        {icon: 'edit', words: 'A new file in it…', go: function () { newFile(full); }}
      ] : [
        {icon: 'download', words: 'Download it', go: function () { download(full); }}
      ]).concat(['sep',
        {icon: 'edit', words: 'Rename…', go: function () { rename(full, e.name); }},
        {icon: 'trash', words: 'Delete…', danger: true, go: function () { remove(full, e); }}
      ]));
    };
    var hereMenu = function (x, y) {
      ctxMenu(x, y, [{head: baseName(st.path)},
        {icon: 'check', words: 'Choose this folder', go: function () { closeModal(); then(st.path); }},
        {icon: 'add', words: 'A new folder here…', go: function () { newFolder(st.path); }},
        {icon: 'edit', words: 'A new file here…', go: function () { newFile(st.path); }},
        {icon: 'refresh', words: 'Read it again', go: function () { go(st.path); }}]);
    };
    var go = function (p) {
      var q = 'hidden=0&path=' + encodeURIComponent(p || '') + (root ? '&root=' + encodeURIComponent(root) : '');
      return filesApi('list', q).then(function (d) {
        st.path = d.path;
        st.d = d;
        path.value = d.path;
        up.disabled = !d.up || (root && !under(d.up));
        up.onclick = function () { go(d.up); };
        clear(list);
        var ents = d.entries.filter(function (e) { return e.kind === 'dir'; })
          .concat(d.entries.filter(function (e) { return e.kind !== 'dir'; }));
        if (!ents.length) list.appendChild(el('p', 'muted small', 'Nothing in it yet.'));
        ents.forEach(function (e) {
          var dir = e.kind === 'dir';
          var b = el('div', 'pick-row' + (dir ? '' : ' file'));
          b.tabIndex = 0;
          b.innerHTML = iconMarkup(dir ? 'folder' : 'file', 15);
          b.appendChild(noI18n(el('span', 'pick-name', e.name)));
          if (!dir && e.size !== undefined) b.appendChild(el('span', 'muted small', bytes(e.size)));
          var more = iconButton('more', 'What can be done with it');
          more.classList.add('pick-more');
          more.onclick = function (ev) { ev.stopPropagation(); var r = more.getBoundingClientRect(); rowMenu(e, r.left, r.bottom); };
          b.appendChild(more);
          b.onclick = function () { if (dir) go(pathJoin(d.path, e.name)); };
          b.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && dir) go(pathJoin(d.path, e.name)); });
          b.addEventListener('contextmenu', function (ev) { ev.preventDefault(); ev.stopPropagation(); rowMenu(e, ev.clientX, ev.clientY); });
          longPress(b, function (x, y) { rowMenu(e, x, y); });
          list.appendChild(b);
        });
        said.textContent = num(ents.filter(function (e) { return e.kind === 'dir'; }).length) + ' ' + txT('folder(s)') + ' · '
          + num(ents.filter(function (e) { return e.kind !== 'dir'; }).length) + ' ' + txT('file(s)');
      }).catch(function (e) { oops(e); if (root && p !== root) go(root); });
    };
    list.addEventListener('contextmenu', function (ev) {
      if (ev.target.closest('.pick-row')) return;
      ev.preventDefault();
      hereMenu(ev.clientX, ev.clientY);
    });
    path.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      if (root && !under(path.value.trim())) { toast('only ' + root + ' and what is under it', 'bad'); path.value = st.path; return; }
      go(path.value.trim());
    });
    mk.onclick = function () { newFolder(st.path); };
    mkf.onclick = function () { newFile(st.path); };
    again.onclick = function () { go(st.path); };
    go(st.path);
  }, [{words: 'Close', close: true},
      {words: 'Choose this one', cls: 'primary', icon: 'check', go: function () { closeModal(); then(st.path); }}], 'medium');
}

/* ---- the one open ---------------------------------------------------------------- */
function openTerm(id) {
  var t = TL.terms.filter(function (x) { return x.id === id; })[0];
  if (!t) return;
  TL.open = id;
  $('term-layout').classList.remove('at-start');
  $('term-empty').hidden = true;
  $('term-open').hidden = false;
  $('term-gone').hidden = true;
  paintTermBar(t);
  drawTermList();
  drawKeys();
  writeHash();
  if (!$('term-files').hidden && CF.t && CF.t.id !== id) chatFiles(t, true);
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
/* Close (1.0.16): the window only, back to the start page - nothing is ended. */
$('tb-close').onclick = function () { closeTermView(); loadTerms(); };
function closeTermView() {
  if (TL.pure) termPure(false);
  termClose();
  $('term-files').hidden = true;
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
/* The list of terminals as otp's settings rail (1.0.5): a strip of icons at
   the edge that slides out when pointed at, and stays out once pinned. On a
   phone the list and the terminal take the screen in turn, as before. */
var TLR = {pinned: false, open: null, shut: null};
function narrow() { return window.matchMedia && window.matchMedia('(max-width: 900px)').matches; }
function pinSide(on) {
  TLR.pinned = !!on;
  var side = $('term-side'), pin = $('tl-pin');
  side.classList.toggle('pinned', TLR.pinned);
  $('term-layout').classList.toggle('side-pinned', TLR.pinned);
  pin.setAttribute('aria-pressed', TLR.pinned ? 'true' : 'false');
  explain(pin, TLR.pinned ? 'The list is staying open. Press again to let it hide itself at the edge of the screen.'
    : 'The list hides itself at the edge of the screen and slides out when you point at it. Press this to keep it open.');
  try { localStorage.setItem('ai-tl-pinned', TLR.pinned ? '1' : '0'); } catch (e) { }
  setTimeout(termFit, 200);
}
(function sideRail() {
  var side = $('term-side'), pin = $('tl-pin');
  pin.innerHTML = iconMarkup('pin', 17);
  pin.onclick = function (e) { e.stopPropagation(); pinSide(!TLR.pinned); };
  side.addEventListener('mouseenter', function () {
    if (narrow()) return;
    clearTimeout(TLR.shut);
    TLR.open = setTimeout(function () { side.classList.add('open'); }, 60);
  });
  side.addEventListener('mouseleave', function () {
    clearTimeout(TLR.open);
    TLR.shut = setTimeout(function () {
      if (CTX.el || (document.activeElement && side.contains(document.activeElement) && document.activeElement.tagName === 'INPUT')) return;
      side.classList.remove('open');
    }, 260);
  });
  var was = '0';
  try { was = localStorage.getItem('ai-tl-pinned') || '0'; } catch (e) { }
  pinSide(was === '1');
}());
$('tb-side').onclick = function () { if (narrow()) sideShow(!TL.side); else pinSide(!TLR.pinned); };
$('tb-font-').onclick = function () { termSetFont((TERM.t ? TERM.t.options.fontSize : 14) - 1); };
$('tb-font+').onclick = function () { termSetFont((TERM.t ? TERM.t.options.fontSize : 14) + 1); };
$('tb-full').onclick = function () {
  TL.full = !TL.full;
  document.body.classList.toggle('term-full', TL.full);
  setTimeout(termFit, 50);
};
/* Only the terminal, over the whole screen (1.0.20): the browser's full
   screen for the terminal's own box - nothing else of the page shows. With
   the keys locked (Chrome, Edge) Esc goes to the terminal and is held to
   come out; where an element cannot take the screen (an iPhone), the box
   covers the whole window instead and Esc twice comes out. */
function termPure(on) {
  var host = $('term-host');
  TL.pure = !!on;
  var x = host.querySelector('.term-pure-x');
  if (!x) {
    x = el('button', 'term-pure-x');
    x.type = 'button';
    x.innerHTML = iconMarkup('close', 16);
    x.setAttribute('aria-label', 'Back from the whole screen');
    x.title = txT('Back from the whole screen');
    x.onclick = function (e) { e.stopPropagation(); termPure(false); };
    host.appendChild(x);
    host.addEventListener('mousemove', function () {
      if (!TL.pure) return;
      x.classList.add('shown');
      clearTimeout(TL.pureX);
      TL.pureX = setTimeout(function () { x.classList.remove('shown'); }, 1800);
    });
  }
  if (on) {
    var req = host.requestFullscreen || host.webkitRequestFullscreen;
    var fallback = function () { host.classList.add('pure'); };
    if (req) {
      try {
        Promise.resolve(req.call(host)).then(function () {
          if (navigator.keyboard && navigator.keyboard.lock) return navigator.keyboard.lock().catch(function () { });
        }).catch(fallback);
      } catch (e) { fallback(); }
    } else fallback();
  } else {
    try { if (navigator.keyboard && navigator.keyboard.unlock) navigator.keyboard.unlock(); } catch (e) { }
    var fs = document.fullscreenElement || document.webkitFullscreenElement;
    if (fs === host) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    host.classList.remove('pure');
  }
  setTimeout(function () { termFit(); if (TERM.t) TERM.t.focus(); }, 150);
}
$('tb-pure').onclick = function () { termPure(true); };
['fullscreenchange', 'webkitfullscreenchange'].forEach(function (ev) {
  document.addEventListener(ev, function () {
    var host = $('term-host');
    if (TL.pure && !(document.fullscreenElement || document.webkitFullscreenElement) && !host.classList.contains('pure')) termPure(false);
  });
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && TL.pure && $('term-host').classList.contains('pure')) {
    var at = Date.now();
    if (TL.pureEsc && at - TL.pureEsc < 400) termPure(false);
    TL.pureEsc = at;
  }
}, true);
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
$('tb-history').onclick = function () { var t = termById(TL.open); if (t) termHistory(t); };
$('tb-files').onclick = function () {
  var t = TL.terms.filter(function (x) { return x.id === TL.open; })[0];
  if (!t) return;
  if (!$('term-files').hidden && CF.t && CF.t.id === t.id) chatFiles(t, false); else chatFiles(t, true);
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
    var ps = el('div', 'me-sec');
    ps.appendChild(el('h3', '', 'Colours of the terminals'));
    ps.appendChild(termPalettePicker());
    body.appendChild(ps);
  }, [{words: 'End it', cls: 'danger', icon: 'power', go: function () {
        api('terms', {do: 'kill', id: t.id}).then(function () { closeModal(); closeTermView(); loadTerms(); }).catch(oops);
      }},
      {words: 'Start it again', icon: 'refresh', go: function () {
        api('terms', {do: 'restart', id: t.id}).then(function () { closeModal(); termOpen(t.id, $('term-host'), TERM.onState); }).catch(oops);
      }},
      {words: 'Change it…', icon: 'gear', go: function () { termEdit(t); }},
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
    tr.addEventListener('contextmenu', function (ev) { ev.preventDefault(); ev.stopPropagation(); flMenu(e, full, ev.clientX, ev.clientY, tr); });
    longPress(tr, function (x, y) { flMenu(e, full, x, y, tr); });
    return tr;
  }, 'plain|An empty folder'));
  explainWhatWasDrawn(host);
}
/* The right button on a file or a folder (1.0.10): everything that can be
   done with it, as in the files beside a chat. */
function flMenu(e, full, x, y, row) {
  var dir = e.kind === 'dir';
  var here = FL.path;
  ctxMenu(x, y, [
    {head: e.name},
    dir ? {icon: 'folder', words: 'Open the folder', go: function () { loadFiles(full); }}
        : {icon: 'eye', words: 'Open it', go: function () { openFile(full, e); }},
    dir ? {icon: 'terminal', words: 'A new Claude Code in it', go: function () { newTermAsk('claude', full); }} : null,
    {icon: 'copy', words: 'Copy its path', go: function () { copyText2(full); }},
    dir ? {icon: 'add', words: 'A new folder in it…', go: function () { flNew('mkdir', full); }} : null,
    dir ? {icon: 'file', words: 'A new file in it…', go: function () { flNew('touch', full); }} : null,
    'sep',
    {icon: 'download', words: dir ? 'Download it as a .zip' : 'Download it', go: function () { download(full); }},
    {icon: 'edit', words: 'Rename', go: function () {
      var name = prompt('A new name for ' + e.name, e.name);
      if (!name || name === e.name) return;
      filesApi('op', '', {op: 'rename', path: full, name: name}).then(function () { loadFiles(here); }).catch(oops);
    }},
    'sep',
    {icon: 'trash', words: 'Delete', danger: true, go: function () {
      confirmThen('Take ' + e.name + ' away?', (dir ? 'The folder <b>' + htmlText(e.name) + '</b> and everything in it are' : '<b>' + htmlText(e.name) + '</b> is') + ' deleted from the server. There is no bin.', 'Delete it', function () {
        filesApi('op', '', {op: 'delete', path: full}).then(function () { loadFiles(here); }).catch(oops);
      });
    }}
  ], row);
}
function flNew(what, inside) {
  var name = prompt(txT(what === 'mkdir' ? 'The name of the new folder' : 'The name of the new file'));
  if (!name) return;
  filesApi('op', '', {op: what, path: inside, name: name}).then(function () { loadFiles(FL.path); }).catch(oops);
}
/* ...and on the list where there is no row: what can be made in the folder shown. */
(function () {
  var host = $('fl-host').closest('.card') || $('fl-host');
  var here = function (x, y) {
    ctxMenu(x, y, [{head: FL.path || '/'},
      {icon: 'add', words: 'A new folder here…', go: function () { flNew('mkdir', FL.path); }},
      {icon: 'file', words: 'A new file here…', go: function () { flNew('touch', FL.path); }},
      {icon: 'upload', words: 'Upload files here…', go: function () { $('fl-input').click(); }},
      {icon: 'terminal', words: 'A new Claude Code here', go: function () { newTermAsk('claude', FL.path); }},
      {icon: 'copy', words: 'Copy its path', go: function () { copyText2(FL.path); }},
      'sep',
      {icon: 'refresh', words: 'Read it again', go: function () { loadFiles(FL.path); }}]);
  };
  host.addEventListener('contextmenu', function (ev) {
    if (ev.target.closest('tr.clickable, button, a, input, select, textarea, label')) return;
    ev.preventDefault();
    here(ev.clientX, ev.clientY);
  });
  longPress(host, function (x, y, target) { if (!target.closest('tr.clickable, button, a, input, select, textarea, label')) here(x, y); });
}());
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
    /* The folder and its git branch side by side (1.0.18): the branch's tag lay over the folder's name. */
    var f = noI18n(el('td', 'hi-folder'));
    f.appendChild(el('span', 'mono small hi-path', it.cwd || '?'));
    if (it.branch) { var br = el('span', 'tag dim hi-branch', it.branch); br.title = 'git branch ' + it.branch; f.appendChild(br); }
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
/* Two parts (1.0.24): the server, and Claude Code's chats with all their
   figures - each its own address, #overview and #overview/claude. */
var OV = {part: 'server'};
function ovPart(part) {
  OV.part = part === 'claude' ? 'claude' : 'server';
  document.querySelectorAll('#ov-seg button').forEach(function (b) { b.classList.toggle('on', b.dataset.ov === OV.part); });
  $('ov-server').hidden = OV.part !== 'server';
  $('ov-usage').hidden = OV.part !== 'claude';
  writeHash();
}
document.querySelectorAll('#ov-seg button').forEach(function (b) {
  b.onclick = function () { ovPart(b.dataset.ov); loadOverview(); };
});
function loadOverview(sub) {
  if (sub !== undefined) ovPart(sub);
  if (OV.part === 'claude') { if (typeof loadUsage === 'function') loadUsage(); return; }
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
  if (name === 'people') { loadUsers(); loadLockouts(); colsCardSay(); }
  if (name === 'mail') loadMail();
  if (name === 'texts') loadTexts();
  if (name === 'mailq') loadMailq();
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
  if (name === 'signin') loadArt();
  if (name === 'acme') loadAcme(); else if (typeof acPoll === 'function') acPoll(false);
  if (name === 'proxy' && typeof drawProxy === 'function') drawProxy();
  if (name === 'about') { loadAbout(); loadConsoleLogin(); loadSoftware(); }
  markDirtyCount();
}
document.querySelectorAll('#ctl-nav button[data-pane]').forEach(function (b) {
  b.onclick = function () { showPane(b.dataset.pane); };
});
function pinRail(on) {
  RAIL.pinned = !!on;
  var nav = $('ctl-nav'), pin = $('ctl-pin');
  nav.classList.toggle('pinned', RAIL.pinned);
  /* The settings' own layout (1.0.11): the first .ctl-layout of the page is
     the Claude Code tab's, and pinning moved that one aside instead. */
  nav.closest('.ctl-layout').classList.toggle('nav-pinned', RAIL.pinned);
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
  var was = '0';
  try { was = localStorage.getItem('ai-rail-pinned') || '0'; } catch (e) { }
  pinRail(was === '1');
}());

/* ---- the settings: exactly otp's (admin.js 1.0.161) ----------------------------------- */
$('ctl-find').addEventListener('input', function () {
  var want = $('ctl-find').value.trim().toLowerCase();
  var box = $('ctl-found');
  clear(box);
  if (!want || !SETTINGS) { box.hidden = true; return; }
  // In the page's language as well (1.0.61): a word seen on screen in Czech
  // found nothing.
  var tr = function (x) {
    try { return (typeof i18nText === 'function' && x) ? (i18nText(x) || '') : ''; } catch (e) { return ''; }
  };
  var hits = SETTINGS.settings.filter(function (s) {
    return (s.name + ' ' + s.key + ' ' + s.says + ' ' + tr(s.name) + ' ' + tr(s.says))
      .toLowerCase().indexOf(want) >= 0;
  }).slice(0, 12);
  if (!hits.length) box.appendChild(el('div', 'ctl-none', 'Nothing by that name'));
  hits.forEach(function (s) {
    var b = el('button', 'ctl-hit');
    b.type = 'button';
    b.appendChild(el('span', 'ctl-hit-t', s.name));
    var pane = Object.keys(SETTINGS.panes).filter(function (p) { return SETTINGS.panes[p].indexOf(s.key) >= 0; })[0];
    var where = document.querySelector('.ctl-nav [data-pane="' + (pane || 'about') + '"]');
    b.appendChild(el('span', 'ctl-hit-w', where ? where.textContent.trim() : (pane || '')));
    b.onclick = function () {
      showPane(pane || 'about');
      $('ctl-find').value = '';
      box.hidden = true;
      var item = document.querySelector('.set-item[data-key="' + s.key + '"]');
      if (item) {
        item.scrollIntoView({block: 'center'});
        item.classList.remove('found');
        void item.offsetWidth;
        item.classList.add('found');
        item.addEventListener('animationend', function () { item.classList.remove('found'); }, {once: true});
      }
    };
    box.appendChild(b);
  });
  box.hidden = !hits.length;
});

function loadSettings(redraw) {
  api('settings').then(function (d) {
    SETTINGS = d;
    /* Another node answers than the one that drew the boxes (1.0.110): the
       web address moved. Measured against that node, its own settings looked
       changed - otp1 took the name otp2 from a page otp2 had drawn. Drawn
       again from the node answering now; what was typed and not saved is put
       aside, said so. */
    if (DRAWN_NODE && d.node && d.node !== DRAWN_NODE) {
      var aside = Object.keys(DIRTY).length;
      toast('this page is answered by ' + d.node + ' now, not ' + DRAWN_NODE + ' (the web address moved): the settings are drawn again from ' + d.node
        + (aside ? '; ' + aside + ' change(s) not saved were put aside' : ''), 'warn');
      DIRTY = {};
      drawSettings(); markDirtyCount();
      var hh = (location.hash || '').split('/');
      showPane(PANE || (hh[1] || 'claude'));
      return;
    }
    /* Typed while this was on its way (1.0.94): kept, not wiped by a redraw;
       the boxes are measured against what is saved now instead. */
    if (redraw !== false && !Object.keys(DIRTY).length) { drawSettings(); markDirtyCount(); }
    else {
      document.querySelectorAll('.set-item[data-key]').forEach(function (item) {
        var st = settingByKey(item.dataset.key);
        if (st && $('set-' + st.key)) markDirty(item, st);
      });
    }
    var h = (location.hash || '').split('/');
    if (redraw !== false) { /* the pane drawn already */ }
  }).catch(oops);
}
function settingByKey(key) {
  return ((SETTINGS && SETTINGS.settings) || []).filter(function (s) { return s.key === key; })[0];
}
function isBool(s) {
  return typeof s.default === 'boolean' || (s.min === 0 && s.max === 1 && typeof s.default === 'number');
}
var TALL = {sms_body: 1, sms_headers: 1, claude_env: 1};

/* A pane drawn in sections (1.0.88): what belongs together side by side,
   and what only one choice uses in a panel of its own that is there only
   while that choice is made - not a page of greyed-out boxes. */
var PANE_LAYOUT = {
  codes: [
    {title: 'The codes', icon: 'token', cols: 5, keys: ['code_digits', 'code_ttl_s', 'code_tries', 'code_send_max', 'code_send_window_min']},
    {title: 'What they say', icon: 'globe', keys: ['code_lang', 'code_mail_fmt'], wide: {code_lang: 2, code_mail_fmt: 2}},
    {title: 'SMS', icon: 'phone', keys: ['sms_mode', 'sms_prefix', 'sms_plain'], wide: {sms_mode: 2},
     master: 'sms_mode', subs: [
       {when: 'teltonika', title: 'The Teltonika gateway', icon: 'router',
        lede: 'TRB140, RUT… on the network: sent through its own API, the way zigmon sends its texts.',
        keys: ['sms_tel_host', 'sms_tel_api', 'sms_tel_modem', 'sms_tel_https', 'sms_tel_user', 'sms_tel_password', 'sms_tel_verify'],
        extra: smsTelExtra},
       {when: 'http', title: 'An HTTP gateway', icon: 'net',
        lede: 'An operator’s or a service’s HTTP API: where, how, with what key, and what it answers when a text went.',
        keys: ['sms_url', 'sms_method', 'sms_token', 'sms_ok_status', 'sms_body', 'sms_headers'], wide: {sms_url: 3, sms_token: 2, sms_ok_status: 2}},
       {when: 'spool', title: 'A modem on this machine', icon: 'terminal',
        lede: 'smstools3 or gammu-smsd: every text a file in their spool folder, sent by their own daemon.',
        keys: ['sms_spool_dir'], wide: {sms_spool_dir: 2}},
       {when: 'off', note: 'SMS is off: codes by SMS cannot be chosen on the enrolment pages, and the realms do not offer them.'}]}
  ]
};
function layoutGrid(keys, wide, shown, cols) {
  var g = el('div', 'set-grid cols-' + (cols || 4));
  keys.forEach(function (key) {
    var s = settingByKey(key);
    if (!s) return;
    shown[key] = true;
    var it = settingItem(s);
    if (wide && wide[key] && !it.classList.contains('tall')) it.classList.add('span-' + wide[key]);
    g.appendChild(it);
  });
  return g;
}
function drawLaidOut(host, pane, shown) {
  var head = function (tag, sec) {
    var h = el(tag, 'set-sec-head');
    if (sec.icon) { var i = el('span', 'set-sec-icon'); i.innerHTML = iconMarkup(sec.icon, 15); h.appendChild(i); }
    h.appendChild(el('span', '', sec.title));
    return h;
  };
  PANE_LAYOUT[pane].forEach(function (sec) {
    var box = el('section', 'set-sec');
    box.appendChild(head('h3', sec));
    box.appendChild(layoutGrid(sec.keys, sec.wide, shown, sec.cols));
    (sec.subs || []).forEach(function (sub) {
      var p = el('div', 'set-sub');
      p.dataset.master = sec.master;
      p.dataset.when = sub.when;
      if (sub.note) {
        p.classList.add('set-sub-note');
        p.appendChild(el('div', 'says', sub.note));
      } else {
        p.appendChild(head('h4', sub));
        if (sub.lede) p.appendChild(el('div', 'says set-sub-lede', sub.lede));
        p.appendChild(layoutGrid(sub.keys, sub.wide, shown));
        if (sub.extra) p.appendChild(sub.extra());
      }
      box.appendChild(p);
    });
    host.appendChild(box);
  });
  /* Anything of the pane the layout does not name still shows, at the end. */
  var left = SETTINGS.panes[pane].filter(function (k) { return !shown[k] && settingByKey(k); });
  if (left.length) {
    var box = el('section', 'set-sec');
    box.appendChild(layoutGrid(left, null, shown));
    host.appendChild(box);
  }
}
function applySubs() {
  var val = function (key) {
    var m = $('set-' + key);
    return m ? String(m._get ? m._get() : m.value) : '';
  };
  document.querySelectorAll('.set-sub[data-master]').forEach(function (p) {
    p.hidden = val(p.dataset.master) !== p.dataset.when;
  });
  /* The gateway's certificates: there while its certificate is checked. */
  var ca = $('smsca');
  if (ca) {
    var on = function (k) { var v = val(k); return v === 'true' || v === '1'; };
    ca.hidden = !(on('sms_tel_verify') && on('sms_tel_https'));
    /* Said plainly when nothing checks who answers (1.0.101): the gateway's
       password and every code sent go to whoever is in between. */
    var warn = $('smsca-warn');
    if (!warn && ca.parentNode) {
      warn = el('div', 'note warn sms-warn');
      warn.id = 'smsca-warn';
      ca.parentNode.insertBefore(warn, ca);
    }
    if (warn) {
      var mode = val('sms_mode');
      var https = on('sms_tel_https'), verify = on('sms_tel_verify');
      warn.hidden = mode !== 'teltonika' || (https && verify);
      warn.textContent = !https
        ? 'Without HTTPS the gateway’s password and every code sent cross the network as they are: anybody on the way reads them.'
        : 'The gateway’s certificate is not checked: anybody between this server and the gateway can stand in for it and read its password and every code sent. Switch the check on and read its certificate from it below.';
    }
  }
}

/* Try the gateway (1.0.113): reached, signed in, its modems and what each
   says about the network - nothing is sent. With what is saved: changes not
   saved yet are asked to be saved first. */
function smsTelExtra() {
  var f = document.createDocumentFragment();
  var box = el('div', 'set-ca tel-test');
  var head = el('div', 'set-ca-head');
  var hi = el('span', 'set-sec-icon'); hi.innerHTML = iconMarkup('pulse', 15);
  head.appendChild(hi);
  head.appendChild(el('b', '', 'Is it talking to us?'));
  var go = cmdButton('Test the connection', 'play', 'small admin-only');
  go.classList.add('right');
  head.appendChild(go);
  box.appendChild(head);
  box.appendChild(el('div', 'says set-sub-lede', 'Signs in to the gateway with what is saved above and asks how its modems are - operator, signal, SIM. Nothing is sent; a test SMS goes from a token’s card.'));
  var out = el('div', 'tel-out');
  box.appendChild(out);
  go.onclick = function () {
    var unsaved = Object.keys(DIRTY).filter(function (k) { return /^sms_/.test(k); });
    if (unsaved.length) { toast('save the changes first - the test uses what is saved', 'warn'); return; }
    busy(go, true);
    clear(out);
    out.appendChild(el('p', 'note', 'Asking the gateway…'));
    api('mail', {action: 'tel_test'}).then(function (d) {
      busy(go, false);
      clear(out);
      var steps = el('div', 'tel-steps');
      (d.steps || []).forEach(function (st) {
        var r = el('div', 'tel-step ' + (st.ok ? 'good' : 'bad'));
        r.appendChild(el('span', 'tel-mark', st.ok ? '✓' : '✗'));
        r.appendChild(el('b', '', st.what));
        if (st.secs) r.appendChild(noI18n(el('span', 'muted small', ' ' + String(st.secs).replace('.', numLang() === 'cs' ? ',' : '.') + ' s')));
        if (st.said) {
          r.appendChild(document.createTextNode(' – '));
          r.appendChild(el('span', 'small' + (st.ok ? ' muted' : ' bad'), st.said));
        }
        steps.appendChild(r);
      });
      out.appendChild(steps);
      (d.modems || []).forEach(function (m) {
        var card = el('div', 'tel-modem' + (m.sends ? ' sends' : ''));
        var t = el('div', 'tel-modem-head');
        t.appendChild(noI18n(el('b', 'mono', m.id || '?')));
        if (m.sends) t.appendChild(el('span', 'tag ok', 'sends the codes'));
        card.appendChild(t);
        var dl = el('dl', 'tel-facts');
        (m.fields || []).forEach(function (kv) {
          if (kv[0] === 'id') return;
          var one = el('div', 'tel-fact');
          one.appendChild(el('dt', '', kv[0]));
          one.appendChild(noI18n(el('dd', 'mono', kv[1])));
          dl.appendChild(one);
        });
        card.appendChild(dl);
        out.appendChild(card);
      });
      out.appendChild(el('p', 'note small ' + (d.ok ? (d.checked ? 'good' : 'warn') : 'bad'), d.ok
        ? 'The gateway answers' + (d.checked ? ', its certificate checked' : (d.https ? ' - its certificate NOT checked' : ' - over plain HTTP')) + ' (' + num(d.took_ms) + ' ms).'
        : 'The gateway cannot send codes like this - see the step marked ✗.'));
      out.appendChild(hideBar(function () { clear(out); }));
    }).catch(function (e) { busy(go, false); clear(out); oops(e); });
  };
  f.appendChild(box);
  f.appendChild(smsCaBlock());
  return f;
}

/* The certificates the Teltonika gateway is checked against (1.0.89): its
   own, read from it with a click, or the authority and chain that signed
   it - pasted or read from a file, added with Save the changes. */
function smsCaBlock() {
  var box = el('div', 'set-ca');
  box.id = 'smsca';
  var head = el('div', 'set-ca-head');
  var hi = el('span', 'set-sec-icon'); hi.innerHTML = iconMarkup('shield', 15);
  head.appendChild(hi);
  head.appendChild(el('b', '', 'The certificates it is checked against'));
  var when = el('span', 'muted small right', '');
  head.appendChild(when);
  box.appendChild(head);
  box.appendChild(el('div', 'says set-sub-lede', 'The gateway’s own certificate (a TRB makes one itself), or the root and the chain of the authority that signed it. With some here only these are trusted, and a gateway written as an address is not checked for a name. With none, the authorities this machine trusts - and the name.'));
  var state = el('div', 'set-ca-list');
  box.appendChild(state);
  var pem = el('textarea', 'mono admin-only');
  pem.rows = 4;
  pem.placeholder = '-----BEGIN CERTIFICATE-----';
  box.appendChild(pem);
  var row = el('div', 'set-ca-tools admin-only');
  var fetch = cmdButton('Read it from the gateway', 'download', '');
  var file = cmdButton('Read a file…', 'upload', '');
  var drop = cmdButton('Take them all away', 'trash', 'danger');
  var input = el('input'); input.type = 'file'; input.accept = '.pem,.crt,.cer,.txt'; input.hidden = true;
  [fetch, file, drop, input].forEach(function (b) { row.appendChild(b); });
  var seen = el('div', 'set-ca-seen');
  box.appendChild(row);
  box.appendChild(seen);
  var draw = function () {
    api('mail').then(function (d) {
      var list = d.sms_ca_list || [];
      when.textContent = list.length ? num(list.length) + ' certificate(s) kept' : 'none imported';
      drop.hidden = !list.length;
      clear(state);
      if (list.length) state.appendChild(certTable(list, function (c) {
        confirmThen('Take this certificate out', '<b>' + htmlText(c.subject || 'this certificate')
          + '</b> is no longer trusted for the SMS gateway. The others stay.', 'Take it out', function () {
            api('mail', {action: 'sms_ca', mode: 'drop', fingerprint: c.fingerprint}).then(function (r) {
              toast(r.message, 'good'); draw();
            }).catch(oops);
          });
      }));
      explainWhatWasDrawn(box);
    }).catch(oops);
  };
  pem.addEventListener('input', function () {
    clear(seen);
    if (!pem.value.trim()) { delete PENDING.smsca; markDirtyCount(); return; }
    pendingSet('smsca', {save: function () {
      return api('mail', {action: 'sms_ca', mode: 'add', ca: pem.value.trim()}).then(function (r) {
        toast(r.message, 'good'); pem.value = ''; clear(seen); draw(); return true;
      });
    }, reset: function () { pem.value = ''; clear(seen); }});
  });
  fetch.onclick = function () {
    if (Object.keys(DIRTY || {}).some(function (k) { return /^sms_tel_(host|https)$/.test(k); })) {
      toast('save the gateway’s address first', 'bad'); return;
    }
    busy(fetch, true);
    api('mail', {action: 'sms_ca_fetch'}).then(function (r) {
      pem.value = r.pem || '';
      pem.dispatchEvent(new Event('input'));
      if ((r.certs || []).length) {
        seen.appendChild(el('div', 'says', 'What the gateway shows - check the fingerprint against the one on the gateway (System → Administration → Certificates) before Save the changes trusts it:'));
        seen.appendChild(certTable(r.certs));
        var top = r.certs[r.certs.length - 1];
        if (top && !top.self_signed) seen.appendChild(el('div', 'says', 'The gateway does not send the certificate of whom signed it: its own is then trusted as it is - only exactly this certificate passes.'));
        explainWhatWasDrawn(seen);
      }
    }).catch(oops).then(function () { busy(fetch, false); });
  };
  file.onclick = function () { input.click(); };
  input.onchange = function () { var f = input.files && input.files[0]; if (f) readCertFile(f, pem); input.value = ''; };
  drop.onclick = function () {
    confirmThen('Take every certificate of the SMS gateway away',
      'The gateway’s certificate will then have to be signed by an authority this machine already trusts, or the check has to be switched off.',
      'Take them all away', function () {
        api('mail', {action: 'sms_ca', mode: 'clear'}).then(function (r) { toast(r.message, 'good'); draw(); }).catch(oops);
      }, true);
  };
  draw();
  return box;
}

function drawSettings() {
  DRAWN_NODE = SETTINGS.node || '';
  var shown = {};
  Object.keys(SETTINGS.panes).forEach(function (pane) {
    var host = $('sect-' + pane);
    if (!host) return;
    clear(host);
    if (PANE_LAYOUT[pane]) { drawLaidOut(host, pane, shown); return; }
    var grid = el('div', 'set-grid');
    SETTINGS.panes[pane].forEach(function (key) {
      var s = settingByKey(key);
      if (!s) return;
      shown[key] = true;
      grid.appendChild(settingItem(s));
    });
    host.appendChild(grid);
  });
  var rest = SETTINGS.settings.filter(function (s) { return !shown[s.key]; });
  var host = $('sect-rest');
  clear(host);
  $('rest-card').hidden = !rest.length;
  if (rest.length) {
    var g = el('div', 'set-grid');
    rest.forEach(function (s) { g.appendChild(settingItem(s)); });
    host.appendChild(g);
  }
  applyOnlyWhen();
  explainWhatWasDrawn($('tab-settings'));
  if (typeof PANE !== 'undefined' && PANE === 'backup' && typeof rbPassTools === 'function') rbPassTools();
}

/* Name, control, then the words, each in its own row of the grid, so every
   box on a row starts at the same height even where one name takes two
   lines (1.0.20). */
/* What a setting does, in three lines at most (1.0.156): a click opens the
   rest in place; the whole is on the name and its (i) as well. */
function saysClamped(words) {
  var box = saysBlock(words);
  box.classList.add('clamp');
  box.addEventListener('click', function () { box.classList.toggle('open'); });
  /* Marked once drawn, so only a text that is cut looks like one. */
  setTimeout(function () { if (box.scrollHeight > box.clientHeight + 2) box.classList.add('cut'); }, 0);
  return box;
}
function settingItem(s) {
  var item = settingItemBare(s);
  var tail = el('div', 'set-tail');
  Array.prototype.slice.call(item.children, 2).forEach(function (c) { tail.appendChild(c); });
  item.appendChild(tail);
  return item;
}
function settingItemBare(s) {
  var item = el('div', 'set-item' + (isBool(s) ? ' set-bool' : ''));
  item.dataset.key = s.key;
  var label = el('label', '', s.name || s.key);
  label.setAttribute('for', 'set-' + s.key);
  var info = el('span', 'iinfo', 'i');
  info.setAttribute('role', 'button');
  info.tabIndex = 0;
  var asText = function (v) { return richText(Array.isArray(v) ? v.join(', ') : String(v)); };
  var where = s.source;
  var story = '<span class="k">on the command line this one is <b>ai --set ' + richText(s.key)
    + '=…</b> · running: ' + (s.secret ? (s.set ? 'set' : 'not set') : asText(s.value))
    + '<br><span class="' + (where === 'default' ? 'same' : 'diff') + '">' + richText(s.source_says || '')
    + (s.saved_by ? ' (by ' + richText(s.saved_by) + (s.saved_at ? ', ' + ago(s.saved_at) : '') + ')' : '')
    + '</span>'
    + (s.file_only ? '<br><span class="same">kept in ' + richText(SETTINGS.config_file)
       + ' - a database cannot hold its own address</span>' : '')
    + (where !== 'default' && !s.secret && String(s.value) !== String(s.default)
       ? '<br><span class="same">the built-in default is ' + asText(s.default) + '</span>' : '') + '</span>';
  var whole = s.says || 'No words have been written for this one yet.';
  if (s.node_key && SETTINGS.cluster) {
    story += '<br><span class="diff">' + richText('this node’s own - every node of the cluster has one of its own; the others’ are in Settings → High availability') + '</span>';
  }
  explain(info, whole, story);
  explain(label, whole, story);
  label.appendChild(info);
  /* A node's own setting, in a cluster (1.0.37): said beside its name. */
  if (s.node_key && SETTINGS.cluster) {
    label.appendChild(document.createTextNode(' '));
    var nt = el('span', 'tag info', 'this node');
    nt.title = SETTINGS.node;
    label.appendChild(nt);
    label.appendChild(document.createTextNode(' '));
    label.appendChild(noI18n(el('span', 'tag dim', SETTINGS.node)));
  }
  item.appendChild(label);
  var input;
  if (isBool(s)) {
    input = switchBox(s.value === true || String(s.value) === '1');
    input._input.disabled = !ADMIN;
    input._input.addEventListener('change', function () { markDirty(item, s); });
    input.id = 'set-' + s.key;
    /* The name is a label for the checkbox itself, so a click on it flips
       the switch (1.0.15); the wrapper keeps the id the readers look up. */
    input._input.id = 'set-' + s.key + '-sw';
    label.setAttribute('for', input._input.id);
    item.appendChild(input);
    if (s.says) item.appendChild(saysClamped(s.short || s.says));   /* the whole on the (i) (1.0.156) */
    return item;
  }
  if (s.choices && s.choices.some(function (c) {
    return String((s.choice_words && s.choice_words[c]) || c).length > 30;
  })) item.classList.add('wide');
  if (s.choices) {
    input = selectBox(s.choices.map(function (c) { return [c, (s.choice_words && s.choice_words[c]) || c]; }), s.value);
  } else if (typeof s.min === 'number') {
    input = el('input');
    input.type = 'number';
    input.min = s.min;
    input.max = s.max;
    input.value = s.value;
  } else if (s.cell) {
    /* Several lines, in its place in the grid as one box (the CA's PEM, as
       upsmon's): not a whole row of its own. */
    input = el('textarea', 'mono cell-text');
    input.spellcheck = false;
    input.placeholder = '-----BEGIN CERTIFICATE-----\n…\n-----END CERTIFICATE-----';
    input.value = s.value === null || s.value === undefined ? '' : String(s.value);
    input.rows = 6;
    item.classList.add('wide', 'memo');
  } else if (TALL[s.key] || s.tall) {
    item.classList.add('tall');
    input = el('textarea');
    input.className = 'mono';
    input.spellcheck = false;
    input.value = s.value === null || s.value === undefined ? '' : String(s.value);
    input.rows = s.key === 'claude_env' || s.key === 'sms_body' ? 4 : 2;
  } else {
    input = s.secret ? maskBox(s.value, '', '') : textBox(s.value, '', '');
    if (s.secret) {
      input.placeholder = s.set ? 'set - leave as it is to keep it' : 'not set';
      input.addEventListener('focus', function () { if (input.value.indexOf('•') === 0) input.select(); });
    }
  }
  input.id = 'set-' + s.key;
  input.disabled = !ADMIN || s.key === 'db_engine';
  input.addEventListener('input', function () { markDirty(item, s); });
  input.addEventListener('change', function () { markDirty(item, s); });
  item.appendChild(input);
  if (s.says) item.appendChild(saysClamped(s.short || s.says));   /* the whole on the (i) (1.0.156) */
  if (s.key === 'db_engine' && ADMIN) {
    var mv = cmdButton('Move to another database…', 'db', 'small');
    mv.style.marginTop = '8px';
    mv.onclick = function () { if (typeof migOpen === 'function') migOpen(); };
    item.appendChild(mv);
  }
  return item;
}

function readValue(s) {
  var input = $('set-' + s.key);
  if (!input) return undefined;
  if (input._get) return input._get();
  if (typeof s.min === 'number' && !s.choices) return String(input.value).trim() === '' ? '' : Number(input.value);
  return input.value;
}
function markDirty(item, s) {
  /* Against what is saved now (1.0.94), not what was when the box was
     drawn: after a save the old value made a change back look like none. */
  s = settingByKey(s.key) || s;
  var now = readValue(s);
  var was = isBool(s) ? ((s.value === true || String(s.value) === '1') ? '1' : '0')
    : (s.value === null || s.value === undefined ? '' : String(s.value));   /* null is empty (1.0.57) */
  var changed = was !== String(now);
  item.classList.toggle('changed', changed);
  /* The database's address is what the steps below it ask about, never
     saved by the save bar (1.0.37): saved, the next restart opened a
     database nothing had been carried into. */
  /* The engine is changed by Move to another database… alone (1.0.56); how
     the one in use is reached - server, account, password, TLS - is saved
     here, tried first, and the daemon starts again on it. */
  if (s.key === 'db_engine') { delete DIRTY[s.key]; markDirtyCount(); applyOnlyWhen(); return; }
  if (changed) DIRTY[s.key] = now; else delete DIRTY[s.key];
  markDirtyCount();
  applyOnlyWhen();
}
/* Changes that are not settings (1.0.56) - the firewall, the web address,
   a certificate authority pasted in - wait for the same save bar:
   PENDING[key] = {save: function () -> Promise (false: not done), reset}. */
var PENDING = {};
var SAVE_BAR_HOME = null;
function saveBarHome() {
  var bar = $('save-bar');
  if (!bar) return;
  if (!SAVE_BAR_HOME) SAVE_BAR_HOME = {parent: bar.parentNode, next: bar.nextSibling};
  if (bar.parentNode !== SAVE_BAR_HOME.parent) {
    SAVE_BAR_HOME.parent.insertBefore(bar, SAVE_BAR_HOME.next && SAVE_BAR_HOME.next.parentNode === SAVE_BAR_HOME.parent ? SAVE_BAR_HOME.next : null);
    bar.classList.remove('in-editor');
  }
}
function saveBarPlace() {
  var bar = $('save-bar');
  if (!bar) return;
  var ed = PANE === 'texts' && TAB === 'settings' ? document.querySelector('.tx-shell.split > .tx-ed') : null;
  if (!ed) { saveBarHome(); return; }
  if (!SAVE_BAR_HOME) SAVE_BAR_HOME = {parent: bar.parentNode, next: bar.nextSibling};
  if (bar.parentNode !== ed || ed.lastChild !== bar) { ed.appendChild(bar); bar.classList.add('in-editor'); }
}
function pendingSet(key, p) { p.pane = p.pane || PANE; PENDING[key] = p; markDirtyCount(); }
/* The one save bar, at the bottom (1.0.123): on every pane where something
   is saved - settings, the firewall, the web address, the time servers, the
   message texts, the pages' looks - and on no other. A pane that does
   something at once (Network, Restart and power off, Backups…) has its own
   buttons for it and no save bar. */
var SAVE_PANES = ['fw', 'time', 'texts'];
function saveBarHere() {
  if (!ADMIN || TAB !== 'settings') return false;
  var pane = $('pane-' + PANE);
  if (!pane) return false;
  /* A setting of the daemon's own (data-key) - not a field that only looks
     like one, as on Network, where nothing is saved: it is done at once. */
  if (SAVE_PANES.indexOf(PANE) >= 0 || pane.querySelector('.set-item[data-key]')) return true;
  return Object.keys(PENDING).some(function (k) { return PENDING[k].pane === PANE; });
}
function markDirtyCount() {
  var n = Object.keys(DIRTY).length + Object.keys(PENDING).length;
  $('set-said').textContent = n ? n + ' change(s) not saved yet' : '';
  $('save-bar').classList.toggle('dirty', n > 0);
  /* Message texts, where only the editor scrolls (1.0.130): the bar is out of
     the way until something is changed, as it is below the end of any other
     page - and then at the bottom. */
  $('save-bar').style.display = saveBarHere() ? '' : 'none';
  saveBarPlace();
}
/* A question as a promise: true for the button, false for anything else. */
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
function applyOnlyWhen() {
  applySubs();
  var rules = (SETTINGS && SETTINGS.only_when) || {};
  /* Why a setting is not in use, or '' (1.0.42): its own condition first, then
     the one it hangs on - a setting depending on one that is itself greyed out
     is greyed out too (The TXT records go into stayed open with ACME off, its
     master's own value being one that would let it). */
  var memo = {};
  function why(key, depth) {
    if (memo[key] !== undefined) return memo[key];
    var rule = rules[key];
    var master = rule && $('set-' + rule[0]);
    if (!rule || !master || depth > 8) return (memo[key] = '');
    var now = master._get ? String(master._get()) : String(master.value);
    var want = rule[1];
    var live = Array.isArray(want) ? want.indexOf(now) >= 0
      : (want === '*' ? !!now.trim() : (want.slice(-4) === '-not' ? now !== want.slice(0, -4) : now === want));
    var other = settingByKey(rule[0]) || {};
    if (!live) {
      return (memo[key] = want === '*' ? 'Not in use until ' + other.name + ' is filled in.'
        : (isBool(other) ? 'Not in use while ' + other.name + ' is off.'
           : 'Not in use while ' + other.name + ' is “' + ((other.choice_words || {})[now] || now || '–') + '”.'));
    }
    return (memo[key] = why(rule[0], (depth || 0) + 1));
  }
  Object.keys(rules).forEach(function (key) {
    var item = document.querySelector('.set-item[data-key="' + key + '"]');
    if (!item || !$('set-' + rules[key][0])) return;
    var said = why(key, 0);
    item.classList.toggle('asleep', !!said);
    var says = item.querySelector('.asleep-why');
    // Written again on every pass (1.0.61): it went on naming the choice it
    // was first put in for.
    if (says) says.remove();
    if (said) (item.querySelector('.set-tail') || item).appendChild(el('div', 'says asleep-why', said));
  });
}
$('set-save').onclick = function () {
  var want = {};
  Object.keys(DIRTY).forEach(function (k) {
    var s = settingByKey(k);
    // A secret's dots are not a change (1.0.61): forgotten, not left on the
    // bar as "not saved" for ever.
    if (s && s.secret && String(DIRTY[k]).indexOf('•') === 0) { delete DIRTY[k]; return; }
    want[k] = DIRTY[k];
  });
  markDirtyCount();
  var keys = Object.keys(PENDING);
  if (!Object.keys(want).length && !keys.length) { toast('nothing has changed'); return; }
  busy($('set-save'), true);
  document.querySelectorAll('.set-item.refused').forEach(function (n) { n.classList.remove('refused'); });
  var chain = Promise.resolve(true);
  if (Object.keys(want).length) {
    chain = api('settings', {settings: want, drawn_by: DRAWN_NODE}).then(function (d) {
      toast(d.message, 'good');
      /* How the database is reached changed (1.0.56): the daemon starts again
         on it; the page waits for it and is loaded again. */
      if (d.restarting) {
        var tries = 0;
        var back = function () {
          tries += 1;
          api('db').then(function () { location.reload(); })
            .catch(function () { if (tries < 60) setTimeout(back, 2000); });
        };
        setTimeout(back, 5000);
      }
      /* What was changed while the save was on its way stays changed
         (1.0.61): the redraw after it threw those away without a word. */
      var left = {};
      Object.keys(DIRTY).forEach(function (k) {
        if (!(k in want) || DIRTY[k] !== want[k]) left[k] = DIRTY[k];
      });
      /* What was saved is no longer a change (1.0.51): left in DIRTY, a
         password - shown as dots once saved, never as what was typed - stayed
         "1 change(s) not saved yet" for ever, and the page was not drawn again. */
      DIRTY = left;
      markDirtyCount();
      if (Object.keys(left).length) loadSettings(false); else loadSettings();
      if (paneLive('upgrade')) loadUpgrade();      /* the card to go back shown or not */
      if (paneLive('backup')) loadRbackup();       /* locked or not, the next one */
      return true;
    }).catch(function (e) {
      var said = String(e.message || e);
      /* The longest key the message starts with (1.0.57): portal before portal_help was taken. */
      var hit = SETTINGS.settings.filter(function (one) {
        return said.indexOf(one.key) === 0 && !/[A-Za-z0-9_]/.test(said.charAt(one.key.length));
      }).sort(function (a, b) { return b.key.length - a.key.length; })[0];
      if (hit) {
        var item = document.querySelector('.set-item[data-key="' + hit.key + '"]');
        if (item) { item.classList.add('refused'); item.scrollIntoView({block: 'center'}); }
        said = '“' + hit.name + '”' + said.slice(hit.key.length);
      }
      toast(said, 'bad');
      return false;
    });
  }
  /* Then the rest, one after the other; the first that fails stops it. */
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
  var keys = Object.keys(PENDING);
  keys.forEach(function (k) { try { PENDING[k].reset(); } catch (e) { /* drawn again anyway */ } });
  PENDING = {};
  /* The changed values forgotten too (1.0.104): loadSettings draws nothing
     again while any is left, so Put them back did nothing at all. */
  DIRTY = {};
  document.querySelectorAll('.set-item.refused').forEach(function (n) { n.classList.remove('refused'); });
  markDirtyCount();
  loadSettings(); toast('put back as the daemon has them');
};
window.addEventListener('beforeunload', function (e) {
  if (Object.keys(DIRTY).length || Object.keys(PENDING).length) { e.preventDefault(); e.returnValue = ''; }
});


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
/* A few boxes asked for in a popup (otp's). */
function askInModal(title, lede, fields, words, icon, go) {
  var boxes = [];
  modal(title, function (body) {
    if (lede) body.appendChild(el('p', 'note', lede));
    var g = el('div', 'formgrid');
    fields.forEach(function (f) {
      var input = f.type === 'password' ? maskBox('', '', '') : el('input');
      if (f.type !== 'password') input.type = f.type || 'text';
      input.placeholder = f.placeholder || '';
      input.autocomplete = 'off';
      if (f.mono) input.className = 'mono';
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); $('modal-foot').querySelector('.btn.primary').click(); }
      });
      boxes.push(input);
      g.appendChild(formField(f.label, input, f.says));
    });
    body.appendChild(g);
    setTimeout(function () { if (boxes[0]) boxes[0].focus(); }, 60);
  }, [{words: 'Close', close: true}, {words: words, cls: 'primary', icon: icon, go: function (b) {
    go(boxes.map(function (x) { return x.value; }), b);
  }}], 'medium');
}
function loadUsers() {
  colsCardSay();
  api('users').then(function (d) {
    US = d;
    var host = $('us-table');
    clear(host);
    host.appendChild(listTable(['Name', 'Role', 'Terminals run as', 'State', 'Second step', 'Last signed in', 'From', 'Columns', 'Note', ''], d.users, function (u) {
      var tr = el('tr');
      var n = el('td'); n.appendChild(noI18n(el('span', 'mono', u.name)));
      if (u.must_change) n.appendChild(el('span', 'sub', 'chooses a password at the next sign-in'));
      tr.appendChild(n);
      var r = el('td'); r.appendChild(el('span', 'tag ' + (u.role === 'admin' ? 'violet' : 'dim'), roleWords(u.role))); tr.appendChild(r);
      var ra = el('td');
      ra.appendChild(noI18n(el('span', 'mono', u.run_as + (u.run_as_own ? '' : ' *'))));
      if (u.role === 'admin') ra.appendChild(el('span', 'sub', 'files everywhere'));
      else ra.appendChild(noI18n(el('span', 'sub mono', u.roots.join(', ') || '~' + u.run_as)));
      tr.appendChild(ra);
      var st = el('td'); st.appendChild(el('span', 'tag ' + (u.disabled ? 'crit' : 'ok'), u.disabled ? 'off' : 'on')); tr.appendChild(st);
      /* The second step of signing in: how it is given, or not yet. */
      var mf = el('td', 'small');
      if (u.mfa) {
        mf.appendChild(el('span', 'tag ok', {app: 'an app', mail: 'e-mail', sms: 'SMS'}[u.mfa.kind] || u.mfa.kind));
        if (u.mfa.dest) mf.appendChild(noI18n(el('span', 'sub mono', u.mfa.dest)));
      } else {
        mf.appendChild(el('span', 'muted', d.mfa_on ? 'set up at the next sign-in' : '–'));
      }
      tr.appendChild(mf);
      tr.appendChild(u.last_login ? stampCell(u.last_login) : el('td', 'muted', 'never'));
      tr.appendChild(noI18n(el('td', 'mono small', u.last_ip || '')));
      tr.appendChild(el('td', 'muted small', u.cols_tables ? num(u.cols_tables) + ' table(s) laid out' : 'as they come'));
      tr.appendChild(noI18n(el('td', 'muted small', u.note || '')));
      var tools = el('td', 'rowtools');
      /* Every row has the same buttons in the same places (otp's): one that
         does not apply to this account is there, dimmed, and says why. */
      var role = selectBox([['admin', roleWords('admin')], ['user', roleWords('user')]], u.role);
      role.onchange = function () {
        api('users', {do: 'edit', name: u.name, role: role.value}).then(function () { toast('the role of ' + u.name + ' is changed', 'good'); loadUsers(); })
          .catch(function (e) { role.value = u.role; oops(e); });
      };
      role.style.marginRight = '10px';
      tools.appendChild(role);
      var info = iconButton('person', 'Its Linux account, its folders and its note');
      info.onclick = function (ev) { ev.stopPropagation(); editUser(u); };
      tools.appendChild(info);
      var pw = iconButton('lock', 'Set a new password');
      pw.onclick = function () {
        askInModal('A new password for ' + u.name, 'They choose their own at the next sign-in.',
          [{label: 'The new one (8 characters at least)', type: 'password'},
           {label: 'Again', type: 'password'}], 'Set it', 'lock', function (v) {
            if (v[0].length < 8) { toast('8 characters at least', 'bad'); return; }
            if (v[0] !== v[1]) { toast('the two are not the same', 'bad'); return; }
            closeModal();
            api('users', {do: 'password', name: u.name, password: v[0], must_change: true})
              .then(function () { toast('the password of ' + u.name + ' is set', 'good'); loadUsers(); }).catch(oops);
          });
      };
      tools.appendChild(pw);
      var off = iconButton('power', u.disabled ? 'Let it sign in again' : 'Stop it signing in');
      if (u.name === ME.name && !u.disabled) { off.disabled = true; off.title = 'Not your own account'; }
      off.onclick = function () {
        api('users', {do: 'edit', name: u.name, disabled: !u.disabled}).then(function () { loadUsers(); }).catch(oops);
      };
      var x = iconButton('trash', 'Remove it');
      if (u.name === ME.name) { x.disabled = true; x.title = 'Not your own account - sign in as another administrator for that'; }
      x.onclick = function () {
        confirmThen('Remove the account ' + u.name, 'It cannot sign in any more. Its terminals go on running as the Linux account they run as.', 'Remove it', function () {
          api('users', {do: 'drop', name: u.name}).then(function () { loadUsers(); }).catch(oops);
        });
      };
      tools.appendChild(off); tools.appendChild(x);
      /* Somebody's own layout of the tables, put back as it comes. */
      var cb = iconButton('undo', u.cols_tables
        ? u.name + ' has laid out ' + num(u.cols_tables) + ' table(s) by hand. Put every one of them back as it comes: the widths, the order and the hidden columns. Nothing else of theirs changes.'
        : u.name + ' has every table as it comes: nothing to put back.');
      cb.classList.add('cols-back');
      if (u.cols_tables) {
        cb.onclick = function (ev) {
          ev.stopPropagation();
          confirmThen('The columns of ' + u.name,
            'Every table ' + htmlText(u.name) + ' has laid out goes back as it comes. They see it '
            + 'the next time a page loads.',
            'Put them back', function () {
              colsReset(u.name).then(function () {
                if (ME && u.name === ME.name) colsCardSay();
                loadUsers();
              }).catch(oops);
            });
        };
      } else {
        cb.disabled = true;
      }
      tools.appendChild(cb);
      var mr = iconButton('shield', u.mfa
        ? 'Reset the second step: ' + u.name + ' sets it up again at the next sign-in. Their sign-ins are ended.'
        : u.name + ' has no second step set up: nothing to reset.');
      if (u.mfa) {
        mr.onclick = function (ev) {
          ev.stopPropagation();
          confirmThen('Reset the second step of ' + u.name + '?',
            htmlText('The way ' + u.name + ' gives the second step is taken away, and their sign-ins are ended. At the next sign-in they choose and set it up again - with the password alone, so do it only when you know it is them (a lost phone, a new one).'),
            'Reset it', function () {
              api('users', {do: 'mfa_reset', name: u.name}).then(function (r) { toast(r.message, 'good'); loadUsers(); }).catch(oops);
            }, true);
        };
      } else {
        mr.disabled = true;
      }
      tools.appendChild(mr);
      tr.appendChild(tools);
      return tr;
    }));
    host.appendChild(el('p', 'muted small', '* the default (Settings - Claude Code), ' + d.default_run_as + ' now'));
    explainWhatWasDrawn(host);
    var sh = $('us-sessions');
    clear(sh);
    sh.appendChild(listTable(['Who', 'Where', 'From', 'Since', 'Last asked', ''], d.sessions, function (s) {
      var tr = el('tr');
      var who = el('td');
      who.appendChild(noI18n(el('span', 'mono', s.name)));
      if (s.id === d.me_sid) { who.appendChild(document.createTextNode(' ')); who.appendChild(el('span', 'tag info', 'this page')); }
      if (s.mfa_pending) who.appendChild(el('span', 'sub', 'the second step not given yet'));
      tr.appendChild(who);
      var where = el('td', '', 'these pages');
      if (s.agent) explain(where, s.agent);
      tr.appendChild(where);
      tr.appendChild(noI18n(el('td', 'mono small', s.ip)));
      tr.appendChild(stampCell(s.created));
      tr.appendChild(el('td', 'muted', ago(s.seen)));
      var tools = el('td', 'rowtools');
      var x = cmdButton('End it', 'cancel', 'small');
      x.onclick = function () {
        confirmThen('End this sign-in', htmlText(String(s.name || '?')) + (s.ip ? ' from ' + htmlText(String(s.ip)) : '')
          + ' is signed out at once.' + (s.id === d.me_sid ? ' It is this one: you are signed out.' : ''), 'End it', function () {
          api('users', {do: 'end', sid: s.id, name: s.name}).then(function () {
            if (s.id === d.me_sid) location.href = '/'; else loadUsers();
          }).catch(oops);
        });
      };
      tools.appendChild(x);
      tr.appendChild(tools);
      return tr;
    }));
  }).catch(oops);
  if (typeof loadLockouts === 'function') loadLockouts();
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
                 ['Key', (info.key || '–') + (prof && prof.alt && prof.alt.info && prof.alt.info.key ? ' + ' + prof.alt.info.key + ' (a second certificate beside it)' : '')]];
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
  /* Automatic certificates beside it (1.0.39, as otp's): who renews this one. */
  var ac = d.acme || {};
  if (ac.on) {
    var acare = (ac.care || {})[target];
    var ach = el('span', 'cchip' + (acare ? '' : ' dim'), acare ? 'renewed by ACME' : 'ACME leaves it alone');
    explain(ach, acare ? 'Settings → Automatic certificates renews it before it runs out. Uploading one here, or making one self-signed, takes it out of ACME’s care - it is kept as it is.'
      : 'Kept as it is: Automatic certificates does not replace it (Look after it there gives it to ACME).');
    ach.style.cursor = 'pointer';
    ach.onclick = function () { location.hash = '#settings/acme'; };
    chips.appendChild(ach);
    var ast = (ac.state || {})[target] || {};
    if (acare && ast.ok === false && ast.said) chips.appendChild(el('span', 'cchip warn', 'the last order failed'));
  }
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
    /* Put in by hand while ACME renews it: said first - it leaves ACME's
       care, or ACME would replace it at its next renewal. */
    var byHand = function (go) {
      if (!(d.acme && d.acme.on && (d.acme.care || {})[target])) { go(); return; }
      confirmThen('ACME renews this certificate', 'One put in here by hand takes ' + webTargetWords(target)
        + ' out of ACME’s care: it is kept as it is, not replaced at the next renewal. Settings → Automatic certificates → Look after it gives it back.', 'Go on', go, false);
    };
    var up = cmdButton('Upload', 'upload', 'small');
    up.onclick = function () { byHand(function () { certUpload(target, prof); }); };
    tools.appendChild(up);
    var req = cmdButton(prof && prof.pending ? 'The waiting request' : 'Request (CSR)', 'list', 'small');
    req.onclick = function () { certRequest(target, prof); };
    tools.appendChild(req);
    var ss = cmdButton('Self-signed', 'key', 'small');
    ss.onclick = function () { byHand(function () { certSelf(target, d); }); };
    tools.appendChild(ss);
    var pol = cmdButton('TLS settings', 'gear', 'small');
    pol.onclick = function () { certPolicy(target, prof, d); };
    /* Whoever gave the certificate - ACME too - its protocols, ciphers, DH
       and HSTS are set here and kept when it is renewed. */
    explain(pol, 'The protocols, the ciphers, the DH parameters and HSTS of ' + webTargetWords(target) + ' - kept as they are whichever way the certificate came, ACME and its renewals too.');
    tools.appendChild(pol);
    var bef = (d.acme && d.acme.before || {})[target];
    if (bef && !bef.ran_out && typeof acmePutBackButton === 'function') tools.appendChild(acmePutBackButton(target, bef, function () { loadWeb(); }));
    /* Download whenever there is a certificate - one ai looks after, or the
       one nginx has from before (1.0.31). */
    if ((prof && prof.cert) || info) {
      var dl = cmdButton('Download', 'download', 'small');
      dl.title = 'The certificate in the form you choose - PEM, CRT, DER, PKCS#7, or with its private key (PEM, PFX)';
      dl.onclick = function () { certExportAsk(target, prof); };
      tools.appendChild(dl);
    }
    if (prof && prof.cert) {
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
/* ---- upgrades (as otp's Upgrades and maintenance, one server) ----------------------- */
/* ---- upgrades and maintenance (1.0.37) ------------------------------------ */
var UP = {timer: null, held: null, misses: 0};
var UP_STATE = {waiting: ['waiting', 'dim'], none: ['waiting', 'dim'], draining: ['taken out of service', 'warn'],
                installing: ['being put in', 'info'], checking: ['checking', 'info'],
                done: ['done', 'ok'], failed: ['failed', 'crit']};
function upgradeSend(file) {
  return sendFile('/files/package?name=' + encodeURIComponent(file.name), file);
}
/* Is this settings pane the one in front, in a tab in front (1.0.57)? The
   timers asked for their pane every 5 s after leaving Settings, and in tabs
   in the background, for as long as the page stayed open. */
function paneLive(name) {
  return TAB === 'settings' && PANE === name && $('pane-' + name) && !$('pane-' + name).hidden;
}
function upgradeAgain(ms) {
  /* Never dropped while the pane is open (1.0.73): in a tab in the
     background it waits and goes on when the tab is shown again, where
     before it stopped for good and only F5 brought it back. */
  clearTimeout(UP.timer);
  UP.timer = setTimeout(function () {
    if (!paneLive('upgrade')) return;
    if (document.hidden) { UP.sleeping = true; return; }
    loadUpgrade(true);
  }, ms);
}
document.addEventListener('visibilitychange', function () {
  if (!document.hidden && UP.sleeping) { UP.sleeping = false; if (paneLive('upgrade')) loadUpgrade(); }
});
/* Behind the web address the answers come from either node, and while one
   is restarting or the address moves, the other's copy of a step may be a
   moment behind (1.0.70): what was shown is never taken back by an older
   answer - each node's step only goes forward. */
function upSteady(d) {
  var p = d && d.plan;
  if (!p) return d;
  /* A plan older than the one shown, from a node whose copy is behind
     (1.0.73): not drawn - the one shown stays. */
  if (UP.keep && UP.keep.id !== p.id && Number(p.at || 0) < Number(UP.keep.at || 0) && UP.last && UP.last.plan) {
    d.plan = UP.last.plan;
    return d;
  }
  if (!UP.keep || UP.keep.id !== p.id) UP.keep = {id: p.id, at: p.at, steps: {}};
  (p.steps || []).forEach(function (st, i) {
    var k = UP.keep.steps[st.name];
    if (k && Number(k.at || 0) > Number(st.at || 0)) p.steps[i] = k;
    else UP.keep.steps[st.name] = st;
  });
  var states = (p.steps || []).map(function (x) { return x.state; });
  if (states.indexOf('failed') >= 0) p.state = 'failed';
  else if (states.length && states.every(function (x) { return x === 'done'; })) p.state = 'done';
  return d;
}
/* New versions on the web (1.0.123): what the address had when last asked,
   and one click to put the newest in. */
function drawUpWeb(d) {
  var w = d.web || {};
  var o = w.online || {};
  liveFill($('up-web'), function (host) {
    var p = el('p', 'note ' + (o.error ? 'bad' : (o.newer ? 'good' : '')));
    if (!o.at) p.textContent = w.check ? 'Not looked at yet - within minutes, or press Look now.' : 'Not looked at: looking every day is switched off below. Look now asks once.';
    else if (o.error) p.textContent = 'Looked ' + ago(o.at) + ': ' + o.error;
    else if (o.newer) p.textContent = 'ai ' + o.newest.version + ' is there - this server runs ' + (o.here || d.version) + ' (looked ' + ago(o.at) + ')';
    else if (o.newest) p.textContent = 'Nothing newer: the newest there is ' + o.newest.version + ' and this server runs ' + (o.here || d.version) + ' (looked ' + ago(o.at) + ')';
    else p.textContent = 'No ai package there (looked ' + ago(o.at) + ')';
    host.appendChild(p);
    /* One chain above (1.0.146): the line for several newer versions sat in
       the middle of it and every case below it said the wrong thing. */
    if (o.at && !o.error && o.newer && (o.newer_list || []).length > 1) {
      host.appendChild(el('p', 'note', num(o.newer_list.length) + ' versions there are newer than this one - choose which to go to; the newest is chosen.'));
    }
    if (o.url) host.appendChild(noI18n(el('p', 'mono small muted', o.url)));
    var row = el('div', 'btnrow');
    var look = cmdButton('Look now', 'refresh', '');
    look.onclick = function () {
      busy(look, true);
      api('upgrade', {action: 'online_look'}).then(function (x) { toast(x.message, 'good'); drawUpgrade(x); })
        .catch(oops).then(function () { busy(look, false); });
    };
    row.appendChild(look);
    var running = !!(d.plan && d.plan.state === 'running');
    if (o.newer && !running) {
      /* More than one newer there (1.0.142): which one, the newest chosen. */
      var list = (o.newer_list || []).filter(function (x) { return x && x.version; });
      var pick = list[0] && list[0].version === o.newest.version ? list[0] : o.newest;
      var choose = null;
      if (list.length > 1) {
        choose = selectBox(list.map(function (x, i) {
          return [x.version, x.version + (i === 0 ? ' (the newest)' : '')];
        }), pick.version);
        explain(choose, 'The versions there newer than the one this server runs. The newest is chosen; any of them can be put in instead.');
        row.appendChild(choose);
      }
      var up = cmdButton('Upgrade to ' + pick.version + ' now', 'play', 'primary');
      var chosen = function () {
        var v = choose ? choose.value : o.newest.version;
        return list.filter(function (x) { return x.version === v; })[0] || o.newest;
      };
      if (choose) {
        choose.onchange = function () {
          setButtonIcon(up, 'play', 'Upgrade to ' + chosen().version + ' now');
        };
      }
      up.onclick = function () {
        var many = (d.nodes || []).length > 1;
        var c = chosen();
        confirmThen('Upgrade to ai ' + c.version + '?', htmlText('It is fetched from ' + (c.url || o.url) + ', its signature checked, and '
          + 'this server is upgraded. The terminals go on running; these pages are back after a few seconds.'), 'Upgrade', function () {
          busy(up, true);
          api('upgrade', {action: 'online_get', version: c.version, start: true}).then(function (x) { toast(x.message, 'good'); drawUpgrade(x); })
            .catch(oops).then(function () { busy(up, false); });
        }, false);
      };
      row.appendChild(up);
      var only = cmdButton('Only fetch it', 'down', '');
      explain(only, 'Fetched and checked, and left ready below - put in when Upgrade is pressed.');
      only.onclick = function () {
        busy(only, true);
        api('upgrade', {action: 'online_get', version: chosen().version}).then(function (x) { toast(x.message, 'good'); drawUpgrade(x); })
          .catch(oops).then(function () { busy(only, false); });
      };
      row.appendChild(only);
    }
    host.appendChild(row);
  });
}
/* Going back to an older version (1.0.143): asked for on purpose, in a card
   of its own - the versions at upgrade_url older than this one, each with what
   stands in its way; the database is checked against the one chosen. */
function upDownConfirm(version, go) {
  var d = UP.last || {};
  var many = (d.nodes || []).filter(function (n) { return n.alive; }).length > 1;
  confirmThen('Go back to ai ' + version + '?', htmlText('The version running now is replaced by the older ' + version
    + '. The terminals go on running; these pages are back after a few seconds. A copy of the database is made first; the database itself stays as it is. What came in the newer versions is gone until you upgrade again.'),
    'Go back', go, true);
}
function upDownChangelog(version) {
  api('upgrade', {action: 'downgrade_changelog', version: version}).then(function (x) {
    var c = x.changelog || {};
    modal('What changed in ' + version, function (body) {
      if (c.from === 'package') body.appendChild(el('p', 'note small', 'Read from the package at the address - it is checked only when it is chosen.'));
      body.appendChild(c.entry ? noI18n(el('pre', 'lines', c.entry)) : el('p', 'note', 'The package says nothing about this version.'));
      if ((c.lost || []).length) {
        var det = el('details', 'fold');
        det.appendChild(el('summary', '', 'What going back gives up: ' + c.lost.length + ' newer version(s), up to ' + c.here));
        c.lost.forEach(function (one) { det.appendChild(noI18n(el('pre', 'lines', one.text))); });
        body.appendChild(det);
      }
    }, [{words: 'Close', close: true}], 'medium');
  }).catch(oops);
}
function drawUpDown(d) {
  var card = $('up-down-card');
  /* Offered only when switched on (1.0.144): Settings → Upgrades. */
  if (card) card.hidden = !(d && d.downgrade_on);
  var host = $('up-down');
  if (!host || host._made || !(d && d.downgrade_on)) return;
  host._made = true;
  var row = el('div', 'btnrow');
  var show = cmdButton('Show the versions to go back to', 'list', '');
  row.appendChild(show);
  host.appendChild(row);
  var list = el('div', '');
  host.appendChild(list);
  show.onclick = function () {
    busy(show, true);
    api('upgrade', {action: 'downgrade_list'}).then(function (x) {
      var g = x.downgrade || {};
      clear(list);
      var at = el('p', 'note small', 'At ' + (g.url || '?') + ' - this server runs ' + (g.here || '') + '; it may go back to ' + (g.lowest || g.floor || '?') + ' or newer.');
      at.style.marginTop = '10px';
      list.appendChild(at);
      var vs = g.versions || [];
      if (!vs.length) { list.appendChild(el('p', 'note', 'No version older than this one is there.')); return; }
      var running = !!((UP.last || {}).plan && UP.last.plan.state === 'running');
      var good = vs.filter(function (v) { return !(v.why || []).length; });
      var bad = vs.filter(function (v) { return (v.why || []).length; });
      /* One row a version, the buttons side by side (1.0.145): the reasons a
         version is refused are said once, folded below - not in every row. */
      var acts = function (v, ok) {
        var cell = el('div', '');
        cell.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-left:auto';
        var notes = cmdButton('What changed', 'list', 'small');
        notes.style.whiteSpace = 'nowrap';
        notes.onclick = function () { upDownChangelog(v.version); };
        cell.appendChild(notes);
        if (ok && !running) {
          var go = cmdButton('Go back to ' + v.version, 'undo', 'small danger');
          go.style.whiteSpace = 'nowrap';
          go.onclick = function () {
            upDownConfirm(v.version, function () {
              busy(go, true);
              api('upgrade', {action: 'downgrade_get', version: v.version, start: true}).then(function (r) { toast(r.message, 'good'); drawUpgrade(r); })
                .catch(oops).then(function () { busy(go, false); });
            });
          };
          cell.appendChild(go);
        }
        return cell;
      };
      /* Rows of their own, not a table (1.0.145): the version and its state on
         the left, the buttons on the right - on a narrow screen the buttons go
         below as a whole, never squeezed into a column. */
      var nowrap = function (node) {
        node.style.whiteSpace = 'nowrap';
        Array.prototype.forEach.call(node.querySelectorAll('span'), function (x) { x.style.whiteSpace = 'nowrap'; });
        return node;
      };
      var rows = function (items, ok) {
        var box = el('div', 'dg-rows');
        items.forEach(function (v) {
          var r = el('div', 'dg-row');
          r.style.cssText = 'display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 16px;padding:8px 10px;border-bottom:1px solid var(--line)';
          var left = el('div', '');
          left.style.cssText = 'display:flex;align-items:center;gap:10px;min-width:9em';
          left.appendChild(noI18n(el('b', '', v.version)));
          var tag = nowrap(el('span', ok ? 'tag ok' : 'tag warn', ok ? 'yes' : (v.short || 'no')));
          if (!ok) explain(tag, (v.why || []).join('\n'));
          left.appendChild(tag);
          r.appendChild(left);
          var right = acts(v, ok);
          Array.prototype.forEach.call(right.children, nowrap);
          r.appendChild(right);
          box.appendChild(r);
        });
        return box;
      };
      if (good.length) list.appendChild(rows(good, true));
      else list.appendChild(el('p', 'note', 'No version at the address may be gone back to.'));
      if (bad.length) {
        var det = el('details', 'fold');
        det.style.marginTop = '12px';
        det.appendChild(el('summary', '', bad.length + ' older version(s) it may not go back to' + (g.lowest ? ' - below ' + g.lowest : '')));
        var reasons = [];
        bad.forEach(function (v) { (v.why || []).forEach(function (w) { if (reasons.indexOf(w) < 0) reasons.push(w); }); });
        var why = el('ul', 'note small');
        why.style.margin = '8px 0';
        reasons.forEach(function (w) { why.appendChild(el('li', 'bad', w)); });
        det.appendChild(why);
        det.appendChild(rows(bad, false));
        list.appendChild(det);
      }
    }).catch(function (e) { clear(list); list.appendChild(el('p', 'note bad', String((e && e.message) || e))); })
      .then(function () { busy(show, false); });
  };
}
/* Maintenance (1.0.46, as otp's): this server out of service, or back. */
function maintenanceAsk(n, on, then) {
  if (!on) {
    api('upgrade', {action: 'maintenance', node: n.name, on: false}).then(function (r) { toast(r.message, 'good'); then(r); }).catch(oops);
    return;
  }
  modal('Take ' + n.name + ' out of service', function (body) {
    var p = el('p', 'note bad');
    p.textContent = 'This is the only server: while it is in maintenance nobody but an administrator can sign in, and no new terminal is started but an administrator\'s. The terminals that run go on, and its pages go on working; its /healthz says 503.';
    body.appendChild(p);
    var why = textBox('', 'why - for the events', '');
    why.id = 'maint-why';
    body.appendChild(formField('Why', why));
  }, [{words: 'No, leave it', close: true},
      {words: 'Take it out', cls: 'danger', icon: 'power', close: true, go: function () {
        api('upgrade', {action: 'maintenance', node: n.name, on: true, why: ($('maint-why') || {}).value || ''})
          .then(function (r) { toast(r.message, 'good'); then(r); }).catch(oops);
      }}], true);
}
function drawUpgrade(d) {
  d = upSteady(d);
  UP.last = d;
  /* The nodes. */
  liveFill($('up-nodes'), function (host) {
  /* By name, so the rows keep their places whichever node answered (1.0.70). */
  var nodesSorted = (d.nodes || []).slice().sort(function (a, b) { return String(a.name).localeCompare(String(b.name)); });
  host.appendChild(listTable(['Node', 'Version', 'Heard from', 'State', ''], nodesSorted, function (n) {
    var tr = el('tr');
    var nm = el('td');
    nm.appendChild(noI18n(el('b', '', n.name)));
    if (n.me) { nm.appendChild(document.createTextNode(' ')); nm.appendChild(el('span', 'tag info', 'this page')); }
    tr.appendChild(nm);
    tr.appendChild(noI18n(el('td', 'mono', n.version || '?')));
    tr.appendChild(el('td', 'muted', n.at ? ago(n.at) : '–'));
    var st = el('td');
    var m = n.maintenance || {};
    if (!n.alive) st.appendChild(el('span', 'tag crit', 'gone'));
    else if (m.on) st.appendChild(el('span', 'tag warn', 'in maintenance'));
    else st.appendChild(el('span', 'tag ok', 'in service'));
    if (m.on && m.why) st.appendChild(el('span', 'sub', m.why + (m.by ? ' · ' + m.by : '') + (m.at ? ' · ' + ago(m.at) : '')));
    tr.appendChild(st);
    var tools = el('td', 'rowtools');
    if (ADMIN && n.alive) {
      var b = cmdButton(m.on ? 'Back in service' : 'Maintenance', m.on ? 'play' : 'power', 'small');
      b.onclick = function (ev) { ev.stopPropagation(); maintenanceAsk(n, !m.on, drawUpgrade); };
      tools.appendChild(b);
    }
    tr.appendChild(tools);
    return tr;
  }, 'plain'));
  });
  drawUpWeb(d);
  /* The package. */
  var plan = d.plan;
  var running = !!(plan && plan.state === 'running');
  liveFill($('up-pkg'), function (pk) {
  if (d.package) {
    var p = d.package;
    var box = el('div', 'notice good');
    box.style.marginTop = '12px';
    if (p.downgrade) box.className = 'notice warn';
    box.appendChild(el('b', '', 'ai ' + p.version + (p.downgrade ? ' - older: ready to go back to' : '')));
    box.appendChild(el('div', 'small', 'signed by ' + (p.signed_by || '?') + ' · ' + bytes(p.bytes) + ' · sent by ' + (p.by || '?') + ' · ' + ago(p.at)));
    pk.appendChild(box);
    if (p.changelog) {
      var det = el('details', 'fold');
      det.appendChild(el('summary', '', 'What changed in ' + p.version));
      var pre = el('pre', 'lines', p.changelog);
      noI18n(pre);
      det.appendChild(pre);
      pk.appendChild(det);
    }
  }
  });
  $('up-forget').hidden = !d.package || running;
  $('up-start').disabled = !d.package || !d.ready || running;
  var many = (d.nodes || []).length > 1;
  var down = !!(d.package && d.package.downgrade);
  setButtonIcon($('up-start'), down ? 'undo' : 'play', down ? (many ? 'Go back on every node, one at a time' : 'Go back on this server')
    : (many ? 'Upgrade every node, one at a time' : 'Upgrade this server'));
  $('up-start').classList.toggle('danger', down);
  $('up-start').classList.toggle('primary', !down);
  drawUpDown(d);
  var rd = $('up-ready');
  clear(rd);
  if (d.package && !d.ready && !running) {
    (d.not_ready || []).forEach(function (w) { rd.appendChild(el('p', 'note bad', w)); });
  }
  if (!d.helper || !d.path_unit) {
    rd.appendChild(el('p', 'note bad', 'This server cannot put a version in by itself yet: ai_upgrade.py is not installed. Upgrade it once on the command line (install.sh --upgrade), which puts it in.'));
  }
  /* The plan. */
  $('up-plan-card').hidden = !plan;
  liveFill($('up-plan'), function (ph) {
  if (plan) {
    ph.appendChild(el('p', 'note', (plan.downgrade ? 'Going back to ' : 'To ') + plan.version + ' · started by ' + (plan.by || '?') + ' · ' + ago(plan.at) + ' · '
      + ({running: 'going on', done: 'done', failed: 'failed', cancelled: 'stopped'})[plan.state]));
    /* How far, as bars (1.0.67): the whole and each node. */
    var steps = plan.steps || [];
    var all = steps.length ? Math.round(steps.reduce(function (m, st) { return m + upPercent(st, plan); }, 0) / steps.length) : 0;
    ph.appendChild(upBar(all, plan.state === 'failed' ? 'bad' : (plan.state === 'done' ? 'good' : ''),
                         num(all) + ' %', true));
    var upTable = listTable(['Server', 'Step', 'How far', 'What happened', 'When'], steps, function (st) {
      var tr = el('tr');
      tr.appendChild(noI18n(el('td', 'mono', st.name)));
      var w = UP_STATE[st.state] || UP_STATE.waiting;
      var c = el('td');
      c.appendChild(el('span', 'tag ' + w[1], w[0]));
      tr.appendChild(c);
      var pc = upPercent(st, plan);
      var bt = el('td', 'up-how');
      bt.appendChild(upBar(pc, st.state === 'failed' ? 'bad' : (st.state === 'done' ? 'good' : ''),
                           st.state === 'installing' && st.part_words ? num(pc) + ' % · ' + st.part_words : num(pc) + ' %'));
      tr.appendChild(bt);
      var said = el('td', 'small', st.said || '');
      if ((st.tail || []).length) {
        var more = el('details', 'fold');
        more.appendChild(el('summary', '', 'what install.sh said'));
        more.appendChild(noI18n(el('pre', 'lines', st.tail.join('\n'))));
        /* Left open across the redraws every 3 s (1.0.69). */
        UP.tailOpen = UP.tailOpen || {};
        if (UP.tailOpen[st.name]) more.open = true;
        more.ontoggle = function () { UP.tailOpen[st.name] = more.open; };
        said.appendChild(more);
      }
      tr.appendChild(said);
      tr.appendChild(el('td', 'muted', st.at ? ago(st.at) : '–'));
      return tr;
    }, 'plain');
    /* Columns of a fixed width (1.0.69): they jumped about with every redraw
       as the bars and the words in them changed. */
    (upTable.querySelector('table') || upTable).classList.add('up-plan-table');
    ph.appendChild(upTable);
    if (plan.state === 'done' && d.version !== VERSION_LOADED) {
      var r = el('p', 'note good');
      r.appendChild(document.createTextNode('This page is still the one of ' + VERSION_LOADED + '. '));
      var a = el('a', 'fgo', 'Load it again');
      a.onclick = function () { location.reload(); };
      r.appendChild(a);
      ph.appendChild(r);
    }
    if (plan.state !== 'running') ph.appendChild(hideBar(function () {
      return api('upgrade', {action: 'hide'}).then(function (x) { drawUpgrade(x); });
    }));
  }
  });
  $('up-cancel').hidden = !running;
  /* Each node's own install.sh output (1.0.70), kept as it comes - the
     answering node changes behind the web address, and the one card showed
     one node's, then the other's. */
  UP.logs = UP.logs || {};
  if (d.node) UP.logs[d.node] = d.log || [];
  var known = Object.keys(UP.logs).sort();
  if (!UP.logNode || !UP.logs[UP.logNode]) UP.logNode = d.node;
  var lseg = $('up-log-nodes');
  if (lseg) {
    clear(lseg);
    lseg.hidden = known.length < 2;
    known.forEach(function (nm) {
      var b = noI18n(el('button', UP.logNode === nm ? 'on' : '', nm));
      b.type = 'button';
      b.onclick = function () { UP.logNode = nm; drawUpgrade(UP.last); };
      lseg.appendChild(b);
    });
  }
  if ($('up-log-node')) $('up-log-node').textContent = UP.logNode || '';
  var lg = $('up-log');
  var lines = UP.logs[UP.logNode] || [];
  lg.textContent = lines.length ? lines.join('\n') : '–';
  noI18n(lg);
  /* Asked again every 3 s while it runs and for two minutes after it ended,
     every 15 s otherwise - so a change made on the other node, or an answer
     from a node a moment behind, is never the last word (1.0.73). */
  if (running) UP.endedAt = 0;
  else if (UP.wasRunning && !UP.endedAt) UP.endedAt = Date.now() / 1000;
  UP.wasRunning = running || (UP.wasRunning && !UP.endedAt);
  upgradeAgain(upRunning() ? 3000 : 15000);
}
/* How far one node is (1.0.67), from its step and how long it has been in
   it: waiting 0, taken out of service up to 20, install.sh 20-82 by its
   sections, checking 85-95, done 100. */
function upPercent(st, plan) {
  var now = Date.now() / 1000, since = now - Number(st.at || now);
  switch (st.state) {
    case 'done': return 100;
    case 'failed': return 100;
    case 'draining':
      return Math.round(3 + 17 * Math.min(1, since / Math.max(1, Number(plan.drain_s || 20))));
    case 'installing':
      var asked = now - Number(st.asked || st.at || now);
      return Math.round(Math.min(92, 5 + 85 * Math.min(1, Number(st.part || 0) / 13) + Math.min(2, asked / 60)));
    case 'checking': return Math.round(85 + Math.min(10, since / 3));
    default: return 0;
  }
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
/* The version these pages came with: what the script was asked for as. */
var VERSION_LOADED = (function () {
  var sc = document.querySelector('script[src*="app.js"]');
  var m = sc && /[?&]v=([0-9.]+)/.exec(sc.getAttribute('src') || '');
  return m ? m[1] : '';
}());
function loadUpgrade(live) {
  /* A short deadline while an upgrade runs (1.0.66): the node answering may
     be restarting, or the web address moving to the other one. */
  var running = upRunning();
  clearTimeout(UP.timer);
  var mine = UP.ask = (UP.ask || 0) + 1;
  api('upgrade', undefined, running ? 8 : 0).then(function (d) {
    if (mine !== UP.ask) return;          /* a newer question is on its way */
    UP.misses = 0;
    if ($('up-retry')) $('up-retry').textContent = '';
    if (!VERSION_LOADED) VERSION_LOADED = d.version;
    if (live) liveRun(function () { drawUpgrade(d); }); else drawUpgrade(d);
  }).catch(function (e) {
    if (mine !== UP.ask) return;
    /* The node that answers these pages may be the one being restarted, or
       the web address may be moving to the other node: asked again, always
       (1.0.73) - not only while the last answer said "running", and without
       a limit. Said once, in a line of its own that is always there. */
    UP.misses = (UP.misses || 0) + 1;
    if (running || e.unreachable || UP.misses <= 3) {
      if ($('up-retry')) $('up-retry').textContent = ('The daemon is starting again with the new version - asking again…');
      upgradeAgain(Math.min(2000 * UP.misses, 6000));
      return;
    }
    oops(e);
    upgradeAgain(15000);
  });
}
/* Whether an upgrade is under way, as far as this page knows (1.0.73): the
   plan says so, or a step is not finished, or it ended a short while ago -
   behind the web address the next answer may come from the node whose copy
   is a moment behind. */
function upRunning() {
  var p = UP.last && UP.last.plan;
  if (!p) return false;
  if (p.state === 'running') return true;
  if ((p.steps || []).some(function (st) { return st.state !== 'done' && st.state !== 'failed' && st.state !== 'cancelled' && st.state !== 'skipped'; })
      && p.state !== 'cancelled' && p.state !== 'failed') return true;
  return Date.now() / 1000 - Number(UP.endedAt || 0) < 120;
}
if ($('up-drop')) {
  (function () {
    var box = $('up-drop');
    var sending = false;
    function send(file) {
      if (!file || sending) return;     /* chosen twice: sent once (1.0.94) */
      sending = true;
      $('up-drop-says').textContent = 'checking ' + file.name + ' (' + bytes(file.size) + ')…';
      upgradeSend(file).then(function (d) {
        sending = false;
        toast(d.message || 'checked', 'good');
        $('up-drop-says').textContent = 'Drop the ai-X.Y.Z.tar.gz here, or press to choose it';
        drawUpgrade(d);
      }).catch(function (e) {
        sending = false;
        $('up-drop-says').textContent = 'Drop the ai-X.Y.Z.tar.gz here, or press to choose it';
        modal('The package was not taken', function (body) {
          body.appendChild(el('p', 'note bad', String(e.message || e)));
        }, null, true);
      });
    }
    box.onclick = function () { $('up-file').click(); };
    $('up-file').onchange = function () { send(this.files && this.files[0]); this.value = ''; };
    ['dragenter', 'dragover'].forEach(function (name) {
      box.addEventListener(name, function (e) { e.preventDefault(); box.classList.add('over'); });
    });
    ['dragleave', 'drop'].forEach(function (name) {
      box.addEventListener(name, function (e) {
        e.preventDefault();
        box.classList.remove('over');
        if (name === 'drop' && e.dataTransfer && e.dataTransfer.files) send(e.dataTransfer.files[0]);
      });
    });
    $('up-start').onclick = function () {
      var d = UP.last || {};
      var p = d.package || {};
      var names = (d.nodes || []).filter(function (n) { return n.alive; }).map(function (n) { return n.name; });
      var many = names.length > 1;
      if (p.downgrade) { upDownConfirm(p.version, function () {
        api('upgrade', {action: 'start'}).then(function (r) { toast(r.message, 'good'); drawUpgrade(r); }).catch(oops);
      }); return; }
      confirmThen('Upgrade this server to ' + p.version,
        'Its own install.sh --upgrade runs, as by hand. The terminals go on running; these pages stop answering for a few seconds while the daemon starts again.',
        'Upgrade', function () {
          api('upgrade', {action: 'start'}).then(function (r) { toast(r.message, 'good'); drawUpgrade(r); }).catch(oops);
        }, !many);
    };
    $('up-forget').onclick = function () {
      confirmThen('Throw the package away', 'The uploaded package is deleted; upload it again to upgrade.', 'Throw it away', function () {
        api('upgrade', {action: 'forget'}).then(function (r) { toast(r.message, 'good'); drawUpgrade(r); }).catch(oops);
      });
    };
    $('up-cancel').onclick = function () {
      confirmThen('Stop the upgrade', 'What is being put in right now is finished.', 'Stop it', function () {
        api('upgrade', {action: 'cancel'}).then(function (r) { toast(r.message, 'good'); drawUpgrade(r); }).catch(oops);
      });
    };
  }());
}

/* ---- about ---------------------------------------------------------------------------- */
function loadAbout() {
  api('machine').then(function (d) {
    var host = $('about-state'), m = d.machine;
    clear(host);
    host.appendChild(kvTable([
      ['ai', m.software.ai], ['Server', m.host + ' · ' + m.os],
      ['PHP of the pages', PHP_SAFETY ? PHP_SAFETY.version + (PHP_SAFETY.patched ? '' : (PHP_SAFETY.guarded ? ' - may not be fixed against php2shell; these pages are guarded' : ' - may not be fixed against php2shell')) : '–'],
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
/* Started once every script of the page is there (1.0.16): run where it
   stands, a page opened at #settings/network - F5 anywhere - asked for
   system.js's, cc.js's and usage.js's loaders before they were loaded, and
   the pane stayed empty. */
function startPage() {
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
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startPage);
else setTimeout(startPage, 0);

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
    mailViaShown();
    var nt = d.notices || {};
    $('mail-notices').textContent = nt.said ? 'The last notice: ' + ago(nt.at) + ' - ' + nt.said : '';
    return d;
  }).catch(oops);
}
function mailSteps(host, d) {
  clear(host);
  if (d.queued === 'waiting') {
    /* Through the outgoing mail: not taken yet, tried again by itself. */
    var p = el('p', 'note warn', 'Waiting in the outgoing mail: ' + d.said + ' - it is tried again by itself.');
    host.appendChild(p);
    var go = cmdButton('Outgoing mail', 'list', 'small');
    go.onclick = function () { showPane('mailq'); };
    host.appendChild(go);
  } else {
    host.appendChild(el('p', 'note ' + (d.sent ? 'good' : 'bad'), (d.sent ? (d.queued ? 'Sent through the outgoing mail: ' : 'Sent: ') : 'Not sent: ') + d.said
      + (d.took_ms !== undefined ? ' · ' + num(d.took_ms) + ' ms' : '')));
  }
  if ((d.steps || []).length) host.appendChild(stepsList(d.steps));
  host.appendChild(hideBar(function () { clear(host); }));
}
/* The choice of how a test mail goes - there only while mail goes
   straight to the recipient's server. */
function mailViaShown() {
  var via = $('mail-test-via');
  if (!via) return;
  var mode = $('set-mail_mode');
  var v = mode ? String(mode._get ? mode._get() : mode.value) : String(((settingByKey('mail_mode') || {}).value) || '');
  via.hidden = v !== 'direct';
}
document.addEventListener('change', function (e) {
  if (e.target && e.target.id === 'set-mail_mode') mailViaShown();
}, true);
$('mail-test').onclick = function () {
  var b = $('mail-test');
  /* Only a change to the mail settings stops the test, not one left on
     another page. */
  if (Object.keys(DIRTY || {}).some(function (k) { return /^(mail_|smtp_)/.test(k); })) {
    toast('save the mail settings first', 'bad'); return;
  }
  busy(b, true);
  var via = $('mail-test-via') && !$('mail-test-via').hidden ? $('mail-test-via').value : 'queue';
  api('mail', {action: 'test', to: $('mail-to').value.trim(), lang: $('mail-test-lang').value, kind: $('mail-test-kind') ? $('mail-test-kind').value : 'short', via: via}).then(function (d) {
    mailSteps($('mail-steps'), d);
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

/* ---- the database (as otp's Settings → The database) ---------------------------- */
var DBSTATE = null;
var ENGINE_SAID = {sqlite: 'the file on this machine', mariadb: 'MariaDB', postgres: 'PostgreSQL'};
var DUMP_SAID = {sqlite: 'a copy of the file', mariadb: 'a MariaDB dump',
                 postgres: 'a PostgreSQL dump', copy: 'a portable copy'};
var TABLE_SAID = {users: 'accounts', sessions: 'sign-ins', events: 'events', terms: 'terminals',
                  fails: 'wrong passwords counted', outbox: 'mails and SMS sent', mailq: 'mails waiting to go',
                  settings: 'settings', meta: 'notes of its own'};

function loadDb() {
  api('db').then(function (d) {
    DBSTATE = d;
    $('db-size').textContent = bytes(d.size) + ' · ' + d.where;
    drawEngine(d);
    drawDisk(d);
    drawCounts(d);
    keptTable($('db-backups'), d.copies || [], {
      kind: 'copy', head: 'Copies kept (' + d.keep + ' at most)',
      where: 'They are files on this machine, under ' + d.backup_dir + ', each with the key '
        + 'that opens its secrets beside it. Copy them off it if they are to survive the machine.'
    });
    keptTable($('db-dumps'), d.dumps || [], {
      kind: 'dump', head: 'Dumps kept (' + d.keep + ' at most)',
      where: 'They are files on this machine, under ' + d.dump_dir + ', each with the key '
        + 'that opens its secrets beside it. Copy them off it if they are to survive the machine.'
    });
    dumpCard(d);
    drawTune(d);
    drawErasable(d.erasable || {});
    if (d.job && d.job.running && ADMIN) dbWatch();     /* its progress is a full administrator's (1.0.146) */
    explainWhatWasDrawn($('pane-db'));
  }).catch(oops);
}

/* ---- which database everything is kept in -------------------------------- */
function dbAsked() {
  var out = {};
  ['db_engine', 'db_host', 'db_port', 'db_name', 'db_user', 'db_password', 'db_timeout_s'].forEach(function (k) {
    var input = $('set-' + k);
    if (!input) return;
    var v = input._get ? input._get() : input.value;
    if (k === 'db_password' && (v === '' || String(v).indexOf('•') === 0)) return;
    out[k] = (k === 'db_port' || k === 'db_timeout_s') ? (String(v).trim() === '' ? 0 : Number(v)) : v;
  });
  return out;
}
function engineChosen() { return String(dbAsked().db_engine || (DBSTATE && DBSTATE.engine) || 'sqlite'); }
function engineWord(name) { return ENGINE_SAID[name] || name; }

function drawEngine(d) {
  $('db-engine-file').textContent = d.config_file || 'the config file';
  $('db-engine-now').textContent = (ENGINE_SAID[d.engine] || d.engine) + ' · ' + d.where;
  var host = $('db-engine-says');
  clear(host);
  var c = d.counts || {};
  host.appendChild(peekFacts([
    ['In use now', d.version],
    ['Where', noI18n(el('span', 'mono', d.where))],
    ['Holding', num(c.users || 0) + ' account(s), ' + num(c.events || 0) + ' event(s)'],
    ['Room it takes', bytes(d.size || 0)]
  ]));
  /* Where the server on this machine listens, and the way to keep it to
     IPv4 there (1.0.26) - IPv6 switched on stays away from it. */
  if (d.listening) {
    var only4 = d.listening.length && d.listening.every(function (a) { return /^127\.0\.0\.1:/.test(a); });
    var lrow = el('div', 'btnrow db-listen');
    lrow.appendChild(el('span', 'small', txT('The server listens on') + ' '));
    lrow.appendChild(noI18n(el('span', 'mono small', d.listening.join(', ') || '–')));
    lrow.appendChild(el('span', 'tag ' + (only4 ? 'ok' : 'warn'), only4 ? 'IPv4, this machine only' : 'not IPv4 only'));
    if (!only4) {
      var b4 = cmdButton('Only IPv4 (127.0.0.1)', 'shield', 'small');
      b4.onclick = function () {
        confirmThen('The database server on IPv4 only?', 'It is told to listen on 127.0.0.1 only - nothing over IPv6, nothing from outside this machine - and started again: these pages wait a few seconds for it.', 'Do it', function () {
          busy(b4, true);
          api('db', {action: 'ipv4_only'}).then(function (r) { toast(r.message, 'good'); loadDb(); })
            .catch(oops).then(function () { busy(b4, false); });
        }, false);
      };
      lrow.appendChild(b4);
    }
    host.appendChild(lrow);
  }
  Object.keys(d.drivers || {}).forEach(function (name) {
    var one = d.drivers[name];
    host.appendChild(el('p', 'btnhelp', engineWord(name) + ': '
      + (one.ready ? 'the driver is installed'
         : (one.says || 'no driver') + ' — install ' + one.package)));
  });
  engineButtons();
}
function engineButtons() {
  var chosen = engineChosen();
  var live = String((DBSTATE && DBSTATE.engine) || 'sqlite');
  var same = chosen === live;
  if ($('db-engine-setup')) $('db-engine-setup').disabled = chosen === 'sqlite';
  if ($('db-engine-move')) $('db-engine-move').disabled = same;
  if ($('db-engine-empty')) $('db-engine-empty').disabled = same;
  if ($('db-engine-use')) $('db-engine-use').disabled = same;
}
document.addEventListener('change', function (e) {
  if (e.target && e.target.id === 'set-db_engine') engineButtons();
});

function engineFacts(d) {
  var facts = [['Reached', d.reached ? 'yes' : 'no'], ['Where', d.where || '']];
  if (d.version) facts.push(['It says it is', d.version]);
  if (d.reached) {
    facts.push(['Tables there', num((d.tables || []).length) + ' of ours']);
    facts.push(['Records in it', num(d.rows || 0)]);
    facts.push(['May this account write', d.writable ? 'yes' : 'NO']);
  }
  return peekFacts(facts);
}

/* ---- the job going on, and the bar that says how far ---------------------- */
var DB_WATCHING = null;
function dbBusyButtons(on) {
  ['db-backup', 'db-dump-make', 'db-optimize', 'db-check', 'db-prune', 'db-tidy',
   'db-restore', 'dump-restore', 'db-engine-move', 'erase-go'].forEach(function (id) {
    var b = $(id);
    if (b) b.disabled = on || (id === 'erase-go' && !erasePicked().length)
      || ((id === 'db-restore' || id === 'dump-restore') && !b._held);
  });
}
/* A bar that has finished gets Hide this; one that starts again loses it. */
function goingCloser(box) {
  if (!box || box.querySelector('.hide-row')) return;
  box.appendChild(hideBar(function () { box.hidden = true; }));
}
function goingOpen(box) {
  if (!box) return;
  box.hidden = false;
  var r = box.querySelector('.hide-row');
  if (r) r.remove();
}
function dbWatch(done) {
  if (DB_WATCHING) return;
  DB_WATCHING = true;     /* taken at once (1.0.57): two watchers ran when asked twice in one round trip */
  var box = $('db-going');
  goingOpen(box);
  dbBusyButtons(true);
  var step = function () {
    api('db', {action: 'job'}).then(function (d) {
      var j = d.job || {};
      var pct = j.whole ? Math.min(100, Math.round(100 * j.done / j.whole)) : (j.running ? 5 : 100);
      $('db-going-fill').style.width = pct + '%';
      $('db-going-says').textContent = (j.what || '') + (j.says ? ' — ' + j.says : '')
        + (j.whole ? ' (' + num(j.done) + ' of ' + num(j.whole) + ')' : '');
      /* Every second while the pane is open; every five once it is left, so
         the job's end is still told and the daemon is not asked for nothing. */
      if (j.running) { DB_WATCHING = setTimeout(step, TAB === 'settings' && PANE === 'db' ? 1000 : 5000); return; }
      DB_WATCHING = null;
      dbBusyButtons(false);
      goingCloser($('db-going'));
      if (j.error) { toast(j.what + ' failed: ' + j.error, 'bad'); $('db-going-says').textContent = j.error; return; }
      var r = j.result || {};
      if (r.rows !== undefined) {
        toast('everything is in ' + r.where + ': ' + num(r.rows) + ' row(s) — now Start using it', 'good');
        $('db-going-says').textContent = 'done: ' + num(r.rows) + ' row(s) in ' + r.where
          + ' · a copy made first: ' + r.copy;
      } else if (r.erased) {
        toast('erased; a copy was made first: ' + r.copy, 'good');
        $('db-going-says').textContent = 'done · a copy made first: ' + r.copy;
      } else if (r.before !== undefined) {
        toast('the disk is given back: ' + bytes(r.before) + ' → ' + bytes(r.after), 'good');
        $('db-going-says').textContent = 'done: ' + bytes(r.before) + ' → ' + bytes(r.after);
      }
      if (done) done(r);
      loadDb();
    }).catch(function (e) { DB_WATCHING = null; dbBusyButtons(false); oops(e); });
  };
  step();
}

/* ---- the disk under it ----------------------------------------------------- */
function drawDisk(d) {
  var host = $('db-disk');
  clear(host);
  var disk = d.disk || {};
  var grew = d.growth || {};
  var cache = d.cache;
  if (cache && cache.low) {
    var slow = el('p', 'note bad');
    slow.appendChild(el('b', '', cache.engine));
    slow.appendChild(document.createTextNode(' keeps '));
    slow.appendChild(el('b', '', bytes(cache.cache)));
    slow.appendChild(document.createTextNode(' of its own in memory ('));
    slow.appendChild(noI18n(el('span', 'mono', cache.setting)));
    slow.appendChild(document.createTextNode(') for a database of '));
    slow.appendChild(el('b', '', bytes(cache.size)));
    slow.appendChild(document.createTextNode('. Its indexes do not fit, so a busy minute waits for the disk. A quarter of the machine’s memory is the usual setting.'));
    host.appendChild(slow);
    if (ADMIN) {
      var go = cmdButton('Tune it for this machine…', 'gear', '');
      go.onclick = openTune;
      host.appendChild(go);
    }
  }
  if (!disk.total) {
    host.appendChild(el('p', 'note', 'The disk this is on could not be measured.'));
    return;
  }
  var share = Number(disk.share || 0);
  var line = el('div', 'disk-bar ' + (share >= 92 ? 'crit' : (share >= 80 ? 'warn' : 'ok')));
  var fill = el('span');
  fill.style.width = Math.max(1, Math.min(100, share)) + '%';
  line.appendChild(fill);
  host.appendChild(line);
  var says = el('p', 'note');
  says.appendChild(el('b', '', bytes(disk.free)));
  says.appendChild(document.createTextNode(' free of ' + bytes(disk.total) + ' on '));
  says.appendChild(noI18n(el('span', 'mono', disk.where || '')));
  says.appendChild(document.createTextNode(' — '));
  says.appendChild(el('span', '', share + '% of it is used'));
  if (grew.a_day) {
    says.appendChild(document.createTextNode(', and this database has been growing '));
    says.appendChild(el('b', '', bytes(grew.a_day)));
    says.appendChild(document.createTextNode(' a day over the last ' + grew.over_days + ' day(s).'));
  } else {
    says.appendChild(document.createTextNode('. How fast it is growing is not known yet: the size is noted once a day, and two are needed.'));
  }
  host.appendChild(says);
  host.appendChild(el('p', 'note', 'That disk holds ' + (disk.holds || '') + '.'));
  if (disk.days_left !== null && disk.days_left !== undefined) {
    host.appendChild(el('p', 'note ' + (disk.days_left < 45 ? 'bad' : ''), disk.days_left > 3650
      ? 'At that rate the disk has years left.'
      : 'At that rate the disk has about ' + num(disk.days_left) + ' day(s) left. Forgetting old records, under the keep-for numbers above, is what shortens it.'));
  }
  var parts = d.parts || [];
  if (parts.length) {
    var wrap = listTable([d.engine !== 'sqlite' ? 'Where' : 'File', 'What it is', {words: 'Size', cls: 'num'}],
      parts, function (one) {
        var tr = el('tr');
        tr.appendChild(noI18n(el('td', 'mono', one.name)));
        tr.appendChild(el('td', 'muted', one.what));
        tr.appendChild(el('td', 'num', bytes(one.bytes)));
        return tr;
      });
    wrap.style.marginTop = '10px';
    host.appendChild(wrap);
  }
}

/* ---- what is in it ----------------------------------------------------------- */
function drawCounts(d) {
  var host = $('db-counts');
  clear(host);
  var rows = (d.tables || []).slice().sort(function (a, b) {
    return (b.bytes || 0) - (a.bytes || 0) || b.rows - a.rows;
  });
  var known = rows.some(function (t) { return t.bytes !== null && t.bytes !== undefined; });
  host.appendChild(listTable(['What', 'Table', {words: 'Rows', cls: 'num'}]
      .concat(known ? [{words: 'Size', cls: 'num'}] : []), rows, function (t) {
    var tr = el('tr');
    tr.appendChild(el('td', '', TABLE_SAID[t.table] || t.table));
    tr.appendChild(noI18n(el('td', 'mono muted small', t.table)));
    tr.appendChild(el('td', 'num', num(t.rows)));
    if (known) tr.appendChild(el('td', 'num', t.bytes === null || t.bytes === undefined ? '–' : bytes(t.bytes)));
    return tr;
  }));
  var key = el('p', 'note ' + (d.key_there ? '' : 'bad'));
  key.appendChild(document.createTextNode(d.key_there ? 'The key that opens the secrets: ' : 'The key that opens the secrets is MISSING: '));
  key.appendChild(noI18n(el('span', 'mono', d.key)));
  host.appendChild(key);
  if (d.free) {
    host.appendChild(el('p', 'btnhelp', d.engine === 'postgres'
      ? num(d.free) + ' row(s) deleted and not yet given back to the disk.'
      : bytes(d.free) + ' free inside it, which the engine uses again; Give the disk back hands it to the operating system.'));
  }
}

/* ---- the two lists of files kept beside it --------------------------------- */
function keptTable(into, rows, opts) {
  clear(into);
  if (!into || !rows || !rows.length) return;
  var dump = opts.kind === 'dump';
  into.appendChild(el('h4', '', opts.head));
  into.appendChild(listTable(['Name', dump ? 'What it is' : 'Taken off', {words: 'Size', cls: 'num'},
                              'Made', 'Key beside it', {words: '', cls: 'act'}], rows, function (b) {
    var line = el('tr');
    line.appendChild(noI18n(el('td', 'mono', b.name)));
    var came = (dump ? DUMP_SAID[b.kind] : ENGINE_SAID[b.from]) || '';
    var mine = !dump || b.mine !== false;
    var off = el('td', came ? (mine ? '' : 'muted') : 'muted', came || 'not said');
    if (!mine) explain(off, 'This dump was taken off a different engine from the one this '
      + 'installation is on now, so it cannot be put back here. Put that engine back on, or '
      + 'use a copy — a copy goes into any of the three.');
    else if (dump && b.kind === 'copy') explain(off, 'Made on a night when the program that '
      + 'dumps this engine was not on the machine, so a portable copy was made instead. It is '
      + 'a whole copy and goes back into any of the three.');
    line.appendChild(off);
    line.appendChild(el('td', 'num', bytes(b.bytes)));
    line.appendChild(stampCell(b.at));
    line.appendChild(el('td', b.key ? 'good' : 'bad', b.key ? 'yes' : 'no'));
    var act = el('td', 'rowtools');
    if (ADMIN) {
      var take = cmdButton('Download', 'down', 'small');
      explain(take, dump
        ? 'Save this dump to the machine you are sitting at - with the key that opens its secrets, '
          + 'locked with a passphrase you give, or without it.'
        : 'Save this copy to the machine you are sitting at - with the key that opens its secrets, '
          + 'locked with a passphrase you give, or without it.');
      take.onclick = function () { dbDownloadAsk({name: b.name, kind: dump ? 'dump' : '', key: b.key}); };
      act.appendChild(take);
      var back = cmdButton('Restore', 'undo', 'small danger');
      explain(back, 'Put <b>this</b> one back, without downloading it and uploading it again: '
        + 'everything in the live database is replaced by what is in this file. You are shown '
        + 'what is in it and asked first, and a copy of what is being replaced is made before '
        + 'anything changes.');
      back.disabled = !mine;
      if (mine) back.onclick = function () { restoreKept(b, opts.kind); };
      act.appendChild(back);
      var gone = cmdButton('Delete', 'trash', 'small danger');
      explain(gone, 'Delete this file, and the key beside it, from the server. The live database is not touched.');
      gone.onclick = function () {
        confirmThen(dump ? 'Delete this dump?' : 'Delete this copy?', 'The file ' + htmlText(b.name)
          + ' and the key beside it are deleted from this machine. The live database is '
          + 'not touched, and the others stay where they are.', 'Delete it', function () {
            api('db', {action: 'delete', name: b.name, kind: opts.kind}).then(function (x) {
              toast(x.message, 'good');
              loadDb();
            }).catch(oops);
          });
      };
      act.appendChild(gone);
    }
    line.appendChild(act);
    return line;
  }));
  into.appendChild(el('p', 'btnhelp', opts.where));
}

function dumpCard(d) {
  var says = $('db-dump-says');
  clear(says);
  var info = d.dump || {};
  $('db-dump-now').textContent = info.words || '';
  $('db-dump-make').disabled = false;
  $('db-dump-get').disabled = false;
  if (info.ready) {
    var line = el('p', 'note good');
    line.appendChild(document.createTextNode('Tonight’s will be '));
    line.appendChild(el('b', '', info.words || 'a dump'));
    if (info.suffix) {
      line.appendChild(document.createTextNode(', written as '));
      line.appendChild(noI18n(el('code', '', info.suffix)));
    }
    line.appendChild(document.createTextNode('.'));
    says.appendChild(line);
  } else {
    says.appendChild(el('p', 'note bad', info.why || 'A dump cannot be made on this machine.'));
    var fix = el('p', 'note');
    fix.appendChild(document.createTextNode('Until it is there, the nightly one is made as a portable copy instead — a whole copy, which goes back into any engine, but several times the size of a dump. To have dumps: '));
    fix.appendChild(noI18n(el('code', '', info.install || '')));
    says.appendChild(fix);
  }
}

/* ---- putting one back ------------------------------------------------------- */
function restoreKept(b, kind) {
  api('db', {action: 'restore_kept', name: b.name, kind: kind, check: true}).then(function (d) {
    askBeforeRestoring(d.says, b.name, function () {
      return api('db', {action: 'restore_kept', name: b.name, kind: kind});
    });
  }).catch(oops);
}

function askBeforeRestoring(says, what, go) {
  var n = (says && says.counts) || {};
  var kind = (says && says.kind) || '';
  modal('Put this database back?', function (body) {
    var facts = [['File', noI18n(el('span', 'mono', String(what)))],
                 ['What it is', DUMP_SAID[kind] || kind], ['Size', bytes(says.bytes || 0)],
                 ['Tables', num(says.tables || 0)], ['Accounts', num(n.users || 0)],
                 ['Administrators', num(says.admins || 0)]];
    if (n.events !== undefined) facts.push(['Events', num(n.events)]);
    if (n.terms !== undefined) facts.push(['Terminals', num(n.terms)]);
    if (says.version) facts.push(['Made by ai', says.version]);
    /* Where it was made (1.0.63): the machine's config.json came with it, to
       be read - it is never put back. */
    var m = says.machine || null;
    if (m) {
      var use = m.in_use || {};
      facts.push(['Made on', noI18n(el('span', 'mono', String(m.node || '?') + (m.host ? ' (' + m.host + ')' : '')))]);
      facts.push(['Its database', noI18n(el('span', 'mono', String(use.db_engine || '?')
        + (use.db_engine && use.db_engine !== 'sqlite' ? ' ' + (use.db_host || '') + ':' + (use.db_port || '') + '/' + (use.db_name || '') : '')))]);
    }
    body.appendChild(peekFacts(facts));
    if (m && m.config) {
      var det = el('details', 'note');
      det.appendChild(el('summary', '', 'Its ' + (m.config_file || 'config.json') + ' (only to read: it is not put back)'));
      det.appendChild(noI18n(el('pre', 'mono', JSON.stringify(m.config, null, 1))));
      body.appendChild(det);
    }
    if (kind === 'mariadb' || kind === 'postgres') {
      body.appendChild(el('p', 'note', 'How many records are in a dump is not read from it — that is what putting it back is for.'));
    }
    var warn = el('p', 'note bad');
    warn.textContent = 'Putting it back replaces everything in the live database with what is in that file. A copy of what is being replaced is made first and kept with the others, so this can be undone — but everything recorded since that file was made will only be in that copy.';
    body.appendChild(warn);
    body.appendChild(el('p', 'btnhelp', 'You will probably be signed out: who is signed in came with the file like everything else. The key that opens the secrets is taken from beside the file, or from inside a downloaded copy; where there is none, the key in use stays.'));
  }, [
    {words: 'No, leave it', close: true},
    {words: 'Restore it', cls: 'danger', icon: 'undo', close: true, go: function () {
      go().then(function (done) {
        if (done && done.job) { setTimeout(function () { dbWatch(function () { setTimeout(function () { window.location.reload(); }, 2500); }); }, 50); return; }
        toast('the database was restored; what it replaced is in ' + done.safety + ' — ' + done.key, 'good');
        setTimeout(function () { window.location.reload(); }, 2500);
      }).catch(oops);
    }}], true);
}

/* A file to put back goes to the daemon's own folder for them, by the
   files' way in, under a name made here; then it is read there. */
function dbSend(file) {
  var up = '';
  var a = new Uint8Array(8);
  crypto.getRandomValues(a);
  for (var i = 0; i < a.length; i++) up += ('0' + a[i].toString(16)).slice(-2);
  return sendFile('/files/put?dir=' + encodeURIComponent((DBSTATE && DBSTATE.uploads) || '/var/lib/ai/db-uploads')
                  + '&name=' + up, file, function () {}).then(function () {
    return api('db', {action: 'upload_check', upload: up});
  });
}

/* ---- a copy or a dump with its key (1.0.123) ------------------------------
   Downloaded with the key that opens its secrets, locked with a passphrase -
   one file that is all of it - or without it; and the same file put back
   with the passphrase. */
function dbDownloadAsk(o) {
  var what = o.kind === 'dump' ? 'dump' : 'copy';
  modal(o.name ? 'Download ' + o.name : (what === 'dump' ? 'Download a dump made now' : 'Download a copy made now'), function (body) {
    var seg = el('div', 'seg');
    var withB = el('button', 'on', 'With the key'), noB = el('button', '', 'Without the key');
    withB.type = noB.type = 'button';
    seg.appendChild(withB); seg.appendChild(noB);
    body.appendChild(seg);
    var withBox = el('div');
    withBox.appendChild(el('p', 'note', what === 'dump'
      ? 'One file that is all of it: the dump and the key that opens its secrets, locked with the passphrase below. Put back here or on another machine (Put a dump back), the passphrase opens the key again. Lost, the key in the file is lost with it - it is not kept anywhere.'
      : 'One file that is all of it: the copy and the key that opens its secrets, locked with the passphrase below. Put back here or on another machine (Put a copy back), the passphrase opens the key again. Lost, the key in the file is lost with it - it is not kept anywhere.'));
    var p1 = secretBox('', '10 characters at least', 'mono');
    var p2 = secretBox('', 'the same again', 'mono');
    p1.id = 'dbk-p1'; p2.id = 'dbk-p2';
    var g = el('div', 'formgrid');
    g.appendChild(formField('Passphrase', p1));
    g.appendChild(formField('The passphrase again', p2));
    withBox.appendChild(g);
    body.appendChild(withBox);
    var noBox = el('div');
    noBox.hidden = true;
    noBox.appendChild(el('p', 'note warn', what === 'dump'
      ? 'The dump alone opens no secret on another machine: the key is the .key file beside it in /var/lib/ai/dumps (or /var/lib/ai/secrets.key). Keep the two together.'
      : 'The copy alone opens no secret on another machine: the key is the .key file beside it in /var/lib/ai/backups (or /var/lib/ai/secrets.key). Keep the two together.'));
    body.appendChild(noBox);
    body._with = true;
    withB.onclick = function () { body._with = true; withB.classList.add('on'); noB.classList.remove('on'); withBox.hidden = false; noBox.hidden = true; };
    noB.onclick = function () { body._with = false; noB.classList.add('on'); withB.classList.remove('on'); withBox.hidden = true; noBox.hidden = false; };
    MODAL_BODY_DBK = body;
  }, [
    {words: 'Cancel', close: true},
    {words: 'Download', cls: 'primary', icon: 'down', go: function (button) {
      var body = MODAL_BODY_DBK;
      if (!body._with) {
        closeModal();
        if (o.now) toast('it is being made; the download starts when it is ready', 'good');
        api('db', {action: 'download', name: o.name || '', kind: o.kind || ''}).then(function (t) {
          download(t.path);
        }).catch(oops);
        return;
      }
      var a = $('dbk-p1').value, b2 = $('dbk-p2').value;
      if (a.length < 10) { toast('a passphrase of 10 characters at least', 'bad'); return; }
      if (a !== b2) { toast('the two passphrases are not the same', 'bad'); return; }
      busy(button, true);
      if (o.now) toast('it is being made; the download starts when it is ready', 'good');
      api('db', {action: 'download_ticket', name: o.name || '', kind: o.kind || '', passphrase: a}).then(function (t) {
        closeModal();
        download(t.path);
        toast(t.name + ' - keep the passphrase apart from the file', 'good');
      }).catch(oops).then(function () { busy(button, false); });
    }}]);
}
var MODAL_BODY_DBK = null;
function dbAskPassphrase(d, fileName) {
  modal('The key in ' + fileName, function (body) {
    body.appendChild(el('p', 'note', 'This file holds the database and the key that opens its secrets, locked with a passphrase. Give it, and both are put back.'));
    var p = secretBox('', '', 'mono');
    p.id = 'dbk-open';
    body.appendChild(formField('Passphrase', p));
    setTimeout(function () { p.focus(); }, 50);
  }, [
    {words: 'Cancel', close: true},
    {words: 'Open it', cls: 'primary', icon: 'key', go: function (button) {
      var pass = $('dbk-open').value;
      busy(button, true);
      api('db', {action: 'upload_restore', upload: d.upload, passphrase: pass, check: true}).then(function (x) {
        closeModal();
        setTimeout(function () {
          askBeforeRestoring(x.says, fileName + ' (with its key)', function () {
            return api('db', {action: 'upload_restore', upload: d.upload, passphrase: pass});
          });
        }, 30);
      }).catch(oops).then(function () { busy(button, false); });
    }}]);
}
function dropBox(ids, empty) {
  var box = $(ids.drop);
  if (!box) return;
  var go = $(ids.go);
  function picked(file) {
    go._held = file || null;
    var says = $(ids.what);
    clear(says);
    says.hidden = !go._held;
    go.disabled = !go._held;
    $(ids.says).textContent = go._held ? go._held.name + ' · ' + bytes(go._held.size) : empty;
    if (!go._held) return;
    says.appendChild(el('p', 'btnhelp', 'Nothing has happened yet. Press Restore from this file and it will be read first — if it is not one of ours, if it is a dump of a different engine, or if it has no administrator in it, it is refused and nothing here changes.'));
  }
  box.onclick = function () { $(ids.file).click(); };
  $(ids.file).onchange = function () { picked(this.files && this.files[0]); this.value = ''; };
  ['dragenter', 'dragover'].forEach(function (name) {
    box.addEventListener(name, function (e) { e.preventDefault(); box.classList.add('over'); });
  });
  ['dragleave', 'drop'].forEach(function (name) {
    box.addEventListener(name, function (e) {
      e.preventDefault();
      box.classList.remove('over');
      if (name === 'drop' && e.dataTransfer && e.dataTransfer.files) picked(e.dataTransfer.files[0]);
    });
  });
  go.onclick = function () {
    var held = go._held;
    if (!held) return;
    busy(go, true);
    dbSend(held).then(function (d) {
      if (d.locked) { dbAskPassphrase(d, held.name); return; }
      askBeforeRestoring(d.says, held.name, function () {
        return api('db', {action: 'upload_restore', upload: d.upload});
      });
    }).catch(oops).then(function () { busy(go, false); });
  };
}

/* ---- the database server's own settings ---------------------------------- */
function drawTune(d) {
  var host = $('db-tune-says');
  clear(host);
  var t = d.tune || {};
  var file = d.engine === 'sqlite';
  $('db-tune').hidden = file;
  var last = t.last;
  $('db-tune-undo').hidden = file || !last || !!last.undone || last.engine !== d.engine;
  $('db-tune-restart').hidden = true;
  if (file) {
    host.appendChild(el('p', 'note', 'The file on this machine has no server to tune: this program sets it up itself.'));
    return;
  }
  if (last && last.engine === d.engine) {
    var p = el('p', 'note');
    if (last.undone) {
      p.appendChild(document.createTextNode('Put back as it was before'));
      p.appendChild(document.createTextNode(' ' + stamp(last.undone) + (last.undone_by ? ' · ' + last.undone_by : '') + '.'));
    } else {
      p.appendChild(document.createTextNode('Tuned for its machine'));
      p.appendChild(document.createTextNode(' ' + stamp(last.at) + (last.by ? ' · ' + last.by : '') + ':'));
      var set = last.set || {};
      Object.keys(set).sort().forEach(function (n, i) {
        p.appendChild(document.createTextNode(i ? ', ' : ' '));
        p.appendChild(noI18n(el('span', 'mono', n + ' = ' + set[n])));
      });
    }
    host.appendChild(p);
  } else {
    host.appendChild(el('p', 'note', 'Not tuned from this page yet.'));
  }
  if ((t.pending || []).length) {
    var w = el('p', 'note bad');
    w.appendChild(document.createTextNode('Waiting for the server’s next start:'));
    t.pending.forEach(function (n, i) {
      w.appendChild(document.createTextNode(i ? ', ' : ' '));
      w.appendChild(noI18n(el('span', 'mono', n)));
    });
    host.appendChild(w);
    if (t.restart && t.restart.may) {
      $('db-tune-restart').hidden = false;
    } else {
      if (t.restart && t.restart.why) host.appendChild(el('p', 'note', 'This program cannot restart it from here: ' + t.restart.why + '.'));
      host.appendChild(el('p', 'note', 'On the server, as root:'));
      host.appendChild(noI18n(el('pre', 'mono small', 'systemctl restart ' + ((t.restart && t.restart.unit) || 'postgresql'))));
      host.appendChild(el('p', 'btnhelp', 'Or let these pages do it: install.sh --upgrade puts in the rule that lets ai restart PostgreSQL on this machine, and nothing else (--no-db-restart takes it away).'));
    }
  }
  if ((t.lost || []).length) {
    var l = el('p', 'note bad');
    l.appendChild(document.createTextNode('MariaDB has been started again since, and these are back as they were:'));
    t.lost.forEach(function (n, i) {
      l.appendChild(document.createTextNode(i ? ', ' : ' '));
      l.appendChild(noI18n(el('span', 'mono', n)));
    });
    host.appendChild(l);
    host.appendChild(el('p', 'note', 'The file the popup gives keeps them over a restart.'));
  }
}

var TUNE = null;
function tuneAdminBoxes(body, engine) {
  var g = el('div', 'formgrid');
  var who = textBox(TUNE && TUNE.user || '', engine === 'postgres' ? 'postgres' : 'root', '');
  who.autocomplete = 'off';
  who.setAttribute('data-lpignore', 'true');
  var word = maskBox('', '', '');
  word.setAttribute('data-lpignore', 'true');
  word.value = TUNE && TUNE.pass || '';
  g.appendChild(formField('An administrator on that server', who, 'Only where ai’s own account may not change them. Used for this one request and stored nowhere: not in the settings, not in the database, not in any log.'));
  g.appendChild(formField('Its password', word));
  body.appendChild(g);
  return {who: who, word: word};
}
function tuneForget() {
  TUNE = null;
  Array.prototype.forEach.call(document.querySelectorAll('#modal-body input'), function (i) { i.value = ''; });
}
function tuneAsked() {
  var out = {machine: {}};
  if (!TUNE) return out;
  if (TUNE.boxes) { TUNE.user = TUNE.boxes.who.value.trim(); TUNE.pass = TUNE.boxes.word.value; }
  if (TUNE.hw) {
    TUNE.ram = TUNE.hw.ram.value.replace(',', '.').trim();
    TUNE.cpus = TUNE.hw.cpus.value.trim();
    TUNE.disk = TUNE.hw.disk.value;
  }
  if (TUNE.ram) out.machine.ram_gb = TUNE.ram;
  if (TUNE.cpus) out.machine.cpus = TUNE.cpus;
  if (TUNE.disk) out.machine.disk = TUNE.disk;
  out.admin_user = TUNE.user || '';
  out.admin_password = TUNE.pass || '';
  return out;
}
function openTune() {
  TUNE = {user: '', pass: '', ram: '', cpus: '', disk: '', plan: null};
  modal('Tuning the database server for its machine', function (body) {
    body.appendChild(el('p', 'note', 'Reading what the machine has and what the server is set to, and timing a few small writes…'));
  }, [{words: 'Close', close: true}], 'tune');
  MODAL_CLOSE = tuneForget;
  tuneLook();
}
function tuneLook(button) {
  var ask = tuneAsked();
  var ticket = modalTicket();
  if (button) busy(button, true);
  api('db', {action: 'tune_plan', machine: ask.machine}).then(function (d) {
    if (!modalStill(ticket)) return;
    TUNE.plan = d;
    tuneDraw(d);
  }).catch(function (e) {
    if (!modalStill(ticket)) return;
    if (button) busy(button, false);
    oops(e);
  });
}
function tuneValue(v) { return v === null || v === undefined || v === '' ? '–' : String(v); }
function tuneDraw(d, done) {
  var changes = (d.items || []).filter(function (it) { return it.change; });
  var buttons = [
    {words: 'Read again', icon: 'refresh', left: true, go: function (b) { tuneLook(b); }},
    {words: 'Close', close: true}
  ];
  if (changes.length) {
    buttons.splice(1, 0, {words: 'Put it in', cls: 'primary', icon: 'gear', admin: true,
                          go: function (b) { tuneApply(b); }});
  }
  /* What waits for the server's next start, started from here - as isemon
     does - where install.sh let this program restart it. */
  var waiting = (d.items || []).some(function (it) { return it.waiting || it.pending; });
  if (waiting && d.restart && d.restart.may) {
    buttons.splice(1, 0, {words: 'Restart the server…', cls: changes.length ? '' : 'primary',
                          icon: 'power', admin: true, go: function () { tuneRestartAsk(); }});
  }
  modal('Tuning ' + d.words + ' for its machine', function (body) {
    var f = d.facts || {};
    body.appendChild(peekFacts([
      ['Server', String(d.version || d.words).replace(/\s*\(.*\)\s*$/, '')],
      ['Where', d.where],
      ['Database', bytes(d.size)],
      f.ram ? ['Memory', bytes(f.ram)] : null,
      f.avail ? ['Free now', bytes(f.avail)] : null,
      f.cpus ? ['Processors', num(f.cpus)] : null,
      ['Disk', f.disk === 'hdd' ? 'a disk that spins' : 'SSD'],
      f.commit_ms !== null && f.commit_ms !== undefined
        ? ['A write made safe in', Number(f.commit_ms).toFixed(1).replace('.', numDecimal()) + ' ms'] : null,
      d.connections ? ['Connections allowed', num(d.connections)] : null
    ]));
    var from = {'this machine': 'Read from this machine, which the server runs on.',
                'typed': 'As typed below.'}[f.source || ''];
    if (from) body.appendChild(el('p', 'note', from));
    if (f.why && f.why !== 'chosen') body.appendChild(el('p', 'note', 'The disk: ' + f.why));
    if (d.need_facts) {
      body.appendChild(el('p', 'note bad', 'The server is on another machine and what it has could not be read from here. Type its memory and processors below and press Read again.'));
    }
    var row = el('div', 'tune-machine');
    var hw = {};
    [['ram', 'Memory, GB', f.ram ? String(Math.round(f.ram / 1073741824 * 10) / 10) : ''],
     ['cpus', 'Processors', f.cpus ? String(f.cpus) : '']].forEach(function (one) {
      var box = el('div', 'set-item');
      box.appendChild(el('label', '', one[1]));
      var input = el('input');
      input.type = 'text';
      input.inputMode = 'decimal';
      input.value = TUNE[one[0]] || one[2];
      box.appendChild(input);
      row.appendChild(box);
      hw[one[0]] = input;
    });
    var dbox = el('div', 'set-item');
    dbox.appendChild(el('label', '', 'Disk'));
    var sel = selectBox([['ssd', 'SSD'], ['hdd', 'a disk that spins']], TUNE.disk || f.disk || 'ssd');
    dbox.appendChild(sel);
    row.appendChild(dbox);
    hw.disk = sel;
    body.appendChild(row);
    TUNE.hw = hw;
    body.appendChild(el('p', 'btnhelp', 'Change any of these and press Read again: the settings are worked out afresh for what is typed.'));
    if (done) {
      if ((done.done || []).length || (done.later || []).length) {
        body.appendChild(el('p', 'note good', 'Put in: ' + ((done.done || []).join(', ') || 'nothing at once')
          + ((done.later || []).length ? ' · at the next start: ' + done.later.join(', ') : '')));
      }
      if ((done.failed || []).length) body.appendChild(el('p', 'note bad', 'Refused: ' + done.failed.join('; ')));
    }
    if ((d.items || []).length) {
      body.appendChild(el('h4', '', changes.length
        ? 'What would change' : 'Nothing to change: every setting is right for this machine'));
      var wrap = listTable(['Setting', 'Now', 'For this machine', 'Takes', 'Why'], d.items, function (it) {
        var tr = el('tr', it.change ? 'tune-change' : '');
        tr.appendChild(noI18n(el('td', 'mono', it.name)));
        tr.appendChild(noI18n(el('td', 'mono', tuneValue(it.now))));
        var want = el('td', 'mono ' + (it.change ? 'good' : 'muted'));
        want.appendChild(noI18n(el('span', '', tuneValue(it.want))));
        if (it.waiting) { want.appendChild(document.createTextNode(' ')); want.appendChild(el('span', 'tag warn', 'waiting for a start')); }
        tr.appendChild(want);
        tr.appendChild(el('td', it.restart ? 'warn' : 'muted', it.takes));
        tr.appendChild(el('td', 'muted small', it.why));
        return tr;
      }, 'plain tune-table');
      body.appendChild(wrap);
    }
    if (d.engine === 'postgres' && waiting && d.restart && !d.restart.may && d.restart.why) {
      body.appendChild(el('p', 'note bad', 'This program cannot restart it from here: ' + d.restart.why + '.'));
    }
    if (d.engine === 'postgres') {
      body.appendChild(el('p', 'btnhelp', d.restart && d.restart.may
        ? 'What takes effect only at the next start waits for it: Restart the server, under this popup, does that when you say so.'
        : 'What takes effect only at the next start waits for it: on the server, as root, systemctl restart ' + ((d.restart && d.restart.unit) || 'postgresql') + '.'));
    }
    if (d.engine === 'mariadb' && d.cnf) {
      body.appendChild(el('h4', '', 'To keep them over a restart'));
      body.appendChild(el('p', 'note', 'SET GLOBAL lasts until MariaDB is next started, and ai may not write in /etc. Put this in /etc/my.cnf.d/zz-ai-tuning.cnf on the server; the ones marked at the next start take effect only from there.'));
      body.appendChild(noI18n(el('pre', 'mono small', d.cnf)));
    }
    body.appendChild(el('h4', '', 'Who changes them'));
    TUNE.boxes = tuneAdminBoxes(body, d.engine);
  }, buttons, 'tune');
  MODAL_CLOSE = tuneForget;
}
function tuneApply(button) {
  var ask = tuneAsked();
  busy(button, true);
  api('db', {action: 'tune_apply', machine: ask.machine, admin_user: ask.admin_user,
             admin_password: ask.admin_password}).then(function (d) {
    TUNE.plan = d;
    tuneDraw(d, d);
    loadDb();
  }).catch(function (e) { busy(button, false); oops(e); });
}

/* ---- erasing what was collected ----------------------------------------- */
function drawErasable(d) {
  var host = $('erase-list');
  var was = {};
  Array.prototype.forEach.call(host.querySelectorAll('input[type=checkbox]'),
    function (b) { was[b.dataset.group] = b.checked; });
  clear(host);
  $('erase-size').textContent = bytes(d.bytes || 0) + ' in all';
  (d.groups || []).forEach(function (g) {
    var row = el('label', 'erase-one' + (g.rows ? '' : ' empty'));
    var box = document.createElement('input');
    box.type = 'checkbox';
    box.dataset.group = g.key;
    box.checked = !!was[g.key];
    box.disabled = !ADMIN || !g.rows;
    box.onchange = markErase;
    row.appendChild(box);
    var words = el('div', 'erase-words');
    var top = el('div', 'erase-top');
    top.appendChild(el('span', 'erase-name', g.name));
    top.appendChild(el('span', 'tag ' + (g.rows ? 'info' : 'dim'), g.rows ? num(g.rows) + ' row(s)' : 'already empty'));
    words.appendChild(top);
    words.appendChild(el('div', 'erase-says', g.says));
    row.appendChild(words);
    host.appendChild(row);
  });
  markErase();
}
function erasePicked() {
  return Array.prototype.filter.call(document.querySelectorAll('#erase-list input[type=checkbox]'),
    function (b) { return b.checked; }).map(function (b) { return b.dataset.group; });
}
function markErase() {
  var picked = erasePicked();
  var go = $('erase-go');
  go.disabled = !ADMIN || !picked.length || !!DB_WATCHING;
  setButtonIcon(go, 'forget', picked.length ? 'Erase ' + picked.length + ' of these…' : 'Erase what is ticked…');
}

/* ---- Move to another database… (1.0.54): a wizard, step by step, Back and
   Next - where to, how to reach it, what is there - and then one job that
   does it all: a copy here, the other one made and (if agreed) emptied,
   everything carried in and counted table by table, the address written
   into config.json and the daemon started again on it. Nothing changes here
   until that last step; a move that fails leaves this installation as it was. */
var MIG = null;
function migDefaults() {
  var live = (DBSTATE && DBSTATE.engine) || 'sqlite';
  var to = live === 'sqlite' ? 'postgres' : 'sqlite';
  /* What the settings above say (1.0.56) is where it starts: the same server,
     account and encryption are the likeliest for the other engine too. */
  var v = function (k, d) { var x = settingByKey(k); return x && x.value !== undefined && x.value !== null && x.value !== '' && String(x.value).charAt(0) !== '•' ? x.value : d; };
  var server = live !== 'sqlite';
  return {step: 0, to: to, host: server ? v('db_host', '') : '', port: 0, name: server ? v('db_name', 'ai') : 'ai',
          user: server ? v('db_user', 'ai') : 'ai', password: '', tls: server ? v('db_tls', '') : '',
          tls_ca: server ? v('db_tls_ca', '') : '', timeout: v('db_timeout_s', 10),
          admin_user: '', admin_password: '', empty_first: false, switch_over: true, check: null};
}
function migSettings() {
  var m = MIG, out = {db_engine: m.to};
  if (m.to !== 'sqlite') {
    out.db_host = m.host; out.db_port = Number(m.port) || 0; out.db_name = m.name; out.db_user = m.user;
    out.db_tls = m.tls; out.db_tls_ca = m.tls_ca; out.db_timeout_s = Number(m.timeout) || 10;
    if (m.password) out.db_password = m.password;
  }
  return out;
}
var MIG_STEPS = ['Where to', 'How to reach it', 'What is there', 'Go', 'Moving'];
function migOpen() {
  MIG = migDefaults();
  modal('Move to another database', function () {}, [], 'medium');
  migDraw();
}
function migSteps(body) {
  var bar = el('div', 'mig-steps');
  MIG_STEPS.forEach(function (w, i) {
    if (i === 1 && MIG.to === 'sqlite') return;
    var one = el('span', 'mig-step' + (i === MIG.step ? ' now' : (i < MIG.step ? ' done' : '')));
    one.appendChild(el('b', '', String(i + 1 - (MIG.to === 'sqlite' && i > 1 ? 1 : 0))));
    one.appendChild(el('span', '', w));
    bar.appendChild(one);
  });
  body.appendChild(bar);
}
function migFoot(buttons) {
  var foot = $('modal-foot');
  clear(foot);
  var made = [];
  buttons.forEach(function (b) {
    if (!b) return;
    var x = cmdButton(b.words, b.icon || '', b.cls || '');
    if (b.left) x.classList.add('left');
    x.disabled = !!b.off;
    x.onclick = function () { b.go(x); };
    foot.appendChild(x);
    made.push(x);
  });
  return made;
}
function migGo(to) { MIG.step = to; migDraw(); }
function migDraw() {
  var body = $('modal-body');
  clear(body);
  migSteps(body);
  var m = MIG, live = (DBSTATE && DBSTATE.engine) || 'sqlite';
  var back = function (n) { return {words: 'Back', icon: 'prev', left: true, go: function () { migGo(n); }}; };
  var close = {words: 'Close', icon: 'close', go: closeModal};
  if (m.step === 0) {
    body.appendChild(el('p', 'note', 'Everything this installation holds - the accounts and their sign-ins, the settings, the events, the terminals, the mails - is in one database. This moves all of it into another one. Nothing here changes until the very last step.'));
    var cards = el('div', 'mig-cards');
    [['sqlite', 'The file on this machine', 'SQLite - nothing to install or run, one file in the state folder. Right for one server.'],
     ['mariadb', 'MariaDB', 'A server - on this machine or another. The account and the database are made by the wizard.'],
     ['postgres', 'PostgreSQL', 'A server - on this machine or another. The account and the database are made by the wizard.']].forEach(function (e) {
      var drv = ((DBSTATE && DBSTATE.drivers) || {})[e[0]];
      var inUse = e[0] === live && live === 'sqlite';
      var c = el('button', 'mig-card' + (m.to === e[0] ? ' on' : '') + (inUse ? ' off' : ''));
      c.type = 'button';
      c.disabled = inUse;
      c.appendChild(el('b', '', e[1]));
      c.appendChild(el('span', 'small muted', e[2]));
      if (e[0] === live) {
        c.appendChild(el('span', 'tag ' + (inUse ? 'dim' : 'warn'), 'in use now'));
        if (!inUse) c.appendChild(el('span', 'small muted', 'Another server or another database of it can still be chosen.'));
      }
      if (drv && !drv.ready) c.appendChild(el('span', 'tag bad', 'no driver: ' + drv.package));
      c.onclick = function () { m.to = e[0]; m.check = null; migDraw(); };
      cards.appendChild(c);
    });
    body.appendChild(cards);
    body.appendChild(el('p', 'btnhelp', 'In use now: ' + engineWord(live) + ' · ' + ((DBSTATE && DBSTATE.where) || '')));
    migFoot([close, {words: 'Next', icon: 'next', cls: 'primary', go: function () { migGo(m.to === 'sqlite' ? 2 : 1); }}]);
    return;
  }
  if (m.step === 1) {
    body.appendChild(el('p', 'note', 'How this program reaches ' + engineWord(m.to) + '. The server must be running; the database and the account need not exist yet - the next step makes them.'));
    var g = el('div', 'formgrid');
    var fld = function (label, key, input, says) {
      input.value = m[key] === undefined || m[key] === null ? '' : String(m[key]);
      input.addEventListener('input', function () { m[key] = input._get ? input._get() : input.value; m.check = null; });
      input.addEventListener('change', function () { m[key] = input.value; m.check = null; });
      g.appendChild(formField(label, input, says));
      return input;
    };
    fld('Server', 'host', textBox('', 'empty: this machine', 'mono'), 'Its name or address.');
    fld('Port', 'port', textBox('', m.to === 'postgres' ? '5432' : '3306', 'mono'), '0 or empty: the engine’s own.');
    fld('Database', 'name', textBox('', 'ai', 'mono'), 'Letters, digits and _ only.');
    fld('Account', 'user', textBox('', 'ai', 'mono'), 'The account this program signs in with.');
    fld('Its password', 'password', maskBox('', 'empty: one is made and kept', 'mono'), 'Empty: a strong one is made when the account is made, and kept in config.json (root only).');
    fld('Encrypted', 'tls', selectBox([['', 'as the driver decides'], ['require', 'encrypted, the certificate not checked'],
      ['verify-ca', 'encrypted, signed by the authority below'], ['verify-full', 'encrypted, the authority and the name checked']], m.tls), 'How the connection is encrypted.');
    fld('The authority of its certificate (a file)', 'tls_ca', textBox('', '/etc/pki/…/ca.pem', 'mono'), 'Only for the two checked kinds.');
    fld('Wait for it (s)', 'timeout', textBox('', '10', 'mono'), 'How long a connection is waited for.');
    body.appendChild(g);
    migFoot([back(0), close, {words: 'Next', icon: 'next', cls: 'primary', go: function () {
      if (!/^[A-Za-z_][A-Za-z0-9_]{0,62}$/.test(m.name) || !/^[A-Za-z_][A-Za-z0-9_]{0,62}$/.test(m.user)) { toast('the database and the account are letters, digits and _ only', 'bad'); return; }
      migGo(2);
    }}]);
    return;
  }
  if (m.step === 2) {
    var box = el('div');
    body.appendChild(box);
    var ask = function (b) {
      if (b) busy(b, true);
      box.appendChild(el('p', 'note', 'Reaching it…'));
      api('db', {action: 'migrate_check', settings: migSettings(), admin_user: m.admin_user, admin_password: m.admin_password})
        .then(function (d) { m.check = d; migDraw(); })
        .catch(function (e) { m.check = {trouble: String(e.message || e), failed: true}; migDraw(); });
    };
    var c = m.check;
    if (!c) { migFoot([back(m.to === 'sqlite' ? 0 : 1), close]); ask(); return; }
    var t = c.try || {};
    var canNow = function () {};
    var facts = [['Where', noI18n(el('span', 'mono', c.where || ''))]];
    if (t.reached) {
      facts.push(['It says it is', t.version || '']);
      facts.push(['Records of ours in it', num(c.rows || 0)]);
      facts.push(['May the account write', t.writable ? 'yes' : 'NO']);
    } else if (c.where) facts.push(['Reached', c.needs_admin ? 'not with that account yet' : 'no']);
    box.appendChild(peekFacts(facts));
    var ready = !c.failed && !c.same && !(c.driver && !c.driver.ready);
    if (c.trouble && !c.needs_admin) box.appendChild(el('p', 'note bad', c.trouble));
    if (c.needs_admin && ready) {
      box.appendChild(el('p', 'note', 'The database and its account are made by an administrator of that server - root on MariaDB, postgres on PostgreSQL, or anyone who may create a database and an account. It is used for this one move and kept nowhere: not in the settings, not in the database, not in any log.'));
      if (t.trouble) box.appendChild(el('p', 'btnhelp mig-trouble', 'With the account: ' + t.trouble));
      var ga = el('div', 'formgrid');
      var au = textBox(m.admin_user, m.to === 'postgres' ? 'postgres' : 'root', 'mono');
      au.addEventListener('input', function () { m.admin_user = au.value.trim(); canNow(); });
      var ap = maskBox('', '', 'mono');
      ap.value = m.admin_password;
      ap.addEventListener('input', function () { m.admin_password = ap.value; });
      ga.appendChild(formField('An administrator of that server', au));
      ga.appendChild(formField('Its password', ap));
      box.appendChild(ga);
    }
    if (c.rows && ready) {
      var sw = switchBox(m.empty_first);
      sw._input.addEventListener('change', function () { m.empty_first = !!sw._get(); migDraw(); });
      box.appendChild(el('p', 'note bad', 'There are ' + num(c.rows) + ' record(s) of ours in it already - an earlier move, or another installation. Moving into it as it is would mix the two.'));
      box.appendChild(formField('Throw away what is in it first (never the one in use)', sw));
    } else if (t.reached && t.writable && ready) {
      box.appendChild(el('p', 'note good', 'Reachable, writable and empty of ours - exactly what a move needs.'));
    }
    var can = function () { return ready && (!c.needs_admin || !!m.admin_user) && (!c.rows || m.empty_first); };
    var bs = migFoot([back(m.to === 'sqlite' ? 0 : 1), close,
      {words: 'Check again', icon: 'refresh', go: function (b) { m.check = null; ask(b); }},
      {words: 'Next', icon: 'next', cls: 'primary', off: !can(), go: function () { migGo(3); }}]);
    canNow = function () { bs[bs.length - 1].disabled = !can(); };
    return;
  }
  if (m.step === 3) {
    var n = (m.check && m.check.counts) || (DBSTATE && DBSTATE.counts) || {};
    var total = 0;
    Object.keys(n).forEach(function (k) { total += Number(n[k] || 0); });
    body.appendChild(peekFacts([
      ['Moved from', engineWord(live) + ' · ' + ((DBSTATE && DBSTATE.where) || '')],
      ['Moved to', (function () { var w = el('span'); w.appendChild(el('span', '', engineWord(m.to))); w.appendChild(document.createTextNode(' · ')); w.appendChild(noI18n(el('span', 'mono', (m.check && m.check.where) || ''))); return w; })()],
      ['What goes', num(total) + ' row(s): ' + num(n.users || 0) + ' account(s), ' + num(n.events || 0) + ' event(s), ' + num(n.terms || 0) + ' terminal(s)']
    ]));
    var ol = el('ol', 'mig-plan');
    [(m.check && m.check.needs_admin) ? (m.password ? 'the database and its account made on ' + engineWord(m.to) : 'the database and its account made on ' + engineWord(m.to) + ', with a password made here') : 'the other database reached',
     m.empty_first ? 'what is in it thrown away first' : 'it is checked to be empty',
     'a copy of everything here made (kept with the others - the way back)',
     'everything carried in',
     'every table counted on both sides - a move that lost anything stops here',
     m.switch_over ? 'the address written into config.json and the daemon started again on it (a few seconds; the terminals go on running)' : 'left at that: you switch over later'].forEach(function (w) { ol.appendChild(el('li', '', w)); });
    body.appendChild(ol);
    var sw2 = switchBox(m.switch_over);
    sw2._input.addEventListener('change', function () { m.switch_over = !!sw2._get(); migDraw(); });
    body.appendChild(formField('Switch over to it at the end', sw2, 'Off: everything is carried in and checked, and this installation stays on the one in use.'));
    body.appendChild(el('p', 'btnhelp', 'Until the switch nothing here changes and nothing is written into config.json. Anything recorded during the move itself (a few seconds) stays only in the copy made first.'));
    migFoot([back(2), close, {words: 'Start the move', icon: 'power', cls: 'primary', go: function (b) {
      busy(b, true);
      api('db', {action: 'migrate', settings: migSettings(), admin_user: m.admin_user, admin_password: m.admin_password,
                 empty_first: m.empty_first, switch: m.switch_over}).then(function () { m.job = null; migGo(4); migPoll(); })
        .catch(function (e) { busy(b, false); oops(e); });
    }}]);
    return;
  }
  /* step 4: moving */
  var j = m.job || {};
  var bar = el('div', 'going wide mig-going' + (j.error ? ' failed' : ''));
  var pct = j.whole ? Math.min(100, Math.round(100 * j.done / j.whole)) : 3;
  bar.innerHTML = '<div class="bar"><span style="width:' + (j.running === false && !j.error ? 100 : pct) + '%"></span></div>';
  var says = el('div', 'says', j.error ? 'stopped at: ' + (j.says || 'the start') : (j.says || 'starting'));
  bar.appendChild(says);
  body.appendChild(bar);
  var r = j.result;
  if (j.error) {
    body.appendChild(el('p', 'note bad', 'The move stopped: ' + j.error));
    body.appendChild(el('p', 'btnhelp', 'Nothing here was changed and this installation goes on as it was. Go back, put it right and start it again.'));
    migFoot([back(2), close]);
    return;
  }
  if (r) {
    body.appendChild(el('p', 'note good', 'Everything is in ' + engineWord(r.engine) + ': ' + num(r.rows) + ' row(s), every table counted on both sides. The copy made first: ' + r.copy + '.'));
    if (r.password) {
      body.appendChild(el('p', 'note', 'The password made for the account (kept in config.json - shown this once):'));
      var pw = textBox(r.password, '', 'mono'); pw.readOnly = true; noI18n(pw);
      body.appendChild(pw);
    }
    if (r.switched) {
      var wait = el('p', 'note', 'The daemon is starting again on it…');
      body.appendChild(wait);
      migFoot([]);
      migBack(wait);
    } else {
      body.appendChild(el('p', 'note', 'Not switched over: this installation stays on ' + engineWord(live) + '. Run the wizard again with the switch on when you want it.'));
      migFoot([close]);
    }
    return;
  }
  migFoot([{words: 'Hide - it goes on', icon: 'close', go: closeModal}]);
}
function migPoll() {
  api('db', {action: 'job'}).then(function (d) {
    var j = d.job || {};
    if (!MIG) return;
    MIG.job = j;
    if (!$('modal').hidden && MIG.step === 4) migDraw();
    if (j.running) setTimeout(migPoll, 800);
    else loadDb();
  }).catch(function () { setTimeout(migPoll, 1500); });
}
/* Waits for the daemon to answer again on the new database, then reloads. */
function migBack(line) {
  var tries = 0;
  var again = function () {
    tries += 1;
    api('db').then(function (d) {
      if (d.engine === MIG.to) { line.textContent = 'Running on ' + engineWord(d.engine) + ' now - the page is loaded again.'; setTimeout(function () { location.reload(); }, 1500); }
      else if (tries < 60) setTimeout(again, 2000);
    }).catch(function () { if (tries < 60) setTimeout(again, 2000); else line.textContent = 'The daemon has not answered for two minutes: systemctl status ai'; });
  };
  setTimeout(again, 4000);
}
if ($('db-migrate')) $('db-migrate').onclick = migOpen;
{
  $('db-backup').onclick = function () {
    busy($('db-backup'), true);
    api('db', {action: 'backup'}).then(function (x) { toast(x.message, 'good'); loadDb(); })
      .catch(oops).then(function () { busy($('db-backup'), false); });
  };
  $('db-download').onclick = function () { dbDownloadAsk({kind: '', now: true, key: true}); };
  $('db-dump-make').onclick = function () {
    busy($('db-dump-make'), true);
    toast('dumping — this takes as long as the database is big');
    api('db', {action: 'dump'}).then(function (d) {
      toast('a dump was made: ' + d.name + ' (' + bytes(d.bytes) + ')', 'good');
      loadDb();
    }).catch(oops).then(function () { busy($('db-dump-make'), false); });
  };
  $('db-dump-get').onclick = function () { dbDownloadAsk({kind: 'dump', now: true, key: true}); };
  $('db-tidy').onclick = function () {
    busy($('db-tidy'), true);
    api('db', {action: 'tidy'}).then(function (x) { toast(x.message, 'good'); loadDb(); })
      .catch(oops).then(function () { busy($('db-tidy'), false); });
  };
  $('db-check').onclick = function () {
    busy($('db-check'), true);
    api('db', {action: 'check'}).then(function (d) {
      modal(d.ok ? 'Nothing in it is broken' : 'Something in it is broken', function (body) {
        var ul = el('ul', 'note');
        (d.said || []).forEach(function (one) { ul.appendChild(noI18n(el('li', 'mono small', one))); });
        body.appendChild(ul);
      }, [{words: 'Close', close: true}], true);
    }).catch(oops).then(function () { busy($('db-check'), false); });
  };
  $('db-optimize').onclick = function () {
    confirmThen('Give the disk back', 'Each table is rebuilt and held shut while it is; sign-ins and the pages wait '
      + 'for it meanwhile - do it when few are signed in. It needs room for a second copy of the biggest table. Worth '
      + 'doing after throwing a lot away, and not otherwise.', 'Give it back',
      function () { api('db', {action: 'give_back'}).then(function () { dbWatch(); }).catch(oops); }, false);
  };
  $('db-prune').onclick = function () {
    var days, everything;
    modal('Forget records older than…', function (body) {
      body.appendChild(el('p', 'note', 'The events and the lines of the mails sent older than this are '
        + 'deleted now, whatever the keep-for numbers say. The accounts, the settings and the terminals are not touched.'));
      days = el('input'); days.type = 'number'; days.min = 1; days.value = 90;
      body.appendChild(formField('Older than (days)', days));
      everything = switchBox(false);
      everything._input.addEventListener('change', function () { days.disabled = !!everything._get(); });
      body.appendChild(formField('Every line, whatever its age — the whole log emptied', everything));
    }, [{words: 'Close', close: true}, {words: 'Forget them', cls: 'danger', icon: 'forget', go: function (b) {
      busy(b, true);
      api('db', {action: 'prune', days: Number(days.value), everything: !!everything._get()}).then(function (d) {
        toast(d.message, 'good'); closeModal(); loadDb();
      }).catch(oops).then(function () { busy(b, false); });
    }}], 'medium');
  };
  $('db-tune').onclick = openTune;
  $('db-tune-restart').onclick = function () { tuneRestartAsk(); };
}
function tuneRestartAsk() {
  {
    var unit = ((DBSTATE && DBSTATE.tune && DBSTATE.tune.restart) || {}).unit || 'postgresql';
    modal('Restart ' + unit, function (body) {
      body.appendChild(el('p', 'note', 'PostgreSQL is stopped and started again so that the settings waiting for its next start take effect. It takes a few seconds; these pages wait for it meanwhile and carry on as soon as it is back.'));
      body.appendChild(el('p', 'note', 'Not done when it might not come back: a shared_buffers larger than the memory free now, or huge pages.'));
    }, [{words: 'Not now', close: true}, {words: 'Restart it', cls: 'primary', icon: 'power', go: function (b) {
      busy(b, true);
      api('db', {action: 'tune_restart'}).then(function (d) {
        toast(d.message, 'good'); closeModal(); loadDb();
      }).catch(function (e) { busy(b, false); oops(e); });
    }}], true);
  }
}
if ($('db-tune-undo')) {
  $('db-tune-undo').onclick = function () {
    var user, pass;
    modal('Put back as it was', function (body) {
      body.appendChild(el('p', 'note', 'Every setting this page changed goes back to what it was before. Empty: ai’s own account, where it has that right.'));
      var g = el('div', 'formgrid');
      user = textBox('', DBSTATE && DBSTATE.engine === 'postgres' ? 'postgres' : 'root', '');
      pass = maskBox('', '', '');
      g.appendChild(formField('An administrator on that server', user));
      g.appendChild(formField('Its password', pass, 'Used for this one request; kept nowhere.'));
      body.appendChild(g);
    }, [{words: 'Close', close: true}, {words: 'Put it back', cls: 'primary', icon: 'undo', go: function (b) {
      busy(b, true);
      api('db', {action: 'tune_undo', admin_user: user.value.trim(), admin_password: pass.value}).then(function (d) {
        toast('put back: ' + (d.done || []).join(', '), 'good'); closeModal(); loadDb();
      }).catch(oops).then(function () { busy(b, false); });
    }}], 'medium');
  };
  $('erase-go').onclick = function () {
    var picked = erasePicked();
    if (!picked.length) return;
    var names = Array.prototype.filter.call(document.querySelectorAll('#erase-list input[type=checkbox]'),
      function (b) { return b.checked; }).map(function (b) {
        return b.closest('.erase-one').querySelector('.erase-name').textContent;
      });
    modal(picked.length === 1 ? 'Erase this?' : 'Erase these ' + picked.length + '?', function (body) {
      body.appendChild(el('p', 'note', 'This erases, for good:'));
      var ul = el('ul', 'ask-list');
      names.forEach(function (n) { ul.appendChild(el('li', '', n)); });
      body.appendChild(ul);
      body.appendChild(el('p', 'note', 'The accounts, the terminals and every setting are not touched.'));
      body.appendChild(el('p', 'muted', 'A copy of the database is made first, so this can be undone by restoring it.'));
    }, [{words: 'No, leave it', close: true}, {words: 'Erase it', cls: 'danger', icon: 'forget', close: true, go: function () {
      api('db', {action: 'erase', groups: picked, tidy: $('erase-tidy').checked}).then(function () {
        dbWatch();
      }).catch(oops);
    }}], true);
  };
  dropBox({drop: 'db-drop', file: 'db-file', says: 'db-drop-says', what: 'db-upload-what', go: 'db-restore'},
          'Drop a database file here, or press to choose one');
  dropBox({drop: 'dump-drop', file: 'dump-file', says: 'dump-drop-says', what: 'dump-upload-what', go: 'dump-restore'},
          'Drop a dump here, or press to choose one');
}

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
        phrase = maskBox('', 'the passphrase', 'mono');
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
  /* The last try (1.0.52, otp's 1.0.169): whether the newest backup can be put back. */
  var tried = (d.verified || []).filter(function (v) { return v.node === d.node; })[0];
  fact('Tried', tried ? (tried.ok ? 'can be put back' : 'NOT GOOD') + ' · ' + ago(tried.at) : 'never', tried ? (tried.ok ? 'good' : 'bad') : 'warn');
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
  var tryb = cmdButton('Try the newest', 'check', '');
  tryb.disabled = !on.length || (d.job && d.job.running);
  explain(tryb, 'The newest backup of this server fetched back from the first destination, opened with the password, every file checked, the database read through and the secrets tried against the key in it - nothing is put back. And the newest nightly copy here read through.');
  tryb.onclick = function () {
    busy(tryb, true);
    api('rbackup', {action: 'verify'}).then(function (x) { toast(x.message, 'good'); RB.job = x.job; rbWatch(); })
      .catch(function (e) { busy(tryb, false); oops(e); });
  };
  acts.appendChild(tryb);
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
  RB.verified = d.verified || [];
  drawRbTried();
}
/* The backups tried (1.0.52, otp's 1.0.169): each try, every check of it; the
   list can be emptied, or a try taken off - the backups themselves stay. */
function drawRbTried() {
  var card = $('rb-tried-card'), host = $('rb-tried'), tools = $('rb-tried-tools');
  if (!card) return;
  var rows = RB.verified || [];
  card.hidden = !rows.length;
  clear(host);
  clear(tools);
  if (!rows.length) return;
  var forget = function (q) {
    api('rbackup', Object.assign({action: 'verified_forget'}, q)).then(function (d) {
      toast(d.message, 'good'); RB.verified = d.verified || []; drawRbTried(); drawRbTop();
    }).catch(oops);
  };
  var wipe = cmdButton('Clear the list', 'trash', 'small');
  wipe.onclick = function () {
    confirmThen('Clear the list of backups tried?', 'Every try goes from this list. <b>The backups themselves stay where they are.</b> Events keeps a line saying who cleared it.', 'Clear the list', function () { forget({all: 1}); }, true);
  };
  tools.appendChild(wipe);
  var list = el('div', 'rb-tried');
  rows.slice(0, 8).forEach(function (v, i) {
    var it = el('details', 'rb-try ' + (v.ok ? 'good' : 'bad'));
    if (i === 0 && !v.ok) it.open = true;
    var sm = el('summary');
    sm.appendChild(el('span', 'dot ' + (v.ok ? 'ok' : 'bad')));
    sm.appendChild(el('b', '', v.ok ? 'Can be put back' : 'Not good'));
    sm.appendChild(noI18n(el('span', 'mono small', v.file || '?')));
    sm.appendChild(el('span', 'muted small', '·'));
    sm.appendChild(el('span', 'muted small', ago(v.at)));
    sm.appendChild(el('span', 'muted small', '·'));
    sm.appendChild(noI18n(el('span', 'muted small', (v.node || '') + ' → ' + (v.target_name || ''))));
    var x = el('button', 'xbtn rb-try-x');
    x.type = 'button';
    x.setAttribute('data-icon', 'close');
    x.title = 'Take it off the list';
    x.onclick = function (e) { e.preventDefault(); e.stopPropagation(); forget({at: v.at}); };
    sm.appendChild(x);
    it.appendChild(sm);
    var ul = el('div', 'rb-checks');
    (v.checks || []).forEach(function (k) {
      var row = el('div', 'rb-check');
      row.appendChild(el('span', 'dot ' + (k.ok ? 'ok' : 'bad')));
      row.appendChild(el('span', '', k.what));
      if (k.said) row.appendChild(noI18n(el('span', 'muted small', '- ' + k.said)));
      ul.appendChild(row);
    });
    it.appendChild(ul);
    list.appendChild(it);
  });
  host.appendChild(list);
  dressButtons(host);
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
      else if (j.result && j.what === 'verify') toast(j.result.ok ? 'the backup was tried: it can be put back' : 'the backup was tried: it is NOT good', j.result.ok ? 'good' : 'bad');
      else if (j.result) toast(j.result.ok ? 'the backup went to every destination' + (j.result.verified ? ' - and it can be put back' : '') : 'the backup did not reach every destination', j.result.ok ? 'good' : 'bad');
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

/* ---- what it runs on (as otp's About) ---------------------------------------------- */
function drawSoftware(host) {
  var box = el('div', 'sw-box');
  host.appendChild(box);
  box.appendChild(el('h3', 'sw-h', 'What it runs on'));
  var wait = el('p', 'muted small', 'asking…');
  box.appendChild(wait);
  api('software').then(function (d) {
    box.removeChild(wait);
    var nodes = d.nodes || [];
    var pages = d.pages || {};
    var sw = function (n, f) { var x = n.software || {}; return f(x) || ''; };
    var prog = function (k) { return function (x) { return (x.programs || {})[k]; }; };
    var mod = function (k) { return function (x) { return (x.modules || {})[k] || ''; }; };
    var rows = [
      ['ai', function (x) { return x.ai; }],
      ['Claude Code', function (x) { return x.claude; }],
      ['group:Python'],
      ['Python', function (x) { return x.python; }],
      ['where', function (x) { return x.python_path; }],
      ['colorama', mod('colorama')],
      ['OpenSSL (Python’s)', function (x) { return x.openssl; }],
      ['SQLite (library)', function (x) { return x.sqlite; }],
      ['group:The terminals'],
      ['tmux', prog('tmux')],
      ['git', prog('git')],
      ['Node.js', prog('node')],
      ['npm', prog('npm')],
      ['group:The pages'],
      ['nginx', prog('nginx')],
      ['php-fpm', prog('php-fpm')],
      ['PHP (command line)', function (x) { return x.php_cli; }],
      ['group:The system'],
      ['system', function (x) { return x.os; }],
      ['kernel', function (x) { return x.kernel + (x.arch ? ' · ' + x.arch : ''); }],
      ['systemd', prog('systemd')],
      ['OpenSSL (system)', prog('openssl')],
      ['chrony', prog('chrony')],
      ['ssh', prog('ssh')],
      ['smbclient', prog('smbclient')],
      ['iptables', prog('iptables')],
      ['firewalld', prog('firewalld')]
    ];
    var t = el('table', 'rows sw-table');
    var th = el('thead'), hr = el('tr');
    hr.appendChild(el('th', '', ''));
    nodes.forEach(function (n) {
      var c = el('th', '');
      c.appendChild(noI18n(el('span', '', n.name)));
      if (n.me) c.appendChild(el('span', 'tag info', 'this one'));
      else if (!n.alive) c.appendChild(el('span', 'tag warn', 'not heard from'));
      hr.appendChild(c);
    });
    th.appendChild(hr); t.appendChild(th);
    var tb = el('tbody');
    rows.forEach(function (r) {
      var tr = el('tr');
      if (r[0].indexOf('group:') === 0) {
        tr.className = 'sw-group';
        var g = el('td', '', r[0].slice(6));
        g.colSpan = nodes.length + 1;
        tr.appendChild(g);
        tb.appendChild(tr);
        return;
      }
      var vals = nodes.map(function (n) { return sw(n, r[1]); });
      if (!vals.some(function (v) { return v; })) return;     /* nowhere: not shown */
      var differs = nodes.length > 1 && vals.some(function (v) { return v !== vals[0]; });
      tr.appendChild(el('td', 'k', r[0]));
      vals.forEach(function (v) {
        var c = noI18n(el('td', 'mono small' + (differs ? ' warn' : ''), v || '–'));
        if (differs) c.title = 'not the same on every node';
        tr.appendChild(c);
      });
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    box.appendChild(t);
    /* The pages: this PHP itself, as php-fpm runs it for the node that
       answered this page. */
    if (pages.php) {
      box.appendChild(el('h3', 'sw-h', 'The pages’ PHP (as php-fpm runs it here)'));
      box.appendChild(peekFacts([['PHP', pages.php], ['How', pages.sapi], ['OPcache', pages.opcache ? 'on' : 'off'],
                                 ['Web server', pages.server || '–']]));
      var ex = el('div', 'sw-ext');
      Object.keys(pages.extensions || {}).forEach(function (k) {
        var v = pages.extensions[k];
        ex.appendChild(noI18n(el('span', 'tag namepill', k + (v ? ' ' + v : ''))));
      });
      box.appendChild(el('div', 'muted small', 'Its extensions (' + num(Object.keys(pages.extensions || {}).length) + '):'));
      box.appendChild(ex);
    }
    explainWhatWasDrawn(box);
  }).catch(function (e) { wait.textContent = String(e.message || e); });
}

function loadSoftware() {
  var host = $('ab-software');
  if (!host) return;
  clear(host);
  drawSoftware(host);
}

/* ---- a test SMS (otp's, 1.0.76) ---------------------------------------------------- */
if ($('sms-try')) {
  $('sms-try').onclick = function () {
    var b = $('sms-try');
    var stop = busyCount(b);
    $('sms-said').textContent = '';
    api('mail', {action: 'sms_test', to: $('sms-to').value.trim()}).then(function (d) {
      $('sms-said').textContent = (d.sent ? '✓ ' : '✗ ') + d.said + ' · ' + d.took_ms + ' ms';
      $('sms-said').style.color = d.sent ? 'var(--ok)' : 'var(--crit)';
      toast(d.sent ? 'sent to ' + d.to : 'not sent: ' + d.said, d.sent ? 'good' : 'bad');
    }).catch(oops).then(stop);
  };
}

/* ---- the outgoing mail and the message texts (as otp's) ------------------------------ */
/* ---- the outgoing mail (1.0.95) -------------------------------------------- */
var MQ = {page: 0, per: 100, timer: null};
var MQ_STATE_WORDS = {sending: ['being sent', 'info'], waiting: ['waiting', 'warn'], sent: ['sent', 'ok'],
                      failed: ['failed', 'crit'], expired: ['given up', 'dim']};
function mailqBadge(c) {
  var b = $('mq-badge');
  if (!b || !c) return;
  var n = (c.waiting || 0) + (c.failed || 0) + (c.sending || 0);
  b.hidden = !n;
  b.textContent = num(n);
  b.className = 'nav-badge' + (c.failed ? ' bad' : '');
  b.title = (c.waiting || 0) + ' waiting · ' + (c.failed || 0) + ' failed';
}
function mailqWatch(on) {
  clearInterval(MQ.timer);
  MQ.timer = null;
  /* Drawn again every 10 s while it is looked at - what waits moves by itself. */
  if (on) MQ.timer = setInterval(function () {
    if (PANE !== 'mailq' || TAB !== 'settings' || document.hidden) { mailqWatch(false); return; }
    if (!document.querySelector('.modal:not([hidden])')) loadMailq(true);
  }, 10000);
}
function mailqStateTag(st) {
  var w = MQ_STATE_WORDS[st] || [st || '?', 'dim'];
  return el('span', 'tag ' + w[1], w[0]);
}
function loadMailq(quiet) {
  if (!$('mq-table')) return;
  if (!quiet) mailqWatch(true);
  apiLatest('mailq', 'mailq&q=' + encodeURIComponent($('mq-q').value) + '&state=' + $('mq-state').value
      + '&limit=' + MQ.per + '&offset=' + MQ.page * MQ.per).then(function (d) {
    qSuggest($('mq-q'), 'mailq').said(d.q_error || '');
    var c = d.counts || {};
    mailqBadge(c);
    var chips = $('mq-chips');
    clear(chips);
    [['waiting', 'waiting for another try'], ['sending', 'being sent'], ['failed', 'failed'],
     ['sent', 'sent'], ['expired', 'given up']].forEach(function (x) {
      var ch = el('button', 'mq-chip ' + (MQ_STATE_WORDS[x[0]] || ['', ''])[1] + ($('mq-state').value === x[0] ? ' on' : ''));
      ch.type = 'button';
      ch.appendChild(el('b', '', num(c[x[0]] || 0)));
      ch.appendChild(el('span', '', x[1]));
      ch.onclick = function () { $('mq-state').value = $('mq-state').value === x[0] ? '' : x[0]; MQ.page = 0; loadMailq(); };
      chips.appendChild(ch);
    });
    $('mq-said').textContent = (d.mode === 'off' ? 'Sending mail is switched off (Settings → Mail): nothing is sent or tried again. · ' : '')
      + 'A mail not taken is tried again for ' + d.retry_hours + ' h (a code to sign in with only while it is good); the list keeps what went or failed for ' + d.keep_days + ' days.';
    liveFill($('mq-table'), function (host) {
    var cluster = false;
    var heads = ['Made', 'To', 'What', 'State', {words: 'Tries', cls: 'num'}, 'Next try / went', 'What it said'];
    if (cluster) heads.push('Node');
    heads.push('');
    host.appendChild(listTable(heads, d.rows, function (r) {
      var tr = el('tr');
      tr.appendChild(stampCell(r.created));
      var to = el('td');
      to.appendChild(noI18n(el('span', 'mono', (r.to || []).join(', '))));
      if (r.name && (r.to || []).join() !== r.name) to.appendChild(noI18n(el('span', 'sub', r.name)));
      tr.appendChild(to);
      var what = el('td');
      what.appendChild(el('span', '', r.kind_words || r.kind));
      if (r.subject) what.appendChild(noI18n(el('span', 'sub', r.subject)));
      tr.appendChild(what);
      var st = el('td');
      st.appendChild(mailqStateTag(r.state));
      tr.appendChild(st);
      tr.appendChild(el('td', 'num', num(r.tries || 0)));
      if (r.state === 'sent') tr.appendChild(stampCell(r.sent_at));
      else if (r.state === 'waiting') {
        var nx = el('td', 'small');
        var left = (r.next_at || 0) - Date.now() / 1000;
        nx.textContent = left > 5 ? 'in ' + span(left) : 'now';
        nx.title = 'tried until ' + dayWords(new Date((r.expires || 0) * 1000)) + ' ' + clockWords(new Date((r.expires || 0) * 1000));
        tr.appendChild(nx);
      } else tr.appendChild(el('td', 'muted small', r.state === 'sending' ? 'now' : '–'));
      var said = el('td', 'muted small mq-said');
      said.textContent = r.said || '';
      said.title = r.said || '';
      noI18n(said);
      tr.appendChild(said);
      if (cluster) tr.appendChild(noI18n(el('td', 'muted small', r.node || '')));
      var tools = el('td', 'rowtools');
      if (ADMIN) {
        if (r.state === 'waiting' || r.state === 'failed') {
          var again = iconButton('refresh', 'Send it again now');
          again.onclick = function (e) { e.stopPropagation(); mailqDo('retry', [r.qid]); };
          tools.appendChild(again);
        }
        var x = iconButton('trash', 'Take it out of the outgoing mail');
        x.onclick = function (e) {
          e.stopPropagation();
          confirmThen('Take the mail out', 'The mail to <b>' + htmlText((r.to || []).join(', ')) + '</b> ('
            + htmlText(r.kind_words || '') + ') goes from the list' + (r.state === 'waiting' ? ' and is not tried again' : '') + '.',
            'Take it out', function () { mailqDo('drop', [r.qid]); }, true);
        };
        tools.appendChild(x);
      }
      tr.appendChild(tools);
      tr.onclick = function () { mailqPeek(r.qid); };
      tr.classList.add('tappable');
      return tr;
    }, 'rows'));
    }, !!quiet);
    pager('mq-pager', MQ.page, MQ.per, d.total, function (p) { MQ.page = p; loadMailq(); });
    explainWhatWasDrawn($('pane-mailq'));
  }).catch(oops);
}
function mailqDo(act, ids) {
  return api('mailq', {action: act, ids: ids || []}).then(function (x) {
    toast(x.message, 'good');
    loadMailq(true);
    setTimeout(function () { if (PANE === 'mailq') loadMailq(true); }, 2500);
  }).catch(oops);
}
function mailqPeek(qid) {
  api('mailq-one&id=' + encodeURIComponent(qid)).then(function (r) {
    modal('A mail to ' + (r.to || []).join(', '), function (body) {
      var kv = el('div', 'me-kv');
      var row = function (k, v) { kv.appendChild(el('div', 'k', k)); var d = el('div', 'v'); if (typeof v === 'string') d.appendChild(noI18n(el('span', '', v))); else d.appendChild(v); kv.appendChild(d); };
      var at = function (ts) { var d = new Date((ts || 0) * 1000); return dayWords(d) + ' ' + clockWords(d); };
      row('State', mailqStateTag(r.state));
      row('What', el('span', '', r.kind_words || '')); if (r.subject) row('Subject', r.subject);
      row('Made', at(r.created) + (r.by ? ' · ' + r.by : ''));
      if (r.state === 'sent') row('Went', at(r.sent_at));
      if (r.state === 'waiting') row('Next try', at(r.next_at));
      row('Tried until', at(r.expires));
      body.appendChild(kv);
      if ((r.history || []).length) {
        body.appendChild(el('h3', '', 'Tries'));
        body.appendChild(listTable(['When', '', 'What it said'], r.history.slice().reverse(), function (h) {
          var tr = el('tr');
          tr.appendChild(stampCell(h.at));
          var t = el('td'); t.appendChild(el('span', 'tag ' + (h.ok ? 'ok' : 'warn'), h.ok ? 'taken' : 'not taken')); tr.appendChild(t);
          var w = noI18n(el('td', 'small', h.said || '')); tr.appendChild(w);
          return tr;
        }, 'rows'));
      }
      if ((r.steps || []).length) {
        body.appendChild(el('h3', '', 'The last try, step by step'));
        body.appendChild(stepsList(r.steps));
      }
      if (!r.has_body && (r.state === 'sent' || r.state === 'expired'))
        body.appendChild(el('p', 'note muted small', 'What the mail held is not kept once it went or was given up.'));
    }, [{words: 'Take it out', icon: 'trash', cls: 'danger', hidden: !ADMIN, go: function () { closeModal(); mailqDo('drop', [qid]); }},
        {spacer: true},
        {words: 'Send it again now', icon: 'refresh', cls: 'primary', hidden: !ADMIN || !r.has_body || !(r.state === 'waiting' || r.state === 'failed'),
         go: function () { closeModal(); mailqDo('retry', [qid]); }},
        {words: 'Close', close: true}].filter(function (b) { return !b.hidden; }), 'medium');
  }).catch(oops);
}
if ($('mq-q')) {
  var mqTimer = null;
  $('mq-q').addEventListener('input', function () { clearTimeout(mqTimer); mqTimer = setTimeout(function () { MQ.page = 0; loadMailq(); }, 300); });
  $('mq-state').onchange = function () { MQ.page = 0; loadMailq(); };
  $('mq-retry-all').onclick = function () { mailqDo('retry_all'); };
  $('mq-drop-sent').onclick = function () {
    confirmThen('Clear the sent mails', 'The mails that went leave the list (the events still say they went).', 'Clear them', function () { mailqDo('drop_sent'); });
  };
  $('mq-drop-failed').onclick = function () {
    confirmThen('Clear the failed mails', 'The mails refused for good, or given up, leave the list - they are not tried again.', 'Clear them', function () { mailqDo('drop_failed'); }, true);
  };
}

/* ==========================================================================
   The texts of the messages (1.0.103): every mail, SMS and question of the
   mail and SMS of a code, in Czech and English, edited as they will look. A mail is shown as it
   arrives - its texts written into where they stand; what is filled in when
   it is sent stands in blue chips. Saved in the database.
   ========================================================================== */
var MODAL_GO = null;
var TX = {data: null, id: null, lang: 'cs', dirty: {}, eds: {}, active: null, range: null, frame: null};
var TX_KINDS = [['mail', 'E-mails', 'mail'], ['sms', 'SMS', 'phone']];
var TX_COLORS = ['#111827', '#1d4ed8', '#b91c1c', '#15803d', '#b45309', '#7c3aed', '#6b7280'];
function txMsg(id) { return ((TX.data || {}).messages || []).filter(function (m) { return m.id === (id || TX.id); })[0]; }
function txField(key) { var m = txMsg(); return m ? m.fields.filter(function (f) { return f.key === key; })[0] : null; }
function txDirtyCount() { return Object.keys(TX.dirty).length; }
function txValue(f) { return Object.prototype.hasOwnProperty.call(TX.dirty, f.key) ? TX.dirty[f.key] : f.value[TX.lang]; }

function loadTexts() {
  api('texts').then(function (d) {
    TX.data = d;
    if (!txMsg(TX.id)) TX.id = d.messages[0].id;
    drawTexts();
  }).catch(oops);
}
/* Leaving what is not saved is asked first. */
function txLeave(go) {
  if (!txDirtyCount()) { go(); return; }
  confirmThen('Leave the changes unsaved?', 'What was written since the last save is thrown away.', 'Throw them away', function () {
    TX.dirty = {};
    go();
  }, true);
}

/* ---- a template and its picture in an editor ---------------------------- */
/* {code} as a chip, {{ and }} as braces; a plain text's lines as breaks. */
function txChipHtml(name, doc) {
  var label = (TX.data.placeholders || {})[name] || name;
  return '<span data-ph="' + name + '" contenteditable="false" title="{' + name + '}" style="display:inline-block;'
    + 'padding:0 6px;margin:0 1px;border-radius:5px;background:#dbeafe;color:#1e3a8a;border:1px solid #bfdbfe;'
    + 'font-size:.86em;line-height:1.5;font-weight:600;white-space:nowrap;vertical-align:baseline;cursor:default;'
    + 'user-select:all">' + htmlText(txT(label)) + '</span>';
}
function txToHtml(tpl, kind) {
  var s = String(tpl || '').replace(/\{\{/g, '').replace(/\}\}/g, '');
  if (kind !== 'rich') s = htmlText(s).replace(/\n/g, '<br>');
  s = s.replace(/\{([A-Za-z_]+)\}/g, function (_m, n) { return txChipHtml(n); });
  return s.replace(//g, '{').replace(//g, '}');
}
function txFromNode(node, kind) {
  var out = '';
  Array.prototype.forEach.call(node.childNodes, function (n) {
    if (n.nodeType === 3) {
      var t = n.nodeValue.replace(/​/g, '').replace(/\{/g, '{{').replace(/\}/g, '}}');
      out += kind === 'rich' ? htmlText(t).replace(/&#39;/g, "'").replace(/&quot;/g, '"') : t;
      return;
    }
    if (n.nodeType !== 1) return;
    var tag = n.tagName.toLowerCase();
    if (n.hasAttribute('data-ph')) { out += '{' + n.getAttribute('data-ph') + '}'; return; }
    if (tag === 'br') { out += kind === 'rich' ? '<br>' : (kind === 'line' ? ' ' : '\n'); return; }
    var inner = txFromNode(n, kind);
    if (tag === 'div' || tag === 'p') {
      out += (out && !/(<br>|\n)$/.test(out) ? (kind === 'rich' ? '<br>' : (kind === 'line' ? ' ' : '\n')) : '') + inner;
      return;
    }
    if (kind !== 'rich') { out += inner; return; }
    if (tag === 'b' || tag === 'strong') out += '<b>' + inner + '</b>';
    else if (tag === 'i' || tag === 'em') out += '<i>' + inner + '</i>';
    else if (tag === 'u') out += '<u>' + inner + '</u>';
    else if (tag === 'a' && n.getAttribute('href')) out += '<a href="' + htmlText(n.getAttribute('href')) + '">' + inner + '</a>';
    else if (tag === 'font' && n.getAttribute('color')) out += '<span style="color:' + n.getAttribute('color') + '">' + inner + '</span>';
    else if (tag === 'span' && n.getAttribute('style')) out += '<span style="' + htmlText(n.getAttribute('style')) + '">' + inner + '</span>';
    else out += inner;
  });
  return out;
}
function txSerialize(ed) {
  var v = txFromNode(ed, ed._f.kind);
  if (ed._f.kind === 'line') v = v.replace(/\s+/g, ' ').trim();
  return v;
}

/* One box of words: in the page, or in the picture of the mail. */
function txEditable(ed, f, doc) {
  ed._f = f;
  ed._doc = doc || document;
  ed.innerHTML = txToHtml(txValue(f), f.kind);
  ed.setAttribute('data-f', f.key);
  ed.setAttribute('spellcheck', 'true');
  ed.setAttribute('lang', TX.lang);
  var may = TX.data.may_change;
  ed.contentEditable = may ? 'true' : 'false';
  TX.eds[f.key] = ed;
  var mark = function () {
    var on = TX.active && TX.active.ed === ed;
    var changed = txValue(f) !== f.default[TX.lang];
    if (ed._inFrame) {
      ed.style.outline = on ? '2px solid #2563eb' : (ed._hover ? '1px dashed #60a5fa' : (changed ? '1px dashed #f59e0b' : '1px dashed transparent'));
      ed.style.outlineOffset = '3px';
      ed.style.borderRadius = '3px';
      ed.style.background = on ? 'rgba(37,99,235,.06)' : '';
    }
    ed.classList.toggle('tx-changed', changed);
    if (ed._mark2) ed._mark2(changed);
  };
  ed._markIt = mark;
  if (!may) { mark(); return ed; }
  ed.addEventListener('focus', function () { TX.active = {ed: ed, f: f, doc: ed._doc}; txToolsState(); Object.keys(TX.eds).forEach(function (k) { TX.eds[k]._markIt(); }); });
  ed.addEventListener('mouseenter', function () { ed._hover = true; mark(); });
  ed.addEventListener('mouseleave', function () { ed._hover = false; mark(); });
  ed.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (f.kind !== 'line') ed._doc.execCommand('insertLineBreak');
    }
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && /^[biu]$/i.test(e.key) && f.kind !== 'rich') e.preventDefault();
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); $('set-save').click(); }
  });
  ed.addEventListener('paste', function (e) {
    e.preventDefault();
    var t = (e.clipboardData || window.clipboardData).getData('text/plain') || '';
    if (f.kind === 'line') t = t.replace(/\s*\n\s*/g, ' ');
    ed._doc.execCommand('insertText', false, t);
  });
  ed.addEventListener('drop', function (e) { e.preventDefault(); });
  ed.addEventListener('input', function () {
    var v = txSerialize(ed);
    if (v === f.value[TX.lang]) delete TX.dirty[f.key]; else TX.dirty[f.key] = v;
    mark();
    txBarState();
    if (ed._onChange) ed._onChange(v);
    if (ed._inFrame) txFitFrame();
  });
  mark();
  return ed;
}
/* Put in where the cursor is, in the box last written in. */
function txInsertChip(name, ed) {
  ed = ed || (TX.active && TX.active.ed);
  if (!ed || !TX.data.may_change) return;
  if ((ed._f.placeholders || []).indexOf(name) < 0) { toast(txT('this text cannot have it'), 'bad'); return; }
  ed.focus();
  if (TX.range && TX.range.ed === ed) {
    var sel = ed._doc.getSelection();
    sel.removeAllRanges();
    sel.addRange(TX.range.r);
  }
  ed._doc.execCommand('insertHTML', false, txChipHtml(name) + '​');
  ed.dispatchEvent(new Event('input'));
}
function txKeepRange() {
  var a = TX.active;
  if (!a) return;
  var sel = a.doc.getSelection();
  if (sel && sel.rangeCount && a.ed.contains(sel.getRangeAt(0).commonAncestorContainer)) {
    TX.range = {ed: a.ed, r: sel.getRangeAt(0).cloneRange()};
  }
}
function txChipsFor(f, ed) {
  var row = el('div', 'tx-chips');
  if (!(f.placeholders || []).length || !TX.data.may_change) return row;
  row.appendChild(el('span', 'small muted', 'Put in:'));
  f.placeholders.forEach(function (p) {
    var b = el('button', 'tx-chip', (TX.data.placeholders || {})[p] || p);
    b.type = 'button';
    b.title = '{' + p + '}';
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
    b.onclick = function () { txInsertChip(p, ed); };
    row.appendChild(b);
  });
  return row;
}
function txResetField(f) {
  var ed = TX.eds[f.key];
  if (!ed) return;
  ed.innerHTML = txToHtml(f.default[TX.lang], f.kind);
  ed.dispatchEvent(new Event('input'));
}

/* ---- the whole pane ------------------------------------------------------ */
function drawTexts() {
  var host = $('tx-root');
  if (!host || !TX.data) return;
  saveBarHome();
  clear(host);
  TX.eds = {};
  TX.active = null;
  TX.range = null;
  /* One scroll, the page's (1.0.128): the list is short enough to stay in
     view beside the editor, which runs down the page - no scroll bars of
     their own. */
  var shell = el('div', 'tx-shell');
  txFitShell(shell);
  /* The messages, by whom they are for, then by how they go. */
  var list = el('div', 'tx-list card');
  var isAdmin = function (m) { return /^admin_/.test(m.id); };
  TX_KINDS.concat([['admin', 'The administration', 'shield']]).forEach(function (k) {
    var ms = TX.data.messages.filter(function (m) { return k[0] === 'admin' ? isAdmin(m) : (m.kind === k[0] && !isAdmin(m)); });
    if (!ms.length) return;
    var hd = el('div', 'tx-list-h');
    hd.innerHTML = iconMarkup(k[2], 14);
    hd.appendChild(el('span', '', k[1]));
    list.appendChild(hd);
    ms.forEach(function (m) {
      var b = el('button', 'tx-item' + (m.id === TX.id ? ' on' : ''));
      b.type = 'button';
      b.appendChild(el('span', 'tx-item-t', m.short || m.title));
      var st = el('span', 'tx-item-s');
      var ch = TX.data.langs.filter(function (l) { return (m.saved[l].changed || []).length; });
      ch.forEach(function (l) { st.appendChild(noI18n(el('span', 'tag warn', l.toUpperCase()))); });
      if (ch.length) b.title = 'Changed here - not as it comes';
      b.appendChild(st);
      b.onclick = function () { if (m.id !== TX.id) txLeave(function () { TX.id = m.id; drawTexts(); }); };
      list.appendChild(b);
    });
  });
  var ha = el('div', 'tx-ha small muted');
  ha.innerHTML = iconMarkup('db', 13);
  ha.appendChild(el('span', '', 'Kept in the database: they go with every copy of it, and to another engine with it.'));
  list.appendChild(ha);
  shell.appendChild(list);
  var ed = el('div', 'tx-ed');
  shell.appendChild(ed);
  host.appendChild(shell);
  txDrawEditor(ed);
}

function txDrawEditor(host) {
  var m = txMsg();
  var head = el('div', 'tx-head card');
  var ttl = el('div', 'tx-title');
  ttl.appendChild(el('h3', '', m.title));
  ttl.appendChild(el('p', 'small muted', m.says));
  head.appendChild(ttl);
  var seg = el('div', 'seg tx-lang');
  TX.data.langs.forEach(function (l) {
    var b = el('button', l === TX.lang ? 'on' : '');
    b.type = 'button';
    b.appendChild(noI18n(el('span', '', {cs: 'Čeština', en: 'English'}[l] || l)));
    if ((m.saved[l].changed || []).length) b.appendChild(el('span', 'tx-dot'));
    b.onclick = function () { if (l !== TX.lang) txLeave(function () { TX.lang = l; drawTexts(); }); };
    seg.appendChild(b);
  });
  head.appendChild(seg);
  /* What is saved, and what can be done with it. */
  var bar = el('div', 'tx-bar');
  var said = el('span', 'tx-said small');
  said.id = 'tx-said';
  bar.appendChild(said);
  var spacer = el('span', 'tx-spacer');
  bar.appendChild(spacer);
  var may = TX.data.may_change;
  var prev = cmdButton('Preview', 'eye', '');
  prev.onclick = txPreview;
  bar.appendChild(prev);
  if (may) {
    var test = cmdButton('Send a sample…', 'mail', '');
    test.onclick = txTest;
    bar.appendChild(test);
  }
  if (may) {
    var back = cmdButton('Put back as it comes', 'undo', 'danger');
    back.id = 'tx-reset';
    back.onclick = txResetAll;
    bar.appendChild(back);
  }
  head.appendChild(bar);
  host.appendChild(head);
  if (!may) host.appendChild(el('p', 'note', 'Only an administrator changes these words.'));
  if (m.kind === 'mail') txDrawMail(host, m);
  else txDrawSms(host, m);
  txBarState();
}

function txBarState() {
  var m = txMsg();
  if (!m) return;
  var n = txDirtyCount();
  var s = $('tx-said');
  if (s) {
    clear(s);
    var sv = m.saved[TX.lang];
    if (n) { s.className = 'tx-said small warn'; s.textContent = num(n) + ' text(s) changed, not saved yet'; }
    else if ((sv.changed || []).length && sv.at) {
      s.className = 'tx-said small';
      s.textContent = 'Saved ' + dayWords(new Date(sv.at * 1000)) + ' ' + clockWords(new Date(sv.at * 1000)) + (sv.by ? ' by ' + sv.by : '')
        + ' · ' + num(sv.changed.length) + ' text(s) not as they come';
    } else { s.className = 'tx-said small muted'; s.textContent = 'As it comes with ai'; }
  }
  /* Saved with the bar at the bottom (1.0.123), as everything else. */
  if (n && TX.data.may_change) {
    if (!PENDING.texts) pendingSet('texts', {pane: 'texts', save: txSave, reset: function () { TX.dirty = {}; drawTexts(); }});
  } else if (PENDING.texts) { delete PENDING.texts; markDirtyCount(); }
  if ($('tx-reset')) $('tx-reset').disabled = !(m.saved[TX.lang].changed || []).length && !n;
}

/* ---- a mail: drawn as it arrives, written into where it stands ----------- */
function txDrawMail(host, m) {
  var may = TX.data.may_change;
  var subj = m.fields.filter(function (f) { return f.where === 'subject'; })[0];
  /* The window of a mail program, with the toolbar over it. */
  var win = el('div', 'tx-mailwin card');
  var meta = el('div', 'tx-meta');
  var r1 = el('div', 'tx-meta-row');
  r1.appendChild(el('span', 'tx-meta-k', 'From'));
  r1.appendChild(noI18n(el('span', 'tx-meta-v mono small', TX.data.sender || '')));
  meta.appendChild(r1);
  var r2 = el('div', 'tx-meta-row');
  r2.appendChild(el('span', 'tx-meta-k', 'Subject'));
  var se = el('div', 'tx-line tx-subject');
  txEditable(se, subj);
  r2.appendChild(se);
  meta.appendChild(r2);
  var sc = txChipsFor(subj, se);
  sc.classList.add('tx-meta-chips');
  meta.appendChild(sc);
  win.appendChild(meta);
  if (may) win.appendChild(txToolbar());
  var stage = el('div', 'tx-stage');
  var frame = el('iframe', 'tx-frame');
  frame.setAttribute('title', m.title);
  TX.frame = frame;
  stage.appendChild(frame);
  var loading = el('p', 'note tx-loading', 'drawing the mail…');
  stage.appendChild(loading);
  win.appendChild(stage);
  host.appendChild(win);
  api('texts&render=' + encodeURIComponent(m.id) + '&lang=' + TX.lang + '&mark=1').then(function (d) {
    var page = String(d.html || '').replace(/<title>[\s\S]*?<\/title>/, '<title></title>')
      .replace(/⟦f:([a-z0-9_]+)⟧/g, function (_m, k) { return '<span data-slot="' + k + '"></span>'; });
    frame.onload = function () {
      loading.remove();
      var doc = frame.contentDocument;
      Array.prototype.forEach.call(doc.querySelectorAll('[data-slot]'), function (slot) {
        var f = txField(slot.getAttribute('data-slot'));
        if (!f) return;
        slot._inFrame = true;
        slot.style.minWidth = '24px';
        slot.style.display = 'inline-block';
        slot.style.cursor = may ? 'text' : 'default';
        slot.title = txT(f.label);
        txEditable(slot, f, doc);
      });
      doc.addEventListener('selectionchange', txKeepRange);
      doc.addEventListener('keyup', txKeepRange);
      doc.addEventListener('mouseup', txKeepRange);
      /* Links in the picture are not followed while it is written in. */
      doc.addEventListener('click', function (e) { var a = e.target.closest && e.target.closest('a'); if (a) e.preventDefault(); });
      txFitFrame();
      setTimeout(txFitFrame, 300);
    };
    frame.srcdoc = page;
  }).catch(function (e) { loading.textContent = e.message; });
  /* What is not in the picture: a greeting without a name, the text version. */
  var others = m.fields.filter(function (f) { return f.where === 'other'; });
  if (others.length) {
    var card = el('div', 'card tx-card');
    card.appendChild(el('h3', 'peek-h', 'When the name is not known'));
    card.appendChild(el('p', 'small muted', 'Used instead of the texts above when there is no name or account to put in.'));
    others.forEach(function (f) { card.appendChild(txFieldBox(f, 'tx-rich')); });
    host.appendChild(card);
  }
  var plain = m.fields.filter(function (f) { return f.where === 'plain'; });
  if (plain.length) {
    var pc = el('div', 'card tx-card');
    pc.appendChild(el('h3', 'peek-h', 'The plain text version'));
    pc.appendChild(el('p', 'small muted', 'What a mail program shows that does not show HTML, and what is sent alone when Settings → Codes by e-mail and SMS says a mail with a code is plain text.'));
    plain.forEach(function (f) { pc.appendChild(txFieldBox(f, 'tx-plain')); });
    host.appendChild(pc);
  }
}
/* One field in the page: its name, a box, what can be put in, its default. */
function txFieldBox(f, cls) {
  var wrap = el('div', 'tx-field');
  var top = el('div', 'tx-field-h');
  top.appendChild(el('b', '', f.label));
  var flag = el('span', 'tag warn small', 'changed');
  top.appendChild(flag);
  var sp = el('span', 'tx-spacer');
  top.appendChild(sp);
  var ed = el('div', 'tx-box ' + (cls || ''));
  if (TX.data.may_change) {
    var rb = cmdButton('As it comes', 'undo', 'small');
    rb.title = txT('Put this text back as it comes with ai');
    rb.onclick = function () { txResetField(f); };
    top.appendChild(rb);
  }
  wrap.appendChild(top);
  txEditable(ed, f);
  ed._mark2 = function (changed) { flag.hidden = !changed; if (rb) rb.disabled = !changed; };
  ed._markIt();
  wrap.appendChild(ed);
  wrap.appendChild(txChipsFor(f, ed));
  return wrap;
}
function txFitFrame() {
  var f = TX.frame;
  if (!f || !f.contentDocument || !f.contentDocument.documentElement) return;
  f.style.height = Math.max(200, f.contentDocument.documentElement.scrollHeight + 4) + 'px';
}
/* Bold, italic, a colour, a link - what mail programs show alike. */
function txToolbar() {
  var bar = el('div', 'tx-tools');
  bar.id = 'tx-tools';
  var cmd = function (icon, title, run, cls) {
    var b = el('button', 'tx-tool' + (cls ? ' ' + cls : ''));
    b.type = 'button';
    b.title = txT(title);
    b.setAttribute('aria-label', txT(title));
    if (/^</.test(icon)) b.innerHTML = icon; else b.appendChild(el('span', '', icon));
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
    b.onclick = function () {
      var a = TX.active;
      if (!a) { toast(txT('click into a text of the mail first'), 'bad'); return; }
      run(a);
      a.ed.dispatchEvent(new Event('input'));
    };
    bar.appendChild(b);
    return b;
  };
  var rich = function (a) { if (a.f.kind !== 'rich') { toast(txT('this text is one plain line'), 'bad'); return false; } return true; };
  cmd('<b>B</b>', 'Bold (Ctrl+B)', function (a) { if (rich(a)) a.doc.execCommand('bold'); }, 'rich-only');
  cmd('<i>I</i>', 'Italic (Ctrl+I)', function (a) { if (rich(a)) a.doc.execCommand('italic'); }, 'rich-only');
  cmd('<u>U</u>', 'Underline (Ctrl+U)', function (a) { if (rich(a)) a.doc.execCommand('underline'); }, 'rich-only');
  bar.appendChild(el('span', 'tx-sep'));
  var colors = el('span', 'tx-colors rich-only');
  TX_COLORS.forEach(function (c) {
    var b = el('button', 'tx-swatch');
    b.type = 'button';
    b.style.background = c;
    b.title = c;
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
    b.onclick = function () {
      var a = TX.active;
      if (!a || !rich(a)) return;
      a.doc.execCommand('styleWithCSS', false, true);
      a.doc.execCommand('foreColor', false, c);
      a.doc.execCommand('styleWithCSS', false, false);
      a.ed.dispatchEvent(new Event('input'));
    };
    colors.appendChild(b);
  });
  bar.appendChild(colors);
  bar.appendChild(el('span', 'tx-sep'));
  cmd(iconMarkup('globe', 15), 'A link', function (a) {
    if (!rich(a)) return;
    txKeepRange();
    var keep = TX.range;
    modalOver(function () {
      modal('A link', function (body) {
        var u = textBox('https://', 'https://…', 'mono');
        noI18n(u);
        body.appendChild(formField('Where it goes', u, 'https://…, http://… or mailto:…'));
        setTimeout(function () { u.focus(); u.select(); }, 50);
        u.addEventListener('keydown', function (e) { if (e.key === 'Enter') MODAL_GO(); });
        MODAL_GO = function () {
          var url = u.value.trim();
          if (!/^(https?:\/\/|mailto:)\S+$/i.test(url)) { toast(txT('a link starts with https://, http:// or mailto:'), 'bad'); return; }
          closeModal();
          a.ed.focus();
          if (keep) { var sel = a.doc.getSelection(); sel.removeAllRanges(); sel.addRange(keep.r); }
          if (a.doc.getSelection().isCollapsed) a.doc.execCommand('insertHTML', false, '<a href="' + htmlText(url) + '">' + htmlText(url) + '</a>');
          else a.doc.execCommand('createLink', false, url);
          a.ed.dispatchEvent(new Event('input'));
        };
      }, [{words: 'Close', close: true}, {words: 'Put it in', cls: 'primary', icon: 'check', go: function () { MODAL_GO(); }}], 'small');
    });
  }, 'rich-only');
  cmd(iconMarkup('close', 15), 'Take the link away', function (a) { if (rich(a)) a.doc.execCommand('unlink'); }, 'rich-only');
  cmd(iconMarkup('broom', 15), 'Take the formatting away', function (a) { if (rich(a)) { a.doc.execCommand('removeFormat'); a.doc.execCommand('unlink'); } }, 'rich-only');
  bar.appendChild(el('span', 'tx-sep'));
  cmd(iconMarkup('undo', 15), 'Undo (Ctrl+Z)', function (a) { a.doc.execCommand('undo'); });
  cmd(iconMarkup('refresh', 15), 'Redo (Ctrl+Y)', function (a) { a.doc.execCommand('redo'); });
  bar.appendChild(el('span', 'tx-sep'));
  /* What can be put into the text being written. */
  var ph = el('span', 'tx-tool-ph');
  ph.id = 'tx-tool-ph';
  bar.appendChild(ph);
  var sp = el('span', 'tx-spacer');
  bar.appendChild(sp);
  var which = el('span', 'tx-which small muted');
  which.id = 'tx-which';
  which.textContent = txT('Click into a text of the mail to write in it.');
  bar.appendChild(which);
  var fr = cmd(iconMarkup('undo', 15) + '<span>' + htmlText(txT('This text as it comes')) + '</span>', 'Put the text being written back as it comes with ai', function (a) { txResetField(a.f); }, 'tx-tool-wide');
  fr.id = 'tx-field-reset';
  return bar;
}
function txToolsState() {
  var a = TX.active;
  var bar = $('tx-tools');
  if (!bar || !a) return;
  var rich = a.f.kind === 'rich';
  Array.prototype.forEach.call(bar.querySelectorAll('.rich-only'), function (b) {
    if (b.tagName === 'BUTTON') b.disabled = !rich;
    else Array.prototype.forEach.call(b.querySelectorAll('button'), function (x) { x.disabled = !rich; });
  });
  var which = $('tx-which');
  if (which) which.textContent = txT(a.f.label) + (rich ? '' : ' · ' + txT('one plain line'));
  var ph = $('tx-tool-ph');
  clear(ph);
  (a.f.placeholders || []).forEach(function (p) {
    var b = el('button', 'tx-chip', (TX.data.placeholders || {})[p] || p);
    b.type = 'button';
    b.title = '{' + p + '}';
    b.addEventListener('mousedown', function (e) { e.preventDefault(); });
    b.onclick = function () { txInsertChip(p, a.ed); };
    ph.appendChild(b);
  });
  if (!(a.f.placeholders || []).length) ph.appendChild(el('span', 'small muted', 'nothing to put in here'));
  var fr = $('tx-field-reset');
  if (fr) fr.disabled = txValue(a.f) === a.f.default[TX.lang];
}

/* ---- an SMS: written, counted, shown on a phone -------------------------- */
function txFill(tpl, field) {
  var smp = (TX.data.samples || {})[TX.lang] || {};
  return String(tpl || '').replace(/\{\{/g, '').replace(/\}\}/g, '').replace(/\{([A-Za-z_]+)\}/g, function (_m, n) {
    if (n === 'dest' && field === 'ask_sms') return '+420 6•• ••• 456';
    return smp[n] !== undefined ? String(smp[n]) : '{' + n + '}';
  }).replace(//g, '{').replace(//g, '}');
}
var TX_GSM = '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà';
var TX_GSM_EXT = '^{}\\[~]|€\f';
function txSmsCount(text) {
  var gsm = true, units = 0;
  for (var i = 0; i < text.length; i++) {
    var c = text.charAt(i);
    if (TX_GSM.indexOf(c) >= 0) units += 1;
    else if (TX_GSM_EXT.indexOf(c) >= 0) units += 2;
    else { gsm = false; break; }
  }
  if (!gsm) units = text.length;
  var one = gsm ? 160 : 70, part = gsm ? 153 : 67;
  return {gsm: gsm, chars: units, parts: units <= one ? 1 : Math.ceil(units / part), one: one};
}
function txPlainSms(t) {
  if (!TX.data.sms_plain || !t.normalize) return t;
  return t.normalize('NFKD').replace(/[̀-ͯ]/g, '');
}
function txDrawSms(host, m) {
  var f = m.fields[0];
  var grid = el('div', 'tx-sms');
  var left = el('div', 'card tx-card');
  left.appendChild(txFieldBox(f, 'tx-plain tx-smsbox'));
  var count = el('div', 'tx-count small');
  left.appendChild(count);
  if (TX.data.sms_plain) left.appendChild(el('p', 'small muted', 'Letters with accents go without them (Settings → Codes by e-mail and SMS → Without accents): the phone gets 160 characters a part instead of 70.'));
  grid.appendChild(left);
  var right = el('div', 'tx-phone');
  var screen = el('div', 'tx-phone-screen');
  var from = el('div', 'tx-phone-from small');
  from.textContent = TX.data.samples && TX.data.samples[TX.lang] ? TX.data.samples[TX.lang].site : '';
  noI18n(from);
  screen.appendChild(from);
  var bubble = noI18n(el('div', 'tx-bubble'));
  screen.appendChild(bubble);
  right.appendChild(screen);
  grid.appendChild(right);
  host.appendChild(grid);
  var draw = function () {
    var text = txPlainSms(txFill(txValue(f), f.key));
    bubble.textContent = text;
    var c = txSmsCount(text);
    clear(count);
    count.appendChild(el('span', c.parts > 1 ? 'tag warn' : 'tag ok', num(c.parts) + ' SMS'));
    count.appendChild(el('span', 'muted', num(c.chars) + ' / ' + num(c.parts > 1 ? c.parts * (c.gsm ? 153 : 67) : c.one) + ' · '
      + (c.gsm ? txT('GSM alphabet') : txT('Unicode - an accent or a sign outside GSM'))));
  };
  TX.eds[f.key]._onChange = draw;
  draw();
}

/* ---- saved, put back, looked at, sent ------------------------------------ */
function txSave() {
  var m = txMsg();
  if (!txDirtyCount() || !TX.data.may_change) return Promise.resolve(true);
  return api('texts', {action: 'save', id: m.id, lang: TX.lang, fields: TX.dirty, was_at: m.saved[TX.lang].at || null}).then(function (d) {
    TX.dirty = {};
    txPutState(d.state);
    toast(d.message, 'good');
    drawTexts();
    return true;
  }).catch(function (e) {
    if (e.status === 409) {
      modalOver(function () {
        confirmThen('Changed meanwhile', htmlText(e.message) + '<br><br>' + htmlText(txT('Load them again - what was written here is then lost - or copy it out first.')),
          'Load them again', function () { TX.dirty = {}; delete PENDING.texts; markDirtyCount(); loadTexts(); }, false);
      });
      return false;
    }
    throw e;
  });
}
function txPutState(st) {
  if (!st) return;
  TX.data.messages = TX.data.messages.map(function (x) { return x.id === st.id ? st : x; });
}
function txResetAll() {
  var m = txMsg();
  var lang = {cs: 'Czech', en: 'English'}[TX.lang] || TX.lang;
  confirmThen('Put “' + htmlText(m.title) + '” back as it comes', 'Every text of this message in <b>' + htmlText(txT(lang))
    + '</b> goes back to how it comes with ai - exactly as it was before it was changed. The other language stays as it is.',
    'Put back', function () {
      api('texts', {action: 'reset', id: m.id, lang: TX.lang}).then(function (d) {
        TX.dirty = {};
        txPutState(d.state);
        toast(d.message, 'good');
        drawTexts();
      }).catch(oops);
    }, true);
}
function txPreview() {
  var m = txMsg();
  api('texts', {action: 'preview', id: m.id, lang: TX.lang, fields: TX.dirty}).then(function (d) {
    modal('Preview: ' + m.title, function (body) {
      var bad = Object.keys(d.bad || {});
      if (bad.length) {
        var w = el('div', 'note warn');
        bad.forEach(function (k) { w.appendChild(el('div', '', d.bad[k])); });
        body.appendChild(w);
      }
      body.appendChild(el('p', 'small muted', 'With sample values, as it would go out now - what is not saved yet included.'));
      if (d.html) {
        var sub = el('div', 'tx-meta-row');
        sub.appendChild(el('span', 'tx-meta-k', 'Subject'));
        sub.appendChild(noI18n(el('b', '', d.subject || '')));
        body.appendChild(sub);
        var fr = el('iframe', 'tx-frame tx-frame-preview');
        fr.setAttribute('title', 'Preview');
        fr.onload = function () {
          try { fr.style.height = Math.max(200, fr.contentDocument.documentElement.scrollHeight + 4) + 'px'; } catch (e) { }
          try { fr.contentDocument.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('a')) e.preventDefault(); }); } catch (e) { }
        };
        fr.srcdoc = d.html;
        body.appendChild(fr);
        if (d.text) {
          body.appendChild(el('h3', 'peek-h', 'The plain text version'));
          var pre = noI18n(el('pre', 'wrap mono small tx-pre'));
          pre.textContent = d.text;
          body.appendChild(pre);
        }
      } else if (d.sms !== undefined) {
        var bub = noI18n(el('div', 'tx-bubble'));
        bub.textContent = d.sms;
        body.appendChild(bub);
      }
    }, [{words: 'Close', close: true}], 'large');
  }).catch(oops);
}
function txTest() {
  var m = txMsg();
  var sms = m.kind === 'sms';
  modalOver(function () {
    modal('Send a sample', function (body) {
      body.appendChild(el('p', 'note', sms ? 'The SMS as it is written now - saved or not - with sample values, to one number.' : 'The mail as it is written now - saved or not - with sample values (a code that opens nothing, a name), to one address.'));
      var to = textBox('', sms ? '+420 603 123 456' : 'jan.novak@example.cz', 'mono');
      noI18n(to);
      body.appendChild(formField(sms ? 'The number' : 'The address', to));
      setTimeout(function () { to.focus(); }, 50);
      to.addEventListener('keydown', function (e) { if (e.key === 'Enter') MODAL_GO(); });
      var out = el('div', 'said');
      body.appendChild(out);
      MODAL_GO = function (button) {
        busy(button, true);
        api('texts', {action: 'test', id: m.id, lang: TX.lang, fields: TX.dirty, to: to.value.trim()}).then(function (d) {
          out.className = 'said good';
          out.textContent = d.message;
        }).catch(function (e) { out.className = 'said bad'; out.textContent = e.message; }).then(function () { busy(button, false); });
      };
    }, [{words: 'Close', close: true}, {words: 'Send', cls: 'primary', icon: sms ? 'phone' : 'mail', go: function (b) { MODAL_GO(b); }}], 'small');
  });
}
var TX_FIT = null;
function txFitShell(shell) {
  var fit = function () {
    if (!shell.isConnected) { window.removeEventListener('resize', fit); if (TX_FIT === fit) TX_FIT = null; return; }
    if (window.innerWidth < 900) { shell.style.height = ''; shell.classList.remove('split'); return; }
    var main = shell.closest('.ctl-main');
    if (!main) return;
    main.scrollTop = 0;
    var h = main.getBoundingClientRect().bottom - shell.getBoundingClientRect().top - 14;
    shell.style.height = Math.max(380, Math.floor(h)) + 'px';
    shell.classList.add('split');
    saveBarPlace();
  };
  TX_FIT = fit;
  setTimeout(fit, 0);
  window.addEventListener('resize', fit);
}

/* ==========================================================================
   A menu on the right mouse button (1.0.5) - drawn as claude.ai draws its own:
   a rounded card, an icon and the words on each line, the dangerous one in
   red at the bottom; arrows and Enter work, Esc or a click elsewhere closes it.
   ========================================================================== */
var CTX = {el: null, items: [], sel: -1, owner: null};
function ctxClose() {
  if (CTX.el) CTX.el.remove();
  if (CTX.owner) CTX.owner.classList.remove('menu');
  CTX.el = null; CTX.items = []; CTX.sel = -1; CTX.owner = null;
}
/** items: [{icon, words, go, danger, key, disabled}] - 'sep' a line, {head: words} a heading. */
function ctxMenu(x, y, items, owner) {
  ctxClose();
  var m = el('div', 'ctx');
  m.setAttribute('role', 'menu');
  var buttons = [];
  items.forEach(function (it) {
    if (!it) return;
    if (it === 'sep') {
      if (m.lastChild && !m.lastChild.classList.contains('ctx-sep')) m.appendChild(el('div', 'ctx-sep'));
      return;
    }
    if (it.head) { m.appendChild(noI18n(el('div', 'ctx-head', it.head))); return; }
    var b = el('button', 'ctx-item' + (it.danger ? ' danger' : ''));
    b.type = 'button';
    b.setAttribute('role', 'menuitem');
    if (it.icon) b.innerHTML = iconMarkup(it.icon, 16);
    b.appendChild(el('span', 'ctx-w', it.words));
    if (it.key) b.appendChild(noI18n(el('span', 'ctx-k', it.key)));
    if (it.disabled) b.disabled = true;
    b.onclick = function (e) { e.stopPropagation(); ctxClose(); if (it.go) it.go(); };
    b.onmouseenter = function () { CTX.sel = buttons.indexOf(b); paint(); };
    buttons.push(b);
    m.appendChild(b);
  });
  if (m.lastChild && m.lastChild.classList.contains('ctx-sep')) m.lastChild.remove();
  document.body.appendChild(m);
  if (typeof i18nWalk === 'function') { try { i18nWalk(m); } catch (e) { } }
  var r = m.getBoundingClientRect();
  var left = Math.min(x, window.innerWidth - r.width - 8), top = y;
  if (top + r.height > window.innerHeight - 8) top = Math.max(8, y - r.height);
  m.style.left = Math.max(8, left) + 'px';
  m.style.top = Math.max(8, top) + 'px';
  CTX.el = m; CTX.items = buttons; CTX.sel = -1; CTX.owner = owner || null;
  if (owner) owner.classList.add('menu');
  function paint() { buttons.forEach(function (b, i) { b.classList.toggle('sel', i === CTX.sel); }); }
  CTX.paint = paint;
}
document.addEventListener('mousedown', function (e) { if (CTX.el && !CTX.el.contains(e.target)) ctxClose(); }, true);
document.addEventListener('keydown', function (e) {
  if (!CTX.el) return;
  var n = CTX.items.length;
  if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); ctxClose(); return; }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault(); e.stopPropagation();
    var d = e.key === 'ArrowDown' ? 1 : -1, i = CTX.sel;
    for (var k = 0; k < n; k++) { i = (i + d + n) % n; if (!CTX.items[i].disabled) break; }
    CTX.sel = i; CTX.paint();
    return;
  }
  if (e.key === 'Enter' && CTX.sel >= 0) { e.preventDefault(); e.stopPropagation(); CTX.items[CTX.sel].click(); }
}, true);
window.addEventListener('resize', ctxClose);
window.addEventListener('blur', ctxClose);
document.addEventListener('scroll', ctxClose, true);

function termById(id) { return TL.terms.filter(function (x) { return x.id === id; })[0]; }
function copyText2(text, said) {
  var done = function () { toast(said || 'copied', 'good'); };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, function () { fallback(); });
  } else fallback();
  function fallback() {
    var ta = el('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { toast('the browser would not copy it', 'bad'); }
    ta.remove();
  }
}
/* What can be done with one chat - from its row in the list, its ⋯, or the
   terminal itself. */
function termActions(t, row) {
  var ended = t.state === 'ended';
  return [
    {head: t.title},
    ended ? {icon: 'eye', words: 'Its last screen', go: function () { endedPeek(t); }}
          : (t.id === TL.open ? null : {icon: 'play', words: 'Open it', go: function () { openTerm(t.id); }}),
    !ended ? {icon: 'window', words: 'Open in a new window', go: function () { window.open(location.pathname + '#terms/' + t.id, '_blank'); }} : null,
    'sep',
    {icon: 'gear', words: t.kind === 'claude' ? 'Change it - model, effort, permissions, folder…' : 'Change it - name, folder…', go: function () { termEdit(t); }},
    {icon: 'pin', words: isPinned(t.id) ? 'Unpin' : 'Pin', go: function () { togglePin(t); }},
    {icon: 'edit', words: 'Rename', go: function () { renameInline(t, row || document.querySelector('.tl-item[data-id="' + t.id + '"]')); }},
    {icon: 'folder', words: 'The files of this chat', disabled: ended && false, go: function () { if (t.id !== TL.open && !ended) openTerm(t.id); chatFiles(t, true); }},
    t.kind === 'claude' ? {icon: 'terminal', words: 'A new Claude Code in its folder', go: function () { startTerm({kind: 'claude', cwd: t.path || t.cwd}); }} : null,
    {icon: 'copy', words: 'Copy the command to attach it on the server', go: function () { copyText2('ai --attach ' + t.id, 'copied: ai --attach ' + t.id); }},
    'sep',
    ended ? {icon: 'refresh', words: 'Start it again', go: function () {
      api('terms', {do: 'again', id: t.id}).then(function (d) { loadTerms(d.id); }).catch(oops);
    }} : {icon: 'refresh', words: 'Start it again', go: function () {
      confirmThen('Start ' + t.title + ' again?', 'What runs in it now is ended and started afresh in the same folder' + (t.kind === 'claude' ? ' - Claude Code picks up the conversation where it was (--continue).' : '.'), 'Start it again', function () {
        api('terms', {do: 'restart', id: t.id}).then(function () { if (t.id === TL.open) termOpen(t.id, $('term-host'), TERM.onState); loadTerms(TL.open, true); }).catch(oops);
      }, false);
    }},
    ended ? {icon: 'trash', words: 'Take it off the list', danger: true, go: function () {
      api('terms', {do: 'forget', id: t.id}).then(function () { loadTerms(); }).catch(oops);
    }} : {icon: 'power', words: 'End it', danger: true, go: function () {
      confirmThen('End ' + t.title + '?', 'What runs in it is ended on the server - for every window looking at it. Its last screen stays in the list for a while.', 'End it', function () {
        api('terms', {do: 'kill', id: t.id}).then(function () { if (t.id === TL.open) closeTermView(); loadTerms(); }).catch(oops);
      }, true);
    }},
    endedCount() ? {icon: 'trash', words: 'Take every ended one off the list (' + endedCount() + ')', danger: true, go: forgetEnded} : null
  ];
}
/* Every ended terminal off the list at once (1.0.18) - one by one it was a
   right click each. The running ones are not touched. */
function endedCount() { return (TL.terms || []).filter(function (x) { return x.state === 'ended'; }).length; }
function forgetEnded() {
  var gone = (TL.terms || []).filter(function (x) { return x.state === 'ended'; });
  if (!gone.length) { toast('no ended terminal in the list'); return; }
  confirmThen('Take ' + gone.length + ' ended terminal(s) off the list?',
    'Their last screens go with them. Nothing that runs is touched, and the conversations of Claude Code stay - they are picked up again under Conversations.',
    'Take them off', function () {
      Promise.all(gone.map(function (x) { return api('terms', {do: 'forget', id: x.id}).catch(function () { }); }))
        .then(function () { toast(gone.length + ' taken off the list', 'good'); loadTerms(TL.open, true); });
    }, true);
}
/* A chat's choices changed (1.0.25): the name, the folder and - for Claude
   Code - the model, the effort, the permission mode and more words. It is
   started again in its own tile and goes on with its conversation. */
var EFFORTS = [['', 'as Claude Code decides'], ['low', 'low'], ['medium', 'medium'], ['high', 'high'], ['xhigh', 'extra high'], ['max', 'max']];
function termEdit(t) {
  var o = t.opts || {};
  var f = {};
  var withNow = function (list, v) { return v && !list.some(function (x) { return x[0] === v; }) ? list.concat([[v, v]]) : list; };
  modal(txT('Change') + ' ' + t.title, function (body) {
    var g = el('div', 'formgrid');
    f.title = textBox(t.title, '');
    g.appendChild(formField('Its name', f.title));
    var dirWrap = el('div', 'btnrow');
    f.cwd = textBox(t.cwd, '', 'mono');
    f.cwd.style.flex = '1';
    dirWrap.appendChild(f.cwd);
    var browse = cmdButton('Choose…', 'archive', 'small');
    browse.onclick = function () { pickFolder(f.cwd.value, function (p) { f.cwd.value = p; }); };
    dirWrap.appendChild(browse);
    var fd = formField('The working directory', dirWrap, t.kind === 'claude' ? 'Its conversation goes with it to the new folder.' : '');
    fd.classList.add('span-2');
    g.appendChild(fd);
    if (t.kind === 'claude') {
      f.model = selectBox(withNow(MODELS, o.model), o.model || '');
      g.appendChild(formField('Model', f.model));
      f.effort = selectBox(EFFORTS, o.effort || '');
      g.appendChild(formField('Effort (--effort)', f.effort));
      f.mode = selectBox(withNow(MODES, o.mode), o.mode || '');
      g.appendChild(formField('Permissions', f.mode));
      f.args = textBox(o.args || '', '--verbose …', 'mono');
      g.appendChild(formField('More words for Claude Code', f.args));
    }
    body.appendChild(g);
    var note = el('p', 'note');
    note.style.marginTop = '16px';
    note.textContent = txT(t.kind === 'claude'
      ? (t.state === 'ended' ? 'It is started again with these, going on with its conversation.'
        : 'Claude Code takes these only when it starts: it is started again in its own tile and goes on with its conversation. What it is doing right now is stopped.')
      : 'A new folder starts the shell again in it.');
    body.appendChild(note);
  }, [{words: 'Close', close: true},
      {words: 'Save and start it again', cls: 'primary', icon: 'refresh', go: function (b) {
        var body = {do: 'edit', id: t.id, title: f.title.value, cwd: f.cwd.value.trim()};
        if (t.kind === 'claude') { body.model = f.model.value; body.effort = f.effort.value; body.mode = f.mode.value; body.args = f.args.value; }
        else if (f.cwd.value.trim() !== t.cwd) body.restart = true;
        busy(b, true);
        api('terms', body).then(function (d) {
          closeModal();
          toast('changed', 'good');
          return loadTerms(d.id || t.id).then(function () { if ((d.id || t.id) === TL.open) termOpen(TL.open, $('term-host'), TERM.onState); });
        }).catch(oops).then(function () { busy(b, false); });
      }}], 'wide');
}
function termMenu(t, x, y, row) { ctxMenu(x, y, termActions(t, row), row); }

/* The right button on the terminal: copying and pasting first, then the chat. */
(function termRightButton() {
  var host = $('term-host');
  /* Before xterm.js sees it: with the mouse on in tmux, the right button
     would otherwise go to tmux and open its own menu inside the terminal. */
  host.addEventListener('mousedown', function (e) {
    if (e.button === 2 && !e.shiftKey) { e.stopPropagation(); e.preventDefault(); }
  }, true);
  host.addEventListener('mouseup', function (e) { if (e.button === 2 && !e.shiftKey) { e.stopPropagation(); e.preventDefault(); } }, true);
  host.addEventListener('contextmenu', function (e) {
    if (e.shiftKey) return;           /* Shift: the browser's own menu */
    e.preventDefault();
    e.stopPropagation();
    /* PuTTY's way, unless the account chose the menu (1.0.23): the right
       button pastes, Ctrl with it opens the menu. */
    if (termRightMode() === 'paste' && !e.ctrlKey && !e.metaKey && !e.target.closest('.term-sb, .term-live, .term-pure-x')) {
      termPasteClipboard();
      return;
    }
    termCtx(e.clientX, e.clientY);
  }, true);
  /* On a tablet the right button is a finger held still (1.0.9). */
  longPress(host, function (x, y) { termCtx(x, y); });
  function termCtx(cx, cy) {
    var t = termById(TL.open);
    var sel = TERM.t && TERM.t.hasSelection() ? TERM.t.getSelection() : '';
    var items = [
      {icon: 'copy', words: 'Copy', key: 'Ctrl+Shift+C', disabled: !sel, go: function () { copyText2(sel); }},
      {icon: 'paste', words: 'Paste', key: termRightMode() === 'paste' ? 'right button' : 'Ctrl+V', go: termPasteClipboard},
      {icon: 'list', words: 'The whole history', go: function () { if (t) termHistory(t); }},
      {icon: 'down', words: 'Back to now', disabled: !TERM.pos.mode, go: function () { termAsk({t: 'live'}); }},
      {icon: 'selectall', words: 'Select everything on the screen', go: function () { if (TERM.t) { TERM.t.selectAll(); TERM.t.focus(); } }},
      {icon: 'copy', words: 'Copy everything on the screen', go: function () {
        if (!TERM.t) return;
        var b = TERM.t.buffer.active, out = [];
        for (var i = 0; i < b.length; i++) { var l = b.getLine(i); if (l) out.push(l.translateToString(true)); }
        copyText2(out.join('\n').replace(/\n+$/, ''), 'the screen was copied');
      }},
      'sep',
      {icon: 'upload', words: 'Give Claude a file…', go: function () { $('tb-attach').click(); }},
      {icon: 'folder', words: 'The files of this chat', go: function () { if (t) chatFiles(t, true); }},
      {icon: 'list', words: 'Claude Code\'s commands', go: function () { $('tb-cmds').click(); }},
      {icon: 'edit', words: 'Write a longer text', go: function () { $('tb-compose').click(); }},
      {icon: 'maximize', words: 'Only the terminal, over the whole screen', go: function () { termPure(true); }},
      {icon: 'unfold', words: TL.full ? 'Back from the whole window' : 'Over the whole window', go: function () { $('tb-full').click(); }},
      {icon: 'broom', words: 'Clear the screen', key: 'Ctrl+L', go: function () { termKeys('\x0c'); }}
    ];
    if (t) items = items.concat(['sep'], termActions(t, null).filter(function (x) {
      return !x || x === 'sep' || (!x.head && x.icon !== 'folder');
    }));
    ctxMenu(cx, cy, items);
  }
}());

/* A finger held still on something (1.0.9): what the right button is on a
   computer. Moving the finger, or a second one, is not it. */
function longPress(node, go, ms) {
  var timer = null, x0 = 0, y0 = 0;
  var stop = function () { clearTimeout(timer); timer = null; };
  node.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1) { stop(); return; }
    var tt = e.touches[0];
    x0 = tt.clientX; y0 = tt.clientY;
    var target = e.target;
    stop();
    timer = setTimeout(function () {
      timer = null;
      node._longPressed = Date.now();
      if (navigator.vibrate) { try { navigator.vibrate(15); } catch (er) { } }
      go(x0, y0, target);
    }, ms || 550);
  }, {passive: true});
  node.addEventListener('touchmove', function (e) {
    var tt = e.touches[0];
    if (timer && (Math.abs(tt.clientX - x0) > 10 || Math.abs(tt.clientY - y0) > 10)) stop();
  }, {passive: true});
  node.addEventListener('touchend', function (e) {
    stop();
    /* The tap that ends a long press opens nothing under it. */
    if (node._longPressed && Date.now() - node._longPressed < 800) e.preventDefault();
  });
  node.addEventListener('touchcancel', stop);
}

/* The whole history of a terminal (1.0.9): every line tmux keeps, with its
   colours, in a window of its own that scrolls as any page does - by finger
   on a tablet - with copy and download. */
function termHistory(t) {
  var view = null;
  modal('The whole history: ' + (t.title || t.id), function (body) {
    var host = el('div', 'term-history');
    host.appendChild(el('p', 'note', 'reading what tmux keeps…'));
    body.appendChild(host);
    api('term&id=' + encodeURIComponent(t.id) + '&lines=all&ansi=1').then(function (d) {
      clear(host);
      var text = String((d.term && d.term.screen) || '').replace(/\s+$/, '');
      var lines = text.split('\n').length;
      view = new window.Terminal({
        fontFamily: '"JetBrains Mono", "Cascadia Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace',
        fontSize: termFont(), lineHeight: 1.1, scrollback: lines + 50, disableStdin: true, cursorBlink: false,
        theme: termTheme(), convertEol: true
      });
      var fit = new window.FitAddon.FitAddon();
      view.loadAddon(fit);
      view.open(host);
      try { fit.fit(); } catch (e) { }
      view.write(text, function () { view.scrollToBottom(); });
      host._plain = text.replace(/\x1b\[[0-9;?]*[ -\/]*[@-~]/g, '').replace(/\x1b\][^\x07]*(\x07|\x1b\\)/g, '');
      host._lines = lines;
      $('modal-title').textContent = txT('The whole history') + ': ' + (t.title || t.id) + ' · ' + num(lines) + ' ' + txT('lines');
    }).catch(function (e) { clear(host); host.appendChild(el('p', 'note bad', String(e.message || e))); });
  }, [
    {words: 'Copy it all', icon: 'copy', go: function () {
      var h = document.querySelector('#modal-body .term-history');
      if (h && h._plain) copyText2(h._plain, 'the whole history was copied');
    }},
    {words: 'Download it', icon: 'download', go: function () {
      var h = document.querySelector('#modal-body .term-history');
      if (!h || !h._plain) return;
      var a = el('a');
      a.href = URL.createObjectURL(new Blob([h._plain + '\n'], {type: 'text/plain'}));
      a.download = (t.title || t.id).replace(/[^\w.-]+/g, '-') + '-history.txt';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    }},
    {spacer: true},
    {words: 'Close', close: true}], 'large');
  MODAL_CLOSE = function () { if (view) { try { view.dispose(); } catch (e) { } } };
}

/* ==========================================================================
   The files of one chat (1.0.5): its own folder and what is in it, beside its
   terminal - never above it, whatever else the account may see. A file is
   handed to Claude by its path (@path), opened, fetched, renamed or deleted;
   files dropped onto the list go into the folder shown.
   ========================================================================== */
var CF = {t: null, root: '', path: '', data: null};
function chatFiles(t, open) {
  var box = $('term-files');
  if (!open) { box.hidden = true; setTimeout(termFit, 50); return; }
  var root = t.cwd || t.path;
  if (CF.t && CF.t.id === t.id && !box.hidden) { cfLoad(CF.path); return; }
  CF.t = t; CF.root = root;
  box.hidden = false;
  $('tf-ic').innerHTML = iconMarkup('folder', 17);
  $('tf-root').textContent = baseName(root);
  $('tf-root').title = root;
  cfLoad(root);
  setTimeout(termFit, 50);
}
function cfRel(p) {
  var r = CF.root.replace(/\/+$/, '');
  if (p === r) return '';
  return p.indexOf(r + '/') === 0 ? p.slice(r.length + 1) : p;
}
function cfLoad(path) {
  return filesApi('list', 'hidden=1&root=' + encodeURIComponent(CF.root) + '&path=' + encodeURIComponent(path || CF.root)).then(function (d) {
    CF.path = d.path; CF.data = d;
    $('tf-crumbs').textContent = cfRel(d.path) ? '/' + cfRel(d.path) : '';
    $('tf-up').disabled = !d.up;
    cfDraw(d);
  }).catch(function (e) {
    if (e && e.status === 403) { toast(String(e.message || e), 'bad'); return cfLoad(CF.root); }
    oops(e);
  });
}
function cfDraw(d) {
  var host = $('tf-list');
  clear(host);
  if (!d.entries.length) host.appendChild(el('div', 'tf-empty', 'An empty folder. Drop files here to put them in.'));
  d.entries.forEach(function (e) {
    var full = pathJoin(d.path, e.name);
    var r = el('button', 'tf-row' + (e.kind === 'dir' ? ' dir' : ''));
    r.type = 'button';
    r.innerHTML = iconMarkup(e.kind === 'dir' ? 'folder' : 'file', 15);
    r.appendChild(noI18n(el('span', 'tf-n', e.name + (e.link ? ' →' : ''))));
    if (e.kind !== 'dir') r.appendChild(el('span', 'tf-s', bytes(e.size)));
    r.title = full;
    r.onclick = function () { if (e.kind === 'dir') cfLoad(full); else openFile(full, e); };
    r.addEventListener('contextmenu', function (ev) { ev.preventDefault(); cfMenu(e, full, ev.clientX, ev.clientY, r); });
    longPress(r, function (x, y) { cfMenu(e, full, x, y, r); });
    host.appendChild(r);
  });
  $('tf-foot').textContent = num(d.entries.length) + ' item(s) · right button: what to do with one';
}
function cfMenu(e, full, x, y, row) {
  var rel = cfRel(full);
  var dir = e.kind === 'dir';
  ctxMenu(x, y, [
    {head: e.name},
    dir ? {icon: 'folder', words: 'Open the folder', go: function () { cfLoad(full); }}
        : {icon: 'eye', words: 'Open it', go: function () { openFile(full, e); }},
    {icon: 'at', words: 'Hand it to Claude (@' + (rel.length > 28 ? '…' + rel.slice(-27) : rel) + ')', go: function () { termType('@' + rel + ' ', false); }},
    {icon: 'copy', words: 'Copy its path', go: function () { copyText2(full); }},
    dir ? {icon: 'terminal', words: 'A new Claude Code in it', go: function () { startTerm({kind: 'claude', cwd: full}); }} : null,
    dir ? {icon: 'add', words: 'A new folder in it…', go: function () { cfNew('mkdir', full); }} : null,
    dir ? {icon: 'file', words: 'A new file in it…', go: function () { cfNew('touch', full); }} : null,
    'sep',
    {icon: 'download', words: dir ? 'Download it as a .zip' : 'Download it', go: function () { download(full); }},
    {icon: 'edit', words: 'Rename', go: function () {
      var name = prompt('A new name for ' + e.name, e.name);
      if (!name || name === e.name) return;
      filesApi('op', '', {op: 'rename', path: full, name: name}).then(function () { cfLoad(CF.path); }).catch(oops);
    }},
    'sep',
    {icon: 'trash', words: 'Delete', danger: true, go: function () {
      confirmThen('Delete ' + e.name + '?', (dir ? 'The folder <b>' + htmlText(e.name) + '</b> and everything in it are' : '<b>' + htmlText(e.name) + '</b> is') + ' deleted from the server. There is no bin.', 'Delete it', function () {
        filesApi('op', '', {op: 'delete', path: full}).then(function () { cfLoad(CF.path); }).catch(oops);
      });
    }}
  ], row);
}
$('tf-up').onclick = function () { if (CF.data && CF.data.up) cfLoad(CF.data.up); };
$('tf-reload').onclick = function () { cfLoad(CF.path); };
$('tf-close').onclick = function () { chatFiles(null, false); };
function cfNew(what, inside) {
  var name = prompt(txT(what === 'mkdir' ? 'The name of the new folder' : 'The name of the new file'));
  if (!name) return;
  filesApi('op', '', {op: what, path: inside, name: name, root: CF.root || undefined})
    .then(function () { cfLoad(CF.path); }).catch(oops);
}
$('tf-mkdir').onclick = function () { cfNew('mkdir', CF.path); };
/* The list itself, where there is no row: what can be made in the folder shown. */
(function () {
  var host = $('tf-list');
  var here = function (x, y) {
    ctxMenu(x, y, [{head: baseName(CF.path || '')},
      {icon: 'add', words: 'A new folder here…', go: function () { cfNew('mkdir', CF.path); }},
      {icon: 'file', words: 'A new file here…', go: function () { cfNew('touch', CF.path); }},
      {icon: 'upload', words: 'Upload files here…', go: function () { $('tf-input').click(); }},
      {icon: 'refresh', words: 'Read it again', go: function () { cfLoad(CF.path); }}]);
  };
  host.addEventListener('contextmenu', function (ev) {
    if (ev.target.closest('.tf-row, button')) return;
    ev.preventDefault();
    here(ev.clientX, ev.clientY);
  });
  longPress(host, function (x, y, target) { if (!target.closest('.tf-row, button')) here(x, y); });
}());
$('tf-send').onclick = function () { $('tf-input').click(); };
function cfSend(files) {
  var list = Array.prototype.slice.call(files || []);
  var next = function () {
    var f = list.shift();
    if (!f) { cfLoad(CF.path); return; }
    $('tf-foot').textContent = 'sending ' + f.name + '…';
    sendFile('/files/put?dir=' + encodeURIComponent(CF.path) + '&name=' + encodeURIComponent(f.name), f, function (a, b) {
      $('tf-foot').textContent = f.name + ' ' + Math.round(a * 100 / b) + ' %';
    }).then(next).catch(function (e) { oops(e); next(); });
  };
  next();
}
$('tf-input').onchange = function () { cfSend($('tf-input').files); $('tf-input').value = ''; };
(function () {
  var host = $('tf-list'), depth = 0;
  var has = function (e) { return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0; };
  host.addEventListener('dragenter', function (e) { if (!has(e)) return; e.preventDefault(); e.stopPropagation(); depth++; host.classList.add('over'); });
  host.addEventListener('dragover', function (e) { if (!has(e)) return; e.preventDefault(); e.stopPropagation(); });
  host.addEventListener('dragleave', function (e) { e.stopPropagation(); if (--depth <= 0) { depth = 0; host.classList.remove('over'); } });
  host.addEventListener('drop', function (e) { if (!has(e)) return; e.preventDefault(); e.stopPropagation(); depth = 0; host.classList.remove('over'); cfSend(e.dataTransfer.files); });
}());

/* ---- the picture of the sign-in (1.0.27): exactly otp's (admin.js 1.0.161),
   one sign-in instead of two. Picked here, kept by the save bar; a picture of
   one's own read into the page and sent with the save. ---------------------- */
var ART = {draft: null, last: null};
function loadArt() {
  return api('art').then(function (d) {
    if (!PENDING.art) ART.draft = null;
    drawArt(d.signin);
  }).catch(oops);
}
function artDraft() {
  var saved = ART.last || {};
  if (!ART.draft) ART.draft = {art: saved.art, data: '', name: '', bytes: 0, forget: false};
  return ART.draft;
}
function artChanged() {
  var dr = ART.draft, saved = ART.last || {};
  return !!(dr && (dr.art !== saved.art || dr.data || dr.forget));
}
function artMark() {
  if (artChanged()) {
    pendingSet('art', {pane: 'signin', save: artSave, reset: function () { ART.draft = null; if (ART.last) drawArt(ART.last); }});
  } else if (PENDING.art) {
    delete PENDING.art;
    markDirtyCount();
  }
  drawArt(ART.last);
}
function artSave() {
  var dr = ART.draft;
  if (!dr || !artChanged()) return Promise.resolve(true);
  return api('art', {action: 'save', art: dr.art, data: dr.data || undefined,
                     name: dr.name || undefined, forget: dr.forget || undefined}).then(function (d) {
    ART.draft = null;
    toast(d.message, 'good');
    drawArt(d.signin);
    return true;
  });
}
function drawArt(saved) {
  if (!saved) return;
  ART.last = saved;
  var dr = ART.draft || {art: saved.art};
  var grid = $('art-grid'), tpl = $('art-gallery');
  if (!grid || !tpl) return;
  /* A picture of your own as it will be after the save: a new one, the one
     kept, or none when it is to be taken away. */
  var own = dr.data ? {src: dr.data, name: dr.name, bytes: dr.bytes, fresh: true}
    : (saved.logo && !dr.forget ? {src: '/?api=logo&v=' + encodeURIComponent(saved.logo.sha || ''),
                                  name: saved.logo.name, bytes: saved.logo.bytes, by: saved.logo.by, at: saved.logo.at} : null);
  clear(grid);
  Array.prototype.forEach.call(tpl.content.children, function (src) {
    var name = src.dataset.art;
    var picked = dr.art === name, isNow = saved.art === name;
    var tile = el('button', 'art-tile' + (picked ? ' on' : '') + (picked && !isNow ? ' unsaved' : ''));
    tile.type = 'button';
    var pic = el('div', 'art-pic');
    if (name === 'custom') {
      if (own) {
        var img = el('img');
        img.src = own.src;
        img.alt = '';
        pic.appendChild(img);
      } else {
        pic.appendChild(el('span', 'muted small', dr.forget ? 'taken away when saved' : 'nothing uploaded yet'));
        pic.classList.add('art-empty');
      }
    } else if (name === 'none') {
      pic.appendChild(el('span', 'muted small', 'only the sign-in'));
      pic.classList.add('art-empty');
    } else {
      pic.innerHTML = src.innerHTML;  /* our own drawing, from this page's markup */
      var t = pic.querySelector('title');
      if (t) t.removeAttribute('id');
      var sv = pic.querySelector('svg');
      if (sv) sv.removeAttribute('aria-labelledby');
    }
    tile.appendChild(pic);
    var cap = el('div', 'art-cap');
    cap.appendChild(el('span', '', src.dataset.words));
    if (picked && !isNow) cap.appendChild(el('span', 'tag warn', 'after saving'));
    else if (isNow) cap.appendChild(el('span', 'tag ok', 'shown'));
    else if (name === saved.default) cap.appendChild(el('span', 'tag', 'the default'));
    tile.appendChild(cap);
    if (name === 'custom' && own) {
      tile.appendChild(noI18n(el('div', 'art-meta mono small muted',
        (own.name || '') + ' · ' + bytes(own.bytes) + (own.fresh ? '' : ' · ' + (own.by || '?') + ', ' + ago(own.at)))));
    }
    tile.disabled = !ADMIN;
    tile.onclick = function () {
      if (name === 'custom' && !own) { $('art-file').click(); return; }
      artDraft().art = name;
      artMark();
    };
    grid.appendChild(tile);
  });
  $('art-forget').hidden = !own;
  $('art-reset').disabled = dr.art === saved.default;
  $('art-said').textContent = '';
  if (typeof i18nWalk === 'function') { try { i18nWalk(grid); } catch (e) { } }
}
if ($('art-upload')) {
  $('art-upload').onclick = function () { $('art-file').click(); };
  $('art-reset').onclick = function () {
    artDraft().art = (ART.last || {}).default;
    artMark();
  };
  $('art-forget').onclick = function () {
    var dr = artDraft();
    if (dr.data) { dr.data = ''; dr.name = ''; dr.bytes = 0; }
    else dr.forget = true;
    if (dr.art === 'custom' && !((ART.last || {}).logo && !dr.forget)) dr.art = (ART.last || {}).default;
    artMark();
  };
  $('art-file').onchange = function () {
    var file = this.files && this.files[0];
    this.value = '';
    if (!file) return;
    if (file.size > 512 * 1024) { toast(file.name + ' is ' + bytes(file.size) + ' - at most 512 KB', 'bad'); return; }
    var reader = new FileReader();
    reader.onload = function () {
      var dr = artDraft();
      dr.data = String(reader.result || ''); dr.name = file.name; dr.bytes = file.size;
      dr.forget = false; dr.art = 'custom';
      artMark();
    };
    reader.readAsDataURL(file);
  };
}


/* Download the certificate (1.0.31): a window to choose its form - the
   certificate alone (PEM, CRT, DER, PKCS#7) or with its private key (PEM,
   the key alone, PFX) - and, with the key, the password that locks it. */
var CERT_FORMATS = [
  {k: 'pem', group: 'cert', name: 'PEM', ext: '.pem', says: 'Text, Base64. nginx, Apache, HAProxy, Linux.'},
  {k: 'crt', group: 'cert', name: 'CRT', ext: '.crt', says: 'The same PEM text, the ending Windows and browsers open with a double click.'},
  {k: 'der', group: 'cert', name: 'DER', ext: '.cer', says: 'Binary, the certificate alone. Java, Windows, network devices.'},
  {k: 'p7b', group: 'cert', name: 'PKCS#7', ext: '.p7b', says: 'The certificate with its chain in one file. Windows, IIS, Tomcat.'},
  {k: 'pfx', group: 'key', name: 'PFX / PKCS#12', ext: '.pfx', says: 'The certificate, its chain and its private key, locked with a password. Windows, IIS, Azure, Exchange.'},
  {k: 'pem_key', group: 'key', name: 'PEM with the key', ext: '.pem', says: 'The certificate, its chain and its private key in one text file - the key locked when a password is given.'},
  {k: 'key', group: 'key', name: 'The private key', ext: '.key', says: 'Only the private key, PEM - locked with AES-256 when a password is given.'}
];
function certExportAsk(target, prof) {
  var st = {fmt: 'pem', chain: true, legacy: false};
  var hasKey = !prof || prof.has_key !== false;
  modal('Download the certificate', function (body) {
    body.appendChild(el('p', 'note', 'Choose the form the other side wants. The private key is given out only in the forms of the second row - whoever has it can be this server.'));
    var boxes = {};
    [['cert', 'The certificate only', 'nothing secret in it'], ['key', 'With the private key', 'secret - keep it safe']].forEach(function (g) {
      var head = el('div', 'cx-head');
      head.appendChild(el('b', '', g[1]));
      head.appendChild(el('span', 'muted small', g[2]));
      body.appendChild(head);
      var grid = el('div', 'cx-grid' + (g[0] === 'key' ? ' cx-keyed' : ''));
      CERT_FORMATS.filter(function (f) { return f.group === g[0]; }).forEach(function (f) {
        var card = el('button', 'cx-card');
        card.type = 'button';
        var top = el('div', 'cx-top');
        top.innerHTML = iconMarkup(f.group === 'key' ? 'key' : 'file');
        top.appendChild(el('b', '', f.name));
        top.appendChild(el('span', 'cx-ext', f.ext));
        card.appendChild(top);
        card.appendChild(el('div', 'cx-says', f.says));
        if (f.group === 'key' && !hasKey) { card.disabled = true; card.title = 'the private key is not kept here'; }
        card.onclick = function () { st.fmt = f.k; paint(); };
        boxes[f.k] = card;
        grid.appendChild(card);
      });
      body.appendChild(grid);
    });
    var opts = el('div', 'cx-opts');
    var chainSw = switchBox(true);
    chainSw._input.onchange = function () { st.chain = chainSw._input.checked; };
    var chainRow = el('label', 'cx-opt');
    chainRow.appendChild(chainSw);
    chainRow.appendChild(el('span', '', 'The chain too (the certificates of the authority that issued it)'));
    opts.appendChild(chainRow);
    body.appendChild(opts);
    var keyBox = el('div', 'cx-keybox');
    keyBox.appendChild(el('p', 'note warn', 'This file holds the private key of the pages. Anybody who has it, and the password, can pose as this server. Download it only for a server of your own, and give the password apart from the file.'));
    var p1 = secretBox('', '8 characters at least', 'mono'), p2 = secretBox('', 'the same again', 'mono');
    var grid2 = el('div', 'formgrid');
    var f1 = formField('Password', p1), f2 = formField('The password again', p2);
    grid2.appendChild(f1); grid2.appendChild(f2);
    keyBox.appendChild(grid2);
    var pwSays = el('p', 'muted small cx-pwsays');
    keyBox.appendChild(pwSays);
    var legSw = switchBox(false);
    legSw._input.onchange = function () { st.legacy = legSw._input.checked; };
    var legRow = el('label', 'cx-opt');
    legRow.appendChild(legSw);
    legRow.appendChild(el('span', '', 'For an older Windows (Server 2016 and before): 3DES and SHA-1 instead of AES-256'));
    keyBox.appendChild(legRow);
    body.appendChild(keyBox);
    var gen = el('button', 'btn cmd small cx-gen', 'Make a strong password');
    gen.type = 'button';
    setButtonIcon(gen, 'key', 'Make a strong password');
    gen.onclick = function () {
      var abc = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789', out = '', r = new Uint32Array(20);
      crypto.getRandomValues(r);
      for (var i = 0; i < 20; i++) out += abc.charAt(r[i] % abc.length);
      p1.value = out; p2.value = out;
      if (p1._show) p1._show(true);
      if (p2._show) p2._show(true);
      if (navigator.clipboard) navigator.clipboard.writeText(out).then(function () { toast('the password is on the clipboard too', 'good'); }, function () {});
    };
    keyBox.insertBefore(gen, pwSays);
    function paint() {
      Object.keys(boxes).forEach(function (k) { boxes[k].classList.toggle('on', k === st.fmt); });
      var f = CERT_FORMATS.filter(function (x) { return x.k === st.fmt; })[0];
      keyBox.hidden = f.group !== 'key';
      chainRow.hidden = st.fmt === 'der' || st.fmt === 'key';
      legRow.hidden = st.fmt !== 'pfx';
      pwSays.textContent = st.fmt === 'pfx' ? 'A .pfx is always locked: the password is needed to open it.'
        : 'Optional: without one the key is in the file as it is - readable by whoever has the file.';
    }
    MODAL_BODY_CX = {st: st, p1: p1, p2: p2};
    paint();
  }, [
    {words: 'Cancel', close: true},
    {words: 'Download', cls: 'primary', icon: 'download', go: function (button) {
      var m = MODAL_BODY_CX, f = m.st.fmt, keyed = f === 'pfx' || f === 'pem_key' || f === 'key';
      var pw = keyed ? m.p1.value : '';
      if (keyed) {
        if (f === 'pfx' && !pw) { toast('a .pfx needs a password', 'bad'); return; }
        if (pw && pw.length < 8) { toast('a password of 8 characters at least', 'bad'); return; }
        if (pw !== m.p2.value) { toast('the two passwords are not the same', 'bad'); return; }
      }
      busy(button, true);
      api('web', {action: 'tls_export', target: target, format: f, password: pw, legacy: m.st.legacy, chain: m.st.chain}).then(function (x) {
        var raw = atob(x.b64), bytes = new Uint8Array(raw.length);
        for (var i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
        saveFile(x.name, bytes, x.type);
        closeModal();
        toast(x.key ? x.name + ' - keep the password apart from the file' : x.name, 'good');
      }).catch(oops).then(function () { busy(button, false); });
    }}], 'wide');
}
var MODAL_BODY_CX = null;
