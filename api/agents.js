// /api/agents.js — Serverless endpoint serving Agent Fleet telemetry & MCP endpoint configurations.
import fs from 'fs';
import path from 'path';

const DEFAULT_AGENTS = [
  {
    id: "espn_scraper",
    name: "ESPN Free Odds Scraper 🏈⚾🏀",
    avatar: "📡",
    status: "Live",
    role: "Zero-Cost Sportsbook Odds Engine",
    specialty: "NFL, MLB, NBA Live Scores & Odds",
    markets_tracked: ["Moneyline", "Point Spreads", "Over/Under Totals"],
    last_run: new Date().toISOString(),
    records_processed: 56,
    latency_ms: 190,
    uptime_pct: 100.0,
    mcp_endpoint: "mcp://agents.destiny.net/v1/espn-scraper",
    mcp_type: "REST API / Free Site Endpoint",
    description: "Polls free ESPN Site API scoreboards with zero subscriptions, extracting live consensus game odds, point spreads, over/under totals, and scores."
  },
  {
    id: "kalshi_scraper",
    name: "Kalshi Market Scraper",
    avatar: "🤖",
    status: "Live",
    role: "Real-Time Ingestion Engine",
    specialty: "NFL, MLB, NBA, WNBA, NHL, NCAAF",
    markets_tracked: ["Moneyline", "Point Spreads", "Totals", "Player Props"],
    last_run: new Date().toISOString(),
    records_processed: 1657,
    latency_ms: 370,
    uptime_pct: 99.9,
    mcp_endpoint: "mcp://agents.destiny.net/v1/kalshi-scraper",
    mcp_type: "SSE / JSON-RPC 2.0",
    description: "High-frequency provider connecting directly to Kalshi trade API for sub-second sports line ingestion across 6 major leagues."
  },
  {
    id: "prop_normalizer",
    name: "Player Props Normalizer",
    avatar: "🧠",
    status: "Live",
    role: "Data Normalization Engine",
    specialty: "NBA & NFL Player Props",
    markets_tracked: ["Points", "Rebounds", "Assists", "3-Pointers", "Passing Yards", "Rushing Yards"],
    last_run: new Date().toISOString(),
    records_processed: 842,
    latency_ms: 120,
    uptime_pct: 99.8,
    mcp_endpoint: "mcp://agents.destiny.net/v1/prop-normalizer",
    mcp_type: "Stdio / HTTP Post",
    description: "Translates raw player contract titles and strike thresholds into standardized player prop lines and 50/50 probability models."
  },
  {
    id: "arbitrage_hunter",
    name: "Arbitrage & Line Hunter",
    avatar: "🎯",
    status: "Active",
    role: "Cross-Market Mispricing Engine",
    specialty: "Multi-Sportsbook Arbitrage",
    markets_tracked: ["Consensus Spreads", "Negative Vig", "Middle Opportunities"],
    last_run: new Date().toISOString(),
    records_processed: 412,
    latency_ms: 215,
    uptime_pct: 99.5,
    mcp_endpoint: "mcp://agents.destiny.net/v1/arbitrage-hunter",
    mcp_type: "SSE Streaming",
    description: "Scans line discrepancies between Kalshi market bids and commercial sportsbook lines to spot risk-free arbitrage opportunities."
  },
  {
    id: "supabase_ingestor",
    name: "Supabase DB Ingestor",
    avatar: "⚡",
    status: "Live",
    role: "Database Persistence Engine",
    specialty: "PostgreSQL & Supabase Realtime",
    markets_tracked: ["Snapshot Records", "Audit Logs", "Line Histories"],
    last_run: new Date().toISOString(),
    records_processed: 1657,
    latency_ms: 45,
    uptime_pct: 100.0,
    mcp_endpoint: "mcp://agents.destiny.net/v1/supabase-ingestor",
    mcp_type: "JSON-RPC over HTTP",
    description: "Persists structured market snapshots and normalized telemetry directly into Supabase tables with fail-safe local caching."
  },
  {
    id: "line_tracker",
    name: "Line Movement Tracker",
    avatar: "📈",
    status: "Active",
    role: "Market Momentum Analyst",
    specialty: "Price Trajectory & Volume",
    markets_tracked: ["24h Candlesticks", "Orderbook Shifts", "Steam Moves"],
    last_run: new Date().toISOString(),
    records_processed: 1289,
    latency_ms: 180,
    uptime_pct: 99.7,
    mcp_endpoint: "mcp://agents.destiny.net/v1/line-tracker",
    mcp_type: "WebSocket",
    description: "Tracks historical line movement shifts, rapid money movement, and steam signals across active game contracts."
  },
  {
    id: "ai_hedge_advisor",
    name: "AI Portfolio Risk Advisor",
    avatar: "🛡️",
    status: "Idle",
    role: "Strategic Hedging Engine",
    specialty: "Active Bet Portfolios",
    markets_tracked: ["Portfolio PnL", "Pace Gauges", "Cashout Optimization"],
    last_run: new Date().toISOString(),
    records_processed: 78,
    latency_ms: 290,
    uptime_pct: 99.2,
    mcp_endpoint: "mcp://agents.destiny.net/v1/ai-hedge-advisor",
    mcp_type: "REST API",
    description: "Analyzes game situation pace risk and automatically recommends optimal cashout thresholds or counter-hedge bets."
  },
  {
    id: "zero_risk_bot",
    name: "Zero-Risk Hedge & Arbitrage Bot",
    avatar: "🤖",
    status: "Live",
    role: "Automated Risk Elimination Engine",
    specialty: "Zero-Risk Arbitrage & Sizing",
    markets_tracked: ["Zero-Risk Hedging", "Guaranteed Profit Locking", "Live Line Sizing"],
    last_run: new Date().toISOString(),
    records_processed: 512,
    latency_ms: 85,
    uptime_pct: 100.0,
    mcp_endpoint: "mcp://agents.destiny.net/v1/zero-risk-bot",
    mcp_type: "SSE / Automated Execution",
    description: "Calculates exact counter-hedge sizing on live lines in real-time to bring total portfolio downside risk down to EXACTLY $0.00."
  },
  {
    id: "weather_agent",
    name: "Atmospheric & Weather Edge Agent 🌦️",
    avatar: "🌦️",
    status: "Live",
    role: "Venue Microclimate & Betting Impact Engine",
    specialty: "NFL & NCAA Stadium Microclimates",
    markets_tracked: ["Wind Vector", "Precipitation Risk", "Temperature Delta", "FG Drag"],
    last_run: new Date().toISOString(),
    records_processed: 8,
    latency_ms: 310,
    uptime_pct: 99.9,
    mcp_endpoint: "mcp://agents.destiny.net/v1/weather-edge",
    mcp_type: "REST API / Open-Meteo",
    description: "Correlates game locations, stadium metadata (open-air, retractable, dome), and real-time weather forecasts to generate quantitative betting impact flags."
  },
  {
    id: "data_quality",
    name: "Data Quality & Feed Guardian Agent 🛡️",
    avatar: "🛡️",
    status: "Live",
    role: "8-Gate Audit & Feed Health Engine",
    specialty: "Data Health & Schema Validation",
    markets_tracked: ["Schema Sanity", "Canonical IDs", "Deduplication", "Book Coverage"],
    last_run: new Date().toISOString(),
    records_processed: 8640,
    latency_ms: 45,
    uptime_pct: 100.0,
    mcp_endpoint: "mcp://agents.destiny.net/v1/data-quality",
    mcp_type: "JSON-RPC 2.0 / Audit Engine",
    description: "Evaluates raw provider pulls against 8 strict validation gates, canonical team resolution, SHA-256 deduplication, and book coverage auditing."
  },
  {
    id: "arb_steam_hunter",
    name: "Line Discrepancy, Arbitrage & Steam Hunter ⚡",
    avatar: "⚡",
    status: "Live",
    role: "Real-Time Discrepancy & Steam Engine",
    specialty: "Pure Arbs, Middles & Rapid Velocity",
    markets_tracked: ["Pure Mathematical Arbs", "Market Middles", "Steam Moves (>=1.5 pts / >=25¢)"],
    last_run: new Date().toISOString(),
    records_processed: 9,
    latency_ms: 18,
    uptime_pct: 100.0,
    mcp_endpoint: "mcp://agents.destiny.net/v1/arb-hunter",
    mcp_type: "JSON-RPC 2.0 / Discrepancy Engine",
    description: "Detects pure mathematical arbitrage across books (<100% implied probability), cross-market middles, and rapid steam velocity line moves."
  },
  {
    id: "props_matrix_hunter",
    name: "Player Props Matrix & Cross-Book Hunter 🎯",
    avatar: "🎯",
    status: "Active (Cross-Book Prop Ingestion)",
    role: "Player Prop Ladder Aggregation & Off-Market Edge Engine",
    specialty: "Cross-Book Props, Prop Arbs, Middles & Ladders",
    markets_tracked: ["Prop Kingz", "FanDuel", "DraftKings", "BetOnline", "Bovada"],
    last_run: new Date().toISOString(),
    records_processed: 42,
    latency_ms: 22,
    uptime_pct: 100.0,
    mcp_endpoint: "mcp://agents.destiny.net/v1/props-hunter",
    mcp_type: "JSON-RPC 2.0 / Props Matrix Engine",
    description: "Ingests multi-sport player props, normalizes player identities across books, aggregates side-by-side matrices, and detects prop arbs, middles, and ladder edges."
  }
];

