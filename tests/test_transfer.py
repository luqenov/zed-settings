import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
import jsonc
import zed_config


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='zed settings ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'repository with spaces'
        self.repo.mkdir()
        for name in ('export-zed.sh', 'install-zed.sh'):
            shutil.copy2(ROOT / name, self.repo / name)
        shutil.copytree(ROOT / 'lib', self.repo / 'lib', ignore=shutil.ignore_patterns('__pycache__'))
        self.config = self.base / 'config home/zed'
        self.config.mkdir(parents=True)
        self.installed = self.base / 'data home/zed/extensions/installed'
        self.installed.mkdir(parents=True)
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.config.parent),
                        XDG_DATA_HOME=str(self.base / 'data home'),
                        HOME=str(self.base / 'home'), PYTHONDONTWRITEBYTECODE='1')
        (self.repo / 'settings.json').write_text('{"theme":"One Dark"}\n')
        (self.repo / 'extensions.txt').write_text('astro\n')

    def cli(self, operation, *args, success=True):
        result = subprocess.run(['bash', str(self.repo / f'{operation}-zed.sh'), *map(str, args)],
                                env=self.env, cwd=self.base, text=True, capture_output=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def backups(self, operation):
        root = self.repo / '.zed-backups' if operation == 'export' else self.config.parent / 'zed-settings-backups'
        return sorted(root.iterdir()) if root.exists() else []

    def config_settings(self):
        return jsonc.loads((self.config / 'settings.json').read_text())

    def test_compact_export_preserves_other_settings_and_comments(self):
        (self.config / 'settings.json').write_text('// keep\n{"auto_install_extensions":{"astro":true},"theme":"light"}')
        (self.installed / 'astro').mkdir()
        self.cli('export')
        text = (self.repo / 'settings.json').read_text()
        self.assertIn('// keep', text)
        self.assertEqual(jsonc.loads(text), {'theme': 'light'})
        self.assertEqual((self.repo / 'extensions.txt').read_text(), 'astro\n')
        self.assertEqual(len(self.backups('export')), 1)

    def test_indented_jsonc_and_last_extension_without_newline(self):
        (self.repo / 'settings.json').write_text('  {\n // keep\n "theme":"dark",\n }')
        (self.repo / 'extensions.txt').write_text('astro\nbiome')
        self.cli('install')
        self.assertEqual(self.config_settings()['auto_install_extensions'], {'astro': True, 'biome': True})
        self.assertIn('// keep', (self.config / 'settings.json').read_text())

    def test_disabled_extensions_survive_export_and_install(self):
        (self.config / 'settings.json').write_text('{"auto_install_extensions":{"astro":true,"biome":false}}')
        for name in ('astro', 'biome'):
            (self.installed / name).mkdir()
        self.cli('export')
        self.assertEqual((self.repo / 'extensions.txt').read_text(), 'astro\n')
        self.assertEqual(jsonc.loads((self.repo / 'settings.json').read_text())['auto_install_extensions'], {'biome': False})
        (self.repo / 'extensions.txt').write_text('astro\nbiome\nastro\n\n')
        self.cli('install')
        self.assertEqual(self.config_settings()['auto_install_extensions'], {'astro': True, 'biome': False})

    def test_dry_runs_create_no_files_or_backups(self):
        (self.config / 'settings.json').write_text('{"theme":"local"}')
        before_repo = (self.repo / 'settings.json').read_bytes()
        before_local = (self.config / 'settings.json').read_bytes()
        for operation in ('export', 'install'):
            self.cli(operation, '--dry-run')
            self.assertEqual(self.backups(operation), [])
        self.assertEqual((self.repo / 'settings.json').read_bytes(), before_repo)
        self.assertEqual((self.config / 'settings.json').read_bytes(), before_local)
        self.assertFalse(any(self.base.rglob('.zed-stage-*')))

    def test_dry_run_does_not_create_missing_config_root(self):
        self.config.rmdir()
        self.cli('install', '--dry-run')
        self.assertFalse(self.config.exists())
        self.assertEqual(self.backups('install'), [])

    def test_backup_covers_all_changed_files_and_supports_restore(self):
        for name in ('settings.json', 'keymap.json', 'tasks.json'):
            value = '{"theme":"old"}' if name == 'settings.json' else '[{"old":true}]'
            (self.config / name).write_text(value)
        for name in ('keymap.json', 'tasks.json'):
            (self.repo / name).write_text('[]')
        for root in (self.repo, self.config):
            for name in ('themes', 'snippets'):
                (root / name).mkdir()
                (root / name / '.hidden').write_text('new' if root == self.repo else 'old')
        old = {name: zed_config.read_entry(self.config / name) for name in zed_config.CONFIG_FILES}
        self.cli('install')
        backup = self.backups('install')[0]
        manifest = json.loads((backup / 'manifest.json').read_text())
        self.assertEqual(set(manifest['entries']), set(zed_config.CONFIG_FILES))
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
        self.cli('install', '--restore', backup, '--dry-run')
        self.cli('install', '--restore', backup)
        for name, entry in old.items():
            self.assertEqual(zed_config.read_entry(self.config / name), entry)

    def test_restore_removes_files_created_by_install(self):
        self.cli('install')
        backup = self.backups('install')[0]
        self.cli('install', '--restore', backup)
        self.assertFalse((self.config / 'settings.json').exists())
        self.assertEqual(len(self.backups('install')), 2)

    def test_repeated_install_is_idempotent_and_does_not_replace_backup(self):
        self.cli('install')
        backups = self.backups('install')
        result = self.cli('install')
        self.assertIn('Already up to date', result.stdout)
        self.assertEqual(self.backups('install'), backups)
        (self.repo / 'settings.json').write_text('{"theme":"new"}')
        self.cli('install')
        self.assertEqual(len(self.backups('install')), 2)
        self.assertTrue(backups[0].exists())

    def test_default_merge_and_explicit_mirror_include_hidden_files(self):
        for root in (self.repo, self.config):
            (root / 'themes').mkdir()
        (self.config / 'themes/old.txt').write_text('old')
        (self.repo / 'themes/.hidden').write_text('new')
        (self.config / 'tasks.json').write_text('[]')
        self.cli('install')
        self.assertTrue((self.config / 'themes/old.txt').exists())
        self.assertEqual((self.config / 'themes/.hidden').read_text(), 'new')
        self.assertTrue((self.config / 'tasks.json').exists())
        self.cli('install', '--mirror')
        self.assertFalse((self.config / 'themes/old.txt').exists())
        self.assertTrue((self.config / 'themes/.hidden').exists())
        self.assertFalse((self.config / 'tasks.json').exists())

    def test_empty_directories_and_no_installed_extensions(self):
        (self.repo / 'themes').mkdir()
        self.cli('install')
        self.assertTrue((self.config / 'themes').is_dir())
        self.cli('export')
        self.assertEqual((self.repo / 'extensions.txt').read_text(), '')

    def test_missing_extension_directory_keeps_existing_list(self):
        (self.config / 'settings.json').write_text('{}')
        self.installed.rmdir()
        self.cli('export', '--mirror')
        self.assertEqual((self.repo / 'extensions.txt').read_text(), 'astro\n')

    def test_invalid_inputs_fail_before_writing(self):
        (self.config / 'settings.json').write_text('{"theme":"untouched"}')
        for name, content in (
                ('settings.json', '{"broken":}'),
                ('extensions.txt', 'invalid"id'),
                ('keymap.json', '{"not":"an array"}'),
                ('tasks.json', '[1,,2]')):
            with self.subTest(name=name):
                original = (self.repo / name).read_bytes() if (self.repo / name).exists() else None
                (self.repo / name).write_text(content)
                self.cli('install', success=False)
                self.assertEqual((self.config / 'settings.json').read_text(), '{"theme":"untouched"}')
                self.assertEqual(self.backups('install'), [])
                if original is None:
                    (self.repo / name).unlink()
                else:
                    (self.repo / name).write_bytes(original)

    def test_symlinks_and_overlapping_paths_are_refused(self):
        external = self.base / 'external'
        external.write_text('keep')
        (self.config / 'settings.json').symlink_to(external)
        self.cli('install', success=False)
        self.assertEqual(external.read_text(), 'keep')
        (self.config / 'settings.json').unlink()
        self.env['XDG_CONFIG_HOME'] = str(self.repo.parent)
        (self.repo.parent / 'zed').symlink_to(self.repo, target_is_directory=True)
        self.cli('install', success=False)
        self.assertEqual(self.backups('install'), [])

    def test_export_restore_and_round_trip(self):
        original = '// local\n{"theme":"custom","auto_install_extensions":{"astro":true,"biome":false}}'
        (self.config / 'settings.json').write_text(original)
        (self.installed / 'astro').mkdir()
        prior_repository = (self.repo / 'settings.json').read_bytes()
        self.cli('export')
        export_backup = self.backups('export')[0]
        self.cli('install')
        self.assertEqual(self.config_settings(), jsonc.loads(original))
        self.cli('export', '--restore', export_backup)
        self.assertEqual((self.repo / 'settings.json').read_bytes(), prior_repository)

    def test_wrong_destination_and_path_traversal_in_backup_are_rejected(self):
        self.cli('install')
        backup = self.backups('install')[0]
        manifest = backup / 'manifest.json'
        data = json.loads(manifest.read_text())
        data['destination'] = '/somewhere/else'
        manifest.write_text(json.dumps(data))
        self.cli('install', '--restore', backup, success=False)
        data['destination'] = str(self.config)
        data['entries'] = {'../escape': False}
        manifest.write_text(json.dumps(data))
        self.cli('install', '--restore', backup, success=False)
        self.assertEqual(self.config_settings()['theme'], 'One Dark')


class TransactionTests(unittest.TestCase):
    def test_mid_transfer_failure_restores_prior_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / 'destination'
            destination.mkdir()
            (destination / 'settings.json').write_text('{"old":true}')
            (destination / 'keymap.json').write_text('[]')
            old = {name: zed_config.read_entry(destination / name) for name in ('settings.json', 'keymap.json')}
            plan = {name: (entry, zed_config.Entry('file', 0o600, b'{"new":true}')) for name, entry in old.items()}
            replace = zed_config.os.replace

            def fail_second_new(source, target):
                if Path(source).parent.name == 'new' and Path(target).name == 'keymap.json':
                    raise OSError('simulated write failure')
                return replace(source, target)

            with patch.object(zed_config.os, 'replace', side_effect=fail_second_new):
                with self.assertRaises(OSError):
                    zed_config.apply_plan('install', destination, plan, root / 'backups', False)
            for name, entry in old.items():
                self.assertEqual(zed_config.read_entry(destination / name), entry)
            self.assertEqual(len(list((root / 'backups').iterdir())), 1)
            self.assertFalse(list(destination.glob('.zed-stage-*')))

    def test_file_replacement_is_atomic_without_moving_original_aside(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'settings.json'
            target.write_text('{}')
            original = zed_config.read_entry(target)
            desired = zed_config.Entry('file', 0o600, b'{"theme":"new"}')
            with patch.object(zed_config.os, 'replace', wraps=zed_config.os.replace) as replace:
                zed_config.apply_plan('install', root, {'settings.json': (original, desired)},
                                      root / 'backups', False)
            self.assertEqual(replace.call_count, 1)
            self.assertEqual(replace.call_args.args[1], target)
            self.assertEqual(target.read_bytes(), desired.data)

    def test_changes_after_planning_abort_before_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'settings.json'
            target.write_text('{}')
            previous = zed_config.read_entry(target)
            target.write_text('{"newer":true}')
            with self.assertRaises(ValueError):
                zed_config.apply_plan('install', root,
                                      {'settings.json': (previous, zed_config.Entry('file', 0o600, b'{}'))},
                                      root / 'backups', False)
            self.assertEqual(target.read_text(), '{"newer":true}')
            self.assertFalse((root / 'backups').exists())


if __name__ == '__main__':
    unittest.main()
