"""Tests for simulation/campaign.py — non-Waiwera parts only.

The Kaggle-only Waiwera invocation is tested on Kaggle by the RFP
benchmark; here we cover the producer side and rendering glue.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from simulation import queue as job_queue
from simulation.campaign import _waiwera_available, enqueue_campaign, render_job
from simulation.sampling import sample


def test_enqueue_campaign_inserts_n_jobs(tmp_path: Path) -> None:
    db = tmp_path / "queue.db"
    n = enqueue_campaign(8, seed=0, db_path=db)
    assert n == 8
    conn = job_queue.connect(db)
    assert job_queue.stats(conn).get("pending") == 8


def test_render_job_writes_files(tmp_path: Path) -> None:
    s = sample(1, seed=42)[0]
    bundle = render_job(s, tmp_path / s.scenario_id)
    assert bundle.json_path.exists()
    assert bundle.mesh_path.exists()


def test_waiwera_available_respects_override(monkeypatch) -> None:
    monkeypatch.setenv("WAIWERA_AVAILABLE", "1")
    assert _waiwera_available() is True
    monkeypatch.setenv("WAIWERA_AVAILABLE", "0")
    assert _waiwera_available() is False


def test_consume_raises_without_waiwera(monkeypatch, tmp_path: Path) -> None:
    from simulation.campaign import consume
    monkeypatch.setenv("WAIWERA_AVAILABLE", "0")
    with pytest.raises(RuntimeError, match="WAIWERA"):
        consume(worker_id="test", work_root=tmp_path, max_jobs=1, db_path=tmp_path / "q.db")
