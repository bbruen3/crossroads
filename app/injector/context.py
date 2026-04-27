from app.models import CrossroadsRequest, MergerOutput, InjectorOutput

async def assemble(
    request: CrossroadsRequest,
    merger_output: MergerOutput,
    model_service: str,
    model_name: str,
    config: dict
) -> InjectorOutput:
    
    # Assemble system prompt
    system_parts = []
    
    base_prompt = config.get("global_system_prompt", "")
    if base_prompt:
        system_parts.append(base_prompt)
    
    if request.enriched_system:
        system_parts.append(request.enriched_system)
    
    if merger_output.system_context:
        system_parts.append(merger_output.system_context)
    
    if merger_output.source_status:
        system_parts.append(merger_output.source_status)
    
    assembled_system = "\n\n".join(filter(None, system_parts))
    
    # Build messages array
    messages = [{"role": "system", "content": assembled_system}]
    
    if merger_output.candidate_context:
        messages.append({
            "role": "assistant",
            "content": f"## Additional Context\n{merger_output.candidate_context}"
        })
    
    # Add history (trimming TODO)
    messages.extend(request.conversation_history)
    
    # Current message always last, always unchanged
    messages.append({"role": "user", "content": request.current_message})
    
    return InjectorOutput(
        messages=messages,
        model_service=model_service,
        model_name=model_name,
        parameters=request.parameters,
        pending_actions=merger_output.pending_actions,
        fingerprint=request.fingerprint,
    )
