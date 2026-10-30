# The Claude Code tab

Everything Claude Code reads besides its command line, for one Linux account
(an administrator chooses which; a user has their own) and, when one is
chosen, one project folder. Files are read and written as that account - its
owner, its modes - and what Claude Code keeps itself (`~/.claude.json`, its MCP
servers and plugins) is changed by Claude Code's own commands, run as that
account.

| pane | what it is | where |
|---|---|---|
| Overview | the version, the sign-in (`claude auth status`), the doctor, update | |
| Settings | the usual keys as fields - model, permission mode, effort, output style, language, transcripts kept, Co-Authored-By, thinking, `.mcp.json` servers, hooks off, tips, updates, API key helper, status line, more folders, the environment - and the whole file as JSON | `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json` |
| Permissions | allow / ask / deny rules built from a tool and what of it | the same files |
| Hooks | a command per event (PreToolUse, PostToolUse, UserPromptSubmit, Stop, SessionStart, ...) with a matcher and a time | the same files |
| Memory | CLAUDE.md | `~/.claude/CLAUDE.md`, `CLAUDE.md`, `CLAUDE.local.md` |
| MCP servers | listed by scope, added (stdio, HTTP, SSE; arguments, environment, headers), removed, checked, a project's servers let in or kept out | `claude mcp add-json / remove / list` |
| Agents, Commands, Skills, Output styles | listed, written with their head (description, tools, model, ...) and body, deleted | `.claude/agents`, `commands`, `skills/*/SKILL.md`, `output-styles` |
| Plugins | installed (on, off, updated, uninstalled), marketplaces (added, updated, removed), what they have (installed for you or the project) | `claude plugin ...` |
| Background sessions | what `claude agents` lists; a background one opened in a terminal (`claude attach`), its output, stopped, removed | |
| Usage | the tokens of the conversations by day, model and folder | `~/.claude/projects/*/*.jsonl` |
| Keyboard | `keybindings.json` | `~/.claude/keybindings.json` |

## What the chats used - on the Overview

The Overview tab counts every chat with Claude Code of the Linux accounts you
may see (an administrator: every account with Claude Code's transcripts; a
user: their own), over 7 days, 30, 90 or a year:

- the estimated cost, the chats, the cost per chat, the answers, the tokens
  written by Claude, sent, and read from the cache, and the cache's share;
- by day and by hour of the day, as cost or as tokens;
- by model, by account and by folder;
- every chat - its first words or summary, account, folder, model, answers,
  tokens, cost and when last - found by words, folder or model and sorted by
  newest, dearest, longest or most written. A click opens its terminal when it
  still runs; the right button (a finger held still) picks it up again with
  `--resume`, copies its ID or the command, or opens its folder in Files.

It is read from Claude Code's own transcripts
(`~/.claude/projects/*/*.jsonl`), each answer counted once. The cost is an
estimate at Anthropic's list prices per token (writing the cache is 1.25 x
input), to compare by: a Claude subscription is not billed by the token. A
model of no known price is named under the figures and counted at nothing.
The terminal of a chat is the Claude Code terminal of the same account and
folder that was open when the chat began.
