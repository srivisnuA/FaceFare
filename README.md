# FaceFare 🚌👤💳

FaceFare is a real-time face-recognition-based fare collection prototype for public transport. Passengers are identified through a camera while boarding and exiting, and the system calculates and deducts the fare from a passenger wallet.

> **Project status:** Prototype / academic project. The current implementation is designed for local development and demonstration, not production deployment.

## Features

- **Real-time face recognition** using OpenCV face detection and DeepFace/FaceNet-based recognition.
- **Entry and exit modes** for simulating passenger boarding and exit.
- **Distance-based fare calculation** using a base fare plus a per-stop rate.
- **Wallet management** with atomic balance updates and fare deduction.
- **Live dashboard** using Flask, Flask-SocketIO, HTML, CSS and JavaScript.
- **SQLite-backed passenger data** for local persistence.
- **Trip/session handling** for tracking boarding and exit state.
- **Privacy handling** that blurs unrecognized faces before the video frame is streamed.
- **Authenticated driver dashboard** with configurable Socket.IO origins.

## Architecture

```text
Camera Feed
    │
    ▼
OpenCV Face Detection
    │
    ▼
DeepFace / FaceNet Recognition
    │
    ▼
Trip / Fare Logic
    ├──────────────┐
    ▼              ▼
SQLite       Atomic Wallet
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
│   ├── auth.py              # Driver/admin authentication
│   └── privacy.py           # Face privacy helpers
├── vision/
│   ├── camera.py            # Camera initialization
│   ├── face_detector.py     # OpenCV DNN detection
│   ├── models/              # Face detector model files
│   └── recognition.py       # DeepFace recognition
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

The filename is used as the passenger identifier after numeric characters are removed. Make sure the resulting identifier matches a passenger in the SQLite database.

### 5. Start the application

```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

## Authentication and Configuration

For local development, the application has development fallbacks. **Do not use those defaults in a deployed environment.**

Set:

**PowerShell**

```powershell
$env:FACEFARE_ENV="production"
$env:FACEFARE_SECRET_KEY="replace-with-a-long-random-secret"
$env:FACEFARE_ADMIN_PASSWORD="replace-with-a-strong-password"
```

Optional Socket.IO cross-origin configuration:

```powershell
$env:FACEFARE_CORS_ORIGINS="https://dashboard.example.com"
```

Multiple origins can be comma-separated.

Do not commit real production secrets, passwords, API keys or credentials.

## How It Works

1. The camera captures video frames.
2. OpenCV detects faces.
3. The recognition pipeline attempts to identify the passenger.
4. In **ENTRY** mode, the passenger is added to the active trip.
5. In **EXIT** mode, the fare is calculated from the boarding and exit stops.
6. The wallet transaction is committed atomically to SQLite.
7. The dashboard receives live state updates through Socket.IO.
8. Unrecognized faces are blurred before the frame is streamed.

## Fare Calculation

```text
Fare = Base Fare + (Stop Distance × Per-Stop Rate)
```

Default values in `config.py`:

- Base fare: **₹10**
- Per-stop rate: **₹5**
- Route: **Stop A → Stop B → Stop C → Stop D → Stop E**

These are prototype configuration values and can be changed.

## Development Notes

The codebase has been hardened around several failure modes:

- Application and admin secrets are required outside development.
- Socket.IO cross-origin access is configurable instead of universally open.
- Login redirects are restricted to local application paths.
- Control actions are validated.
- Wallet updates use SQLite transactions to avoid concurrent lost updates or negative balances.
- Database connections are closed reliably.
- Camera/model initialization is defensive.
- Transaction logging is serialized across threads.
- Unrecognized faces are blurred before streaming.
- The legacy duplicate Flask implementation has been removed.

## Privacy Considerations

Face recognition involves biometric data and requires careful handling. This prototype should only be tested with appropriate consent and controlled access.

Before production use, the system should address secure biometric-data storage, encryption, access controls, retention/deletion policies, passenger consent, protection of reference face images, audit logging and secure authentication.

The current implementation does **not** claim to provide the planned SHA-256 embedding-hashing architecture or a complete privacy-preserving biometric deployment.

## Roadmap

1. Improve recognition performance and temporal stability.
2. Add automated tests and CI.
3. Persist complete trip and transaction records.
4. Implement dual-camera entry/exit architecture.
5. Calibrate and validate recognition thresholds with representative test data.
6. Strengthen privacy-preserving biometric-data handling.
7. Add production deployment and monitoring configuration.

## License

No open-source license is currently specified for this repository. Until a license is added, the code should not be assumed to be freely reusable, modified or redistributed.

## Author

**Srivisnu A**  
CSE — Data Science
