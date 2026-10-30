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
  /* On the alternate screen (Claude Code full-screen) the history is the
     program's own and where it is is not known here: the bar is a jog
     wheel then - the thumb in the middle, dragged up or down by as much as
     the history should move, and back to the middle when let go. */
  sb.bar.hidden = !p.size && !p.alt;
  sb.bar.classList.toggle('jog', !!p.alt);
  if (p.alt) {
    sb.thumb.style.height = '22%';
    sb.thumb.style.top = (39 + (sb.jog || 0)) + '%';
    sb.live.hidden = true;
    return;
  }
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
  /* The jog wheel: lines moved = the drag in rows of the terminal; a click
     above or below the thumb a page. */
  var jogY = 0, jogAcc = 0;
  var cell = function () { return (TERM.host && TERM.t) ? TERM.host.clientHeight / Math.max(1, TERM.t.rows) : 18; };
  var down = function (e) {
    var y = e.touches ? e.touches[0].clientY : e.clientY;
    e.preventDefault();
    e.stopPropagation();
    if (TERM.pos.alt) {
      var tr = thumb.getBoundingClientRect();
      if (y < tr.top || y > tr.bottom) {
        var rows = Math.max(1, (TERM.t ? TERM.t.rows : 24) - 2);
        termAsk({t: 'scroll', n: y < tr.top ? rows : -rows});
        return;
      }
      dragging = 'jog'; jogY = y; jogAcc = 0; TERM.sb.jogFrom = y;
      return;
    }
    dragging = true;
    place(y);
  };
  var move = function (e) {
    if (!dragging) return;
    var y = e.touches ? e.touches[0].clientY : e.clientY;
    if (dragging === 'jog') {
      var r = bar.getBoundingClientRect();
      TERM.sb.jog = Math.max(-39, Math.min(39, 100 * (y - TERM.sb.jogFrom) / Math.max(1, r.height)));
      jogAcc += (jogY - y) * 3;
      jogY = y;
      var n = Math.trunc(jogAcc / cell());
      if (n) { jogAcc -= n * cell(); termAsk({t: 'scroll', n: n}); }
      termPosDraw();
    } else place(y);
    e.preventDefault();
  };
  var up = function () {
    if (dragging === 'jog') { TERM.sb.jog = 0; termPosDraw(); }
    dragging = false;
  };
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

/* The colours of the terminals (1.0.19). "classic" is PuTTY's - the VGA
   palette, a full blue for mc's panels; "soft" is the pages' own, lighter
   one, kept for whoever liked it. Chosen under More, kept with the account. */
