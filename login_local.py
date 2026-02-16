#!/usr/bin/env python3
"""
Login to Telegram using credentials from .env.
Session is stored in project dir to avoid NFS/home path issues.

Usage:
  uv run python login_local.py              # MCP session (.session-state)
  uv run python login_local.py --agent     # Agent session (.session-state-agent)
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

# Load .env before any mcp_telegram imports
from dotenv import load_dotenv
load_dotenv()

PROJECT_DIR = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description="Login to Telegram")
parser.add_argument("--agent", action="store_true", help="Create session for agent_vibe (avoids MCP lock)")
args = parser.parse_args()

if args.agent:
    SESSION_BASE = PROJECT_DIR / ".session-state-agent"
else:
    SESSION_BASE = PROJECT_DIR / ".session-state"

SESSION_DIR = SESSION_BASE / "mcp-telegram"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
os.environ["XDG_STATE_HOME"] = str(SESSION_BASE)

api_id = os.environ.get("TELEGRAM_API_ID") or os.environ.get("API_ID")
api_hash = os.environ.get("TELEGRAM_API_HASH") or os.environ.get("API_HASH")

if not api_id or not api_hash:
    print("Error: Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env", file=sys.stderr)
    sys.exit(1)

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError


async def main():
    session_path = SESSION_DIR / "session"
    client = TelegramClient(
        str(session_path),
        int(api_id),
        api_hash,
    )

    await client.connect()
    if not await client.is_user_authorized():
        phone = input("Phone (e.g. +49123456789): ").strip()
        try:
            await client.send_code_request(phone)
            code = input("Code from Telegram: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                pw = input("2FA password: ")
                await client.sign_in(password=pw)
        except FloodWaitError as e:
            print(f"Telegram rate limit: wait {e.seconds}s", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Login failed: {e}", file=sys.stderr)
            sys.exit(1)

    me = await client.get_me()
    print(f"Logged in as {me.first_name} (@{me.username or 'n/a'})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
