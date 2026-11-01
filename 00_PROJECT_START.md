# Brigitte Personal AI Hub

**Status:** Project foundation established  
**Last updated:** 2026-11-01  
**Purpose:** Provide a reliable, provider-independent starting point for developing and maintaining Brigitte's Personal AI Hub across different AI systems, accounts and local tools.

## 1. The goal

Build an integrated, modular Personal AI Hub that Brigitte can shape and expand over time.

The Hub should provide one central environment for managing projects, information, tools, AI services and personal workflows.

It must remain under Brigitte's control and must not depend on one AI, account, subscription, model or provider.

The intended system is:

- Local-first and offline-first.
- Modular and expandable.
- Independent of individual AI providers.
- Based on portable formats and open standards where practical.
- Affordable, with free and open-source solutions preferred.
- Understandable, maintainable and recoverable.

Essential local functions should remain available without an internet connection. Cloud AI and external services are optional capabilities.

## 2. Core principles

1. **Local source of truth.** The files and data controlled by Brigitte are the authoritative project record.
2. **AI is replaceable.** Any AI should be able to resume work using the project documentation without depending on chat history or saved memory.
3. **Small steps.** Prefer the smallest useful next step. Avoid unnecessary complexity and maintenance.
4. **No surprise actions.** Do not install software, change system settings, move files, connect accounts, publish data or spend money without explicit approval.
5. **Preserve originals.** Summaries and generated outputs must not replace original documents or source data.
6. **Explain clearly.** Separate confirmed facts, assumptions, proposals, open questions and recommendations.
7. **Privacy by default.** Store only information needed for the project. Do not copy sensitive personal information into general project context unless necessary and explicitly approved.
8. **Cost-aware.** Prefer free and locally controllable options where practical. Identify costs, quotas, API requirements and vendor lock-in before recommending dependencies.
9. **Human approval.** Brigitte remains the final decision-maker, especially for external actions, deletion, sharing, publication, payments and automation.
10. **Accessible workflow.** Provide complete, concrete instructions. Work in manageable steps and avoid unnecessary technical complexity.
11. **Document decisions.** Important changes and technical decisions must be recorded so work can continue across AI systems.
12. **Recoverability.** Data and project changes should be documented, exportable and recoverable wherever practical.

## 3. Start here — instructions for any AI

Read the project documentation in this order:

1. `00_PROJECT_START.md`
2. `HUB_MANIFEST.json`
3. `PROJECT_STATE.md`
4. `RULES_AND_PERMISSIONS.md`
5. `AI_CONTEXT.json`
6. `ARCHITECTURE.md`
7. `ARCHITECTURE_CONTEXT.json`
8. `CHANGELOG.md` when decision history is relevant.

Then:

- Summarize the current project state briefly.
- Identify the next action in `PROJECT_STATE.md`.
- Respect the existing decisions and permissions.
- Do not redo completed work without a clear reason.
- If information conflicts, identify the conflict instead of silently choosing.
- Distinguish implemented functionality from planned functionality.
- Do not assume that a proposed technical solution has been approved.
- Propose updates to relevant project files when important information changes.

The project files are the continuity mechanism. Chat history and AI memory are supplementary, not authoritative.

## 4. Working method

Keep project development structured and manageable.

Track these five elements:

- **End goal:** What the project is intended to achieve.
- **Main path:** The agreed development approach.
- **Current position:** What has actually been completed or is in progress.
- **Next step:** One concrete action.
- **Parking lot:** Useful ideas that are deliberately postponed.

At the end of a meaningful work session:

1. Summarize what changed.
2. Record important decisions and reasons in `CHANGELOG.md`.
3. Update `PROJECT_STATE.md` when progress or the next action changes.
4. Update `AI_CONTEXT.json` when structured project context materially changes.
5. Update `ARCHITECTURE_CONTEXT.json` when the target architecture changes.
6. Keep `HUB_MANIFEST.json` synchronized when project files or their roles change.
7. Do not record routine chat details.

## 5. Current project scope

The project has two connected parts:

### A. Project continuity and documentation

The documentation establishes:

- Project identity and objectives.
- Architecture and technical principles.
- Current development status.
- Permissions and security boundaries.
- Decisions and development history.
- Continuity between AI providers and sessions.

### B. Personal AI Hub application

The intended application will provide a central interface with modular functions.

An initial technical foundation already exists:

- `dashboard.html` — initial HTML dashboard.
- `Brigitte_Personal_AI_Hub.py` — starter-file generator.

The dashboard is an initial implementation, not the completed Hub.

The current dashboard uses browser `localStorage`. A more suitable long-term local storage architecture and offline infrastructure still need to be evaluated.

The complete application, AI orchestration, agent structure and integrations have not yet been implemented.

## 6. Development environment

**Project folder:**

`J:\GIT\PROJECTS\Brigitte_Personal_AI_Hub`

**Repository:**

`AI-Vision-Official/Brigitte_Personal_AI_Hub`

**Operating environment:** Windows 10 Pro.

The project should use existing tools and resources wherever practical.

Do not install additional software or modify the development environment without explicit approval.

The Python starter-file generator must not be executed without explicit approval because it may recreate or overwrite files.

## 7. Development priorities

The development sequence is:

1. Establish and synchronize project documentation.
2. Inspect the existing dashboard and its functionality.
3. Inventory the available local development tools.
4. Evaluate storage and offline requirements.
5. Identify the first practical use case.
6. Select the minimum suitable technical solution.
7. Implement and test one component at a time.
8. Expand the application while preserving existing functionality.

Do not build a large framework before the first practical requirements are established.

## 8. Permissions and limitations

These project instructions do not automatically authorize:

- Software installations.
- Changes to operating system settings.
- Account connections or external access.
- Paid services or subscriptions.
- Sending messages or emails.
- Publishing content.
- Sharing personal information.
- Deleting, moving or overwriting original files.
- Unsupervised automation with consequential effects.

Such actions require explicit approval from Brigitte.

## 9. Status vocabulary

Use these terms consistently:

- **Confirmed:** Explicitly agreed or verified.
- **Proposed:** A recommendation that has not yet been approved.
- **Open:** A decision or fact still requiring investigation.
- **Planned:** Intended functionality that has not yet been implemented.
- **Implemented:** Functionality that exists and has been verified.
- **Partially implemented:** A working foundation exists, but the intended functionality is incomplete.
- **Parked:** Intentionally postponed.

Never describe planned functionality as implemented.

## 10. Current next step

Complete the documentation synchronization review.

After that, inspect the existing dashboard and local development environment before selecting the first practical implementation milestone.

No additional software installation or system modification is required for this documentation phase.