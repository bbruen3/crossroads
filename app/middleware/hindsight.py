import urllib.request
import urllib.error
import json
from datetime import datetime, timezone
from app.models import CrossroadsRequest
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)

HINDSIGHT_BASE = "http://hindsight:8888"
BANK_ID = "bbruen3"
RECALL_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{BANK_ID}/memories/recall"
RETAIN_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{BANK_ID}/memories"


def _post(url: str, payload: dict, timeout: int = 10) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


async def recall(request: CrossroadsRequest, config: dict) -> CrossroadsRequest:
    logging.info(f"Hindsight recall: querying for '{request.current_message[:50]}'")
    hindsight_cfg = config.get("hindsight", {})
    top_k = hindsight_cfg.get("recall_top_k", 10)
    
    try:
        data = _post(RECALL_URL, {"query": request.current_message, "top_k": top_k})
    except Exception as e:
        import traceback
        logging.debug("hindsight recall type: {type(e).__name__}")
        logging.debug("hindsight recall repr: {repr(e)}")
        traceback.print_exc()
        return request
    
    results = data.get("results", [])
    logging.info(f"Hindsight recall: got {len(results)} results")
    if not results:
        return request
    
    # Deduplicate by text
    seen = set()
    unique = []
    for r in results:
        text = r.get("text", "").strip()
        if text and text not in seen:
            seen.add(text)
            unique.append(r)
    
    # Split high/low confidence by type
    high = [r for r in unique if r.get("type") in ("world", "experience")]
    low = [r for r in unique if r.get("type") not in ("world", "experience")]
    
    logging.info(f"Hindsight: {len(high)} high confidence, {len(low)} low confidence memories")
    logging.info(f"Hindsight high sample: {[r['text'][:50] for r in high[:3]]}")

    if high:
        lines = [f"- {r['text']}" for r in high]
        block = "## Memory\n" + "\n".join(lines)
        request.enriched_system = (request.enriched_system + f"\n\n{block}").strip()
        logging.info(f"Hindsight: injected {len(high)} memories into system prompt")
        logging.info(f"Hindsight system prompt length: {len(request.enriched_system)}")
    
    for r in low:
        request.candidate_context.append({
            "source": "hindsight",
            "text": r["text"],
            "type": r.get("type"),
            "context": r.get("context"),
        })
    
    return request


async def extract(
    user_message: str,
    assistant_response: str,
    conversation_id: str,
    config: dict
) -> None:
    hindsight_cfg = config.get("hindsight", {})
    if not hindsight_cfg.get("extract_enabled", True):
        return
    
    content = f"User: {user_message}\nAssistant: {assistant_response}"
    item = {
        "content": content,
        "document_id": f"turn_{conversation_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "context": "conversation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "update_mode": "replace",
    }
    
    try:
        _post(RETAIN_URL, {"items": [item], "async": True}, timeout=30)
    except Exception as e:
        logging.debug("hindsight extract error: {e}")