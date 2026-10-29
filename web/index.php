<?php
/**
 * index.php — the pages of ai: Claude Code on this server, in the browser.
 *
 * otp's administration pages, for a terminal server: the same header, the
 * same tabs, the same settings down a rail at the left edge, the same popups.
 * It collects nothing itself and decides nothing: every word comes from the
 * ai daemon over its API on localhost, and the daemon decides whether whoever
 * is signed in may have it. The terminals themselves (a WebSocket) and the
 * files go from nginx to the daemon directly, with the same cookie.
 */
declare(strict_types=1);

require_once __DIR__ . '/ai-page.php';
require_once __DIR__ . '/ai-api.php';

if (isset($_GET['api'])) {
    $what = (string) $_GET['api'];
    $post = $_SERVER['REQUEST_METHOD'] === 'POST';
    if ($what === 'lang' && !$post) {
        ai_serve_lang();
    }
    if ($what === 'software' && !$post) {
        /* What the server runs on - and of the pages, what this PHP itself
           is: php-fpm's, not the command line's (as otp's). */
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        [$status, $body] = ai_call('/api/software', 'GET', null, 20.0);
        $data = json_decode((string) $body, true);
        if ($status !== 200 || !is_array($data)) {
            http_response_code($status ?: 503);
            echo $body ?: json_encode(['ok' => false, 'error' => 'the daemon is not answering']);
            exit;
        }
        $ext = [];
        foreach (get_loaded_extensions() as $e) {
            $v = phpversion($e);
            $ext[$e] = ($v === false || $v === PHP_VERSION) ? '' : (string) $v;
        }
        ksort($ext, SORT_NATURAL | SORT_FLAG_CASE);
        $data['pages'] = [
            'php' => PHP_VERSION, 'sapi' => PHP_SAPI, 'extensions' => $ext,
            'opcache' => function_exists('opcache_get_status') && is_array(@opcache_get_status(false))
                && !empty(@opcache_get_status(false)['opcache_enabled']),
            'server' => (string) ($_SERVER['SERVER_SOFTWARE'] ?? ''),
            'os' => PHP_OS_FAMILY,
        ];
        echo json_encode($data);
        exit;
    }
    if ($post) {
        ai_guard_post();
    }
    if ($what === 'login' && $post) {
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        $sent = sent_body();
        [$status, $body] = ai_call('/api/auth/login', 'POST', [
            'name'     => (string) ($sent['name'] ?? ''),
            'password' => (string) ($sent['password'] ?? ''),
            'agent'    => substr((string) ($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 200),
        ], 30.0);
        if ($status === 0) {
            http_response_code(503);
            echo json_encode(['ok' => false, 'error' =>
                'the daemon is not answering — is ai.service running?']);
            exit;
        }
        $data = json_decode($body, true);
        if ($status === 200 && is_array($data) && !empty($data['token'])) {
            ai_set_session((string) $data['token']);
            unset($data['token']);
            echo json_encode($data);
            exit;
        }
        http_response_code($status === 200 ? 400 : $status);
        echo json_encode(is_array($data) ? $data : ['ok' => false, 'error' => 'sign-in failed']);
        exit;
    }
    if ($what === 'mfa' && $post) {
        /* The second step given: the daemon ends the sign-in the password
           opened and hands a new one - its cookie set here, the token never
           shown to the page (as otp's). */
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store');
        $sent = sent_body();
        $sent['lang'] = (string) ($_COOKIE['ai_lang'] ?? '');
        [$status, $body] = ai_call('/api/auth/mfa', 'POST', $sent, 90.0);
        if ($status === 0) {
            http_response_code(503);
            echo json_encode(['ok' => false, 'error' =>
                'the daemon is not answering — is ai.service running?']);
            exit;
        }
        $data = json_decode($body, true);
        if (is_array($data) && !empty($data['token'])) {
            if ($status === 200) {
                ai_set_session((string) $data['token']);
            }
            unset($data['token']);
        }
        http_response_code($status);
        echo json_encode(is_array($data) ? $data : ['ok' => false, 'error' => 'the second step failed']);
        exit;
    }
    if ($what === 'logout' && $post) {
        ai_call('/api/auth/logout', 'POST', [], 10.0);
        ai_clear_session();
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => true]);
        exit;
    }
    /* Reads apart from writes, so a GET can never reach a road that changes
       something, whatever is typed in the address bar. */
    $reads = [
        'status' => '/api/status', 'overview' => '/api/overview', 'whoami' => '/api/auth/whoami',
        'terms' => '/api/terms', 'term' => '/api/term', 'history' => '/api/history',
        'claude' => '/api/claude', 'settings' => '/api/settings', 'users' => '/api/users',
        'events' => '/api/events', 'log' => '/api/log', 'machine' => '/api/machine',
        'net' => '/api/net', 'firewall' => '/api/firewall', 'cert' => '/api/cert',
        'sshkeys' => '/api/sshkeys', 'osup' => '/api/osup',
        'ntp' => '/api/ntp', 'power' => '/api/power', 'upgrade' => '/api/upgrade', 'linux' => '/api/linux',
        'console-login' => '/api/console-login', 'mfa' => '/api/auth/mfa', 'lockouts' => '/api/lockouts',
        'mail' => '/api/mail', 'web' => '/api/web', 'db' => '/api/db', 'export' => '/api/export',
        'rbackup' => '/api/rbackup', 'software' => '/api/software', 'my-settings' => '/api/auth/settings',
    ];
    $writes = [
        'password' => '/api/auth/password', 'prefs' => '/api/auth/prefs',
        'terms' => '/api/terms', 'history' => '/api/history', 'claude' => '/api/claude',
        'settings' => '/api/settings', 'users' => '/api/users', 'net' => '/api/net',
        'trial' => '/api/trial', 'firewall' => '/api/firewall', 'cert' => '/api/cert',
        'sshkeys' => '/api/sshkeys', 'osup' => '/api/osup', 'ntp' => '/api/ntp',
        'power' => '/api/power', 'upgrade' => '/api/upgrade', 'console-login' => '/api/console-login',
        'lockouts' => '/api/lockouts', 'mail' => '/api/mail', 'web' => '/api/web', 'db' => '/api/db',
        'import' => '/api/import', 'rbackup' => '/api/rbackup', 'columns' => '/api/auth/columns',
        'my-settings' => '/api/auth/settings',
    ];
    if ($post) {
        if (!isset($writes[$what])) {
            http_response_code(404);
            header('Content-Type: application/json');
            echo json_encode(['ok' => false, 'error' => 'unknown endpoint']);
            exit;
        }
        ai_relay($writes[$what], 'POST', sent_json(), 300.0);
        exit;
    }
    if (!isset($reads[$what])) {
        http_response_code(404);
        header('Content-Type: application/json');
        echo json_encode(['ok' => false, 'error' => 'unknown endpoint']);
        exit;
    }
    $query = $_GET;
    unset($query['api']);
    ai_relay($reads[$what] . ($query ? '?' . http_build_query($query) : ''), 'GET', null, 60.0);
    exit;
}

