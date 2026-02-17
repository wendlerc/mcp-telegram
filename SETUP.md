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

## Vibe→Agent Flow

1. agent_vibe polls Telegram group
2. On new message: sends "Starting...", runs `cursor agent` with instruction
3. Agent uses telegram-agent MCP (send_message, send_file) or .vibe-send-queue
4. agent_vibe forwards queue, sends "Done ✓"

## Push to GitHub

SSH key needs passphrase. Run manually:

```bash
ssh-add ~/.ssh/id_ed25519   # enter passphrase when prompted
cd mcp-telegram && git push origin main
```
