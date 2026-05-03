"""Tests for simulation/queue.py — atomicity, FIFO, and state machine."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation import queue as job_queue


@pytest.fixture
def conn(tmp_path: Path):
    db = tmp_path / "queue.db"
    return job_queue.connect(db)


def test_enqueue_and_stats(conn) -> None:
    for i in range(5):
        job_queue.enqueue(conn, f"sc_{i:04d}", {"i": i})
    s = job_queue.stats(conn)
    assert s.get("pending") == 5


def test_enqueue_duplicate_is_noop(conn) -> None:
    job_queue.enqueue(conn, "sc_0001", {"v": 1})
    job_queue.enqueue(conn, "sc_0001", {"v": 2})
    assert job_queue.stats(conn).get("pending") == 1


def test_claim_fifo_and_marks_running(conn) -> None:
    for i in range(3):
        job_queue.enqueue(conn, f"sc_{i:04d}", {"i": i})
    jobs = job_queue.claim(conn, worker_id="w1", n=2)
    assert [j.scenario_id for j in jobs] == ["sc_0000", "sc_0001"]
    assert all(j.status == "running" for j in jobs)
    s = job_queue.stats(conn)
    assert s.get("running") == 2
    assert s.get("pending") == 1


def test_claim_does_not_double_dispatch(conn) -> None:
    job_queue.enqueue(conn, "sc_0001", {"i": 1})
    a = job_queue.claim(conn, worker_id="wA", n=1)
    b = job_queue.claim(conn, worker_id="wB", n=1)
    assert len(a) == 1
    assert len(b) == 0


def test_claim_empty_returns_empty(conn) -> None:
    assert job_queue.claim(conn, worker_id="w", n=1) == []


def test_mark_done_and_failed(conn) -> None:
    job_queue.enqueue(conn, "sc_0001", {"i": 1})
    job_queue.enqueue(conn, "sc_0002", {"i": 2})
    job_queue.claim(conn, worker_id="w1", n=2)
    job_queue.mark_done(conn, "sc_0001", "/tmp/sc_0001.h5", 12.5)
    job_queue.mark_failed(conn, "sc_0002", "boom")
    s = job_queue.stats(conn)
    assert s.get("done") == 1
    assert s.get("failed") == 1


def test_params_round_trip(conn) -> None:
    payload = {"a": 1, "b": 2.0, "c": "x"}
    job_queue.enqueue(conn, "sc_0001", payload)
    jobs = job_queue.claim(conn, worker_id="w", n=1)
    assert jobs[0].params == payload
