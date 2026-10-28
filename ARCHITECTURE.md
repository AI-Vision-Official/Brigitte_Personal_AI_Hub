# Architecture

**Status:** Conceptual only — no implementation decisions finalized.

## Design objective

Keep the project modular so that changing one AI provider or tool does not require rebuilding the entire system. The local project files remain the durable handover point.

## Proposed layers

### 1. Project record

Files in this folder:
- `00_PROJECT_START.md` — onboarding and working method.
- `AI_CONTEXT.json` — structured, machine-readable project facts and status.
- `PROJECT_STATE.md` — current progress and next action.
- `ARCHITECTURE.md` — intended system structure.
- `RULES_AND_PERMISSIONS.md` — safety and approval boundaries.
- `CHANGELOG.md` — important decisions and changes.

### 2. User interface — future option

A simple interface may eventually provide access to selected tools, project status, and AI services. Whether this should be a local web page, desktop interface, or another form remains open.

### 3. Orchestration — future option

A small coordinator may route tasks to selected providers or local tools. It should use clear interfaces and avoid making the entire system dependent on one provider's proprietary features.

### 4. AI/provider adapters — future option

Each provider or local model should be treated as a replaceable adapter where practical. Provider-specific capabilities, rate limits, costs, and data handling must be documented rather than assumed to be equivalent.

### 5. Tools and data sources — future option

Tools should be added only for a defined use case. Each tool should have a clear purpose, permissions, inputs, outputs, and failure behavior.

### 6. Local storage and logs — future option

Project data should use readable, documented formats where practical. Logs should avoid secrets and unnecessary personal data. Original source files should remain unchanged unless a separate, explicitly approved workflow requires otherwise.

## Dependency principles

- Prefer open standards and portable formats.
- Keep provider-specific code isolated.
- Avoid mandatory paid APIs unless the user explicitly approves the cost and dependency.
- Check current pricing, quotas, licensing, and terms before choosing a service.
- Do not store API keys or passwords in Markdown, JSON, source control, or logs.
- Make backups before any future migration or bulk change.
- Keep core functions usable when an optional provider or internet connection is unavailable, where practical.

## Minimal first version

The first implementation should be selected only after the first use case is agreed. Avoid building a large framework before there is a concrete need.

A reasonable evaluation checklist:
1. Does this solve the first use case?
2. Can Brigitte understand and control it?
3. Can it be run without unnecessary cost?
4. Can the provider or component be replaced?
5. Can the data be exported and backed up?
6. What happens when the service is unavailable?
7. Does it require access to private files or accounts, and is that access necessary?

## Not decided yet

- Programming language and framework.
- Local model/runtime.
- Cloud AI providers.
- User interface.
- Database or storage engine.
- Authentication model.
- Logging and backup implementation.
- Hosting or deployment approach.

These are open decisions, not implied commitments.