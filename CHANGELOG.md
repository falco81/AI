# ai — what changed

Every change is a new version: the number is in `ai.py` (`ai --version`), on
the pages (Settings → About), in the name of the folder and of the archive.

## 1.0.51

- **A password saved stays saved on the page** (Settings, the save bar): what was saved was left among the
  changes, so a password - shown as dots once saved, never as what was typed - kept *1 change(s) not saved yet*
  for ever and the page was not drawn again; on Backups the top still said *NOT locked - set the password*,
  though the password was saved. The saved ones are forgotten as changes now, the page is drawn again, and
  Backups shows at once whether its backups are locked and when the next one goes.

## 1.0.50

- **No more kernel notices over the ai console** (as otp's 1.0.210): every `systemctl daemon-reload` - each
  dnf update touching units, ai's own install - has systemd's generators log lines such as
  `/etc/rc.d/rc.local is not marked executable, skipping` to the kernel's log, and where the console log level
  is 7 the kernel printed them over the console on tty1. install.sh (install and every upgrade) now writes
  `/etc/sysctl.d/80-ai-console.conf` with `kernel.printk = 4 4 1 7` - errors only on the console, RHEL's own
  default; `journalctl -k` keeps everything - unless `kernel.printk` is already set by hand elsewhere, which is
  left alone. `--uninstall` takes the file away. rc.local is not made executable.

## 1.0.49

- **Settings -> Proxy: each use switched on by itself**, all off at first (the proxy itself too) - with none on,
  nothing ai does goes through it. The uses: *The updates of ai*, *The system updates* (dnf, apt), *ACME - the
  CA*, *ACME - the DNS APIs* (Cloudflare, acme-dns, deSEC), *The SMS gateway (HTTP)*, *The SMS router
  (Teltonika)*, *The terminals and Claude Code* (HTTPS_PROXY, HTTP_PROXY, NO_PROXY in the new claude and shell
  terminals) and *Installing and updating Claude Code*. A use that is off goes straight, never through what the
  environment of the service says. Mail (SMTP), the backups (FTP, SFTP, SMB), NTP and the database are not HTTP
  and always go straight. *Try it* asks through the proxy as saved, whichever uses are on.

## 1.0.48

- **The proxy is for the updates only** (Settings -> Proxy): the new versions of ai (looked for and fetched) and
  the system updates (dnf, apt) go through it, nothing else. The SMS gateway, ACME's CA and its DNS APIs go
  straight again, as before 1.0.47 - a proxy that is down or refuses can no longer stop anything ai does but
  its updates. *The SMS gateway through it too* is gone; the page and *Try it* say what the proxy is for.

## 1.0.47

**Settings -> Proxy, as otp's** (off until switched on): an HTTP proxy, with a user name and a password kept
sealed, for what ai asks of the web - the new versions, the SMS gateway, the ACME CA and its DNS APIs - and for
dnf or apt fetching the system updates (handed to the update's job in a file only root reads, never on a
command line). Names, domains and nets reached straight are listed (`.example.cz`, `10.0.0.0/8`); the system
updates and the SMS gateway can each be left out of it. Mail and the database never go through it, nor does
what the environment of the service says.
- **Try it**: an address asked the way ai asks the web - through the proxy, or straight where none is set or
  the address is in the list - and the way it went drawn: this server, the proxy, the address, each link green
  or red, then every step with its time (the name looked up, the connection, the tunnel, TLS and the
  certificate, the answer).
- `ai --proxy-test [URL]`; the menu has it under *Server*, after Network, as otp's.

## 1.0.46

**Upgrades and maintenance, as otp 1.0.197 (without high availability)**
- *Settings -> Upgrades and maintenance -> The nodes*: the server, its version, when it was heard from, and
  whether it is **in service** or **in maintenance** (why, by whom, when) - with *Maintenance* / *Back in
  service*, asked first with the reason for the events.
- **Maintenance**: this server out of service - `/healthz` says `503 maintenance HOST` (and `ok HOST` otherwise),
  so a monitor or a load balancer leaves it alone; nobody but an administrator signs in and no new terminal is
  started but an administrator's; the terminals that run go on, and so do these pages. The header says *in
  maintenance*. An upgrade from these pages takes the server out first and brings it back once the new version
  runs (or the upgrade failed); one taken out by hand stays out until brought back.
  `ai --maintenance on|off|status [--why ...]`; the console has it under Upgrades.
- *What root said last* folded until opened (a long log pushed the rest down); *From the web*: its settings in
  otp's order and words (*Look for a new version every day*, *Where new versions are looked for*, *Offer going
  back to an older version*), ai's own auto-upgrade after them.
- **The settings menu in otp's groups and order**: *Access* (Accounts, The sign-in page, Certificates and TLS,
  Automatic certificates, Firewall and access, SSH keys of root), *Server* (Network, Time, Restart and power
  off), *Data*, and *Monitoring and updates* (System updates, Upgrades, About).

