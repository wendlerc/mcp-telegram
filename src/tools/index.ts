import { listDialogsTool } from './listDialogs.js';
import { listMessagesTool } from './listMessages.js';
import { createGroupTool } from './createGroup.js';
import { sendMessageTool } from './sendMessage.js';

/**
 * Export all tools as an array
 */
export const tools = [
  listDialogsTool,
  listMessagesTool,
  createGroupTool,
  sendMessageTool,
];

/**
 * Export individual tools
 */
export {
  listDialogsTool,
  listMessagesTool,
  createGroupTool,
  sendMessageTool,
}; 