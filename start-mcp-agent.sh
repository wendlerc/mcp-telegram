#!/bin/bash
# MCP server for Cursor *agent* — uses separate session to avoid "database is locked"
# when Cursor IDE also has MCP running (both would otherwise use .session-state).
export XDG_STATE_HOME="${XDG_STATE_HOME:-/share/datasets/home/wendler/code/mcp-telegram/.session-state-agent-mcp}"
export API_ID="${API_ID:-34785037}"
export API_HASH="${API_HASH:-83d6e4eaef935264ea9f3c0599d254bf}"
export PYTHONUNBUFFERED=1
MCP_DIR="/share/datasets/home/wendler/code/mcp-telegram"
exec "$MCP_DIR/.venv/bin/python" "$MCP_DIR/run_mcp_reconnect.py"
