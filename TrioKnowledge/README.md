# Trio documentation and settings knowledge base

This folder contains the latest official TrioDocs material retrieved on **November 27, 2026**, a code comparison against **main / v1.0.2**, and local tools for asking questions and reviewing settings files.

The **updated documentation edition is now the accepted current reference** for the graph, question answers and document search. The active knowledge base contains 105 current documents and neutral reference topics, without documentation mismatch/gap labels or change flags. Earlier source snapshots and comparison reports are retained as history outside the active graph/search corpus. Change highlighting and diffs remain in the updated source documents.

## Start here

- [Ask questions and evaluate a settings file in the graph](knowledge/explorer.html): enter a question or choose an English Trio CSV / settings JSON. Processing happens entirely in browser memory. Answers use cited reviewed findings and retrieved passages; loaded settings can inform configuration questions. Clear settings removes the working report and answers, and downloading an evaluation is optional.
- [Full updated documentation edition](updated-docs/index.html): all 104 original Markdown documents plus a new Settings Export guide, with 19 changed/new pages, highlighted revised blocks and per-page red/green diffs. [All changes](updated-docs/all-changes.diff) and [coverage manifest](updated-docs/manifest.json) are included. This is a local 1.0.2 alignment draft; inherited device procedures/screenshots have not all been revalidated.
- [Historical documentation comparison](review/DOCUMENTATION-UPDATE-REPORT.md): the original findings and evidence used to prepare the accepted updated edition. These are not open mismatch flags in the graph.
- [Interactive knowledge graph](knowledge/explorer.html): open this file in a browser. Search a topic, choose a node, and follow its settings, code, documentation and reviewed findings. It works offline.
- [Official docs source](upstream/source/docs/index.md): all Markdown, images and videos are retained in the original tree.
- [Snapshot manifest](upstream/manifest.json): every downloaded sitemap URL, retrieval time, hashes, and release/source commits.
- [Settings catalog](knowledge/settings-catalog.json): model types/defaults, bundled defaults, picker ranges/steps, serialized keys, and source references. A model default and a bundled default can differ; neither is assumed to be the user's current value.
- [UI label coverage](knowledge/ui-label-coverage.csv): exact-label documentation candidates, explicitly unreviewed.

## Ask questions

Run from `/Users/robertweir/Dev/Trio` with Python 3.9+ and SQLite FTS5; no additional packages or paid API are needed:

```sh
python3 TrioKnowledge/tools/trio_kb.py ask "Does UAM insulin already count when I bolus late?"
python3 TrioKnowledge/tools/trio_kb.py ask "How does Basal Testing change Max IOB and Autosens?"
python3 TrioKnowledge/tools/trio_kb.py ask "What is the difference between Recommended Bolus Percentage and SMB Delivery Ratio?"
python3 TrioKnowledge/tools/trio_kb.py neighbors maxIOB
```

Both the graph question form and `ask` accept natural-language questions and return current reference answers and full-text passages with citations. They use **offline extractive retrieval**, not a hosted chatbot or an LLM that can synthesize an answer to any question. Relevance varies; check the cited passage. Use `--json` on the CLI for structured results. The graph is also available as [JSON nodes and edges](knowledge/graph.json), and [trio.sqlite](knowledge/trio.sqlite) contains current documents, reference topics, pinned code and release notes. Superseded published/source documentation is archived rather than queried.

You can also ask questions in this chat. For future assistants: use the updated edition as the accepted current documentation, run `ask`, and follow its document/code citations. Do not present archived comparison labels as unresolved documentation issues. Keep revision highlights in the source-document edition. Do not infer personal settings from factory defaults or old chat history.

## Evaluate a settings file

```sh
python3 TrioKnowledge/tools/trio_kb.py evaluate /absolute/path/to/TrioSettings.csv
python3 TrioKnowledge/tools/trio_kb.py evaluate /absolute/path/to/settings.json
```

The evaluator accepts the **English Trio Settings CSV export** or a JSON object with stored keys. In Trio use **Settings → Export Settings**, including Metadata, Therapy, Algorithm and Features for a useful review. Non-English headers are rejected; unmapped/localized rows are explicitly listed as unassessed. It recognizes the core dosing/SMB/Autosens/calculator CSV rows, not every schedule, preset or service field. The CSV is a review export, not an import/restore format.