**Automatic certificates -> In your DNS** across the whole width again, each column a fixed share of it: the
same on a reload and after *Check DNS* (the last column's words changed and the columns were shared out anew).

## 1.0.45

- **Automatic certificates -> In your DNS**: room between the columns - the table no longer packed them against
  each other; each copy button still right after its text.

## 1.0.44

- **Automatic certificates -> In your DNS**: the table stretched across a wide screen and left wide gaps between
  each record and its copy button. It is as wide as what is in it now: every text as wide as it needs, its copy
  button right after it, one under the other.

## 1.0.43

- **Automatic certificates -> In your DNS**: the copy buttons flickered at every refresh of the page - they
  were lined up by measuring the text after it was drawn, so each redraw showed them out of line first (and a
  redraw merged into the page never lined them up at all). They now have narrow columns of their own right
  after the record and the value: one under the other, right after the longest text, by the table itself.

## 1.0.42

- **A setting hanging on one that is greyed out is greyed out too**, on every settings page: with ACME off,
  *The TXT records go into* (and *Wait for DNS to carry it*, the deSEC fields...) stayed open, because the
  choice they hang on would have let them. It says why from the setting further up ("Not in use while
  Certificates from an ACME CA is off").
- **The CA's own certificate** is a memo two columns wide and two settings tall, a whole PEM in view in a
  small monospaced font (resizable), the settings beside it stacked as usual.

## 1.0.41

- **Automatic certificates exactly as upsmon's (4.1.7)**: the page's script is upsmon's own - the card (its tags,
  *For*, *Issued by*, *Keys*, *Good until*, *Last ordered*, *Ordered by*), the order going on, the TXT record by
  hand, *Back to the one before*, *Its name...*, *In your DNS* with its steps and *Check DNS*; the pane's words and
  the menu button too. Every setting has upsmon's name, help (with its `code` marks) and choices, in its order;
  *The CA's own certificate* is a box in its place in the grid, as upsmon's, not a whole row.

## 1.0.40

**Automatic certificates: the keys as upsmon's (4.1.6, 4.1.7)** - every key Let's Encrypt accepts
(https://letsencrypt.org/docs/integration-guide/):
- **The certificate's key:** RSA 2048, 3072, 4096 or ECDSA P-256, P-384 - and, the new default, **both**: two
  certificates for the name, RSA served by default and the much smaller ECDSA one to the clients that take it
  (*Both: RSA 2048 + ECDSA P-256 (advised)*, or *Both: RSA 4096 + ECDSA P-384*). The second order only signs:
  the name is already proven. nginx gets two `ssl_certificate` / `ssl_certificate_key` pairs (`ai.pem` and
  `ai-ecdsa.pem`); a certificate put in another way on Certificates and TLS drops the ECDSA one.
- **The account's key** (new setting): ECDSA P-256 (ES256), P-384 (ES384) or RSA 2048, 3072, 4096 (RS256) -
  never a certificate's key. A change makes a new account at the next order.
- The keys show on the ACME card (*Keys*), on the certificate (*Key*) and beside the account; the order's
  steps say which keys were made. *What the last order did*: the time one narrow column, the words beside it.
- A key chosen before is kept; one never chosen is *both* from the next renewal - *Order it now* for it at once.
- The second certificate's key never reaches the page.

## 1.0.39

**Automatic certificates (ACME), as otp's** - *Settings -> Automatic certificates*, off until switched on:
- The certificate of the pages ordered from **Let's Encrypt**, its staging, or another ACME CA (step-ca, an
  internal CA - its directory and its root given), and **renewed by itself** when fewer than 30 days (as set)
  are left - a CA giving short-lived certificates at a third of their life. Checked once an hour; a failed
  order is tried again after 6 hours. An account the CA no longer knows is made anew by itself.
- **HTTP-01**: nginx sends port 80's `/.well-known/acme-challenge/` to `acme.php`, which gives the answer kept
  in the database (put into nginx's file by itself on an existing install). **DNS-01** for a server the CA
  cannot reach: RFC 2136 (nsupdate with a TSIG key, kept sealed, in a file only for the moment it runs),
  Cloudflare, acme-dns, **deSEC.io** (free; its name servers asked straight until both have the record), or
  by hand (the TXT record shown, the order waiting for *It is in DNS*). *The TXT records go into*: a zone of
  its own, the name with one CNAME to it in your DNS. *DNS servers for ACME*: public ones to see what the CA sees.
- **The key of the certificate - every one Let's Encrypt takes**: ECDSA P-256 or P-384, RSA 2048, 3072 or
  4096 - or **both**, as Let's Encrypt advises: an RSA certificate by default and an ECDSA one nginx offers to
  the clients that can take it (two `ssl_certificate` pairs). The account at the CA has a key of its own,
  never the certificate's. Another key asked for orders the certificate anew.
- The card: what it has now, days left, the key, the last order step by step (*What the last order did*),
  *Try port 80* (asked as the CA will), *Order it now*, *Look after it* / *Leave it alone*, *Its name...*, and
  **Back to the one before...** - a certificate of your own replaced by ACME is kept and put back with its key.
  **In your DNS** lists what the name needs there, with the steps of the way chosen and **Check DNS**.
- *Certificates and TLS* says who renews the certificate; one uploaded or made self-signed there is kept -
  ACME does not replace it (asked first). Its TLS settings stay through every renewal.
- `ai --acme`, `ai --acme-order` (followed); the console: *The server -> The certificate of the pages*.
- Every order, renewal and failure is an event.

## 1.0.38

- **Backups to SMB on a machine smbclient sees no interface of**: smbclient stopped with *Could not determine
  network interfaces, you must use a interfaces config line* (an address with a /32 mask, IPv6 alone, no
  network interface it takes). It is asked again with the loopback as its interface list - a list only its
  NetBIOS broadcasts use, never the connection to the server - and goes on.

## 1.0.37

**Updates and restarts on a schedule, as otp's (1.0.164)**
- *System updates -> On a schedule* (off until switched on): a look for updates every day at a set time -
  for the card, nothing put in - and the updates put in by themselves in a window: only the security ones
  (`dnf --security`, `unattended-upgrade` on apt) or all of them, every day, week or month, restarted by
  itself where needed or the restart offered.
- *Restart and power off -> On a schedule*: the server restarted in a window, every week or month - only when
  an update left it waiting for a restart, or every time. Not while an update or a look for updates is going
  on: it waits for it.
- Each once in its window; one that cannot start is said in the events, not tried over and over.
- An update by hand can be the security updates only, too (*Which*).

## 1.0.36

- **System updates after a restart made by itself**: the server was restarted as asked (*Restart by itself when
  needed*), but the pane went on saying *ai needs a restart* - what the update had wanted was never let go.
  A restart wanted before the machine last started is taken as done now, and once it is back ai looks for
  updates again by itself, so the pane says how it stands after the restart.
- The update's end cleared only the count: *of them security* and *restart after the update* stayed as they
  were before it. They go with the rest now.
- The restart after the update came only while somebody had the pane open (what the update's job wrote was
  read in only then); the daemon reads it every 15 seconds now.
- *After the update* shows the choice of the last update when the page is loaded again, not always *Ask me*.

## 1.0.35

- **System updates: the restart on a line of its own**: *restart after the update* (or *restart needed*) stood
  beside the server's name and its other tags and ran out of the card; it is on its own line under them now.

## 1.0.34

- **ai on the newest Python there is**: the install and every upgrade - from the pages too - look for the
  newest `python3.X` the repositories offer (on AlmaLinux 9 python3.14, 3.13 or 3.12, whichever its 9.x has),
  put it in beside the system's own python3 (which stays: dnf runs on it) and move ai onto it - ai.service and
  the command `ai` both. A Python is taken only when it starts ai and has ssl, sqlite3 and termios; one that
  does not is passed over, and with none newer ai stays where it is. The database driver and colorama are put
  in for that Python (its own package, or pip). The choice is kept in /usr/local/lib/ai/python;
  `--python PATH` chooses one, `--no-python-update` keeps the one in use. Settings -> About shows which runs.
  ai is checked on Python 3.11, 3.12, 3.13 and 3.14.

## 1.0.33

- **PHP on the 8.3 stream, at 8.3.36**: the install and every upgrade put PHP on `php:8.3` now, not `php:8.2`
  (1.0.32) - 8.3.36 has the php2shell fix. An 8.0, 8.1 or 8.2 is moved up to it, an 8.3 brought to its newest
  build, a newer PHP without the fix moved to it as well; a newer one with the fix is kept. On EL 8, which has
  no `php:8.3`, it is `php:8.2` and its 8.2.35. `--php-stream X.Y` still chooses another.

## 1.0.32

- **PHP on the 8.2 stream, at 8.2.35**: on AlmaLinux / Rocky / RHEL 8 and 9 (PHP as AppStream modules) the
  install and every upgrade - from the pages as well - put PHP on `php:8.2`, whose 8.2.35 has the php2shell
  fix (CVE-2026-109618, CVE-2026-109619): an older PHP (8.0, 8.1) is moved there, and so is a newer one that
  does not have the fix yet (an 8.3 short of 8.3.36); an 8.2 is brought to its newest build. The stream is
  reset and enabled, every PHP package moved with `dnf distro-sync`, php-fpm restarted, and the version
  reached is said. A newer PHP that has the fix is kept; `install.sh --upgrade --php-stream 8.2` moves even
  that, `--php-stream 8.3` puts another stream instead, `--no-php-update` leaves PHP alone. ai's PHP pool and
  the guard against php2shell stay as they were.

## 1.0.31

- **Downloading the certificate, in the form wanted**: *Download* under Settings -> Certificates and TLS opens a
  window to choose it - the certificate alone as PEM, CRT, DER or PKCS#7 (.p7b), or with its private key:
  PFX / PKCS#12 (always locked with a password; AES-256, or 3DES and SHA-1 for an older Windows), PEM with the
  key, or the key alone (both locked with AES-256 when a password is given). The chain goes along unless
  switched off; *Make a strong password* makes one and puts it on the clipboard. A download with the key is
  written in the events, as a warning. It is there for the certificate nginx had before ai looked after it too.

## 1.0.30

- **The command line and the console caught up with the pages**: what came on the pages since 1.0.13 is in
  `ai` and `ai --console` too -
  `--new` with `--effort` and `--mode` (and the model of any version, in the console from a list);
  `--edit ID` (`--title`, `--model`, `--effort`, `--mode`, `--cwd`) - a chat's choices changed, it goes on with
  its conversation; `--forget ID|ended` - ended terminals off the list; `--usage [--days N]` - what the chats
  used and what it costs, by model, account, folder and chat; `--signin-art [NAME]`, `--signin-logo FILE`,
  `--signin-logo-forget` - the picture of the sign-in; `--db-ipv4 [only]` - where the database server listens,
  kept to 127.0.0.1. In the console: Terminals (change a chat, take ended ones off, what the chats used),
  Settings - The picture of the sign-in page, Data - The database server.
- **A terminal's last screen in the console** opened over the menus without its own screen; it has one now.

## 1.0.29

- **The picture chosen for the sign-in shown to everybody**: the page tells a visitor not signed in from
  elsewhere no more than the language - and left out which picture was chosen, so from any other machine the
  sign-in kept showing the default one (from the server itself it was right). It is told the picture now too.

## 1.0.28

- **The pages after the upgrade to 1.0.27**: install.sh put in the PHP files of the pages by a list of names,
  and 1.0.27's new one (`ai-art.php`, the pictures of the sign-in) was not on it - so after the upgrade the
  page answered HTTP 500. It now puts in every PHP file there is, and a check makes sure it stays so.

## 1.0.27

- **The picture of the sign-in, chosen as otp's**: Settings -> The sign-in page shows every picture the sign-in
  can carry, drawn for what ai is - a browser, a terminal, a chat, tmux panes, the devices it reaches, the spark,
  a tablet, a diff, folders, agents side by side, the usage, the keys - and none at all; pick one and Save.
  *Upload your own* puts the site's own picture there instead (PNG, JPEG, GIF, WebP or SVG up to 512 KB, an
  SVG with a script or a link out turned away); *Forget it* takes it away again. The choice is in the database,
  so it is in every backup and in the exported configuration, and the import puts it back.

## 1.0.26

- **nginx on IPv6 whenever the machine has it**: installed with IPv6 off in the kernel, nginx's file was written
  without its `[::]` listen lines, and IPv6 switched on later never got them. They are put in (or taken out)
  after every change under Settings -> Network and when the daemon starts, nginx tested first and reloaded.
  The firewall needed nothing: its rules are written for IPv4 and IPv6 alike already.
- **The database server kept to IPv4**: The database shows where a MariaDB or PostgreSQL server on this machine
  listens, and *Only IPv4 (127.0.0.1)* tells it to listen on 127.0.0.1 alone - nothing over IPv6, nothing from
  outside - and starts it again (MariaDB: a `bind-address` file of ai's; PostgreSQL: `listen_addresses`).

## 1.0.25

- **A chat's choices changed while it runs**: *Change it…* on a chat's right button, its ⋯ and under More - its
  name, working directory, model (any version), effort, permission mode and more words for Claude Code. Claude
  Code takes these only when it starts, so the chat is started again in its own tile and goes on with its
  conversation; a new folder gets the conversation's transcript too, where Claude Code looks for it. A shell
  can be moved to another folder the same way.
- Claude Code's own options a chat was started with (effort, tools, system prompt, agent...) are kept when it
  is started again; only the model, the permission mode and the words were.

## 1.0.24

- **Files only in the folder of the chats** (Settings -> Claude Code, shown once the folder of the chats is set):
  on, the Files tab, the files of a chat, downloads and uploads reach that folder and what is under it only -
  for every account, administrators too; the daemon refuses any other path, and a path from before opens the
  folder itself.
- **The Overview in two**: *The server* (the machine, who is signed in, lately) and *Claude Code - the chats*
  (what the chats used, by day, hour, model, account and folder, and every chat), each its own address -
  `#overview` and `#overview/claude` - kept on F5.

## 1.0.23

- **Alt codes in the terminals**: Alt held and digits on the numeric keypad type their character when Alt is
  let go, as Windows does - Alt+64 is @, Alt+nnn the old DOS code page (437), Alt+0nnn the Windows one (1252).
  The digits went to the terminal as Esc and a digit.
- **The right button pastes, as in PuTTY**: in a terminal the right button puts the clipboard in, and what is
  selected is copied by itself; Ctrl with the right button (or a finger held still) opens the menu. Under your
  account (Language and letters) the right button can open the menu instead, as before. The browser asks once
  whether the page may read the clipboard.

## 1.0.22

- The headings of the start page (*Folders used lately*, *Going on*, *Ended lately*) have their room above
  again: a rule of the empty terminal pane took it away and each stood pressed against what was over it.

## 1.0.21

- On the start page *Folders used lately* stands above *Going on*, next to the box whose folder it sets, with
  room under it; its heading is in Czech too.

## 1.0.20

- **Only the terminal, over the whole screen**: a button in the terminal's bar (four corners) - and on the
  terminal's right button - puts the terminal alone over the whole screen, no bar, no buttons. Where the keys
  can be locked (Chrome, Edge) Esc goes to the terminal and is held to come back; where an element cannot take
  the screen, the terminal covers the whole window and Esc twice comes back. A × shows in the corner when the
  mouse moves.

## 1.0.19

- **The terminals' colours as PuTTY's**: the palette of the terminals was the pages' own, light and soft - mc's
  blue panels came out pale. The classic VGA palette PuTTY uses is now the default, bold drawn in the bright
  colours as PuTTY does. Eight to choose from - classic (PuTTY), xterm, the Linux console, Tango, Solarized dark,
  Dracula, the pages' soft one, light - as swatches under your account (Language and letters) and under More
  in a terminal, kept with the account.
- **Ended lately on the start page**: under *Going on*, the last six that ended - the pinned ones first - each
  started again where it stopped, in its own tile, by a click; *all of them* opens the list with the ended ones.
  More room between the two.

## 1.0.18

- **Every ended terminal off the list at once**: *Take every ended one off the list (n)* on the right button
  of the list of terminals and of any terminal in it, asked first. The running ones are not touched, and the
  conversations of Claude Code stay under Conversations. One at a time is still *Take it off the list*.
- In Conversations the git branch of a conversation stands beside its folder: its tag lay over the folder's
  name.

## 1.0.17

- **One tile a conversation in the list**: before 1.0.16 picking a conversation up again started a new terminal
  each time, and with *with the ended ones* the list showed the same chat many times over beside the one
  running it. The terminals that held the same conversation are merged by themselves: the running one - else
  the newest - is kept, the ended copies forgotten. An ended tile is matched only by the conversation it was
  started with, never by a guess from the times.

## 1.0.16

- **A chat keeps its tile**: each chat with Claude Code is given its conversation's ID when it starts
  (`--session-id`), and ai keeps it. Picking a conversation up again (Conversations, the Overview, the chat's
  menu) goes back into the terminal that holds it - opened if it still runs, started again in its own place if
  it ended, with its name and its pin - instead of a new tile. *Start it again* and *Restart* go on with the
  chat's own conversation (`--resume`), not the folder's last one or an empty new one; a `/clear` or a
  `/resume` inside the chat is followed.
- **Close** in the terminal's bar: back to the start page, the chat goes on running on the server.
- **Every version of the models**: Fable 5.1 and 5, Opus 5.5 to 4.6, Sonnet 5.5 to 4.6, Haiku 5.5 and 4.5 by
  name, beside the families (always their newest) - in the new terminal dialog, the start page and Claude
  Code's settings.
- **F5 anywhere keeps the page**: a page opened at its address (Settings -> Network, Time, the Overview's usage,
  the Claude Code tab) asked for its data before the scripts that load it were there, and stayed empty.

## 1.0.15

- The ⋯ of a chat in the list of terminals is in the row's bottom right corner: at the top it lay over the
  chat's name and its state. The state (running, ended, open) is never cut short any more.
- The figures of the Overview's usage line up: each tile's figure on one line whatever its label wraps to, the
  tiles across the whole width, every number of the tables in one font with digits of one width.

## 1.0.14

- **The scroll bar moves with the history again**: Claude Code's full-screen look (now its default for many
  accounts) keeps its history to itself, where the bar beside the terminal could only be a jog wheel standing
  still. Claude Code is started drawing itself the classic way (`CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1`), so
  everything it says is in tmux's history: the bar shows where you are, History shows all of it, a finger
  scrolls it. Settings -> Claude Code -> *Claude Code written into the terminal's history* (on) turns it off;
  `/tui` in a chat switches that one. Chats already running keep their look until started again.
- **The time zone is saved**: the Time pane is drawn again every 10 seconds, and a zone chosen in the list
  drawn before that went into a draft thrown away - the save put in the old one. The draft is refreshed in
  place now.
- **A window over a window goes back to the one under it**: choosing a folder from the new terminal dialog,
  and every question asked twice ("Delete it?"), opens over the dialog; Close or No returns to it as it was.
- **Where a chat may start, said where it is chosen**: the new terminal dialog says whether the folder of the
  chats limits it (or that it may start anywhere), with the way to Settings -> Claude Code -> *The folder of
  the chats*.
- The banner's link to a new version opens Settings -> Upgrades itself, not only Settings.

## 1.0.13

- **What the chats used, on the Overview**: every chat with Claude Code of the accounts you may see, with its
  answers, tokens (written, sent, cache) and an estimated cost at Anthropic's list prices; the same by day, hour
  of the day, model, account and folder, as cost or as tokens, over 7 days to a year. A chat opens in its
  terminal, or is picked up again with `--resume`; found and sorted by newest, dearest, longest. A Claude
  subscription is not billed by the token: the cost is there to compare by.
- **Even spacing in the Claude Code tab**: the account and project bar, the heading, each card and the row of
  tiles are 16 pixels apart everywhere - the tiles touched the card above them.

## 1.0.12

- **The right button anywhere on the list of terminals**, not only on a chat: a new Claude Code or shell, picking
  up a conversation, the ended ones shown or not, finding a terminal, the list kept open or hiding itself, read
  again. A finger held still does the same on a tablet.

## 1.0.11

- **The pinned menu of the settings moves the page aside again**: pinning it moved the Claude Code tab's page
  instead (the first of the two on the page), so the settings stayed under the menu. Pointed at, the menu lies
  over the page as otp's does; pinned, the page is beside it - exactly as otp.
- The banner saying a new version is out is in the banner's own colour, not the browser's visited purple, which
  could not be read on its yellow; every link of the pages is in their blue, visited or not.

## 1.0.10

- **A scroll bar for Claude Code full-screen**: Claude Code's full-screen look keeps its history itself, so
  tmux had none and the bar beside the terminal hid itself. It is now a jog wheel there - dragged up goes back,
  down comes on, its ends a page - and a finger on the terminal moves it, as the mouse wheel does.
- **The rails do not move under the pointer**: the list of terminals slides out with the pin, *New terminal* and
  every chat's icon exactly where they were; what an item of a rail says is shown beside the rail, not over the items.
- **The right button in the Files tab**: on a file or a folder (open, a new Claude Code in it, copy the path,
  a new folder or file in it, download, rename, delete) and on the list (new folder or file, upload, a new
  Claude Code, copy the path, read again); a finger held still does the same on a tablet.

## 1.0.9

- **The history on a tablet**: a finger on the terminal moves back through tmux's history and on again, a bar
  on its right is always there to drag or tap, *Back to now* returns; **History** shows every line tmux keeps,
  with its colours, in a window that scrolls by finger - copied or downloaded.
- **A finger held still is the right button**: on the terminal, the chats, the files and the folders.
- **The folder of the chats** (Settings → Claude Code): a new chat starts in it or under it only - the daemon
  refuses the rest; the folder picker starts there, never goes above it, and makes, renames and deletes
  folders and files (buttons, right button, a finger held still). The chat's own files make new files too.
- **Starting as on claude.ai**: a greeting, a box to write the task in, the folder, model, permission mode and
  effort as chips, Enter starts Claude Code on it; the chats going on as cards below.
- **Every option of Claude Code** in the new chat dialog as fields - name, effort, fallback model, every
  permission mode, allowed / denied / built-in tools, more folders, the system prompt added or replaced, the
  agent, MCP configs, settings and their sources, plugin folders, worktree, fork, session ID, autocompact,
  Remote Control, verbose, debug, safe mode, bare, restricted, Chrome, IDE, brief, no slash commands, a screen
  reader, the first message, a session in the background - kept as how the account's chats start when asked.
- **The Claude Code tab**, for an account and a project: settings (fields and JSON), permissions (allow, ask,
  deny), hooks, memory (CLAUDE.md), MCP servers (added, removed, checked, let in), agents, commands, skills,
  output styles, plugins and marketplaces, background sessions (opened, logs, stopped, removed), usage by day,
  model and folder, keybindings, the sign-in and the doctor.
- The model, the permission mode, the more words and the last folder of a new chat are remembered again: they
  were dropped by the daemon.

## 1.0.8

- **Settings → Accounts as otp's**: every account in one row with its role chosen right there and the same
  buttons in the same places - its Linux account and folders, a new password typed by the administrator,
  stop or let it sign in, remove it, **put its columns back as they come**, reset its second step - a button
  that does not apply dimmed and saying why; how many tables each has laid out; *Signed in now* as otp's,
  each sign-in ended with a question first.
- **The menus hide themselves with their pin on every screen 981 px wide or more**, whatever the browser says
  about a touch screen or a mouse; narrower, they lie across the top as before.

## 1.0.7

- **The menu of the settings in otp's order**: Claude Code, Signing in (codes by e-mail and SMS, message
  texts), Mail (mail, outgoing mail), Access (accounts, certificates and TLS, firewall), Server (network,
  time, restart, system updates, SSH keys), Data (the database, backups, export and import), Updates.
