# Questions, settings uploads and updated-document validation

Completed November 27, 2026 against main / v1.0.2 `0b29cd53415e7f0e668677749cad8daf81c68c2f`.

## Questions in the graph

The generated explorer includes a question form, all reviewed findings, the settings catalog and 5,413 evidence passages, including the updated edition. Answers show relevant reviewed statements and source passages with citations; they are extractive retrieval, not arbitrary generated clinical advice. Loaded settings can contribute stored/effective values to a relevant question. Unknown questions explicitly report that no reviewed answer directly covers them.

Handler checks passed for question submission, answer text, citations, selecting graph topics, case/type filters, zero-result clearing, and resetting. The generated file has no unresolved build placeholders.

## Settings export evaluation

CSV/JSON parsing and evaluation execute in browser memory. No network or persistent-storage APIs are used in the browser logic. Files and question answers are not saved automatically; the user can explicitly download a report or clear the loaded state. The UI explains that checks concern types, ranges, dependencies and modes rather than personal dose optimization. Every unsupported row remains visible as unassessed.

All 20 browser/Python parity fixtures passed. They cover aliases, nested models, missing settings, UAM permissions, Basal Testing/LGS effective values, higher thresholds, invalid types, picker limits/steps, percent factors, duplicate aliases, legacy mode migration, CSV unit conversion, mode annotations, version boundaries, quoting and embedded newlines. Ten further parser/question checks passed, including duplicate JSON keys and settings-aware answers.

UI-handler checks passed for selecting a synthetic file, rendering an evaluation, using it in a question, clearing settings/answers, displaying parsing errors and cancelling stale asynchronous file reads. No real personal export was supplied or assessed.

## Full updated document set

The edition includes all 104 original Markdown documents (101 sitemap pages and three includes), plus one new Settings Export guide: **105 rendered documents**. Nineteen source documents are revised/new. All original media/assets are retained with matching hashes. Source snapshots are unchanged.

Every updated page highlights added/revised blocks and includes a complete red/green diff. Combined changes are available in `updated-docs/all-changes.diff` (689 lines). Original-source and updated-source links are retained. Markdown includes resolve, equations render offline as native MathML, and all checked local links/media resolve. The coverage/change manifest identifies each source path and its hash.

Six documentation tests passed: full source/assets retention, sitemap coverage, page rendering/highlights/diffs, local links/assets, actual replacement of incorrect instructions, and offline equation rendering. Repeated builds preserve the same page/change counts.

The set is labeled as a local 1.0.2 alignment draft. Unchanged material, inherited screenshots, external service status and every device procedure have not all been independently validated. This does not represent upstream approval or publication.

## Overall verification and browser status

- 23 knowledge-base tests and six document tests passed: **29 Python tests**.
- 20 browser/Python parity cases, ten additional parser/question checks and the explorer UI-handler checks passed.
- SQLite integrity, graph links, code/evidence hashes and exact citation-line checks passed.
- `git diff --check` passed. Existing app files/dependencies/settings remain unchanged; only `TrioKnowledge/` is untracked. Rendering packages live in the ignored, task-local `.venv-docs` environment.
- The built-in browser inventory confirmed both the updated graph and the full-document index opened, with their expected titles. The graph was reopened with a version query to avoid the prior tab's cached content.
- Browser automation blocks local-file page interaction. Handler tests use a minimal DOM fixture, and document tests inspect rendered HTML; no full browser layout or native file-picker walkthrough is claimed.
