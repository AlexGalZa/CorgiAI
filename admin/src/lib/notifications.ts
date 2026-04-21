// Notification channels — configure webhooks in env vars

export async function notifySlack(message: string) {
  const url = import.meta.env.VITE_SLACK_WEBHOOK_URL;
  if (!url) return; // Not configured
  try {
    await fetch(url, { method: 'POST', body: JSON.stringify({ text: message }) });
  } catch (e) {
    console.warn('Slack notification failed:', e);
  }
}

export async function notifyTelegram(message: string) {
  const token = import.meta.env.VITE_TELEGRAM_BOT_TOKEN;
  const chatId = import.meta.env.VITE_TELEGRAM_CHAT_ID;
  if (!token || !chatId) return;
  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text: message, parse_mode: 'HTML' }),
    });
  } catch (e) {
    console.warn('Telegram notification failed:', e);
  }
}
