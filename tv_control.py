"""LG webOS TV control: pairing, app listing, and app launching.

Usage:
    python3 tv_control.py pair                # one-time pairing, saves client key
    python3 tv_control.py list-apps            # print installed apps and their IDs
    python3 tv_control.py launch <app_id>      # launch an app by ID
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from aiowebostv import WebOsClient, WebOsTvPairError

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(
            f"{CONFIG_PATH} not found. Copy config.example.json to config.json "
            "and set your TV's host IP."
        )
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


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


async def list_apps(host: str, client_key: str | None) -> None:
    client = WebOsClient(host, client_key=client_key)
    await client.connect()
    apps = await client.get_apps() or []
    await client.disconnect()
    for app in sorted(apps, key=lambda a: a.get("title", "")):
        print(f"{app.get('id')}\t{app.get('title')}")


async def launch_app(host: str, client_key: str | None, app_id: str) -> None:
    client = WebOsClient(host, client_key=client_key)
    await client.connect()
    await client.launch_app(app_id)
    await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="LG webOS TV control")
    parser.add_argument("--host", help="TV IP address (defaults to config.json)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pair")
    sub.add_parser("list-apps")
    launch_parser = sub.add_parser("launch")
    launch_parser.add_argument("app_id")
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
        asyncio.run(list_apps(host, client_key))
    elif args.cmd == "launch":
        asyncio.run(launch_app(host, client_key, args.app_id))


if __name__ == "__main__":
    main()
