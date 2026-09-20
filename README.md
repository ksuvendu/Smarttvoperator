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

### 3. Enable SSH inside iSH (so Shortcuts can reach it)

```sh
ssh-keygen -A
passwd            # set a password for the default user, needed for SSH login
/usr/sbin/sshd
```

`sshd` doesn't survive iSH restarts by default — after reopening iSH, just
run `/usr/sbin/sshd` again before using the Shortcut. (You can automate this
later if you want; out of scope for v1.)

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

### 8. Configure command phrases

```sh
cp commands.example.json commands.json
```

Edit `commands.json` and replace `REPLACE_WITH_IPTV_APP_ID` with the app ID
you found in step 7. Add more entries the same way — each entry is
`{"label": ..., "keywords": [...], "app_id": ...}`, and matching is a simple
case-insensitive substring check against the transcribed text.

### 9. Test the pipeline manually (no voice yet)

```sh
python3 voice_agent.py "open iptv"
```

This should print what it matched and launch the app on the TV.

### 10. Wire up the iOS Shortcut

In the **Shortcuts** app, create a new shortcut:

1. **Dictate Text** (this is what you'll speak into).
2. **Run Script Over SSH**:
   - Host: `localhost`, Port: `22` (iSH's sshd)
   - User / password: the iSH user you set in step 3
   - Script: `cd ~/Smarttvoperator && python3 voice_agent.py "$(Dictated Text)"`
     (insert the *Dictated Text* variable from step 1 into the script field)
3. Optionally add **Show Result** to see the SSH output.
4. Add the Shortcut to your Home Screen for one-tap voice control.

Note: iSH must be open (or at least running in the background) with `sshd`
started for the SSH step to succeed.

## Files

- `tv_control.py` — pairing, `list_apps()`, `launch_app()` (CLI: `pair`,
  `list-apps`, `launch <app_id>`)
- `commands.example.json` / `commands.json` — phrase-to-app mapping (not
  committed; copy the example)
- `voice_agent.py` — entry point: takes transcribed text, matches it, launches
  the app
- `config.example.json` / `config.json` — TV host + paired client key (not
  committed; copy the example)

## Out of scope for v1

Wake-word / always-listening mode, LLM-based intent parsing, and any device
other than the TV.
