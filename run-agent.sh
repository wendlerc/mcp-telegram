#!/bin/bash
# Run the Vibe agent. Use from screen: ./run-agent.sh
cd "$(dirname "$0")"
exec uv run python agent_vibe.py -w /share/datasets/home/wendler/code --dialog -5150901335 -i 1