var TERM_PALETTES = {
  classic: {
    background: '#000000', foreground: '#bbbbbb', cursor: '#bbbbbb', cursorAccent: '#000000',
    selectionBackground: 'rgba(88,166,255,.40)',
    black: '#000000', red: '#bb0000', green: '#00bb00', yellow: '#bbbb00', blue: '#0000bb',
    magenta: '#bb00bb', cyan: '#00bbbb', white: '#bbbbbb', brightBlack: '#555555',
    brightRed: '#ff5555', brightGreen: '#55ff55', brightYellow: '#ffff55', brightBlue: '#5555ff',
    brightMagenta: '#ff55ff', brightCyan: '#55ffff', brightWhite: '#ffffff'
  },
  xterm: {
    background: '#000000', foreground: '#e5e5e5', cursor: '#e5e5e5', cursorAccent: '#000000',
    selectionBackground: 'rgba(88,166,255,.40)',
    black: '#000000', red: '#cd0000', green: '#00cd00', yellow: '#cdcd00', blue: '#0000ee',
    magenta: '#cd00cd', cyan: '#00cdcd', white: '#e5e5e5', brightBlack: '#7f7f7f',
    brightRed: '#ff0000', brightGreen: '#00ff00', brightYellow: '#ffff00', brightBlue: '#5c5cff',
    brightMagenta: '#ff00ff', brightCyan: '#00ffff', brightWhite: '#ffffff'
  },
  linux: {
    background: '#000000', foreground: '#aaaaaa', cursor: '#aaaaaa', cursorAccent: '#000000',
    selectionBackground: 'rgba(88,166,255,.40)',
    black: '#000000', red: '#aa0000', green: '#00aa00', yellow: '#aa5500', blue: '#0000aa',
    magenta: '#aa00aa', cyan: '#00aaaa', white: '#aaaaaa', brightBlack: '#555555',
    brightRed: '#ff5555', brightGreen: '#55ff55', brightYellow: '#ffff55', brightBlue: '#5555ff',
    brightMagenta: '#ff55ff', brightCyan: '#55ffff', brightWhite: '#ffffff'
  },
  tango: {
    background: '#000000', foreground: '#d3d7cf', cursor: '#d3d7cf', cursorAccent: '#000000',
    selectionBackground: 'rgba(114,159,207,.40)',
    black: '#2e3436', red: '#cc0000', green: '#4e9a06', yellow: '#c4a000', blue: '#3465a4',
    magenta: '#75507b', cyan: '#06989a', white: '#d3d7cf', brightBlack: '#555753',
    brightRed: '#ef2929', brightGreen: '#8ae234', brightYellow: '#fce94f', brightBlue: '#729fcf',
    brightMagenta: '#ad7fa8', brightCyan: '#34e2e2', brightWhite: '#eeeeec'
  },
  solarized: {
    background: '#002b36', foreground: '#839496', cursor: '#93a1a1', cursorAccent: '#002b36',
    selectionBackground: 'rgba(147,161,161,.30)',
    black: '#073642', red: '#dc322f', green: '#859900', yellow: '#b58900', blue: '#268bd2',
    magenta: '#d33682', cyan: '#2aa198', white: '#eee8d5', brightBlack: '#586e75',
    brightRed: '#cb4b16', brightGreen: '#93a1a1', brightYellow: '#657b83', brightBlue: '#839496',
    brightMagenta: '#6c71c4', brightCyan: '#93a1a1', brightWhite: '#fdf6e3'
  },
  dracula: {
    background: '#282a36', foreground: '#f8f8f2', cursor: '#f8f8f2', cursorAccent: '#282a36',
    selectionBackground: 'rgba(68,71,90,.85)',
    black: '#21222c', red: '#ff5555', green: '#50fa7b', yellow: '#f1fa8c', blue: '#bd93f9',
    magenta: '#ff79c6', cyan: '#8be9fd', white: '#f8f8f2', brightBlack: '#6272a4',
    brightRed: '#ff6e6e', brightGreen: '#69ff94', brightYellow: '#ffffa5', brightBlue: '#d6acff',
    brightMagenta: '#ff92df', brightCyan: '#a4ffff', brightWhite: '#ffffff'
  },
  light: {
    background: '#ffffff', foreground: '#1f2328', cursor: '#1f2328', cursorAccent: '#ffffff',
    selectionBackground: 'rgba(9,105,218,.25)',
    black: '#24292f', red: '#cf222e', green: '#116329', yellow: '#4d2d00', blue: '#0969da',
    magenta: '#8250df', cyan: '#1b7c83', white: '#6e7781', brightBlack: '#57606a',
    brightRed: '#a40e26', brightGreen: '#1a7f37', brightYellow: '#633c01', brightBlue: '#218bff',
    brightMagenta: '#a475f9', brightCyan: '#3192aa', brightWhite: '#8c959f'
  },
  soft: {
    background: '#0b0f14', foreground: '#e6edf3', cursor: '#e6edf3', cursorAccent: '#0b0f14',
    selectionBackground: 'rgba(88,166,255,.35)',
    black: '#484f58', red: '#ff7b72', green: '#3fb950', yellow: '#d29922', blue: '#58a6ff',
    magenta: '#bc8cff', cyan: '#39c5cf', white: '#b1bac4', brightBlack: '#6e7681',
    brightRed: '#ffa198', brightGreen: '#56d364', brightYellow: '#e3b341', brightBlue: '#79c0ff',
    brightMagenta: '#d2a8ff', brightCyan: '#56d4dd', brightWhite: '#f0f6fc'
  }
};
/* Their names, in the order offered. Bold drawn bright where the palette's
   own terminal does so (PuTTY, xterm, the Linux console). */
var TERM_PALETTE_NAMES = [['classic', 'Classic - as PuTTY'], ['xterm', 'xterm'], ['linux', 'The Linux console'],
  ['tango', 'Tango (GNOME)'], ['solarized', 'Solarized dark'], ['dracula', 'Dracula'],
  ['soft', 'Soft - the pages\' own'], ['light', 'Light']];
