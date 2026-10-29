#!/usr/bin/env bash
#
# install.sh — set up ai on AlmaLinux / Rocky / RHEL 9 and 10, and on Debian
# 12 and Ubuntu 24.04.
#
# The same shape as otp's installer: the packages (tmux, nginx, PHP-FPM fixed
# against php2shell), the program, its configuration, the systemd unit, log
# rotation, nginx with TLS and a php-fpm pool of its own, SELinux, the
# firewall, the first account - and, if asked, Claude Code itself for root.
# Run it from inside the unpacked folder, as root:
#
#     sudo ./install.sh
#
# Everything it asks can be given on the command line; --help lists it.
# --dry-run prints what would happen and changes nothing. --upgrade replaces
# the program and the pages and restarts the service - the terminals (tmux)
# go on running through it - keeping the database, the configuration and the
# accounts. --uninstall removes the service and the pages and keeps the rest.
#
set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_VERSION="$(sed -n "s/^__version__ = '\(.*\)'.*/\1/p" "$SOURCE_DIR/ai.py" 2>/dev/null | head -n1)"
AI_VERSION="${AI_VERSION:-unknown}"
WEB_GROUP="ai-web"
POOL_USER="ai-www"
LIB_DIR="/usr/local/lib/ai"
BIN_LINK="/usr/local/bin/ai"
CONFIG_DIR="/etc/ai"
CONFIG_FILE="$CONFIG_DIR/config.json"
STATE_DIR="/var/lib/ai"
LOG_DIR="/var/log/ai"
WEB_DIR="/var/www/ai"
CERT_DIR="/etc/nginx/certs"
NGINX_CONF="/etc/nginx/conf.d/ai.conf"
UNIT_FILE="/etc/systemd/system/ai.service"
LOGROTATE_FILE="/etc/logrotate.d/ai"

DRY_RUN=""
ASSUME_YES=""
DO_UPGRADE=""
DO_UNINSTALL=""
REWRITE_NGINX=""
PHP_UPDATE="yes"
PHP_STREAM="8.3"
WITH_CLAUDE=""
SERVER_NAME=""
ALLOW=""
ADMIN_USER="admin"
ADMIN_PASSWORD=""
CERT_FILE=""
KEY_FILE=""
API_PORT=""

if [[ -t 1 ]]; then
    C_HEAD=$'\033[1;36m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'
    C_BAD=$'\033[1;31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
    C_HEAD=""; C_OK=""; C_WARN=""; C_BAD=""; C_DIM=""; C_OFF=""
fi
step()  { printf '\n%s==> %s%s\n' "$C_HEAD" "$1" "$C_OFF"; }
say()   { printf '    %s\n' "$1"; }
note()  { printf '    %s%s%s\n' "$C_DIM" "$1" "$C_OFF"; }
good()  { printf '    %s%s%s\n' "$C_OK" "$1" "$C_OFF"; }
warn()  { printf '    %s%s%s\n' "$C_WARN" "$1" "$C_OFF"; }
fail()  { printf '\n%sERROR: %s%s\n' "$C_BAD" "$1" "$C_OFF" >&2; exit 1; }

run() {
    if [[ -n "$DRY_RUN" ]]; then
        note "[would run] $*"
        return 0
    fi
    "$@"
}

write_file() {      # write_file DEST MODE < content
    local dest="$1" mode="${2:-0644}" body dir tmp
    body="$(cat)"
    if [[ -n "$DRY_RUN" ]]; then
        note "[would write] $dest (${#body} bytes, mode $mode)"
        return 0
    fi
    dir="$(dirname -- "$dest")"
    [[ -d "$dir" ]] || install -d -m 0755 "$dir"
    tmp="$(mktemp "$dir/.ai-write.XXXXXX")"
    printf '%s\n' "$body" > "$tmp"
    chmod "$mode" "$tmp"
    mv -fT -- "$tmp" "$dest"
}

# Asked as otp's installer asks: Enter keeps what is in brackets. With --yes,
# or with no terminal to ask on, what is in brackets is taken.
confirm() {      # confirm "question" [default y|n]
    local default="${2:-y}" answer
    if [[ -n "$ASSUME_YES" || ! -t 0 ]]; then [[ "$default" == "y" ]]; return; fi
    read -r -p "    $1 [$( [[ $default == y ]] && echo Y/n || echo y/N )] " answer || true
    answer="${answer:-$default}"
    [[ "$answer" =~ ^[YyAa] ]]
}

