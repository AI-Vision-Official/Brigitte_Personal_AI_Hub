# Architecture

**Status:** Target architecture defined — implementation remains incremental.  
**Version:** 2.0  
**Last updated:** 1 November 2026

## 1. Design objective

Brigitte Personal AI Hub is intended to become one integrated, modular personal AI environment.

The system should provide a central interface for managing projects, information, tools, AI services and personal workflows.

The architecture must remain:

- Local-first and offline-first.
- Independent of any single AI provider, model or subscription.
- Modular and expandable.
- Based on portable data formats and open standards where practical.
- Understandable and controllable by Brigitte.
- Secure, recoverable and transparent.

Local project files and user-controlled data remain the durable source of truth.

## 2. System overview

The intended system consists of six architectural layers:

1. Central user interface.
2. Application and module layer.
3. AI orchestration.
4. AI providers and local models.
5. Tools and external integrations.
6. Local data and storage.

The layers should communicate through documented interfaces rather than being tightly coupled.

Essential local functionality should remain available without an internet connection. Cloud AI, external APIs and online integrations are optional capabilities.

## 3. Architectural layers

### 3.1 Project record and documentation

The project documentation defines the system's goals, structure, current state and operating rules.

Core files:

- `HUB_MANIFEST.json` — project identity, file inventory and documentation entry points.
- `AI_CONTEXT.json` — structured project context and working principles.
- `ARCHITECTURE_CONTEXT.json` — machine-readable target architecture.
- `00_PROJECT_START.md` — onboarding and working method.
- `PROJECT_STATE.md` — current progress and next action.
- `ARCHITECTURE.md` — human-readable system architecture.
- `RULES_AND_PERMISSIONS.md` — security and approval boundaries.
- `CHANGELOG.md` — important decisions and changes.

These files should remain consistent. Changes to the architecture must be reflected in the relevant project records.

### 3.2 Central user interface

**Target:** One central dashboard that provides access to the system's modules.

The interface should support:

- Project and task overview.
- Daily planning and appointments.
- Access to knowledge and documents.
- AI services and specialist functions.
- Health and wellbeing organization.
- Creative and community projects.
- System status and notifications.

**Current implementation:** An initial HTML dashboard exists in `dashboard.html`.

**Current limitation:** The dashboard is an initial foundation, not yet the complete application.

The final interface technology remains subject to evaluation.

### 3.3 Application and module layer

The application layer contains the actual functions of the Hub.

Each functional area should be implemented as a separate module with clearly defined responsibilities.

Planned modules include:

- Dashboard and system overview.
- Daily management and planning.
- Communication and email.
- Knowledge and document management.
- Projects and administration.
- Health and wellbeing.
- Creative writing and content development.
- Heal the World Project, AI Vision and Funsum.
- Automation and workflow management.

Modules should be independently maintainable where practical.

### 3.4 AI orchestration

The orchestration layer coordinates tasks between the main application, AI agents, models and tools.

The intended agent structure is:

**Main Agent**
- Coordinates the overall workflow.
- Understands the user's request.
- Delegates tasks where appropriate.
- Maintains project direction.

**Specialist Agents**
- Handle defined areas of expertise.
- Work within assigned permissions.
- Return results to the Main Agent.

**Control Agent**
- Checks permissions and proposed actions.
- Identifies risks and inconsistencies.
- Enforces approval requirements.

**Documentalist**
- Maintains project documentation.
- Records important decisions and changes.
- Helps preserve continuity between AI providers and sessions.

Brigitte remains the final decision-maker.

**Status:** Conceptual design. The agent structure has not yet been implemented.

### 3.5 AI providers and local models

AI providers and models should be replaceable components wherever technically practical.

Potential categories:

- Cloud-based AI services.
- Locally running language models.
- Specialized AI services.
- Non-AI automation tools.

Each provider must have documented information about:

- Capabilities and limitations.
- Costs and usage restrictions.
- Data handling and privacy.
- Availability and dependencies.
- Provider-specific features.

The system must not assume that different providers offer equivalent functionality.

No paid provider, API or subscription becomes mandatory without explicit approval.

### 3.6 Tools and external integrations

Tools should be introduced only when they support a defined use case.

Possible integrations include:

- Local applications and scripts.
- File and document processing.
- Email and calendar services.
- External APIs.
- Knowledge databases.
- Automation systems.

Every integration should have a documented purpose, permissions, inputs, outputs and failure behavior.

Access to external accounts or private data must be limited to what is actually necessary.

