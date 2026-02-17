#!/bin/bash
# Wrapper to ensure MCP server gets correct env when spawned by Cursor agent.
# Uses run_mcp_reconnect.py for reconnect-on-failure when connection drops during long agent runs.
# Use venv python directly (faster than uv run) — Cursor may timeout during MCP handshake.
export XDG_STATE_HOME="${XDG_STATE_HOME:-/share/datasets/home/wendler/code/mcp-telegram/.session-state}"
export API_ID="${API_ID:-34785037}"
export API_HASH="${API_HASH:-83d6e4eaef935264ea9f3c0599d254bf}"
export PYTHONUNBUFFERED=1
MCP_DIR="/share/datasets/home/wendler/code/mcp-telegram"
exec "$MCP_DIR/.venv/bin/python" "$MCP_DIR/run_mcp_reconnect.py"