export default async function handler(req, res) {
  try {
    let telemetryData = {};
    let snapshotData = null;
    let weatherData = null;
    let qualityData = null;
    let arbData = null;
    let propsData = null;
    let liveStreamData = null;

    // Try reading backend/agent_telemetry.json
    try {
      const telPath = path.join(process.cwd(), 'backend', 'agent_telemetry.json');
      if (fs.existsSync(telPath)) {
        telemetryData = JSON.parse(fs.readFileSync(telPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read agent_telemetry.json:", e.message);
    }

    // Try reading backend/snapshots/live_market_stream.json
    try {
      const livePath = path.join(process.cwd(), 'backend', 'snapshots', 'live_market_stream.json');
      const fallbackPath = path.join(process.cwd(), 'backend', 'live_market_stream.json');
      if (fs.existsSync(livePath)) {
        liveStreamData = JSON.parse(fs.readFileSync(livePath, 'utf8'));
      } else if (fs.existsSync(fallbackPath)) {
        liveStreamData = JSON.parse(fs.readFileSync(fallbackPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read live_market_stream.json:", e.message);
    }

    // Try reading backend/latest_snapshot.json
    try {
      const snapPath = path.join(process.cwd(), 'backend', 'latest_snapshot.json');
      if (fs.existsSync(snapPath)) {
        snapshotData = JSON.parse(fs.readFileSync(snapPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read latest_snapshot.json:", e.message);
    }

    // Try reading backend/weather_snapshot.json
    try {
      const weatherPath = path.join(process.cwd(), 'backend', 'weather_snapshot.json');
      if (fs.existsSync(weatherPath)) {
        weatherData = JSON.parse(fs.readFileSync(weatherPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read weather_snapshot.json:", e.message);
    }

    // Try reading backend/quality_snapshot.json
    try {
      const qualityPath = path.join(process.cwd(), 'backend', 'quality_snapshot.json');
      if (fs.existsSync(qualityPath)) {
        qualityData = JSON.parse(fs.readFileSync(qualityPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read quality_snapshot.json:", e.message);
    }

    // Try reading backend/arb_opportunities.json
    try {
      const arbPath = path.join(process.cwd(), 'backend', 'arb_opportunities.json');
      if (fs.existsSync(arbPath)) {
        arbData = JSON.parse(fs.readFileSync(arbPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read arb_opportunities.json:", e.message);
    }

    // Try reading backend/props_matrix_latest.json
    try {
      const propsPath = path.join(process.cwd(), 'backend', 'props_matrix_latest.json');
      if (fs.existsSync(propsPath)) {
        propsData = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
      }
    } catch (e) {
      console.warn("Could not read props_matrix_latest.json:", e.message);
    }

    // Merge dynamic telemetry into default agents
    const agents = DEFAULT_AGENTS.map(agent => {
      const liveTel = telemetryData[agent.id];
      if (liveTel) {
        return {
          ...agent,
          status: liveTel.status || agent.status,
          last_run: liveTel.last_run || agent.last_run,
          records_processed: liveTel.records_processed || agent.records_processed,
          latency_ms: liveTel.latency_ms || agent.latency_ms,
        };
      }
      if (snapshotData && agent.id === 'kalshi_scraper') {
        return {
          ...agent,
          last_run: snapshotData.timestamp,
          records_processed: snapshotData.total_markets_processed,
          latency_ms: snapshotData.execution_latency_ms
        };
      }
      return agent;
    });

    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    res.status(200).json({
      success: true,
      timestamp: new Date().toISOString(),
      agent_count: agents.length,
      health_report: qualityData || null,
      arb_summary: arbData || null,
      props_matrix_summary: propsData || null,
      live_stream_summary: liveStreamData ? {
        timestamp: liveStreamData.timestamp,
        total_records: liveStreamData.total_records,
        sources: liveStreamData.sources
      } : null,
      snapshot_summary: snapshotData ? {
        snapshot_id: snapshotData.snapshot_id,
        total_records: snapshotData.total_markets_processed,
        leagues: snapshotData.leagues_covered
      } : null,
      weather_summary: weatherData ? {
        timestamp: weatherData.timestamp,
        venues_scanned: weatherData.total_venues_scanned,
        stadiums: weatherData.reports
      } : null,
      agents: agents
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
