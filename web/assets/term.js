/* term.js - a terminal of the server, drawn in the page.
   xterm.js on a WebSocket to the daemon (/ws/term), which attaches a tmux
   client to the terminal for as long as this page looks at it. Closing the
   page ends that client and nothing else: the terminal goes on running in
   tmux, and is attached again here - or anywhere - when it is opened. A
   connection that drops is made again by itself, for as long as the terminal
   runs. Files dropped onto it or pasted into it (Ctrl+V) are written into the
   working directory's upload folder and their path typed in, for Claude. */
'use strict';

var TERM = {
  t: null, fit: null, ws: null, id: '', host: null, want: false, tries: 0,
  timer: null, ping: null, onState: null, ro: false, font: 14, lastSize: '',
  mods: {ctrl: false, alt: false}, onMods: null, locked: false,
  pos: {size: 0, at: 0, mode: false, rows: 0}, sb: null, posTimer: null
};

/* ---- tmux's history, moved from here (1.0.9) --------------------------------
   The page is one more tmux client: tmux draws the screen in place, so the
   history is tmux's, not xterm's. A mouse wheel reaches it by itself (tmux's
   mouse mode); a finger on a tablet and the scroll bar beside the terminal
   ask the daemon to move it - in tmux's copy mode, left again at the bottom. */
function termAsk(msg) {
  if (TERM.ws && TERM.ws.readyState === 1) TERM.ws.send(JSON.stringify(msg));
}
function termPosDraw() {
  var sb = TERM.sb;
  if (!sb) return;
  var p = TERM.pos, total = p.size + Math.max(1, p.rows || (TERM.t ? TERM.t.rows : 24));
  var shown = Math.max(1, p.rows || (TERM.t ? TERM.t.rows : 24));
  sb.bar.hidden = !p.size;
  var h = Math.max(8, 100 * shown / total);
  var top = 100 * (p.size - p.at) / total;
  sb.thumb.style.height = h + '%';
  sb.thumb.style.top = Math.min(100 - h, top) + '%';
  sb.live.hidden = !p.mode;
  if (p.mode) sb.liveWords.textContent = p.at + ' / ' + p.size;
}
function termScrollBar(host) {
  if (TERM.sb) return;
  var bar = el('div', 'term-sb');
  var thumb = el('div', 'term-sb-thumb');
  bar.appendChild(thumb);
  var live = el('button', 'term-live');
  live.type = 'button';
  live.hidden = true;
  live.innerHTML = iconMarkup('down', 14);
  var liveWords = el('span', '', '');
  live.appendChild(el('span', '', 'Back to now'));
  live.appendChild(liveWords);
  liveWords.className = 'muted';
  live.onclick = function () { termAsk({t: 'live'}); if (TERM.t) TERM.t.focus(); };
  host.appendChild(bar);
  host.appendChild(live);
  TERM.sb = {bar: bar, thumb: thumb, live: live, liveWords: liveWords};
  var dragging = false, sent = 0;
  var place = function (y) {
    var r = bar.getBoundingClientRect();
    var p = TERM.pos, total = p.size + Math.max(1, p.rows || 24);
    var h = Math.max(1, p.rows || 24) / total;
    var f = Math.max(0, Math.min(1, (y - r.top) / r.height - h / 2) / Math.max(0.0001, 1 - h));
    var now = Date.now();
    if (now - sent > 70) { sent = now; termAsk({t: 'scrollto', f: Math.min(1, f)}); }
  };
  var down = function (e) {
    dragging = true;
    var y = e.touches ? e.touches[0].clientY : e.clientY;
    place(y);
    e.preventDefault();
    e.stopPropagation();
  };
  var move = function (e) {
    if (!dragging) return;
    place(e.touches ? e.touches[0].clientY : e.clientY);
    e.preventDefault();
  };
  var up = function () { dragging = false; };
  bar.addEventListener('mousedown', down);
  bar.addEventListener('touchstart', down, {passive: false});
  window.addEventListener('mousemove', move);
  window.addEventListener('touchmove', move, {passive: false});
  window.addEventListener('mouseup', up);
  window.addEventListener('touchend', up);
  /* A finger on the terminal itself: up and down moves the history, as on
     a phone - a tap is still a tap (the keyboard, a selection). */
  var ty = null, acc = 0, moved = false;
  host.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1 || e.target.closest('.term-sb, .term-live')) return;
    ty = e.touches[0].clientY; acc = 0; moved = false;
  }, {passive: true});
  host.addEventListener('touchmove', function (e) {
    if (ty === null || e.touches.length !== 1) return;
    var y = e.touches[0].clientY;
    acc += y - ty;
    ty = y;
    if (!moved && Math.abs(acc) < 10) return;
    moved = true;
    var cell = (TERM.host && TERM.t) ? TERM.host.clientHeight / Math.max(1, TERM.t.rows) : 18;
    var n = Math.trunc(acc / cell);
    if (n) { acc -= n * cell; termAsk({t: 'scroll', n: n}); }
    e.preventDefault();
  }, {passive: false});
  host.addEventListener('touchend', function () { ty = null; });
  /* The wheel is tmux's own: only the bar is told where it got to. */
  host.addEventListener('wheel', debounce(function () { termAsk({t: 'pos'}); }, 120), {passive: true});
}

