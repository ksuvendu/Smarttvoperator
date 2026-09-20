#!/usr/bin/env python3
"""Entry point: transcribed text -> parsed command -> TV action.

Supported phrasing:
    "open netflix" / "launch iptv" / "start youtube"   -> just opens the app
    "play scandal in netflix" / "play x on youtube"    -> opens the app and
                                                           tries to pass the
                                                           content along
    "netflix"                                          -> bare app name also
                                                           works

Any app name is matched against the TV's actual installed apps (fuzzy,
case-insensitive), so this isn't limited to a fixed list. `commands.json` is
optional and only needed for aliases (e.g. you say "iptv" but the app title
is something else).

On iSH there's no local speech-to-text, so the transcription happens in an
iOS Shortcut (native dictation) which passes the text in here, either as a
command-line argument (via the Shortcuts "Run Script Over SSH" action) or
piped over stdin for manual testing:

    python3 voice_agent.py "play scandal in netflix"
    echo "open iptv" | python3 voice_agent.py
"""
import asyncio
import re
import sys

from tv_control import AppNotFoundError, launch, load_aliases, load_config

PLAY_RE = re.compile(r"^\s*play\s+(?P<content>.+?)\s+(?:on|in)\s+(?P<app>.+?)\s*$", re.I)
OPEN_RE = re.compile(r"^\s*(?:open|launch|start)\s+(?P<app>.+?)\s*$", re.I)


def parse_command(text: str) -> tuple[str, str | None]:
    """Return (app_query, content_query) parsed from free-form text."""
    match = PLAY_RE.match(text)
    if match:
        return match.group("app").strip(), match.group("content").strip()
    match = OPEN_RE.match(text)
    if match:
        return match.group("app").strip(), None
    return text.strip(), None


def get_input_text() -> str:
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    return sys.stdin.readline().strip()


def main() -> None:
    text = get_input_text()
    if not text:
        print("No input heard.")
        return
    print(f"Heard: {text!r}")

    app_query, content_query = parse_command(text)

    config = load_config()
    host = config.get("host")
    client_key = config.get("client_key")
    if not host or not client_key:
        sys.exit("TV not paired yet. Run `python3 tv_control.py pair` first.")

    try:
        app, note = asyncio.run(launch(host, client_key, app_query, content_query, load_aliases()))
    except AppNotFoundError as err:
        print(err)
        return

    print(f"Launched: {app.get('title')} ({app.get('id')})")
    if note:
        print(note)


if __name__ == "__main__":
    main()
