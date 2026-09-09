# -*- coding: utf-8 -*-
import sys
import os
import argparse
from pathlib import Path
from typing import List, Set

if sys.stdout.encoding != 'utf-8':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

DEFAULT_IGNORES = {
    '.git', 'node_modules', '.venv', 'venv', '__pycache__',
    '.pytest_cache', '.uv', 'dist', 'build', '.next',
    '.idea', '.vscode', 'coverage', '.turbo', '.cache'
}

def generate_tree(dir_path: Path, max_depth: int = 3, current_depth: int = 0, prefix: str = '', ignores: Set[str] = None, dirs_only: bool = False, show_size: bool = False) -> List[str]:
    if ignores is None:
        ignores = DEFAULT_IGNORES
    if current_depth >= max_depth:
        return []
    try:
        entries = sorted(list(dir_path.iterdir()), key=lambda e: (not e.is_dir(), e.name.lower()))
    except (PermissionError, OSError):
        return [prefix + '└── [Permission Denied]']

    filtered_entries = [
        e for e in entries
        if e.name not in ignores and not (e.name.startswith('.') and e.name not in ('.env.example', '.gitignore', '.dockerignore'))
    ]
    if dirs_only:
        filtered_entries = [e for e in filtered_entries if e.is_dir()]

    lines = []
    count = len(filtered_entries)
    for i, entry in enumerate(filtered_entries):
        is_last = (i == count - 1)
        connector = '└── ' if is_last else '├── '
        child_prefix = prefix + ('    ' if is_last else '│   ')
        if entry.is_dir():
            lines.append(prefix + connector + entry.name + '/')
            lines.extend(generate_tree(entry, max_depth=max_depth, current_depth=current_depth + 1, prefix=child_prefix, ignores=ignores, dirs_only=dirs_only, show_size=show_size))
        else:
            size_str = ''
            if show_size:
                try:
                    sz = entry.stat().st_size
                    if sz < 1024:
                        size_str = ' (' + str(sz) + ' B)'
                    elif sz < 1024 * 1024:
                        size_str = f' ({sz/1024:.1f} KB)'
                    else:
                        size_str = f' ({sz/(1024*1024):.1f} MB)'
                except Exception:
                    pass
            lines.append(prefix + connector + entry.name + size_str)
    return lines

def main():
    parser = argparse.ArgumentParser(description='Smart Project Tree Generator')
    parser.add_argument('path', nargs='?', default='.', help='Root directory path (default: current dir)')
    parser.add_argument('-L', '--depth', type=int, default=3, help='Max depth level (default: 3)')
    parser.add_argument('-d', '--dirs-only', action='store_true', help='List directories only')
    parser.add_argument('-s', '--sizes', action='store_true', help='Show file sizes')
    parser.add_argument('-I', '--ignore', help='Comma-separated ignore names/patterns')
    parser.add_argument('-o', '--output', help='Save output to file (e.g. project_tree.md)')
    args = parser.parse_args()

    root_path = Path(args.path).resolve()
    ignores = set(DEFAULT_IGNORES)
    if args.ignore:
        for ig in args.ignore.split(','):
            if ig.strip():
                ignores.add(ig.strip())

    header = root_path.name + '/'
    tree_lines = [header] + generate_tree(root_path, max_depth=args.depth, ignores=ignores, dirs_only=args.dirs_only, show_size=args.sizes)
    nl = chr(10)
    result_text = nl.join(tree_lines)
    print(result_text)

    if args.output:
        out_file = Path(args.output)
        if out_file.suffix == '.md':
            content = '# Project Structure' + nl + nl + '`	ext' + nl + result_text + nl + '`' + nl
        else:
            content = result_text
        out_file.write_text(content, encoding='utf-8')
        print(nl + f'[Tree saved to {out_file.resolve()}]')

if __name__ == '__main__':
    main()