/* ---- the page ------------------------------------------------------------ */
$me      = ai_whoami();
/* Signed in with the password, the second step still to give: the sign-in
   page, asking for it - nothing of the pages yet. */
$mfa     = (is_array($me) && !empty($me['mfa'])) ? (string) $me['mfa'] : '';
if ($mfa !== '') { $me = null; }
$health  = ai_get('/api/health', 5.0);
$alive   = is_array($health);
$token_there = file_exists(AI_TOKEN);
$token_ok    = ai_token() !== null;
$web_user    = function_exists('posix_getpwuid') && function_exists('posix_geteuid')
    ? (posix_getpwuid(posix_geteuid())['name'] ?? '?') : '?';
if (!$me && !ai_local()) {
    $token_there = false;
    if (!$token_ok || empty($health['users'])) {
        $alive = false;
    }
    $health = ['lang' => (string) ($health['lang'] ?? 'cs'), 'users' => 1];
}
$initial = $me ? (ai_get('/api/status', 8.0) ?: null) : null;
$host    = (string) ($_SERVER['HTTP_HOST'] ?? php_uname('n'));
$site    = (string) ($initial['site'] ?? '');
$title   = $site !== '' ? $site . ' · ai' : 'ai';
$lang    = ai_lang_pick($me, (string) ($health['lang'] ?? 'cs'));
$load    = $lang !== 'en' && ai_lang_pack($lang) !== null;
if ($me && ($_COOKIE['ai_lang'] ?? '') !== $lang) {
    setcookie('ai_lang', $lang, ['expires' => time() + 365 * 86400, 'path' => '/',
              'secure' => ai_https(), 'httponly' => false, 'samesite' => 'Strict']);
}
$admin = is_array($me) && ($me['role'] ?? '') === 'admin';
?>
<!doctype html>
<html lang="<?= h($lang) ?>" class="app-shell-root<?= $load ? ' i18n-wait' : '' ?>">
<head>
<?php ai_head($title, $lang, $load, $nonce, '/'); ?>
</head>
<body class="app-shell fold-words<?= $me ? ' framed' : '' ?>">
<div class="wrap">

<?php if (!$me): ?>
<div class="signin">
  <div class="signbox">
    <svg class="signart" viewBox="0 0 420 150" role="img" aria-labelledby="sa-title"><title id="sa-title">What this program does</title>
      <rect class="plate" x=".75" y=".75" width="418.5" height="148.5" rx="14"/>
      <rect x="26" y="26" width="200" height="98" rx="8" fill="none" stroke="var(--info)" stroke-width="2" opacity=".8"/>
      <path d="M40 52l10 8-10 8" fill="none" stroke="var(--ok)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <rect class="logline" x="58" y="57" width="90" height="6" rx="3"/>
      <rect class="logline good" x="40" y="78" width="120" height="6" rx="3"/>
      <rect class="logline" x="40" y="92" width="70" height="6" rx="3"/>
      <rect x="40" y="106" width="10" height="8" rx="1.5" fill="var(--warn)"><animate attributeName="opacity" values="1;0;1" dur="1.2s" repeatCount="indefinite"/></rect>
      <path class="flow" d="M236 75 H290"/>
      <rect x="300" y="40" width="94" height="70" rx="10" fill="none" stroke="var(--muted)" stroke-width="2"/>
      <path d="M318 62h58M318 75h40M318 88h50" stroke="var(--muted)" stroke-width="3" stroke-linecap="round" opacity=".7"/>
      <text class="lbl" x="26" y="18">CLAUDE CODE</text>
      <text class="lbl" x="394" y="30" text-anchor="end">THE SERVER</text>
      <text class="lbl" x="210" y="142" text-anchor="middle">IN THE BROWSER · NOTHING ENDS WHEN IT CLOSES</text>
    </svg>
    <div class="card">
    <h1 data-no-i18n><?= h($title) ?></h1>
    <p class="lede">Claude Code on <span data-no-i18n><?= h($host) ?></span>. Sign in to go on.</p>
    <?php if (!$token_ok && $token_there): ?>
      <div class="offline">
        The daemon is running, but this page may not read what it wrote.<br><br>
        <span class="mono"><?= h(AI_TOKEN) ?></span> exists and is not readable by
        <span class="mono"><?= h($web_user) ?></span>, which is what this page runs as.
        On the server:<br>
        <span class="mono">usermod -a -G ai-web <?= h($web_user) ?></span><br>
        <span class="mono">systemctl restart php-fpm nginx</span>
      </div>
    <?php elseif (!$alive): ?>
      <div class="offline">The daemon is not answering. Nobody can sign in until
        <span class="mono">ai.service</span> is running:<br>
        <span class="mono">systemctl status ai</span> ·
        <span class="mono">journalctl -u ai -n 50</span></div>
    <?php elseif (empty($health['users'])): ?>
      <div class="offline">There is no account on this machine yet. Make one on the server:<br>
        <span class="mono">ai --add-user yourname --role admin</span></div>
    <?php endif; ?>
    <div id="mfa-box" data-stage="<?= h($mfa) ?>" hidden></div>
    <form id="signin-form" autocomplete="on"<?= $mfa !== '' ? ' hidden' : '' ?>>
      <input type="text" id="in-name" name="username" placeholder="name" autocomplete="username"
             autocapitalize="none" spellcheck="false" required>
      <input type="password" id="in-pass" name="password" placeholder="password"
             autocomplete="current-password" required>
      <button class="btn primary cmd" type="submit" id="in-go"><svg
        viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
        stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
        ><path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4"/><path d="M14 12h7"/><path
        d="M18 9l3 3-3 3"/></svg><span>Sign in</span></button>
      <div class="said" id="in-said"></div>
    </form>
    <div style="margin-top:14px;display:flex;justify-content:space-between;align-items:center">
      <span class="muted small">ai <?= h(AI_VERSION) ?></span>
      <span class="langpick" id="langpick"></span>
    </div>
    </div>
  </div>
