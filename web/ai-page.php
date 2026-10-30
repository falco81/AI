<?php
/**
 * ai-page.php — what the page needs before it draws: the headers, the
 * languages, the head.
 *
 * Included by index.php, never a page of its own. Everything here is how
 * otp (and isemon before it) draws itself, so that they look and behave alike:
 * one nonce per page in the Content-Security-Policy, nothing loaded from
 * anywhere but this server, and the words swapped into the chosen language
 * before the browser paints them.
 */
declare(strict_types=1);

if (PHP_SAPI !== 'cli' && isset($_SERVER['SCRIPT_FILENAME'])
        && realpath((string) $_SERVER['SCRIPT_FILENAME']) === realpath(__FILE__)) {
    http_response_code(404);
    exit;
}

const AI_VERSION = '1.0.27';
const AI_LANG_CODE = '/^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$/';

header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');

/* The address bar, as it was typed. nginx counts sign-in attempts by looking
   for api=login in it, and PHP takes the last of two `api=` or decodes `%61pi`
   into `api` where nginx does not; a request written so that the two read it
   differently is nobody's, and is refused before either page looks at it. */
$ai_query = (string) ($_SERVER['QUERY_STRING'] ?? '');
if (substr_count($ai_query, 'api=') > 1 || preg_match('/(^|&)[^=&]*%/', $ai_query)
    // ...nor in its value (1.0.33): api=lo%67in is login to PHP and not to
    // nginx, which then counted no sign-in attempt at all. No endpoint name
    // has anything to escape.
    || preg_match('/(^|&)api=[^&]*[%+]/', $ai_query)
    // ...nor a name PHP reads otherwise than nginx (1.0.61): "+api=login" is
    // api=login to PHP, its leading space dropped, and not to nginx's count.
    || preg_match('/(^|&)(?![A-Za-z0-9_-]*(=|&|$))/', $ai_query)) {
    http_response_code(400);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false, 'error' => 'that address is not one of this page\'s']);
    exit;
}
unset($ai_query);

$nonce = base64_encode(random_bytes(16));
/* The terminal (xterm.js) writes <style> elements of its own as it draws, so
   styles are not held to the nonce; scripts are. Its WebSocket goes to this
   same host. */
$ai_host = (string) ($_SERVER['HTTP_HOST'] ?? '');
$ai_ws = preg_match('/^([A-Za-z0-9.-]{1,253}|\[[0-9A-Fa-f:.]{2,45}\])(:[0-9]{1,5})?$/', $ai_host)
    ? ' wss://' . $ai_host . ' ws://' . $ai_host : '';
