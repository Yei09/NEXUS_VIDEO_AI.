import json, os, time
from pathlib import Path
from threading import Lock

class EvolutionMemory:
    def __init__(self,root="evolution"):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.events=self.root/"history.jsonl"; self.state=self.root/"state.json"; self.lock=Lock()
        if not self.state.exists(): self.save_state({"schema_version":1,"status":"READY","current_cycle":None,"next_objective":"Run multimodel core tests","models":{}})
    def record(self,event_type,payload):
        event={"timestamp":time.time(),"type":event_type,"payload":payload}
        with self.lock,self.events.open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(event,ensure_ascii=False,sort_keys=True)+"\n"); stream.flush(); os.fsync(stream.fileno())
        return event
    def save_state(self,state):
        value=dict(state); value["last_updated"]=time.time()
        temp=self.state.with_suffix(".json.tmp"); temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8"); temp.replace(self.state)
        return value
    def load_state(self): return json.loads(self.state.read_text(encoding="utf-8"))
    def recover(self):
        count=0
        if self.events.exists():
            with self.events.open(encoding="utf-8") as stream:
                for line in stream:
                    if line.strip(): json.loads(line); count+=1
        return {"state":self.load_state(),"events_validated":count,"journal":str(self.events)}
