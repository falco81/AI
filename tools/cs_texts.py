# -*- coding: utf-8 -*-
"""The Czech of ai's pages: English as the code writes it -> Czech.

tools/lang.py turns this (and the words otp's pages share with these, taken
from otp's own cs.json) into web/lang/cs.json. STRINGS are whole pieces of
text, PATTERNS have {0}, {1} where the page puts a name or a number, RICH are
sentences with <b> in them, swapped whole.
"""

STRINGS = {
    # ---- the sign-in -------------------------------------------------------
    'Claude Code on': 'Claude Code na',
    'Sign in to go on.': 'Pokračujte přihlášením.',
    'CLAUDE CODE': 'CLAUDE CODE',
    'THE SERVER': 'SERVER',
    'IN THE BROWSER · NOTHING ENDS WHEN IT CLOSES': 'V PROHLÍŽEČI · ZAVŘENÍM NIC NEKONČÍ',
    'What this program does': 'Co tento program dělá',
    'The daemon is not answering. Nobody can sign in until': 'Démon neodpovídá. Nikdo se nepřihlásí, dokud neběží',
    'is running:': ':',
    'There is no account on this machine yet. Make one on the server:': 'Na tomto stroji zatím není žádný účet. Založte ho na serveru:',
    'The daemon is running, but this page may not read what it wrote.': 'Démon běží, ale tato stránka nesmí číst, co zapsal.',
    'exists and is not readable by': 'existuje a nemůže ho číst',
    ', which is what this page runs as.': ', pod kterým tato stránka běží.',
    'On the server:': 'Na serveru:',
    'Signing in…': 'Přihlašuji…',
    'Welcome back.': 'Vítejte zpět.',

    # ---- the header and the tabs --------------------------------------------
    'The account you are signed in as: its password, the language of these pages, the letters of the terminal.':
        'Účet, pod kterým jste přihlášeni: jeho heslo, jazyk těchto stránek, velikost písma terminálu.',
    'running': 'běží',
    'running, with trouble': 'běží, s potížemi',
    'being upgraded': 'probíhá upgrade',
    'Terminals': 'Terminály',
    'Claude Code and shells running on this server: open one, start a new one. Each goes on running when the browser is closed.':
        'Claude Code a shelly běžící na tomto serveru: otevřete některý, nebo spusťte nový. Každý běží dál i po zavření prohlížeče.',
    'Files': 'Soubory',
    'The files of the server: look, fetch, send, drop them in; a text file opened and edited here.':
        'Soubory serveru: prohlížet, stahovat, nahrávat, přetáhnout sem; textový soubor otevřít a upravit přímo zde.',
    'Conversations': 'Konverzace',
    'Every conversation Claude Code has kept, folder by folder - picked up again where it was left.':
        'Každá konverzace, kterou si Claude Code uložil, složku po složce – navázat lze tam, kde skončila.',
    'Overview': 'Přehled',
    'The server at a glance: what it is, how busy, its disks, its addresses, who is signed in.':
        'Server na první pohled: co to je, jak je vytížený, jeho disky, adresy a kdo je přihlášen.',
    'Events': 'Události',
    'Every sign-in, every terminal started or ended, every change of a setting and of the machine.':
        'Každé přihlášení, každý spuštěný či ukončený terminál, každá změna nastavení a stroje.',
    'Settings': 'Nastavení',
    'Claude Code, the accounts, the certificate, the firewall, the network, the time, the system\'s updates, SSH keys and new versions of this program.':
        'Claude Code, účty, certifikát, firewall, síť, čas, aktualizace systému, SSH klíče a nové verze tohoto programu.',

    # ---- the terminals -------------------------------------------------------
    'New': 'Nový',
    'A new terminal: Claude Code or a shell, in the folder you choose.': 'Nový terminál: Claude Code nebo shell, ve složce, kterou zvolíte.',
    'find a terminal…': 'najít terminál…',
    'Which terminals the list shows.': 'Které terminály seznam ukazuje.',
    'with the ended ones': 'i s ukončenými',
    'Claude Code on this server': 'Claude Code na tomto serveru',
    'Start one in a folder, and it goes on running on the server until it is ended here - close the browser, lose the connection, come back from another computer: it is where you left it. Files dropped or pasted into the terminal (Ctrl+V) are handed to Claude.':
        'Spusťte ho v některé složce a poběží na serveru, dokud ho tady neukončíte – zavřete prohlížeč, ztratíte spojení, vrátíte se z jiného počítače: najdete ho tam, kde jste ho nechali. Soubory přetažené nebo vložené do terminálu (Ctrl+V) dostane Claude.',
    'New Claude Code': 'Nový Claude Code',
    'New shell': 'Nový shell',
    'Pick up a conversation': 'Navázat na konverzaci',
    'Show or hide the list of terminals.': 'Ukázat nebo skrýt seznam terminálů.',
    'Commands': 'Příkazy',
    'Claude Code\'s commands - /model, /compact, /resume... - put into the terminal, ready to be sent.':
        'Příkazy Claude Code – /model, /compact, /resume… – vložené do terminálu, připravené k odeslání.',
    'File for Claude': 'Soubor pro Claude',
    'Give Claude a file: it is written into the working directory\'s upload folder and its path typed into the terminal. Dropping a file onto the terminal, or pasting one (Ctrl+V), does the same.':
        'Předat Claude soubor: uloží se do složky pro nahrané soubory v pracovním adresáři a jeho cesta se napíše do terminálu. Totéž udělá přetažení souboru na terminál nebo jeho vložení (Ctrl+V).',
    'The files of this terminal\'s working directory.': 'Soubory pracovního adresáře tohoto terminálu.',
    'Write': 'Psát',
    'A box to write longer text in, sent to the terminal at once - handy on a phone, or for many lines.':
        'Pole pro delší text, odeslaný do terminálu najednou – hodí se na telefonu nebo pro víc řádků.',
    'Smaller letters': 'Menší písmo',
    'Bigger letters': 'Větší písmo',
    'The terminal over the whole window (Esc twice, or this again, to come back).': 'Terminál přes celé okno (zpět dvakrát Esc, nebo znovu toto tlačítko).',
    'More': 'Další',
    'Rename it, start it again, end it, open it in a window of its own.': 'Přejmenovat, spustit znovu, ukončit, otevřít ve vlastním okně.',
    'Drop the file to give it to Claude': 'Pusťte soubor a Claude ho dostane',
    'Write here - Ctrl+Enter sends it, with Enter after it': 'Pište sem – Ctrl+Enter odešle text i s Enterem',
    'Send': 'Odeslat',
    'Put the text into the terminal and press Enter (Ctrl+Enter).': 'Vložit text do terminálu a stisknout Enter (Ctrl+Enter).',
    'Only put it in': 'Jen vložit',
    'Put the text into the terminal without pressing Enter.': 'Vložit text do terminálu bez stisku Enteru.',
    'Claude Code in a folder used lately': 'Claude Code v nedávno použité složce',
    'Running': 'Běží',
    'No terminal yet. Press New.': 'Zatím žádný terminál. Stiskněte Nový.',
    'Nothing matches.': 'Nic tomu neodpovídá.',
    'open': 'otevřený',
    'ended': 'ukončený',
    'Claude Code': 'Claude Code',
    'shell': 'shell',
    'command': 'příkaz',
    'connecting…': 'připojuji…',
    'live': 'živě',
    'paused': 'pozastaveno',
    'it has ended': 'skončil',
    'This terminal has ended.': 'Tento terminál skončil.',
    'Back to the list': 'Zpět na seznam',
    'Close it': 'Zavřít ho',
    'Start it again': 'Spustit znovu',
    'Take it off the list': 'Odebrat ze seznamu',
    '(nothing was kept of its screen)': '(z jeho obrazovky se nic neuchovalo)',
    'Folder': 'Složka',
    'Ran as': 'Běžel jako',
    'Started': 'Spuštěn',
    'Ended': 'Ukončen',
    'Kind': 'Druh',
    'Now in': 'Teď v',
    'Runs as': 'Běží jako',
    'Started by': 'Spustil',
    'Windows looking at it': 'Oken, která ho sledují',
    'Running now': 'Právě běží',
    'On the server': 'Na serveru',
    'Its name': 'Jeho název',
    'Rename': 'Přejmenovat',
    'End it': 'Ukončit ho',
    'In a window of its own': 'Ve vlastním okně',
    'the connection dropped - again in': 'spojení se přerušilo – znovu za',
    'the terminal is not connected': 'terminál není připojený',
    'copied': 'zkopírováno',

    # the new terminal
    'A new terminal': 'Nový terminál',
    'A shell': 'Shell',
    'The working directory': 'Pracovní adresář',
    'the home folder': 'domovská složka',
    'Choose…': 'Vybrat…',
    'Where it starts. It is made if it is not there yet and the box below says so.': 'Kde začne. Pokud ještě neexistuje a přepínač níže to říká, vytvoří se.',
    'Make it if it is not there': 'Vytvořit, pokud neexistuje',
    'from the folder': 'podle složky',
    'Runs as (Linux account)': 'Běží jako (účet Linuxu)',
    'Whose files it may change, whose Claude Code sign-in it uses.': 'Čí soubory smí měnit a čí přihlášení ke Claude Code používá.',
    'Start with': 'Začít',
    'a new conversation': 'novou konverzací',
    'the last conversation of this folder (--continue)': 'poslední konverzací této složky (--continue)',
    'choose one of its conversations (--resume)': 'výběrem z jejích konverzací (--resume)',
    'Model': 'Model',
    'as Claude Code chooses': 'jak zvolí Claude Code',
    'Opus to plan, Sonnet to do': 'Opus plánuje, Sonnet provádí',
    'Permissions': 'Oprávnění',
    'ask before changes (default)': 'ptát se před změnami (výchozí)',
    'accept edits by itself': 'úpravy přijímat samo',
    'plan only': 'jen plánovat',
    'never ask (bypass permissions)': 'nikdy se neptat (bypass permissions)',
    'Never ask is refused by Claude Code when it runs as root.': 'Claude Code odmítne „nikdy se neptat“, když běží jako root.',
    'More words for its command line': 'Další parametry příkazové řádky',
    'Start it': 'Spustit',
    'Choose a folder': 'Vyberte složku',
    'Choose this one': 'Vybrat tuto',
    'No folders in it.': 'Nejsou v ní žádné složky.',
    'The name of the new folder': 'Název nové složky',
    'The name of the new file': 'Název nového souboru',

    # keys and commands
    'Escape: stops Claude in the middle of what it is doing, closes a menu.': 'Escape: zastaví Claude uprostřed práce, zavře nabídku.',
    'Twice Escape: Claude Code goes back to an earlier message (rewind).': 'Dvakrát Escape: Claude Code se vrátí k dřívější zprávě (rewind).',
    'Tab: completes a path or a command.': 'Tab: doplní cestu nebo příkaz.',
    'Shift+Tab: switches Claude Code\'s mode - asking, accepting edits, planning.': 'Shift+Tab: přepíná režim Claude Code – ptát se, přijímat úpravy, plánovat.',
    'Up': 'Nahoru', 'Down': 'Dolů', 'Left': 'Vlevo', 'Right': 'Vpravo',
    'A new line in what you are writing, without sending it (\\ and Enter).': 'Nový řádek v psaném textu, bez odeslání (\\ a Enter).',
    'Ctrl+C: stops what runs; twice, Claude Code ends.': 'Ctrl+C: zastaví, co běží; dvakrát ukončí Claude Code.',
    'Ctrl+D: the end of input; ends a shell.': 'Ctrl+D: konec vstupu; ukončí shell.',
    'Ctrl+R: searches back through what was typed.': 'Ctrl+R: hledá zpětně v napsaném.',
    'Ctrl+O: Claude Code shows everything it did, in detail.': 'Ctrl+O: Claude Code ukáže podrobně vše, co udělal.',
    'Ctrl+T: Claude Code\'s list of tasks.': 'Ctrl+T: seznam úkolů Claude Code.',
    'Ctrl+L: clears the screen.': 'Ctrl+L: vymaže obrazovku.',
    'Scrolls back through the terminal (tmux): arrows and Page Up/Down, q to come back. The mouse wheel does the same.':
        'Listování historií terminálu (tmux): šipky a Page Up/Down, q pro návrat. Totéž dělá kolečko myši.',
    'Claude Code\'s commands': 'Příkazy Claude Code',
    'Pressed, a command is typed into the terminal and sent. Anything you have written there yet goes with it. Typing / in the terminal shows the same list - and the commands of your own (.claude/commands).':
        'Po stisknutí se příkaz napíše do terminálu a odešle. Co už tam máte napsané, odejde s ním. Napsáním / v terminálu se ukáže tentýž seznam – i s vašimi vlastními příkazy (.claude/commands).',
    'Only type it, do not send it': 'Jen napsat, neodesílat',
    'find…': 'hledat…',
    'what Claude Code can do, and its keys': 'co Claude Code umí a jeho klávesy',
    'a new conversation, the old one kept': 'nová konverzace, stará zůstane',
    'the conversation shortened into a summary, to go on with less': 'konverzace zkrácená do shrnutí, aby se pokračovalo s menším kontextem',
    'go back to an earlier conversation of this folder': 'návrat k dřívější konverzaci této složky',
    'choose the model': 'volba modelu',
    'how full the context is': 'jak plný je kontext',
    'what this conversation has cost': 'kolik tato konverzace stála',
    'how much of the plan is used': 'kolik z předplatného je vyčerpáno',
    'version, account, model, connections': 'verze, účet, model, připojení',
    'Claude Code\'s settings': 'nastavení Claude Code',
    'what it may do without asking': 'co smí dělat bez ptaní',
    'CLAUDE.md, its memory files': 'CLAUDE.md, soubory jeho paměti',
    'a CLAUDE.md written for this project': 'CLAUDE.md napsaný pro tento projekt',
    'a review of a pull request': 'revize pull requestu',
    'a security review of the changes': 'bezpečnostní revize změn',
    'its subagents': 'jeho subagenti',
    'the MCP servers': 'MCP servery',
    'the hooks': 'hooky',
    'plugins': 'pluginy',
    'another folder it may work in': 'další složka, ve které smí pracovat',
    'the conversation into a file or the clipboard': 'konverzace do souboru nebo schránky',
    'back to an earlier point of the conversation': 'návrat k dřívějšímu bodu konverzace',
    'its list of tasks': 'jeho seznam úkolů',
    'the shells it runs in the background': 'shelly, které spouští na pozadí',
    'vim keys in its input': 'klávesy vim v jeho vstupu',
    'how it writes': 'jak píše',
    'its status line': 'jeho stavový řádek',
    'Shift+Enter for new lines': 'Shift+Enter pro nové řádky',
    'checks its installation': 'zkontroluje svou instalaci',
    'sign in to a Claude account': 'přihlášení k účtu Claude',
    'sign out': 'odhlášení',
    'what is new in it': 'co je v něm nového',
    'tell Anthropic about a problem': 'nahlásit problém společnosti Anthropic',
    'end Claude Code': 'ukončit Claude Code',

    # ---- the files ---------------------------------------------------------------
    'One folder up.': 'O složku výš.',
    'The folder shown. Type another and press Enter.': 'Zobrazená složka. Napište jinou a stiskněte Enter.',
    'The folders this account may use, and the ones you keep (the star).': 'Složky, které tento účet smí používat, a ty, které si držíte (hvězdička).',
    'go to…': 'přejít na…',
    'Keep this folder in the list beside, to come back to it at once.': 'Držet tuto složku v seznamu vedle, abyste se k ní hned vrátili.',
    'hidden files': 'skryté soubory',
    'New folder': 'Nová složka',
    'New file': 'Nový soubor',
    'Send files': 'Nahrát soubory',
    'Send files from this computer into this folder. Dropping them onto the list, or pasting them (Ctrl+V), does the same.':
        'Nahrát soubory z tohoto počítače do této složky. Totéž udělá jejich přetažení na seznam nebo vložení (Ctrl+V).',
    'Claude here': 'Claude zde',
    'A new Claude Code terminal in this folder.': 'Nový terminál Claude Code v této složce.',
    'Drop the files to send them into this folder': 'Pusťte soubory a nahrají se do této složky',
    'Name': 'Název',
    'Size': 'Velikost',
    'Changed': 'Změněno',
    'Owner': 'Vlastník',
    'Rights': 'Práva',
    'An empty folder': 'Prázdná složka',
    'Download it': 'Stáhnout',
    'Download it as a .zip': 'Stáhnout jako .zip',
    'Rename it': 'Přejmenovat',
    'Take it away': 'Odstranit',
    'Delete it': 'Smazat',
    'Save it': 'Uložit',
    'saved': 'uloženo',
    'no longer kept': 'už se nedrží',
    'kept in the list': 'drží se v seznamu',

    # ---- the conversations ----------------------------------------------------------
    'What Claude Code keeps of every conversation (~/.claude/projects), newest first. Pick one up again: a new terminal opens in its folder with':
        'Co si Claude Code uchovává z každé konverzace (~/.claude/projects), nejnovější nahoře. Navažte na ni: ve její složce se otevře nový terminál s',
    ', and the conversation goes on where it stopped.': 'a konverzace pokračuje tam, kde skončila.',
    'words of it, a folder…': 'slova z ní, složka…',
    'Whose conversations: the Linux account Claude Code ran as.': 'Čí konverzace: účet Linuxu, pod kterým Claude Code běžel.',
    'Only those of one folder.': 'Jen ty z jedné složky.',
    'every folder': 'všechny složky',
    'When': 'Kdy',
    'What it was about': 'O čem byla',
    'Messages': 'Zpráv',
    'Pick it up': 'Navázat',
    'No conversation of Claude Code here yet': 'Zatím tu není žádná konverzace Claude Code',
    'reading…': 'čtu…',

    # ---- the overview ---------------------------------------------------------------------
    'Terminals running': 'Běžící terminály',
    'Load': 'Zátěž',
    'Memory': 'Paměť',
    'Disk': 'Disk',
    'This server': 'Tento server',
    'Version': 'Verze',
    'System updates': 'Aktualizace systému',
    'Certificate': 'Certifikát',
    'The machine': 'Stroj',
    'Signed in now': 'Právě přihlášení',
    'Lately': 'Poslední dění',
    'System': 'Systém',
    'Addresses': 'Adresy',
    'Disks': 'Disky',
    'Swap': 'Swap',
    'Software': 'Software',
    'Who': 'Kdo',
    'From': 'Odkud',
    'Last': 'Naposledy',
    'What': 'Co',
    'the newest known': 'nejnovější známá',
    'not looked at yet': 'zatím nezjišťováno',
    'self-signed': 'podepsaný sám sebou',
    'Nothing yet': 'Zatím nic',

    # ---- the events --------------------------------------------------------------
    'a name, an address, a word…': 'jméno, adresa, slovo…',
    'every kind': 'všechny druhy',

    # ---- the settings: the rail ----------------------------------------------------------
    'Claude Code itself: installed for which accounts, signed in or not, updated; how every terminal starts it.':
        'Claude Code samotný: pro které účty je nainstalovaný, zda je přihlášený, aktualizace; jak ho každý terminál spouští.',
    'Access': 'Přístup',
    'Accounts': 'Účty',
    'Who may sign in to these pages, what each may do, which Linux account their terminals run as, and who is signed in right now.':
        'Kdo se smí přihlásit k těmto stránkám, co kdo smí, pod jakým účtem Linuxu běží jeho terminály a kdo je právě přihlášen.',
    'Signing in': 'Přihlašování',
    'How long a sign-in lasts, wrong passwords, and changes that go back by themselves unless kept.':
        'Jak dlouho přihlášení vydrží, chybná hesla a změny, které se samy vrátí, pokud se nepotvrdí.',
    'Certificate and TLS': 'Certifikát a TLS',
    'The certificate of these pages: given, or made here.': 'Certifikát těchto stránek: dodaný, nebo vytvořený zde.',
    'Firewall and access': 'Firewall a přístup',
    'Who may reach these pages, and the server\'s firewall (iptables or firewalld).': 'Kdo smí na tyto stránky a firewall serveru (iptables nebo firewalld).',
    'Server': 'Server',
    'Network': 'Síť',
    'The server\'s address, gateway, DNS servers and host name.': 'Adresa serveru, brána, DNS servery a název stroje.',
    'Time': 'Čas',
    'The clock: its time zone and time servers (chrony).': 'Hodiny: časové pásmo a časové servery (chrony).',
    'The operating system\'s packages, looked at and updated, its output shown as it goes.': 'Balíčky operačního systému – zjistit a aktualizovat, s výpisem průběžně na obrazovce.',
    'SSH keys': 'SSH klíče',
    'The keys that may sign in over SSH, to root or another account: made here, added or taken away.': 'Klíče, které se smí přihlásit přes SSH, k rootovi či jinému účtu: vytvořit zde, přidat, odebrat.',
    'Restart and power off': 'Restart a vypnutí',
    'Restart or switch off the server, or only its services.': 'Restartovat nebo vypnout server, nebo jen jeho služby.',
    'This program': 'Tento program',
    'Upgrades': 'Upgrady',
    'New versions of ai: from the web by themselves, or sent here.': 'Nové verze ai: z webu samy, nebo nahrané sem.',
    'About': 'O programu',
    'Version, the name of the pages, the language, what is running, the log.': 'Verze, název stránek, jazyk, co běží, log.',
    'Find a setting…': 'Najít nastavení…',
    'Nothing by that name': 'Nic takového',
    'Save the changes': 'Uložit změny',
    'Save the changed settings. They take effect the moment they are saved - nothing restarts.': 'Uložit změněná nastavení. Platí okamžikem uložení – nic se nerestartuje.',
    'Put them back': 'Vrátit je',
    'Throw away the changes on this page and read the settings back as they are.': 'Zahodit změny na této stránce a načíst nastavení znovu, jak jsou.',
    'back to the default': 'zpět na výchozí',

    # ---- Claude Code pane ----------------------------------------------------------------
    'Claude Code is installed for each Linux account the terminals run as - root\'s is root\'s, another account\'s its own. Signing in to Claude (a Claude account or an API key) is done once per account, in a terminal:':
        'Claude Code se instaluje pro každý účet Linuxu, pod kterým terminály běží – rootův patří rootovi, jiný účet má svůj. Přihlášení ke Claude (účet Claude nebo API klíč) se dělá jednou pro každý účet, v terminálu:',
    'asks by itself the first time, or': 'se poprvé zeptá sám, nebo',
    'The accounts': 'Účty',
    'Look again': 'Zjistit znovu',
    'Linux account': 'Účet Linuxu',
    'Signed in': 'Přihlášen',
    'Node.js': 'Node.js',
    'not installed': 'nenainstalován',
    'yes': 'ano',
    'not yet': 'zatím ne',
    'API key': 'API klíč',
    'Install it': 'Nainstalovat',
    'With npm': 'Přes npm',
    'Update it': 'Aktualizovat',
    'Check it': 'Zkontrolovat',
    'Sign in': 'Přihlásit',
    'claude update, in a terminal you watch.': 'claude update, v terminálu, který sledujete.',
    'claude doctor: what is wrong with the installation, if anything.': 'claude doctor: co je s instalací v nepořádku, pokud vůbec něco.',
    'Claude Code in a terminal of its own: it asks how to sign in the first time; or type /login.': 'Claude Code ve vlastním terminálu: poprvé se sám zeptá, jak se přihlásit; nebo napište /login.',
    'The command that starts Claude Code': 'Příkaz, který spouští Claude Code',
    'Looked up on the PATH of the account a terminal runs as (its login shell, so ~/.local/bin counts), or a full path.':
        'Hledá se v PATH účtu, pod kterým terminál běží (jeho login shell, takže se počítá i ~/.local/bin), nebo celá cesta.',
    'Always started with': 'Vždy spouštět s',
    'Words added to every start of Claude Code, as on its command line - for example --model opus. Each new terminal can add its own.':
        'Parametry přidané ke každému spuštění Claude Code, jako na jeho příkazové řádce – třeba --model opus. Každý nový terminál může přidat své.',
    'Environment of every terminal': 'Prostředí každého terminálu',
    'One NAME=value a line, set in every terminal started from here (an API key, a proxy, DISABLE_AUTOUPDATER=1...). Lines starting with # are ignored.':
        'Jedno JMÉNO=hodnota na řádek, nastavené v každém terminálu spuštěném odsud (API klíč, proxy, DISABLE_AUTOUPDATER=1…). Řádky začínající # se ignorují.',
    'Language and characters of the terminals': 'Jazyk a znaky terminálů',
    'LANG of every terminal. A UTF-8 one is needed for Claude Code to draw itself.': 'LANG každého terminálu. Aby se Claude Code správně vykreslil, musí být UTF-8.',
    'Runs as, unless the account says otherwise': 'Běží jako, pokud účet neříká jinak',
    'The Linux account a terminal runs as for an account that has none of its own.': 'Účet Linuxu, pod kterým běží terminál účtu, který žádný vlastní nemá.',
    'Working directory offered first': 'Nabízený pracovní adresář',
    'The directory a new terminal starts in, unless one is chosen. Empty: the home directory of the account it runs as.':
        'Adresář, ve kterém nový terminál začne, pokud se nezvolí jiný. Prázdné: domovský adresář účtu, pod kterým běží.',
    'Where files given to Claude go': 'Kam jdou soubory předané Claude',
    'A file dropped or pasted into a terminal is written here - a folder inside the working directory, or a full path - and its path typed into the terminal. It gets a .gitignore of its own, so git leaves it alone.':
        'Soubor přetažený nebo vložený do terminálu se uloží sem – složka uvnitř pracovního adresáře, nebo celá cesta – a jeho cesta se napíše do terminálu. Dostane vlastní .gitignore, takže ho git nechá být.',
    'Largest file taken (MB)': 'Největší přijatý soubor (MB)',
    'A file sent from the browser, to the working directory or to Claude.': 'Soubor nahraný z prohlížeče, do pracovního adresáře nebo pro Claude.',
    'Ended terminals kept (days)': 'Ukončené terminály držet (dní)',
    'How long a terminal that has ended stays in the list, to look at its last screen.': 'Jak dlouho zůstane ukončený terminál v seznamu, aby šla zobrazit jeho poslední obrazovka.',

    # ---- accounts ----------------------------------------------------------------
    'Make an account': 'Založit účet',
    'Role': 'Role',
    'Terminals run as': 'Terminály běží jako',
    'Files in': 'Soubory v',
    'Last sign-in': 'Poslední přihlášení',
    'administrator': 'administrátor',
    'user': 'uživatel',
    'everywhere': 'všude',
    'never': 'nikdy',
    'off': 'vypnutý',
    'to choose a password': 'má si zvolit heslo',
    'Since': 'Od',
    'Browser': 'Prohlížeč',
    'you': 'vy',
    'End this sign-in': 'Ukončit toto přihlášení',
    'A new account': 'Nový účet',
    'Make it': 'Vytvořit',
    'user - terminals of their own, files in their folders': 'uživatel – vlastní terminály, soubory ve svých složkách',
    'administrator - everything': 'administrátor – vše',
    'Terminals run as (Linux account)': 'Terminály běží jako (účet Linuxu)',
    'Whoever signs in here is this account on the server: its files, its rights, its Claude Code sign-in.': 'Kdo se tu přihlásí, je na serveru tímto účtem: jeho soubory, jeho práva, jeho přihlášení ke Claude Code.',
    'Folders for files (a user)': 'Složky pro soubory (uživatel)',
    'One a line. Empty: the home folder of the Linux account. An administrator may use every folder.': 'Jedna na řádek. Prázdné: domovská složka účtu Linuxu. Administrátor smí používat všechny složky.',
    'A note': 'Poznámka',
    'Password': 'Heslo',
    'made and shown, if empty': 'pokud prázdné, vytvoří se a ukáže',
    'Make a new Linux account by this name': 'Založit nový účet Linuxu s tímto názvem',
    'Its name (small letters)': 'Jeho název (malá písmena)',
    'It may use sudo (wheel / sudo group)': 'Smí používat sudo (skupina wheel / sudo)',
    'Switched off - may not sign in': 'Vypnutý – nesmí se přihlásit',
    'A new password': 'Nové heslo',
    'Shown this once. It has to be changed at the first sign-in.': 'Ukazuje se jen teď. Při prvním přihlášení se musí změnit.',
    'the password was copied': 'heslo bylo zkopírováno',

    # the account menu
    'Language of the pages': 'Jazyk stránek',
    'Size of the terminal\'s letters': 'Velikost písma terminálu',
    'The present one': 'Současné',
    'The one you were given': 'To, které jste dostali',
    'A new one (at least 10 characters)': 'Nové (alespoň 10 znaků)',
    'The new one again': 'Nové ještě jednou',
    'Change the password': 'Změnit heslo',
    'First choose a password of your own': 'Nejdřív si zvolte vlastní heslo',
    'This account was given its password by somebody else. Before anything else, choose one that only you know.':
        'Tento účet dostal heslo od někoho jiného. Než cokoli dalšího, zvolte si takové, které znáte jen vy.',
    'the two new ones are not the same': 'obě nová hesla nejsou stejná',
    'the password is changed': 'heslo je změněno',

    # ---- certificate ----------------------------------------------------------------
    'The certificate nginx shows for these pages. install.sh made a self-signed one; put in your own (with its chain), or make a new self-signed one for other names. nginx checks it before it takes it - one it does not take is never put in.':
        'Certifikát, který nginx ukazuje pro tyto stránky. install.sh vytvořil certifikát podepsaný sám sebou; vložte vlastní (s řetězcem), nebo vytvořte nový pro jiná jména. nginx ho před přijetím zkontroluje – takový, který nepřijme, se nikdy nenasadí.',
    'Now': 'Teď',
    'Your own certificate': 'Vlastní certifikát',
    'The certificate (PEM), with its chain after it': 'Certifikát (PEM), za ním jeho řetězec',
    'Its private key (PEM, not locked)': 'Jeho privátní klíč (PEM, nezamčený)',
    'Put it in': 'Nasadit',
    'Read files…': 'Načíst soubory…',
    'A new self-signed one': 'Nový podepsaný sám sebou',
    'For the names (and addresses)': 'Pro jména (a adresy)',
    'Valid for (days)': 'Platný (dní)',
    'There is no certificate at the place nginx reads it from.': 'V místě, odkud ho nginx čte, není žádný certifikát.',
    'For': 'Pro',
    'Names': 'Jména',
    'By': 'Vydal',
    'Valid': 'Platnost',
    'File': 'Soubor',
    'A new self-signed certificate?': 'Nový certifikát podepsaný sám sebou?',
    'The browsers warn about it again until it is trusted.': 'Prohlížeče budou znovu varovat, dokud mu nebudou důvěřovat.',
    'the certificate is in': 'certifikát je nasazen',
    'a new certificate is in': 'nový certifikát je nasazen',

    # ---- firewall -------------------------------------------------------------------
    'Who may reach these pages': 'Kdo smí na tyto stránky',
    'nginx\'s own list, before anything is asked: everybody, or only these networks (this machine always may).':
        'Vlastní seznam nginx, ještě než se na cokoli zeptá: všichni, nebo jen tyto sítě (tento stroj smí vždy).',
    'The firewall': 'Firewall',
    'What the machine has now': 'Co má stroj teď',
    'Everybody may': 'Smí všichni',
    'Only these networks (one a line)': 'Jen tyto sítě (jedna na řádek)',
    'The rules below are in force': 'Pravidla níže platí',
    'SSH (22) always open': 'SSH (22) vždy otevřené',
    'These pages (80, 443) always open': 'Tyto stránky (80, 443) vždy otevřené',
    'Whatever no rule names is': 'Co žádné pravidlo nejmenuje, se',
    'let in': 'pustí',
    'dropped': 'zahodí',
    'Dropped: only what the rules let in comes in.': 'Zahodí: dovnitř projde jen to, co pravidla pustí.',
    'firewalld refuses it anyway.': 'firewalld to odmítne tak jako tak.',
    'firewalld runs here: the rules below are put in as rich rules of its default zone; what the zone itself allows stays as it is.':
        'Zde běží firewalld: pravidla níže se vloží jako rich rules jeho výchozí zóny; co povoluje zóna sama, zůstává, jak je.',
    'ufw manages this server\'s firewall. Change it with ufw, or switch it off (ufw disable) to manage it here.':
        'Firewall tohoto serveru spravuje ufw. Měňte ho přes ufw, nebo ho vypněte (ufw disable) a spravujte zde.',
    'Protocol': 'Protokol',
    'Port': 'Port',
    'Family': 'Rodina',
    'Note': 'Poznámka',
    'drop': 'zahodit',
    'refuse': 'odmítnout',
    'any': 'jakýkoli',
    'both': 'obě',
    'anywhere': 'odkudkoli',
    '443 or 8000-8100': '443 nebo 8000-8100',
    'No rule of your own': 'Žádné vlastní pravidlo',
    'Add a rule': 'Přidat pravidlo',
    'Take this rule away': 'Odebrat toto pravidlo',
    'a test machine': 'testovací stroj',
    'none': 'žádný',

    # changes on trial
    'Keep it': 'Ponechat',
    'Put the old back now': 'Vrátit staré hned',
    'Put the old back now?': 'Vrátit staré hned?',
    'Put it back': 'Vrátit',
    'What was there before the change comes back at once.': 'Co bylo před změnou, se hned vrátí.',
    'The new network waits to be kept': 'Nová síť čeká na potvrzení',
    'The new firewall waits to be kept': 'Nový firewall čeká na potvrzení',
    'Who may reach the pages waits to be kept': 'Kdo smí na stránky – čeká na potvrzení',
    'Not kept, the server goes back to its old network by itself. Keep it once the pages answer at the new address.':
        'Bez potvrzení se server sám vrátí ke staré síti. Potvrďte, jakmile stránky odpovídají na nové adrese.',
    'Not kept, the rules as they were before come back by themselves. Keep it once SSH and these pages still answer.':
        'Bez potvrzení se samy vrátí pravidla, jak byla předtím. Potvrďte, jakmile SSH i tyto stránky stále odpovídají.',
    'Not kept, the list as it was before comes back by itself. Keep it once the pages still answer from where you are.':
        'Bez potvrzení se sám vrátí seznam, jak byl předtím. Potvrďte, jakmile stránky odpovídají i odtud, kde jste.',
    'going back now': 'právě se vrací',
    'kept': 'ponecháno',
    'put back': 'vráceno',

    # ---- network ---------------------------------------------------------------------
    'Change it': 'Změnit',
    'Host name': 'Název stroje',
    'Gateway': 'Brána',
    'DNS': 'DNS',
    'The connection': 'Připojení',
    'IPv4': 'IPv4',
    'set here': 'nastavená zde',
    'from DHCP': 'z DHCP',
    'Addresses with their prefix': 'Adresy s prefixem',
    'DNS servers': 'DNS servery',
    'Search domains': 'Prohledávané domény',
    'IPv6': 'IPv6',
    'automatic': 'automaticky',
    'IPv6 addresses': 'IPv6 adresy',
    'IPv6 gateway': 'IPv6 brána',
    'Change the network?': 'Změnit síť?',
    'Change it?': 'Změnit?',
    'NetworkManager (nmcli) is not on this server, so its network is set by hand (netplan, /etc/network/interfaces) - not here.':
        'Na tomto serveru není NetworkManager (nmcli), takže se jeho síť nastavuje ručně (netplan, /etc/network/interfaces) – ne zde.',
    'NetworkManager has no connection here to change.': 'NetworkManager tu nemá žádné připojení ke změně.',

    # ---- time ---------------------------------------------------------------------
    'Now on the server': 'Teď na serveru',
    'Time zone': 'Časové pásmo',
    'Kept right by NTP': 'Seřizováno přes NTP',
    'Time servers': 'Časové servery',
    'Time servers (one a line; empty: those of the system)': 'Časové servery (jeden na řádek; prázdné: ty systémové)',
    'chrony is not installed': 'chrony není nainstalováno',
    'set': 'nastaveno',

    # ---- system updates ----------------------------------------------------------------
    'The packages of the operating system (dnf or apt). The update runs as a job of its own on the server - closing the page or restarting this program does not stop it - and what it says shows here as it goes. The terminals go on running.':
        'Balíčky operačního systému (dnf nebo apt). Aktualizace běží na serveru jako samostatná úloha – zavření stránky ani restart tohoto programu ji nezastaví – a co vypisuje, se ukazuje zde průběžně. Terminály běží dál.',
    'Waiting': 'Čekající',
    'Look now': 'Zjistit teď',
    'Update everything': 'Aktualizovat vše',
    'Security updates only': 'Jen bezpečnostní aktualizace',
    'What it says': 'Co vypisuje',
    'Not looked at yet. Press Look now.': 'Zatím nezjišťováno. Stiskněte Zjistit teď.',
    'Package': 'Balíček',
    'Everything is up to date': 'Vše je aktuální',
    'Update the system?': 'Aktualizovat systém?',
    'Every package with an update is updated now. The terminals go on running; a new kernel needs a restart of the server, said here when it does.':
        'Teď se aktualizuje každý balíček, který má aktualizaci. Terminály běží dál; nové jádro vyžaduje restart serveru – zde se to řekne.',
    'started': 'spuštěno',
    'looking…': 'zjišťuji…',
    'done': 'hotovo',
    'failed': 'selhalo',
    'lost': 'ztraceno',

    # ---- SSH keys -------------------------------------------------------------------
    'The keys in an account\'s ~/.ssh/authorized_keys - who may sign in to it over SSH.': 'Klíče v ~/.ssh/authorized_keys účtu – kdo se k němu smí přihlásit přes SSH.',
    'The keys of': 'Klíče účtu',
    'Add a public key': 'Přidat veřejný klíč',
    'Add it': 'Přidat',
    'Make a key pair': 'Vytvořit pár klíčů',
    'A new key pair made here: the public half is added, the private half shown once, to keep.': 'Nový pár klíčů vytvořený zde: veřejná část se přidá, privátní se jednou ukáže k uschování.',
    'Fingerprint': 'Otisk',
    'not a key': 'není klíč',
    'No key': 'Žádný klíč',
    'Take this key away': 'Odebrat tento klíč',
    'Take the key away?': 'Odebrat klíč?',
    'SSH port': 'SSH port',
    'root may sign in': 'root se smí přihlásit',
    'With a password': 'Heslem',
    'With a key': 'Klíčem',
    'added': 'přidáno',
    'A new key pair': 'Nový pár klíčů',
    'Ed25519 (the best choice)': 'Ed25519 (nejlepší volba)',
    'RSA 4096 (for old clients)': 'RSA 4096 (pro staré klienty)',
    'Its name (the comment)': 'Jeho název (komentář)',
    'laptop of jan': 'notebook Jana',
    'The private key - shown once': 'Privátní klíč – ukazuje se jen jednou',
    'Keep it now: it is not kept on the server. Its public half was added to the account.': 'Uschovejte si ho hned: na serveru se nedrží. Jeho veřejná část byla přidána k účtu.',
    'Copy it': 'Zkopírovat',
    'Save it as a file': 'Uložit jako soubor',

    # ---- power -----------------------------------------------------------------------
    'The terminals live in tmux: restarting this program or the web server ends none of them. Restarting the server ends them all.':
        'Terminály žijí v tmux: restart tohoto programu ani webového serveru žádný neukončí. Restart serveru ukončí všechny.',
    'Restart ai': 'Restartovat ai',
    'Restart nginx and PHP': 'Restartovat nginx a PHP',
    'Restart the server': 'Restartovat server',
    'Switch the server off': 'Vypnout server',
    'Restart the server?': 'Restartovat server?',
    'Every terminal ends with it.': 'Všechny terminály skončí s ním.',
    'Restart it': 'Restartovat',
    'Switch the server off?': 'Vypnout server?',
    'Every terminal ends, and the server stays off until somebody switches it on.': 'Všechny terminály skončí a server zůstane vypnutý, dokud ho někdo nezapne.',
    'Switch it off': 'Vypnout',

    # ---- upgrades ------------------------------------------------------------------------
    'A new version of ai is checked before anything is put in: signed by a release key this server trusts, every file the one signed. Then its own install.sh --upgrade runs, as by hand. The terminals go on running; the pages come back after a few seconds.':
        'Nová verze ai se před nasazením zkontroluje: podepsaná release klíčem, kterému tento server důvěřuje, každý soubor ten podepsaný. Pak se spustí její vlastní install.sh --upgrade, jako ručně. Terminály běží dál; stránky se vrátí po pár sekundách.',
    'From the web': 'Z webu',
    'A package sent from here': 'Balíček nahraný odsud',
    'An': 'Balíček',
    'as released.': 'tak, jak byl vydán.',
    'Send a package…': 'Nahrát balíček…',
    'What the last upgrade said': 'Co vypsal poslední upgrade',
    'On the command line': 'Na příkazové řádce',
    'Here': 'Zde',
    'Looked at': 'Kde se hledá',
    'Last look': 'Naposledy zjišťováno',
    'Newest there': 'Nejnovější tam',
    'Release keys trusted': 'Důvěryhodné release klíče',
    'Upgrade now': 'Upgradovat teď',
    'Upgrade': 'Upgradovat',
    'It is fetched, checked and put in. The terminals go on running; these pages are back after a few seconds.':
        'Stáhne se, zkontroluje a nasadí. Terminály běží dál; tyto stránky se vrátí po pár sekundách.',
    'This is the newest version there.': 'Toto je nejnovější verze, která tam je.',
    'the upgrade is running': 'upgrade probíhá',
    'Signed by': 'Podepsal',
    'Here now': 'Zde teď',
    'Where new versions are looked for': 'Kde se hledají nové verze',
    'A GitHub folder (https://github.com/OWNER/REPO/tree/BRANCH/FOLDER), a web page or a folder listing with ai-X.Y.Z.tar.gz links, or one package\'s address. HTTPS only.':
        'Složka na GitHubu (https://github.com/OWNER/REPO/tree/BRANCH/FOLDER), webová stránka či výpis složky s odkazy na ai-X.Y.Z.tar.gz, nebo adresa jednoho balíčku. Jen HTTPS.',
    'Look once a day': 'Zjišťovat jednou denně',
    'Whether there is a newer version - it is only said, unless the next switch is on too.': 'Zda je venku novější verze – jen se to oznámí, pokud není zapnutý i další přepínač.',
    'Put a newer version in by itself': 'Novější verzi nasadit samo',
    'Once a day, at the hour below: a newer signed version found there is fetched, checked and put in. The terminals go on running; the pages reconnect after a few seconds.':
        'Jednou denně, v hodinu níže: novější podepsaná verze, která se tam najde, se stáhne, zkontroluje a nasadí. Terminály běží dál; stránky se po pár sekundách znovu připojí.',
    'At what hour': 'V kolik hodin',
    'Local time of this server, 0-23.': 'Místní čas tohoto serveru, 0–23.',

    # ---- about ----------------------------------------------------------------------------
    'Its own log': 'Jeho vlastní log',
    'Read it': 'Přečíst',
    'PHP of the pages': 'PHP stránek',
    'Its folders': 'Jeho složky',
    'Server': 'Server',
    'Name of this installation': 'Název této instalace',
    'What the pages call this server, beside its host name. Empty: the host name alone.': 'Jak stránky tento server nazývají, vedle názvu stroje. Prázdné: jen název stroje.',
    'For whoever has not chosen one of their own (the account menu).': 'Pro toho, kdo si nezvolil vlastní (nabídka účtu).',
    'Debug log': 'Ladicí log',
    'Writes far more into /var/log/ai/ai.log.': 'Zapisuje mnohem víc do /var/log/ai/ai.log.',

    # ---- signing in settings ----------------------------------------------------------------
    'Signed out after (hours without a click)': 'Odhlásit po (hodinách bez kliknutí)',
    'A sign-in nobody used for this long ends by itself. The terminals go on running.': 'Přihlášení, které nikdo takhle dlouho nepoužil, skončí samo. Terminály běží dál.',
    'Signed out after at most (hours)': 'Odhlásit nejpozději po (hodinách)',
    'However much it is used, a sign-in ends after this long.': 'Ať se používá jakkoli, přihlášení po této době skončí.',
    'Wrong passwords before a pause': 'Chybných hesel před pauzou',
    'From one address or for one name; then nobody signs in from there for the pause below.': 'Z jedné adresy nebo pro jedno jméno; pak se odtamtud po dobu pauzy níže nikdo nepřihlásí.',
    'The pause (minutes)': 'Pauza (minuty)',
    'Shortest password': 'Nejkratší heslo',
    'Changes that could cut you off go back after (seconds)': 'Změny, které by vás mohly odříznout, se vrátí po (sekundách)',
    'A change of the network, the firewall or who may reach the pages is taken back by itself unless it is kept within this time - pressed Keep it, from the old address or the new.':
        'Změna sítě, firewallu nebo toho, kdo smí na stránky, se sama vrátí, pokud se v této době nepotvrdí – stiskem Ponechat, ze staré adresy nebo z nové.',
    'Events kept (days)': 'Události držet (dní)',

    # ---- what the server says (the daemon's own words) --------------------------------------------
    'wrong name or password': 'chybné jméno nebo heslo',
    'not signed in': 'nepřihlášen',
    'change your password first': 'nejdřív si změňte heslo',
    'only an administrator may do that': 'to smí jen administrátor',
    'the present password is not that': 'současné heslo je jiné',
    'that request did not come from this page': 'ten požadavek nepřišel z této stránky',
    'that terminal is somebody else\'s': 'ten terminál patří někomu jinému',
    'no such terminal': 'takový terminál není',
    'that terminal has ended': 'ten terminál skončil',
    'it is still running - end it first': 'ještě běží – nejdřív ho ukončete',
    'a name, please': 'zadejte název',
    'a full path, please': 'zadejte celou cestu',
    'a file needs a name': 'soubor potřebuje název',
    'not a file': 'není soubor',
    'it is a folder': 'je to složka',
    'it is not text; download it instead': 'není to text; stáhněte si ho',
    'it was changed on the server since it was opened here - open it again': 'na serveru se mezitím změnil – otevřete ho znovu',
    'no such file': 'takový soubor není',
    'this is the last administrator: make another one first': 'toto je poslední administrátor: nejdřív založte dalšího',
    'not your own account - sign in as another administrator for that': 'ne vlastní účet – na to se přihlaste jako jiný administrátor',
    'only an administrator installs or updates Claude Code': 'Claude Code instaluje a aktualizuje jen administrátor',
    'an upgrade is running already': 'upgrade už probíhá',
    'it is being looked at already': 'už se zjišťuje',
    'neither dnf nor apt is on this server': 'na tomto serveru není dnf ani apt',
    'the server could not be reached': 'server je nedostupný',
    'the server is not answering just now': 'server právě neodpovídá',
    'the page got something that is not an answer': 'stránka dostala něco, co není odpověď',
    'that file is bigger than the server takes': 'ten soubor je větší, než server přijme',
    'the daemon is not answering — is ai.service running?': 'démon neodpovídá — běží ai.service?',
    'a test machine: nothing changed': 'testovací stroj: nic se nezměnilo',
    'who may reach the pages: changed': 'kdo smí na stránky: změněno',
    'add or drop': 'přidat nebo odebrat',
    'that key is there already': 'ten klíč už tam je',
    'no such key there': 'takový klíč tam není',
    'one public key line, as ssh-ed25519 AAAA... comment': 'jeden řádek veřejného klíče, jako ssh-ed25519 AAAA… komentář',
    'restarts the server': 'restartuje server',
    'switches the server off': 'vypne server',
    'restarts ai.service (the terminals go on)': 'restartuje ai.service (terminály běží dál)',
    'restarts nginx and php-fpm': 'restartuje nginx a php-fpm',
    'only https:// addresses are asked': 'ptá se jen na adresy https://',
    'the role is admin or user': 'role je admin nebo user',
    'a name of letters, digits and . _ @ - (up to 64)': 'jméno z písmen, číslic a . _ @ - (až 64 znaků)',
    'not the name itself': 'ne samotné jméno',
    'more than the same few characters again and again': 'víc než pár stejných znaků pořád dokola',
    'the two were not the same': 'obě nebyla stejná',
    # ---- the panes taken from otp, as ai words them --------------------------------------
    'The keys that may sign in to the server as root over SSH: made here, added or taken away.':
        'Klíče, které se smí přihlásit k serveru jako root přes SSH: vytvořit zde, přidat, odebrat.',
    'SSH keys of root': 'SSH klíče uživatele root',
    "Who may reach the pages, and the machine's own firewall: what ai's functions need is let in by itself, and you add whatever else you want - for IPv4 and IPv6.":
        'Kdo smí na stránky a vlastní firewall stroje: co potřebují funkce ai, se povolí samo, a vy přidáte cokoli dalšího – pro IPv4 i IPv6.',
    'The pages, the terminals and the files share ports 80 and 443, so who may reach them is said by nginx; the machine itself always may.':
        'Stránky, terminály i soubory sdílejí porty 80 a 443, takže kdo na ně smí, určuje nginx; stroj sám smí vždy.',
    "The server's address, gateway, DNS servers, host name and - switched on - IPv6, set through NetworkManager. A change goes back by itself unless it is kept: open the pages at the new address and press Keep it.":
        'Adresa serveru, brána, DNS servery, název stroje a – je-li zapnuté – IPv6, nastavované přes NetworkManager. Změna se sama vrátí, pokud se nepotvrdí: otevřete stránky na nové adrese a stiskněte Ponechat.',
    'The server keeps its clock with chrony: here is how far off it is, which servers it follows, and the time servers and the time zone set for it.':
        'Server si drží čas pomocí chrony: tady je vidět, jak moc se odchyluje, které servery sleduje, a jaké časové servery a časové pásmo má nastavené.',
    'The server restarted or switched off from here; the page follows it down and up again. The terminals live in tmux: restarting the server ends them all, restarting only ai or the web server (below) ends none.':
        'Restart nebo vypnutí serveru odsud; stránka ho sleduje při vypnutí i opětovném startu. Terminály žijí v tmux: restart serveru je ukončí všechny, restart jen ai nebo webového serveru (níže) žádný.',
    'Only the services': 'Jen služby',
    'The operating system\'s packages, updated by dnf (or apt). The update runs as a job of its own on the server - closing the page or restarting ai does not stop it - and what it says shows here as it goes. A restart an update needs is offered when it is done, or made by itself.':
        'Balíčky operačního systému, aktualizované přes dnf (nebo apt). Aktualizace běží na serveru jako samostatná úloha – zavření stránky ani restart ai ji nezastaví – a co vypisuje, se ukazuje zde průběžně. Restart, který aktualizace potřebuje, se po dokončení nabídne, nebo proběhne sám.',
    'The keys that may sign in to the server as root over SSH - the lines of /root/.ssh/authorized_keys. A key made here is shown once, to be kept by you, and kept nowhere on the server; one of your own is put on by its public half. Every change is written into Events.':
        'Klíče, které se smí přihlásit k serveru jako root přes SSH – řádky souboru /root/.ssh/authorized_keys. Klíč vytvořený zde se ukáže jednou, abyste si ho uschovali, a na serveru se nikde nedrží; vlastní klíč se nahraje svou veřejnou částí. Každá změna se zapíše do Událostí.',
    'https://…/ - the terminals, the files and these settings': 'https://…/ – terminály, soubory a toto nastavení',
    'The pages': 'Stránky',
    "In INPUT first: the chain AI-IN - your own rules in their order, then what ai's functions need. What it does not let in goes on to the rules that were there before.":
        'V INPUT jako první: řetězec AI-IN – vaše vlastní pravidla v jejich pořadí, pak to, co potřebují funkce ai. Co nepustí, jde dál k pravidlům, která tam byla předtím.',
    'Looked at in this order, first: a DROP or REJECT here wins over what ai lets in below.':
        'Procházejí se v tomto pořadí jako první: DROP nebo REJECT zde má přednost před tím, co ai povoluje níže.',
    'Worked out from what is set up, and changed with it. What keeps the pages reachable from this machine cannot be turned off.':
        'Odvozeno z toho, co je nastavené, a mění se s tím. Co drží stránky dosažitelné z tohoto stroje, nelze vypnout.',
    'to manage the machine - turned off, take care to keep a rule of your own for it':
        'ke správě stroje – když ho vypnete, nezapomeňte si na něj nechat vlastní pravidlo',
    'ping, and IPv6 cannot work without ICMPv6 (neighbour discovery)': 'ping; IPv6 bez ICMPv6 nefunguje (neighbour discovery)',
    'answers of a DHCPv6 server, for an address given that way': 'odpovědi DHCPv6 serveru, pro adresu přidělenou tímto způsobem',
    'DHCPv6 client': 'DHCPv6 klient',
    'these pages, the terminals and the files; who may reach them is under "Who may reach the pages"':
        'tyto stránky, terminály a soubory; kdo na ně smí, je v části „Kdo smí na stránky“',
    'this server serves the time to the networks set under Settings → Time': 'tento server poskytuje čas sítím nastaveným v Nastavení → Čas',
    'NTP (time served)': 'NTP (poskytovaný čas)',
    'IPv4 (iptables)': 'IPv4 (iptables)',
    'IPv6 (ip6tables)': 'IPv6 (ip6tables)',
    'Stratum': 'Stratum',
    'Leap status': 'Stav přestupné sekundy',
    'Networks that may ask this server for the time (UDP 123). Empty: nobody. The firewall opens it by itself.':
        'Sítě, které se smí tohoto serveru ptát na čas (UDP 123). Prázdné: nikdo. Firewall to otevře sám.',
    'dnf (or apt) updates every package. The terminals go on running meanwhile; a restart it needs is offered at the end.':
        'dnf (nebo apt) aktualizuje všechny balíčky. Terminály mezitím běží dál; restart, který bude potřeba, se nabídne na konci.',
    'For a minute or two the pages do not answer, and every terminal ends with it.': 'Minutu či dvě stránky neodpovídají a všechny terminály skončí.',
    'Not kept within the time set under Signing in, the old network comes back by itself: open the pages at the new address and press Keep it.':
        'Pokud se nepotvrdí v čase nastaveném v Přihlašování, stará síť se vrátí sama: otevřete stránky na nové adrese a stiskněte Ponechat.',
    'The server restarts: for a minute or two nothing answers, and every terminal ends.': 'Server se restartuje: minutu či dvě nic neodpovídá a všechny terminály skončí.',
    'The server is switched off. Nothing answers - and every terminal ends - until somebody switches it on again at the machine.':
        'Server se vypne. Nic neodpovídá – a všechny terminály skončí –, dokud ho někdo u stroje znovu nezapne.',
    'Switched on, the server takes IPv6 beside IPv4: nginx answers on both, the firewall is set for both.':
        'Po zapnutí server vedle IPv4 používá i IPv6: nginx odpovídá na obou, firewall je nastavený pro obě.',
    'Whatever only AI-IN let in (SSH, the pages) is then up to your own rules.': 'Co pouštěl jen AI-IN (SSH, stránky), pak závisí na vašich vlastních pravidlech.',
    'in place (firewalld)': 'nasazeno (firewalld)',
    "firewalld looks after the firewall of": 'firewall stroje spravuje firewalld',
    'Look again': 'Zjistit znovu',
    'Change it': 'Změnit',
    'Disk': 'Disk',
    'All keys': 'Všechny klávesy',
    'The console at login': 'Konzole při přihlášení',
    'It opens when root signs in': 'Otevře se při přihlášení roota',
    "the ai console opens when root signs in at the console or over SSH (q leaves it for the shell)": 'konzole ai se otevře, když se root přihlásí na konzoli nebo přes SSH (q ji opustí do shellu)',
    "root signs in to the ordinary shell; `ai --console` opens the console": 'root se přihlásí do běžného shellu; `ai --console` otevře konzoli',
    'every key goes to the terminal now - hold Esc to come back': 'všechny klávesy teď jdou do terminálu – zpět podržením Esc',
    'the browser has its keys back': 'prohlížeč má své klávesy zpět',
    'A function key, F1 to F12.': 'Funkční klávesa F1 až F12.',
    'Ctrl held for the next key - pressed here or typed: Ctrl, then C is Ctrl+C. For a phone, which has no Ctrl.': 'Ctrl podržený pro další klávesu – stisknutou zde nebo napsanou: Ctrl, pak C je Ctrl+C. Pro telefon, který Ctrl nemá.',
    'Alt held for the next key - pressed here or typed: Alt, then B is Alt+B (a word back).': 'Alt podržený pro další klávesu – stisknutou zde nebo napsanou: Alt, pak B je Alt+B (o slovo zpět).',
    'The terminal over the whole screen, and every key of the keyboard given to it - Ctrl+W, Ctrl+T, Ctrl+N, Ctrl+Tab, Esc and F11 too, which the browser keeps for itself otherwise (Chrome and Edge). Hold Esc to come back.': 'Terminál přes celou obrazovku a všechny klávesy klávesnice předané jemu – i Ctrl+W, Ctrl+T, Ctrl+N, Ctrl+Tab, Esc a F11, které si jinak nechává prohlížeč (Chrome a Edge). Zpět podržením Esc.',
    'A new line in what you are writing, without sending it - Shift+Enter, Alt+Enter and Ctrl+Enter on the keyboard do the same.': 'Nový řádek v psaném textu, bez odeslání – totéž dělá Shift+Enter, Alt+Enter a Ctrl+Enter na klávesnici.',
    'Ctrl+Z: puts what runs in the background (fg brings it back).': 'Ctrl+Z: pošle běžící program na pozadí (fg ho vrátí).',
    'Home': 'Home', 'End': 'End', 'Page Up': 'Page Up', 'Page Down': 'Page Down', 'Insert': 'Insert', 'Delete': 'Delete',
    "this browser keeps some keys for itself (Ctrl+W, Ctrl+T, Ctrl+N): Chrome or Edge give them all": 'tento prohlížeč si některé klávesy nechává (Ctrl+W, Ctrl+T, Ctrl+N): Chrome nebo Edge je předají všechny',
    # ---- 1.0.4: what otp had and ai had not yet ----
    'Put this copy back': 'Obnovit tuto kopii',
    'How the mails of these pages leave this machine: the codes of the second step, and notices of warnings and failures.':
        'Jak pošta těchto stránek odchází z tohoto stroje: kódy druhého kroku a upozornění na varování a selhání.',
    "How SMS leaves this machine, for the codes of the second step: an HTTP gateway, a modem's spool, or a Teltonika on the network.":
        'Jak odcházejí SMS s kódy druhého kroku: HTTP brána, fronta modemu, nebo Teltonika v síti.',
    'What people get from this server - the mails and the SMS, in Czech and English.':
        'Co lidé od tohoto serveru dostávají – e-maily a SMS, česky a anglicky.',
    'Every mail and SMS this server sent, or tried to: where, what, how it went.':
        'Každý e-mail a SMS, které tento server poslal nebo zkusil poslat: kam, co a jak to dopadlo.',
    'The database: copies made every night, downloaded, put back.':
        'Databáze: kopie dělané každou noc, stažení, obnova.',
    'Backups to other machines: a folder, FTP, FTPS, SFTP, SCP or a Windows share - on a schedule, locked with a password; put back from here.':
        'Zálohy na jiné stroje: složka, FTP, FTPS, SFTP, SCP nebo sdílená složka Windows – podle plánu, zamčené heslem; obnova odsud.',
    'The whole configuration as one file: exported, imported.':
        'Celá konfigurace jako jeden soubor: export a import.',
    'Updates':
        'Aktualizace',
    'Messages':
        'Zprávy',
    'Data':
        'Data',
    'SMS':
        'SMS',
    'Mail':
        'Pošta',
    'Message texts':
        'Texty zpráv',
    'Outgoing mail':
        'Odchozí pošta',
    'Backups':
        'Zálohy',
    'Database':
        'Databáze',
    'Export and import':
        'Export a import',
    'Certificates and TLS':
        'Certifikáty a TLS',
    'Addresses and names with wrong passwords or wrong codes still counted - at the limit (Settings → Signing in) they are locked out until the time runs out. Clear one, or all of them, and they may try again at once.':
        'Adresy a jména, kterým se ještě počítají chybná hesla nebo kódy – po dosažení limitu (Nastavení → Přihlašování) jsou zablokované, dokud čas nevyprší. Smažte jedno nebo všechna a mohou to hned zkusit znovu.',
    'Locked out':
        'Zablokováno',
    'Columns of the tables':
        'Sloupce tabulek',
    'Second step':
        'Druhý krok',
    'at the next sign-in':
        'při příštím přihlášení',
    'second step not given yet':
        'druhý krok ještě nezadán',
    'Reset the second step':
        'Zrušit druhý krok',
    'Reset it':
        'Zrušit',
    'e-mail':
        'e-mail',
    'app':
        'aplikace',
    "The codes of the second step of signing in, sent by e-mail, and notices of what Events marks as a warning or a failure. The mail leaves through your mail server (SMTP), or straight to the server of the recipient's domain with no relay at all.":
        'Kódy druhého kroku přihlášení posílané e-mailem a upozornění na to, co Události označí jako varování nebo selhání. Pošta odchází přes váš poštovní server (SMTP), nebo rovnou na server domény příjemce, bez jakéhokoli relaye.',
    'Sends a short message the way the codes and the notices go, and shows every step: the server reached, TLS, signing in, the message handed over and what the server said. Save the changes first.':
        'Pošle krátkou zprávu stejnou cestou jako kódy a upozornění a ukáže každý krok: spojení se serverem, TLS, přihlášení, předání zprávy a co server odpověděl. Nejdřív uložte změny.',
    'Try it':
        'Vyzkoušet',
    'Send a test':
        'Poslat zkoušku',
    'The certificate authority':
        'Certifikační autorita',
    'The second step of signing in, for everybody':
        'Druhý krok přihlášení pro všechny',
    'After a right password these pages ask for a code too: from an authenticator app, or sent by e-mail. The first time, each account chooses how and proves it; Accounts → Reset the second step, or ai --reset-2fa NAME as root, takes it away again. Switched on, every other sign-in ends, so each gives its second step.':
        'Po správném hesle se tyto stránky zeptají ještě na kód: z aplikace autentikátoru, nebo poslaný e-mailem či SMS. Poprvé si každý účet zvolí způsob a ověří ho; Účty → Zrušit druhý krok nebo ai --reset-2fa JMÉNO jako root ho zase zruší. Zapnutím skončí všechna ostatní přihlášení, aby každé zadalo svůj druhý krok.',
    'Offered: an authenticator app':
        'Nabízeno: aplikace autentikátoru',
    'Google or Microsoft Authenticator, FreeOTP, 1Password... - a QR code scanned once.':
        'Google nebo Microsoft Authenticator, FreeOTP, 1Password… – QR kód se naskenuje jednou.',
    'Offered: a code by e-mail':
        'Nabízeno: kód e-mailem',
    'Only where sending mail is set up (Settings → Mail).':
        'Jen tam, kde je nastavené odesílání pošty (Nastavení → Pošta).',
    'Offered: a code by SMS':
        'Nabízeno: kód SMS',
    'Only where sending SMS is set up (Settings → SMS).':
        'Jen tam, kde je nastavené odesílání SMS (Nastavení → SMS).',
    'Codes of the app taken this many periods early or late':
        'Kódy aplikace přijaté o tolik období dříve či později',
    'A period is 30 s. 1 forgives a phone half a minute out; 0 takes only the code of now.':
        'Období je 30 s. 1 odpustí telefonu půl minuty odchylky; 0 bere jen právě platný kód.',
    'Digits of a code sent by mail':
        'Číslic kódu posílaného poštou',
    'A code sent is good for (s)':
        'Poslaný kód platí (s)',
    'Sending mail':
        'Odesílání pošty',
    'off - no mail is sent':
        'vypnuto – neposílá se žádná pošta',
    'through a mail server (SMTP)':
        'přes poštovní server (SMTP)',
    "straight to the recipients' servers (MX)":
        'rovnou na servery příjemců (MX)',
    "How a mail of these pages leaves this machine: through your mail server, or straight to the recipient's (its MX record, looked up here) - which many networks block on port 25.":
        'Jak pošta těchto stránek opouští tento stroj: přes váš poštovní server, nebo rovnou na server příjemce (jeho záznam MX, zjištěný zde) – což mnoho sítí na portu 25 blokuje.',
    'Mail server':
        'Poštovní server',
    "The mail server's name or address: smtp.example.cz, or a relay in your network.":
        'Název nebo adresa poštovního serveru: smtp.example.cz, nebo relay ve vaší síti.',
    'Port':
        'Port',
    '0 picks the usual one for the encryption: 587 for STARTTLS, 465 for TLS, 25 without.':
        '0 zvolí obvyklý podle šifrování: 587 pro STARTTLS, 465 pro TLS, 25 bez.',
    'Encryption':
        'Šifrování',
    'STARTTLS - plain, then encrypted (587)':
        'STARTTLS – nejdřív otevřeně, pak šifrovaně (587)',
    'TLS from the start (465)':
        'TLS od začátku (465)',
    'STARTTLS where the server offers it':
        'STARTTLS, kde ho server nabízí',
    'none - plain text (25)':
        'žádné – čistý text (25)',
    'STARTTLS on 587 is what most servers want; SMTPS on 465 is TLS from the first byte.':
        'Většina serverů chce STARTTLS na 587; SMTPS na 465 je TLS od prvního bajtu.',
    'Signing in':
        'Přihlašování',
    'what the server offers':
        'co server nabízí',
    'none - the server lets this machine send':
        'žádné – server tomuto stroji odesílání dovolí',
    'XOAUTH2 (the password is the access token)':
        'XOAUTH2 (heslo je přístupový token)',
    'How this machine signs in to the server. None where the relay lets this machine send as it is.':
        'Jak se tento stroj k serveru přihlašuje. Žádné tam, kde relay tento stroj nechá posílat bez přihlášení.',
    'Account':
        'Účet',
    'Password':
        'Heslo',
    'Kept sealed in the database; never shown again. Empty keeps the one saved.':
        'Uchováno zapečetěné v databázi; už se nikdy neukáže. Prázdné ponechá uložené.',
    "Check the server's certificate":
        'Ověřovat certifikát serveru',
    'Off only for a server with a certificate nobody signed - its password then goes to whoever answers in its place.':
        'Vypnout jen u serveru s certifikátem, který nikdo nepodepsal – heslo pak dostane kdokoli, kdo odpoví místo něj.',
    'Wait for the server (s)':
        'Čekat na server (s)',
    'From (address)':
        'Od (adresa)',
    'The address the mails come from - one your mail server lets this machine send as.':
        'Adresa, ze které pošta chodí – taková, za kterou smí tento stroj přes váš server posílat.',
    'From (name)':
        'Od (jméno)',
    'Replies to':
        'Odpovědi na',
    'Empty: to the From address.':
        'Prázdné: na adresu Od.',
    'This machine calls itself (EHLO)':
        'Tento stroj se představuje (EHLO)',
    'Empty: its host name.':
        'Prázdné: název stroje.',
    "Port of the recipients' servers":
        'Port serverů příjemců',
    "Encryption to the recipients' servers":
        'Šifrování k serverům příjemců',
    'encrypted where the server offers it':
        'šifrovaně, kde to server nabízí',
    'always encrypted, the certificate checked':
        'vždy šifrovaně, s ověřením certifikátu',
    "DNS servers for the recipients' domains":
        'DNS servery pro domény příjemců',
    'Addresses, separated by commas. Empty: the ones this machine uses (/etc/resolv.conf).':
        'Adresy oddělené čárkami. Prázdné: ty, které používá tento stroj (/etc/resolv.conf).',
    'Language of the mail':
        'Jazyk pošty',
    'Notices go to':
        'Upozornění dostává',
    'Addresses, separated by commas, that are told by mail what Events marks as a warning or a failure - a backup that did not go, a newer version, an account locked out. Empty: nobody.':
        'Adresy oddělené čárkami, kterým se e-mailem oznámí, co Události označí jako varování nebo selhání – neodeslaná záloha, nová verze, zablokovaný účet. Prázdné: nikdo.',
    'What they are told':
        'Co se jim oznamuje',
    'warnings and failures':
        'varování a selhání',
    'failures only':
        'jen selhání',
    'At most one notice mail every (minutes)':
        'Nejvýš jeden e-mail s upozorněním za (minut)',
    'What happens in between goes in the next one, together.':
        'Co se stane mezitím, přijde v dalším, pohromadě.',
    'switched off':
        'vypnuto',
    'through a mail server':
        'přes poštovní server',
    'straight to the recipients':
        'rovnou příjemcům',
    'A copy every night':
        'Kopie každou noc',
    "SQLite's own backup of the database in use, with the key its secrets are sealed with and config.json beside it, into /var/lib/ai/copies.":
        'Vlastní záloha SQLite z používané databáze, spolu s klíčem, kterým jsou zapečetěná její tajemství, a s config.json, do /var/lib/ai/copies.',
    'At what hour':
        'V kolik hodin',
    'Copies kept':
        'Ponechaných kopií',
    'The newest ones; older ones are taken away.':
        'Ty nejnovější; starší se mažou.',
    'One database holds everything: the accounts and their sign-ins, the settings, the events and the list of terminals. It is a SQLite file on this machine. The secrets in it are sealed with a key kept beside it, in the state folder - and every copy is kept with that key beside it.':
        'Jedna databáze drží všechno: účty a jejich přihlášení, nastavení, události a seznam terminálů. Je to soubor SQLite na tomto stroji. Tajemství v ní jsou zapečetěná klíčem uloženým vedle ní ve stavové složce – a každá kopie se drží s tímto klíčem vedle sebe.',
    'The copies it keeps':
        'Kopie, které drží',
    "Every night at the hour above, SQLite's own backup of the database in use, packed with the key its secrets are sealed with and config.json. A copy is the database whole: put back, it replaces every account, every setting and every event - and a copy of what is there now is made first, so that can be undone too.":
        'Každou noc v hodinu výše vlastní záloha SQLite z používané databáze, zabalená s klíčem jejích tajemství a s config.json. Kopie je celá databáze: obnovená nahradí každý účet, každé nastavení a každou událost – a předtím se udělá kopie současného stavu, takže i to jde vrátit.',
    'Make one now':
        'Vytvořit hned',
    'A copy now, rather than waiting for tonight. It is kept with the others and counts as one of them.':
        'Kopie teď, místo čekání na noc. Uchová se s ostatními a počítá se mezi ně.',
    'Put a copy back':
        'Obnovit kopii',
    'A copy from somewhere else - one downloaded from here, or from another server of ai. Nothing happens until it has been read, checked and shown to you.':
        'Kopie odjinud – stažená odsud, nebo z jiného serveru ai. Nic se nestane, dokud se nepřečte, neověří a neukáže vám.',
    'Drop a copy here, or press to choose one':
        'Přetáhněte sem kopii, nebo klikněte a vyberte ji',
    'The file':
        'Soubor',
    'Its key':
        'Jeho klíč',
    'The copies':
        'Kopie',
    'The last copy':
        'Poslední kopie',
    'none yet':
        'zatím žádná',
    'In it':
        'Obsahuje',
    'The copy':
        'Kopie',
    'Made':
        'Vytvořeno',
    'Size':
        'Velikost',
    'Download it':
        'Stáhnout',
    'Put it back':
        'Obnovit',
    'Take it away':
        'Odebrat',
    'Take the copy away?':
        'Odebrat kopii?',
    'No copy has been made yet.':
        'Zatím nebyla vytvořena žádná kopie.',
    'Made by':
        'Vytvořil',
    'Accounts':
        'Účty',
    'Events':
        'Události',
    'The key of its secrets':
        'Klíč jejích tajemství',
    'in it - the same as here':
        'je v ní – stejný jako zde',
    'in it - it replaces the one here':
        'je v ní – nahradí ten zdejší',
    'not in it: secrets sealed elsewhere cannot be opened':
        'není v ní: tajemství zapečetěná jinde nepůjde otevřít',
    'Everything is replaced by what is in it: every account, every setting, every event. Whoever is signed in may have to sign in again. A copy of what is here now is made first.':
        'Vše se nahradí tím, co je v ní: každý účet, každé nastavení, každá událost. Kdo je přihlášen, se možná bude muset přihlásit znovu. Nejdřív se udělá kopie současného stavu.',
    "The whole configuration as one file: the settings, the accounts of these pages, the certificate and TLS of the pages, who may reach the pages, the firewall and the mail server's authorities. The events and the terminals are not in it: they move with a copy of the database. On the command line: ai --export-config FILE [--with-secrets] and ai --import-config FILE --yes.":
        'Celá konfigurace jako jeden soubor: nastavení, účty těchto stránek, certifikát a TLS stránek, kdo smí na stránky, firewall a autority poštovního serveru. Události a terminály v něm nejsou: ty se přenášejí s kopií databáze. Na příkazové řádce: ai --export-config SOUBOR [--with-secrets] a ai --import-config SOUBOR --yes.',
    'Export':
        'Exportovat',
    'Export with the secrets':
        'Export i s tajemstvími',
    'Import a file…':
        'Importovat soubor…',
    "The password hashes of the accounts, their authenticator keys, the mail server's password and the private key of the certificate go into the file - locked with a passphrase made now and shown once. The file opens only with it.":
        'Do souboru půjdou hashe hesel účtů, jejich klíče autentikátoru, heslo poštovního serveru a soukromý klíč certifikátu – zamčené heslovou frází vytvořenou teď a ukázanou jednou. Soubor otevře jen ona.',
    'Export them':
        'Exportovat',
    'The passphrase of the file':
        'Heslová fráze souboru',
    'The file opens only with this passphrase - it is not shown again and not kept here. Write it down apart from the file.':
        'Soubor otevře jen tato fráze – znovu se neukáže a zde se neuchová. Zapište si ji odděleně od souboru.',
    'Exactly the file':
        'Přesně podle souboru',
    'Add to what is here':
        'Přidat k tomu, co tu je',
    'Passphrase':
        'Heslová fráze',
    'Going back to an older version':
        'Návrat ke starší verzi',
    "Only to a version that is safe: one that reads what the newer versions wrote into the database the same, and has every security fix that matters - each version says how far back it may go, and the highest of what ran on this database counts. A copy of the database is made first (Settings → Database); the package is checked like an upgrade's. The terminals go on running.":
        'Jen k verzi, která je bezpečná: čte to, co novější verze zapsaly do databáze, stejně, a má všechny podstatné bezpečnostní opravy – každá verze říká, kam až se smí vrátit, a platí nejvyšší z toho, co na této databázi běželo. Nejdřív se udělá kopie databáze (Nastavení → Databáze); balíček se ověří jako při upgradu. Terminály běží dál.',
    'Version':
        'Verze',
    'Published':
        'Vydáno',
    'Go back to it':
        'Vrátit se k ní',
    'Go back':
        'Vrátit se',
    'not safe here':
        'zde není bezpečná',
    'What it runs on':
        'Na čem běží',
    'The terminals':
        'Terminály',
    'The pages':
        'Stránky',
    'The system':
        'Systém',
    'this one':
        'tento',
    'where':
        'kde',
    'system':
        'systém',
    'kernel':
        'jádro',
    'Your account':
        'Váš účet',
    'What you may do':
        'Co smíte',
    'Anything: terminals as any Linux account, every file, the settings and the server itself.':
        'Všechno: terminály jako kterýkoli účet Linuxu, každý soubor, nastavení i samotný server.',
    'Terminals of your own, as the Linux account below, and the files of your folders. No setting and no account.':
        'Vlastní terminály jako účet Linuxu níže a soubory vašich složek. Žádné nastavení a žádný účet.',
    'Language and letters':
        'Jazyk a písmo',
    'The language of these pages':
        'Jazyk těchto stránek',
    'Every table you have laid out goes back as it comes: the widths and the order of the columns, on every page. Nobody else’s change.':
        'Každá tabulka, kterou jste uspořádali, se vrátí do výchozího stavu: šířky i pořadí sloupců, na všech stránkách. Nikomu jinému se nic nezmění.',
    'While this is on, the edge of any column’s heading can be dragged to size it and the heading itself to move it, and the right button on a heading hides a column, brings a hidden one back or adds an empty one for room; each change is kept the moment you let go. It is for this sign-in only: signing out or the sign-in running out turns it off again. Off, the tables are drawn as you left them and nothing can move them.':
        'Dokud je to zapnuté, okraj záhlaví kteréhokoli sloupce jde tažením zúžit či rozšířit a samotné záhlaví přesunout; pravé tlačítko na záhlaví sloupec skryje, vrátí skrytý nebo přidá prázdný pro místo; každá změna se uloží, jakmile pustíte. Platí jen pro toto přihlášení: odhlášení nebo vypršení přihlášení to vypne. Vypnuté se tabulky kreslí, jak jste je nechali, a nic s nimi nepohne.',
    'Your settings in a file':
        'Vaše nastavení v souboru',
    'How you have set these pages up for yourself — the columns of the tables, the language, the letters and keys of the terminal — saved as a JSON file, and read back here or on another machine running ai. Never your password, your role or anything else about the account.':
        'Jak jste si tyto stránky nastavili – sloupce tabulek, jazyk, písmo a klávesy terminálu – uložené jako soubor JSON a načtené zpět zde nebo na jiném stroji s ai. Nikdy vaše heslo, role ani nic dalšího o účtu.',
    'Every table is as it comes.':
        'Všechny tabulky jsou ve výchozím stavu.',
    'Backups to the destinations on a schedule':
        'Zálohy do cílů podle plánu',
    'A backup is made and sent to every destination switched on, at the time below. Back up now sends one whenever wanted.':
        'Záloha se vytvoří a pošle do všech zapnutých cílů v čase níže. Zálohovat teď ji pošle kdykoli.',
    'At':
        'V',
    "When, as HH:MM on this machine's clock.":
        'Kdy, jako HH:MM podle hodin tohoto stroje.',
    'How often':
        'Jak často',
    'daily, or weekly on the day below.':
        'denně, nebo týdně v den níže.',
    'daily':
        'denně',
    'weekly':
        'týdně',
    'On (1 Monday - 7 Sunday)':
        'V den (1 pondělí – 7 neděle)',
    'The day of a weekly backup.':
        'Den týdenní zálohy.',
    'Backups kept at each destination':
        'Ponechaných záloh v každém cíli',
    "How many of this server's backups each destination keeps; the oldest go once a new one is there.":
        'Kolik záloh tohoto serveru si každý cíl ponechá; nejstarší se smažou, jakmile je tam nová.',
    'And none older than (days)':
        'A žádná starší než (dní)',
    'Older ones are taken away too - 0: only the count above decides.':
        'Starší se smažou také – 0: rozhoduje jen počet výše.',
    'The password of the backups':
        'Heslo záloh',
    'Every backup is locked with it (AES-256, opened with ai or with openssl alone). Keep it apart from the backups: without it none of them can be opened. Without one nothing is sent.':
        'Každá záloha je jím zamčená (AES-256, otevře ji ai nebo samotný openssl). Držte ho odděleně od záloh: bez něj nejde žádnou otevřít. Bez hesla se nic neposílá.',
    'saved - empty keeps it':
        'uloženo – prázdné ho ponechá',
    'not set':
        'nenastaveno',
    "A backup is everything of this program: the whole database (the accounts, every setting, the certificate and TLS, the firewall, the events, the list of terminals), the key its secrets are sealed with and this machine's config.json - with RESTORE.md, the exact steps to bring it all back on a machine installed from nothing. Locked with the password below; sent to every destination switched on - a folder, FTP, FTPS, SFTP, SCP or a Windows/Samba share. The files of the Linux accounts (their projects, ~/.claude) are not in it.":
        'Záloha je všechno z tohoto programu: celá databáze (účty, každé nastavení, certifikát a TLS, firewall, události, seznam terminálů), klíč jejích tajemství a config.json tohoto stroje – s RESTORE.md, přesným postupem, jak vše obnovit na stroji nainstalovaném od nuly. Zamčená heslem níže; posílá se do všech zapnutých cílů – složka, FTP, FTPS, SFTP, SCP nebo sdílená složka Windows/Samba. Soubory účtů Linuxu (jejich projekty, ~/.claude) v ní nejsou.',
    'When, how many, and the password':
        'Kdy, kolik a heslo',
    'Where they go':
        'Kam jdou',
    'What was sent':
        'Co bylo odesláno',
    'A whole path on this machine.':
        'Celá cesta na tomto stroji.',
    'this server':
        'tento server',
    'Only an administrator sees and changes the backups: they hold every secret.':
        'Zálohy vidí a mění jen administrátor: obsahují všechna tajemství.',
    'No password of the backups is set: the file will hold <b>every secret of this server</b> readable. Set the password first unless you know where the file goes.':
        'Heslo záloh není nastavené: soubor bude obsahovat <b>všechna tajemství tohoto serveru</b> čitelně. Nejdřív nastavte heslo, pokud nevíte, kam soubor půjde.',
    'Everything in the database is replaced with what the backup holds - accounts, settings, the certificate, events, and who is signed in: you sign in again afterwards, with an account the backup has. A copy of what is here now is made first (Settings → Database). The terminals go on running.':
        'Vše v databázi se nahradí tím, co obsahuje záloha – účty, nastavení, certifikát, události i to, kdo je přihlášen: potom se přihlásíte znovu účtem, který je v záloze. Nejdřív se udělá kopie současného stavu (Nastavení → Databáze). Terminály běží dál.',
    'No backup of ai there.':
        'Žádná záloha ai tam není.',
    'The codes of the second step of signing in, sent by SMS: through an SMS gateway with an HTTP API, a GSM modem on this machine (smstools3 or gammu-smsd), or a Teltonika gateway (TRB140, RUT…) on the network.':
        'Kódy druhého kroku přihlášení posílané SMS: přes SMS bránu s HTTP API, GSM modem na tomto stroji (smstools3 nebo gammu-smsd), nebo bránu Teltonika (TRB140, RUT…) v síti.',
    'A short SMS sent the way the codes go - save the changes first. For a Teltonika, Test the connection signs in to it and asks how its modems are; nothing is sent.':
        'Krátká SMS poslaná stejnou cestou jako kódy – nejdřív uložte změny. U Teltoniky se Otestovat spojení k bráně přihlásí a zeptá se na stav modemů; nic se neodešle.',
    'Send a test SMS':
        'Poslat zkušební SMS',
    'Test the connection':
        'Otestovat spojení',
    'The certificates the gateway is checked against':
        'Certifikáty, proti kterým se brána ověřuje',
    "The gateway's own certificate (a TRB makes one itself), or the root and the chain of the authority that signed it. With some here only these are trusted; with none, the authorities this machine trusts.":
        'Vlastní certifikát brány (TRB si ho vytvoří sama), nebo kořen a řetězec autority, která ho podepsala. Jsou-li zde nějaké, věří se jen jim; bez nich autoritám, kterým věří tento stroj.',
    'Read it from the gateway':
        'Načíst z brány',
    'How SMS is sent':
        'Jak se posílají SMS',
    'off - no SMS is sent':
        'vypnuto – SMS se neposílají',
    'an SMS gateway with an HTTP API':
        'SMS brána s HTTP API',
    'a modem on this machine - a file into the spool of smstools / gammu':
        'modem na tomto stroji – soubor do fronty smstools / gammu',
    'a Teltonika gateway (TRB140, RUT…) on the network':
        'brána Teltonika (TRB140, RUT…) v síti',
    'An SMS gateway with an HTTP API (most operators and services), a GSM modem on this machine run by smstools3 or gammu-smsd (a file into its spool folder), or a Teltonika gateway (TRB140, RUT…) on the network through its own API. Off: no code goes by SMS.':
        'SMS brána s HTTP API (většina operátorů a služeb), GSM modem na tomto stroji obsluhovaný smstools3 nebo gammu-smsd (soubor do jeho fronty), nebo brána Teltonika (TRB140, RUT…) v síti přes její vlastní API. Vypnuto: žádný kód nejde SMS.',
    'Country code for numbers written without one':
        'Předvolba pro čísla zapsaná bez ní',
    'A number typed as 603 123 456 becomes +420603123456. Empty: a number has to be typed with its country code.':
        'Číslo zapsané jako 603 123 456 se změní na +420603123456. Prázdné: číslo se musí zapsat s předvolbou.',
    'Without accents (one SMS, not two)':
        'Bez diakritiky (jedna SMS, ne dvě)',
    'A letter with an accent makes the whole SMS the wide alphabet, 70 characters a part instead of 160.':
        'Písmeno s diakritikou přepne celou SMS do široké abecedy, 70 znaků na díl místo 160.',
    "The gateway's address (URL)":
        'Adresa brány (URL)',
    'Where the message is sent. {to} is the number (+420…), {to_digits} the number without +, {text} the message, {token} the key below. https://sms.example.cz/api/send?to={to}&text={text}':
        'Kam se zpráva posílá. {to} je číslo (+420…), {to_digits} číslo bez +, {text} zpráva, {token} klíč níže. https://sms.example.cz/api/send?to={to}&text={text}',
    'HTTP method':
        'Metoda HTTP',
    'POST sends the body below; GET only the address.':
        'POST pošle tělo níže; GET jen adresu.',
    "The gateway's key ({token})":
        'Klíč brány ({token})',
    'Its API key or password, kept sealed in the database and put where {token} is written.':
        'Její klíč API nebo heslo, uchované zapečetěné v databázi a dosazené tam, kde je napsáno {token}.',
    'The gateway said it was sent when the answer holds':
        'Brána potvrdila odeslání, když odpověď obsahuje',
    'Some gateways answer 200 to everything: a word their answer holds only when it was sent. Empty: any 2xx.':
        'Některé brány odpovídají 200 na všechno: slovo, které jejich odpověď obsahuje, jen když se odeslalo. Prázdné: jakékoli 2xx.',
    'What is sent (body)':
        'Co se posílá (tělo)',
    'For POST. Starting with { it is JSON: {"to": "{to}", "text": "{text}"}; otherwise a form: to={to}&text={text}. Empty: the address alone.':
        'Pro POST. Začíná-li {, je to JSON: {"to": "{to}", "text": "{text}"}; jinak formulář: to={to}&text={text}. Prázdné: jen adresa.',
    'Headers':
        'Hlavičky',
    'One a line, Name: value - Authorization: Bearer {token}.':
        'Jedna na řádek, Název: hodnota – Authorization: Bearer {token}.',
    'The spool folder':
        'Složka fronty',
    'smstools3: /var/spool/sms/outgoing. A file "To: 420…" and the text is written there and the modem\'s daemon sends it.':
        'smstools3: /var/spool/sms/outgoing. Zapíše se tam soubor „To: 420…“ s textem a démon modemu ho odešle.',
    "The Teltonika's address":
        'Adresa Teltoniky',
    'The gateway on the network: 192.168.1.1, or host:port.':
        'Brána v síti: 192.168.1.1, nebo host:port.',
    'Its interface':
        'Její rozhraní',
    "RutOS's own API (/api, RutOS 7 - the default)":
        'Vlastní API RutOS (/api, RutOS 7 – výchozí)',
    'the older Post/Get SMS service (/cgi-bin/sms_send)':
        'starší služba Post/Get SMS (/cgi-bin/sms_send)',
    'RutOS 7 offers its own API out of the box; the older Post/Get service has to be switched on by hand.':
        'RutOS 7 má vlastní API hned po vybalení; starší službu Post/Get je třeba zapnout ručně.',
    'Its modem':
        'Její modem',
    'Which modem sends - 1-1, 3-1… Empty: the one the gateway names first.':
        'Který modem posílá – 1-1, 3-1… Prázdné: ten, který brána uvede první.',
    'Over HTTPS':
        'Přes HTTPS',
    'HTTPS keeps its password and the codes off the wire.':
        'HTTPS udrží heslo i kódy mimo síť v čitelné podobě.',
    'Check its certificate':
        'Ověřovat její certifikát',
    "Checked against the certificates imported below - the gateway's own or the authority that signed it; with none imported, against the authorities this machine trusts. Off: any certificate is taken.":
        'Ověřuje se proti certifikátům importovaným níže – vlastnímu certifikátu brány nebo autoritě, která ho podepsala; bez importovaných proti autoritám, kterým věří tento stroj. Vypnuto: přijme se jakýkoli certifikát.',
    'Its user':
        'Její uživatel',
    'An account of the gateway that may use its API.':
        'Účet brány, který smí používat její API.',
    'Its password':
        'Její heslo',
    'Kept sealed in the database. Never shown again.':
        'Uchováno zapečetěné v databázi. Už se nikdy neukáže.',
    'an HTTP gateway':
        'HTTP brána',
    'a modem on this machine':
        'modem na tomto stroji',
    'a Teltonika gateway':
        'brána Teltonika',
    'save the SMS settings first':
        'nejdřív uložte nastavení SMS',
    'What people get from this server - the mails and the SMS, in Czech and English. The words in braces are filled in when it is sent: {site} the name of these pages, {code} the code, {minutes} how long it is good for, {n} {what} {lines} {url} in a notice. An empty text is the built-in one.':
        'Co lidé od tohoto serveru dostávají – e-maily a SMS, česky a anglicky. Slova ve složených závorkách se při odeslání doplní: {site} název těchto stránek, {code} kód, {minutes} jak dlouho platí, {n} {what} {lines} {url} v upozornění. Prázdný text je vestavěný.',
    'A sign-in code by mail':
        'Kód pro přihlášení e-mailem',
    'the subject':
        'předmět',
    'the text':
        'text',
    'Filled in:':
        'Doplní se:',
    'Checking an address (setting up the second step)':
        'Ověření adresy (nastavení druhého kroku)',
    'A test mail':
        'Zkušební e-mail',
    'Notices of warnings and failures':
        'Upozornění na varování a selhání',
    'A sign-in code by SMS':
        'Kód pro přihlášení SMS',
    'Checking a number by SMS':
        'Ověření čísla SMS',
    'A test SMS':
        'Zkušební SMS',
    'back to the built-in text':
        'zpět na vestavěný text',
    'Every mail and SMS this server sends - a code to sign in with, a code to check an address, a notice, a test - written down here: where it went, what it was and what the other side said. What a message held is never kept: a code goes in no list.':
        'Každý e-mail a SMS, které tento server posílá – kód pro přihlášení, kód k ověření adresy, upozornění, zkouška – se zde zapíše: kam šel, co to bylo a co odpověděla druhá strana. Obsah zprávy se nikdy neuchovává: kód nejde do žádného seznamu.',
    'an address, a number, what the server said…':
        'adresa, číslo, co server odpověděl…',
    'every state':
        'všechny stavy',
    'sent':
        'odesláno',
    'failed':
        'selhalo',
    'Clear the sent ones':
        'Smazat odeslané',
    'Clear the failed ones':
        'Smazat selhané',
    'Nothing has been sent yet.':
        'Zatím se nic neposlalo.',
    'When':
        'Kdy',
    'How':
        'Jak',
    'To':
        'Komu',
    'What':
        'Co',
    'State':
        'Stav',
    'What the other side said':
        'Co odpověděla druhá strana',
    'Took':
        'Trvalo',
    'a test SMS':
        'zkušební SMS',
    'a test mail':
        'zkušební e-mail',
    'a sign-in code':
        'kód pro přihlášení',
    'a code to check the address':
        'kód k ověření adresy',
    'save the changes first':
        'nejdřív uložte změny',
    'How the pages speak HTTPS: the certificate with its chain, the protocols, the ciphers.':
        'Jak stránky mluví HTTPS: certifikát s jeho řetězcem, protokoly, šifry.',
    'Certificates':
        'Certifikáty',
    'A certificate is sent as PEM files (the certificate, its key, the chain, the root - in any order, or all in one file) or as a PFX / PKCS#12 file, with its password or without; or the request is made here and only what the authority sends back is uploaded. It is put in nginx and nginx is asked before it is reloaded - one it does not take is never put in.':
        'Certifikát se posílá jako soubory PEM (certifikát, jeho klíč, řetězec, kořen – v libovolném pořadí, nebo vše v jednom souboru) nebo jako soubor PFX / PKCS#12, s heslem i bez; nebo se žádost vytvoří zde a nahraje se jen to, co autorita pošle zpět. Vloží se do nginx a nginx se zeptá, než se znovu načte – ten, který nevezme, se nikdy nevloží.',
    "the certificate answered on vm's own name and address":
        'certifikát, kterým odpovídá vlastní název a adresa vm',
    'The built-in value: false':
        'Vestavěná hodnota: vypnuto',
    'What runs in it is ended on the server - for every window looking at it. Its last screen stays in the list for a while.':
        'Co v něm běží, se na serveru ukončí – pro všechna okna, která se na něj dívají. Jeho poslední obrazovka zůstane chvíli v seznamu.',
    ' - Claude Code picks up the conversation where it was (--continue).':
        ' – Claude Code naváže na konverzaci tam, kde byla (--continue).',
    # ---- 1.0.5: chats like claude.ai ----
    'Pinned':
        'Připnuté',
    'The others':
        'Ostatní',
    'Pin':
        'Připnout',
    'Unpin':
        'Odepnout',
    'Rename':
        'Přejmenovat',
    'Open it':
        'Otevřít',
    'Open in a new window':
        'Otevřít v novém okně',
    'Its last screen':
        'Jeho poslední obrazovka',
    'The files of this chat':
        'Soubory tohoto chatu',
    'A new Claude Code in its folder':
        'Nový Claude Code v jeho složce',
    'Copy the command to attach it on the server':
        'Zkopírovat příkaz k připojení na serveru',
    'Start it again':
        'Spustit znovu',
    'Take it off the list':
        'Odebrat ze seznamu',
    'End it':
        'Ukončit ho',
    'Copy':
        'Kopírovat',
    'Paste':
        'Vložit',
    'Select everything on the screen':
        'Vybrat vše na obrazovce',
    'Copy everything on the screen':
        'Zkopírovat celou obrazovku',
    'Give Claude a file…':
        'Předat Claude soubor…',
    "Claude Code's commands":
        'Příkazy Claude Code',
    'Write a longer text':
        'Napsat delší text',
    'Over the whole window':
        'Přes celé okno',
    'Back from the whole window':
        'Zpět z celého okna',
    'Clear the screen':
        'Vymazat obrazovku',
    'New terminal':
        'Nový terminál',
    'The sign-in page':
        'Přihlašovací stránka',
    "The picture above the sign-in of these pages: one of ai's drawings, a picture of your own, or none.":
        'Obrázek nad přihlášením těchto stránek: jedna z kreseb ai, vlastní obrázek, nebo žádný.',
    'The picture on the sign-in':
        'Obrázek na přihlášení',
    'Upload a picture of your own':
        'Nahrát vlastní obrázek',
    'Back to the default':
        'Zpět na výchozí',
    'Take my own picture away':
        'Odebrat vlastní obrázek',
    'Claude Code in the browser, the server behind it (as ai came)':
        'Claude Code v prohlížeči, za ním server (jak ai přišlo)',
    'The terminal, Claude Code at the prompt':
        'Terminál, Claude Code na příkazové řádce',
    'A task asked, Claude Code at work on it':
        'Zadaný úkol, Claude Code na něm pracuje',
    'Terminals that go on when the browser closes':
        'Terminály, které běží dál i po zavření prohlížeče',
    'One server, from the desk, the laptop and the tablet':
        'Jeden server – z počítače, notebooku i tabletu',
    'The spark of Claude':
        'Jiskra Claude',
    'A chat on the tablet, scrolled by finger':
        'Chat na tabletu, posouvaný prstem',
    'A change to the code, line by line':
        'Změna kódu, řádek po řádku',
    'The folder of the chats and what is under it':
        'Složka chatů a co je pod ní',
    'A task shared out to agents':
        'Úkol rozdělený agentům',
    'What the chats used, day by day':
        'Co chaty spotřebovaly, den po dni',
    'Signed in, the keys of the server safe':
        'Přihlášeno, klíče serveru v bezpečí',
    'No picture':
        'Žádný obrázek',
    'A picture of your own':
        'Vlastní obrázek',
    'taken away when saved':
        'po uložení odebrán',
    'nothing uploaded yet':
        'zatím nic nenahráno',
    'only the sign-in':
        'jen přihlášení',
    'after saving':
        'po uložení',
    'shown':
        'zobrazený',
    'the default':
        'výchozí',
    'saved - the sign-in shows it':
        'uloženo – přihlášení ho ukazuje',
    'The server listens on':
        'Server naslouchá na',
    'IPv4, this machine only':
        'IPv4, jen tento stroj',
    'not IPv4 only':
        'ne jen IPv4',
    'Only IPv4 (127.0.0.1)':
        'Jen IPv4 (127.0.0.1)',
    'The database server on IPv4 only?':
        'Databázový server jen na IPv4?',
    'It is told to listen on 127.0.0.1 only - nothing over IPv6, nothing from outside this machine - and started again: these pages wait a few seconds for it.':
        'Nastaví se, aby naslouchal jen na 127.0.0.1 – nic přes IPv6, nic zvenku – a spustí se znovu: stránky na něj pár sekund počkají.',
    'the database server listens on 127.0.0.1 only now':
        'databázový server teď naslouchá jen na 127.0.0.1',
    'Change it…':
        'Upravit…',
    'Change it - model, effort, permissions, folder…':
        'Upravit – model, úsilí, oprávnění, složka…',
    'Change it - name, folder…':
        'Upravit – název, složka…',
    'Change':
        'Upravit',
    'Its conversation goes with it to the new folder.':
        'Jeho konverzace se přesune s ním do nové složky.',
    'More words for Claude Code':
        'Další parametry pro Claude Code',
    'It is started again with these, going on with its conversation.':
        'Spustí se znovu s těmito volbami a bude pokračovat ve své konverzaci.',
    'Claude Code takes these only when it starts: it is started again in its own tile and goes on with its conversation. What it is doing right now is stopped.':
        'Claude Code tyto volby bere jen při spuštění: spustí se znovu ve své dlaždici a bude pokračovat ve své konverzaci. To, co právě dělá, se přeruší.',
    'A new folder starts the shell again in it.':
        'Nová složka spustí shell znovu v ní.',
    'Save and start it again':
        'Uložit a spustit znovu',
    'changed':
        'změněno',
    'The server':
        'Server',
    'Claude Code - the chats':
        'Claude Code – chaty',
    'Files only in the folder of the chats':
        'Soubory jen ve složce chatů',
    'On: the Files tab, the files of a chat, downloads and uploads reach the folder of the chats and what is under it only - for every account, administrators too; the daemon refuses any other path. Off: an administrator anywhere, a user in their own folders. Means nothing while the folder of the chats is empty.':
        'Zapnuto: záložka Soubory, soubory chatu, stahování i nahrávání sahají jen do složky chatů a pod ni – pro každý účet, i pro administrátory; démon jinou cestu odmítne. Vypnuto: administrátor kamkoli, uživatel do svých složek. Bez vyplněné složky chatů nemá význam.',
    'pastes, as in PuTTY - what is selected is copied by itself; Ctrl + right button: the menu':
        'vkládá jako v PuTTY – označený text se sám zkopíruje; Ctrl + pravé tlačítko: menu',
    'opens the menu (copy, paste, the chat...)':
        'otevře menu (kopírovat, vložit, chat…)',
    'The right mouse button in a terminal':
        'Pravé tlačítko myši v terminálu',
    'right button':
        'pravé tlačítko',
    'the browser did not let the page read the clipboard - allow it for this page, or Ctrl+V':
        'prohlížeč stránce nedovolil číst schránku – povolte to pro tuto stránku, nebo Ctrl+V',
    'Folders used lately':
        'Nedávno použité složky',
    'Back from the whole screen':
        'Zpět z celé obrazovky',
    'Only the terminal, over the whole screen':
        'Jen terminál přes celou obrazovku',
    'Only the terminal, over the whole screen - no bar, no buttons. Hold Esc to come back (or Esc twice where the browser cannot take the whole screen); the × in the corner when the mouse moves does it too.':
        'Jen terminál přes celou obrazovku – bez lišty a tlačítek. Zpět podržením Esc (nebo dvakrát Esc, kde prohlížeč celou obrazovku neumí); totéž udělá × v rohu, které se ukáže při pohybu myši.',
    'Ended lately':
        'Nedávno ukončené',
    'all of them':
        'všechny',
    'Start it again where it stopped':
        'Spustit znovu tam, kde skončil',
    'Classic - as PuTTY':
        'Klasické – jako PuTTY',
    'The Linux console':
        'Konzole Linuxu',
    "Soft - the pages' own":
        'Jemné – jako stránky',
    'Light':
        'Světlé',
    'Solarized dark':
        'Solarized tmavé',
    'The colours of the terminals - for every terminal you open, kept with your account:':
        'Barvy terminálů – pro každý terminál, který otevřete, uložené u vašeho účtu:',
    'Colours of the terminals':
        'Barvy terminálů',
    'For every terminal you open, kept with your account.':
        'Pro každý terminál, který otevřete; uloženo u vašeho účtu.',
    'no ended terminal in the list':
        'v seznamu není žádný ukončený terminál',
    'Their last screens go with them. Nothing that runs is touched, and the conversations of Claude Code stay - they are picked up again under Conversations.':
        'Jejich poslední obrazovky zmizí s nimi. Nic běžícího se nezmění a konverzace Claude Code zůstanou – navážete na ně v Konverzacích.',
    'Take them off':
        'Odebrat je',
    'Opus - the newest':
        'Opus – nejnovější',
    'Sonnet - the newest':
        'Sonnet – nejnovější',
    'Haiku - the newest':
        'Haiku – nejnovější',
    'Fable - the newest':
        'Fable – nejnovější',
    'A family (always its newest) or one version. Any other name of a model can be written in the JSON below.':
        'Rodina (vždy její nejnovější) nebo jedna verze. Jakýkoli jiný název modelu lze zapsat do JSON níže.',
    'Back to the start page. Only this window is closed: the chat goes on running on the server, and is opened again from the list.':
        'Zpět na úvodní stránku. Zavře se jen toto okno: chat běží na serveru dál a otevřete ho znovu ze seznamu.',
    'Only in':
        'Jen ve složce',
    'and the folders under it.':
        'a ve složkách pod ní.',
    'Anywhere on the server.':
        'Kdekoli na serveru.',
    'Limit it to one folder':
        'Omezit na jednu složku',
    "Claude Code written into the terminal's history":
        'Claude Code zapisuje do historie terminálu',
    "On: Claude Code draws itself the classic way (CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1), so what it says goes into tmux's history - the scroll bar beside the terminal shows where you are, History shows all of it, a finger scrolls it on a tablet. Off: its full-screen look, which keeps the history itself (the bar is then only a jog wheel). /tui in Claude Code switches one chat.":
        'Zapnuto: Claude Code se vykresluje klasicky (CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1), takže co píše, jde do historie tmuxu – posuvník vedle terminálu ukazuje, kde jste, Historie ukáže všechno, na tabletu se posouvá prstem. Vypnuto: jeho celoobrazovkový vzhled, který si historii drží sám (posuvník je pak jen kolečko). /tui v Claude Code přepne jeden chat.',
    "From Claude Code's own transcripts of these Linux accounts:":
        'Z vlastních záznamů Claude Code těchto účtů Linuxu:',
    "The cost is an estimate at Anthropic's list prices per token, to compare by - a Claude subscription is not billed by the token.":
        'Cena je odhad podle ceníku Anthropic za token, pro srovnání – předplatné Claude se po tokenech neúčtuje.',
    'No price known for:':
        'Neznámá cena pro:',
    'By account':
        'Po účtech',
    'By hour of the day':
        'Po hodinách dne',
    'Cache share':
        'Podíl cache',
    'Chat':
        'Chat',
    'Chats':
        'Chaty',
    'Claude Code: what the chats used':
        'Claude Code: co chaty spotřebovaly',
    'Copy its ID':
        'Zkopírovat ID',
    'Copy the command to pick it up':
        'Zkopírovat příkaz k navázání',
    'Cost':
        'Cena',
    'Count again':
        'Spočítat znovu',
    'Estimated cost':
        'Odhad ceny',
    'Its folder in Files':
        'Jeho složka v Souborech',
    'Only the first 300 shown - find a chat to narrow it.':
        'Zobrazeno jen prvních 300 – zúžte hledáním.',
    'Open its terminal':
        'Otevřít jeho terminál',
    'Per chat':
        'Na chat',
    'Pick it up again (--resume)':
        'Navázat (--resume)',
    'The chats':
        'Chaty',
    'Written by Claude':
        'Napsal Claude',
    'cost':
        'cena',
    'tokens':
        'tokeny',
    'counting the chats…':
        'počítám chaty…',
    'find a chat - words, folder, model…':
        'najít chat – slova, složka, model…',
    'its terminal ended':
        'terminál skončil',
    'newest first':
        'nejnovější první',
    'no account':
        'žádného účtu',
    'the dearest first':
        'nejdražší první',
    'the longest first':
        'nejdelší první',
    'the most written first':
        'nejvíc napsáno první',
    'A new Claude Code…':
        'Nový Claude Code…',
    'A new shell…':
        'Nový shell…',
    'Only the running ones':
        'Jen běžící',
    'With the ended ones':
        'I s ukončenými',
    'Find a terminal':
        'Najít terminál',
    'Let the list hide itself':
        'Nechat seznam schovávat',
    'Keep the list open':
        'Nechat seznam otevřený',
    'Open the folder':
        'Otevřít složku',
    'Copy its path':
        'Zkopírovat cestu',
    'A new Claude Code in it':
        'Nový Claude Code v ní',
    'Download it as a .zip':
        'Stáhnout jako .zip',
    'Download it':
        'Stáhnout',
    'Delete':
        'Smazat',
    'Delete it':
        'Smazat',
    'An empty folder. Drop files here to put them in.':
        'Prázdná složka. Přetáhněte sem soubory, aby se do ní nahrály.',
    'What to do with it':
        'Co s ním',
    'Pin it, rename it, its files, start it again, end it… - the right mouse button on it does the same.':
        'Připnout, přejmenovat, jeho soubory, spustit znovu, ukončit… – totéž nabídne pravé tlačítko myši.',
    'renamed':
        'přejmenováno',
    'copied':
        'zkopírováno',
    'the screen was copied':
        'obrazovka byla zkopírována',
    'the browser would not copy it':
        'prohlížeč to nezkopíroval',
    'this browser lets only Ctrl+V paste':
        'tento prohlížeč dovolí vkládat jen přes Ctrl+V',
    'the browser did not let the page read the clipboard - Ctrl+V does':
        'prohlížeč stránce nedovolil číst schránku – Ctrl+V funguje',
    'Keep this list open':
        'Nechat seznam otevřený',
    'The list is staying open. Press again to let it hide itself at the edge of the screen.':
        'Seznam zůstává otevřený. Dalším stiskem se bude schovávat u okraje obrazovky.',
    'The list hides itself at the edge of the screen and slides out when you point at it. Press this to keep it open.':
        'Seznam se schovává u okraje obrazovky a vysune se, když na něj najedete myší. Stiskem ho necháte otevřený.',
    'Keep the list of terminals open beside the terminal, or let it hide itself at the edge (it slides out when you point at it).':
        'Nechat seznam terminálů otevřený vedle terminálu, nebo ho nechat schovávat u okraje (vysune se, když na něj najedete myší).',
    'The files of this chat: its own folder and what is in it, beside the terminal - nothing above it.':
        'Soubory tohoto chatu: jeho vlastní složka a co v ní je, vedle terminálu – nic nad ní.',
    'One folder up - never above the folder of this chat.':
        'O složku výš – nikdy nad složku tohoto chatu.',
    'Upload files into the folder shown. Dropping them onto this list does the same.':
        'Nahrát soubory do zobrazené složky. Totéž udělá jejich přetažení na tento seznam.',
    'A new folder here.':
        'Nová složka zde.',
    'Read the folder again.':
        'Načíst složku znovu.',
    'Close the files of this chat.':
        'Zavřít soubory tohoto chatu.',
    'Sign out of this browser. The terminals and Claude Code go on running on the server, and you may be signed in from other places at the same time - they stay signed in.':
        'Odhlásit tento prohlížeč. Terminály a Claude Code běží na serveru dál a můžete být zároveň přihlášeni i odjinud – ta přihlášení zůstanou.',
    'Where you are signed in':
        'Kde jste přihlášeni',
    'You may be signed in from several places at once - every one sees the same terminals, live. Signing out or closing the browser ends no terminal: Claude Code goes on working on the server.':
        'Můžete být přihlášeni z více míst najednou – každé vidí stejné terminály, živě. Odhlášení ani zavření prohlížeče žádný terminál neukončí: Claude Code na serveru pracuje dál.',
    'Sign out everywhere':
        'Odhlásit všude',
    'Sign out everywhere?':
        'Odhlásit všude?',
    'Every sign-in of yours ends - here and on every other computer. The terminals go on running.':
        'Skončí všechna vaše přihlášení – zde i na všech ostatních počítačích. Terminály běží dál.',
    'signed out - the terminal goes on running':
        'odhlášeno – terminál běží dál',
    # ---- 1.0.6: the database, the outgoing mail, the texts, the upgrades as otp's ----
    'Codes sent after the password, by e-mail or SMS: how long they last, how many, and the SMS gateway.':
        'Kódy posílané po hesle e-mailem nebo SMS: jak dlouho platí, kolik jich smí přijít a SMS brána.',
    'Every word people get from this server - the mails and the SMS of a code - in Czech and in English, edited as they will look.':
        'Každé slovo, které lidé od tohoto serveru dostanou – e-maily a SMS s kódem – česky i anglicky, upravované tak, jak budou vypadat.',
    "How the mails of these pages leave this machine: a mail server, or straight to the recipients' - the codes of the second step and the notices.":
        'Jak e-maily těchto stránek odcházejí z tohoto stroje: přes poštovní server, nebo rovnou na servery příjemců – kódy druhého kroku a upozornění.',
    'Who may open these pages, what each of them may do, which Linux account their terminals run as, and who is signed in right now.':
        'Kdo smí otevřít tyto stránky, co kdo smí, pod kterým účtem Linuxu běží jeho terminály a kdo je právě přihlášen.',
    'The certificate of these pages, and how TLS is spoken.':
        'Certifikát těchto stránek a jak se mluví TLS.',
    "Who may reach these pages; and the machine's firewall (iptables or firewalld) - what ai needs opens by itself.":
        'Kdo se k těmto stránkám dostane; a firewall stroje (iptables nebo firewalld) – co ai potřebuje, se otevře samo.',
    "The server's address, gateway, DNS servers, host name and IPv6.":
        'Adresa serveru, brána, servery DNS, název hostitele a IPv6.',
    'The clock: chrony, its time servers, how far off it is - codes from the app are worked out from it.':
        'Hodiny: chrony, jeho časové servery, o kolik se odchylují – kódy z aplikace se počítají podle nich.',
    "The operating system's packages updated, its output shown as it goes; a restart offered when one is needed.":
        'Aktualizace balíků operačního systému s výstupem průběžně; restart se nabídne, když je potřeba.',
    'Which database everything lives in, how big it is, copies of it, and how long things are kept.':
        'V jaké databázi všechno je, jak je velká, její kopie a jak dlouho se co uchovává.',
    'Backups of everything to another machine - FTP, FTPS, SFTP, SCP, SMB or a folder - locked with a password, on a schedule, and putting one back.':
        'Zálohy všeho na jiný stroj – FTP, FTPS, SFTP, SCP, SMB nebo složka – zamčené heslem, podle plánu, a jejich obnova.',
    'Everything that makes this installation what it is, as one file to carry to another machine.':
        'Všechno, co dělá tuto instalaci tím, čím je, jako jeden soubor k přenesení na jiný stroj.',
    'A new version, put in from here: from the web or a package sent, or back to an older one.':
        'Nová verze nasazená odsud: z webu nebo z poslaného balíku, nebo návrat ke starší.',
    'Version, what is running, the language, the log.':
        'Verze, co běží, jazyk, log.',
    'Put this one back, without downloading it and uploading it again: everything in the live database is replaced by what is in this file. You are shown what is in it and asked first, and a copy of what is being replaced is made before anything changes.':
        'Vrátit tento soubor bez stahování a nového nahrávání: všechno v živé databázi se nahradí tím, co je v tomto souboru. Nejdřív se ukáže, co v něm je, a zeptá se vás, a než se cokoli změní, udělá se kopie toho, co se nahrazuje.',
    'Codes of the second step of signing in sent by e-mail or SMS: how long they last, how many, and the SMS gateway.':
        'Kódy druhého kroku přihlášení posílané e-mailem nebo SMS: jak dlouho platí, kolik jich smí přijít a SMS brána.',
    'Every mail sent - a code to sign in with, a notice, a test - and what became of it: sent, waiting for another try (greylisting, a server away), failed. Sent again or taken away by hand.':
        'Každý odeslaný e-mail – kód pro přihlášení, upozornění, zkouška – a co se s ním stalo: odesláno, čeká na další pokus (greylisting, nedostupný server), selhalo. Ručně odeslat znovu nebo odebrat.',
    'a sample sign-in code':
        'ukázkový kód pro přihlášení',
    'a sample address check':
        'ukázkové ověření adresy',
    'What people get from this server - the mails and the SMS of a code, in Czech and English. Click into a text to write; the blue parts are filled in when it is sent.':
        'Co lidé od tohoto serveru dostávají – e-maily a SMS s kódem, česky i anglicky. Klikněte do textu a pište; modré části se doplní při odeslání.',
    'Every mail this server sends - a code to sign in with, a code to check an address, the notices, a test - goes through here. What the receiving side does not take at once (greylisting\'s "try again later", a server away, a full mailbox) waits and is tried again by itself; what it refuses for good is shown as failed. What a mail held is never kept once it went. The SMS are in the events.':
        'Každý e-mail, který tento server posílá – kód pro přihlášení, kód pro ověření adresy, upozornění, zkouška – jde tudy. Co přijímající strana hned nevezme („zkuste to později“ u greylistingu, nedostupný server, plná schránka), čeká a zkouší se znovu samo; co odmítne natrvalo, je vidět jako selhané. Obsah e-mailu se po odeslání nikdy neuchovává. SMS jsou v událostech.',
    'The second step of signing in may be a code sent after the password, instead of the app (Settings → Accounts → The second step of signing in). E-mail goes the way set under Mail; SMS through a gateway or a modem set up here.':
        'Druhým krokem přihlášení může být kód poslaný po hesle místo aplikace (Nastavení → Účty → Druhý krok přihlášení). E-mail jde tak, jak je nastaveno v Poště; SMS přes bránu nebo modem nastavené zde.',
    'One database holds everything: the accounts and their sign-ins, the settings, the events, the mails sent and the list of terminals. It is a file on this machine unless you say otherwise. The secrets in it are sealed with a key kept beside it, in the state folder - and every copy and every dump is kept with that key beside it.':
        'Všechno drží jedna databáze: účty a jejich přihlášení, nastavení, události, odeslanou poštu a seznam terminálů. Je to soubor na tomto stroji, pokud neurčíte jinak. Tajné údaje v ní jsou zapečetěné klíčem uloženým vedle ní ve složce stavu – a každá kopie a každý dump se uchovává s tímto klíčem vedle sebe.',
    'A dump from somewhere else — one downloaded from here, or a file copied off the dumps folder. It replaces everything: every account, every event, every setting and every terminal. Nothing happens until it has been read, checked and shown to you.':
        'Dump odjinud – stažený odsud nebo soubor zkopírovaný ze složky dumpů. Nahradí všechno: každý účet, každou událost, každé nastavení a každý terminál. Nic se nestane, dokud nebude přečten, zkontrolován a ukázán vám.',
    'Copy everything that is here into that database: every account, every event, every setting and every terminal. What is here is left exactly as it is.':
        'Zkopírovat všechno, co je tady, do té databáze: každý účet, každou událost, každé nastavení a každý terminál. Co je tady, zůstane přesně tak, jak je.',
    'Make a copy now and save it to the machine you are sitting at, with the key that opens the secrets inside it. Nothing is kept here.':
        'Udělat kopii hned a uložit ji do počítače, u kterého sedíte, s klíčem, který otevírá tajné údaje v ní. Tady se nic neuchová.',
    'Throws away exactly what the "keep for" numbers already say is too old — the events and the lines of the mails sent, each by its own number of days. It happens by itself every hour; this is the same thing, now. Lowering one of those numbers deletes nothing by itself: this is what does it.':
        'Zahodí přesně to, co čísla „uchovávat“ už označují za příliš staré – události a řádky odeslané pošty, každé podle vlastního počtu dní. Děje se to samo každou hodinu; tohle je totéž hned. Snížení některého z čísel samo nic nesmaže: smaže to až tohle.',
    'Forgets the events and the lines of the mails sent older than an age you choose here, whatever the "keep for" numbers say. Only those two kinds of record: the accounts, the terminals and the settings are not touched.':
        'Zapomene události a řádky odeslané pošty starší, než zde zvolíte, bez ohledu na čísla „uchovávat“. Jen tyto dva druhy záznamů: účtů, terminálů a nastavení se to nedotkne.',
    'A database from somewhere else — one downloaded from here, or a file copied off the backups folder. It replaces everything: every account, every event, every setting and every terminal. Nothing happens until it has been read, checked and shown to you.':
        'Databáze odjinud – stažená odsud nebo soubor zkopírovaný ze složky záloh. Nahradí všechno: každý účet, každou událost, každé nastavení a každý terminál. Nic se nestane, dokud nebude přečtena, zkontrolována a ukázána vám.',
    'The accounts, the terminals and every setting are never touched by this.':
        'Účtů, terminálů a žádného nastavení se to nikdy nedotkne.',
    'They are not options you could tick by mistake: they are not in the list at all.':
        'Nejsou to volby, které byste mohli omylem zaškrtnout: v seznamu vůbec nejsou.',
    'A new version put in from here: send the package, or take it from the web, and this server is upgraded - checked first, then its own install.sh --upgrade, as by hand. The terminals go on running; these pages come back after a few seconds. The command line (install.sh --upgrade) works as it always has.':
        'Nová verze nasazená odsud: pošlete balík nebo ho vezměte z webu a tento server se upgraduje – nejdřív kontrola, pak jeho vlastní install.sh --upgrade, jako ručně. Terminály běží dál; tyto stránky se vrátí za pár sekund. Příkazová řádka (install.sh --upgrade) funguje jako vždy.',
    "The version it runs and how it is. An upgrade does not stop the terminals: tmux is not the daemon's, and the daemon finds them again when it starts.":
        'Verze, kterou běží, a jak na tom je. Upgrade terminály nezastaví: tmux nepatří démonovi a démon je po startu znovu najde.',
    'Where new versions are published - the address below - is looked at once a day. A newer ai found there is offered here, and put in with one click: fetched, its signature checked like a package sent by hand, then this server upgraded. Nothing is put in by itself unless the setting below says so.':
        'Místo, kde vycházejí nové verze – adresa níže – se prohlíží jednou denně. Novější ai, které se tam najde, se nabídne zde a nasadí jedním kliknutím: stáhne se, podpis se zkontroluje jako u balíku poslaného ručně a pak se tento server upgraduje. Samo se nic nenasadí, pokud to neříká nastavení níže.',
    'The .tar.gz of a new ai, as it was released. It is checked before anything else: it must be signed by a release key this server trusts, every file in it must be the one signed, and it must not be older than what runs here (unless going back is allowed, and then only to a safe version). Root checks it all again before it is put in.':
        '.tar.gz nového ai tak, jak vyšlo. Nejdřív se zkontroluje: musí být podepsané klíčem vydání, kterému tento server věří, každý soubor v něm musí být ten podepsaný a nesmí být starší než to, co tu běží (pokud není povolen návrat, a pak jen na bezpečnou verzi). Root to celé zkontroluje znovu, než se nasadí.',
    "Only to a version that is safe: one that reads what the newer versions wrote into the database the same, and has every security fix that matters - each version says how far back it may go, and the highest of what ran on this database counts. The database is not put back nor changed: its tables stay as they are and the older version runs on them (a copy of it is made first). The package is checked like an upgrade's before anything is put in.":
        'Jen na verzi, která je bezpečná: takovou, která čte, co novější verze zapsaly do databáze, stejně, a má každou opravu bezpečnosti, na které záleží – každá verze říká, jak daleko zpět smí, a platí nejvyšší z toho, co na této databázi běželo. Databáze se nevrací ani nemění: její tabulky zůstanou, jak jsou, a starší verze na nich běží (předtím se udělá její kopie). Balík se před nasazením zkontroluje jako při upgradu.',
    'The output of install.sh, the last time this server was upgraded from these pages.':
        'Výstup install.sh při posledním upgradu tohoto serveru z těchto stránek.',
    'The same, by hand, as root:':
        'Totéž ručně, jako root:',
    'Which database everything is kept in: a SQLite file on this machine, or a MariaDB or a PostgreSQL server. Kept in config.json, not in the database - changed only by the steps of the card below (try it, set it up, carry everything across, start using it).':
        'V jaké databázi je všechno uloženo: soubor SQLite na tomto stroji, nebo server MariaDB či PostgreSQL. Uloženo v config.json, ne v databázi – mění se jen kroky karty níže (vyzkoušet, nastavit, přenést všechno, začít používat).',
    'Its name or address. Empty: this machine.':
        'Jeho jméno nebo adresa. Prázdné: tento stroj.',
    "0: the engine's own (3306, 5432).":
        '0: výchozí enginu (3306, 5432).',
    'Letters, digits and _ only.':
        'Jen písmena, číslice a _.',
    'Kept in config.json (root only). Set it up makes one.':
        'Uloženo v config.json (jen pro roota). Nastavit… ho vytvoří.',
    'How long a connection is waited for.':
        'Jak dlouho se čeká na spojení.',
    'How the connection to the server is encrypted.':
        'Jak je spojení se serverem šifrované.',
    'A PEM file on this machine.':
        'Soubor PEM na tomto stroji.',
    "A copy of everything - every row of every table, in a shape any of the three engines takes back - with the key its secrets are sealed with beside it, into /var/lib/ai/backups; and a dump by the engine's own program into /var/lib/ai/dumps.":
        'Kopie všeho – každý řádek každé tabulky ve tvaru, který vezme zpět kterýkoli ze tří enginů – s klíčem, kterým jsou zapečetěné její tajné údaje, vedle sebe do /var/lib/ai/backups; a dump vlastním programem enginu do /var/lib/ai/dumps.',
    'Of each kind; older ones are taken away.':
        'Od každého druhu; starší se odeberou.',
    'Going back to an older version on these pages - only to one that is safe on this database. Off: the card is not shown, and ai --downgrade alone does it.':
        'Návrat ke starší verzi na těchto stránkách – jen k té, která je na této databázi bezpečná. Vypnuto: karta se neukáže a dělá to jen ai --downgrade.',
    'The language of a mail or SMS with a code, where the page it was asked from says none.':
        'Jazyk e-mailu nebo SMS s kódem, pokud stránka, odkud se o něj žádalo, žádný neuvádí.',
    'A mail the other side did not take yet (greylisting, a server away, a full mailbox) is tried again by itself, ever less often, for this long; then it is given up.':
        'E-mail, který druhá strana zatím nevzala (greylisting, nedostupný server, plná schránka), se zkouší znovu sám, stále méně často, po tuto dobu; pak se vzdá.',
    'Outgoing mail lists what went and what did not; what a mail held is never kept once it went.':
        'Odchozí pošta ukazuje, co odešlo a co ne; obsah e-mailu se po odeslání nikdy neuchovává.',
    'Wait for it (s)':
        'Čekat na ni (s)',
    'Encrypted':
        'Šifrováno',
    'as the driver decides':
        'jak rozhodne ovladač',
    'encrypted, the certificate not checked':
        'šifrovaně, certifikát se nekontroluje',
    'encrypted, signed by the authority below':
        'šifrovaně, podepsáno autoritou níže',
    'encrypted, the authority and the name checked':
        'šifrovaně, kontroluje se autorita i jméno',
    'The authority of its certificate (a file)':
        'Autorita jeho certifikátu (soubor)',
    'HTML - with the plain text beside it':
        'HTML – s prostým textem vedle',
    'Kept in the database: they go with every copy of it, and to another engine with it.':
        'Uloženo v databázi: jdou s každou její kopií a s ní i do jiného enginu.',
    'Sent when somebody signs in to these pages with the second step by mail.':
        'Posílá se, když se někdo přihlašuje na tyto stránky s druhým krokem e-mailem.',
    'Used instead of the texts above when there is no name or account to put in.':
        'Použije se místo textů výše, když není jméno ani účet k doplnění.',
    'What a mail program shows that does not show HTML, and what is sent alone when Settings → Codes by e-mail and SMS says a mail with a code is plain text.':
        'Co ukáže poštovní program, který neumí HTML, a co se posílá samo, když Nastavení → Kódy e-mailem a SMS říká, že e-mail s kódem je prostý text.',
    'Save this copy to the machine you are sitting at - with the key that opens its secrets, locked with a passphrase you give, or without it.':
        'Uložit tuto kopii do počítače, u kterého sedíte – s klíčem, který otevírá její tajné údaje, zamčeným heslovou frází, kterou zadáte, nebo bez něj.',
    'Save this dump to the machine you are sitting at - with the key that opens its secrets, locked with a passphrase you give, or without it.':
        'Uložit tento dump do počítače, u kterého sedíte – s klíčem, který otevírá jeho tajné údaje, zamčeným heslovou frází, kterou zadáte, nebo bez něj.',
    'This dump was taken off a different engine from the one this installation is on now, so it cannot be put back here. Put that engine back on, or use a copy — a copy goes into any of the three.':
        'Tento dump pochází z jiného enginu, než na kterém je tato instalace teď, takže ho sem vrátit nejde. Vraťte ten engine, nebo použijte kopii – kopie jde do kteréhokoli ze tří.',
    'MariaDB: the driver is installed':
        'MariaDB: ovladač je nainstalovaný',
    'PostgreSQL: the driver is installed':
        'PostgreSQL: ovladač je nainstalovaný',
    'terminals':
        'terminály',
    'wrong passwords counted':
        'počítaná chybná hesla',
    'mails waiting to go':
        'pošta čekající na odeslání',
    'The key that opens the secrets:':
        'Klíč, který otevírá tajné údaje:',
    'The key that opens the secrets is MISSING:':
        'Klíč, který otevírá tajné údaje, CHYBÍ:',
    'what this program noted about itself: sign-ins, terminals started and ended, changes, copies, starts and stops.':
        'co si tento program zapsal o sobě: přihlášení, spuštěné a ukončené terminály, změny, kopie, starty a zastavení.',
    'the outgoing mail':
        'odchozí pošta',
    'every mail sent or waiting, where it went and what the other side said. One still waiting is not sent any more.':
        'každý odeslaný nebo čekající e-mail, kam šel a co řekla druhá strana. Čekající se už neodešle.',
    'the ended terminals':
        'ukončené terminály',
    'the list of terminals that have ended, with their last screens. Running ones are not touched.':
        'seznam ukončených terminálů s jejich poslední obrazovkou. Běžících se to nedotkne.',
    'One file that is all of it: the copy and the key that opens its secrets, locked with the passphrase below. Put back here or on another machine (Put a copy back), the passphrase opens the key again. Lost, the key in the file is lost with it - it is not kept anywhere.':
        'Jeden soubor, ve kterém je všechno: kopie a klíč k jejím tajným údajům, zamčený heslovou frází níže. Při vrácení tady nebo na jiném stroji (Obnovit kopii) fráze klíč zase otevře. Ztratí-li se, je ztracen i klíč v souboru – nikde jinde se neuchovává.',
    'The copy alone opens no secret on another machine: the key is the .key file beside it in /var/lib/ai/backups (or /var/lib/ai/secrets.key). Keep the two together.':
        'Kopie sama na jiném stroji žádný tajný údaj neotevře: klíčem je soubor .key vedle ní v /var/lib/ai/backups (nebo /var/lib/ai/secrets.key). Držte je pohromadě.',
    'One file that is all of it: the dump and the key that opens its secrets, locked with the passphrase below. Put back here or on another machine (Put a dump back), the passphrase opens the key again. Lost, the key in the file is lost with it - it is not kept anywhere.':
        'Jeden soubor, ve kterém je všechno: dump a klíč k jeho tajným údajům, zamčený heslovou frází níže. Při vrácení tady nebo na jiném stroji (Obnovit dump) fráze klíč zase otevře. Ztratí-li se, je ztracen i klíč v souboru – nikde jinde se neuchovává.',
    'The dump alone opens no secret on another machine: the key is the .key file beside it in /var/lib/ai/dumps (or /var/lib/ai/secrets.key). Keep the two together.':
        'Dump sám na jiném stroji žádný tajný údaj neotevře: klíčem je soubor .key vedle něj v /var/lib/ai/dumps (nebo /var/lib/ai/secrets.key). Držte je pohromadě.',
    'The events and the lines of the mails sent older than this are deleted now, whatever the keep-for numbers say. The accounts, the settings and the terminals are not touched.':
        'Události a řádky odeslané pošty starší než toto se smažou hned, bez ohledu na čísla „uchovávat“. Účtů, nastavení a terminálů se to nedotkne.',
    'Each table is rebuilt and held shut while it is; sign-ins and the pages wait for it meanwhile - do it when few are signed in. It needs room for a second copy of the biggest table. Worth doing after throwing a lot away, and not otherwise.':
        'Každá tabulka se přestaví a po tu dobu je zavřená; přihlašování a stránky na ni mezitím čekají – dělejte to, když je přihlášeno málo lidí. Potřebuje místo na druhou kopii největší tabulky. Vyplatí se po zahození většího množství dat, jinak ne.',
    'Administrators':
        'Administrátoři',
    'You will probably be signed out: who is signed in came with the file like everything else. The key that opens the secrets is taken from beside the file, or from inside a downloaded copy; where there is none, the key in use stays.':
        'Pravděpodobně budete odhlášeni: kdo je přihlášen, přišlo se souborem jako všechno ostatní. Klíč k tajným údajům se vezme zpoza souboru nebo ze stažené kopie; kde žádný není, zůstane klíč, který se používá.',
    'The accounts, the terminals and every setting are not touched.':
        'Účtů, terminálů ani nastavení se to nedotkne.',
    'Sent when somebody sets up the second step by mail, to check the address.':
        'Posílá se, když si někdo nastavuje druhý krok e-mailem, k ověření adresy.',
    'The mail as it is written now - saved or not - with sample values (a code that opens nothing, a name), to one address.':
        'E-mail tak, jak je teď napsaný – uložený nebo ne – s ukázkovými hodnotami (kód, který nic neotevře, jméno), na jednu adresu.',
    'Sent when somebody signs in to these pages with the second step by SMS.':
        'Posílá se, když se někdo přihlašuje na tyto stránky s druhým krokem přes SMS.',
    'Sent when somebody sets up the second step by SMS, to check the number.':
        'Posílá se, když si někdo nastavuje druhý krok přes SMS, k ověření čísla.',
    'too old':
        'příliš stará',
    'The sign-in code by mail':
        'Kód pro přihlášení e-mailem',
    'The sign-in code by SMS':
        'Kód pro přihlášení přes SMS',
    'Upgrades and maintenance':
        'Upgrady a údržba',
    'Upgrade this server':
        'Upgradovat tento server',
    'Go back on this server':
        'Vrátit tento server',
    'Drop the ai-X.Y.Z.tar.gz here, or press to choose it':
        'Sem přetáhněte ai-X.Y.Z.tar.gz, nebo klikněte a vyberte ho',
    'What root said last':
        'Co naposledy řekl root',
    'Show the versions to go back to':
        'Ukázat verze, ke kterým se lze vrátit',
    'What changed':
        'Co se změnilo',
    'a code to sign in':
        'kód pro přihlášení',
    'a code to check an address':
        'kód pro ověření adresy',
    'notices':
        'upozornění',
    'a test':
        'zkouška',
    'a mail':
        'e-mail',
    'The daemon is starting again with the new version - asking again…':
        'Démon startuje znovu s novou verzí – ptám se znovu…',
    'Kept in the database:':
        'Uloženo v databázi:',
    'Send every waiting one now':
        'Odeslat všechny čekající hned',
    'waiting for another try':
        'čeká na další pokus',
    'given up':
        'vzdáno',
    # ---- 1.0.8: the accounts as otp's ----
    'files everywhere':
        'soubory všude',
    'Its Linux account, its folders and its note':
        'Jeho účet Linuxu, složky a poznámka',
    'chooses a password at the next sign-in':
        'zvolí si heslo při příštím přihlášení',
    'the second step not given yet':
        'druhý krok zatím nezadán',
    'Not your own account':
        'Ne vlastní účet',
    'Not your own account - sign in as another administrator for that':
        'Ne vlastní účet – přihlaste se k tomu jako jiný administrátor',
    'It cannot sign in any more. Its terminals go on running as the Linux account they run as.':
        'Už se nepřihlásí. Jeho terminály běží dál pod účtem Linuxu, pod kterým běží.',
    ' It is this one: you are signed out.':
        ' Je to toto přihlášení: budete odhlášeni.',
    # ---- 1.0.9: the tablet, the folder of the chats, the Claude Code tab, the start ----
    'Claude Code itself, as claude.ai keeps your settings: its settings, permissions, hooks, memory, MCP servers, agents, commands, skills, plugins, background sessions and usage - for you and for a project.':
        'Claude Code samotné, jako claude.ai drží vaše nastavení: jeho nastavení, oprávnění, hooky, paměť, MCP servery, agenti, příkazy, dovednosti, pluginy, relace na pozadí a spotřeba – pro vás i pro projekt.',
    'What are we working on?':
        'Na čem budeme pracovat?',
    'Describe a task or ask a question - Claude Code starts on it in the folder below and goes on on the server. Enter starts it, Shift+Enter is a new line.':
        'Popište úkol nebo položte otázku – Claude Code se do toho pustí ve složce níže a pokračuje na serveru. Enter spustí, Shift+Enter je nový řádek.',
    'The folder it works in.':
        'Složka, ve které pracuje.',
    'The model.':
        'Model.',
    'What it may do without asking.':
        'Co smí bez ptaní.',
    'How hard it thinks.':
        'Jak usilovně přemýšlí.',
    'Every option of Claude Code, in the full dialog.':
        'Všechny volby Claude Code v úplném dialogu.',
    'Every option…':
        'Všechny volby…',
    'Start it (Enter)':
        'Spustit (Enter)',
    'Claude Code without a message':
        'Claude Code bez zprávy',
    'Everything this terminal has shown since it started - tmux keeps it - in a window of its own that scrolls by finger too; copied or downloaded.':
        'Všechno, co tento terminál od spuštění ukázal – drží to tmux – ve vlastním okně, které se posouvá i prstem; dá se zkopírovat nebo stáhnout.',
    'History':
        'Historie',
    'ask before changes':
        'ptát se před změnami',
    'effort':
        'úsilí',
    'Good morning':
        'Dobré ráno',
    'Good afternoon':
        'Dobré odpoledne',
    'Good evening':
        'Dobrý večer',
    'What it starts on, as though typed first - empty: nothing, it waits for you.':
        'Čím začne, jako by to bylo napsané jako první – prázdné: nic, počká na vás.',
    'a new one in the background (--bg)':
        'novou na pozadí (--bg)',
    'Its name in Claude Code (--name)':
        'Jeho název v Claude Code (--name)',
    'shown in the prompt box and in /resume':
        'zobrazí se u výzvy a v /resume',
    'another… (written below)':
        'jiný… (napsaný níže)',
    'Effort (--effort)':
        'Úsilí (--effort)',
    'as Claude Code decides':
        'jak rozhodne Claude Code',
    'low':
        'nízké',
    'medium':
        'střední',
    'high':
        'vysoké',
    'extra high':
        'velmi vysoké',
    'max':
        'maximum',
    'auto (a classifier decides)':
        'automaticky (rozhoduje klasifikátor)',
    'manual (ask for everything)':
        'ručně (ptát se na všechno)',
    'do not ask (deny what is not allowed)':
        'neptat se (zakázat, co není povoleno)',
    'The first message':
        'První zpráva',
    'Every option of Claude Code':
        'Všechny volby Claude Code',
    'Tools and permissions':
        'Nástroje a oprávnění',
    'Allowed without asking (--allowedTools)':
        'Povoleno bez ptaní (--allowedTools)',
    'One a line, or with commas.':
        'Jeden na řádek nebo oddělené čárkou.',
    'Never (--disallowedTools)':
        'Nikdy (--disallowedTools)',
    'Only these built-in tools (--tools)':
        'Jen tyto vestavěné nástroje (--tools)',
    'Never asking may be switched on in it':
        'Lze v ní zapnout „nikdy se neptat“',
    'What it knows':
        'Co ví',
    'More folders it may use (--add-dir)':
        'Další složky, které smí používat (--add-dir)',
    'Add a folder…':
        'Přidat složku…',
    'One a line.':
        'Jedna na řádek.',
    'Added to its system prompt':
        'Přidáno k systémové výzvě',
    'Its whole system prompt instead':
        'Celá vlastní systémová výzva místo jeho',
    "--system-prompt: Claude Code's own is not used then.":
        '--system-prompt: vlastní výzva Claude Code se pak nepoužije.',
    'The agent of the session (--agent)':
        'Agent relace (--agent)',
    'MCP servers from files (--mcp-config)':
        'MCP servery ze souborů (--mcp-config)',
    'One a line: a file or JSON.':
        'Jeden na řádek: soubor nebo JSON.',
    'Only those servers':
        'Jen tyto servery',
    'More settings (--settings)':
        'Další nastavení (--settings)',
    'Settings read from (--setting-sources)':
        'Nastavení číst z (--setting-sources)',
    'Plugins from folders (--plugin-dir)':
        'Pluginy ze složek (--plugin-dir)',
    'For this session only.':
        'Jen pro tuto relaci.',
    'The session':
        'Relace',
    'Continued as a new conversation':
        'Pokračovat jako nová konverzace',
    '--fork-session, with --continue or --resume':
        '--fork-session, s --continue nebo --resume',
    'In a new git worktree (--worktree)':
        'V novém git worktree (--worktree)',
    'Make a worktree':
        'Vytvořit worktree',
    'Its session ID (--session-id)':
        'ID relace (--session-id)',
    'Compacted at (--autocompact)':
        'Zhutnit při (--autocompact)',
    'When the model is busy (--fallback-model)':
        'Když je model přetížený (--fallback-model)',
    'Remote Control on, named':
        'Remote Control zapnuté, s názvem',
    '--remote-control: the session can be followed from claude.ai.':
        '--remote-control: relaci lze sledovat z claude.ai.',
    'Remote Control':
        'Remote Control',
    'How it runs':
        'Jak běží',
    'Verbose':
        'Podrobně',
    'Debug, of what (--debug)':
        'Ladění, čeho (--debug)',
    'Debug':
        'Ladění',
    'Safe mode':
        'Bezpečný režim',
    '--safe-mode: CLAUDE.md, hooks, plugins, MCP and the rest of yours switched off':
        '--safe-mode: CLAUDE.md, hooky, pluginy, MCP a ostatní vaše vypnuté',
    'Bare':
        'Holé',
    '--bare: no hooks, plugins, CLAUDE.md discovery, keychain':
        '--bare: bez hooků, pluginů, hledání CLAUDE.md a klíčenky',
    'Restricted':
        'Omezené',
    '--restricted: no tools that run code':
        '--restricted: bez nástrojů, které spouštějí kód',
    'Claude in Chrome':
        'Claude v Chrome',
    'as set':
        'podle nastavení',
    'on (--chrome)':
        'zapnuto (--chrome)',
    'off (--no-chrome)':
        'vypnuto (--no-chrome)',
    'Connect to the IDE':
        'Připojit se k IDE',
    'Messages to you (SendUserMessage)':
        'Zprávy pro vás (SendUserMessage)',
    'No skills or /commands':
        'Bez dovedností a /příkazů',
    'For a screen reader':
        'Pro čtečku obrazovky',
    "The machine's details in the first message":
        'Údaje o stroji v první zprávě',
    'Anything else claude --help lists, as typed.':
        'Cokoli dalšího z claude --help, tak jak to napíšete.',
    'Keep these as how my chats start':
        'Takhle začínat všechny mé chaty',
    'Kept with your account, offered every time.':
        'Uloží se k vašemu účtu a nabídne se pokaždé.',
    'Read the folder again':
        'Načíst složku znovu',
    'folder(s)':
        'složek',
    'file(s)':
        'souborů',
    'What can be done with it':
        'Co s tím jde dělat',
    'Choose this folder':
        'Vybrat tuto složku',
    'A new folder in it…':
        'Nová složka v ní…',
    'A new file in it…':
        'Nový soubor v ní…',
    'Rename…':
        'Přejmenovat…',
    'Delete…':
        'Smazat…',
    'A new folder here…':
        'Nová složka zde…',
    'A new file here…':
        'Nový soubor zde…',
    'Read it again':
        'Načíst znovu',
    'Upload files here…':
        'Nahrát sem soubory…',
    'Nothing in it yet.':
        'Zatím je prázdná.',
    'With everything in it. It cannot be undone.':
        'Se vším, co v ní je. Nejde to vrátit.',
    'It cannot be undone.':
        'Nejde to vrátit.',
    'The version, the sign-in, what is set up - and the doctor.':
        'Verze, přihlášení, co je nastaveno – a doktor.',
    'Setting it up':
        'Nastavení',
    'settings.json: the model, the permission mode, the environment and the rest, for you, the project or only you in the project.':
        'settings.json: model, režim oprávnění, prostředí a další – pro vás, pro projekt nebo jen pro vás v projektu.',
    'What Claude Code may do without asking, what it asks first, and what it never does.':
        'Co Claude Code smí bez ptaní, na co se nejdřív zeptá a co nikdy neudělá.',
    'Commands run by Claude Code itself before or after a tool, when a prompt is sent, when it stops.':
        'Příkazy, které Claude Code spouští sám před nástrojem nebo po něm, při odeslání výzvy, když skončí.',
    'Hooks':
        'Hooky',
    'CLAUDE.md - what Claude Code reads at the start of every conversation.':
        'CLAUDE.md – co Claude Code čte na začátku každé konverzace.',
    'The tools and data Claude Code reaches through the Model Context Protocol.':
        'Nástroje a data, ke kterým se Claude Code dostane přes Model Context Protocol.',
    'MCP servers':
        'MCP servery',
    'Extending it':
        'Rozšíření',
    'Subagents: a prompt, a model and tools of their own, called by name.':
        'Subagenti: vlastní výzva, model a nástroje, volaní jménem.',
    'Agents':
        'Agenti',
    'Your own /commands: a prompt kept in a file, with arguments.':
        'Vlastní /příkazy: výzva uložená v souboru, s argumenty.',
    'Folders of instructions Claude Code loads when they fit the task.':
        'Složky s pokyny, které Claude Code načte, když se hodí k úkolu.',
    'Skills':
        'Dovednosti',
    'How Claude Code writes its answers.':
        'Jak Claude Code píše odpovědi.',
    'Output styles':
        'Styly výstupu',
    'Running it':
        'Běh',
    'Plugins and their marketplaces: installed, enabled, updated.':
        'Pluginy a jejich tržiště: nainstalované, zapnuté, aktualizované.',
    'Plugins':
        'Pluginy',
    'Sessions Claude Code runs on its own (claude --bg): opened, stopped, removed.':
        'Relace, které Claude Code běží samo (claude --bg): otevřít, zastavit, odebrat.',
    'Background sessions':
        'Relace na pozadí',
    'The tokens the conversations used, by day, model and folder.':
        'Tokeny, které konverzace spotřebovaly, po dnech, modelech a složkách.',
    'Usage':
        'Spotřeba',
    "keybindings.json: Claude Code's own keys.":
        'keybindings.json: vlastní klávesy Claude Code.',
    'Keyboard':
        'Klávesnice',
    'The Linux account':
        'Účet Linuxu',
    'Whose Claude Code: its home holds its settings, memory and the rest.':
        'Čí Claude Code: v jeho domovské složce je nastavení, paměť a další.',
    'The project folder':
        'Složka projektu',
    'Choose a project…':
        'Vybrat projekt…',
    'Another project…':
        'Jiný projekt…',
    'Without a project':
        'Bez projektu',
    'A new Claude Code here':
        'Nové Claude Code zde',
    'no project chosen - only what is yours everywhere':
        'žádný projekt – jen to vaše, co platí všude',
    'Its .claude folder, CLAUDE.md and .mcp.json - shared with everybody working in it.':
        'Jeho složka .claude, CLAUDE.md a .mcp.json – sdílené se všemi, kdo v něm pracují.',
    'not there':
        'není',
    'Its folder':
        'Jeho složka',
    'Ask the doctor':
        'Zeptat se doktora',
    'Sign in again':
        'Přihlásit znovu',
    'agents':
        'agentů',
    'commands':
        'příkazů',
    'skills':
        'dovedností',
    'output styles':
        'stylů výstupu',
    'MCP servers ':
        'MCP serverů',
    'Its files':
        'Jeho soubory',
    'mine':
        'moje',
    'the project':
        'projekt',
    'mine in the project':
        'moje v projektu',
    'Memory (CLAUDE.md)':
        'Paměť (CLAUDE.md)',
    'MCP servers (.mcp.json)':
        'MCP servery (.mcp.json)',
    'Mine (all my folders)':
        'Moje (všechny mé složky)',
    'This project (shared, in the repository)':
        'Tento projekt (sdílené, v repozitáři)',
    'Mine in this project (not shared)':
        'Moje v tomto projektu (nesdílené)',
    'The model':
        'Model',
    'Any other name of a model can be written in the JSON below.':
        'Jiný název modelu lze napsat do JSON níže.',
    'Permission mode at the start':
        'Režim oprávnění na začátku',
    'as Claude Code decides (default)':
        'jak rozhodne Claude Code (výchozí)',
    'Effort':
        'Úsilí',
    'Output style':
        'Styl výstupu',
    'The name of a style: Default, Explanatory, Learning or one of yours.':
        'Název stylu: Default, Explanatory, Learning nebo některý váš.',
    'The language it answers in':
        'Jazyk odpovědí',
    'e.g. czech':
        'např. czech',
    'Keep the transcripts (days)':
        'Držet přepisy (dní)',
    'Co-Authored-By in commits':
        'Co-Authored-By v commitech',
    'Thinking always on':
        'Přemýšlení vždy zapnuté',
    'Let in every server of .mcp.json':
        'Pustit každý server z .mcp.json',
    'Switch every hook off':
        'Vypnout všechny hooky',
    'Tips while it works':
        'Tipy během práce',
    'Updates itself':
        'Aktualizuje se samo',
    'A command that prints the API key':
        'Příkaz, který vypíše klíč API',
    'The status line: a command':
        'Stavový řádek: příkaz',
    'Its output is shown under the prompt.':
        'Jeho výstup se ukáže pod výzvou.',
    'More folders it may use':
        'Další složky, které smí používat',
    'Its environment':
        'Jeho prostředí',
    'NAME=value, one a line: set in every session.':
        'JMÉNO=hodnota, jedno na řádek: nastaví se v každé relaci.',
    'Save the settings':
        'Uložit nastavení',
    'All of it as JSON':
        'Celé jako JSON',
    'that is not JSON':
        'to není JSON',
    'not there yet - saving makes it':
        'zatím neexistuje – uložením vznikne',
    'The file is not JSON Claude Code can read - put it right in the text below.':
        'Soubor není JSON, který by Claude Code přečetlo – opravte ho v textu níže.',
    'The settings file is not JSON - put it right under Settings first.':
        'Soubor nastavení není JSON – nejdřív ho opravte v Nastavení.',
    'Choose a project above for its own settings.':
        'Pro vlastní nastavení projektu ho vyberte nahoře.',
    'A rule is a tool, and what of it in brackets: Bash(npm run test:*), Read(./secrets/**), Edit(src/**), WebFetch(domain:example.com), mcp__github. Deny wins over ask, ask over allow.':
        'Pravidlo je nástroj a v závorce co z něj: Bash(npm run test:*), Read(./secrets/**), Edit(src/**), WebFetch(domain:example.com), mcp__github. Zákaz má přednost před dotazem, dotaz před povolením.',
    'allow it':
        'povolit',
    'ask first':
        'nejdřív se zeptat',
    'an MCP tool (mcp__…)':
        'nástroj MCP (mcp__…)',
    'Add the rule':
        'Přidat pravidlo',
    'Never':
        'Nikdy',
    'Ask first':
        'Nejdřív se zeptat',
    'Allowed without asking':
        'Povoleno bez ptaní',
    'Take the rule away':
        'Odebrat pravidlo',
    'Save the permissions':
        'Uložit oprávnění',
    'which MCP tool?':
        'který nástroj MCP?',
    'Each hook is a command Claude Code runs itself, with the event as JSON on its input. A matcher picks the tools (Bash, Edit|Write, mcp__.*); empty is every one. An exit code of 2 stops the tool and tells Claude why.':
        'Každý hook je příkaz, který Claude Code spouští samo, s událostí jako JSON na vstupu. Matcher vybírá nástroje (Bash, Edit|Write, mcp__.*); prázdný je každý. Návratový kód 2 nástroj zastaví a řekne Claudovi proč.',
    'For the tools (a matcher)':
        'Pro nástroje (matcher)',
    'The command':
        'Příkaz',
    'Its time (s)':
        'Jeho čas (s)',
    'Add the hook':
        'Přidat hook',
    'No hook yet.':
        'Zatím žádný hook.',
    'Save the hooks':
        'Uložit hooky',
    'Tools':
        'Nástroje',
    'Command':
        'Příkaz',
    'which command?':
        'jaký příkaz?',
    'Mine (~/.claude/CLAUDE.md)':
        'Moje (~/.claude/CLAUDE.md)',
    'The project (CLAUDE.md)':
        'Projekt (CLAUDE.md)',
    'Mine in the project (CLAUDE.local.md)':
        'Moje v projektu (CLAUDE.local.md)',
    'Markdown. A line @path/to/file brings another file in; # at the start of a prompt in a session adds a line here.':
        'Markdown. Řádek @cesta/k/souboru přidá další soubor; # na začátku výzvy v relaci sem přidá řádek.',
    'The servers':
        'Servery',
    'Check them':
        'Zkontrolovat je',
    'Add a server':
        'Přidat server',
    'Whose':
        'Čí',
    'What it runs':
        'Co spouští',
    'Secrets':
        'Tajné údaje',
    'kept out':
        'nepuštěný',
    'waiting to be let in':
        'čeká na puštění',
    'Let it in for this project':
        'Pustit pro tento projekt',
    'Keep it out of this project':
        'Nepouštět do tohoto projektu',
    'Take the server away':
        'Odebrat server',
    'An MCP server':
        'MCP server',
    'What it is':
        'Co to je',
    'a command on this machine (stdio)':
        'příkaz na tomto stroji (stdio)',
    'an address (HTTP)':
        'adresa (HTTP)',
    'an address (SSE)':
        'adresa (SSE)',
    'Its arguments, one a line':
        'Jeho argumenty, jeden na řádek',
    'The address':
        'Adresa',
    'Headers, one a line':
        'Hlavičky, jedna na řádek',
    'Its environment (NAME=value, one a line)':
        'Jeho prostředí (JMÉNO=hodnota, jedno na řádek)',
    'Added with claude mcp add-json, as the account - Claude Code keeps it where it keeps its own.':
        'Přidá se přes claude mcp add-json pod tímto účtem – Claude Code si ho uloží tam, kam ukládá svoje.',
    'The agents':
        'Agenti',
    'A new agent':
        'Nový agent',
    'Claude Code calls one by itself when its description fits, or when asked: "use the reviewer agent".':
        'Claude Code ho zavolá samo, když se hodí jeho popis, nebo když o to požádáte: „use the reviewer agent“.',
    'The commands':
        'Příkazy',
    'A new command':
        'Nový příkaz',
    'Typed as /name in a session; $ARGUMENTS is what follows it, $1 $2 one word each. A folder makes /folder:name.':
        'V relaci se píše /název; $ARGUMENTS je to, co následuje, $1 $2 po jednom slově. Složka dělá /složka:název.',
    'None yet.':
        'Zatím žádný.',
    'The skills':
        'Dovednosti',
    'A new skill':
        'Nová dovednost',
    'Each is a folder with SKILL.md; Claude Code reads its description and loads it when it fits the task.':
        'Každá je složka se SKILL.md; Claude Code čte její popis a načte ji, když se hodí k úkolu.',
    'The output styles':
        'Styly výstupu',
    'A new style':
        'Nový styl',
    'Chosen with /output-style, or as the output style in Settings.':
        'Vybírá se přes /output-style nebo jako styl výstupu v Nastavení.',
    'Edit it':
        'Upravit',
    'Letters, digits, - and _.':
        'Písmena, číslice, - a _.',
    'When it is used':
        'Kdy se použije',
    'Its tools (empty: all)':
        'Jeho nástroje (prázdné: všechny)',
    'Its model':
        'Jeho model',
    'Its colour':
        'Jeho barva',
    'Its system prompt':
        'Jeho systémová výzva',
    'Letters, digits, - and _; a folder/name for /folder:name.':
        'Písmena, číslice, - a _; složka/název pro /složka:název.',
    'What it does':
        'Co dělá',
    'Its arguments':
        'Jeho argumenty',
    'Tools it may use':
        'Nástroje, které smí používat',
    'The prompt':
        'Výzva',
    'When to use it':
        'Kdy ji použít',
    'A new output style':
        'Nový styl výstupu',
    'Keep the coding instructions (true/false)':
        'Zachovat pokyny pro programování (true/false)',
    'a name first':
        'nejdřív název',
    'Available':
        'Dostupné',
    'Show what the marketplaces have':
        'Ukázat, co tržiště nabízejí',
    'Installed':
        'Nainstalované',
    'No plugin installed. Install one from a marketplace below.':
        'Žádný plugin není nainstalovaný. Nainstalujte některý z tržiště níže.',
    'Marketplaces':
        'Tržiště',
    'Add a marketplace':
        'Přidat tržiště',
    'Plugin':
        'Plugin',
    'Switch off':
        'Vypnout',
    'Switch on':
        'Zapnout',
    'Uninstall it':
        'Odinstalovat',
    'Uninstall':
        'Odinstalovat',
    'Install':
        'Nainstalovat',
    'find a plugin…':
        'najít plugin…',
    'Its sessions':
        'Jeho relace',
    'Start one in the background…':
        'Spustit jednu na pozadí…',
    'What claude agents lists: the sessions of this account that run now - in a terminal, or in the background on their own (claude --bg), and those that ended. A background one is opened in a terminal of these pages with claude attach.':
        'Co vypisuje claude agents: relace tohoto účtu, které právě běží – v terminálu nebo samy na pozadí (claude --bg) – a ty, které skončily. Relace na pozadí se otevře v terminálu těchto stránek přes claude attach.',
    'No session.':
        'Žádná relace.',
    'in the background':
        'na pozadí',
    'in a terminal':
        'v terminálu',
    'Its output':
        'Její výstup',
    'Remove it (and its worktree, where that is safe)':
        'Odebrat (i její worktree, kde je to bezpečné)',
    '7 days':
        '7 dní',
    '30 days':
        '30 dní',
    '90 days':
        '90 dní',
    'a year':
        'rok',
    'counting…':
        'počítám…',
    'Tokens written by Claude':
        'Tokeny napsané Claudem',
    'Tokens sent':
        'Odeslané tokeny',
    'Written to the cache':
        'Zapsáno do cache',
    'Read from the cache':
        'Přečteno z cache',
    'Answers':
        'Odpovědi',
    'By day':
        'Po dnech',
    'Nothing in these days.':
        'V těchto dnech nic.',
    'By model':
        'Podle modelu',
    'Written':
        'Napsáno',
    'Sent':
        'Odesláno',
    'Cache read':
        'Z cache',
    'By folder':
        'Podle složky',
    'tokens written':
        'napsaných tokenů',
    'answers':
        'odpovědí',
    'Claude Code\'s own keys, as /keybindings writes them: {"bindings": [{"context": "Chat", "bindings": {"ctrl+e": "chat:externalEditor"}}]}.':
        'Vlastní klávesy Claude Code, jak je zapisuje /keybindings: {"bindings": [{"context": "Chat", "bindings": {"ctrl+e": "chat:externalEditor"}}]}.',
    'A new chat starts in this folder or in one under it, and nowhere else: the folder picker offers it and what is under it, never the rest of the machine. Empty: anywhere the account may go.':
        'Nový chat začne v této složce nebo v některé pod ní, a nikde jinde: výběr složky nabídne jen ji a co je pod ní, nikdy zbytek stroje. Prázdné: kdekoli, kam účet smí.',
    'The folder of the chats':
        'Složka chatů',
    'The whole history':
        'Celá historie',
    'lines':
        'řádků',
    'reading what tmux keeps…':
        'čtu, co drží tmux…',
    'Copy it all':
        'Zkopírovat vše',
    'the whole history was copied':
        'celá historie je zkopírovaná',
    'Back to now':
        'Zpět na teď',
    # ---- 1.0.31: downloading the certificate ----
    'Download the certificate':
        'Stáhnout certifikát',
    'Choose the form the other side wants. The private key is given out only in the forms of the second row - whoever has it can be this server.':
        'Zvolte formát, který chce druhá strana. Privátní klíč se vydává jen ve formátech druhé řady – kdo ho má, může se vydávat za tento server.',
    'The certificate only':
        'Jen certifikát',
    'nothing secret in it':
        'nic tajného v něm není',
    'With the private key':
        'S privátním klíčem',
    'secret - keep it safe':
        'tajné – dobře ho uschovejte',
    'Text, Base64. nginx, Apache, HAProxy, Linux.':
        'Text, Base64. nginx, Apache, HAProxy, Linux.',
    'The same PEM text, the ending Windows and browsers open with a double click.':
        'Stejný text PEM s příponou, kterou Windows a prohlížeče otevřou dvojklikem.',
    'Binary, the certificate alone. Java, Windows, network devices.':
        'Binární, jen certifikát. Java, Windows, síťová zařízení.',
    'The certificate with its chain in one file. Windows, IIS, Tomcat.':
        'Certifikát s řetězcem v jednom souboru. Windows, IIS, Tomcat.',
    'The certificate, its chain and its private key, locked with a password. Windows, IIS, Azure, Exchange.':
        'Certifikát, jeho řetězec a privátní klíč, zamčené heslem. Windows, IIS, Azure, Exchange.',
    'PEM with the key':
        'PEM s klíčem',
    'The certificate, its chain and its private key in one text file - the key locked when a password is given.':
        'Certifikát, řetězec a privátní klíč v jednom textovém souboru – klíč zamčený, pokud zadáte heslo.',
    'The private key':
        'Privátní klíč',
    'Only the private key, PEM - locked with AES-256 when a password is given.':
        'Jen privátní klíč, PEM – zamčený AES-256, pokud zadáte heslo.',
    'the private key is not kept here':
        'privátní klíč tu uložený není',
    'The chain too (the certificates of the authority that issued it)':
        'I řetězec (certifikáty autority, která ho vydala)',
    'This file holds the private key of the pages. Anybody who has it, and the password, can pose as this server. Download it only for a server of your own, and give the password apart from the file.':
        'Tento soubor obsahuje privátní klíč stránek. Kdo ho má i s heslem, může se vydávat za tento server. Stahujte ho jen pro vlastní server a heslo předávejte odděleně od souboru.',
    '8 characters at least':
        'alespoň 8 znaků',
    'The password again':
        'Heslo znovu',
    'For an older Windows (Server 2016 and before): 3DES and SHA-1 instead of AES-256':
        'Pro starší Windows (Server 2016 a starší): 3DES a SHA-1 místo AES-256',
    'Make a strong password':
        'Vytvořit silné heslo',
    'the password is on the clipboard too':
        'heslo je i ve schránce',
    'A .pfx is always locked: the password is needed to open it.':
        'Soubor .pfx je vždy zamčený: k otevření je potřeba heslo.',
    'Optional: without one the key is in the file as it is - readable by whoever has the file.':
        'Nepovinné: bez hesla je klíč v souboru tak, jak je – čitelný pro každého, kdo soubor má.',
    'a .pfx needs a password':
        'soubor .pfx potřebuje heslo',
    'a password of 8 characters at least':
        'heslo alespoň 8 znaků',
    'the two passwords are not the same':
        'hesla nejsou stejná',
    'The certificate in the form you choose - PEM, CRT, DER, PKCS#7, or with its private key (PEM, PFX)':
        'Certifikát ve formátu, který zvolíte – PEM, CRT, DER, PKCS#7, nebo s privátním klíčem (PEM, PFX)',
    'a .pfx is always locked: give it a password':
        'soubor .pfx je vždy zamčený: zadejte heslo',
    'the private key of the certificate is not here to be given out':
        'privátní klíč certifikátu tu není k vydání',
    'there is no certificate of the pages here':
        'certifikát stránek tu není',
    # ---- 1.0.37: updates and restarts on a schedule ----
    'This server looks what dnf (or apt) has waiting, every day at the time below - for the card above. Nothing is put in.':
        'Server každý den v čase níže zjistí, co má dnf (nebo apt) připraveno – pro kartu výše. Nic se neinstaluje.',
    'The updates put in by themselves in the window below, as by hand - the terminals go on running meanwhile. Off until switched on.':
        'Aktualizace se nainstalují samy v okně níže, stejně jako ručně – terminály mezitím běží dál. Vypnuto, dokud se nezapne.',
    'When, as HH:MM - a quiet hour, away from the backups.':
        'Kdy, jako HH:MM – v klidnou hodinu, mimo zálohy.',
    'A restart the update needs - made by itself, or offered on the page.':
        'Restart, který aktualizace potřebuje – provede se sám, nebo se nabídne na stránce.',
    'The server restarted in the window below. Every terminal ends with it. Off until switched on.':
        'Server se restartuje v okně níže. Skončí s tím každý terminál. Vypnuto, dokud se nezapne.',
    'Only when one is needed':
        'Jen když je potřeba',
    'Only when an update left the server waiting for a restart; off: every time.':
        'Jen když aktualizace nechala server čekat na restart; vypnuto: pokaždé.',
    'Only the security updates':
        'Jen bezpečnostní',
    'Every update':
        'Všechny aktualizace',
    'On a schedule':
        'Podle plánu',
    # ---- 1.0.39: automatic certificates (ACME) ----
    'A token from deSEC (Token management) - one that may change this domain’s records. Kept sealed.':
        'Token z deSEC (Token management) – takový, který smí měnit záznamy této domény. Uložený zapečetěně.',
    'A zone the records go into instead of the name’s own (acme.example.net), each name with a CNAME to it in your DNS - In your DNS above says which. Empty: _acme-challenge.NAME itself.':
        'Zóna, do které záznamy jdou místo zóny samotného jména (acme.example.net), každé jméno s CNAME na ni ve vašem DNS – které, říká Ve vašem DNS výše. Prázdné: přímo _acme-challenge.JMÉNO.',
    'As the DNS server knows it, ai-acme.; allowed to update _acme-challenge records only.':
        'Jak ho zná DNS server, ai-acme.; smí měnit jen záznamy _acme-challenge.',
    'ECDSA P-384':
        'ECDSA P-384',
    'RSA 3072':
        'RSA 3072',
    'RSA 4096':
        'RSA 4096',
    'HTTP-01 needs port 80 of the name reachable from the internet (or from the CA, for a CA of your own). DNS-01 needs nothing open: the CA reads a TXT record.':
        'HTTP-01 potřebuje port 80 jména dostupný z internetu (nebo z CA, u vlastní CA). DNS-01 nepotřebuje nic otevřeného: CA čte záznam TXT.',
    'Let’s Encrypt':
        'Let’s Encrypt',
    'Let’s Encrypt - staging (to try it)':
        'Let’s Encrypt – staging (na vyzkoušení)',
    'Let’s Encrypt, its staging (certificates browsers do not trust - to try it), or another.':
        'Let’s Encrypt, jeho staging (certifikáty, kterým prohlížeče nevěří – na vyzkoušení), nebo jiná.',
    'Let’s Encrypt’s certificates last 90 days; 30 is what it advises.':
        'Certifikáty Let’s Encrypt platí 90 dní; 30 je, co doporučuje.',
    'The CA’s own certificate':
        'Vlastní certifikát CA',
    'The CA’s root (PEM), where the system does not trust it already.':
        'Kořen CA (PEM), pokud mu systém ještě nedůvěřuje.',
    'The DNS servers asked for everything on this page: the address of the CA and of the DNS API, Check DNS, Try port 80, and whether the TXT record can be seen before the CA is asked - 1.1.1.1, 9.9.9.9 to see what the internet sees. Empty: the machine’s own (/etc/resolv.conf).':
        'DNS servery, kterých se ptá vše na této stránce: adresa CA a DNS API, Ověřit DNS, Vyzkoušet port 80 a zda je záznam TXT vidět, než se zeptá CA – 1.1.1.1, 9.9.9.9, aby bylo vidět, co vidí internet. Prázdné: vlastní servery stroje (/etc/resolv.conf).',
    'The certificate of the pages ordered from the CA and renewed by itself - by HTTP-01 port 80 of the name must reach this server, by DNS-01 nothing has to be open. Off until switched on.':
        'Certifikát stránek objednaný od CA a obnovovaný sám – u HTTP-01 musí port 80 jména vést na tento server, u DNS-01 nemusí být nic otevřené. Vypnuto, dokud se nezapne.',
    'The directory of another ACME CA, https://ca.example.cz/acme/acme/directory.':
        'Adresář jiné ACME CA, https://ca.example.cz/acme/acme/directory.',
    'The key’s secret (base64). Kept sealed; written to a file only ai reads for the moment nsupdate runs.':
        'Tajemství klíče (base64). Uložené zapečetěně; zapíše se do souboru, který čte jen ai, jen na dobu běhu nsupdate.',
    'The name the certificate is for. Empty: the name of the certificate it has now, else the full host name. Its name… on the card above changes it too.':
        'Jméno, pro které je certifikát. Prázdné: jméno certifikátu, který má teď, jinak plné jméno stroje. Mění ho i Jeho jméno… na kartě výše.',
    'The primary DNS server of the zone, ns1.example.cz or with a port 10.0.0.53:53.':
        'Primární DNS server zóny, ns1.example.cz nebo s portem 10.0.0.53:53.',
    'The server’s DNS name':
        'DNS jméno serveru',
    'What Let’s Encrypt takes: RSA of 2048, 3072 or 4096 bits, ECDSA P-256 or P-384. ECDSA is smaller and quicker; RSA for old clients. Both: an RSA certificate by default and an ECDSA one to the clients that can take it - what Let’s Encrypt advises. The account at the CA has a key of its own.':
        'Co Let’s Encrypt přijímá: RSA 2048, 3072 nebo 4096 bitů, ECDSA P-256 nebo P-384. ECDSA je menší a rychlejší; RSA pro staré klienty. Oba: certifikát RSA výchozí a ECDSA klientům, kteří ho umí – to Let’s Encrypt doporučuje. Účet u CA má vlastní klíč.',
    'Where the record goes, example.cz. Empty: as the server finds it.':
        'Kam záznam patří, example.cz. Prázdné: jak ji najde server.',
    'Your domain at deSEC, example.dedyn.io (free) or one of your own whose DNS is there. The records go into it; your DNS has a CNAME to it for each name - In your DNS above says which.':
        'Vaše doména u deSEC, example.dedyn.io (zdarma) nebo vlastní, jejíž DNS je tam. Záznamy jdou do ní; váš DNS má na ni pro každé jméno CNAME – které, říká Ve vašem DNS výše.',
    'both - RSA 2048 by default, ECDSA P-256 to who can take it':
        'oba – RSA 2048 výchozí, ECDSA P-256 pro ty, kdo ho umí',
    'https://auth.acme-dns.example.cz; _acme-challenge.NAME is a CNAME to the subdomain below.':
        'https://auth.acme-dns.example.cz; _acme-challenge.JMÉNO je CNAME na subdoménu níže.',
    'Automatic certificates':
        'Automatické certifikáty',
    'Off - switch it on below, choose the CA, and save.':
        'Vypnuto – zapněte níže, zvolte CA a uložte.',
    'no certificate of its own':
        'žádný vlastní certifikát',
    'Ordered from the CA now and put into nginx. ACME renews it from then on.':
        'Objedná se od CA hned a vloží do nginx. Od té doby ho ACME obnovuje.',
    'Replace the certificate of the pages?':
        'Nahradit certifikát stránek?',
    'The DNS name the certificate of the pages is for. Empty: the name of the certificate it has now, else the full host name.':
        'DNS jméno, pro které je certifikát stránek. Prázdné: jméno certifikátu, který má teď, jinak plné jméno stroje.',
    'The name of this certificate is not known yet: give it (Its name…).':
        'Jméno tohoto certifikátu zatím není známé: zadejte ho (Jeho jméno…).',
    "The name of the pages' certificate":
        'Jméno certifikátu stránek',
    'Empty: the name of the certificate it has now, else the full host name.':
        'Prázdné: jméno certifikátu, který má teď, jinak plné jméno stroje.',
    'The name points at the address that reaches port 80 of this server - from the internet, or from your own CA.':
        'Jméno ukazuje na adresu, která vede na port 80 tohoto serveru – z internetu, nebo z vaší vlastní CA.',
    'Port 80 is open to it - the firewall in front of the server, and Firewall and access here.':
        'Port 80 je pro ni otevřený – firewall před serverem i Firewall a přístup zde.',
    'Try port 80 on the card, then Order it now.':
        'Vyzkoušejte port 80 na kartě, pak Objednat teď.',
    'HTTP-01: the CA asks port 80 of the name - so the name points at this server, and port 80 is open to the CA.':
        'HTTP-01: CA se ptá na portu 80 jména – takže jméno ukazuje na tento server a port 80 je pro CA otevřený.',
    'Each record looked up from this server now, through its DNS servers - as the CA will look. A record just put in may take a while to show (its TTL).':
        'Každý záznam se teď vyhledá z tohoto serveru přes jeho DNS servery – jak bude hledat CA. Právě vložený záznam se může chvíli neukazovat (jeho TTL).',
    'Better: a CNAME once in your DNS to a zone ai can write to (deSEC is free) - then nothing is by hand any more.':
        'Lépe: jednou CNAME ve vašem DNS na zónu, do které ai umí zapisovat (deSEC je zdarma) – pak už není nic ručně.',
    'DNS-01: the CA reads a TXT record ai puts in. What has to be in your DNS for it - once - is below.':
        'DNS-01: CA čte záznam TXT, který vloží ai. Co pro to musí být ve vašem DNS – jednou – je níže.',
    'ai puts it in':
        'vloží ho ai',
    'nothing to do: ai puts it in and takes it away':
        'nic dělat: ai ho vloží a zase odebere',
    'the name points at an address that reaches port 80 of this server':
        'jméno ukazuje na adresu, která vede na port 80 tohoto serveru',
    "The certificate of these pages ordered from Let's Encrypt or another ACME CA and renewed by itself well before it runs out. The CA checks the name by asking it on port 80 (HTTP-01), or by a record in DNS (DNS-01) for a server it cannot see from the internet.":
        'Certifikát těchto stránek objednaný od Let’s Encrypt nebo jiné ACME CA a obnovovaný sám dlouho předtím, než vyprší. CA ověří jméno dotazem na portu 80 (HTTP-01), nebo záznamem v DNS (DNS-01) u serveru, který z internetu nevidí.',
    'or the public address in front of it':
        'nebo veřejná adresa před ním',
    "The certificates ordered from Let's Encrypt (or another ACME CA) and renewed by themselves.":
        'Certifikáty objednané od Let’s Encrypt (nebo jiné ACME CA) a obnovované samy.',
}

