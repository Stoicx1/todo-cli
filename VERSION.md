# Versioning Guide (Reference for Humans and AI Tools)

Purpose: Define a clear, minimal, and automatable versioning workflow for this Python CLI/TUI app, so humans and AI tools can consistently bump, tag, and surface the current version.

## Scope
- Applies to the entire repo (CLI/TUI app, tests, and docs).
- Focuses on: where the version lives, how to display it, how and when to bump, tagging and releases, and automation options.

## Version Scheme
- Use Semantic Versioning (SemVer): MAJOR.MINOR.PATCH (e.g., 1.4.2)
  - MAJOR: breaking changes or incompatible behavior.
  - MINOR: new features, backward compatible.
  - PATCH: bug fixes or small improvements.
- Pre-releases: -alpha.N, -beta.N, -rc.N (e.g., 2.0.0-rc.1)
- Optional build metadata for dev builds: +<shortsha>[-dirty] (e.g., 1.5.0-dev+abc123)

## Single Source of Truth
- Recommended now: a plain text file at repo root named `VERSION` that contains exactly the version string (e.g., `0.4.0`).
- Tag each release in Git using `vX.Y.Z` (or `vX.Y.Z-rc.N` for pre-releases).
- The application should read the version from `VERSION` at runtime and, if not found, derive a dev version from Git (`git describe`) as a fallback.

Directory anchors:
- VERSION → exact version string for releases (and pre-releases).
- CHANGELOG.md → human-readable changes for each version.
- Git tag `vX.Y.Z` → immutable pointer to the release commit.

## Where/How Version Appears in the App
- CLI flags: `--version` and `-v` should print the version, e.g., `todo-cli 1.2.0`.
- Help: include version in the `--help` footer if practical.
- Dev builds: include commit info, e.g., `todo-cli 1.3.0-dev+abc123-dirty`.

Expected helper (to be implemented if not present):
- `utils.version.get_version() -> str`
  - Tries to read `VERSION` (exact string).
  - If missing or empty, attempts `git describe --tags --dirty --always` to form `X.Y.Z-dev+<sha>[-dirty]`.
  - Returns a safe default like `0.0.0-dev` if offline/no Git.
  - This function can be reused by UI, logs, and AI tools.

## When to Bump
- PATCH: bug fix, small non-breaking improvement.
- MINOR: add feature(s) without breaking existing behavior.
- MAJOR: breaking changes, removed flags/behaviors, incompatible data.
- Pre-release: long-running/unstable changes before final.

## Release Flow (Milestone → Release)
1. Ensure tests pass and docs updated (esp. CHANGELOG.md under “Unreleased”).
2. Decide SemVer bump (patch/minor/major) for the milestone.
3. Update `VERSION` with the new version (e.g., `1.4.0`).
4. Finalize CHANGELOG.md: move entries from “Unreleased” → new version with date.
5. Commit: `chore(release): v1.4.0` and include changelog summary.
6. Tag: `git tag -a v1.4.0 -m "v1.4.0"` (annotated tag).
7. Push: `git push origin main --follow-tags` (or push tag separately).
8. CI/build: create artifacts, attach to release notes (if configured).

Hotfixes:
- Branch from the last release tag, apply fix, bump PATCH, tag, release, merge back to main.

Pre-releases:
- Use `VERSION` like `2.0.0-rc.1` and tag `v2.0.0-rc.1`. Iterate rc.2/rc.3 until final.

## Commands (Git + File-based bump)
- Edit version: open `VERSION`, set to new version string only (no extra text).
- Commit version and changelog:
  - `git add VERSION CHANGELOG.md`
  - `git commit -m "chore(release): vX.Y.Z"`
- Create annotated tag: `git tag -a vX.Y.Z -m "vX.Y.Z"`
- Push: `git push && git push --tags`

## Changelog Conventions
- Keep `CHANGELOG.md` using “Keep a Changelog” style.
- Sections for each release: Added, Changed, Fixed, Removed, Deprecated, Security.
- Maintain an “Unreleased” section; at release, move entries under the new version with date.

## Automation Options (Python)

Option A — bump2version (file-based, light weight):
- Install: `pip install bump2version`
- Add a `.bumpversion.cfg` like:
  ```ini
  [bumpversion]
  current_version = 0.1.0
  commit = True
  tag = True
  tag_name = v{new_version}

  [bumpversion:file:VERSION]
  ```
- Run:
  - Patch: `bump2version patch`
  - Minor: `bump2version minor`
  - Major: `bump2version major`
  - Pre-release: `bump2version --new-version 2.0.0-rc.1 release`

Option B — setuptools_scm (derive from Git tags):
- Use when you prefer tags-as-truth and automatic dev versions.
- Requires `pyproject.toml` configuration and Git tags. Example stub:
  ```toml
  [project]
  name = "todo-cli"
  dynamic = ["version"]

  [tool.setuptools_scm]
  version_scheme = "post-release"
  local_scheme = "node-and-date"
  ```
- Behavior: tagged commits yield exact versions; untagged yield `X.Y.Z.devN+g<sha>`.

Option C — Scripted bump (very simple):
- Write a short script to validate new version, update `VERSION`, and create tag.
- Useful if you want zero extra dependencies and maximum control.

Choose one option and stick with it. This repo defaults to the simple `VERSION` file + Git tags unless tooling is added later.

## Expected AI Tooling Behavior
- Read-only: AI tools should use `utils.version.get_version()` to retrieve the version string for display, logs, and any telemetry.
- Bump and tag: when asked to prepare a release, AI should:
  - Update `VERSION` according to SemVer policy.
  - Update `CHANGELOG.md` (move “Unreleased” to the new version with date).
  - Commit with message `chore(release): vX.Y.Z`.
  - Create annotated tag `vX.Y.Z`.
  - Never move or rewrite existing tags.
- Pre-release handling: Prefer `-rc.N` before a major or large minor; bump N sequentially.
- Dev builds: If no `VERSION` and not on a tag, AI may derive `X.Y.Z-dev+<sha>` using Git.

## Release Quality Checklist
- All tests pass locally and/or in CI.
- CHANGELOG.md updated and proofread.
- `VERSION` bumped correctly; no trailing whitespace.
- App prints the new version with `--version`.
- If packaging/publishing is enabled, artifacts include the exact version.
- Tag pushed; release notes published if applicable.

## Example: Minor Release 1.4.0
1. Validate tests and docs.
2. Edit `VERSION` → `1.4.0`.
3. Update CHANGELOG.md: move Unreleased entries under `## [1.4.0] - 2025-10-26`.
4. `git add VERSION CHANGELOG.md`
5. `git commit -m "chore(release): v1.4.0"`
6. `git tag -a v1.4.0 -m "v1.4.0"`
7. `git push origin main && git push origin v1.4.0`

## Example: Pre-release 2.0.0-rc.1
1. `echo 2.0.0-rc.1 > VERSION`
2. Update CHANGELOG.md with RC notes.
3. Commit and tag `v2.0.0-rc.1`.
4. Iterate rc.2/rc.3 as needed; final: set `VERSION` to `2.0.0`, tag `v2.0.0`.

---
Notes:
- This document is implementation-agnostic: the helper `utils.version.get_version()` is the intended stable API surface for the rest of the codebase and AI tools. If it doesn’t exist yet, implement it following the behavior described above.
- If we later add packaging (pyproject, wheels), revisit the setuptools_scm option or wiring the `VERSION` file into package metadata.

