import httpx
from datetime import datetime, timezone
from app.models import CrossroadsRequest

HINDSIGHT_BASE = "http://hindsight:8888"
BANK_ID = "bbruen3"
RECALL_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{BANK_ID}/memories/recall"
RETAIN_URL = f"{HINDSIGHT_BASE}/v1/default/banks/{BANK_ID}/memories"

# Relevance score threshold for high vs low confidence memories
HIGH_CONFIDENCE_THRESHOLD = 0.75


async def recall(request: CrossroadsRequest, config: dict) -> CrossroadsRequest:
    """Query Hindsight for relevant memories and inject into request context."""
    hindsight_cfg = config.get("hindsight", {})
    top_k = hindsight_cfg.get("recall_top_k", 10)
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                RECALL_URL,
                json={"query": request.current_message, "top_k": top_k}
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"DEBUG hindsight recall error: {e}")
        return request
    
    results = data.get("results", [])
    if not results:
        return request
    
    # Deduplicate by text content
    seen_texts = set()
    unique_results = []
    for r in results:
        text = r.get("text", "").strip()
        if text and text not in seen_texts:
            seen_texts.add(text)
            unique_results.append(r)
    
    # Split into high and low confidence based on type
    # world/experience types tend to be more synthesized and reliable
    high_confidence = []
    low_confidence = []
    
    for r in unique_results:
        memory_type = r.get("type", "")
        if memory_type in ("world", "experience"):
            high_confidence.append(r)
        else:
            low_confidence.append(r)
    
    # Build high confidence block for system prompt
    if high_confidence:
        memory_lines = [f"- {r['text']}" for r in high_confidence]
        memory_block = "## Memory\n" + "\n".join(memory_lines)
        request.enriched_system = (request.enriched_system + f"\n\n{memory_block}").strip()
    
    # Add low confidence to candidate context
    for r in low_confidence:
        request.candidate_context.append({
            "source": "hindsight",
            "text": r["text"],
            "type": r.get("type"),
            "context": r.get("context"),
        })
    
    # If memories are sufficient to answer without pipes, flag it
    # Simple heuristic: if we have high confidence memories, let classification decide
    # Don't set memory_sufficient here -- leave that to classification layer
    
    return request


async def extract(
    user_message: str,
    assistant_response: str,
    conversation_id: str,
    config: dict
) -> None:
    """Extract and retain memories from a completed conversation turn."""
    hindsight_cfg = config.get("hindsight", {})
    
    if not hindsight_cfg.get("extract_enabled", True):
        return
    
    # Build content from the turn
    content = f"User: {user_message}\nAssistant: {assistant_response}"
    
    item = {
        "content": content,
        "document_id": f"turn_{conversation_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "context": "conversation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "update_mode": "replace",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                RETAIN_URL,
                json={"items": [item], "async": True}
            )
            resp.raise_for_status()
    except Exception as e:
        print(f"DEBUG hindsight extract error: {e}")