PATTERNS = {
    'Take every ended one off the list ({0})':
        'Odebrat všechny ukončené ze seznamu ({0})',
    'Take {0} ended terminal(s) off the list?':
        'Odebrat {0} ukončených terminálů ze seznamu?',
    '{0} taken off the list':
        '{0} odebráno ze seznamu',
    'ai {0} on {1}.': 'ai {0} na {1}.',
    '{0} terminal(s) running.': '{0} {0:terminál běží|terminály běží|terminálů běží}.',
    ' A newer version is out: {0} (Settings - Upgrades).': ' Vyšla novější verze: {0} (Nastavení – Upgrady).',
    'ai {0} is out - Settings - Upgrades': 'Vyšlo ai {0} – Nastavení – Upgrady',
    'The server is not answering just now ({0}) - asking again.': 'Server právě neodpovídá ({0}) – ptám se znovu.',
    '{0}:{1} left': 'zbývá {0}:{1}',
    'You: {0}': 'Vy: {0}',
    'The account {0}': 'Účet {0}',
    'The password of {0}': 'Heslo účtu {0}',
    'A new Claude Code terminal in {0}': 'Nový terminál Claude Code v {0}',
    'It has ended: {0}': 'Skončil: {0}',
    'exited ({0})': 'skončil ({0})',
    'exited': 'skončil',
    '{0} · {1} · {2} ago': '{0} · {1} · před {2}',
    'What ran in it has ended (exit {0}). Its last screen is above.': 'Co v něm běželo, skončilo (exit {0}). Jeho poslední obrazovka je výše.',
    'What ran in it has ended. Its last screen is above.': 'Co v něm běželo, skončilo. Jeho poslední obrazovka je výše.',
    'the connection dropped - again in {0} s': 'spojení se přerušilo – znovu za {0} s',
    'sending {0}…': 'nahrávám {0}…',
    'the file {0} is Claude\'s now: {1}': 'soubor {0} teď má Claude: {1}',
    'the picture {0} is Claude\'s now: {1}': 'obrázek {0} teď má Claude: {1}',
    '{0} item(s)': '{0} {0:položka|položky|položek}',
    '{0} item(s) (only the first 10 000)': '{0} {0:položka|položky|položek} (jen prvních 10 000)',
    'there: {0}': 'je tam: {0}',
    'A new name for {0}': 'Nový název pro {0}',
    'Take {0} away?': 'Odstranit {0}?',
    'The pasted text as a file called': 'Vložený text jako soubor s názvem',
    '{0} of {1}': '{0} z {1}',
    '{0} Claude Code · {1} open now': '{0} Claude Code · {1} právě otevřených',
    '{0} processor(s) · {1} · {2}': '{0} {0:procesor|procesory|procesorů} · {1} · {2}',
    '{0} of {1}': '{0} z {1}',
    '{0} free on {1}': '{0} volno na {1}',
    'up {0} · {1}': 'běží {0} · {1}',
    '{0} {1} free of {2}': '{0} {1} volno z {2}',
    '{0} is out': 'vyšla {0}',
    'a restart is wanted · looked {0}': 'je potřeba restart · zjišťováno {0}',
    'looked {0}': 'zjišťováno {0}',
    '{0} days': '{0} {0:den|dny|dní}',
    '{0} event(s)': '{0} {0:událost|události|událostí}',
    '{0} change(s) not saved yet': '{0} {0:neuložená změna|neuložené změny|neuložených změn}',
    '* the default (Settings - Claude Code), {0} now': '* výchozí (Nastavení – Claude Code), teď {0}',
    'the default ({0})': 'výchozí ({0})',
    '{0} (yours)': '{0} (váš)',
    'in - keep it within {0} s': 'nasazeno – potvrďte do {0} s',
    '{0} - keep it within {1} s': '{0} – potvrďte do {1} s',
    '{0} package(s) to update · looked {1}': '{0} {0:balíček|balíčky|balíčků} k aktualizaci · zjišťováno {1}',
    '{0} package(s) to update · looked {1} · a restart of the server is wanted': '{0} {0:balíček|balíčky|balíčků} k aktualizaci · zjišťováno {1} · je potřeba restart serveru',
    'Looking for updates… ({0})': 'Hledám aktualizace… ({0})',
    'Anthropic\'s own installer, in a terminal you watch: {0}': 'Instalátor od Anthropicu, v terminálu, který sledujete: {0}',
    'Upgrade to {0}?': 'Upgradovat na {0}?',
    'ai {0}': 'ai {0}',
    '{0} - {1} ({2} days left)': '{0} – {1} (zbývá {2} dní)',
    'The nginx file of the pages ({0}) has no list written by install.sh: change it there.': 'Soubor nginx těchto stránek ({0}) nemá seznam zapsaný install.sh: změňte ho tam.',
    'as it is ({0})': 'jak je ({0})',
    'Whoever holds {0} may no longer sign in as {1} with it.': 'Kdo drží {0}, se s ním už nepřihlásí jako {1}.',
    '{0}, in step': '{0}, seřízeno',
    '{0}, not in step yet': '{0}, zatím neseřízeno',
    'too many wrong passwords - try again in {0} min': 'příliš mnoho chybných hesel – zkuste to znovu za {0} min',
    'the password: {0}': 'heslo: {0}',
    'at least {0} characters': 'alespoň {0} znaků',
    'there is an account called {0} already': 'účet {0} už existuje',
    '{0} is not a folder on this server': '{0} není složka na tomto serveru',
    '{0} is outside the folders this account may use': '{0} je mimo složky, které tento účet smí používat',
    'there is no Linux account {0} on this machine': 'na tomto stroji není účet Linuxu {0}',
    'tmux would not start it: {0}': 'tmux ho nespustil: {0}',
    'it is {0} - too big to show here; download it instead': 'má {0} – příliš velký na zobrazení zde; stáhněte si ho',
    'that file is bigger than this server takes ({0} MB at most)': 'ten soubor je větší, než tento server přijme (nejvýš {0} MB)',
    'the file did not arrive whole ({0} of {1} bytes)': 'soubor nedorazil celý ({0} z {1} bajtů)',
    'there is a {0} there already': '{0} už tam je',
    '{0} is not taken away from here': '{0} se odsud neodstraňuje',
    '{0} is not an address': '{0} není adresa',
    'nginx does not take it, so everything was put back: {0}': 'nginx to nepřijal, takže se vše vrátilo: {0}',
    'GitHub did not answer: {0}': 'GitHub neodpověděl: {0}',
    'ai {0} is not at {1}': 'ai {0} na {1} není',
    'ai {0} is not newer than {1}, which runs here': 'ai {0} není novější než {1}, která tu běží',
    'the package was refused: {0}': 'balíček byl odmítnut: {0}',
    'the server did not answer in {0} s': 'server neodpověděl do {0} s',
    'Claude · {0}': 'Claude · {0}',
    'shell · {0}': 'shell · {0}',
    # ---- 1.0.4: what otp had and ai had not yet ----
    'The built-in value: {0}':
        'Vestavěná hodnota: {0}',
    '{0} account(s), {1} event(s), {2} terminal(s), {3} setting(s) saved':
        '{0} {0:účet|účty|účtů}, {1} {1:událost|události|událostí}, {2} {2:terminál|terminály|terminálů}, {3} {3:uložené nastavení|uložená nastavení|uložených nastavení}',
    '· {0} characters':
        '· {0} {0:znak|znaky|znaků}',
    'sent: {0}':
        'odesláno: {0}',
    'failed: {0}':
        'selhalo: {0}',
    'Put {0} back':
        'Obnovit {0}',
    'The oldest that is safe on this database: ai {0}':
        'Nejstarší bezpečná na této databázi: ai {0}',
    'older than {0}, the oldest that is safe on this database':
        'starší než {0}, nejstarší bezpečná na této databázi',
    'second step: {0}':
        'druhý krok: {0}',
    'Reset the second step of {0}?':
        'Zrušit druhý krok účtu {0}?',
    'Go back to ai {0}?':
        'Vrátit se k ai {0}?',
    'From {0} to {1}: a copy of the database is made first, then that version is fetched, checked and put in. The terminals go on running; these pages are back after a few seconds.':
        'Z {0} na {1}: nejdřív se udělá kopie databáze, pak se ta verze stáhne, ověří a nainstaluje. Terminály běží dál; stránky se vrátí za pár sekund.',
    'going back to {0}':
        'návrat na {0}',
    'Import {0}':
        'Import {0}',
    'imported: {0}':
        'importováno: {0}',
    'made: {0}':
        'vytvořeno: {0}',
    'taken away: {0}':
        'odebráno: {0}',
    'put back - what was there before is kept as {0}':
        'obnoveno – co tu bylo předtím, je uchováno jako {0}',
    'The last notice: {0} - {1}':
        'Poslední upozornění: {0} – {1}',
    'Sent: {0}':
        'Odesláno: {0}',
    'Not sent: {0}':
        'Neodesláno: {0}',
    "the certificate answered on {0}'s own name and address":
        'certifikát, kterým odpovídá vlastní název a adresa {0}',
    '{0}: the text has to say {code} - the code itself is put there':
        '{0}: text musí obsahovat {code} – tam se dosadí samotný kód',
    'reset - {0} sets the second step up again at the next sign-in':
        'zrušeno – {0} si druhý krok nastaví znovu při příštím přihlášení',
    '{0} had no second step set up':
        '{0} neměl nastavený druhý krok',
    'too many wrong codes - try again in {0} min':
        'příliš mnoho chybných kódů – zkuste to znovu za {0} min',
    'cleared: {0}':
        'smazáno: {0}',
    # ---- 1.0.5: chats like claude.ai ----
    'pinned: {0}':
        'připnuto: {0}',
    'no longer pinned: {0}':
        'odepnuto: {0}',
    'Hand it to Claude (@{0})':
        'Předat Claude (@{0})',
    '{0} item(s) · right button: what to do with one':
        '{0} {0:položka|položky|položek} · pravé tlačítko: co s ní',
    'Start {0} again?':
        'Spustit {0} znovu?',
    'End {0}?':
        'Ukončit {0}?',
    'Delete {0}?':
        'Smazat {0}?',
    'copied: {0}':
        'zkopírováno: {0}',
    'sending {0}…':
        'nahrávám {0}…',
    'that is outside the folder of this chat ({0})':
        'to je mimo složku tohoto chatu ({0})',
    'What runs in it now is ended and started afresh in the same folder{0}':
        'Co v něm teď běží, se ukončí a spustí znovu ve stejné složce{0}',
    # ---- 1.0.6: the database, the outgoing mail, the texts, the upgrades as otp's ----
    'older than {0}, the oldest that is safe on this database: what the newer versions wrote into it would not be read the same, or a security fix would be lost':
        'starší než {0}, nejstarší bezpečná na této databázi: to, co do ní zapsaly novější verze, by se nečetlo stejně, nebo by se ztratila oprava bezpečnosti',
    '{0} older version(s) it may not go back to - below {1}':
        '{0} {0:starší verze, ke které se vrátit nesmí|starší verze, ke kterým se vrátit nesmí|starších verzí, ke kterým se vrátit nesmí} – pod {1}',
    '{0}: the outgoing mail has no such field - it has {1}':
        '{0}: odchozí pošta takové pole nemá – má {1}',
    'The file {0} and the key beside it are deleted from this machine. The live database is not touched, and the others stay where they are.':
        'Soubor {0} a klíč vedle něj se z tohoto stroje smažou. Živé databáze se to nedotkne a ostatní zůstanou, kde jsou.',
    'A mail to {0}':
        'E-mail pro {0}',
    'They are files on this machine, under {0}, each with the key that opens its secrets beside it. Copy them off it if they are to survive the machine.':
        'Jsou to soubory na tomto stroji v {0}, každý s klíčem k jeho tajným údajům vedle sebe. Zkopírujte je jinam, pokud mají stroj přežít.',
    # ---- 1.0.8: the accounts as otp's ----
    '{0} table(s) laid out':
        '{0} {0:tabulka upravena|tabulky upraveny|tabulek upraveno}',
    'the role of {0} is changed':
        'role účtu {0} je změněna',
    'the password of {0} is set':
        'heslo účtu {0} je nastaveno',
    # ---- 1.0.9: the tablet, the folder of the chats, the Claude Code tab, the start ----
    'Choose a folder in {0}':
        'Vybrat složku v {0}',
    'Only {0} and what is under it (Settings - Claude Code - The folder of the chats).':
        'Jen {0} a co je pod ní (Nastavení – Claude Code – Složka chatů).',
    'Good evening, {0}':
        'Dobrý večer, {0}',
    'Good morning, {0}':
        'Dobré ráno, {0}',
    'Good afternoon, {0}':
        'Dobré odpoledne, {0}',
    'Claude Code of {0}':
        'Claude Code účtu {0}',
    'The whole history: {0}':
        'Celá historie: {0}',
    'A new folder in {0}:':
        'Nová složka v {0}:',
    'A new file in {0}:':
        'Nový soubor v {0}:',
    'A new name for {0}:':
        'Nový název pro {0}:',
    'Delete the folder {0}?':
        'Smazat složku {0}?',
    'deleted: {0}':
        'smazáno: {0}',
    'saved: {0}':
        'uloženo: {0}',
    'No MCP server for this account{0}':
        'Žádný MCP server pro tento účet{0}',
    'Uninstall {0}?':
        'Odinstalovat {0}?',
    'Take the marketplace {0} away?':
        'Odebrat tržiště {0}?',
    'Remove {0}?':
        'Odebrat {0}?',
    '{0} - keep the password apart from the file': '{0} – heslo uschovejte odděleně od souboru',
    'The protocols, the ciphers, the DH parameters and HSTS of {0} - kept as they are whichever way the certificate came, ACME and its renewals too.': 'Protokoly, šifry, parametry DH a HSTS {0} – zůstanou, jak jsou, ať certifikát přišel jakkoli, i přes ACME a jeho obnovy.',
    'One put in here by hand takes {0} out of ACME’s care: it is kept as it is, not replaced at the next renewal. Settings → Automatic certificates → Look after it gives it back.': 'Certifikát vložený zde ručně vyjme {0} z péče ACME: zůstane, jak je, při příští obnově se nenahradí. Nastavení → Automatické certifikáty → Starat se ho vrátí.',
    'http://{0}/.well-known/acme-challenge/ asked from this server, as the CA will ask it - whether it reaches ai. A firewall in front of the server may still stop the CA from outside.': 'http://{0}/.well-known/acme-challenge/ se zeptá z tohoto serveru, jak se zeptá CA – zda dojde k ai. Firewall před serverem může CA zvenku ještě zastavit.',
}

