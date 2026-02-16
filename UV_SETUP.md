# mcp-telegram with uv (Python)

Uses the Python mcp-telegram (Telethon) instead of Node.js. No Node required.

## 1. Install dependencies

```bash
cd /share/datasets/home/wendler/code/mcp-telegram
uv sync
```

## 2. Install Cursor CLI (for Vibe→Agent workflow)

```bash
curl https://cursor.com/install -fsS | bash
```

Ensure `~/.local/bin` is in your PATH. The installer creates `agent` (not `cursor`). If `cursor agent` is needed, create `~/.local/bin/cursor`:

```bash
echo '#!/bin/bash
[[ "$1" == "agent" ]] && shift
exec agent "$@"' > ~/.local/bin/cursor
chmod +x ~/.local/bin/cursor
```

## 3. Telegram login (one-time)

Use the local login script — reads credentials from `.env`, stores session in project dir (avoids NFS/home path issues):

```bash
cd /share/datasets/home/wendler/code/mcp-telegram
uv run python login_local.py
uv run python login_local.py --agent
```

The first login creates the MCP session (`.session-state`). The second creates a separate agent session (`.session-state-agent`) so agent_vibe and MCP don't lock each other's SQLite session file. Enter phone + code for each.

## 4. Cursor Agent login (one-time)

Authenticate the Cursor CLI so it can run agent tasks:

```bash
agent login
```

Follow the prompts (browser or token). Run `agent status` to verify.

## 4b. Enable Telegram MCP for agent (one-time)

The agent needs the Telegram MCP approved to use send_message:

```bash
agent mcp enable telegram
```

This lets the agent send results to the Vibe chat via the MCP tool.

## 5. Cursor MCP config

Use the `start-mcp.sh` wrapper so the agent reliably gets env when spawning the MCP server:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "/share/datasets/home/wendler/code/mcp-telegram/start-mcp.sh",
      "args": [],
      "env": {
        "API_ID": "34785037",
        "API_HASH": "83d6e4eaef935264ea9f3c0599d254bf",
        "XDG_STATE_HOME": "/share/datasets/home/wendler/code/mcp-telegram/.session-state"
      }
    }
  }
}
```

The wrapper sets env fallbacks so the server starts even if the agent doesn't pass them. Restart Cursor after saving.

## 6. Run Vibe→Agent in screen

Create a screen and run the agent there so it persists:

```bash
screen -dmS cursor-agent
screen -S cursor-agent -X stuff "cd /share/datasets/home/wendler/code/mcp-telegram && ./run-agent.sh\r"
```

Edit `run-agent.sh` to set your group ID (e.g. `--dialog=-5150901335`). Use `--dialog=ID` (not `-d ID`) so negative IDs are parsed correctly. Get the ID from MCP `search_dialogs` or create a group. The agent uses Composer 1.5 by default (set in `agent_vibe.py`).

**Attach to the screen:**
```bash
screen -r cursor-agent
```

**Detach:** `Ctrl+A` then `D`

**Stop the agent:** Attach to screen, then `Ctrl+C`

## Getting your group ID

- **MCP**: Ask Cursor to search your dialogs (e.g. "search my Telegram dialogs for X")
- **CLI**: `uv run mcp-telegram tools` then use `search_dialogs`
- **Create group**: `uv run mcp-telegram create-group "My Vibe Group"` — ID is printed
- **Bots**: Add [@userinfobot](https://t.me/userinfobot) to the group; it replies with the group ID

## Sending results to Telegram (MCP)

After `agent mcp enable telegram`, the agent can use the **send_message** MCP tool. Use entity set to your Vibe group ID (e.g. `-5150901335`) and message prefixed with `[bot]`. The agent prompt instructs it to send summaries, lists, and findings this way.

**Sending files:** Use the **send_file** MCP tool (not `send_message` with `file_path`). Cursor may serialize `file_path` incorrectly for `send_message`. `send_file` accepts `entity`, `file_path` (str), and optional `message`. Restart MCP/Cursor after package updates to pick up new tools.

**Important:** `agent_vibe.py` disconnects from Telegram before running the agent so the MCP server can use the session. Start/Done status is sent by reconnecting briefly.

## Troubleshooting

**"Connection failed" / "Tool not found"** — Use `start-mcp.sh` as the MCP command (see step 5). Restart Cursor after changing mcp.json. Run `agent mcp enable telegram` and `agent mcp list` to verify.

**"database is locked"** — agent_vibe and MCP share the same SQLite session file by default. Run both logins so each has its own session:

```bash
uv run python login_local.py
uv run python login_local.py --agent
```

## Summary

- **Telegram MCP**: Tools in Cursor (send_message, send_file, list dialogs, etc.)
- **Vibe→Agent**: `agent_vibe.py` polls a Telegram group and runs Cursor agent on each message
- **Results**: Agent uses send_message (text) and send_file (files) MCP tools (run `agent mcp enable telegram` first)
- **Sessions**: MCP uses `.session-state`, agent_vibe uses `.session-state-agent` (run both logins to avoid "database is locked")
