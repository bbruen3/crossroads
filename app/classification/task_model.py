from app.models import Intent

async def classify(message: str, config: dict) -> Intent:
    # TODO: call task model via oMLX API
    # Prompt constrains output to category list + entities + confidence JSON
    # Falls back to loaded main model if task model unavailable
    return Intent(primary='web_search', confidence=0.5)
