#!/usr/bin/env python3
"""Create a source release from an explicit allowlist, never the working tree."""
import hashlib
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('launch.sh', 'VERSION', 'README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'SECURITY.md', 'LICENSE')
DIRECTORIES = {
    'src': {'.py'}, 'scripts': {'.py', '.md'},
    'assets': {'.svg', '.png', '.txt', '.md'}, 'docs': {'.md'},
    'site': {'.html', '.css', '.js', '.md'}, 'tests': {'.py'},
    '.github': {'.yml', '.yaml', '.md'},
}


def main():
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise SystemExit('VERSION must be a semantic release version')
    if not (ROOT / 'LICENSE').is_file():
        raise SystemExit('Choose and add LICENSE before building a public release.')
    output = ROOT / 'dist/releases'
    output.mkdir(parents=True, exist_ok=True)
    name = f'floatty-{version}'
    archive = output / (name + '.tar.gz')
    members = [ROOT / item for item in FILES]
    for directory, extensions in DIRECTORIES.items():
        members.extend(p for p in (ROOT / directory).rglob('*')
                       if p.is_file() and p.suffix in extensions
                       and not any(part.startswith('.') for part in p.relative_to(ROOT / directory).parts))
    with tarfile.open(archive, 'w:gz') as bundle:
        for path in sorted(members):
            if path.is_symlink() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo'):
                continue
            if path.name.startswith('.env') or path.suffix in ('.log', '.sock'):
                continue
            relative = path.relative_to(ROOT)
            info = bundle.gettarinfo(str(path), arcname=str(Path(name) / relative))
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mode = 0o755 if relative == Path('launch.sh') else 0o644
            with path.open('rb') as source:
                bundle.addfile(info, source)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + '.sha256').write_text(f'{digest}  {archive.name}\n')
    print(archive)

if __name__ == '__main__':
    main()
