import base64, json, mimetypes, urllib.request, urllib.error
from pathlib import Path
from nexus_ai.adapters.base import BaseAdapter, ProviderUnavailable, AdapterError, require_loopback_url

class LlamaCppVisionAdapter(BaseAdapter):
    provider_id="llama.cpp-vision"
    supported_modalities=("vision",)
    def __init__(self,base_url,model_id,timeout_seconds=180):
        super().__init__(model_id,timeout_seconds); self.base_url=require_loopback_url(base_url)
    def _request(self,path,payload=None,timeout=5):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(self.base_url+path,data=data,headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response: return json.loads(response.read().decode())
        except (urllib.error.URLError,TimeoutError,OSError) as exc: raise ProviderUnavailable(f"Vision endpoint unavailable: {exc}") from exc
        except (ValueError,UnicodeDecodeError) as exc: raise AdapterError(f"Invalid endpoint JSON: {exc}") from exc
    def health(self):
        return {"available":True,"provider":self.provider_id,"model_id":self.model_id,
                "response":self._request("/health",timeout=min(5,self.timeout_seconds))}
    def execute(self,task):
        image_path=task.inputs.get("image_path")
        if not image_path: raise AdapterError("inputs.image_path is required")
        path=Path(image_path)
        if not path.is_file() or path.stat().st_size==0: raise AdapterError("image_path missing or empty")
        if path.stat().st_size>20*1024*1024: raise AdapterError("Image exceeds 20 MB safety limit")
        mime=mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime not in ("image/png","image/jpeg","image/webp","image/gif"): raise AdapterError("Unsupported image MIME type")
        encoded=base64.b64encode(path.read_bytes()).decode("ascii")
        data_url=f"data:{mime};base64,{encoded}"
        payload={"model":self.model_id,"messages":[{"role":"user","content":[
            {"type":"text","text":task.prompt},{"type":"image_url","image_url":{"url":data_url}}]}],
            "max_tokens":int(task.constraints.get("max_tokens",512))}
        data=self._request("/v1/chat/completions",payload,min(task.timeout_seconds,self.timeout_seconds))
        try: answer=data["choices"][0]["message"]["content"]
        except (KeyError,IndexError,TypeError) as exc: raise AdapterError("Vision response missing message content") from exc
        if not isinstance(answer,str) or not answer.strip(): raise AdapterError("Vision model returned empty content")
        return {"text":answer,"served_model":data.get("model",self.model_id),"usage":data.get("usage",{})}
