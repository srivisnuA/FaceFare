from deepface import DeepFace
import numpy as np
import os
import re
import cv2

KNOWN_FACES_DIR = "assets/known_faces"

# OpenCV face detector
face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

known_embeddings = []
known_names = []

def load_known_faces():

    for file in os.listdir(KNOWN_FACES_DIR):

        path = os.path.join(KNOWN_FACES_DIR, file)

        try:
            embedding = DeepFace.represent(
                img_path=path,
                model_name="Facenet",
                enforce_detection=False
            )[0]["embedding"]

            name = os.path.splitext(file)[0]
            name = re.sub(r'\d+', '', name)

            known_embeddings.append(np.array(embedding))
            known_names.append(name)

        except:
            pass


load_known_faces()


def recognize_face(frame):

    # Detect face first
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return "No passenger detected"

    try:
        embedding = DeepFace.represent(
            img_path=frame,
            model_name="Facenet",
            enforce_detection=False
        )[0]["embedding"]

        embedding = np.array(embedding)

        best_match = None
        best_distance = 999

        for i, known in enumerate(known_embeddings):

            distance = np.linalg.norm(embedding - known)

            if distance < best_distance:
                best_distance = distance
                best_match = known_names[i]

        if best_distance < 10:
            return best_match

        return "Unknown passenger"

    except:
        return "No passenger detected"