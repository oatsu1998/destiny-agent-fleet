# Technical Implementation Plan & Roadmap

This document outlines the architectural standards, recent feature implementations, and system roadmap for the Destiny Sports platform.

## Architectural Guidelines
1. **Strict Real Data**: No mock or fabricated data allowed. Show N/A or Weather unavailable when live data is absent.
2. **Modular Frontend**: Vanilla JavaScript components with central state management via `state-manager.js` and universal header via `nav.js`.
3. **CORS Safety**: Server-side proxy functions in `/api/` handle external API integrations (Kalshi, sportsbook odds) to bypass browser CORS restrictions.

---

## Recent Feature Implementations

### Outdoor Game Weather Chips (`index.html`)
- **Open-Meteo Integration**: Fetches real-time temperature, wind speed, wind direction degrees, wind gusts, and WMO weather codes.
- **US State Disambiguation**: Uses a state lookup dictionary to match venue city and state (`OH` -> `Ohio`).
- **Wind Flag Indicator**: Renders a 14px cyan flag SVG rotated using `transform: rotate(${deg}deg)` matching the meteorological wind direction with cardinal direction text (`NW`, `SE`, etc.).
- **Dome Filtering**: Indoor venues (`indoor: true`) do not render weather chips.

### NFL Player Props Integration (`/api/kalshi-props.js` & `props.html`)
- **Kalshi Series Expansion**: Added 4 NFL series tickers:
  - `KXNFLPASSYDS` (Passing Yards)
  - `KXNFLRSHYDS` (Rushing Yards)
  - `KXNFLRECYDS` (Receiving Yards)
  - `KXNFLREC` (Receptions)
- **UI Tabs**: Added the NFL tab filter and custom card creation options in `props.html`.
- **Empty State Handling**: Gracefully handles zero active priced markets by displaying `NO LIVE PROPS PRICED YET` without breaking.

### Command Center Initialization Fix (`index.html`)
- Safely references `betSlip.length` using a `typeof` guard (`typeof betSlip !== 'undefined' && Array.isArray(betSlip)`) inside `renderLiveWagersPanel()` to prevent `ReferenceError` crashes during initial page render.

### Line Tracker History Fix (`line-tracker.html`)
- Defined missing `fetchHistory()` function in `line-tracker.html` to handle historical odds matrix requests.

---

## Ongoing Roadmap & Next Steps
- **Sidebar Drag & Drop**: Upgrade drag-and-drop ordering to Pointer Events for mobile touch devices.
- **Enhanced Live Feed**: Real-time websocket tick animations across player prop cards.
