<?php
/**
 * ai-art.php — the pictures of the sign-in (1.0.27), as otp's otp-art.php.
 *
 * Drawn in the page's own colours, so they follow the light and the dark look
 * and need nothing fetched. Which one the sign-in shows is picked under
 * Settings → The sign-in page and kept in the database. 'custom' is a picture
 * of the site's own, served by ?api=logo; 'none' is no picture at all.
 */
declare(strict_types=1);

const AI_ARTS = ['browser', 'terminal', 'chat', 'tmux', 'devices', 'spark', 'tablet', 'diff', 'folders',
                 'agents', 'usage', 'keys', 'none', 'custom'];

/** What the sign-in shows until something else is picked. */
const AI_ART_DEFAULT = 'browser';

/** The words under each picture in the choice. */
const AI_ART_WORDS = [
    'browser' => 'Claude Code in the browser, the server behind it (as ai came)',
    'terminal' => 'The terminal, Claude Code at the prompt',
    'chat'    => 'A task asked, Claude Code at work on it',
    'tmux'    => 'Terminals that go on when the browser closes',
    'devices' => 'One server, from the desk, the laptop and the tablet',
    'spark'   => 'The spark of Claude',
    'tablet'  => 'A chat on the tablet, scrolled by finger',
    'diff'    => 'A change to the code, line by line',
    'folders' => 'The folder of the chats and what is under it',
    'agents'  => 'A task shared out to agents',
    'usage'   => 'What the chats used, day by day',
    'keys'    => 'Signed in, the keys of the server safe',
    'none'    => 'No picture',
    'custom'  => 'A picture of your own',
];

