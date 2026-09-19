# security/privacy.py
# ─────────────────────────────────────────────────────────────────
# Privacy-by-design safeguards for the live camera feed.
# ─────────────────────────────────────────────────────────────────

import cv2


UNKNOWN_IDENTITIES = frozenset({
    "Unknown",
    "Unknown passenger",
    "No Face",
    "No passenger detected",
})


def blur_face(frame, x: int, y: int, w: int, h: int, ksize: int = 35):
    """
    Blur a face region of frame in-place.

    Coordinates are clipped to the frame so malformed detection boxes
    cannot produce an invalid slice.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return frame

    if w <= 0 or h <= 0:
        return frame

    frame_h, frame_w = frame.shape[:2]
    x1 = max(0, min(int(x), frame_w))
    y1 = max(0, min(int(y), frame_h))
    x2 = max(x1, min(int(x + w), frame_w))
    y2 = max(y1, min(int(y + h), frame_h))

    if x2 <= x1 or y2 <= y1:
        return frame

    k = max(3, int(ksize))
    if k % 2 == 0:
        k += 1

    roi = frame[y1:y2, x1:x2]
    blurred = cv2.GaussianBlur(roi, (k, k), 0)
    frame[y1:y2, x1:x2] = blurred
    return frame


def is_enrolled_passenger(pid: str) -> bool:
    """Return True only for a non-empty recognized passenger ID."""
    return bool(pid) and pid not in UNKNOWN_IDENTITIES
