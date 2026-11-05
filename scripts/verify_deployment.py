"""Verify the private production page without printing Access credentials."""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from cloudflare_access import ORIGIN, fetch_site, load_credentials, site_url


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.text.append(value)


def verify_html(body, content_type, expected):
    if 'text/html' not in content_type:
        raise RuntimeError('Production URL did not return HTML')
    if 'cloudflareaccess.com' in body and ('Send login code' in body or 'Sign in' in body):
        raise RuntimeError('Access login page returned instead of the site')
    page = Page()
    page.feed(body)
    text = ' '.join(' '.join(page.text).split())
    if 'V75travet.se' not in text or expected not in text:
        raise RuntimeError('Expected publication text was not found')
    return page


def links_to(page, base_path, target_path):
    target = urlsplit(site_url(target_path))
    return any((link.scheme, link.netloc, link.path) == (target.scheme, target.netloc, target.path)
               for link in (urlsplit(urljoin(ORIGIN+base_path, href)) for href in page.links))


def verify_home_link(home, path, credentials):
    if links_to(home, '/', path):
        return
    # Saturday reports are linked through the archive already on the homepage.
    if path.startswith('/efteranalys/') and links_to(home, '/', '/efteranalys/'):
        body, kind = fetch_site('/efteranalys/', credentials)
        archive = verify_html(body, kind, 'V75travet.se')
        if links_to(archive, '/efteranalys/', path):
            return
    raise RuntimeError('Homepage/archive does not link to the requested report')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True)
    parser.add_argument('--expect', required=True)
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--output-dir', type=pathlib.Path)
    args = parser.parse_args()
    site_url(args.path)
    credentials = load_credentials()
    body, content_type = fetch_site(args.path, credentials)
    page = verify_html(body, content_type, args.expect)
    homepage, homepage_type = fetch_site('/', credentials)
    home = verify_html(homepage, homepage_type, 'V75travet.se')
    verify_home_link(home, args.path, credentials)
    print('PASS: authenticated production content and homepage report link')
    if args.browser:
        if not args.output_dir:
            parser.error('--browser requires --output-dir outside the published repository')
        root = pathlib.Path(__file__).resolve().parents[1]
        if args.output_dir.resolve().is_relative_to(root):
            parser.error('Store verification screenshots outside the published repository')
        payload = {**credentials, 'url': site_url(args.path), 'expect': args.expect,
                   'outputDir': str(args.output_dir.resolve())}
        environment = os.environ.copy()
        modules = pathlib.Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
        if not environment.get('NODE_PATH') and modules.is_dir():
            environment['NODE_PATH'] = str(modules)
        try:
            result = subprocess.run([shutil.which('node') or 'node', str(root/'scripts/verify_private_browser.cjs')],
                                    input=json.dumps(payload), text=True, capture_output=True, env=environment,
                                    timeout=120)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Browser verification timed out; use a writable local output folder') from None
        if result.returncode:
            raise RuntimeError('Authenticated browser verification failed; credentials were not logged')
        print('PASS: authenticated mobile/desktop content, links and screenshots')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        # Only controlled messages; never dump network request objects or stdin.
        print('FAILED:', str(error) if isinstance(error, (RuntimeError, ValueError)) else 'Local verification error')
        raise SystemExit(1)
