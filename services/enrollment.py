import os
import re
import threading

from PIL import Image, ImageOps, UnidentifiedImageError

from security.privacy import UNKNOWN_IDENTITIES

KNOWN_FACES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "known_faces",
)

ALLOWED_IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
MAX_PHOTOS_PER_REQUEST = 5
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MIN_IMAGE_WIDTH = 160
MIN_IMAGE_HEIGHT = 160
MAX_PASSENGER_ID_LENGTH = 50

_PASSENGER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,49}$")
ENROLLMENT_LOCK = threading.Lock()


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


def validate_image_file(file) -> str:
    """Validate an uploaded image's size and actual image contents."""
    filename = getattr(file, "filename", "")
    extension = validate_image_extension(filename)

    stream = getattr(file, "stream", None)
    if stream is None:
        raise ValueError("Invalid image upload")

    position = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)

    if size <= 0:
        raise ValueError("Uploaded image is empty")
    if size > MAX_PHOTO_BYTES:
        raise ValueError("Each photo must be 10 MB or smaller")

    try:
        with Image.open(stream) as image:
            width, height = image.size
            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                raise ValueError(
                    f"Each photo must be at least {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels"
                )
            image.verify()
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError):
        raise ValueError("Uploaded file is not a valid image") from None
    finally:
        stream.seek(position)

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


def save_passenger_photos(pid: str, files) -> list[str]:
    """Save uploaded image files as <pid>1.jpg, <pid>2.jpg, etc."""
    pid = normalize_passenger_id(pid)

    if not files:
        raise ValueError("At least one photo is required")

    files = list(files)
    if len(files) > MAX_PHOTOS_PER_REQUEST:
        raise ValueError(
            f"A maximum of {MAX_PHOTOS_PER_REQUEST} photos can be uploaded at once"
        )

    with ENROLLMENT_LOCK:
        directory = ensure_passenger_directory(pid)
        next_index = next_photo_index(pid)
        saved_paths = []

        try:
            for file in files:
                validate_image_file(file)

                path = os.path.join(
                    directory,
                    f"{pid}{next_index}.jpg",
                )
                file.stream.seek(0)
                with Image.open(file.stream) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.save(path, format="JPEG", quality=92, optimize=True)
                saved_paths.append(path)
                next_index += 1
        except Exception:
            for path in saved_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass
            raise

        return saved_paths
