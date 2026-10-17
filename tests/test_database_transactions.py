"""Real SQLite tests: concurrency, rollback, migration and retry semantics."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from database import db, models
from services.fare_engine import calculate_fare
from services.trip_manager import board, exit_bus
from services.wallet import top_up


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(db, "DB_PATH", str(Path(self.temp.name) / "test.db"))
        self.path_patch.start()
        db.init_db(seed=False)
        models.add_passenger("alice", 10)

    def tearDown(self):
        self.path_patch.stop()
        self.temp.cleanup()

    def test_concurrent_deductions_never_overdraw(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: models.change_balance("alice", -1), range(30)))
        self.assertEqual(sum(value is not None for value in results), 10)
        self.assertEqual(models.get_balance("alice"), 0)
        ledger = models.get_transactions("alice")
        self.assertEqual(len(ledger), 11)
        self.assertEqual(sum(row["delta_cents"] for row in ledger), 0)

    def test_concurrent_topups_keep_cache_and_database_in_sync(self):
        cache = models.get_passengers()
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertTrue(all(pool.map(lambda _: top_up(cache, "alice", .01), range(40))))
        self.assertEqual(models.get_balance("alice"), 10.4)
        self.assertEqual(cache["alice"]["balance"], 10.4)

    def test_transaction_retry_does_not_charge_twice(self):
        models.change_balance("alice", -2, operation_id="trip-1")
        models.change_balance("alice", 3)
        self.assertEqual(models.change_balance("alice", -2, operation_id="trip-1"), 11)
        self.assertEqual(len(models.get_transactions("alice")), 3)
        with self.assertRaises(ValueError):
            models.change_balance("alice", -3, operation_id="trip-1")

    def test_ledger_failure_rolls_back_balance_and_rename(self):
        with closing(db.get_connection()) as conn, conn:
            conn.execute("CREATE TRIGGER reject_ledger BEFORE INSERT ON wallet_transactions BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            models.change_balance("alice", 1)
        with self.assertRaises(sqlite3.IntegrityError):
            models.edit_passenger("alice", "renamed", 20)
        self.assertEqual(models.get_all_balances(), {"alice": 10})
        self.assertEqual(models.get_transactions("alice")[0]["balance_cents"], 1000)

    def test_invalid_edit_leaves_identity_and_balance_untouched(self):
        for amount in [True, float("nan"), float("inf"), -.01, .001, 10**1000]:
            with self.subTest(amount=repr(amount)), self.assertRaises(ValueError):
                models.edit_passenger("alice", "new", amount)
        self.assertEqual(models.get_all_balances(), {"alice": 10})

    def test_rename_preserves_balance_and_ledger_delete_cascades(self):
        models.change_balance("alice", 5)
        models.rename_passenger("alice", "new")
        self.assertEqual(models.get_balance("new"), 15)
        self.assertEqual(len(models.get_transactions("new")), 2)
        models.delete_passenger("new")
        self.assertEqual(models.get_transactions("new"), [])

    def test_schema_initialization_does_not_duplicate_opening_balance(self):
        db.init_db(seed=False)
        db.init_db(seed=False)
        self.assertEqual(len(models.get_transactions("alice")), 1)

    def test_deleted_passengers_are_not_reseeded_on_restart(self):
        models.delete_passenger("alice")
        db.init_db()
        self.assertEqual(models.get_all_balances(), {})

    def test_legacy_wallet_gets_one_opening_entry(self):
        with closing(db.get_connection()) as conn, conn:
            conn.execute("INSERT INTO passengers VALUES ('legacy', 12.50)")
        db.init_db(seed=False)
        self.assertEqual(models.get_transactions("legacy")[0]["delta_cents"], 1250)

    def test_maximum_balance_cannot_overflow(self):
        models.update_balance("alice", 1_000_000_000)
        with self.assertRaises(ValueError):
            models.change_balance("alice", .01)
        self.assertEqual(models.get_balance("alice"), 1_000_000_000)

    def test_fare_boundaries_and_trip_cleanup(self):
        self.assertEqual(calculate_fare(0), 10)
        self.assertEqual(calculate_fare(3), 25)
        self.assertEqual(calculate_fare(2, .1, .1), .3)
        for value in [float("nan"), float("inf"), .001, -1]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate_fare(1, value)
        state = {"onboard": [], "boarding_stop": {"alice": 0}}
        board(state, "alice")
        board(state, "alice")
        self.assertEqual(state["onboard"], ["alice"])
        exit_bus(state, "alice")
        self.assertEqual(state, {"onboard": [], "boarding_stop": {}})
