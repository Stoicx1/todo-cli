# 30‑Day Roadmap — Execution Plan

- Goal: Make the CLI a local‑first, developer‑friendly task hub with standout focus, ambient capture, and smart UX.
- Scope: Four weekly milestones with shippable value each week.
- Constraints: Keep changes incremental, fast, and reversible. Favor local, privacy‑preserving features.

## Week 1 — Inputs, Filters, Output Hygiene

- Natural‑language add → structured fields
  - Parse quick‑capture syntax: name, tags (`@tag`), priority (`#high|#1`), due (`~tomorrow|~2025‑10‑31`)
  - Map to existing validation + sanitization
  - Graceful fallbacks and clear error messages
  - Success criteria: `add "Fix login" #1 @backend ~tomorrow` creates a valid task

- Context‑aware filter completions (baseline)
  - After `filter ` → suggest `status|priority|tag`
  - After `filter status=` → suggest `done|undone`
  - After `filter priority=` → suggest `1|2|3|high|med|low`
  - After `filter tag=` → suggest existing tags from tag index
  - Success: Keyboard‑only filtering with minimal typing

- Multi‑message status (UX)
  - Render the last 2–3 messages/panels instead of only the last
  - Compact style; never overflow the prompt area

- Unicode output audit
  - Ensure every user‑facing string has `USE_UNICODE` fallbacks
  - Cover: forms, insights/suggest content, help, save/load messages

## Week 2 — Ambient Capture + Reviews

- Git ambient capture (read‑only)
  - Quick actions: `capture git` mines `git status`, `git diff --name-only`, and staged commit messages
  - Heuristics: Turn `TODO:` comments and changed files into suggested tasks (opt‑in)
  - Never writes to git; purely reads and suggests

- Daily/Weekly Review rituals
  - `/review daily` and `/review weekly` guided prompts
  - Output a clean Markdown report (wins, stuck, next actions)
  - Save to `review-YYYY-MM-DD.md` in project dir

## Week 3 — Focus Engine + Dedupe

- Focus Session mode
  - Command: `focus 25` (Pomodoro minutes), queue = current filter/sort
  - Minimal UI (timer, current task, next up), pause/skip/complete
  - Session summary appended to the task as a note

- Duplicate detector + merge
  - Fuzzy matching by normalized title + tags
  - `dedupe` lists candidates; `merge <id> <id>` consolidates fields and tags safely

## Week 4 — Calendar Export + Templates

- Calendar export (ICS)
  - Select tasks → export as `.ics` (time‑blocking)
  - No online calendar integration; file export only

- Smart templates
  - Built‑in templates: Bug, Spike, Chore
  - `new bug` → interactive checklist scaffold (repro → fix → test → PR)

---

## Deliverables & Success Criteria

- Week 1: NL add (MVP), smarter filter completions, multi‑message status, full Unicode hardening
- Week 2: Git capture (read‑only, safe), daily/weekly review with Markdown export
- Week 3: Focus Session (usable), duplicate detector + safe merge
- Week 4: ICS export (basic), templates with checklists

---

## UX Principles

- Keyboard‑first, instant feedback (no spinners unless doing I/O)
- Consistent messages via state (panels or lines), not transient prints
- Configurable, but sensible defaults; preferences persist locally

---

## Risks & Mitigations

- Terminal compatibility (Windows cp1252): audit all outputs, fallback to ASCII
- Scope creep in ambient capture: keep read‑only, add flags to gate heuristics
- Performance with large repos: time‑box capture operations, show partial results

---

## Tracking Checklist

- [ ] W1: NL add parser and mapping
- [ ] W1: Filter completions (status/priority/tags)
- [ ] W1: Multi‑message status rendering
- [ ] W1: Unicode audit complete
- [ ] W2: Git ambient capture (read‑only)
- [ ] W2: Daily/Weekly review flows + Markdown export
- [ ] W3: Focus Session (timer, queue, summary)
- [ ] W3: Duplicate detector and merge flow
- [ ] W4: ICS export for selected tasks
- [ ] W4: Smart templates (Bug/Spike/Chore)

---

## Verification Snippets

- Filter completion: type `filter ` → should see field suggestions
- NL add: `add "Fix login" #1 @backend ~tomorrow`
- Focus: `focus 25` → timer appears; `skip`/`pause` works
- Reviews: `/review weekly` → `review-YYYY-MM-DD.md` created
- Export: `export ics 3,5,9` → `tasks.ics` created

