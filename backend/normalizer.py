import re
import datetime
from typing import Dict, Any, List, Optional

# Team Mapping dictionary for code normalization
TEAM_MAP = {
    # NFL
    'nyg': 'NYG', 'newyorkgiants': 'NYG', 'giants': 'NYG',
    'lar': 'LAR', 'losangelesrams': 'LAR', 'rams': 'LAR',
    'kc': 'KC', 'kansascitychiefs': 'KC', 'chiefs': 'KC',
    'ind': 'IND', 'indianapoliscolts': 'IND', 'colts': 'IND',
    'phi': 'PHI', 'philadelphiaeagles': 'PHI', 'eagles': 'PHI',
    'dal': 'DAL', 'dallascowboys': 'DAL', 'cowboys': 'DAL',
    'sf': 'SF', 'sanfrancisco49ers': 'SF', '49ers': 'SF',
    'gb': 'GB', 'greenbaypackers': 'GB', 'packers': 'GB',
    'den': 'DEN', 'denverbroncos': 'DEN', 'broncos': 'DEN',
    'sea': 'SEA', 'seattleseahawks': 'SEA', 'seahawks': 'SEA',
    'bal': 'BAL', 'baltimoreravens': 'BAL', 'ravens': 'BAL',
    'cin': 'CIN', 'cincinnatibengals': 'CIN', 'bengals': 'CIN',
    'buf': 'BUF', 'buffalobills': 'BUF', 'bills': 'BUF',
    'mia': 'MIA', 'miamidolphins': 'MIA', 'dolphins': 'MIA',
    'ne': 'NE', 'newenglandpatriots': 'NE', 'patriots': 'NE',
    'nyj': 'NYJ', 'newyorkjets': 'NYJ', 'jets': 'NYJ',
    'pit': 'PIT', 'pittsburghsteelers': 'PIT', 'steelers': 'PIT',
    'cle': 'CLE', 'clevelandbrowns': 'CLE', 'browns': 'CLE',
    'hou': 'HOU', 'houstontexans': 'HOU', 'texans': 'HOU',
    'jax': 'JAX', 'jacksonvillejaguars': 'JAX', 'jaguars': 'JAX',
    'ten': 'TEN', 'tennesseetitans': 'TEN', 'titans': 'TEN',
    'lv': 'LV', 'lasvegasraiders': 'LV', 'raiders': 'LV',
    'lac': 'LAC', 'losangeleschargers': 'LAC', 'chargers': 'LAC',
    'chi': 'CHI', 'chicagobears': 'CHI', 'bears': 'CHI',
    'det': 'DET', 'detroitlions': 'DET', 'lions': 'DET',
    'min': 'MIN', 'minnesotavikings': 'MIN', 'vikings': 'MIN',
    'atl': 'ATL', 'atlantafalcons': 'ATL', 'falcons': 'ATL',
    'car': 'CAR', 'carolinapanthers': 'CAR', 'panthers': 'CAR',
    'no': 'NO', 'neworleanssaints': 'NO', 'saints': 'NO',
    'tb': 'TB', 'tampabaybuccaneers': 'TB', 'buccaneers': 'TB', 'bucs': 'TB',
    'ari': 'ARI', 'arizonacardinals': 'ARI', 'cardinals': 'ARI',
    'was': 'WAS', 'washingtoncommanders': 'WAS', 'commanders': 'WAS',

    # MLB
    'cws': 'CWS', 'chicagowhitesox': 'CWS', 'whitesox': 'CWS',
    'nyy': 'NYY', 'newyorkyankees': 'NYY', 'yankees': 'NYY',
    'nym': 'NYM', 'newyorkmets': 'NYM', 'mets': 'NYM',
    'lad': 'LAD', 'losangelesdodgers': 'LAD', 'dodgers': 'LAD',
    'bos': 'BOS', 'bostonredsox': 'BOS', 'redsox': 'BOS',
    'chc': 'CHC', 'chicagocubs': 'CHC', 'cubs': 'CHC',
    'sd': 'SD', 'sandiegopadres': 'SD', 'padres': 'SD',
    'tex': 'TEX', 'texasrangers': 'TEX', 'rangers': 'TEX',
    'tor': 'TOR', 'torontobluejays': 'TOR', 'bluejays': 'TOR',

    # NBA
    'okc': 'OKC', 'oklahomacitythunder': 'OKC', 'thunder': 'OKC',
    'sas': 'SAS', 'sanantoniospurs': 'SAS', 'spurs': 'SAS',
    'lal': 'LAL', 'losangeleslakers': 'LAL', 'lakers': 'LAL',
    'gsw': 'GSW', 'goldenstatewarriors': 'GSW', 'warriors': 'GSW',
    'nyk': 'NYK', 'newyorkknicks': 'NYK', 'knicks': 'NYK',
    'mil': 'MIL', 'milwaukeebucks': 'MIL', 'bucks': 'MIL',
    'phx': 'PHX', 'phoenixsuns': 'PHX', 'suns': 'PHX',
}

