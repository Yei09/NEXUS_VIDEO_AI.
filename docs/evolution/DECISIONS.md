# Architecture decisions

1. Keep multimodel package separate from Blender and FFmpeg.
2. Use Python standard library for the initial core; no runtime dependencies or model downloads.
3. Use explicit local endpoints and workflows; no implicit cloud providers.
4. Paid providers are rejected by default; no API keys or secrets added.
5. Fallback requires registered adapter, supported modality, successful health check and cost/license/hardware policy compliance.
6. Agents are role profiles, not claims of nine independent model instances.
7. Estimates are not hardware measurements.
8. No scheduled evolution workflow until manual cycles are proven.