header("Content-Security-Policy: default-src 'self'; "
     . "script-src 'self' 'nonce-$nonce'; "
     . "style-src 'self' 'unsafe-inline'; "
     . "img-src 'self' data: blob:; connect-src 'self'$ai_ws; font-src 'self'; object-src 'none'; "
     . "base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
unset($ai_host, $ai_ws);

function h($value): string
{
    return htmlspecialchars((string) $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/* The body as it came, objects kept objects (1.0.61): decoded into arrays,
   {} went on to the daemon as [] and was refused as "not an object". */
function sent_json(): object
{
    $raw = file_get_contents('php://input');
    $got = $raw === false || $raw === '' ? null : json_decode($raw, false);
    return is_object($got) ? $got : new stdClass();
}

function sent_body(): array
{
    $raw = file_get_contents('php://input');
    $got = $raw === false || $raw === '' ? null : json_decode($raw, true);
    return is_array($got) ? $got : [];
}

/* ---- the languages ---------------------------------------------------------
   Exactly otp's: every word is English in the code, and a file in lang/
   says what each English text is in that language. A file that is missing or
   broken is simply not offered, and the page is the English it always was. */
function ai_lang_dir(): string
{
    return __DIR__ . '/lang';
}

function ai_langs(): array
{
    static $known = null;
    if ($known !== null) {
        return $known;
    }
    $known = [];
    foreach (@glob(ai_lang_dir() . '/*.json') ?: [] as $file) {
        $code = basename($file, '.json');
        if (!preg_match(AI_LANG_CODE, $code) || !is_readable($file)) {
            continue;
        }
        $fh = @fopen($file, 'rb');
        if (!$fh) {
            continue;
        }
        $head = (string) @fread($fh, 8192);
        fclose($fh);
        if (!preg_match('/"_meta"\s*:\s*(\{[^{}]*\})/s', $head, $m)) {
            continue;
        }
        $meta = json_decode($m[1], true);
        if (!is_array($meta) || ($meta['code'] ?? '') !== $code) {
            continue;
        }
        $name = trim((string) ($meta['name'] ?? ''));
        $known[$code] = ['code' => $code, 'name' => $name !== '' ? $name : $code,
                         'english' => trim((string) ($meta['english'] ?? $name)) ?: $code,
                         'file' => $file, 'mtime' => (int) @filemtime($file)];
    }
    ksort($known);
    return $known;
}

function ai_lang_pack(string $code): ?array
{
    $langs = ai_langs();
    if (!isset($langs[$code])) {
        return null;
    }
    $raw = @file_get_contents($langs[$code]['file']);
    $all = is_string($raw) ? json_decode($raw, true) : null;
    if (!is_array($all)) {
        return null;
    }
    $pack = ['code' => $code, 'strings' => [], 'patterns' => [], 'rich' => []];
    foreach (['strings', 'patterns', 'rich'] as $part) {
        foreach (($all[$part] ?? []) as $entry) {
            if (!is_array($entry)) {
                continue;
            }
            $from = (string) ($entry['source'] ?? '');
            $to   = (string) ($entry['text'] ?? '');
            if ($from === '' || $to === '' || $to === $from) {
                continue;
            }
            if ($part === 'patterns') {
                $pack[$part][] = [$from, $to];
            } else {
                $pack[$part][$from] = $to;
            }
        }
    }
    $pack['strings'] = (object) $pack['strings'];
    $pack['rich']    = (object) $pack['rich'];
    return $pack;
}

/** The language a page is drawn in: the person's own choice, then this
    browser's, then what the installation says, then English. */
function ai_lang_pick(?array $me, string $default): string
{
    $want = '';
    if ($me && isset($me['prefs']) && is_array($me['prefs'])) {
        $want = (string) ($me['prefs']['lang'] ?? '');
    }
    if ($want === '') {
        $want = (string) ($_COOKIE['ai_lang'] ?? '');
    }
    if ($want === '') {
        $want = $default;
    }
    $langs = ai_langs();
    return ($want !== '' && isset($langs[$want])) ? $want : 'en';
}

/** Answer `?api=lang` - one language's texts as a script - and stop. */
function ai_serve_lang(): void
{
    $code = (string) ($_GET['code'] ?? '');
    $pack = preg_match(AI_LANG_CODE, $code) ? ai_lang_pack($code) : null;
    header('Content-Type: application/javascript; charset=utf-8');
    if ($pack === null) {
        header('Cache-Control: no-store');
        echo "/* no such language here: the page stays in English */\n";
        exit;
    }
    header('Cache-Control: private, max-age=31536000, immutable');
    header_remove('Pragma');
    echo 'window.AI_LANG_PACK = '
        . json_encode($pack, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP
                             | JSON_UNESCAPED_SLASHES) . ";\n";
    exit;
}

/** The language list, English first. */
function ai_lang_list(): array
{
    $langs = ai_langs();
    $out = [isset($langs['en'])
        ? ['code' => 'en', 'name' => $langs['en']['name'], 'english' => $langs['en']['english']]
        : ['code' => 'en', 'name' => 'English', 'english' => 'English']];
    foreach ($langs as $one) {
        if ($one['code'] !== 'en') {
            $out[] = ['code' => $one['code'], 'name' => $one['name'], 'english' => $one['english']];
        }
    }
    return $out;
}

/** Requests that were never this page's: refused before anything is read,
    as on otp - JSON only, same origin only, a few hundred bytes. */
function ai_guard_post(): void
{
    $told = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
    $kind = strtolower((string) ($_SERVER['CONTENT_TYPE'] ?? ''));
    $restore = false;   /* files go to the daemon straight from nginx (/files/), never here */
    if ($told > 8 * 1024 * 1024 && !$restore) {
        http_response_code(413);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => false, 'error' => 'that is too much to send here']);
        exit;
    }
    $from = (string) ($_SERVER['HTTP_SEC_FETCH_SITE'] ?? '');
    /* A browser that says nothing of where the request came from, but sends
       an Origin of another site (1.0.101): refused as a cross-site one. */
    $origin = (string) ($_SERVER['HTTP_ORIGIN'] ?? '');
    $foreign = false;
    if ($from === '' && $origin !== '' && $origin !== 'null') {
        $oh = strtolower((string) parse_url($origin, PHP_URL_HOST));
        $op = parse_url($origin, PHP_URL_PORT);
        $hh = strtolower((string) ($_SERVER['HTTP_HOST'] ?? ''));
        $want = $oh . ($op ? ':' . $op : '');
        $foreign = $oh === '' || ($hh !== $want && $hh !== $oh);
    }
    if ((strpos($kind, 'application/json') !== 0 && !$restore)
            || ($from !== '' && $from !== 'same-origin' && $from !== 'none') || $foreign) {
        http_response_code(403);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['ok' => false, 'error' => 'that request did not come from this page']);
        exit;
    }
}

/** The head of a page: the language, the words-swapper, the style. */
function ai_head(string $title, string $lang, bool $load, string $nonce, string $base): void
{
    $langs = ai_langs();
    $v = AI_VERSION . '-' . (int) @filemtime(__DIR__ . '/assets/ai.css')
       . '-' . (int) @filemtime(__DIR__ . '/assets/core.js');
    echo "<meta charset=\"utf-8\">\n";
    echo "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n";
    echo '<title>' . h($title) . "</title>\n";
    echo '<link rel="icon" href="' . h($base) . 'assets/favicon.svg" type="image/svg+xml">' . "\n";
    if ($load) {
        echo '<script nonce="' . h($nonce) . '" src="?api=lang&amp;code=' . h(rawurlencode($lang))
           . '&amp;v=' . (int) ($langs[$lang]['mtime'] ?? 0) . '"></script>' . "\n";
    }
    echo '<script nonce="' . h($nonce) . '">window.AI_LANGS = '
       . json_encode(ai_lang_list(), JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP)
       . '; window.AI_LANG = ' . json_encode($lang) . ";</script>\n";
    echo '<script nonce="' . h($nonce) . '" src="' . h($base) . 'assets/i18n.js?v=' . h($v)
       . '"></script>' . "\n";
    echo '<link rel="stylesheet" nonce="' . h($nonce) . '" href="' . h($base) . 'assets/ai.css?v='
       . h($v) . '">' . "\n";
    echo '<link rel="stylesheet" href="' . h($base) . 'assets/xterm/xterm.css?v=5.5.0">' . "\n";
}