- **The menu hides itself and has its pin** on a computer with a touch screen as well: it was only so where
  the browser said there was a mouse and nothing else (the list of terminals likewise).
- **The address of the database saved as otp saves it**: with Save, into `/etc/ai/config.json` - and only once
  that database opens and its tables are put right; it was refused before.

## 1.0.6

- **The database as otp's**: SQLite, **MariaDB or PostgreSQL**, on this machine or another. *Settings → The
  database* is otp's pane: fill the address in, **try it**, **set it up** (the database and an account with
  rights on it alone, its password made here; the server's administrator used once and kept nowhere),
  **carry everything across**, **start using it** - and back the same way. What is here is never touched by
  any of it. The address is the only setting kept in `/etc/ai/config.json` alone.
- **Dumps by the engine's own program** every night (SQLite's backup, `pg_dump`, `mariadb-dump`) and
  **portable copies** that go into any of the three; both downloaded with the key of their secrets locked with
  a passphrase (or without it), and put back from the list or from a file sent - read and shown first, a copy
  of what is replaced made before. The disk it is on and how fast it grows, every table, check it, give the
  disk back, forget old records, erase the collected data, and the database server tuned for its machine.
- **Otp's outgoing mail**: every mail is tried at once, and what the other side does not take yet
  (greylisting, a server away) is tried again by itself - a code while it is good; refused for good it is
  failed. Sent again or taken out by hand, searched by field, counted in a badge in the menu. A test mail
  goes straight (every step shown) or through it.
