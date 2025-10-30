# Follow‑Up Plan: Phase 2–7 (Docs + Shortcuts Consistency)

Date: 2025-10-29
Owner: core/docs

## Context & Decisions (locked)
- Remove Rich UI references from docs (Textual‑only going forward).
- Keep Option B key bindings in Textual:
  - `x` = done, `d` = delete (selected item), `r` = refresh
- StatusBar height fix approved (6) — implemented in both themes.
- Clean encoding/formatting issues across docs — started; complete in Phase 3.

## Status (today)
- Done:
  - StatusBar height updated to 6 (dark + light CSS in `textual_app.py`).
  - Footer bullet encoding fixed (proper `•`, ASCII fallback kept).
  - “Age” sections: added corrected lines (sort/filter examples) in README, Usage, Quick Ref.
- Pending cleanup:
  - Remove the original corrupted “Age” lines containing control chars/backticks.

---

## Phase 2 — Unify Shortcuts and Bindings
[ ] Keep Textual bindings as Option B (no functional change): `x` done, `d` delete, `r` refresh.
[ ] Align typed command aliases to avoid conflicts with key bindings:
    - Remove `d` → `done` alias (prevents confusion with `d` key = delete).
    - Keep deletion via typed `remove|delete|del` words only (no single‑letter typed alias).
    - Keep `r` reserved for Textual refresh keybinding only (no typed alias to remove).
[ ] Update `core/commands.py` `COMMAND_ALIASES` accordingly.
[ ] Update `textual_widgets/command_input.py` suggester entries (remove `d` as done; do not suggest `r` for remove).
[ ] Review `textual_widgets/context_footer.py` hints to ensure they describe key bindings (selection actions) vs typed commands distinctly.

## Phase 3 — Documentation Sync (Textual‑only)
[ ] Remove Rich UI references and `--ui rich` from:
    - `readme.md`, `USAGE_GUIDE.md`, `docs/technical/TEXTUAL_QUICKSTART.md`, `MIGRATION_GUIDE.md` (or add a deprecation note).
[ ] Replace prompt_toolkit dropdown/completer narrative with Textual `Suggester` description.
[ ] Standardize “See:” paths for bugfix doc to `docs/history/BUGFIX_COMPREHENSIVE_TEXTUAL_2025.md`.
[ ] Cleanup “Age” sections by deleting the corrupted lines (control chars / stray `\` / `` `n`` fragments) now that corrected lines exist.
[ ] Verify README “Version” section formatting remains correct.

## Phase 4 — Guardrails / Tests
[ ] Add a small unit test (or script in CI) to assert no conflicting one‑letter typed aliases exist for destructive actions.
[ ] Optional: add a script to check docs’ shortcut tables against code truth (BINDINGS + COMMAND_ALIASES).

## Phase 5 — UX Polish
[ ] Verify StatusBar shows two lines without clipping in both themes.
[ ] Footer hints: ensure clarity between “key bindings (selection)” and “typed commands (with args)”.
[ ] Confirm theming docs (theme config path/behavior) align with `core/theme_config.py`.

## Phase 6 — Rich UI Policy
[ ] Remove or clearly mark any remaining Rich UI mentions (e.g., migration guide gets a brief deprecation note).

## Phase 7 — Release Prep
[ ] Update `CHANGELOG.md` for mappings, doc cleanups, and StatusBar fix.
[ ] Bump `VERSION` and `VERSION.md` per policy.

## Acceptance Checklist
[ ] No docs reference `--ui rich` or prompt_toolkit dropdown.
[ ] Docs, footer, and code agree on Option B.
[ ] No single‑letter typed alias for delete or remove; only words (`remove|delete|del`).
[ ] “Age” sections render cleanly with correct examples.
[ ] StatusBar renders two lines in both themes.

