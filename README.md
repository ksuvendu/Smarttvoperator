# Voice Control for LG webOS TV (iSH / iOS)

Speak a command on your phone ("open iptv") and it launches that app on your
LG webOS TV over WiFi.

## How it works on iOS

iSH (Alpine Linux under emulation) has no access to iOS's Speech framework,
so there's no `termux-speech-to-text` equivalent here. Instead:

1. An **iOS Shortcut** does the dictation natively ("Dictate Text").
2. The Shortcut runs `voice_agent.py` inside iSH over SSH (Shortcuts has a
   built-in **"Run Script Over SSH"** action), passing the dictated text as
   the command's argument.
3. `voice_agent.py` matches the text against `commands.json` and launches
   the matching app on the TV.

This keeps voice capture native (fast, accurate, offline-capable) while all
the TV logic lives in iSH.

## Setup

### 1. Install iSH

From the App Store, install **iSH Shell**. Open it once to finish setup.

### 2. Install packages in iSH

```sh
apk update
apk add python3 py3-pip openssh
```

### 3. Enable SSH inside iSH, and make it start on its own

```sh
apk add openssh openrc
ssh-keygen -A
passwd            # set a password for root — the Shortcut logs in as root
rc-update add sshd default
sed -i 's/::sysinit:.*/::sysinit:\/sbin\/openrc sysinit/' /etc/inittab
```

Fully close iSH (swipe it away, don't just background it) and reopen it once
so this takes effect. From then on, `sshd` starts automatically the moment
iSH launches — you never have to type a command by hand to enable it again;
the Shortcut in step 10 handles launching iSH for you.

If this OpenRC autostart doesn't take on your iSH build (SSH connection
refused when testing), the manual fallback always works: open iSH and run
`/usr/sbin/sshd`.

### 4. Get the code into iSH

Clone this repo (or copy the files) into iSH, e.g.:

```sh
cd ~
git clone <this-repo-url> Smarttvoperator
cd Smarttvoperator
pip install -r requirements.txt
```

### 5. Configure the TV connection

```sh
cp config.example.json config.json
```

Edit `config.json` and confirm `host` is your TV's IP (`192.168.5.16`).

### 6. Pair with the TV (first deliverable)

```sh
python3 tv_control.py pair
```

Accept the pairing prompt that appears on the TV screen. This saves a
`client_key` into `config.json` so you never have to re-pair.

### 7. List installed apps to find IPTV's app ID

```sh
python3 tv_control.py list-apps
```

This prints every installed app as `<app_id>\t<title>`. Find the IPTV app in
the list and copy its `app_id`.

### 8. (Optional) Set up phrase aliases

You don't need to pre-register apps — `voice_agent.py` fuzzy-matches any
spoken app name against the TV's real installed-app list, so "open netflix",
"open iptv", "launch prime video" etc. all work out of the box for whatever
is actually installed.

Only add an alias if what you say doesn't resemble the app's real title
(e.g. you say "iptv" but it's installed under a different name):

```sh
cp commands.example.json commands.json
```

Edit `commands.json` — it's a flat `{"spoken phrase": "app id or title"}` map.

### 9. Test the pipeline manually (no voice yet)

```sh
python3 voice_agent.py "open iptv"
python3 voice_agent.py "open netflix"
python3 voice_agent.py "play scandal in netflix"
```

This should print what it matched and launch the app on the TV.

**Supported phrasing:**
- `open <app>` / `launch <app>` / `start <app>` — opens any installed app
- `<app>` on its own (e.g. just "netflix") — same as above
- `play <content> in/on <app>` — opens the app and passes the content along
  as a best-effort `contentId`. **Caveat:** LG's webOS API has no documented,
  reliable way to search inside an app like Netflix by title text — this may
  just open Netflix's home/search screen instead of actually playing
  "Scandal". Try it on your TV and see what actually happens; the matching
  logic in `tv_control.py`'s `launch()` can be tuned once you know how your
  TV's app responds. Apps like YouTube tend to support content deep-links
  more reliably than Netflix does.

### 10. Build the one-tap Shortcut

Once this is built, using it means: tap the Shortcut (or say its name to
Siri), speak, done — nothing to type or run by hand.

In the **Shortcuts** app, create a new shortcut with these actions in order:

1. **Open App** → iSH — this launches/wakes iSH so `sshd` (autostarted in
   step 3) is actually running. It doesn't need to stay in the foreground.
2. **Wait** → 2 seconds — gives iSH's startup a moment to finish. If the SSH
   step below fails, increase this.
3. **Dictate Text** — this is what you'll speak into.
4. **Run Script Over SSH**:
   - Host: `localhost`, Port: `22`
   - User: `root`, Authentication: password (the one from step 3 above)
   - Script: `cd ~/Smarttvoperator && python3 voice_agent.py "$(Dictated Text)"`
     (insert the *Dictated Text* variable from step 3 into the script field)
5. **Show Result** (optional) — shows what it matched/launched.

Add the Shortcut to your Home Screen, or give it a name and ask Siri for it.

The very first time it runs, Shortcuts will show a one-time prompt to
confirm the SSH host's fingerprint — that's a one-off security check, not
something you'll see on every run.

## Files

- `tv_control.py` — pairing, app listing, fuzzy app resolution, and launching
  (CLI: `pair`, `list-apps`, `launch <name-or-id> [--content ...]`)
- `commands.example.json` / `commands.json` — optional phrase aliases for
  apps whose spoken name doesn't match their real title (not committed; copy
  the example)
- `voice_agent.py` — entry point: takes transcribed text, parses
  "open/play X (in Y)", resolves the app against the TV's real app list, and
  launches it
- `config.example.json` / `config.json` — TV host + paired client key (not
  committed; copy the example)

## Out of scope for v1

Wake-word / always-listening mode, LLM-based intent parsing, and any device
other than the TV.