RICH = {
    'The ai console (<code>ai --console</code>) opens by itself when root signs in at the server\'s screen or over SSH; q leaves it for the ordinary shell. Never inside a terminal of these pages.':
        'Konzole ai (<code>ai --console</code>) se otevře sama, když se root přihlásí na obrazovce serveru nebo přes SSH; q ji opustí do běžného shellu. Nikdy uvnitř terminálu těchto stránek.',
    'Its <b>public</b> half goes into <code>/root/.ssh/authorized_keys</code> of this server. The <b>private</b> half is never kept here: it is shown to you once, to download or copy. The key is then in the list below - exported or taken away there; a key of your own is added there too.':
        'Jeho <b>veřejná</b> část se zapíše do <code>/root/.ssh/authorized_keys</code> tohoto serveru. <b>Soukromá</b> část se zde nikdy nedrží: ukáže se vám jednou, ke stažení nebo zkopírování. Klíč je pak v seznamu níže – tam se exportuje nebo odebírá; tam se přidává i vlastní klíč.',
    'Who may sign in to these pages. An <b>administrator</b> may do everything, start terminals as any Linux account and change the server; a <b>user</b> has terminals of their own only, running as the Linux account given here, and files only in its folders. Whoever signs in here is, on the server, the Linux account their terminals run as.':
        'Kdo se smí přihlásit k těmto stránkám. <b>Administrátor</b> smí všechno, spouštět terminály jako kterýkoli účet Linuxu a měnit server; <b>uživatel</b> má jen vlastní terminály, běžící jako zde zadaný účet Linuxu, a soubory jen ve svých složkách. Kdo se tu přihlásí, je na serveru tím účtem Linuxu, pod kterým běží jeho terminály.',
    'Both go back by themselves unless kept: after a change, press <b>Keep it</b> within the time under Signing in - from the old address or the new. A change that cut you off is so taken back without anybody\'s help.':
        'Obojí se samo vrátí, pokud se nepotvrdí: po změně stiskněte <b>Ponechat</b> v čase uvedeném v Přihlašování – ze staré adresy nebo z nové. Změna, která vás odřízla, se tak vrátí bez cizí pomoci.',
    'Set through NetworkManager. A change goes back by itself unless kept: open the pages at the new address and press <b>Keep it</b>.':
        'Nastavuje se přes NetworkManager. Změna se sama vrátí, pokud se nepotvrdí: otevřete stránky na nové adrese a stiskněte <b>Ponechat</b>.',
    'The connection is brought up again with the new settings. Open the pages at the new address and press <b>Keep it</b> - not kept, the old settings come back by themselves.':
        'Připojení se znovu nahodí s novým nastavením. Otevřete stránky na nové adrese a stiskněte <b>Ponechat</b> – bez potvrzení se staré nastavení vrátí samo.',
    # ---- 1.0.4: what otp had and ai had not yet ----
    "Every table on these pages can be laid out the way you read it. Press your name at the top right and switch on <b>Edit the columns</b>; then drag the edge of a column's heading to make it wider or narrower, and drag the heading itself to move the column. The right button on a heading hides a column, brings a hidden one back or adds an empty one for room. Twice on an edge puts that table's widths back. Each change is kept with your account the moment you let go, not in this browser, and comes back wherever you sign in; nobody else's tables change. The switch is for this sign-in only: signing out or the sign-in running out turns it off again, and the columns stay as you left them.":
        'Každou tabulku na těchto stránkách si můžete uspořádat podle sebe. Klikněte na své jméno vpravo nahoře a zapněte <b>Upravit sloupce</b>; pak tažením okraje záhlaví sloupec rozšíříte nebo zúžíte a tažením samotného záhlaví ho přesunete. Pravé tlačítko na záhlaví sloupec skryje, vrátí skrytý nebo přidá prázdný pro místo. Dvojklik na okraj vrátí šířky té tabulky. Každá změna se uloží k vašemu účtu v okamžiku, kdy pustíte – ne v tomto prohlížeči – a vrátí se, ať se přihlásíte kdekoli; tabulky nikoho jiného se nezmění. Přepínač platí jen pro toto přihlášení: odhlášení nebo vypršení přihlášení ho vypne a sloupce zůstanou, jak jste je nechali.',
    '<b>Edit the columns</b><br>While this is on, the edge of any column’s heading can be dragged to size it and the heading itself to move it, and the right button on a heading hides a column, brings a hidden one back or adds an empty one for room; each change is kept the moment you let go. It is for this sign-in only: signing out or the sign-in running out turns it off again. Off, the tables are drawn as you left them and nothing can move them.':
        '<b>Upravit sloupce</b><br>Dokud je to zapnuté, okraj záhlaví kteréhokoli sloupce jde tažením zúžit či rozšířit a samotné záhlaví přesunout; pravé tlačítko na záhlaví sloupec skryje, vrátí skrytý nebo přidá prázdný pro místo; každá změna se uloží, jakmile pustíte. Platí jen pro toto přihlášení: odhlášení nebo vypršení přihlášení to vypne. Vypnuté se tabulky kreslí, jak jste je nechali, a nic s nimi nepohne.',
    # ---- 1.0.6: the database, the outgoing mail, the texts, the upgrades as otp's ----
    'Put <b>this</b> one back, without downloading it and uploading it again: everything in the live database is replaced by what is in this file. You are shown what is in it and asked first, and a copy of what is being replaced is made before anything changes.':
        'Vrátit <b>tento</b> soubor bez stahování a nového nahrávání: všechno v živé databázi se nahradí tím, co je v tomto souboru. Nejdřív se ukáže, co v něm je, a zeptá se vás, a než se cokoli změní, udělá se kopie toho, co se nahrazuje.',
}