JSON can be flat or nested under `preferences`, `settings` and `pumpSettings`. Use Swift field names, serialized keys such as `max_iob` / `SMBInterval`, or qualified names such as `Preferences.maxIOB`. Percentages in JSON are fractions (80% = `0.8`). Glucose values in JSON use the app's stored mg/dL convention even when display units are mmol/L. English CSV percentage and glucose units are converted using each row's Unit column.

Checks cover supported primitive types/enums, picker bounds/steps, inconsistent Autosens bounds, UAM versus SMB permissions, legacy Closed Loop migration, and stored versus effective values in constrained dosing modes. Reports cite code or reviewed finding IDs. Missing values remain unknown; supplied out-of-range values are retained for review rather than silently repaired. CSV mode annotations are preserved. Output is printed to the terminal; no input settings are uploaded or stored by the tool.

The evaluator reports mechanical behavior and configuration issues. It does not calculate a personal insulin dose, establish clinical suitability, simulate pump operation, or account for absent glucose history, active overrides or treatment records. No personal settings were supplied or assessed in this task. Add a current export for a configuration-specific review.

## Provenance and scope

- App: `0b29cd53415e7f0e668677749cad8daf81c68c2f`, `main`, tag `v1.0.2`; both upstream branch and tag were checked live and matched the clean local checkout. `Config.xcconfig` declares 1.0.2.
- Docs source: `159649de635575ee3f732008dafcff25eb39181c`, `nightscout/trio-docs`, branch `dev`, latest head when captured.
- Website: **101/101 sitemap pages**, with zero download failures, plus its complete live search index. HTML is a faithful evidence snapshot and may still link to remote styles/scripts. The offline graph and local source Markdown are the offline reading entry points; this is not a rebuilt mirror of the website.
- Source repository: **104 docs Markdown files** (101 pages plus three include fragments), with all repository assets and license. Source dev and published website remain separate; the source snapshot is not assumed to be the deployment commit.
- Code snapshot: committed first-party Swift (including tests, Watch and extensions), JSON, JavaScript, documentation, build scripts, configuration and license. Exact source blobs are copied from Git, not the working tree. File hashes and device-driver submodule commits are recorded in [code-manifest.json](knowledge/code-manifest.json). Submodule implementations are not exhaustively indexed or clinically verified.
- Review: corpus-wide collection and search, settings/UI inventories, and targeted manual tracing of the 12 findings. No claim of a sentence-by-sentence audit or full device QA. See the report's remaining review limits.

Upstream content retains its original authorship and licensing: [docs license](upstream/source/LICENSE) and [app license](knowledge/code/LICENSE.txt). Upstream files are unchanged; proposed corrections live in `review/`. No app behavior, dependencies, branch, pump setting, or external documentation was changed.

## Rebuild and verify

```sh
# Rebuild current indexes, catalog and explorer from the updated edition and pinned Git blobs:
python3 TrioKnowledge/tools/build.py
python3 TrioKnowledge/tools/test_kb.py -v
node TrioKnowledge/tools/test_explorer.js
node TrioKnowledge/tools/test_browser_kb.js

# Re-download the current published site and replay the source snapshot pinned inside this script:
python3 TrioKnowledge/tools/snapshot.py
```

`snapshot.py` is a capture/reproduction helper, not an unattended update service. Its docs-source commit is intentionally pinned. To capture a future release, verify the requested app ref and latest docs-source commit, update the pin, save a separate snapshot folder, then rebuild and review factual claims. A new index alone does not revalidate the curated findings.

To regenerate the full highlighted documentation edition, use its isolated rendering tools (the app's dependencies are unaffected):

```sh
python3 -m venv TrioKnowledge/tools/.venv-docs
TrioKnowledge/tools/.venv-docs/bin/python -m pip install -r TrioKnowledge/tools/docs-requirements.txt
TrioKnowledge/tools/.venv-docs/bin/python TrioKnowledge/tools/update_docs.py
TrioKnowledge/tools/.venv-docs/bin/python TrioKnowledge/tools/test_updated_docs.py -v
python3 TrioKnowledge/tools/build.py
```

The edition retains editable Markdown and the full source/assets tree. Its HTML resolves Markdown includes, keeps media local, and renders equations as native MathML without a remote renderer. Yellow blocks mark additions/revisions; removed text is available in each page's diff and `all-changes.diff`. Rebuilding is repeatable from the unchanged upstream snapshot. The graph is a complete single file with its evidence embedded, so it needs no server or API key.

Keep any future personal exports in an external/private location. `TrioKnowledge/private/` is ignored locally if you choose to use it. Generated output and source snapshots are local; nothing has been committed or published.
