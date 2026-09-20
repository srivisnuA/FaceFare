# app.py  —  FaceFare · Flask + SocketIO backend
# ─────────────────────────────────────────────────────────────────
import cv2
import base64
import numpy as np
import threading
import time
import traceback
import os
import re
import shutil
import secrets
from functools import wraps
from hmac import compare_digest
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, render_template, jsonify, request, redirect, url_for, session, send_from_directory
from flask_socketio import SocketIO, emit

from vision.camera import open_camera
from vision.recognition import recognize_face, load_known_faces
from vision.face_detector import detect_faces
from database.models import (
    get_passengers,
    get_all_balances,
    add_passenger,
    update_balance,
    rename_passenger,
    delete_passenger,
)
from services.trip_manager import board, exit_bus
from services.enrollment import normalize_passenger_id, passenger_directory, save_passenger_photos, ENROLLMENT_LOCK
from services.wallet import deduct_balance
from services.fare_engine import calculate_fare
from services.logger import log_transaction
from security.auth import login_required, is_authenticated, check_password
from security.privacy import blur_face, is_enrolled_passenger
from config import SECRET_KEY, BUS_STOPS, BASE_FARE, PER_STOP_RATE

# ─────────────────────────────────────────────
# App + SocketIO
# ─────────────────────────────────────────────

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FACEFARE_ENV", "development").lower() == "production",
    MAX_CONTENT_LENGTH=55 * 1024 * 1024,
)

SOCKETIO_CORS_ORIGINS = os.environ.get("FACEFARE_CORS_ORIGINS", "").strip()
if SOCKETIO_CORS_ORIGINS:
    SOCKETIO_CORS_ORIGINS = [
        origin.strip()
        for origin in SOCKETIO_CORS_ORIGINS.split(",")
        if origin.strip()
    ]
else:
    SOCKETIO_CORS_ORIGINS = None

