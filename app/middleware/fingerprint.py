import hashlib
import json
from app.models import CrossroadsRequest

async def fingerprint_request(request: CrossroadsRequest) -> CrossroadsRequest:
    payload = {
        "message": request.current_message,
        "system": request.enriched_system,
        "model": request.model_requested,
    }
    request.fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:16]
    return request
