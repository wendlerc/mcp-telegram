#!/bin/bash
# MCP server for Gemini CLI agent — uses separate session to avoid "database is locked"
# when the IDE or another MCP instance also has a session open.
# Uses nvm Node 22 (Gemini CLI requires Node >= 20).
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 2>/dev/null

export XDG_STATE_HOME="${XDG_STATE_HOME:-/share/datasets/home/wendler/code/mcp-telegram/.session-state-agent-mcp}"
export API_ID="${API_ID:-34785037}"
export API_HASH="${API_HASH:-83d6e4eaef935264ea9f3c0599d254bf}"
export PYTHONUNBUFFERED=1
MCP_DIR="/share/datasets/home/wendler/code/mcp-telegram"
exec "$MCP_DIR/.venv/bin/python" "$MCP_DIR/run_mcp_reconnect.py"
