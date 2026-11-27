#!/usr/bin/env python3
"""Regression checks for source provenance, retrieval, and evaluation boundaries."""
import csv
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import trio_kb as kb


class KnowledgeTests(unittest.TestCase):
    def test_explorer_entrypoints_use_built_graph(self):
        built = (kb.ROOT / 'knowledge/explorer.html').read_text()
        self.assertNotIn('__GRAPH__', built)
        self.assertNotIn('__FACTS__', built)
        self.assertIn('const data={', built)
        entrypoint = (kb.ROOT / 'tools/explorer.html').read_text()
        self.assertIn('url=../knowledge/explorer.html', entrypoint)
        self.assertIn('explorer.template.html', (kb.ROOT / 'tools/build.py').read_text())

    def evaluate(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text(json.dumps(data))
            return kb.evaluate(path)

    def codes(self, report):
        return {f['code'] for f in report['findings']}

    def test_snapshot_coverage_and_hashes(self):
        manifest = json.loads((kb.ROOT / 'upstream/manifest.json').read_text())
        self.assertEqual(manifest['sitemap_count'], manifest['downloaded_count'])
        self.assertFalse(manifest['failures'])
        for item in manifest['pages']:
            self.assertEqual(hashlib.sha256((kb.ROOT / item['path']).read_bytes()).hexdigest(), item['sha256'])

    def test_graph_has_no_dangling_edges(self):
        graph = kb.read('graph.json')
        ids = {n['id'] for n in graph['nodes']}
        self.assertEqual(len(ids), len(graph['nodes']))
        self.assertTrue(all(e['from'] in ids and e['to'] in ids for e in graph['edges']))

    def test_graph_uses_current_docs_without_review_flags(self):
        graph = kb.read('graph.json')
        self.assertEqual(graph['documentation_basis'], 'updated-docs/source/docs')
        documents = [n for n in graph['nodes'] if n['kind'] == 'document']
        self.assertEqual(len(documents), 105)
        self.assertTrue(all(n['path'].startswith('updated-docs/site/') for n in documents))
        self.assertTrue(all(n['kind'] not in ('verified-mismatch', 'verified-gap', 'verified-behavior', 'updated-document') for n in graph['nodes']))
        self.assertTrue(all('changed' not in n for n in graph['nodes']))
        self.assertTrue(all(e['relation'] not in ('revises', 'addresses') for e in graph['edges']))
        self.assertTrue(all(f['status'] == 'current' and 'update' not in f for f in kb.read('facts.json')))
        with closing(sqlite3.connect(kb.ROOT / 'knowledge/trio.sqlite')) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM chunks WHERE kind IN ('published','docs-source','verified-fact','updated-docs')").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(DISTINCT path) FROM chunks WHERE kind='current-document'").fetchone()[0], 105)

    def test_source_document_change_highlights_are_retained(self):
        edition = kb.ROOT / 'updated-docs'
        manifest = json.loads((edition / 'manifest.json').read_text())
        for page in manifest['pages']:
            self.assertEqual(hashlib.sha256((edition / 'source/docs' / page['path']).read_bytes()).hexdigest(), page['sha256'])
            if page['changed']:
                self.assertIn('data-change="added-or-revised"', (edition / page['html']).read_text())
                self.assertTrue((edition / 'diffs' / (page['path'] + '.diff')).is_file())

    def test_fact_evidence_lines_match_anchors(self):
        for fact in kb.read('facts.json'):
            for ref in fact['evidence']:
                lines = (kb.ROOT / ref['local_path']).read_text().splitlines()
                self.assertIn(ref['anchor'], lines[ref['line'] - 1])

    def test_catalog_contains_only_properties_of_its_declared_model(self):
        fields = kb.read('settings-catalog.json')
        self.assertNotIn('TrioSettings.stringValue', {f['id'] for f in fields})
        for field in fields:
            line = (kb.ROOT / 'knowledge/code' / field['source']).read_text().splitlines()[field['line'] - 1]
            self.assertIn(field['name'] + ':', line)

    def test_database_integrity(self):
        with closing(sqlite3.connect(kb.ROOT / 'knowledge/trio.sqlite')) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('SELECT count(*) FROM chunks').fetchone(), db.execute('SELECT count(*) FROM search').fetchone())

    def test_retrieved_passage_line_numbers_are_real(self):
        with closing(sqlite3.connect(kb.ROOT / 'knowledge/trio.sqlite')) as db:
            texts = {}
            for path, start, end, passage in db.execute('SELECT path,start_line,end_line,text FROM chunks'):
                if path not in texts:
                    texts[path] = (kb.ROOT / path).read_text().splitlines()
                self.assertEqual('\n'.join(texts[path][start - 1:end]), passage)

    def test_code_snapshot_hashes(self):
        manifest = kb.read('code-manifest.json')
        for entry in manifest['files']:
            self.assertEqual(hashlib.sha256((kb.ROOT / 'knowledge/code' / entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_iob_question_finds_verified_answer(self):
        self.assertEqual(kb.ask('Does UAM insulin already count when I bolus late?')['answers'][0]['id'], 'F11')

    def test_query_punctuation_cannot_break_fts(self):
        self.assertTrue(kb.ask('"SMB" OR -- (interval)?')['evidence'])

    def test_empty_question_is_handled(self):
        self.assertFalse(kb.ask('???')['answers'])

    def test_persisted_aliases_and_model_qualified_keys(self):
        result = self.evaluate({'preferences': {'max_iob': 0, 'SMBInterval': 3}, 'settings': {'dosingMode': 'closed'}})
        self.assertEqual(result['provided_valid_values']['smbInterval'], 3)
        self.assertEqual(result['errors'], 0)

    def test_missing_values_are_not_defaulted(self):
        result = self.evaluate({'enableUAM': True})
        self.assertNotIn('maxIOB', result['effective_known_values'])
        self.assertIn('smb-permission-unknown', self.codes(result))
        self.assertIn('mode-missing', self.codes(result))

    def test_unknown_input_is_explicitly_unassessed(self):
        result = self.evaluate({'notASetting': 100})
        self.assertEqual(result['unassessed'][0]['name'], 'notASetting')
        self.assertIn('nothing-evaluated', self.codes(result))

    def test_all_disabled_smb_conditions_are_distinct_from_missing(self):
        result = self.evaluate(dict(enableUAM=True, enableSMBAlways=False, enableSMBWithCOB=False, enableSMBAfterCarbs=False, enableSMBWithTemptarget=False, enableSMB_high_bg=False))
        self.assertIn('uam-without-smb-permission', self.codes(result))

    def test_basal_testing_effective_values_preserve_stored(self):
        result = self.evaluate(dict(dosingMode='basalTesting', maxIOB=5, autosensMin=0.7, autosensMax=1.2, useNewFormula=True, sigmoid=True, threshold_setting=60))
        self.assertEqual(result['provided_valid_values']['maxIOB'], 5)
        self.assertEqual(result['effective_known_values']['maxIOB'], 0)
        self.assertEqual(result['effective_known_values']['threshold_setting'], 72)
        self.assertFalse(result['effective_known_values']['useNewFormula'])

    def test_basal_testing_keeps_higher_threshold(self):
        self.assertEqual(self.evaluate(dict(dosingMode='basalTesting', threshold_setting=90))['effective_known_values']['threshold_setting'], 90)

    def test_types_and_nonfinite_values_are_rejected(self):
        self.assertEqual(self.evaluate({'enableUAM': 'true', 'SMBInterval': True, 'maxIOB': float('nan')})['errors'], 3)

    def test_picker_minimum_and_step(self):
        self.assertNotIn('outside-picker-range', self.codes(self.evaluate({'maxSMBBasalMinutes': 15})))
        self.assertIn('outside-picker-range', self.codes(self.evaluate({'maxSMBBasalMinutes': 10})))
        self.assertIn('off-picker-step', self.codes(self.evaluate({'maxSMBBasalMinutes': 16})))

    def test_factor_uses_stored_fraction_not_display_percent(self):
        self.assertNotIn('outside-picker-range', self.codes(self.evaluate({'overrideFactor': 0.8})))
        self.assertIn('outside-picker-range', self.codes(self.evaluate({'overrideFactor': 80})))

    def test_duplicate_alias_is_reported(self):
        self.assertIn('duplicate-setting', self.codes(self.evaluate({'maxIOB': 1, 'max_iob': 2})))

    def test_new_dosing_mode_takes_precedence_over_legacy(self):
        result = self.evaluate({'dosingMode': 'open', 'closedLoop': True})
        self.assertEqual(result['provided_valid_values']['dosingMode'], 'open')
        self.assertEqual(self.evaluate({'closedLoop': True})['provided_valid_values']['dosingMode'], 'closed')

    def test_english_csv_units_annotations_and_unassessed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.csv'
            with path.open('w', newline='', encoding='utf-8-sig') as handle:
                writer = csv.writer(handle)
                writer.writerows([
                    ['Setting Category', 'Subcategory', 'Setting Name', 'Value', 'Unit'],
                    ['Metadata', '', 'Dosing Mode', 'Basal Testing', ''],
                    ['Therapy', '', 'Maximum Insulin on Board (IOB)', '5 (mode is using 0)', 'U'],
                    ['Features', '', 'Recommended Bolus Percentage', '80', '%'],
                    ['Therapy', '', 'Minimum Safety Threshold', '4.0', 'mmol/L'],
                    ['Algorithm', '', 'Dynamic ISF', 'Logarithmic (mode is using Disabled)', ''],
                    ['Therapy', '', 'Basal Rate', '0.7', 'U/hr']])
            result = kb.evaluate(path)
            self.assertEqual(result['errors'], 0)
            self.assertEqual(result['provided_valid_values']['overrideFactor'], 0.8)
            self.assertEqual(result['provided_valid_values']['threshold_setting'], 72)
            self.assertTrue(result['provided_valid_values']['useNewFormula'])
            self.assertFalse(result['effective_known_values']['useNewFormula'])
            self.assertEqual(len(result['unassessed']), 1)


if __name__ == '__main__':
    unittest.main()
