import cv2


CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480


def open_camera(
    camera_index: int = CAMERA_INDEX,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
):
    """Open and configure a camera, raising a clear error on failure."""
    if not isinstance(camera_index, int) or isinstance(camera_index, bool):
        raise TypeError("camera_index must be an integer")
    if width <= 0 or height <= 0:
        raise ValueError("camera dimensions must be positive")

    cam = cv2.VideoCapture(camera_index)

    if not cam.isOpened():
        cam.release()
        raise RuntimeError(
            f"Camera {camera_index} is not accessible. "
            "Check the device index and camera permissions."
        )

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    return cam
