from dataclasses import dataclass, field, asdict
from typing import Any
import time, uuid

@dataclass
class Task:
    modality: str
    prompt: str
    inputs: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 120.0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    def validate(self):
        if not isinstance(self.modality, str) or not self.modality:
            raise ValueError("modality is required")
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not 0 < float(self.timeout_seconds) <= 3600:
            raise ValueError("timeout_seconds must be in (0, 3600]")
        if not isinstance(self.inputs, dict) or not isinstance(self.constraints, dict):
            raise ValueError("inputs and constraints must be objects")

@dataclass
class ProviderResult:
    ok: bool
    provider_id: str
    model_id: str
    modality: str
    request_id: str
    output: Any = None
    error: str | None = None
    elapsed_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    def to_dict(self):
        return asdict(self)
