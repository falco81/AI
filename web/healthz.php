<?php
/**
 * healthz.php — does this server answer? 200 "ok" when the ai daemon does,
 * 503 when not. Says nothing else, so anybody may ask (a monitor, a load
 * balancer).
 */
declare(strict_types=1);

require_once __DIR__ . '/ai-api.php';

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');
$h = ai_get('/api/health', 4.0);
$u = ai_upgrading();
if ((!is_array($h) || empty($h['ok'])) && $u !== null && $u['state'] === 'running') {
    // Being upgraded (1.0.96): the daemon restarts on purpose - maintenance, not down.
    http_response_code(503);
    echo 'maintenance ' . preg_replace('/[^A-Za-z0-9._-]/', '', php_uname('n')) . ': being upgraded to '
        . ($u['version'] ?: '?') . "\n";
} elseif (!is_array($h) || empty($h['ok'])) {
    http_response_code(503);
    echo "down\n";
} elseif (!empty($h['maintenance'])) {
    // Taken out by hand or for an upgrade (1.0.46, as otp's): a monitor or a
    // balancer leaves it alone until it is back.
    http_response_code(503);
    echo 'maintenance ' . preg_replace('/[^A-Za-z0-9._-]/', '', (string) ($h['node'] ?? '')) . "\n";
} else {
    echo 'ok ' . preg_replace('/[^A-Za-z0-9._-]/', '', (string) ($h['node'] ?? '')) . "\n";
}
