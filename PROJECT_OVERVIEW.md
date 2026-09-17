# Destiny Sports Command Center — Project Overview

Destiny is a real-time sports intelligence, live odds tracking, player props command center, and market analytics platform.

## Real-Data Principle
- **No Mock Data**: Every score, line, market, candlestick chart, and weather metric is pulled from live, authoritative APIs (ESPN, Kalshi, Open-Meteo).
- **Graceful Fallbacks**: If real data is unavailable for a fixture or market, the UI displays clear N/A or Weather unavailable state cards rather than generating simulated numbers.

---

## System Architecture

### Core Pages & Views
1. **Command Center (`index.html`)**:
   - Real-time ESPN game scoreboards for NFL, MLB, NBA, WNBA, NHL, and NCAAF.
   - **Game Track / My Bets Modal (`#my-bets-modal-overlay`)**: Live game header scores, team logos, situational down/distance alerts, and live consensus market lines.
   - **7-Wager Active Portfolio Engine**: Seeding and tracking of active game wagers (`destiny_game_wagers`), supporting duplicate line entries and `CASHED 🟢` positions.
   - **Combined Portfolio PnL Trajectory Graph**: Real-time total portfolio PnL curve calculations across line intervals (`34.5–40.5`, `40.5–48.5`, `Over 48.5`), dynamically balancing game totals and team total allocations.
   - **Bet Trajectory Gauge & AI Hedge Advisor**: Dynamic pace gauges, remaining score budget calculations, pace risk alerts (`🚨 HIGH PACE RISK`, `🟢 ON TRACK`), and AI cashout/hedge recommendations.
   - **Interactive Matchup Selector Dropdown**: Top modal navigation selector allowing users to switch between active tracked game portfolios (e.g. `GB @ DEN` vs `CIN @ ARI`).
   - **Live Weather Engine**: Outdoor weather chips powered by Open-Meteo (temperature, wind speed, cardinal direction, WMO weather icon, and rotated cyan wind flag SVG).
   - **Live Sportsbook Sidebar & Ticker**: Top scrolling ESPN score ticker and left vertical sidebar featuring Live Wagers (🔴 🟡 🟢 ticket health indicators), Destiny League featured matches, live game filters, and countdown clocks for off-day leagues.

2. **Kalshi Live Prediction Terminal (`kalshi.html`)**:
   - Full Kalshi sports dataset loading via dual proxy fetching (`/api/kalshi` + `/api/kalshi-props`), ingesting 1,500+ open prediction markets.
   - Dedicated league & prop filter tabs: 🔥 `All Markets`, 🏈 `NFL`, ⚾ `MLB`, 🏀 `NBA`, 🏀 `WNBA`, 🏒 `NHL`, 🎯 `Player Props`.
   - Dynamic market type labels for Moneyline, Point Spread, Total Points, and Player Prop contracts.
   - Real-time candlestick price charts, depth orderbooks, and interactive trade execution console.

3. **Player Props Command Center (`props.html`)**:
   - Real player prop markets from Kalshi (`/api/kalshi-props`).
   - NBA & WNBA: Points, Rebounds, Assists, 3-Pointers.
   - NFL: Passing Yards (`KXNFLPASSYDS`), Rushing Yards (`KXNFLRSHYDS`), Receiving Yards (`KXNFLRECYDS`), Receptions (`KXNFLREC`).
   - Dynamic 50/50 line detection, sportsbook odds comparisons, custom prop cards, and My Props tracker.

4. **Line Tracker (`line-tracker.html`)**:
   - Multi-bookmaker line movement history matrix and historical price chart loader (`fetchHistory()`).

5. **My Bets Tracking (`my-bets.html`)**:
   - Bet slip tracker with active ticket monitoring, win/loss status, and 95% cash-out controls.

6. **Strategy Sandbox (`sandbox.html`) & Portfolio (`portfolio.html`)**:
   - Interactive backtesting environment mirroring the Game Track modal engine, PnL trajectory graphs, AI strategy recommendations, and full bankroll ledger tracking.

7. **Daily Betting Results & Game Recaps (`results.html`)**:
   - Completed game scoreboards, graded closing lines, Action Network / Sportsbook style outcome trackers (soft green win/cover pills, soft slate/blue Under hits, neutral Push tags).
   - Daily Slate KPI summary header (O/U totals %, Spread ATS cover %, Moneyline fav/dog breakdown, Team Totals %).
   - Date stepper & date picker controls, league filter pills (ALL, NFL, NCAAF, NBA, MLB), and custom JSON payload importer modal.

8. **About Network (`about.html`)**:
   - Public product documentation, real-data policy statement, and system navigation map.

---

## Serverless API Infrastructure (`/api/`)
- `/api/results.js`: Serves graded daily game results and closing lines matching the Destiny Results JSON schema.
- `/api/kalshi-props.js`: Fetches open player prop markets across NBA, WNBA, and NFL series tickers.
- `/api/kalshi-history.js`: Fetches 24-hour candlestick price history for individual Kalshi market tickers.
- `/api/kalshi.js`: Fetches live sports prediction markets (Moneyline, Spread, Total) across 6 leagues.
- `/api/odds.js`: Integrates external sportsbook lines.

---

## Technical Stack
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System with CSS variables), ES6+ JavaScript.
- **State & Feed**: `state-manager.js` (reactive state container) & `live-feed.js` (real-time Kalshi market updates).
- **Navigation**: `nav.js` (universal sticky header, live clock, bankroll indicator, force refresh, and drawer menu).
- **Deployment**: Vercel Serverless Functions & GitHub Actions.
