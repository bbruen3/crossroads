from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from app.admin.routes import router as admin_router

app = FastAPI(title="Crossroads", version="0.1.0")
app.include_router(admin_router, prefix="/admin")

_config = None

@app.on_event("startup")
async def startup():
    global _config
    from app.config import get_config
    _config = get_config()
    print(f"DEBUG startup: config loaded, services={[s['name'] for s in _config.get('model_services', [])]}")

def config():
    return _config

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/v1/models")
async def list_models():
    cfg = config()
    if cfg is None:
        return {"object": "list", "data": []}
    
    models = []
    
    async with httpx.AsyncClient() as client:
        for service in cfg.get("model_services", []):
            base_url = service["base_url"]
            api_key = service.get("api_key", "")
            exposed = service.get("exposed_models", None)
            
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            try:
                resp = await client.get(
                    f"{base_url}/models",
                    headers=headers,
                    timeout=5.0
                )
                resp.raise_for_status()
                data = resp.json()
                
                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    if exposed and exposed != "all_models":
                        if model_id not in exposed:
                            continue
                    models.append({
                        "id": f"{service['name']}/{model_id}",
                        "object": "model",
                        "created": model.get("created", 0),
                        "owned_by": service["name"],
                    }) 
            except Exception as e:
                print(f"DEBUG service {service.get('name')} error: {e}")
    
    models.append({
        "id": "crossroads/auto",
        "object": "model",
        "owned_by": "crossroads",
    })
    
    return {"object": "list", "data": models}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    cfg = config()
    if cfg is None:
        return JSONResponse({"error": "config not loaded"}, status_code=500)
    
    body = await request.json()
    model_id = body.get("model", "")
    messages = body.get("messages", [])
    
    # Separate system, history, and current message
    system_messages = [m for m in messages if m["role"] == "system"]
    history = [m for m in messages if m["role"] != "system"]
    current_message = history[-1]["content"] if history else ""
    conversation_history = history[:-1]
    
    base_system = system_messages[0]["content"] if system_messages else ""
    
    # Build CrossroadsRequest
    from app.models import CrossroadsRequest
    cr = CrossroadsRequest(
        original_messages=messages,
        current_message=current_message,
        conversation_history=conversation_history,
        model_requested=model_id,
        parameters={k: v for k, v in body.items() if k not in ("model", "messages")},
        enriched_system=base_system,
    )
    
    # Run always-on middleware
    from app.middleware.datetime_inject import inject_datetime
    from app.middleware.fingerprint import fingerprint_request
    from app.middleware.hindsight import recall as hindsight_recall
    cr = await hindsight_recall(cr, cfg)
    cr = await inject_datetime(cr, cfg)
    cr = await fingerprint_request(cr)
    
    # Parse service prefix
    parts = model_id.split("/", 1)
    if len(parts) != 2:
        return JSONResponse({"error": f"Invalid model format: {model_id}"}, status_code=400)
    
    service_name, model_name = parts[0], parts[1]
    
    service = next(
        (s for s in cfg.get("model_services", []) if s["name"] == service_name),
        None
    )
    if not service:
        return JSONResponse({"error": f"Unknown service: {service_name}"}, status_code=404)
    
    # Reassemble messages with enriched system
    forward_messages = []
    if cr.enriched_system:
        forward_messages.append({"role": "system", "content": cr.enriched_system})
    forward_messages.extend(cr.conversation_history)
    forward_messages.append({"role": "user", "content": cr.current_message})
    
    forward_body = {**body, "model": model_name, "messages": forward_messages}
    
    headers = {"Content-Type": "application/json"}
    api_key = service.get("api_key", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    base_url = service["base_url"]
    is_streaming = body.get("stream", False)
    
    if is_streaming:
        from fastapi.responses import StreamingResponse
        import asyncio
        
        async def stream_generator():
            buffer = []
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    json=forward_body,
                    headers=headers,
                    timeout=120.0
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        buffer.append(chunk)
                        yield chunk
            
            # Outlet: extract memories after stream completes
            try:
                from app.middleware.hindsight import extract as hindsight_extract
                full_response = b"".join(buffer).decode("utf-8", errors="ignore")
                # Extract assistant content from SSE chunks
                import re
                content_parts = re.findall(r'"content":"(.*?)"', full_response)
                assistant_text = "".join(content_parts).replace("\\n", "\n")
                if assistant_text:
                    conv_id = cr.parameters.get("conversation_id", "unknown")
                    asyncio.create_task(
                        hindsight_extract(cr.current_message, assistant_text, conv_id, cfg)
                    )
            except Exception as e:
                print(f"DEBUG outlet error: {e}")
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream"
        )