ask() {          # ask VAR "prompt" "default"
    local var="$1" prompt="$2" default="${3:-}" answer
    if [[ -n "${!var:-}" ]]; then default="${!var}"; fi
    if [[ -n "$ASSUME_YES" || ! -t 0 ]]; then
        printf -v "$var" '%s' "$default"
        return
    fi
    if [[ -n "$default" ]]; then
        read -r -p "    $prompt [$default]: " answer || true
    else
        read -r -p "    $prompt: " answer || true
    fi
    printf -v "$var" '%s' "${answer:-$default}"
}

ask_secret() {   # ask_secret VAR "prompt" - typed unseen, twice; empty = none
    local var="$1" prompt="$2" answer again
    [[ -n "$ASSUME_YES" || ! -t 0 ]] && return
    while true; do
        read -r -s -p "    $prompt: " answer || true; echo
        [[ -z "$answer" ]] && { printf -v "$var" '%s' ''; return; }
        if (( ${#answer} < 10 )); then
            warn "that is shorter than ten characters"
            continue
        fi
        read -r -s -p "    and again: " again || true; echo
        [[ "$answer" == "$again" ]] && { printf -v "$var" '%s' "$answer"; return; }
        warn "those two are not the same"
    done
}

usage() {
    cat <<EOF
ai $AI_VERSION - Claude Code on this server, in a web browser.

  sudo ./install.sh [options]

--server-name HOST     the pages' host name (default: this machine's)
--allow CIDR[,..]      who may reach the pages (default: the private networks,
                       RFC 1918; "all" for everybody)
--admin-user NAME      the first account (admin)
--admin-password PASS  its password (otherwise one is made and printed)
--cert FILE --key FILE the TLS certificate and key (otherwise a self-signed one)
--claude               install Claude Code for root as well (Anthropic's installer)
--no-claude            do not offer it
--port N               the port of the daemon's API on 127.0.0.1 (default 9871)
--php-stream X.Y       the AppStream PHP stream for a machine with no PHP yet (8.3)
--no-php-update        leave PHP as it is (it is still checked)
--upgrade              replace the program and the pages, restart; keep the rest
--rewrite-nginx        write the nginx file afresh (otherwise one there is kept)
--uninstall            remove the service and the pages; keep the data (asks)
--dry-run              print what would happen
--yes                  never ask
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --server-name) SERVER_NAME="${2:?}"; shift 2 ;;
        --allow) ALLOW="${2:?}"; shift 2 ;;
        --admin-user) ADMIN_USER="${2:?}"; shift 2 ;;
        --admin-password) ADMIN_PASSWORD="${2:?}"; shift 2 ;;
        --cert) CERT_FILE="${2:?}"; shift 2 ;;
        --key) KEY_FILE="${2:?}"; shift 2 ;;
        --claude) WITH_CLAUDE="yes"; shift ;;
        --no-claude) WITH_CLAUDE="no"; shift ;;
        --port) API_PORT="${2:?}"; shift 2 ;;
        --php-stream) PHP_STREAM="${2:?}"; shift 2 ;;
        --no-php-update) PHP_UPDATE=""; shift ;;
        --upgrade) DO_UPGRADE="yes"; shift ;;
        --rewrite-nginx) REWRITE_NGINX="yes"; shift ;;
        --uninstall) DO_UNINSTALL="yes"; shift ;;
        --dry-run) DRY_RUN="yes"; shift ;;
        --yes|-y) ASSUME_YES="yes"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage; fail "what is $1?" ;;
    esac
done

[[ $EUID -eq 0 || -n "$DRY_RUN" ]] || fail "run it as root: sudo ./install.sh"
[[ -f "$SOURCE_DIR/ai.py" ]] || fail "run it from inside the unpacked folder (ai.py is not beside it)"

# ---------------------------------------------------------------------------
# Which system
# ---------------------------------------------------------------------------
PKG=""
OS_ID=""; OS_MAJOR=""
if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-}"; OS_MAJOR="${VERSION_ID%%.*}"
fi
if command -v dnf >/dev/null 2>&1; then PKG=dnf
elif command -v apt-get >/dev/null 2>&1; then PKG=apt
fi
NGINX_USER=nginx
id nginx >/dev/null 2>&1 || NGINX_USER=www-data
[[ "$PKG" == "apt" ]] && NGINX_USER=www-data

