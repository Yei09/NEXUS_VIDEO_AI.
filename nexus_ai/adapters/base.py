from abc import ABC, abstractmethod
from urllib.parse import urlsplit
import time
from nexus_ai.types import ProviderResult

class AdapterError(RuntimeError): pass
class ProviderUnavailable(AdapterError): pass

def require_loopback_url(url):
    """Reject hosted endpoints: this release only permits services on this machine."""
    parsed=urlsplit(url)
    if parsed.scheme not in ("http","https") or parsed.hostname not in ("localhost","127.0.0.1","::1"):
        raise ValueError("Only localhost/loopback provider URLs are allowed by the no-cloud policy")
    if not parsed.port and parsed.scheme=="http": pass
    return url.rstrip("/")

class BaseAdapter(ABC):
    provider_id="abstract"
    supported_modalities=()
    def __init__(self,model_id,timeout_seconds=120):
        if not model_id: raise ValueError("model_id is required")
        self.model_id,self.timeout_seconds=model_id,timeout_seconds
    def supports(self,modality): return modality in self.supported_modalities
    def run(self,task):
        task.validate()
        if not self.supports(task.modality): raise AdapterError(f"{self.provider_id} does not support {task.modality}")
        started=time.monotonic()
        try:
            output=self.execute(task)
            if output is None: raise AdapterError("provider returned empty output")
            return ProviderResult(True,self.provider_id,self.model_id,task.modality,task.request_id,
                                  output=output,elapsed_seconds=time.monotonic()-started)
        except ProviderUnavailable as exc:
            return ProviderResult(False,self.provider_id,self.model_id,task.modality,task.request_id,
                                  error=str(exc),elapsed_seconds=time.monotonic()-started,
                                  metadata={"availability":"unavailable"})
        except Exception as exc:
            return ProviderResult(False,self.provider_id,self.model_id,task.modality,task.request_id,
                                  error=f"{type(exc).__name__}: {exc}",elapsed_seconds=time.monotonic()-started)
    @abstractmethod
    def execute(self,task): raise NotImplementedError
    @abstractmethod
    def health(self): raise NotImplementedError