</div>
</div>
<script nonce="<?= h($nonce) ?>" src="/assets/core.js?v=<?= h(AI_VERSION) ?>"></script>
<script nonce="<?= h($nonce) ?>">
(function () {
  var form = $('signin-form'), said = $('in-said'), go = $('in-go');
  var host = $('langpick');
  if (host && window.AI_LANGS && window.AI_LANGS.length > 1) {
    window.AI_LANGS.forEach(function (l) {
      var b = el('button', l.code === window.AI_LANG ? 'on' : '', l.code.toUpperCase());
      b.type = 'button';
      b.setAttribute('data-no-i18n', '');
      b.title = l.name;
      b.onclick = function () {
        document.cookie = 'ai_lang=' + encodeURIComponent(l.code) + '; path=/; max-age=31536000; '
          + 'samesite=strict' + (location.protocol === 'https:' ? '; secure' : '');
        location.reload();
      };
      host.appendChild(b);
    });
  }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    said.className = 'said';
    said.textContent = '';
    go.disabled = true;
    var words = go.querySelector('span');
    words.textContent = 'Signing in…';
    api('login', {name: $('in-name').value, password: $('in-pass').value}).then(function (d) {
      if (d && d.mfa) { form.hidden = true; mfaStep(); return; }
      said.className = 'said good';
      said.textContent = 'Welcome back.';
      location.reload();
    }).catch(function (e) {
      said.className = 'said bad';
      said.textContent = String(e.message || e);
      go.disabled = false;
      words.textContent = 'Sign in';
      $('in-pass').value = '';
      $('in-pass').focus();
    });
  });
  if ($('mfa-box').dataset.stage) mfaStep(); else $('in-name').focus();
}());
</script>
</body>
</html>
<?php exit; endif; ?>

<header>
  <h1 data-no-i18n><?= h($site ?: 'ai') ?> <span class="host"><?= h($host) ?></span></h1>
  <span id="state-pill" class="pill unknown"><span class="dot"></span><span>…</span></span>
  <div class="spacer"></div>
  <div class="btnrow">
    <button type="button" class="btn small mebtn" id="me-btn" data-icon="person"
            title="The account you are signed in as: its password, the language of these pages, the letters of the terminal."><span class="me-name" data-no-i18n><?= h($me['name']) ?></span></button>
    <button class="btn small" id="signout" data-icon="out">Sign out</button>
  </div>
  <div class="updated" id="updated" title="Click to pause or resume the live updates">
    <b>live</b><br><span id="updated-at">…</span></div>
</header>

<div id="offline" class="offline" hidden></div>
<div id="phpsafety" class="offline" hidden></div>
<div id="problems" class="offline warnish" hidden></div>
<div id="trials" class="trials" hidden></div>

<div class="tabs" role="tablist">
  <button role="tab" aria-selected="true" data-tab="terms" data-icon="terminal"
          title="Claude Code and shells running on this server: open one, start a new one. Each goes on running when the browser is closed.">Terminals<span class="count" id="tabn-terms"></span></button>
  <button role="tab" aria-selected="false" data-tab="files" data-icon="archive"
          title="The files of the server: look, fetch, send, drop them in; a text file opened and edited here.">Files</button>
  <button role="tab" aria-selected="false" data-tab="history" data-icon="history"
          title="Every conversation Claude Code has kept, folder by folder - picked up again where it was left.">Conversations</button>
  <button role="tab" aria-selected="false" data-tab="overview" data-icon="chart" class="admin-only"
          title="The server at a glance: what it is, how busy, its disks, its addresses, who is signed in.">Overview</button>
  <button role="tab" aria-selected="false" data-tab="events" data-icon="list"
          title="Every sign-in, every terminal started or ended, every change of a setting and of the machine.">Events</button>
  <button role="tab" aria-selected="false" data-tab="settings" data-icon="gear" class="admin-only"
          title="Claude Code, the accounts, the certificate, the firewall, the network, the time, the system's updates, SSH keys and new versions of this program.">Settings</button>
</div>

