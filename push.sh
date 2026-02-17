#!/bin/bash
# Push to GitHub without needing /tmp (workaround when /tmp is full).
# Usage: ./push.sh
# Requires: passphrase when prompted, or run with: echo 129 | ./push.sh (if expect available)
set -e
MCP_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$MCP_DIR/../tmp/ssh-agent-push"
mkdir -p "$AGENT_DIR"
eval $(ssh-agent -s -a "$AGENT_DIR/agent")
echo "Add key (passphrase 129):" && ssh-add ~/.ssh/id_ed25519
cd "$MCP_DIR" && git push origin main
kill $SSH_AGENT_PID 2>/dev/null || true
