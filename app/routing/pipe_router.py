from app.models import Intent, RouterOutput
import asyncio

async def route(intent: Intent, config: dict) -> dict:
    # TODO: resolve pipes from registry based on intent
    # Execute in tiers: A (always_on) -> B (intent-matched) -> C (crawl)
    # Parallel execution within tiers
    # Dependency graph resolution
    return {
        "tier_a_results": [],
        "tier_b_results": [],
        "tier_c_results": [],
        "failed_pipes": [],
        "timed_out_pipes": [],
        "execution_time_ms": 0,
    }
