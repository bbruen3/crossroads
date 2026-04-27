import re
import json
import time

BLOCK_PATTERN = re.compile(r'<!-- crossroads\n(.*?)\n-->', re.DOTALL)

def parse(response: str) -> dict:
    match = BLOCK_PATTERN.search(response)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception:
        return {}

def evaluate_entry(entry: dict, stale_threshold_pct: float = 0.1) -> str:
    now = int(time.time())
    injected_at = entry.get("injected_at", 0)
    ttl = entry.get("ttl", 300)
    age = now - injected_at
    remaining = ttl - age
    stale_threshold = ttl * stale_threshold_pct
    
    if remaining <= 0:
        return "expired"
    elif remaining <= stale_threshold:
        return "stale"
    return "fresh"

def build(pipes: dict, pending_actions: list = None) -> str:
    payload = {
        "pipes": pipes,
        "actions_pending": pending_actions or []
    }
    return f"\n<!-- crossroads\n{json.dumps(payload)}\n-->"

def strip(response: str) -> str:
    return BLOCK_PATTERN.sub('', response).rstrip()
