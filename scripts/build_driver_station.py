#!/usr/bin/env python3
"""Build the standalone SvelteKit app and stage it as Python package data."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'driver-station'
    npm = shutil.which('npm')
    node = shutil.which('node')
    if not npm or not node:
        raise RuntimeError('Building the Driver Station requires Node.js 22.12+ and npm. Wheel installations do not require Node.js.')
    version = json.loads(subprocess.check_output([node, '-p', 'JSON.stringify(process.versions.node.split(".").map(Number))'], text=True))
    if tuple(version[:2]) < (22, 12):
        raise RuntimeError('Building the Driver Station requires Node.js 22.12+ on PATH.')
    subprocess.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=source, check=True)
    subprocess.run([npm, 'run', 'build'], cwd=source, check=True)
    output = source / 'build'
    index = output / 'index.html'
    if not index.is_file() or not (output / '_app' / 'immutable').is_dir():
        raise RuntimeError('SvelteKit did not produce the static Driver Station bundle')
    # Retain licenses for dependencies shipped as JavaScript and local fonts.
    licenses = output / 'licenses'
    licenses.mkdir(exist_ok=True)
    lock = json.loads((source / 'package-lock.json').read_text())
    for package, metadata in lock['packages'].items():
        if not package or metadata.get('dev') and package != 'node_modules/svelte':
            continue
        folder = source / package
        for license_file in folder.glob('LICENSE*'):
            if license_file.is_file():
                name = package.removeprefix('node_modules/').replace('/', '-')
                shutil.copy2(license_file, licenses / f'{name}-{license_file.name}')
    # Stage the completed bundle before replacing any existing packaged frontend.
    target = root / 'src' / 'ftcsim' / 'web'
    with tempfile.TemporaryDirectory(dir=target.parent) as temporary:
        staged = Path(temporary) / 'ds'
        shutil.copytree(output, staged)
        if target.exists():
            shutil.rmtree(target)
        staged.replace(target)
    print(f'Driver Station bundled: {len(list(target.rglob("*")))} entries')


if __name__ == '__main__':
    main()
