from deepface import DeepFace
import numpy as np
import os
import re
import cv2

KNOWN_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "known_faces",
)

MATCH_THRESHOLD = 10.0

known_embeddings = []
known_names = []

def load_known_faces():
    """Load embeddings from the enrolled-face directory."""
    known_embeddings.clear()
    known_names.clear()

    if not os.path.isdir(KNOWN_FACES_DIR):
        return

    for file in sorted(os.listdir(KNOWN_FACES_DIR)):
        path = os.path.join(KNOWN_FACES_DIR, file)

        if not os.path.isfile(path):
            continue

        try:
            embedding = DeepFace.represent(
                img_path=path,
                model_name="Facenet",
                enforce_detection=False,
            )[0]["embedding"]

            name = os.path.splitext(file)[0]
            name = re.sub(r"\d+", "", name).strip()

            if not name:
                continue

            known_embeddings.append(np.asarray(embedding, dtype=np.float32))
            known_names.append(name)
        except Exception as exc:
            print(f"[Recognition] Could not load {file}: {exc}")


load_known_faces()


def recognize_face(frame):
    """Return the best enrolled passenger match for a face crop."""
    if frame is None or getattr(frame, "size", 0) == 0:
        return "No passenger detected"

    try:
        embedding = DeepFace.represent(
            img_path=frame,
            model_name="Facenet",
            enforce_detection=False,
        )[0]["embedding"]

        embedding = np.asarray(embedding, dtype=np.float32)

        if not known_embeddings:
            return "Unknown passenger"

        best_match = None
        best_distance = float("inf")

        for name, known in zip(known_names, known_embeddings):
            if known.shape != embedding.shape:
                continue

            distance = float(np.linalg.norm(embedding - known))
            if distance < best_distance:
                best_distance = distance
                best_match = name

        if best_match is not None and best_distance < MATCH_THRESHOLD:
            return best_match

        return "Unknown passenger"

    except Exception as exc:
        print(f"[Recognition] Recognition error: {exc}")
        return "No passenger detected"
