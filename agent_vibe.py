#!/usr/bin/env python3
"""
Vibe → Cursor Agent: Poll a Telegram group for messages and run Cursor agent on each.
Uses the agent CLI (cursor/agent) and Python mcp-telegram session.
"""
import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Session in project dir
PROJECT_DIR = Path(__file__).resolve().parent
os.environ["XDG_STATE_HOME"] = str(PROJECT_DIR / ".session-state")

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

# Ensure PATH has ~/.local/bin for cursor/agent
home = Path.home()
local_bin = home / ".local" / "bin"
if local_bin.exists():
    env = os.environ.copy()
    env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
else:
    env = os.environ.copy()

BOT_PREFIX = "[bot]"
BOT_PATTERNS = ("Starting:", "Done ✓", "Yes —", "New approach:", "Update:")


def is_bot_message(text: str) -> bool:
    return text.startswith(BOT_PREFIX) or any(text.startswith(p) for p in BOT_PATTERNS)


def get_or_create_chat_id(workspace: Path, chat_file: str) -> str:
    chat_path = workspace / chat_file
    if chat_path.exists():
        cid = chat_path.read_text().strip()
        if cid:
            return cid
    result = subprocess.run(
        ["cursor", "agent", "create-chat"],
        capture_output=True,
        text=True,
        cwd=workspace,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cursor agent create-chat failed: {result.stderr}")
    chat_id = result.stdout.strip()
    chat_path.write_text(chat_id)
    return chat_id


def run_agent(instruction: str, workspace: Path, chat_id: str, dialog_id: str) -> int:
    prompt = f"Execute this instruction from Vibe.\n\nInstruction: {instruction}"

    proc = subprocess.run(
        [
            "cursor", "agent",
            "--model", "composer-1.5",
            "--print",
            "--approve-mcps",
            "--force",
            "--sandbox", "disabled",
            "--workspace", str(workspace),
            "--resume", chat_id,
            prompt,
        ],
        cwd=workspace,
        env=env,
    )
    return proc.returncode or 0


async def main():
    parser = argparse.ArgumentParser(description="Vibe → Cursor Agent")
    parser.add_argument("-d", "--dialog", default="-5150901335", help="Vibe group ID")
    parser.add_argument("-w", "--workspace", default="/share/datasets/home/wendler/code", help="Workspace for agent")
    parser.add_argument("--chat-file", default=".vibe-agent-chat", help="File to persist chat ID")
    parser.add_argument("-i", "--interval", type=int, default=1, help="Poll interval (seconds)")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    chat_id = get_or_create_chat_id(workspace, args.chat_file)

    from mcp_telegram.telegram import Telegram

    tg = Telegram()
    tg.create_client(
        api_id=os.environ.get("TELEGRAM_API_ID") or os.environ.get("API_ID"),
        api_hash=os.environ.get("TELEGRAM_API_HASH") or os.environ.get("API_HASH"),
    )
    await tg.client.connect()
    if not await tg.client.is_user_authorized():
        print("Not logged in. Run: uv run python login_local.py", file=sys.stderr)
        sys.exit(1)

    queue: list[tuple[int, str]] = []
    seen_ids: set[int] = set()
    last_processed_id = 0
    initialized = False
    processing = False

    async def fetch_and_enqueue():
        nonlocal last_processed_id, initialized
        try:
            entity = int(args.dialog) if args.dialog.lstrip("-").isdigit() else args.dialog
            result = await tg.get_messages(entity, limit=20)
            raw = list(reversed(result.messages)) if result.messages else []
            if not initialized:
                last_processed_id = max(0, *(m.message_id for m in raw)) if raw else 0
                initialized = True
                return
            for msg in raw:
                if msg.message_id <= last_processed_id or msg.message_id in seen_ids:
                    continue
                text = (msg.message or "").strip()
                if not text or is_bot_message(text):
                    continue
                seen_ids.add(msg.message_id)
                last_processed_id = max(last_processed_id, msg.message_id)
                queue.append((msg.message_id, text))
                asyncio.create_task(process_queue())
        except Exception as e:
            print(f"Fetch error: {e}", file=sys.stderr)

    entity = int(args.dialog) if args.dialog.lstrip("-").isdigit() else args.dialog

    async def process_queue():
        nonlocal processing
        if processing or not queue:
            return
        processing = True
        msg_id, text = queue.pop(0)
        print(f"\n📩 Processing instruction: {text[:60]}{'...' if len(text) > 60 else ''}\n")
        try:
            await tg.send_message(entity, f"{BOT_PREFIX} Starting...")
            code = await asyncio.to_thread(run_agent, text, workspace, chat_id, args.dialog)
            status = f"{BOT_PREFIX} Done ✓" if code == 0 else f"{BOT_PREFIX} Error (exit {code})"
            await tg.send_message(entity, status)
            print(f"\n✓ Agent finished (exit {code})\n")
        except Exception as e:
            await tg.send_message(entity, f"{BOT_PREFIX} Error: {e}")
            print(f"Error: {e}", file=sys.stderr)
        finally:
            processing = False
            if queue:
                asyncio.create_task(process_queue())

    await fetch_and_enqueue()

    print("Vibe → Cursor Agent")
    print(f"Dialog: {args.dialog}")
    print(f"Workspace: {workspace}")
    print(f"Shared chat: {chat_id}")
    print(f"Fetching every {args.interval}s. Press Ctrl+C to stop.\n")

    while True:
        await asyncio.sleep(args.interval)
        await fetch_and_enqueue()


if __name__ == "__main__":
    asyncio.run(main())
