#!/usr/bin/env python3
"""
Vibe → Gemini Agent: Poll a Telegram group for messages and run Gemini CLI on each.
Adapted from agent_vibe.py (Cursor version) for Google's Gemini CLI.

Usage:
  uv run python agent_vibe_gemini.py                          # interactive chat picker
  uv run python agent_vibe_gemini.py -w /path/to/workspace    # picker + custom workspace
  uv run python agent_vibe_gemini.py --dialog=-5150901335     # skip picker, use this chat
  uv run python agent_vibe_gemini.py --help
"""
import argparse
import logging

# Quiet Telethon connection spam
logging.getLogger("telethon").setLevel(logging.WARNING)
import asyncio
import os
import subprocess
import sys
import uuid
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

# Ensure PATH has nvm node v22 and ~/.local/bin
home = Path.home()
local_bin = home / ".local" / "bin"
nvm_node_bin = home / ".nvm" / "versions" / "node"
env = os.environ.copy()

# Find nvm node v22+ for gemini CLI (requires Node >= 20)
node_bin = None
if nvm_node_bin.exists():
    for d in sorted(nvm_node_bin.iterdir(), reverse=True):
        version = d.name.lstrip("v").split(".")[0]
        if version.isdigit() and int(version) >= 20:
            candidate = d / "bin"
            if (candidate / "node").exists():
                node_bin = str(candidate)
                break

path_parts = []
if node_bin:
    path_parts.append(node_bin)
if local_bin.exists():
    path_parts.append(str(local_bin))
path_parts.append(env.get("PATH", ""))
env["PATH"] = ":".join(path_parts)

# Use Google Login auth (uses paid subscription, not free-tier API key)
env["GOOGLE_GENAI_USE_GCA"] = "true"

BOT_PREFIX = "[bot]"
BOT_PATTERNS = ("Starting:", "Done ✓", "Yes —", "New approach:", "Update:")


def is_bot_message(text: str) -> bool:
    return text.startswith(BOT_PREFIX) or any(text.startswith(p) for p in BOT_PATTERNS)


def run_agent_env(workspace: Path, queue_path: Path) -> dict:
    """Env for agent: VIBE_SEND_QUEUE path for file fallback when MCP times out."""
    e = env.copy()
    e["VIBE_SEND_QUEUE"] = str(queue_path)
    # Ensure nvm Node is used by gemini
    if node_bin:
        e["PATH"] = f"{node_bin}:{e.get('PATH', '')}"
    return e


async def run_agent(
    instruction: str,
    workspace: Path,
    dialog_id: str,
    queue_path: Path,
    resume: bool = False,
) -> int:
    """Run gemini CLI. Telegram client must be DISCONNECTED so the MCP server can use the session."""
    queue_path.write_text("")  # Clear before run
    queue_name = queue_path.name

    prompt = f"""REQUIRED: Report back to this group. Use send_message MCP tool with entity="{dialog_id}" (always use this entity, not Vibe). If it returns "Tool not found" or times out, use this fallback instead:
  echo "[bot] your message" >> {queue_name}
Prefix every message with "[bot]". Send progress updates, summaries, findings, and completion notes. agent_vibe forwards {queue_name} to Telegram after you finish.

Execute this instruction:

{instruction}"""

    args = [
        "gemini",
        "--prompt", prompt,
        "--approval-mode", "yolo",
        "--output-format", "text",
    ]
    if resume:
        args.extend(["--resume", "latest"])

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=workspace,
        env=run_agent_env(workspace, queue_path),
    )
    assert proc.stdout is not None
    async for line in proc.stdout:
        print(line.decode(errors="replace").rstrip())
    await proc.wait()
    return proc.returncode or 0