socketio = SocketIO(
    app,
    cors_allowed_origins=SOCKETIO_CORS_ORIGINS,
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

# ─────────────────────────────────────────────
# Shared state
# ─────────────────────────────────────────────

state_lock = threading.Lock()

state = {
    "mode":          "ENTRY",
    "current_stop":  0,
    "onboard":       [],
    "boarding_stop": {},
    "logs":          [],
    "revenue":       0,
}

passengers = get_passengers()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _safe_next_url(target):
    """Allow only local application paths after login."""
    if not target:
        return url_for("index")

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return url_for("index")

    return target


def _csrf_token():
    """Return the per-session CSRF token, creating it when needed."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def csrf_protect(view_func):
    """Require the session's CSRF token for authenticated state changes."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        token = request.headers.get("X-CSRF-Token", "")
        if not token or not compare_digest(token, _csrf_token()):
            return jsonify({"ok": False, "error": "Invalid CSRF token."}), 403
        return view_func(*args, **kwargs)
    return wrapped


# ─────────────────────────────────────────────
# Snapshot helper
# NOTE: acquires state_lock internally — NEVER call while already holding it
# ─────────────────────────────────────────────

def build_snapshot(recognized=None):
    if recognized is None:
        recognized = []
    with state_lock:
        snap = {
            "mode":         state["mode"],
            "current_stop": state["current_stop"],
            "stop_name":    BUS_STOPS[state["current_stop"]],
            "onboard":      list(state["onboard"]),
            "logs":         list(state["logs"][-50:]),
            "revenue":      state["revenue"],
            "wallets":      get_all_balances(),
            "recognized":   list(recognized),
        }
    return snap


# ─────────────────────────────────────────────
# Passenger logic — call while holding state_lock
# ─────────────────────────────────────────────

def handle_passenger(pid, current_stop):
    mode = state["mode"]

    if mode == "ENTRY":
        if pid not in state["onboard"]:
            board(state, pid)
            state["boarding_stop"][pid] = current_stop
            log_transaction(pid, "BOARD", f"stop={BUS_STOPS[current_stop]}")
            return {
                "passenger": pid,
                "event":     "BOARD",
                "stop":      BUS_STOPS[current_stop],
                "distance":  "—",
                "fare":      "—",
                "time":      datetime.now().strftime("%H:%M:%S"),
            }
    else:
        if pid in state["onboard"]:
            start    = state["boarding_stop"].get(pid, current_stop)
            end      = current_stop
            distance = max(0, end - start)
            fare     = calculate_fare(distance, BASE_FARE, PER_STOP_RATE)
            if deduct_balance(passengers, pid, fare):
                exit_bus(state, pid)
                state["revenue"] += fare
                log_transaction(pid, "EXIT", f"stop={BUS_STOPS[end]}, distance={distance}, fare={fare}")
                return {
                    "passenger": pid,
                    "event":     "EXIT",
                    "stop":      BUS_STOPS[end],
                    "distance":  distance,
                    "fare":      fare,
                    "time":      datetime.now().strftime("%H:%M:%S"),
                }
            else:
                log_transaction(pid, "DECLINED", f"stop={BUS_STOPS[end]}, distance={distance}, fare={fare} (insufficient balance)")
                return {
                    "passenger": pid,
                    "event":     "DECLINED",
                    "stop":      BUS_STOPS[end],
                    "distance":  distance,
                    "fare":      fare,
                    "time":      datetime.now().strftime("%H:%M:%S"),
                }
    return None


# ─────────────────────────────────────────────
# Camera thread
# ─────────────────────────────────────────────

camera_running = False
camera_lock    = threading.Lock()


def _process_frame(frame):
    """Detect, recognize, annotate, and encode one camera frame."""
    try:
        boxes = detect_faces(frame)
    except Exception as exc:
        print(f"[Camera] Detection error: {exc}")
        boxes = []

    recognized = []

    for (x, y, w, h) in boxes:
        try:
            crop = frame[y:y+h, x:x+w]
            if crop.size == 0:
                continue

            pid = recognize_face(crop)

            if not is_enrolled_passenger(pid):
                blur_face(frame, x, y, w, h)

            if pid in ("Unknown", "Unknown passenger"):
                color, label = (0, 165, 255), "Unknown"
            elif pid in ("No Face", "No passenger detected"):
                color, label = (60, 60, 220), "No Face"
            else:
                color, label = (50, 220, 120), pid

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            (tw, th), bl = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
            )
            cv2.rectangle(
                frame, (x, y-th-bl-8), (x+tw+6, y), color, -1
            )
            cv2.putText(
                frame, label, (x+3, y-bl-3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA
            )

            if pid in passengers:
                recognized.append(pid)
                with state_lock:
                    entry = handle_passenger(pid, state["current_stop"])
                    if entry:
                        state["logs"].append(entry)

        except Exception as exc:
            print(f"[Camera] Face processing error: {exc}")
            continue

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok:
        raise RuntimeError("Could not encode camera frame")

    return base64.b64encode(buf).decode("utf-8"), recognized


def _decode_browser_frame(data):
    """Decode a browser getUserMedia JPEG/data URL into an OpenCV frame."""
    if not isinstance(data, str) or not data:
        raise ValueError("Camera frame is missing")

    encoded = data.split(",", 1)[1] if "," in data else data
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("Camera frame is invalid") from exc

    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Camera frame is too large")

    frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Camera frame could not be decoded")

    return frame


def camera_thread():
    global camera_running
    print("[Camera] Thread started")

    try:
        cam = open_camera()
    except Exception as exc:
        print(f"[Camera] open_camera() crashed: {exc}")
        traceback.print_exc()
        socketio.emit("camera_error", {"msg": f"Local camera unavailable: {exc}"})
        socketio.emit("camera_status", {"running": False})
        with camera_lock:
            camera_running = False
        return

    if cam is None or not cam.isOpened():
        print("[Camera] Camera not opened")
        socketio.emit(
            "camera_error",
            {"msg": "Local server camera could not be opened."},
        )
        socketio.emit("camera_status", {"running": False})
        with camera_lock:
            camera_running = False
        return

    print("[Camera] Camera opened OK")
    socketio.emit("camera_status", {"running": True})

    try:
        while True:
            with camera_lock:
                if not camera_running:
                    break

            ret, frame = cam.read()
            if not ret:
                print("[Camera] cam.read() failed — camera disconnected?")
                break

            try:
                b64_frame, recognized = _process_frame(frame)
                socketio.emit("frame", {"img": b64_frame})
                socketio.emit("update", build_snapshot(recognized))
            except Exception as exc:
                print(f"[Camera] Frame processing error: {exc}")

            time.sleep(0.033)

    except Exception as exc:
        print(f"[Camera] Unexpected crash: {exc}")
        traceback.print_exc()

    finally:
        cam.release()
        print("[Camera] Released")
        with camera_lock:
            camera_running = False
        socketio.emit("camera_status", {"running": False})


# ─────────────────────────────────────────────
# HTTP routes
# ─────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password(password):
            session["authenticated"] = True
            next_url = _safe_next_url(request.args.get("next"))
            return redirect(next_url)
        error = "Incorrect password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("authenticated", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template(
        "index.html",
        stops         = BUS_STOPS,
        base_fare     = BASE_FARE,
        per_stop_rate = PER_STOP_RATE,
        csrf_token    = _csrf_token(),
    )


