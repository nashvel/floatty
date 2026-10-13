#!/usr/bin/env python3
"""Build and validate the standalone GitHub Pages site without dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'dist/site'

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()
    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                raise ValueError('Duplicate HTML id: ' + attrs['id'])
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])


def validate(root):
    pages = {}
    for path in root.rglob('*.html'):
        parser = Page()
        parser.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()] = parser
    if not pages or (root / 'index.html').resolve() not in pages:
        raise ValueError('Missing index.html')
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            if url.path.startswith('/'):
                raise ValueError('Use relative links for GitHub project Pages: ' + link)
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(root.resolve()):
                raise ValueError('Link escapes site: ' + link)
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                raise ValueError('Broken local link: ' + link)
            if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                raise ValueError('Missing anchor: ' + link)
    print(f'Validated {len(pages)} HTML pages and their local links.')


def main():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)  # Only this tool's generated output.
    OUTPUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'site', OUTPUT, dirs_exist_ok=True)
    for folder in ('branding', 'screenshots'):
        shutil.copytree(ROOT / 'assets' / folder, OUTPUT / 'assets' / folder, dirs_exist_ok=True)
    (OUTPUT / '.nojekyll').touch()
    validate(OUTPUT)
    print('Pages artifact:', OUTPUT)

if __name__ == '__main__':
    main()
