import io
import os
import tempfile
import unittest

from PIL import Image

import services.enrollment as enrollment


class FakeUpload:
    def __init__(self, filename, payload):
        self.filename = filename
        self.stream = io.BytesIO(payload)

    def save(self, path):
        self.stream.seek(0)
        with open(path, "wb") as handle:
            handle.write(self.stream.read())


def image_bytes(fmt="PNG", size=(320, 240)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (80, 120, 160)).save(buffer, format=fmt)
    return buffer.getvalue()


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_dir = enrollment.KNOWN_FACES_DIR
        enrollment.KNOWN_FACES_DIR = self.temp_dir.name

    def tearDown(self):
        enrollment.KNOWN_FACES_DIR = self.original_dir
        self.temp_dir.cleanup()

    def test_save_converts_uploaded_images_to_jpeg(self):
        files = [
            FakeUpload("praveen.png", image_bytes("PNG")),
            FakeUpload("praveen.jpeg", image_bytes("JPEG")),
        ]

        paths = enrollment.save_passenger_photos("praveen", files)

        self.assertEqual(
            [os.path.basename(path) for path in paths],
            ["praveen1.jpg", "praveen2.jpg"],
        )
        self.assertTrue(all(path.endswith(".jpg") for path in paths))
        with Image.open(paths[0]) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (320, 240))

    def test_rejects_undersized_images(self):
        files = [FakeUpload("tiny.jpg", image_bytes("JPEG", (100, 100)))]
        with self.assertRaisesRegex(ValueError, "at least 160x160"):
            enrollment.save_passenger_photos("tiny", files)

    def test_rejects_invalid_image_content(self):
        files = [FakeUpload("fake.jpg", b"not an image")]
        with self.assertRaisesRegex(ValueError, "valid image"):
            enrollment.save_passenger_photos("fake", files)

    def test_rejects_more_than_five_images(self):
        files = [FakeUpload(f"p{i}.jpg", image_bytes("JPEG")) for i in range(6)]
        with self.assertRaisesRegex(ValueError, "maximum of 5"):
            enrollment.save_passenger_photos("many", files)

    def test_next_photo_index_skips_existing_numbers(self):
        directory = enrollment.ensure_passenger_directory("praveen")
        with open(os.path.join(directory, "praveen1.jpg"), "wb") as handle:
            handle.write(image_bytes("JPEG"))
        with open(os.path.join(directory, "praveen4.jpg"), "wb") as handle:
            handle.write(image_bytes("JPEG"))

        self.assertEqual(enrollment.next_photo_index("praveen"), 5)


if __name__ == "__main__":
    unittest.main()
