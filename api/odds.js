// Server-side proxy for The Odds API — keeps the API key off the client.
// This runs on Vercel's server, not the browser, so the key in `apiKey`
// below is never sent to anyone viewing page source.
// File location: /api/odds.js in your project root.
//
// Setup: add an ODDS_API_KEY environment variable in your Vercel project
// settings (Settings -> Environment Variables) with your The Odds API key,
// then redeploy.
//
// Usage from the client, mirrors The Odds API's own path structure:
//   /api/odds?path=basketball_nba/odds&regions=us&markets=h2h,spreads,totals&oddsFormat=american
//   /api/odds?path=basketball_nba/events
//   /api/odds?path=basketball_nba/events/<eventId>/odds&regions=us&markets=player_points&oddsFormat=american

export default async function handler(req, res) {
  try {
    const { path, ...rest } = req.query;

    if (!path) {
      res.status(400).json({ error: 'Missing required "path" query param, e.g. ?path=basketball_nba/odds' });
      return;
    }

    const apiKey = process.env.ODDS_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: 'ODDS_API_KEY is not configured on the server' });
      return;
    }

    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(rest)) {
      if (value !== undefined) params.set(key, value);
    }
    params.set('apiKey', apiKey);

    const targetUrl = `https://api.the-odds-api.com/v4/sports/${path}?${params.toString()}`;

    const response = await fetch(targetUrl, { cache: 'no-store' });

    // Pass through Odds API's usage headers so the client can keep tracking quota
    const remaining = response.headers.get('x-requests-remaining');
    const used = response.headers.get('x-requests-used');
    if (remaining !== null) res.setHeader('x-requests-remaining', remaining);
    if (used !== null) res.setHeader('x-requests-used', used);

    const data = await response.json();

    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }

    res.setHeader('Cache-Control', 's-maxage=5, stale-while-revalidate=10');
    res.status(200).json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
