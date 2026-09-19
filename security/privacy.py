# security/privacy.py
# ─────────────────────────────────────────────────────────────────
# Privacy-by-design safeguards for the live camera feed:
#
#   - Faces that are NOT recognized as an enrolled passenger are
#     blurred before the frame is streamed to the dashboard, so
#     bystanders who aren't system users are never broadcast
#     clearly over the network.
#   - No raw camera frames or face crops are ever written to disk —
#     each frame only lives in memory for one loop iteration before
#     being discarded (see app.py's camera_thread()).
# ─────────────────────────────────────────────────────────────────

import cv2


def blur_face(frame, x: int, y: int, w: int, h: int, ksize: int = 35):
    """
    Blur the given face region of *frame* in-place, for privacy.
    Used for any face that isn't a recognized, enrolled passenger.
    """
    roi = frame[y:y + h, x:x + w]
    if roi.size == 0:
        return frame

    # Kernel size must be odd for GaussianBlur.
    k = ksize if ksize % 2 == 1 else ksize + 1
    blurred = cv2.GaussianBlur(roi, (k, k), 0)
    frame[y:y + h, x:x + w] = blurred
    return frame


def is_enrolled_passenger(pid: str) -> bool:
    """True if *pid* is a real recognized passenger (not Unknown/No Face)."""
    return pid not in ("Unknown", "Unknown passenger", "No Face", "No passenger detected")