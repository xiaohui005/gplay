---
name: gplay-system
description: Use when working inside D:\gongju\gplay on system development, feature changes, bug fixes, project analysis, validation, build/restart handoff, or when repeated project-specific workflows should be captured as standards or promoted into subskills for the GPlay project.
---

# GPlay System

## Overview

Use this as the system-level skill for `D:\gongju\gplay`. It is intentionally a growing skill: start with conservative project discovery and validation, then turn repeated work into stable standards or subskills after real use.

Do not assume the project stack, commands, ports, backend/frontend boundaries, or deployment process before reading the repository. If the project is still empty or incomplete, document the missing facts and keep rules provisional.

## Working Stance

Act as the project maintainer for GPlay:

1. Read the existing project before changing files.
2. Keep changes scoped to the requested feature, bug, or workflow.
3. Prefer existing project patterns over new abstractions.
4. Validate with the commands available in the repository.
5. Record repeated discoveries in this skill instead of relying on memory.

## Standard Workflow

1. **Discover**
   - Inspect repository structure, package manifests, scripts, README, environment files, and existing docs.
   - Identify frontend, backend, shared packages, scripts, generated assets, and test/build commands.
   - If a fact is not discoverable, mark it as `待确认` instead of guessing.

2. **Plan the change**
   - Define the user-visible goal, affected modules, data/API impact, and risk.
   - For existing features, identify current behavior before changing it.
   - For new features, define the smallest useful first version.

3. **Implement conservatively**
   - Follow local style, naming, routing, state management, and API conventions.
   - Avoid broad refactors unless needed to complete the request safely.
   - Preserve user changes and unrelated worktree changes.

4. **Validate**
   - Run targeted checks first, then broader checks when risk is higher.
   - If frontend exists, build before handoff unless the user asks otherwise.
   - If backend exists and the task affects backend behavior, restart backend after validation when the project has a known restart command.

5. **Update standards**
   - If the same pattern appears at least twice, update `references/project-standards.md`.
   - If a workflow becomes specific and repeatable, create or update a subskill under `subskills/`.
   - If validation becomes deterministic, add or update scripts under `scripts/`.

## Subskill Strategy

Keep only one top-level skill: `gplay-system`.

Use future subskills for repeated areas, for example:

| Future subskill | When to create |
|---|---|
| `subskills/frontend-workflow` | Repeated frontend layout, build, route, component, or UI validation rules appear |
| `subskills/backend-workflow` | Backend service, API, database, auth, restart, or logging patterns become clear |
| `subskills/feature-prd-to-code` | Requirements repeatedly need PM-style analysis before implementation |
| `subskills/validation-gate` | Build/test/restart/review checks become stable |
| `subskills/release-handoff` | Delivery notes, deployment, changelog, or packaging rules become repeated |

Do not create a subskill from one isolated task. First capture the finding in `references/project-standards.md`; promote it to a subskill after it proves reusable.

## Required Handoff

Before saying work is complete:

- State what changed.
- State which files changed.
- State which validation commands ran and their result.
- If validation could not run, state the concrete reason.
- If frontend exists, report build result.
- If backend exists and was restarted, report the restart command/result.
- If new project knowledge was discovered, state whether the skill references were updated.

## References

- Read `references/project-standards.md` for accumulated GPlay project facts and standards.
- Read `references/subskill-standard.md` before creating or updating a subskill.
- Read `references/usage-guide.md` when the user asks how to use this system skill.
- Run `scripts/audit_gplay_skill.py` before handoff after editing this skill.
