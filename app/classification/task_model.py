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


INTENT_CATEGORIES = [
    "web_search", "weather", "news", "wikipedia", "academic", "financial",
    "legal", "sports", "github", "huggingface", "packages", "docker",
    "stackoverflow", "security", "music_query", "music_action", "media_query",
    "media_action", "homelab", "notify", "calendar_query", "calendar_action",
    "send_message", "multi_intent", "memory_sufficient", "conversational",
    "code", "reasoning", "creative",
]

INTENT_PROMPT = """Classify the user message into one or more intents and extract entities.

Available intents: {intents}

Rules:
- Choose the most specific intent(s) that apply
- Use "conversational" for greetings, acknowledgments, small talk
- Use "memory_sufficient" if the question can be answered from personal context alone
- Use "multi_intent" if the message clearly requests multiple distinct things
- confidence: 0.0-1.0 reflecting how certain you are

Return ONLY a JSON object:
{{"primary": "intent_name", "secondary": [], "entities": {{}}, "confidence": 0.0, "requires_action": false, "action_type": "", "model_hint": "default"}}

model_hint options: "default", "code", "reasoning", "simple"

User message: {message}

JSON:"""


def classify_intent(message: str, config: dict) -> dict:
    """
    Use the task model to classify user intent.
    Returns structured intent dict.
    """
    try:
        base_url, model_name, api_key = _get_task_model_config(config)
    except ValueError as e:
        logging.warning(f"Task model config error: {e}")
        return {
            "primary": "web_search",
            "confidence": 0.3,
            "secondary": [],
            "entities": {},
            "requires_action": False,
            "action_type": "",
            "model_hint": "default",
        }
    
    prompt = INTENT_PROMPT.format(
        intents=", ".join(INTENT_CATEGORIES),
        message=message[:500]
    )
    
    try:
        result = _post(
            f"{base_url}/chat/completions",
            {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
                "stream": False,
            },
            api_key=api_key,
        )
        
        content = result["choices"][0]["message"]["content"].strip()
        
        # Strip markdown fences
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        parsed = json.loads(content.strip())
        logging.info(f"Intent classification: {parsed.get('primary')} ({parsed.get('confidence', 0):.2f})")
        return parsed
        
    except Exception as e:
        logging.warning(f"Intent classification error: {e}")
        return {
            "primary": "web_search",
            "confidence": 0.3,
            "secondary": [],
            "entities": {},
            "requires_action": False,
            "action_type": "",
            "model_hint": "default",
        }