- **Otp's message texts designer**: the mail of a code is otp's HTML mail with its plain text part, edited as
  it arrives - bold, italic, colours, links, the parts filled in as blue chips - in Czech and English; the
  SMS beside a phone, counted in parts; previewed, sent as a sample, put back as it comes. The texts of 1.0.5
  are carried over.
- **Upgrades and Accounts as otp's**: this server, the web with the newer versions to choose from, a package
  dropped in and held until Upgrade, going back to a safe version with what changed, the upgrade with how far
  it is, what root said last; the accounts in otp's order.
- The installer: `--with-db mariadb|postgres` puts in the driver and the client tools beforehand (the engine in
  use gets them by itself on an upgrade), `--no-db-restart`.
- A second daemon that cannot have the port no longer writes its own token over the running one's.
- Going back is possible to 1.0.6 at the oldest: the tables changed.

## 1.0.5

- **The files of a chat** beside its terminal: its own folder and what is under it, never above it (the
  daemon refuses a path outside it); the right button hands a file to Claude (`@path`), opens, downloads,
  renames or deletes it; files dropped onto the list are uploaded there.
- **The right mouse button**, with a menu drawn as claude.ai draws one: on the terminal - copy, paste,
  select or copy the screen, a file for Claude, the chat's files, commands, clear the screen - and on a chat
  in the list (or its ⋯): open, open in a new window, pin, rename in its row, its files, a new Claude Code in
  its folder, the command to attach it, start it again, end it. tmux's own menu on that button is off.