var TERM_BOLD_BRIGHT = {classic: 1, xterm: 1, linux: 1};
/** The palettes as swatches to choose from: each its 16 colours on its own background. */
function termPalettePicker(onPick) {
  var box = el('div', 'pal-pick');
  var now = termPalette();
  TERM_PALETTE_NAMES.forEach(function (n) {
    var th = TERM_PALETTES[n[0]];
    var b = el('button', 'pal-card' + (n[0] === now ? ' on' : ''));
    b.type = 'button';
    var sw = el('div', 'pal-sw');
    sw.style.background = th.background;
    var t = el('span', 'pal-txt', 'ls -l');
    t.style.color = th.foreground;
    sw.appendChild(t);
    var dots = el('div', 'pal-dots');
    ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', 'brightBlack', 'brightRed', 'brightGreen',
     'brightYellow', 'brightBlue', 'brightMagenta', 'brightCyan', 'brightWhite'].forEach(function (k) {
      var d = el('i');
      d.style.background = th[k];
      dots.appendChild(d);
    });
    sw.appendChild(dots);
    b.appendChild(sw);
    b.appendChild(el('span', 'pal-name', n[1]));
    b.onclick = function () {
      box.querySelectorAll('.pal-card').forEach(function (x) { x.classList.toggle('on', x === b); });
      termSetPalette(n[0]);
      if (onPick) onPick(n[0]);
    };
    box.appendChild(b);
  });
  return box;
}
function termPalette() {
  var want = '';
  try { want = (typeof prefs === 'function' && prefs().term_colors) || ''; } catch (e) { }
  return TERM_PALETTES[want] ? want : 'classic';
}
function termTheme() { return TERM_PALETTES[termPalette()]; }
/** Another palette, on the terminal open now and on every one opened after. */
function termSetPalette(name) {
  if (!TERM_PALETTES[name]) return;
  if (typeof savePrefs === 'function') savePrefs({term_colors: name}).catch(function () { });
  if (typeof ME !== 'undefined' && ME) { ME.prefs = ME.prefs || {}; ME.prefs.term_colors = name; }
  var th = TERM_PALETTES[name];
  if (TERM.t) { TERM.t.options.theme = th; TERM.t.options.drawBoldTextInBrightColors = !!TERM_BOLD_BRIGHT[name]; }
  document.documentElement.style.setProperty('--term-bg', th.background);
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
    /* Alt codes, as Windows types them (1.0.23): Alt held, digits on the
       numeric keypad, the character when Alt is let go - Alt+64 is @. xterm
       sent each digit as Esc+digit; they are gathered here instead. */
    if (e.type === 'keydown' && e.altKey && !e.ctrlKey && !e.metaKey && /^Numpad[0-9]$/.test(e.code || '')) {
      TERM.altDigits = (TERM.altDigits || '') + e.code.slice(6);
      e.preventDefault();
      return false;
    }
    if (e.type === 'keyup' && e.key === 'Alt' && TERM.altDigits) {
      var ch = termAltCode(TERM.altDigits);
      TERM.altDigits = '';
      if (ch && TERM.ws && TERM.ws.readyState === 1 && !TERM.ro) {
        TERM.ws.send(new TextEncoder().encode(ch));
        TERM.altSent = {ch: ch, at: Date.now()};     /* the browser may type it too: once is enough */
      }
      return false;
    }
    if (e.type === 'keydown' && e.key === 'Alt') TERM.altDigits = '';
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
    if (TERM.altSent && d === TERM.altSent.ch && Date.now() - TERM.altSent.at < 800) { TERM.altSent = null; return; }
    if (TERM.ws && TERM.ws.readyState === 1 && !TERM.ro) TERM.ws.send(new TextEncoder().encode(termModsUse(d)));
  });
  /* PuTTY's way (1.0.23): what is selected is copied by itself, the right
     button pastes. Chosen under the account; the menu is then Ctrl + right button. */
  t.onSelectionChange(debounce(function () {
    if (termRightMode() !== 'paste' || !t.hasSelection()) return;
    var sel = t.getSelection();
    if (sel && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(sel).catch(function () { });
  }, 250));
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
  /* The palette kept with the account - read again, it may have come after the first terminal was made. */
  TERM.t.options.theme = termTheme();
  /* Bold in the bright colours, as PuTTY draws it - ls's folders bold blue on black. */
  TERM.t.options.drawBoldTextInBrightColors = !!TERM_BOLD_BRIGHT[termPalette()];
  document.documentElement.style.setProperty('--term-bg', termTheme().background);
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

/* The character of an Alt code: Alt+nnn the old DOS code page (437), as
   Windows has it; Alt+0nnn the Windows one (1252); past 255 Windows takes
   the rest of 256. */
var CP437_LOW = '\u0000☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼';
var CP437_HIGH = 'ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■\u00a0';
var CP1252_HIGH = '€\u0081‚ƒ„…†‡ˆ‰Š‹Œ\u008dŽ\u008f\u0090‘’“”•–—˜™š›œ\u009džŸ';
function termAltCode(digits) {
  var n = parseInt(digits, 10);
  if (isNaN(n) || n <= 0) return '';
  if (digits.charAt(0) === '0') {
    n = n % 256;
    if (n >= 128 && n < 160) return CP1252_HIGH.charAt(n - 128);
    return String.fromCharCode(n);
  }
  n = n % 256;
  if (n < 32) return CP437_LOW.charAt(n);
  if (n === 127) return '⌂';
  if (n >= 128) return CP437_HIGH.charAt(n - 128);
  return String.fromCharCode(n);
}
function termRightMode() {
  var want = '';
  try { want = (typeof prefs === 'function' && prefs().term_right) || ''; } catch (e) { }
  return want === 'menu' ? 'menu' : 'paste';
}
/** The clipboard into the terminal - the right button in PuTTY's way. */
function termPasteClipboard() {
  if (!navigator.clipboard || !navigator.clipboard.readText) { toast('this browser lets only Ctrl+V paste', 'warn'); return; }
  navigator.clipboard.readText().then(function (text) { if (text) termType(text, false); },
    function () { toast('the browser did not let the page read the clipboard - allow it for this page, or Ctrl+V', 'warn'); });
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
