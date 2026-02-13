#!/usr/bin/env node

import bigInt from 'big-integer';
import { FastMCP } from 'fastmcp';

import { config } from './config.js';
import { tools } from './tools/index.js';
import { createClient } from './lib/telegram.js';
import { logger } from './utils/logger.js';
import pkg from '../package.json' with { type: 'json' };

const VIBE_DIALOG_ID = '-5150901335';

/**
 * Create and configure the MCP server
 */
export function createServer() {
  // Create FastMCP server
  const server = new FastMCP({
    name: 'mcp-telegram',
    version: pkg.version as `${number}.${number}.${number}`,
  });

  // Register Vibe messages as an MCP resource - Cursor can add this to context
  server.addResource({
    uri: 'vibe://messages',
    name: 'Vibe Messages',
    mimeType: 'text/markdown',
    description: 'Latest messages from the Vibe Telegram group - your instructions',
    async load() {
      const client = await createClient();
      const messages = await client.getMessages(bigInt(VIBE_DIALOG_ID), { limit: 20 });
      const lines: string[] = ['# Instructions from Vibe', '', `*Fetched: ${new Date().toISOString()}*`, '', '---', ''];
      for (const msg of (messages || []).reverse()) {
        const text = (msg as { message?: string }).message ?? '';
        if (text) {
          const date = (msg as { date?: number }).date
            ? new Date((msg as { date: number }).date * 1000).toLocaleString()
            : '';
          lines.push(`**${date}**`);
          lines.push('');
          lines.push(text);
          lines.push('');
          lines.push('---');
          lines.push('');
        }
      }
      return { text: lines.join('\n') };
    },
  });

  // Register all tools with FastMCP
  for (const tool of tools) {
    logger.info(`Tool added: ${tool.name}`);
    // @ts-ignore - FastMCP types may not match exactly
    server.addTool(tool);
  }

  // Set up event handlers
  server.on('connect', (event) => {
    // @ts-ignore - FastMCP Session type might not have id property
    const sessionId = event.session?.id || 'unknown';
    logger.info('Client connected', { sessionId });
  });

  server.on('disconnect', (event) => {
    // @ts-ignore - FastMCP Session type might not have id property
    const sessionId = event.session?.id || 'unknown';
    logger.info('Client disconnected', { sessionId });
  });

  return server;
}

/**
 * Start the server with configured transport
 */
export function startServer(server: FastMCP) {
  const transportType = config.server.transportType;
  
  logger.info(`Starting ${server.options.name} v${server.options.version}`);
  
  // Start the server based on the transport type
  if (transportType === 'stdio') {
    server.start({
      transportType: 'stdio',
    });
    logger.info('Server started with stdio transport');
  } else if (transportType === 'sse') {
    const port = config.server.port || 3000;
    const endpoint = config.server.endpoint || 'mcp';
    
    server.start({
      transportType: 'sse',
      sse: {
        endpoint: `/${endpoint}`,
        port: port,
      },
    });
    logger.info(`Server started with SSE transport on port ${port} at endpoint /${endpoint}`);
  } else {
    logger.error(`Unsupported transport type: ${transportType}`);
    process.exit(1);
  }

  return server;
}

// Set up process event handlers
process.on('uncaughtException', (error) => {
  logger.error('Uncaught exception', { error });
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled Promise rejection', { reason });
});

// Create server instance (but don't start it)
const server = createServer();

export default server; 