@app.route("/api/passengers", methods=["POST"])
@login_required
@csrf_protect
def create_passenger():
    """Create a passenger and save their enrolled face photos."""
    pid_raw = request.form.get("name", "")
    balance_raw = request.form.get("initial_balance", "100")
    files = request.files.getlist("photos")

    try:
        pid = normalize_passenger_id(pid_raw)
        initial_balance = float(balance_raw)
        if not initial_balance >= 0:
            raise ValueError("Initial balance must be non-negative")

        if pid in passengers:
            return jsonify({
                "ok": False,
                "error": f"Passenger '{pid}' already exists. Use + PHOTOS to add more face photos.",
            }), 409

        saved_paths = save_passenger_photos(pid, files)

        try:
            add_passenger(pid, initial_balance)
        except Exception:
            for path in saved_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass
            directory = passenger_directory(pid)
            if os.path.isdir(directory) and not os.listdir(directory):
                try:
                    os.rmdir(directory)
                except OSError:
                    pass
            raise

        passengers[pid] = {"balance": initial_balance}
        load_known_faces()

        return jsonify({
            "ok": True,
            "passenger": pid,
            "balance": initial_balance,
            "photos": [os.path.basename(path) for path in saved_paths],
        }), 201

    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        print(f"[Enrollment] Could not create passenger: {exc}")
        return jsonify({"ok": False, "error": "Could not create passenger."}), 409


@app.route("/api/passengers/<path:pid>", methods=["PATCH"])
@login_required
@csrf_protect
def edit_passenger(pid):
    """Edit a passenger name and/or wallet balance."""
    with ENROLLMENT_LOCK:
        try:
            old_pid = normalize_passenger_id(pid)
            if old_pid not in passengers:
                return jsonify({"ok": False, "error": "Passenger not found."}), 404

            data = request.get_json(silent=True) or {}
            new_pid = normalize_passenger_id(data.get("name", old_pid))

            try:
                new_balance = float(data.get("balance", passengers[old_pid]["balance"]))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "Balance must be a number."}), 400

            if new_pid != old_pid and new_pid in passengers:
                return jsonify({"ok": False, "error": f"Passenger '{new_pid}' already exists."}), 409

            old_dir = passenger_directory(old_pid)
            new_dir = passenger_directory(new_pid)
            moved_dir = False

            if new_pid != old_pid and os.path.exists(old_dir):
                if os.path.exists(new_dir):
                    return jsonify({"ok": False, "error": "Target passenger photo folder already exists."}), 409
                os.rename(old_dir, new_dir)
                moved_dir = True

            try:
                if new_pid != old_pid:
                    rename_passenger(old_pid, new_pid)
                update_balance(new_pid, new_balance)
            except Exception:
                if moved_dir and os.path.exists(new_dir) and not os.path.exists(old_dir):
                    os.rename(new_dir, old_dir)
                raise

            passenger_data = passengers.pop(old_pid)
            passenger_data["balance"] = new_balance
            passengers[new_pid] = passenger_data

            with state_lock:
                state["onboard"] = [new_pid if p == old_pid else p for p in state["onboard"]]
                if old_pid in state["boarding_stop"]:
                    state["boarding_stop"][new_pid] = state["boarding_stop"].pop(old_pid)

            load_known_faces()
            socketio.emit("update", build_snapshot())

            return jsonify({
                "ok": True,
                "passenger": new_pid,
                "balance": new_balance,
            })
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except Exception as exc:
            print(f"[Passenger] Could not edit {pid!r}: {exc}")
            return jsonify({"ok": False, "error": "Could not edit passenger."}), 409


