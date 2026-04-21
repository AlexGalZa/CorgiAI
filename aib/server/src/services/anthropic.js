const Anthropic = require('@anthropic-ai/sdk');
const env = require('../config/env');
const SYSTEM_PROMPT = require('../prompts/system');

const client = new Anthropic({ apiKey: env.anthropicApiKey });

async function chat(messages) {
  const lastMessage = messages[messages.length - 1];
  const hasAttachment = Array.isArray(lastMessage?.content) &&
    lastMessage.content.some(b =>
      b.type === 'image' ||
      (b.type === 'text' && b.text?.startsWith('[UPLOADED DOCUMENT:'))
    );

  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: hasAttachment ? 1024 : 512,
    system: [{ type: 'text', text: SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } }],
    messages: messages.map(m => ({
      role: m.role,
      content: m.content,
    })),
  });

  const textBlock = response.content.find(b => b.type === 'text');
  return textBlock ? textBlock.text : '';
}

function buildMultimodalContent(userText, fileData) {
  const contentBlocks = [];

  if (fileData.type === 'image') {
    contentBlocks.push({
      type: 'image',
      source: {
        type: 'base64',
        media_type: fileData.mediaType,
        data: fileData.base64,
      },
    });
  } else if (fileData.type === 'pdf') {
    contentBlocks.push({
      type: 'text',
      text: `[UPLOADED DOCUMENT: ${fileData.filename}]\n\n${fileData.extractedText}\n\n[END DOCUMENT]`,
    });
  }

  const text = userText && userText.trim()
    ? userText.trim()
    : 'Please analyze this insurance document and give me a concise summary of the key coverages and any concerns.';

  contentBlocks.push({
    type: 'text',
    text,
  });

  return contentBlocks;
}

async function extract(extractionPrompt) {
  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4096,
    messages: [
      {
        role: 'user',
        content: extractionPrompt,
      },
    ],
  });

  const textBlock = response.content.find(b => b.type === 'text');
  const text = textBlock ? textBlock.text : '{}';

  const cleaned = text.replace(/```json\n?/g, '').replace(/```\n?/g, '').trim();
  return JSON.parse(cleaned);
}

module.exports = { chat, extract, buildMultimodalContent };
