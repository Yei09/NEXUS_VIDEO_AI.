import json, os, platform, shutil
from pathlib import Path

def _memory_mb():
    """Return (total, available) RAM in MiB on Linux, Windows and POSIX hosts."""
    if Path("/proc/meminfo").exists():
        values={}
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                key,raw=line.split(":",1)
                if key in ("MemTotal","MemAvailable","MemFree","Buffers","Cached"):
                    values[key]=int(raw.strip().split()[0])
            total=values.get("MemTotal")
            available=values.get("MemAvailable")
            if available is None:
                available=values.get("MemFree",0)+values.get("Buffers",0)+values.get("Cached",0)
            return (round(total/1024) if total else None,
                    round(available/1024) if available else None)
        except (OSError,ValueError,IndexError):
            pass
    if os.name=="nt":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),
                          ("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),
                          ("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),
                          ("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),
                          ("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
            status=MEMORYSTATUSEX(); status.dwLength=ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullTotalPhys/1024**2),round(status.ullAvailPhys/1024**2)
        except Exception:
            pass
    try:
        page=os.sysconf("SC_PAGE_SIZE")
        total=page*os.sysconf("SC_PHYS_PAGES")
        available=page*os.sysconf("SC_AVPHYS_PAGES")
        return round(total/1024**2),round(available/1024**2)
    except (AttributeError,OSError,ValueError):
        return None,None

def snapshot(path="."):
    disk=shutil.disk_usage(path); total,available=_memory_mb()
    return {"platform":platform.platform(),"machine":platform.machine(),
            "cpu_count_logical":os.cpu_count(),"ram_total_mb":total,
            "ram_available_mb":available,"disk_total_gb":round(disk.total/1024**3,2),
            "disk_free_gb":round(disk.free/1024**3,2),
            "measurement_scope":"current execution host only; not the user's personal computer"}

if __name__=="__main__": print(json.dumps(snapshot(),indent=2))