<!-- ===================== Terminals ===================== -->
<section class="panel" id="tab-terms">
  <div class="term-layout" id="term-layout">
    <aside class="card term-side" id="term-side">
      <h2>Terminals <span class="right"><button class="btn small cmd primary" id="tl-new" data-icon="add"
          title="A new terminal: Claude Code or a shell, in the folder you choose.">New</button></span></h2>
      <div class="btnrow" style="margin-bottom:8px">
        <input type="search" id="tl-q" placeholder="find a terminal…" style="flex:1;min-width:120px">
        <select id="tl-show" title="Which terminals the list shows.">
          <option value="live">running</option>
          <option value="all">with the ended ones</option>
        </select>
      </div>
      <div id="tl-list" class="tl-list"></div>
    </aside>
    <div class="card term-main" id="term-main">
      <div class="term-empty" id="term-empty">
        <h2>Claude Code on this server</h2>
        <p class="note">Start one in a folder, and it goes on running on the server until it is ended
          here - close the browser, lose the connection, come back from another computer: it is where
          you left it. Files dropped or pasted into the terminal (Ctrl+V) are handed to Claude.</p>
        <div class="btnrow">
          <button class="btn cmd primary" id="te-claude" data-icon="terminal">New Claude Code</button>
          <button class="btn cmd" id="te-shell" data-icon="terminal">New shell</button>
          <button class="btn cmd" id="te-hist" data-icon="history">Pick up a conversation</button>
        </div>
        <div id="te-recent" style="margin-top:18px"></div>
      </div>
      <div class="term-open" id="term-open" hidden>
        <div class="term-bar">
          <button class="btn small iconly" id="tb-side" data-icon="list" title="Show or hide the list of terminals."></button>
          <span class="term-title" id="tb-title" data-no-i18n>…</span>
          <span class="pill small" id="tb-state"><span class="dot"></span><span>…</span></span>
          <span class="muted small mono term-path" id="tb-path" data-no-i18n></span>
          <span class="spacer"></span>
          <button class="btn small" id="tb-cmds" data-icon="list" title="Claude Code's commands - /model, /compact, /resume... - put into the terminal, ready to be sent.">Commands</button>
          <button class="btn small" id="tb-attach" data-icon="upload" title="Give Claude a file: it is written into the working directory's upload folder and its path typed into the terminal. Dropping a file onto the terminal, or pasting one (Ctrl+V), does the same.">File for Claude</button>
          <button class="btn small" id="tb-files" data-icon="archive" title="The files of this terminal's working directory.">Files</button>
          <button class="btn small" id="tb-compose" data-icon="edit" title="A box to write longer text in, sent to the terminal at once - handy on a phone, or for many lines.">Write</button>
          <button class="btn small iconly" id="tb-font-" title="Smaller letters">A−</button>
          <button class="btn small iconly" id="tb-font+" title="Bigger letters">A+</button>
          <button class="btn small iconly" id="tb-full" data-icon="unfold" title="The terminal over the whole window (Esc twice, or this again, to come back)."></button>
          <button class="btn small" id="tb-more" data-icon="gear" title="Rename it, start it again, end it, open it in a window of its own.">More</button>
        </div>
        <div class="term-host" id="term-host" data-no-i18n>
          <div class="term-drop" id="term-drop" hidden><div>Drop the file to give it to Claude</div></div>
          <div class="term-gone" id="term-gone" hidden></div>
        </div>
        <div class="term-keys" id="term-keys"></div>
        <div class="term-compose" id="term-compose" hidden>
          <textarea id="tc-text" rows="4" placeholder="Write here - Ctrl+Enter sends it, with Enter after it"></textarea>
          <div class="btnrow">
            <button class="btn cmd primary" id="tc-send" data-icon="play" title="Put the text into the terminal and press Enter (Ctrl+Enter).">Send</button>
            <button class="btn cmd" id="tc-put" data-icon="edit" title="Put the text into the terminal without pressing Enter.">Only put it in</button>
            <button class="btn cmd" id="tc-close" data-icon="close">Close</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ===================== Files ===================== -->
<section class="panel" id="tab-files" hidden>
  <div class="card full" data-hold>
    <h2>Files <span class="right" id="fl-said"></span></h2>
    <div class="btnrow filters fl-bar">
      <button class="btn cmd iconly" id="fl-up" data-icon="up" title="One folder up."></button>
      <input type="text" id="fl-path" class="mono" spellcheck="false" autocomplete="off" style="flex:1;min-width:200px" title="The folder shown. Type another and press Enter.">
      <select id="fl-roots" title="The folders this account may use, and the ones you keep (the star)."></select>
      <button class="btn cmd iconly" id="fl-fav" data-icon="flag" title="Keep this folder in the list beside, to come back to it at once."></button>
      <label class="muted small"><input type="checkbox" id="fl-hidden" checked> hidden files</label>
      <button class="btn cmd" id="fl-mkdir" data-icon="add">New folder</button>
      <button class="btn cmd" id="fl-newfile" data-icon="edit">New file</button>
      <button class="btn cmd primary" id="fl-send" data-icon="upload" title="Send files from this computer into this folder. Dropping them onto the list, or pasting them (Ctrl+V), does the same.">Send files</button>
      <button class="btn cmd" id="fl-term" data-icon="terminal" title="A new Claude Code terminal in this folder.">Claude here</button>
      <input type="file" id="fl-input" multiple hidden>
    </div>
    <div class="fl-drop-host" id="fl-host">
      <div class="term-drop" id="fl-drop" hidden><div>Drop the files to send them into this folder</div></div>
      <div id="fl-table" class="scroll rowsonly"></div>
    </div>
    <div id="fl-progress"></div>
  </div>
</section>

<!-- ===================== Conversations ===================== -->
<section class="panel" id="tab-history" hidden>
  <div class="card full" data-hold>
    <h2>Conversations <span class="right" id="hi-said"></span></h2>
    <p class="note">What Claude Code keeps of every conversation (~/.claude/projects), newest first.
      Pick one up again: a new terminal opens in its folder with <span class="mono">claude --resume</span>,
      and the conversation goes on where it stopped.</p>
    <div class="btnrow filters">
      <input type="search" id="hi-q" placeholder="words of it, a folder…" style="flex:1;min-width:200px">
      <select id="hi-as" class="admin-only" title="Whose conversations: the Linux account Claude Code ran as."></select>
      <select id="hi-cwd" title="Only those of one folder."><option value="">every folder</option></select>
    </div>
    <div id="hi-table" class="scroll rowsonly"></div>
  </div>
