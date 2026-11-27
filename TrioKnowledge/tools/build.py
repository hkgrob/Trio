#!/usr/bin/env python3
"""Rebuild the version-pinned catalog, retrieval database, and evidence graph."""
import hashlib
import csv
import json
from pathlib import Path
import re
import sqlite3
import subprocess

from current_knowledge import load_facts
from export_schema import export_fields

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = ROOT / 'knowledge'


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    manifest = json.loads((ROOT / 'upstream/manifest.json').read_text())
    sha = manifest['app_commit']
    OUT.mkdir(exist_ok=True)
    # Read committed blobs, not potentially edited working-copy files.
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', sha], cwd=REPO, text=True).splitlines()
    paths = [p for p in paths if p.endswith(('.swift', '.json', '.md', '.js', '.py', '.sh', '.xcconfig', '.yml', '.yaml'))
             or p in ('.gitmodules', 'LICENSE.txt', 'Trio.xcodeproj/project.pbxproj')]
    source = {}
    for path in paths:
        raw = subprocess.check_output(['git', 'show', f'{sha}:{path}'], cwd=REPO)
        text = raw.decode('utf-8')
        local = OUT / 'code' / path
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(raw)
        source[path] = text
    tree = subprocess.check_output(['git', 'ls-tree', '-r', sha], cwd=REPO, text=True).splitlines()
    dump(OUT / 'code-manifest.json', {'commit': sha,
         'files': [{'path': p, 'sha256': hashlib.sha256(t.encode()).hexdigest()} for p, t in source.items()],
         'submodules': [{'path': row.split('\t', 1)[1], 'commit': row.split()[2]} for row in tree if row.startswith('160000 ')]})
    catalog = []
    picker_path = 'Trio/Sources/Models/DecimalPickerSettings.swift'
    pickers = {}
    for match in re.finditer(r'var (\w+) = PickerSetting\((.*?)\)', source[picker_path], re.S):
        fields = dict(re.findall(r'(value|step|min|max):\s*(-?[\d.]+)', match[2]))
        kind = re.search(r'PickerSettingType\.(\w+)', match[2])
        if len(fields) == 4:
            pickers[match[1]] = {**{k: float(v) for k, v in fields.items()},
                                 'unit_type': kind[1] if kind else None,
                                 'source': picker_path, 'line': source[picker_path][:match.start()].count('\n') + 1}
    for model in ('Preferences', 'TrioSettings', 'PumpSettings'):
        path = f'Trio/Sources/Models/{model}.swift'
        text = source[path]
        mappings = dict(re.findall(r'case (\w+) = "([^"]+)"', text))
        model_start = text.index('struct ' + model)
        header = text[model_start:].split('\n}', 1)[0]
        for match in re.finditer(r'^    (?:var|let) (\w+): ([\w?]+)(?: = ([^\n]+))?$', header, re.M):
            name, typ, literal = match.groups()
            literal = literal.strip() if literal else None
            try:
                default = json.loads(literal) if literal else None
            except ValueError:
                default = literal
            catalog.append({'id': f'{model}.{name}', 'name': name, 'json_key': mappings.get(name, name),
                            'model': model, 'type': typ, 'model_default': default,
                            'source': path, 'line': text[:model_start + match.start()].count('\n') + 1,
                            'picker': pickers.get('dia' if name == 'insulinActionCurve' else name), 'ui_references': [], 'docs_candidates': []})
    for entry in catalog:
        defaults_path = {'Preferences': 'Trio/Resources/json/defaults/preferences.json',
                         'TrioSettings': 'Trio/Resources/json/defaults/freeaps/freeaps_settings.json',
                         'PumpSettings': 'Trio/Resources/json/defaults/settings/settings.json'}[entry['model']]
        defaults = json.loads(source[defaults_path])
        entry['bundled_default_present'] = entry['json_key'] in defaults
        entry['bundled_default'] = defaults.get(entry['json_key'])
        entry['bundled_defaults_source'] = defaults_path
        # A reference is lexical evidence, not a claim that every field is user-editable.
        token = re.compile(r'\b' + re.escape(entry['name']) + r'\b')
        for path, text in source.items():
            if '/Modules/' not in path or '/View/' not in path:
                continue
            hits = [i for i, line in enumerate(text.splitlines(), 1) if token.search(line)]
            if hits:
                entry['ui_references'].append({'path': path, 'lines': hits})
    # Inventory labels, including controls not stored in these three models.
    labels = []
    for path, text in source.items():
        if '/Modules/' not in path or '/View/' not in path:
            continue
        for m in re.finditer(r'(?:label:\s*(?:String\(\s*localized:\s*|Text\(\s*))"([^"\n]+)"', text):
            labels.append({'label': m[1], 'source': path, 'line': text[:m.start()].count('\n') + 1})
    dump(OUT / 'ui-labels.json', labels)
    docs = []
    current_root = ROOT / 'updated-docs/source/docs'
    if not current_root.is_dir():
        raise ValueError('Build the updated documentation edition before rebuilding knowledge.')
    for path in sorted(current_root.rglob('*.md')):
        relative = str(path.relative_to(current_root))
        text = path.read_text().split('\n## 1.0.2 source references', 1)[0]
        docs.append({'id': 'doc:' + relative, 'kind': 'current-document',
                     'path': str(path.relative_to(ROOT)),
                     'url': '../updated-docs/site/' + str(Path(relative).with_suffix('.html')),
                     'title': next((l.lstrip('# ') for l in text.splitlines() if l.startswith('# ')), Path(relative).stem.replace('-', ' ').title()),
                     'text': text})
    for entry in catalog:
        phrases = [entry['name'], entry['json_key']]
        for d in docs:
            if any(re.search(r'\b' + re.escape(p) + r'\b', d['text'], re.I) for p in phrases):
                entry['docs_candidates'].append(d['path'])
    with (OUT / 'ui-label-coverage.csv').open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['UI label', 'Code path', 'Line', 'Documentation candidate paths', 'Review status'])
        normalize = lambda s: re.sub(r'[^a-z0-9 ]', '', re.sub(r'\s+', ' ', s.lower()))
        for item in labels:
            label = normalize(item['label'])
            matches = [d['path'] for d in docs if len(label) >= 5 and label in normalize(d['text'])]
            writer.writerow([item['label'], item['source'], item['line'], '; '.join(matches), 'Lexical match only' if matches else 'No exact label match; manual review needed'])
    dump(OUT / 'settings-catalog.json', catalog)
    export_mapping = export_fields(source['Trio/Sources/Modules/SettingsExport/SettingsExportStateModel.swift'], catalog)
    dump(OUT / 'export-fields.json', export_mapping)
    facts = load_facts(ROOT)
    for fact in facts:
        for ref in fact['evidence']:
            text = source.get(ref['path'])
            if text is None:
                text = (ROOT / ref['path']).read_text()
            anchor = ref['anchor']
            if anchor not in text:
                raise ValueError(f"Missing evidence anchor: {fact['id']} {ref}")
            ref['line'] = text[:text.index(anchor)].count('\n') + 1
            ref['local_path'] = ('knowledge/code/' + ref['path']) if ref['path'] in source else ref['path']
            if ref['path'] in source:
                ref['url'] = f"https://github.com/nightscout/Trio/blob/{sha}/{ref['path']}#L{ref['line']}"
            else:
                relative = ref['path'].removeprefix('updated-docs/source/docs/')
                ref['url'] = '../updated-docs/site/' + str(Path(relative).with_suffix('.html'))
    dump(OUT / 'facts.json', facts)
    for fact in facts:
        answer_path = OUT / 'answers' / (fact['id'] + '.md')
        answer_path.parent.mkdir(exist_ok=True)
        answer_path.write_text('# ' + fact['title'] + '\n\n' + fact['answer'] + '\n\n' + '\n'.join(f"- {r['url']}" for r in fact['evidence']) + '\n')
    dbpath = OUT / 'trio.sqlite'
    if dbpath.exists():
        dbpath.unlink()
    db = sqlite3.connect(dbpath)
    db.execute('CREATE TABLE chunks(id INTEGER PRIMARY KEY, kind TEXT, title TEXT, path TEXT, url TEXT, start_line INTEGER, end_line INTEGER, text TEXT)')
    db.execute("CREATE VIRTUAL TABLE search USING fts5(title, text, content='chunks', content_rowid='id', tokenize='porter unicode61')")
    def add(kind, title, path, url, text):
        lines = text.splitlines()
        for start in range(0, len(lines), 65):
            end = min(start + 85, len(lines))
            body = '\n'.join(lines[start:end])
            cursor = db.execute('INSERT INTO chunks(kind,title,path,url,start_line,end_line,text) VALUES(?,?,?,?,?,?,?)', (kind, title, path, url, start + 1, end, body))
            db.execute('INSERT INTO search(rowid,title,text) VALUES(?,?,?)', (cursor.lastrowid, title, body))
    for doc in docs:
        add(doc['kind'], doc['title'], doc['path'], doc['url'], doc['text'])
    for path, text in source.items():
        add('code', Path(path).name, 'knowledge/code/' + path, f'https://github.com/nightscout/Trio/blob/{sha}/{path}', text)
    for fact in facts:
        path = 'knowledge/answers/' + fact['id'] + '.md'
        add('current-reference', fact['title'], path, fact['evidence'][0]['url'], (ROOT / path).read_text())
    release = ROOT / 'upstream/release-v1.0.2.md'
    if release.exists():
        add('official-release', 'Trio v1.0.2 release notes', str(release.relative_to(ROOT)), 'https://github.com/nightscout/Trio/releases/tag/v1.0.2', release.read_text())
    db.commit()
    nodes, edges = [], []
    def node(id, kind, label, **extra):
        nodes.append({'id': id, 'kind': kind, 'label': label, **extra})
    node('release:1.0.2', 'release', 'Trio 1.0.2 main', commit=sha)
    node('snapshot:docs', 'snapshot', 'Trio 1.0.2 documentation', source='updated-docs/source/docs')
    for doc in docs:
        node(doc['id'], 'document', doc['title'], path='updated-docs/site/' + str(Path(doc['path'].removeprefix('updated-docs/source/docs/')).with_suffix('.html')))
        edges.append({'from': 'snapshot:docs', 'to': doc['id'], 'relation': 'contains'})
    for path in source:
        node('code:' + path, 'code', Path(path).name, path='knowledge/code/' + path,
             url=f'https://github.com/nightscout/Trio/blob/{sha}/{path}')
        edges.append({'from': 'release:1.0.2', 'to': 'code:' + path, 'relation': 'contains'})
    for item in catalog:
        node(item['id'], 'setting', item['name'], json_key=item['json_key'], default=item['model_default'])
        edges.append({'from': item['id'], 'to': 'code:' + item['source'], 'relation': 'declared_in'})
        edges.append({'from': item['id'], 'to': 'release:1.0.2', 'relation': 'present_in'})
        for ref in item['ui_references']:
            edges.append({'from': item['id'], 'to': 'code:' + ref['path'], 'relation': 'referenced_in_ui'})
        for ref in item['docs_candidates']:
            edges.append({'from': item['id'], 'to': 'doc:' + ref.removeprefix('updated-docs/source/docs/'), 'relation': 'referenced_in_documentation'})
    for fact in facts:
        node(fact['id'], 'topic', fact['title'], answer=fact['answer'])
        for ref in fact['evidence']:
            target = 'code:' + ref['path'] if ref['path'] in source else 'doc:' + ref['path'].removeprefix('updated-docs/source/docs/')
            if target in {n['id'] for n in nodes}:
                edges.append({'from': fact['id'], 'to': target, 'relation': 'evidenced_by', 'line': ref['line']})
        for setting in fact.get('settings', []):
            if setting not in {n['id'] for n in nodes}:
                raise ValueError('Unknown setting ' + setting)
            edges.append({'from': fact['id'], 'to': setting, 'relation': 'explains'})
    for a, relation, b in [('TrioSettings.overrideFactor', 'scales_manual_recommendation_separately_from', 'Preferences.smbDeliveryRatio'),
                           ('TrioSettings.dosingMode', 'overrides_effective_value_of', 'Preferences.maxIOB'),
                           ('Preferences.autosensMin', 'must_not_exceed', 'Preferences.autosensMax'),
                           ('Preferences.enableUAM', 'does_not_itself_enable', 'Preferences.enableSMBAlways')]:
        edges.append({'from': a, 'to': b, 'relation': relation, 'basis': 'Current documentation and source references'})
    graph = {'release': sha, 'documentation_basis': 'updated-docs/source/docs', 'nodes': nodes, 'edges': edges}
    dump(OUT / 'graph.json', graph)
    # Single-file offline explorer with embedded graph; no server, CDN or account required.
    template = (ROOT / 'tools/explorer.template.html').read_text()
    db.row_factory = sqlite3.Row
    corpus = [dict(row) for row in db.execute('SELECT kind,title,path,url,start_line,end_line,text FROM chunks')]
    substitutions = {'__GRAPH__': graph, '__FACTS__': facts, '__CATALOG__': catalog, '__CORPUS__': corpus, '__EXPORT_FIELDS__': export_mapping}
    for marker, payload in substitutions.items():
        template = template.replace(marker, json.dumps(payload).replace('<', '\\u003c'))
    template = template.replace('__BROWSER_CORE__', (ROOT / 'tools/browser-kb.js').read_text())
    template = template.replace('__CONFIG_REVIEW__', (ROOT / 'tools/configuration-review.js').read_text())
    template = template.replace('__APP_UI__', (ROOT / 'tools/explorer-app.js').read_text())
    (OUT / 'explorer.html').write_text(template)
    stats = {'app_commit': sha, 'docs_source_commit': manifest['docs_source_commit'], 'source_documents': len(docs), 'documentation_basis': 'updated-docs/source/docs',
             'published_pages': manifest['downloaded_count'], 'pinned_code_files': len(source), 'settings': len(catalog),
             'ui_label_occurrences': len(labels), 'facts': len(facts), 'graph_nodes': len(nodes), 'graph_edges': len(edges),
             'search_chunks': db.execute('SELECT count(*) FROM chunks').fetchone()[0]}
    dump(OUT / 'build-summary.json', stats)
    db.close()
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
