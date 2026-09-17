// /api/kalshi-props.js — real player prop markets from Kalshi (free), for
// NBA + WNBA Points / Rebounds / Assists / Threes. Runs server-side so CORS
// doesn't apply. No paid odds API involved.

const SERIES_LIST = [
  { ticker: 'KXNBAPTS',     league: 'NBA',  stat: 'Points' },
  { ticker: 'KXNBAREB',     league: 'NBA',  stat: 'Rebounds' },
  { ticker: 'KXNBAAST',     league: 'NBA',  stat: 'Assists' },
  { ticker: 'KXNBA3PT',     league: 'NBA',  stat: '3-Pointers' },
  { ticker: 'KXWNBAPTS',    league: 'WNBA', stat: 'Points' },
  { ticker: 'KXWNBAREB',    league: 'WNBA', stat: 'Rebounds' },
  { ticker: 'KXWNBAAST',    league: 'WNBA', stat: 'Assists' },
  { ticker: 'KXWNBA3PT',    league: 'WNBA', stat: '3-Pointers' },
  { ticker: 'KXNFLPASSYDS', league: 'NFL',  stat: 'Passing Yards' },
  { ticker: 'KXNFLRSHYDS',  league: 'NFL',  stat: 'Rushing Yards' },
  { ticker: 'KXNFLRECYDS',  league: 'NFL',  stat: 'Receiving Yards' },
  { ticker: 'KXNFLREC',     league: 'NFL',  stat: 'Receptions' },
];

async function fetchSeries(ticker) {
  try {
    const r = await fetch(
      `https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=${ticker}&status=open&limit=1000`
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
      SERIES_LIST.map(async ({ ticker, league, stat }) => {
        const markets = await fetchSeries(ticker);
        return markets.map((m) => ({ ...m, _league: league, _stat: stat }));
      })
    );

    const markets = results.flat();

    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.status(200).json({ markets });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
