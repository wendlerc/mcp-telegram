#!/usr/bin/env python3
"""
List all Telegram dialogs (chats, groups, channels) with their IDs.
Use this to find a group ID when @userinfobot doesn't work.

Run when agent_vibe is idle (or stop it first) to avoid session lock.
  uv run python list_dialogs.py
"""
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
# Try agent session first; if "database is locked", stop agent_vibe and run again
os.environ["XDG_STATE_HOME"] = str(PROJECT_DIR / ".session-state-agent")

api_id = os.environ.get("TELEGRAM_API_ID") or os.environ.get("API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH") or os.environ.get("API_HASH")
if not api_id or not api_hash:
    print("Error: Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env", file=sys.stderr)
    sys.exit(1)

from telethon import TelegramClient
from telethon.utils import get_peer_id

SESSION_DIR = Path(os.environ["XDG_STATE_HOME"]) / "mcp-telegram"
session_path = SESSION_DIR / "session"


async def main():
    client = TelegramClient(str(session_path), int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("Not logged in. Run: uv run python login_local.py --agent", file=sys.stderr)
        sys.exit(1)

    print("Dialogs (groups/channels have negative IDs):\n")
    async for d in client.iter_dialogs():
        name = (d.name or d.title or "?")
        eid = get_peer_id(d.entity)
        print(f"  {eid}\t{name}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
