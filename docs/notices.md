# What needs the administrator: the notices

ai has one system for everything an administrator must know or do (1.0.85). Every notice is shown:

- **on the pages**: the alerts that were always at the top (tmux missing, the certificate running out, a newer
  version) stay there, in the yellow bar as before. What a version needs done and SELinux no longer enforcing are in
  **Settings → Upgrades** (1.0.88), with a count on the Settings tab and on Upgrades, the state pill opening it - a card each - red with an ✕ for a step that is needed,
  yellow with a ⚠ to mind, blue for information - its title, what happened and why, where to run the command
  ("As root, on the server:" or the notice's own `cli_where`), the command in a box with *Copy*, and when the card
  goes; on the right *Open it* (the place in Settings), *Done* (one a version added) and *Not now* (hidden in this
  browser for 8 hours; a card whose words change comes back at once). The state pill turns red (*running - a step is
  needed*);
- **on the command line**: `ai --notices` (exit 1 while a step is needed), `ai --status`, and in the console
  (`ai --console`) on signing in as root;
- in the **events** (Events tab, `ai --events`): when it came, and who said it is done.

A notice: `id`, `level` (`crit` a step is needed / `warn` mind / `info`), `title`, `said` (what and why), `cli` (the
command that fixes it), `cli_where` (where to run it, e.g. "As root, in the folder the package was unpacked in:"), `link` (a place in Settings, e.g. `settings/upgrade`), and for one a version added: `since`,
`done_by` (`admin`: said done with *Done* or `ai --notice-done ID`; `''`: goes only by its check), `check`.

## Two kinds

**Checks** - worked out from the state of the server, and gone by themselves when the cause is:

| id | level | when |
|---|---|---|
| `tmux` | crit | tmux is not installed |
| `cert` | warn / crit | the certificate of the pages runs out within 14 days (3 days: crit) |
| `selinux-off` | warn | SELinux was Enforcing when ai first looked and is not now - by an update, by hand, by another program |
| `newer` | info | a newer version of ai is out |

**A version's own** - for what an upgrade cannot do by itself: a step on the command line, SELinux it changes,
a service to restart by hand. Listed in `VERSION_NOTICES` in `ai.py`; the daemon adds each one **once**, when it
first starts on that version (or on a later one, coming from an earlier) - never on a fresh install - and it stays
until done.

## Adding one for a future version

In `ai.py`, `VERSION_NOTICES`:

```python
VERSION_NOTICES = [
    {'since': '1.0.90', 'id': 'v1.0.90-relabel', 'level': 'crit',
     'title': 'SELinux labels have to be set again for ai 1.0.90',
     'said': 'The pages moved to /var/www/ai; until they are relabelled nginx may not read them.',
     'cli': 'restorecon -Rv /var/www/ai',
     'check': 'selinux_labels'},          # optional: a key of NOTICE_CHECKS - True once the cause is gone
]
```

- `id` stays the same forever (a notice said done is not added again).
- With a `check` it goes by itself once the check says so: `file:/a/path` (done once that file is there), or a key
  of `NOTICE_CHECKS` (it gets the store, returns True when done); `check_words` says on the card when it goes. Without
  one it waits for *Done*. *Look again* on the card runs the checks at once.
- A step that can be done for the administrator should rather be done by the upgrade itself; a notice is for what
  needs a person (a decision, a command with a password, a reboot).
- Put the title and the words into `tools/cs_texts.py` too.
