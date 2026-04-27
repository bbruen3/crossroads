import json
import logging
import urllib.request
import urllib.error

def _post(url: str, payload: dict, api_key: str = "", timeout: int = 30) -> dict:
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get_task_model_config(config: dict) -> tuple[str, str, str]:
    """Returns (base_url, model_name, api_key) for the task model service."""
    task_cfg = config.get("task_model", {})
    service_name = task_cfg.get("service", "omlx")
    model_name = task_cfg.get("model", "")
    
    service = next(
        (s for s in config.get("model_services", []) if s["name"] == service_name),
        None
    )
    if not service:
        raise ValueError(f"Task model service '{service_name}' not found")
    
    return service["base_url"], model_name, service.get("api_key", "")


EXTRACTION_PROMPT = """Analyze this conversation turn. Determine if the assistant response contains factual information worth storing as a memory about the user, their environment, preferences, projects, or infrastructure.

Return ONLY a JSON object with no other text:
{{"worth_extracting": true/false, "reason": "brief reason"}}

Rules:
- true if: response contains facts about user's setup, preferences, decisions, infrastructure, or projects
- false if: response is a refusal, error, generic answer, code execution output, or contains no user-specific facts
- false if: response says the assistant "cannot", "doesn't have access", or "is unable to"

User message: {user_message}

Assistant response: {assistant_response}

JSON:"""


def classify_turn_worth_extracting(
    user_message: str,
    assistant_response: str,
    config: dict
) -> bool:
    try:
        base_url, model_name, api_key = _get_task_model_config(config)
    except ValueError as e:
        logging.warning(f"Task model config error: {e}")
        return False

    prompt = EXTRACTION_PROMPT.format(
        user_message=user_message[:500],
        assistant_response=assistant_response[:1000]
    )

    try:
        result = _post(
            f"{base_url}/chat/completions",
            {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.1,
                "stream": False,
            },
            api_key=api_key,
        )
        
        content = result["choices"][0]["message"]["content"].strip()
        
        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        parsed = json.loads(content.strip())
        worth = parsed.get("worth_extracting", False)
        reason = parsed.get("reason", "")
        logging.info(f"Extraction classification: {worth} -- {reason}")
        return bool(worth)
        
    except Exception as e:
        logging.warning(f"Task model classification error: {e}")
        # Fail closed -- don't extract if classification fails
        return False


def classify_intent(message: str, config: dict) -> dict:
    """
    Classify the intent of a user message.
    Returns structured intent dict.
    Stub -- full implementation in Component 3.
    """
    return {
        "primary": "conversational",
        "confidence": 0.5,
        "secondary": [],
        "entities": {},
        "requires_action": False,
        "model_hint": "default",
    }