</section>

<!-- ===================== Overview ===================== -->
<section class="panel" id="tab-overview" hidden>
  <div class="grid top">
    <div class="card metric info" id="card-terms"><div class="label">Terminals running</div>
      <div class="value" id="m-terms">–</div><div class="sub" id="m-terms-sub">&nbsp;</div></div>
    <div class="card metric ok" id="card-load"><div class="label">Load</div>
      <div class="value" id="m-load">–</div><div class="sub" id="m-load-sub">&nbsp;</div></div>
    <div class="card metric ok" id="card-mem"><div class="label">Memory</div>
      <div class="value" id="m-mem">–</div><div class="sub" id="m-mem-sub">&nbsp;</div></div>
    <div class="card metric ok" id="card-disk"><div class="label">Disk</div>
      <div class="value" id="m-disk">–</div><div class="sub" id="m-disk-sub">&nbsp;</div></div>
  </div>
  <div class="grid top" style="margin-top:14px">
    <div class="card metric ok" id="card-server"><div class="label">This server</div>
      <div class="value" id="m-server">–</div><div class="sub" id="m-server-sub">&nbsp;</div></div>
    <div class="card metric info" id="card-ver"><div class="label">Version</div>
      <div class="value" id="m-ver">–</div><div class="sub" id="m-ver-sub">&nbsp;</div></div>
    <div class="card metric info" id="card-osup"><div class="label">System updates</div>
      <div class="value" id="m-osup">–</div><div class="sub" id="m-osup-sub">&nbsp;</div></div>
    <div class="card metric ok" id="card-cert"><div class="label">Certificate</div>
      <div class="value" id="m-cert">–</div><div class="sub" id="m-cert-sub">&nbsp;</div></div>
  </div>
  <div class="grid halves" style="margin-top:14px">
    <div class="card"><h2>The machine</h2><div id="ov-machine"></div></div>
    <div class="card"><h2>Signed in now</h2><div id="ov-signed"></div>
      <h2 style="margin-top:16px">Lately</h2><div id="ov-events"></div></div>
  </div>
</section>

<!-- ===================== Events ===================== -->
<section class="panel" id="tab-events" hidden>
  <div class="card full" data-hold>
    <h2>Events <span class="right" id="ev-said"></span></h2>
    <div class="btnrow filters">
      <input type="search" id="ev-q" placeholder="a name, an address, a word…" style="flex:1;min-width:200px">
      <select id="ev-kind"><option value="">every kind</option></select>
      <select id="ev-per"><option>50</option><option selected>100</option><option>500</option></select>
    </div>
    <div id="ev-table" class="scroll rowsonly"></div>
    <div class="pager" id="ev-pager"></div>
  </div>
</section>

