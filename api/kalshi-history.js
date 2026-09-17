// /api/kalshi-history.js — real price history for one Kalshi market, for
// the small trend chart under each game card. Runs server-side so CORS
// doesn't apply. No paid API, no fabricated points.

export default async function handler(req, res) {
  const { ticker } = req.query;
  if (!ticker || typeof ticker !== 'string') {
    res.status(400).json({ error: 'ticker query param required' });
    return;
  }

  // Ticker format: KXWNBAGAME-26AUG18INDTOR-TOR -> series is everything
  // before the second-to-last "-" segment.
  const parts = ticker.split('-');
  if (parts.length < 3) {
    res.status(400).json({ error: 'invalid ticker format' });
    return;
  }
  const seriesTicker = parts[0];
  const eventTicker = parts.slice(0, 2).join('-');

  const nowSec = Math.floor(Date.now() / 1000);
  const startSec = nowSec - 24 * 60 * 60; // last 24 hours
  const periodInterval = 60; // hourly candles (Kalshi only accepts 1, 60, or 1440)

  try {
    const url = `https://api.elections.kalshi.com/trade-api/v2/series/${seriesTicker}/markets/${ticker}/candlesticks?start_ts=${startSec}&end_ts=${nowSec}&period_interval=${periodInterval}`;
    const r = await fetch(url);
    if (!r.ok) {
      res.status(502).json({ error: 'Kalshi returned status ' + r.status });
      return;
    }
    const data = await r.json();
    const candles = data.candlesticks || [];

    // Real closing price per candle only — skip candles with no trade data
    // (empty price object) rather than inventing a flat line through them.
    const points = candles
      .map(c => {
        const close = c.price && c.price.close_dollars;
        if (close === undefined || close === null || close === '') return null;
        const cents = Math.round(parseFloat(close) * 100);
        if (isNaN(cents)) return null;
        return { ts: c.end_period_ts, cents };
      })
      .filter(Boolean);

    res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=120');
    res.status(200).json({ ticker, points });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
