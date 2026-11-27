# Validation receipt

## Graph search follow-up

The user had opened `tools/explorer.html`, the unbuilt template. The template is now named `tools/explorer.template.html`; the old path redirects to `knowledge/explorer.html`. The completed explorer was opened in the built-in browser and its tab appeared in browser inventory. Browser automation still blocks local-file interaction, so rendered-layout verification remains unavailable. All 23 Python tests and the JavaScript handler checks passed, including search results, selecting a result, case-insensitive search with a type filter, zero-result clearing, and resetting search. These checks execute the generated explorer script with a minimal DOM test fixture, not a full browser rendering engine.

Verified on 2026-11-27T20:06:46.695053+00:00.

## Documentation download

- Published pages: 101/101; failures: 0.
- All saved HTML hashes match the download manifest. Complete source archive hash is retained in the manifest.
- Published search text independently confirms the switch, SMB limit, 15-minute trend, ten-minute remote window and Libre dev-only wording.

## Code comparison

- App commit: `0b29cd53415e7f0e668677749cad8daf81c68c2f`; upstream main and v1.0.2 refs matched this commit when checked.
- Pinned text source files: 1180; model settings: 117; reviewed findings: 12.
- Model-property and evidence line numbers resolve to their actual declarations/anchors. All copied code files match their manifest hashes.
- First-party code, tests, Watch/extensions and build files are searchable. Driver Gitlink commits are recorded; driver walkthroughs are not claimed.

## Knowledge graph and question search

- Graph: 1415 unique nodes and 2081 relationships; no dangling edges.
- Search corpus: 5177 passages; SQLite integrity and FTS row counts passed.
- Every indexed passage matches the exact cited local-file line range. Natural-language retrieval found the reviewed IOB answer.
- Explorer JavaScript passed Node syntax checking. Visual browser preview was blocked by the in-app browser local-file URL policy; rendered layout was not visually verified.

## Settings evaluation

- JSON aliases, nested models, duplicate aliases, invalid types/nonfinite numbers, unknown fields, missing values, picker bounds/steps, factor units and mode migration/overrides passed regression checks.
- Synthetic English CSV verified percentage/mg-dL conversion, mode annotations, Dynamic ISF selection, and explicit reporting of unassessed rows. No personal configuration was supplied.

## Overall checks

- 22/22 regression tests passed. Full output: [test-results.txt](test-results.txt).
- All Python tools compiled. Explorer JavaScript syntax passed. `git diff --check` passed (tracked files unchanged).
- Git status contains only the new untracked `TrioKnowledge/` folder. No changes to existing app files, dependencies or settings; nothing committed or published.
