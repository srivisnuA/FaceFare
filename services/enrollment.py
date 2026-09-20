import os
import re

from security.privacy import UNKNOWN_IDENTITIES

KNOWN_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "known_faces",
)

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
MAX_PHOTOS_PER_REQUEST = 5
MAX_PASSENGER_ID_LENGTH = 50

_PASSENGER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,49}$")


def normalize_passenger_id(raw_pid: str) -> str:
    """Validate and normalize a passenger identifier for storage and URLs."""
    if not isinstance(raw_pid, str):
        raise ValueError("Passenger name must be text")

    pid = " ".join(raw_pid.strip().split())
    if not pid:
        raise ValueError("Passenger name is required")
    if len(pid) > MAX_PASSENGER_ID_LENGTH:
        raise ValueError("Passenger name is too long")
    if pid in UNKNOWN_IDENTITIES:
        raise ValueError("This passenger name is reserved")
    if not _PASSENGER_ID_PATTERN.fullmatch(pid):
        raise ValueError(
            "Passenger name may contain only letters, numbers, spaces, "
            "hyphens, and underscores"
        )
    return pid


def passenger_directory(pid: str) -> str:
    """Return the filesystem directory used for a passenger's face images."""
    pid = normalize_passenger_id(pid)
    return os.path.join(KNOWN_FACES_DIR, pid)


def validate_image_extension(filename: str) -> str:
    """Return a safe lowercase image extension or raise ValueError."""
    if not isinstance(filename, str):
        raise ValueError("Invalid image filename")

    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Only JPG, JPEG, and PNG images are allowed")
    return extension


def next_photo_index(pid: str) -> int:
    """Find the next numeric filename suffix for a passenger."""
    directory = passenger_directory(pid)
    if not os.path.isdir(directory):
        return 1

    prefix = f"{pid}"
    indexes = []

    for filename in os.listdir(directory):
        stem, extension = os.path.splitext(filename)
        if extension.lower() not in ALLOWED_IMAGE_EXTENSIONS:
            continue
        match = re.fullmatch(rf"{re.escape(prefix)}(\d+)", stem)
        if match:
            indexes.append(int(match.group(1)))

    return max(indexes, default=0) + 1


def ensure_passenger_directory(pid: str) -> str:
    """Create and return a passenger's face-image directory."""
    directory = passenger_directory(pid)
    os.makedirs(directory, exist_ok=True)
    return directory