@app.route("/api/passengers/<path:pid>", methods=["DELETE"])
@login_required
@csrf_protect
def remove_passenger(pid):
    """Delete a passenger, wallet record, and enrolled face directory."""
    with ENROLLMENT_LOCK:
        try:
            pid = normalize_passenger_id(pid)
            if pid not in passengers:
                return jsonify({"ok": False, "error": "Passenger not found."}), 404

            with state_lock:
                if pid in state["onboard"]:
                    return jsonify({
                        "ok": False,
                        "error": "Passenger is currently onboard. Exit them before deleting.",
                    }), 409

            directory = passenger_directory(pid)
            tombstone = None
            if os.path.isdir(directory):
                tombstone = directory + f".deleting-{secrets.token_hex(6)}"
                os.rename(directory, tombstone)

            try:
                delete_passenger(pid)
            except Exception:
                if tombstone and os.path.exists(tombstone):
                    os.rename(tombstone, directory)
                raise

            if tombstone:
                shutil.rmtree(tombstone, ignore_errors=True)

            passengers.pop(pid, None)
            with state_lock:
                state["boarding_stop"].pop(pid, None)

            load_known_faces()
            socketio.emit("update", build_snapshot())

            return jsonify({"ok": True, "passenger": pid})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except Exception as exc:
            print(f"[Passenger] Could not delete {pid!r}: {exc}")
            return jsonify({"ok": False, "error": "Could not delete passenger."}), 409


@app.route("/api/passengers/<path:pid>/photos", methods=["POST"])
@login_required
@csrf_protect
def add_passenger_photos(pid):
    """Add face photos to an existing passenger and reload recognition."""
    try:
        pid = normalize_passenger_id(pid)
        if pid not in passengers:
            return jsonify({"ok": False, "error": "Passenger not found."}), 404

        files = request.files.getlist("photos")
        saved_paths = save_passenger_photos(pid, files)
        load_known_faces()

        return jsonify({
            "ok": True,
            "passenger": pid,
            "photos": [os.path.basename(path) for path in saved_paths],
        }), 201

    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        print(f"[Enrollment] Could not add photos for {pid!r}: {exc}")
        return jsonify({"ok": False, "error": "Could not add passenger photos."}), 409


@app.route("/api/passengers/<path:pid>/balance", methods=["PATCH"])
@login_required
@csrf_protect
def update_passenger_balance(pid):
    """Update an existing passenger's wallet balance from the dashboard."""
    try:
        pid = normalize_passenger_id(pid)
        if pid not in passengers:
            return jsonify({"ok": False, "error": "Passenger not found."}), 404

        data = request.get_json(silent=True) or {}
        if "balance" not in data:
            return jsonify({"ok": False, "error": "Balance is required."}), 400

        try:
            new_balance = float(data["balance"])
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Balance must be a number."}), 400

        update_balance(pid, new_balance)
        passengers[pid]["balance"] = new_balance

        socketio.emit("update", build_snapshot())

        return jsonify({
            "ok": True,
            "passenger": pid,
            "balance": new_balance,
        })
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        print(f"[Wallet] Could not update balance for {pid!r}: {exc}")
        return jsonify({"ok": False, "error": "Could not update passenger balance."}), 409


