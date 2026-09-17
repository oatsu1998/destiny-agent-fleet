function loadGlobalResources() {
    // Inject Theme CSS if not present
    if (!document.querySelector('link[href*="theme.css"]')) {
        const themeLink = document.createElement('link');
        themeLink.rel = 'stylesheet';
        themeLink.href = 'theme.css';
        document.head.appendChild(themeLink);
    }

    // Inject State Manager JS if not present
    if (!window.DestinyState && !document.querySelector('script[src*="state-manager.js"]')) {
        const stateScript = document.createElement('script');
        stateScript.src = 'state-manager.js';
        document.head.appendChild(stateScript);
    }

    // Inject Live Feed JS if not present
    if (!window.DestinyLiveFeed && !document.querySelector('script[src*="live-feed.js"]')) {
        const feedScript = document.createElement('script');
        feedScript.src = 'live-feed.js';
        document.head.appendChild(feedScript);
    }
}

let isGlobalNavInitialized = false;

function initGlobalNav() {
    if (isGlobalNavInitialized) return;
    if (document.getElementById('destiny-global-nav') || document.querySelector('nav.global-nav')) {
        isGlobalNavInitialized = true;
        return;
    }
    isGlobalNavInitialized = true;

    loadGlobalResources();

    // Inject CSS for Nav
    const style = document.createElement('style');
    style.textContent = `
        .global-nav {
            background: #0a0c0f;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 8px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: 62px;
            position: sticky;
            top: 0;
            z-index: 1000;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }
        .global-nav-brand-wrap {
            transition: opacity 0.2s, transform 0.2s;
        }
        .global-nav-brand-wrap:hover {
            opacity: 0.95;
            transform: translateY(-1px);
        }
        .destiny-logo-badge {
            display: flex;
            align-items: center;
            justify-content: center;
            filter: drop-shadow(0 2px 8px rgba(6, 182, 212, 0.45));
        }
        .brand-top-text {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 16px;
            font-weight: 900;
            letter-spacing: 1px;
            color: #ffffff;
            text-transform: uppercase;
            line-height: 1;
        }
        .brand-bottom-text {
            font-family: 'Barlow Condensed', sans-serif;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 2.2px;
            color: #06b6d4;
            text-transform: uppercase;
            line-height: 1;
            margin-top: 1px;
        }
        .global-nav-brand {
            color: #f59e0b;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-size: 15px;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .global-nav-links {
            display: flex;
            gap: 14px;
            align-items: center;
        }
        .global-nav-link {
            color: #94a3b8;
            text-decoration: none;
            font-weight: 600;
            padding: 6px 10px;
            border-radius: 4px;
            transition: all 0.2s;
            position: relative;
        }
        .global-nav-link:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }
        .global-nav-link.active {
            color: #f59e0b;
            font-weight: 800;
        }
        .global-nav-link.active::after {
            content: '';
            position: absolute;
            bottom: -16px;
            left: 0;
            right: 0;
            height: 2px;
            background: #f59e0b;
        }
        .nav-clock-pill {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 600;
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 6px;
            height: 32px;
            white-space: nowrap;
        }
        .global-nav-clock {
            color: #06b6d4;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1;
        }
        .nav-refresh-btn {
            background: rgba(6, 182, 212, 0.1);
            border: 1px solid rgba(6, 182, 212, 0.3);
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 800;
            color: #06b6d4;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s;
            height: 32px;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
        }
        .nav-refresh-btn:hover {
            background: rgba(6, 182, 212, 0.2);
            color: #fff;
            border-color: #06b6d4;
            transform: translateY(-1px);
        }
        .universal-menu-btn {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 800;
            color: #e4e4e7;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s;
            height: 32px;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
        }
        .universal-menu-btn:hover {
            background: rgba(255, 255, 255, 0.12);
            color: #fff;
            border-color: rgba(255, 255, 255, 0.25);
        }
        .universal-menu-dropdown {
            position: absolute;
            top: 42px;
            right: 0;
            background: #111418;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.7);
            min-width: 220px;
            padding: 8px 0;
            display: none;
            flex-direction: column;
            z-index: 1001;
        }
        .universal-menu-dropdown.open {
            display: flex;
        }
        .universal-menu-item {
            padding: 8px 16px;
            color: #cbd5e1;
            text-decoration: none;
            font-size: 11px;
            font-weight: 600;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .universal-menu-item:hover {
            background: rgba(255, 255, 255, 0.06);
            color: #06b6d4;
            padding-left: 20px;
        }
        .nav-bankroll-pill {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: bold;
            color: #f59e0b;
            display: flex;
            align-items: center;
            gap: 6px;
            height: 32px;
            white-space: nowrap;
        }
        .nav-bankroll-val {
            color: #fff;
        }
    `;
    document.head.appendChild(style);

    // Determine current page for active state
    const currentPath = window.location.pathname;
    const isAgents = currentPath.toLowerCase().includes('agents');
    const isResults = currentPath.toLowerCase().includes('results');
    const isLineTracker = currentPath.toLowerCase().includes('line-tracker');
    const isProps = currentPath.toLowerCase().includes('props');
    const isMyBets = currentPath.toLowerCase().includes('my-bets');
    const isBetSlip = currentPath.toLowerCase().includes('bet-slip') || currentPath.toLowerCase().includes('betslip');
    const isBetHistory = currentPath.toLowerCase().includes('bet-history') || currentPath.toLowerCase().includes('bethistory');
    const isHistory = currentPath.toLowerCase().includes('history') && !isBetHistory;
    const isKalshi = currentPath.toLowerCase().includes('kalshi');
    const isSandbox = currentPath.toLowerCase().includes('sandbox');
    const isPortfolio = currentPath.toLowerCase().includes('portfolio');
    const isLayout = currentPath.toLowerCase().includes('layout');
    const isWalkthrough = currentPath.toLowerCase().includes('walkthrough');

    // Get current bankroll from localStorage or default $1,000,000.00
    const savedBankroll = parseFloat(localStorage.getItem('destiny_bankroll') || localStorage.getItem('bankroll')) || 1000000.00;
    const formattedBankroll = '$' + savedBankroll.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // Inject HTML
    const nav = document.createElement('nav');
    nav.id = 'destiny-global-nav';
    nav.className = 'global-nav';
    nav.innerHTML = `
        <!-- Left: Brand Logo -->
        <div style="display:flex; align-items:center;">
            <a href="index.html" class="global-nav-brand-wrap" style="display:flex; align-items:center; gap:10px; text-decoration:none; margin-right:28px;">
                <div class="destiny-logo-badge">
                    <svg width="34" height="34" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <rect width="36" height="36" rx="9" fill="url(#destiny_grad)"/>
                        <text x="18" y="25" font-family="'Barlow Condensed', 'Arial Black', sans-serif" font-weight="900" font-size="20" fill="#FFFFFF" text-anchor="middle" letter-spacing="-0.5">DN</text>
                        <defs>
                            <linearGradient id="destiny_grad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#06B6D4"/>
                                <stop offset="1" stop-color="#2563EB"/>
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <div style="display:flex; flex-direction:column; justify-content:center; line-height:0.95;">
                    <span class="brand-top-text">DESTINY</span>
                    <span class="brand-bottom-text">NETWORK</span>
                </div>
            </a>

            <!-- Center: Desktop Horizontal Links -->
            <div class="global-nav-links">
                <a href="index.html" class="global-nav-link ${(!isResults && !isLineTracker && !isProps && !isMyBets && !isHistory && !isBetSlip && !isBetHistory && !isKalshi && !isSandbox && !isPortfolio && !isLayout && !isWalkthrough && !isAgents) ? 'active' : ''}">Home</a>
                <a href="agents.html" class="global-nav-link ${isAgents ? 'active' : ''}" style="color:#06b6d4; font-weight:800;">⚡ Agent Fleet</a>
                <a href="results.html" class="global-nav-link ${isResults ? 'active' : ''}">Daily Results</a>
                <a href="my-bets.html" class="global-nav-link ${isMyBets ? 'active' : ''}">Live Bets</a>
                <a href="line-tracker.html" class="global-nav-link ${isLineTracker ? 'active' : ''}">Line Tracker</a>
                <a href="props.html" class="global-nav-link ${isProps ? 'active' : ''}">Props</a>
                <a href="kalshi.html" class="global-nav-link ${isKalshi ? 'active' : ''}">Kalshi</a>
                <a href="sandbox.html" class="global-nav-link ${isSandbox ? 'active' : ''}">Sandbox</a>
                <a href="portfolio.html" class="global-nav-link ${isPortfolio ? 'active' : ''}">Portfolio</a>
                <a href="walkthrough.html" class="global-nav-link ${isWalkthrough ? 'active' : ''}">Walkthrough</a>
            </div>
        </div>

        <!-- Right: Clock Pill + Refresh Button + Walkthrough Button + Bankroll Pill + Menu Button in Single Row -->
        <div style="display:flex; align-items:center; gap:10px; position:relative;">
            <div class="nav-clock-pill">
                <span>🕒</span>
                <span id="global-nav-clock" class="global-nav-clock">Loading date...</span>
            </div>

            <a href="walkthrough.html" class="nav-walkthrough-btn ${isWalkthrough ? 'active' : ''}" style="background: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.4); border-radius: 4px; padding: 5px 12px; font-size: 11px; font-weight: 800; color: #06b6d4; display: flex; align-items: center; gap: 6px; text-decoration: none; height: 32px; white-space: nowrap; font-family: 'JetBrains Mono', monospace; transition: all 0.2s;" title="View Walkthrough">
                <span>📋</span> <span>WALKTHROUGH</span>
            </a>

            <button class="nav-refresh-btn" onclick="handleNavRefresh()" title="Force Refresh Live Data">
                <span>↻</span> <span>REFRESH</span>
            </button>

            <div class="nav-bankroll-pill">
                <span>BANKROLL:</span>
                <span class="nav-bankroll-val bankroll-amount">${formattedBankroll}</span>
            </div>

            <!-- Universal Menu Button on Far Right -->
            <button class="universal-menu-btn" onclick="toggleUniversalMenu(event)" title="Open Universal Navigation Menu">
                <span style="font-size:14px;">☰</span> MENU
            </button>

            <!-- Universal Dropdown Drawer (Right Aligned) -->
            <div id="universal-menu-dropdown" class="universal-menu-dropdown" onclick="event.stopPropagation()">
                <div style="padding:6px 16px 8px; font-size:10px; color:#f59e0b; font-weight:800; border-bottom:1px solid rgba(255,255,255,0.08); letter-spacing:1px;">UNIVERSAL NAVIGATION</div>
                <a href="walkthrough.html" class="universal-menu-item ${isWalkthrough ? 'active' : ''}" style="background: rgba(6, 182, 212, 0.12); color: #06b6d4; font-weight: 800; border-left: 3px solid #06b6d4; margin: 4px 0;">
                    <span style="display:flex; align-items:center; justify-content:space-between; width:100%;">
                        <span>📋 Walkthrough</span>
                        <span style="font-size:9px; background:rgba(6,182,212,0.25); color:#06b6d4; padding:2px 6px; border-radius:3px; border:1px solid rgba(6,182,212,0.5); font-weight:bold;">UPDATED</span>
                    </span>
                </a>
                <a href="index.html" class="universal-menu-item">🏠 Home</a>
                <a href="agents.html" class="universal-menu-item ${isAgents ? 'active' : ''}" style="color: #06b6d4; font-weight: 800;">⚡ Agent Fleet Command Center</a>
                <a href="results.html" class="universal-menu-item">🏆 Daily Results & Recaps</a>
                <a href="my-bets.html" class="universal-menu-item">🎟️ Live Bets Tracking</a>
                <a href="line-tracker.html" class="universal-menu-item">📈 Line Tracker</a>
                <a href="props.html" class="universal-menu-item">🎯 Player Props</a>
                <a href="history.html" class="universal-menu-item">📜 Line History & Logs</a>
                <a href="bet-history.html" class="universal-menu-item">📑 Bet History Ledger</a>
                <a href="bet-slip.html" class="universal-menu-item">🧾 Bet Slip Builder</a>
                <a href="kalshi.html" class="universal-menu-item">📊 Kalshi Live Markets</a>
                <a href="sandbox.html" class="universal-menu-item">🧪 Strategy Sandbox</a>
                <a href="portfolio.html" class="universal-menu-item">💼 Portfolio & Ledger</a>
                <a href="layout.html" class="universal-menu-item">📐 Layout & Widgets</a>
                <a href="about.html" class="universal-menu-item">ℹ️ About</a>
            </div>
        </div>
    `;

    // Remove any existing nav element before inserting
    const existingNavs = document.querySelectorAll('#destiny-global-nav, nav.global-nav');
    existingNavs.forEach(el => el.remove());

    document.body.insertBefore(nav, document.body.firstChild);

    // Live Clock Update
    function updateClock() {
        const clockEl = document.getElementById('global-nav-clock');
        if (clockEl) {
            const now = new Date();
            const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            
            const dayStr = days[now.getDay()];
            const monthStr = months[now.getMonth()];
            const dateNum = now.getDate();
            
            let hours = now.getHours();
            const ampm = hours >= 12 ? 'PM' : 'AM';
            hours = hours % 12;
            hours = hours ? hours : 12;
            const mins = String(now.getMinutes()).padStart(2, '0');
            const secs = String(now.getSeconds()).padStart(2, '0');

            clockEl.innerText = `${dayStr}, ${monthStr} ${dateNum} · ${hours}:${mins}:${secs} ${ampm}`;
        }
    }
    updateClock();
    setInterval(updateClock, 1000);

    // Global Refresh Trigger Handler
    window.handleNavRefresh = function() {
        if (typeof window.manualRefresh === 'function') {
            window.manualRefresh();
        } else {
            window.location.reload();
        }
    };

    // Universal Menu Toggle Logic
    window.toggleUniversalMenu = function(e) {
        if (e) e.stopPropagation();
        const dd = document.getElementById('universal-menu-dropdown');
        if (dd) dd.classList.toggle('open');
    };

    // Close Universal Menu on outside click or Escape
    document.addEventListener('click', () => {
        const dd = document.getElementById('universal-menu-dropdown');
        if (dd && dd.classList.contains('open')) dd.classList.remove('open');
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const dd = document.getElementById('universal-menu-dropdown');
            if (dd && dd.classList.contains('open')) dd.classList.remove('open');
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGlobalNav);
} else {
    initGlobalNav();
}
