"""Сервер целиком: поднимаем на свободном порту и стучим настоящими запросами."""

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from app import seed
from app.config import Config
from app.db import open_or_create
from app.server import make_handler


class Live(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = Config.load()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.config = Config(
            db_path=Path(cls.tmp.name) / "test.db",
            schema_path=base.schema_path,
            static_dir=base.static_dir,
            host="127.0.0.1",
            port=0,                       # ядро выдаст свободный порт
            hero_name="Тестовый герой",
        )

        con, _fresh = open_or_create(cls.config)
        seed.fill(con)
        con.close()

        cls.httpd = ThreadingHTTPServer((cls.config.host, 0), make_handler(cls.config))
        cls.base_url = f"http://{cls.config.host}:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    # --- помощники --------------------------------------------------------
    def get(self, path):
        try:
            with urllib.request.urlopen(self.base_url + path, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def post(self, path, payload=None):
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload or {}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    # --- тесты ------------------------------------------------------------
    def test_state_is_served(self):
        status, state = self.get("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["profile"]["name"], seed.HERO["ru"])
        self.assertEqual(len(state["mains"]), 2)

    def test_index_page_is_served(self):
        with urllib.request.urlopen(self.base_url + "/", timeout=5) as response:
            body = response.read().decode("utf-8")
        self.assertEqual(response.status, 200)
        self.assertIn("<title>", body)

    def test_unknown_api_path_is_404(self):
        status, payload = self.get("/api/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", payload)

    def test_post_creates_and_returns_full_state(self):
        status, payload = self.post(
            "/api/quests", {"kind": "side", "title": "Сходить за хлебом", "stat": "body", "xp": 5}
        )
        self.assertEqual(status, 200)
        self.assertIn("state", payload)
        self.assertIn("flash", payload)
        titles = [s["title"] for s in payload["state"]["sides"]]
        self.assertIn("Сходить за хлебом", titles)

    def test_validation_error_comes_back_as_400(self):
        status, payload = self.post("/api/quests", {"kind": "side", "title": "", "stat": "body"})
        self.assertEqual(status, 400)
        self.assertIn("не заполнено", payload["error"])

    def test_language_survives_a_restart(self):
        status, payload = self.post("/api/profile", {"lang": "en"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"]["profile"]["lang"], "en")

        _status, fresh = self.get("/api/state")
        self.assertEqual(fresh["profile"]["lang"], "en")
        self.post("/api/profile", {"lang": "ru"})

    def test_unknown_language_is_rejected(self):
        status, payload = self.post("/api/profile", {"lang": "fr"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_broken_json_is_rejected(self):
        request = urllib.request.Request(
            self.base_url + "/api/quests",
            data=b"{not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 400)

    def test_hitting_the_boss_changes_stored_state(self):
        _status, state = self.get("/api/state")
        boss = state["bosses"][0]

        status, payload = self.post(f"/api/quests/{boss['id']}/hit")
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"]["bosses"][0]["hpLeft"], boss["hpLeft"] - 1)

        _status, fresh = self.get("/api/state")            # значение действительно в базе
        self.assertEqual(fresh["bosses"][0]["hpLeft"], boss["hpLeft"] - 1)

    def test_get_on_write_route_is_404(self):
        status, _payload = self.get("/api/profile")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