php_fpm_units() {
    local found="" unit listed
    systemctl cat php-fpm.service >/dev/null 2>&1 && found="php-fpm"
    listed="$(systemctl list-unit-files --no-legend 'php*-fpm.service' 2>/dev/null || true)"
    while read -r unit _rest; do
        unit="${unit%.service}"
        [[ -n "$unit" && "$unit" != "php-fpm" && "$unit" =~ ^php[0-9.]*-fpm$ ]] && found="$found $unit"
    done <<< "$listed"
    echo "$found"
}

# ---------------------------------------------------------------------------
# Removing it
# ---------------------------------------------------------------------------
if [[ -n "$DO_UNINSTALL" ]]; then
    step "Removing ai $AI_VERSION"
    say "The database, the configuration and the accounts are kept: $STATE_DIR and $CONFIG_DIR"
    say "The terminals running now (tmux) go on running until they end or the server restarts."
    if [[ -n "$ASSUME_YES" && ! -t 0 ]]; then
        fail "removing is never a default: run --uninstall on a terminal, it asks"
    fi
    ASSUME_YES="" confirm "Go ahead?" n || { say "Nothing was changed."; exit 0; }
    run systemctl disable --now ai.service 2>/dev/null || true
    for one in "$UNIT_FILE" "$LOGROTATE_FILE" "$NGINX_CONF" "$BIN_LINK" /etc/php-fpm.d/ai.conf /etc/php/*/fpm/pool.d/ai.conf; do
        [[ -e "$one" ]] && run rm -f "$one"
    done
    [[ -d "$LIB_DIR" ]] && run rm -rf "$LIB_DIR"
    [[ -d "$WEB_DIR" ]] && run rm -rf "$WEB_DIR"
    run systemctl daemon-reload
    for unit in $(php_fpm_units); do run systemctl try-restart "$unit" || true; done
    command -v nginx >/dev/null && run systemctl reload nginx 2>/dev/null || true
    good "Gone. $STATE_DIR and $CONFIG_DIR were left alone."
    say "To remove the rest:  rm -rf $STATE_DIR $CONFIG_DIR $LOG_DIR; userdel $POOL_USER; groupdel $WEB_GROUP"
    say "  its certificate:    rm -f $CERT_DIR/ai.pem $CERT_DIR/ai.key"
    exit 0
fi

if [[ -n "$DO_UPGRADE" ]]; then
    step "Upgrading ai to $AI_VERSION"
    HAD="$(sed -n "s/^__version__ = '\(.*\)'.*/\1/p" "$LIB_DIR/ai.py" 2>/dev/null | head -n1 || true)"
    [[ -n "$HAD" ]] && say "installed now: $HAD" || warn "ai is not installed here yet - installing it whole"
    [[ -z "$HAD" ]] && DO_UPGRADE=""
else
    step "Installing ai $AI_VERSION"
fi
say "system: ${PRETTY_NAME:-unknown} (package manager: ${PKG:-none})"

# ---------------------------------------------------------------------------
# PHP, fixed against php2shell (as otp's installer)
# ---------------------------------------------------------------------------
php_fpm_bin() {
    local b
    b="$(command -v php-fpm 2>/dev/null || true)"
    [[ -z "$b" && -x /usr/sbin/php-fpm ]] && b=/usr/sbin/php-fpm
    if [[ -z "$b" ]]; then
        b="$(ls -1 /usr/sbin/php-fpm[0-9]* 2>/dev/null | sort -V | tail -n 1 || true)"
    fi
    echo "$b"
}
php_fpm_version() {
    local b v
    b="$(php_fpm_bin)"
    [[ -n "$b" ]] || { echo ""; return; }
    v="$("$b" -v 2>/dev/null | head -n 1 | awk '{print $2}')"
    echo "${v%%[-+~]*}"
}
ver_ge() { [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n 1)" == "$2" ]]; }
php_fixed() {
    local v b f log
    v="$(php_fpm_version)"
    [[ -n "$v" ]] || return 1
    b="$(echo "$v" | cut -d. -f1,2)"
    case "$b" in
        8.2) f=8.2.35 ;; 8.3) f=8.3.36 ;; 8.4) f=8.4.27 ;; 8.5) f=8.5.12 ;;
        *) if ver_ge "$b" 8.6; then return 0; fi; f="" ;;
    esac
    [[ -n "$f" ]] && ver_ge "$v" "$f" && return 0
    if [[ "$PKG" == "dnf" ]]; then
        log="$(rpm -q --changelog php-fpm php-common 2>/dev/null || true)"
        grep -q 'CVE-2026-109618' <<< "$log" && return 0
    elif [[ "$PKG" == "apt" ]]; then
        for log in /usr/share/doc/php*-fpm/changelog.Debian.gz /usr/share/doc/php*-common/changelog.Debian.gz; do
            [[ -f "$log" ]] || continue
            grep -q 'CVE-2026-109618' <<< "$(zcat "$log" 2>/dev/null || true)" && return 0
        done
    fi
    return 1
}
php_says() {
    local v
    v="$(php_fpm_version)"; v="${v:-?}"
    if php_fixed; then good "PHP $v has the php2shell fix (CVE-2026-109618, CVE-2026-109619)"
    else warn "PHP $v does NOT have the php2shell fix - ai's page is guarded meanwhile (no multipart, no body parsing)"; fi
}
php_guard() {
    local dir
    for dir in /etc/php.d /etc/php/*/fpm/conf.d /etc/php/*/cli/conf.d; do
        [[ -d "$dir" ]] || continue
        if [[ -f "$dir/99-php2shell.ini" ]] && grep -q 'upload_progress.enabled *= *0' "$dir/99-php2shell.ini"; then
            continue
        fi
        run install -m 0644 "$SOURCE_DIR/deploy/99-php2shell.ini" "$dir/99-php2shell.ini"
        good "$dir/99-php2shell.ini - session upload progress off"
    done
}

