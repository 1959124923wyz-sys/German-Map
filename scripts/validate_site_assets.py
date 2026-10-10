#!/usr/bin/env python3
"""Check published HTML dependencies without running any data rebuild.

No network, no external HTML parser, no rewriting of source files.
This is intentionally format-independent: it works for every map topic and
will pick up a future finance/index.html without changing a hardcoded count.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / 'index.html'] + sorted((ROOT / 'topics').glob('*/index.html'))


class References(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.assets: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        fields = dict(attrs)
        if tag == 'script' and fields.get('src'):
            self.assets.append(('script', fields['src']))
        elif tag == 'link' and fields.get('href'):
            if 'stylesheet' in (fields.get('rel') or '').lower().split():
                self.assets.append(('stylesheet', fields['href']))
        elif tag == 'a' and fields.get('href'):
            self.assets.append(('link', fields['href']))


def target_for(page: Path, reference: str) -> Path | None:
    ref = urlsplit(reference.strip())
    if ref.scheme or ref.netloc or not ref.path or reference.startswith('//'):
        return None
    dest = ((ROOT / ref.path.lstrip('/')) if ref.path.startswith('/')
            else (page.parent / unquote(ref.path))).resolve()
    if not dest.is_relative_to(ROOT):
        raise AssertionError(f'Local reference escapes repository: {page}: {reference}')
    if dest.is_dir() or ref.path.endswith('/'):
        dest = dest / 'index.html'
    return dest


def main() -> None:
    assert PAGES and (ROOT / 'index.html') in PAGES
    checks = 0
    for page in PAGES:
        parser = References()
        parser.feed(page.read_text(encoding='utf-8'))
        for kind, ref in parser.assets:
            dest = target_for(page, ref)
            if dest is None:
                continue
            assert dest.is_file(), f'{page.relative_to(ROOT)} {kind} missing: {ref}'
            checks += 1
        print(f'PASS {page.relative_to(ROOT)} dependencies')
    railway = ROOT / 'topics/railway/index.html'
    if railway.exists():
        parser = References()
        parser.feed(railway.read_text(encoding='utf-8'))
        scripts = [urlsplit(ref).path for kind, ref in parser.assets if kind == 'script']
        a, b, c, d, e = ('js/rail-geometry.js', 'js/rail-analysis.js', 'js/rail-service-groups.js', 'js/rail-picker.js', 'overview.js')
        assert all(p in scripts for p in (a, b, c, d, e))
        assert scripts.index(a) < scripts.index(b) < scripts.index(c) < scripts.index(d) < scripts.index(e), scripts
    print(f'SUCCESS {len(PAGES)} published pages, {checks} local dependencies verified')


if __name__ == '__main__':
    main()
