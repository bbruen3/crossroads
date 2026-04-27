from app.models import CrossroadsRequest

async def recall(request: CrossroadsRequest, config: dict) -> CrossroadsRequest:
    # TODO: query Hindsight API and score results
    # High confidence -> enriched_system
    # Low confidence -> candidate_context
    # Set memory_sufficient if recall is sufficient to answer
    return request

async def extract(user_message: str, assistant_response: str, config: dict) -> None:
    # TODO: send completed turn to Hindsight for extraction
    pass