function ai_art_svg(string $name): string
{
    $defs = '<defs><radialGradient id="sa-glow" cx="50%" cy="42%" r="62%">'
          . '<stop offset="0" stop-color="var(--info)" stop-opacity=".30"/>'
          . '<stop offset="1" stop-color="var(--info)" stop-opacity=".04"/></radialGradient></defs>'
          . '<rect class="plate" x=".75" y=".75" width="418.5" height="186.5" rx="14"/>';
    $open = function (string $n, string $title) use ($defs): string {
        return '<svg class="signart art-' . $n . '" viewBox="0 0 420 188" role="img" aria-labelledby="sa-title">'
            . '<title id="sa-title">' . $title . '</title>' . $defs;
    };
    $dots = '<circle class="spark dot" r="2.6" cx="0" cy="0"/><circle class="spark dot dot2" r="2.6" cx="0" cy="0"/>'
          . '<circle class="spark dot dot3" r="2.6" cx="0" cy="0"/>';
    $mono = 'font-family="ui-monospace,Menlo,Consolas,monospace"';
    $star = function (float $x, float $y, float $s, string $cls = 'star'): string {
        // The four-pointed spark, centred on x,y, s its half size.
        $p = sprintf('M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f '
                   . 'C%.1f %.1f %.1f %.1f %.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1fZ',
            $x, $y - $s, $x + $s * .14, $y - $s * .14, $x + $s * .14, $y - $s * .14, $x + $s, $y,
            $x + $s * .14, $y + $s * .14, $x + $s * .14, $y + $s * .14, $x, $y + $s,
            $x - $s * .14, $y + $s * .14, $x - $s * .14, $y + $s * .14, $x - $s, $y,
            $x - $s * .14, $y - $s * .14, $x - $s * .14, $y - $s * .14, $x, $y - $s);
        return '<path class="' . $cls . '" d="' . $p . '"/>';
    };
    switch ($name) {
    case 'browser':
        return $open('browser', 'Claude Code in the browser, the server behind it')
            . '<text class="lbl" x="28" y="30">CLAUDE CODE</text>'
            . '<rect x="28" y="40" width="212" height="112" rx="9" fill="var(--panel2)" stroke="var(--info)" stroke-width="2" opacity=".95"/>'
            . '<circle cx="42" cy="52" r="3" fill="var(--crit)" opacity=".7"/><circle cx="52" cy="52" r="3" fill="var(--warn)" opacity=".7"/><circle cx="62" cy="52" r="3" fill="var(--ok)" opacity=".7"/>'
            . '<path d="M44 74l10 8-10 8" fill="none" stroke="var(--ok)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
            . '<rect class="logline" x="62" y="79" width="96" height="6" rx="3"/>'
            . '<rect class="logline good" x="44" y="100" width="128" height="6" rx="3"/>'
            . '<rect class="logline" x="44" y="114" width="76" height="6" rx="3"/>'
            . '<rect class="cursor" x="44" y="128" width="10" height="9" rx="1.5"/>'
            . '<path class="flow" d="M250 96 H300"/>' . $dots
            . '<text class="lbl" x="392" y="30" text-anchor="end">THE SERVER</text>'
            . '<rect x="306" y="52" width="86" height="88" rx="10" fill="none" stroke="var(--tx-mut)" stroke-width="2"/>'
            . '<path d="M322 76h54M322 96h38M322 116h48" stroke="var(--tx-mut)" stroke-width="3" stroke-linecap="round" opacity=".7"/>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">IN THE BROWSER · NOTHING ENDS WHEN IT CLOSES</text></svg>';
    case 'terminal':
        return $open('terminal', 'The terminal, Claude Code at the prompt')
            . '<rect x="40" y="26" width="340" height="132" rx="10" fill="var(--panel2)" stroke="var(--line)" stroke-width="1.5"/>'
            . '<rect x="40" y="26" width="340" height="22" rx="10" fill="var(--line)" opacity=".5"/>'
            . '<circle cx="56" cy="37" r="3.5" fill="var(--crit)" opacity=".7"/><circle cx="68" cy="37" r="3.5" fill="var(--warn)" opacity=".7"/><circle cx="80" cy="37" r="3.5" fill="var(--ok)" opacity=".7"/>'
            . '<text x="58" y="72" font-size="12" fill="var(--ok)" ' . $mono . '>$</text>'
            . '<text x="72" y="72" font-size="12" fill="var(--tx)" ' . $mono . '>claude</text>'
            . $star(66, 96, 8, 'star')
            . '<text x="82" y="100" font-size="11.5" fill="var(--tx-mut)" ' . $mono . '>Welcome to Claude Code</text>'
            . '<rect x="58" y="114" width="304" height="26" rx="6" fill="none" stroke="var(--info)" stroke-width="1.4" opacity=".8"/>'
            . '<text x="68" y="131" font-size="11.5" fill="var(--info)" ' . $mono . '>&gt;</text>'
            . '<rect class="cursor" x="82" y="121" width="8" height="12" rx="1"/>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">CLAUDE CODE · ON THE SERVER · IN YOUR BROWSER</text></svg>';
    case 'chat':
        return $open('chat', 'A task asked, Claude Code at work on it')
            . '<rect x="190" y="24" width="190" height="34" rx="12" fill="var(--info)" opacity=".22"/>'
            . '<rect x="206" y="36" width="120" height="6" rx="3" fill="var(--tx)" opacity=".6"/><rect x="206" y="46" width="76" height="5" rx="2.5" fill="var(--tx)" opacity=".35"/>'
            . $star(58, 92, 13, 'star')
            . '<rect x="82" y="70" width="230" height="72" rx="12" fill="var(--panel2)" stroke="var(--line)"/>'
            . '<rect class="logline" x="96" y="84" width="150" height="6" rx="3"/>'
            . '<rect class="logline good" x="96" y="98" width="110" height="6" rx="3"/>'
            . '<rect class="logline" x="96" y="112" width="176" height="6" rx="3"/>'
            . '<circle class="typing t1" cx="100" cy="129" r="3"/><circle class="typing t2" cx="111" cy="129" r="3"/><circle class="typing t3" cx="122" cy="129" r="3"/>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">ASK · IT READS, WRITES AND RUNS · IT ASKS FIRST</text></svg>';
    case 'tmux':
        return $open('tmux', 'Terminals that go on when the browser closes')
            . '<rect x="36" y="26" width="348" height="124" rx="9" fill="var(--panel2)" stroke="var(--line)" stroke-width="1.5"/>'
            . '<path d="M210 26 V150 M210 88 H384" stroke="var(--line)" stroke-width="1.5"/>'
            . '<rect class="logline good" x="50" y="44" width="110" height="5" rx="2.5"/><rect class="logline" x="50" y="56" width="140" height="5" rx="2.5"/><rect class="logline" x="50" y="68" width="90" height="5" rx="2.5"/><rect class="logline" x="50" y="80" width="126" height="5" rx="2.5"/><rect class="logline warn" x="50" y="92" width="70" height="5" rx="2.5"/><rect class="logline" x="50" y="104" width="118" height="5" rx="2.5"/><rect class="cursor" x="50" y="118" width="8" height="10" rx="1"/>'
            . '<rect class="logline" x="224" y="44" width="120" height="5" rx="2.5"/><rect class="logline good" x="224" y="56" width="90" height="5" rx="2.5"/><rect class="logline" x="224" y="68" width="136" height="5" rx="2.5"/>'
            . '<rect class="col" x="226" y="128" width="12" height="14" rx="2" fill="var(--info)"/><rect class="col" x="244" y="118" width="12" height="24" rx="2" fill="var(--info)"/><rect class="col" x="262" y="108" width="12" height="34" rx="2" fill="var(--ok)"/><rect class="col" x="280" y="122" width="12" height="20" rx="2" fill="var(--info)"/>'
            . '<rect x="36" y="140" width="348" height="10" rx="0" fill="var(--ok)" opacity=".35"/>'
            . '<text x="44" y="148" font-size="8" fill="var(--tx)" ' . $mono . '>[ai] 0:claude  1:shell  2:logs</text>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">CLOSE THE BROWSER · IT GOES ON · OPEN IT ANYWHERE</text></svg>';
    case 'devices':
        return $open('devices', 'One server, from the desk, the laptop and the tablet')
            . '<rect x="178" y="30" width="64" height="86" rx="8" fill="var(--panel2)" stroke="var(--tx-mut)" stroke-width="2"/>'
            . '<path d="M190 48h40M190 64h40M190 80h40" stroke="var(--tx-mut)" stroke-width="3" stroke-linecap="round" opacity=".6"/>'
            . '<circle class="led" cx="196" cy="102" r="3"/><circle class="led l2" cx="208" cy="102" r="3"/><circle class="led l3" cx="220" cy="102" r="3"/>'
            . '<text class="lbl" x="210" y="22" text-anchor="middle">THE SERVER</text>'
            . '<path class="flow" d="M176 90 L96 122"/><path class="flow" d="M210 118 L210 132"/><path class="flow" d="M244 90 L326 122"/>' . $dots
            . '<rect x="44" y="122" width="74" height="44" rx="5" fill="none" stroke="var(--info)" stroke-width="2"/><path d="M70 166v6h22v-6" fill="none" stroke="var(--info)" stroke-width="2"/>'
            . '<rect x="180" y="134" width="60" height="34" rx="4" fill="none" stroke="var(--info)" stroke-width="2"/><path d="M172 170h76" stroke="var(--info)" stroke-width="2.5" stroke-linecap="round"/>'
            . '<rect x="304" y="120" width="56" height="48" rx="7" fill="none" stroke="var(--info)" stroke-width="2"/><circle cx="332" cy="162" r="1.8" fill="var(--info)"/>'
            . '</svg>';
    case 'spark':
        return $open('spark', 'The spark of Claude')
            . '<circle cx="210" cy="86" r="58" fill="url(#sa-glow)"/>'
            . '<circle class="orbit" cx="210" cy="86" r="62" fill="none" stroke="var(--line)" stroke-width="1.2" stroke-dasharray="4 7"/>'
            . $star(210, 86, 38, 'star big')
            . $star(152, 46, 7, 'star small s1') . $star(272, 128, 6, 'star small s2') . $star(276, 44, 5, 'star small s3')
            . '<text class="lbl" x="210" y="176" text-anchor="middle">CLAUDE CODE · ON YOUR SERVER</text></svg>';
    case 'tablet':
        return $open('tablet', 'A chat on the tablet, scrolled by finger')
            . '<rect x="120" y="18" width="180" height="140" rx="14" fill="var(--panel2)" stroke="var(--tx-mut)" stroke-width="2.4"/>'
            . '<rect x="132" y="30" width="156" height="116" rx="4" fill="none" stroke="var(--line)"/>'
            . '<g class="scrolling"><rect class="logline" x="140" y="40" width="110" height="5" rx="2.5"/><rect class="logline good" x="140" y="52" width="80" height="5" rx="2.5"/><rect class="logline" x="140" y="64" width="126" height="5" rx="2.5"/><rect class="logline" x="140" y="76" width="96" height="5" rx="2.5"/><rect class="logline warn" x="140" y="88" width="60" height="5" rx="2.5"/><rect class="logline" x="140" y="100" width="118" height="5" rx="2.5"/><rect class="logline good" x="140" y="112" width="90" height="5" rx="2.5"/><rect class="logline" x="140" y="124" width="104" height="5" rx="2.5"/></g>'
            . '<rect x="280" y="36" width="5" height="104" rx="2.5" fill="var(--line)"/><rect class="thumb" x="280" y="44" width="5" height="34" rx="2.5" fill="var(--info)"/>'
            . '<g class="finger"><circle cx="330" cy="92" r="11" fill="var(--info)" opacity=".18"/><circle cx="330" cy="92" r="5" fill="var(--info)" opacity=".55"/></g>'
            . '<path d="M330 66v52M324 72l6-6 6 6M324 112l6 6 6-6" fill="none" stroke="var(--tx-mut)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" opacity=".7"/>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">THE WHOLE HISTORY · BY FINGER</text></svg>';
    case 'diff':
        return $open('diff', 'A change to the code, line by line')
            . '<rect x="40" y="22" width="340" height="132" rx="9" fill="var(--panel2)" stroke="var(--line)"/>'
            . '<text x="54" y="40" font-size="10" fill="var(--tx-mut)" ' . $mono . '>Update(app.py)</text>'
            . '<rect x="48" y="50" width="324" height="16" fill="var(--crit)" opacity=".22"/><text x="56" y="62" font-size="10" fill="var(--crit)" ' . $mono . '>- timeout = 25</text>'
            . '<rect x="48" y="68" width="324" height="16" fill="var(--ok)" opacity=".22"/><text x="56" y="80" font-size="10" fill="var(--ok)" ' . $mono . '>+ timeout = 3</text>'
            . '<rect x="48" y="86" width="324" height="16" fill="var(--ok)" opacity=".22"/><text x="56" y="98" font-size="10" fill="var(--ok)" ' . $mono . '>+ retries = 2</text>'
            . '<rect class="logline" x="56" y="112" width="170" height="5" rx="2.5"/><rect class="logline" x="56" y="124" width="120" height="5" rx="2.5"/>'
            . '<rect x="270" y="126" width="96" height="20" rx="6" fill="var(--ok)" opacity=".85"/><text x="318" y="140" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--panel)">ACCEPT</text>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">EVERY CHANGE SHOWN · YOURS TO ALLOW</text></svg>';
    case 'folders':
        return $open('folders', 'The folder of the chats and what is under it')
            . '<path d="M60 40h34l8 8h52v22H60z" fill="var(--warn)" opacity=".75"/><text x="70" y="64" font-size="10" font-weight="700" fill="var(--panel)" ' . $mono . '>/srv/chats</text>'
            . '<path d="M78 72v74M78 92h26M78 120h26M78 146h26" fill="none" stroke="var(--line)" stroke-width="1.6"/>'
            . '<path d="M108 84h26l6 6h40v14h-72z" fill="var(--info)" opacity=".6"/><text x="114" y="100" font-size="9.5" fill="var(--tx)" ' . $mono . '>shop</text>'
            . '<path d="M108 112h26l6 6h40v14h-72z" fill="var(--info)" opacity=".6"/><text x="114" y="128" font-size="9.5" fill="var(--tx)" ' . $mono . '>sms</text>'
            . '<path d="M108 140h26l6 6h40v14h-72z" fill="var(--info)" opacity=".35"/><text x="114" y="156" font-size="9.5" fill="var(--tx)" ' . $mono . '>notes</text>'
            . '<path class="flow" d="M196 124 H252"/>' . $dots
            . $star(286, 124, 16, 'star')
            . '<rect x="250" y="40" width="130" height="36" rx="8" fill="var(--panel2)" stroke="var(--crit)" stroke-dasharray="4 4" opacity=".7"/>'
            . '<text x="315" y="62" text-anchor="middle" font-size="9.5" fill="var(--crit)" ' . $mono . '>/etc  /root  ✕</text>'
            . '<text class="lbl" x="210" y="180" text-anchor="middle">THE CHATS STAY IN THEIR FOLDER</text></svg>';
    case 'agents':
        return $open('agents', 'A task shared out to agents')
            . $star(80, 92, 20, 'star')
            . '<path class="flow" d="M108 92 C150 92 160 48 206 48"/><path class="flow" d="M108 92 H206"/><path class="flow" d="M108 92 C150 92 160 136 206 136"/>'
            . '<rect x="212" y="32" width="150" height="32" rx="8" fill="var(--panel2)" stroke="var(--info)"/><text x="226" y="52" font-size="10" fill="var(--tx)" ' . $mono . '>explore · the code</text>'
            . '<rect x="212" y="76" width="150" height="32" rx="8" fill="var(--panel2)" stroke="var(--info)"/><text x="226" y="96" font-size="10" fill="var(--tx)" ' . $mono . '>plan · the change</text>'
            . '<rect x="212" y="120" width="150" height="32" rx="8" fill="var(--panel2)" stroke="var(--ok)"/><text x="226" y="140" font-size="10" fill="var(--tx)" ' . $mono . '>test · it runs</text>'
            . '<circle class="led" cx="350" cy="48" r="3.5"/><circle class="led l2" cx="350" cy="92" r="3.5"/><circle class="led l3" cx="350" cy="136" r="3.5"/>'
            . '<text class="lbl" x="210" y="178" text-anchor="middle">ONE TASK · AGENTS SIDE BY SIDE</text></svg>';
    case 'usage':
        $b = '';
        foreach ([34, 52, 28, 66, 80, 44, 92, 58, 70, 38, 86, 62] as $i => $h) {
            $b .= sprintf('<rect class="col grow" x="%d" y="%d" width="18" height="%d" rx="3" fill="%s" style="animation-delay:%.2fs"/>',
                70 + $i * 24, 150 - $h, $h, $i === 6 ? 'var(--ok)' : 'var(--info)', $i * .08);
        }
        return $open('usage', 'What the chats used, day by day')
            . '<text class="lbl" x="70" y="30">TOKENS · DAY BY DAY</text>'
            . '<path d="M62 150H364" stroke="var(--line)" stroke-width="1.5"/>' . $b
            . '<text x="364" y="30" text-anchor="end" font-size="15" font-weight="700" fill="var(--ok)" ' . $mono . '>$ 12.40</text>'
            . '<text class="lbl" x="210" y="176" text-anchor="middle">EVERY CHAT COUNTED</text></svg>';
    case 'keys':
        $k = function (int $x, int $w, string $t) use ($mono): string {
            return '<rect x="' . $x . '" y="112" width="' . $w . '" height="34" rx="6" fill="var(--panel2)" stroke="var(--line)" stroke-width="1.5"/>'
                . '<text x="' . ($x + $w / 2) . '" y="134" text-anchor="middle" font-size="11" fill="var(--tx)" ' . $mono . '>' . $t . '</text>';
        };
        return $open('keys', 'Signed in, the keys of the server safe')
            . '<path class="halo" d="M210 18 l46 16 v32c0 27-19 44-46 53c-27-9-46-26-46-53V34z" fill="var(--info)" opacity=".35"/>'
            . '<path class="shield" d="M210 22 l42 15 v30c0 25-17 41-42 49c-25-8-42-24-42-49V37z"/>'
            . '<rect x="196" y="60" width="28" height="22" rx="4" fill="none" stroke="var(--ok)" stroke-width="3"/>'
            . '<path d="M202 60v-7a8 8 0 0 1 16 0v7" fill="none" stroke="var(--ok)" stroke-width="3"/>'
            . $k(60, 54, 'Ctrl') . $k(122, 48, 'Alt') . $k(178, 64, 'Esc') . $k(250, 48, 'Tab') . $k(306, 54, 'F12')
            . '<text class="lbl" x="210" y="172" text-anchor="middle">TLS · A SECOND STEP · EVERY KEY TO THE TERMINAL</text></svg>';
    }
    return '';
}

