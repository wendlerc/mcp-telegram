#!/usr/bin/env python3
"""Send a video (or other file) to the Vibe Telegram chat.

Usage:
  uv run python send_video.py <file_path> [message]
  uv run python send_video.py /path/to/video.mp4 "[bot] Pong2p control video"

Note: If you get "database is locked", the MCP/agent may be holding the session.
      Stop the agent, run this script, then restart the agent.

Extend this script or the MCP send_message tool for more file-sending use cases.
"""
import asyncio
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.environ["XDG_STATE_HOME"] = str(PROJECT_DIR / ".session-state")

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

from mcp_telegram.telegram import Telegram

VIBE_ENTITY = "-5150901335"


async def main():
    if len(sys.argv) < 2:
        print("Usage: python send_video.py <file_path> [message]", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1]).resolve()
    message = sys.argv[2] if len(sys.argv) > 2 else ""

    if not file_path.exists():
        print(f"File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    if not file_path.is_file():
        print(f"Not a file: {file_path}", file=sys.stderr)
        sys.exit(1)

    tg = Telegram()
    tg.create_client(
        api_id=os.environ.get("TELEGRAM_API_ID") or os.environ.get("API_ID"),
        api_hash=os.environ.get("TELEGRAM_API_HASH") or os.environ.get("API_HASH"),
    )
    await tg.client.connect()
    if not await tg.client.is_user_authorized():
        print("Not logged in. Run: uv run python login_local.py", file=sys.stderr)
        sys.exit(1)

    await tg.send_message(
        VIBE_ENTITY,
        message,
        file_path=[str(file_path)],
    )
    await tg.client.disconnect()
    print(f"Sent: {file_path}")


if __name__ == "__main__":
    asyncio.run(main())