def cents_to_american_odds(cents: float) -> str:
    """Convert probability price in cents (1-99) to standard American odds format."""
    try:
        p = float(cents)
        if p <= 0 or p >= 100:
            return "EVEN"
        if p == 50:
            return "+100"
        if p > 50:
            odds = round(-(p / (100.0 - p)) * 100)
            return str(odds)
        else:
            odds = round(((100.0 - p) / p) * 100)
            return f"+{odds}"
    except (ValueError, TypeError):
        return "EVEN"

def real_price_cents(market: Dict[str, Any]) -> Optional[int]:
    """Calculate effective market price in cents based on orderbook/trade signals."""
    last = market.get('last_price_dollars')
    bid = market.get('yes_bid_dollars')
    ask = market.get('yes_ask_dollars')
    prev = market.get('previous_price_dollars')

    try:
        if last is not None and 0 < float(last) < 1.0:
            return round(float(last) * 100)
        if bid is not None and ask is not None and float(bid) > 0 and float(ask) > 0:
            return round(((float(bid) + float(ask)) / 2.0) * 100)
        if bid is not None and 0 < float(bid) < 1.0:
            return round(float(bid) * 100)
        if ask is not None and 0 < float(ask) < 1.0:
            return round(float(ask) * 100)
        if prev is not None and 0 < float(prev) < 1.0:
            return round(float(prev) * 100)
    except (ValueError, TypeError):
        pass
    return None

def normalize_team(code_or_name: str) -> str:
    """Normalize a team string into a clean uppercase ticker."""
    if not code_or_name:
        return 'UNKNOWN'
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', str(code_or_name)).lower()
    return TEAM_MAP.get(cleaned, str(code_or_name).upper())

def normalize_market(raw_market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize a raw Kalshi or sportsbook market item into standard sports data schema.
    """
    ticker = raw_market.get('ticker', '')
    title = raw_market.get('title', '')
    sub_title = raw_market.get('yes_sub_title', '') or title
    event_ticker = raw_market.get('event_ticker', '')
    league = raw_market.get('_league') or 'GENERAL'
    sport_map = {
        'NFL': 'football', 'NCAAF': 'football',
        'NBA': 'basketball', 'NCAAB': 'basketball', 'WNBA': 'basketball',
        'MLB': 'baseball', 'NHL': 'hockey'
    }
    sport = raw_market.get('_sport') or sport_map.get(league, 'general')
    kind = raw_market.get('_kind') or 'game'
    stat = raw_market.get('_stat')

    yes_cents = real_price_cents(raw_market)
    if yes_cents is None:
        return None

    no_cents = 100 - yes_cents
    american_odds = cents_to_american_odds(yes_cents)
    implied_prob = round(yes_cents / 100.0, 4)

    # Parse spread/total line if present
    strike_line = raw_market.get('floor_strike')
    if strike_line is None:
        strike_line = raw_market.get('cap_strike')

    line_value = float(strike_line) if strike_line is not None else None

    # Determine teams from ticker or title
    ticker_parts = ticker.split('-')
    team_code = ticker_parts[-1] if len(ticker_parts) >= 3 else ''
    normalized_team_code = normalize_team(team_code)

    return {
        'id': ticker,
        'ticker': ticker,
        'event_ticker': event_ticker,
        'league': league,
        'sport': sport,
        'market_kind': kind,
        'stat_category': stat,
        'title': title,
        'team_or_selection': sub_title,
        'team_code': normalized_team_code,
        'yes_cents': yes_cents,
        'no_cents': no_cents,
        'american_odds': american_odds,
        'implied_prob': implied_prob,
        'line_value': line_value,
        'volume': float(raw_market.get('volume_fp') or 0),
        'status': raw_market.get('status', 'open'),
        'open_time': raw_market.get('open_time'),
        'close_time': raw_market.get('close_time'),
        'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def create_snapshot(normalized_records: List[Dict[str, Any]], elapsed_sec: float) -> Dict[str, Any]:
    """Package normalized market records into a clean database snapshot."""
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    leagues = sorted(list({r['league'] for r in normalized_records}))

    return {
        'snapshot_id': f"snap_{int(datetime.datetime.now().timestamp())}",
        'timestamp': now_utc,
        'total_markets_processed': len(normalized_records),
        'leagues_covered': leagues,
        'execution_latency_ms': round(elapsed_sec * 1000, 2),
        'records': normalized_records
    }
