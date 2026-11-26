import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import cloudflare_access as access
from verify_deployment import main, verify_html, verify_home_link


class AccessTests(unittest.TestCase):
    def test_cloud_credentials_require_both_values_and_avoid_the_local_vault(self):
        variables = {access.CLIENT_ID_ENV: 'test-client', access.CLIENT_SECRET_ENV: 'test-secret'}
        with patch.dict(os.environ, variables, clear=True), patch.object(access, 'credential_path') as path:
            self.assertEqual(access.load_credentials()['clientId'], 'test-client')
            path.assert_not_called()
        with patch.dict(os.environ, {access.CLIENT_ID_ENV: 'test-client'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'Both .* secrets'):
                access.load_credentials()
        with patch.dict(os.environ, {}, clear=True), patch.object(access.os, 'name', 'posix'):
            with self.assertRaisesRegex(RuntimeError, 'No Cloudflare Access credentials'):
                access.load_credentials()

    def test_credentials_are_windows_user_encrypted_outside_repo(self):
        if os.name != 'nt':
            self.skipTest('Windows DPAPI integration test')
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, LOCALAPPDATA=folder):
            access.save_credentials('test-client', 'test-secret')
            encrypted = access.credential_path().read_bytes()
            self.assertNotIn(b'test-secret', encrypted)
            self.assertNotIn(b'test-client', encrypted)
            self.assertEqual(access.load_credentials()['clientSecret'], 'test-secret')

    def test_credentials_never_follow_redirects(self):
        request = access.urllib.request.Request(access.ORIGIN)
        with self.assertRaisesRegex(RuntimeError, 'redirected'):
            access.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://example.org/')

    def test_cannot_send_credentials_to_another_origin(self):
        for path in ['https://example.org/', '//example.org/', 'http://v75travet.se/', '/x#secret']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                access.site_url(path)
        self.assertEqual(access.site_url('/efteranalys/'), access.ORIGIN+'/efteranalys/')

    def test_header_injection_is_rejected(self):
        with self.assertRaises(ValueError):
            access.validate_credentials({'clientId':'test\r\nother: value','clientSecret':'test'})

    def test_stale_or_login_pages_do_not_pass(self):
        for body in ['<title>V75travet.se</title>old report',
                     'Sign in cloudflareaccess.com Send login code expected']:
            with self.assertRaises(RuntimeError):
                verify_html(body, 'text/html', 'expected')
        with self.assertRaises(RuntimeError):
            verify_html('V75travet.se expected', 'text/plain', 'expected')
        verify_html('<title>V75travet.se</title><h1>expected</h1>', 'text/html', 'expected')

    def test_saturday_report_must_be_reachable_through_homepage_archive(self):
        home = verify_html('V75travet.se <a href="./efteranalys/">Arkiv</a>', 'text/html', 'Arkiv')
        with patch('verify_deployment.fetch_site', return_value=(
                'V75travet.se <a href="./2026-11-07/">Rapport</a>', 'text/html')):
            verify_home_link(home, '/efteranalys/2026-11-07/', {})
            with self.assertRaises(RuntimeError):
                verify_home_link(home, '/efteranalys/2026-11-14/', {})

    def test_cloud_check_requires_the_exact_published_report(self):
        body = '<title>V75travet.se</title><h1>Report</h1>'
        path = '/uppdateringar/2026-11-26/'
        home = f'V75travet.se <a href="{path}">Report</a>'
        with tempfile.TemporaryDirectory() as folder:
            source = pathlib.Path(folder) / 'index.html'
            source.write_bytes(body.encode('utf-8'))
            with patch.object(sys, 'argv', ['verify_deployment.py', '--path', path, '--expect-file', str(source)]), \
                    patch('verify_deployment.load_credentials', return_value={}), \
                    patch('verify_deployment.fetch_site', side_effect=[
                        (body, 'text/html'), (home, 'text/html'), (body + ' old version', 'text/html')]):
                main()
                with self.assertRaisesRegex(RuntimeError, 'differs from the checked-out publication'):
                    main()


if __name__ == '__main__':
    unittest.main()