<!-- ===================== Settings ===================== -->
<section class="panel" id="tab-settings" hidden>
<div class="ctl-layout">
  <nav class="ctl-nav" id="ctl-nav" aria-label="Settings sections">
    <div class="ctl-navtop">
      <button type="button" class="ctl-pin" id="ctl-pin" aria-pressed="false" aria-label="Keep this menu open"></button>
      <div class="ctl-find-wrap">
        <input type="search" id="ctl-find" placeholder="Find a setting…" autocomplete="off" aria-label="Find a setting">
        <div class="ctl-found" id="ctl-found" hidden></div>
      </div>
    </div>
    <div class="ctl-group">Claude Code</div>
    <button type="button" data-pane="claude" data-icon="terminal" title="Claude Code itself: installed for which accounts, signed in or not, updated; how every terminal starts it.">Claude Code</button>
    <div class="ctl-group">Access</div>
    <button type="button" data-pane="people" data-icon="person" title="Who may sign in to these pages, what each may do, which Linux account their terminals run as, and who is signed in right now.">Accounts</button>
    <button type="button" data-pane="access" data-icon="shield" title="How long a sign-in lasts, wrong passwords, and changes that go back by themselves unless kept.">Signing in</button>
    <button type="button" data-pane="mail" data-icon="mail" title="How the mails of these pages leave this machine: the codes of the second step, and notices of warnings and failures.">Mail</button>
    <button type="button" data-pane="web" data-icon="lock" title="The certificate of these pages: given, or made here.">Certificate and TLS</button>
    <button type="button" data-pane="fw" data-icon="wall" title="Who may reach these pages, and the server's firewall (iptables or firewalld).">Firewall and access</button>
    <div class="ctl-group">Server</div>
    <button type="button" data-pane="network" data-icon="net" title="The server's address, gateway, DNS servers and host name.">Network</button>
    <button type="button" data-pane="time" data-icon="clock" title="The clock: its time zone and time servers (chrony).">Time</button>
    <button type="button" data-pane="osup" data-icon="download" title="The operating system's packages, looked at and updated, its output shown as it goes.">System updates</button>
    <button type="button" data-pane="sshkeys" data-icon="key" title="The keys that may sign in to the server as root over SSH: made here, added or taken away.">SSH keys of root</button>
    <button type="button" data-pane="power" data-icon="power" title="Restart or switch off the server, or only its services.">Restart and power off</button>
    <div class="ctl-group">This program</div>
    <button type="button" data-pane="db" data-icon="db" title="The database: copies made every night, downloaded, put back.">Database</button>
    <button type="button" data-pane="backup" data-icon="upload" title="Backups to other machines: a folder, FTP, FTPS, SFTP, SCP or a Windows share - on a schedule, locked with a password; put back from here.">Backups</button>
    <button type="button" data-pane="carry" data-icon="archive" title="The whole configuration as one file: exported, imported.">Export and import</button>
    <button type="button" data-pane="upgrade" data-icon="up" title="New versions of ai: from the web by themselves, or sent here.">Upgrades</button>
    <button type="button" data-pane="about" data-icon="info" title="Version, the name of the pages, the language, what is running, the log.">About</button>
  </nav>

  <div class="ctl-main">
  <div class="ctl-pane" id="pane-claude">
    <div class="ctl-head"><h2 class="ctl-title">Claude Code</h2>
      <p class="ctl-lede">Claude Code is installed for each Linux account the terminals run as -
        root's is root's, another account's its own. Signing in to Claude (a Claude account or an API
        key) is done once per account, in a terminal: <span class="mono">claude</span> asks by itself the
        first time, or <span class="mono">/login</span>.</p></div>
    <div class="card full"><h2>The accounts <span class="right"><button class="btn small cmd" id="cc-look" data-icon="refresh">Look again</button></span></h2>
      <div id="cc-table"></div></div>
    <div class="card full"><div id="sect-claude"></div></div>
  </div>

  <div class="ctl-pane" id="pane-people" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Accounts</h2>
      <p class="ctl-lede">Who may sign in to these pages. An <b>administrator</b> may do everything,
        start terminals as any Linux account and change the server; a <b>user</b> has terminals of
        their own only, running as the Linux account given here, and files only in its folders.
        Whoever signs in here is, on the server, the Linux account their terminals run as.</p></div>
    <div class="card full">
      <div class="btnrow" style="margin-bottom:12px"><button class="btn cmd primary" id="us-add" data-icon="add">Make an account</button></div>
      <div id="us-table"></div>
    </div>
    <div class="card full"><h2>Signed in now</h2><div id="us-sessions"></div></div>
    <div class="card full" id="cols-card">
      <h2>Columns of the tables <span class="right" id="cols-count"></span></h2>
      <p class="note">Every table on these pages can be laid out the way you read it. Press
        your name at the top right and switch on <b>Edit the columns</b>; then drag the edge of
        a column's heading to make it wider or narrower, and drag the heading itself to move
        the column. The right button on a heading hides a column, brings a hidden one back or
        adds an empty one for room. Twice on an edge puts that table's widths back. Each change
        is kept with your account the moment you let go, not in this browser, and comes back
        wherever you sign in; nobody else's tables change. The switch is for this sign-in
        only: signing out or the sign-in running out turns it off again, and the columns stay
        as you left them.</p>
      <div class="btnrow" style="margin-top:12px">
        <button class="btn cmd" id="cols-edit-go" data-icon="edit"
                title="The same switch as under your name: on for this sign-in only.">Edit the columns</button>
        <button class="btn cmd" id="cols-reset" data-icon="undo"
                title="Every table back as it comes: the widths and the order of the columns you set, on every page. Nobody else's are touched.">Put my columns back as they come</button>
        <button class="btn cmd" id="cols-export" data-icon="download"
                title="How you have set these pages up for yourself, saved as a JSON file.">Export my settings</button>
        <button class="btn cmd" id="cols-import" data-icon="upload"
                title="Read a file saved by Export my settings - here or on another machine running ai.">Import settings…</button>
      </div>
    </div>
    <div class="card full" id="lo-card"><h2>Locked out <span class="right" id="lo-tools"></span></h2>
      <p class="note">Addresses and names with wrong passwords or wrong codes still counted - at the limit
        (Settings → Signing in) they are locked out until the time runs out. Clear one, or all of them,
        and they may try again at once.</p>
      <div id="lo-table"></div></div>
  </div>

  <div class="ctl-pane" id="pane-access" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Signing in</h2></div>
    <div class="card full"><div id="sect-access"></div></div>
  </div>

  <div class="ctl-pane" id="pane-mail" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Mail</h2>
      <p class="ctl-lede">The codes of the second step of signing in, sent by e-mail, and notices of what
        Events marks as a warning or a failure. The mail leaves through your mail server (SMTP), or
        straight to the server of the recipient's domain with no relay at all.</p></div>
    <div class="card full"><div id="sect-mail"></div></div>
    <div class="card full">
      <h2>Try it <span class="right muted small" id="mail-said"></span></h2>
      <p class="note">Sends a short message the way the codes and the notices go, and shows every step:
        the server reached, TLS, signing in, the message handed over and what the server said. Save the
        changes first.</p>
      <div class="btnrow admin-only filters">
        <input type="email" id="mail-to" placeholder="somebody@example.cz" style="flex:1;min-width:240px">
        <select id="mail-test-lang"><option value="cs">Čeština</option><option value="en">English</option></select>
        <button class="btn cmd primary" id="mail-test" data-icon="mail">Send a test</button>
      </div>
      <div id="mail-steps"></div>
      <div class="muted small" id="mail-notices" style="margin-top:8px"></div>
    </div>
    <div class="card full">
      <h2>The certificate authority <span class="right muted small" id="mca-when"></span></h2>
      <p class="note">Needed only when the mail server's certificate was signed by an authority of your own that this machine does not already trust. Paste one (or a whole chain), or read it from the .crt / .pem / .cer file, and press Save the changes below. Each is listed and can be taken out by itself.</p>
      <div id="mca-state"></div>
      <textarea id="mca-pem" rows="5" class="mono admin-only" style="width:100%;margin-top:10px"
                placeholder="-----BEGIN CERTIFICATE-----&#10;MIID...&#10;-----END CERTIFICATE-----"></textarea>
      <div class="btnrow admin-only" style="margin-top:10px">
        <button class="btn cmd" id="mca-file" data-icon="upload">Read a file…</button>
        <button class="btn cmd danger" id="mca-drop" data-icon="trash">Take them all away</button>
        <input type="file" id="mca-input" accept=".pem,.crt,.cer,.txt" hidden>
      </div>
    </div>
  </div>

  <div class="ctl-pane" id="pane-web" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Certificates and TLS</h2>
      <p class="ctl-lede">How the pages speak HTTPS: the certificate with its chain, the protocols,
        the ciphers.</p></div>
    <div class="card full">
      <h2>Certificates</h2>
      <p class="note">A certificate is sent as PEM files (the certificate, its key, the chain, the
        root - in any order, or all in one file) or as a PFX / PKCS#12 file, with its password or
        without; or the request is made here and only what the authority sends back is uploaded.
        It is put in nginx and nginx is asked before it is reloaded - one it does not take is never
        put in.</p>
      <div id="web-certs" class="cert-grid"></div>
    </div>
  </div>

  <div class="ctl-pane" id="pane-db" hidden>
    <div class="ctl-head"><h2 class="ctl-title">The database</h2>
      <p class="ctl-lede">One database holds everything: the accounts and their sign-ins, the settings,
        the events and the list of terminals. It is a SQLite file on this machine. The secrets in it are
        sealed with a key kept beside it, in the state folder - and every copy is kept with that key
        beside it.</p></div>
    <div class="card full"><div id="sect-db"></div></div>
    <div class="card full">
      <h2>The copies it keeps <span class="right muted small" id="db-now"></span></h2>
      <p class="note">Every night at the hour above, SQLite's own backup of the database in use, packed with
        the key its secrets are sealed with and config.json. A copy is the database whole: put back, it
        replaces every account, every setting and every event - and a copy of what is there now is made
        first, so that can be undone too.</p>
      <div id="db-says"></div>
      <div class="btnrow admin-only" style="margin-top:12px">
        <button class="btn cmd" id="db-make" data-icon="save" title="A copy now, rather than waiting for tonight. It is kept with the others and counts as one of them.">Make one now</button>
      </div>
      <div id="db-copies" style="margin-top:18px"></div>
      <div class="admin-only" style="margin-top:18px">
        <h4>Put a copy back</h4>
        <p class="note">A copy from somewhere else - one downloaded from here, or from another server of ai.
          Nothing happens until it has been read, checked and shown to you.</p>
        <div class="drop" id="dbu-drop">
          <input type="file" id="dbu-file" accept=".gz,.db,application/gzip,application/octet-stream" hidden>
          <span id="dbu-says">Drop a copy here, or press to choose one</span>
        </div>
      </div>
    </div>
  </div>

  <div class="ctl-pane" id="pane-backup" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Backups</h2>
      <p class="ctl-lede">A backup is everything of this program: the whole database (the accounts, every
        setting, the certificate and TLS, the firewall, the events, the list of terminals), the key its
        secrets are sealed with and this machine's config.json - with RESTORE.md, the exact steps to bring
        it all back on a machine installed from nothing. Locked with the password below; sent to every
        destination switched on - a folder, FTP, FTPS, SFTP, SCP or a Windows/Samba share. The files of the
        Linux accounts (their projects, ~/.claude) are not in it.</p></div>
    <div id="rb-top"></div>
    <div class="card full"><h2>When, how many, and the password</h2><div id="sect-backup"></div></div>
    <div class="card full"><h2>Where they go <span class="right" id="rb-add-host"></span></h2>
      <div id="rb-targets"></div></div>
    <div class="card full"><h2>What was sent <span class="right" id="rb-runs-tools"></span></h2><div id="rb-runs"></div></div>
  </div>

  <div class="ctl-pane" id="pane-carry" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Export and import</h2>
      <p class="ctl-lede">The whole configuration as one file: the settings, the accounts of these pages,
        the certificate and TLS of the pages, who may reach the pages, the firewall and the mail server's
        authorities. The events and the terminals are not in it: they move with a copy of the database.
        On the command line: ai --export-config FILE [--with-secrets] and ai --import-config FILE --yes.</p></div>
    <div class="card full">
      <div class="btnrow">
        <button class="btn cmd admin-only" id="ex-plain" data-icon="download">Export</button>
        <button class="btn cmd danger admin-only" id="ex-whole" data-icon="key">Export with the secrets</button>
        <button class="btn cmd admin-only" id="ex-load" data-icon="upload">Import a file…</button>
        <input type="file" id="ex-file" accept=".json" hidden>
      </div>
    </div>
  </div>

  <div class="ctl-pane" id="pane-fw" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Firewall and access</h2>
      <p class="ctl-lede">Who may reach the pages, and the machine's own firewall: what ai's
        functions need is let in by itself, and you add whatever else you want - for IPv4 and IPv6.</p></div>
    <div class="card full">
      <h2>Who may reach the pages</h2>
      <p class="note">The pages, the terminals and the files share ports 80 and 443, so who may
        reach them is said by nginx; the machine itself always may.</p>
      <div id="fw-access"></div>
    </div>
    <div class="card full">
      <div class="fw-top"><div><h2>The firewall (iptables / ip6tables)</h2>
        <p class="note" id="fw-lede"></p></div>
        <div id="fw-master"></div></div>
      <div id="fw-nodes" class="fw-nodes"></div>
      <div id="fw-body"></div>
    </div>
  </div>

  <div class="ctl-pane" id="pane-network" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Network</h2>
      <p class="ctl-lede">The server's address, gateway, DNS servers, host name and - switched on - IPv6,
        set through NetworkManager. A change goes back by itself unless it is kept: open the pages at the
        new address and press Keep it.</p></div>
    <div id="net-host"></div>
  </div>
  <div class="ctl-pane" id="pane-time" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Time</h2>
      <p class="ctl-lede">The server keeps its clock with chrony: here is how far off it is, which servers it
        follows, and the time servers and the time zone set for it.</p></div>
    <div id="ntp-host"></div>
  </div>
  <div class="ctl-pane" id="pane-power" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Restart and power off</h2>
      <p class="ctl-lede">The server restarted or switched off from here; the page follows it down and up
        again. The terminals live in tmux: restarting the server ends them all, restarting only ai or the
        web server (below) ends none.</p></div>
    <div id="pw-host"></div>
    <div class="card full"><h2>Only the services</h2>
      <div class="btnrow">
        <button class="btn cmd" id="pw-ai" data-icon="refresh">Restart ai</button>
        <button class="btn cmd" id="pw-web" data-icon="refresh">Restart nginx and PHP</button>
      </div></div>
  </div>
  <div class="ctl-pane" id="pane-osup" hidden>
    <div class="ctl-head"><h2 class="ctl-title">System updates</h2>
      <p class="ctl-lede">The operating system's packages, updated by dnf (or apt). The update runs as a job
        of its own on the server - closing the page or restarting ai does not stop it - and what it says
        shows here as it goes. A restart an update needs is offered when it is done, or made by itself.</p></div>
    <div id="ou-host"></div>
  </div>
  <div class="ctl-pane" id="pane-sshkeys" hidden>
    <div class="ctl-head"><h2 class="ctl-title">SSH keys of root</h2>
      <p class="ctl-lede">The keys that may sign in to the server as root over SSH - the lines of
        /root/.ssh/authorized_keys. A key made here is shown once, to be kept by you, and kept nowhere on the
        server; one of your own is put on by its public half. Every change is written into Events.</p></div>
    <div id="sk-host"></div>
  </div>

  <div class="ctl-pane" id="pane-upgrade" hidden>
    <div class="ctl-head"><h2 class="ctl-title">Upgrades</h2>
      <p class="ctl-lede">A new version of ai is checked before anything is put in: signed by a release
        key this server trusts, every file the one signed. Then its own install.sh --upgrade runs, as by
        hand. The terminals go on running; the pages come back after a few seconds.</p></div>
    <div class="card full"><h2>From the web <span class="right"><button class="btn small cmd" id="up-look" data-icon="refresh">Look now</button></span></h2>
      <div id="up-web"></div></div>
    <div class="card full"><h2>A package sent from here</h2>
      <p class="note">An <span class="mono">ai-X.Y.Z.tar.gz</span> as released.</p>
      <div class="btnrow"><button class="btn cmd" id="up-send" data-icon="upload">Send a package…</button>
        <input type="file" id="up-input" accept=".tar.gz,.tgz,application/gzip" hidden></div>
      <div id="up-sent"></div></div>
    <div class="card full"><div id="sect-upgrade"></div></div>
    <div class="card full admin-only" id="up-down-card" hidden>
      <h2>Going back to an older version</h2>
      <p class="note">Only to a version that is safe: one that reads what the newer versions wrote into
        the database the same, and has every security fix that matters - each version says how far back
        it may go, and the highest of what ran on this database counts. A copy of the database is made
        first (Settings → Database); the package is checked like an upgrade's. The terminals go on running.</p>
      <div id="up-down"></div>
    </div>
    <div class="card full"><h2>What the last upgrade said <span class="right muted small" id="up-state"></span></h2>
      <pre class="lines tall" id="up-log">–</pre></div>
    <div class="card full"><h2>On the command line</h2>
      <pre class="lines">ai --upgrade-check              # what is at the address, and whether it is newer
