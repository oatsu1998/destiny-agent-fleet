// This runs on Vercel's server, not the browser — so CORS doesn't apply here.
// File location: /api/kalshi.js in your project root.
//
// Pulls THREE kinds of real Kalshi markets per league, all free (no paid odds API):
//   1. GAME   — moneyline (who wins)
//   2. SPREAD — point spread (multiple threshold markets per game; the client
//               picks the one closest to 50/50 as "the line", just like a
//               sportsbook sets its spread at the number the market agrees on)
//   3. TOTAL  — over/under total points (same idea, multiple thresholds)
//
// Kalshi's `category=Sports` filter on the general /markets endpoint only
// returns confusing multi-leg "combo" markets, so we query each league's
// specific series directly instead and merge the results.

const LEAGUES = {
  MLB:   { game: 'KXMLBGAME',   spread: 'KXMLBSPREAD',   total: 'KXMLBTOTAL' },
  NFL:   { game: 'KXNFLGAME',   spread: 'KXNFLSPREAD',   total: 'KXNFLTOTAL' },
  NBA:   { game: 'KXNBAGAME',   spread: 'KXNBASPREAD',   total: 'KXNBATOTAL' },
  NHL:   { game: 'KXNHLGAME',   spread: 'KXNHLSPREAD',   total: 'KXNHLTOTAL' },
  NCAAF: { game: 'KXNCAAFGAME', spread: 'KXNCAAFSPREAD', total: 'KXNCAAFTOTAL' },
  WNBA:  { game: 'KXWNBAGAME',  spread: 'KXWNBASPREAD',  total: 'KXWNBATOTAL' },
};

// Every series ticker we need to fetch, tagged with which league + which
// market kind it is so the client doesn't have to guess from the ticker text.
const SERIES_LIST = Object.entries(LEAGUES).flatMap(([league, s]) => ([
  { ticker: s.game,   league, kind: 'game' },
  { ticker: s.spread, league, kind: 'spread' },
  { ticker: s.total,  league, kind: 'total' },
]));

async function fetchSeries(ticker) {
  try {
    const r = await fetch(
      `https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=${ticker}&status=open&limit=200`
    );
    if (!r.ok) return [];
    const d = await r.json();
    return d.markets || [];
  } catch {
    return [];
  }
}

export default async function handler(req, res) {
  try {
    const results = await Promise.all(
      SERIES_LIST.map(async ({ ticker, league, kind }) => {
        const markets = await fetchSeries(ticker);
        // Tag each market with league + kind so live-feed.js doesn't need
        // to re-derive it from the ticker string.
        return markets.map((m) => ({ ...m, _league: league, _kind: kind }));
      })
    );

    const markets = results.flat();

    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.status(200).json({ markets });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
