import re
from app.models import Intent

RULES = [
    (re.compile(r'\b(weather|forecast|temperature|rain|snow)\b', re.I), 'weather'),
    (re.compile(r'\br/\w+\b|reddit\.com', re.I), 'reddit'),
    (re.compile(r'github\.com/[\w\-]+/[\w\-]+', re.I), 'github'),
    (re.compile(r'\b(play|queue|skip|pause)\b.{0,30}\b(song|track|music|album)\b', re.I), 'music_action'),
    (re.compile(r'\b(add|find|get)\b.{0,30}\b(movie|show|series|episode)\b', re.I), 'media_action'),
    (re.compile(r'\b(news|headlines|latest)\b', re.I), 'news'),
    (re.compile(r'\b(stock|ticker|market|shares|crypto)\b', re.I), 'financial'),
]

def classify(message: str) -> Intent | None:
    matches = []
    for pattern, intent_name in RULES:
        if pattern.search(message):
            matches.append(intent_name)
    
    if not matches:
        return None
    
    if len(matches) == 1:
        return Intent(primary=matches[0], confidence=0.95)
    
    # Multiple matches = multi_intent
    return Intent(primary='multi_intent', confidence=0.95, secondary=matches)
