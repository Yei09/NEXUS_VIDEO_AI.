# NEXUS Blender 3D prototype

This workflow is a manual, CPU-only proof-of-render on GitHub-hosted Ubuntu. It builds actual corridor geometry, a bone-rigged actor, an independently animated shadow mesh, a hinged door and a keyed 3D camera in Blender/Cycles. FFmpeg encodes H.264/AAC and extracts all evidence from the MP4.

## Run
GitHub → Actions → “NEXUS Blender 3D prototype (manual)” → Run workflow on `cinematic-reconstruction`. Keep samples at 8 initially. No GPU, Make, Drive, commercial API, scheduled trigger or publishing integration is used.

## Acceptance
The validator probes the encoded MP4 and compares adjacent decoded frames for walking, door and shadow intervals. Property/keyframe presence alone is not accepted. Artifacts include the MP4, six stills, consecutive motion sequences, camera samples, scene manifest, timed audio cue JSON, FFprobe, validation and performance reports.

## Performance caveat
GitHub-hosted runner resource availability varies. Blender installation, render wall time, child peak RSS, output size and achieved rendered frames per second are recorded per run. This prototype uses low Cycles CPU samples and a stylized procedural actor; it is a reusable foundation, not final photorealistic character production. The workflow must actually run before any speed or resource claim is made.
