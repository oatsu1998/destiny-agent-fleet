/* ==========================================================================
   DESTINY NETWORK — Cross-Page & Multi-Tab State Synchronization Engine
   ========================================================================== */

(function() {
    'use strict';

    try {
        const raw = localStorage.getItem('destiny_game_wagers');
        if (raw) {
            const list = JSON.parse(raw);
            if (Array.isArray(list)) {
                const cleaned = list.map(w => {
                    if (!w) return w;
                    const id = String(w.id || '');
                    const ticket = String(w.ticketNumber || '');
                    if (id.includes('994125729') || ticket.includes('994125729')) return { ...w, status: 'LOST' };
                    if (id.includes('994126389') || ticket.includes('994126389')) return { ...w, status: 'LOST' };
                    if (id.includes('994154199') || ticket.includes('994154199')) return { ...w, status: 'WON', toWin: 42.37 };
                    if (id.includes('994131534') || ticket.includes('994131534')) return { ...w, status: 'WON', toWin: 17.86 };
                    if (id.includes('994128595') || ticket.includes('994128595')) return { ...w, status: 'WON', toWin: 8.00 };
                    if (id.includes('993183110-1') || ticket.includes('993183110-1')) return { ...w, status: 'WON', toWin: 40.00 };
                    return w;
                }).filter(w => {
                    if (!w) return false;
                    const id = String(w.id || '');
                    const ticket = String(w.ticketNumber || '');
                    const date = String(w.acceptedDate || '');
                    const ts = String(w.timestamp || '');
                    const text = (String(w.event || '') + ' ' + String(w.target || '') + ' ' + String(w.matchup || '') + ' ' + String(w.selection || '') + ' ' + String(w.description || '') + ' ' + String(w.side || '')).toUpperCase();

                    if (id.includes('wager-seed') || id.includes('mock-okc') || id.includes('9913') || id.includes('9912')) return false;
                    if (date.includes('8/28') || date.includes('8/29') || ts.includes('2026-08-28') || ts.includes('2026-08-29')) return false;
                    if (text.includes('VIKINGS') || text.includes('BRONCOS') || text.includes('SAN JOSE') || text.includes('SJSU') || text.includes('NC STATE') || text.includes('NCST') || text.includes('MEMPHIS') || text.includes('GB @ DEN') || text.includes('PACKERS') || text.includes('GREEN BAY') || text.includes('THUNDER') || text.includes('SPURS') || text.includes('OKLAHOMA') || text.includes('OKC @ SAS') || text.includes('DENVER') || text.includes('GB')) return false;
                    return true;
                });
                localStorage.setItem('destiny_game_wagers', JSON.stringify(cleaned));
            }
        }
    } catch(e) {}

    const KEYS = {
        BANKROLL: 'bankroll',
        WAGERS: 'destiny_game_wagers',
        PROPS: 'destiny_tracked_picks',
        KALSHI_POSITIONS: 'kalshi_positions',
        GAME_HISTORY: 'destiny_game_history'
    };

    const subscribers = new Map();

    const DestinyState = {
        KEYS: KEYS,

        // ── Bankroll Management ──────────────────────────────────────────────
        getBankroll: function() {
            const saved = localStorage.getItem(KEYS.BANKROLL);
            const val = parseFloat(saved);
            return isNaN(val) ? 10000.00 : val;
        },

        setBankroll: function(amount, notify = true) {
            const val = parseFloat(amount);
            const sanitized = isNaN(val) ? 10000.00 : val;
            localStorage.setItem(KEYS.BANKROLL, sanitized.toFixed(2));
            if (notify) this._notify(KEYS.BANKROLL, sanitized);
            return sanitized;
        },

        isLegacyWager: function(w) {
            if (!w) return false;
            const id = String(w.id || '');
            const ticket = String(w.ticketNumber || '');
            const date = String(w.acceptedDate || '');
            const ts = String(w.timestamp || '');
            const text = (String(w.event || '') + ' ' + String(w.target || '') + ' ' + String(w.matchup || '') + ' ' + String(w.selection || '') + ' ' + String(w.description || '') + ' ' + String(w.side || '')).toUpperCase();

            if (id.includes('9913') || id.includes('9912') || ticket.includes('9913') || ticket.includes('9912') || id.includes('wager-seed') || id.includes('mock-okc')) return true;
            if (date.includes('8/28') || date.includes('8/29') || ts.includes('2026-08-28') || ts.includes('2026-08-29')) return true;
            if (text.includes('VIKINGS') || text.includes('BRONCOS') || text.includes('SAN JOSE') || text.includes('SJSU') || text.includes('NC STATE') || text.includes('NCST') || text.includes('MEMPHIS') || text.includes('GB @ DEN') || text.includes('PACKERS') || text.includes('GREEN BAY') || text.includes('THUNDER') || text.includes('SPURS') || text.includes('OKLAHOMA') || text.includes('OKC @ SAS') || text.includes('DENVER') || text.includes('GB')) return true;

            return false;
        },

        getWagers: function() {
            try {
                let stored = JSON.parse(localStorage.getItem(KEYS.WAGERS) || '[]');
                const defaultWagers = [
                    {
                        id: 'ticket-993182991-1',
                        ticketNumber: '993182991-1',
                        event: 'FRESNO STATE at USC',
                        matchup: 'FRESNO ST @ USC',
                        target: 'Teaser (3 Teams) — Fresno St +28.5, LSU -4 & Stanford +30.5',
                        selection: 'Fresno State +28.5',
                        type: 'Teaser',
                        side: 'Fresno St +28.5 / LSU -4 / Stanford +30.5',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 25.00,
                        wager: 25.00,
                        toWin: 40.00,
                        placedOdds: '+28.5',
                        odds: '+28.5',
                        currentOdds: '+38.5',
                        status: 'LOST',
                        acceptedDate: '09/04/26 07:56 PM GMT-5',
                        timestamp: '2026-09-04T19:56:00.000Z',
                        description: 'Football - NCAA - Fresno State vs USC - Teaser | 151 Fresno State +28½ -102 For Game | 09/04/2026 | 09:00:00 PM (EST) | Settled LOST | Football - NCAA - Clemson vs LSU - Teaser | 220 LSU -4 -110 For Game | 09/05/2026 | 07:30:00 PM (EST) | Pending | Football - NCAA - Miami Florida vs Stanford - Teaser | 154 Stanford +30½ -105 For Game | 09/04/2026 | 09:00:00 PM (EST) | Pending',
                        history: ['54.5', '38.0', '22.0'],
                        legs: [
                            { matchup: 'FRESNO STATE at USC', event: 'FRESNO STATE at USC', awayTag: 'FRESNO ST', homeTag: 'USC', selection: 'Fresno State +28.5', odds: '+28.5', status: 'LOST' },
                            { matchup: 'CLEMSON at LSU', event: 'CLEMSON at LSU', awayTag: 'CLEM', homeTag: 'LSU', selection: 'LSU -4', odds: '-110', status: 'PENDING' },
                            { matchup: 'MIAMI FLORIDA at STANFORD', event: 'MIAMI FLORIDA at STANFORD', awayTag: 'MIA', homeTag: 'STAN', selection: 'Stanford +30.5', odds: '-105', status: 'PENDING' }
                        ]
                    },
                    {
                        id: 'ticket-993183110-1',
                        ticketNumber: '993183110-1',
                        event: 'MIAMI FL at STANFORD / FRESNO ST at USC / CLEMSON at LSU',
                        matchup: 'MIA @ STAN / FRESNO ST @ USC / CLEM @ LSU',
                        target: 'Teaser (3 Teams) — Miami FL -18.5, USC -16.5 & LSU -4',
                        selection: 'Teaser — Miami FL -18.5, USC -16.5 & LSU -4 (+160)',
                        type: 'Teaser',
                        side: 'Miami FL -18.5 / USC -16.5 / LSU -4',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 25.00,
                        wager: 25.00,
                        toWin: 40.00,
                        placedOdds: '+160',
                        odds: '+160',
                        currentOdds: '+160',
                        status: 'WON',
                        acceptedDate: '09/04/26 07:57 PM GMT-5',
                        timestamp: '2026-09-04T19:57:00.000Z',
                        description: 'Football - NCAA - Miami Florida vs Stanford - Teaser | 153 Miami Florida -18½ -115 For Game | 09/04/2026 | 09:00:00 PM (EST) | Settled WON | Football - NCAA - Fresno State vs USC - Teaser | 152 USC -16½ -118 For Game | 09/04/2026 | 09:00:00 PM (EST) | Settled WON | Football - NCAA - Clemson vs LSU - Teaser | 220 LSU -4 -110 For Game | 09/05/2026 | 07:30:00 PM (EST) | Settled WON',
                        history: ['+160', '+160', '+160'],
                        legs: [
                            { matchup: 'MIAMI FLORIDA at STANFORD', event: 'MIAMI FLORIDA at STANFORD', awayTag: 'MIA', homeTag: 'STAN', selection: 'Miami Florida -18.5', odds: '-115', status: 'WON' },
                            { matchup: 'FRESNO STATE at USC', event: 'FRESNO STATE at USC', awayTag: 'FRESNO ST', homeTag: 'USC', selection: 'USC -16.5', odds: '-118', status: 'WON' },
                            { matchup: 'CLEMSON at LSU', event: 'CLEMSON at LSU', awayTag: 'CLEM', homeTag: 'LSU', selection: 'LSU -4', odds: '-110', status: 'WON' }
                        ]
                    },
                    {
                        id: 'ticket-993192834-1',
                        ticketNumber: '993192834-1',
                        event: 'FRESNO STATE at USC',
                        matchup: 'FRESNO ST @ USC',
                        target: 'FRESNO STATE at USC',
                        selection: 'FRESNO ST — Team Total — OVER 9.5',
                        type: 'Live',
                        side: 'Fresno St Team Total Over 9.5',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 79.32,
                        wager: 79.32,
                        toWin: 66.10,
                        placedOdds: '-120',
                        odds: '-120',
                        currentOdds: '-120',
                        status: 'LOST',
                        acceptedDate: '09/04/26 08:44 PM GMT-5',
                        timestamp: '2026-09-04T20:44:00.000Z',
                        description: 'FRESNO STATE at USC - FRESNO ST - Team Total - OVER 9.5',
                        history: ['-120', '-120', '-120'],
                        legs: [
                            { matchup: 'FRESNO STATE at USC', event: 'FRESNO STATE at USC', awayTag: 'FRESNO ST', homeTag: 'USC', selection: 'Fresno St Team Total Over 9.5', odds: '-120', status: 'LOST' }
                        ]
                    },
                    {
                        id: 'ticket-994125729',
                        ticketNumber: '994125729',
                        event: 'SMU at FLORIDA STATE',
                        matchup: 'SMU @ FSU',
                        target: 'SMU at FLORIDA STATE - Side [3rd Quarter] - FLORIDA ST -2.5',
                        selection: 'FLORIDA ST -2.5 [3rd Quarter]',
                        type: 'Live',
                        side: 'Florida St -2.5 [3rd Qtr]',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 50.05,
                        wager: 50.05,
                        toWin: 29.44,
                        placedOdds: '-170',
                        odds: '-170',
                        currentOdds: '-170',
                        status: 'LOST',
                        acceptedDate: '9/8/26',
                        timestamp: '2026-09-08T00:00:00.000Z',
                        description: 'SMU at FLORIDA STATE - Side [3rd Quarter] - FLORIDA ST -2.5',
                        history: ['-170'],
                        legs: [
                            { matchup: 'SMU at FLORIDA STATE', event: 'SMU at FLORIDA STATE', awayTag: 'SMU', homeTag: 'FSU', selection: 'FLORIDA ST -2.5 [3rd Quarter]', odds: '-170', status: 'LOST' }
                        ]
                    },
                    {
                        id: 'ticket-994154199',
                        ticketNumber: '994154199',
                        event: 'SMU at FLORIDA STATE',
                        matchup: 'SMU @ FSU',
                        target: 'SMU at FLORIDA STATE - SMU - Team Total - UNDER 29.5',
                        selection: 'SMU Team Total UNDER 29.5',
                        type: 'Live',
                        side: 'SMU Under 29.5',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 44.49,
                        wager: 44.49,
                        toWin: 42.37,
                        placedOdds: '-105',
                        odds: '-105',
                        currentOdds: '-105',
                        status: 'WON',
                        acceptedDate: '9/8/26',
                        timestamp: '2026-09-08T00:15:00.000Z',
                        description: 'SMU at FLORIDA STATE - SMU - Team Total - UNDER 29.5',
                        history: ['-105'],
                        legs: [
                            { matchup: 'SMU at FLORIDA STATE', event: 'SMU at FLORIDA STATE', awayTag: 'SMU', homeTag: 'FSU', selection: 'SMU Team Total UNDER 29.5', odds: '-105', status: 'WON' }
                        ]
                    },
                    {
                        id: 'ticket-994131534',
                        ticketNumber: '994131534',
                        event: 'SMU at FLORIDA STATE',
                        matchup: 'SMU @ FSU',
                        target: 'SMU at FLORIDA STATE - Total - UNDER 55.5',
                        selection: 'UNDER 55.5',
                        type: 'Live',
                        side: 'Under 55.5',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 25.00,
                        wager: 25.00,
                        toWin: 17.86,
                        placedOdds: '-140',
                        odds: '-140',
                        currentOdds: '-140',
                        status: 'WON',
                        acceptedDate: '9/8/26',
                        timestamp: '2026-09-08T00:10:00.000Z',
                        description: 'SMU at FLORIDA STATE - Total - UNDER 55.5',
                        history: ['-140'],
                        legs: [
                            { matchup: 'SMU at FLORIDA STATE', event: 'SMU at FLORIDA STATE', awayTag: 'SMU', homeTag: 'FSU', selection: 'UNDER 55.5', odds: '-140', status: 'WON' }
                        ]
                    },
                    {
                        id: 'ticket-994128595',
                        ticketNumber: '994128595',
                        event: 'SMU at FLORIDA STATE',
                        matchup: 'SMU @ FSU',
                        target: 'SMU at FLORIDA STATE - Total - UNDER 50.5',
                        selection: 'UNDER 50.5',
                        type: 'Live',
                        side: 'Under 50.5',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 10.00,
                        wager: 10.00,
                        toWin: 8.00,
                        placedOdds: '-125',
                        odds: '-125',
                        currentOdds: '-125',
                        status: 'WON',
                        acceptedDate: '9/8/26',
                        timestamp: '2026-09-08T00:05:00.000Z',
                        description: 'SMU at FLORIDA STATE - Total - UNDER 50.5',
                        history: ['-125'],
                        legs: [
                            { matchup: 'SMU at FLORIDA STATE', event: 'SMU at FLORIDA STATE', awayTag: 'SMU', homeTag: 'FSU', selection: 'UNDER 50.5', odds: '-125', status: 'WON' }
                        ]
                    },
                    {
                        id: 'ticket-994126389',
                        ticketNumber: '994126389',
                        event: 'SMU at FLORIDA STATE',
                        matchup: 'SMU @ FSU',
                        target: 'SMU at FLORIDA STATE - Total - UNDER 45.5',
                        selection: 'UNDER 45.5',
                        type: 'Live',
                        side: 'Under 45.5',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline',
                        stake: 25.85,
                        wager: 25.85,
                        toWin: 24.62,
                        placedOdds: '-105',
                        odds: '-105',
                        currentOdds: '-105',
                        status: 'LOST',
                        acceptedDate: '9/8/26',
                        timestamp: '2026-09-08T00:01:00.000Z',
                        description: 'SMU at FLORIDA STATE - Total - UNDER 45.5',
                        history: ['-105'],
                        legs: [
                            { matchup: 'SMU at FLORIDA STATE', event: 'SMU at FLORIDA STATE', awayTag: 'SMU', homeTag: 'FSU', selection: 'UNDER 45.5', odds: '-105', status: 'LOST' }
                        ]
                    }
                ];

                if (stored && Array.isArray(stored)) {
                    stored = stored.filter(sw => !this.isLegacyWager(sw));
                }

                if (!stored || !Array.isArray(stored) || stored.length === 0) {
                    stored = defaultWagers;
                } else {
                    // Merge any missing default wagers into stored and sync default settled statuses
                    defaultWagers.forEach(dw => {
                        const matchIdx = stored.findIndex(sw => 
                            sw.id === dw.id || 
                            (sw.ticketNumber && dw.ticketNumber && sw.ticketNumber === dw.ticketNumber) || 
                            (sw.id && dw.ticketNumber && sw.id.includes(dw.ticketNumber)) ||
                            (sw.ticketNumber && dw.id && dw.id.includes(sw.ticketNumber))
                        );
                        if (matchIdx < 0) {
                            stored.push(dw);
                        } else {
                            stored[matchIdx].status = dw.status;
                            if (dw.legs) stored[matchIdx].legs = dw.legs;
                            if (dw.toWin) stored[matchIdx].toWin = dw.toWin;
                        }
                    });
                }

                stored = stored.map(w => {
                    const st = String(w.status || 'PENDING').toUpperCase();
                    return {
                        ...w,
                        status: (st === 'PENDING' || st === 'OPEN') ? 'PENDING' : st,
                        odds: w.placedOdds || w.odds || '-110',
                        placedOdds: w.placedOdds || w.odds || '-110',
                        sportsbook: 'BetOnline',
                        bookmaker: 'BetOnline'
                    };
                });

                localStorage.setItem(KEYS.WAGERS, JSON.stringify(stored));
                return stored;
            } catch (e) {
                console.error('[DestinyState] Error reading wagers:', e);
                return [];
            }
        },

        saveWagers: function(wagersArr, notify = true) {
            const data = Array.isArray(wagersArr) ? wagersArr : [];
            localStorage.setItem(KEYS.WAGERS, JSON.stringify(data));
            if (notify) this._notify(KEYS.WAGERS, data);
            return data;
        },

        settleWager: function(wagerId, newStatus, customPayout = null) {
            const wagers = this.getWagers();
            const w = wagers.find(item => item.id === wagerId);
            if (!w) return null;

            w.status = newStatus;

            let payout = 0;
            if (customPayout !== null && !isNaN(parseFloat(customPayout))) {
                payout = parseFloat(customPayout);
            } else if (newStatus === 'WON') {
                payout = (parseFloat(w.stake) || 0) + (parseFloat(w.toWin) || 0);
            } else if (newStatus === 'PUSH' || newStatus === 'VOID') {
                payout = parseFloat(w.stake) || 0;
            } else if (newStatus === 'LOST') {
                payout = 0;
            } else if (newStatus === 'CASHED') {
                payout = parseFloat(w.cashout) || ((parseFloat(w.stake) || 0) * 0.95);
            }

            w.settledPayout = payout;
            w.settledDate = new Date().toISOString();

            this.saveWagers(wagers);

            if (payout > 0) {
                const currentBankroll = this.getBankroll();
                this.setBankroll(currentBankroll + payout);
            }

            this.showToast(`Wager ${w.ticketNumber || w.id} settled as ${newStatus} ($${payout.toFixed(2)})`, newStatus === 'WON' || newStatus === 'CASHED' ? 'win' : 'accent');
            return w;
        },

        addWager: function(wagerObj) {
            const wagers = this.getWagers();
            wagerObj.id = wagerObj.id || 'w_' + Date.now();
            wagerObj.timestamp = wagerObj.timestamp || new Date().toISOString();
            wagers.unshift(wagerObj);
            this.saveWagers(wagers);
            this.showToast(`Wager added: ${wagerObj.event || wagerObj.matchup || 'New Bet'}`, 'win');
            return wagerObj;
        },

        // ── Player Props ─────────────────────────────────────────────────────
        getProps: function() {
            try {
                return JSON.parse(localStorage.getItem(KEYS.PROPS) || '[]');
            } catch (e) {
                console.error('[DestinyState] Error reading props:', e);
                return [];
            }
        },

        saveProps: function(propsArr, notify = true) {
            const data = Array.isArray(propsArr) ? propsArr : [];
            localStorage.setItem(KEYS.PROPS, JSON.stringify(data));
            if (notify) this._notify(KEYS.PROPS, data);
            return data;
        },

        addProp: function(propObj) {
            const props = this.getProps();
            propObj.id = propObj.id || 'p_' + Date.now();
            propObj.status = propObj.status || 'PENDING';
            props.unshift(propObj);
            this.saveProps(props);

            // Automatically mirror into Wagers as well for cross-page portfolio tracking
            const wagerMirror = {
                id: 'prop_wager_' + propObj.id,
                event: `${propObj.player} — ${propObj.stat} ${propObj.type} ${propObj.line}`,
                matchup: propObj.matchup || 'Player Prop',
                stake: propObj.stake || 50,
                odds: propObj.odds || '-110',
                status: propObj.status === 'WON' ? 'WON' : propObj.status === 'LOST' ? 'LOST' : 'PENDING',
                type: 'Player Prop',
                bookmaker: propObj.bookmaker || 'FanDuel',
                clv: '+4.2%'
            };
            const wagers = this.getWagers();
            const existingIdx = wagers.findIndex(w => w.id === wagerMirror.id);
            if (existingIdx >= 0) {
                wagers[existingIdx] = wagerMirror;
            } else {
                wagers.unshift(wagerMirror);
            }
            this.saveWagers(wagers);

            this.showToast(`Tracked Prop: ${propObj.player} ${propObj.type} ${propObj.line}`, 'cyan');
            return propObj;
        },

        // ── Kalshi Positions ─────────────────────────────────────────────────
        getKalshiPositions: function() {
            try {
                return JSON.parse(localStorage.getItem(KEYS.KALSHI_POSITIONS) || '[]');
            } catch (e) {
                return [];
            }
        },

        saveKalshiPositions: function(positionsArr, notify = true) {
            const data = Array.isArray(positionsArr) ? positionsArr : [];
            localStorage.setItem(KEYS.KALSHI_POSITIONS, JSON.stringify(data));
            if (notify) this._notify(KEYS.KALSHI_POSITIONS, data);
            return data;
        },

        // ── Game History Snapshots ───────────────────────────────────────────
        getGameHistory: function() {
            try {
                return JSON.parse(localStorage.getItem(KEYS.GAME_HISTORY) || '{}');
            } catch (e) {
                return {};
            }
        },

        saveGameHistory: function(historyObj, notify = true) {
            const data = historyObj && typeof historyObj === 'object' ? historyObj : {};
            localStorage.setItem(KEYS.GAME_HISTORY, JSON.stringify(data));
            if (notify) this._notify(KEYS.GAME_HISTORY, data);
            return data;
        },

        // ── Event Subscription API ───────────────────────────────────────────
        subscribe: function(key, callback) {
            if (!subscribers.has(key)) {
                subscribers.set(key, new Set());
            }
            subscribers.get(key).add(callback);
            return function unsubscribe() {
                if (subscribers.has(key)) {
                    subscribers.get(key).delete(callback);
                }
            };
        },

        _notify: function(key, data) {
            if (subscribers.has(key)) {
                subscribers.get(key).forEach(cb => {
                    try { cb(data); } catch (e) { console.error(e); }
                });
            }
            // Also notify wildcard subscribers
            if (subscribers.has('*')) {
                subscribers.get('*').forEach(cb => {
                    try { cb(key, data); } catch (e) { console.error(e); }
                });
            }
        },

        // ── Toast UI Helper ─────────────────────────────────────────────────
        showToast: function(msg, type = 'accent') {
            let container = document.getElementById('destiny-toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'destiny-toast-container';
                document.body.appendChild(container);
            }

            const toast = document.createElement('div');
            toast.className = `destiny-toast ${type}`;
            toast.innerHTML = `<span style="font-weight:bold;">[DESTINY]</span> <span>${msg}</span>`;
            container.appendChild(toast);

            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    };

    // ── Listen to Window Storage Event for Multi-Tab Syncing ───────────────
    window.addEventListener('storage', function(e) {
        if (!e.key) return;
        let parsed = e.newValue;
        try { parsed = JSON.parse(e.newValue); } catch(err) {}
        
        DestinyState._notify(e.key, parsed);
        
        // Auto-update any top nav bankroll display
        if (e.key === KEYS.BANKROLL) {
            document.querySelectorAll('.bankroll-amount, #bankrollVal').forEach(el => {
                el.textContent = '$' + parseFloat(parsed || 10000).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            });
        }
    });

    window.DestinyState = DestinyState;
})();
