# Hardware and resource report

## CI host measurement
Latest successful GitHub Actions run 44446367711 measured the hosted Linux runner:
- OS/platform: Linux x86_64
- Logical CPUs: 4
- Total RAM: 15,983 MB
- Available RAM: recorded by the hardware probe
- Disk: 144.35 GB total, 87.19 GB free

This is the temporary GitHub-hosted runner, **not the user's personal development computer**.

## Personal computer measurement
Run on the target host:
python -m nexus_ai.cli hardware

The probe supports Linux procfs, Windows GlobalMemoryStatusEx and POSIX sysconf where available. It reports total/available RAM, OS, architecture, logical CPU count and disk space.

The runtime reserves 2 GB from measured available RAM when setting the default model-selection ceiling. If RAM cannot be measured, the safe default is zero, so no model is automatically selected. The user can supply a stricter memory ceiling through the runtime policy; paid and remote access remain disabled.

For a real model benchmark, record peak resident memory, CPU utilization, latency, context length, quantization and model file size during a representative task.

## Conservative model guidance
- Qwen2.5-1.5B GGUF Q4_K_M is the first candidate only after checking disk/RAM; no download occurs automatically.
- Qwen3-4B waits for a measured hardware report.
- Qwen2.5-VL-3B GGUF has an 8 GB planning floor; do not install on low-memory hardware without measurement.
- FLUX.1 schnell is not recommended for an unknown low-memory PC; do not download without checking GPU/RAM/disk.
- Kokoro is relatively small by parameter count, but runtime, phonemizer and voice packs add dependencies.
- Blender/FFmpeg resource use depends on scene, resolution, samples, codec and filters.

All catalog figures are planning estimates, not measured minimum requirements.
