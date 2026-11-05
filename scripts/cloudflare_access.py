"""Local, Windows-user encrypted Access credentials; never shipped to the site."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
import pathlib
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ORIGIN = 'https://v75travet.se'


def credential_path():
    return pathlib.Path(os.environ['LOCALAPPDATA']) / 'V75travet' / 'Cloudflare' / 'access-token.bin'


def crypt(data, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Windows user encryption is required')
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buf = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    dll = ctypes.WinDLL('crypt32', use_last_error=True)
    function = dll.CryptUnprotectData if decrypt else dll.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise RuntimeError('Windows credential encryption/decryption failed')
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        free = ctypes.WinDLL('kernel32').LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(output.data)


def validate_credentials(value):
    if not isinstance(value, dict):
        raise ValueError('Invalid credential record')
    for key in ('clientId', 'clientSecret'):
        item = value.get(key)
        if not isinstance(item, str) or not item.strip() or '\r' in item or '\n' in item:
            raise ValueError('Both Access credentials are required')
    if value.get('origin', ORIGIN) != ORIGIN:
        raise ValueError('Credentials are restricted to V75travet.se')
    return value


def save_credentials(client_id, client_secret):
    value = validate_credentials({'origin': ORIGIN, 'clientId': client_id, 'clientSecret': client_secret})
    encrypted = crypt(json.dumps(value).encode())
    path = credential_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(encrypted)
        temporary = pathlib.Path(f.name)
    os.replace(temporary, path)


def load_credentials():
    path = credential_path()
    if not path.exists():
        raise RuntimeError('Cloudflare Access credentials have not been configured locally')
    return validate_credentials(json.loads(crypt(path.read_bytes(), decrypt=True)))


def site_url(path):
    if not isinstance(path, str) or not path.startswith('/') or path.startswith('//'):
        raise ValueError('Only a relative V75travet.se path is accepted')
    result = urllib.parse.urlsplit(ORIGIN + path)
    if result.scheme != 'https' or result.netloc != 'v75travet.se' or result.fragment:
        raise ValueError('Invalid verification URL')
    return urllib.parse.urlunsplit(result)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward credentials to the Access login page or another host.
        raise RuntimeError('Verification was redirected; Access authorization or URL needs attention')


def fetch_site(path, credentials=None):
    credentials = validate_credentials(credentials or load_credentials())
    req = urllib.request.Request(site_url(path), headers={
        'User-Agent': 'V75travet-deployment-verifier', 'Cache-Control': 'no-cache',
        'CF-Access-Client-Id': credentials['clientId'],
        'CF-Access-Client-Secret': credentials['clientSecret']})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            return response.read().decode('utf-8'), response.headers.get('Content-Type', '')
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'Verification returned HTTP {exc.code}') from None
    except urllib.error.URLError:
        raise RuntimeError('Could not reach V75travet.se') from None
