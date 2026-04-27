from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/refresh-models")
async def refresh_models():
    # TODO: invalidate model cache and re-fetch from all services
    return {"status": "refreshed"}

@router.get("/pipes")
async def list_pipes():
    from app.pipes.registry import all_pipes
    return {"pipes": [p.name for p in all_pipes()]}

@router.get("/config")
async def show_config():
    from app.config import get_config
    return get_config()
