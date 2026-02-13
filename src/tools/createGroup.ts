import { Tool } from 'fastmcp';
import { Api, utils } from 'telegram';
import { z } from 'zod';

import { createClient } from '../lib/telegram.js';
import { logger } from '../utils/logger.js';

/**
 * Schema for CreateGroup parameters
 */
export const CreateGroupParamsSchema = z.object({
  title: z.string().describe('Name of the group'),
  about: z.string().optional().describe('Group description (optional)'),
});

/**
 * Create Group Tool - Create a new Telegram group/supergroup for receiving instructions
 */
export const createGroupTool: Tool<undefined, typeof CreateGroupParamsSchema> = {
  name: 'createGroup',
  description:
    'Create a new Telegram group chat. Use this to set up a group where you can send instructions. Returns the group ID for use with listMessages.',
  parameters: CreateGroupParamsSchema,
  execute: async (args, { log }) => {
    logger.info('Creating group', args);

    const validateResult = CreateGroupParamsSchema.safeParse(args);
    if (!validateResult.success) {
      throw new Error(
        `Invalid parameters for createGroup: ${JSON.stringify(validateResult.error.format())}`
      );
    }

    const { title, about } = validateResult.data;
    const client = await createClient();

    try {
      const result = await client.invoke(
        new Api.channels.CreateChannel({
          megagroup: true,
          title,
          about: about || 'Instructions group',
        })
      );

      // Extract the new channel from the Updates response
      const updates = result as Api.Updates;
      let channelId: string | null = null;
      let channelTitle = title;

      if (updates.chats && updates.chats.length > 0) {
        const channel = updates.chats[0];
        channelId = utils.getPeerId(channel).toString();
        if ('title' in channel) {
          channelTitle = channel.title;
        }
      }

      if (!channelId) {
        throw new Error('Failed to get group ID from response');
      }

      log.debug(`Created group ${channelTitle} with ID ${channelId}`);

      return JSON.stringify({
        success: true,
        id: channelId,
        title: channelTitle,
        message:
          `Group "${channelTitle}" created. Send messages there and ask me to "get messages from [group name]" or use dialog ID ${channelId} to read your instructions.`,
      });
    } catch (error) {
      log.error('Error creating group:', (error as Error).message);
      throw error;
    }
  },
};
