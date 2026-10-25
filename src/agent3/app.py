"""Tiny HTTP service: GET /health and GET /hello?name=<name>."""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .config import ConfigError, load_config

# Name: 1-32 chars; must start and end with a letter/digit; inside also _ - and space.
NAME_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_ \-]*[A-Za-z0-9])?")
MAX_NAME_LEN = 32
MAX_TARGET_LEN = 512   # whole request target (path + query)
MAX_QUERY_LEN = 256
MAX_QUERY_FIELDS = 5
MAX_BODY_BYTES = 1024  # GET carries no body; larger declared bodies get 413


def validate_name(raw: str | None) -> str:
    """Return a safe name or raise ValueError."""
    if raw is None:
        return "world"
    if len(raw) > MAX_NAME_LEN or not NAME_RE.fullmatch(raw):
        raise ValueError(
            "name must be 1-32 chars, start and end with a letter or digit; "
            "allowed inside: letters, digits, space, _ and -"
        )
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

    def _body_problem(self):
        """Return (status, message) if the request declares a body, else None."""
        if self.headers.get("Transfer-Encoding"):
            return 400, "chunked bodies are not supported"
        raw = self.headers.get("Content-Length")
        if raw is None:
            return None
        if not raw.isascii() or not raw.isdigit():
            return 400, "invalid Content-Length"
        size = int(raw)
        if size > MAX_BODY_BYTES:
            return 413, "request body too large"
        if size > 0:
            return 400, "request body not allowed"
        return None

    def do_GET(self):
        try:
            problem = self._body_problem()
            if problem:
                return self._send(problem[0], {"error": problem[1]})
            if len(self.path) > MAX_TARGET_LEN:
                return self._send(414, {"error": "request target too long"})
            parts = urlsplit(self.path)
            if len(parts.query) > MAX_QUERY_LEN:
                return self._send(414, {"error": "query too long"})
            if parts.path == "/health":
                return self._send(200, {"status": "ok"})
            if parts.path == "/hello":
                try:
                    query = parse_qs(
                        parts.query,
                        keep_blank_values=True,
                        max_num_fields=MAX_QUERY_FIELDS,
                    )
                except ValueError:
                    return self._send(400, {"error": "too many query parameters"})
                values = query.get("name")
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
