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
