#!/usr/bin/env python3
"""
Run MCP Telegram server with reconnect-on-failure.
Patches the server to reconnect when the Telegram connection drops during long agent runs.
"""
import asyncio
import logging
import sys

# Apply before mcp_telegram imports
logging.getLogger("telethon").setLevel(logging.WARNING)

from mcp_telegram.telegram import Telegram
from mcp_telegram.server import mcp
from mcp_telegram import server as server_module


class ReconnectTelegram(Telegram):
    """Telegram wrapper that reconnects on connection failure."""

    async def _ensure_connected(self):
        if self._client is None:
            return
        if not self._client.is_connected():
            await self._client.connect()

    async def _with_reconnect(self, make_coro):
        """Run coroutine, retry with reconnect on connection errors.
        make_coro must be a callable returning a coroutine (for retry to get fresh coro).
        """
        last_err = None
        for attempt in range(2):
            try:
                await self._ensure_connected()
                return await make_coro()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(x in err_str for x in ("connection", "disconnect", "not connected", "closed")):
                    try:
                        if self._client and self._client.is_connected():
                            await self._client.disconnect()
                    except Exception:
                        pass
                    await asyncio.sleep(1)
                    continue
                raise
        raise last_err

    async def send_message(self, entity, message="", file_path=None, reply_to=None):
        await self._with_reconnect(
            lambda: Telegram.send_message(self, entity, message, file_path=file_path, reply_to=reply_to)
        )

    async def edit_message(self, entity, message_id, message):
        await self._with_reconnect(lambda: Telegram.edit_message(self, entity, message_id, message))

    async def delete_message(self, entity, message_ids):
        await self._with_reconnect(lambda: Telegram.delete_message(self, entity, message_ids))

    async def search_dialogs(self, query, limit=10, global_search=False):
        return await self._with_reconnect(lambda: Telegram.search_dialogs(self, query, limit, global_search))

    async def get_draft(self, entity):
        return await self._with_reconnect(lambda: Telegram.get_draft(self, entity))

    async def set_draft(self, entity, message):
        await self._with_reconnect(lambda: Telegram.set_draft(self, entity, message))

    async def get_messages(self, entity, limit=10, start_date=None, end_date=None, unread=False, mark_as_read=False):
        return await self._with_reconnect(
            lambda: Telegram.get_messages(self, entity, limit, start_date, end_date, unread, mark_as_read)
        )

    async def download_media(self, entity, message_id, path=None):
        return await self._with_reconnect(lambda: Telegram.download_media(self, entity, message_id, path))

    async def message_from_link(self, link):
        return await self._with_reconnect(lambda: Telegram.message_from_link(self, link))


# Replace tg with reconnect wrapper
server_module.tg = ReconnectTelegram()

# Use lazy connect: don't connect on startup (takes 3+ sec, agent may timeout).
# Connect on first tool call via _ensure_connected.
async def lazy_lifespan(server):
    try:
        server_module.tg.create_client()
        yield
    finally:
        try:
            if server_module.tg._client and server_module.tg._client.is_connected():
                await server_module.tg._client.disconnect()
        except Exception:
            pass

server_module.app_lifespan = lazy_lifespan

if __name__ == "__main__":
    mcp.run()