async def pick_dialog(tg_client) -> str:
    """Interactive wizard: list Telegram dialogs and let user pick one."""
    from telethon.utils import get_peer_id

    await tg_client.connect()
    if not await tg_client.is_user_authorized():
        print("Not logged in. Run: uv run python login_local.py --agent", file=sys.stderr)
        sys.exit(1)

    dialogs = []
    print("\n📱 Loading your Telegram chats...\n")
    async for d in tg_client.iter_dialogs():
        name = d.name or d.title or "?"
        eid = get_peer_id(d.entity)
        dialogs.append((eid, name))

    await tg_client.disconnect()

    if not dialogs:
        print("No dialogs found!", file=sys.stderr)
        sys.exit(1)

    # Display numbered list
    print("─" * 50)
    print("  #   ID                Name")
    print("─" * 50)
    for i, (eid, name) in enumerate(dialogs, 1):
        # Truncate long names
        display_name = name[:35] + "…" if len(name) > 35 else name
        print(f"  {i:3d}  {eid:<18} {display_name}")
    print("─" * 50)
    print(f"  Found {len(dialogs)} chats.\n")

    while True:
        try:
            choice = input("Select chat number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                sys.exit(0)
            idx = int(choice) - 1
            if 0 <= idx < len(dialogs):
                eid, name = dialogs[idx]
                print(f"\n✓ Selected: {name} (ID: {eid})\n")
                return str(eid)
            else:
                print(f"  Please enter a number between 1 and {len(dialogs)}")
        except ValueError:
            print("  Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)


async def main():
    parser = argparse.ArgumentParser(description="Vibe → Gemini Agent")
    parser.add_argument("-d", "--dialog", default=None,
                        help="Vibe group ID (omit to pick interactively)")
    parser.add_argument("-w", "--workspace", default="/share/datasets/home/wendler/code", help="Workspace for agent")
    parser.add_argument("--queue", default=".vibe-send-queue", help="Queue file for fallback when MCP fails")
    parser.add_argument("-i", "--interval", type=int, default=1, help="Poll interval (seconds)")
    parser.add_argument("--resume", action="store_true", default=None,
                        help="Resume last Gemini session (skip prompt)")
    parser.add_argument("--no-resume", action="store_true",
                        help="Start fresh session (skip prompt)")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    queue_path = workspace / args.queue

    # Ask whether to resume last session
    if args.resume:
        resume_session = True
    elif args.no_resume:
        resume_session = False
    else:
        try:
            answer = input("\n🔄 Resume last Gemini session? [y/N]: ").strip().lower()
            resume_session = answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    if resume_session:
        print("  ↳ Will resume last session\n")
    else:
        print("  ↳ Starting fresh session\n")

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

    # Interactive chat picker if no --dialog provided
    if args.dialog is None:
        args.dialog = await pick_dialog(tg.client)

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
        nonlocal processing, resume_session
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
            code = await run_agent(merged, workspace, args.dialog, queue_path, resume=resume_session)
            # After the first task, always resume (keep session continuity)
            resume_session = True
            await asyncio.sleep(DB_LOCK_DELAY * 2)  # Extra wait for MCP to release session
            # Forward queued messages (agent used echo >> queue when MCP failed)
            if queue_path.exists():
                lines = [l.strip() for l in queue_path.read_text().splitlines() if l.strip()]
                for line in lines:
                    try:
                        msg = line if line.startswith(BOT_PREFIX) else f"{BOT_PREFIX} {line}"
                        await connect_send_disconnect(entity, msg)
                    except Exception as e:
                        print(f"Failed to send queued message: {e}", file=sys.stderr)
                queue_path.write_text("")
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

    print("Vibe → Gemini Agent")
    print(f"Dialog: {args.dialog}")
    print(f"Workspace: {workspace}")
    print(f"Resume sessions: {resume_session}")
    print(f"Fetching every {args.interval}s. Press Ctrl+C to stop.\n")

    while True:
        await asyncio.sleep(args.interval)
        await fetch_and_enqueue()


if __name__ == "__main__":
    asyncio.run(main())
