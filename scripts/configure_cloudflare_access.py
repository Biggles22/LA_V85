"""One-use loopback form. Secret input is encrypted locally, never logged."""
import http.server
import secrets
import threading
import urllib.parse
from cloudflare_access import save_credentials


def main():
    nonce = secrets.token_urlsafe(32)
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body):
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body.encode())

        def valid(self):
            return self.path == '/' + nonce and self.headers.get('Host') == server_name

        def do_GET(self):
            if not self.valid():
                return self.send(404, 'Not found')
            self.send(200, '''<!doctype html><html lang="sv"><meta charset="utf-8"><title>V75travet – lokal nyckellagring</title><h1>Spara Cloudflare-nyckeln lokalt</h1><p>Uppgifterna krypteras för ditt Windows-konto och sparas utanför GitHub-projektet. De skickas bara till denna lokala engångstjänst.</p><form method="post"><p><label>Client ID <input name="clientId" type="password" autocomplete="off" required></label></p><p><label>Client Secret <input name="clientSecret" type="password" autocomplete="off" required></label></p><button>Spara krypterat</button></form></html>''')

        def do_POST(self):
            if not self.valid() or self.headers.get('Origin') != origin:
                return self.send(403, 'Not allowed')
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length < 8192:
                    return self.send(400, 'Invalid input')
                fields = urllib.parse.parse_qs(self.rfile.read(length).decode(), strict_parsing=True)
                save_credentials(fields['clientId'][0].strip(), fields['clientSecret'][0].strip())
            except Exception:
                return self.send(400, 'Kunde inte spara. Inga nyckelvärden har loggats.')
            self.send(200, '<!doctype html><meta charset="utf-8"><title>Nyckeln sparad</title><h1>Nyckeln har sparats krypterat</h1><p>Engångstjänsten stängs nu. Inga nyckelvärden visas eller har loggats.</p>')
            threading.Thread(target=server.shutdown, daemon=True).start()
    server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
    server_name = f'127.0.0.1:{server.server_port}'
    origin = 'http://' + server_name
    print(origin + '/' + nonce, flush=True)
    server.serve_forever()
    server.server_close()
    print('Credentials saved with Windows user encryption; setup server stopped.', flush=True)


if __name__ == '__main__':
    main()
