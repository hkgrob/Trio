#!/usr/bin/env python3
"""Capture the published TrioDocs sitemap and pin its upstream source (stdlib only)."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'upstream'
DOCS_SHA = '159649de635575ee3f732008dafcff25eb39181c'


def fetch(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Trio-local-documentation-snapshot/1.0'}), timeout=90) as response:
                return response.read(), response.geturl(), dict(response.headers)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def page(url):
    data, final, headers = fetch(url)
    relative = url.removeprefix('https://triodocs.org/').strip('/')
    path = BASE / 'published' / relative / 'index.html'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {'url': url, 'resolved_url': final, 'path': str(path.relative_to(ROOT)),
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            'etag': headers.get('ETag'), 'last_modified': headers.get('Last-Modified')}


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    sitemap, _, _ = fetch('https://triodocs.org/sitemap.xml')
    (BASE / 'sitemap.xml').write_bytes(sitemap)
    urls = [x.text for x in ET.fromstring(sitemap).findall('{*}url/{*}loc')]
    records, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        jobs = {pool.submit(page, url): url for url in urls}
        for job in concurrent.futures.as_completed(jobs):
            try:
                records.append(job.result())
            except Exception as error:
                failures.append({'url': jobs[job], 'error': str(error)})
    # Preserve the site's complete published search corpus as a second independent record.
    data, _, _ = fetch('https://triodocs.org/search/search_index.json')
    (BASE / 'search_index.json').write_bytes(data)
    archive = BASE / 'trio-docs-source.tar.gz'
    if not archive.exists():
        data, _, _ = fetch(f'https://codeload.github.com/nightscout/trio-docs/tar.gz/{DOCS_SHA}')
        archive.write_bytes(data)
    destination = BASE / 'source'
    destination.mkdir(exist_ok=True)
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            parts = Path(member.name).parts[1:]
            if not parts:
                continue
            target = destination.joinpath(*parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Archive path escapes destination')
            if member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle.extractfile(member).read())
    git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT.parent, text=True).strip()
    manifest = {'retrieved_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'site': 'https://triodocs.org/', 'docs_source_commit': DOCS_SHA,
                'docs_source_branch': 'dev', 'app_commit': git('rev-parse', 'HEAD'),
                'app_branch': git('branch', '--show-current'), 'app_tag': git('describe', '--exact-match', '--tags'),
                'sitemap_count': len(urls), 'downloaded_count': len(records),
                'source_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'pages': sorted(records, key=lambda x: x['url']), 'failures': failures,
                'scope': 'Every sitemap page as HTML; full published search index; complete pinned source including images. HTML is an evidence snapshot, not a standalone offline website.'}
    (BASE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'pages'}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
