#!/usr/bin/env python3
"""Compile and package the SDK and JVM dependencies."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parents[1]
    target = root / 'src/ftcsim/sdk'
    target.mkdir(parents=True, exist_ok=True)
    wrapper = 'gradlew.bat' if os.name == 'nt' else './gradlew'
    subprocess.run([wrapper, '--no-daemon', 'bundlePythonSdk',
                    f'-PftcsimBundleDir={target / "libs"}'],
                   cwd=root / 'sdk/desktop', check=True)
    # Keep JVM classes and data while dropping Android UI resources.
    for android in (target / 'libs').glob('android-all-*.jar'):
        staged = android.with_suffix('.tmp')
        with ZipFile(android) as source, ZipFile(staged, 'w', ZIP_DEFLATED) as output:
            for item in source.infolist():
                if item.filename.startswith(('res/', 'raw-res/')) or item.filename == 'resources.arsc':
                    continue
                if item.filename.startswith('META-INF/') and item.filename.endswith(('.SF', '.RSA', '.DSA')):
                    continue
                output.writestr(item, source.read(item))
        staged.replace(android)
    shutil.copy2(root / 'sdk/LICENSE', target / 'LICENSE')
    jars = sorted((target / 'libs').glob('*.jar'))
    if not any(p.name.startswith('ftc-sdk-jvm-') for p in jars) or not any(p.name.startswith('ftc-desktop-runtime-') for p in jars):
        raise RuntimeError('SDK build did not produce required JARs')
    (target / 'manifest.json').write_text(json.dumps({
        'sdk_version': '12.0.0', 'runtime_version': '0.2.0',
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in jars},
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
