from deepface import DeepFace
import numpy as np
import os
import re
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.environ.get(
    "FACEFARE_DATA_DIR",
    os.path.join(PROJECT_ROOT, "data"),
)
KNOWN_FACES_DIR = os.path.join(DATA_DIR, "known_faces")

MATCH_THRESHOLD = float(os.environ.get("FACEFARE_MATCH_THRESHOLD", "10.0"))
MATCH_MARGIN = float(os.environ.get("FACEFARE_MATCH_MARGIN", "0.20"))

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

        # Compare every enrolled photo, but collapse scores by passenger.
        # This improves consistency when a passenger has several enrolled images.
        person_best = {}
        for name, known in enrolled:
            if known.shape != embedding.shape:
                continue

            distance = float(np.linalg.norm(embedding - known))
            current = person_best.get(name)
            if current is None or distance < current:
                person_best[name] = distance

        if not person_best:
            return "Unknown passenger"

        ranked = sorted(person_best.items(), key=lambda item: item[1])
        best_match, best_distance = ranked[0]

        # Keep the original recognition threshold so enrolled passengers
        # continue to be recognized normally. Only reject a very close
        # runner-up when the two scores are genuinely almost identical.
        if best_distance < MATCH_THRESHOLD:
            if len(ranked) > 1:
                second_name, second_distance = ranked[1]
                if (
                    second_distance < MATCH_THRESHOLD
                    and (second_distance - best_distance) < MATCH_MARGIN
                ):
                    print(
                        f"[Recognition] Ambiguous match: {best_match} "
                        f"{best_distance:.3f} vs runner-up {second_name} "
                        f"{second_distance:.3f}"
                    )
                    return "Unknown passenger"
            return best_match

        return "Unknown passenger"

    except Exception as exc:
        print(f"[Recognition] Recognition error: {exc}")
        return "No passenger detected"
