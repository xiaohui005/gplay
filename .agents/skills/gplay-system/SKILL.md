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
   - If frontend exists, **build** before handoff unless the user asks otherwise.
   - If backend exists and the task affects backend behavior, **restart** backend after validation.
   - **Verify servers actually accessible**: run `curl.exe` or `Invoke-WebRequest` to confirm both `:8008` and `:5173` return HTTP 200, not just that the process is listening.
   - **Check page rendering**: use Playwright (`node -e "..."`) to open a key page (e.g. detail page) and verify no JS errors (`pageerror` events) and expected text exists.
   - If any validation step fails, **do not mark done** — investigate and fix first.
   - If a validation command cannot run (e.g. dependency missing), state the concrete reason.

5. **Update standards**
   - If the same pattern appears at least twice, update `references/project-standards.md`.
   - If a workflow becomes specific and repeatable, create or update a subskill under `subskills/`.
   - If validation becomes deterministic, add or update scripts under `scripts/`.

## Subskill Strategy

Keep only one top-level skill: `gplay-system`.

Use future subskills for repeated areas, for example:

| subskill | 创建时间 | 何时使用 |
|---|---|---|
| `subskills/dev-server-workflow` | 已创建 | 前后端启动/重启/构建/验证/播种 |
| `subskills/frontend-workflow` | 待创建 | 前端布局、组件、样式规则重复出现 |
| `subskills/backend-workflow` | 待创建 | 后端 API、数据库、业务逻辑模式变清晰 |
| `subskills/feature-prd-to-code` | 待创建 | 需求需要 PM 式分析再实施 |
| `subskills/validation-gate` | 待创建 | 构建/测试/重启/审查检查稳定 |
| `subskills/release-handoff` | 待创建 | 交付记录、部署、更新日志规则重复 |

Do not create a subskill from one isolated task. First capture the finding in `references/project-standards.md`; promote it to a subskill after it proves reusable.

## Required Handoff

Before saying work is complete:

- State what changed.
- State which files changed.
- State which validation commands ran and their result.
- If validation could not run, state the concrete reason.
- If frontend exists, report build result (and whether dev server serves 200).
- If backend exists and was restarted, report the restart command/result.
- If new project knowledge was discovered, state whether the skill references were updated.
- **CRITICAL**: After any change that could affect page rendering, verify the running dev server serves the page without JS errors (`pageerror` events) using Playwright. Do not rely solely on build success.

## References

- Read `references/project-standards.md` for accumulated GPlay project facts and standards.
- Read `references/subskill-standard.md` before creating or updating a subskill.
- Read `references/usage-guide.md` when the user asks how to use this system skill.
- Read `subskills/dev-server-workflow/SKILL.md` for local dev server start/restart/build workflow.
- Run `scripts/audit_gplay_skill.py` before handoff after editing this skill.
