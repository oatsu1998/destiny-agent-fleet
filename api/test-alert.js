export default async function handler(req, res) {
  const TELEGRAM_BOT_TOKEN = "8940771064:AAHz6XRKxJrhaciM7yYlHKpGl9xRqGKMPN0";
  const TELEGRAM_CHAT_ID = "6168326177";

  try {
    const response = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: TELEGRAM_CHAT_ID,
          text: "Test alert from Destiny Agent Fleet. If you see this, it's working!",
        }),
      }
    );
    const data = await response.json();
    res.status(200).json({ status: "sent", telegram_response: data });
  } catch (err) {
    res.status(500).json({ status: "error", message: err.message });
  }
}
