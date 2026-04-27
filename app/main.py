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
    
    # Parse service prefix
    parts = model_id.split("/", 1)
    if len(parts) != 2:
        return JSONResponse({"error": f"Invalid model format: {model_id}"}, status_code=400)
    
    service_name, model_name = parts[0], parts[1]
    
    # Find service config
    service = next(
        (s for s in cfg.get("model_services", []) if s["name"] == service_name),
        None
    )
    
    if not service:
        return JSONResponse({"error": f"Unknown service: {service_name}"}, status_code=404)
    
    # Forward request with original model name (no prefix)
    forward_body = {**body, "model": model_name}
    
    headers = {"Content-Type": "application/json"}
    api_key = service.get("api_key", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    base_url = service["base_url"]
    is_streaming = body.get("stream", False)
    
    if is_streaming:
        from fastapi.responses import StreamingResponse
        
        async def stream_generator():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    json=forward_body,
                    headers=headers,
                    timeout=120.0
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream"
        )
    else:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                json=forward_body,
                headers=headers,
                timeout=120.0
            )
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