@app.route("/api/passengers/<path:pid>/photos/<path:filename>", methods=["GET"])
@login_required
def serve_passenger_photo(pid, filename):
    """Serve one enrolled face photo to the authenticated management UI."""
    try:
        pid = normalize_passenger_id(pid)
        if pid not in passengers:
            return jsonify({"ok": False, "error": "Passenger not found."}), 404

        if not isinstance(filename, str) or os.path.basename(filename) != filename:
            return jsonify({"ok": False, "error": "Invalid photo filename."}), 400

        stem, extension = os.path.splitext(filename)
        if extension.lower() not in {".jpg", ".jpeg", ".png"}:
            return jsonify({"ok": False, "error": "Invalid photo filename."}), 400
        if not re.fullmatch(rf"{re.escape(pid)}\d+", stem):
            return jsonify({"ok": False, "error": "Invalid photo filename."}), 400

        directory = passenger_directory(pid)
        if not os.path.isdir(directory) or not os.path.isfile(os.path.join(directory, filename)):
            return jsonify({"ok": False, "error": "Photo not found."}), 404

        return send_from_directory(directory, filename, max_age=0)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        print(f"[Enrollment] Could not serve photo for {pid!r}: {exc}")
        return jsonify({"ok": False, "error": "Could not serve passenger photo."}), 409


@app.route("/api/passengers/<path:pid>/photos", methods=["GET"])
@login_required
def list_passenger_photos(pid):
    """Return enrolled face-photo filenames for an existing passenger."""
    try:
        pid = normalize_passenger_id(pid)
        if pid not in passengers:
            return jsonify({"ok": False, "error": "Passenger not found."}), 404

        directory = passenger_directory(pid)
        if not os.path.isdir(directory):
            return jsonify({"ok": True, "passenger": pid, "photos": []})

        photos = sorted(
            filename
            for filename in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, filename))
            and os.path.splitext(filename)[1].lower() in {".jpg", ".jpeg", ".png"}
        )

        return jsonify({
            "ok": True,
            "passenger": pid,
            "photos": photos,
        })
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        print(f"[Enrollment] Could not list photos for {pid!r}: {exc}")
        return jsonify({"ok": False, "error": "Could not list passenger photos."}), 409


@app.route("/api/passengers/<path:pid>/photos", methods=["DELETE"])
@login_required
@csrf_protect
def delete_passenger_photos(pid):
    """Delete selected face photos while keeping at least one enrolled image."""
    with ENROLLMENT_LOCK:
        try:
            pid = normalize_passenger_id(pid)
            if pid not in passengers:
                return jsonify({"ok": False, "error": "Passenger not found."}), 404

            data = request.get_json(silent=True) or {}
            filenames = data.get("photos")
            if not isinstance(filenames, list) or not filenames:
                return jsonify({"ok": False, "error": "Select at least one photo."}), 400

            directory = passenger_directory(pid)
            if not os.path.isdir(directory):
                return jsonify({"ok": False, "error": "No enrolled photos found."}), 404

            current_files = [
                filename
                for filename in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, filename))
                and os.path.splitext(filename)[1].lower() in {".jpg", ".jpeg", ".png"}
            ]

            targets = []
            for filename in filenames:
                if not isinstance(filename, str) or os.path.basename(filename) != filename:
                    return jsonify({"ok": False, "error": "Invalid photo filename."}), 400

                stem, extension = os.path.splitext(filename)
                if extension.lower() not in {".jpg", ".jpeg", ".png"}:
                    return jsonify({"ok": False, "error": "Invalid photo filename."}), 400
                if not re.fullmatch(rf"{re.escape(pid)}\d+", stem):
                    return jsonify({"ok": False, "error": "Invalid photo filename."}), 400
                if filename not in current_files:
                    return jsonify({"ok": False, "error": f"Photo not found: {filename}"}), 404

                targets.append(filename)

            targets = list(dict.fromkeys(targets))
            if len(current_files) - len(targets) < 1:
                return jsonify({
                    "ok": False,
                    "error": "At least one face photo must remain enrolled.",
                }), 400

            deleted = []
            for filename in targets:
                os.remove(os.path.join(directory, filename))
                deleted.append(filename)

            load_known_faces()

            return jsonify({
                "ok": True,
                "passenger": pid,
                "deleted": deleted,
            })
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        except Exception as exc:
            print(f"[Enrollment] Could not delete photos for {pid!r}: {exc}")
            return jsonify({"ok": False, "error": "Could not delete passenger photos."}), 409


