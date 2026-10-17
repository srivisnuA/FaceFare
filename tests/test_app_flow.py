"""Authenticated camera-free trip flow using real persistence."""
import importlib
import base64
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from database import db, models
import cv2
import numpy as np
from PIL import Image
from services import enrollment


class AppFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = tempfile.TemporaryDirectory()
        with patch.object(db, "DB_PATH", str(Path(cls.bootstrap.name) / "bootstrap.db")), patch.dict(os.environ, {"FACEFARE_DEMO": "1"}):
            cls.module = importlib.import_module("app")
        cls.module.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.bootstrap.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, "DB_PATH", str(Path(self.temp.name) / "wallet.db"))
        self.db_patch.start()
        db.init_db(seed=False)
        models.add_passenger("demo", 100)
        self.module.passengers.clear()
        self.module.passengers.update(models.get_passengers())
        self.module.state.update(mode="ENTRY", current_stop=0, onboard=[], boarding_stop={}, logs=[], revenue=0)
        self.log_patch = patch.object(self.module, "log_transaction")
        self.log_patch.start()
        self.client = self.module.app.test_client()

    def tearDown(self):
        self.log_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def login(self):
        self.client.get("/login")
        with self.client.session_transaction() as session:
            token = session["_csrf_token"]
        from security.auth import ADMIN_PASSWORD
        response = self.client.post("/login", data={"password": ADMIN_PASSWORD, "csrf_token": token})
        self.assertEqual(response.status_code, 302)
        self.client.get("/")
        with self.client.session_transaction() as session:
            self.headers = {"X-CSRF-Token": session["_csrf_token"]}

    def post(self, path, data):
        return self.client.post(path, json=data, headers=self.headers)

    def test_authentication_and_csrf_required(self):
        self.assertEqual(self.client.post("/control", json={"action": "entry"}).status_code, 401)
        self.assertEqual(self.client.post("/login", data={"password": "facefare123"}).status_code, 403)
        self.login()
        self.assertEqual(self.client.post("/control", json={"action": "entry"}).status_code, 403)
        self.assertEqual(self.post("/control", []).status_code, 400)
        self.assertEqual(self.client.get("/logout").status_code, 405)

    def test_full_trip_duplicate_scan_and_ledger(self):
        self.login()
        self.assertEqual(self.post("/api/demo/scan", {"passenger": "demo"}).json["event"]["event"], "BOARD")
        self.assertIsNone(self.post("/api/demo/scan", {"passenger": "demo"}).json["event"])
        self.assertEqual(self.post("/control", {"action": "prev_stop"}).status_code, 409)
        self.post("/control", {"action": "next_stop"})
        self.post("/control", {"action": "next_stop"})
        self.post("/control", {"action": "exit"})
        result = self.post("/api/demo/scan", {"passenger": "demo"}).json
        self.assertEqual(result["event"]["fare"], 20)
        self.assertEqual(result["snapshot"]["wallets"]["demo"], 80)
        self.assertEqual(result["snapshot"]["onboard"], [])
        self.assertIsNone(self.post("/api/demo/scan", {"passenger": "demo"}).json["event"])
        self.assertEqual(len(models.get_transactions("demo")), 2)
        self.assertEqual(self.module.state["boarding_stop"], {})

    def test_insufficient_funds_preserves_trip_and_revenue(self):
        self.login()
        models.update_balance("demo", 1)
        self.post("/api/demo/scan", {"passenger": "demo"})
        self.post("/control", {"action": "exit"})
        result = self.post("/api/demo/scan", {"passenger": "demo"}).json
        self.assertEqual(result["event"]["event"], "DECLINED")
        self.assertEqual(result["snapshot"]["onboard"], ["demo"])
        self.assertEqual(result["snapshot"]["revenue"], 0)
        self.assertEqual(models.get_balance("demo"), 1)

    def test_invalid_edit_cannot_partially_rename(self):
        self.login()
        response = self.client.patch("/api/passengers/demo", json={"name": "new", "balance": -1}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(models.get_all_balances(), {"demo": 100})
        response = self.client.patch("/api/passengers/demo/balance", json={"balance": True}, headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def test_simulation_disabled_and_private_photos(self):
        self.assertEqual(self.client.get("/api/passengers/demo/photos/demo1.jpg").status_code, 401)
        self.login()
        with patch.object(self.module, "DEMO_MODE", False):
            self.assertEqual(self.post("/api/demo/scan", {"passenger": "demo"}).status_code, 404)
        self.assertEqual(self.client.get("/").headers["Cache-Control"], "no-store")

    def test_login_redirect_cannot_leave_site(self):
        with self.module.app.test_request_context():
            for url in ["https://evil.test", "//evil.test", "/\\evil.test", "///evil.test"]:
                self.assertEqual(self.module._safe_next_url(url), "/")

    def test_logout_disconnects_socket_and_revokes_session(self):
        self.login()
        socket = self.module.socketio.test_client(self.module.app, flask_test_client=self.client)
        self.assertTrue(socket.is_connected())
        self.assertEqual(self.client.post("/logout", headers=self.headers).status_code, 302)
        self.assertFalse(socket.is_connected())
        self.assertEqual(self.post("/control", {"action": "entry"}).status_code, 401)

    def test_photos_remain_accessible_after_passenger_rename(self):
        self.login()
        with patch.object(enrollment, "KNOWN_FACES_DIR", str(Path(self.temp.name) / "faces")):
            directory = Path(enrollment.ensure_passenger_directory("demo"))
            Image.new("RGB", (160, 160)).save(directory / "demo1.jpg")
            response = self.client.patch("/api/passengers/demo", json={"name": "renamed"}, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            with self.client.get("/api/passengers/renamed/photos/demo1.jpg") as photo:
                self.assertEqual(photo.status_code, 200)
                self.assertEqual(photo.mimetype, "image/jpeg")

    def test_detection_failure_does_not_stream_unredacted_pixels(self):
        with patch.object(self.module, "detect_faces", side_effect=RuntimeError("no detector")):
            encoded, recognized = self.module._process_frame(np.full((80, 80, 3), 255, dtype=np.uint8))
        frame = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), dtype=np.uint8), cv2.IMREAD_COLOR)
        # JPEG quantization may reconstruct a black pixel as intensity one.
        self.assertLessEqual(int(frame.max()), 2)
        self.assertEqual(recognized, [])