- **Pinned chats** at the top of the list, kept with the account (wherever you sign in).
- **The list of terminals and the menu of settings hide themselves** at the edge of the screen as otp's do,
  slide out when pointed at, and stay out once pinned; not pinned is the default, as in otp.
- Signing out (or a sign-in ended by an administrator) closes that window's view of a terminal - never the
  terminal; **Sign out everywhere** under your name. Several sign-ins at once see the same terminals live.

## 1.0.4

What otp has and ai had not yet - taken over from otp 1.0.161, its code and its pages:

- **The second step of signing in**: an authenticator app (a QR code made here), a code by e-mail or by
  SMS; for everybody when switched on (`ai --admin-2fa on`), set up by each account at its first sign-in,
  reset from Accounts or with `ai --reset-2fa NAME`. Until it is given, a sign-in can do nothing else.
- **Secrets sealed** in the database with `/var/lib/ai/secrets.key`, as otp seals them.
- **Locked out**: the addresses and names counted after wrong passwords and codes, listed and cleared
  (Accounts; `ai --lockouts`, `ai --unlock`).
- **Mail**: SMTP or straight to the recipients' MX, a test with every step, the authorities of your own;
  notices of warnings and failures by mail.
- **SMS**: an HTTP gateway, a modem's spool or a Teltonika gateway, a test, its certificates.
- **Message texts** in Czech and English, edited on the pages; **Outgoing mail**: every mail and SMS sent.
- **Certificates and TLS** as otp's: PEM or PFX uploaded, a request (CSR) made here, self-signed; the chain
  sorted and checked; standard, intermediate, modern or custom TLS, DH parameters, HSTS
  (`ai --tls-import`, `--tls-preset`, `--tls-dh`, `--tls-hsts`).
