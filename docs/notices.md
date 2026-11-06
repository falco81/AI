# What needs the administrator: the notices

ai has one system for everything an administrator must know or do (1.0.85). Every notice is shown:

- **on the pages**: a bar under the header (red for a step that is needed, yellow for mind this, blue for
  information), the state pill turning red (*running - a step is needed*), and *How to fix it*: a window with what
  happened and why, the command for the command line (copied with a click) and the place in Settings;
- **on the command line**: `ai --notices` (exit 1 while a step is needed), `ai --status`, and in the console
  (`ai --console`) on signing in as root;
- in the **events** (Events tab, `ai --events`): when it came, and who said it is done.

A notice: `id`, `level` (`crit` a step is needed / `warn` mind / `info`), `title`, `said` (what and why), `cli` (the
command that fixes it), `link` (a place in Settings, e.g. `settings/upgrade`), and for one a version added: `since`,
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
- With a `check` it goes by itself once the check says so; add the check to `NOTICE_CHECKS` (it gets the store,
  returns True when done). Without one it waits for *Done*.
- A step that can be done for the administrator should rather be done by the upgrade itself; a notice is for what
  needs a person (a decision, a command with a password, a reboot).
- Put the title and the words into `tools/cs_texts.py` too.
