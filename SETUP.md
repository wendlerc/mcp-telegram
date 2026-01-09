# Telegram MCP Server - Claude Code Setup

## Quick Setup for Claude Code

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Click "Create new application"
4. Fill in the form:
   - Title: `MCP Server`
   - Short name: `mcp`
   - Platform: `Desktop`
5. Click "Create application" and copy your `api_id` and `api_hash`

### 2. Configure

```bash
cp .env.example .env
nano .env  # Add your api_id and api_hash
```

### 3. Sign In (One-Time)

```bash
npm run sign-in
```

Enter your phone number and confirmation code when prompted.

### 4. Install to Claude Code

```bash
claude mcp add --scope user --transport stdio telegram -- \
  node /Users/gsarti/Documents/projects/mcps/mcp-telegram/dist/index.js
```

### 5. Verify

Ask Claude:
- "List my Telegram chats"
- "Show recent messages"

## Uninstall

```bash
claude mcp remove telegram
```
