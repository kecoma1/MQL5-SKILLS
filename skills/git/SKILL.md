---
name: git
description: Use when creating branches, writing commits, or following repository Git conventions in this workspace. Follow the local branch naming and commit message patterns, including issue references when available.
---

# Git

Use this skill when the user asks for help with branches, commits, or Git naming conventions in this repository.

## Branch Names

Create short, lowercase branch names with hyphens.
Use one of these prefixes:

- `feature/branch-name`
- `bug/branch-name`
- `hotfix/branch-name`
- `chore/branch-name`
- `docs/branch-name`
- `refactor/branch-name`
- `test/branch-name`

Choose the prefix by intent:

- `feature/` for new functionality
- `bug/` for defect fixes that are not urgent production fixes
- `hotfix/` for urgent fixes
- `chore/` for maintenance, config, tooling, or cleanup
- `docs/` for documentation-only changes
- `refactor/` for structural code improvements without intended behavior change
- `test/` for test-only additions or fixes

Examples:

```text
feature/add-git-skill
bug/fix-backtest-report-path
hotfix/repair-mt5-launch-command
chore/normalize-skill-path-placeholders
docs/update-run-backtests-skill
refactor/simplify-fvg-loader
test/add-backtest-config-coverage
```

## Commit Format

Use this format for commit subjects:

```text
type(scope): summary
```

Preferred example:

```text
feat(skills): add git conventions skill
```

When there is a related issue, add a blank line and reference it like this:

```text
feat(skills): add git conventions skill

refs #123
```

## Commit Types

Use these commit types:

- `feat` for new behavior or new functionality
- `fix` for bug fixes
- `hotfix` for urgent production fixes when the repository uses a distinct hotfix commit type
- `chore` for maintenance or tooling updates
- `docs` for documentation changes
- `refactor` for internal code restructuring without intended behavior change
- `test` for test changes
- `perf` for performance improvements
- `build` for build pipeline or dependency packaging changes
- `ci` for CI workflow changes

## Scope

Use a short scope that matches the affected area.

Examples:

- `skills`
- `backtests`
- `compile`
- `mt5`
- `docs`

## Summary Rules

Keep the summary short and action-oriented.

- Use lowercase unless a term requires uppercase.
- Do not end the summary with a period.
- Prefer specific outcomes over vague wording.

Good:

```text
fix(backtests): use placeholder report path in ini example
```

Avoid:

```text
fix(stuff): various updates
```

## Issue References

Use issue references when the repository tracks work with issue IDs.

- Use `refs #issue-id` when the commit relates to an issue
- Use `closes #issue-id` when the commit is intended to close the issue

Examples:

```text
fix(mt5): handle missing tester log gracefully

refs #45
```

```text
docs(skills): clarify branch naming rules

closes #52
```

## Pull Request Alignment

When preparing multiple commits for one branch:

- keep commits focused
- do not mix unrelated changes in the same commit
- keep the branch name aligned with the main intent of the work

If the work is small and tightly related, prefer one clean commit over many noisy commits.
