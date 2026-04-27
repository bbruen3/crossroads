from abc import ABC, abstractmethod
from app.models import PipeResult

class BasePipe(ABC):
    name: str = ""
    triggers: list = []
    domains: list = []
    requires_auth: bool = False
    supports_action: bool = False
    cache_ttl: int = 300
    timeout_seconds: int = 10

    @abstractmethod
    async def can_handle(self, query: str, context: dict) -> float:
        pass

    @abstractmethod
    async def fetch(self, query: str, context: dict) -> PipeResult:
        pass

    async def act(self, intent: dict, context: dict) -> PipeResult:
        raise NotImplementedError(f"{self.name} does not support actions")
