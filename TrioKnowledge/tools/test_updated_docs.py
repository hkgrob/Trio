#!/usr/bin/env python3
"""Verify full-edition coverage, real edits, highlights, diffs and local assets."""
import hashlib
import json
from pathlib import Path
import unittest

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / 'updated-docs'


class UpdatedDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((EDITION / 'manifest.json').read_text())
        cls.pages = cls.manifest['pages']

    def test_all_original_documents_and_assets_retained(self):
        upstream = ROOT / 'upstream/source/docs'
        for source in upstream.rglob('*'):
            if not source.is_file():
                continue
            copied = EDITION / 'source/docs' / source.relative_to(upstream)
            self.assertTrue(copied.is_file(), str(source))
            if source.suffix != '.md':
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), hashlib.sha256(copied.read_bytes()).digest())
        self.assertEqual(len(self.pages), 105)
        self.assertEqual(sum(p.get('new_page', False) for p in self.pages), 1)

    def test_every_sitemap_page_is_in_edition(self):
        routes = set()
        for page in self.pages:
            path = page['path'][:-3]
            route = '' if path == 'index' else path.removesuffix('/index')
            routes.add('https://triodocs.org/' + (route + '/' if route else ''))
        for page in json.loads((ROOT / 'upstream/manifest.json').read_text())['pages']:
            self.assertIn(page['url'], routes)

    def test_every_page_renders_and_each_changed_page_has_diff(self):
        for page in self.pages:
            rendered = BeautifulSoup((EDITION / page['html']).read_text(), 'html.parser')
            self.assertIsNotNone(rendered.find('article'), page['path'])
            self.assertIsNotNone(rendered.find(id='toggle'), page['path'])
            self.assertNotIn('{% include-markdown', rendered.find('article').get_text())
            self.assertNotIn('<!--include-markdown', rendered.find('article').get_text())
            source = EDITION / 'source/docs' / page['path']
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), page['sha256'])
            if page['changed']:
                self.assertTrue(rendered.select('.changed-block'), page['path'])
                diff = EDITION / 'diffs' / (page['path'] + '.diff')
                self.assertTrue(diff.is_file(), page['path'])
                self.assertIn('@@', diff.read_text(), page['path'])
            elif page['original_sha256']:
                self.assertEqual(page['sha256'], page['original_sha256'])

    def test_zero_local_link_and_asset_failures(self):
        self.assertEqual(self.manifest['inherited_link_issues'], [])
        for page in self.pages:
            path = EDITION / page['html']
            soup = BeautifulSoup(path.read_text(), 'html.parser')
            for element in soup.find_all(['a', 'img', 'source', 'video']):
                url = element.get('href' if element.name == 'a' else 'src')
                if not url or url.startswith(('#', 'https:', 'http:', 'mailto:', 'tel:', 'data:')):
                    continue
                target = path.parent / url.split('#', 1)[0]
                self.assertTrue(target.exists(), page['path'] + ': ' + url)

    def test_equations_render_offline_as_mathml(self):
        page = BeautifulSoup((EDITION / 'site/configuration/settings/therapy/units-limits.html').read_text(), 'html.parser')
        self.assertTrue(page.find_all('math'))
        self.assertFalse(page.select('script[type^="math/tex"]'))

    def test_actual_incorrect_instructions_are_replaced(self):
        docs = EDITION / 'source/docs'
        closed = (docs / 'configuration/settings/closed-loop.md').read_text()
        self.assertIn('four-option picker', closed)
        self.assertNotIn('configure the following settings as such', closed)
        remote = (docs / 'configuration/settings/features/remote-control.md').read_text()
        self.assertNotIn('Recent bolus (8 minutes ago)', remote)
        self.assertIn('greater than or equal to 20%', remote)
        self.assertIn('default six-minute lookback', remote)
        smb = (docs / 'configuration/settings/algorithm/smb-settings.md').read_text()
        self.assertEqual(smb.count('15-180 minutes (5-minute steps)'), 2)
        self.assertNotIn('**Setting Limits:** _30-180 minutes_', smb)
        calculator = (docs / 'usage/features/bolus-calculator.md').read_text()
        self.assertNotIn('changed over the last 15 minutes', calculator)
        self.assertIn('newer than 20 minutes ago', calculator)
        self.assertIn('Backdated carbohydrate entries', calculator)
        self.assertTrue((docs / 'configuration/settings/export-settings.md').is_file())


if __name__ == '__main__':
    unittest.main()
