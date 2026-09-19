# FaceFare 🚌👤💳

FaceFare is a real-time face-recognition-based fare collection prototype for public transport. Passengers are identified through a camera while boarding and exiting, and the system calculates and deducts the fare from a passenger wallet.

> **Project status:** Prototype / academic project. The current implementation is designed for local development and demonstration, not production deployment.

## Features

- **Real-time face recognition** using OpenCV face detection and DeepFace/FaceNet-based recognition.
- **Entry and exit modes** for simulating passenger boarding and exit.
- **Distance-based fare calculation** using a base fare plus a per-stop rate.
- **Wallet management** with balance checks and fare deduction.
- **Live dashboard** using Flask, Flask-SocketIO, HTML, CSS and JavaScript.
- **SQLite-backed passenger data** for local persistence.
- **Trip/session handling** for tracking boarding and exit state.
- **Known-face directory** for enrolling reference images.

## Architecture

```text
Camera Feed
    │
    ▼
OpenCV Detection
    │
    ▼
DeepFace / FaceNet Recognition
    │
    ▼
Trip / Fare Logic
    ├──────────────┐
    ▼              ▼
SQLite        Wallet / Fare
    └──────┬───────┘
           ▼
Flask + Socket.IO
    Live Dashboard
```

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| Web backend | Flask |
| Real-time communication | Flask-SocketIO |
| Computer vision | OpenCV |
| Face recognition | DeepFace / FaceNet |
| ML runtime | TensorFlow / Keras |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Charts | Chart.js |

## Project Structure

```text
FaceFare/
├── app.py
├── app2.py                  # Legacy/alternate Flask implementation
├── config.py
├── requirements.txt
├── assets/
│   └── known_faces/         # Reference face images
├── database/
│   ├── db.py                # SQLite connection and initialization
│   └── models.py            # Passenger/wallet operations
├── services/
│   ├── fare_engine.py       # Fare calculation
│   ├── logger.py            # Event logging
│   ├── trip_manager.py      # Boarding/exit state
│   └── wallet.py            # Wallet operations
├── security/
│   ├── auth.py
│   └── privacy.py
├── vision/
│   ├── camera.py
│   ├── face_detector.py
│   └── recognition.py
└── templates/
    ├── index.html
    └── login.html
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/srivisnuA/FaceFare.git
cd FaceFare
```

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv venv
venv\\Scripts\\activate
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add known faces

Place reference images for enrolled passengers under `assets/known_faces/`.

### 5. Start the application

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

## How It Works

1. The camera captures video frames.
2. OpenCV detects faces.
3. The recognition pipeline attempts to identify the passenger.
4. In **ENTRY** mode, the passenger is added to the active trip.
5. In **EXIT** mode, the fare is calculated from the boarding and exit stops.
6. The wallet is updated.
7. The dashboard receives live state updates through Socket.IO.

## Fare Calculation

```text
Fare = Base Fare + (Stop Distance × Per-Stop Rate)
```

Default values in `config.py`:

- Base fare: **₹10**
- Per-stop rate: **₹5**
- Route: **Stop A → Stop B → Stop C → Stop D → Stop E**

These are prototype configuration values and can be changed.

## Configuration

The Flask secret key can be supplied through the `FACEFARE_SECRET_KEY` environment variable.

```powershell
$env:FACEFARE_SECRET_KEY="replace-with-a-random-secret"
```

Do not commit real production secrets, passwords, API keys or credentials.

## Current Development Notes

FaceFare is still under active development. Planned engineering improvements include:

- Recognition speed and stability.
- Separation of camera, recognition, business and web layers.
- Persistent trip and transaction records.
- Atomic wallet/fare transactions.
- Authentication and session security.
- Automated testing.
- Dual-camera entry/exit support.
- Privacy and biometric-data handling.

The repository contains prototype and legacy components while these areas are being consolidated.

## Privacy Considerations

Face recognition involves biometric data and requires careful handling. This prototype should only be tested with appropriate consent and controlled access.

Before production use, the system should address secure biometric-data storage, encryption, access controls, retention/deletion policies, passenger consent, protection of reference face images, audit logging and secure authentication.

## Roadmap

1. Stabilize the recognition pipeline.
2. Improve recognition performance and temporal stability.
3. Separate application, service and vision responsibilities.
4. Persist trips and transactions.
5. Make wallet/fare operations atomic.
6. Harden authentication and web security.
7. Add automated tests.
8. Remove or archive legacy implementations.
9. Implement the dual-camera entry/exit architecture.
10. Strengthen privacy-preserving biometric-data handling.
11. Add production deployment and monitoring configuration.

## License

No open-source license is currently specified for this repository. Until a license is added, the code should not be assumed to be freely reusable, modified or redistributed.

## Author

**Srivisnu A**  
CSE — Data Science
