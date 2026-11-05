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
from verify_deployment import verify_html, verify_home_link


class AccessTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
