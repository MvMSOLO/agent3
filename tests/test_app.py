import json
import threading
import unittest
import urllib.error
import urllib.request

from agent3.app import make_server, validate_name
from agent3.config import ConfigError, load_config


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)  # port 0: free port
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as r:
                return r.status, json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            body = e.read()
            return e.code, (json.loads(body) if body else {}), e.headers

    def test_health(self):
        status, body, headers = self.get("/health")
        self.assertEqual((status, body), (200, {"status": "ok"}))
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_hello_default_and_named(self):
        self.assertEqual(self.get("/hello")[1], {"message": "Hello, world!"})
        self.assertEqual(self.get("/hello?name=Ali")[1], {"message": "Hello, Ali!"})

    def test_rejects_bad_input(self):
        for bad in ["<script>", "a" * 33, "", "x;y", "name=1&name=2"]:
            q = bad if "=" in bad else f"name={bad}"
            self.assertEqual(self.get("/hello?" + q)[0], 400, bad)

    def test_unknown_path_and_long_query(self):
        self.assertEqual(self.get("/nope")[0], 404)
        self.assertEqual(self.get("/hello?name=" + "a" * 300)[0], 414)

    def test_post_not_allowed(self):
        req = urllib.request.Request(self.base + "/health", data=b"x", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 405)


class UnitTest(unittest.TestCase):
    def test_validate_name(self):
        self.assertEqual(validate_name(None), "world")
        with self.assertRaises(ValueError):
            validate_name("../etc")

    def test_config_defaults_are_safe(self):
        cfg = load_config({})
        self.assertEqual((cfg.host, cfg.port, cfg.api_token), ("127.0.0.1", 8080, None))

    def test_config_rejects_bad_port(self):
        for bad in ["abc", "-1", "70000"]:
            with self.assertRaises(ConfigError):
                load_config({"AGENT3_PORT": bad})


if __name__ == "__main__":
    unittest.main()