- **The database**: a copy every night with its key, downloaded, put back (`ai --db-copy`, `--db-restore`).
- **Backups to other machines**: a folder, FTP, FTPS, SFTP, SCP, SMB; locked with a password, on a schedule,
  RESTORE.md beside each, put back from the pages or with `ai --restore-bundle`.
- **Export and import** of the whole configuration, with the secrets locked by a passphrase.
- **Going back to an older version** - only to a safe one (`ai --downgrade-check`, `ai --downgrade`).
- **About**: what the server runs on, Python to PHP's extensions.
- **The columns of every table** laid out per person (otp's cols.js); your own settings to a file and back.
- The PHP running the pages said when it may be without the php2shell fix.
- The settings rail grouped as otp's: Access, Messages, Server, Data, Updates.
- The console: the second step, the locked out, a reset, the copies, backups, export, a test mail, going back.
- install.sh puts in smbclient (samba-client) for backups to a share.

## 1.0.3 — 29 October 2026

**The command line and the console, as otp's**
- `ai --console`: otp's console, whole - the menus on a text screen, windows
  and forms, lists to scroll, the live log and the journal with grep as you
  type - with ai's menus: status and checks, terminals (opened right there in
  tmux, started, ended), accounts, settings, firewall and access, the server
  (network, time, updates, SSH keys, certificate, power), upgrades, the
  service. It opens by itself when root signs in (`ai --console-at-login
  on|off`); never inside a terminal of the pages.
