"""Tiny HTTP service: GET /health and GET /hello?name=<name>."""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .config import ConfigError, load_config

NAME_RE = re.compile(r"[A-Za-z0-9_\- ]{1,32}")
MAX_QUERY_LEN = 256


def validate_name(raw: str | None) -> str:
    """Return a safe name or raise ValueError."""
    if raw is None:
        return "world"
    if not NAME_RE.fullmatch(raw):
        raise ValueError("name must be 1-32 chars: letters, digits, space, _ or -")
    return raw


class Handler(BaseHTTPRequestHandler):
    server_version = "agent3"  # no detailed version disclosure
    sys_version = ""

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            parts = urlsplit(self.path)
            if len(parts.query) > MAX_QUERY_LEN:
                return self._send(414, {"error": "query too long"})
            if parts.path == "/health":
                return self._send(200, {"status": "ok"})
            if parts.path == "/hello":
                values = parse_qs(parts.query, keep_blank_values=True).get("name")
                if values and len(values) > 1:
                    return self._send(400, {"error": "name given more than once"})
                name = validate_name(values[0] if values else None)
                return self._send(200, {"message": f"Hello, {name}!"})
            return self._send(404, {"error": "not found"})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except Exception:  # never leak internals to the client
            return self._send(500, {"error": "internal error"})

    def _method_not_allowed(self):
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_DELETE = do_PATCH = _method_not_allowed

    def log_message(self, fmt, *args):  # request line only; no headers/tokens
        super().log_message(fmt, *args)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    try:
        cfg = load_config()
    except ConfigError as exc:
        raise SystemExit(f"config error: {exc}")
    server = make_server(cfg.host, cfg.port)
    print(f"listening on http://{cfg.host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
