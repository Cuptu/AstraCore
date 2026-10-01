#!/usr/bin/env python3
"""Verify the shipped archive after extraction to a new directory."""
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import zipfile


def main():
    archive = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='AstraCore runtime 核验 ') as temporary:
        destination = Path(temporary)
        if archive.suffix == '.zip':
            with zipfile.ZipFile(archive) as package:
                for name in package.namelist():
                    if not (destination / name).resolve().is_relative_to(destination):
                        raise RuntimeError(f'Archive path escapes destination: {name}')
                package.extractall(destination)
        else:
            with tarfile.open(archive) as package:
                package.extractall(destination, filter='data')
        subprocess.run([sys.executable, str(Path(__file__).with_name('verify-runtime.py')),
                        '--runtime-dir', str(destination)], check=True, timeout=180)
    print(f'Extracted and verified relocatable archive: {archive.name}')


if __name__ == '__main__':
    main()
