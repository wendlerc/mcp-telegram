#!/bin/bash
# Run the Vibe → Gemini agent. Use from screen: ./run-agent-gemini.sh
# Requires: nvm with Node >= 20 (for gemini CLI), uv, Telegram session
cd "$(dirname "$0")"

# Load nvm so gemini CLI (Node 22) is available
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22 2>/dev/null

# Omit --dialog to get the interactive chat picker at startup.
# To skip the picker: ./run-agent-gemini.sh --dialog=-5150901335
exec uv run python agent_vibe_gemini.py -w /share/datasets/home/wendler/code -i 1 "$@"
