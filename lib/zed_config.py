#!/usr/bin/env python3
"""Export and install a small, explicitly managed set of Zed configuration files."""

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sys
import tempfile

import jsonc


REPO = Path(__file__).resolve().parents[1]
CONFIG_FILES = ('settings.json', 'keymap.json', 'tasks.json', 'themes', 'snippets')
EXTENSION_ID = re.compile(r'[a-z0-9][a-z0-9_-]*\Z')


@dataclass
class Entry:
    kind: str
    mode: int
    data: bytes = b''
    children: dict = field(default_factory=dict)


def read_entry(path):
    if path.is_symlink():
        raise ValueError(f'Symlinks are not managed: {path}')
    if not path.exists():
        return None
    mode = path.stat().st_mode & 0o777
    if path.is_file():
        return Entry('file', mode, path.read_bytes())
    if path.is_dir():
        return Entry('directory', mode, children={
            child.name: read_entry(child) for child in sorted(path.iterdir())
        })
    raise ValueError(f'Not a regular file or directory: {path}')


def write_entry(path, entry):
    if entry.kind == 'file':
        path.write_bytes(entry.data)
    else:
        path.mkdir()
        for name, child in entry.children.items():
            write_entry(path / name, child)
    path.chmod(entry.mode)


def remove_entry(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def overlay(current, incoming):
    if current is None or current.kind != 'directory' or incoming.kind != 'directory':
        return incoming
    children = dict(current.children)
    for name, entry in incoming.children.items():
        children[name] = overlay(children.get(name), entry)
    return Entry('directory', current.mode, children=children)


def xdg_path(variable, default):
    path = Path(os.environ.get(variable) or default)
    if not path.is_absolute():
        raise ValueError(f'{variable} must be an absolute path')
    return path


def validate_entry(name, entry):
    if entry is None:
        return
    if name.endswith('.json'):
        if entry.kind != 'file':
            raise ValueError(f'{name} must be a regular file')
        expected = dict if name == 'settings.json' else list
        value = jsonc.require_type(entry.data.decode('utf-8-sig'), expected)
        if name == 'settings.json':
            extensions = value.get('auto_install_extensions', {})
            if not isinstance(extensions, dict):
                raise ValueError('auto_install_extensions must be an object')
            for identifier, enabled in extensions.items():
                validate_extension_id(identifier)
                if not isinstance(enabled, bool):
                    raise ValueError(f'Extension state must be true or false: {identifier}')
    elif name in ('themes', 'snippets'):
        if entry.kind != 'directory':
            raise ValueError(f'{name} must be a directory')
        for filename, child in entry.children.items():
            if child.kind == 'file' and filename.endswith('.json'):
                jsonc.loads(child.data.decode('utf-8-sig'))
            elif child.kind == 'directory':
                validate_entry(name, child)


def validate_extension_id(identifier):
    if not EXTENSION_ID.fullmatch(identifier):
        raise ValueError(f'Invalid extension ID: {identifier!r}')


def extension_ids(entry):
    if entry.kind != 'file':
        raise ValueError('extensions.txt must be a regular file')
    result = set()
    for line in entry.data.decode('utf-8-sig').splitlines():
        identifier = line.strip()
        if identifier:
            validate_extension_id(identifier)
            result.add(identifier)
    return sorted(result)


def configure_extensions(settings, identifiers, exporting=False):
    text = settings.data.decode('utf-8-sig')
    values = jsonc.require_type(text, dict)
    disabled = {name: False for name, enabled in values.get('auto_install_extensions', {}).items()
                if enabled is False}
    if exporting:
        states = disabled
    else:
        states = {name: True for name in identifiers}
        states.update(disabled)
    text = jsonc.set_root_property(text, 'auto_install_extensions', dict(sorted(states.items())) or None)
    return Entry('file', settings.mode, (text.rstrip() + '\n').encode())


def build_plan(operation, source, destination, data_dir, mirror):
    names = CONFIG_FILES + (('extensions.txt',) if operation == 'export' else ())
    before = {name: read_entry(destination / name) for name in names}
    incoming = {name: read_entry(source / name) for name in CONFIG_FILES}
    if incoming['settings.json'] is None:
        raise ValueError(f'Missing required settings.json: {source}')
    for name, entry in incoming.items():
        validate_entry(name, entry)
    desired = {}
    for name, entry in incoming.items():
        if entry is None:
            if mirror:
                desired[name] = None
        elif not mirror and name in ('themes', 'snippets'):
            desired[name] = overlay(before[name], entry)
        else:
            desired[name] = entry
    if operation == 'export':
        desired['settings.json'] = configure_extensions(incoming['settings.json'], [], exporting=True)
        installed = data_dir / 'extensions/installed'
        if installed.is_symlink():
            raise ValueError(f'Symlinked extension installation directory: {installed}')
        if installed.is_dir():
            disabled = jsonc.loads(desired['settings.json'].data.decode()).get('auto_install_extensions', {})
            identifiers = []
            for path in sorted(installed.iterdir()):
                if path.is_dir() and path.name not in disabled:
                    validate_extension_id(path.name)
                    identifiers.append(path.name)
            data = ''.join(name + '\n' for name in sorted(set(identifiers))).encode()
            desired['extensions.txt'] = Entry('file', 0o644, data)
        else:
            print(f'Note: extension directory unavailable; keeping extensions.txt: {installed}')
    else:
        extensions = read_entry(source / 'extensions.txt')
        if extensions is not None:
            desired['settings.json'] = configure_extensions(incoming['settings.json'], extension_ids(extensions))
    return {name: (before[name], entry) for name, entry in desired.items() if before[name] != entry}


def save_backup(operation, destination, plan, backup_root):
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-')
    backup = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_root))
    (backup / 'files').mkdir(mode=0o700)
    for name, (previous, _) in plan.items():
        if previous is not None:
            write_entry(backup / 'files' / name, previous)
    metadata = {
        'version': 1, 'operation': operation, 'destination': str(destination),
        'entries': {name: previous is not None for name, (previous, _) in plan.items()},
    }
    (backup / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return backup


def replace_entry(destination, name, entry, stage):
    prepared = stage / 'new' / name
    previous = stage / 'old' / name
    target = destination / name
    if entry is not None and entry.kind == 'file' and (not target.exists() or target.is_file()):
        os.replace(prepared, target)
        return
    if target.exists():
        os.replace(target, previous)
    try:
        if entry is not None:
            os.replace(prepared, target)
    except BaseException:
        if previous.exists():
            os.replace(previous, target)
        raise


def apply_plan(operation, destination, plan, backup_root, dry_run):
    if not plan:
        print('Already up to date. No files changed.')
        return None
    for name, (previous, desired) in plan.items():
        action = 'remove' if desired is None else ('create' if previous is None else 'update')
        print(f'{action}: {destination / name}')
    if dry_run:
        print('Dry run: no files, directories or backups created.')
        return None
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.zed-stage-', dir=destination) as temporary:
        stage = Path(temporary)
        (stage / 'new').mkdir()
        (stage / 'old').mkdir()
        (stage / 'rollback').mkdir()
        for name, (_, desired) in plan.items():
            if desired is not None:
                write_entry(stage / 'new' / name, desired)
        # WARN: stop if another process changed a target after the plan was prepared.
        for name, (previous, _) in plan.items():
            if read_entry(destination / name) != previous:
                raise ValueError(f'Target changed during planning: {destination / name}')
        backup = save_backup(operation, destination, plan, backup_root)
        print(f'Backup: {backup}')
        completed = []
        try:
            for name, (_, desired) in plan.items():
                completed.append(name)
                replace_entry(destination, name, desired, stage)
        except BaseException:
            errors = []
            for name in reversed(completed):
                try:
                    previous = stage / 'old' / name
                    if previous.exists():
                        remove_entry(destination / name)
                        os.replace(previous, destination / name)
                    elif plan[name][0] is None:
                        remove_entry(destination / name)
                    elif plan[name][0].kind == 'file':
                        saved = stage / 'rollback' / name
                        write_entry(saved, plan[name][0])
                        os.replace(saved, destination / name)
                except OSError as error:
                    errors.append(str(error))
            if errors:
                print(f'Rollback incomplete. Restore from {backup}: {errors}', file=sys.stderr)
            raise
    return backup


def restore_plan(operation, destination, backup):
    if (backup.is_symlink() or (backup / 'manifest.json').is_symlink()
            or (backup / 'files').is_symlink()):
        raise ValueError('Symlinked backups are not supported')
    metadata = json.loads((backup / 'manifest.json').read_text())
    if (metadata.get('version') != 1 or metadata.get('operation') != operation
            or metadata.get('destination') != str(destination)):
        raise ValueError('Backup does not match this operation and destination')
    entries = metadata.get('entries')
    allowed = CONFIG_FILES + (('extensions.txt',) if operation == 'export' else ())
    if not isinstance(entries, dict) or not entries:
        raise ValueError('Backup manifest has no entries')
    plan = {}
    for name, present in entries.items():
        if name not in allowed or not isinstance(present, bool):
            raise ValueError('Invalid backup manifest entry')
        desired = read_entry(backup / 'files' / name) if present else None
        if present and desired is None:
            raise ValueError(f'Backup entry missing: {name}')
        current = read_entry(destination / name)
        if desired != current:
            plan[name] = (current, desired)
    return plan


def interrupted(signum, _frame):
    raise KeyboardInterrupt(f'Interrupted by signal {signum}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('export', 'install'))
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing anything')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--mirror', action='store_true', help='Remove missing managed entries and mirror theme/snippet trees')
    group.add_argument('--restore', type=Path, metavar='BACKUP', help='Restore a backup for this operation')
    args = parser.parse_args(argv)
    config = xdg_path('XDG_CONFIG_HOME', Path.home() / '.config') / 'zed'
    data = xdg_path('XDG_DATA_HOME', Path.home() / '.local/share') / 'zed'
    if config.is_symlink():
        raise ValueError(f'Symlinked configuration root is not supported: {config}')
    config = config.resolve()
    if config == REPO or config in REPO.parents or REPO in config.parents:
        raise ValueError('Repository and Zed configuration paths must not overlap')
    source, destination = (config, REPO) if args.operation == 'export' else (REPO, config)
    backup_root = REPO / '.zed-backups' if args.operation == 'export' else config.parent / 'zed-settings-backups'
    if args.restore:
        plan = restore_plan(args.operation, destination, args.restore.absolute())
    else:
        plan = build_plan(args.operation, source, destination, data, args.mirror)
    apply_plan(args.operation, destination, plan, backup_root, args.dry_run)
    if args.operation == 'install' and not args.dry_run and not args.restore:
        print('Open Zed to apply settings and install enabled extensions.')
    return 0


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupted)
    try:
        sys.exit(main())
    except (OSError, ValueError, UnicodeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Interrupted. Check the reported backup if recovery is needed.', file=sys.stderr)
        sys.exit(130)
