import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
import jsonc


class JsoncTests(unittest.TestCase):
    def test_comments_strings_and_trailing_commas(self):
        text = r'''// header
        {"url":"https://example.org/*literal*/", /* note */ "items":[1,2,],}
        '''
        self.assertEqual(jsonc.loads(text), {'url': 'https://example.org/*literal*/', 'items': [1, 2]})

    def test_remove_property_in_every_position(self):
        cases = [
            '{"auto_install_extensions":{"a":true},"theme":"dark"}',
            '{"theme":"dark","auto_install_extensions":{"a":true}}',
            '{"theme":"dark","auto_install_extensions":{"a":true},}',
            '{"auto_install_extensions":{"a":true},}',
            '{"auto_install_extensions":{"a":true}}',
        ]
        for text in cases:
            with self.subTest(text=text):
                expected = jsonc.loads(text)
                del expected['auto_install_extensions']
                self.assertEqual(jsonc.loads(jsonc.set_root_property(text, 'auto_install_extensions', None)), expected)

    def test_inserts_into_indented_compact_and_empty_objects(self):
        for text in ('  {"theme":"dark"}', '{}', '{/* note */}', '{"theme":"dark",}',
                     '{"theme":"dark" // trailing note\n}', '// header\n{\n}\n'):
            with self.subTest(text=text):
                result = jsonc.set_root_property(text, 'auto_install_extensions', {'astro': True})
                self.assertEqual(jsonc.loads(result)['auto_install_extensions'], {'astro': True})
                if 'note' in text:
                    self.assertIn('note', result)

    def test_removal_preserves_surrounding_line_layout(self):
        text = '{\n  "auto_install_extensions": {"astro": true},\n  "theme": "dark"\n}\n'
        result = jsonc.set_root_property(text, 'auto_install_extensions', None)
        self.assertEqual(result, '{\n  "theme": "dark"\n}\n')

    def test_only_replaces_root_property(self):
        text = '''// keep this header
{"nested":{"auto_install_extensions":{"inner":true}},
 "auto_install_extensions":{"old":true}, "theme":"dark"}'''
        result = jsonc.set_root_property(text, 'auto_install_extensions', {'disabled': False})
        self.assertIn('// keep this header', result)
        self.assertEqual(jsonc.loads(result)['nested'], {'auto_install_extensions': {'inner': True}})
        self.assertEqual(jsonc.loads(result)['auto_install_extensions'], {'disabled': False})

    def test_rejects_invalid_and_ambiguous_inputs(self):
        for text in ('', '{"a":1 "b":2}', '{"a":1,"a":2}', '{"a":NaN}', '{,}', '[,]',
                     '{"a":01}', '{/* unfinished}', '{"x":"bad\\q"}', '{"a":,}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                jsonc.loads(text)
        with self.assertRaises(ValueError):
            jsonc.set_root_property('[]', 'auto_install_extensions', {})


if __name__ == '__main__':
    unittest.main()
