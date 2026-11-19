import json, urllib.request, urllib.error
from nexus_ai.adapters.base import BaseAdapter, ProviderUnavailable, AdapterError, require_loopback_url

class LlamaCppAdapter(BaseAdapter):
    provider_id="llama.cpp"
    supported_modalities=("text","code","audit","planning")
    def __init__(self,base_url,model_id,timeout_seconds=120):
        super().__init__(model_id,timeout_seconds); self.base_url=require_loopback_url(base_url)
    def _request(self,path,payload=None,timeout=5):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(self.base_url+path,data=data,headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response: return json.loads(response.read().decode())
        except (urllib.error.URLError,TimeoutError,OSError) as exc: raise ProviderUnavailable(f"llama.cpp endpoint unavailable: {exc}") from exc
        except (ValueError,UnicodeDecodeError) as exc: raise AdapterError(f"Invalid JSON: {exc}") from exc
    def health(self):
        return {"available":True,"provider":self.provider_id,"model_id":self.model_id,
                "response":self._request("/health",timeout=min(5,self.timeout_seconds))}
    def execute(self,task):
        temperature=float(task.constraints.get("temperature",0.7)); max_tokens=int(task.constraints.get("max_tokens",512))
        if not 0<=temperature<=2 or not 1<=max_tokens<=32768: raise AdapterError("Invalid temperature or max_tokens")
        payload={"model":self.model_id,"messages":[{"role":"user","content":task.prompt}],
                 "temperature":temperature,"max_tokens":max_tokens}
        data=self._request("/v1/chat/completions",payload,min(task.timeout_seconds,self.timeout_seconds))
        try: content=data["choices"][0]["message"]["content"]
        except (KeyError,IndexError,TypeError) as exc: raise AdapterError("Missing choices[0].message.content") from exc
        if not isinstance(content,str) or not content.strip(): raise AdapterError("Empty model output")
        return {"text":content,"usage":data.get("usage",{}),"served_model":data.get("model",self.model_id)}
