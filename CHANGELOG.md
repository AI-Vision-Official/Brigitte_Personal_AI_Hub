# Changelog

Important project decisions and changes only. Do not use this file as a transcript of every work session.

## 2026-10-28 — Initial continuity structure

**Status:** Agreed direction; starter files drafted.

### Decisions
- The project must not depend on one AI, one account, or one supplier.
- A central local folder will serve as the authoritative project source.
- Use Markdown for human-readable documentation and JSON for structured context.
- Begin with six files:
  - `00_PROJECT_START.md`
  - `AI_CONTEXT.json`
  - `PROJECT_STATE.md`
  - `ARCHITECTURE.md`
  - `RULES_AND_PERMISSIONS.md`
  - `CHANGELOG.md`
- Do not install anything or move existing files while establishing the documentation structure.
- Keep the setup lightweight and avoid unnecessary maintenance.

### Reason
AI conversations, account access, context windows, and product features can change. Portable local files make it easier to continue with another AI or without the original chat.

### Not decided
- First practical feature.
- Technical stack or provider.
- Whether the first implementation is a local dashboard, assistant, or another form.
- Backup/version-control method.

### Next step
Review the starter files, correct inaccuracies, and select one first use case before implementation.