ai --upgrade-online             # the newest: fetched, checked, put in
ai --downgrade X.Y.Z            # back to an older one - only a safe one
tar xzf ai-X.Y.Z.tar.gz && cd ai-X.Y.Z && ./install.sh --upgrade</pre></div>
  </div>

  <div class="ctl-pane" id="pane-about" hidden>
    <div class="ctl-head"><h2 class="ctl-title">About</h2></div>
    <div class="card full"><div id="about-state"></div></div>
    <div class="card full"><div id="ab-software"></div></div>
    <div class="card full"><h2>The console at login</h2>
      <p class="note">The ai console (<code>ai --console</code>) opens by itself when root signs in at the
        server's screen or over SSH; q leaves it for the ordinary shell. Never inside a terminal of these pages.</p>
      <div id="ab-console"></div></div>
    <div class="card full"><div id="sect-general"></div></div>
    <div class="card full"><h2>Its own log <span class="right"><button class="btn small cmd" id="ab-log" data-icon="refresh">Read it</button></span></h2>
      <pre class="lines tall" id="ab-logtext">–</pre></div>
  </div>

  <div class="save-bar" id="save-bar">
    <button class="btn cmd primary" id="set-save" data-icon="save"
            title="Save the changed settings. They take effect the moment they are saved - nothing restarts.">Save the changes</button>
    <button class="btn cmd" id="set-reset" data-icon="undo"
            title="Throw away the changes on this page and read the settings back as they are.">Put them back</button>
    <span class="muted small" id="set-said"></span>
  </div>
  </div>
