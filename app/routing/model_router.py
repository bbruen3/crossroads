from app.models import InjectorOutput

async def select_model(request, config: dict) -> tuple[str, str]:
    """Returns (service_name, model_name)."""
    model_requested = request.model_requested
    
    if model_requested == "crossroads/auto":
        # Apply intent-based routing rules
        rules = config.get("routing_rules", {})
        hint = getattr(request, 'model_hint', 'default')
        rule = rules.get(f"{hint}_model", rules.get("default_model", {}))
        return rule.get("service", "omlx"), rule.get("model", "")
    
    # Honor requested model -- look up service from registry
    for service in config.get("model_services", []):
        for model in service.get("models", []):
            if model.get("name") == model_requested:
                return service["name"], model_requested
    
    # Fallback
    fallback = config.get("routing_rules", {}).get("fallback_model", {})
    return fallback.get("service", "omlx"), fallback.get("model", "")
