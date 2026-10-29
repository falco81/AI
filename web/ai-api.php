<?php
/**
 * ai-api.php — the pages' side of the daemon API.
 *
 * Taken from otp (and isemon before it), where it is the whole of the web
 * side. The page holds nothing and decides nothing: the daemon does all the
 * work and answers on http://127.0.0.1:<port>; this file is the thin client
 * that talks to it. The terminals (WebSocket) and the files go to the daemon
 * straight from nginx, with the same session cookie; everything else comes
 * through here.
 *
 * Two things travel with every request that changes something: the API token
 * the daemon dropped in a file readable only by root and the web server's
 * group, and the session of whoever is signed in. The browser holds the
 * session in a cookie it cannot read itself (HttpOnly), and never sees the
 * token at all — so a page that somebody manages to run JavaScript in still
 * cannot lift anything worth having out of it.
 */
declare(strict_types=1);

// Included by index.php and admin/index.php, never a page of its own. The nginx
// vhost shipped with this refuses it by name, but a site's own vhost may not,
// and a file that answers when asked is a file somebody will one day put a
// side effect in. Asked for directly, it answers as though it were not there.
if (PHP_SAPI !== 'cli' && isset($_SERVER['SCRIPT_FILENAME'])
        && realpath((string) $_SERVER['SCRIPT_FILENAME']) === realpath(__FILE__)) {
    http_response_code(404);
    exit;
}

const AI_HOST    = '127.0.0.1';
/* api_port in the settings, as the daemon wrote it down when it started
   (1.0.59); 9871 where it has not. */
define('AI_PORT', (static function (): int {
    $p = (int) trim((string) @file_get_contents('/run/ai/api-port'));
    return ($p >= 1024 && $p <= 65535) ? $p : 9871;
})());
const AI_TOKEN   = '/run/ai/api-token';

/* The sign-in: one cookie, for the whole site - nginx hands it to the daemon
   with the terminals and the files too. */
define('AI_COOKIE', 'ai_session');
define('AI_COOKIE_PATH', '/');

/** Whether this page was reached over TLS - directly, or through a proxy in
 *  front that terminates it and says so. */
