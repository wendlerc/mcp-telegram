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

Ensure `~/.local/bin` is in your PATH. The installer creates `agent` and `cursor-agent`; a `cursor` wrapper is provided so `cursor agent` works.

## 3. Telegram login (one-time)

Use the local login script — reads credentials from `.env`, stores session in project dir (avoids NFS/home path issues):

```bash
cd /share/datasets/home/wendler/code/mcp-telegram
uv run python login_local.py
```

Enter only your phone number and the code from Telegram (no API ID/hash prompts).

## 4. Cursor Agent login (one-time)

Authenticate the Cursor CLI so it can run agent tasks:

```bash
agent login
```

Follow the prompts (browser or token). Run `agent status` to verify.

## 5. Cursor MCP config

Add to Cursor → Settings → MCP → Edit Config. **Important:** `XDG_STATE_HOME` must point to the project session dir so the server finds your login:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uv",
      "args": ["run", "--project", "/share/datasets/home/wendler/code/mcp-telegram", "mcp-telegram", "start"],
      "env": {
        "API_ID": "34785037",
        "API_HASH": "83d6e4eaef935264ea9f3c0599d254bf",
        "XDG_STATE_HOME": "/share/datasets/home/wendler/code/mcp-telegram/.session-state"
      }
    }
  }
}
```

Restart Cursor after saving.

## 6. Run Vibe→Agent in screen

Create a screen and run the agent there so it persists:

```bash
screen -dmS cursor-agent
screen -S cursor-agent -X stuff "cd /share/datasets/home/wendler/code/mcp-telegram && uv run python agent_vibe.py -w /share/datasets/home/wendler/code -d YOUR_GROUP_ID -i 1\r"
```

Replace `YOUR_GROUP_ID` with your Telegram group ID (e.g. `-5150901335`). Get it from MCP `search_dialogs` or create a group.

**Attach to the screen:**
```bash
screen -r cursor-agent
```

**Detach:** `Ctrl+A` then `D`

**Stop the agent:** Attach to screen, then `Ctrl+C`

## Summary

- **Telegram MCP**: Tools in Cursor (send_message, list dialogs, etc.)
- **Vibe→Agent**: `agent_vibe.py` polls a Telegram group and runs Cursor agent on each message
- **Workspace**: `/share/datasets/home/wendler/code`
