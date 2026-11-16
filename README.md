# NEXUS VIDEO AI

Cloud-first, private-by-default short-video generator. It creates original Spanish scripts, synthesizes narration with Piper TTS, renders vertical MP4 with FFmpeg, validates output, and can upload to Google Drive. It never publishes to social networks.

## Safety defaults

- Manual `workflow_dispatch` only. No scheduled workflow is enabled.
- No paid services or billing setup is required by this repository.
- Google Drive upload is skipped unless the owner explicitly configures `GOOGLE_SERVICE_ACCOUNT_JSON` as a GitHub Actions secret.
- Make.com is an optional metadata-only coordinator; MP4 files are never sent through Make.
- No social publishing integrations exist.

## First manual test

1. Configure the Piper model secrets/variables described in `docs/SETUP.md`.
2. Optionally configure Drive credentials (no credentials are committed).
3. Open **Actions → NEXUS Video - Manual Test → Run workflow**.
4. Download the generated MP4 artifact. If Drive credentials are configured, the workflow also verifies the uploaded file metadata.

See `docs/SETUP.md` for exact setup. The first commit intentionally leaves daily schedules disabled.
