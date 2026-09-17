/* ==========================================================================
   DESTINY NETWORK — Kalshi Real-Time Fast Sports Data Engine
   NO SIMULATED DATA. Real prices only, sub-second update streaming.

   Pulls real Kalshi markets per league & player props:
     - GAME   -> moneyline (who wins)
     - SPREAD -> point spread (picks threshold closest to 50/50)
     - TOTAL  -> over/under total points
     - PROPS  -> player prop lines (Points/Rebounds/Assists/Threes/Yards)
   ========================================================================== */

(function() {
    'use strict';

    function centsToAmericanOdds(cents) {
        const p = parseFloat(cents);
        if (isNaN(p) || p <= 0 || p >= 100) return 'EVEN';
        if (p === 50) return '+100';
        if (p > 50) {
            const odds = Math.round(- (p / (100 - p)) * 100);
            return odds.toString();
        } else {
            const odds = Math.round(+ ((100 - p) / p) * 100);
            return '+' + odds.toString();
        }
    }

    const LEAGUE_SERIES = {
        MLB:   { game: 'KXMLBGAME',   spread: 'KXMLBSPREAD',   total: 'KXMLBTOTAL' },
        NFL:   { game: 'KXNFLGAME',   spread: 'KXNFLSPREAD',   total: 'KXNFLTOTAL' },
        NBA:   { game: 'KXNBAGAME',   spread: 'KXNBASPREAD',   total: 'KXNBATOTAL' },
        NHL:   { game: 'KXNHLGAME',   spread: 'KXNHLSPREAD',   total: 'KXNHLTOTAL' },
        NCAAF: { game: 'KXNCAAFGAME', spread: 'KXNCAAFSPREAD', total: 'KXNCAAFTOTAL' },
        WNBA:  { game: 'KXWNBAGAME',  spread: 'KXWNBASPREAD',  total: 'KXWNBATOTAL' },
    };

    // Dictionary mapping team names, cities, abbreviations, and Kalshi truncated titles to normalized team codes.
    const TEAM_MAP = {
        // NFL
        'nyg': 'nyg', 'newyorkgiants': 'nyg', 'newyorkg': 'nyg', 'giants': 'nyg',
        'lar': 'lar', 'losangelesrams': 'lar', 'losangelesr': 'lar', 'rams': 'lar', 'la': 'lar',
        'kc': 'kc', 'kansascity': 'kc', 'kansascitychiefs': 'kc', 'chiefs': 'kc',
        'ind': 'ind', 'indianapolis': 'ind', 'indianapoliscolts': 'ind', 'colts': 'ind',
        'phi': 'phi', 'philadelphia': 'phi', 'philadelphiaeagles': 'phi', 'eagles': 'phi',
        'dal': 'dal', 'dallas': 'dal', 'dallascowboys': 'dal', 'cowboys': 'dal',
        'sf': 'sf', 'sanfrancisco': 'sf', 'sanfrancisco49ers': 'sf', '49ers': 'sf',
        'gb': 'gb', 'greenbay': 'gb', 'greenbaypackers': 'gb', 'packers': 'gb',
        'den': 'den', 'denver': 'den', 'denverbroncos': 'den', 'broncos': 'den',
        'sea': 'sea', 'seattle': 'sea', 'seattleseahawks': 'sea', 'seahawks': 'sea',
        'bal': 'bal', 'baltimore': 'bal', 'baltimoreravens': 'bal', 'ravens': 'bal',
        'cin': 'cin', 'cincinnati': 'cin', 'cincinnatibengals': 'cin', 'bengals': 'cin',
        'buf': 'buf', 'buffalo': 'buf', 'buffalobills': 'buf', 'bills': 'buf',
        'mia': 'mia', 'miami': 'mia', 'miamidolphins': 'mia', 'dolphins': 'mia',
        'ne': 'ne', 'newengland': 'ne', 'newenglandpatriots': 'ne', 'patriots': 'ne',
        'nyj': 'nyj', 'newyorkjets': 'nyj', 'newyorkj': 'nyj', 'jets': 'nyj',
        'pit': 'pit', 'pittsburgh': 'pit', 'pittsburghsteelers': 'pit', 'steelers': 'pit',
        'cle': 'cle', 'cleveland': 'cle', 'clevelandbrowns': 'cle', 'browns': 'cle',
        'hou': 'hou', 'houston': 'hou', 'houstontexans': 'hou', 'texans': 'hou',
        'jax': 'jax', 'jacksonville': 'jax', 'jacksonvillejaguars': 'jax', 'jaguars': 'jax',
        'ten': 'ten', 'tennessee': 'ten', 'tennesseetitans': 'ten', 'titans': 'ten',
        'lv': 'lv', 'lasvegas': 'lv', 'lasvegasraiders': 'lv', 'raiders': 'lv',
        'lac': 'lac', 'losangeleschargers': 'lac', 'chargers': 'lac',
        'chi': 'chi', 'chicagobears': 'chi', 'bears': 'chi',
        'det': 'det', 'detroit': 'det', 'detroitlions': 'det', 'lions': 'det',
        'min': 'min', 'minnesota': 'min', 'minnesotavikings': 'min', 'vikings': 'min',
        'atl': 'atl', 'atlanta': 'atl', 'atlantafalcons': 'atl', 'falcons': 'atl',
        'car': 'car', 'carolina': 'car', 'carolinapanthers': 'car', 'panthers': 'car',
        'no': 'no', 'neworleans': 'no', 'neworleanssaints': 'no', 'saints': 'no',
        'tb': 'tb', 'tampabay': 'tb', 'tampabaybuccaneers': 'tb', 'buccaneers': 'tb', 'bucs': 'tb',
        'ari': 'ari', 'arizona': 'ari', 'arizonacardinals': 'ari', 'cardinals': 'ari',
        'was': 'was', 'washington': 'was', 'washingtoncommanders': 'was', 'commanders': 'was',

        // MLB
        'cws': 'cws', 'chicagowhitesox': 'cws', 'chicagows': 'cws', 'whitesox': 'cws',
        'nyy': 'nyy', 'newyorkyankees': 'nyy', 'newyorky': 'nyy', 'yankees': 'nyy',
        'nym': 'nym', 'newyorkmets': 'nym', 'newyorkm': 'nym', 'mets': 'nym',
        'lad': 'lad', 'losangelesdodgers': 'lad', 'dodgers': 'lad',
        'bos': 'bos', 'bostonredsox': 'bos', 'redsox': 'bos',
        'chc': 'chc', 'chicagocubs': 'chc', 'cubs': 'chc',
        'hou': 'hou', 'houstonastros': 'hou', 'astros': 'hou',
        'atl': 'atl', 'atlantabraves': 'atl', 'braves': 'atl',
        'stl': 'stl', 'stlouiscardinals': 'stl', 'cardinals': 'stl',
        'sf': 'sf', 'sanfranciscogiants': 'sf',
        'sd': 'sd', 'sandiegopadres': 'sd', 'padres': 'sd',
        'tex': 'tex', 'texasrangers': 'tex', 'rangers': 'tex',
        'tor': 'tor', 'torontobluejays': 'tor', 'bluejays': 'tor',
        'sea': 'sea', 'seattlemariners': 'sea', 'mariners': 'sea',
        'min': 'min', 'minnesotatwins': 'min', 'twins': 'min',
        'cle': 'cle', 'clevelandguardians': 'cle', 'guardians': 'cle',
        'phi': 'phi', 'philadelphiaphillies': 'phi', 'phillies': 'phi',
        'tb': 'tb', 'tampabayrays': 'tb', 'rays': 'tb',
        'bal': 'bal', 'baltimoreorioles': 'bal', 'orioles': 'bal',
        'ari': 'ari', 'arizonadiamondbacks': 'ari', 'dbacks': 'ari',
        'mil': 'mil', 'milwaukeebrewers': 'mil', 'brewers': 'mil',
        'det': 'det', 'detroittigers': 'det', 'tigers': 'det',
        'cin': 'cin', 'cincinnatireds': 'cin', 'reds': 'cin',
        'pit': 'pit', 'pittsburghpirates': 'pit', 'pirates': 'pit',
        'col': 'col', 'coloradorockies': 'col', 'rockies': 'col',
        'wsh': 'wsh', 'washingtonnationals': 'wsh', 'nationals': 'wsh', 'nats': 'wsh',
        'laa': 'laa', 'losangelesangels': 'laa', 'angels': 'laa',

        // NBA
        'okc': 'okc', 'oklahomacity': 'okc', 'oklahomacitythunder': 'okc', 'thunder': 'okc',
        'sas': 'sas', 'sanantonio': 'sas', 'sanantoniospurs': 'sas', 'spurs': 'sas',
        'lal': 'lal', 'losangeleslakers': 'lal', 'lakers': 'lal',
        'gsw': 'gsw', 'goldenstate': 'gsw', 'goldenstatewarriors': 'gsw', 'warriors': 'gsw',
        'bos': 'bos', 'bostonceltics': 'bos', 'celtics': 'bos',
        'mia': 'mia', 'miamiheat': 'mia', 'heat': 'mia',
        'chi': 'chi', 'chicagobulls': 'chi', 'bulls': 'chi',
        'bkn': 'bkn', 'brooklynnets': 'bkn', 'nets': 'bkn',
        'nyk': 'nyk', 'newyorkknicks': 'nyk', 'knicks': 'nyk',
        'mil': 'mil', 'milwaukeebucks': 'mil', 'bucks': 'mil',
        'den': 'den', 'denvernuggets': 'den', 'nuggets': 'den',
        'phx': 'phx', 'phoenixsuns': 'phx', 'suns': 'phx',
        'dal': 'dal', 'dallasmavericks': 'dal', 'mavericks': 'dal', 'mavs': 'dal',
        'lac': 'lac', 'losangelesclippers': 'lac', 'clippers': 'lac',
        'min': 'min', 'minnesotatimberwolves': 'min', 'timberwolves': 'min', 'wolves': 'min',
        'cle': 'cle', 'clevelandcavaliers': 'cle', 'cavaliers': 'cle', 'cavs': 'cle',
        'sac': 'sac', 'sacramentokings': 'sac', 'kings': 'sac',
        'ind': 'ind', 'indianapacers': 'ind', 'pacers': 'ind',
        'orl': 'orl', 'orlandomagic': 'orl', 'magic': 'orl',
        'nop': 'nop', 'neworleanspelicans': 'nop', 'pelicans': 'nop',
        'atl': 'atl', 'atlantahawks': 'atl', 'hawks': 'atl',
        'tor': 'tor', 'torontoraptors': 'tor', 'raptors': 'tor',
        'mem': 'mem', 'memphisgrizzlies': 'mem', 'grizzlies': 'mem',
        'uta': 'uta', 'utahjazz': 'uta', 'jazz': 'uta',
        'cha': 'cha', 'charlottehornets': 'cha', 'hornets': 'cha',
        'por': 'por', 'portlandtrailblazers': 'por', 'blazers': 'por',
        'was': 'was', 'washingtonwizards': 'was', 'wizards': 'was',

        // NCAA / Colleges & WNBA
        'ucla': 'ucla', 'pur': 'pur', 'purdue': 'pur',
        'sjsu': 'sjsu', 'sanjosest': 'sjsu', 'fres': 'fres', 'fresnost': 'fres',
        'smu': 'smu', 'southernmethodist': 'smu', 'mustangs': 'smu', 'smumustangs': 'smu',
        'fsu': 'fsu', 'floridastate': 'fsu', 'seminoles': 'fsu', 'floridastateseminoles': 'fsu',
        'ala': 'ala', 'alabama': 'ala', 'crimsontide': 'ala',
        'uga': 'uga', 'georgia': 'uga', 'bulldogs': 'uga',
        'tex': 'tex', 'texas': 'tex', 'longhorns': 'tex',
        'ou': 'ou', 'oklahoma': 'ou', 'sooners': 'ou',
        'osu': 'osu', 'ohiostate': 'osu', 'buckeyes': 'osu',
        'mich': 'mich', 'michigan': 'mich', 'wolverines': 'mich',
        'ore': 'ore', 'oregon': 'ore', 'ducks': 'ore',
        'nd': 'nd', 'notredame': 'nd', 'fightingirish': 'nd',
        'usc': 'usc', 'trojans': 'usc',
        'psu': 'psu', 'pennstate': 'psu', 'nittanylions': 'psu',
        'clem': 'clem', 'clemson': 'clem', 'tigers': 'clem',
        'lsu': 'lsu', 'lsutigers': 'lsu',
        'tenn': 'tenn', 'tennessee': 'tenn', 'volunteers': 'tenn', 'vols': 'tenn',
        'olemiss': 'olemiss', 'mississippi': 'olemiss', 'rebels': 'olemiss',
        'tamu': 'tamu', 'texasaandm': 'tamu', 'aggies': 'tamu',
        'utah': 'utah', 'utes': 'utah',
        'colo': 'colo', 'colorado': 'colo', 'buffs': 'colo',
        'mia': 'mia', 'miamifl': 'mia', 'hurricanes': 'mia',
        'fla': 'fla', 'floridagators': 'fla', 'gators': 'fla',
        'aub': 'aub', 'auburn': 'aub'
    };

    function gameKeyOf(market) {
        if (!market || !market._league) return null;
        const prefixes = LEAGUE_SERIES[market._league];
        if (!prefixes) return null;
        const prefix = prefixes[market._kind];
        if (!prefix || !market.event_ticker || !market.event_ticker.startsWith(prefix + '-')) return null;
        return market._league + '::' + market.event_ticker.slice(prefix.length + 1);
    }

    // Real price algorithm — never guesses or invents 1-cent fake bids.
    // 1. Last price (if > 0 and < 1.0)
    // 2. Mid-price between bid & ask (if both > 0)
    // 3. Valid bid or ask
    // 4. Previous price
    function realPriceCents(m) {
        const last = parseFloat(m.last_price_dollars);
        const bid = parseFloat(m.yes_bid_dollars);
        const ask = parseFloat(m.yes_ask_dollars);
        const prev = parseFloat(m.previous_price_dollars);

        if (!isNaN(last) && last > 0 && last < 1.0) {
            return Math.round(last * 100);
        }
        if (!isNaN(bid) && bid > 0 && !isNaN(ask) && ask > 0) {
            return Math.round(((bid + ask) / 2) * 100);
        }
        if (!isNaN(bid) && bid > 0 && bid < 1.0) {
            return Math.round(bid * 100);
        }
        if (!isNaN(ask) && ask > 0 && ask < 1.0) {
            return Math.round(ask * 100);
        }
        if (!isNaN(prev) && prev > 0 && prev < 1.0) {
            return Math.round(prev * 100);
        }
        return null;
    }

    function normalizeCode(str) {
        if (!str) return '';
        const norm = (str || '').toLowerCase().replace(/[^a-z0-9]/g, '');
        return TEAM_MAP[norm] || norm;
    }

    // Advanced team matcher matching title, abbreviation, city, and ticker suffix.
    function teamMatches(kalshiLabel, espnName, espnAbbr) {
        if (!kalshiLabel) return false;
        const kCode = normalizeCode(kalshiLabel);
        const nCode = normalizeCode(espnName);
        const aCode = normalizeCode(espnAbbr);

        if (kCode && (kCode === aCode || kCode === nCode)) return true;

        const kNorm = (kalshiLabel || '').toLowerCase().replace(/[^a-z0-9]/g, '');
        const nNorm = (espnName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
        const aNorm = (espnAbbr || '').toLowerCase().replace(/[^a-z0-9]/g, '');

        if (nNorm && (nNorm.includes(kNorm) || kNorm.includes(nNorm))) return true;
        if (aNorm && (aNorm === kNorm || kNorm.includes(aNorm))) return true;

        return false;
    }

    const listeners = {
        odds: new Set(),
        scores: new Set(),
        lineShift: new Set(),
        kalshi: new Set(),
        momentum: new Set(),
        error: new Set()
    };

    let pollTimer = null;
    let consecutiveFailures = 0;

    const KALSHI_PROXY_URL = '/api/kalshi';
    const KALSHI_PROPS_PROXY_URL = '/api/kalshi-props';
    const POLL_INTERVAL_MS = 1500; // Ultra-fast 1.5-second polling interval

    const DestinyLiveFeed = {
        centsToAmericanOdds: centsToAmericanOdds,
        kalshiCache: {},       // ticker -> tick payload
        gameIndex: {},         // gameKey -> [ { team, teamCode, yesPrice, ticker } ]
        spreadIndex: {},       // gameKey -> [ { team, teamCode, line, yesPrice, ticker } ]
        totalIndex: {},        // gameKey -> [ { line, yesPrice, ticker } ]
        lastError: null,

        connect: function() {
            this._pollRealKalshiData();
            if (pollTimer) clearInterval(pollTimer);
            pollTimer = setInterval(() => this._pollRealKalshiData(), POLL_INTERVAL_MS);
        },

        _pollRealKalshiData: function() {
            Promise.allSettled([
                fetch(KALSHI_PROXY_URL).then(r => r.ok ? r.json() : Promise.reject('Proxy HTTP ' + r.status)),
                fetch(KALSHI_PROPS_PROXY_URL).then(r => r.ok ? r.json() : Promise.reject('Props HTTP ' + r.status))
            ])
            .then(results => {
                let markets = [];
                if (results[0].status === 'fulfilled' && results[0].value && results[0].value.markets) {
                    markets.push(...results[0].value.markets);
                }
                if (results[1].status === 'fulfilled' && results[1].value && results[1].value.markets) {
                    markets.push(...results[1].value.markets);
                }

                if (markets.length === 0) {
                    this._setError('No open Kalshi sports/props markets returned');
                    return;
                }

                consecutiveFailures = 0;
                this.lastError = null;

                const newGameIndex = {};
                const newSpreadIndex = {};
                const newTotalIndex = {};
                let pricedCount = 0;

                markets.forEach(m => {
                    const yesPrice = realPriceCents(m);
                    if (yesPrice === null) return; // Skip zero-liquidity unpriced markets

                    pricedCount++;
                    const gk = gameKeyOf(m);

                    if (gk) {
                        const tickerParts = (m.ticker || '').split('-');
                        const teamCode = tickerParts.length >= 3 ? tickerParts[tickerParts.length - 1] : '';

                        if (m._kind === 'game') {
                            if (!newGameIndex[gk]) newGameIndex[gk] = [];
                            newGameIndex[gk].push({ team: m.yes_sub_title || m.title, teamCode, yesPrice, ticker: m.ticker });
                        } else if (m._kind === 'spread') {
                            if (!newSpreadIndex[gk]) newSpreadIndex[gk] = [];
                            newSpreadIndex[gk].push({ team: m.yes_sub_title || m.title, teamCode, line: m.floor_strike, yesPrice, ticker: m.ticker });
                        } else if (m._kind === 'total') {
                            if (!newTotalIndex[gk]) newTotalIndex[gk] = [];
                            newTotalIndex[gk].push({ line: m.floor_strike, yesPrice, ticker: m.ticker });
                        }
                    }

                    // Tick payload for active subscribers
                    const prevPayload = this.kalshiCache[m.ticker];
                    const direction = prevPayload ? (yesPrice > prevPayload.yesPrice ? 'UP' : (yesPrice < prevPayload.yesPrice ? 'DOWN' : prevPayload.direction || 'FLAT')) : 'FLAT';
                    const payload = {
                        ticker: m.ticker,
                        eventTicker: m.event_ticker,
                        team: m.yes_sub_title || m.title,
                        matchup: m.title,
                        yesPrice: yesPrice,
                        noPrice: 100 - yesPrice,
                        americanOdds: centsToAmericanOdds(yesPrice),
                        direction: direction,
                        volume: parseFloat(m.volume_fp) || 0,
                        closeTime: m.close_time || null,
                        kind: m._kind || (m._stat ? 'prop' : 'game'),
                        stat: m._stat || null,
                        league: m._league || null,
                        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false })
                    };

                    this.kalshiCache[m.ticker] = payload;
                    listeners.kalshi.forEach(cb => cb(payload));
                    listeners.momentum.forEach(cb => cb(payload));
                    listeners.odds.forEach(cb => cb(payload));
                });

                this.gameIndex = newGameIndex;
                this.spreadIndex = newSpreadIndex;
                this.totalIndex = newTotalIndex;

                if (pricedCount === 0) {
                    this._setError('Kalshi markets open but awaiting initial liquidity');
                    return;
                }

                this._updateBadge(true, '⚡ KALSHI REAL-TIME FEED ACTIVE');
            })
            .catch(err => {
                consecutiveFailures++;
                this._setError(err.message || String(err));
            });
        },

        _findGameKey: function(awayAbbr, homeAbbr, awayName, homeName) {
            const allKeys = new Set([
                ...Object.keys(this.gameIndex || {}),
                ...Object.keys(this.spreadIndex || {}),
                ...Object.keys(this.totalIndex || {})
            ]);

            const aAbbr = (awayAbbr || '').toLowerCase().trim();
            const hAbbr = (homeAbbr || '').toLowerCase().trim();
            const aName = (awayName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            const hName = (homeName || '').toLowerCase().replace(/[^a-z0-9]/g, '');

            for (const gk of allKeys) {
                const gkLower = gk.toLowerCase();
                let awayHit = false;
                let homeHit = false;

                // 1. Event ticker substring match
                if (aAbbr && aAbbr.length >= 2 && gkLower.includes(aAbbr)) awayHit = true;
                if (hAbbr && hAbbr.length >= 2 && gkLower.includes(hAbbr)) homeHit = true;

                if (!awayHit && aName && aName.length >= 3 && gkLower.includes(aName)) awayHit = true;
                if (!homeHit && hName && hName.length >= 3 && gkLower.includes(hName)) homeHit = true;

                if (awayHit && homeHit) return gk;

                // 2. Team label match across gameIndex and spreadIndex
                const gameTeams = this.gameIndex[gk] || [];
                const spreadTeams = this.spreadIndex[gk] || [];
                const allTeams = [...gameTeams, ...spreadTeams];

                for (const t of allTeams) {
                    if (teamMatches(t.team, awayName, awayAbbr) || (t.teamCode && teamMatches(t.teamCode, awayName, awayAbbr))) awayHit = true;
                    if (teamMatches(t.team, homeName, homeAbbr) || (t.teamCode && teamMatches(t.teamCode, homeName, homeAbbr))) homeHit = true;
                }

                if (awayHit && homeHit) return gk;
            }
            return null;
        },

        getKalshiOdds: function(awayAbbr, homeAbbr, awayName, homeName) {
            const gk = this._findGameKey(awayAbbr, homeAbbr, awayName, homeName);
            if (!gk) return null;
            const teams = this.gameIndex[gk] || [];
            if (!teams || teams.length === 0) return null;

            if (teams.length >= 2) {
                const awayEntry = (teamMatches(teams[0].team, awayName, awayAbbr) || (teams[0].teamCode && teamMatches(teams[0].teamCode, awayName, awayAbbr))) ? teams[0] : teams[1];
                const homeEntry = awayEntry === teams[0] ? teams[1] : teams[0];
                return {
                    awayCents: awayEntry.yesPrice,
                    homeCents: homeEntry.yesPrice,
                    awayAmerican: centsToAmericanOdds(awayEntry.yesPrice),
                    homeAmerican: centsToAmericanOdds(homeEntry.yesPrice),
                    awayTicker: awayEntry.ticker,
                    homeTicker: homeEntry.ticker
                };
            } else if (teams.length === 1) {
                const entry = teams[0];
                const isAway = teamMatches(entry.team, awayName, awayAbbr) || (entry.teamCode && teamMatches(entry.teamCode, awayName, awayAbbr));
                const awayPrice = isAway ? entry.yesPrice : (100 - entry.yesPrice);
                const homePrice = isAway ? (100 - entry.yesPrice) : entry.yesPrice;
                return {
                    awayCents: awayPrice,
                    homeCents: homePrice,
                    awayAmerican: centsToAmericanOdds(awayPrice),
                    homeAmerican: centsToAmericanOdds(homePrice),
                    awayTicker: entry.ticker,
                    homeTicker: entry.ticker
                };
            }

            return null;
        },

        getKalshiBookLine: function(awayAbbr, homeAbbr, awayName, homeName) {
            const gk = this._findGameKey(awayAbbr, homeAbbr, awayName, homeName);
            if (!gk) return null;

            let spread = null;
            const spreadMarkets = this.spreadIndex[gk];
            if (spreadMarkets && spreadMarkets.length) {
                const closest = spreadMarkets.reduce((best, m) =>
                    Math.abs(m.yesPrice - 50) < Math.abs(best.yesPrice - 50) ? m : best
                );
                const favIsAway = teamMatches(closest.team, awayName, awayAbbr) || (closest.teamCode && teamMatches(closest.teamCode, awayName, awayAbbr));
                const favIsHome = !favIsAway && (teamMatches(closest.team, homeName, homeAbbr) || (closest.teamCode && teamMatches(closest.teamCode, homeName, homeAbbr)));
                if (favIsAway || favIsHome) {
                    const favCents = closest.yesPrice;
                    const dogCents = 100 - closest.yesPrice;
                    spread = {
                        awayLine: favIsAway ? -closest.line : closest.line,
                        homeLine: favIsHome ? -closest.line : closest.line,
                        awayAmerican: centsToAmericanOdds(favIsAway ? favCents : dogCents),
                        homeAmerican: centsToAmericanOdds(favIsHome ? favCents : dogCents)
                    };
                }
            }

            let total = null;
            const totalMarkets = this.totalIndex[gk];
            if (totalMarkets && totalMarkets.length) {
                const closest = totalMarkets.reduce((best, m) =>
                    Math.abs(m.yesPrice - 50) < Math.abs(best.yesPrice - 50) ? m : best
                );
                total = {
                    line: closest.line,
                    overAmerican: centsToAmericanOdds(closest.yesPrice),
                    underAmerican: centsToAmericanOdds(100 - closest.yesPrice)
                };
            }

            if (!spread && !total) return null;
            return { spread, total };
        },

        _setError: function(message) {
            this.lastError = message;
            console.error('[DestinyLiveFeed] Kalshi feed update:', message);
            this._updateBadge(false, `⛔ KALSHI DATA UNAVAILABLE`);
            listeners.error.forEach(cb => cb({ message, consecutiveFailures, timestamp: new Date().toLocaleTimeString() }));
        },

        onOddsUpdate: function(cb) { listeners.odds.add(cb); return () => listeners.odds.delete(cb); },
        onScoreUpdate: function(cb) { listeners.scores.add(cb); return () => listeners.scores.delete(cb); },
        onLineShift: function(cb) { listeners.lineShift.add(cb); return () => listeners.lineShift.delete(cb); },
        onKalshiTick: function(cb) { listeners.kalshi.add(cb); return () => listeners.kalshi.delete(cb); },
        onKalshiMomentum: function(cb) { listeners.momentum.add(cb); return () => listeners.momentum.delete(cb); },
        onError: function(cb) { listeners.error.add(cb); return () => listeners.error.delete(cb); },

        _updateBadge: function(active, text) {
            const badges = document.querySelectorAll('.live-ticker, #apiStatusBadge, .live-pill, #webhookStatusBadge');
            badges.forEach(b => {
                if (b) {
                    const textSpan = b.querySelector('span:last-child') || b;
                    if (textSpan && textSpan !== b) textSpan.textContent = text;
                    b.style.borderColor = active ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.7)';
                }
            });
        }
    };

    window.centsToAmericanOdds = centsToAmericanOdds;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => DestinyLiveFeed.connect());
    } else {
        DestinyLiveFeed.connect();
    }

    window.DestinyLiveFeed = DestinyLiveFeed;
})();