- In colour, as otp's: colorama when it is there (install.sh installs
  python3-colorama), the same escape sequences by hand when it is not; every
  table and line coloured; `--help` in two columns; `--json` and `--no-color`.
- New commands: `--check`, `--open-web` (HTTP and HTTPS let in by firewalld,
  ufw or iptables), `--fw status|on|off`, `--fw-open PORT [--from CIDR]`,
  `--fw-del N`, `--pages-from`, `--change-keep`, `--change-back`, `--net`,
  `--ntp`, `--osup check|upgrade|status`, `--sshkeys`, `--sshkey-add`,
  `--cert`, `--reboot`, `--poweroff`, `--screen`, `--end`, `--restart-term`,
  `--again`, `--new … --shell|--continue|--pick|--model`, `--del-user`,
  `--disable-user`, `--enable-user`, `--set-role`, `--set-run-as`,
  `--end-sign-ins`, `--sign-ins`, `--log`, `--set KEY=VALUE`,
  `--upgrade-status`.

## 1.0.2 — 29 October 2026

**install.sh gone through against otp's, line by line**
- The first account: a password given is neither printed at the end nor said
  to be changed; one made by the installer is printed and has to be changed at
  the first sign-in (it did not have to).
- Who may reach the pages is checked before anything is installed, and the
  address you are signed in from over SSH, if it is not among them, is offered
  to be added - not shut out of the pages you just installed.
