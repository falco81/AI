# The ai console when root signs in (as otp's).
# Switched with `ai --console-at-login on|off`; q in the console leaves it
# for this shell, and `ai --console` opens it again. Nothing happens for a
# command run over SSH, scp/sftp, a non-interactive shell, a shell opened
# from the console itself, or when AI_NO_CONSOLE is set.
if [ -n "${PS1:-}" ] && [ -t 0 ] && [ -t 1 ] && [ -z "${AI_CONSOLE:-}" ] \
   && [ -z "${AI_NO_CONSOLE:-}" ] && [ -z "${SSH_ORIGINAL_COMMAND:-}" ] \
   && [ -z "${TMUX:-}" ] && [ -z "${AI_TERMINAL:-}" ] \
   && [ "$(id -u 2>/dev/null)" = "0" ] && [ -x /usr/local/bin/ai ] \
   && [ -f /etc/ai-console-login ] && [ ! -L /etc/ai-console-login ] \
   && [ "$(head -c 3 /etc/ai-console-login 2>/dev/null)" = "on" ]; then
    export AI_CONSOLE=1
    /usr/local/bin/ai --console
fi
