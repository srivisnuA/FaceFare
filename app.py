# app.py  —  FaceFare · Flask + SocketIO backend
# ─────────────────────────────────────────────────────────────────
import cv2
import base64
import threading
import time
import traceback
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

from vision.camera import open_camera
from vision.recognition import recognize_face
from database.models import get_passengers, get_all_balances
from services.trip_manager import board, exit_bus
from services.wallet import deduct_balance

# ─────────────────────────────────────────────
# App + SocketIO
# ─────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = "facefare_secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading",
    logger=False,
    engineio_logger=False,
)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

BUS_STOPS     = ["Stop A", "Stop B", "Stop C", "Stop D", "Stop E"]
BASE_FARE     = 10
PER_STOP_RATE = 5

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
# Haar cascade
# ─────────────────────────────────────────────

_haar = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

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
            distance = max(1, end - start)
            fare     = BASE_FARE + distance * PER_STOP_RATE
            if deduct_balance(passengers, pid, fare):
                exit_bus(state, pid)
                state["revenue"] += fare
                return {
                    "passenger": pid,
                    "event":     "EXIT",
                    "stop":      BUS_STOPS[end],
                    "distance":  distance,
                    "fare":      fare,
                    "time":      datetime.now().strftime("%H:%M:%S"),
                }
            else:
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


def camera_thread():
    global camera_running
    print("[Camera] Thread started")

    # ── Open camera ──────────────────────────
    try:
        cam = open_camera()
    except Exception as e:
        print(f"[Camera] open_camera() crashed: {e}")
        traceback.print_exc()
        socketio.emit("camera_error",  {"msg": f"open_camera() failed: {e}"})
        socketio.emit("camera_status", {"running": False})
        with camera_lock:
            camera_running = False
        return

    if cam is None or not cam.isOpened():
        print("[Camera] Camera not opened — check device index in open_camera()")
        socketio.emit("camera_error",  {"msg": "Camera could not be opened. Check device index."})
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

            # ── Face detection ────────────────
            try:
                gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                boxes = _haar.detectMultiScale(
                    gray,
                    scaleFactor  = 1.1,
                    minNeighbors = 5,
                    minSize      = (50, 50),
                )
            except Exception as e:
                print(f"[Camera] Detection error: {e}")
                boxes = []

            recognized = []

            for (x, y, w, h) in boxes:
                try:
                    crop = frame[y:y+h, x:x+w]
                    if crop.size == 0:
                        continue

                    pid = recognize_face(crop)

                    if pid in ("Unknown", "Unknown passenger"):
                        color, label = (0, 165, 255), "Unknown"
                    elif pid in ("No Face", "No passenger detected"):
                        color, label = (60, 60, 220), "No Face"
                    else:
                        color, label = (50, 220, 120), pid

                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.rectangle(frame, (x, y-th-bl-8), (x+tw+6, y), color, -1)
                    cv2.putText(frame, label, (x+3, y-bl-3),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 1, cv2.LINE_AA)

                    if pid in passengers:
                        recognized.append(pid)
                        with state_lock:
                            entry = handle_passenger(pid, state["current_stop"])
                            if entry:
                                state["logs"].append(entry)

                except Exception as e:
                    print(f"[Camera] Face processing error: {e}")
                    continue

            # ── Encode & emit ─────────────────
            try:
                _, buf    = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                b64_frame = base64.b64encode(buf).decode("utf-8")
                socketio.emit("frame",  {"img": b64_frame})
                socketio.emit("update", build_snapshot(recognized))
            except Exception as e:
                print(f"[Camera] Emit error: {e}")

            time.sleep(0.033)

    except Exception as e:
        print(f"[Camera] Unexpected crash: {e}")
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

@app.route("/")
def index():
    return render_template(
        "index.html",
        stops         = BUS_STOPS,
        base_fare     = BASE_FARE,
        per_stop_rate = PER_STOP_RATE,
    )


@app.route("/control", methods=["POST"])
def control():
    data   = request.get_json(silent=True) or {}
    action = data.get("action", "")
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
    print(f"[SocketIO] Client connected: {request.sid}")
    emit("update", build_snapshot())
    with camera_lock:
        running = camera_running
    emit("camera_status", {"running": running})


@socketio.on("disconnect")
def on_disconnect():
    print(f"[SocketIO] Client disconnected: {request.sid}")


@socketio.on("start_camera")
def on_start_camera():
    global camera_running
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
        host         = "0.0.0.0",
        port         = 5000,
        debug        = False,
        use_reloader = False,   # reloader = 2 processes = double camera threads
    )