- php-fpm is reloaded, not restarted - the other PHP sites of the machine go
  on - and started when it was not running.
- Python 3.9 or newer is checked; a command that fails says on which line.
- Debian and Ubuntu get the SSH client only, not an SSH server.
- `--rewrite-nginx` keeps the file there before in /etc/nginx/ai-backups/
  (the last ten).
- At the end, the pages' address by IP too, for until the name is in DNS.
- Without `SSH_CLIENT` (installed from the console) it stopped at once.

## 1.0.1 — 29 October 2026

**install.sh asks, as otp's does**
- A fresh install asks *A few questions* before it does anything, Enter keeping
  what is in brackets: the pages' hostname (FQDN), who may reach the pages, the
  first account and its password (typed twice, unseen; empty = one made and
  printed), the Linux account the terminals run as (made when it is not there),
  and whether to install Claude Code for root. The hostname was taken from the
  machine without asking. `--yes` takes what is in brackets, as before.
- A setting changed on the command line (`ai --setting`) is taken by the
  running daemon within a minute.

## 1.0.0 — 29 October 2026

**The first version: Claude Code on the server, from the browser**
- Terminals of Claude Code and shells in tmux, one tmux server per Linux
  account in a systemd scope of its own: closing the browser, losing the
  connection or restarting ai ends none of them. xterm.js on a WebSocket,
  reconnected by itself; several windows on one terminal; the last screen of
  one that ended kept; started again, ended, renamed, opened in a window of
  its own; `ai --attach` on the server.
- The whole keyboard: Ctrl and Alt combinations, arrows, F1-F12, Shift+Enter
  for a new line, copy and paste, and *All keys* (Keyboard Lock) for the keys
  a browser keeps; Ctrl, Alt and the special keys on screen for a phone;
  Claude Code's commands from a list; a box for long text.
- Files: a browser of the server's files with upload (button, drag and drop,
  Ctrl+V), download (folders as .zip), text files edited, pictures shown; files
  and pictures dropped or pasted into a terminal handed to Claude.
- Conversations: every one Claude Code kept, by folder, resumed in a new
  terminal.
- Claude Code installed, updated and checked for each Linux account from the
  pages; the model, the permission mode and more words per terminal.
- Accounts: administrators and users, each with the Linux account its
  terminals run as and the folders of its files; Linux accounts made here.
- The server, as otp 1.0.161 draws it: firewall and who may reach the pages,
  network, time, system updates, root's SSH keys, restart and power off;
  certificate and TLS; changes that could cut you off taken back unless kept.
- New versions signed (Ed25519), from GitHub or sent from the pages, put in by
  hand or by themselves; the last ten in release/.
- Czech and English.