@app.route("/control", methods=["POST"])
@login_required
@csrf_protect
def control():
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")

    if action not in {"entry", "exit", "next_stop", "prev_stop"}:
        return jsonify({"ok": False, "error": "Invalid control action."}), 400

    with state_lock:
        if action == "entry":
            state["mode"] = "ENTRY"
        elif action == "exit":
            state["mode"] = "EXIT"
        elif action == "next_stop":
            if state["current_stop"] < len(BUS_STOPS) - 1:
                state["current_stop"] += 1
        elif action == "prev_stop":
            if state["current_stop"] > 0:
                state["current_stop"] -= 1

    socketio.emit("update", build_snapshot())
    return jsonify({"ok": True})


# ─────────────────────────────────────────────
# SocketIO events
# ─────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    if not is_authenticated():
        print(f"[SocketIO] Rejected unauthenticated client: {request.sid}")
        return False
    print(f"[SocketIO] Client connected: {request.sid}")
    emit("update", build_snapshot())
    with camera_lock:
        running = camera_running
    emit("camera_status", {"running": running})


@socketio.on("disconnect")
def on_disconnect():
    print(f"[SocketIO] Client disconnected: {request.sid}")


@socketio.on("browser_frame")
def on_browser_frame(data, ack=None):
    """Process a frame captured by the authenticated browser camera."""
    if not is_authenticated():
        if callable(ack):
            ack({"ok": False, "error": "Authentication required."})
        return

    try:
        frame = _decode_browser_frame((data or {}).get("img"))
        b64_frame, recognized = _process_frame(frame)
        emit("frame", {"img": b64_frame})
        emit("update", build_snapshot(recognized))
        if callable(ack):
            ack({"ok": True})
    except ValueError as exc:
        emit("camera_error", {"msg": str(exc)})
        if callable(ack):
            ack({"ok": False, "error": str(exc)})
    except Exception as exc:
        print(f"[Camera] Browser frame error: {exc}")
        emit("camera_error", {"msg": "Could not process browser camera frame."})
        if callable(ack):
            ack({"ok": False, "error": "Could not process browser camera frame."})


@socketio.on("start_camera")
def on_start_camera():
    global camera_running
    if not is_authenticated():
        print("[SocketIO] Rejected unauthenticated start_camera")
        return

    print("[SocketIO] start_camera received")
    with camera_lock:
        already = camera_running
        if not already:
            camera_running = True

    if not already:
        t = threading.Thread(target=camera_thread, daemon=True, name="CameraThread")
        t.start()
        print("[SocketIO] Camera thread launched")
    else:
        print("[SocketIO] Camera already running — sending status")
        emit("camera_status", {"running": True})


@socketio.on("stop_camera")
def on_stop_camera():
    global camera_running
    if not is_authenticated():
        print("[SocketIO] Rejected unauthenticated stop_camera")
        return

    print("[SocketIO] stop_camera received")
    with camera_lock:
        camera_running = False
    emit("camera_status", {"running": False})


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  FaceFare  →  http://localhost:5000")
    print("=" * 50)
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        use_reloader=False,
    )