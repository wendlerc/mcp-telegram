#!/usr/bin/env python3
"""Send a message to the Vibe Telegram chat. Usage: python send_vibe.py "message" """
import asyncio
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["XDG_STATE_HOME"] = str(PROJECT_DIR / ".session-state")

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

from mcp_telegram.telegram import Telegram


async def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "No message"
    tg = Telegram()
    tg.create_client(
        api_id=os.environ.get("TELEGRAM_API_ID") or os.environ.get("API_ID"),
        api_hash=os.environ.get("TELEGRAM_API_HASH") or os.environ.get("API_HASH"),
    )
    await tg.client.connect()
    if not await tg.client.is_user_authorized():
        print("Not logged in. Run: uv run python login_local.py", file=sys.stderr)
        sys.exit(1)
    await tg.send_message(-5150901335, msg)
    await tg.client.disconnect()
    print("Sent.")


if __name__ == "__main__":
    asyncio.run(main())
