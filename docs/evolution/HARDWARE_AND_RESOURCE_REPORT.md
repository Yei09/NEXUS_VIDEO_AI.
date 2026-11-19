# Hardware and resource report

## CI host measurement
Latest GitHub Actions run 44446367711 measured the hosted Linux runner:
- OS/platform: Linux x86_64
- Logical CPUs: 4
- Total RAM: 15,983 MB
- Disk: 144.35 GB total, 87.19 GB free

This is the temporary GitHub-hosted runner, **not the user's personal development computer**. It must not be used as the user's hardware profile.

## Personal computer measurement
This repository operation cannot inspect the user's personal PC. Run on the target host:
python -m nexus_ai.cli hardware

The command reports OS, architecture, logical CPU count, total RAM when Linux procfs is available, total disk and free disk. It labels the host measured.

For a real model benchmark, record peak resident memory, CPU utilization, latency, context length, quantization and model file size during a representative task.

## Conservative model guidance
- Qwen2.5-1.5B GGUF Q4_K_M is the first candidate only after checking disk/RAM; no download occurs automatically.
- Qwen3-4B waits for a measured hardware report.
- Qwen2.5-VL-3B GGUF has an 8 GB planning floor; do not install on low-memory hardware without measurement.
- FLUX.1 schnell is not recommended for an unknown low-memory PC; do not download without checking GPU/RAM/disk.
- Kokoro is relatively small by parameter count, but runtime, phonemizer and voice packs add dependencies.
- Blender/FFmpeg resource use depends on scene, resolution, samples, codec and filters.

All catalog figures are planning estimates, not measured minimum requirements.