function ai_https(): bool
{
    if (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') {
        return true;
    }
    return strtolower((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https';
}

/** Whether this request comes from the machine itself - the operator at the
 *  console, who may be told where things are and what the pages run as. */
function ai_local(): bool
{
    return in_array((string) ($_SERVER['REMOTE_ADDR'] ?? ''), ['127.0.0.1', '::1'], true);
}

/** Read the API token the daemon wrote for us, or null if we can't. */
function ai_token(): ?string
{
    if (!is_readable(AI_TOKEN)) {
        return null;
    }
    $token = trim((string) @file_get_contents(AI_TOKEN));
    return $token !== '' ? $token : null;
}

/** The session of whoever is signed in, from the cookie. */
function ai_session(): string
{
    $got = (string) ($_COOKIE[AI_COOKIE] ?? '');
    return preg_match('/^[A-Za-z0-9_-]{16,128}$/', $got) === 1 ? $got : '';
}

/** Start one. Same-site and HttpOnly, and Secure whenever the page is on TLS. */
function ai_set_session(string $token): void
{
    setcookie(AI_COOKIE, $token, [
        'expires'  => 0,                 /* until the browser is closed */
        'path'     => AI_COOKIE_PATH,
        'secure'   => ai_https(),
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
}

function ai_clear_session(): void
{
    setcookie(AI_COOKIE, '', [
        'expires'  => time() - 3600,
        'path'     => AI_COOKIE_PATH,
        'secure'   => ai_https(),
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
}

/**
 * Call the daemon. Returns [status, body-string]; status 0 means unreachable.
 * $payload, when given, is sent as a JSON body and turns this into a POST.
 */
function ai_call(string $path, string $method = 'GET', array|object|null $payload = null,
                     float $timeout = 30.0): array
{
    $headers = ['Accept: application/json'];
    $headers[] = 'X-Ai-Client: '
        . preg_replace('/[^0-9a-fA-F:.]/', '', (string) ($_SERVER['REMOTE_ADDR'] ?? ''));
    // The name the pages were reached by, for the link in a token's mail
    // (1.0.33) - built by the daemon from this, never taken from the page.
    $host = (string) ($_SERVER['HTTP_HOST'] ?? '');
    if (preg_match('/^([A-Za-z0-9.-]{1,253}|\[[0-9A-Fa-f:.]{2,45}\])(:[0-9]{1,5})?$/', $host)) {
        $headers[] = 'X-Ai-Host: ' . $host;
    }
    $session = ai_session();
    if ($session !== '') {
        $headers[] = 'X-Ai-Session: ' . $session;
    }
    // The language of the page (1.0.127): a code mailed from it is written in it.
    $lang = preg_replace('/[^a-z]/', '', (string) ($_COOKIE['ai_lang'] ?? ''));
    if (strlen($lang) === 2) {
        $headers[] = 'X-Ai-Lang: ' . $lang;
    }
    $token = ai_token();
    if ($token === null) {
        return [0, ''];
    }
    $headers[] = 'X-Ai-Token: ' . $token;

    $body = null;
    if ($payload !== null) {
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        if ($body === false) {
            /* A number JSON cannot hold (1e400 is INF to PHP) - the request's
               fault, said so, not a 500 with an empty body (1.0.103). */
            return [400, json_encode(['ok' => false, 'error' => 'a number in the request is too big']) ?: ''];
        }
        $headers[] = 'Content-Type: application/json';
        $headers[] = 'Content-Length: ' . strlen($body);
    } elseif ($method !== 'GET') {
        $headers[] = 'Content-Length: 0';
    }

    /* A socket, spoken to by hand, rather than file_get_contents('http://…').
       That one needs allow_url_fopen, which a hardened php.ini switches off —
       and when it is off every call here fails silently and the dashboard
       says "the daemon is not answering" about a daemon that is running
       perfectly. A socket to localhost needs no ini setting at all.

       The daemon always sends a Content-Length and never chunks, so reading
       the body is reading that many bytes. */
    $errno = 0;
    $errstr = '';
    $sock = @stream_socket_client(
        'tcp://' . AI_HOST . ':' . AI_PORT, $errno, $errstr, $timeout,
        STREAM_CLIENT_CONNECT);
    if ($sock === false) {
        return [0, ''];
    }
    stream_set_timeout($sock, (int) $timeout);

    $request = $method . ' ' . $path . " HTTP/1.1\r\n"
        . 'Host: ' . AI_HOST . ':' . AI_PORT . "\r\n"
        . "Connection: close\r\n"
        . implode("\r\n", $headers) . "\r\n\r\n";
    if ($body !== null) {
        $request .= $body;
    }
    if (@fwrite($sock, $request) === false) {
        @fclose($sock);
        return [0, ''];
    }

    $raw = '';
    while (!feof($sock)) {
        $chunk = @fread($sock, 65536);
        if ($chunk === false || $chunk === '') {
            $info = stream_get_meta_data($sock);
            if (!empty($info['timed_out'])) {
                @fclose($sock);
                return [0, ''];
            }
            break;
        }
        $raw .= $chunk;
    }
    @fclose($sock);

    $split = strpos($raw, "\r\n\r\n");
    if ($split === false) {
        return [0, ''];
    }
    $head = substr($raw, 0, $split);
    $reply = substr($raw, $split + 4);
    $status = 0;
    if (preg_match('#^HTTP/\S+\s+(\d+)#', $head, $m)) {
        $status = (int) $m[1];
    }
    return [$status, $reply];
}

/** Call the daemon and return the decoded reply, or null. */
function ai_get(string $path, float $timeout = 30.0): ?array
{
    [$status, $body] = ai_call($path, 'GET', null, $timeout);
    if ($status !== 200) {
        return null;
    }
    $data = json_decode($body, true);
    return is_array($data) ? $data : null;
}

/** Pass a daemon reply straight through to the browser. */
function ai_relay(string $path, string $method = 'GET', array|object|null $payload = null,
                      float $timeout = 30.0): void
{
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');

    if (ai_token() === null) {
        http_response_code(503);
        /* Where the token lives is for whoever is on the machine; from
           anywhere else it is a daemon that is not answering. */
        echo json_encode(['ok' => false, 'error' => ai_local()
            ? 'the API token is unreadable — is ai.service running, and is '
              . AI_TOKEN . ' readable by the web server?'
            : 'the daemon is not answering — is ai.service running?']);
        return;
    }
    [$status, $body] = ai_call($path, $method, $payload, $timeout);
    if ($status === 0) {
        http_response_code(503);
        echo json_encode(['ok' => false, 'error' =>
            'the daemon is not answering — is ai.service running?']);
        return;
    }
    /* A 401 is no longer taken as the end of the session here (1.0.73): while
       the web address moves between the nodes, or a node restarts during an
       upgrade, one answer may say so for a moment, and throwing the cookie
       away signed the person out in the middle of watching the upgrade. The
       page asks again (whoami) and goes to the sign-in only when the session
       is really gone; signing out takes the cookie away. */
    http_response_code($status);
    echo ai_squeeze($body);
}

/**
 * A large answer, compressed for a browser that says it takes gzip.
 *
 * A page of failed attempts with every field in it is a few hundred kilobytes
 * and shrinks to a tenth of that.
 */
function ai_squeeze(string $body): string
{
    $accepts = (string) ($_SERVER['HTTP_ACCEPT_ENCODING'] ?? '');
    if (strlen($body) < 2048 || !function_exists('gzencode') || headers_sent()
        || stripos($accepts, 'gzip') === false || ini_get('zlib.output_compression')) {
        return $body;
    }
    $packed = gzencode($body, 4);
    if ($packed === false) {
        return $body;
    }
    header('Content-Encoding: gzip');
    header('Vary: Accept-Encoding');
    header('Content-Length: ' . strlen($packed));
    return $packed;
}

/** Whoever is signed in, as the daemon sees them, or null. */
function ai_whoami(): ?array
{
    $got = ai_get('/api/auth/whoami', 5.0);
    $who = is_array($got) ? ($got['who'] ?? null) : null;
    if (is_array($who)) {
        $prefs = $who['prefs'] ?? null;
        $who['prefs'] = (is_array($prefs) && $prefs) ? $prefs : new stdClass();
        /* An empty layout is an object, not a list, to the page. */
        $cols = $who['cols'] ?? null;
        $who['cols'] = (is_array($cols) && $cols) ? $cols : new stdClass();
    }
    return $who;
}

/**
 * Whether the PHP running this page is safe from php2shell (CVE-2026-109618,
 * CVE-2026-109619), as far as it can tell from inside: its version against
 * the fixed releases of 21 October 2026, and whether this page's own guard -
 * request bodies never taken apart by PHP, no upload progress - is in force.
 * A distribution that backported the fix keeps its old version number, so a
 * version below the fixed ones is "may be affected", not "is".
 */
function ai_php_safety(): array
{
    $fixed = ['8.2' => '8.2.35', '8.3' => '8.3.36', '8.4' => '8.4.27', '8.5' => '8.5.12'];
    $branch = PHP_MAJOR_VERSION . '.' . PHP_MINOR_VERSION;
    if (isset($fixed[$branch])) {
        $patched = version_compare(PHP_VERSION, $fixed[$branch], '>=');
        $needs = $fixed[$branch];
    } else {
        /* Newer than the branches fixed that day is fixed; older is end of
           life, with no fix from PHP itself. */
        $patched = version_compare($branch, '8.5', '>');
        $needs = $patched ? '' : '8.2.35';
    }
    $reading = (string) ini_get('enable_post_data_reading');
    $progress = (string) ini_get('session.upload_progress.enabled');
    $off = function (string $v): bool {
        return in_array(strtolower($v), ['0', '', 'off', 'false', 'no'], true);
    };
    return [
        'version'  => PHP_VERSION,
        'sapi'     => PHP_SAPI,
        'patched'  => $patched,
        'needs'    => $needs,
        'guarded'  => $off($reading) && $off($progress),
        'post_reading' => !$off($reading),
        'upload_progress' => !$off($progress),
    ];
}