### 3.7 Local data and storage

Local storage is a fundamental part of the architecture.

The intended storage strategy may combine:

- JSON for structured configuration and metadata.
- Markdown for readable documentation.
- IndexedDB for browser-based application data.
- Local files and directories for user-controlled documents.
- A suitable local database where justified.
- Exportable backups and recovery records.

**Current implementation:** The initial dashboard uses browser `localStorage`.

**Limitation:** `localStorage` is not sufficient as the final storage architecture for a larger application.

Any migration to a more suitable storage solution must include a verified backup, a tested migration procedure and a recovery path before existing application data is changed.

Original source files must remain unchanged unless a separate workflow has been explicitly approved.

## 4. Offline-first architecture

Offline functionality is a core design requirement.

The intended system should support:

- Opening the application without internet access.
- Accessing locally stored information.
- Using essential local modules.
- Maintaining local project data.
- Exporting and backing up information.
- Recovering from interrupted or failed operations.

Possible technical components include a service worker, offline application shell, local database and local processing tools.

The following may require an internet connection:

- Cloud AI providers.
- External APIs.
- Online integrations.
- Remote synchronization.
- External information retrieval.

Loss of an internet connection must not unnecessarily disable essential local functions.

## 5. Security and permissions

Security must be considered throughout the architecture.

The system must:

- Avoid storing passwords, API keys or secrets in ordinary project files.
- Protect personal information.
- Minimize unnecessary data collection.
- Keep logs free of secrets and unnecessary personal data.
- Use documented permissions for integrations.
- Preserve recoverable backups.
- Make consequential operations transparent.

Explicit approval from Brigitte is required before:

- Sending emails or messages.
- Publishing content.
- Sharing personal information.
- Installing software or changing system settings.
- Making payments or starting subscriptions.
- Deleting or moving original files.
- Performing significant bulk modifications.

The system must never silently expand its permissions.

## 6. Dependency principles

- Prefer open standards and portable formats.
- Keep provider-specific code isolated.
- Prefer free, open-source and locally usable components where practical.
- Avoid mandatory paid APIs.
- Check current pricing, quotas, licensing and terms before selecting services.
- Make backups before migrations or bulk changes.
- Keep essential functions independent of optional providers.
- Document technical dependencies and known limitations.

## 7. Development strategy

Development should proceed incrementally.

The intended approach:

1. Establish and maintain reliable project documentation.
2. Inspect and understand the existing dashboard.
3. Evaluate the current local development environment.
4. Confirm the storage and offline strategy.
5. Select the first concrete use case.
6. Implement and test one manageable component at a time.
7. Preserve working functionality.
8. Expand only when the existing foundation is stable.

Avoid building a large framework before its requirements are clear.

## 8. Technical decisions

The following principles are established:

| Subject | Status |
|---|---|
| Integrated central application | Confirmed |
| Local-first architecture | Confirmed |
| Offline-first architecture | Confirmed |
| Modular design | Confirmed |
| Provider independence | Confirmed |
| Human approval for consequential actions | Confirmed |
| HTML dashboard as initial foundation | Implemented |
| Browser localStorage | Implemented, temporary |
| IndexedDB | Proposed |
| Local AI runtime | Not decided |
| Application framework | Not decided |
| Database technology | Not decided |
| Agent orchestration technology | Not decided |
| Authentication model | Not decided |
| Backup implementation | Not decided |
| Deployment approach | Not decided |

These statuses distinguish established requirements from technical choices that still require evaluation.

## 9. Evaluation checklist

Every significant architectural decision should be assessed against these questions:

1. Does it support a concrete use case?
2. Can Brigitte understand and control it?
3. Can it operate without unnecessary costs?
4. Can the component or provider be replaced?
5. Can the data be exported and backed up?
6. What happens when the service or internet connection is unavailable?
7. Does it require access to private files or accounts?
8. Is that access necessary and appropriately restricted?
9. Can the system recover from failure?

## 10. Current architecture position

The initial dashboard has undergone baseline functional testing using synthetic data in a separate browser session. Task management, notes, appointments, recurring items, projects, On Hold persistence, and JSON import/export were tested successfully. These tests do not constitute a complete security or reliability assessment.

The project has established its target architecture and core operating principles.

An initial dashboard exists, and browser-based local storage is currently used.

The complete application, modular system, offline infrastructure, AI orchestration and agent structure are still planned.

The next development priority is to inspect the existing dashboard and technical environment before making further implementation decisions.

The architecture remains open to refinement as practical requirements become clearer.