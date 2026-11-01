# Changelog

Important project decisions and changes only. This file is not a transcript of every work session.

## 2026-10-28 — Initial continuity structure

**Status:** Initial project direction established.

### Decisions

- The project must not depend on one AI, one account or one supplier.
- A central local folder will serve as the authoritative project source.
- Use Markdown for human-readable documentation and JSON for structured context.
- Begin with six core documentation files:
  - `00_PROJECT_START.md`
  - `AI_CONTEXT.json`
  - `PROJECT_STATE.md`
  - `ARCHITECTURE.md`
  - `RULES_AND_PERMISSIONS.md`
  - `CHANGELOG.md`
- Do not install anything or move existing files while establishing the documentation structure.
- Keep the setup lightweight and avoid unnecessary maintenance.

### Reason

AI conversations, account access, context windows and product features can change. Portable local files make it easier to continue with another AI or without the original chat.

### Not decided

- First practical feature.
- Technical stack or provider.
- Final application architecture.
- Backup and version-control method.

---

## 2026-11-01 — Project foundation and architecture clarification

**Status:** Documentation substantially updated. Technical implementation remains in progress.

### Decisions

- The target is one integrated Personal AI Hub, not merely a collection of separate AI tools.
- Local-first and offline-first are established architectural requirements.
- AI providers, models and subscriptions must remain replaceable wherever technically practical.
- Essential local functionality should not depend on an internet connection.
- The project will use a modular architecture with a central user interface.
- Human approval is required for consequential actions.
- The Main Agent, Specialist Agents, Control Agent and Documentalist are the intended AI organization.
- Local files and user-controlled data remain the authoritative source of truth.
- Free, open-source and locally controllable solutions are preferred where practical.
- Existing original files must be preserved.

### Documentation changes

The following project records were created or updated:

- `HUB_MANIFEST.json` — project manifest created.
- `AI_CONTEXT.json` — structured project context updated and JSON validation passed.
- `ARCHITECTURE_CONTEXT.json` — target architecture recorded and JSON validation passed.
- `ARCHITECTURE.md` — updated to describe the intended architecture and distinguish current implementation from planned functionality.
- `PROJECT_STATE.md` — updated with current progress, next steps and parked items.
- `00_PROJECT_START.md` — updated with project objectives, working method and development priorities.

`RULES_AND_PERMISSIONS.md` has been reviewed and a revised version prepared. Saving and verification remain to be confirmed.

### Existing implementation clarified

- `dashboard.html` exists as an initial HTML dashboard.
- The dashboard currently uses browser `localStorage`.
- `Brigitte_Personal_AI_Hub.py` exists as a starter-file generator.
- The dashboard is not yet the complete application.
- The Python starter-file generator must not be executed without explicit approval because it may recreate or overwrite files.

### Architecture decisions still open

- Application framework and programming language.
- Long-term local storage technology.
- Local AI runtime.
- Cloud AI providers.
- Agent orchestration technology.
- Authentication and access control implementation.
- Offline infrastructure.
- Backup and recovery implementation.
- First practical implementation use case.

### Reason

The project has moved beyond an initial documentation-only concept. An existing dashboard foundation and a clearer target architecture are now known. The documentation must reflect that distinction without presenting planned functionality as already implemented.

### Next step

Complete the documentation synchronization review:

1. Verify `RULES_AND_PERMISSIONS.md`.
2. Review `HUB_MANIFEST.json` for consistency with the current file structure.
3. Check `AI_CONTEXT.json` and `ARCHITECTURE_CONTEXT.json` for consistency.
4. Verify that the documentation set agrees on project status and next actions.

After documentation synchronization, inspect the existing dashboard and local development environment before selecting the first practical implementation milestone.
---

## 2026-11-01 — Dashboard baseline tests

**Status:** Initial manual browser tests passed.

### Technical validation

- `git diff --check` produced no reported errors.
- The JavaScript extracted from `dashboard.html` passed Node.js syntax validation using `node --check`.

### Functional tests

The following functions were tested in a separate Chrome Incognito session using temporary test data:

- On Hold persistence after page refresh.
- Task persistence and completion status.
- Note persistence.
- JSON export.
- JSON import, including retention of the test task, note and On Hold text.
- Project persistence.
- Appointment persistence.
- Recurring item persistence.

All listed tests passed.

### Scope and limitations

These were basic functional tests, not a comprehensive validation of security, recovery, error handling, storage limits or multi-tab behaviour.

No claim is made that all possible data-loss scenarios have been eliminated.

### Next step

Documentation synchronization review, followed by further inspection of the dashboard and local development environment.

## 2026-11-01 - Documentation synchronization completed

- Updated and reviewed `00_PROJECT_START.md`.
- Updated and verified `RULES_AND_PERMISSIONS.md`.
- Updated `ARCHITECTURE.md` with dashboard test information and safer migration requirements.
- Updated `PROJECT_STATE.md` to reflect the current project status and next development phase.
- Updated `HUB_MANIFEST.json` to reflect the final documentation synchronization.
- Validated `HUB_MANIFEST.json`, `AI_CONTEXT.json` and `ARCHITECTURE_CONTEXT.json` as valid JSON.
- Completed baseline dashboard tests using synthetic data in a separate browser session.
- No software was installed and no system settings were changed.
- No Git commit or push was performed as part of this update.

**Next step:** Inventory the available local development tools and evaluate storage, backup and offline requirements.
