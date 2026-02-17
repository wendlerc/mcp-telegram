#!/bin/bash
# Run the Doom vibe agent in a separate group.
# 1. Create "Doom" group in Telegram, add @userinfobot to get group ID
# 2. Replace DOOM_GROUP_ID below with the numeric ID (e.g. -1001234567890)
# 3. screen -dmS cursor-agent-doom ./run-agent-doom.sh
DOOM_GROUP_ID="${DOOM_GROUP_ID:--5140326713}"
cd "$(dirname "$0")"
exec uv run python agent_vibe.py -w /share/datasets/home/wendler/code \
  --dialog="$DOOM_GROUP_ID" \
  --chat-file=.vibe-agent-chat-doom \
  --queue=.vibe-send-queue-doom \
  -i 1
