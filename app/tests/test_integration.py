import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import integration as api
import server


class PlanningTests(unittest.TestCase):
    def test_appearance_survives_restore_and_reenable(self):
        original = {'plugins': [{'id': api.PLUGIN, 'design': 'split', 'blankMs': 15000, 'unlock': 'fade'}]}
        config, record = api.plan_enable(original, server.DEFAULTS)
        config['plugins'][0]['design'] = 'zen'
        config, record = api.plan_restore(config, record)
        config, record = api.plan_enable(config, server.DEFAULTS, record)
        self.assertEqual(config['plugins'][0], {**original['plugins'][0], 'design': 'zen'})

    def test_enable_keeps_stock_idle_and_preserves_unrelated_settings(self):
        original = {'idle': {'screensaver': 150, 'lock': 300, 'custom': 99}, 'plugins': [{'id': 'other', 'value': 2}], 'disabledPlugins': ['omarchy.media'], 'other': {'keep': True}}
        config, state = api.plan_enable(original, server.DEFAULTS)
        self.assertEqual(original['idle']['lock'], 300)
        self.assertEqual(config['idle'], {'screensaver': 421, 'lock': 420, 'custom': 99})
        self.assertNotIn('omarchy.idle', config['disabledPlugins'])
        self.assertIn('omarchy.lock', config['disabledPlugins'])
        self.assertIn(api.PLUGIN, config['cloneSourceRestores'])
        self.assertEqual(config['other'], original['other'])
        restored, state = api.plan_restore(config, state)
        for key in original:
            self.assertEqual(restored[key], original[key])
        self.assertFalse(state['active'])

    def test_repeated_setup_retains_original_timing(self):
        config, state = api.plan_enable({}, server.DEFAULTS)
        config, state = api.plan_enable(config, {**server.DEFAULTS, 'lockMinutes': 9}, state)
        restored, state = api.plan_restore(config, state)
        self.assertNotIn('idle', restored)
        self.assertEqual(config['idle']['lock'], 540)
        self.assertEqual(len(config['plugins']), 1)

    def test_restoration_preserves_later_user_edits(self):
        config, state = api.plan_enable({'idle': {'lock': 180}}, server.DEFAULTS)
        config['idle'].update(lock=900, other=21)
        restored, _ = api.plan_restore(config, state)
        self.assertEqual(restored['idle'], {'lock': 900, 'other': 21})

    def test_external_timing_changes_are_not_silently_overwritten(self):
        config, state = api.plan_enable({}, server.DEFAULTS)
        config['idle']['lock'] = 900
        with self.assertRaisesRegex(ValueError, 'outside Flight Board'):
            api.plan_enable(config, server.DEFAULTS, state)

    def test_restore_is_idempotent_after_ownership_is_released(self):
        config, state = api.plan_enable({'idle': {'lock': 180}}, server.DEFAULTS)
        config, state = api.plan_restore(config, state)
        config['idle']['lock'] = 420  # A later deliberate edit equals our old value.
        restored, _ = api.plan_restore(config, state)
        self.assertEqual(restored['idle']['lock'], 420)

    def test_disabled_stock_idle_is_not_taken_over(self):
        with self.assertRaisesRegex(ValueError, 'stock Omarchy idle'):
            api.plan_enable({'disabledPlugins': ['omarchy.idle']}, server.DEFAULTS)

    def test_invalid_shapes_and_foreign_records_are_rejected(self):
        for config in ({'idle': []}, {'plugins': {}}, {'disabledPlugins': 'bad'}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                api.plan_enable(config, server.DEFAULTS)
        with self.assertRaises(ValueError):
            api.plan_enable({}, server.DEFAULTS, {'plugin': 'other'})


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paths = {'STATE': root / 'state', 'SHELL': root / 'shell.json', 'SETTINGS': root / 'settings.json', 'RECORD': root / 'state/integration.json'}
        for key, value in self.paths.items():
            patcher = patch.object(api, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_partial_write_failure_rolls_back_without_losing_user_files(self):
        api.atomic(api.SHELL, b'{"old": 1}')
        transaction = api.Transaction({api.SHELL: {'new': 2}, api.RECORD: {'active': True}})
        real = api.atomic
        def fail(path, data):
            if path == api.RECORD:
                raise OSError('disk full')
            real(path, data)
        with patch.object(api, 'atomic', side_effect=fail), self.assertRaises(OSError):
            transaction.apply()
        transaction.rollback()
        self.assertEqual(api.SHELL.read_bytes(), b'{"old": 1}')
        self.assertFalse(api.RECORD.exists())
        self.assertTrue((transaction.backup / 'files.json').exists())

    def test_concurrent_edit_after_planning_is_rejected(self):
        api.atomic(api.SHELL, b'{}')
        transaction = api.Transaction({api.SHELL: {'changed': True}})
        api.atomic(api.SHELL, b'{"user": true}')
        with self.assertRaisesRegex(RuntimeError, 'changed during setup'):
            transaction.apply()
        transaction.rollback()
        self.assertEqual(json.loads(api.SHELL.read_bytes()), {'user': True})

    def test_rollback_never_overwrites_newer_user_edit(self):
        api.atomic(api.SHELL, b'{}')
        transaction = api.Transaction({api.SHELL: {'changed': True}})
        transaction.apply()
        api.atomic(api.SHELL, b'{"user": true}')
        with self.assertRaisesRegex(RuntimeError, 'Kept newer user edits'):
            transaction.rollback()
        self.assertEqual(json.loads(api.SHELL.read_bytes()), {'user': True})

    def test_symlink_is_refused(self):
        target = Path(self.temp.name) / 'target'
        target.write_text('{}')
        api.SHELL.symlink_to(target)
        with self.assertRaises(ValueError):
            api.Transaction({api.SHELL: {}})
        self.assertEqual(target.read_text(), '{}')

    def test_preference_save_synchronizes_fallback_and_preserves_original(self):
        config, record = api.plan_enable({'idle': {'lock': 180}}, server.DEFAULTS)
        api.atomic(api.SHELL, api.encode(config))
        api.atomic(api.RECORD, api.encode(record))
        api.save_preferences({**server.DEFAULTS, 'lockMinutes': 9})
        self.assertEqual(api.read(api.SHELL)['idle']['lock'], 540)
        self.assertEqual(api.read(api.SETTINGS)['lockMinutes'], 9)
        self.assertEqual(api.read(api.RECORD)['originalIdle']['lock']['value'], 180)

    def test_save_after_normal_disable_does_not_reenable_plugin(self):
        config, record = api.plan_enable({}, server.DEFAULTS)
        config['plugins'] = []
        config['disabledPlugins'] = []
        config['cloneSourceRestores'] = []
        api.atomic(api.SHELL, api.encode(config))
        api.atomic(api.RECORD, api.encode(record))
        before = api.SHELL.read_bytes()
        api.save_preferences({**server.DEFAULTS, 'rows': 12})
        self.assertEqual(api.SHELL.read_bytes(), before)
        self.assertEqual(api.read(api.SETTINGS)['rows'], 12)

    def test_failed_verification_restores_every_owned_file(self):
        api.atomic(api.SHELL, b'{"idle": {"lock": 180}}')
        original = api.SHELL.read_bytes()
        with patch.object(api, 'preflight'), patch.object(server, 'settings', return_value=dict(server.DEFAULTS)), patch.object(api, 'restart_and_verify', side_effect=RuntimeError('verify failed')), patch.object(api.subprocess, 'run'):
            with self.assertRaisesRegex(RuntimeError, 'verify failed'):
                api.change('enable')
        self.assertEqual(api.SHELL.read_bytes(), original)
        self.assertFalse(api.SETTINGS.exists())
        self.assertFalse(api.RECORD.exists())

    def test_restore_after_normal_disable_restores_timing(self):
        config, record = api.plan_enable({'idle': {'lock': 180, 'screensaver': 120}}, server.DEFAULTS)
        config.update(plugins=[], disabledPlugins=[], cloneSourceRestores=[])
        restored, _ = api.plan_restore(config, record)
        self.assertEqual(restored['idle'], {'lock': 180, 'screensaver': 120})
        self.assertNotIn('omarchy.lock', restored['disabledPlugins'])

    def test_changed_timing_while_disabled_requires_setup_to_synchronize(self):
        config, record = api.plan_enable({}, server.DEFAULTS)
        api.atomic(api.SHELL, api.encode(config))
        api.atomic(api.RECORD, api.encode(record))
        api.atomic(api.SETTINGS, api.encode({**server.DEFAULTS, 'lockMinutes': 9}))
        self.assertEqual(api.status(), {'configured': True, 'active': False})
