from dataclasses import dataclass
AGENT_ROLES={
 "director":("planning","text"),"screenwriter":("text",),
 "cinematographer":("text","planning"),"character_designer":("text","image"),
 "environment_designer":("text","image"),"audio_specialist":("text","speech","audio"),
 "programmer":("code","text"),"technical_auditor":("audit","code"),
 "cinematic_evaluator":("vision","audit","text")}
@dataclass
class Agent:
    role:str
    router:object
    @property
    def responsibilities(self): return AGENT_ROLES[self.role]
    def run(self,prompt,modality=None,**kwargs):
        selected=modality or self.responsibilities[0]
        if selected not in self.responsibilities: raise ValueError(f"{self.role} cannot perform {selected}")
        from nexus_ai.types import Task
        return self.router.dispatch(Task(modality=selected,prompt=prompt,**kwargs))
