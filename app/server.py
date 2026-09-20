"""HTTP-слой: статика плюс JSON-API. Только стандартная библиотека."""

import json
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from . import api, db

MAX_BODY = 64 * 1024


def make_handler(config):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(config.static_dir), **kwargs)

        # --- API ---------------------------------------------------------
        def do_GET(self):
            if self.route() == "/api/state":
                self.with_db(lambda con: self.send_json(api.read_state(con)))
            elif self.route().startswith("/api/"):
                self.send_json({"error": "Нет такого адреса"}, 404)
            else:
                super().do_GET()

        def do_POST(self):
            path = self.route()
            if not path.startswith("/api/"):
                self.send_json({"error": "Нет такого адреса"}, 404)
                return

            try:
                body = self.read_json()
            except ValueError as err:
                self.send_json({"error": str(err)}, 400)
                return

            def run(con):
                try:
                    with con:
                        flash = api.dispatch(con, path, body)
                        state = api.read_state(con)
                except api.Bad as err:
                    self.send_json({"error": err.message}, err.status)
                except sqlite3.IntegrityError as err:
                    self.send_json({"error": f"База отвергла запись: {err}"}, 400)
                else:
                    self.send_json({"state": state, "flash": flash})

            self.with_db(run)

        # --- помощники ---------------------------------------------------
        def route(self):
            return self.path.split("?")[0].rstrip("/") or "/"

        def with_db(self, work):
            con = db.connect(config.db_path)
            try:
                work(con)
            finally:
                con.close()

        def read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("Тело запроса слишком большое")
            if not length:
                return {}
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as err:
                raise ValueError("Тело запроса — не JSON") from err
            if not isinstance(data, dict):
                raise ValueError("Ожидался объект JSON")
            return data

        def send_json(self, payload, status=200):
            blob = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(blob)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(blob)

        def log_message(self, fmt, *args):
            # Тишина для статики: в консоли интересны только вызовы API.
            if args and "/api/" in str(args[0]):
                super().log_message(fmt, *args)

    return Handler


def serve(config):
    con, fresh = db.open_or_create(config)
    con.close()
    if fresh:
        print(f"База создана: {config.db_path}")

    httpd = ThreadingHTTPServer((config.host, config.port), make_handler(config))
    print(f"Life Quests: {config.url}   (Ctrl+C — остановить)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлен.")
    finally:
        httpd.server_close()
