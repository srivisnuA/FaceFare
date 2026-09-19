# vision/face_detector.py
# ─────────────────────────────────────────────────────────────────
# Face detection using OpenCV's DNN-based SSD detector (Res10 /
# Caffe model).
# ─────────────────────────────────────────────────────────────────

import cv2
import os

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
_PROTOTXT = os.path.join(_MODEL_DIR, "deploy.prototxt")
_WEIGHTS = os.path.join(_MODEL_DIR, "res10_300x300.caffemodel")

CONFIDENCE_THRESHOLD = 0.6

_net = None


def _get_net():
    """Load the detector lazily so importing the module does not fail."""
    global _net

    if _net is None:
        if not os.path.isfile(_PROTOTXT):
            raise FileNotFoundError(f"Face detector model not found: {_PROTOTXT}")
        if not os.path.isfile(_WEIGHTS):
            raise FileNotFoundError(f"Face detector weights not found: {_WEIGHTS}")

        _net = cv2.dnn.readNetFromCaffe(_PROTOTXT, _WEIGHTS)

    return _net


def detect_faces(frame):
    """
    Detect faces in a BGR frame.

    Returns a list of (x, y, w, h) boxes clipped to the frame bounds.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return []

    h, w = frame.shape[:2]
    if h <= 0 or w <= 0:
        return []

    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),
        1.0,
        (300, 300),
        (104.0, 177.0, 123.0),
    )

    net = _get_net()
    net.setInput(blob)
    detections = net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        box = detections[0, 0, i, 3:7] * [w, h, w, h]
        x1, y1, x2, y2 = box.astype("int")

        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(w, int(x2)), min(h, int(y2))

        if x2 <= x1 or y2 <= y1:
            continue

        boxes.append((x1, y1, x2 - x1, y2 - y1))

    return boxes
