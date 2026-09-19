# vision/face_detector.py
# ─────────────────────────────────────────────────────────────────
# Face detection using OpenCV's DNN-based SSD detector (Res10 /
# Caffe model), swapped in to replace the old Haar Cascade detector.
#
# Why: Haar Cascade is fast but weak — poor with angled faces, bad
# lighting, and gives no confidence score (more false positives).
# This CNN-based detector is far more robust while still running
# close to real-time (~22 FPS), unlike MTCNN/RetinaFace which are
# much more accurate but too slow (~2.5s/frame) for a live feed.
# ─────────────────────────────────────────────────────────────────

import cv2
import os

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
_PROTOTXT  = os.path.join(_MODEL_DIR, "deploy.prototxt")
_WEIGHTS   = os.path.join(_MODEL_DIR, "res10_300x300.caffemodel")

_net = cv2.dnn.readNetFromCaffe(_PROTOTXT, _WEIGHTS)

CONFIDENCE_THRESHOLD = 0.6


def detect_faces(frame):
    """
    Detect faces in a BGR frame.
    Returns a list of (x, y, w, h) boxes, clipped to the frame bounds,
    for every detection above CONFIDENCE_THRESHOLD.
    """
    h, w = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
    )
    _net.setInput(blob)
    detections = _net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence < CONFIDENCE_THRESHOLD:
            continue

        box = detections[0, 0, i, 3:7] * [w, h, w, h]
        (x1, y1, x2, y2) = box.astype("int")

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            continue

        boxes.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1)))

    return boxes