# FaceFare 🚌👤💳

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-SocketIO-black)](https://flask-socketio.readthedocs.io/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Face_Detection-green)](https://opencv.org/)
[![DeepFace](https://img.shields.io/badge/DeepFace-Facenet-orange)](https://github.com/serengil/deepface)

## 📌 Overview

FaceFare is a real-time, face-recognition-based fare collection system for public transport. Instead of tickets or tap cards, passengers are identified by their face as they board and exit — their wallet is automatically debited based on the distance travelled between stops, with zero manual scanning or payment steps.

A live camera feed, passenger recognition, and fare deduction are all shown on a real-time web dashboard.

## 🚀 Key Features

- **🎥 Real-Time Face Recognition** — Detects and identifies passengers from a live camera feed using OpenCV (Haar Cascade for detection) and DeepFace (Facenet embeddings) for recognition.
- **⛽ Automatic Fare Calculation** — Fare is calculated dynamically from a base fare plus a per-stop rate, based on the distance between the passenger's boarding and exit stops.
- **💰 Wallet-Based Payments** — Each passenger has a wallet balance that's automatically debited on exit; boarding is declined if funds are insufficient.
- **🔀 Entry/Exit Mode Switching** — The system can be toggled between ENTRY mode (boarding passengers) and EXIT mode (deducting fares as passengers leave).
- **🖥️ Live Web Dashboard** — A Flask + SocketIO powered frontend shows the live camera feed, onboard passenger list, recent transaction logs, and running revenue in real time.

## 🛠️ Technology Stack

- **Backend:** Flask, Flask-SocketIO
- **Computer Vision:** OpenCV (Haar Cascade face detection)
- **Face Recognition:** DeepFace (Facenet embedding model)
- **Deep Learning Runtime:** TensorFlow / Keras
- **Frontend:** HTML, CSS, JavaScript (Socket.IO client)

## 🏗️ System Architecture

1. **Camera Capture** — A background thread continuously reads frames from the webcam.
2. **Face Detection** — Each frame is scanned with a Haar Cascade classifier to locate faces.
3. **Face Recognition** — Detected face crops are passed to DeepFace, which generates a Facenet embedding and compares it against known passenger embeddings (loaded from `assets/known_faces/`) using distance matching.
4. **Passenger State Handling** — Depending on the current mode (ENTRY/EXIT), a recognized passenger is either boarded (recorded onboard + boarding stop) or charged and exited (fare calculated from stop distance, wallet debited).
5. **Live Updates** — Every processed frame pushes an updated state snapshot (onboard list, logs, wallet balances, revenue) to the frontend over WebSockets via SocketIO.

## 📂 Project Structure

```
FaceFare/
├── app.py                  # Main Flask + SocketIO application
├── assets/known_faces/     # Reference face images for known passengers
├── database/
│   └── models.py           # Passenger records & wallet balances
├── services/
│   ├── trip_manager.py     # Board/exit passenger logic
│   └── wallet.py           # Wallet deduction/top-up logic
├── vision/
│   ├── camera.py           # Webcam capture
│   └── recognition.py      # Face embedding + matching
├── templates/index.html    # Live dashboard frontend
└── requirements.txt
```

## 💻 Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/srivisnuA/FaceFare.git
cd FaceFare

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add reference faces
# Place one or more images per known passenger inside assets/known_faces/
# (filename, minus digits/extension, is used as the passenger's identity)

# 5. Run the application
python app.py

# 6. Open the dashboard
# Visit http://localhost:5000 in your browser
```

## 🎮 Usage

- Click **Start Camera** on the dashboard to begin live detection.
- Use the **Entry / Exit** toggle to switch between boarding and exit modes.
- Use **Next Stop / Previous Stop** to simulate the bus moving along its route as passengers board and exit.
- Recognized passengers are automatically boarded (ENTRY mode) or charged and exited (EXIT mode) based on the distance travelled.

## 🔮 Future Improvements

- Persistent storage (SQLite/PostgreSQL) for passenger wallets and trip history, replacing the current in-memory store
- Authentication for the driver/admin control panel
- Support for topping up wallets from the dashboard
- Deployment-ready configuration for running on embedded/edge hardware

## 📄 License

This project currently has no license specified.