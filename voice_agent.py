#!/usr/bin/env python3
"""Entry point: transcribed text -> command match -> TV action.

On iSH there's no local speech-to-text, so the transcription happens in an
iOS Shortcut (native dictation) which passes the text in here, either as a
command-line argument (via the Shortcuts "Run Script Over SSH" action) or
piped over stdin for manual testing:

    python3 voice_agent.py "open iptv"
    echo "open iptv" | python3 voice_agent.py
"""
import asyncio
import json
import sys
from pathlib import Path

from tv_control import launch_app, load_config

COMMANDS_PATH = Path(__file__).parent / "commands.json"


def load_commands() -> list[dict]:
    if not COMMANDS_PATH.exists():
        sys.exit(
            f"{COMMANDS_PATH} not found. Copy commands.example.json to "
            "commands.json and fill in your app IDs."
        )
    return json.loads(COMMANDS_PATH.read_text())


def match_command(text: str, commands: list[dict]) -> dict | None:
    text = text.lower()
    for command in commands:
        if any(keyword.lower() in text for keyword in command["keywords"]):
            return command
    return None


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

    commands = load_commands()
    command = match_command(text, commands)
    if command is None:
        print(f"No matching command for: {text!r}")
        return
    print(f"Matched: {command['label']} -> launching app {command['app_id']}")

    config = load_config()
    host = config.get("host")
    client_key = config.get("client_key")
    if not host or not client_key:
        sys.exit("TV not paired yet. Run `python3 tv_control.py pair` first.")

    asyncio.run(launch_app(host, client_key, command["app_id"]))
    print("Done.")


if __name__ == "__main__":
    main()
