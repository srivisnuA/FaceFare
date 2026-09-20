from deepface import DeepFace
import numpy as np
import os
import re
import threading

KNOWN_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "known_faces",
)

MATCH_THRESHOLD = 10.0

known_embeddings = []
known_names = []
recognition_lock = threading.RLock()


def _face_files():
    """Yield enrolled image paths with their passenger identifiers."""
    if not os.path.isdir(KNOWN_FACES_DIR):
        return

    for root, dirs, files in os.walk(KNOWN_FACES_DIR):
        dirs.sort()
        for file in sorted(files):
            path = os.path.join(root, file)
            if not os.path.isfile(path):
                continue

            if root == KNOWN_FACES_DIR:
                # Backward compatibility with the original flat layout:
                # praveen1.jpg, praveen2.jpg -> passenger "praveen".
                name = re.sub(r"\d+", "", os.path.splitext(file)[0]).strip()
            else:
                # New layout:
                # known_faces/praveen/praveen1.jpg -> passenger "praveen".
                name = os.path.basename(root).strip()

            if name:
                yield path, name


def load_known_faces():
    """Load embeddings from flat or per-passenger face directories."""
    with recognition_lock:
        known_embeddings.clear()
        known_names.clear()

        files = list(_face_files())
        for path, name in files:
            try:
                embedding = DeepFace.represent(
                    img_path=path,
                    model_name="Facenet",
                    enforce_detection=False,
                )[0]["embedding"]

                known_embeddings.append(
                    np.asarray(embedding, dtype=np.float32)
                )
                known_names.append(name)
            except Exception as exc:
                print(f"[Recognition] Could not load {path}: {exc}")



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

        with recognition_lock:
            if not known_embeddings:
                return "Unknown passenger"
            enrolled = list(zip(known_names, known_embeddings))

        best_match = None
        best_distance = float("inf")

        for name, known in enrolled:
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
