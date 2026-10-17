"""Demonstrate a complete trip with synthetic scans in an isolated temporary DB."""
import json
import os
from pathlib import Path
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix="facefare-demo-") as directory:
        os.environ["FACEFARE_DEMO"] = "1"
        os.environ["FACEFARE_DATA_DIR"] = directory
        from services import logger
        logger.LOG_FILE = str(Path(directory) / "transactions.log")
        import app as service
        from database.models import add_passenger, get_transactions
        from security.auth import ADMIN_PASSWORD
        add_passenger("demo-rider", 100)
        service.refresh_passenger_cache()
        client = service.app.test_client()
        client.get("/login")
        with client.session_transaction() as session:
            token = session["_csrf_token"]
        response = client.post("/login", data={"password": ADMIN_PASSWORD, "csrf_token": token})
        assert response.status_code == 302
        client.get("/")
        with client.session_transaction() as session:
            headers = {"X-CSRF-Token": session["_csrf_token"]}

        def post(path, payload):
            result = client.post(path, json=payload, headers=headers)
            if result.status_code != 200:
                raise RuntimeError(result.json)
            return result.json

        boarding = post("/api/demo/scan", {"passenger": "demo-rider"})
        for _ in range(2):
            post("/control", {"action": "next_stop"})
        post("/control", {"action": "exit"})
        exit_result = post("/api/demo/scan", {"passenger": "demo-rider"})
        duplicate = post("/api/demo/scan", {"passenger": "demo-rider"})
        assert exit_result["snapshot"]["wallets"]["demo-rider"] == 80
        assert duplicate["event"] is None
        print(json.dumps({
            "mode": "synthetic scans through Flask test client; real SQLite",
            "boarding": boarding["event"], "exit": exit_result["event"],
            "final_balance": 80, "duplicate_exit_charged": False,
            "ledger": get_transactions("demo-rider"),
        }, indent=2))


if __name__ == "__main__":
    main()
