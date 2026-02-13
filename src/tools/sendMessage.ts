import { Tool } from 'fastmcp';
import bigInt from 'big-integer';
import { z } from 'zod';

import { createClient } from '../lib/telegram.js';
import { logger } from '../utils/logger.js';

/**
 * Schema for SendMessage parameters
 */
export const SendMessageParamsSchema = z.object({
  dialogId: z.string().describe('ID of the dialog/group to send to'),
  message: z.string().describe('Message text to send'),
});

/**
 * Send Message Tool - Send a message to a Telegram group or chat
 */
export const sendMessageTool: Tool<undefined, typeof SendMessageParamsSchema> = {
  name: 'sendMessage',
  description:
    'Send a message to a Telegram group or chat. Use this to post progress updates, completion status, or replies.',
  parameters: SendMessageParamsSchema,
  execute: async (args, { log }) => {
    logger.info('Sending message', { dialogId: args.dialogId });

    const validateResult = SendMessageParamsSchema.safeParse(args);
    if (!validateResult.success) {
      throw new Error(
        `Invalid parameters for sendMessage: ${JSON.stringify(validateResult.error.format())}`
      );
    }

    const { dialogId, message } = validateResult.data;
    const client = await createClient();

    try {
      const entity = bigInt(dialogId);
      await client.sendMessage(entity, { message });
      log.debug(`Message sent to ${dialogId}`);
      return JSON.stringify({ success: true, message: 'Message sent' });
    } catch (error) {
      log.error('Error sending message:', (error as Error).message);
      throw error;
    }
  },
};
