import cv2
from camera import open_camera

cam = open_camera()

while True:
    ret, frame = cam.read()

    if not ret:
        break

    cv2.imshow("FaceFare Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cam.release()
cv2.destroyAllWindows()