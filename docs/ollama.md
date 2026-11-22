# Chats with Ollama

Since 1.0.101. A chat can talk to a model of [Ollama](https://ollama.com) instead of Claude. It is the same
Claude Code, pointed at Ollama: Ollama 0.14 and newer speaks the Anthropic Messages API (`/v1/messages`), and
Claude Code talks to any server that does. Nothing else is installed for it.

## Switched on

**Settings → Ollama**, or on the server:

```
ai --set ollama_on=1
ai --set ollama_where=local ollama_port=11434        # Ollama on this server
ai --set ollama_where=remote ollama_url=http://192.168.1.50:11434   # elsewhere on the network
```

| setting | what |
|---|---|
| `ollama_on` | chats with Ollama offered at all (off at first) |
| `ollama_who` | `all` accounts, or `admins` only |
| `ollama_where` | `local`: `http://127.0.0.1:PORT`; `remote`: the address below |
| `ollama_port` | the port on this server (11434) |
| `ollama_url` | `http://host:11434` or `https://…` behind a proxy of your own (a `/v1` at the end is taken off) |
| `ollama_key` | a bearer token, only when something in front of Ollama asks for one; sealed like every password |
| `ollama_model` | the model a chat starts with when none is chosen (empty: the first Ollama lists) |
| `ollama_small` | the model for Claude Code's small work on the side - Haiku's part (empty: the chat's own) |

Ollama elsewhere on the network has to listen there (`OLLAMA_HOST=0.0.0.0` in its service). Only the server
asks it, never the browser, so it does not have to be reachable from the browsers.

## What Ollama has

The settings, and `ai --ollama` (`--json`), ask Ollama for its version (`/api/version`), its models
(`/api/tags`) and each model's context and abilities (`/api/show`, up to 40 models, 8 at a time). A model
without **tools** is marked: Claude Code works by tools, and such a model can only talk. What was found is kept
for 30 seconds. *Try it* in the settings asks with the values written there before they are saved.

## A new chat

A new chat starts with Claude unless an Ollama model is chosen for it (1.0.102). The model chip under the box of a new chat lists **Claude (subscription)** and below it **Ollama** with its
models; *Every option…* has them in the model list. A chat started with an Ollama model runs Claude Code with:

```
ANTHROPIC_BASE_URL=http://…:11434
ANTHROPIC_AUTH_TOKEN=ollama                (or the key)
ANTHROPIC_API_KEY=                         (empty)
ANTHROPIC_MODEL, ANTHROPIC_DEFAULT_OPUS_MODEL, ANTHROPIC_DEFAULT_SONNET_MODEL,
CLAUDE_CODE_SUBAGENT_MODEL                 the model chosen
ANTHROPIC_DEFAULT_HAIKU_MODEL, ANTHROPIC_SMALL_FAST_MODEL   the small one
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

Ollama's host is added to `NO_PROXY` when the terminals use the proxy. A `--model` in the words every chat
is started with (Settings → Claude Code) is left out of an Ollama chat. The chat keeps its choice: started
again, picked up, or changed (*Change…* offers Ollama's models and Claude's, and the conversation goes with
it either way). A model Ollama does not have is refused before anything is changed. When Ollama does not
answer, the chat starts all the same and Claude Code says what is wrong.

On the server:

```
ai --new DIR --ollama qwen3-coder:30b
ai --new DIR --ollama                     the model offered first
```

The list of chats says *Ollama MODEL* under such a chat.

## Context length (1.0.105)

Claude Code sends a long system prompt and the descriptions of its tools with every question. Ollama keeps only
as much of a chat as its context length, and its own default is small: 4096 tokens under 24 GB of VRAM, 32768
from 24 GB, 262144 from 48 GB. With too little, the model loses the thread and writes on until Claude Code stops
it: *Claude's response exceeded the 128000 output token maximum*. Ollama recommends at least 64000 for coding
tools.

- **What Ollama has** shows *Context now* for each loaded model (Ollama's `/api/ps`), in orange under 64000, and
  whether the model runs partly on the CPU. A note says when the context is too little.
- **Ollama on this server** (systemd): *Set it on this server's Ollama* writes
  `/etc/systemd/system/ollama.service.d/ai-context.conf` with `OLLAMA_CONTEXT_LENGTH` (the setting *Context length
  to set*, 65536 at first) and starts Ollama again. *Take it away again* removes the file. Only that one file is
  written. On the server: `curl` the API, or `ollama ps` for the CONTEXT column.
- **Ollama elsewhere**: set `OLLAMA_CONTEXT_LENGTH=65536` where it runs (its service, or the slider in the Ollama
  app) and start it again.

More context takes more memory. A model that no longer fits the GPU runs partly on the CPU, slower.

*Longest answer* (`CLAUDE_CODE_MAX_OUTPUT_TOKENS`, 32000 at first) stops an answer that runs on long before
Claude Code's own 128000: a local model that lost the thread would otherwise write for an hour first.
