import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import lampos


class LampOSJournalTest(unittest.TestCase):
    def test_result_requires_matching_run_and_refreshes_after_native_update(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            journal = state / "config/harness/results.json"
            journal.parent.mkdir(parents=True)
            journal.write_text(
                json.dumps(
                    {
                        "results": {
                            "one": {
                                "inputs": [{"runId": "other"}],
                                "payload": {"fullText": "wrong"},
                            }
                        }
                    }
                )
            )
            with patch.object(lampos, "STATE", state):
                self.assertIsNone(lampos.harness_result("current"))
                journal.write_text(
                    json.dumps(
                        {
                            "results": {
                                "two": {
                                    "inputs": [{"runId": "current"}],
                                    "payload": {"fullText": "confirmed"},
                                }
                            }
                        }
                    )
                )
                self.assertEqual(lampos.harness_result("current"), "confirmed")
                self.assertIsNone(lampos.harness_result("other"))

    def test_unknown_receipt_is_returned_without_resubmission(self):
        with (
            patch.object(
                lampos,
                "_journal",
                return_value={
                    "inputs": {"one": {"runId": "current", "idempotencyKey": "fixture"}}
                },
            ),
            patch.object(
                lampos, "request", return_value={"receipt": {"state": "unknown"}}
            ) as request,
        ):
            self.assertEqual(lampos.harness_delivery("current"), {"state": "unknown"})
            request.assert_called_once_with(
                "/api/harness/request",
                {"type": "receipt.get", "idempotencyKey": "fixture"},
            )

    def test_volume_rejects_invalid_values_before_command(self):
        with patch.object(lampos.subprocess, "run") as run:
            for value in [-1, 101, True, "30"]:
                with self.assertRaises(ValueError):
                    lampos.output_volume({"output": "default"}, value)
            run.assert_not_called()
