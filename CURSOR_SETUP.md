# Cursor MCP Setup

## Add the Telegram MCP Server

1. **Open Cursor Settings**
   - Press `⌘ + ,` (Mac) or `Ctrl + ,` (Windows/Linux)
   - Or: **Cursor** → **Settings**

2. **Go to MCP**
   - Search for "MCP" in the settings search bar
   - Or navigate to **Features** → **Model Context Protocol**

3. **Add the Telegram server**
   - Click **"Add new MCP server"** or **"Edit Config"**
   - Add this entry (merge with existing `mcpServers` if you have other servers):

```json
{
  "mcpServers": {
    "telegram": {
      "command": "node",
      "args": [
        "/path/to/mcp-telegram/dist/index.js",
        "mcp"
      ]
    }
  }
}
```

4. **Save** and **restart Cursor** (or reload the window: `⌘ + Shift + P` → "Developer: Reload Window")

## Verify

Ask in chat:
- "List my Telegram chats"
- "Show my recent dialogs"

If connected, the AI will use the Telegram tools to respond.
