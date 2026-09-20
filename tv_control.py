"""LG webOS TV control: pairing, app listing, and app launching.

Usage:
    python3 tv_control.py pair                          # one-time pairing, saves client key
    python3 tv_control.py list-apps                      # print installed apps and their IDs
    python3 tv_control.py launch <name-or-id>            # launch an app, fuzzy-matched by name
    python3 tv_control.py launch <name-or-id> --content "scandal"   # experimental: pass a
                                                          # contentId/search term to the app
"""
import argparse
import asyncio
import difflib
import json
import sys
from pathlib import Path

from aiowebostv import WebOsClient, WebOsTvPairError

CONFIG_PATH = Path(__file__).parent / "config.json"
COMMANDS_PATH = Path(__file__).parent / "commands.json"


class AppNotFoundError(Exception):
    """Raised when no installed app matches the requested name."""


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(
            f"{CONFIG_PATH} not found. Copy config.example.json to config.json "
            "and set your TV's host IP."
        )
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def load_aliases() -> dict[str, str]:
    """Optional phrase -> app id/title overrides, e.g. {"iptv": "com.example.iptv"}."""
    if not COMMANDS_PATH.exists():
        return {}
    return json.loads(COMMANDS_PATH.read_text())


def find_app(apps: list[dict], query: str, aliases: dict[str, str] | None = None) -> dict | None:
    """Resolve free-form text (e.g. "netflix", "the iptv one") to an installed app."""
    query = query.strip().lower()
    aliases = aliases or {}

    alias_target = aliases.get(query)
    if alias_target:
        for app in apps:
            if query in (app.get("id", "").lower(), app.get("title", "").lower()):
                return app
        query = alias_target.strip().lower()

    for app in apps:
        if query in (app.get("id", "").lower(), app.get("title", "").lower()):
            return app

    for app in apps:
        title = app.get("title", "").lower()
        if title and (query in title or title in query):
            return app

    titles = [app.get("title", "") for app in apps]
    close = difflib.get_close_matches(query, [t.lower() for t in titles], n=1, cutoff=0.6)
    if close:
        return apps[[t.lower() for t in titles].index(close[0])]

    return None


async def get_apps(host: str, client_key: str | None) -> list[dict]:
    client = WebOsClient(host, client_key=client_key)
    await client.connect()
    try:
        return await client.get_apps() or []
    finally:
        await client.disconnect()


async def pair(host: str) -> None:
    config = load_config()
    client = WebOsClient(host, client_key=config.get("client_key"))
    print("Connecting to the TV. If this is the first pairing, accept the")
    print("prompt that appears on the TV screen now.")
    try:
        await client.connect()
    except WebOsTvPairError as err:
        sys.exit(f"Pairing failed: {err}")
    config["host"] = host
    config["client_key"] = client.client_key
    save_config(config)
    await client.disconnect()
    print(f"Paired successfully. Client key saved to {CONFIG_PATH}")


async def launch(
    host: str,
    client_key: str | None,
    app_query: str,
    content_query: str | None = None,
    aliases: dict[str, str] | None = None,
) -> dict:
    """Resolve app_query against installed apps and launch it (optionally with content)."""
    client = WebOsClient(host, client_key=client_key)
    await client.connect()
    try:
        apps = await client.get_apps() or []
        app = find_app(apps, app_query, aliases)
        if app is None:
            titles = ", ".join(sorted(a.get("title", "") for a in apps if a.get("title")))
            raise AppNotFoundError(
                f"No installed app matches {app_query!r}. Installed apps: {titles}"
            )
        if content_query:
            await client.launch_app_with_content_id(app["id"], content_query)
        else:
            await client.launch_app(app["id"])
        return app
    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="LG webOS TV control")
    parser.add_argument("--host", help="TV IP address (defaults to config.json)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pair")
    sub.add_parser("list-apps")
    launch_parser = sub.add_parser("launch")
    launch_parser.add_argument("app", help="App name or id (fuzzy-matched against installed apps)")
    launch_parser.add_argument(
        "--content",
        help="Experimental: contentId/search term to pass to the app (not all apps support this)",
    )
    args = parser.parse_args()

    if args.cmd == "pair":
        host = args.host or (load_config().get("host") if CONFIG_PATH.exists() else None)
        if not host:
            sys.exit("No TV host set. Pass --host or set 'host' in config.json.")
        asyncio.run(pair(host))
        return

    config = load_config()
    host = args.host or config.get("host")
    client_key = config.get("client_key")
    if not host:
        sys.exit("No TV host set. Pass --host or set 'host' in config.json.")
    if not client_key:
        sys.exit("No client key found. Run `python3 tv_control.py pair` first.")

    if args.cmd == "list-apps":
        for app in sorted(asyncio.run(get_apps(host, client_key)), key=lambda a: a.get("title", "")):
            print(f"{app.get('id')}\t{app.get('title')}")
    elif args.cmd == "launch":
        try:
            app = asyncio.run(launch(host, client_key, args.app, args.content, load_aliases()))
        except AppNotFoundError as err:
            sys.exit(str(err))
        print(f"Launched: {app.get('title')} ({app.get('id')})")


if __name__ == "__main__":
    main()
