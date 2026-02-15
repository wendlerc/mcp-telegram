#!/usr/bin/env node

import { spawn, execSync } from 'child_process';
import { Command } from 'commander';
import { config as dotenvConfig } from 'dotenv';
import { createInterface } from 'readline';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

import { Api } from 'telegram';
import bigInt from 'big-integer';
import { connectToTelegram, logoutFromTelegram, createClient } from './lib/index.js';
import { logger } from './utils/logger.js';
import { config } from './config.js';
import server, { startServer } from './mcp.js';
import pkg from '../package.json' with { type: 'json' };

// Load environment variables
dotenvConfig();

// Create CLI program
const program = new Command();

// Set basic CLI info
program
  .name('mcp-telegram')
  .description('Telegram MCP server - interact with Telegram via Model Context Protocol')
  .version(pkg.version);

// Command: sign-in
program
  .command('sign-in')
  .description('Sign in to Telegram')
  .action(async () => {
    logger.info('Starting Telegram sign-in process...');
    
    const apiId = config.telegram.apiId;
    const apiHash = config.telegram.apiHash;
    
    if (!apiId || !apiHash) {
      logger.error('TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables must be set');
      process.exit(1);
    }
    
    const rl = createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    const phoneNumber = await new Promise<string>(resolve => {
      rl.question('Enter your phone number (with country code): ', answer => {
        resolve(answer);
        rl.close();
      });
    });
    
    try {
      await connectToTelegram(apiId, apiHash, phoneNumber);
      logger.info('Sign-in successful!');
      process.exit(0);
    } catch (error) {
      logger.error('Failed to sign in:', error);
      process.exit(1);
    }
  });

// Command: mcp
program
  .command('mcp')
  .description('Start the MCP server')
  .option('-t, --transport <type>', 'Transport type (stdio, sse)', 'stdio')
  .option('-p, --port <number>', 'Port for HTTP/SSE transport', '3000')
  .option('-e, --endpoint <path>', 'Endpoint for SSE transport', 'mcp')
  .action(async (options) => {
    // Override config with command line options
    if (options.transport) {
      config.server.transportType = options.transport;
    }
    if (options.port) {
      config.server.port = parseInt(options.port, 10);
    }
    if (options.endpoint) {
      config.server.endpoint = options.endpoint;
    }
    
    logger.info(`Starting MCP server with ${config.server.transportType} transport...`);
    
    // Set up graceful shutdown
    process.on('SIGINT', () => {
      logger.info('Server shutting down (SIGINT)');
      process.exit(0);
    });
    
    process.on('SIGTERM', () => {
      logger.info('Server shutting down (SIGTERM)');
      process.exit(0);
    });
    
    // Start the server
    startServer(server);
  });

