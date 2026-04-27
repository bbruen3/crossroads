import re
from app.models import Intent

# Hard rules: (compiled_pattern, intent, confidence)
# Order matters -- first match wins for single intent
# Patterns are checked for multi-intent separately
RULES = [
    # Weather
    (re.compile(r'\b(weather|forecast|temperature|rain|snow|humidity|wind|storm|sunny|cloudy|UV index)\b', re.I), 'weather', 0.95),
    
    # News
    (re.compile(r'\b(news|headlines|latest|breaking|today\'s|current events)\b', re.I), 'news', 0.90),
    
    # Music actions
    (re.compile(r'\b(play|queue|skip|pause|resume|shuffle|repeat)\b.{0,40}\b(song|track|music|album|artist|playlist)\b', re.I), 'music_action', 0.95),
    
    # Music queries
    (re.compile(r'\b(what(\'s| is) (playing|on)|now playing|last played|scrobble|listen history)\b', re.I), 'music_query', 0.90),
    
    # Media actions
    (re.compile(r'\b(add|find|get|download|grab|request)\b.{0,40}\b(movie|film|show|series|episode|season|documentary|watchlist)\b', re.I), 'media_action', 0.90),
    
    # Media actions
    (re.compile(r'\b(watchlist|watch list)\b', re.I), 'media_action', 0.90),
    
    # Media queries
    (re.compile(r'\b(what(\'s| is) (on|available)|recommend|suggest).{0,40}\b(watch|movie|show|film)\b', re.I), 'media_query', 0.85),
    
    # Homelab
    (re.compile(r'\b(NAS|docker|compose|container|plex|sonarr|radarr|lidarr|prowlarr|qbittorrent|gluetun|tailscale|homelab|server|service)\b', re.I), 'homelab', 0.85),
    
    # GitHub
    (re.compile(r'github\.com/[\w\-]+|gh\s+\w+|\bpull request\b|\bPR\b|\bissue\b.{0,20}\brepo\b', re.I), 'github', 0.95),
    
    # Packages
    (re.compile(r'\b(pip install|npm install|brew install|apt install|cargo add|pypi|npmjs)\b', re.I), 'packages', 0.95),
    
    # Docker
    (re.compile(r'\b(dockerfile|docker-compose|docker compose|docker run|docker pull|container|image)\b', re.I), 'docker', 0.90),
    
    # Financial
    (re.compile(r'\b(stock|ticker|share price|market cap|crypto|bitcoin|ETF|dividend|earnings|S&P|nasdaq|NYSE)\b', re.I), 'financial', 0.90),
    
    # Sports
    (re.compile(r'\b(score|standings|game|match|vs|versus|roster|playoff|championship|league|NBA|NFL|MLB|NHL|EPL|F1)\b', re.I), 'sports', 0.85),
    
    # Calendar queries
    (re.compile(r'\b(what(\'s| is) on my (calendar|schedule)|do i have|am i (free|busy)|upcoming events)\b', re.I), 'calendar_query', 0.90),
    
    # Calendar actions
    (re.compile(r'\b(schedule|add to calendar|create event|block|remind me|set a reminder)\b', re.I), 'calendar_action', 0.85),
    
    # Notify
    (re.compile(r'\b(send (me |a )?(notification|alert|push|message)|notify me|ping me)\b', re.I), 'notify', 0.90),
    
    # Code
    (re.compile(r'\b(write|debug|fix|refactor|explain|review)\b.{0,30}\b(code|function|class|script|module|bug|error)\b', re.I), 'code', 0.85),
    
    # Reasoning
    (re.compile(r'\b(think through|analyze|evaluate|compare|pros and cons|trade.?offs|should I|is it worth)\b', re.I), 'reasoning', 0.80),
    
    # Wikipedia/reference
    (re.compile(r'\b(what is|who is|who was|what was|define|definition of|history of|explain)\b.{0,40}\b\w+\b', re.I), 'wikipedia', 0.60),  # low confidence, broad
    
    # Security
    (re.compile(r'\b(CVE|vulnerability|exploit|patch|firewall|VPN|encryption|SSL|TLS|certificate)\b', re.I), 'security', 0.90),
]

# Intents that are conversational by nature -- skip pipes
CONVERSATIONAL_PATTERNS = [
    re.compile(r'^(hi|hello|hey|good (morning|afternoon|evening)|thanks|thank you|ok|okay|sure|got it|sounds good|great|perfect|nice|cool)\b', re.I),
    re.compile(r'^(yes|no|maybe|I (see|understand|agree|disagree))\b', re.I),
]


def classify(message: str) -> Intent | None:
    """
    Attempt hard-rule classification. Returns Intent if confident match found,
    None if ambiguous or no match (falls through to task model).
    """
    
    # Check conversational first
    for pattern in CONVERSATIONAL_PATTERNS:
        if pattern.match(message.strip()):
            return Intent(
                primary='conversational',
                confidence=0.95,
                skip_pipes=True,
            )
    
    # Collect all matches
    matches = []
    for pattern, intent_name, confidence in RULES:
        if pattern.search(message):
            matches.append((intent_name, confidence))
    
    if not matches:
        return None  # No match -- fall through to task model
    
    if len(matches) == 1:
        intent_name, confidence = matches[0]
        return Intent(primary=intent_name, confidence=confidence)
    
    # Multiple matches -- check if they're compatible or truly multi-intent
    intents = [m[0] for m in matches]
    avg_confidence = sum(m[1] for m in matches) / len(matches)
    
    # Some combinations are naturally co-occurring, not true multi-intent
    # e.g. homelab + docker is still just homelab
    SUBSUMES = {
        'homelab': {'docker'},
        'code': {'github'},
    }
    
    filtered = list(intents)
    for primary, subsumed in SUBSUMES.items():
        if primary in filtered:
            filtered = [i for i in filtered if i not in subsumed or i == primary]
    
    if len(filtered) == 1:
        return Intent(primary=filtered[0], confidence=avg_confidence)
    
    # Genuine multi-intent
    return Intent(
        primary='multi_intent',
        confidence=avg_confidence,
        secondary=filtered,
    )