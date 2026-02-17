#!/bin/bash
# End-to-end setup for MCP Telegram + Vibe→Agent.
# Run from mcp-telegram dir. Requires: .env with TELEGRAM_API_ID, TELEGRAM_API_HASH
set -e
MCP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$MCP_DIR"

echo "=== 1. Install dependencies ==="
uv sync

echo ""
echo "=== 2. Check .env ==="
if [ ! -f .env ]; then
    echo "Create .env with TELEGRAM_API_ID and TELEGRAM_API_HASH (from my.telegram.org)"
    exit 1
fi
source .env
if [ -z "$TELEGRAM_API_ID" ] && [ -z "$API_ID" ]; then
    echo "Set TELEGRAM_API_ID (or API_ID) in .env"
    exit 1
fi
if [ -z "$TELEGRAM_API_HASH" ] && [ -z "$API_HASH" ]; then
    echo "Set TELEGRAM_API_HASH (or API_HASH) in .env"
    exit 1
fi
echo "OK: .env found"

echo ""
echo "=== 3. Telegram login (one-time, interactive) ==="
echo "Run these three commands. Enter phone + code for each:"
echo "  uv run python login_local.py"
echo "  uv run python login_local.py --agent"
echo "  uv run python login_local.py --agent-mcp"
read -p "Run first login now? [y/N] " r
if [ "$r" = "y" ] || [ "$r" = "Y" ]; then
    uv run python login_local.py
fi
read -p "Run agent login? [y/N] " r
if [ "$r" = "y" ] || [ "$r" = "Y" ]; then
    uv run python login_local.py --agent
fi
read -p "Run agent-mcp login? [y/N] " r
if [ "$r" = "y" ] || [ "$r" = "Y" ]; then
    uv run python login_local.py --agent-mcp
fi

echo ""
echo "=== 4. Cursor Agent MCP ==="
echo "Run: agent mcp disable telegram; agent mcp enable telegram-agent"
echo "Add to ~/.cursor/mcp.json (see SETUP.md for full config):"
echo '  "telegram": { "command": "'"$MCP_DIR"'/start-mcp.sh", ... }'
echo '  "telegram-agent": { "command": "'"$MCP_DIR"'/start-mcp-agent.sh", ... }'

echo ""
echo "=== 5. Get your group ID ==="
echo "  uv run python list_dialogs.py   # list all groups (stop agent_vibe first if locked)"
echo "  Or add @userinfobot to group, send /start"

echo ""
echo "=== 6. Edit run-agent.sh ==="
echo "Set --dialog=YOUR_GROUP_ID (e.g. -5150901335)"

echo ""
echo "=== 7. Start Vibe→Agent ==="
echo "  screen -dmS cursor-agent"
echo "  screen -S cursor-agent -X stuff \"cd $MCP_DIR && ./run-agent.sh\\r\""
echo "  screen -r cursor-agent   # attach"

echo ""
echo "=== Optional: Second agent (e.g. Doom) ==="
echo "  Edit run-agent-doom.sh: set DOOM_GROUP_ID"
echo "  screen -dmS cursor-agent-doom ./run-agent-doom.sh"

echo ""
echo "Done. See UV_SETUP.md and SETUP.md for details."