# ---------------------------------------------------------------------------
# The packages
# ---------------------------------------------------------------------------
install_packages() {
    step "Packages"
    local want=(python3 tmux nginx openssl curl tar git chrony)
    if [[ "$PKG" == "dnf" ]]; then
        want+=(openssh-clients ncurses-term procps-ng iproute util-linux policycoreutils-python-utils)
        local missing=()
        for p in "${want[@]}"; do rpm -q "$p" >/dev/null 2>&1 || missing+=("$p"); done
        if ((${#missing[@]})); then
            say "installing: ${missing[*]}"
            run dnf install -y "${missing[@]}" || {
                # One that the repositories do not have stops none of the rest.
                for p in "${missing[@]}"; do run dnf install -y "$p" >/dev/null 2>&1 || warn "$p could not be installed"; done
            }
        else
            note "everything is there already"
        fi
        if ! command -v php-fpm >/dev/null 2>&1 && ! ls /usr/sbin/php-fpm* >/dev/null 2>&1; then
            local streams now
            streams="$(dnf -q module list php 2>/dev/null || true)"
            now="$(dnf -q module list --enabled php 2>/dev/null || true)"
            now="$(awk '/^php /{print $2; exit}' <<< "$now")"
            if [[ -z "$now" ]] && grep -qE "^php +${PHP_STREAM//./\\.}( |$)" <<< "$streams"; then
                say "PHP comes from the stream php:$PHP_STREAM"
                run dnf module enable -y "php:$PHP_STREAM"
            fi
            run dnf install -y php-fpm php-cli php-common
        elif [[ -n "$PHP_UPDATE" ]] && ! php_fixed; then
            say "PHP is installed but not fixed: updating the packages that are there"
            run dnf upgrade -y --refresh 'php*' || true
        fi
    elif [[ "$PKG" == "apt" ]]; then
        want+=(ssh ncurses-term procps iproute2 php-fpm php-cli)
        local missing=()
        for p in "${want[@]}"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
        if ((${#missing[@]})); then
            say "installing: ${missing[*]}"
            run apt-get update -q
            DEBIAN_FRONTEND=noninteractive run apt-get install -y "${missing[@]}" || warn "some packages could not be installed"
        else
            note "everything is there already"
        fi
        if [[ -n "$PHP_UPDATE" ]] && ! php_fixed; then
            local have
            have="$(dpkg-query -W -f='${Package} ${Status}\n' 'php*' 2>/dev/null | awk '/ installed$/{print $1}' | tr '\n' ' ' || true)"
            [[ -n "$have" ]] && { run apt-get install -y --only-upgrade $have || true; }
        fi
    else
        warn "this distribution is not one this knows: install python3, tmux, nginx and php-fpm yourself"
    fi
    command -v tmux >/dev/null 2>&1 || [[ -n "$DRY_RUN" ]] || fail "tmux is not installed and could not be - the terminals need it"
    command -v python3 >/dev/null 2>&1 || [[ -n "$DRY_RUN" ]] || fail "python3 is not installed"
    php_says
    php_guard
    if command -v chronyd >/dev/null 2>&1; then
        systemctl is-active --quiet systemd-timesyncd 2>/dev/null && run systemctl disable --now systemd-timesyncd || true
        for u in chronyd chrony; do
            if systemctl cat "$u.service" >/dev/null 2>&1; then
                run systemctl enable --now "$u" >/dev/null 2>&1 || true
                break
            fi
        done
    fi
    return 0
}

# ---------------------------------------------------------------------------
# The program
# ---------------------------------------------------------------------------
install_program() {
    step "The program"
    getent group "$WEB_GROUP" >/dev/null || run groupadd --system "$WEB_GROUP"
    if ! id "$POOL_USER" >/dev/null 2>&1; then
        run useradd --system --no-create-home --home-dir /nonexistent --shell /sbin/nologin -g "$WEB_GROUP" "$POOL_USER"
    fi
    run install -d -m 0755 "$LIB_DIR" "$LIB_DIR/release-keys" "$LIB_DIR/docs"
    run install -m 0755 "$SOURCE_DIR/ai.py" "$LIB_DIR/ai.py"
    run install -m 0755 "$SOURCE_DIR/deploy/ai_upgrade.py" "$LIB_DIR/ai_upgrade.py"
    run install -m 0755 "$SOURCE_DIR/deploy/ai_os.py" "$LIB_DIR/ai_os.py"
    run install -m 0644 "$SOURCE_DIR/deploy/tmux.conf" "$LIB_DIR/tmux.conf"
    run install -m 0644 "$SOURCE_DIR"/deploy/release-keys/*.pub "$LIB_DIR/release-keys/"
    run install -m 0644 "$SOURCE_DIR"/README.md "$SOURCE_DIR"/INSTALL.md "$SOURCE_DIR"/CHANGELOG.md "$LIB_DIR/"
    [[ -d "$SOURCE_DIR/docs" ]] && run install -m 0644 "$SOURCE_DIR"/docs/*.md "$LIB_DIR/docs/"
    run ln -sfn "$LIB_DIR/ai.py" "$BIN_LINK"
    run install -d -m 0755 "$CONFIG_DIR"
    if [[ ! -f "$CONFIG_FILE" ]]; then
        local port="${API_PORT:-9871}"
        sed "s/\"api_port\": 9871/\"api_port\": $port/" "$SOURCE_DIR/deploy/config.json" | write_file "$CONFIG_FILE" 0640
    elif [[ -n "$API_PORT" ]]; then
        run python3 - "$CONFIG_FILE" "$API_PORT" <<'PY'
import json, sys
p, port = sys.argv[1], int(sys.argv[2])
c = json.load(open(p))
c['api_port'] = port
open(p, 'w').write(json.dumps(c, indent=2) + '\n')
PY
    fi
    run install -d -m 0711 "$STATE_DIR"
    run install -d -m 0750 "$LOG_DIR"
    write_file "$UNIT_FILE" 0644 < "$SOURCE_DIR/deploy/ai.service"
    write_file "$LOGROTATE_FILE" 0644 < "$SOURCE_DIR/deploy/ai.logrotate"
    run systemctl daemon-reload
    good "$LIB_DIR, $BIN_LINK, $UNIT_FILE"
}

# ---------------------------------------------------------------------------
# The pages: the pool, nginx, the certificate
# ---------------------------------------------------------------------------
allow_lines() {         # allow_lines "a,b" -> nginx allow lines, or the defaults
    local list="$1" out="" one
    if [[ -z "$list" ]]; then
        printf '        allow 192.168.0.0/16;\n        allow 172.16.0.0/12;\n        allow 10.0.0.0/8;'
        return
    fi
    if [[ "$list" == "all" ]]; then
        printf '        allow all;'
        return
    fi
    IFS=',' read -r -a cidrs <<< "$list"
    for one in "${cidrs[@]}"; do
        one="$(echo "$one" | xargs)"
        [[ "$one" =~ ^[0-9A-Fa-f:.]+(/[0-9]{1,3})?$ ]] || fail "--allow: $one is not an address or a network"
        [[ -n "$one" ]] && out+="        allow $one;"$'\n'
    done
    printf '%s' "${out%$'\n'}"
}

php_pool_dir() {
    if [[ -d /etc/php-fpm.d ]]; then echo /etc/php-fpm.d; return; fi
    local b v d
    b="$(php_fpm_bin)"
    v="${b##*/php-fpm}"
    if [[ -n "$v" && -d "/etc/php/$v/fpm/pool.d" ]]; then echo "/etc/php/$v/fpm/pool.d"; return; fi
    for d in $(ls -1d /etc/php/*/fpm/pool.d 2>/dev/null | sort -V -r || true); do
        v="$(echo "$d" | cut -d/ -f4)"
        [[ -x "/usr/sbin/php-fpm$v" ]] && { echo "$d"; return; }
    done
    echo ""
}

install_pages() {
    step "The pages"
    run install -d -m 0755 "$WEB_DIR" "$WEB_DIR/assets" "$WEB_DIR/assets/xterm" "$WEB_DIR/lang"
    run install -m 0644 "$SOURCE_DIR"/web/index.php "$SOURCE_DIR"/web/ai-api.php "$SOURCE_DIR"/web/ai-page.php \
        "$SOURCE_DIR"/web/healthz.php "$SOURCE_DIR"/web/.user.ini "$WEB_DIR/"
    run install -m 0644 "$SOURCE_DIR"/web/assets/*.* "$WEB_DIR/assets/"
    run install -m 0644 "$SOURCE_DIR"/web/assets/xterm/* "$WEB_DIR/assets/xterm/"
    run install -m 0644 "$SOURCE_DIR"/web/lang/*.json "$WEB_DIR/lang/"
    run chown -R root:root "$WEB_DIR"
    good "$WEB_DIR"

    local pool_dir sock
    pool_dir="$(php_pool_dir)"
    [[ -n "$pool_dir" || -n "$DRY_RUN" ]] || fail "php-fpm's pool folder was not found - is php-fpm installed?"
    if [[ -d /run/php-fpm || "$PKG" == "dnf" ]]; then sock=/run/php-fpm/ai.sock; else sock=/run/php/ai.sock; fi
    sed -e "s#^listen = .*#listen = $sock#" -e "s#^listen.owner = .*#listen.owner = $NGINX_USER#" \
        -e "s#^listen.group = .*#listen.group = $NGINX_USER#" "$SOURCE_DIR/deploy/php-fpm-ai.conf" \
        | write_file "${pool_dir:-/etc/php-fpm.d}/ai.conf" 0644
    good "the php-fpm pool: ${pool_dir:-/etc/php-fpm.d}/ai.conf ($sock)"

    # The certificate: given, or one there already, or a new self-signed one.
    run install -d -m 0755 "$CERT_DIR"
    if [[ -n "$CERT_FILE" && -n "$KEY_FILE" ]]; then
        run install -m 0644 "$CERT_FILE" "$CERT_DIR/ai.pem"
        run install -m 0600 "$KEY_FILE" "$CERT_DIR/ai.key"
        good "the certificate given: $CERT_DIR/ai.pem"
    elif [[ ! -f "$CERT_DIR/ai.pem" || ! -f "$CERT_DIR/ai.key" ]]; then
        local alt="DNS:$SERVER_NAME" ip
        [[ "$SERVER_NAME" != "$(hostname -f 2>/dev/null || hostname)" ]] && alt+=",DNS:$(hostname -f 2>/dev/null || hostname)"
        for ip in $(hostname -I 2>/dev/null || true); do alt+=",IP:$ip"; done
        run openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 825 \
            -keyout "$CERT_DIR/ai.key" -out "$CERT_DIR/ai.pem" -subj "/CN=$SERVER_NAME" \
            -addext "subjectAltName=$alt" >/dev/null 2>&1
        run chmod 0600 "$CERT_DIR/ai.key"
        good "a self-signed certificate for $alt (Settings - Certificate and TLS puts your own in)"
    else
        note "the certificate there is kept: $CERT_DIR/ai.pem"
    fi

    if [[ ! -f "$NGINX_CONF" || -n "$REWRITE_NGINX" ]]; then
        local lines body
        lines="$(allow_lines "$ALLOW")"
        body="$(sed -e "s/server_name ai.example.local;/server_name $SERVER_NAME;/" \
                     -e "s#unix:/run/php-fpm/ai.sock#unix:$sock#" \
                     -e "s/127.0.0.1:9871/127.0.0.1:${API_PORT:-9871}/" "$SOURCE_DIR/deploy/nginx-ai.conf")"
        body="$(printf '%s' "$body" | python3 -c 'import re, sys
lines = sys.argv[1]
text = sys.stdin.read()
print(re.sub(r"(# AI-ALLOW-BEGIN\n).*?(\n[ \t]*# AI-ALLOW-END)", lambda m: m.group(1) + lines + m.group(2), text, flags=re.S), end="")' "$lines")"
        # A machine with IPv6 switched off in its kernel: nginx refuses [::].
        [[ -e /proc/net/if_inet6 ]] || body="$(grep -v 'listen *\[::\]' <<< "$body")"
        printf '%s\n' "$body" | write_file "$NGINX_CONF" 0644
        good "nginx: $NGINX_CONF ($SERVER_NAME)"
    else
        note "nginx: $NGINX_CONF is kept (--rewrite-nginx writes it afresh)"
        if [[ -n "$API_PORT" ]]; then
            run sed -i "s/127.0.0.1:[0-9]\{4,5\};/127.0.0.1:$API_PORT;/" "$NGINX_CONF"
        fi
    fi
    # Debian's own site answers every name on 80 - left as it is; ours has a name.
    if command -v getenforce >/dev/null 2>&1 && [[ "$(getenforce 2>/dev/null)" != "Disabled" ]]; then
        run setsebool -P httpd_can_network_connect 1 2>/dev/null || warn "could not set httpd_can_network_connect (nginx to the daemon)"
        command -v restorecon >/dev/null && run restorecon -R "$WEB_DIR" "$CERT_DIR" 2>/dev/null || true
        good "SELinux: nginx may reach the daemon on 127.0.0.1"
    fi
}

open_firewall() {
    step "The firewall"
    if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
        run firewall-cmd --permanent --add-service=http >/dev/null
        run firewall-cmd --permanent --add-service=https >/dev/null
        run firewall-cmd --reload >/dev/null
        good "firewalld: http and https open"
    elif command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q 'Status: active'; then
        run ufw allow 80/tcp >/dev/null
        run ufw allow 443/tcp >/dev/null
        good "ufw: 80 and 443 open"
    else
        note "no firewall running here to open (Settings - Firewall and access can manage one)"
    fi
}

start_all() {
    step "Starting"
    run systemctl enable ai.service >/dev/null 2>&1 || true
    run systemctl restart ai.service
    local unit
    for unit in $(php_fpm_units); do
        run systemctl enable "$unit" >/dev/null 2>&1 || true
        run systemctl restart "$unit" || warn "$unit would not restart"
    done
    if [[ -z "$DRY_RUN" ]]; then
        if nginx -t >/dev/null 2>&1; then
            systemctl enable nginx >/dev/null 2>&1 || true
            systemctl is-active --quiet nginx && systemctl reload nginx || systemctl restart nginx
            good "nginx answers"
        else
            nginx -t || true
            warn "nginx does not take its configuration - see above"
        fi
        local i
        for i in $(seq 1 20); do
            [[ -s /run/ai/api-token ]] && break
            sleep 0.5
        done
        systemctl is-active --quiet ai.service && good "ai.service runs" || warn "ai.service does not run: journalctl -u ai -n 50"
    fi
}

first_account() {
    [[ -n "$DO_UPGRADE" ]] && return 0
    step "The first account"
    if [[ -n "$DRY_RUN" ]]; then note "[would make] $ADMIN_USER (administrator)"; return 0; fi
    if [[ -n "$("$BIN_LINK" --users 2>/dev/null)" ]] && ! grep -q '^name: admin' "$STATE_DIR/first-login.txt" 2>/dev/null; then
        note "there are accounts already: $("$BIN_LINK" --users | awk '{print $1}' | tr '\n' ' ')"
        return 0
    fi
    # The daemon made 'admin' itself on its first start, when there was none.
    if grep -q '^name: admin' "$STATE_DIR/first-login.txt" 2>/dev/null && [[ "$ADMIN_USER" == "admin" && -z "$ADMIN_PASSWORD" ]]; then
        FIRST_PW="$(sed -n 's/^password: //p' "$STATE_DIR/first-login.txt")"
        return 0
    fi
    local pw="$ADMIN_PASSWORD"
    [[ -n "$pw" ]] || pw="$(tr -dc 'A-HJ-NP-Za-km-z2-9' < /dev/urandom | head -c 16)"
    "$BIN_LINK" --add-user "$ADMIN_USER" --role admin --password "$pw" >/dev/null 2>&1 \
        || "$BIN_LINK" --passwd "$ADMIN_USER" --password "$pw" >/dev/null \
        || fail "the password of $ADMIN_USER was not taken (ai --passwd $ADMIN_USER sets it)"
    if [[ "$ADMIN_USER" != "admin" ]] && grep -q '^name: admin' "$STATE_DIR/first-login.txt" 2>/dev/null; then
        "$BIN_LINK" --drop-user admin >/dev/null 2>&1 || true
        rm -f "$STATE_DIR/first-login.txt"
    fi
    FIRST_PW="$pw"
}

install_claude() {
    [[ "$WITH_CLAUDE" == "no" ]] && return 0
    if command -v claude >/dev/null 2>&1 || [[ -x /root/.local/bin/claude ]]; then
        note "Claude Code is installed for root already: $( (command -v claude || echo /root/.local/bin/claude) | head -n1)"
        return 0
    fi
    [[ -n "$DO_UPGRADE" && -z "$WITH_CLAUDE" ]] && return 0
    if [[ "$WITH_CLAUDE" != "yes" ]]; then
        confirm "Install Claude Code for root now (Anthropic's installer, claude.ai/install.sh)?" n || {
            note "later: Settings - Claude Code - Install it, or: curl -fsSL https://claude.ai/install.sh | bash"
            return 0
        }
    fi
    step "Claude Code, for root"
    if [[ -n "$DRY_RUN" ]]; then note "[would run] curl -fsSL https://claude.ai/install.sh | bash"; return 0; fi
    if curl -fsSL https://claude.ai/install.sh | bash; then
        good "Claude Code is installed for root"
    else
        warn "the installer did not finish - try again from Settings - Claude Code"
    fi
}

# ---------------------------------------------------------------------------
# Doing it
# ---------------------------------------------------------------------------
RUN_AS=""
if [[ -z "$SERVER_NAME" && -f "$NGINX_CONF" ]]; then
    SERVER_NAME="$(awk '/server_name/{gsub(";","",$2); print $2; exit}' "$NGINX_CONF")"
    [[ "$SERVER_NAME" == "ai.example.local" ]] && SERVER_NAME=""
fi
[[ -n "$SERVER_NAME" ]] || SERVER_NAME="$(hostname -f 2>/dev/null || hostname)"
if [[ -z "$DO_UPGRADE" ]]; then
    if [[ -z "$ASSUME_YES" && -t 0 ]]; then
        step "A few questions"
        note "Enter to keep what is in brackets."
    fi
    ask SERVER_NAME "The pages' hostname (FQDN)"
    if [[ ! -f "$NGINX_CONF" || -n "$REWRITE_NGINX" ]]; then
        ask ALLOW "Who may reach the pages (CIDRs, comma between; all = everybody)" "192.168.0.0/16,172.16.0.0/12,10.0.0.0/8"
    fi
    ask ADMIN_USER "The first account of the pages"
    [[ -n "$ADMIN_PASSWORD" ]] || ask_secret ADMIN_PASSWORD "Its password (empty = make one and print it)"
    ask RUN_AS "The Linux account the terminals run as" "root"
    if [[ -z "$WITH_CLAUDE" ]]; then
        if command -v claude >/dev/null 2>&1 || [[ -x /root/.local/bin/claude ]]; then
            WITH_CLAUDE="no"
        elif confirm "Install Claude Code for root now (Anthropic's installer, claude.ai/install.sh)?" y; then
            WITH_CLAUDE="yes"
        else
            WITH_CLAUDE="no"
        fi
    fi
fi
[[ "$SERVER_NAME" =~ ^[A-Za-z0-9.-]{1,253}$ ]] || fail "$SERVER_NAME is not a host name"
[[ "$ADMIN_USER" =~ ^[A-Za-z0-9][A-Za-z0-9._@-]{0,63}$ ]] || fail "$ADMIN_USER is not a name for an account"
if [[ -n "$RUN_AS" ]] && ! id "$RUN_AS" >/dev/null 2>&1; then
    if [[ "$RUN_AS" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] && confirm "There is no Linux account $RUN_AS - make it (useradd -m)?" y; then
        run useradd -m -s /bin/bash "$RUN_AS"
    else
        fail "there is no Linux account $RUN_AS"
    fi
fi

FIRST_PW=""
install_packages
install_program
install_pages
[[ -z "$DO_UPGRADE" ]] && open_firewall
start_all
first_account
if [[ -n "$RUN_AS" && "$RUN_AS" != "root" && -z "$DRY_RUN" ]]; then
    "$BIN_LINK" --setting default_run_as "$RUN_AS" >/dev/null && good "the terminals run as $RUN_AS (Settings - Claude Code)"
fi
install_claude

step "Done: ai $AI_VERSION"
say "The pages:      https://$SERVER_NAME/"
if [[ -n "$FIRST_PW" ]]; then
    say "Sign in as:     $ADMIN_USER"
    say "Its password:   $FIRST_PW   (to be changed at the first sign-in)"
fi
say "On the server:  ai --status · ai --sessions · ai --attach ID"
[[ -n "$DO_UPGRADE" ]] && say "The terminals that were running go on running."
exit 0