// Command: poll
program
  .command('poll')
  .description('Continuously fetch messages from a group and write to file (for Cursor to read)')
  .option('-d, --dialog <id>', 'Dialog/group ID', '-5150901335')
  .option('-o, --output <file>', 'Output file path', '.vibe-instructions.md')
  .option('-i, --interval <seconds>', 'Poll interval in seconds', '30')
  .action(async (options) => {
    const fs = await import('fs');
    const path = await import('path');
    const dialogId = options.dialog;
    const outputPath = path.resolve(process.cwd(), options.output);
    const intervalMs = parseInt(options.interval, 10) * 1000;

    console.log(`Polling Vibe (${dialogId}) every ${options.interval}s → ${outputPath}`);
    console.log('Press Ctrl+C to stop.\n');

    const fetchAndWrite = async () => {
      try {
        const client = await createClient();
        const messages = await client.getMessages(dialogId, { limit: 20 });
        const lines: string[] = [
          '# Instructions from Vibe',
          '',
          `*Last updated: ${new Date().toISOString()}*`,
          '',
          '---',
          '',
        ];
        for (const msg of (messages || []).reverse()) {
          const text = (msg as { message?: string; text?: string }).message ?? (msg as { message?: string; text?: string }).text ?? '';
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
        fs.writeFileSync(outputPath, lines.join('\n'));
        process.stdout.write(`\r✓ Updated ${outputPath} (${messages?.length || 0} messages)`);
      } catch (err) {
        process.stdout.write(`\r✗ Error: ${(err as Error).message}`);
      }
    };

    await fetchAndWrite();
    setInterval(fetchAndWrite, intervalMs);
  });

// Command: agent - fetch messages and run Cursor agent on each (single process, same path for all)
program
  .command('agent')
  .description('Fetch Vibe messages and run Cursor agent on each')
  .option('-d, --dialog <id>', 'Dialog/group ID', '-5150901335')
  .option('-w, --workspace <path>', 'Workspace for Cursor agent', process.cwd())
  .option('--chat-file <file>', 'File to persist shared chat ID', '.vibe-agent-chat')
  .option('-i, --interval <seconds>', 'Fetch interval in seconds', '3')
  .action(async (options) => {
    const dialogId = options.dialog;
    const workspace = resolve(options.workspace);
    const chatFilePath = resolve(workspace, options.chatFile);
    const intervalMs = parseInt(options.interval, 10) * 1000;

    const getOrCreateChatId = (): string => {
      if (existsSync(chatFilePath)) {
        const id = readFileSync(chatFilePath, 'utf-8').trim();
        if (id) return id;
      }
      const chatId = execSync('cursor agent create-chat', {
        encoding: 'utf-8',
        cwd: workspace,
      }).trim();
      writeFileSync(chatFilePath, chatId);
      return chatId;
    };

    const chatId = getOrCreateChatId();

    const BOT_PREFIX = '[bot]';
    const isBotMessage = (text: string): boolean =>
      text.startsWith(BOT_PREFIX) ||
      ['Starting:', 'Done ✓', 'Yes —', 'New approach:', 'Update:'].some((p) => text.startsWith(p));

    const runAgent = (instruction: string): Promise<number> =>
      new Promise((resolveExit) => {
        const statusReminder = `

---
IMPORTANT: You MUST report status back to the Vibe Telegram chat. Use the sendMessage tool with dialogId ${dialogId}.
CRITICAL: Prefix EVERY message you send with "${BOT_PREFIX}" (e.g. "${BOT_PREFIX} Starting..."). This prevents your updates from being processed as new tasks.
Post updates: when you start, at milestones, and when you complete (or on errors).`;
        const prompt = `Execute this instruction from Vibe.${statusReminder}

Instruction: ${instruction}`;
        const args = [
          'agent',
          '--print',
          '--approve-mcps',
          '--force',
          '--sandbox',
          'disabled',
          '--workspace',
          workspace,
          '--resume',
          chatId,
          prompt,
        ];
        const proc = spawn('cursor', args, {
          stdio: ['ignore', 'pipe', 'pipe'],
          shell: false,
        });
        proc.stdout?.pipe(process.stdout);
        proc.stderr?.pipe(process.stderr);
        proc.on('close', (code) => resolveExit(code ?? 0));
      });

    const client = await createClient();
    const queue: { id: number; text: string }[] = [];
    const seenIds = new Set<number>();
    let lastProcessedId = 0;
    let initialized = false;
    let processing = false;

    const fetchAndEnqueue = async () => {
      try {
        const messages = await client.getMessages(bigInt(dialogId), { limit: 20 });
        const raw = (messages || []).slice().reverse();
        if (!initialized) {
          lastProcessedId = Math.max(0, ...raw.map((m) => (m as { id?: number }).id ?? 0));
          initialized = true;
          return;
        }
        for (const msg of raw) {
          const id = (msg as { id?: number }).id ?? 0;
          const text = ((msg as { message?: string }).message ?? '').trim();
          if (id <= lastProcessedId || seenIds.has(id) || !text || isBotMessage(text)) continue;
          seenIds.add(id);
          lastProcessedId = Math.max(lastProcessedId, id);
          queue.push({ id, text });
          processQueue();
        }
      } catch (err) {
        console.error('Fetch error:', (err as Error).message);
      }
    };

    const processQueue = () => {
      if (processing || queue.length === 0) return;
      processing = true;
      const { id, text } = queue.shift()!;
      console.log(`\n📩 Processing instruction: ${text.slice(0, 60)}${text.length > 60 ? '...' : ''}\n`);
      runAgent(text)
        .then((code) => {
          console.log(`\n✓ Agent finished (exit ${code})\n`);
          processing = false;
          processQueue();
        })
        .catch((err) => {
          console.error('Error:', (err as Error).message);
          processing = false;
          processQueue();
        });
    };

    await fetchAndEnqueue();
    setInterval(fetchAndEnqueue, intervalMs);

    console.log(`Vibe → Cursor Agent`);
    console.log(`Dialog: ${dialogId}`);
    console.log(`Workspace: ${workspace}`);
    console.log(`Shared chat: ${chatId}`);
    console.log(`Fetching every ${options.interval}s. Press Ctrl+C to stop.\n`);
  });

// Command: create-group
program
  .command('create-group')
  .description('Create a new Telegram group for instructions')
  .argument('[title]', 'Group name', 'Cursor Instructions')
  .action(async (title) => {
    try {
      const { utils } = await import('telegram');
      const client = await createClient();
      const result = await client.invoke(
        new Api.channels.CreateChannel({
          megagroup: true,
          title,
          about: 'Group for sending instructions to Cursor AI',
        })
      );
      const updates = result as Api.Updates;
      const channelId = updates.chats?.[0]
        ? utils.getPeerId(updates.chats[0]).toString()
        : null;
      if (channelId) {
        logger.info(`Group "${title}" created! ID: ${channelId}`);
        console.log(`\n✓ Group "${title}" created successfully.`);
        console.log(`  Send messages there, then ask: "Get messages from ${title}"`);
        console.log(`  Or use dialog ID: ${channelId}\n`);
      } else {
        logger.info('Group created');
        console.log('\n✓ Group created. Check your Telegram app.\n');
      }
      process.exit(0);
    } catch (error) {
      logger.error('Failed to create group:', error);
      console.error('Error:', (error as Error).message);
      process.exit(1);
    }
  });

// Command: logout
program
  .command('logout')
  .description('Logout from Telegram')
  .action(async () => {
    logger.info('Logging out from Telegram...');
    
    try {
      await logoutFromTelegram();
      logger.info('Logout successful!');
    } catch (error) {
      logger.error('Failed to logout:', error);
      process.exit(1);
    }
  });

// Command: send
program
  .command('send')
  .description('Send a message to a Telegram group or chat')
  .requiredOption('-d, --dialog <id>', 'Dialog/group ID')
  .requiredOption('-m, --message <text>', 'Message text to send')
  .action(async (options) => {
    try {
      const client = await createClient();
      const entity = bigInt(options.dialog);
      await client.sendMessage(entity, { message: options.message });
      console.log('✓ Message sent');
      process.exit(0);
    } catch (error) {
      logger.error('Failed to send message:', error);
      console.error('Error:', (error as Error).message);
      process.exit(1);
    }
  });

// Default command - display help
program
  .action(() => {
    program.help();
  });

// Process CLI arguments
program.parse(process.argv); 