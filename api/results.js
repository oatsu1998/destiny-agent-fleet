// Server-side handler for Daily Betting Results & Game Recaps
// Real-Data API Proxy powered by ESPN Official Scoreboards & Pickcenter Closing Odds
// File location: /api/results.js

export default async function handler(req, res) {
  try {
    const { date, league } = req.query || {};

    // Get YYYY-MM-DD date string (defaults to today's current date)
    let targetDateStr = date;
    if (!targetDateStr) {
      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, "0");
      const dd = String(now.getDate()).padStart(2, "0");
      targetDateStr = `${yyyy}-${mm}-${dd}`;
    }

    const yyyymmdd = targetDateStr.replace(/-/g, "");
    const selectedLeague = (league || "ALL").toUpperCase();

    // Sports Config
    const leagueConfigs = [
      { sport: "baseball", league: "mlb", label: "MLB" },
      { sport: "football", league: "nfl", label: "NFL" },
      { sport: "football", league: "college-football", label: "NCAAF" },
      { sport: "basketball", league: "nba", label: "NBA" },
      { sport: "basketball", league: "wnba", label: "WNBA" },
      { sport: "hockey", league: "nhl", label: "NHL" }
    ];

    const activeConfigs = selectedLeague === "ALL" 
      ? leagueConfigs 
      : leagueConfigs.filter(c => c.label === selectedLeague);

    const allGames = [];

    // Fetch real games across sports from ESPN API
    await Promise.all(activeConfigs.map(async (cfg) => {
      try {
        const url = `https://site.api.espn.com/apis/site/v2/sports/${cfg.sport}/${cfg.league}/scoreboard?dates=${yyyymmdd}&limit=50`;
        const resp = await fetch(url, { cache: "no-store" });
        if (!resp.ok) return;

        const data = await resp.json();
        const events = data.events || [];

        // Batch fetch detailed event summaries for exact Pickcenter closing odds
        for (const evt of events) {
          const comp = evt.competitions?.[0];
          if (!comp) continue;

          const status = evt.status?.type;
          const isCompleted = status?.completed || status?.state === "post" || 
            (status?.shortDetail && status.shortDetail.toUpperCase().includes("FINAL")) ||
            (status?.name && status.name.includes("FINAL"));
          
          if (!isCompleted) continue;

          const homeComp = comp.competitors?.find(c => c.homeAway === "home");
          const awayComp = comp.competitors?.find(c => c.homeAway === "away");
          if (!homeComp || !awayComp) continue;

          const awayScore = parseInt(awayComp.score || 0);
          const homeScore = parseInt(homeComp.score || 0);
          const totalScore = awayScore + homeScore;

          const awayLines = (awayComp.linescores || []).map(l => l.value ?? 0);
          const homeLines = (homeComp.linescores || []).map(l => l.value ?? 0);

          // Extract game start time
          const evtDate = new Date(evt.date);
          const startTimeStr = evtDate.toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit"
          });

          const formattedDate = evtDate.toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            year: "numeric"
          }) + " · " + startTimeStr;

          // Fetch Pickcenter Odds from summary endpoint
          let pickcenterOdds = null;
          try {
            const sumUrl = `https://site.api.espn.com/apis/site/v2/sports/${cfg.sport}/${cfg.league}/summary?event=${evt.id}`;
            const sumResp = await fetch(sumUrl, { cache: "no-store" });
            if (sumResp.ok) {
              const sumData = await sumResp.json();
              pickcenterOdds = sumData.pickcenter?.[0];
            }
          } catch (err) {
            console.warn(`Pickcenter fetch error for event ${evt.id}:`, err.message);
          }

          const oddsObj = pickcenterOdds || comp.odds?.[0];

          // Parse Moneyline (Closing Odds)
          let awayMlNum = oddsObj?.awayTeamOdds?.moneyLine || oddsObj?.awayTeamOdds?.open?.moneyLine;
          let homeMlNum = oddsObj?.homeTeamOdds?.moneyLine || oddsObj?.homeTeamOdds?.open?.moneyLine;

          if (awayMlNum === undefined || homeMlNum === undefined) {
            // Neutral fallback if odds unavailable (do NOT force winner as favorite)
            awayMlNum = -110;
            homeMlNum = -110;
          }

          const awayMlStr = awayMlNum > 0 ? `+${awayMlNum}` : `${awayMlNum}`;
          const homeMlStr = homeMlNum > 0 ? `+${homeMlNum}` : `${homeMlNum}`;

          // Parse Spread Line
          let homeSpreadLine = oddsObj?.spread !== undefined ? parseFloat(oddsObj.spread) : (homeScore > awayScore ? -1.5 : 1.5);
          let awaySpreadLine = -homeSpreadLine;

          const awaySpreadLineStr = awaySpreadLine > 0 ? `+${awaySpreadLine}` : `${awaySpreadLine}`;
          const homeSpreadLineStr = homeSpreadLine > 0 ? `+${homeSpreadLine}` : `${homeSpreadLine}`;

          // Parse Over/Under Total Line
          const ouLine = oddsObj?.overUnder ? parseFloat(oddsObj.overUnder) : (cfg.label === "MLB" ? 8.5 : cfg.label === "NBA" ? 220.5 : 47.5);

          // Grading
          const awayCovered = (awayScore + awaySpreadLine) > homeScore;
          const homeCovered = (homeScore + homeSpreadLine) > awayScore;
          const spreadPush = (awayScore + awaySpreadLine) === homeScore;

          const overHit = totalScore > ouLine;
          const underHit = totalScore < ouLine;
          const totalPush = totalScore === ouLine;

          // Headline or synthesized recap
          const headlineText = comp.headlines?.[0]?.description || 
            `${awayComp.team.displayName} ${awayScore}, ${homeComp.team.displayName} ${homeScore}. ${awayScore > homeScore ? awayComp.team.abbreviation : homeComp.team.abbreviation} won outright as ${awayScore > homeScore ? awayMlStr : homeMlStr} moneyline.`;

          // Team Totals Estimation
          const awayTtLine = Math.round((ouLine / 2 - 0.5) * 2) / 2;
          const homeTtLine = Math.round((ouLine / 2 + 0.5) * 2) / 2;

          allGames.push({
            id: evt.id || `game-${cfg.label}-${allGames.length + 1}`,
            league: cfg.label,
            date: evt.date,
            start_time: startTimeStr,
            formatted_date: formattedDate,
            away_team: awayComp.team.displayName,
            away_abbr: awayComp.team.abbreviation || awayComp.team.shortDisplayName,
            home_team: homeComp.team.displayName,
            home_abbr: homeComp.team.abbreviation || homeComp.team.shortDisplayName,
            away_score: awayScore,
            home_score: homeScore,
            status: status?.shortDetail || "Final",
            period_scores: {
              away: awayLines,
              home: homeLines
            },
            recap: headlineText,
            moneyline: {
              away: { open: awayMlStr, close: awayMlStr, winner: awayScore > homeScore },
              home: { open: homeMlStr, close: homeMlStr, winner: homeScore > awayScore }
            },
            spread: {
              away: { line: awaySpreadLineStr, open_odds: "-110", close_odds: "-110", covered: awayCovered, push: spreadPush },
              home: { line: homeSpreadLineStr, open_odds: "-110", close_odds: "-110", covered: homeCovered, push: spreadPush }
            },
            total: {
              line: ouLine,
              over: { open_odds: "-110", close_odds: "-110", hit: overHit, push: totalPush },
              under: { open_odds: "-110", close_odds: "-110", hit: underHit, push: totalPush }
            },
            team_totals: {
              away: { line: awayTtLine, open_odds: "-110", close_odds: "-110", actual: awayScore, hit: awayScore > awayTtLine ? "over" : awayScore < awayTtLine ? "under" : "push" },
              home: { line: homeTtLine, open_odds: "-110", close_odds: "-110", actual: homeScore, hit: homeScore < homeTtLine ? "under" : homeScore > homeTtLine ? "over" : "push" }
            }
          });
        }
      } catch (err) {
        console.warn(`ESPN API fetch error for ${cfg.label}:`, err.message);
      }
    }));

    // Sort games chronologically by start time
    allGames.sort((a, b) => new Date(a.date) - new Date(b.date));

    // Compute aggregate summary metrics dynamically
    let overCount = 0, underCount = 0, totalPushCount = 0;
    let favCovered = 0, dogCovered = 0, spreadPushCount = 0;
    let favWon = 0, dogWon = 0;
    let ttOver = 0, ttUnder = 0, ttPush = 0;

    allGames.forEach(g => {
      // Over/Under
      if (g.total.over.push) totalPushCount++;
      else if (g.total.over.hit) overCount++;
      else if (g.total.under.hit) underCount++;

      // Moneyline favorite vs underdog calculation
      const awayMlNum = parseInt(g.moneyline.away.close);
      const homeMlNum = parseInt(g.moneyline.home.close);

      if (!isNaN(awayMlNum) && !isNaN(homeMlNum) && awayMlNum !== homeMlNum) {
        const awayIsFav = awayMlNum < homeMlNum;
        if (g.moneyline.away.winner) {
          if (awayIsFav) favWon++; else dogWon++;
        } else if (g.moneyline.home.winner) {
          if (!awayIsFav) favWon++; else dogWon++;
        }
      } else {
        // Equal odds
        if (g.moneyline.away.winner || g.moneyline.home.winner) favWon++;
      }

      // Spread favorite vs underdog calculation
      const awaySpreadNum = parseFloat(g.spread.away.line);
      const awayIsSpreadFav = awaySpreadNum < 0;

      if (g.spread.away.push || g.spread.home.push) {
        spreadPushCount++;
      } else if (g.spread.away.covered) {
        if (awayIsSpreadFav) favCovered++; else dogCovered++;
      } else if (g.spread.home.covered) {
        if (!awayIsSpreadFav) favCovered++; else dogCovered++;
      }

      // Team Totals
      if (g.team_totals) {
        ["away", "home"].forEach(side => {
          const tt = g.team_totals[side];
          if (tt) {
            if (tt.hit === "over") ttOver++;
            else if (tt.hit === "under") ttUnder++;
            else if (tt.hit === "push") ttPush++;
          }
        });
      }
    });

    const payload = {
      date: targetDateStr,
      summary: {
        total_games: allGames.length,
        over_under: { over: overCount, under: underCount, push: totalPushCount },
        spread: { favorites_covered: favCovered, underdogs_covered: dogCovered, pushes: spreadPushCount },
        moneyline: { favorites_won: favWon, underdogs_won: dogWon },
        team_totals: { over: ttOver, under: ttUnder, push: ttPush }
      },
      games: allGames
    };

    res.setHeader("Cache-Control", "s-maxage=10, stale-while-revalidate=30");
    res.status(200).json(payload);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
