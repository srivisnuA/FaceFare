import cv2
from recognition import recognize_face
from camera import open_camera

face_detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

cam = open_camera()

last_person = "No passenger detected"
stable_person = "No passenger detected"
frame_count = 0
STABILITY_THRESHOLD = 10

while True:

    ret, frame = cam.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_detector.detectMultiScale(gray, 1.3, 5)

    detected_person = "No passenger detected"

    if len(faces) > 0:
        (x, y, w, h) = faces[0]
        face_frame = frame[y:y+h, x:x+w]

        detected_person = recognize_face(face_frame)

        # Draw bounding box
        color = (0,255,0) if detected_person not in ["Unknown passenger","No passenger detected"] else (0,165,255)
        cv2.rectangle(frame,(x,y),(x+w,y+h),color,2)

    # stability logic
    if detected_person == last_person:
        frame_count += 1
    else:
        frame_count = 0

    if frame_count > STABILITY_THRESHOLD:
        stable_person = detected_person

    last_person = detected_person

    # display stable result
    if stable_person == "No passenger detected":
        color = (0,0,255)
    elif stable_person == "Unknown passenger":
        color = (0,165,255)
    else:
        color = (0,255,0)

    cv2.putText(
        frame,
        stable_person,
        (30,50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        2
    )

    cv2.imshow("FaceFare Passenger Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()