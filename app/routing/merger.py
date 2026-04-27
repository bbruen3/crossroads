from app.models import MergerOutput

async def merge(router_output: dict, intent, config: dict) -> MergerOutput:
    # TODO: dedup, relevance score, budget enforcement
    return MergerOutput(
        source_status="Consulted: none"
    )
