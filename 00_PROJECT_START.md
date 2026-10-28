# Brigitte's Personal AI Hub

**Status:** Initial draft  
**Last updated:** 2026-10-28  
**Purpose:** Keep the project understandable and usable across different AI providers, accounts, and local tools.

## The goal

Build a personal AI hub that Brigitte can shape over time: a practical, modular setup that can use different AI services and, where useful, local tools or local models. It should remain under Brigitte's control and should not depend on one AI, one account, one subscription, or one provider.

## Core principles

1. **Local source of truth.** The files in this project folder are the authoritative project record.
2. **AI is replaceable.** Any AI should be able to resume work from these files without relying on chat history or saved memory.
3. **Small steps.** Prefer the smallest useful next step. Do not turn setup into a maintenance project.
4. **No surprise actions.** Do not install software, change system settings, move existing files, connect accounts, publish data, or spend money without explicit approval.
5. **Preserve originals.** Summaries and generated outputs never replace source documents or original data.
6. **Explain clearly.** Separate confirmed facts, assumptions, open questions, and recommendations.
7. **Privacy by default.** Store only information needed for the project. Do not copy personal or sensitive details into general project context unless necessary and explicitly approved.
8. **Cost-aware.** Prefer free and locally controllable options where practical. Identify costs, quotas, API requirements, and vendor lock-in before recommending a dependency.
9. **Human approval for consequential actions.** Brigitte remains the decision-maker, especially for external actions, deletion, sharing, publication, and automation.
10. **Accessible workflow.** Give complete, concrete steps and avoid unnecessary complexity.

## Start here — for any AI

Read these files in this order:

1. `00_PROJECT_START.md`
2. `PROJECT_STATE.md`
3. `RULES_AND_PERMISSIONS.md`
4. `ARCHITECTURE.md`
5. `AI_CONTEXT.json`
6. `CHANGELOG.md` when the decision history is relevant

Then:
- Summarize the current state briefly.
- Identify the next step listed in `PROJECT_STATE.md`.
- Do not redo completed work unless there is a clear reason.
- If information conflicts, point out the conflict instead of silently choosing.
- If you make a material decision or change, propose an update to the relevant project file.

## Working method

For each work session, keep the project record small and current:

- **End goal:** what this project is meant to achieve.
- **Main path:** the agreed approach.
- **Current position:** what is confirmed as complete or in progress.
- **Next step:** one concrete action.
- **Parking lot:** useful ideas that are not part of the current step.

At the end of a meaningful session:
1. Summarize what changed.
2. Record decisions and reasons in `CHANGELOG.md`.
3. Update `PROJECT_STATE.md` if status or next step changed.
4. Update `AI_CONTEXT.json` only when structured context materially changes.
5. Do not record routine chat details.

## Current scope

This folder is the project continuity layer. It is not yet the AI hub application itself. No software installation, account connection, repository change, or migration is authorized by these files.

## First next step

Review these six starter files, correct any inaccurate assumptions, and then choose the smallest practical first implementation step. Do not install anything until that step is explicitly agreed.

## Status vocabulary

- **Confirmed:** explicitly agreed or verified.
- **Proposed:** a recommendation not yet approved.
- **Open:** a decision or fact still needed.
- **Parked:** intentionally deferred.
""",