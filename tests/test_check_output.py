import errno
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import unittest


REPORTER = Path(__file__).resolve().parent / 'check-output.sh'


class CheckOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='check-output-test-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.env = dict(os.environ, TMPDIR=str(self.directory), TERM='xterm-256color')
        self.env.pop('CI', None)
        self.env.pop('NO_COLOR', None)

    def run_reporter(self, script, *flags):
        return subprocess.run(['bash', '-eu', '-c', 'source "$1"; shift; ' + script,
                               'fixture', str(REPORTER), *flags], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_success_hides_command_noise_and_cleans_logs(self):
        result = self.run_reporter('''
check_init fixture "$@"
check_step 'Configuration and recovery' bash -c 'echo INTERNAL_FIXTURE_DETAIL; echo "Ran 3 tests in 0.001s" >&2'
check_finish
''', '--plain')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Configuration and recovery ... OK', result.stdout)
        self.assertIn('Passed: 1 check, 3 tests', result.stdout)
        self.assertNotIn('INTERNAL_FIXTURE_DETAIL', result.stdout)
        self.assertNotIn('\x1b', result.stdout)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_failure_keeps_diagnostics_and_original_exit_status(self):
        result = self.run_reporter('''
check_init fixture "$@"
check_step 'Backup recovery' python3 -B - <<'PYTHON'
import sys
print('Fixture failure details', file=sys.stderr)
sys.exit(23)
PYTHON
check_finish
''')
        self.assertEqual(result.returncode, 23)
        self.assertIn('Backup recovery ... FAIL', result.stdout)
        self.assertIn('Fixture failure details', result.stdout)
        self.assertIn('Stopped at: Backup recovery (exit 23)', result.stderr)
        self.assertNotIn('Passed:', result.stdout)
        self.assertEqual(list(self.directory.iterdir()), [])
        function_failure = self.run_reporter("""
check_init fixture "$@"
broken_validator() { (exit 17); echo SHOULD_NOT_RUN; }
check_step 'Configuration' broken_validator
check_finish
""")
        self.assertEqual(function_failure.returncode, 17)
        self.assertNotIn('SHOULD_NOT_RUN', function_failure.stdout)
        self.assertNotIn('Passed:', function_failure.stdout)

    def test_verbose_reveals_successful_command_details(self):
        result = self.run_reporter('''
check_init fixture "$@"
check_step 'Configuration' bash -c 'echo INTERNAL_FIXTURE_DETAIL'
check_finish
''', '--verbose')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('INTERNAL_FIXTURE_DETAIL', result.stdout)

    def test_counts_python_and_node_tests_and_reports_skips(self):
        result = self.run_reporter('''
check_init fixture "$@"
check_step 'Python tests' bash -c 'printf "Ran 3 tests in 0.001s\\nOK (skipped=1)\\n"'
check_step 'Node tests' bash -c 'printf "# tests 2\\n# skipped 1\\n"'
check_skip 'Desktop validator' 'not installed'
check_finish
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Passed: 2 checks, 5 tests', result.stdout)
        self.assertIn('Skipped: 1 optional check, 2 tests.', result.stdout)

    def test_animation_only_runs_in_an_interactive_terminal(self):
        for flags, ci, animated in [((), False, True), (('--plain',), False, False), ((), True, False)]:
            with self.subTest(flags=flags, ci=ci):
                environment = dict(self.env)
                if ci:
                    environment['CI'] = 'true'
                master, slave = pty.openpty()
                process = None
                try:
                    process = subprocess.Popen([
                        'bash', '-eu', '-c',
                        'source "$1"; shift; check_init fixture "$@"; check_step "Runtime checks" sleep 0.3; check_finish',
                        'fixture', str(REPORTER), *flags], env=environment,
                        stdout=slave, stderr=slave)
                    os.close(slave)
                    slave = None
                    output = bytearray()
                    while True:
                        ready, _, _ = select.select([master], [], [], 5)
                        if not ready:
                            process.kill()
                            process.wait()
                            self.fail('Terminal check did not complete')
                        try:
                            data = os.read(master, 4096)
                        except OSError as error:
                            if error.errno == errno.EIO:
                                break
                            raise
                        if not data:
                            break
                        output.extend(data)
                    self.assertEqual(process.wait(timeout=5), 0)
                    self.assertEqual(b'\x1b[2K' in output, animated)
                    self.assertIn(b'Runtime checks', output)
                    self.assertIn(b'Passed:', output)
                finally:
                    if process is not None and process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    if slave is not None:
                        os.close(slave)

    def test_help_and_invalid_flags_do_not_run_checks(self):
        help_result = self.run_reporter('check_init fixture "$@"', '--help')
        self.assertEqual(help_result.returncode, 0)
        self.assertIn('--verbose', help_result.stdout)
        invalid = self.run_reporter('check_init fixture "$@"', '--unknown')
        self.assertEqual(invalid.returncode, 2)
        self.assertIn('Unknown option', invalid.stderr)
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