/* What a key with Ctrl held sends, as a terminal sends it: a letter its
   control character, and the few others a terminal knows. */
function termCtrl(ch) {
  var c = ch.charCodeAt(0);
  if (c >= 97 && c <= 122) return String.fromCharCode(c - 96);
  if (c >= 64 && c <= 95) return String.fromCharCode(c - 64);
  return {' ': '\x00', '2': '\x00', '3': '\x1b', '4': '\x1c', '5': '\x1d', '6': '\x1e', '7': '\x1f',
          '8': '\x7f', '/': '\x1f', '?': '\x7f'}[ch] || ch;
}
/* The Ctrl and Alt of the toolbar (a phone has neither): held for the next key. */
function termModsUse(d) {
  var m = TERM.mods;
  if (!m.ctrl && !m.alt) return d;
  if (d.length === 1 || (d.length === 2 && d.charAt(0) === '\x1b' && !m.alt)) {
    if (m.ctrl) d = d.length === 1 ? termCtrl(d) : d;
    if (m.alt) d = '\x1b' + d;
  } else if (/^\x1b\[[A-D]$/.test(d)) {
    /* An arrow with Ctrl or Alt: xterm's own way, CSI 1;5A / 1;3A. */
    d = '\x1b[1;' + (1 + (m.alt ? 2 : 0) + (m.ctrl ? 4 : 0)) + d.charAt(2);
  }
  m.ctrl = m.alt = false;
  if (TERM.onMods) TERM.onMods();
  return d;
}

/* Every key of the keyboard into the terminal (Keyboard Lock): the page over
   the whole screen, and the keys the browser keeps for itself - Ctrl+W,
   Ctrl+T, Ctrl+N, Ctrl+Tab, Esc, F11 - given to the terminal too. Chrome,
   Edge and Opera do it; holding Esc leaves it. */
function termLockKeys(on) {
  var root = document.documentElement;
  if (on) {
    var go = root.requestFullscreen ? root.requestFullscreen() : Promise.reject(new Error('no full screen'));
    return Promise.resolve(go).then(function () {
      if (navigator.keyboard && navigator.keyboard.lock) return navigator.keyboard.lock();
      throw new Error('this browser keeps some keys for itself (Ctrl+W, Ctrl+T, Ctrl+N): Chrome or Edge give them all');
    }).then(function () { TERM.locked = true; if (TERM.t) TERM.t.focus(); return true; });
  }
  TERM.locked = false;
  try { if (navigator.keyboard && navigator.keyboard.unlock) navigator.keyboard.unlock(); } catch (e) { }
  if (document.fullscreenElement && document.exitFullscreen) return document.exitFullscreen().then(function () { return false; });
  return Promise.resolve(false);
}
document.addEventListener('fullscreenchange', function () {
  if (!document.fullscreenElement && TERM.locked) {
    TERM.locked = false;
    try { navigator.keyboard.unlock(); } catch (e) { }
    if (TERM.onMods) TERM.onMods();
  }
  setTimeout(termFit, 80);
});

function termFont() {
  var f = 14;
  try { f = parseInt(localStorage.getItem('ai-term-font') || '', 10) || 0; } catch (e) { }
  if (!f && ME && ME.prefs && ME.prefs.font) f = parseInt(ME.prefs.font, 10) || 14;
  return Math.max(8, Math.min(32, f || (window.innerWidth < 700 ? 12 : 14)));
}

function termTheme() {
  return {
    background: '#0b0f14', foreground: '#e6edf3', cursor: '#e6edf3', cursorAccent: '#0b0f14',
    selectionBackground: 'rgba(88,166,255,.35)',
    black: '#484f58', red: '#ff7b72', green: '#3fb950', yellow: '#d29922', blue: '#58a6ff',
    magenta: '#bc8cff', cyan: '#39c5cf', white: '#b1bac4', brightBlack: '#6e7681',
    brightRed: '#ffa198', brightGreen: '#56d364', brightYellow: '#e3b341', brightBlue: '#79c0ff',
    brightMagenta: '#d2a8ff', brightCyan: '#56d4dd', brightWhite: '#f0f6fc'
  };
}

/** A file sent to the daemon as the body itself - never a form (php2shell's
    guard refuses multipart) - with how far it got as it goes. */
function sendFile(url, file, progress) {
  return new Promise(function (ok, bad) {
    var x = new XMLHttpRequest();
    x.open('POST', url);
    x.setRequestHeader('Content-Type', 'application/octet-stream');
    x.setRequestHeader('X-Ai-Req', '1');
    if (x.upload && progress) {
      x.upload.onprogress = function (e) { if (e.lengthComputable) progress(e.loaded, e.total); };
    }
    x.onload = function () {
      var d = null;
      try { d = JSON.parse(x.responseText); } catch (e) { }
      if (x.status === 200 && d && d.ok !== false) ok(d);
      else if (x.status === 413) bad(new Error((d && d.error) || 'that file is bigger than the server takes'));
      else bad(new Error((d && d.error) || ('HTTP ' + x.status)));
    };
    x.onerror = function () { bad(new Error('the server could not be reached')); };
    x.send(file);
  });
}

/** Straight to the daemon, by the cookie: the files. */
function filesApi(what, query, body) {
  var url = '/files/' + what + (query ? '?' + query : '');
  var opts = {credentials: 'same-origin', headers: {'X-Ai-Req': '1'}};
  if (body !== undefined) {
    opts.method = 'POST';
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  return fetch(url, opts).then(function (r) {
    return r.text().then(function (t) {
      var d;
      try { d = JSON.parse(t); } catch (e) {
        throw new Error(r.status === 502 || r.status === 504 ? 'the server is not answering just now'
                        : 'the page got something that is not an answer');
      }
      if (r.status === 401) { signedOutNow(); }
      if (!r.ok || d.ok === false) { var err = new Error(d.error || ('HTTP ' + r.status)); err.status = r.status; throw err; }
      return d;
    });
  });
}

/** Files given to Claude in the open terminal: one after another, each said. */
function termGiveFiles(files) {
  if (!TERM.id || !files || !files.length) return;
  var id = TERM.id, list = Array.prototype.slice.call(files);
  var next = function () {
    var f = list.shift();
    if (!f) { if (TERM.t) TERM.t.focus(); return; }
    var name = f.name || ('pasted.' + ((f.type || '').split('/')[1] || 'bin').replace('jpeg', 'jpg'));
    toast('sending ' + name + '…');
    sendFile('/files/chat?term=' + encodeURIComponent(id) + '&name=' + encodeURIComponent(name), f,
      function (a, b) { if (b > 2e6) toast(name + ' ' + Math.round(a * 100 / b) + ' %'); })
      .then(function (d) {
        toast((d.image ? 'the picture ' : 'the file ') + name + ' is Claude\'s now: ' + d.path, 'good');
        next();
      }).catch(function (e) { oops(e); next(); });
  };
  next();
}

function termWsUrl(id, cols, rows) {
  return (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/term?id='
    + encodeURIComponent(id) + '&c=' + cols + '&r=' + rows + (TERM.ro ? '&ro=1' : '');
}

function termSay(state, words) {
  if (TERM.onState) TERM.onState(state, words);
}

function termSendSize() {
  if (!TERM.t || !TERM.ws || TERM.ws.readyState !== 1) return;
  var s = TERM.t.cols + 'x' + TERM.t.rows;
  if (s === TERM.lastSize) return;
  TERM.lastSize = s;
  TERM.ws.send(JSON.stringify({t: 'resize', c: TERM.t.cols, r: TERM.t.rows}));
}

function termFit() {
  if (!TERM.t || !TERM.fit || !TERM.host || !TERM.host.offsetWidth) return;
  try { TERM.fit.fit(); } catch (e) { }
  termSendSize();
}

function termMake(host) {
  var t = new window.Terminal({
    fontFamily: '"JetBrains Mono", "Cascadia Mono", Menlo, Consolas, "DejaVu Sans Mono", "Liberation Mono", monospace',
    fontSize: termFont(), lineHeight: 1.1, cursorBlink: true, scrollback: 5000,
    allowProposedApi: true, macOptionIsMeta: true, theme: termTheme(), drawBoldTextInBrightColors: false,
    rightClickSelectsWord: false, windowsMode: false, altClickMovesCursor: false
  });
  var fit = new window.FitAddon.FitAddon();
  t.loadAddon(fit);
  try {
    t.loadAddon(new window.WebLinksAddon.WebLinksAddon(function (e, uri) {
      window.open(uri, '_blank', 'noopener,noreferrer');
    }));
  } catch (e) { }
  t.open(host);
  /* What tmux copies (a selection made with the mouse in it) comes as OSC 52:
     put on this computer's clipboard. */
  try {
    t.parser.registerOscHandler(52, function (data) {
      var i = data.indexOf(';');
      var b64 = i >= 0 ? data.slice(i + 1) : data;
      if (!b64 || b64 === '?') return true;
      try {
        var bin = atob(b64), bytes = new Uint8Array(bin.length);
        for (var n = 0; n < bin.length; n++) bytes[n] = bin.charCodeAt(n);
        var text = new TextDecoder('utf-8').decode(bytes);
        if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(function () {
          toast('copied', 'good');
        }, function () { });
      } catch (e) { }
      return true;
    });
  } catch (e) { }
  /* The keys a terminal wants that a browser would take, or that xterm
     sends as the plain key: Ctrl+C with something selected copies it;
     Ctrl+Shift+C copies, Ctrl+Shift+V and Ctrl+V paste (the browser's paste,
     which hands pictures and files to Claude too); Shift+Enter, Ctrl+Enter
     and Alt+Enter are a new line in Claude Code (Esc and Enter, as its own
     /terminal-setup makes them). Everything else is xterm's: every letter
     with Ctrl or Alt, the arrows, Home/End, Page Up/Down, Insert/Delete,
     F1-F12, with Shift, Ctrl and Alt as a terminal sends them. */
  t.attachCustomKeyEventHandler(function (e) {
    if (e.type !== 'keydown') return true;
    var k = e.key, ctrl = e.ctrlKey || e.metaKey;
    if (ctrl && !e.altKey && !e.shiftKey && (k === 'c' || k === 'C') && t.hasSelection()) {
      copyText(t.getSelection(), null, 'copied');
      t.clearSelection();
      e.preventDefault();
      return false;
    }
    if (ctrl && e.shiftKey && (k === 'C' || k === 'c')) {
      if (t.hasSelection()) copyText(t.getSelection(), null, 'copied');
      e.preventDefault();
      return false;
    }
    if (ctrl && (k === 'v' || k === 'V') && !e.altKey) return false;          /* the browser pastes */
    if (k === 'Enter' && (e.shiftKey || e.altKey || (ctrl && !e.metaKey)) && !(e.shiftKey && ctrl)) {
      e.preventDefault();
      if (TERM.ws && TERM.ws.readyState === 1 && !TERM.ro) TERM.ws.send(new TextEncoder().encode('\x1b\r'));
      return false;
    }
    /* The browser's own for these, never the page's: they stay the terminal's. */
    if (ctrl && /^[a-z]$/i.test(k) && 'cvCV'.indexOf(k) < 0) e.preventDefault();
    if (/^F([1-9]|1[0-2])$/.test(k) || (e.altKey && /^[a-z0-9]$/i.test(k))) e.preventDefault();
    return true;
  });
  t.onData(function (d) {
    if (TERM.ws && TERM.ws.readyState === 1 && !TERM.ro) TERM.ws.send(new TextEncoder().encode(termModsUse(d)));
  });
  t.onBinary(function (d) {
    if (!TERM.ws || TERM.ws.readyState !== 1 || TERM.ro) return;
    var b = new Uint8Array(d.length);
    for (var i = 0; i < d.length; i++) b[i] = d.charCodeAt(i) & 255;
    TERM.ws.send(b);
  });
  t.onResize(function () { termSendSize(); });
  return {t: t, fit: fit};
}

/* The file pasted (Ctrl+V) or dropped goes to Claude; text pasted goes in as
   it always does, by xterm itself. */
function termWireFiles(host) {
  if (host._wired) return;
  host._wired = true;
  host.addEventListener('paste', function (e) {
    var cd = e.clipboardData;
    if (!cd) return;
    var files = [];
    if (cd.files && cd.files.length) files = Array.prototype.slice.call(cd.files);
    else if (cd.items) {
      Array.prototype.forEach.call(cd.items, function (it) {
        if (it.kind === 'file') { var f = it.getAsFile(); if (f) files.push(f); }
      });
    }
    if (files.length) {
      e.preventDefault();
      e.stopPropagation();
      termGiveFiles(files);
    }
  }, true);
  var drop = $('term-drop'), depth = 0;
  var has = function (e) {
    return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0;
  };
  host.addEventListener('dragenter', function (e) { if (!has(e)) return; e.preventDefault(); depth++; drop.hidden = false; });
  host.addEventListener('dragover', function (e) { if (!has(e)) return; e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
  host.addEventListener('dragleave', function (e) { if (!has(e)) return; depth = Math.max(0, depth - 1); if (!depth) drop.hidden = true; });
  host.addEventListener('drop', function (e) {
    if (!has(e)) return;
    e.preventDefault();
    depth = 0;
    drop.hidden = true;
    termGiveFiles(e.dataTransfer.files);
  });
}

function termClose() {
  TERM.want = false;
  clearTimeout(TERM.timer);
  clearInterval(TERM.ping);
  clearInterval(TERM.posTimer);
  if (TERM.ws) { try { TERM.ws.close(); } catch (e) { } }
  TERM.ws = null;
  TERM.id = '';
}

/** Open terminal `id` in `host`: the one xterm of the page, emptied and attached. */
function termOpen(id, host, onState) {
  termClose();
  TERM.id = id;
  TERM.host = host;
  TERM.onState = onState;
  TERM.want = true;
  TERM.tries = 0;
  TERM.lastSize = '';
  if (!TERM.t) {
    var made = termMake(host);
    TERM.t = made.t;
    TERM.fit = made.fit;
    if (window.ResizeObserver) new ResizeObserver(debounce(termFit, 60)).observe(host);
    window.addEventListener('resize', debounce(termFit, 100));
    termWireFiles(host);
    termScrollBar(host);
  }
  TERM.t.reset();
  termFit();
  termConnect();
  setTimeout(function () { if (TERM.t) TERM.t.focus(); }, 30);
}

function termConnect() {
  if (!TERM.want || !TERM.id) return;
  var id = TERM.id;
  termFit();
  var ws;
  try {
    ws = new WebSocket(termWsUrl(id, TERM.t.cols || 120, TERM.t.rows || 40));
  } catch (e) {
    termSay('lost', String(e.message || e));
    return;
  }
  ws.binaryType = 'arraybuffer';
  TERM.ws = ws;
  termSay('connecting', 'connecting…');
  var opened = false;
  ws.onopen = function () {
    if (TERM.ws !== ws) return;
    opened = true;
    TERM.tries = 0;
    TERM.lastSize = '';
    termSay('live', 'live');
    termSendSize();
    clearInterval(TERM.ping);
    TERM.ping = setInterval(function () {
      if (ws.readyState === 1) ws.send(JSON.stringify({t: 'ping'}));
    }, 25000);
    /* Where in the history, for the bar: asked now and then while it is seen. */
    clearInterval(TERM.posTimer);
    TERM.pos = {size: 0, at: 0, mode: false, rows: 0};
    termAsk({t: 'pos'});
    TERM.posTimer = setInterval(function () {
      if (ws.readyState === 1 && !document.hidden && TERM.host && TERM.host.offsetWidth) ws.send(JSON.stringify({t: 'pos'}));
    }, 2000);
  };
  ws.onmessage = function (m) {
    if (TERM.ws !== ws) return;
    if (typeof m.data === 'string') {
      var d = null;
      try { d = JSON.parse(m.data); } catch (e) { return; }
      if (d && d.t === 'error') termSay('lost', d.error || 'the terminal could not be reached');
      if (d && d.t === 'pos') { TERM.pos = d; termPosDraw(); return; }
      /* This sign-in has ended (signed out here or elsewhere, or ended by an
         administrator): the terminal goes on running, the page asks for a
         sign-in again. */
      if (d && d.t === 'signed-out') { TERM.want = false; termSay('lost', 'signed out - the terminal goes on running'); setTimeout(function () { location.reload(); }, 1500); }
      return;
    }
    TERM.t.write(new Uint8Array(m.data));
  };
  ws.onclose = function () {
    if (TERM.ws !== ws) return;
    clearInterval(TERM.ping);
    TERM.ws = null;
    if (!TERM.want || TERM.id !== id) return;
    /* Is it still running? Then the connection is made again; if not, the
       page says it has ended. */
    fetch('?api=term&id=' + encodeURIComponent(id) + '&lines=5', {credentials: 'same-origin'})
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!TERM.want || TERM.id !== id) return;
        var st = d && d.term ? d.term.state : '';
        if (st === 'ended') { termSay('ended', 'it has ended'); return; }
        termRetry(opened);
      }).catch(function () { termRetry(opened); });
  };
}

function termRetry(wasOpen) {
  if (!TERM.want) return;
  TERM.tries += 1;
  var wait = Math.min(10000, wasOpen && TERM.tries === 1 ? 300 : 1000 * Math.pow(1.6, TERM.tries - 1));
  termSay('lost', 'the connection dropped - again in ' + Math.round(wait / 1000) + ' s');
  clearTimeout(TERM.timer);
  TERM.timer = setTimeout(termConnect, wait);
}

/** Text into the terminal as though pasted (bracketed), and Enter after it. */
function termType(text, enter) {
  if (!TERM.ws || TERM.ws.readyState !== 1) { toast('the terminal is not connected', 'bad'); return; }
  var body = text ? '\x1b[200~' + text + '\x1b[201~' : '';
  TERM.ws.send(new TextEncoder().encode(body));
  if (enter) setTimeout(function () { if (TERM.ws) TERM.ws.send(new TextEncoder().encode('\r')); }, 120);
  if (TERM.t) TERM.t.focus();
}

/** Raw keys into the terminal (Esc, Tab, arrows...). */
function termKeys(seq) {
  if (!TERM.ws || TERM.ws.readyState !== 1) { toast('the terminal is not connected', 'bad'); return; }
  TERM.ws.send(new TextEncoder().encode(termModsUse(seq)));
  if (TERM.t) TERM.t.focus();
}

function termSetFont(n) {
  n = Math.max(8, Math.min(32, n));
  try { localStorage.setItem('ai-term-font', String(n)); } catch (e) { }
  if (TERM.t) {
    TERM.t.options.fontSize = n;
    termFit();
  }
}
