from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
ADAPTERS = HERE / "plugin" / "adapters"
SCRIPTS = HERE / "scripts"
sys.path.insert(0, str(ADAPTERS))

import common


def load_control():
    spec = importlib.util.spec_from_file_location("mem0_control_under_test", SCRIPTS / "mem0_control.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


control = load_control()


def load_hook():
    spec = importlib.util.spec_from_file_location("mem0_hook_under_test", ADAPTERS / "hook.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


hook = load_hook()


class AdapterTests(unittest.TestCase):
    def test_hook_uses_memoff_session_id(self):
        with patch.dict(os.environ, {"MEMOFF_SESSION_ID": "harness-session"}, clear=False):
            forwarded = json.loads(hook.forwarded_hook_input('{"session_id":"claude-session","prompt":"x"}'))
            self.assertEqual(forwarded["session_id"], "harness-session")
            self.assertEqual(forwarded["prompt"], "x")

    def test_scope_maps_repeat_store_to_both_mem0_lanes(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "MEMOFF_MEMORY_STORE": "memoff_mem0_r2_deadbeef",
                "MEMOFF_MEM0_DATA_ROOT": directory,
            },
            clear=False,
        ):
            common.configure_mem0_environment()
            self.assertEqual(os.environ["MEM0_PROJECT_ID"], "memoff_mem0_r2_deadbeef")
            self.assertEqual(os.environ["MEM0_USER_ID"], "memoff_mem0_r2_deadbeef")
            self.assertEqual(
                Path(os.environ["MEM0_CODE_DATA_DIR"]),
                Path(directory) / "memoff_mem0_r2_deadbeef",
            )
            self.assertEqual(os.environ["MEM0_TELEMETRY"], "false")

    def test_store_name_cannot_escape_data_root(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "MEMOFF_MEMORY_STORE": "..",
                "MEMOFF_MEM0_DATA_ROOT": directory,
            },
            clear=False,
        ):
            path = common.data_dir()
            self.assertEqual(path.parent, Path(directory))
            self.assertNotIn(path.name, {"", ".", ".."})

    def test_injected_context_is_copied_verbatim(self):
        context = "Relevant repository memories:\n- Keep File.write atomic."
        output = json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"MEMOFF_INJECTED_DIR": directory, "MEMOFF_SESSION_ID": "issue/08"},
            clear=False,
        ):
            written = common.audit_injected_context(output)
            self.assertEqual(len(written), 1)
            self.assertEqual(written[0].read_text(encoding="utf-8"), context)
            self.assertTrue(written[0].name.startswith("mem0-issue_08-01-"))

    def test_receipt_contains_ids_and_no_memory_bodies(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "MEMOFF_MEMORY_STORE": "receipt_store",
                "MEMOFF_MEM0_DATA_ROOT": directory,
                "MEMOFF_SESSION_ID": "issue-session",
            },
            clear=False,
        ):
            common.configure_mem0_environment()
            db = common.data_dir() / "evidence.sqlite3"
            db.parent.mkdir(parents=True)
            connection = sqlite3.connect(db)
            connection.executescript(
                """
                CREATE TABLE retrievals (
                    session_id TEXT, repo_id TEXT, memory_id TEXT,
                    injected_at TEXT, rank INTEGER, score REAL,
                    memory_text TEXT, context_chars INTEGER
                );
                CREATE TABLE operations (
                    id INTEGER PRIMARY KEY, session_id TEXT,
                    operation TEXT, duration_ms REAL
                );
                INSERT INTO retrievals VALUES
                    ('issue-session', 'repo', 'memory-123', 'now', 1, 0.91,
                     'secret body that must not appear', 32);
                INSERT INTO operations VALUES
                    (1, 'issue-session', 'first-prompt-search', 12.5);
                """
            )
            connection.commit()
            connection.close()

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(control.do_receipt(), 0)
            receipt = json.loads(stdout.getvalue())
            self.assertEqual(receipt["items"][0]["id"], "memory-123")
            self.assertEqual(receipt["items"][0]["rank"], 1)
            self.assertEqual(receipt["recall_ms"], 12.5)
            self.assertNotIn("secret body", stdout.getvalue())

    def test_wait_accepts_completed_flush_and_rejects_failed_flush(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "MEMOFF_MEMORY_STORE": "wait_store",
                "MEMOFF_MEM0_DATA_ROOT": directory,
                "MEM0_API_KEY": "test-only-key",
                "MEMOFF_SESSION_ID": "wait-session",
                "MEMOFF_WAIT_SECONDS": "0.1",
            },
            clear=False,
        ):
            common.configure_mem0_environment()
            db = common.data_dir() / "evidence.sqlite3"
            db.parent.mkdir(parents=True)
            connection = sqlite3.connect(db)
            connection.execute("CREATE TABLE flushes (session_id TEXT, status TEXT, created_at TEXT)")
            connection.execute("INSERT INTO flushes VALUES ('wait-session', 'semantic-succeeded', 'now')")
            pending = common.data_dir() / "pending"
            pending.mkdir()
            (pending / "worker.running").write_text("{}", encoding="utf-8")
            connection.commit()
            connection.close()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(control.do_wait(), 0)

            connection = sqlite3.connect(db)
            connection.execute("DELETE FROM flushes")
            connection.execute("INSERT INTO flushes VALUES ('wait-session', 'semantic-failed', 'now')")
            connection.commit()
            connection.close()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(control.do_wait(), 1)

    def test_smoke_wipe_check_detects_local_rows(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "MEMOFF_MEMORY_STORE": "dirty_store",
                "MEMOFF_MEM0_DATA_ROOT": directory,
                "MEMOFF_SMOKE": "1",
            },
            clear=False,
        ):
            common.configure_mem0_environment()
            db = common.data_dir() / "evidence.sqlite3"
            db.parent.mkdir(parents=True)
            connection = sqlite3.connect(db)
            connection.executescript(
                "CREATE TABLE events (id INTEGER);"
                "CREATE TABLE flushes (id INTEGER);"
                "CREATE TABLE retrievals (id INTEGER);"
                "INSERT INTO events VALUES (1);"
            )
            connection.commit()
            connection.close()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(control.do_wipe_check(), 1)

    def test_usage_is_explicitly_unmeasured(self):
        with patch.dict(os.environ, {"MEMOFF_SESSION_ID": "s"}, clear=False):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(control.do_usage(), 0)
            rows = json.loads(stdout.getvalue())
            self.assertEqual(rows[0]["source"], "server")
            self.assertNotIn("tokens_in", rows[0])
            self.assertNotIn("cost_usd", rows[0])
            self.assertIn("unmeasured", rows[0]["token_basis"])


if __name__ == "__main__":
    unittest.main()
