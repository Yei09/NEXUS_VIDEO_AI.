import json, os, platform, shutil
from pathlib import Path

def snapshot(path="."):
    disk=shutil.disk_usage(path); ram=None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"): ram=round(int(line.split()[1])/1024); break
    except (OSError,ValueError,IndexError): pass
    return {"platform":platform.platform(),"machine":platform.machine(),"cpu_count_logical":os.cpu_count(),
            "ram_total_mb":ram,"disk_total_gb":round(disk.total/1024**3,2),
            "disk_free_gb":round(disk.free/1024**3,2),
            "measurement_scope":"current execution host only; not the user's personal computer"}
if __name__=="__main__": print(json.dumps(snapshot(),indent=2))