/** The picture the sign-in shows: one of the drawings, the site's own, or nothing. */
function ai_signin_art(array $art): string
{
    $name = (string) ($art['art'] ?? AI_ART_DEFAULT);
    if ($name === 'none') {
        return '';
    }
    if ($name === 'custom') {
        return '<img class="signlogo" src="/?api=logo&amp;v=' . htmlspecialchars((string) ($art['sha'] ?? ''), ENT_QUOTES)
            . '" alt="">';
    }
    return ai_art_svg(in_array($name, AI_ARTS, true) ? $name : AI_ART_DEFAULT);
}

/** The picture of the site's own, as the sign-in's <img> asks for it - to anybody (it is on the sign-in). */
function ai_serve_logo(): void
{
    [$status, $body] = ai_call('/api/logo', 'GET', null, 10.0);
    $data = $status === 200 ? json_decode((string) $body, true) : null;
    $logo = is_array($data) ? ($data['logo'] ?? null) : null;
    $kinds = ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml'];
    if (!is_array($logo) || !in_array($logo['type'] ?? '', $kinds, true)) {
        http_response_code(404);
        header('Cache-Control: no-store');
        exit;
    }
    $raw = base64_decode((string) ($logo['b64'] ?? ''), true);
    if ($raw === false) {
        http_response_code(404);
        exit;
    }
    $etag = '"' . preg_replace('/[^0-9a-f]/', '', (string) ($logo['sha'] ?? '')) . '"';
    header_remove('Pragma');
    header_remove('Expires');
    header('Content-Type: ' . $logo['type']);
    header('X-Content-Type-Options: nosniff');
    header("Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox");
    header('Content-Disposition: inline; filename="logo"');
    header('ETag: ' . $etag);
    header('Cache-Control: public, max-age=' . (isset($_GET['v']) ? '86400' : '60'));
    if (trim((string) ($_SERVER['HTTP_IF_NONE_MATCH'] ?? '')) === $etag) {
        http_response_code(304);
        exit;
    }
    header('Content-Length: ' . strlen($raw));
    echo $raw;
    exit;
}
