# MCP Telegram

A TypeScript implementation of an MCP (Model Context Protocol) server for working with Telegram through MTProto, built using FastMCP. Includes a **Vibe → Cursor Agent** workflow that executes instructions from a Telegram group as headless Cursor agent tasks.

**Python/uv setup:** If you don't have Node.js, see [UV_SETUP.md](UV_SETUP.md) for a Python-based setup using `uv` (no Node required). Run both `login_local.py` and `login_local.py --agent` so MCP and agent_vibe use separate sessions (avoids "database is locked"). Run `agent mcp enable telegram` so the agent can use send_message.

## Overview

- **MCP tools** for Cursor: `listDialogs`, `listMessages`, `createGroup`, `sendMessage`
- **Vibe resource**: MCP resource `vibe://messages` for loading Telegram instructions into context
- **Vibe → Agent**: Push-based workflow that runs Cursor agent on each new message from a Telegram group

## Installation

```bash
npm install
npm run build
```

Create a `.env` file with `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` (from [my.telegram.org](https://my.telegram.org)), then run `node dist/index.js sign-in` to authenticate.

## Usage

### Sign in

```bash
node dist/index.js sign-in
```

### Start MCP server (for Cursor)

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "node",
      "args": ["/path/to/mcp-telegram/dist/index.js", "mcp"]
    }
  }
}
```

### Vibe → Cursor Agent (Push Workflow)

Run a process that listens for new messages in your Vibe Telegram group and executes each as a Cursor agent task:

```bash
node dist/index.js agent
```

**How it works:**
- Fetches messages via `getMessages` every 3s (same API for every instruction)
- Skips bot status messages (see caveat below)
- Uses `--resume` so all instructions share the same Cursor chat (context preserved)
- Agent posts progress back to Vibe via the `sendMessage` MCP tool

**Caveat — `[bot]` prefix required:** The agent must prefix every status message it sends to Vibe with `[bot]` (e.g. `[bot] Starting...`, `[bot] Done ✓`). Otherwise those messages will be fetched and processed as new tasks. The agent prompt and `.cursorrules` enforce this; ensure both are in place.

**Options:**
- `-d, --dialog <id>` — Vibe group ID (default: -5150901335)
- `-w, --workspace <path>` — Workspace for Cursor agent
- `-i, --interval <seconds>` — Fetch interval (default: 3)
- `--chat-file <file>` — File to persist shared Cursor chat ID (default: .vibe-agent-chat)

**Requirements:** Cursor CLI (`cursor agent`) installed and authenticated.

### Other CLI commands

```bash
# Poll Vibe to file (legacy)
node dist/index.js poll -d -5150901335 -o .vibe-instructions.md

# Create a new Telegram group
node dist/index.js create-group "My Group"

# Logout
node dist/index.js logout
```

### Sending files (Python setup)

**MCP `send_file` tool:** Use this when `send_message` with `file_path` fails (Cursor may serialize `file_path` incorrectly). The `send_file` tool accepts a single path string and works reliably:

- **Parameters:** `entity` (chat ID), `file_path` (absolute path), `message` (optional caption)
- **Example:** `send_file(entity="-5150901335", file_path="/path/to/video.mp4", message="[bot] Caption")`
- **Note:** Restart the MCP server (or Cursor) after package updates to pick up the `send_file` tool.

**Reminder script (`remind_when_training_done.py`):** Polls for `model.pt` in a toy-wm experiment dir; when training finishes, sends a reminder to Vibe. Run in background: `nohup uv run python remind_when_training_done.py --run-dir blissful-ring-807 &`

**CLI fallback (`send_video.py`):** When the agent is stopped and you need to send a file without MCP:

```bash
cd mcp-telegram
uv run python send_video.py /path/to/video.mp4 "[bot] Optional caption"
```

If you get "database is locked", run `uv run python login_local.py --agent` to create a separate session for agent_vibe (see [UV_SETUP.md](UV_SETUP.md)).

CLI Options for the `mcp` command:
- `-t, --transport <type>`: Transport type (stdio, sse), defaults to 'stdio'
- `-p, --port <number>`: Port for HTTP/SSE transport, defaults to 3000
- `-e, --endpoint <path>`: Endpoint for SSE transport, defaults to 'mcp'

### Starting the MCP Server

Start the MCP server with stdio transport (default, used by Cursor AI):
```bash
npm run start
# or
npm run mcp
```

You can also run the server programmatically:

```typescript
import server, { startServer } from 'mcp-telegram';

// Start the server with the configuration
startServer(server);
```

### Environment Variables

The application uses the following environment variables:

- `TELEGRAM_API_ID`: Your Telegram API ID
- `TELEGRAM_API_HASH`: Your Telegram API Hash
- `TRANSPORT_TYPE`: Transport type ('stdio', 'http', or 'sse'), defaults to 'stdio'
- `PORT`: Port for HTTP or SSE transports, defaults to 3000
- `ENDPOINT`: Endpoint for SSE transport, defaults to 'mcp'
- `LOG_LEVEL`: Logging level, defaults to 'info'

These can be set in a `.env` file in the project root.

## Development

Development requires Node.js version 18 or higher.

```bash
# Run in development mode
npm run dev

# Lint the code
npm run lint

# Run tests
npm run test
```

## FastMCP Integration

The server is implemented using FastMCP, which provides a modern TypeScript implementation of the Model Context Protocol. It supports stdio and SSE transports, making it compatible with different client integration approaches.

### Server Transports

- **stdio**: Default transport, useful for direct integration with tools like Cursor AI
- **sse**: Server-Sent Events transport for real-time communication

## MCP Tools

### listDialogs

List available dialogs, chats and channels.

Parameters: `unread`, `archived`, `ignorePinned`

### listMessages

List messages in a given dialog, chat or channel.

Parameters: `dialogId`, `unread`, `limit` (default: 20)

### createGroup

Create a new Telegram supergroup.

Parameters: `title`, `about`

### sendMessage

Send a message to a dialog/group.

Parameters: `dialogId`, `message`

**Vibe workflow:** When sending to the Vibe group (used by the agent), prefix status updates with `[bot]` so they are not processed as new tasks.

## MCP Resource

### Vibe Messages (`vibe://messages`)

In Cursor, type `@` and add **Vibe Messages** to load the latest instructions from your Vibe Telegram group into context.

## Project Structure

```
src/
├── config.ts               # Application configuration
├── index.ts                # CLI entry point (sign-in, mcp, agent, poll, etc.)
├── mcp.ts                  # MCP server setup (tools, Vibe resource)
├── tools/                  # MCP tool implementations
│   ├── index.ts
│   ├── listDialogs.ts
│   ├── listMessages.ts
│   ├── createGroup.ts
│   └── sendMessage.ts
├── lib/                    # Core Telegram functionality
│   ├── index.ts
│   └── telegram.ts
└── utils/
    ├── errorHandler.ts
    └── logger.ts
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.