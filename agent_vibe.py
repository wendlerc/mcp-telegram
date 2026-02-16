#!/usr/bin/env python3
"""
Vibe → Cursor Agent: Poll a Telegram group for messages and run Cursor agent on each.
Uses the agent CLI (cursor/agent) and Python mcp-telegram session.
"""
import argparse
import logging

# Quiet Telethon connection spam (Connecting to... Disconnecting from...)
logging.getLogger("telethon").setLevel(logging.WARNING)
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Session in project dir — use separate agent session to avoid MCP lock
PROJECT_DIR = Path(__file__).resolve().parent
AGENT_SESSION_DIR = PROJECT_DIR / ".session-state-agent"
os.environ["XDG_STATE_HOME"] = str(AGENT_SESSION_DIR)

# Use datasets for temp (avoid /tmp when root is full)
TMP_BASE = Path("/share/datasets/home/wendler/code/tmp")
TMP_BASE.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(TMP_BASE)
os.environ["TEMP"] = str(TMP_BASE)
os.environ["TMP"] = str(TMP_BASE)

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


async def run_agent(
    instruction: str,
    workspace: Path,
    chat_id: str,
    dialog_id: str,
) -> int:
    """Run agent. Telegram client must be DISCONNECTED so the MCP server can use the session."""
    prompt = f"""REQUIRED: You MUST actually INVOKE the send_message MCP tool to report to Vibe — do NOT just describe or mention it in text. Call the tool with entity="{dialog_id}" and message="[bot] your update". Prefix every message with "[bot]". Send progress updates, summaries, findings, and completion notes. Never output instructions like "use sendMessage with dialogId..." — instead, call the tool.

Execute this instruction from Vibe:

{instruction}"""

    proc = await asyncio.create_subprocess_exec(
        "cursor", "agent",
        "--model", "composer-1.5",
        "--print",
        "--approve-mcps",
        "--force",
        "--sandbox", "disabled",
        "--workspace", str(workspace),
        "--resume", chat_id,
        prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=workspace,
        env=env,
    )
    assert proc.stdout is not None
    async for line in proc.stdout:
        print(line.decode(errors="replace").rstrip())
    await proc.wait()
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

    tg_lock = asyncio.Lock()  # Serialize Telegram ops to avoid CancelledError races
    DB_LOCK_RETRIES = 10
    DB_LOCK_DELAY = 3  # seconds to wait for MCP to release session

    def is_db_locked(e: Exception) -> bool:
        return "database is locked" in str(e).lower() or "database_locked" in str(e).lower()

    # Retry create_client — SQLiteSession opens DB on init; MCP may hold the lock
    tg = None
    for attempt in range(DB_LOCK_RETRIES):
        try:
            tg = Telegram()
            tg.create_client(
                api_id=os.environ.get("TELEGRAM_API_ID") or os.environ.get("API_ID"),
                api_hash=os.environ.get("TELEGRAM_API_HASH") or os.environ.get("API_HASH"),
            )
            break
        except Exception as e:
            if is_db_locked(e) and attempt < DB_LOCK_RETRIES - 1:
                print(f"Session locked (attempt {attempt + 1}/{DB_LOCK_RETRIES}), retrying in {DB_LOCK_DELAY}s...", file=sys.stderr)
                await asyncio.sleep(DB_LOCK_DELAY)
            else:
                raise

    async def connect_fetch_disconnect():
        async with tg_lock:
            for attempt in range(DB_LOCK_RETRIES):
                try:
                    await tg.client.connect()
                    if not await tg.client.is_user_authorized():
                        raise RuntimeError("Not logged in. Run: uv run python login_local.py")
                    entity = int(args.dialog) if args.dialog.lstrip("-").isdigit() else args.dialog
                    try:
                        result = await tg.get_messages(entity, limit=20)
                    finally:
                        await tg.client.disconnect()
                    return entity, result
                except Exception as e:
                    if tg.client.is_connected():
                        await tg.client.disconnect()
                    if is_db_locked(e) and attempt < DB_LOCK_RETRIES - 1:
                        await asyncio.sleep(DB_LOCK_DELAY)
                        continue
                    raise

    async def connect_send_disconnect(entity, msg):
        async with tg_lock:
            for attempt in range(DB_LOCK_RETRIES):
                try:
                    await tg.client.connect()
                    try:
                        await tg.send_message(entity, msg)
                    finally:
                        await tg.client.disconnect()
                    return
                except Exception as e:
                    if tg.client.is_connected():
                        await tg.client.disconnect()
                    if is_db_locked(e) and attempt < DB_LOCK_RETRIES - 1:
                        await asyncio.sleep(DB_LOCK_DELAY)
                        continue
                    raise

    queue: list[tuple[int, str]] = []
    seen_ids: set[int] = set()
    last_processed_id = 0
    initialized = False
    processing = False

    async def fetch_and_enqueue():
        nonlocal last_processed_id, initialized
        if processing:
            return  # Skip fetch while agent runs — MCP holds the session
        try:
            entity, result = await connect_fetch_disconnect()
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
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Fetch error: {e}", file=sys.stderr)

    entity = int(args.dialog) if args.dialog.lstrip("-").isdigit() else args.dialog

    async def process_queue():
        nonlocal processing
        if processing or not queue:
            return
        processing = True
        # Merge all queued messages into one todo (messages sent while agent was busy)
        batch: list[tuple[int, str]] = []
        while queue:
            batch.append(queue.pop(0))
        merged = "\n".join(f"{i+1}. {t}" for i, (_, t) in enumerate(batch))
        if len(batch) > 1:
            merged = f"Combined {len(batch)} messages into one todo:\n\n{merged}"
        preview = merged[:80] + "..." if len(merged) > 80 else merged
        print(f"\n📩 Processing: {preview}\n")
        try:
            await connect_send_disconnect(entity, f"{BOT_PREFIX} Starting...")
            code = await run_agent(merged, workspace, chat_id, args.dialog)
            await asyncio.sleep(DB_LOCK_DELAY * 2)  # Extra wait for MCP to release session
            status = f"{BOT_PREFIX} Done ✓" if code == 0 else f"{BOT_PREFIX} Error (exit {code})"
            await connect_send_disconnect(entity, status)
            print(f"\n✓ Agent finished (exit {code})\n")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if not is_db_locked(e):
                try:
                    await connect_send_disconnect(entity, f"{BOT_PREFIX} Error: {e}")
                except Exception:
                    pass
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
