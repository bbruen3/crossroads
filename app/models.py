from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass
class CrossroadsRequest:
    original_messages: list
    current_message: str
    conversation_history: list
    model_requested: str
    parameters: dict
    enriched_system: str = ""
    candidate_context: list = field(default_factory=list)
    user_context: dict = field(default_factory=dict)
    memory_sufficient: bool = False
    fingerprint: str = ""

@dataclass
class Intent:
    primary: str
    secondary: list = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    confidence: float = 0.0
    urls: list = field(default_factory=list)
    requires_action: bool = False
    action_type: str = ""
    skip_pipes: bool = False
    model_hint: str = "default"

@dataclass
class PipeResult:
    pipe_name: str
    content: str
    confidence: float = 0.0
    relevance_score: float = 0.0
    sources: list = field(default_factory=list)
    requires_confirmation: bool = False
    cache_ttl: int = 300

@dataclass
class ScoredResult:
    pipe_result: PipeResult
    pipe_confidence: float
    relevance_score: float
    final_score: float
    tokens: int

@dataclass
class MergerOutput:
    system_context: str = ""
    candidate_context: str = ""
    source_status: str = ""
    pending_actions: list = field(default_factory=list)
    total_tokens: int = 0
    scores: list = field(default_factory=list)

@dataclass
class InjectorOutput:
    messages: list
    model_service: str
    model_name: str
    parameters: dict
    total_tokens: int = 0
    history_turns_trimmed: int = 0
    hindsight_extractions: int = 0
    pending_actions: list = field(default_factory=list)
    fingerprint: str = ""

@dataclass
class RequestLog:
    request_id: str
    timestamp: str
    user: str
    original_message: str
    intent: Optional[Any]
    pipes_fired: list = field(default_factory=list)
    pipes_failed: list = field(default_factory=list)
    model_service: str = ""
    model_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cache_hit: bool = False
    history_trimmed: int = 0
    hindsight_extractions: int = 0