</div>
</section>

</div><!-- /wrap -->

<div class="modal" id="modal" hidden>
  <div class="box" id="modal-box">
    <div class="head"><h3 id="modal-title">…</h3>
      <button class="xbtn" id="modal-x" data-icon="close" aria-label="Close"></button></div>
    <div class="body" id="modal-body"></div>
    <div class="foot" id="modal-foot"></div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script nonce="<?= h($nonce) ?>">
var ME = <?= json_encode($me, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP) ?>;
var STATUS = <?= $initial ? json_encode($initial, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP) : 'null' ?>;
var PHP_SAFETY = <?= $admin ? json_encode(ai_php_safety(), JSON_HEX_TAG | JSON_HEX_AMP) : 'null' ?>;
</script>
<script nonce="<?= h($nonce) ?>" src="/assets/core.js?v=<?= h(AI_VERSION) ?>"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/xterm/xterm.js?v=5.5.0"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/xterm/addon-fit.js?v=0.10.0"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/xterm/addon-web-links.js?v=0.11.0"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/cols.js?v=<?= h(AI_VERSION) ?>"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/term.js?v=<?= h(AI_VERSION) ?>"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/app.js?v=<?= h(AI_VERSION) ?>"></script>
<script nonce="<?= h($nonce) ?>" src="/assets/system.js?v=<?= h(AI_VERSION) ?>"></script>
</body>
</html>
