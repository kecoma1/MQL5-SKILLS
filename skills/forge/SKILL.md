---
name: forge
description: "Work with Forge-hosted Git repositories from this workspace, including login, staged commits, and push workflows. Use when Codex needs to prepare or send commits to Forge or Forgejo remotes such as forge.mql5.io, refresh credentials, inspect Git status, or write commit messages that follow Conventional Commits like feat(rsi): summary."
---

# Forge

## Overview

Use this skill when the task involves committing or pushing code to a Forge remote from this workspace.

Follow a tight workflow: inspect status, stage only intended files, review the staged diff, write a Conventional Commit message, commit, and push to the Forge remote.

## Required workflow

1. Inspect the repo state with `git status --short`.
2. Identify unrelated local changes and do not touch them unless the user explicitly asks.
3. Stage only the files that belong to the current task.
4. Review the staged diff before committing:
   - `git diff --cached --name-only`
   - `git diff --cached --stat`
   - `git diff --cached -- <path>`
5. Write the commit message using Conventional Commits.
6. Commit with `git commit -m "type(scope): summary"`.
7. Push with `git push origin <branch>`.
8. If push fails due to credentials, fix login first and retry the same push.

## Commit convention

Use this format:

```text
type(scope): summary
```

Use short lowercase summaries in imperative style.

Example:

```text
feat(rsi): add stop loss and take profit optimization
```

Preferred types:
- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `perf`
- `build`
- `ci`
- `revert`

Rules:
- Always include a scope when a clear subsystem exists.
- Use the EA, feature, or folder as scope when possible, such as `rsi`, `forge`, `backtest`, `skills`, `premiere`.
- Keep the summary specific and under roughly 72 characters when practical.
- Avoid vague subjects like `update stuff` or `changes`.

## Login to Forge in this workspace

This workspace uses:

```text
git config --get credential.helper
manager
```

That means Git Credential Manager handles stored credentials on Windows.

The current remote pattern is:

```text
https://forge.mql5.io/<user>/<repo>.git
```

Example from this repo:

```text
https://forge.mql5.io/<user-id>/mql5.git
```

## Authentication workflow

When pushing for the first time, or when credentials expired:

1. Run:

```powershell
git push origin main
```

2. If Git Credential Manager prompts for credentials, use:
   - Forge username
   - Forge personal access token or valid password, whichever the Forge server accepts

3. Let Git Credential Manager store the credential.
4. Retry the push if needed.

If push fails with an authentication error, state the exact error and do not invent success.

## Refreshing bad credentials

If Forge credentials are stale, remove the old credential from Windows Credential Manager or let Git Credential Manager replace it on the next prompt.

Useful checks:

```powershell
git remote -v
git branch --show-current
git config --get credential.helper
git credential-manager --version
```

If needed, retry:

```powershell
git push origin main
```

## Safe commit behavior

- Never commit unrelated modified or deleted files just to get a clean tree.
- Never use `git add .` in a dirty repo unless the user explicitly wants everything.
- Prefer explicit paths in `git add -- <paths>`.
- If the repo contains unrelated user changes, commit only the files for the current task.
- Before pushing, confirm the staged file list matches the intended task.

## Example workflow

```powershell
git status --short
git add -- skills/forge/SKILL.md skills/forge/agents/openai.yaml
git diff --cached --name-only
git commit -m "feat(forge): add forge commit workflow skill"
git push origin main
```

## Final reporting

When finishing, report:
- the commit hash
- the commit message
- whether push succeeded
- any authentication issue that still blocks the push
