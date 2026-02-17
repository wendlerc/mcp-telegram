# MCP Telegram — Current Setup

## Session Layout

Three separate Telegram sessions avoid SQLite "database is locked":

| Session Dir | Used By | Purpose |
|-------------|---------|---------|
| `.session-state` | Cursor IDE MCP (`telegram`) | Composer tools (send_message, send_file) |
| `.session-state-agent` | agent_vibe.py | Polling, Start/Done status |
| `.session-state-agent-mcp` | Cursor Agent MCP (`telegram-agent`) | Agent send_message, send_file when running |

## MCP Config (~/.cursor/mcp.json)

```json
{
  "mcpServers": {
    "telegram": {
      "command": "/path/to/mcp-telegram/start-mcp.sh",
      "args": [],
      "env": {
        "API_ID": "...",
        "API_HASH": "...",
        "XDG_STATE_HOME": "/path/to/mcp-telegram/.session-state"
      }
    },
    "telegram-agent": {
      "command": "/path/to/mcp-telegram/start-mcp-agent.sh",
      "args": [],
      "env": {
        "API_ID": "...",
        "API_HASH": "...",
        "XDG_STATE_HOME": "/path/to/mcp-telegram/.session-state-agent-mcp"
      }
    }
  }
}
```

- **telegram**: Cursor IDE Composer
- **telegram-agent**: Cursor Agent (run `agent mcp enable telegram-agent`)

## Login (one-time)

```bash
uv run python login_local.py              # .session-state (IDE MCP)
uv run python login_local.py --agent      # .session-state-agent (agent_vibe)
uv run python login_local.py --agent-mcp  # .session-state-agent-mcp (Agent MCP)
```

## Sending to Vibe

- **MCP tools**: `send_message(entity="-5150901335", message="[bot] ...")`, `send_file(entity, file_path, message)`
- **Fallback**: `echo "[bot] msg" >> .vibe-send-queue` (agent_vibe forwards after agent finishes)
- **CLI**: `uv run python send_video.py /path/to/file "[bot] caption"` — requires session free (stop agent_vibe first, or use `XDG_STATE_HOME=.session-state-agent-mcp`)

## agent_vibe options

- `-d, --dialog` — Group ID (default: -5150901335)
- `--chat-file` — Cursor chat persistence (default: .vibe-agent-chat)
- `--queue` — Fallback queue file when MCP fails (default: .vibe-send-queue)
- `-w, --workspace` — Agent workspace

The prompt includes the dialog entity ID so the agent reports to the correct group (fixes second-agent reporting to wrong group).

## Vibe→Agent Flow

1. agent_vibe polls Telegram group
2. On new message: sends "Starting...", runs `cursor agent` with instruction
3. Agent uses telegram-agent MCP (send_message, send_file) or .vibe-send-queue
4. agent_vibe forwards queue, sends "Done ✓"

## Second Agent (e.g. Doom)

Run a second agent for another group with its own context:

```bash
# 1. Get group ID: uv run python list_dialogs.py (stop agent_vibe first if "database is locked")
# 2. Edit run-agent-doom.sh: DOOM_GROUP_ID or set env
# 3. screen -dmS cursor-agent-doom ./run-agent-doom.sh
```

Each agent uses `--dialog`, `--chat-file`, `--queue` so they have separate chats and send queues. The prompt includes the entity ID so the agent reports to the correct group.

## list_dialogs.py

Find group IDs when @userinfobot doesn't work:

```bash
uv run python list_dialogs.py   # stop agent_vibe first if "database is locked"
```

## End-to-end setup

```bash
./setup_end2end.sh
```

Guides through install, login, MCP config, and run-agent.

## Push to GitHub

SSH key needs passphrase. When `/tmp` is full, use `ssh-agent -a` to put the socket elsewhere:

```bash
# Workaround when /tmp has no space
AGENT_DIR=/path/to/code/tmp/ssh-agent-push
mkdir -p "$AGENT_DIR"
eval $(ssh-agent -s -a "$AGENT_DIR/agent")
ssh-add ~/.ssh/id_ed25519   # enter passphrase when prompted
cd mcp-telegram && git push origin main
```

Or use `./push.sh` (prompts for passphrase).
