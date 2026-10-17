"""Wallet boundary and persistence tests without requiring a live camera."""
import math
import unittest
from unittest.mock import patch

from services import wallet


class WalletValidationTests(unittest.TestCase):
    def test_invalid_amounts_are_rejected_before_persistence(self):
        passengers = {"p1": {"balance": 100}}
        for amount in (float("nan"), float("inf"), -float("inf"), 0, -1, True, "10"):
            with self.subTest(amount=repr(amount)):
                with patch("services.wallet._change_balance") as change:
                    self.assertFalse(wallet.top_up(passengers, "p1", amount))
                    self.assertFalse(wallet.deduct_balance(passengers, "p1", amount))
                    change.assert_not_called()
        self.assertEqual(passengers["p1"]["balance"], 100)

    def test_successful_top_up_updates_cache_only_after_persistence(self):
        passengers = {"p1": {"balance": 100}}
        with patch("services.wallet._change_balance", return_value=125) as change:
            self.assertTrue(wallet.top_up(passengers, "p1", 25))
            change.assert_called_once_with("p1", 25)
        self.assertEqual(passengers["p1"]["balance"], 125)

    def test_insufficient_funds_preserve_cached_balance(self):
        passengers = {"p1": {"balance": 10}}
        with patch("services.wallet._change_balance", return_value=None):
            self.assertFalse(wallet.deduct_balance(passengers, "p1", 50))
        self.assertEqual(passengers["p1"]["balance"], 10)


if __name__ == "__main__":
    unittest.main()
