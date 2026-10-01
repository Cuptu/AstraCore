#!/usr/bin/env python3
"""Make the flat macOS runtime relocatable; fail on incomplete dependency closure."""
import argparse
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys


def run(*args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Command failed: {args!r}\n{error.output}") from error


def dependencies(binary):
    return [re.sub(r'\s+\(compatibility version.*$', '', line.strip())
            for line in run('/usr/bin/otool', '-L', str(binary)).splitlines()[1:]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runtime')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Mach-O relocation requires macOS')
    runtime = Path(args.runtime).resolve()
    pending = list(runtime.iterdir())
    visited = set()
    binaries = []
    while pending:
        binary = pending.pop().resolve()
        if binary in visited or not binary.is_file():
            continue
        if binary.parent != runtime:
            raise RuntimeError(f'Runtime symlink escapes payload: {binary}')
        visited.add(binary)
        if 'Mach-O' not in run('/usr/bin/file', '-b', str(binary)):
            continue
        binaries.append(binary)
        binary.chmod(binary.stat().st_mode | stat.S_IWUSR)
        identity_lines = run('/usr/bin/otool', '-D', str(binary)).splitlines()[1:]
        identity = identity_lines[0].strip() if identity_lines else None
        deps = dependencies(binary)
        for dep in deps:
            if dep == identity or dep.startswith(('/usr/lib/', '/System/Library/')):
                continue
            target = runtime / Path(dep).name
            if not target.exists():
                source = Path(dep)
                if not source.is_absolute() or not source.is_file():
                    raise RuntimeError(f'Unresolved dependency {dep} in {binary}')
                shutil.copy2(source.resolve(), target)
                pending.append(target)
            if target.resolve().parent != runtime:
                raise RuntimeError(f'Dependency escapes payload: {target}')
            run('/usr/bin/install_name_tool', '-change', dep,
                '@loader_path/' + target.name, str(binary))
        if identity:
            run('/usr/bin/install_name_tool', '-id', '@rpath/' + binary.name, str(binary))
    for binary in binaries:
        # Preserve third-party symbols/metadata. Some system-distributed Mach-O
        # files cannot be safely stripped; signing must follow all modifications.
        run('/usr/bin/codesign', '--force', '--timestamp=none', '--sign', '-', str(binary))
        run('/usr/bin/codesign', '--verify', '--strict', str(binary))
        identity_lines = run('/usr/bin/otool', '-D', str(binary)).splitlines()[1:]
        identity = identity_lines[0].strip() if identity_lines else None
        for dep in dependencies(binary):
            if dep == identity or dep.startswith(('/usr/lib/', '/System/Library/')):
                continue
            if not dep.startswith('@loader_path/') or not (runtime / dep[len('@loader_path/'):]).is_file():
                raise RuntimeError(f'Non-relocatable dependency {dep} in {binary}')
    print(f'Relocated and signed {len(binaries)} Mach-O binaries')


if __name__ == '__main__':
    main()
