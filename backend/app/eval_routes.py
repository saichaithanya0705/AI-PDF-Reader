"""Read-only API for RAG eval reports produced by app/evals/harness.py.

Runs are started from the CLI, not over HTTP: a run calls paid NVIDIA endpoints
and takes tens of seconds, so it should not be triggerable by any signed-in user.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from .auth_middleware import get_current_user
from .evals.harness import HISTORY_DIR, LATEST_PATH

router = APIRouter(prefix="/api/evals", tags=["evals"])


def _read_report(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No eval report found. Run: python -m app.evals.harness")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Eval report is not valid JSON")


@router.get("/latest")
async def latest_eval_report(current_user: dict = Depends(get_current_user)):
    return _read_report(LATEST_PATH)


@router.get("/history")
async def eval_history(current_user: dict = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """Compact per-run summaries, newest first, for trend display."""
    runs: List[Dict[str, Any]] = []
    for path in sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:50]:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        variants = report.get("variants", {})
        runs.append({
            "run_id": report.get("run_id"),
            "created_at": report.get("created_at"),
            "mode": report.get("mode"),
            "git_commit": report.get("git_commit"),
            "passed": report.get("passed"),
            "hybrid": variants.get("hybrid", {}).get("summary", {}),
            "hybrid_rerank": variants.get("hybrid_rerank", {}).get("summary", {}),
            "cross_document": variants.get("cross_document", {}).get("summary", {}),
        })
    return runs
