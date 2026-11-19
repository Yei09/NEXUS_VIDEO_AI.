from nexus_ai.types import ProviderResult

class Director:
    """Policy-aware selector; only registered, health-checked local adapters are eligible."""
    def __init__(self,registry,adapters,memory=None,policy=None):
        self.registry,self.adapters,self.memory=registry,adapters,memory
        self.policy=policy or {"allow_paid":False,"allow_remote":False,"allow_conditional_api":False,
                               "max_memory_mb":None,"allowed_licenses":[],"max_cost_usd":0.0}
    def _score(self,model,task):
        cost_class=model["potential_cost"]["class"]
        if cost_class=="paid" and not self.policy.get("allow_paid",False): return None
        if cost_class=="api_free_conditional" and not self.policy.get("allow_conditional_api",False): return None
        if model["access_type"].startswith("api") and not self.policy.get("allow_remote",False): return None
        if model.get("availability") in ("unavailable","not_available"): return None
        if model["potential_cost"].get("estimated_usd_per_task",0)>self.policy.get("max_cost_usd",0): return None
        allowed=self.policy.get("allowed_licenses",[])
        if allowed and model["license"] not in allowed: return None
        limit=self.policy.get("max_memory_mb"); need=model.get("hardware",{}).get("ram_mb_min")
        if limit is not None and (need is None or need>limit): return None
        quality=float(model.get("quality",{}).get(task.modality,0))
        speed=float(model.get("speed_score",0))
        return quality+speed*0.15
    def dispatch(self,task):
        task.validate(); candidates=[]
        for model in self.registry.list(task.modality):
            adapter=self.adapters.get(model["id"])
            if adapter is None or not adapter.supports(task.modality): continue
            score=self._score(model,task)
            if score is None: continue
            try: health=adapter.health()
            except Exception: continue
            if health.get("available"): candidates.append((score,model["id"],adapter))
        candidates.sort(key=lambda item:(-item[0],item[1])); attempts=[]
        for score,model_id,adapter in candidates:
            result=adapter.run(task)
            attempts.append({"model_id":model_id,"score":score,"ok":result.ok,"error":result.error})
            if result.ok:
                result.metadata.update({"selection_score":score,"fallback_attempts":attempts[:-1]})
                if self.memory: self.memory.record("provider_result",result.to_dict())
                return result
        result=ProviderResult(False,"nexus-director","none",task.modality,task.request_id,
            error="No available, registered, policy-compliant provider",
            metadata={"attempts":attempts,"fallback_count":len(attempts)})
        if self.memory: self.memory.record("provider_failure",result.to_dict())
        return result
