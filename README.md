# agent3

Minimal, secure-by-default HTTP service skeleton (Python 3.10+, standard library only).

## Endpoints
- `GET /health` returns `{"status": "ok"}`
- `GET /hello?name=Ali` returns `{"message": "Hello, Ali!"}` (name: 1-32 chars, letters/digits/space/`_`/`-`)

## Run
```bash
cp .env.example .env        # optional; values are read from the environment
export AGENT3_HOST=127.0.0.1 AGENT3_PORT=8080
PYTHONPATH=src python -m agent3.app
curl "http://127.0.0.1:8080/hello?name=Ali"
```

## Test
```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Security defaults
- Binds to `127.0.0.1` by default; exposing it is an explicit choice (`AGENT3_HOST`).
- Configuration only from environment variables; no secrets in code. `.env` is git-ignored.
- All input validated (allow-list regex, length limits); errors return generic JSON, never stack traces.
- Only GET is allowed; responses carry `nosniff` and `no-store` headers.

## Not included (yet)
TLS, authentication, rate limiting. Put it behind a reverse proxy before exposing it publicly.
